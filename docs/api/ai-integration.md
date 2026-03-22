# Integração com IA — OpenAI GPT-4o-mini

## Visão Geral

A plataforma usa **OpenAI GPT-4o-mini** como motor de inteligência artificial com **quatro personas distintas**, cada uma otimizada para um papel específico. Todas as chamadas usam o mesmo endpoint (`/v1/chat/completions`), diferenciadas por temperatura e system prompt.

---

## Quatro Personas de IA

### 1. Mestre do Jogo (RPG)
**Função:** Gerar narrativa open-world responsiva às ações do jogador.

**Chamado em:** `get_gm_narrative()` em `game.py`

**Temperatura:** 0.75 (criativo mas consistente)

**Parâmetros:**
```python
model="gpt-4o-mini", temperature=0.75, max_tokens=1024
```

**System prompt (resumido):**
```
Você é Mestre de Jogo narrando "[campanha]". Narre em segunda pessoa, tempo presente.

--- BREVIDADE (REGRA MAIS IMPORTANTE) ---
- Ação simples: 1-2 frases + "O que você faz?"
- Exploração: 2-3 frases
- Evento importante: 3-4 frases
NUNCA ultrapasse 4 frases.

--- REGRAS FUNDAMENTAIS ---
1. Narre APENAS o resultado imediato da ação.
2. Use [STATUS_UPDATE] para HP: [STATUS_UPDATE] {"hp_change": -4}
3. Use [INVENTORY_UPDATE] para itens: [INVENTORY_UPDATE] {"add": ["item"]}
7. ANTI-REPETIÇÃO: NUNCA redescreva o que já está em "recent_narrations".
10. Encerre sempre com: "O que você faz?"

--- NARRAÇÃO SONORA ---
15. Inclua o som que os objetos produzem.
16. Mencione o som ANTES do objeto (isca sonora).
17. Som ambiente apenas ao entrar em local novo.
```

**Injeção Shadowdark (quando há rolagem de dados):**
```
[DADOS SHADOWDARK]
Modificador: Vantagem (2d20 → maior) | Dados: [4, 16] | Usado: 16 | DC: 12
RESULTADO: SUCESSO (16 vs DC 12) — narre o jogador tendo sucesso.
REGRA ABSOLUTA: narre ESTRITAMENTE conforme o resultado. Não inverta nem ignore os dados.
```

**Output esperado:**
```
[STATUS_UPDATE] {"hp_change": -3}

A criatura recua ferida... [1-4 frases narrativas]

O que você faz?
```

---

### 2. Mestre dos Contos (Story Mode)
**Função:** Adaptar eventos do mapa de contos usando o estilo do autor original.

**Chamado em:** `get_story_master_narrative()` em `game.py`

**Temperatura:** 0.75

**Parâmetros:**
```python
model="gpt-4o-mini", temperature=0.75, max_tokens=1024
```

**Prompt padrão:**
```
Você é o Mestre dos Contos, narrando "[NOME DO CONTO]".

TEXTO ORIGINAL (use como referência de estilo):
[conteúdo do .txt]

ESTADO DAS VARIÁVEIS DINÂMICAS:
[variavel]: [valor]

EVENTO ATUAL: [id] — [descricao_para_ia]

OPÇÕES:
(A) [texto_a]  (B) [texto_b]  (C) [texto_c]

Instruções:
1. Narre no estilo do texto original
2. Apresente as opções EXATAMENTE como listadas
3. Não adicione nem remova opções
```

---

### 3. Archivista (State Manager)
**Função:** Extrair e atualizar o estado do mundo em JSON puro após cada narrativa.

**Chamado em:** `update_world_state()` em `world_state_manager.py`

**Temperatura:** 0.2 (precisão > criatividade)

**Parâmetros:**
```python
model="gpt-4o-mini", temperature=0.2, max_tokens=2048
```

**System prompt:**
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

**Output esperado:**
```json
{
  "player_character": { ... },
  "world_state": {
    "current_location_key": "taverna_corvo_ferido",
    "interactable_elements_in_scene": {
      "objetos": ["balcão", "vela", "lareira"],
      "npcs": ["taverneiro"],
      "npc_itens": { "taverneiro": ["caneca", "chave enferrujada"] },
      "containers": {},
      "saidas": ["porta norte", "escada"],
      "chao": []
    },
    "important_npcs_in_scene": { "taverneiro": "Olha desconfiado" },
    "recent_events_summary": ["Entrou na taverna do Corvo Ferido"]
  }
}
```

---

### 4. Olhos do Jogador (HUD Narrativo)
**Função:** Responder consultas de inspeção do jogador (inventário, saúde, ambiente) de forma imersiva, sem avançar a narrativa. O tempo do jogo não passa.

**Chamado em:** `get_player_eyes_response()` em `game.py`

**Temperatura:** 0.2 (factual, como o Archivista)

**Parâmetros:**
```python
model="gpt-4o-mini", temperature=0.2, max_tokens=200
```

**Detecção de consulta:** `is_inspection_action(action)` → `'inventory'`, `'health'`, `'environment'`, ou `None`

**Keywords de inspeção detectadas:**
| Tipo | Exemplos |
|------|---------|
| `inventory` | "inventário", "bolsa", "meus itens", "o que eu tenho" |
| `health` | "status", "saúde", "como estou", "meu hp" |
| `environment` | "o que eu vejo", "ao meu redor", "onde estou", "o que tem aqui" |

**Contexto enviado (mínimo e focado):**
- `inventory` → `{inventory, slots_usados, max_slots}`
- `health` → `{status, classe}`
- `environment` → `{local_atual, descricao_da_cena, cena (mapa semântico), narrações_recentes}`

