"""Session-end helpers for lightweight KAIROS reentry artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def generate_session_reentry(
    world_state: dict[str, Any],
    output_path: str | Path = "memory/session_reentry.md",
) -> Path:
    """Generate a concise session reentry summary at game close."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    pc = world_state.get("player_character", {}) if isinstance(world_state, dict) else {}
    ws = world_state.get("world_state", {}) if isinstance(world_state, dict) else {}
    status = pc.get("status", {}) if isinstance(pc, dict) else {}
    hp = pc.get("hp_current", status.get("hp", "?"))
    hp_max = pc.get("hp_max", status.get("max_hp", "?"))
    mood = world_state.get("narration_mood", "normal") if isinstance(world_state, dict) else "normal"
    location = ws.get("current_location_key", "desconhecido")
    quests = ws.get("active_quests", {})
    recent = ws.get("recent_events_summary", [])
    scene_npcs = ws.get("scene_npc_signatures", {})
    scene_npc_ids = []
    if isinstance(scene_npcs, dict):
        for key, value in scene_npcs.items():
            if isinstance(value, dict):
                rid = value.get("referencia_id") or value.get("id") or key
                if isinstance(rid, str) and rid.strip():
                    scene_npc_ids.append(rid.strip())

    lines = [
        "# Session Reentry",
        f"generated_at: {_utc_now_iso()}",
        "",
        "## Snapshot",
        f"- player: {pc.get('name', 'desconhecido')}",
        f"- class: {pc.get('class', 'Aventureiro')}",
        f"- hp: {hp}/{hp_max}",
        f"- location: {location}",
        f"- mood: {mood}",
        f"- combat_active: {'true' if bool(ws.get('combat_state', {}).get('active')) else 'false'}",
        "",
        "## Active Quests",
    ]

    if isinstance(quests, dict) and quests:
        for key, value in quests.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Scene NPCs",
            ", ".join(scene_npc_ids) if scene_npc_ids else "none",
            "",
            "## Recent Events",
        ]
    )

    if isinstance(recent, list) and recent:
        for item in recent[-5:]:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output

