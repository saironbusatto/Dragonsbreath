# campaign_manager.py — Gerenciador de Campanhas

## Visão Geral

Módulo responsável por carregar e fornecer dados das campanhas RPG. Opera exclusivamente com leitura de arquivos — não modifica dados de campanha em tempo de execução.

---

## Estrutura de Arquivos por Campanha

```
campanhas/
└── {campaign_id}/
    ├── campanha.md          # Narrativa e contexto geral
    ├── npcs.json            # Personagens não-jogadores
    ├── locais.json          # Localizações e gatilhos
    ├── itens_magicos.json   # Itens com propriedades mágicas
    ├── itens_comuns.json    # Itens mundanos e consumíveis
    └── <handler>.py         # (Opcional) Módulo de evento de campanha
```

Arquivos `<handler>.py` são carregados dinamicamente pelo motor quando um gatilho do tipo `campaign_event` dispara. Cada campanha pode ter zero ou mais handlers.

---

## Funções

### `load_campaign(campaign_id) → dict`
Carrega todos os arquivos de uma campanha em um único dicionário.

```python
{
    "id": campaign_id,
    "name": "O Lamento do Bardo",
    "npcs": { ... },           # Conteúdo de npcs.json
    "locais": { ... },         # Conteúdo de locais.json
    "itens_magicos": [ ... ],  # Conteúdo de itens_magicos.json
    "itens_comuns": [ ... ],   # Conteúdo de itens_comuns.json
    "narrativa": "...",        # Conteúdo de campanha.md
    "player_template": { ... },# De config.json
    "world_template": { ... }  # De config.json
}
```

---

### `list_campaigns() → list[dict]`
Retorna lista de campanhas disponíveis lendo `config.json`.

```python
[
    {
        "id": "lamento_do_bardo",
        "name": "O Lamento do Bardo",
        "description": "Narrativa gótica sobre perda e ilusão musical"
    },
    {
        "id": "exemplo_fantasia",
        "name": "A Busca pelo Cristal Perdido",
        "description": "Aventura clássica de fantasia"
    }
]
```

---

### `set_current_campaign(campaign_id) → void`
Atualiza `current_campaign` em `config.json`.

---

### `get_current_campaign() → str`
Lê `current_campaign` de `config.json`.

---

### `load_npcs(campaign_id) → dict`
Carrega apenas NPCs da campanha.

---

### `load_locations(campaign_id) → dict`
Carrega localizações e seus gatilhos narrativos.

---

### `load_items(campaign_id) → tuple[list, list]`
Retorna `(itens_magicos, itens_comuns)`.

---

### `load_campaign_handler(handler_name: str) → module | None`

Carrega dinamicamente um módulo Python de evento da campanha atual.

```python
# Exemplo: handler_name="tarokka"
# Carrega: campanhas/curse_of_strahd/tarokka.py
mod = load_campaign_handler("tarokka")
```

Retorna o módulo Python ou `None` se não encontrado. Usa `importlib.util` para carregamento por caminho. O diretório base é inferido a partir do campo `files.npcs` da campanha ativa em `config.json`.

---

### `get_campaign_inspection_patterns() → dict[str, list[str]]`

Varre todos os arquivos `.py` da pasta da campanha atual e agrega o dicionário `INSPECTION_KEYWORDS` de cada handler encontrado.

```python
# Retorno típico (curse_of_strahd com tarokka.py):
{
    "prophecies": ["profecias", "tarokka", "cartas de madam eva", ...]
}
```

Usado por `game.py` para estender o sistema de inspeção HUD sem hardcodar padrões de campanha no motor.

---

## config.json — Schema Completo

