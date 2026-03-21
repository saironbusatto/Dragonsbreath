# Entidades do Sistema

## Diagrama de Entidades

```
┌─────────────────────────────────┐
│         WorldState              │
├─────────────────────────────────┤
│ player_character: PlayerChar    │
│ world_state: WorldData          │
│ game_mode: str                  │
│ rodadas_sem_gatilho: int        │
└────────────┬────────────────────┘
             │ contém
    ┌────────┴────────┐
    │                 │
    ▼                 ▼
┌──────────────┐  ┌──────────────────────┐
│ PlayerChar   │  │ WorldData            │
├──────────────┤  ├──────────────────────┤
│ name: str    │  │ current_location_key │
│ class: str   │  │ scene_description    │
│ current_act  │  │ active_quests {}     │
│ status {}    │  │ npcs_in_scene {}     │
│ max_slots    │  │ recent_events []     │
│ inventory [] │  │ gatilhos_ativos {}   │
│ desejo: str  │  │ gatilhos_usados {}   │
└──────────────┘  │ interactable [] │
                  └──────────────────────┘
```

---

## Entidade: WorldState
Raiz do estado persistido do jogo.

```json
{
  "player_character": { ... },
  "world_state": { ... },
  "game_mode": "rpg",
  "rodadas_sem_gatilho": 0
}
```

| Campo                  | Tipo    | Descrição                                          |
|------------------------|---------|----------------------------------------------------|
| `player_character`     | Object  | Dados completos do personagem jogador              |
| `world_state`          | Object  | Estado atual do mundo do jogo                      |
| `game_mode`            | String  | `"rpg"` ou `"story"`                               |
| `rodadas_sem_gatilho`  | Integer | Contador para cálculo de probabilidade de gatilhos |

---

## Entidade: PlayerCharacter
Representa o personagem controlado pelo jogador.

```json
{
  "name": "Aldric",
  "class": "Bardo",
  "current_act": 1,
  "status": {
    "hp": 20,
    "max_hp": 20
  },
  "max_slots": 10,
  "inventory": ["Alaúde", "Adaga", "Mochila", "Kit Viagem", "Kit Iluminação"],
  "desejo": "Descobrir a verdade sobre a praga musical"
}
```

| Campo         | Tipo    | Descrição                                                  |
|---------------|---------|------------------------------------------------------------|
| `name`        | String  | Nome do personagem (definido pelo jogador)                 |
| `class`       | String  | `"Bardo"` ou `"Aventureiro"` (define habilidades e HP)    |
| `current_act` | Integer | Ato atual da campanha (1, 2, 3...)                         |
| `status.hp`   | Integer | Pontos de vida atuais                                      |
| `status.max_hp`| Integer | Pontos de vida máximos                                    |
| `max_slots`   | Integer | Capacidade máxima do inventário em slots                   |
| `inventory`   | Array   | Lista de itens carregados (strings)                        |
| `desejo`      | String  | Motivação/objetivo principal do personagem                 |

---

## Entidade: WorldData
Estado atual do mundo do jogo.

```json
{
  "current_location_key": "umbraton",
  "immediate_scene_description": "Você está nas portas de Umbraton...",
  "active_quests": {
    "main_quest": "Encontrar a origem da praga musical"
  },
  "important_npcs_in_scene": {
    "Kael": "Bardo misterioso com alaúde prateado"
  },
  "recent_events_summary": [
    "Jogador chegou a Umbraton",
    "Conversou com o porteiro"
  ],
  "gatilhos_ativos": {
    "umbraton": ["corvo_na_gargula"]
  },
  "gatilhos_usados": {
    "umbraton": []
  },
  "interactable_elements_in_scene": ["portão", "corvo", "gárgula", "lanterna"]
}
```

