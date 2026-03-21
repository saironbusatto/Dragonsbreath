# Fluxo de Dados

## Fluxo Completo — Modo RPG

```
Jogador digita/fala ação
         │
         ▼
┌─────────────────────────┐
│  Captura de Entrada     │
│  text input OU          │
│  speech_to_text()       │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐      ┌──────────────────────┐
│  Comando especial?       ├─YES─►│  Executar comando    │
│  inventario/status/      │      │  (sem chamar IA)     │
│  chikito/               │      └──────────────────────┘
└──────────┬──────────────┘
           │ NO
           ▼
┌─────────────────────────┐
│  Extrair objetos da     │
│  ação do jogador        │
│  extract_objects_       │
│  from_action()          │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐      ┌──────────────────────────────┐
│  Validar ação           ├─FAIL─►│  Narrar erro amigável        │
│  validate_player_       │       │  "Esse objeto não está aqui" │
│  action()               │       └──────────────────────────────┘
└──────────┬──────────────┘
           │ OK
           ▼
┌─────────────────────────┐
│  Verificar gatilhos     │
│  da localização atual   │
│  P = 30% + 10% × rodadas│
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────┐
│  Construir prompt para Gemini                           │
│                                                         │
│  - Estado do mundo atual (world_state)                  │
│  - Dados da campanha (NPCs, locais, itens)              │
│  - Classe e inventário do personagem                    │
│  - Ação do jogador                                      │
│  - Gatilhos ativos (se houver)                          │
│  - Resumo de eventos recentes                           │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │  Gemini API    │
              │  1.5-Flash     │
              │                │
              │  (Mestre do    │
              │   Jogo)        │
              └───────┬────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│  Resposta narrativa do Mestre                           │
│                                                         │
│  [STATUS_UPDATE: hp=15]  ← parseado pelo game.py       │
│  [INVENTORY_UPDATE: +item] ← parseado pelo game.py     │
│  Narração da cena...                                    │
│  "O que você faz?"                                      │
└─────────┬───────────────────────────────────────────────┘
          │
          ├──────────────────────────────────────────────────────┐
          │                                                       │
          ▼                                                       ▼
┌──────────────────────┐                          ┌──────────────────────────┐
│  trigger_contextual  │                          │  narrator_speech()       │
│  _sfx()              │                          │                          │
│                      │                          │  Google Cloud TTS        │
│  Analisa texto →     │                          │  → pyttsx3 (fallback)    │
│  dispara MP3s        │                          │                          │
│  correspondentes     │                          │  Lê em voz alta          │
└──────────────────────┘                          └──────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│  update_world_state()                                   │
│                                                         │
│  Envia narrativa + estado para Gemini (Archivista)      │
│  → Extrai interactable_elements_in_scene               │
│  → Atualiza NPCs na cena                               │
│  → Atualiza localização                                │
│  → Atualiza eventos recentes                           │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │  save_world_   │
              │  state()       │
              │                │
              │  → estado_do_  │
              │    mundo.json  │
              └───────┬────────┘
                      │
                      ▼
              ┌────────────────┐
              │  play_chime()  │
              │  (pronto para  │
              │   próxima ação)│
              └────────────────┘
```

---

## Fluxo Completo — Modo Conto Interativo

