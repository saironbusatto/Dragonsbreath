"""Deterministic layered-memory loader for per-turn prompt context."""

from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from pathlib import Path
from typing import Any


@dataclass
class TurnContext:
    index: str
    player: str
    location: str
    combat: str | None
    mood: str | None
    resurrection: str | None
    npcs: dict[str, str]
    token_estimate: int
    loaded_files: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MemoryLoader:
    def __init__(self, memory_dir: str | Path = "memory") -> None:
        self.memory_dir = Path(memory_dir)

    def load_turn_context(self, world_state: dict) -> TurnContext:
        ws = world_state.get("world_state", {}) if isinstance(world_state, dict) else {}
        loaded_files: list[str] = []

        index = self._read("MEMORY.md", loaded_files)
        if index is None:
            index = self._legacy_index(world_state)

        player = self._read("player.md", loaded_files)
        if player is None:
            player = self._legacy_player(world_state)

        location = self._read("location.md", loaded_files)
        if location is None:
            location = self._legacy_location(world_state)

        mood = self._read("mood.md", loaded_files)
        if mood is None:
            mood = self._legacy_mood(world_state)

        combat_active = bool(ws.get("combat_active"))
        if not combat_active:
            combat_active = bool(ws.get("combat_state", {}).get("active"))
        combat = None
        if combat_active:
            combat = self._read("combat.md", loaded_files)
            if combat is None:
                combat = self._legacy_combat(world_state)

        resurrection = None
        resurrection_state = world_state.get("resurrection_state", {}) if isinstance(world_state, dict) else {}
        stage = resurrection_state.get("stage") if isinstance(resurrection_state, dict) else None
        if stage:
            resurrection = self._read("resurrection.md", loaded_files)
            if resurrection is None:
                resurrection = self._legacy_resurrection(world_state)

        npcs: dict[str, str] = {}
        scene_sigs = ws.get("scene_npc_signatures", {})
        if isinstance(scene_sigs, dict):
            for scene_key, signature in scene_sigs.items():
                npc_id = self._resolve_scene_npc_id(scene_key, signature)
                if not npc_id:
                    continue
                content = self._read(f"npcs/{npc_id}.md", loaded_files)
                if content is not None:
                    npcs[npc_id] = content

        total_text = "\n".join(
            [
                index or "",
                player or "",
                location or "",
                mood or "",
                combat or "",
                resurrection or "",
                *npcs.values(),
            ]
        )
        token_estimate = max(0, len(total_text) // 4)

        return TurnContext(
            index=index or "",
            player=player or "",
            location=location or "",
            combat=combat,
            mood=mood,
            resurrection=resurrection,
            npcs=npcs,
            token_estimate=token_estimate,
            loaded_files=loaded_files,
        )

    def _read(self, relative_path: str, loaded_files: list[str]) -> str | None:
        path = self.memory_dir / relative_path
        if not path.exists() or not path.is_file():
            return None
        text = path.read_text(encoding="utf-8")
        loaded_files.append(str(path.as_posix()))
        return text

    def _resolve_scene_npc_id(self, scene_key: str, signature: Any) -> str | None:
        if isinstance(signature, dict):
            rid = signature.get("referencia_id") or signature.get("id")
            if isinstance(rid, str) and rid.strip():
                return rid.strip()
        if isinstance(scene_key, str) and scene_key.strip():
            return scene_key.strip()
        return None

    def _legacy_index(self, world_state: dict) -> str:
        ws = world_state.get("world_state", {}) if isinstance(world_state, dict) else {}
        location = ws.get("current_location_key", "desconhecido")
        mood = world_state.get("narration_mood", "normal") if isinstance(world_state, dict) else "normal"
        return (
            "[LEGACY_FALLBACK]\n"
            "index_source: world_state\n"
            f"current_location_key: {location}\n"
            f"narration_mood: {mood}\n"
        )

    def _legacy_player(self, world_state: dict) -> str:
        payload = world_state.get("player_character", {}) if isinstance(world_state, dict) else {}
        return "[LEGACY_FALLBACK]\n" + json.dumps(payload, ensure_ascii=False, indent=2)

    def _legacy_location(self, world_state: dict) -> str:
        ws = world_state.get("world_state", {}) if isinstance(world_state, dict) else {}
        payload = {
            "current_location_key": ws.get("current_location_key"),
            "immediate_scene_description": ws.get("immediate_scene_description"),
            "interactable_elements_in_scene": ws.get("interactable_elements_in_scene"),
            "scene_npc_signatures": ws.get("scene_npc_signatures"),
        }
        return "[LEGACY_FALLBACK]\n" + json.dumps(payload, ensure_ascii=False, indent=2)

    def _legacy_mood(self, world_state: dict) -> str:
        mood = world_state.get("narration_mood", "normal") if isinstance(world_state, dict) else "normal"
        return f"[LEGACY_FALLBACK]\nmood: {mood}\n"

    def _legacy_combat(self, world_state: dict) -> str:
        payload = (
            world_state.get("world_state", {}).get("combat_state", {})
            if isinstance(world_state, dict)
            else {}
        )
        return "[LEGACY_FALLBACK]\n" + json.dumps(payload, ensure_ascii=False, indent=2)

    def _legacy_resurrection(self, world_state: dict) -> str:
        payload = world_state.get("resurrection_state", {}) if isinstance(world_state, dict) else {}
        return "[LEGACY_FALLBACK]\n" + json.dumps(payload, ensure_ascii=False, indent=2)

