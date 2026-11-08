"""Integridade de navegação do locais.json do Curse of Strahd (fonte usada pelo jogo)."""
import json
from pathlib import Path

import pytest

LOCAIS_PATH = Path(__file__).resolve().parent.parent / "campanhas" / "curse_of_strahd" / "locais.json"
DEATH_HOUSE_START = "area_1a_entrada"

# Destinos que não são locais, mas marcadores explícitos.
MARKERS = {"BLOQUEADO_MIMIC"}

# Ligações de mão única intencionais: (origem, destino).
ONE_WAY_EXCEPTIONS = {
    ("area_37_portcullis", "area_38_camara_ritual"),  # portcullis só abre pela roda na 38
    ("area_33_sala_lideres_culto", "BLOQUEADO_MIMIC"),  # a "porta" é o mimic
}

SECRET_STAIRS = "area_21_escada_secreta_espiral"
# Única entrada pelo andar de cima é a porta secreta condicional da 18; a 22 é a saída de baixo.
SECRET_STAIRS_ENTRIES = {"area_18_deposito_restos_baba", "area_22_acesso_dungeon"}


@pytest.fixture(scope="module")
def locais() -> dict:
    return json.loads(LOCAIS_PATH.read_text(encoding="utf-8"))["locais"]


def _edges(locais: dict) -> list[tuple[str, str, str]]:
    return [(src, d, dst) for src, loc in locais.items() for d, dst in loc.get("exits", {}).items()]


def test_every_exit_target_exists(locais):
    bad = [(s, d, t) for s, d, t in _edges(locais) if t not in locais and t not in MARKERS]
    assert not bad, f"saídas para ids inexistentes: {bad}"


def test_every_exit_has_semantic_description(locais):
    bad = [(s, d) for s, d, _ in _edges(locais) if d not in locais[s].get("exits_semanticos", {})]
    assert not bad, f"saídas sem exits_semanticos: {bad}"


def test_every_death_house_room_reachable_from_entrance(locais):
    seen, stack = {DEATH_HOUSE_START}, [DEATH_HOUSE_START]
    while stack:
        for t in locais[stack.pop()].get("exits", {}).values():
            if t in locais and t not in seen:
                seen.add(t)
                stack.append(t)
    unreachable = sorted(k for k in locais if k.startswith("area_") and k not in seen)
    assert not unreachable, f"inalcançáveis: {unreachable}"


def test_every_link_has_way_back(locais):
    missing = [
        (s, t) for s, _, t in _edges(locais)
        if (s, t) not in ONE_WAY_EXCEPTIONS
        and not (t in locais and s in locais[t].get("exits", {}).values())
    ]
    assert not missing, f"sem caminho de volta: {missing}"


def test_every_enemy_has_structured_trigger():
    npcs = json.loads((LOCAIS_PATH.parent / "npcs.json").read_text(encoding="utf-8"))["npcs"]
    enemies = {k: v["combate"] for k, v in npcs.items() if isinstance(v.get("combate"), dict)}
    bad = {
        k: c.get("gatilho") for k, c in enemies.items()
        if not (isinstance(c.get("gatilho"), list) and c["gatilho"]
                and all(isinstance(g, str) and g.replace("_", "").isalnum() and g.islower() for g in c["gatilho"]))
    }
    assert enemies and not bad, f"combate sem gatilho estruturado: {bad}"


def test_death_house_npcs_have_valid_allowed_rooms(locais):
    npcs = json.loads((LOCAIS_PATH.parent / "npcs.json").read_text(encoding="utf-8"))["npcs"]
    # Obrigatório para inimigos da Death House; validado em qualquer NPC que o declare.
    checked = {
        k: v for k, v in npcs.items()
        if "allowed_rooms" in v
        or (isinstance(v.get("combate"), dict) and v.get("home_location", "").startswith("area_"))
    }
    bad = {
        k: v.get("allowed_rooms") for k, v in checked.items()
        if not v.get("allowed_rooms")
        or v["home_location"] not in v["allowed_rooms"]
        or any(r not in locais for r in v["allowed_rooms"])
    }
    assert checked and not bad, f"allowed_rooms inválido: {bad}"


def test_death_house_enemies_have_initial_status():
    npcs = json.loads((LOCAIS_PATH.parent / "npcs.json").read_text(encoding="utf-8"))["npcs"]
    missing = [
        k for k, v in npcs.items()
        if isinstance(v.get("combate"), dict) and v.get("home_location", "").startswith("area_")
        and not v["combate"].get("status_inicial")
    ]
    assert not missing, f"inimigos sem status_inicial: {missing}"


def test_death_house_rooms_have_floor_and_ambient_description(locais):
    floors = {"terreo", "segundo", "terceiro", "sotao", "dungeon"}
    rooms = {k: v for k, v in locais.items() if k.startswith("area_")}
    bad = [
        k for k, v in rooms.items()
        if v.get("andar") not in floors or not v.get("ambient_descricao")
    ]
    assert len(rooms) == 57 and not bad, f"salas sem andar/ambient_descricao: {bad}"


def test_secret_stairs_have_no_shortcuts(locais):
    entries = {s: d for s, d, t in _edges(locais) if t == SECRET_STAIRS}
    assert set(entries) <= SECRET_STAIRS_ENTRIES, f"atalho para a escada secreta: {set(entries) - SECRET_STAIRS_ENTRIES}"
    secret_exit = entries["area_18_deposito_restos_baba"]
    assert secret_exit.startswith("porta_secreta")
    assert "[SECRETO" in locais["area_18_deposito_restos_baba"]["exits_semanticos"][secret_exit]
