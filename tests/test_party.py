"""Formato de grupo (party.py): conversão de save solo, personagem ativo e chaves do motor."""
import copy
import json
from unittest.mock import patch

import party

SOLO = {
    "player_character": {"name": "Aldric", "class": "Bardo", "status": {"hp": 20, "max_hp": 20}},
    "world_state": {"current_location_key": "umbraton"},
}


def test_legacy_save_becomes_party_of_one():
    state = party.ensure_party(SOLO)
    assert state["party"] == {
        "active_member_id": "p1",
        "members": [{
            "id": "p1", "nickname": "Aldric", "connected": True,
            "location_key": "umbraton", "character": SOLO["player_character"],
        }],
    }
    assert "party" not in SOLO  # não muta a entrada


def test_ensure_party_is_idempotent():
    once = party.ensure_party(SOLO)
    assert party.ensure_party(once) == once


def test_commit_active_writes_sheet_and_location_back():
    state = copy.deepcopy(party.ensure_party(SOLO))
    state["player_character"]["status"]["hp"] = 7
    state["world_state"]["current_location_key"] = "taverna"
    committed = party.commit_active(state)
    (member,) = committed["party"]["members"]
    assert member["character"]["status"]["hp"] == 7
    assert member["location_key"] == "taverna"
    assert state["party"]["members"][0]["character"]["status"]["hp"] == 20  # entrada intacta


def test_activate_loads_member_sheet_into_player_character():
    state = party.ensure_party(SOLO)
    mira = {"id": "p2", "nickname": "Mira", "connected": True, "location_key": "umbraton",
            "character": {"name": "Mira", "class": "Ocultista"}}
    state = {**state, "party": {**state["party"], "members": [*state["party"]["members"], mira]}}
    active = party.activate(state, "p2")
    assert active["player_character"] == mira["character"]
    assert active["party"]["active_member_id"] == "p2"


def test_without_engine_keys_hides_party():
    state = party.ensure_party(SOLO)
    assert "party" not in party.without_engine_keys(state)
    assert "party" in state


def test_archivist_never_sees_nor_drops_party():
    from world_state_manager import update_world_state
    state = party.ensure_party(SOLO)
    sent = {}

    def fake_llm(system, user):
        sent["user"] = user
        return json.dumps({"player_character": SOLO["player_character"],
                           "world_state": {"current_location_key": "umbraton"}})

    with patch("world_state_manager.get_openai_response_archivista", side_effect=fake_llm):
        new = update_world_state(state, "olho", "nada acontece")
    assert '"party"' not in sent["user"]
    assert new["party"] == state["party"]


def test_gm_prompt_hides_party(monkeypatch):
    import game
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    sent = {}

    def fake_call(key, system, user, *a, **k):
        sent["user"] = user
        return "ok"

    with patch.object(game, "_call_gm_api", side_effect=fake_call):
        game.get_gm_narrative(party.ensure_party(SOLO), "olho", {"locais": {}})
    assert '"party"' not in sent["user"]


def test_turn_keeps_party_in_sync_with_sheet():
    from test_action_characterization import _run_case
    saved = _run_case("normal")["session_state"]
    (member,) = saved["party"]["members"]
    assert member["character"] == saved["player_character"]
    assert member["location_key"] == saved["world_state"]["current_location_key"]
