"""One-time bootstrap from legacy save to layered memory topics."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
from typing import Any

from memory_invariants import validate_state_invariants
from memory_writer import MemoryWriter, WriteIntent


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


@dataclass
class BootstrapResult:
    status: str
    session_id: str
    message: str
    created_files: list[str]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def bootstrap_memory(
    state_path: Path | str = "estado_do_mundo.json",
    memory_dir: Path | str = "memory",
    baseline_path: Path | str = "memory_migration_baseline.json",
    config_path: Path | str = "config.json",
    campaign_locais_override: dict[str, Any] | None = None,
) -> BootstrapResult:
    state_path = Path(state_path)
    memory_dir = Path(memory_dir)
    baseline_path = Path(baseline_path)
    config_path = Path(config_path)
    session_id = _utc_now_iso()

    if memory_dir.exists():
        return BootstrapResult(
            status="already_bootstrapped",
            session_id=session_id,
            message="memory/ já existe; bootstrap não será executado.",
            created_files=[],
        )

    if not state_path.exists():
        return BootstrapResult(
            status="aborted",
            session_id=session_id,
            message="estado_do_mundo.json não encontrado.",
            created_files=[],
            error="legacy_state_missing",
        )

    legacy_state = json.loads(state_path.read_text(encoding="utf-8"))
    campaign_locais = campaign_locais_override or _load_campaign_locais(config_path)

    staged_topics, index_content, pending_npc_ids = _build_topics_from_legacy(
        legacy_state=legacy_state,
        session_id=session_id,
        config_path=config_path,
    )

    created_files = sorted(staged_topics.keys()) + ["memory/MEMORY.md"]
    intents = [
        WriteIntent(file=path, content=content)
        for path, content in staged_topics.items()
    ]
    projected_state = dict(legacy_state)
    if pending_npc_ids:
        projected_state["__pending_npc_topic_files"] = sorted(pending_npc_ids)

    # Guard rail: explicit pre-check to fail fast before writes are committed.
    checked, violations = validate_state_invariants(
        projected_state,
        campaign_locais=campaign_locais,
        memory_dir=memory_dir,
    )
    if violations:
        violation_codes = [v.code for v in violations]
        result = BootstrapResult(
            status="aborted",
            session_id=session_id,
            message="Bootstrap abortado por violação de invariante.",
            created_files=[],
            error=", ".join(violation_codes),
        )
        _log_bootstrap_failure(
            session_id,
            result.error or "invariant_failure",
            baseline_path.parent / "memory_bootstrap.log",
        )
        return result

    writer = MemoryWriter(
        memory_dir=memory_dir,
        legacy_path=state_path,
        campaign_locais=campaign_locais,
        session_id=session_id,
        memory_mode="dual_write",
    )
    entry = writer.plan(intents, agent="bootstrap")
    entry.projected_state = projected_state
    entry.index_content = index_content
    entry.legacy_state = legacy_state
    entry.invariants_checked = checked

    commit_result = writer.execute(entry)
    if not commit_result.success:
        _cleanup_failed_bootstrap(memory_dir)
        _log_bootstrap_failure(
            session_id,
            commit_result.entry.error or "bootstrap_commit_failed",
            baseline_path.parent / "memory_bootstrap.log",
        )
        return BootstrapResult(
            status="aborted",
            session_id=session_id,
            message="Bootstrap abortado durante commit WAL.",
            created_files=[],
            error=commit_result.entry.error,
        )

    _update_baseline_after_bootstrap(
        baseline_path=baseline_path,
        session_id=session_id,
    )
    return BootstrapResult(
        status="bootstrapped",
        session_id=session_id,
        message="Bootstrap de memória concluído com sucesso.",
        created_files=created_files,
    )


def _build_topics_from_legacy(
    legacy_state: dict[str, Any],
    session_id: str,
    config_path: Path,
) -> tuple[dict[str, str], str, set[str]]:
    ws = legacy_state.get("world_state", {})
    pc = legacy_state.get("player_character", {})
    status = pc.get("status", {}) if isinstance(pc, dict) else {}

    hp_current = pc.get("hp_current", status.get("hp", 0))
    hp_max = pc.get("hp_max", status.get("max_hp", 0))
    inventory = pc.get("inventory", []) if isinstance(pc, dict) else []
    active_quests = ws.get("active_quests", {})
    combat_state = ws.get("combat_state", {})
    combat_active = bool(ws.get("combat_active", combat_state.get("active", False)))
    mood = legacy_state.get("narration_mood", "normal")
    resurrection_state = legacy_state.get("resurrection_state", {})
    location_key = ws.get("current_location_key", "desconhecido")

    scene_sigs = ws.get("scene_npc_signatures", {})
    registry_sigs = ws.get("npc_signatures", {})
    npc_map = _collect_npc_signature_map(scene_sigs, registry_sigs)

    topics: dict[str, str] = {}
    topics["memory/player.md"] = (
        "# Player\n"
        f"name: {pc.get('name', 'desconhecido')}\n"
        f"class: {pc.get('class', 'Aventureiro')}\n"
        f"hp_current: {hp_current}\n"
        f"hp_max: {hp_max}\n"
        f"inventory_count: {len(inventory)}\n"
        "inventory_json:\n"
        f"{json.dumps(inventory, ensure_ascii=False, indent=2)}\n"
    )

    topics["memory/location.md"] = (
        "# Location\n"
        f"current_location_key: {location_key}\n"
        "scene_json:\n"
        f"{json.dumps(ws.get('interactable_elements_in_scene', {}), ensure_ascii=False, indent=2)}\n"
        "scene_npc_signatures_json:\n"
        f"{json.dumps(scene_sigs, ensure_ascii=False, indent=2)}\n"
    )

    topics["memory/quests.md"] = (
        "# Quests\n"
        "active_quests_json:\n"
        f"{json.dumps(active_quests, ensure_ascii=False, indent=2)}\n"
    )

    topics["memory/mood.md"] = (
        "# Mood\n"
        f"narration_mood: {mood}\n"
    )

    topics["memory/combat.md"] = (
        "# Combat\n"
        f"combat_active: {'true' if combat_active else 'false'}\n"
        "combat_state_json:\n"
        f"{json.dumps(combat_state, ensure_ascii=False, indent=2)}\n"
    )

    topics["memory/resurrection.md"] = (
        "# Resurrection\n"
        "resurrection_state_json:\n"
        f"{json.dumps(resurrection_state, ensure_ascii=False, indent=2)}\n"
    )

    scene_npc_ids = sorted(
        {
            npc_id
            for npc_id in _extract_scene_npc_ids(scene_sigs)
            if npc_id
        }
    )
    topics["memory/scene/current_npcs.md"] = (
        "# Scene NPCs\n"
        "scene_npc_ids_json:\n"
        f"{json.dumps(scene_npc_ids, ensure_ascii=False, indent=2)}\n"
    )

    for npc_id, signature in npc_map.items():
        topics[f"memory/npcs/{npc_id}.md"] = _format_npc_topic(npc_id, signature, session_id)

    campaign_path = _load_campaign_markdown_path(config_path)
    index_content = _build_memory_index(
        location_key=location_key,
        mood=mood,
        combat_active=combat_active,
        campaign_path=campaign_path,
    )
    return topics, index_content, set(npc_map.keys())


def _build_memory_index(
    location_key: str,
    mood: str,
    combat_active: bool,
    campaign_path: str,
) -> str:
    return (
        "player: memory/player.md\n"
        "location: memory/location.md\n"
        "quests: memory/quests.md\n"
        "mood: memory/mood.md\n"
        "combat: memory/combat.md\n"
        "resurrection: memory/resurrection.md\n"
        "scene_npcs: memory/scene/current_npcs.md\n"
        f"campaign: {campaign_path}\n\n"
        "facts:\n"
        f"- current_location_key: {location_key}\n"
        f"- narration_mood: {mood}\n"
        f"- combat_active: {'true' if combat_active else 'false'}\n"
    )


def _load_campaign_markdown_path(config_path: Path) -> str:
    cfg = _load_json(config_path, default={})
    current = cfg.get("current_campaign")
    campaigns = cfg.get("campaigns", {})
    files = campaigns.get(current, {}).get("files", {}) if isinstance(campaigns, dict) else {}
    return files.get("campanha", "")


def _load_campaign_locais(config_path: Path) -> dict[str, Any]:
    cfg = _load_json(config_path, default={})
    current = cfg.get("current_campaign")
    campaigns = cfg.get("campaigns", {})
    files = campaigns.get(current, {}).get("files", {}) if isinstance(campaigns, dict) else {}
    locais_path = files.get("locais")
    if not locais_path:
        return {}

    raw = _load_json(Path(locais_path), default={})
    locais = raw.get("locais", {})
    return locais if isinstance(locais, dict) else {}


def _collect_npc_signature_map(scene_sigs: Any, registry_sigs: Any) -> dict[str, dict[str, Any]]:
    collected: dict[str, dict[str, Any]] = {}

    if isinstance(registry_sigs, dict):
        for npc_id, signature in registry_sigs.items():
            if isinstance(npc_id, str) and npc_id.strip() and isinstance(signature, dict):
                collected[npc_id.strip()] = dict(signature)

    if isinstance(scene_sigs, dict):
        for scene_name, signature in scene_sigs.items():
            npc_id = None
            if isinstance(signature, dict):
                rid = signature.get("referencia_id") or signature.get("id")
                if isinstance(rid, str) and rid.strip():
                    npc_id = rid.strip()
            if not npc_id and isinstance(scene_name, str) and scene_name.strip():
                npc_id = scene_name.strip()
            if not npc_id:
                continue
            payload = dict(signature) if isinstance(signature, dict) else {"nome": scene_name}
            if "nome" not in payload and isinstance(scene_name, str):
                payload["nome"] = scene_name
            collected[npc_id] = payload

    return collected


def _extract_scene_npc_ids(scene_sigs: Any) -> set[str]:
    ids: set[str] = set()
    if not isinstance(scene_sigs, dict):
        return ids
    for scene_name, payload in scene_sigs.items():
        if isinstance(payload, dict):
            rid = payload.get("referencia_id") or payload.get("id")
            if isinstance(rid, str) and rid.strip():
                ids.add(rid.strip())
                continue
        if isinstance(scene_name, str) and scene_name.strip():
            ids.add(scene_name.strip())
    return ids


def _format_npc_topic(npc_id: str, signature: dict[str, Any], session_id: str) -> str:
    signature = signature if isinstance(signature, dict) else {}
    name = _line(signature.get("nome"), npc_id)
    origem = _line(signature.get("origem"), "improvisado")
    tipo = _line(signature.get("tipo"), "npc_improvisado")
    moral = _line(signature.get("moral_tonalidade"), "ambigua")
    archetype = _line(signature.get("arquetipo_social"), "habitante")
    motivation = _line(signature.get("motivacao_principal"), "Sobreviver ao dia.")
    voice = _line(signature.get("voz_textual"), "Tom neutro.")

    return (
        f"# NPC: {name}\n"
        f"id: {npc_id}\n"
        f"origem: {origem}\n"
        f"tipo: {tipo}\n"
        f"moral: {moral}\n"
        f"arquetipo: {archetype}\n"
        f"motivacao: {motivation}\n"
        f"voz: {voice}\n"
        f"criado_em: {session_id}\n"
        f"ultima_aparicao: {session_id}\n"
        "relacao_jogador: neutro\n"
        "segredo: ~\n"
    )


def _line(value: Any, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    return text.replace("\n", " ").replace("\r", " ")


def _update_baseline_after_bootstrap(
    baseline_path: Path,
    session_id: str,
) -> None:
    baseline = _load_json(baseline_path, default={})
    baseline["memory_mode"] = "dual_write"
    baseline["bootstrap_at"] = _utc_now_iso()
    baseline["bootstrap_session"] = session_id
    baseline["dual_write_clean_sessions"] = int(baseline.get("dual_write_clean_sessions", 0))
    baseline["dual_write_min_sessions"] = int(
        baseline.get("dual_write_min_sessions", os.environ.get("MEMORY_DUAL_WRITE_MIN_SESSIONS", "20"))
    )
    baseline["last_divergence_at"] = baseline.get("last_divergence_at")
    baseline_path.write_text(
        json.dumps(baseline, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _cleanup_failed_bootstrap(memory_dir: Path) -> None:
    if memory_dir.exists():
        shutil.rmtree(memory_dir)


def _log_bootstrap_failure(session_id: str, error: str, log_path: Path) -> None:
    line = f"{_utc_now_iso()} | session={session_id} | status=aborted | error={error}\n"
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line)


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default
