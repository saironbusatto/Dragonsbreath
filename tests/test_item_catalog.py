"""Passo 4b (parte 1): formato do catálogo de itens e validação ao carregar a campanha."""
import json

import pytest

import item_catalog

ITEMS = {
    "tocha": {"nome": "Tocha", "apelidos": ["tocha velha"], "slots": 1, "livre": True, "categoria": "luz",
              "alcance": "perto", "duracao_min": 60, "precisa_fogo": True, "chance_apagar": 20},
    "chave_cripta": {"nome": "Chave da cripta", "slots": 1, "categoria": "chave", "abre": "porta_cripta_aberta"},
    "carta": {"nome": "Carta em latim", "categoria": "narrativo"},
}
FLAGS = {"porta_cripta_aberta"}


def _errors(items=ITEMS, locais=None, npcs=None, extra=None):
    return item_catalog.validate(items, locais or {}, npcs or {}, FLAGS, extra or {})


def test_valid_catalog_has_no_errors():
    locais = {"area_5": {"itens": [{"id": "tocha", "qtd": 2},
                                   {"id": "chave_cripta", "escondido": {"dificuldade": 15, "local": "sob o tapete",
                                                                        "pista": "marcas de arrasto"}}]}}
    assert _errors(locais=locais, npcs={"coveiro": {"itens": ["chave_cripta"]}}) == []


def test_item_needs_known_category_and_its_fields():
    errors = _errors({"vela": {"nome": "Vela", "categoria": "luz", "alcance": "perto"},
                      "coisa": {"nome": "Coisa", "categoria": "inventada"},
                      "sem_nome": {"categoria": "narrativo"}})
    assert any("vela" in e and "duracao_min" in e for e in errors)
    assert any("coisa" in e and "inventada" in e for e in errors)
    assert any("sem_nome" in e and "nome" in e for e in errors)


def test_key_must_open_a_flag_that_exists():
    errors = _errors({"chave": {"nome": "Chave", "categoria": "chave", "abre": "porta_que_nao_existe"}})
    assert any("porta_que_nao_existe" in e for e in errors)


def test_campaign_can_add_its_own_categories():
    relic = {"osso": {"nome": "Osso de santo", "categoria": "reliquia", "poder": "afasta mortos-vivos"}}
    assert _errors(relic, extra={"reliquia": ["poder", "cargas"]}) != []
    assert _errors({"osso": {**relic["osso"], "cargas": 3}}, extra={"reliquia": ["poder", "cargas"]}) == []


def test_rooms_and_npcs_can_only_point_to_catalog_items():
    errors = _errors(locais={"area_1": {"itens": [{"id": "espada_fantasma"},
                                                  {"id": "tocha", "escondido": {"dificuldade": 13, "local": "x"}}]}},
                     npcs={"guarda": {"itens": ["chave_inexistente"]}})
    assert any("area_1" in e and "espada_fantasma" in e for e in errors)
    assert any("area_1" in e and "dificuldade" in e for e in errors)      # só 9, 12, 15 ou 18
    assert any("area_1" in e and "pista" in e for e in errors)
    assert any("guarda" in e and "chave_inexistente" in e for e in errors)


def _campaign(tmp_path, monkeypatch, items, strict):
    paths = {}
    for name, data in (("itens_comuns", {"itens_comuns": items}), ("itens_magicos", {"itens_magicos": {}}),
                       ("locais", {"locais": {}}), ("npcs", {"npcs": {}})):
        paths[name] = str(tmp_path / f"{name}.json")
        (tmp_path / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")
    campaign = {"files": paths, "catalogo_estrito": strict,
                "world_template": {"initial_flags": {"casa": {"porta_cripta_aberta": False}}}}
    monkeypatch.setattr(item_catalog, "get_current_campaign", lambda: campaign)


def test_strict_campaign_with_broken_catalog_refuses_to_load(tmp_path, monkeypatch):
    _campaign(tmp_path, monkeypatch, {"vela": {"nome": "Vela", "categoria": "luz"}}, strict=True)
    with pytest.raises(item_catalog.CatalogError) as err:
        item_catalog.load()
    assert "vela" in str(err.value)


def test_strict_campaign_with_valid_catalog_loads_and_resolves_names(tmp_path, monkeypatch):
    _campaign(tmp_path, monkeypatch, ITEMS, strict=True)
    catalog = item_catalog.load()
    assert catalog.strict is True
    assert catalog.find("TOCHA velha") == "tocha" and catalog.find("chave_cripta") == "chave_cripta"
    assert catalog.find("espada lendária") is None


def test_loose_campaign_loads_even_with_uncategorized_items(tmp_path, monkeypatch):
    _campaign(tmp_path, monkeypatch, {"vela": {"nome": "Vela", "efeito": "ilumina"}}, strict=False)
    assert item_catalog.load().strict is False


def test_shipped_campaigns_load():
    """As campanhas do repositório continuam carregando (as estritas precisam estar válidas)."""
    from campaign_manager import campaign_scope, load_config
    for campaign_id in load_config()["campaigns"]:
        with campaign_scope(campaign_id):
            item_catalog.load()