| Campo                        | Tipo   | Descrição                                                       |
|------------------------------|--------|-----------------------------------------------------------------|
| `current_location_key`       | String | ID da localização atual (chave em `locais.json`)               |
| `immediate_scene_description`| String | Última descrição gerada pelo Mestre                             |
| `active_quests`              | Object | Missões em andamento `{id: descrição}`                         |
| `important_npcs_in_scene`    | Object | NPCs presentes na cena atual `{nome: descrição}`               |
| `recent_events_summary`      | Array  | Histórico resumido dos últimos eventos                          |
| `gatilhos_ativos`            | Object | Gatilhos disponíveis por localização `{local_id: [ids]}`       |
| `gatilhos_usados`            | Object | Gatilhos já disparados `{local_id: [ids]}`                     |
| `interactable_elements_in_scene` | Array | Objetos com os quais o jogador pode interagir              |

---

## Entidade: NPC

```json
{
  "Kael": {
    "aparencia_facil": "Um bardo sábio e carismático, viaja há décadas...",
    "verdade_oculta": "Dragão negro ancião que manipula através da música...",
    "papel": "antagonista_principal",
    "localização_ato1": "taverna_corvo_ferido"
  }
}
```

| Campo           | Tipo   | Descrição                                   |
|-----------------|--------|---------------------------------------------|
| `aparencia_facil`| String | O que o jogador percebe inicialmente        |
| `verdade_oculta` | String | A realidade por trás da aparência           |
| `papel`          | String | Papel narrativo (antagonista, aliado, etc.) |
| `localização_ato*`| String | Onde encontrar em cada ato                 |

---

## Entidade: Local (Location)

```json
{
  "umbraton": {
    "nome": "Umbraton",
    "descricao": "Cidade gótica envolta em névoa...",
    "gatilhos": [
      {
        "id": "corvo_na_gargula",
        "descricao": "Um corvo pousa em uma gárgula e canta...",
        "sfx": "corvo",
        "proximo_gatilho": "diario_vibra"
      }
    ]
  }
}
```

| Campo       | Tipo   | Descrição                                             |
|-------------|--------|-------------------------------------------------------|
| `nome`      | String | Nome exibido da localização                           |
| `descricao` | String | Descrição narrativa base do local                     |
| `gatilhos`  | Array  | Lista de gatilhos narrativos disponíveis neste local  |

---

## Entidade: Gatilho (Trigger)

```json
{
  "id": "corvo_na_gargula",
  "descricao": "Um corvo pousa em uma gárgula próxima e emite um grasnido inquietante. Nesse momento, seu diário na mochila vibra levemente.",
  "sfx": "corvo",
  "proximo_gatilho": "diario_vibra"
}
```

| Campo            | Tipo   | Descrição                                                |
|------------------|--------|----------------------------------------------------------|
| `id`             | String | Identificador único do gatilho                           |
| `descricao`      | String | Texto narrativo injetado na cena quando ativado          |
| `sfx`            | String | Keyword de efeito sonoro a disparar                      |
| `proximo_gatilho`| String | ID do próximo gatilho na cadeia (ou `null`)              |

**Probabilidade de ativação:**
```
P = min(0.90, 0.30 + (rodadas_sem_gatilho × 0.10))
```

---

## Entidade: Item

### Item Mágico

```json
{
  "nome": "Anel do Sussurro",
  "raridade": "Incomum",
  "slots": 1,
  "descricao": "Um anel de prata com runas gravadas...",
  "efeito": "Permite entender melodias mágicas e resistir a ilusões sônicas.",
  "como_obter": "Recompensa após completar o Ato 1"
}
```

### Item Comum

```json
{
  "nome": "Poção de Cura",
  "slots": 1,
  "descricao": "Frasco de líquido avermelhado com aroma herbal.",
  "efeito": "Restaura 10 HP quando consumida.",
  "como_obter": "Comprar em lojas ou encontrar em baús"
}
```

| Campo       | Tipo    | Descrição                                       |
|-------------|---------|------------------------------------------------|
| `nome`      | String  | Nome do item                                   |
| `raridade`  | String  | Comum / Incomum / Raro / Lendário              |
| `slots`     | Integer | Espaço ocupado no inventário (1-2 slots)       |
| `descricao` | String  | Descrição narrativa do item                    |
| `efeito`    | String  | Efeito mecânico ou narrativo                   |
| `como_obter`| String  | Como o jogador consegue este item              |

