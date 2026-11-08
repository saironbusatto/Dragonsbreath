"""Campanha por sessão: a web não troca mais a campanha global (config.json)."""
import concurrent.futures
import json
from pathlib import Path
from unittest.mock import patch

import pytest

import campaign_manager

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
GLOBAL_ID = CONFIG["current_campaign"]
OTHER_ID = next(cid for cid in CONFIG["campaigns"] if cid != GLOBAL_ID)


def _name(cid: str) -> str:
    return CONFIG["campaigns"][cid]["name"]


# ─── campaign_manager ────────────────────────────────────────────────────────

def test_scope_overrides_global_campaign_and_resets():
    assert campaign_manager.get_current_campaign()["name"] == _name(GLOBAL_ID)
    with campaign_manager.campaign_scope(OTHER_ID):
        assert campaign_manager.get_current_campaign()["name"] == _name(OTHER_ID)
    assert campaign_manager.get_current_campaign()["name"] == _name(GLOBAL_ID)


def test_scope_is_isolated_per_thread():
    def read_in_scope(cid):
        with campaign_manager.campaign_scope(cid):
            return campaign_manager.get_current_campaign()["name"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        names = list(pool.map(read_in_scope, [GLOBAL_ID, OTHER_ID] * 3))
    assert names == [_name(GLOBAL_ID), _name(OTHER_ID)] * 3


def test_submit_in_context_propagates_scope_to_pool_threads():
    with campaign_manager.campaign_scope(OTHER_ID):
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            name = campaign_manager.submit_in_context(
                pool, lambda: campaign_manager.get_current_campaign()["name"]
            ).result()
    assert name == _name(OTHER_ID)


def test_campaign_exists():
    assert campaign_manager.campaign_exists(OTHER_ID)
    assert not campaign_manager.campaign_exists("campanha_que_nao_existe")


# ─── web_api ─────────────────────────────────────────────────────────────────

def _web_mocks(web_api, seen: list):
    """Mocka as APIs externas; grava a campanha ativa vista pelo GM e pelo Arquivista."""
    def gm(*a, **k):
        seen.append(("gm", campaign_manager.get_current_campaign()["name"]))
        return "Você segue em frente. O que você faz?"

    def archivist(ws, *a, **k):
        seen.append(("arquivista", campaign_manager.get_current_campaign()["name"]))
        return ws

    return [
        patch.object(web_api, "get_gm_narrative", side_effect=gm),
        patch.object(web_api, "update_world_state", side_effect=archivist),
        patch.object(web_api, "clean_and_process_ai_response", side_effect=lambda raw, ws: (raw, ws)),
        patch.object(web_api, "build_audio_payload", return_value=(None, None)),
        patch.object(web_api, "to_audio_response", return_value=None),
        patch.object(web_api, "_get_ambient_for_act", return_value=None),
        patch.object(web_api, "_get_intro_music", return_value=None),
        patch.object(web_api, "detect_sfx_list", return_value=[]),
        patch.object(web_api, "_select_trigger", return_value=(None, None)),
        patch.object(web_api, "resolve_action_roll", return_value=None),
    ]


@pytest.fixture
def web():
    from contextlib import ExitStack
    from fastapi.testclient import TestClient
    import web_api

    seen: list = []
    config_path = ROOT / "config.json"
    original = config_path.read_bytes()
    try:
        with ExitStack() as stack:
            for p in _web_mocks(web_api, seen):
                stack.enter_context(p)
            yield TestClient(web_api.app), web_api, seen
    finally:
        # Mesmo se o código regredir e voltar a gravar a campanha global, o teste não deixa sujeira.
        if config_path.read_bytes() != original:
            config_path.write_bytes(original)


def test_start_rejects_unknown_campaign(web):
    client, _, _ = web
    r = client.post("/api/start", json={"player_name": "Ana", "campaign_id": "nao_existe"})
    assert r.status_code == 400


def test_start_does_not_touch_global_config(web):
    client, web_api, seen = web
    before = (ROOT / "config.json").read_bytes()
    with patch.object(campaign_manager, "switch_campaign") as switch:
        r = client.post("/api/start", json={"player_name": "Ana", "campaign_id": OTHER_ID})
    assert r.status_code == 200
    switch.assert_not_called()
    assert (ROOT / "config.json").read_bytes() == before
    assert web_api.sessions[r.json()["session_id"]]["campaign_id"] == OTHER_ID
    assert ("gm", _name(OTHER_ID)) in seen and ("arquivista", _name(OTHER_ID)) in seen


def test_actions_use_each_sessions_own_campaign(web):
    client, _, seen = web
    sid_a = client.post("/api/start", json={"player_name": "Ana", "campaign_id": GLOBAL_ID}).json()["session_id"]
    sid_b = client.post("/api/start", json={"player_name": "Bia", "campaign_id": OTHER_ID}).json()["session_id"]
    seen.clear()

    for sid in (sid_b, sid_a, sid_b):
        r = client.post("/api/action", json={"session_id": sid, "action": "sigo em frente"})
        assert r.status_code == 200

    expected = [_name(OTHER_ID), _name(GLOBAL_ID), _name(OTHER_ID)]
    assert [name for who, name in seen if who == "gm"] == expected
    assert [name for who, name in seen if who == "arquivista"] == expected  # roda em thread do pool
