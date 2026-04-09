import os
import logging
import requests
import pygame
import speech_recognition as sr
import io
from dotenv import load_dotenv
import json
import base64

logger = logging.getLogger(__name__)

# Tenta importar pyttsx3 para TTS gratuito local
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

# Tenta importar Google Cloud TTS para opção mais barata
try:
    from google.cloud import texttospeech
    GOOGLE_TTS_AVAILABLE = True
except ImportError:
    GOOGLE_TTS_AVAILABLE = False

load_dotenv()

# Configurações de custo e qualidade
TTS_PRIORITY = [
    "google_cloud",  # Mais barato: $4/1M chars (Standard) vs $22/1M (ElevenLabs)
    "local_pyttsx3", # Gratuito
    "elevenlabs"     # Mais caro, mas melhor qualidade
]

# Cache para evitar chamadas desnecessárias
_tts_cache = {}
_last_tts_service = None

# Inicializa pygame mixer para áudio
_mixer_initialized = False

def _ensure_mixer_initialized():
    """Garante que o mixer pygame está inicializado apenas quando necessário."""
    global _mixer_initialized
    if not _mixer_initialized:
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            _mixer_initialized = True
        except Exception as e:
            logger.warning(f"Falha ao inicializar pygame mixer: {e}. Áudio desativado.")

def text_to_speech_google_cloud(text, voice_type="master"):
    """TTS usando Google Cloud com arquivo JSON (mais barato: $4/1M chars vs $22/1M ElevenLabs)"""
    if not GOOGLE_TTS_AVAILABLE:
        return False

    try:
        # Configura credenciais usando o arquivo JSON local
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

        # Se não estiver no .env, tenta usar o arquivo JSON local
        if not credentials_path:
            json_file = 'dragonsbreath-NOVO.json'
            if os.path.exists(json_file):
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = json_file
                logger.info(f"Usando credenciais do arquivo: {json_file}")
            else:
                logger.error("Arquivo de credenciais Google Cloud não encontrado")
                return False

        client = texttospeech.TextToSpeechClient()

        # Seleciona vozes configuradas no .env (fallback para Neural2)
        if voice_type == "narrator":
            voice_name = os.getenv('GOOGLE_TTS_VOICE_NARRATOR', 'pt-BR-Neural2-A')
            gender = texttospeech.SsmlVoiceGender.FEMALE
        else:
            voice_name = os.getenv('GOOGLE_TTS_VOICE_MASTER', 'pt-BR-Neural2-B')
            gender = texttospeech.SsmlVoiceGender.MALE

        voice = texttospeech.VoiceSelectionParams(
            language_code="pt-BR",
            name=voice_name,
            ssml_gender=gender
        )

        # Configuração de áudio otimizada para português brasileiro
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.5,  # Velocidade aumentada conforme preferência
            pitch=0.0,
            volume_gain_db=0.0,
            sample_rate_hertz=22050  # Qualidade otimizada
        )

        synthesis_input = texttospeech.SynthesisInput(text=text)

        logger.info(f"Sintetizando com Google Cloud TTS (pt-BR): {voice_name}")
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        # Reproduz o áudio
        _ensure_mixer_initialized()
        audio_data = io.BytesIO(response.audio_content)
        pygame.mixer.music.load(audio_data)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            try:
                pygame.time.wait(100)
            except KeyboardInterrupt:
                pygame.mixer.music.stop()
                raise

        logger.info(f"Google Cloud TTS concluído ({len(response.audio_content)} bytes)")
        return True

    except Exception as e:
        logger.warning(f"Google Cloud TTS error: {e}. Verifique se dragonsbreath-NOVO.json está presente.")
        return False

def text_to_speech_local(text, voice_type="master"):
    """TTS gratuito usando pyttsx3 (sistema local)"""
    if not PYTTSX3_AVAILABLE:
        return False

    try:
        engine = pyttsx3.init()

        # Configura velocidade mais rápida (conforme preferência do usuário)
        rate = engine.getProperty('rate')
        engine.setProperty('rate', rate + 50)

        # Tenta configurar voz portuguesa se disponível
        voices = engine.getProperty('voices')
        for voice in voices:
            if 'portuguese' in voice.name.lower() or 'brasil' in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break
            # Fallback para vozes femininas/masculinas se português não disponível
            elif voice_type == "narrator" and 'female' in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break
            elif voice_type == "master" and 'male' in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break

        engine.say(text)
        engine.runAndWait()
        return True
    except Exception as e:
        logger.warning(f"Local TTS error: {e}")
        return False

