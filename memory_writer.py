"""Centralized layered-memory write orchestration for Phase 2.

All writes to `memory/` must go through `MemoryWriter`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import uuid
from typing import Any
from memory_invariants import (
    InvariantViolation,
    INVARIANTS_CHECKED,
    check_combat_consistency,
    check_location_exists,
    check_npc_files_present,
    check_resurrection_consistency,
    validate_state_invariants,
)


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


@dataclass
class WriteIntent:
    file: str
    content: str
    required_fields: list[str] = field(default_factory=list)


@dataclass
class JournalEntry:
    turn: int
    session_id: str
    agent: str
    status: str
    planned_at: str
    committed_at: str | None = None
    writes: list[dict[str, Any]] = field(default_factory=list)
    invariants_checked: list[str] = field(default_factory=list)
    invariants_failed: list[str] = field(default_factory=list)
    rollback_applied: bool = False
    error: str | None = None
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    projected_state: dict[str, Any] = field(default_factory=dict, repr=False)
    index_content: str | None = field(default=None, repr=False)
    legacy_state: dict[str, Any] | None = field(default=None, repr=False)
    _runtime: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass
class CommitResult:
    success: bool
    status: str
    entry: JournalEntry
    violations: list[InvariantViolation] = field(default_factory=list)


class MemoryWriter:
    """Single writer for topic files, index, and optional legacy sync."""

    def __init__(
        self,
        memory_dir: str | Path = "memory",
        journal_path: str | Path | None = None,
        legacy_path: str | Path = "estado_do_mundo.json",
        campaign_locais: dict[str, Any] | None = None,
        agent: str = "archivista",
        session_id: str | None = None,
        memory_mode: str | None = None,
    ) -> None:
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        if journal_path is None:
            journal_path = self.memory_dir / "turn_journal.jsonl"
        self.journal_path = Path(journal_path)
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.journal_path.exists():
            self.journal_path.touch()

        self.legacy_path = Path(legacy_path)
        self.campaign_locais = campaign_locais or {}
        self.agent = agent
        self.session_id = session_id or _utc_now_iso()
        self.memory_mode = (memory_mode or os.environ.get("MEMORY_MODE", "legacy")).strip()
        self.dual_write_min_sessions = int(
            os.environ.get("MEMORY_DUAL_WRITE_MIN_SESSIONS", "20")
        )
        self._startup_gc_tmp_files()

    def plan(self, writes: list[WriteIntent], agent: str | None = None) -> JournalEntry:
        turn = self._next_turn()
        entry = JournalEntry(
            turn=turn,
            session_id=self.session_id,
            agent=agent or self.agent,
            status="planned",
            planned_at=_utc_now_iso(),
            writes=[
                {"file": w.file, "status": "pending", "bytes": 0}
                for w in writes
            ],
        )
        entry._runtime = {
            "intents": [WriteIntent(w.file, w.content, list(w.required_fields)) for w in writes],
            "tmp_paths": [],
            "replaced_files": {},
        }
        self._append_journal_record(self._serialize_entry(entry))
        return entry

    def execute(self, entry: JournalEntry) -> CommitResult:
        entry.status = "writing"
        self._append_journal_record(self._serialize_entry(entry))

        violations: list[InvariantViolation] = []
        try:
            intents = entry._runtime.get("intents", [])
            if not intents:
                raise ValueError("JournalEntry sem intents de escrita")

            # 1) Write each topic file into tmp
            for idx, intent in enumerate(intents):
                final_path = self._resolve_memory_path(intent.file)
                tmp_path = self._tmp_path_for(final_path)
                final_path.parent.mkdir(parents=True, exist_ok=True)
                tmp_path.write_text(intent.content, encoding="utf-8")

                entry._runtime["tmp_paths"].append(tmp_path)
                write_ref = entry.writes[idx]
                write_ref["status"] = "writing"
                write_ref["bytes"] = len(intent.content.encode("utf-8"))
                write_ref["_final_path"] = str(final_path)
                write_ref["_tmp_path"] = str(tmp_path)

            # 2) Validate each tmp
            for idx, intent in enumerate(intents):
                tmp_path = Path(entry.writes[idx]["_tmp_path"])
                self._validate_tmp_file(tmp_path, intent.required_fields)
                entry.writes[idx]["status"] = "validated"

            # 3) Validate invariants in projected state
            projected_state = entry.projected_state or entry.legacy_state or {}
            violations = self.validate_invariants(projected_state)
            entry.invariants_checked = list(
                getattr(self, "_last_invariants_checked", INVARIANTS_CHECKED)
            )
            if violations:
                entry.invariants_failed = [v.code for v in violations]
                raise ValueError(
                    "Invariant violation(s): " + ", ".join(entry.invariants_failed)
                )

            # 4) Rename tmp -> final atomically
            for idx, _intent in enumerate(intents):
                final_path = Path(entry.writes[idx]["_final_path"])
                tmp_path = Path(entry.writes[idx]["_tmp_path"])
                self._snapshot_before_replace(entry, final_path)
                tmp_path.replace(final_path)
                entry.writes[idx]["status"] = "committed"
                entry.writes[idx]["bytes"] = final_path.stat().st_size

            # 5) Update MEMORY.md (index) when provided
            if entry.index_content is not None:
                index_path = self.memory_dir / "MEMORY.md"
                self._snapshot_before_replace(entry, index_path)
                self._atomic_write_text(index_path, entry.index_content)

            # 6) Sync legacy snapshot while legacy compatibility is active
            if self._should_sync_legacy(entry):
                self._snapshot_before_replace(entry, self.legacy_path)
                self._atomic_write_text(
                    self.legacy_path,
                    json.dumps(entry.legacy_state, indent=2, ensure_ascii=False),
                )

            # 7) Write committed line in journal
            entry.status = "committed"
            entry.committed_at = _utc_now_iso()
            self._append_journal_record(self._serialize_entry(entry))
            return CommitResult(success=True, status="committed", entry=entry)

        except Exception as exc:
            entry.status = "aborted"
            entry.error = str(exc)
            entry.rollback_applied = self.rollback(entry)
            entry.committed_at = _utc_now_iso()
            self._append_journal_record(self._serialize_entry(entry))
            return CommitResult(
                success=False,
                status="aborted",
                entry=entry,
                violations=violations,
            )

    def rollback(self, entry: JournalEntry) -> bool:
        applied = False

        # Remove temporary files
        for tmp_path in entry._runtime.get("tmp_paths", []):
            p = Path(tmp_path)
            if p.exists():
                p.unlink()
                applied = True

        # Restore replaced files
        replaced = entry._runtime.get("replaced_files", {})
        for path_str, old_bytes in replaced.items():
            path = Path(path_str)
            if old_bytes is None:
                if path.exists():
                    path.unlink()
                    applied = True
            else:
                self._atomic_write_bytes(path, old_bytes)
                applied = True

        return applied

    def validate_invariants(self, state_snapshot: dict[str, Any]) -> list[InvariantViolation]:
        checked, violations = validate_state_invariants(
            state_snapshot,
            self.campaign_locais,
            self.memory_dir,
        )
        self._last_invariants_checked = checked
        return violations

    def create_npc_topic_if_missing(
        self,
        npc_id: str,
        signature: dict[str, Any],
        world_state: dict[str, Any],
    ) -> bool:
        """
        Cria `memory/npcs/{npc_id}.md` via WAL se o arquivo não existir.
        Retorna True se criou, False se já existia.
        """
        if not npc_id or not str(npc_id).strip():
            return False

        normalized_id = str(npc_id).strip()
        npc_path = self.memory_dir / "npcs" / f"{normalized_id}.md"
        if npc_path.exists():
            return False

        content = self._format_npc_topic_content(normalized_id, signature)
        entry = self.plan(
            [WriteIntent(file=str(npc_path), content=content, required_fields=["id:", "criado_em:"])],
            agent="npc_builder",
        )
        state_copy = dict(world_state) if isinstance(world_state, dict) else {}
        pending = list(state_copy.get("__pending_npc_topic_files", []))
        pending.append(normalized_id)
        state_copy["__pending_npc_topic_files"] = pending
        entry.projected_state = state_copy
        entry.legacy_state = world_state if isinstance(world_state, dict) else None

        result = self.execute(entry)
        return bool(result.success)

    def check_combat_consistency(self, state: dict[str, Any]) -> InvariantViolation | None:
        return check_combat_consistency(state)

    def check_resurrection_consistency(self, state: dict[str, Any]) -> InvariantViolation | None:
        return check_resurrection_consistency(state)

    def check_location_exists(self, state: dict[str, Any]) -> InvariantViolation | None:
        return check_location_exists(state, self.campaign_locais)

    def check_npc_files_present(
        self, state: dict[str, Any]
    ) -> list[InvariantViolation] | None:
        return check_npc_files_present(state, self.memory_dir)

    def get_last_valid_journal_entry(self) -> dict[str, Any] | None:
        if not self.journal_path.exists():
            return None
        last_valid: dict[str, Any] | None = None
        with self.journal_path.open("r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    last_valid = parsed
        return last_valid

    def _startup_gc_tmp_files(self) -> None:
        tmp_candidates = sorted(self.memory_dir.rglob(".tmp_*"))
        if not tmp_candidates:
            return

        for tmp in tmp_candidates:
            if not tmp.is_file():
                continue
            now = _utc_now_iso()
            writing_record = {
                "turn": self._next_turn(),
                "session_id": self.session_id,
                "agent": "gc_startup",
                "status": "writing",
                "planned_at": now,
                "committed_at": None,
                "writes": [
                    {
                        "file": str(tmp),
                        "status": "writing",
                        "bytes": 0,
                    }
                ],
                "invariants_checked": [],
                "invariants_failed": [],
                "rollback_applied": False,
                "error": None,
                "entry_id": uuid.uuid4().hex,
            }
            self._append_journal_record(writing_record)

            status = "committed"
            error = None
            try:
                tmp.unlink()
            except Exception as exc:
                status = "aborted"
                error = str(exc)

            now = _utc_now_iso()
            record = {
                "turn": self._next_turn(),
                "session_id": self.session_id,
                "agent": "gc_startup",
                "status": status,
                "planned_at": now,
                "committed_at": now,
                "writes": [
                    {
                        "file": str(tmp),
                        "status": status,
                        "bytes": 0,
                    }
                ],
                "invariants_checked": [],
                "invariants_failed": [],
                "rollback_applied": False,
                "error": error,
                "entry_id": uuid.uuid4().hex,
            }
            self._append_journal_record(record)

    def _next_turn(self) -> int:
        last = self.get_last_valid_journal_entry()
        if not last:
            return 1
        try:
            return int(last.get("turn", 0)) + 1
        except (TypeError, ValueError):
            return 1

    def _resolve_memory_path(self, file_path: str) -> Path:
        candidate = Path(file_path)
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            parts = list(candidate.parts)
            if parts and parts[0] == self.memory_dir.name:
                parts = parts[1:]
            resolved = (self.memory_dir / Path(*parts)).resolve()

        memory_root = self.memory_dir.resolve()
        if resolved != memory_root and memory_root not in resolved.parents:
            raise ValueError(f"Caminho fora de memory/: {file_path}")
        return resolved

    def _tmp_path_for(self, final_path: Path) -> Path:
        return final_path.parent / f".tmp_{final_path.name}"

    def _validate_tmp_file(self, tmp_path: Path, required_fields: list[str]) -> None:
        content = tmp_path.read_text(encoding="utf-8")
        if not isinstance(content, str):
            raise ValueError(f"Conteúdo inválido em {tmp_path}")

        for required in required_fields:
            if required not in content:
                raise ValueError(
                    f"Campo obrigatório ausente em {tmp_path.name}: {required}"
                )

        if tmp_path.suffix == ".json":
            json.loads(content)

    def _should_sync_legacy(self, entry: JournalEntry) -> bool:
        if entry.legacy_state is None:
            return False
        return self.memory_mode != "layered"

    def _snapshot_before_replace(self, entry: JournalEntry, path: Path) -> None:
        replaced = entry._runtime.setdefault("replaced_files", {})
        key = str(path.resolve())
        if key in replaced:
            return
        if path.exists():
            replaced[key] = path.read_bytes()
        else:
            replaced[key] = None

    def _format_npc_topic_content(self, npc_id: str, signature: dict[str, Any]) -> str:
        signature = signature if isinstance(signature, dict) else {}
        name = self._line_value(signature.get("nome"), default=npc_id)
        origem = self._line_value(signature.get("origem"), default="improvisado")
        tipo = self._line_value(signature.get("tipo"), default="npc_improvisado")
        moral = self._line_value(signature.get("moral_tonalidade"), default="ambigua")
        archetype = self._line_value(signature.get("arquetipo_social"), default="habitante")
        motivation = self._line_value(signature.get("motivacao_principal"), default="Sobreviver ao dia.")
        voice = self._line_value(signature.get("voz_textual"), default="Tom neutro.")
        created_at = self._line_value(self.session_id, default=_utc_now_iso())

        lines = [
            f"# NPC: {name}",
            f"id: {npc_id}",
            f"origem: {origem}",
            f"tipo: {tipo}",
            f"moral: {moral}",
            f"arquetipo: {archetype}",
            f"motivacao: {motivation}",
            f"voz: {voice}",
            f"criado_em: {created_at}",
            f"ultima_aparicao: {created_at}",
            "relacao_jogador: neutro",
            "segredo: ~",
        ]
        return "\n".join(lines) + "\n"

    def _line_value(self, value: Any, default: str = "") -> str:
        if value is None:
            return default
        text = str(value).strip()
        if not text:
            return default
        return text.replace("\n", " ").replace("\r", " ")

    def _serialize_entry(self, entry: JournalEntry) -> dict[str, Any]:
        serial_writes: list[dict[str, Any]] = []
        for w in entry.writes:
            serial_writes.append(
                {
                    "file": w.get("file"),
                    "status": w.get("status"),
                    "bytes": w.get("bytes", 0),
                }
            )

        invariants_checked = list(entry.invariants_checked or INVARIANTS_CHECKED)

        payload = {
            "turn": entry.turn,
            "session_id": entry.session_id,
            "agent": entry.agent,
            "status": entry.status,
            "planned_at": entry.planned_at,
            "committed_at": entry.committed_at,
            "writes": serial_writes,
            "invariants_checked": invariants_checked,
            "invariants_failed": list(entry.invariants_failed),
            "rollback_applied": entry.rollback_applied,
            "error": entry.error,
            "entry_id": entry.entry_id,
        }
        return payload

    def _append_journal_record(self, record: dict[str, Any]) -> None:
        with self.journal_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False))
            f.write("\n")

    def _atomic_write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.parent / f".tmp_{path.name}"
        tmp_path.write_text(content, encoding="utf-8")
        tmp_path.replace(path)

    def _atomic_write_bytes(self, path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.parent / f".tmp_restore_{path.name}"
        tmp_path.write_bytes(content)
        tmp_path.replace(path)
