"""
Web API — Dragon's Breath / Plataforma Ressoar
Interface de voz: o jogador fala, o Mestre responde em áudio.
"""
import uuid
import os
import re
import base64
import random
import tempfile
import concurrent.futures
import requests as http_requests
from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import os as _os

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
from database import init_db, list_saves, get_save, upsert_save, delete_save
from auth import get_current_user, get_optional_user
from game import (
    get_gm_narrative,
    clean_and_process_ai_response,
    load_game_context_for_act,
    bootstrap_location_triggers,
    sync_act_with_location,
    is_inspection_action,
    get_player_eyes_response,
    resolve_action_roll,
    PAUSE_BEAT_PROMPT_SECONDS,
    start_resurrection_limbo,
    resolve_resurrection_offering,
)

app = FastAPI(title="Ressoar")

# Sessões em memória: { session_id: world_state }
sessions: dict[str, dict] = {}

# Mapa sessão → user_id (para auto-save)
session_user: dict[str, int] = {}

# Mapa sessão → campaign_id (para auto-save)
session_campaign: dict[str, str] = {}

# ── Bootstrap DB na inicialização ────────────────────────────────────────────
init_db()

_MOOD_TTS_SPEED = {
    "combat": 1.45,
    "tense": 1.15,
    "dramatic": 0.85,
    "sad": 0.80,
    "relief": 0.92,
    "normal": 1.0,
}


def _resolve_tts_speed(mood: str, tutorial_active: bool = False) -> float:
    speed = _MOOD_TTS_SPEED.get((mood or "normal").lower(), 1.0)
    if tutorial_active:
        return max(speed, 1.3)
    return speed


# ─── SFX: Freesound.org (gratuito) com fallback local ────────────────────────

