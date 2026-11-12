"""Passo 4a: o Arquivista confere a narração; o motor grava fatos e cobra tags esquecidas por 1 turno."""
import json
from unittest.mock import patch

import gm_tags
import party
from world_state_manager import update_world_state


def _state(**extra):
    base = {
        "player_character": {"name": "Aldric", "status": {"hp": 20, "max_hp": 20}, "inventory": []},
        "world_state": {"current_location_key": "area_5"},
        "flags": {}, "facts": [], "turn": 3,
    }
    state = party.ensure_party({**base, **extra})
    mira = {"id": "p2", "nickname": "Mi", "connected": True, "location_key": "area_5",
            "character": {"name": "Mira", "status": {"hp": 10, "max_hp": 10}, "inventory": []}}
    return {**state, "party": {**state["party"], "members": [*state["party"]["members"], mira]}}


def test_review_adds_world_facts_with_entities_turn_and_room():
    review = {"fatos_novos": [{"texto": "Rose confiou no grupo", "entidades": ["Rose"]},
                              {"texto": "rose  CONFIOU no grupo", "entidades": []}]}
    new, _ = gm_tags.apply_review(_state(), review, "area_5")
    assert new["facts"] == [{"text": "Rose confiou no grupo", "location_key": "area_5", "active": True,
                             "entities": ["Rose"], "turn": 3}]


def test_review_undoes_active_facts():
    s = _state(facts=[{"text": "A porta está trancada", "location_key": "area_5", "active": True}])
    new, _ = gm_tags.apply_review(s, {"fatos_desfeitos": ["a porta está TRANCADA"]}, "area_5")
    assert new["facts"][0]["active"] is False


def test_review_turns_untagged_sheet_changes_into_pending():
    review = {"ficha_sem_tag": [{"tipo": "hp", "alvo": "Mira", "descricao": "a lâmina cortou o braço"},
                                {"tipo": "ouro", "alvo": "Mira", "descricao": "tipo inválido"}]}
    new, _ = gm_tags.apply_review(_state(), review, "area_5")
    assert new["pending"] == [{"tipo": "hp", "alvo": "Mira", "descricao": "a lâmina cortou o braço", "turn": 3}]
    assert new["party"] == _state()["party"]  # ficha intocada


def test_review_ignores_garbage_from_the_model():
    for junk in (None, "texto", [], {"fatos_novos": "x", "ficha_sem_tag": [1, "a"], "fatos_desfeitos": {}}):
        new, leaks = gm_tags.apply_review(_state(), junk, "area_5")
        assert new["facts"] == [] and new["pending"] == [] and leaks == []


def test_review_reports_npc_secret_leaks():
    _, leaks = gm_tags.apply_review(_state(), {"segredos_revelados": [{"npc": "Rose", "segredo": "está morta"}]}, "area_5")
    assert leaks == [{"npc": "Rose", "segredo": "está morta"}]


def test_pending_goes_to_gm_prompt_for_one_turn_then_is_settled():
    s = _state(pending=[{"tipo": "hp", "alvo": "Mi", "descricao": "corte no braço", "turn": 3},
                        {"tipo": "item", "alvo": "Aldric", "descricao": "pegou a vela", "turn": 3}])
    assert "corte no braço" in gm_tags.build_pending_block(s)

    import game
    _, after = game.clean_and_process_ai_response("A dor arde. [HP:Mira=-3]", s)
    assert after["pending"] == []
    ignored = gm_tags.pop_transient(after)["pending_ignored"]
    assert [p["alvo"] for p in ignored] == ["Aldric"]  # o HP da Mira (apelido Mi) foi resolvido
    assert gm_tags.build_pending_block(after) == ""


def test_each_gm_response_advances_the_turn_and_tag_facts_carry_it():
    import game
    _, after = game.clean_and_process_ai_response("[FATO:a vela apagou]", _state())
    assert after["turn"] == 4 and after["facts"][0]["turn"] == 4


