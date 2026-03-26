# game.py — Motor Principal

## Visão Geral

`game.py` é o coração da plataforma. Contém ~1.277 linhas e orquestra todos os subsistemas, implementa os dois loops de jogo e toda a lógica de negócio.

---

## Atualizações Recentes (Curse of Strahd — Fases 1-7)

Principais evoluções incorporadas ao módulo:

- Prompt v2 do Mestre com contrato narrativo cinematográfico e brevidade forçada.
- Sistema de combate com `combat_state` e gatilho `[HDYWDTDT]` para finalizações relevantes.
- Sistema de ritmo emocional com `emotional_pacing` e alívio forçado após tensão prolongada.
- Tag `[PAUSE_BEAT]` tratada no backend para pausa dramática em áudio.
- Fluxo de ressurreição baroviana:
  - limbo ao chegar em `hp == 0`;
  - oferenda emocional;
  - DC progressiva (12/15/18);
  - persistência de `death_count`, `resurrection_flaws` e `alignment`.
- Ajustes para coerência de classe (vantagem/desvantagem contextual no Shadowdark).

Referência detalhada por fase:
- `docs/campaigns/curse-of-strahd-evolucao-fases.md`

---

## Funções Principais

### `main()`
**Ponto de entrada do programa.**

```
main()
  ├── Verificar estado_do_mundo.json
  ├── Se existe: perguntar se quer continuar
  │     └── load_world_state() → retomar modo correto
  └── Se não: play_ressoar_opening_sequence() → select_game_mode()
```

---

### `select_game_mode() → str`
Apresenta o menu de seleção entre RPG e Conto Interativo.

**Retorna:** `"rpg"` ou `"story"`

---

### `select_rpg_campaign() → dict`
Lista campanhas disponíveis do `config.json` e permite ao jogador escolher.

**Efeitos colaterais:**
- Atualiza `current_campaign` no `config.json`
- Retorna os dados completos da campanha selecionada

---

### `iniciar_modo_rpg(campaign_data, world_state=None)`
Inicializa o modo RPG para novo jogo ou continuação.

**Fluxo:**
1. Apresenta tutorial/introdução via Gemini
2. Coleta nome do personagem
3. `create_initial_world_state()` se novo jogo
4. Entra em `new_game_loop()`

---

### `new_game_loop(world_state, campaign_data)`
**Loop principal do modo RPG.** Executa indefinidamente até `chikito`.

```python
while True:
    # 1. Capturar input
    action = input() ou speech_to_text()

    # 2. Checar comandos especiais
    if action in ["inventário", "status", "chikito"]:
        execute_command(action)
        continue

    # 3. Validar ação
    objects = extract_objects_from_action(action)
    if not validate_player_action(objects, world_state):
        print(error_msg)
        continue

    # 4. Verificar gatilhos
    trigger_text = check_and_fire_trigger(world_state)

    # 5. Chamar Gemini Mestre
    narrative = get_gm_narrative(world_state, campaign_data, action, trigger_text)

    # 6. Parsear updates
    parse_status_update(narrative, world_state)
    parse_inventory_update(narrative, world_state)

    # 7. Áudio
    trigger_contextual_sfx(narrative)
    narrator_speech(narrative)

    # 8. Atualizar estado
    update_world_state(world_state, narrative)
    save_world_state(world_state)
    play_chime()
```

---

### `extract_objects_from_action(action) → list[str]`
Extrai substantivos/objetos mencionados na ação do jogador.

**Algoritmo:**
- Tokeniza string por espaços
- Remove stop words (artigos, preposições, verbos comuns)
- Retorna lista de candidatos a objetos

**Exemplo:**
```
Input:  "Vou até a mesa e pego o livro"
Output: ["mesa", "livro"]
```

---

### `validate_player_action(action, character, world_state=None) → tuple[bool, str]`
Valida ações fisicamente impossíveis (voar, teleporte, magia proibida etc.) e retorna feedback textual.

---

### `get_gm_narrative(world_state, player_action, game_context, roll_result=None) → str`
Constrói o prompt e chama o modelo para gerar a narrativa do Mestre.

**Contexto fornecido ao modelo:**
- Nome, classe, HP, inventário do personagem
- Localização atual e descrição da cena
- Mapa semântico da cena (`interactable_elements_in_scene`)
- Ação do jogador
- Gatilho (se houver)
- Dados do contexto do ato (NPCs, locais, itens)
- Regras da classe (habilidades e restrições)
- Resultado de dados Shadowdark (quando aplicável)

**Instruções chave no prompt:**
- Narrar consequências da ação
- Usar `[STATUS_UPDATE] {"hp_change": ...}` para dano/cura
- Usar `[INVENTORY_UPDATE] {"add": [...], "remove": [...]}` para inventário
- Usar `[MOOD:combat|tense|dramatic|sad|relief|normal]` ao final
- NUNCA oferecer múltipla escolha
- Sempre terminar com "O que você faz?"
- Respeitar limitações da classe