# Mapeamento: keywords PT → query EN para Freesound
_SFX_MAP = {
    # Animais
    "corvo":      "raven crow caw dark",
    "corvos":     "flock crows cawing",
    "lobo":       "wolf howl",
    "lobos":      "wolves howling pack",
    "cavalo":     "horse hooves gallop",
    "cavalos":    "horses hooves gallop",
    "rato":       "rats scurrying squeaking",
    "ratos":      "rats scurrying squeaking",
    "serpente":   "snake hiss",
    "dragão":     "dragon roar",
    # Natureza / clima
    "chuva":      "rain ambient outdoor",
    "tempestade": "thunderstorm rain",
    "trovão":     "thunder crack storm",
    "relâmpago":  "lightning strike thunder",
    "vento":      "wind howling",
    "névoa":      "fog mist eerie atmosphere",
    "neblina":    "fog mist eerie atmosphere",
    "floresta":   "forest ambient birds",
    "rio":        "river stream flowing",
    "água":       "water stream flowing",
    "mar":        "ocean waves sea",
    "montanha":   "mountain wind howling",
    # Locais
    "taverna":    "medieval tavern inn ambience",
    "taverneiro": "tavern indoor ambience",
    "cidade":     "medieval city ambience",
    "vila":       "medieval village atmosphere",
    "umbraton":   "dark city gothic ambience",
    "mercado":    "market bazaar crowd",
    "castelo":    "castle medieval stone ambience",
    "masmorra":   "dungeon dark dripping",
    "calabouço":  "dungeon dark dripping",
    "caverna":    "cave dripping echo",
    "cemitério":  "graveyard cemetery dark wind",
    "pântano":    "swamp bog ambience",
    # Pessoas / sons humanos
    "pessoas":    "crowd murmur voices",
    "multidão":   "crowd talking indoor",
    "criança":    "children running footsteps",
    "grito":      "scream horror terror",
    "risada":     "evil laugh maniacal",
    "choro":      "crying sobbing",
    "sussurro":   "whisper dark eerie",
    "passos":     "footsteps stone floor",
    "guarda":     "armor footsteps march",
    # Combate / ação
    "espada":     "sword clash metal",
    "batalha":    "battle sword clash metal",
    "flecha":     "arrow whoosh",
    "explosão":   "explosion boom",
    # Objetos / ambiente
    "moeda":      "coin gold drop",
    "fogo":       "fire crackling fireplace",
    "porta":      "door creak open",
    "sino":       "bell church toll",
    "magia":      "magic spell whoosh sparkle",
    "feitiço":    "magic spell whoosh sparkle",
    "fantasma":   "ghost haunting eerie wind",
    "sombra":     "dark ominous eerie ambient",
    "musica":     "medieval lute bard music",
    "alaúde":     "medieval lute bard music",
    "melodia":    "medieval melody flute ambient",
    # Sistema
    "dados":      "dice rolling tabletop wooden",
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

# Música de abertura (buscada uma vez, cacheada para toda a sessão do servidor)
_intro_music_url: str | None = None

def _get_intro_music() -> str | None:
    global _intro_music_url
    if _intro_music_url:
        return _intro_music_url
    for query in [
        "epic orchestral fanfare fantasy opening",
        "majestic brass fanfare heroic intro",
        "orchestral sting medieval heroic",
    ]:
        url = _search_freesound(query, duration_filter="duration:[4 TO 20]")
        if url:
            _intro_music_url = url
            print(f"[INTRO] Música de abertura: {url}")
            return url
    return None

# Som de dissonância para ação inválida
_sfx_error_url: str | None = None

def _get_error_sfx() -> str | None:
    """Retorna URL do som de dissonância/erro. Busca no Freesound uma vez, cacheia."""
    global _sfx_error_url
    if _sfx_error_url:
        return _sfx_error_url
    url = _search_freesound("wrong note lute dissonance medieval")
    if not url:
        url = _search_freesound("dissonance sting error sound")
    _sfx_error_url = url
    return url


# Sons de dados (buscados uma vez e cacheados)
_sfx_dice_url:     str | None = None
_sfx_critical_url: str | None = None
_sfx_fumble_url:   str | None = None

def _get_dice_sfx() -> str | None:
    global _sfx_dice_url
    if _sfx_dice_url:
        return _sfx_dice_url
    _sfx_dice_url = _search_freesound("dice rolling tabletop wooden")
    return _sfx_dice_url

def _get_critical_sfx() -> str | None:
    global _sfx_critical_url
    if _sfx_critical_url:
        return _sfx_critical_url
    _sfx_critical_url = _search_freesound("fanfare triumph short brass")
    return _sfx_critical_url

def _get_fumble_sfx() -> str | None:
    global _sfx_fumble_url
    if _sfx_fumble_url:
        return _sfx_fumble_url
    _sfx_fumble_url = _search_freesound("dark sting dissonant low bass")
    return _sfx_fumble_url


# ─── Ambient por ato ──────────────────────────────────────────────────────────

_ACT_AMBIENTS: dict[int, str] = {
    1: "rain ambience dark",
    2: "choir medieval ambient",
    3: "dark dramatic orchestral",
}
_ambient_cache: dict[int, str | None] = {}

def _get_ambient_for_act(act: int) -> str | None:
    """Retorna URL do preview (~30s) para loop ambiente do ato.
    O browser faz loop desse preview indefinidamente.
    """
    if act in _ambient_cache:
        return _ambient_cache[act]
    query = _ACT_AMBIENTS.get(act)
    # Sem filtro de duração: previews Freesound sempre ~30s, perfeitos para loop
    url = _search_freesound(query, duration_filter=None) if query else None
    _ambient_cache[act] = url
    print(f"[AMBIENT] Ato {act}: {url}")
    return url


# ─── Sistema de triggers (portado de game.py) ─────────────────────────────────

def _resolve_sfx_keyword(kw_pt: str | None) -> str | None:
    """Resolve uma keyword PT para URL de SFX (Freesound → fallback local)."""
    if not kw_pt:
        return None
    query_en = _SFX_MAP.get(kw_pt)
    if not query_en:
        return None
    return _search_freesound(query_en) or _SFX_LOCAL_FALLBACK.get(kw_pt)

def _select_trigger(world_state: dict, game_context: dict) -> tuple[str | None, str | None]:
    """Seleciona um gatilho narrativo com chance progressiva.
    Retorna (descricao_para_injetar, url_sfx_do_gatilho).
    """
    from campaign_manager import get_current_campaign
    campaign = get_current_campaign()
    default_location = campaign.get("world_template", {}).get("initial_location", "local_inicial")

    location_key = world_state["world_state"].get("current_location_key", default_location)
    gatilhos_ativos = world_state["world_state"].get("gatilhos_ativos", {}).get(location_key, [])
    locais_definidos = game_context.get("locais", {})
    gatilhos_definidos = locais_definidos.get(location_key, {}).get("gatilhos", {})

    base_chance = 0.3
    acumulado = world_state.get("rodadas_sem_gatilho", 0) * 0.1
    chance_total = min(base_chance + acumulado, 0.9)

    if gatilhos_ativos and random.random() < chance_total:
        gatilho_id = random.choice(gatilhos_ativos)
        gatilho = gatilhos_definidos.get(gatilho_id, {})
        descricao = gatilho.get("descricao")
        sfx_kw = gatilho.get("sfx")

        world_state["world_state"]["gatilhos_ativos"][location_key].remove(gatilho_id)
        world_state["world_state"]["gatilhos_usados"].setdefault(location_key, []).append(gatilho_id)

        proximo_id = gatilho.get("proximo")
        if proximo_id:
            world_state["world_state"]["gatilhos_ativos"][location_key].append(proximo_id)

        world_state["rodadas_sem_gatilho"] = 0
        print(f"[TRIGGER] {gatilho_id} → sfx={sfx_kw!r}")
        return descricao, _resolve_sfx_keyword(sfx_kw)
    else:
        world_state["rodadas_sem_gatilho"] = world_state.get("rodadas_sem_gatilho", 0) + 1
        return None, None

def _search_freesound(query_en: str, duration_filter: str | None = "duration:[1 TO 25]") -> str | None:
    """Busca no Freesound e retorna URL de preview MP3, ou None.
    duration_filter=None → sem filtro de duração (para sons longos/ambientes).
    """
    api_key = os.getenv("FREESOUND_API_KEY")
    if not api_key:
        return None
    cache_key = f"{query_en}|{duration_filter}"
    if cache_key in _sfx_cache:
        return _sfx_cache[cache_key]
    try:
        params: dict = {
            "query": query_en,
            "token": api_key,
            "fields": "id,previews",
            "page_size": 3,
        }
        if duration_filter:
            params["filter"] = duration_filter
        resp = http_requests.get(
            "https://freesound.org/apiv2/search/text/",
            params=params,
            timeout=4,
        )
        results = resp.json().get("results", [])
        if results:
            url = results[0]["previews"].get("preview-hq-mp3") or results[0]["previews"].get("preview-lq-mp3")
            if url:
                _sfx_cache[cache_key] = url
                print(f"[SFX] Freesound: {query_en!r} → {url}")
                return url
    except Exception as e:
        print(f"[SFX] Freesound erro: {e}")
    return None

def detect_sfx_list(narrative_text: str) -> list[dict]:
    """Retorna até 3 SFX com posição relativa no texto (0.0–1.0).
    Cada entrada: {"url": "...", "position": 0.35}
    Position = onde no texto aquela palavra aparece → usada pelo browser
    para agendar o som no momento certo da narração.

    Usa word-boundary regex para evitar falsos matches como
    "taverna" dentro de "taverneiro".
    """
    text_lower = narrative_text.lower()
    total_chars = max(len(narrative_text), 1)
    results: list[dict] = []
    used_positions: list[int] = []

    for kw_pt, query_en in _SFX_MAP.items():
        if len(results) >= 3:
            break
        # "dados" é tratado exclusivamente via roll_sfx — nunca via texto
        if kw_pt == "dados":
            continue
        # Word-boundary: "taverna" não deve casar dentro de "taverneiro"
        match = re.search(r'\b' + re.escape(kw_pt) + r'\b', text_lower)
        if not match:
            continue
        pos = match.start()
        # Evita dois sons muito próximos no texto (< 40 chars de distância)
        if any(abs(pos - used) < 40 for used in used_positions):
            continue
        url = _search_freesound(query_en) or _SFX_LOCAL_FALLBACK.get(kw_pt)
        if url:
            results.append({"url": url, "position": round(pos / total_chars, 3)})
            used_positions.append(pos)
            print(f"[SFX] '{kw_pt}' pos={pos}/{total_chars} → {url}")

    return results


# ─── TTS server-side (retorna bytes MP3) ─────────────────────────────────────

def synthesize_speech(text: str, voice_type: str = "master", speed: float = 1.0) -> bytes | None:
    """Chama OpenAI TTS e retorna os bytes MP3, ou None se indisponível.

    Vozes configuráveis via env:
      OPENAI_TTS_VOICE_MASTER   (padrão: fable)
      OPENAI_TTS_VOICE_NARRATOR (padrão: nova)
    Modelo configurável via OPENAI_TTS_MODEL (padrão: tts-1).
    speed: 0.25–4.0 (padrão 1.0)
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("[TTS] OPENAI_API_KEY não configurada")
        return None

    if voice_type == "narrator":
        voice = os.getenv("OPENAI_TTS_VOICE_NARRATOR", "nova")
    else:
        voice = os.getenv("OPENAI_TTS_VOICE_MASTER", "fable")

    model = os.getenv("OPENAI_TTS_MODEL", "tts-1")
    print(f"[TTS] Sintetizando com voz={voice} modelo={model} speed={speed}, texto={text[:60]!r}...")

    try:
        from openai import OpenAI as _OpenAI
        client = _OpenAI(api_key=api_key)
        response = client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
            response_format="mp3",
            speed=speed,
        )
        audio_bytes = response.content
        print(f"[TTS] OK — {len(audio_bytes)} bytes")
        return audio_bytes
    except Exception as e:
        print(f"[TTS] ERRO: {e}")
        return None


def to_audio_response(text: str, voice_type: str = "master", speed: float = 1.0) -> str | None:
    """Retorna áudio como base64 string, ou None."""
    audio_bytes = synthesize_speech(text, voice_type, speed)
    if audio_bytes:
        return base64.b64encode(audio_bytes).decode("utf-8")
    return None


def build_audio_payload(
    text: str,
    voice_type: str = "master",
    speed: float = 1.0,
    pause_segments: list[str] | None = None,
    pause_ms: int = PAUSE_BEAT_PROMPT_SECONDS,
) -> tuple[str | None, list[dict] | None]:
    """
    Retorna (audio_base64, audio_timeline).
    - Sem pause beats: usa payload tradicional `audio`.
    - Com pause beats: gera timeline com segmentos de áudio e pausas reais.
    """
    valid_segments = [
        seg.strip() for seg in (pause_segments or [])
        if isinstance(seg, str) and seg.strip()
    ]

    if len(valid_segments) > 1:
        timeline: list[dict] = []
        for idx, segment in enumerate(valid_segments):
            clip = to_audio_response(segment, voice_type, speed)
            if clip:
                timeline.append({"type": "audio", "audio": clip})
            if idx < len(valid_segments) - 1:
                timeline.append({"type": "pause", "ms": pause_ms})

        if timeline and any(item.get("type") == "audio" for item in timeline):
            return None, timeline

    return to_audio_response(text, voice_type, speed), None


# ─── Modelos de request ───────────────────────────────────────────────────────

class TranscribeRequest(BaseModel):
    audio: str       # base64 do áudio gravado pelo MediaRecorder
    mime_type: str = "audio/webm"  # mime type enviado pelo browser

class TTSRequest(BaseModel):
    text: str
    voice_type: str = "narrator"

class StartRequest(BaseModel):
    player_name: str
    campaign_id: str
    tutorial: bool = False
    player_class: str = "Aventureiro"
    # JWT token opcional — permite vincular a sessão ao usuário logado
    token: str | None = None

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
        "death_count": pc.get("death_count", 0),
        "alignment": pc.get("alignment", "neutro"),
        "resurrection_flaws": pc.get("resurrection_flaws", []),
        "inventory": pc.get("inventory", []),
        "max_slots": pc.get("max_slots", 10),
        "location": ws.get("current_location_key", ""),
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.post("/api/tts")
def tts_endpoint(req: TTSRequest):
    """Sintetiza texto em áudio MP3 (base64). Usado pelo prólogo e tutorial."""
    audio = to_audio_response(req.text, req.voice_type)
    return {"audio": audio}


@app.post("/api/transcribe")
def transcribe_audio(req: TranscribeRequest):
    """Transcreve áudio via OpenAI Whisper (gpt-4o-mini-transcribe).
    Recebe base64 de áudio webm/opus gravado pelo MediaRecorder do browser.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(500, "OPENAI_API_KEY não configurada")

    try:
        audio_bytes = base64.b64decode(req.audio)
    except Exception:
        raise HTTPException(400, "Áudio base64 inválido")

    # Determina extensão pelo mime type (webm, mp4, ogg, wav, etc.)
    _EXT_MAP = {
        "audio/webm": ".webm", "audio/ogg": ".ogg",
        "audio/mp4": ".mp4",   "audio/wav": ".wav",
        "audio/mpeg": ".mp3",  "audio/mp3": ".mp3",
    }
    ext = _EXT_MAP.get(req.mime_type.split(";")[0].strip(), ".webm")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name

        from openai import OpenAI as _OpenAI
        client = _OpenAI(api_key=api_key)
        with open(tmp_path, "rb") as f:
            result = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=f,
                language="pt",
                # Prompt ajuda Whisper com vocabulário específico do jogo
                prompt="Jogo de RPG medieval. Nomes: Umbraton, Bardo, Bardo Viajante, taverna, praga, dragão, santuário.",
            )
        text = result.text.strip()
        print(f"[TRANSCRIBE] {text!r}")
        return {"text": text}
    except Exception as e:
        print(f"[TRANSCRIBE] ERRO: {e}")
        raise HTTPException(500, f"Erro na transcrição: {e}")
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


