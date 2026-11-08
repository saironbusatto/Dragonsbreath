"""Integridade de navegação do mapa da Death House (Curse of Strahd)."""
import json
from pathlib import Path

import pytest

MAP_PATH = Path(__file__).resolve().parent.parent / "campanhas" / "curse_of_strahd" / "death_house_map.json"
START = "area_1a_entrada"

# Destinos que não são salas, mas marcadores explícitos.
MARKERS = {"BLOQUEADO_MIMIC"}

# Ligações de mão única intencionais: (origem, destino).
ONE_WAY_EXCEPTIONS = {
    ("area_37_portcullis", "area_38_camara_ritual"),  # portcullis só abre pela roda na 38
    ("area_33_sala_lideres_culto", "BLOQUEADO_MIMIC"),  # a "porta" é o mimic
}

# Salas condicionais e as únicas salas que podem levar a elas (sem atalhos que pulem o segredo).
CONDITIONAL_ENTRIES = {
    "area_21_escada_secreta_espiral": {"area_18_deposito_restos_baba", "area_22_acesso_dungeon"},
}


@pytest.fixture(scope="module")
def rooms():
    return json.loads(MAP_PATH.read_text(encoding="utf-8"))["rooms"]


def _edges(rooms):
    return [(rid, d, t) for rid, r in rooms.items() for d, t in r["saidas"].items()]


def test_room_keys_match_ids(rooms):
    assert all(rid == r["id"] for rid, r in rooms.items())


def test_every_exit_target_exists(rooms):
    bad = [(s, d, t) for s, d, t in _edges(rooms) if t not in rooms and t not in MARKERS]
    assert not bad, f"saídas para ids inexistentes: {bad}"


def test_every_room_reachable_from_entrance(rooms):
    seen, stack = {START}, [START]
    while stack:
        for t in rooms[stack.pop()]["saidas"].values():
            if t in rooms and t not in seen:
                seen.add(t)
                stack.append(t)
    assert set(rooms) - seen == set(), f"inalcançáveis: {sorted(set(rooms) - seen)}"


def test_every_link_has_way_back(rooms):
    missing = [
        (s, t) for s, _, t in _edges(rooms)
        if (s, t) not in ONE_WAY_EXCEPTIONS
        and not (t in rooms and s in rooms[t]["saidas"].values())
    ]
    assert not missing, f"sem caminho de volta: {missing}"


def test_conditional_rooms_have_no_shortcuts(rooms):
    for target, allowed in CONDITIONAL_ENTRIES.items():
        assert rooms[target].get("condicao_existencia"), f"{target} perdeu a condição"
        sources = {s for s, _, t in _edges(rooms) if t == target}
        assert sources <= allowed, f"atalho para {target}: {sources - allowed}"
