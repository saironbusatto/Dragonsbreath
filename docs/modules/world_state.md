# world_state_manager.py — Gerenciador de Estado do Mundo

## Visão Geral

Módulo responsável por criar, carregar, salvar e atualizar o estado completo do mundo do jogo RPG. Inclui o sistema AI Archivista que usa Gemini para manter consistência do estado após cada narrativa.

---

## Estrutura Completa do Estado

```json
{
  "player_character": {
    "name": "Aldric",
    "class": "Bardo",
    "current_act": 1,
    "status": {
      "hp": 20,
      "max_hp": 20
    },
    "max_slots": 10,
    "inventory": [
      "Alaúde",
      "Adaga",
      "Mochila",
      "Kit Viagem",
      "Kit Iluminação"
    ],
    "desejo": "Descobrir a verdade sobre a praga musical que assola Umbraton"
  },
  "world_state": {
    "current_location_key": "umbraton",
    "immediate_scene_description": "Você está diante das antigas portas de pedra de Umbraton...",
    "active_quests": {
      "main_quest": "Investigar a praga musical e encontrar sua origem",
      "side_quest_1": "Encontrar o irmão de Lyra"
    },
    "important_npcs_in_scene": {
      "Porteiro": "Guarda nervoso que desconfia de viajantes"
    },
    "recent_events_summary": [
      "Chegou às portas de Umbraton ao anoitecer",
      "O porteiro questionou sobre a origem do viajante",
      "Uma melodia estranha veio de dentro da cidade"
    ],
    "gatilhos_ativos": {
      "umbraton": ["corvo_na_gargula", "crianca_correndo"],
      "taverna_corvo_ferido": ["taverneiro_se_cala", "musica_familiar"]
    },
    "gatilhos_usados": {
      "umbraton": [],
      "taverna_corvo_ferido": []
    },
    "interactable_elements_in_scene": [
      "portão",
      "gárgula",
      "pedras",
      "lanterna",
      "porteiro"
    ]
  },
  "game_mode": "rpg",
  "rodadas_sem_gatilho": 2
}
```

---

## Funções

### `create_initial_world_state(campaign_data, player_name) → dict`
Cria um estado inicial a partir do template da campanha.

**Processo:**
1. Lê `player_template` do `campaign_data`
2. Aplica `player_name` fornecido pelo jogador
3. Lê `world_template` para estado inicial do mundo
4. Inicializa listas de gatilhos com valores da campanha

**Resultado:** `world_state` pronto para a primeira rodada

---

### `load_world_state(filepath="estado_do_mundo.json") → dict | None`
Carrega estado salvo do arquivo JSON.

```python
with open(filepath, 'r', encoding='utf-8') as f:
    return json.load(f)
# Retorna None se arquivo não existe
```

---

### `save_world_state(world_state, filepath="estado_do_mundo.json") → void`
Persiste o estado atual em JSON.

```python
with open(filepath, 'w', encoding='utf-8') as f:
    json.dump(world_state, f, ensure_ascii=False, indent=2)
```

**Chamada:** Ao final de cada turno RPG, garantindo que nenhuma ação seja perdida.

---

### `update_world_state(world_state, gm_narrative) → dict`
**Função central do AI Archivista.**

Envia o estado atual e a última narrativa do Mestre para o Gemini (em modo Archivista) e recebe o estado atualizado.

**Prompt enviado ao Gemini:**
```
Você é o Archivista — um sistema silencioso de gestão de estado.
Analise a narrativa do Mestre e atualize o estado do mundo:

Estado atual: {world_state_json}

Última narrativa do Mestre: {gm_narrative}

Retorne APENAS um JSON válido com:
- interactable_elements_in_scene: lista de objetos substantivos mencionados
- important_npcs_in_scene: NPCs presentes na cena
- current_location_key: localização atual (se mudou)
- recent_events_summary: adicionar resumo deste evento (manter últimos 5)
```

**Parâmetros Gemini para Archivista:**
```python
temperature = 0.2  # Muito baixo — precisão > criatividade
max_output_tokens = 512
```

---

### `get_gemini_response_archivista(prompt) → str`
Wrapper específico para chamadas Gemini no papel de Archivista.
Usa configurações mais conservadoras que o Mestre do Jogo.

---

## Sistema de Gatilhos (implementado no world_state_manager)

### Dados dos Gatilhos
Os gatilhos são carregados de `locais.json` de cada campanha:

```json
{
  "umbraton": {
    "gatilhos": [
      {
        "id": "corvo_na_gargula",
        "descricao": "Um corvo pousa em uma gárgula próxima e emite um grasnido inquietante. Seu diário na mochila vibra levemente.",
        "sfx": "corvo",
        "proximo_gatilho": "diario_vibra"
      },
      {
        "id": "diario_vibra",
        "descricao": "O diário vibra novamente, com mais intensidade. Parece querer ser aberto.",
        "sfx": null,
        "proximo_gatilho": null
      }
    ]
  }
}
```

### Lógica de Disparo (no game.py, usa dados do world_state)

```python
def check_trigger(world_state):
    location = world_state["world_state"]["current_location_key"]
    active = world_state["world_state"]["gatilhos_ativos"].get(location, [])

    if not active:
        world_state["rodadas_sem_gatilho"] += 1
        return None

    rounds = world_state["rodadas_sem_gatilho"]
    probability = min(0.90, 0.30 + rounds * 0.10)

    if random.random() < probability:
        trigger_id = active[0]
        # Mover para usados
        world_state["world_state"]["gatilhos_usados"][location].append(trigger_id)
        world_state["world_state"]["gatilhos_ativos"][location].remove(trigger_id)
        # Ativar próximo da cadeia
        # Resetar contador
        world_state["rodadas_sem_gatilho"] = 0
        return trigger_data
    else:
        world_state["rodadas_sem_gatilho"] += 1
        return None
```

---

## Progressão por Atos

O `current_act` em `player_character` controla qual conteúdo está disponível:

| Ato | Localização principal | Gatilhos ativos          | NPCs disponíveis              |
|-----|----------------------|--------------------------|-------------------------------|
| 1   | Umbraton + Arredores | `corvo_na_gargula`, `crianca_correndo`, `grito_viela` | Porteiro, Lysenn, Silas, Lyra |
| 2   | Taverna + Santuário  | `taverneiro_se_cala`, `musica_familiar`, `figura_encapuzada` | Kael, Virella, Irmão Ellun |
| 3   | Interior do Santuário | `sussurro_praga`, `sino_toca` | Kael (forma verdadeira), Archivista |

---

## Diagrama do Ciclo de Vida do Estado

```
create_initial_world_state()
         │
         ▼
    world_state em memória
         │
    ┌────┴────────────────────────────┐
    │          A cada turno:          │
    │                                 │
    │  1. Ação do jogador             │
    │  2. Validação                   │
    │  3. Gemini gera narrativa       │
    │  4. Parse [STATUS/INVENTORY]    │
    │  5. update_world_state()        │
    │     └─ Gemini Archivista        │
    │        atualiza campos          │
    │  6. save_world_state()          │
    │     └─ → estado_do_mundo.json  │
    └─────────────────────────────────┘
         │
    (próxima sessão)
         │
    load_world_state()
         │
         ▼
    world_state em memória
    (continua do ponto salvo)
```
