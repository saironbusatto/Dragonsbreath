"""Tags do Mestre (gm_tags.py): leitura, conferência pelo motor e eventos de ficha."""
import copy

import gm_tags
import party


def _state():
    base = {
        "player_character": {"name": "Aldric", "status": {"hp": 20, "max_hp": 20}, "max_slots": 3,
                             "inventory": ["Corda", "Adaga"]},
        "world_state": {"current_location_key": "area_5"},
        "flags": {"death_house": {"portcullis_37_raised": False}},
        "facts": [],
    }
    state = party.ensure_party(base)
    mira = {"id": "p2", "nickname": "Mira", "connected": True, "location_key": "area_5",
            "character": {"name": "Mira", "status": {"hp": 10, "max_hp": 10}, "max_slots": 1, "inventory": []}}
    return {**state, "party": {**state["party"], "members": [*state["party"]["members"], mira]}}


def _run(text, state=None, roll_success=False):
    clean, tags = gm_tags.extract(text)
    new, events, rejected = gm_tags.apply(state or _state(), tags, roll_success=roll_success)
    return clean, new, events, rejected


def _mira(state):
    return next(m for m in state["party"]["members"] if m["id"] == "p2")["character"]


def _with_mira_hp(hp):
    s = copy.deepcopy(_state())
    _mira(s)["status"]["hp"] = hp
    return s


def test_extract_strips_all_engine_tags_from_text():
    clean, tags = gm_tags.extract("A garra rasga. [HP:Aldric=-6] [FATO:a cortina queimou] [MODO:turnos] Fim.")
    assert clean == "A garra rasga. Fim."
    assert [t["kind"] for t in tags] == ["HP", "FATO", "MODO"]


def test_hp_on_active_member_goes_to_player_character_and_is_clamped():
    _, new, events, _ = _run("[HP:aldric=-30]")
    assert new["player_character"]["status"]["hp"] == 0
    assert events == [{"type": "hp", "target": "Aldric", "before": 20, "after": 0}]


def test_hp_on_other_member_goes_to_party_sheet():
    _, new, events, _ = _run("[HP:Mira=+5]", state=_with_mira_hp(4))
    assert _mira(new)["status"]["hp"] == 9
    assert events[0]["target"] == "Mira"


def test_unknown_target_is_rejected_not_applied():
    _, new, events, rejected = _run("[HP:ghoul_2=-8]")
    assert events == [] and rejected[0]["reason"] == "alvo desconhecido"
    assert new == _state()


def test_item_add_respects_slots():
    _, new, events, rejected = _run("[ITEM:Aldric+Tocha] [ITEM:Aldric+Lanterna]")
    assert new["player_character"]["inventory"] == ["Corda", "Adaga", "Tocha"]
    assert len(events) == 1 and rejected[0]["reason"] == "sem espaço"


def test_item_remove_only_what_character_has():
    _, new, events, rejected = _run("[ITEM:Aldric-corda] [ITEM:Aldric-Espada]")
    assert new["player_character"]["inventory"] == ["Adaga"]
    assert rejected[0]["reason"] == "não tem o item"


def test_item_transfer_between_members():
    _, new, events, _ = _run("[ITEM:Aldric>Mira:Adaga]")
    assert new["player_character"]["inventory"] == ["Corda"]
    assert _mira(new)["inventory"] == ["Adaga"]
    assert [e["type"] for e in events] == ["item_remove", "item_add"]


def test_item_transfer_fails_whole_when_receiver_full():
    s = _state()
    _mira(s)["inventory"] = ["Pedra"]
    _, new, events, rejected = _run("[ITEM:Aldric>Mira:Adaga]", state=s)
    assert new["player_character"]["inventory"] == ["Corda", "Adaga"]
    assert events == [] and rejected[0]["reason"] == "sem espaço"


def test_conditions_add_and_remove():
    _, new, _, _ = _run("[COND:Mira+envenenado] [COND:Mira+caído] [COND:Mira-caído] [COND:Mira+envenenado]")
    assert _mira(new)["conditions"] == ["envenenado"]


def test_fact_is_stored_with_room_and_deduplicated():
    _, new, _, rejected = _run("[FATO:A cortina do quarto queimou] [FATO:a  cortina do QUARTO queimou]")
    assert new["facts"] == [{"text": "A cortina do quarto queimou", "location_key": "area_5", "active": True}]
    assert rejected[0]["reason"] == "fato repetido"


def test_flag_needs_existing_flag_and_successful_roll():
    _, no_roll, _, rejected = _run("[FLAG:portcullis_37_raised=true]")
    assert no_roll["flags"]["death_house"]["portcullis_37_raised"] is False
    assert rejected[0]["reason"] == "sem rolagem bem-sucedida"

    _, rolled, events, _ = _run("[FLAG:portcullis_37_raised=true]", roll_success=True)
    assert rolled["flags"]["death_house"]["portcullis_37_raised"] is True
    assert events == [{"type": "flag", "target": "portcullis_37_raised", "before": False, "after": True}]

    _, _, _, rejected = _run("[FLAG:porta_inventada=true]", roll_success=True)
    assert rejected[0]["reason"] == "flag não existe na campanha"


def test_legacy_tags_go_through_the_same_checks():
    clean, new, events, _ = _run('Golpe. [STATUS_UPDATE] {"hp_change": -4} [INVENTORY_UPDATE] {"add": ["Chave"], "remove": ["Corda"]}')
    assert clean == "Golpe."
    assert new["player_character"]["status"]["hp"] == 16
    assert new["player_character"]["inventory"] == ["Adaga", "Chave"]
    assert [e["type"] for e in events] == ["hp", "item_add", "item_remove"]


def test_apply_does_not_mutate_input():
    s = _state()
    before = copy.deepcopy(s)
    _run("[HP:Aldric=-5] [ITEM:Aldric-Corda] [FATO:x]", state=s)
    assert s == before


def test_ensure_flags_seeds_missing_flags_without_overwriting():
    state = {"flags": {"death_house": {"a": True}}}
    seeded = gm_tags.ensure_flags(state, {"death_house": {"a": False, "b": False}, "vallaki": {"c": False}})
    assert seeded["flags"] == {"death_house": {"a": True, "b": False}, "vallaki": {"c": False}}
    assert seeded["facts"] == []


def test_archivist_cannot_change_the_sheet():
    import json
    from unittest.mock import patch
    from world_state_manager import update_world_state
    state = _state()
    hacked = {**state, "player_character": {**state["player_character"], "inventory": ["Item fantasma"]}}
    with patch("world_state_manager.get_openai_response_archivista", return_value=json.dumps(party.without_engine_keys(hacked))):
        new = update_world_state(state, "olho", "nada")
    assert new["player_character"] == state["player_character"]
    assert new["flags"] == state["flags"] and new["facts"] == state["facts"]
