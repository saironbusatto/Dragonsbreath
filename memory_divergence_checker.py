"""Dual-write divergence checker for layered memory migration."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


@dataclass
class Divergence:
    field: str
    topic_value: Any
    legacy_value: Any
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DivergenceReport:
    clean: bool
    divergences: list[Divergence]
    checked_fields: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "clean": self.clean,
            "checked_fields": list(self.checked_fields),
            "divergences": [d.to_dict() for d in self.divergences],
        }


def check_divergence(memory_dir: Path, legacy_state: dict) -> DivergenceReport:
    memory_dir = Path(memory_dir)
    divergences: list[Divergence] = []
    checked_fields = [
        "hp_current",
        "current_location_key",
        "combat_active",
        "narration_mood",
        "scene_npc_topic_files",
    ]

    topic_hp = _extract_scalar(memory_dir / "player.md", "hp_current")
    legacy_hp = _legacy_hp(legacy_state)
    if _normalize(topic_hp) != _normalize(legacy_hp):
        divergences.append(
            Divergence(
                field="hp_current",
                topic_value=topic_hp,
                legacy_value=legacy_hp,
                message="HP divergente entre player.md e estado legado.",
            )
        )

    topic_loc = _extract_scalar(memory_dir / "MEMORY.md", "current_location_key")
    legacy_loc = legacy_state.get("world_state", {}).get("current_location_key")
    if _normalize(topic_loc) != _normalize(legacy_loc):
        divergences.append(
            Divergence(
                field="current_location_key",
                topic_value=topic_loc,
                legacy_value=legacy_loc,
                message="Local atual divergente entre MEMORY.md e legado.",
            )
        )

    topic_combat = _to_bool(_extract_scalar(memory_dir / "combat.md", "combat_active"))
    legacy_combat = bool(
        legacy_state.get("world_state", {}).get("combat_state", {}).get("active")
    )
    if topic_combat is None or topic_combat != legacy_combat:
        divergences.append(
            Divergence(
                field="combat_active",
                topic_value=topic_combat,
                legacy_value=legacy_combat,
                message="Estado de combate divergente entre combat.md e legado.",
            )
        )

    topic_mood = _extract_scalar(memory_dir / "mood.md", "narration_mood")
    legacy_mood = legacy_state.get("narration_mood", "normal")
    if _normalize(topic_mood) != _normalize(legacy_mood):
        divergences.append(
            Divergence(
                field="narration_mood",
                topic_value=topic_mood,
                legacy_value=legacy_mood,
                message="Mood divergente entre mood.md e legado.",
            )
        )

    scene_sigs = legacy_state.get("world_state", {}).get("scene_npc_signatures", {})
    expected_ids = _extract_scene_npc_ids(scene_sigs)
    npc_dir = memory_dir / "npcs"
    topic_ids = {
        p.stem
        for p in npc_dir.glob("*.md")
        if p.is_file()
    }
    missing_ids = sorted(expected_ids - topic_ids)
    extra_ids = sorted(topic_ids - expected_ids)
    if missing_ids or extra_ids:
        divergences.append(
            Divergence(
                field="scene_npc_topic_files",
                topic_value={"missing": missing_ids, "extra": extra_ids},
                legacy_value=sorted(expected_ids),
                message="Divergência entre NPCs da cena e arquivos em memory/npcs/.",
            )
        )

    return DivergenceReport(
        clean=(len(divergences) == 0),
        divergences=divergences,
        checked_fields=checked_fields,
    )


def update_dual_write_status(
    baseline_path: Path,
    report: DivergenceReport,
    min_sessions: int | None = None,
) -> dict[str, Any]:
    baseline_path = Path(baseline_path)
    baseline = _load_json(baseline_path, default={})
    minimum = int(min_sessions or os.environ.get("MEMORY_DUAL_WRITE_MIN_SESSIONS", "20"))

    baseline["memory_mode"] = baseline.get("memory_mode", "dual_write")
    baseline["dual_write_min_sessions"] = minimum
    clean_sessions = int(baseline.get("dual_write_clean_sessions", 0))

    if report.clean:
        clean_sessions += 1
        baseline["dual_write_clean_sessions"] = clean_sessions
        baseline["last_divergence_at"] = None
    else:
        baseline["dual_write_clean_sessions"] = 0
        baseline["last_divergence_at"] = _utc_now_iso()
        baseline["last_divergence_fields"] = [d.field for d in report.divergences]
        clean_sessions = 0

    threshold_reached = clean_sessions >= minimum and baseline.get("last_divergence_at") is None
    baseline["dual_write_threshold_reached"] = threshold_reached
    baseline["promotion_recommended"] = threshold_reached
    baseline["promotion_requires_manual_confirmation"] = True
    baseline["last_divergence_report"] = report.to_dict()
    baseline["last_checked_at"] = _utc_now_iso()

    baseline_path.write_text(
        json.dumps(baseline, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return baseline


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _extract_scalar(path: Path, key: str) -> str | None:
    if not path.exists():
        return None
    prefix = f"{key}:"
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.lower().startswith(prefix.lower()):
            return line.split(":", 1)[1].strip()
    return None


def _legacy_hp(state: dict[str, Any]) -> int | None:
    player = state.get("player_character", {})
    hp = player.get("hp_current")
    if hp is None and isinstance(player.get("status"), dict):
        hp = player["status"].get("hp")
    if hp is None:
        return None
    try:
        return int(hp)
    except (TypeError, ValueError):
        return None


def _to_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    token = value.strip().lower()
    if token in ("true", "1", "yes", "sim"):
        return True
    if token in ("false", "0", "no", "nao", "não"):
        return False
    return None


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _extract_scene_npc_ids(scene_sigs: Any) -> set[str]:
    if not isinstance(scene_sigs, dict):
        return set()
    npc_ids: set[str] = set()
    for scene_name, payload in scene_sigs.items():
        if isinstance(payload, dict):
            rid = payload.get("referencia_id") or payload.get("id")
            if isinstance(rid, str) and rid.strip():
                npc_ids.add(rid.strip())
                continue
        if isinstance(scene_name, str) and scene_name.strip():
            npc_ids.add(scene_name.strip())
    return npc_ids

