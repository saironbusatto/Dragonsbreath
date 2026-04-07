from pathlib import Path

from memory_loader import MemoryLoader


def _seed_core_files(memory_dir: Path) -> None:
    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / "MEMORY.md").write_text("index\n", encoding="utf-8")
    (memory_dir / "player.md").write_text("player\n", encoding="utf-8")
    (memory_dir / "location.md").write_text("location\n", encoding="utf-8")
    (memory_dir / "mood.md").write_text("mood\n", encoding="utf-8")


def test_turn_without_combat_returns_combat_none(tmp_path):
    memory_dir = tmp_path / "memory"
    _seed_core_files(memory_dir)
    loader = MemoryLoader(memory_dir=memory_dir)

    world_state = {"world_state": {"combat_state": {"active": False}}}
    turn_ctx = loader.load_turn_context(world_state)

    assert turn_ctx.combat is None


def test_turn_with_combat_active_loads_combat_md(tmp_path):
    memory_dir = tmp_path / "memory"
    _seed_core_files(memory_dir)
    (memory_dir / "combat.md").write_text("combat: active\n", encoding="utf-8")
    loader = MemoryLoader(memory_dir=memory_dir)

    world_state = {"world_state": {"combat_active": True}}
    turn_ctx = loader.load_turn_context(world_state)

    assert turn_ctx.combat == "combat: active\n"
    assert str((memory_dir / "combat.md").as_posix()) in turn_ctx.loaded_files


def test_turn_with_resurrection_stage_loads_resurrection_md(tmp_path):
    memory_dir = tmp_path / "memory"
    _seed_core_files(memory_dir)
    (memory_dir / "resurrection.md").write_text("stage: awaiting_offering\n", encoding="utf-8")
    loader = MemoryLoader(memory_dir=memory_dir)

    world_state = {"resurrection_state": {"stage": "awaiting_offering"}, "world_state": {}}
    turn_ctx = loader.load_turn_context(world_state)

    assert turn_ctx.resurrection == "stage: awaiting_offering\n"
    assert str((memory_dir / "resurrection.md").as_posix()) in turn_ctx.loaded_files


def test_scene_npc_without_topic_file_is_omitted(tmp_path):
    memory_dir = tmp_path / "memory"
    _seed_core_files(memory_dir)
    (memory_dir / "npcs").mkdir(parents=True, exist_ok=True)
    loader = MemoryLoader(memory_dir=memory_dir)

    world_state = {
        "world_state": {
            "scene_npc_signatures": {
                "figura encapuzada": {"referencia_id": "improvisado_figura_encapuzada"}
            }
        }
    }
    turn_ctx = loader.load_turn_context(world_state)

    assert turn_ctx.npcs == {}


def test_token_estimate_is_positive_and_proportional(tmp_path):
    memory_dir = tmp_path / "memory"
    _seed_core_files(memory_dir)
    loader = MemoryLoader(memory_dir=memory_dir)

    small_state = {"world_state": {}}
    small_ctx = loader.load_turn_context(small_state)

    (memory_dir / "player.md").write_text("player\n" + ("lorem " * 400), encoding="utf-8")
    big_ctx = loader.load_turn_context(small_state)

    assert small_ctx.token_estimate > 0
    assert big_ctx.token_estimate > small_ctx.token_estimate

