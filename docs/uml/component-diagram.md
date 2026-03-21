# Diagrama de Componentes

## Componentes do Sistema

```mermaid
graph TB
    subgraph UI["Interface do Usuário"]
        TXT[Terminal / stdout]
        MIC[Microfone]
        SPK[Caixas de Som]
        KBD[Teclado]
    end

    subgraph CORE["Motor Principal — game.py"]
        GM[GameEngine]
        RPG[new_game_loop]
        STORY[interactive_story_loop]
        VAL[Validador de Ações]
        SFX_T[SFX Trigger Engine]
        CMD[Processador de Comandos]
    end

    subgraph STATE["Gerenciamento de Estado — world_state_manager.py"]
        WSM[WorldStateManager]
        PERSIST[Persistência JSON]
        ARCH[AI Archivista]
    end

    subgraph CAMPAIGN["Gerenciamento de Campanha — campaign_manager.py"]
        CM[CampaignManager]
        CFG[config.json]
        NPC_F[npcs.json]
        LOC_F[locais.json]
        ITEMS_F[itens_*.json]
        CAMP_F[campanha.md]
    end

    subgraph AUDIO["Sistema de Áudio — audio_manager.py"]
        AM[AudioManager]
        TTS[TTS Engine]
        SFX_P[SFX Player]
        STT[STT Engine]
    end

    subgraph AI_EXT["APIs de IA — Externas"]
        GEMINI[Google Gemini 1.5-Flash]
    end

    subgraph AUDIO_EXT["APIs de Áudio — Externas"]
        GCTTS[Google Cloud TTS]
        EL[ElevenLabs]
        PYTTS[pyttsx3 local]
        GSTT[Google Speech API]
    end

    subgraph DATA["Dados Persistidos"]
        SAVE[estado_do_mundo.json]
        STORIES[contos_interativos/]
        SOUNDS[sons/sistema/*.mp3]
    end

    KBD --> GM
    MIC --> STT
    STT --> GM
    GM --> TXT
    GM --> AM

    GM --> RPG
    GM --> STORY
    RPG --> VAL
    RPG --> SFX_T
    RPG --> CMD
    RPG --> WSM
    STORY --> WSM

    VAL --> WSM
    SFX_T --> AM
    CMD --> TXT

    WSM --> PERSIST
    WSM --> ARCH
    PERSIST --> SAVE
    ARCH --> GEMINI

    GM --> CM
    CM --> CFG
    CM --> NPC_F
    CM --> LOC_F
    CM --> ITEMS_F
    CM --> CAMP_F

    RPG --> GEMINI
    STORY --> GEMINI

    AM --> TTS
    AM --> SFX_P
    AM --> STT

    TTS --> GCTTS
    TTS --> PYTTS
    TTS --> EL
    STT --> GSTT

    SFX_P --> SOUNDS
    TXT --> SPK
    AM --> SPK

    STORY --> STORIES
```

---

## Diagrama de Dependências entre Módulos

```
game.py
  ├── audio_manager.py
  │     ├── google.cloud.texttospeech
  │     ├── pygame
  │     ├── speech_recognition
  │     ├── pyaudio
  │     ├── pyttsx3
  │     └── requests (ElevenLabs)
  │
  ├── world_state_manager.py
  │     ├── google.generativeai (Archivista)
  │     └── json (persistência)
  │
  ├── campaign_manager.py
  │     └── json (leitura de dados)
  │
  ├── google.generativeai (Mestre RPG + Mestre Contos)
  └── python-dotenv
```

---

## Diagrama de Deployment

```
┌────────────────────────────────────────────────────────────────────┐
│                    MÁQUINA LOCAL DO USUÁRIO                        │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Python Runtime 3.8+                       │  │
│  │                                                              │  │
│  │  game.py ←──────────── audio_manager.py                     │  │
│  │    │                                                         │  │
│  │    ├── world_state_manager.py                                │  │
│  │    └── campaign_manager.py                                   │  │
│  │                                                              │  │
│  │  Arquivos de dados (JSON, TXT, MP3):                        │  │
│  │  campanhas/*, contos_interativos/*, sons/sistema/*           │  │
│  │  estado_do_mundo.json (save file)                            │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  Hardware: Microfone, Caixas de Som, Teclado, Terminal             │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ HTTPS
                               │
          ┌────────────────────┼─────────────────────┐
          │                    │                     │
          ▼                    ▼                     ▼
┌──────────────────┐  ┌────────────────┐  ┌──────────────────────┐
│  Google Gemini   │  │ Google Cloud   │  │    Google Speech     │
│  API             │  │ TTS API        │  │    Recognition API   │
│                  │  │                │  │                      │
│  generativelang  │  │  texttospeech  │  │  speech.googleapis   │
│  uage.googleapis │  │  .googleapis   │  │                      │
└──────────────────┘  └────────────────┘  └──────────────────────┘
```

---

## Componentes por Responsabilidade

| Componente               | Arquivo                    | Tipo        |
|--------------------------|----------------------------|-------------|
| Motor de Jogo            | `game.py`                  | Orquestrador|
| Sistema de Áudio         | `audio_manager.py`         | Serviço     |
| Gerenciador de Estado    | `world_state_manager.py`   | Repositório |
| Gerenciador de Campanha  | `campaign_manager.py`      | Repositório |
| IA Mestre RPG            | Gemini (via game.py)       | Externo     |
| IA Mestre Contos         | Gemini (via game.py)       | Externo     |
| IA Archivista            | Gemini (via WSM)           | Externo     |
| TTS Principal            | Google Cloud TTS           | Externo     |
| TTS Fallback             | pyttsx3                    | Local       |
| STT                      | Google Speech API          | Externo     |
| SFX Engine               | pygame.mixer               | Local       |
| Dados de Campanha        | `campanhas/*/`             | Dados       |
| Dados de Contos          | `contos_interativos/`      | Dados       |
| Efeitos Sonoros          | `sons/sistema/*.mp3`       | Dados       |
| Save do Jogo             | `estado_do_mundo.json`     | Dados       |
| Configuração             | `config.json`              | Configuração|
| Variáveis de Ambiente    | `.env`                     | Configuração|
