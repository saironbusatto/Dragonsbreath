# world_state_manager.py — Gerenciador de Estado do Mundo

## Visão Geral

Módulo responsável por criar, carregar, salvar e atualizar o estado completo do mundo do jogo RPG. Inclui o AI Archivista (OpenAI GPT-4o-mini, temperatura 0.2) que mantém consistência do estado após cada narrativa.

---

## Campos Persistentes Recentes (Fases 2-7)

Além do estado base, o sistema agora preserva:

- `player_character.death_count`
- `player_character.resurrection_flaws`
- `player_character.alignment`
- `resurrection_state` (runtime, quando em limbo)
- `world_state.combat_state`
- `world_state.emotional_pacing`
- `world_state.scene_npc_signatures`

Isso garante continuidade entre sessões para:

- atuação consistente de NPCs;
- clímax e ritmo de combate;
- custo narrativo de morte e retorno.

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
      "main_quest": "Investigar a praga musical e encontrar sua origem"
    },
    "important_npcs_in_scene": {
      "Porteiro": "Guarda nervoso que desconfia de viajantes"
    },
    "recent_events_summary": [
      "Chegou às portas de Umbraton ao anoitecer",
      "O porteiro questionou sobre a origem do viajante"
    ],
    "gatilhos_ativos": {
      "umbraton": ["corvo_na_gargula", "crianca_correndo"]
    },
    "gatilhos_usados": {
      "umbraton": []
    },
    "interactable_elements_in_scene": {
      "objetos": ["portão", "gárgula", "lanterna"],
      "npcs": ["porteiro"],
      "npc_itens": {},
      "containers": {},
      "saidas": ["entrada da cidade"],
      "chao": []
    }
  },
  "recent_narrations": [
    "Primeiros 300 chars da penúltima narração do Mestre",
    "Primeiros 300 chars da última narração do Mestre"
  ],
  "game_mode": "rpg",
  "rodadas_sem_gatilho": 0
}
```

### Mapa Semântico da Cena (`interactable_elements_in_scene`)

Gerado pelo Archivista após cada narrativa. Estrutura de 6 categorias:

| Chave        | Tipo           | Conteúdo                                              |
|--------------|----------------|-------------------------------------------------------|
| `objetos`    | Array[String]  | Objetos standalone presentes na cena                  |
| `npcs`       | Array[String]  | Personagens/criaturas presentes                       |
| `npc_itens`  | Object         | `{nome_npc: [itens visíveis]}` — só se mencionado     |
| `containers` | Object         | `{container: [conteúdo visível]}` — só se mencionado  |
| `saidas`     | Array[String]  | Saídas e passagens                                    |
| `chao`       | Array[String]  | Itens abandonados ou caídos no chão                   |

**Retrocompatibilidade:** `_flatten_scene_map()` em `game.py` aceita o formato antigo (lista plana) e o novo (dicionário).

---

## Funções

### `create_initial_world_state(campaign_data, player_name) → dict`

Cria um estado inicial a partir do template da campanha.

**Processo:**
1. Lê `player_template` do `campaign_data`
2. Aplica `player_name` fornecido pelo jogador
3. Lê `world_template` para estado inicial do mundo
4. Inicializa listas de gatilhos com valores da campanha
5. Inicializa `interactable_elements_in_scene` como dicionário vazio com as 6 chaves
6. Inicializa `recent_narrations` como lista vazia

**Resultado:** `world_state` pronto para a primeira rodada.

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

Envia o estado atual e a última narrativa do Mestre para o OpenAI (GPT-4o-mini em modo Archivista) e recebe o estado atualizado.

**Parâmetros OpenAI para Archivista:**

```python
model = "gpt-4o-mini"
temperature = 0.2  # Precisão máxima — nunca inventa
max_tokens = 2048
```

**System prompt do Archivista (resumido):**

```
Você é o Arquivista — um sistema silencioso que mantém o estado de um RPG.
Retorne APENAS o JSON completo e válido. Nenhuma palavra extra.

