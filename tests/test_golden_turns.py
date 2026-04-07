import json
from pathlib import Path

import pytest

from memory_invariants import validate_state_invariants
from memory_loader import MemoryLoader
from memory_writer import MemoryWriter, WriteIntent


GOLDEN_DIR = Path(__file__).parent / "golden"


def _build_topic_intents_from_world_state(world_state: dict) -> tuple[list[WriteIntent], str]:
    ws = world_state.get("world_state", {})
    pc = world_state.get("player_character", {})
    status = pc.get("status", {}) if isinstance(pc, dict) else {}
    hp_current = pc.get("hp_current", status.get("hp", 0))
    hp_max = pc.get("hp_max", status.get("max_hp", 0))

    intents = [
        WriteIntent(
            file="memory/player.md",
            content=(
                "# Player\n"
                f"name: {pc.get('name', 'desconhecido')}\n"
                f"class: {pc.get('class', 'Aventureiro')}\n"
                f"hp_current: {hp_current}\n"
                f"hp_max: {hp_max}\n"
            ),
            required_fields=["hp_current:"],
        ),
        WriteIntent(
            file="memory/location.md",
            content=(
                "# Location\n"
                f"current_location_key: {ws.get('current_location_key', 'desconhecido')}\n"
                "scene_npc_signatures_json:\n"
                f"{json.dumps(ws.get('scene_npc_signatures', {}), ensure_ascii=False, indent=2)}\n"
            ),
            required_fields=["current_location_key:"],
        ),
        WriteIntent(
            file="memory/mood.md",
            content=f"narration_mood: {world_state.get('narration_mood', 'normal')}\n",
            required_fields=["narration_mood:"],
        ),
        WriteIntent(
            file="memory/combat.md",
            content=(
                f"combat_active: {'true' if bool(ws.get('combat_active')) else 'false'}\n"
                "combat_state_json:\n"
                f"{json.dumps(ws.get('combat_state', {}), ensure_ascii=False, indent=2)}\n"
            ),
        ),
        WriteIntent(
            file="memory/resurrection.md",
            content=(
                "resurrection_state_json:\n"
                f"{json.dumps(world_state.get('resurrection_state', {}), ensure_ascii=False, indent=2)}\n"
            ),
        ),
        WriteIntent(
            file="memory/scene/current_npcs.md",
            content=(
                "scene_npc_ids_json:\n"
                f"{json.dumps(sorted(_scene_npc_ids(ws.get('scene_npc_signatures', {}))), ensure_ascii=False, indent=2)}\n"
            ),
        ),
    ]
    index = (
        "player: memory/player.md\n"
        "location: memory/location.md\n"
        "mood: memory/mood.md\n"
        "combat: memory/combat.md\n"
        "resurrection: memory/resurrection.md\n"
        "scene_npcs: memory/scene/current_npcs.md\n\n"
        "facts:\n"
        f"- current_location_key: {ws.get('current_location_key', 'desconhecido')}\n"
        f"- narration_mood: {world_state.get('narration_mood', 'normal')}\n"
        f"- combat_active: {'true' if bool(ws.get('combat_active')) else 'false'}\n"
    )
    return intents, index


def _scene_npc_ids(scene_sigs) -> set[str]:
    ids = set()
    if not isinstance(scene_sigs, dict):
        return ids
    for key, value in scene_sigs.items():
        if isinstance(value, dict):
            rid = value.get("referencia_id") or value.get("id")
            if isinstance(rid, str) and rid.strip():
                ids.add(rid.strip())
                continue
        if isinstance(key, str) and key.strip():
            ids.add(key.strip())
    return ids


@pytest.mark.parametrize(
    "golden_file",
    sorted(p.name for p in GOLDEN_DIR.glob("*.json")),
)
def test_golden_turn_structural_contract(tmp_path, golden_file):
    payload = json.loads((GOLDEN_DIR / golden_file).read_text(encoding="utf-8"))
    world_state = payload["input"]["world_state"]
    expected = payload["expected"]

    memory_dir = tmp_path / "memory"
    writer = MemoryWriter(
        memory_dir=memory_dir,
        legacy_path=tmp_path / "estado_do_mundo.json",
        campaign_locais={
            "castelo_ravenloft": {},
            "taverna_corvo_ferido": {},
            "cemiterio_antigo": {},
            "umbraton": {},
        },
        memory_mode="dual_write",
        session_id="golden-session",
    )

    # NPC files first (same order enforced in runtime path).
    scene_sigs = world_state.get("world_state", {}).get("scene_npc_signatures", {})
    if isinstance(scene_sigs, dict):
        for scene_name, signature in scene_sigs.items():
            npc_id = None
            if isinstance(signature, dict):
                npc_id = signature.get("referencia_id") or signature.get("id")
            if not npc_id and isinstance(scene_name, str):
                npc_id = scene_name
            if npc_id:
                writer.create_npc_topic_if_missing(str(npc_id), signature if isinstance(signature, dict) else {}, world_state)

    intents, index_content = _build_topic_intents_from_world_state(world_state)
    entry = writer.plan(intents, agent="archivista")
    entry.projected_state = dict(world_state)
    entry.legacy_state = dict(world_state)
    entry.index_content = index_content
    result = writer.execute(entry)
    assert result.status == expected["journal_status"]

    checked, violations = validate_state_invariants(
        state=world_state,
        campaign_locais={
            "castelo_ravenloft": {},
            "taverna_corvo_ferido": {},
            "cemiterio_antigo": {},
            "umbraton": {},
        },
        memory_dir=memory_dir,
    )
    assert checked
    assert (len(violations) == 0) is expected["invariants_pass"]

    loader = MemoryLoader(memory_dir=memory_dir)
    turn_ctx = loader.load_turn_context(world_state)

    for field in expected["turn_context_fields"]:
        assert getattr(turn_ctx, field) is not None

    expected_npcs = set(expected.get("turn_context_npcs_present", []))
    assert expected_npcs.issubset(set(turn_ctx.npcs.keys()))

    if expected["combat_active_after"]:
        assert turn_ctx.combat is not None
    else:
        assert turn_ctx.combat is None

    if expected.get("expect_npc_builder"):
        journal_path = memory_dir / "turn_journal.jsonl"
        lines = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert any(row.get("agent") == "npc_builder" and row.get("status") == "committed" for row in lines)

