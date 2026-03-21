# audio_manager.py — Sistema de Áudio

## Visão Geral

Módulo responsável por toda saída e entrada de áudio da plataforma. Abstrai três provedores de TTS com fallback automático, reprodução de SFX via pygame e reconhecimento de voz.

---

## Arquitetura do Módulo

```
AudioManager
│
├── TTS (Text-to-Speech)
│   ├── Provedor 1: Google Cloud TTS (pt-BR Neural, $4/1M chars)
│   ├── Provedor 2: pyttsx3 (local, offline, gratuito)
│   └── Provedor 3: ElevenLabs (premium, $22/1M chars)
│
├── SFX (Sound Effects)
│   └── pygame.mixer + arquivos MP3 em sons/sistema/
│
└── STT (Speech-to-Text)
    └── SpeechRecognition + Google Speech API
```

---

## Funções Principais

### `text_to_speech(texto, tipo_voz="narrador")`
Função central de TTS com cadeia de fallback automática.

**Parâmetro `tipo_voz`:**
- `"narrador"` → voz feminina (`pt-BR-Neural2-A`)
- `"mestre"` → voz masculina (`pt-BR-Neural2-B`)

**Configuração de voz (Google Cloud TTS):**
```python
voice_config = {
    "language_code": "pt-BR",
    "name": "pt-BR-Neural2-A",  # ou Neural2-B
    "ssml_gender": FEMALE  # ou MALE
}

audio_config = {
    "audio_encoding": LINEAR16,
    "sample_rate_hertz": 22050,
    "speaking_rate": 1.5  # 50% mais rápido
}
```

---

### `narrator_speech(texto)`
Narração com voz feminina. Usada para:
- Introdução da plataforma
- Contos Interativos
- Mensagens do sistema

```python
narrator_speech(texto) → text_to_speech(texto, tipo_voz="narrador")
```

---

### `master_speech(texto)`
Narração com voz masculina. Usada para:
- Narrativa do Mestre do RPG
- Eventos dramáticos do jogo

```python
master_speech(texto) → text_to_speech(texto, tipo_voz="mestre")
```

---

### `play_sfx(keyword)`
Reproduz efeito sonoro baseado em uma palavra-chave.

**Mapeamento completo:**

| Keyword    | Arquivo MP3                                   | Contexto                     |
|------------|-----------------------------------------------|------------------------------|
| `corvo`    | `creepy-crow-caw-322991.mp3`                  | Aparição de corvo singular   |
| `crows`    | `crows-6371.mp3`                              | Bando de corvos              |
| `village`  | `medieval_village_atmosphere-79282.mp3`       | Cenas em cidades/vilas       |
| `town`     | `people-talking-in-the-old-town.mp3`          | Multidão urbana              |
| `tavern`   | `tavern_ambience_inside_laughter-73008.mp3`   | Interior de taverna          |
| `rain`     | `Rain-on-city-deck.mp3`                       | Chuva, tempestade            |
| `scream`   | `scream-of-terror-325532.mp3`                 | Gritos, terror               |
| `coin`     | `coin-recieved.mp3`                           | Transações, recompensas      |
| `crianca`  | `rianca_correndo.mp3`                         | Criança correndo             |
| `familiar1`| `familiar_sound.mp3`                          | Som familiar/memorável       |
| `familiar2`| `familiar_sound2.mp3`                         | Sussurro da praga            |
| `familiar3`| `familiar_sound3.mp3`                         | Terceira variante familiar   |
| `chime`    | `chime-2-356833.mp3`                          | Sistema pronto para input    |
| `logo`     | `logo-sfx-316751.mp3`                         | Abertura da plataforma       |
| `fome`     | `fome.mp3`                                    | Fome/sobrevivência           |

**Implementação:**
```python
def play_sfx(keyword):
    arquivo = SFX_MAP.get(keyword)
    if arquivo and os.path.exists(arquivo):
        sound = pygame.mixer.Sound(arquivo)
        sound.play()
```

---

### `play_chime()`
Toca o som de "chime" indicando que o sistema está pronto para receber input.
Usado ao final de cada turno, após a narração completa.

---

### `play_ressoar_opening_sequence()`
Reproduz a sequência completa de abertura da plataforma:
1. Logo SFX (`logo-sfx-316751.mp3`)
2. Narração da introdução (voz feminina)
3. Explicação dos dois modos

**Texto narrado:**
> "Bem-vindo à Plataforma Ressoar, onde histórias ganham voz e mundos ganham vida. Aqui, sua imaginação encontrará um narrador sempre pronto..."

---

### `speech_to_text() → str`
Captura áudio do microfone e converte para texto via Google Speech Recognition.

**Configuração:**
```python
recognizer = sr.Recognizer()
with sr.Microphone() as source:
    recognizer.adjust_for_ambient_noise(source)
    audio = recognizer.listen(source)
    text = recognizer.recognize_google(audio, language="pt-BR")
```

**Tratamento de erros:**
- `sr.UnknownValueError` → "Não entendi, tente novamente"
- `sr.RequestError` → "Erro de conexão, use o teclado"

---

## Inicialização

```python
import pygame
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
```

A inicialização acontece uma vez no início do programa. O mixer permanece ativo durante toda a sessão.

---

## Tratamento de Erros de Áudio

O módulo usa try/except em todos os pontos de integração:

```
Google Cloud TTS falha → log silencioso → tenta pyttsx3
pyttsx3 falha → log silencioso → tenta ElevenLabs
ElevenLabs falha → log silencioso → sem áudio (só texto)
pygame falha → log silencioso → continua sem SFX
Microfone falha → solicita input de teclado
```

A plataforma nunca quebra por falha de áudio — sempre tem fallback textual.

---

## Arquivos de Áudio

Todos em `sons/sistema/`:

```
sons/sistema/
├── chime-2-356833.mp3              (0.5s — indicador de prontidão)
├── coin-recieved.mp3               (1.5s — transação/recompensa)
├── creepy-crow-caw-322991.mp3      (2s — corvo singular)
├── crows-6371.mp3                  (3s — bando de corvos)
├── fome.mp3                        (2s — som de fome)
├── logo-sfx-316751.mp3             (3s — abertura da plataforma)
├── medieval_village_atmosphere-79282.mp3  (loop — atmosfera de vila)
├── people-talking-in-the-old-town-city-center.mp3  (loop — multidão)
├── Rain-on-city-deck.mp3           (loop — chuva)
├── rianca_correndo.mp3             (2s — criança correndo)
├── scream-of-terror-325532.mp3     (2s — grito)
├── tavern_ambience_inside_laughter-73008.mp3  (loop — taverna)
├── familiar_sound.mp3              (3s — som familiar/memorável)
├── familiar_sound2.mp3             (3s — sussurro da praga)
└── familiar_sound3.mp3             (3s — terceira variante)
```

---

## Configuração de Vozes

| Voz          | Código Google TTS    | Gênero    | Uso                        |
|--------------|----------------------|-----------|----------------------------|
| Narradora    | `pt-BR-Neural2-A`    | Feminino  | Intro, contos, sistema     |
| Mestre       | `pt-BR-Neural2-B`    | Masculino | Narrativa RPG              |

**Por que Neural2?** São as vozes mais naturais do Google Cloud TTS, com prosódia muito superior às vozes Standard, fundamentais para a imersão da plataforma.

**Por que 1.5x de velocidade?** Narração de jogos precisa ser dinâmica. Velocidade normal soa muito lenta para interações de RPG.
