**English** · [Português (BR)](README.pt-BR.md)

# Ressoar Platform

Interactive storytelling platform with generative AI, neural voice narration and contextual sound effects. Two game modes: open-world RPG and Interactive Tales based on classic literature.

---

## Game Modes

### RPG Mode

Open-world adventure where the player freely writes what their character does. An AI Game Master (Gemini) responds with consequential narratives, respecting world state, inventory and the limitations of the chosen class.

- Semantic validation system — you can only interact with objects present in the current scene
- Inventory with slots (capacity by weight, not by quantity)
- Narrative triggers with increasing probability, ensuring dynamism
- **Narrative Mood** system per turn (`combat`, `tense`, `dramatic`, `sad`, `relief`, `normal`) that changes narration style and TTS speed
- Persistent state saved automatically every turn

**Available campaigns:**

- **O Lamento do Bardo** (The Bard's Lament) — gothic narrative about loss, illusion and the power of music (class: Bard)
- **A Busca pelo Cristal Perdido** (The Quest for the Lost Crystal) — classic fantasy adventure (class: Adventurer)
- **Curse of Strahd — O Vale das Sombras** (The Valley of Shadows) — gothic horror in Barovia, with an ancestral curse and a showdown against Strahd (class: Adventurer)

### Interactive Tales Mode

Adaptations of classic literary works with branching choices (A/B/C) that influence dynamic variables and determine the story's ending. The AI narrates using the original author's style and vocabulary.

**Available tales:**

- **The Raven** (Edgar Allan Poe) — 4 possible endings, variables: sanity, hope, obsession, acceptance

---

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your API keys

# Run
python game.py
```

---

## Required APIs

| API | Required | Use |
| --- | --- | --- |
| [Google Gemini](https://ai.google.dev/) | Yes | AI narration (Game Master, Story Master, Archivist) |
| [Google Cloud TTS](https://cloud.google.com/text-to-speech) | Recommended | Neural pt-BR voice (~$4/1M chars) |
| [ElevenLabs](https://elevenlabs.io/) | No | Alternative premium TTS (~$22/1M chars) |

```env
GEMINI_API_KEY=your_key_here
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_CLOUD_PROJECT=your-project-id
ELEVENLABS_API_KEY=your_key_here  # optional
```

If no TTS is configured, the platform works normally and displays text only.

---

## Commands

### RPG Mode Commands

| Command | Action |
| --- | --- |
| `inventário` (inventory) | Shows items and used/total slots |
| `status` / `saúde` / `vida` (health) | Shows current and max HP |
| `chikito` | Saves and exits |
| Any other input | Sent as an action to the Game Master |

### Tale Mode Commands

| Command | Action |
| --- | --- |
| `A`, `B` or `C` | Chooses among the narrative options |

---

## Project Structure

```text
Dragonsbreath/
├── game.py                     # Main engine — game loops and business logic
├── audio_manager.py            # TTS, SFX and voice recognition
├── world_state_manager.py      # RPG world state and AI Archivist
├── campaign_manager.py         # Campaign data loading
├── config.json                 # Declarative campaign configuration
├── .env.example                # Environment variable template
├── requirements.txt            # Python dependencies
├── test_plataforma_ressoar.py  # Platform verification tests
├── estado_do_mundo.json        # Automatic save game (generated at runtime)
├── campanhas/
│   ├── lamento_do_bardo/       # NPCs, locations, items and narrative of the gothic campaign
│   ├── exemplo_fantasia/       # NPCs, locations, items and narrative of the classic campaign
│   └── curse_of_strahd/        # NPCs, locations, items and narrative of the gothic horror campaign
├── contos_interativos/
│   ├── o_corvo_poe.txt         # Original reference text (author's style)
│   └── o_corvo_poe_eventos.json # Event map, choices and dynamic variables
├── sons/sistema/               # 15 MP3 sound effects triggered contextually
└── docs/                       # Complete technical documentation
```

---

## Technology Stack

- **Python 3.8+**
- **Google Gemini 1.5-Flash** — AI narration (3 personas: Game Master, Story Master, Archivist)
- **Google Cloud TTS** — neural pt-BR voices (Neural2-A female / Neural2-B male, 1.5x speed)
- **pygame** — audio playback engine
- **SpeechRecognition + pyaudio** — voice input
- **pyttsx3** — local offline TTS (automatic fallback)

---

## Tests

```bash
python test_plataforma_ressoar.py
```

Checks file structure, campaign settings, tale integrity and function imports.

---

## Technical Documentation

The [docs/](docs/README.md) folder contains the complete system documentation:

- [Architecture overview](docs/architecture/overview.md)
- [Data flow](docs/architecture/data-flow.md)
- [UML class diagram](docs/uml/class-diagram.md)
- [Sequence diagrams](docs/uml/sequence-diagrams.md)
- [State diagrams](docs/uml/state-diagrams.md)
- [System entities](docs/entities/entities.md)
- [AI integration](docs/api/ai-integration.md)

---

## Troubleshooting

**`GEMINI_API_KEY` not configured**
Set the key in the `.env` file. Without it the platform cannot generate narratives.

**`ModuleNotFoundError`**
Run `pip install -r requirements.txt` to install all dependencies.

**No audio / TTS error**
The platform works without audio — check `.env` if you want to enable TTS. The text fallback is automatic.

**Microphone not recognized**
Install `pyaudio` and check the device drivers. Keyboard input works normally without a microphone.

---

*Ressoar Platform — where every sound tells a unique story.*