@app.get("/api/campaigns")
def get_campaigns():
    return {"campaigns": list_available_campaigns()}


# ─── Auth / config endpoints ──────────────────────────────────────────────────

@app.get("/api/config")
def get_config():
    """Expõe a Clerk Publishable Key para o frontend (é uma chave pública)."""
    return {
        "clerk_publishable_key": _os.environ.get("CLERK_PUBLISHABLE_KEY", ""),
        "clerk_frontend_api": _os.environ.get(
            "CLERK_FRONTEND_API",
            "https://definite-firefly-91.clerk.accounts.dev",
        ),
    }


@app.get("/api/auth/me")
def me(current_user: dict = Depends(get_current_user)):
    """Verifica o token Clerk e retorna o clerk_user_id."""
    return {"clerk_user_id": current_user["clerk_user_id"]}


# ─── Save/Load endpoints ──────────────────────────────────────────────────────

@app.get("/api/saves")
def get_saves(current_user: dict = Depends(get_current_user)):
    saves = list_saves(current_user["clerk_user_id"])
    return {"saves": saves}


@app.post("/api/save")
def manual_save(session_id: str, current_user: dict = Depends(get_current_user)):
    world_state = sessions.get(session_id)
    if world_state is None:
        raise HTTPException(404, "Sessão não encontrada")
    pc = world_state.get("player_character", {})
    uid = current_user["clerk_user_id"]
    save_id = upsert_save(
        clerk_user_id=uid,
        character_name=pc.get("name", "?"),
        character_class=pc.get("class", "Aventureiro"),
        campaign_id=session_campaign.get(session_id, "unknown"),
        world_state=world_state,
    )
    session_user[session_id] = uid
    return {"save_id": save_id, "message": "Progresso salvo"}