def text_to_speech_elevenlabs(text, voice_type="master"):
    """TTS usando ElevenLabs (mais caro: $22/1M chars, mas melhor qualidade)"""
    _ensure_mixer_initialized()

    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        return False

    # Seleciona a voz baseada no tipo (usando vozes mais baratas)
    if voice_type == "narrator":
        # Voz feminina mais barata para introdução do Ressoar
        voice_id = "pNInz6obpgDQGcFmaJgB"  # Adam - voz mais barata (pode ser usada para feminino)
    else:
        # Voz masculina mais barata para o Mestre
        voice_id = "pNInz6obpgDQGcFmaJgB"  # Adam - voz mais barata

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }

    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",  # Mantém multilíngue para português
        "voice_settings": {
            "stability": 0.5,  # Reduzido para economizar processamento
            "similarity_boost": 0.5,  # Reduzido para economizar processamento
            "style": 0.0,  # Mínimo para economizar
            "use_speaker_boost": False,  # Desabilitado para economizar
            "speed": 1.5
        }
    }

    try:
        # Reduz volume dos efeitos sonoros durante a fala (30% de redução = 70% do volume)
        pygame.mixer.set_num_channels(8)
        for i in range(8):
            channel = pygame.mixer.Channel(i)
            if channel.get_busy():
                channel.set_volume(0.7)  # 70% do volume original (30% de redução)

        response = requests.post(url, json=data, headers=headers)

        if response.status_code == 200:
            audio_data = io.BytesIO(response.content)
            pygame.mixer.music.load(audio_data)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                try:
                    pygame.time.wait(100)
                except KeyboardInterrupt:
                    pygame.mixer.music.stop()
                    raise
            # Restaura volume dos efeitos sonoros
            for i in range(8):
                channel = pygame.mixer.Channel(i)
                if channel.get_busy():
                    channel.set_volume(1.0)  # Volume normal
            return True
        else:
            if response.status_code == 401:
                logger.warning("ElevenLabs API quota exceeded")
            else:
                logger.warning(f"ElevenLabs API error - Status: {response.status_code}")
            return False
    except Exception as e:
        logger.warning(f"ElevenLabs TTS error: {e}")
        return False

def text_to_speech(text, voice_type="master"):
    """Sistema inteligente de TTS com fallback por custo-efetividade

    Prioridade:
    1. Google Cloud TTS (Standard): $4/1M chars (82% mais barato que ElevenLabs)
    2. Local pyttsx3: GRATUITO
    3. ElevenLabs: $22/1M chars (melhor qualidade, mas mais caro)

    Args:
        text: Texto para converter em fala
        voice_type: "master" para voz do mestre (Brian), "narrator" para narradora (voz feminina)
    """
    global _last_tts_service

    # Cache simples para evitar repetições
    cache_key = f"{text[:50]}_{voice_type}"
    if cache_key in _tts_cache:
        logger.debug("Usando áudio em cache")
        return

    # Tenta cada serviço na ordem de prioridade
    for service in TTS_PRIORITY:
        success = False

        if service == "google_cloud":
            logger.debug("Tentando Google Cloud TTS...")
            success = text_to_speech_google_cloud(text, voice_type)

        elif service == "local_pyttsx3":
            logger.debug("Tentando TTS local (gratuito)...")
            success = text_to_speech_local(text, voice_type)

        elif service == "elevenlabs":
            logger.debug("Tentando ElevenLabs TTS (premium)...")
            success = text_to_speech_elevenlabs(text, voice_type)

        if success:
            _last_tts_service = service
            _tts_cache[cache_key] = True
            logger.debug(f"TTS bem-sucedido com {service}")
            return
        else:
            logger.warning(f"Falha no {service}, tentando próximo...")

    # Se todos falharam
    logger.error("Todos os serviços de TTS falharam - continuando apenas com texto")
    _last_tts_service = None