**Parâmetros do modelo:**
```python
temperature = 0.75
max_tokens = 1024
```

---

### `clean_and_process_ai_response(response_text, world_state) → tuple[str, dict]`
Processa tags estruturadas da resposta do Mestre e devolve narrativa limpa + estado atualizado.

**Processa:**
- `[MOOD:...]` → grava em `world_state["narration_mood"]` (fallback `normal`)
- `[INVENTORY_UPDATE] {...}` → adiciona/remove itens
- `[STATUS_UPDATE] {...}` → ajusta HP com clamp entre `0` e `max_hp`

---

### `trigger_contextual_sfx(narrative) → void`
Analisa o texto da narrativa e dispara efeitos sonoros correspondentes.

**Mapeamento de keywords:**

| Keyword no texto            | Arquivo de som                              |
|-----------------------------|---------------------------------------------|
| corvo, grasnido             | creepy-crow-caw-322991.mp3                  |
| corvos (plural)             | crows-6371.mp3                              |
| cidade, vila, portões       | medieval_village_atmosphere.mp3             |
| taverna, bar, bebida        | tavern_ambience_inside_laughter.mp3         |
| chuva, tempestade           | Rain-on-city-deck.mp3                       |
| grito, berro                | scream-of-terror-325532.mp3                 |
| moeda, ouro, compra         | coin-recieved.mp3                           |
| criança correndo            | rianca_correndo.mp3                         |
| música familiar             | familiar_sound.mp3                          |
| sussurro praga              | familiar_sound2.mp3                         |

---

### `get_item_slots(item_name, campaign_data) → int`
Retorna quantos slots um item ocupa no inventário.

**Fallback:** 1 slot se item não encontrado nas listas da campanha.

---

### `calculate_used_slots(inventory, campaign_data) → int`
Calcula total de slots usados pelo inventário atual.

---

### `load_game_context_for_act(act, campaign_data) → dict`
Carrega contexto específico do ato atual (NPCs, locais, gatilhos relevantes).

---

### `iniciar_modo_conto(story=None)`
Inicializa o modo conto interativo.

**Fluxo:**
1. `select_interactive_story()` — exibe contos disponíveis
2. Carrega `.txt` e `_eventos.json`
3. Inicializa variáveis dinâmicas do conto
4. Entra em `interactive_story_loop()`

---

### `select_interactive_story() → tuple[str, dict, str]`
Lista contos disponíveis em `contos_interativos/` e permite seleção.

**Retorna:** `(texto_original, eventos, nome_conto)`

---

### `interactive_story_loop(texto_original, eventos, variaveis)`
**Loop principal do modo conto.** Executa até evento final.

```python
current_evento = "inicio"

while True:
    evento = eventos[current_evento]

    # Final?
    if not evento["opcoes"]:
        show_final_stats(variaveis)
        break

    # Gerar narrativa
    narrative = get_story_master_narrative(texto_original, evento, variaveis)

    # Áudio e exibição
    trigger_contextual_sfx(narrative)
    print(narrative)
    narrator_speech(narrative)
    play_chime()

    # Escolha do jogador
    choice = get_valid_choice(["A", "B", "C"])
    opcao = evento["opcoes"][choice_index]

    # Aplicar efeito
    for var, delta in opcao["efeito"].items():
        variaveis[var] += delta

    current_evento = opcao["proximo_evento"]
```

---

### `get_story_master_narrative(texto_original, evento, variaveis) → str`
Chama o Gemini como Mestre dos Contos para adaptar o evento literariamente.

**Instrui o Gemini a:**
1. Localizar o evento no mapa
2. Narrar usando estilo do texto original
3. Apresentar exatamente as opções (A), (B), (C)
4. Não adicionar explicações além da narrativa
5. Usar as variáveis dinâmicas para colorir a narrativa

---

## Constantes Importantes

```python
SAVE_FILE = "estado_do_mundo.json"
CONFIG_FILE = "config.json"
STORIES_DIR = "contos_interativos"
SOUNDS_DIR = "sons/sistema"

SPECIAL_COMMANDS = ["inventário", "inventario", "status", "saúde", "vida", "chikito"]

TRIGGER_BASE_PROBABILITY = 0.30
TRIGGER_INCREMENT = 0.10
TRIGGER_MAX = 0.90
```

---

## Parsing de Tags Especiais na Narrativa

O Gemini é instruído a incluir tags estruturadas que o `game.py` extrai:

### Status Update
```
[STATUS_UPDATE: hp=15]
[STATUS_UPDATE: hp_change=-5]
```

### Inventory Update
```
[INVENTORY_UPDATE: +Espada de Bronze]
[INVENTORY_UPDATE: -Poção de Cura]
```

O sistema extrai essas tags com regex antes de exibir a narrativa ao jogador.
