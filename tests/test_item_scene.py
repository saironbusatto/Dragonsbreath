"""Passo 4b (parte 2): em campanha de catálogo estrito, só entra na ficha o item que está na cena."""
import gm_tags
import item_catalog
import party
from item_catalog import Catalog

ITEMS = {
    "tocha": {"nome": "Tocha", "apelidos": ["tocha velha"], "categoria": "luz", "livre": True},
    "chave_cripta": {"nome": "Chave da cripta", "apelidos": ["chave"], "categoria": "chave"},
    "pocao": {"nome": "Poção de Cura", "apelidos": ["poção"], "categoria": "consumivel"},
    "adaga": {"nome": "Adaga de prata", "categoria": "arma"},
}
LOCAIS = {
    "area_5": {"itens": [{"id": "tocha", "qtd": 1}, {"id": "pocao"},
                         {"id": "adaga", "escondido": {"dificuldade": 15, "local": "sob o tapete", "pista": "x"}}]},
    "area_9": {"itens": [{"id": "adaga"}]},
}
NPCS = {"coveiro": {"nome": "Velho Coveiro", "itens": ["chave_cripta"]}, "strahd": {"nome": "Strahd", "itens": ["adaga"]}}
STRICT = Catalog(items=ITEMS, locais=LOCAIS, npcs=NPCS, strict=True)


def _state():
    base = {"player_character": {"name": "Aldric", "inventory": []},
            "world_state": {"current_location_key": "area_5",
                            "important_npcs_in_scene": {"coveiro": {}},
                            "scene_npc_signatures": {"mendigo": {"nome": "Mendigo", "improvised": True}}}}
    state = party.ensure_party(base)
    mira = {"id": "p2", "nickname": "Mira", "connected": True, "location_key": "area_9",
            "character": {"name": "Mira", "inventory": []}}
    return {**state, "party": {**state["party"], "members": [*state["party"]["members"], mira]}}


def _run(text, state=None, catalog=STRICT):
    state = state or _state()
    _, tags = gm_tags.extract(text)
    return gm_tags.apply(state, tags, scene=item_catalog.scene(state, catalog))


def _mira(state):
    return next(m for m in state["party"]["members"] if m["id"] == "p2")["character"]


def test_loose_catalog_keeps_accepting_any_item():
    new, _, rejected = _run("[ITEM:Aldric+Espada lendária]", catalog=Catalog(items=ITEMS, strict=False))
    assert new["player_character"]["inventory"] == ["Espada lendária"] and rejected == []


def test_item_in_the_room_is_taken_once_with_its_catalog_name():
    new, events, rejected = _run("[ITEM:Aldric+tocha velha] [ITEM:Aldric+Tocha]")
    assert new["player_character"]["inventory"] == ["Tocha"]
    assert events == [{"type": "item_add", "target": "Aldric", "item": "Tocha"}]
    assert rejected[0]["reason"] == "item não está na cena"


def test_item_outside_catalog_or_hidden_is_refused():
    _, _, rejected = _run("[ITEM:Aldric+Espada lendária] [ITEM:Aldric+Adaga de prata]")
    assert [r["reason"] for r in rejected] == ["item fora do catálogo", "item não está na cena"]


def test_each_member_takes_from_the_room_they_are_in():
    new, _, rejected = _run("[ITEM:Mira+Adaga de prata] [ITEM:Mira+Tocha]")
    assert _mira(new)["inventory"] == ["Adaga de prata"]
    assert rejected[0]["reason"] == "item não está na cena"


def test_dropped_item_stays_in_the_room_but_consumable_is_spent():
    new, _, _ = _run("[ITEM:Aldric+Tocha] [ITEM:Aldric+Poção] [ITEM:Aldric-Tocha] [ITEM:Aldric-Poção]")
    assert new["player_character"]["inventory"] == []
    again, _, rejected = _run("[ITEM:Aldric+Tocha] [ITEM:Aldric+Poção]", state=new)
    assert again["player_character"]["inventory"] == ["Tocha"]
    assert rejected[0]["reason"] == "item não está na cena"


def test_npc_in_scene_hands_over_only_what_it_has():
    new, events, rejected = _run("[ITEM:Velho Coveiro>Aldric:chave] [ITEM:coveiro>Aldric:chave] [ITEM:Strahd>Aldric:Adaga de prata]")
    assert new["player_character"]["inventory"] == ["Chave da cripta"]
    assert events == [{"type": "item_add", "target": "Aldric", "item": "Chave da cripta"}]
    assert [r["reason"] for r in rejected] == ["npc não tem o item", "alvo desconhecido"]  # Strahd não está em cena


def test_improvised_npc_only_gives_free_items():
    new, _, rejected = _run("[ITEM:Mendigo>Aldric:Tocha] [ITEM:Mendigo>Aldric:chave]")
    assert new["player_character"]["inventory"] == ["Tocha"]
    assert rejected[0]["reason"] == "npc não tem o item"


def test_member_can_give_an_item_to_an_npc_who_can_give_it_back():
    new, _, rejected = _run("[ITEM:Aldric+Tocha] [ITEM:Aldric>Mendigo:Tocha] [ITEM:Mendigo>Aldric:Tocha]")
    assert rejected == [] and new["player_character"]["inventory"] == ["Tocha"]


def test_game_turn_uses_the_campaign_catalog(monkeypatch):
    import game
    monkeypatch.setattr(item_catalog, "load", lambda: STRICT)
    _, after = game.clean_and_process_ai_response("Você acha! [ITEM:Aldric+Espada lendária] [ITEM:Aldric+Tocha]", _state())
    assert after["player_character"]["inventory"] == ["Tocha"]
    assert gm_tags.pop_transient(after)["tags_rejected"][0]["reason"] == "item fora do catálogo"
