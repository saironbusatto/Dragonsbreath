"""
Web API — Dragon's Breath / Plataforma Ressoar
Interface de voz: o jogador fala, o Mestre responde em áudio.
"""
import uuid
import os
import base64
import requests as http_requests
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

app = FastAPI(title="Ressoar")

# Sessões em memória: { session_id: world_state }
sessions: dict[str, dict] = {}


# ─── SFX: Freesound.org (gratuito) com fallback local ────────────────────────

# Mapeamento: keywords PT → query EN para Freesound
_SFX_MAP = {
    "corvo":      "raven crow caw dark",
    "corvos":     "flock crows cawing",
    "grito":      "scream horror terror",
    "criança":    "children running footsteps",
    "moeda":      "coin gold drop",
    "cidade":     "medieval city ambience",
    "vila":       "medieval village atmosphere",
    "umbraton":   "dark city gothic ambience",
    "pessoas":    "crowd murmur voices",
    "multidão":   "crowd talking indoor",
    "chuva":      "rain ambient outdoor",
    "tempestade": "thunderstorm rain",
    "taverna":    "medieval tavern inn ambience",
    "taverneiro": "tavern indoor ambience",
    "passos":     "footsteps stone floor",
    "vento":      "wind howling",
    "fogo":       "fire crackling fireplace",
    "porta":      "door creak open",
    "sino":       "bell church toll",
    "trovão":     "thunder crack storm",
    "floresta":   "forest ambient birds",
    "masmorra":   "dungeon dark dripping",
    "espada":     "sword clash metal",
    "flecha":     "arrow whoosh",
    "lobo":       "wolf howl",
    "água":       "water stream flowing",
    "mercado":    "market bazaar crowd",
    "cavalo":     "horse hooves gallop",
    "sino":       "bell ding small",
}

# Fallback local quando Freesound não está disponível
_SFX_LOCAL_FALLBACK = {
    "corvo":   "/sons/sistema/creepy-crow-caw-322991.mp3",
    "corvos":  "/sons/sistema/crows-6371.mp3",
    "grito":   "/sons/sistema/scream-of-terror-325532.mp3",
    "criança": "/sons/sistema/rianca_correndo.mp3",
    "moeda":   "/sons/sistema/coin-recieved.mp3",
    "cidade":  "/sons/sistema/medieval_village_atmosphere-79282.mp3",
    "vila":    "/sons/sistema/medieval_village_atmosphere-79282.mp3",
    "pessoas": "/sons/sistema/people-talking-in-the-old-town-city-center.mp3",
    "chuva":   "/sons/sistema/Rain-on-city-deck.mp3",
    "taverna": "/sons/sistema/tavern_ambience_inside_laughter-73008.mp3",
}

# Cache: query → URL (evita chamadas repetidas ao Freesound)
_sfx_cache: dict[str, str] = {}

def _keyword_from_narrative(text: str) -> tuple[str, str] | None:
    """Encontra o primeiro keyword PT e retorna (keyword_pt, query_en)."""
    text_lower = text.lower()
    for kw_pt, query_en in _SFX_MAP.items():
        if kw_pt in text_lower:
            return kw_pt, query_en
    return None

def _search_freesound(query_en: str) -> str | None:
    """Busca no Freesound e retorna URL de preview MP3, ou None."""
    api_key = os.getenv("FREESOUND_API_KEY")
    if not api_key:
        return None
    if query_en in _sfx_cache:
        return _sfx_cache[query_en]
    try:
        resp = http_requests.get(
            "https://freesound.org/apiv2/search/text/",
            params={
                "query": query_en,
                "token": api_key,
                "fields": "id,previews",
                "filter": "duration:[1 TO 25]",
                "page_size": 3,
            },
            timeout=4,
        )
        results = resp.json().get("results", [])
        if results:
            url = results[0]["previews"].get("preview-hq-mp3") or results[0]["previews"].get("preview-lq-mp3")
            if url:
                _sfx_cache[query_en] = url
                print(f"[SFX] Freesound: {query_en!r} → {url}")
                return url
    except Exception as e:
        print(f"[SFX] Freesound erro: {e}")
    return None

def detect_sfx(narrative_text: str) -> str | None:
    """Retorna URL do SFX: tenta Freesound primeiro, fallback local."""
    match = _keyword_from_narrative(narrative_text)
    if not match:
        return None
    kw_pt, query_en = match

    # 1. Tenta Freesound
    url = _search_freesound(query_en)
    if url:
        return url

    # 2. Fallback: arquivo local
    return _SFX_LOCAL_FALLBACK.get(kw_pt)


# ─── TTS server-side (retorna bytes MP3) ─────────────────────────────────────

def synthesize_speech(text: str, voice_type: str = "master") -> bytes | None:
    """Chama Google Cloud TTS e retorna os bytes MP3, ou None se indisponível."""
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
    print(f"[TTS] GOOGLE_APPLICATION_CREDENTIALS={creds_path!r}")
    print(f"[TTS] GOOGLE_CREDENTIALS_JSON set={bool(creds_json)}")

    try:
        from google.cloud import texttospeech

        if voice_type == "narrator":
            voice_name = os.getenv("GOOGLE_TTS_VOICE_NARRATOR", "pt-BR-Neural2-A")
            gender = texttospeech.SsmlVoiceGender.FEMALE
        else:
            voice_name = os.getenv("GOOGLE_TTS_VOICE_MASTER", "pt-BR-Neural2-B")
            gender = texttospeech.SsmlVoiceGender.MALE

        print(f"[TTS] Sintetizando com voz={voice_name}, texto={text[:60]!r}...")
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
        print(f"[TTS] OK — {len(response.audio_content)} bytes")
        return response.audio_content
    except Exception as e:
        print(f"[TTS] ERRO: {e}")
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
    sfx = detect_sfx(opening_clean)

    return {
        "session_id": session_id,
        "narrative": opening_clean,
        "audio": audio,
        "sfx": sfx,
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
    sfx = detect_sfx(cleaned_narrative)

    return {
        "narrative": cleaned_narrative,
        "audio": audio,
        "sfx": sfx,
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

app.mount("/sons", StaticFiles(directory="sons"), name="sons")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_index():
    return FileResponse("static/index.html")