def play_sfx(sfx_name):
    """Toca um efeito sonoro específico"""
    _ensure_mixer_initialized()

    sfx_files = {
        "chime": "sons/sistema/chime-2-356833.mp3",
        "coin": "sons/sistema/coin-recieved.mp3",
        "crow": "sons/sistema/creepy-crow-caw-322991.mp3",
        "crows": "sons/sistema/crows-6371.mp3",
        "fome": "sons/sistema/fome.mp3",
        "logo": "sons/sistema/logo-sfx-316751.mp3",
        "village": "sons/sistema/medieval_village_atmosphere-79282.mp3",
        "people": "sons/sistema/people-talking-in-the-old-town-city-center.mp3",
        "rain": "sons/sistema/Rain-on-city-deck.mp3",
        "tavern": "sons/sistema/tavern_ambience_inside_laughter-73008.mp3",
        "familiar1": "sons/sistema/familiar_sound.mp3",
        "familiar2": "sons/sistema/familiar_sound2.mp3",
        "familiar3": "sons/sistema/familiar_sound3.mp3",
        "crianca": "sons/sistema/rianca_correndo.mp3",
        "scream": "sons/sistema/scream-of-terror-325532.mp3"
    }
    
    try:
        sfx_path = sfx_files.get(sfx_name)
        if sfx_path and os.path.exists(sfx_path):
            pygame.mixer.Sound(sfx_path).play()
        else:
            logger.warning(f"Sound file not found: {sfx_path}")
    except Exception as e:
        logger.warning(f"Sound effect error: {e}")

# Mapeamento de palavras-chave para efeitos sonoros contextuais (deduplicado)
SFX_KEYWORDS: dict[str, list[str]] = {
    'crow':      ['corvo', 'corvos', 'grasnido', 'grasnar', 'pássaro negro', 'ave sombria', 'olhos brancos', 'ave majestosa', 'criatura sinistra'],
    'crows':     ['bando de corvos', 'corvos voam', 'múltiplos corvos', 'revoada'],
    'scream':    ['grito', 'grita', 'berro', 'urro', 'gritou', 'brado', 'clamor', 'alarido', 'desespero', 'angústia'],
    'crianca':   ['criança', 'criança correndo', 'passos de criança', 'menino', 'menina', 'garoto', 'garota'],
    'coin':      ['moeda', 'moedas', 'dinheiro', 'ouro', 'prata', 'tesouro', 'riqueza'],
    'village':   ['cidade', 'vila', 'povoado', 'ruas', 'portões', 'muralhas', 'casa', 'sala', 'ambiente'],
    'people':    ['pessoas', 'multidão', 'conversas', 'vozes', 'murmúrios', 'visitante', 'alguém'],
    'rain':      ['chuva', 'chove', 'chovendo', 'gotas', 'tempestade', 'aguaceiro', 'dezembro', 'noite sombria'],
    'tavern':    ['taverna', 'bar', 'estalagem', 'bebida', 'taverneiro', 'aconchegante'],
    'wind':      ['vento', 'ventos', 'brisa', 'rajada', 'ventania', 'sopro', 'uivava', 'sussurrava o vento'],
    'fire':      ['fogo', 'chamas', 'lareira', 'brasas', 'crepitar', 'fogueira', 'incêndio', 'ardor'],
    'door':      ['porta', 'batida', 'batidas', 'bater', 'pancada', 'pancadas', 'rangido', 'abrir porta', 'batida suave', 'batida persistente'],
    'footsteps': ['passos', 'passadas', 'caminhada', 'pisar', 'pegadas', 'aproximar-se'],
    'bell':      ['sino', 'sinos', 'badalar', 'badalada', 'repique', 'campainha'],
    'thunder':   ['trovão', 'trovões', 'trovoada', 'estrondo', 'ribombo'],
    'water':     ['água', 'rio', 'riacho', 'córrego', 'fonte', 'gotejamento', 'pingar'],
    'night':     ['noite', 'escuridão', 'trevas', 'sombras', 'luar', 'meia-noite', 'anoitecer', 'silêncio da noite'],
    'book':      ['livro', 'livros', 'páginas', 'folhear', 'estante', 'pergaminho', 'volumes', 'páginas amareladas'],
    'candle':    ['vela', 'velas', 'chama', 'pavio', 'cera', 'iluminação', 'luz fraca'],
    'clock':     ['relógio', 'tique-taque', 'ponteiros', 'badaladas'],
    'whisper':   ['sussurro', 'sussurros', 'murmurar', 'cochichar', 'voz baixa', 'sussurrar'],
}