@app.post("/api/load/{save_id}")
def load_save(save_id: int, current_user: dict = Depends(get_current_user)):
    import json as _json
    uid = current_user["clerk_user_id"]
    save = get_save(save_id, uid)
    if not save:
        raise HTTPException(404, "Save não encontrado")

    world_state = _json.loads(save["world_state"])
    new_session_id = str(uuid.uuid4())
    sessions[new_session_id] = world_state
    session_user[new_session_id] = uid
    session_campaign[new_session_id] = save["campaign_id"]

    recent = world_state.get("recent_narrations", [])
    last_narrative = recent[-1] if recent else "A aventura continua..."

    return {
        "session_id": new_session_id,
        "state": _state_summary(world_state),
        "last_narrative": last_narrative,
        "campaign_id": save["campaign_id"],
    }


@app.delete("/api/saves/{save_id}")
def remove_save(save_id: int, current_user: dict = Depends(get_current_user)):
    if not delete_save(save_id, current_user["clerk_user_id"]):
        raise HTTPException(404, "Save não encontrado")
    return {"message": "Personagem removido"}


@app.post("/api/start")
def start_game(req: StartRequest):
    if not req.player_name.strip():
        raise HTTPException(400, "Nome não pode ser vazio")

    switch_campaign(req.campaign_id)
    world_state = create_initial_world_state(req.player_name.strip(), req.player_class)
    world_state["game_mode"] = "rpg"
    if req.tutorial:
        world_state["tutorial_turn"] = 3

    current_act = world_state["player_character"]["current_act"]
    game_context = load_game_context_for_act(current_act, world_state)
    game_context["gatilhos"] = []

    opening_raw = get_gm_narrative(world_state, "Iniciou a aventura", game_context)
    opening_clean, world_state = clean_and_process_ai_response(opening_raw, world_state)
    world_state = update_world_state(world_state, "Iniciou a aventura", opening_raw)
    world_state["recent_narrations"] = [opening_clean[:300]]

    session_id = str(uuid.uuid4())
    sessions[session_id] = world_state
    session_campaign[session_id] = req.campaign_id

    # Vincula sessão ao usuário Clerk se token válido
    if req.token:
        from auth import get_optional_user as _opt
        from fastapi.security import HTTPAuthorizationCredentials as _Creds
        try:
            from jose import jwt as _jwt
            from auth import _get_jwks, CLERK_FRONTEND_API as _CFAPI
            claims = _jwt.decode(
                req.token, _get_jwks(), algorithms=["RS256"],
                options={"verify_aud": False},
            )
            uid = claims.get("sub")
            if uid:
                session_user[session_id] = uid
        except Exception:
            pass

    mood = world_state.get("narration_mood", "normal")
    tts_speed = _resolve_tts_speed(mood, tutorial_active=req.tutorial)
    pause_segments = world_state.get("pause_beat_segments", [])

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        future_tts     = pool.submit(build_audio_payload, opening_clean, "master", tts_speed, pause_segments)
        future_ambient = pool.submit(_get_ambient_for_act, current_act)
        future_intro   = pool.submit(_get_intro_music)
        audio, audio_timeline = future_tts.result()
        ambient_url           = future_ambient.result()
        intro_music_url       = future_intro.result()

    world_state["pause_beat_segments"] = []
    world_state["pause_beat_count"] = 0
    sfx = detect_sfx_list(opening_clean)

    return {
        "session_id": session_id,
        "narrative": opening_clean,
        "audio": audio,
        "audio_timeline": audio_timeline,
        "sfx": sfx,
        "mood": mood,
        "intro_music": intro_music_url,
        "ambient": {"url": ambient_url, "volume": 0.15} if ambient_url else None,
        "state": _state_summary(world_state),
        "tutorial_turn": world_state.get("tutorial_turn", 0),
    }