---

## Entidade: Campaign (Campanha)

Configuração declarativa em `config.json`:

```json
{
  "name": "O Lamento do Bardo",
  "description": "Narrativa gótica sobre perda e ilusão",
  "files": {
    "npcs": "campanhas/lamento_do_bardo/npcs.json",
    "itens_magicos": "campanhas/lamento_do_bardo/itens_magicos.json",
    "itens_comuns": "campanhas/lamento_do_bardo/itens_comuns.json",
    "locais": "campanhas/lamento_do_bardo/locais.json",
    "campanha": "campanhas/lamento_do_bardo/campanha.md"
  },
  "player_template": {
    "class": "Bardo",
    "starting_hp": 20,
    "max_slots": 10,
    "starting_inventory": ["Alaúde", "Adaga", "Mochila", "Kit Viagem", "Kit Iluminação"]
  },
  "world_template": {
    "initial_description": "Você está nas portas de Umbraton...",
    "initial_quest": "Investigar a praga musical",
    "initial_location": "umbraton",
    "initial_triggers": {
      "umbraton": ["corvo_na_gargula", "crianca_correndo"]
    }
  }
}
```

---

## Entidade: InteractiveStory (Conto Interativo)

### Arquivo de Eventos

```json
{
  "inicio": {
    "descricao_para_ia": "Cena inicial — homem em câmara escura ouve batida.",
    "opcoes": [
      {
        "texto": "(A) Abrir a porta",
        "efeito": {"esperanca": 1},
        "proximo_evento": "porta_aberta"
      },
      {
        "texto": "(B) Ignorar a batida",
        "efeito": {"obsessao": 1},
        "proximo_evento": "silencio_pesado"
      }
    ]
  },
  "final_aceitacao": {
    "descricao_para_ia": "Final — personagem encontra paz.",
    "opcoes": []
  }
}
```

| Campo             | Tipo   | Descrição                                                 |
|-------------------|--------|-----------------------------------------------------------|
| `descricao_para_ia`| String | Contexto fornecido à IA para gerar a narrativa da cena   |
| `opcoes`          | Array  | Lista de escolhas disponíveis (vazio = evento final)      |
| `opcoes[].texto`  | String | Texto da opção exibido ao jogador                         |
| `opcoes[].efeito` | Object | Mudanças nas variáveis dinâmicas `{variavel: delta}`      |
| `opcoes[].proximo_evento` | String | ID do próximo evento no mapa                   |

---

## Entidade: DynamicVariables (Variáveis Dinâmicas — Contos)

Variáveis numéricas que mudam com escolhas do jogador e determinam finais.

Exemplo para "O Corvo":

| Variável    | Range | Descrição                                    |
|-------------|-------|----------------------------------------------|
| `sanidade`  | 0-10  | Estabilidade mental do personagem            |
| `esperanca` | 0-10  | Capacidade de encontrar significado           |
| `obsessao`  | 0-5   | Fixação na perda e no passado                |
| `aceitacao` | 0-10  | Capacidade de seguir em frente               |

**Mapeamento de finais (exemplo):**
- `obsessao >= 4` + `aceitacao <= 3` → `final_desespero`
- `esperanca >= 7` + `sanidade >= 6` → `final_aceitacao`

---

## Entidade: AudioConfig

Não é persistida — configuração em código no `audio_manager.py`.

| Configuração       | Valor                        | Descrição                   |
|--------------------|------------------------------|-----------------------------|
| Voz narradora      | `pt-BR-Neural2-A`            | Feminina, para intro/contos |
| Voz mestre         | `pt-BR-Neural2-B`            | Masculina, para RPG         |
| Velocidade         | `1.5`                        | 1.5x mais rápido que normal |
| Taxa de amostragem | `22050 Hz`                   | Qualidade de áudio          |
| Formato saída      | MP3                          | Compatível com pygame       |
| SFX base path      | `sons/sistema/`              | Diretório dos efeitos       |
