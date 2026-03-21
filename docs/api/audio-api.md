# API de Áudio — TTS, SFX e STT

## Google Cloud Text-to-Speech

### Configuração
```python
from google.cloud import texttospeech

client = texttospeech.TextToSpeechClient()
```

Requer `GOOGLE_APPLICATION_CREDENTIALS` apontando para um JSON de service account com permissões na Cloud TTS API.

### Síntese de Voz
```python
synthesis_input = texttospeech.SynthesisInput(text=texto)

voice = texttospeech.VoiceSelectionParams(
    language_code="pt-BR",
    name="pt-BR-Neural2-A",  # Feminino (narradora)
    # name="pt-BR-Neural2-B"  # Masculino (mestre)
    ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
)

audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.LINEAR16,
    sample_rate_hertz=22050,
    speaking_rate=1.5
)

response = client.synthesize_speech(
    input=synthesis_input,
    voice=voice,
    audio_config=audio_config
)

# Salvar e reproduzir
with open("temp_audio.mp3", "wb") as f:
    f.write(response.audio_content)

pygame.mixer.music.load("temp_audio.mp3")
pygame.mixer.music.play()
while pygame.mixer.music.get_busy():
    pygame.time.wait(100)
```

### Custo
- Vozes Neural2: $16 por 1 milhão de caracteres
- Vozes Standard: $4 por 1 milhão de caracteres
- Primeiro 1M chars/mês: gratuito

---

## pyttsx3 (Fallback Local)

### Configuração
```python
import pyttsx3

engine = pyttsx3.init()
engine.setProperty('rate', 180)   # Palavras por minuto
engine.setProperty('volume', 0.9) # 0.0 a 1.0

# Tentar configurar voz em português
voices = engine.getProperty('voices')
for voice in voices:
    if 'pt' in voice.id.lower() or 'brazil' in voice.name.lower():
        engine.setProperty('voice', voice.id)
        break
```

### Síntese
```python
engine.say(texto)
engine.runAndWait()
```

### Limitações
- Qualidade muito inferior ao Google Cloud TTS
- Vozes em português podem não estar disponíveis em todos os sistemas
- Não suporta ajuste de velocidade com a mesma naturalidade

---

## ElevenLabs (Premium Opcional)

### Configuração
```python
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = config.get("elevenlabs", {}).get("voice_id", "21m00Tcm4TlvDq8ikWAM")
```

### Síntese via HTTP
```python
url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"

headers = {
    "Accept": "audio/mpeg",
    "Content-Type": "application/json",
    "xi-api-key": ELEVENLABS_API_KEY
}

data = {
    "text": texto,
    "model_id": "eleven_multilingual_v2",
    "voice_settings": {
        "stability": 0.5,
        "similarity_boost": 0.75
    }
}

response = requests.post(url, json=data, headers=headers)

# Stream para pygame
audio_stream = io.BytesIO(response.content)
pygame.mixer.music.load(audio_stream)
pygame.mixer.music.play()
```

### Custo
- Starter: $5/mês (30.000 chars)
- Creator: $22/mês (100.000 chars)

---

## pygame.mixer — Engine de SFX

### Inicialização
```python
import pygame

pygame.mixer.init(
    frequency=22050,    # Taxa de amostragem Hz
    size=-16,           # 16-bit signed
    channels=2,         # Estéreo
    buffer=512          # Buffer pequeno = baixa latência
)
```

### Reprodução de SFX
```python
# Carrega e toca (sem bloquear)
sound = pygame.mixer.Sound("sons/sistema/arquivo.mp3")
sound.play()

# Para controle de volume
sound.set_volume(0.7)
sound.play()
```

### Reprodução de TTS (bloqueia até terminar)
```python
pygame.mixer.music.load("temp_narration.mp3")
pygame.mixer.music.play()

while pygame.mixer.music.get_busy():
    pygame.time.wait(100)  # Poll a cada 100ms
```

---

## Google Speech Recognition (STT)

### Configuração
```python
import speech_recognition as sr

recognizer = sr.Recognizer()
```

### Captura e Reconhecimento
```python
with sr.Microphone() as source:
    print("🎙️ Ouvindo...")
    recognizer.adjust_for_ambient_noise(source, duration=1)

    try:
        audio = recognizer.listen(source, timeout=10)
        texto = recognizer.recognize_google(audio, language="pt-BR")
        return texto
    except sr.WaitTimeoutError:
        return None
    except sr.UnknownValueError:
        print("Não entendi. Tente novamente ou use o teclado.")
        return None
    except sr.RequestError as e:
        print(f"Erro de conexão: {e}. Use o teclado.")
        return None
```

### Limitações
- Requer conexão com internet (Google Speech API)
- Funciona melhor em ambiente silencioso
- Pode ter dificuldade com nomes fantásticos/inventados

---

## Comparativo de Provedores TTS

| Aspecto            | Google Cloud TTS     | pyttsx3            | ElevenLabs          |
|--------------------|---------------------|---------------------|---------------------|
| Qualidade          | ★★★★★               | ★★☆☆☆               | ★★★★★               |
| Custo              | $4-16/1M chars       | Gratuito            | $5-22/mês           |
| Latência           | ~500ms               | ~100ms              | ~800ms              |
| Offline            | Não                  | Sim                 | Não                 |
| Idiomas            | 40+                  | Depende do SO       | 29+                 |
| Vozes pt-BR        | Neural2-A/B          | Depende do SO       | Multilingual v2     |
| Velocidade custom  | Sim (1.5x)           | Sim (rate)          | Sim                 |
| **Uso recomendado**| **Principal**        | **Fallback**        | **Alternativa**     |