@app.post("/api/action")
def take_action(req: ActionRequest):
    world_state = sessions.get(req.session_id)
    if world_state is None:
        raise HTTPException(404, "Sessão não encontrada. Inicie um novo jogo.")

    action = req.action.strip()
    if not action:
        raise HTTPException(400, "Ação não pode ser vazia")

    resurrection_state = world_state.get("resurrection_state", {})
    if isinstance(resurrection_state, dict) and resurrection_state.get("stage") == "awaiting_offering":
        result = resolve_resurrection_offering(world_state, action)
        roll_data = result.get("roll") or {}
        narrative = result["narrative"]
        mood = world_state.get("narration_mood", result.get("mood", "sad"))
        tts_speed = _resolve_tts_speed(mood, tutorial_active=False)
        pause_segments = world_state.get("pause_beat_segments", [])
        audio, audio_timeline = build_audio_payload(
            narrative,
            "master",
            tts_speed,
            pause_segments=pause_segments,
        )
        world_state["pause_beat_segments"] = []
        world_state["pause_beat_count"] = 0
        sessions[req.session_id] = world_state

        return {
            "narrative": narrative,
            "audio": audio,
            "audio_timeline": audio_timeline,
            "sfx": [],
            "mood": mood,
            "roll": result.get("roll"),
            "roll_sfx": _get_dice_sfx() if result.get("roll") else None,
            "critical_sfx": _get_critical_sfx() if roll_data.get("critical") else None,
            "fumble_sfx": _get_fumble_sfx() if roll_data.get("fumble") else None,
            "resurrection": True,
            "resurrection_result": result.get("result_type"),
            "valid": bool(result.get("ok", False)),
            "state": _state_summary(world_state),
            "tutorial_turn": world_state.get("tutorial_turn", 0),
        }

    # HUD Narrativo — Agente "Olhos do Jogador" (não avança o tempo do jogo)
    if is_inspection_action(action):
        narrative = get_player_eyes_response(action, world_state)
        print(f"[OLHOS] {narrative[:80]!r}...")
        return {
            "narrative": narrative,
            "audio": to_audio_response(narrative, "narrator"),
            "state": _state_summary(world_state),
            "inspection": True,
            "valid": True,
        }

    # Processa ação no motor do jogo
    character = world_state.get("player_character", {})
    current_act = character.get("current_act", 1)
    game_context = load_game_context_for_act(current_act, world_state)
    bootstrap_location_triggers(world_state, game_context.get("locais", {}))

    # Sistema de dados Shadowdark
    roll_result = resolve_action_roll(action, character, world_state)
    if roll_result:
        mod_pt = {"advantage": "Vantagem", "disadvantage": "Desvantagem", "normal": "Normal"}[roll_result["modifier"]]
        print(f"[DADOS] {mod_pt} | {roll_result['dice']} → {roll_result['roll']} vs DC {roll_result['dc']} | {'SUCESSO' if roll_result['success'] else 'FALHA'}{'(CRÍTICO)' if roll_result['critical'] else ''}{'(FUMBLE)' if roll_result['fumble'] else ''}")

    # Seleciona gatilho narrativo e injeta na ação
    trigger_desc, trigger_sfx_url = _select_trigger(world_state, game_context)
    action_with_trigger = f"{action}\n[Gatilho]: {trigger_desc}" if trigger_desc else action
    game_context["gatilhos"] = [trigger_desc] if trigger_desc else []

    gm_response = get_gm_narrative(world_state, action_with_trigger, game_context, roll_result)
    cleaned_narrative, world_state = clean_and_process_ai_response(gm_response, world_state)

    # Arquivista (update_world_state) e TTS rodam em paralelo — maior ganho de latência
    mood_pre      = world_state.get("narration_mood", "normal")
    tutorial_turn = world_state.get("tutorial_turn", 0)
    tts_speed_pre = _resolve_tts_speed(mood_pre, tutorial_active=tutorial_turn > 0)
    pause_segments_pre = world_state.get("pause_beat_segments", [])
    hdywdtd_pre   = bool(world_state.get("hdywdtd_pending"))
    hdywdtd_prompt_pre = world_state.get("hdywdtd_prompt", "Como você quer fazer isso?") if hdywdtd_pre else None

    def _build_tts():
        if hdywdtd_pre:
            spd = min(tts_speed_pre, 0.82)
            if isinstance(pause_segments_pre, list) and pause_segments_pre:
                segs = [s for s in pause_segments_pre if isinstance(s, str) and s.strip()]
                segs.append(hdywdtd_prompt_pre)
                return build_audio_payload(" ".join(segs), "master", spd, pause_segments=segs)
            txt = f"{cleaned_narrative} ... {hdywdtd_prompt_pre}" if cleaned_narrative else hdywdtd_prompt_pre
            return build_audio_payload(txt, "master", spd)
        return build_audio_payload(cleaned_narrative, "master", tts_speed_pre, pause_segments=pause_segments_pre)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        future_ws  = pool.submit(update_world_state, world_state, action_with_trigger, gm_response)
        future_tts = pool.submit(_build_tts)
        world_state        = future_ws.result()
        audio, audio_timeline = future_tts.result()

    if hdywdtd_pre:
        world_state["hdywdtd_pending"] = False

    sync_act_with_location(world_state)

    limbo_started, limbo_narrative = start_resurrection_limbo(world_state)
    if limbo_started:
        cleaned_narrative = limbo_narrative
        world_state["narration_mood"] = "sad"
        audio, audio_timeline = build_audio_payload(cleaned_narrative, "master", _resolve_tts_speed("sad"))

    recent = world_state.get("recent_narrations", [])
    recent.append(cleaned_narrative[:300])
    world_state["recent_narrations"] = recent[-2:]

    tutorial_turn = world_state.get("tutorial_turn", 0)
    if tutorial_turn > 0:
        world_state["tutorial_turn"] = tutorial_turn - 1

    sessions[req.session_id] = world_state

    # Auto-save para usuários autenticados via Clerk
    uid = session_user.get(req.session_id)
    if uid:
        try:
            pc = world_state.get("player_character", {})
            upsert_save(
                clerk_user_id=uid,
                character_name=pc.get("name", "?"),
                character_class=pc.get("class", "Aventureiro"),
                campaign_id=session_campaign.get(req.session_id, "unknown"),
                world_state=world_state,
            )
        except Exception as _e:
            print(f"[SAVE] Auto-save falhou: {_e}")

    new_act = world_state.get("player_character", {}).get("current_act", 1)
    ambient_url = _get_ambient_for_act(new_act) if new_act != current_act else None
    mood = world_state.get("narration_mood", mood_pre)
    hdywdtd = hdywdtd_pre

    world_state["pause_beat_segments"] = []
    world_state["pause_beat_count"] = 0

    # SFX: usa hint do GM (IA) quando disponível; fallback para keyword scan
    gm_sfx_hint = world_state.pop("_gm_sfx_hint", None)
    if gm_sfx_hint:
        sfx_url = _resolve_sfx_keyword(gm_sfx_hint)
        sfx = [{"url": sfx_url, "position": 0.1}] if sfx_url else []
    else:
        sfx = detect_sfx_list(cleaned_narrative)

    return {
        "narrative": cleaned_narrative,
        "audio": audio,
        "audio_timeline": audio_timeline,
        "sfx": sfx,
        "mood": mood,
        "trigger_sfx": trigger_sfx_url,
        "roll_sfx":      _get_dice_sfx()    if roll_result else None,
        "critical_sfx":  _get_critical_sfx() if roll_result and roll_result["critical"] else None,
        "fumble_sfx":    _get_fumble_sfx()   if roll_result and roll_result["fumble"]   else None,
        "roll": roll_result,
        "hdywdtd": hdywdtd,
        "hdywdtd_prompt": hdywdtd_prompt_pre,
        "resurrection": limbo_started,
        "resurrection_result": "limbo" if limbo_started else None,
        "ambient": {"url": ambient_url, "volume": 0.15} if ambient_url else None,
        "state": _state_summary(world_state),
        "valid": True,
        "tutorial_turn": world_state.get("tutorial_turn", 0),
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
def serve_landing():
    return FileResponse("static/landing.html")

@app.get("/jogo")
def serve_game():
    return FileResponse("static/index.html")
