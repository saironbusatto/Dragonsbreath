"""
Web API — Dragon's Breath / Plataforma Ressoar
Interface de voz: o jogador fala, o Mestre responde em áudio.
"""
import uuid
import os
import base64
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Google Cloud: suporte a credenciais via variável de ambiente (Railway/cloud)
_google_creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
if _google_creds_json:
    import tempfile
    _tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    _tmp.write(_google_creds_json)
    _tmp.close()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _tmp.name

from campaign_manager import list_available_campaigns, switch_campaign
from world_state_manager import create_initial_world_state, update_world_state
from game import (
    get_gm_narrative,
    clean_and_process_ai_response,
    load_game_context_for_act,
    validate_player_action,
)

app = FastAPI(title="Dragon's Breath RPG")

# Sessões em memória: { session_id: world_state }
sessions: dict[str, dict] = {}


# ─── TTS server-side (retorna bytes MP3) ─────────────────────────────────────

def synthesize_speech(text: str, voice_type: str = "master") -> bytes | None:
    """Chama Google Cloud TTS e retorna os bytes MP3, ou None se indisponível."""
    try:
        from google.cloud import texttospeech

        if voice_type == "narrator":
            voice_name = os.getenv("GOOGLE_TTS_VOICE_NARRATOR", "pt-BR-Neural2-A")
            gender = texttospeech.SsmlVoiceGender.FEMALE
        else:
            voice_name = os.getenv("GOOGLE_TTS_VOICE_MASTER", "pt-BR-Neural2-B")
            gender = texttospeech.SsmlVoiceGender.MALE

        client = texttospeech.TextToSpeechClient()
        response = client.synthesize_speech(
            input=texttospeech.SynthesisInput(text=text),
            voice=texttospeech.VoiceSelectionParams(
                language_code="pt-BR",
                name=voice_name,
                ssml_gender=gender,
            ),
            audio_config=texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.4,
                pitch=0.0,
            ),
        )
        return response.audio_content
    except Exception as e:
        print(f"⚠️  TTS error: {e}")
        return None


def to_audio_response(text: str, voice_type: str = "master") -> str | None:
    """Retorna áudio como base64 string, ou None."""
    audio_bytes = synthesize_speech(text, voice_type)
    if audio_bytes:
        return base64.b64encode(audio_bytes).decode("utf-8")
    return None


# ─── Modelos de request ───────────────────────────────────────────────────────

class StartRequest(BaseModel):
    player_name: str
    campaign_id: str

class ActionRequest(BaseModel):
    session_id: str
    action: str


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _state_summary(world_state: dict) -> dict:
    pc = world_state.get("player_character", {})
    ws = world_state.get("world_state", {})
    return {
        "name": pc.get("name", ""),
        "class": pc.get("class", ""),
        "hp": pc.get("status", {}).get("hp", 0),
        "max_hp": pc.get("status", {}).get("max_hp", 0),
        "inventory": pc.get("inventory", []),
        "max_slots": pc.get("max_slots", 10),
        "location": ws.get("current_location_key", ""),
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/api/campaigns")
def get_campaigns():
    return {"campaigns": list_available_campaigns()}


@app.post("/api/start")
def start_game(req: StartRequest):
    if not req.player_name.strip():
        raise HTTPException(400, "Nome não pode ser vazio")

    switch_campaign(req.campaign_id)
    world_state = create_initial_world_state(req.player_name.strip())
    world_state["game_mode"] = "rpg"

    current_act = world_state["player_character"]["current_act"]
    game_context = load_game_context_for_act(current_act, world_state)
    game_context["gatilhos"] = []

    opening_raw = get_gm_narrative(world_state, "Iniciou a aventura", game_context)
    opening_clean, world_state = clean_and_process_ai_response(opening_raw, world_state)
    world_state = update_world_state(world_state, "Iniciou a aventura", opening_raw)

    session_id = str(uuid.uuid4())
    sessions[session_id] = world_state

    audio = to_audio_response(opening_clean, "master")

    return {
        "session_id": session_id,
        "narrative": opening_clean,
        "audio": audio,
        "state": _state_summary(world_state),
    }


@app.post("/api/action")
def take_action(req: ActionRequest):
    world_state = sessions.get(req.session_id)
    if world_state is None:
        raise HTTPException(404, "Sessão não encontrada. Inicie um novo jogo.")

    action = req.action.strip()
    if not action:
        raise HTTPException(400, "Ação não pode ser vazia")

    # Comandos de status por voz
    action_lower = action.lower()
    if any(w in action_lower for w in ("inventário", "inventario", "bolsa", "meus itens")):
        pc = world_state["player_character"]
        inv = pc.get("inventory", [])
        used = len(inv)
        total = pc.get("max_slots", 10)
        narrative = (
            f"Você carrega {used} de {total} itens: {', '.join(inv)}."
            if inv else "Sua bolsa está vazia."
        )
        return {"narrative": narrative, "audio": to_audio_response(narrative), "state": _state_summary(world_state), "valid": True}

    if any(w in action_lower for w in ("status", "saúde", "saude", "vida", "hp", "quanto hp")):
        pc = world_state["player_character"]
        hp = pc.get("status", {}).get("hp", 0)
        max_hp = pc.get("status", {}).get("max_hp", 0)
        narrative = f"Você tem {hp} de {max_hp} pontos de vida."
        return {"narrative": narrative, "audio": to_audio_response(narrative), "state": _state_summary(world_state), "valid": True}

    # Valida ação
    character = world_state.get("player_character", {})
    is_valid, validation_msg = validate_player_action(action, character, world_state)
    if not is_valid:
        return {
            "narrative": validation_msg,
            "audio": to_audio_response(validation_msg),
            "state": _state_summary(world_state),
            "valid": False,
        }

    # Processa ação no motor do jogo
    current_act = character.get("current_act", 1)
    game_context = load_game_context_for_act(current_act, world_state)

    gm_response = get_gm_narrative(world_state, action, game_context)
    cleaned_narrative, world_state = clean_and_process_ai_response(gm_response, world_state)
    world_state = update_world_state(world_state, action, gm_response)

    sessions[req.session_id] = world_state

    audio = to_audio_response(cleaned_narrative, "master")

    return {
        "narrative": cleaned_narrative,
        "audio": audio,
        "state": _state_summary(world_state),
        "valid": True,
    }


@app.get("/api/state/{session_id}")
def get_state(session_id: str):
    world_state = sessions.get(session_id)
    if world_state is None:
        raise HTTPException(404, "Sessão não encontrada")
    return _state_summary(world_state)


# ─── Frontend ─────────────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_index():
    return FileResponse("static/index.html")
