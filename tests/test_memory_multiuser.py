"""Isolamento de memória por save — garante que jogadores não misturam memória no web."""
import json
from pathlib import Path

import pytest

import game


def _ws_with_npc(name: str, npc_id: str) -> dict:
    return {
        "player_character": {"name": name, "class": "Bardo"},
        "world_state": {
            "current_location_key": "taverna",
            "scene_npc_signatures": {
                npc_id: {"referencia_id": npc_id, "nome": npc_id, "improvised": True},
            },
        },
        "narration_mood": "normal",
    }


def test_namespace_is_stable_and_persisted():
    ws = {"player_character": {}, "world_state": {}}
    ns1 = game._memory_namespace(ws)
    ns2 = game._memory_namespace(ws)
    assert ns1 == ns2                       # estável na mesma sessão
    assert ws["_memory_namespace"] == ns1   # persistido no world_state (viaja no save)


def test_distinct_saves_get_distinct_dirs():
    a, b = {"world_state": {}}, {"world_state": {}}
    dir_a = game._memory_dir_for(a)
    assert dir_a != game._memory_dir_for(b)
    assert Path(dir_a).is_absolute()                     # absoluto (WAL exige)
    assert Path(dir_a).parent.name == "memory"           # sob a base memory/
    assert Path(dir_a).name == a["_memory_namespace"]    # namespace = subdir


def test_turn_context_does_not_leak_npcs_between_saves(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMORY_MODE", "dual_write")
    monkeypatch.chdir(tmp_path)

    save_a = _ws_with_npc("Alice", "guarda_alfa")
    save_b = _ws_with_npc("Bob", "bruxa_beta")

    game._build_turn_context(save_a, {"locais": {}})
    game._build_turn_context(save_b, {"locais": {}})

    dir_a = Path(game._memory_dir_for(save_a))
    dir_b = Path(game._memory_dir_for(save_b))

    assert dir_a != dir_b
    # O NPC do save A existe só no dir do save A, nunca no do save B
    assert (dir_a / "npcs" / "guarda_alfa.md").exists()
    assert not (dir_b / "npcs" / "guarda_alfa.md").exists()
    assert (dir_b / "npcs" / "bruxa_beta.md").exists()
    assert not (dir_a / "npcs" / "bruxa_beta.md").exists()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
