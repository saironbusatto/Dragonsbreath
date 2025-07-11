import os
import requests
import pygame
import speech_recognition as sr
import io
from dotenv import load_dotenv

load_dotenv()

# Inicializa pygame mixer para áudio
try:
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
except:
    pass

def text_to_speech(text):
    """Converte texto em áudio usando ElevenLabs"""
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        pass
        return
    
    url = "https://api.elevenlabs.io/v1/text-to-speech/nPczCjzI2devNBz1zQrb"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.7,
            "similarity_boost": 0.8,
            "style": 0.3,
            "use_speaker_boost": True
        }
    }
    
    try:
        # Reduz volume dos efeitos sonoros durante a fala
        pygame.mixer.set_num_channels(8)
        for i in range(8):
            channel = pygame.mixer.Channel(i)
            if channel.get_busy():
                channel.set_volume(0.4)  # 40% do volume original
        
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            audio_data = io.BytesIO(response.content)
            pygame.mixer.music.load(audio_data)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
                
            # Restaura volume dos efeitos sonoros
            for i in range(8):
                channel = pygame.mixer.Channel(i)
                if channel.get_busy():
                    channel.set_volume(1.0)  # Volume normal
        else:
            pass
    except Exception as e:
        pass

def play_sfx(sfx_name):
    """Toca um efeito sonoro específico"""
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
    except Exception as e:
        pass

def play_chime():
    """Toca o som de chime quando o jogo está ouvindo"""
    play_sfx("chime")

def speech_to_text():
    """Converte fala em texto usando reconhecimento de voz"""
    play_chime()  # Toca o chime antes de ouvir
    r = sr.Recognizer()
    
    with sr.Microphone() as source:
        try:
            r.adjust_for_ambient_noise(source, duration=0.3)
            audio = r.listen(source, timeout=5, phrase_time_limit=10)
            
            text = r.recognize_google(audio, language='pt-BR')
            return text
            
        except sr.WaitTimeoutError:
            text_to_speech("Não consegui ouvir nada. Tente falar novamente.")
            play_chime()
            return speech_to_text()
        except sr.UnknownValueError:
            text_to_speech("Não consegui entender. Pode repetir?")
            play_chime()
            return speech_to_text()
        except KeyboardInterrupt:
            text_to_speech("Interrompido. Tente novamente.")
            play_chime()
            return speech_to_text()
        except Exception as e:
            text_to_speech("Erro no reconhecimento. Tente novamente.")
            play_chime()
            return speech_to_text()