```json
{
  "current_campaign": "lamento_do_bardo",
  "campaigns": {
    "lamento_do_bardo": {
      "name": "O Lamento do Bardo",
      "description": "Em uma cidade gótica envolta em névoa, um bardo busca a verdade sobre uma praga musical que silencia os vivos e ecoa nos mortos.",
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
        "starting_inventory": [
          "Alaúde",
          "Adaga",
          "Mochila",
          "Kit Viagem",
          "Kit Iluminação"
        ]
      },
      "world_template": {
        "initial_description": "Você está diante das antigas portas de pedra de Umbraton, uma cidade que ouve sussurros onde deveria haver canções.",
        "initial_quest": "Investigar a praga musical que silencia músicos e causa comportamentos estranhos nos habitantes de Umbraton",
        "initial_location": "umbraton",
        "initial_triggers": {
          "umbraton": ["corvo_na_gargula", "crianca_correndo", "grito_viela"],
          "taverna_corvo_ferido": ["taverneiro_se_cala", "musica_familiar"]
        }
      }
    },
    "exemplo_fantasia": {
      "name": "A Busca pelo Cristal Perdido",
      ...
    }
  },
  "elevenlabs": {
    "voice_id": "21m00Tcm4TlvDq8ikWAM"
  }
}
```

---

## Sistema de Classes de Personagem

As classes são definidas na `player_template` de cada campanha. O Gemini é instruído sobre as capacidades e limitações de cada classe via prompt.

### Bardo
```
HP inicial: 20
Slots: 10 (5 usados pelo inventário inicial)
Inventário inicial: Alaúde, Adaga, Mochila, Kit Viagem, Kit Iluminação

PODE: Performance musical, persuasão, investigação, contar histórias
NÃO PODE: Magia direta, voar, ressuscitar mortos, habilidades sobrenaturais
```

### Aventureiro
```
HP inicial: 25
Slots: 10 (7 usados pelo inventário inicial)
Inventário inicial: Espada Longa, Escudo, Armadura de Couro, Mochila,
                   Corda (10m), Kit de Ferramentas, Kit de Viagem

PODE: Combate, exploração, sobrevivência, uso de ferramentas
NÃO PODE: Magia, voar, habilidades sobrenaturais
```

---

## Como Criar uma Nova Campanha

Para adicionar uma nova campanha sem alterar código:

1. **Criar pasta:** `campanhas/minha_campanha/`

2. **Criar `campanha.md`:** Narrativa, contexto, atos e missões

3. **Criar `npcs.json`:** Seguindo o schema de NPCs com `aparencia_facil` e `verdade_oculta`

4. **Criar `locais.json`:** Com localizações e seus gatilhos narrativos

5. **Criar `itens_magicos.json` e `itens_comuns.json`:** Items com `nome`, `slots`, `descricao`, `efeito`

6. **Registrar em `config.json`:**
```json
"minha_campanha": {
  "name": "Nome da Campanha",
  "description": "...",
  "files": {
    "npcs": "campanhas/minha_campanha/npcs.json",
    ...
  },
  "player_template": { ... },
  "world_template": { ... }
}
```

A campanha aparecerá automaticamente no menu de seleção.

---

## Padrão de Handler de Evento de Campanha

Para criar um minigame ou evento interativo exclusivo da campanha, adicione um arquivo `<nome>.py` na pasta da campanha com a seguinte interface:

```python
# Interface pública esperada pelo motor
INSPECTION_KEYWORDS: dict[str, list[str]]  # padrões para o HUD

def on_trigger(world_state: dict) -> dict:
    """Chamado quando um gatilho com tipo='campaign_event' e handler='<nome>' dispara."""

def process_turn(world_state: dict, player_action: str) -> dict:
    """Processa uma rodada dentro do evento. Retorna {"narrative", "mood", "completed"}."""

def get_inspect_response(world_state: dict) -> str:
    """Resposta do HUD quando o jogador usar uma keyword de inspeção do handler."""

def build_gm_context_block(world_state: dict) -> str:
    """Bloco de texto injetado no system prompt do GM para cada turno."""
```

Para disparar o handler, registre o gatilho em `locais.json` com:
```json
"meu_evento": {
  "tipo": "campaign_event",
  "handler": "nome_do_arquivo",
  "descricao": "...",
  "sfx": "magia"
}
```

O motor (`game.py`) detecta `tipo == "campaign_event"`, carrega o módulo via `load_campaign_handler()` e despacha. Nenhuma alteração em `game.py` é necessária.

**Exemplo implementado:** `campanhas/curse_of_strahd/tarokka.py` — minigame de leitura de cartas com Madam Eva (5 cartas, estado persistido, injeção de localizações no GM).