```
Seleção do conto
     │
     ▼
┌──────────────────────────────────────┐
│  Carregar arquivos                   │
│  {conto}.txt → texto original        │
│  {conto}_eventos.json → mapa eventos │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Inicializar variáveis dinâmicas     │
│  ex.: sanidade=5, esperanca=5...     │
│  current_evento = "inicio"           │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐         ┌─────────────────────┐
│  Carregar evento atual do mapa       │         │  Evento é "final_*"?│
│  eventos["current_evento"]           ├──YES───►│  Mostrar estatísticas│
└──────────────┬───────────────────────┘         │  Encerrar           │
               │ NO                              └─────────────────────┘
               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Construir prompt Story Master                                  │
│                                                                 │
│  - Texto original completo (referência de estilo)              │
│  - Mapa de eventos                                              │
│  - Evento atual + opções disponíveis                           │
│  - Variáveis dinâmicas atuais                                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
                      ┌────────────────┐
                      │  Gemini API    │
                      │  (Story Master)│
                      └───────┬────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Narrativa + Choices                                         │
│                                                              │
│  "O homem sentou-se e contemplou o silêncio..."             │
│                                                              │
│  (A) Tentar falar com a visão                               │
│  (B) Fechar os olhos e rezar                                │
│  (C) Sair do quarto                                         │
└──────────────────────────────────────────────────────────────┘
          │
          ├──────────────────────────────────────────────────────┐
          │                                                       │
          ▼                                                       ▼
┌──────────────────────┐                          ┌──────────────────────────┐
│  trigger_contextual  │                          │  narrator_speech()       │
│  _sfx()              │                          │  (lê narrativa em voz)   │
│  (sons ambientes)    │                          └──────────────────────────┘
└──────────────────────┘
          │
          ▼
┌──────────────────────────────┐
│  Aguardar input do jogador   │
│  "A", "B" ou "C"             │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│  Processar escolha                                           │
│                                                              │
│  opcao_escolhida["efeito"] → aplicar em variáveis           │
│  ex.: sanidade -= 1, esperanca += 1                         │
│                                                              │
│  opcao_escolhida["proximo_evento"] → avançar no mapa        │
└──────────────────────────────────────────────────────────────┘
               │
               ▼
        (retorna ao loop)
```

---

## Fluxo de Dados do Estado do Mundo

```
estado_do_mundo.json
        │
        ▼
┌─────────────────────────────────────────┐
│              world_state dict           │
│                                         │
│  player_character                       │
│  ├── name                               │
│  ├── class                              │
│  ├── current_act                        │
│  ├── status (hp, max_hp)               │
│  ├── max_slots                          │
│  ├── inventory [...]                    │
│  └── desejo                             │
│                                         │
│  world_state                            │
│  ├── current_location_key              │
│  ├── immediate_scene_description       │
│  ├── active_quests {}                  │
│  ├── important_npcs_in_scene {}        │
│  ├── recent_events_summary [...]       │
│  ├── gatilhos_ativos {}               │
│  ├── gatilhos_usados {}               │
│  └── interactable_elements_in_scene [] │
│                                         │
│  game_mode: "rpg" | "story"            │
│  rodadas_sem_gatilho: int              │
└─────────────────────────────────────────┘
        │
        │  (passado como contexto para)
        ▼
┌─────────────────────────────────────────┐
│            Gemini Prompts               │
│                                         │
│  Mestre: usa world_state + ação        │
│  Archivista: atualiza world_state      │
└─────────────────────────────────────────┘
```

---

## Fluxo do Sistema de Áudio

```
Texto para narrar
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│                   text_to_speech()                       │
│                                                         │
│   1. Tentar Google Cloud TTS                            │
│      └─ Sucesso? → reproduzir audio                    │
│      └─ Falha? → tentar próximo                        │
│                                                         │
│   2. Tentar pyttsx3 (local, offline)                   │
│      └─ Sucesso? → reproduzir audio                    │
│      └─ Falha? → tentar próximo                        │
│                                                         │
│   3. ElevenLabs (se configurado)                       │
│      └─ Sucesso? → reproduzir audio                    │
│      └─ Falha? → só imprimir texto                     │
└─────────────────────────────────────────────────────────┘

Narrativa do Mestre
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│              trigger_contextual_sfx()                    │
│                                                         │
│   Analisa texto por palavras-chave:                    │
│   "corvo" → sons/sistema/creepy-crow-caw.mp3           │
│   "taverna" → sons/sistema/tavern_ambience.mp3         │
│   "chuva" → sons/sistema/Rain-on-city-deck.mp3         │
│   "grito" → sons/sistema/scream-of-terror.mp3          │
│   ...                                                   │
│                                                         │
│   pygame.mixer.Sound(arquivo).play()                   │
└─────────────────────────────────────────────────────────┘
```