**System prompt:**
```
Você é a consciência interna e os olhos do personagem — uma voz suave e factual
que traduz dados do jogo em linguagem imersiva.

REGRAS ABSOLUTAS:
1. Baseie-se EXCLUSIVAMENTE nos dados JSON fornecidos. Nunca invente.
2. NÃO avance a narrativa, NÃO tome ações, NÃO descreva eventos novos.
3. Máximo 2-3 frases curtas.
4. Tom: calmo, factual, levemente poético.
5. NÃO encerre com "O que você faz?"
```

**Voz usada:** `pt-BR-Neural2-A` (feminina, Narradora) — distinguível da voz masculina do Mestre.

**Exemplo:**
```
Jogador: "O que eu tenho na mochila?"
→ "Você carrega seu alaúde de madeira e um diário com anotações —
   dois objetos em dez espaços disponíveis."
```

---

## Configuração do Cliente OpenAI

```python
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

response = client.chat.completions.create(
    model=os.environ.get("OPENAI_MODEL_MESTRE", "gpt-4o-mini"),
    messages=[
        {"role": "system", "content": system_content},
        {"role": "user",   "content": user_content},
    ],
    temperature=0.75,
    max_tokens=1024,
)
```

**Variáveis de ambiente:**
| Variável | Default | Uso |
|----------|---------|-----|
| `OPENAI_API_KEY` | — | Obrigatória |
| `OPENAI_MODEL` | `gpt-4o-mini` | Modelo padrão |
| `OPENAI_MODEL_MESTRE` | herda `OPENAI_MODEL` | Mestre do Jogo |
| `OPENAI_MODEL_ARQUIVISTA` | herda `OPENAI_MODEL` | Archivista |

---

## Sistema de Dados Shadowdark

Antes de chamar o Mestre, `resolve_action_roll(action, character)` determina se há risco e rola os dados:

```python
# Sem rolagem para ações rotineiras
# Retorna None → GM narra livremente

# Com rolagem para ações arriscadas
{
  "roll": 16,           # resultado usado
  "dice": [4, 16],      # todos os dados rolados
  "dc": 12,             # classe de dificuldade (9/12/15/18)
  "modifier": "advantage",  # advantage / disadvantage / normal
  "success": True,
  "critical": False,    # natural 20
  "fumble": False,      # natural 1
}
```

**Classes de Dificuldade:**
| DC | Nome | Uso |
|----|------|-----|
| 9  | Fácil | Tarefas simples |
| 12 | Normal | Maioria dos desafios |
| 15 | Difícil | Oposição forte, objetos "pesado/reforçado" |
| 18 | Extremo | "impossível", "invencível" |

**Vantagem por classe:**
| Classe | Vantagem | Desvantagem |
|--------|----------|-------------|
| Bardo | persuasão, música, investigação | força bruta, combate |
| Aventureiro | combate, atletismo, intimidação | persuasão, furtividade, magia |

---

## Tratamento de Erros

```python
except Exception:
    return "{}"  # Archivista: mantém estado anterior
    return "O Mestre sente uma perturbação... Tente novamente. O que você faz?"
```

**Fallbacks:**
- IA indisponível → mensagem padrão de erro
- Archivista retorna JSON inválido → mantém `old_state` sem atualizar
- Olhos do Jogador sem API key → mensagem estática informando indisponibilidade

---

## Estimativa de Custo

Baseado em uso típico de 1 hora de jogo (GPT-4o-mini: ~$0.15/1M input, ~$0.60/1M output):

| Persona | Tokens/chamada | Chamadas/hora | Total/hora |
|---------|---------------|---------------|------------|
| Mestre RPG | ~2.000 in + 300 out | 30 | ~69.000 |
| Story Master | ~4.000 in + 400 out | 10 | ~44.000 |
| Archivista | ~2.000 in + 500 out | 30 | ~75.000 |
| Olhos do Jogador | ~400 in + 150 out | 8 | ~4.400 |
| Whisper STT | ~$0.006/min áudio | 60 min | ~$0.36 |
| **Total** | | | **~192.400 tokens** |

**Custo estimado: ~$0.03–0.07 por hora de jogo** (incluindo Whisper)

---

## Estratégias de Prompt Engineering

### 1. System vs User split
System prompt = instruções fixas (persona, regras). User prompt = contexto dinâmico (world_state, ação). Economiza tokens de re-envio.

### 2. Contexto mínimo por persona
O Olhos do Jogador recebe apenas o fragmento relevante (inventory OU health OU cena), não o `world_state` completo.

### 3. Output estruturado para o Archivista
JSON puro sem markdown reduz erros de parsing e tokens desnecessários.

### 4. Temperatura diferenciada

| Persona | Temp | Razão |
|---------|------|-------|
| Mestre RPG | 0.75 | Criativo mas coerente com o mundo |
| Story Master | 0.75 | Fiel ao estilo do autor mas vivo |
| Archivista | 0.20 | Precisão máxima, sem invenção |
| Olhos do Jogador | 0.20 | Factual — nunca alucina itens |

### 5. Trava narrativa via dados
A injeção `[DADOS SHADOWDARK]` com `REGRA ABSOLUTA` impede o GM de inverter resultados de falha/sucesso por "gentileza narrativa".

### 6. Anti-repetição com `recent_narrations`
As últimas 2 narrações são armazenadas em `world_state["recent_narrations"]` e enviadas ao GM, ativando a Rule 7 (ANTI-REPETIÇÃO).