def trigger_contextual_sfx(narrative_text: str):
    """Analisa o texto narrativo e toca o efeito sonoro contextual mais adequado."""
    text_lower = narrative_text.lower()
    for sfx_name, keywords in SFX_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                play_sfx(sfx_name)
                return


def narrator_speech(text):
    """Usa voz feminina para narração (introdução do Ressoar)"""
    text_to_speech(text, voice_type="narrator")

def master_speech(text):
    """Usa voz masculina para o Mestre do jogo"""
    text_to_speech(text, voice_type="master")

def play_chime():
    """Toca o som de chime quando o jogo está ouvindo"""
    play_sfx("chime")

def play_ressoar_opening_sequence():
    """
    Sequência especial de abertura da Plataforma Ressoar:
    1. Som único de abertura (logo)
    2. Narração sobre o Ressoar
    3. Pausa antes das opções
    """
    logger.info("Iniciando sequência de abertura do Ressoar...")

    # 1. Som único de abertura - logo do Ressoar
    logger.debug("Tocando som de abertura...")
    play_sfx("logo")

    # Aguarda o som terminar
    import time
    time.sleep(2)  # Ajuste conforme duração do som do logo

    # 2. Narração especial sobre o Ressoar com voz feminina (TEXTO ORIGINAL)
    ressoar_intro = """Existe um som que só você pode emitir.

Um timbre único, uma frequência que é só sua.

Bem-vindo a Ressoar.

Este não é um lugar para seguir caminhos, mas para criar ecos.

Cada passo seu deixará uma marca. Cada feito seu será lembrado.

O mundo é todo ouvidos. O que ele vai escutar de você?"""

    logger.debug("Narrando introdução do Ressoar...")
    narrator_speech(ressoar_intro)

    # 3. Pausa dramática antes das opções
    time.sleep(1)
    logger.info("Sequência de abertura concluída. Apresentando opções...")

def play_mode_selection_audio():
    """
    Áudio específico para a seleção de modo de jogo.
    Toca após a sequência de abertura.
    """
    selection_text = """Agora escolha sua jornada:
    Modo RPG para aventuras com liberdade total,
    ou Modo Conto Interativo para histórias clássicas com múltiplos destinos."""

    narrator_speech(selection_text)
    play_chime()  # Indica que pode fazer a escolha

def speech_to_text():
    """Converte fala em texto usando reconhecimento de voz"""
    _ensure_mixer_initialized()
    play_chime()  # Toca o chime antes de ouvir
    r = sr.Recognizer()

    try:
        with sr.Microphone() as source:
            try:
                r.adjust_for_ambient_noise(source, duration=0.5)  # Tempo adequado para calibrar
                audio = r.listen(source, timeout=10, phrase_time_limit=15)  # Tempo suficiente para falar após narração

                text = r.recognize_google(audio, language='pt-BR')
                return text

            except sr.WaitTimeoutError:
                logger.warning("Tempo limite para fala excedido.")
                return input("Digite sua ação: > ").strip()
            except sr.UnknownValueError:
                logger.warning("Não consegui entender a fala.")
                return input("Digite sua ação: > ").strip()
            except KeyboardInterrupt:
                logger.info("Reconhecimento de voz interrompido pelo usuário.")
                return input("Digite sua ação: > ").strip()
            except Exception as e:
                logger.warning(f"Erro no reconhecimento de voz: {e}")
                return input("Digite sua ação: > ").strip()
    except Exception as e:
        logger.warning(f"Microfone não disponível: {e}")
        return input("Digite sua ação: > ").strip()