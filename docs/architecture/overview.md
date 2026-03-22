# Visão Geral da Arquitetura

## Conceito

A Plataforma Ressoar é uma plataforma de narrativa interativa que combina:
- **IA Generativa** (OpenAI GPT-4o-mini) como narrador/mestre inteligente
- **Text-to-Speech** neural em Português Brasileiro
- **Efeitos sonoros contextuais** disparados automaticamente pela narrativa
- **Dois modos de jogo** com lógicas distintas mas mesma infraestrutura

---

## Arquitetura de Alto Nível

```
┌────────────────────────────────────────────────────────────────┐
│                        PLATAFORMA RESSOAR                      │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────┐          ┌──────────────────────────────┐   │
│  │   ENTRADA    │          │         SAÍDA                │   │
│  │              │          │                              │   │
│  │  Teclado     │          │  Texto no Terminal           │   │
│  │  Microfone   │          │  Narração TTS (voz)          │   │
│  │  (Voz)       │          │  Efeitos Sonoros             │   │
│  └──────┬───────┘          └──────────────┬───────────────┘   │
│         │                                 │                   │
│  ┌──────▼──────────────────────────────── ▼──────────────┐    │
│  │                    game.py                            │    │
│  │              (Motor Principal)                        │    │
│  │                                                       │    │
│  │   ┌─────────────┐      ┌──────────────────────────┐  │    │
│  │   │  Modo RPG   │      │   Modo Conto Interativo  │  │    │
│  │   │             │      │                          │  │    │
│  │   │ new_game_   │      │ interactive_story_loop() │  │    │
│  │   │    loop()   │      │                          │  │    │
│  │   └──────┬──────┘      └────────────┬─────────────┘  │    │
│  └──────────┼──────────────────────────┼────────────────┘    │
│             │                          │                      │
│  ┌──────────▼──────────┐  ┌────────────▼──────────────┐      │
│  │ world_state_manager │  │    campaign_manager.py    │      │
│  │                     │  │                           │      │
│  │  - Estado do mundo  │  │  - Selecionar campanha    │      │
│  │  - Estado do player │  │  - Carregar arquivos      │      │
│  │  - Persistência     │  │  - Configurações          │      │
│  │  - AI Archivista    │  │                           │      │
│  └─────────────────────┘  └───────────────────────────┘      │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐     │
│  │                   audio_manager.py                   │     │
│  │                                                      │     │
│  │    TTS Chain:  Google Cloud TTS → pyttsx3            │     │
│  │    SFX:        pygame + arquivo MP3                  │     │
│  │    STT:        Google Speech Recognition             │     │
│  └──────────────────────────────────────────────────────┘     │
│                                                               │
└────────────────────────────────────────────────────────────────┘
          │                                │
          ▼                                ▼
┌──────────────────┐            ┌──────────────────────┐
│   OpenAI API     │            │  Google Cloud TTS    │
│  GPT-4o-mini     │            │  (pt-BR Neural)      │
│                  │            │                      │
│  - Game Master   │            │  Whisper STT         │
│  - Story Master  │            │  pyttsx3 (fallback)  │
│  - Archivista    │            └──────────────────────┘
│  - Olhos do Jog. │
└──────────────────┘
```

---

## Camadas da Arquitetura

### Camada 1: Interface de Usuário
Responsável por capturar entrada (texto/voz) e exibir saída (texto/áudio).

- `input()` nativo do Python para entrada de texto
- `SpeechRecognition` + `pyaudio` para entrada de voz
- `print()` para output textual
- `audio_manager.py` para output em áudio

### Camada 2: Motor de Jogo (`game.py`)
Orquestra todos os sistemas, contém os dois loops principais:
- `new_game_loop()` — loop do modo RPG
- `interactive_story_loop()` — loop do modo conto

Responsabilidades:
- Roteamento entre modos
- Validação de ações do jogador
- Disparo de efeitos sonoros contextuais
- Parsing de comandos especiais (`inventário`, `status`, `chikito`)
- Construção de prompts para IA

### Camada 3: Gerenciadores de Domínio
- **`world_state_manager.py`**: Persiste e atualiza o estado do RPG
- **`campaign_manager.py`**: Carrega e gerencia dados das campanhas

### Camada 4: Sistema de Áudio (`audio_manager.py`)
Abstrai toda saída de áudio:
- TTS com cadeia de fallback
- Reprodução de SFX/MP3
- Captura de voz

### Camada 5: Serviços Externos
- **Google Gemini API**: Geração de narrativa com IA
- **Google Cloud TTS**: Síntese de voz neural
- **Google Speech Recognition**: Reconhecimento de voz

---

## Separação de Responsabilidades

| Arquivo                  | Responsabilidade                                           |
|--------------------------|-------------------------------------------------------------|
| `game.py`               | Orquestração, loops de jogo, lógica de negócio              |
| `audio_manager.py`      | Toda saída/entrada de áudio (TTS, SFX, STT)                 |
| `world_state_manager.py`| Persistência e mutação do estado do mundo RPG               |
| `campaign_manager.py`   | Leitura e fornecimento de dados de campanha                 |
| `config.json`           | Configuração declarativa das campanhas                      |
| `estado_do_mundo.json`  | Arquivo de save — estado serializado do jogo atual          |

---

## Decisões Arquiteturais Chave

### 1. Estado Centralizado
Todo o estado do jogo RPG vive em um único dicionário (`world_state`) serializado em JSON. Isso simplifica:
- Persistência (um arquivo)
- Troca de contexto com a IA (um objeto)
- Debug e inspeção manual

### 2. AI como Serviço de Narrativa
A IA não controla a lógica — ela só gera texto narrativo. A lógica de validação, inventário, e triggers fica no Python, garantindo consistência.

### 3. Quatro Personas de IA Especializadas
- **Mestre** (`get_gm_narrative`): Narrador open-world do RPG — voz masculina
- **Mestre dos Contos** (`get_story_master_narrative`): Adaptador literário estruturado
- **Archivista** (`update_world_state`): Extrator silencioso de estado — nunca fala com o jogador
- **Olhos do Jogador** (`get_player_eyes_response`): HUD narrativo para consultas de inspeção — voz feminina, tempo do jogo não avança

### 4. Sistema de Gatilhos Progressivo
Narrativa dinâmica via gatilhos com probabilidade crescente (30% base + 10%/rodada), evitando longos períodos sem eventos dramáticos.

### 5. Validação Semântica de Ações
O jogador só pode interagir com objetos explicitamente mencionados na narração atual. Isso mantém a coerência narrativa e impede "soluções mágicas".
