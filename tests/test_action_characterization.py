"""Caracterização de /api/action: a resposta e o estado salvo não podem mudar na refatoração.

O snapshot foi gravado com o código anterior à extração de run_turn().
Para regravar de propósito: UPDATE_ACTION_SNAPSHOT=1 pytest tests/test_action_characterization.py
"""
import copy
import json
import os
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest

# Fora de tests/golden/: lá o test_golden_turns espera só arquivos no formato de turno dele.
SNAPSHOT = Path(__file__).resolve().parent / "snapshots" / "action_responses.json"

BASE_STATE = {
    "campaign_id": "lamento_do_bardo",
    "game_mode": "rpg",
    "player_character": {
        "name": "Aldric", "class": "Bardo", "current_act": 1,
        "status": {"hp": 20, "max_hp": 20}, "max_slots": 10,
        "inventory": ["Alaúde de Madeira", "Adaga de Ferro"],
        "death_count": 0, "resurrection_flaws": [], "alignment": "neutro",
    },
    "world_state": {
        "current_location_key": "umbraton",
        "immediate_scene_description": "Portões de Umbraton.",
        "interactable_elements_in_scene": {
            "objetos": ["portão"], "npcs": [], "npc_itens": {},
            "containers": {}, "saidas": ["norte"], "chao": [],
        },
        "gatilhos_ativos": {}, "gatilhos_usados": {},
    },
    "recent_narrations": ["Você chega aos portões."],
}

ROLL = {"modifier": "normal", "dice": "1d20", "roll": 15, "dc": 12,
        "success": True, "critical": False, "fumble": False}

CASES = {
    "normal": {"action": "abro o portão"},
    "with_roll": {"action": "escalo o muro", "roll": ROLL},
    "inspection": {"action": "olho ao redor"},
    "invalid": {"action": "paro o tempo"},
    "resurrection": {"action": "ofereço meu alaúde", "awaiting_offering": True},
}


def _archivist(ws, action, gm):
    new = copy.deepcopy(ws)
    new["world_state"]["immediate_scene_description"] = f"Após: {action[:20]}"
    return new


def _run_case(name: str) -> dict:
    from fastapi.testclient import TestClient
    import web_api

    case = CASES[name]
    state = copy.deepcopy(BASE_STATE)
    if case.get("awaiting_offering"):
        state["resurrection_state"] = {"stage": "awaiting_offering"}
    sid = f"char-{name}"
    web_api.sessions[sid] = state
    web_api.session_user[sid] = "user-123"

    patches = [
        patch.object(web_api, "get_gm_narrative", return_value="O portão range. O que você faz? [MOOD:tense]"),
        patch.object(web_api, "clean_and_process_ai_response",
                     side_effect=lambda raw, ws: (raw.replace(" [MOOD:tense]", ""), {**ws, "narration_mood": "tense"})),
        patch.object(web_api, "update_world_state", side_effect=_archivist),
        patch.object(web_api, "build_audio_payload", side_effect=lambda text, *a, **k: (f"AUDIO<{text[:12]}>", None)),
        patch.object(web_api, "to_audio_response", side_effect=lambda text, *a, **k: f"AUDIO<{text[:12]}>"),
        patch.object(web_api, "_select_trigger", return_value=("um corvo grasna", "corvo.mp3")),
        patch.object(web_api, "resolve_action_roll", return_value=case.get("roll")),
        patch.object(web_api, "detect_sfx_list", return_value=[{"url": "porta.mp3", "position": 0.2}]),
        patch.object(web_api, "_get_ambient_for_act", return_value="ambiente.mp3"),
        patch.object(web_api, "_get_dice_sfx", return_value="dado.mp3"),
        patch.object(web_api, "_get_critical_sfx", return_value="critico.mp3"),
        patch.object(web_api, "_get_fumble_sfx", return_value="fumble.mp3"),
        patch.object(web_api, "get_player_eyes_response", return_value="Você vê o portão e névoa."),
        patch.object(web_api, "resolve_resurrection_offering",
                     return_value={"narrative": "A oferenda é aceita.", "ok": True, "mood": "sad",
                                   "roll": None, "result_type": "accepted"}),
        patch.object(web_api, "load_game_context_for_act", return_value={"locais": {}}),
        patch.object(web_api, "upsert_save"),
    ]
    with ExitStack() as stack:
        mocks = [stack.enter_context(p) for p in patches]
        r = TestClient(web_api.app).post("/api/action", json={"session_id": sid, "action": case["action"]})
        upsert = mocks[-1]
        autosave = upsert.call_args.kwargs if upsert.called else None

    assert r.status_code == 200, r.text
    saved = web_api.sessions.pop(sid)
    web_api.session_user.pop(sid, None)
    if autosave:
        autosave = {k: v for k, v in autosave.items() if k != "world_state"}
    return {"response": r.json(), "session_state": saved, "autosave": autosave}


def _all_cases() -> dict:
    return {name: json.loads(json.dumps(_run_case(name), ensure_ascii=False)) for name in CASES}


@pytest.mark.parametrize("name", list(CASES))
def test_action_response_matches_snapshot(name):
    if os.environ.get("UPDATE_ACTION_SNAPSHOT") == "1":
        SNAPSHOT.write_text(json.dumps(_all_cases(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    expected = json.loads(SNAPSHOT.read_text(encoding="utf-8"))[name]
    assert json.loads(json.dumps(_run_case(name), ensure_ascii=False)) == expected
