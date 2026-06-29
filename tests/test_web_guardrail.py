"""Guardrail anti-impossível no caminho WEB (/api/action)."""
from unittest.mock import patch

import pytest


def _client_and_session():
    from fastapi.testclient import TestClient
    import web_api

    sid = "test-guardrail"
    web_api.sessions[sid] = {
        "player_character": {
            "name": "Alice", "class": "Bardo", "current_act": 1,
            "status": {"hp": 10, "max_hp": 10},
        },
        "world_state": {"current_location_key": "taverna"},
    }
    return TestClient(web_api.app), web_api, sid


def test_impossible_action_blocked_before_gm():
    client, web_api, sid = _client_and_session()
    with patch.object(web_api, "to_audio_response", return_value=None), \
         patch("web_api.get_gm_narrative") as mock_gm:
        r = client.post("/api/action", json={"session_id": sid, "action": "paro o tempo"})
    assert r.status_code == 200
    data = r.json()
    assert data["valid"] is False
    assert "não pode" in data["narrative"].lower()
    mock_gm.assert_not_called()   # bloqueou antes de gastar o GM


def test_normal_action_reaches_gm():
    client, web_api, sid = _client_and_session()
    with patch.object(web_api, "to_audio_response", return_value=None), \
         patch.object(web_api, "build_audio_payload", return_value=(None, None)), \
         patch("web_api.get_gm_narrative", return_value="Você abre a porta.") as mock_gm, \
         patch("web_api.update_world_state", side_effect=lambda ws, *a, **k: ws), \
         patch("web_api.clean_and_process_ai_response", side_effect=lambda raw, ws: (raw, ws)):
        r = client.post("/api/action", json={"session_id": sid, "action": "abro a porta"})
    assert r.status_code == 200
    assert r.json().get("valid") is True
    mock_gm.assert_called_once()   # ação válida chega ao GM


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
