"""
Testes para database.py — persistência SQLite de saves.
Usa banco em memória (:memory:) para isolamento total.
"""
import json
import os
import pytest

os.environ.setdefault("DB_PATH", ":memory:")

import database


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    """Banco em arquivo temporário isolado por teste."""
    db_file = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_file)
    monkeypatch.setattr(database, "DB_PATH", db_file)
    database.init_db()
    yield


# ── init_db ───────────────────────────────────────────────────────────────────

def test_init_db_creates_saves_table():
    with database.get_db() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='saves'"
        ).fetchall()
    assert len(rows) == 1


def test_init_db_idempotent():
    """Chamar init_db duas vezes não levanta erro."""
    database.init_db()
    database.init_db()


# ── upsert_save / list_saves / get_save ──────────────────────────────────────

def test_upsert_creates_new_save():
    save_id = database.upsert_save(
        clerk_user_id="user_1",
        character_name="Aldric",
        character_class="Guerreiro",
        campaign_id="lamento_do_bardo",
        world_state={"hp": 10},
    )
    assert isinstance(save_id, int)
    assert save_id > 0


def test_upsert_updates_existing_save():
    id1 = database.upsert_save("user_1", "Aldric", "Guerreiro", "camp_1", {"hp": 10})
    id2 = database.upsert_save("user_1", "Aldric", "Guerreiro", "camp_1", {"hp": 8})
    assert id1 == id2  # mesmo slot


def test_upsert_updates_world_state():
    database.upsert_save("user_1", "Aldric", "Guerreiro", "camp_1", {"hp": 10})
    database.upsert_save("user_1", "Aldric", "Guerreiro", "camp_1", {"hp": 5})
    save = database.get_save(1, "user_1")
    ws = json.loads(save["world_state"])
    assert ws["hp"] == 5


def test_upsert_different_campaigns_create_separate_saves():
    id1 = database.upsert_save("user_1", "Aldric", "Guerreiro", "camp_1", {})
    id2 = database.upsert_save("user_1", "Aldric", "Guerreiro", "camp_2", {})
    assert id1 != id2


def test_list_saves_returns_user_saves():
    database.upsert_save("user_1", "Aldric", "Guerreiro", "camp_1", {})
    database.upsert_save("user_1", "Mira", "Ladina", "camp_2", {})
    database.upsert_save("user_2", "Outro", "Mago", "camp_1", {})
    saves = database.list_saves("user_1")
    assert len(saves) == 2
    names = {s["character_name"] for s in saves}
    assert names == {"Aldric", "Mira"}


def test_list_saves_empty_for_unknown_user():
    saves = database.list_saves("user_nao_existe")
    assert saves == []


def test_get_save_returns_correct_row():
    save_id = database.upsert_save("user_1", "Aldric", "Guerreiro", "camp_1", {"hp": 10})
    save = database.get_save(save_id, "user_1")
    assert save is not None
    assert save["character_name"] == "Aldric"
    assert save["character_class"] == "Guerreiro"
    assert save["campaign_id"] == "camp_1"


def test_get_save_returns_none_for_wrong_user():
    save_id = database.upsert_save("user_1", "Aldric", "Guerreiro", "camp_1", {})
    save = database.get_save(save_id, "user_2")
    assert save is None


def test_get_save_returns_none_for_missing_id():
    save = database.get_save(9999, "user_1")
    assert save is None


# ── delete_save ───────────────────────────────────────────────────────────────

def test_delete_save_removes_row():
    save_id = database.upsert_save("user_1", "Aldric", "Guerreiro", "camp_1", {})
    result = database.delete_save(save_id, "user_1")
    assert result is True
    assert database.get_save(save_id, "user_1") is None


def test_delete_save_returns_false_for_wrong_user():
    save_id = database.upsert_save("user_1", "Aldric", "Guerreiro", "camp_1", {})
    result = database.delete_save(save_id, "user_2")
    assert result is False
    assert database.get_save(save_id, "user_1") is not None


def test_delete_save_returns_false_for_missing_id():
    result = database.delete_save(9999, "user_1")
    assert result is False


# ── isolamento entre usuários ─────────────────────────────────────────────────

def test_user_cannot_access_other_user_save():
    id1 = database.upsert_save("user_1", "Aldric", "Guerreiro", "camp_1", {"secret": True})
    assert database.get_save(id1, "user_2") is None


def test_list_saves_ordered_by_updated_at_desc():
    database.upsert_save("user_1", "Aldric", "Guerreiro", "camp_1", {})
    database.upsert_save("user_1", "Mira", "Ladina", "camp_2", {})
    # Atualiza o primeiro save para ser o mais recente
    database.upsert_save("user_1", "Aldric", "Guerreiro", "camp_1", {"hp": 99})
    saves = database.list_saves("user_1")
    assert saves[0]["character_name"] == "Aldric"