def test_archivist_sees_facts_and_group_and_engine_applies_its_review():
    s = _state(facts=[{"text": "A porta está trancada", "location_key": "area_5", "active": True}])
    sent = {}

    def fake_archivist(system, user):
        sent["system"], sent["user"] = system, user
        out = party.without_engine_keys(s)
        out["conferencia"] = {"fatos_novos": [{"texto": "A cortina queimou", "entidades": []}],
                              "fatos_desfeitos": ["A porta está trancada"],
                              "ficha_sem_tag": [{"tipo": "cond", "alvo": "Mira", "descricao": "ficou envenenada"}],
                              "segredos_revelados": [{"npc": "Rose", "segredo": "está morta"}]}
        return json.dumps(out)

    with patch("world_state_manager.get_openai_response_archivista", side_effect=fake_archivist):
        new = update_world_state(s, "olho", "fogo")
    assert "A porta está trancada" in sent["user"] and "Mira" in sent["user"]
    assert "conferencia" in sent["system"]
    assert "conferencia" not in new
    assert [f["text"] for f in new["facts"] if f["active"]] == ["A cortina queimou"]
    assert new["pending"][0]["alvo"] == "Mira"
    assert gm_tags.pop_transient(new)["secret_leaks"] == [{"npc": "Rose", "segredo": "está morta"}]


# --- auditoria do 4a ---

def test_pending_is_dropped_when_engine_already_applied_that_change_this_turn():
    """Dano já aplicado (tag antiga ou nova) não pode ser cobrado de novo: evitaria dano em dobro."""
    import game
    _, s = game.clean_and_process_ai_response('A garra rasga. [STATUS_UPDATE] {"hp_change": -4}', _state())
    events = gm_tags.pop_transient(s)["sheet_events"]
    review = {"ficha_sem_tag": [{"tipo": "hp", "alvo": "Aldric", "descricao": "garra causou dano"},
                                {"tipo": "cond", "alvo": "Aldric", "descricao": "ficou sangrando"}]}
    new, _ = gm_tags.apply_review(s, review, "area_5", events)
    assert [p["tipo"] for p in new["pending"]] == ["cond"]


def test_archivist_is_told_what_was_applied_and_review_is_filtered_end_to_end():
    s = _state()
    events = [{"type": "hp", "target": "Mira", "before": 10, "after": 6}]
    sent = {}

    def fake_archivist(system, user):
        sent["system"], sent["user"] = system, user
        return json.dumps({**party.without_engine_keys(s),
                           "conferencia": {"ficha_sem_tag": [{"tipo": "hp", "alvo": "Mi", "descricao": "corte"}]}})

    with patch("world_state_manager.get_openai_response_archivista", side_effect=fake_archivist):
        new = update_world_state(s, "ataco", "golpe", events)
    assert "STATUS_UPDATE" in sent["system"]          # tags antigas também contam como tag
    assert '"after": 6' in sent["user"]               # o Arquivista vê o que o motor já aplicou
    assert new["pending"] == []                       # apelido "Mi" = Mira, já aplicado


def test_review_from_the_model_is_capped_in_size_and_count():
    big = "x" * 5000
    review = {"fatos_novos": [{"texto": f"{big} {i}", "entidades": [big] * 50} for i in range(40)],
              "ficha_sem_tag": [{"tipo": "hp", "alvo": big, "descricao": big}] * 30,
              "segredos_revelados": [{"npc": big, "segredo": big}] * 30}
    new, leaks = gm_tags.apply_review(_state(), review, "area_5")
    assert len(new["facts"]) <= gm_tags.MAX_REVIEW_ITEMS and len(new["pending"]) <= gm_tags.MAX_REVIEW_ITEMS
    assert len(leaks) <= gm_tags.MAX_REVIEW_ITEMS
    assert len(gm_tags.build_pending_block(new)) < 3000 and len(gm_tags.build_world_memory_block(new)) < 3000
    assert len(json.dumps(leaks)) < 3000


def test_undone_fact_only_affects_the_room_where_it_happened():
    s = _state(facts=[{"text": "A porta está trancada", "location_key": "area_1", "active": True},
                      {"text": "A porta está trancada", "location_key": "area_5", "active": True}])
    new, _ = gm_tags.apply_review(s, {"fatos_desfeitos": ["A porta está trancada"]}, "area_5")
    assert {f["location_key"]: f["active"] for f in new["facts"]} == {"area_1": True, "area_5": False}


def test_archivist_reply_that_is_not_a_json_object_keeps_previous_state():
    s = _state()
    for reply in ("[1]", '"oi"', "42", "null"):
        with patch("world_state_manager.get_openai_response_archivista", return_value=reply):
            assert update_world_state(s, "olho", "nada") == s