REGRAS DE ATUALIZAÇÃO:
1. Atualize 'immediate_scene_description' com a situação atual.
2. Atualize 'current_location_key' se o jogador mudou de local.
3. Adicione/remova NPCs em 'important_npcs_in_scene'.
4. Atualize 'active_quests' se necessário.
5. Mantenha 'recent_events_summary' com os 3-4 eventos mais recentes.
6. Atualize inventário e status se necessário.
7. MAPA SEMÂNTICO DA CENA: Preencha 'interactable_elements_in_scene' como dicionário:
   - "objetos": lista de objetos standalone
   - "npcs": personagens presentes
   - "npc_itens": {npc: [itens visíveis]} — só se explicitamente mencionado
   - "containers": {container: [conteúdo visível]} — só se mencionado
   - "saidas": saídas e passagens
   - "chao": itens abandonados no chão
   Extraia APENAS o que foi mencionado. Ao mudar de local, limpe o mapa.
```

**Fallback:** Se o Archivista retornar JSON inválido → mantém `old_state` sem atualizar.

---

## Sistema de Gatilhos

### Dados dos Gatilhos

Carregados de `locais.json` de cada campanha:

```json
{
  "umbraton": {
    "gatilhos": [
      {
        "id": "corvo_na_gargula",
        "descricao": "Um corvo pousa em uma gárgula próxima e emite um grasnido inquietante.",
        "sfx": "corvo",
        "proximo_gatilho": "diario_vibra"
      },
      {
        "id": "diario_vibra",
        "descricao": "O diário vibra novamente, com mais intensidade.",
        "sfx": null,
        "proximo_gatilho": null
      }
    ]
  }
}
```

### Lógica de Disparo (em `game.py`)

```python
rounds = world_state["rodadas_sem_gatilho"]
probability = min(0.90, 0.30 + rounds * 0.10)

if random.random() < probability:
    # dispara gatilho → reseta contador para 0
else:
    world_state["rodadas_sem_gatilho"] += 1
```

---

## Campo `recent_narrations`

Armazena os primeiros 300 caracteres das últimas 2 narrações do Mestre. Alimenta a **Rule 7 (ANTI-REPETIÇÃO)** do prompt do GM.

```python
# Atualizado a cada turno em web_api.py:
recent = world_state.get("recent_narrations", [])
recent.append(cleaned_narrative[:300])
world_state["recent_narrations"] = recent[-2:]
```

Inicializado em `/api/start` com a descrição de abertura da campanha.

---

## Progressão por Atos

| Ato | Localização principal | Gatilhos ativos                                        |
|-----|-----------------------|--------------------------------------------------------|
| 1   | Umbraton + Arredores  | `corvo_na_gargula`, `crianca_correndo`, `grito_viela`  |
| 2   | Taverna + Santuário   | `taverneiro_se_cala`, `musica_familiar`                |
| 3   | Interior do Santuário | `sussurro_praga`, `sino_toca`                          |

---

## Diagrama do Ciclo de Vida do Estado

```
create_initial_world_state()
         │
         ▼
    world_state em memória
         │
    ┌────┴─────────────────────────────────┐
    │           A cada turno:              │
    │                                      │
    │  1. Ação do jogador                  │
    │  2. is_inspection_action()           │
    │     └─ SIM → Olhos do Jogador        │
    │            (tempo não avança)        │
    │  3. validate_player_action()         │
    │  4. resolve_action_roll() → dados    │
    │  5. _select_trigger()                │
    │  6. get_gm_narrative() + dados       │
    │  7. Parse [STATUS/INVENTORY]         │
    │  8. recent_narrations append         │
    │  9. update_world_state()             │
    │     └─ OpenAI Archivista             │
    │        atualiza mapa semântico       │
    │ 10. save_world_state()               │
    │     └─ → estado_do_mundo.json        │
    └──────────────────────────────────────┘
         │
    (próxima sessão)
         │
    load_world_state()
         │
         ▼
    world_state em memória
    (continua do ponto salvo)
```
