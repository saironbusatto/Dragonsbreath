"""Independent invariant validator for layered memory state transitions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


INVARIANTS_CHECKED = [
    "combat_consistency",
    "hp_resurrection",
    "location_exists",
    "npc_file_present",
]


@dataclass
class InvariantViolation:
    code: str
    details: Any = None


def check_combat_consistency(state: dict[str, Any]) -> InvariantViolation | None:
    combat = state.get("world_state", {}).get("combat_state", {})
    if not isinstance(combat, dict):
        return None
    if not combat.get("active") and combat.get("initiative_order"):
        return InvariantViolation("combat_ghost_initiative", combat)
    return None


def check_resurrection_consistency(state: dict[str, Any]) -> InvariantViolation | None:
    resurrection_state = state.get("resurrection_state", {})
    stage = resurrection_state.get("stage") if isinstance(resurrection_state, dict) else None
    if not stage:
        return None

    player = state.get("player_character", {})
    hp = player.get("hp_current")
    if hp is None and isinstance(player.get("status"), dict):
        hp = player["status"].get("hp")
    if hp is None:
        hp = 1

    if hp > 0:
        return InvariantViolation("resurrection_with_living_player", {"stage": stage, "hp": hp})
    return None


def check_location_exists(
    state: dict[str, Any],
    campaign_locais: dict[str, Any] | None = None,
) -> InvariantViolation | None:
    if not campaign_locais:
        return None
    loc = state.get("world_state", {}).get("current_location_key")
    if loc and loc not in campaign_locais:
        return InvariantViolation("ghost_location", loc)
    return None


def check_npc_files_present(
    state: dict[str, Any],
    memory_dir: str | Path,
) -> list[InvariantViolation] | None:
    sigs = state.get("world_state", {}).get("scene_npc_signatures", {})
    if not isinstance(sigs, dict):
        return None

    memory_root = Path(memory_dir)
    npc_dir = memory_root / "npcs"
    pending_topics = {
        str(item).strip()
        for item in state.get("__pending_npc_topic_files", [])
        if isinstance(item, str) and item.strip()
    }

    violations: list[InvariantViolation] = []
    for key, value in sigs.items():
        candidate_ids: list[str] = []
        if isinstance(value, dict):
            rid = value.get("referencia_id") or value.get("id")
            if rid:
                candidate_ids.append(str(rid))
        if isinstance(key, str) and key.strip():
            candidate_ids.append(key.strip())

        found = False
        for npc_id in candidate_ids:
            if (npc_dir / f"{npc_id}.md").exists():
                found = True
                break
            if npc_id in pending_topics:
                found = True
                break

        if not found:
            npc_id = candidate_ids[0] if candidate_ids else str(key)
            violations.append(InvariantViolation("npc_missing_topic_file", npc_id))

    return violations or None


def validate_state_invariants(
    state: dict[str, Any],
    campaign_locais: dict[str, Any] | None,
    memory_dir: str | Path,
) -> tuple[list[str], list[InvariantViolation]]:
    violations: list[InvariantViolation] = []

    checks = [
        check_combat_consistency(state),
        check_resurrection_consistency(state),
        check_location_exists(state, campaign_locais),
        check_npc_files_present(state, memory_dir),
    ]

    for result in checks:
        if result is None:
            continue
        if isinstance(result, list):
            violations.extend(result)
        else:
            violations.append(result)

    return list(INVARIANTS_CHECKED), violations

