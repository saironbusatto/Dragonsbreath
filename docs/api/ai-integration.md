# Integração com IA — Google Gemini

## Visão Geral

A plataforma usa Google Gemini 1.5-Flash como motor de inteligência artificial com três personas distintas, cada uma otimizada para um papel específico.

---

## Três Personas de IA

### 1. Mestre do Jogo (RPG)
**Função:** Gerar narrativa open-world responsiva às ações do jogador.

**Chamado em:** `get_gm_narrative()` em `game.py`

**Temperatura:** 0.75 (criativo mas consistente)

**Prompt padrão:**
```
Você é o Mestre de uma aventura RPG de fantasia gótica.
O jogador é um [CLASSE] chamado [NOME].

ESTADO ATUAL DO MUNDO:
- Localização: [LOCAL]
- Cena: [DESCRIÇÃO]
- HP: [HP]/[MAX_HP]
- Inventário ([SLOTS_USADOS]/[MAX_SLOTS] slots): [ITENS]
- Missão ativa: [MISSÃO]
- NPCs presentes: [NPCS]
- Eventos recentes: [RESUMO]

DADOS DA CAMPANHA:
[NPCs, locais, itens relevantes]

REGRAS DA CLASSE [CLASSE]:
Pode: [lista de capacidades]
Não pode: [lista de restrições]

[GATILHO NARRATIVO — se houver]

AÇÃO DO JOGADOR: "[AÇÃO]"

Instruções:
1. Narre as consequências da ação de forma imersiva
2. Use [STATUS_UPDATE: hp_change=X] para alterações de HP
3. Use [INVENTORY_UPDATE: +Item] ou [-Item] para inventário
4. Inclua 2-4 objetos ESPECÍFICOS e NOMEADOS na cena
5. NUNCA ofereça múltipla escolha ao jogador
6. Termine com "O que você faz?"
7. Respeite as limitações da classe do personagem
8. Seja consistente com o tom gótico/melancólico da campanha
```

**Output esperado:**
```
[STATUS_UPDATE: hp_change=-3]

A criatura avança sobre você com garras afiadas...
[narrativa imersiva de 200-400 palavras]

O que você faz?
```

---

### 2. Mestre dos Contos (Story Mode)
**Função:** Adaptar eventos do mapa de contos usando o estilo do autor original.

**Chamado em:** `get_story_master_narrative()` em `game.py`

**Temperatura:** 0.75

**Prompt padrão:**
```
Você é o Mestre dos Contos, narrando "[NOME DO CONTO]".

TEXTO ORIGINAL (use como referência de estilo e vocabulário):
[conteúdo completo do .txt]

ESTADO DAS VARIÁVEIS DINÂMICAS:
[variavel]: [valor]
...

EVENTO ATUAL:
ID: [evento_id]
Contexto: [descricao_para_ia]

OPÇÕES DISPONÍVEIS:
(A) [texto_opcao_a]
(B) [texto_opcao_b]
(C) [texto_opcao_c]

Instruções:
1. Narre este evento usando o estilo e vocabulário do texto original
2. Use as variáveis para colorir emocionalmente a narrativa
3. Apresente as opções EXATAMENTE como listadas acima, ao final
4. Não adicione opções, não remova opções
5. Não quebre a quarta parede nem explique mecânicas
6. Termine obrigatoriamente com as opções formatadas
```

**Output esperado:**
```
[narrativa de 150-300 palavras no estilo do autor]

(A) Abrir a porta imediatamente
(B) Hesitar, ouvir o silêncio primeiro
(C) Mergulhar nos livros para ignorar
```

---

### 3. Archivista (State Manager)
**Função:** Extrair e atualizar estado do mundo a partir da narrativa gerada.

**Chamado em:** `update_world_state()` em `world_state_manager.py`

**Temperatura:** 0.2 (baixo — precisão > criatividade)

**Prompt padrão:**
```
Você é o Archivista — um sistema silencioso de gerenciamento de estado.
Analise a narrativa e retorne um JSON atualizado do estado do mundo.

ESTADO ATUAL:
[world_state_json]

ÚLTIMA NARRATIVA DO MESTRE:
[gm_narrative]

Retorne APENAS JSON válido (sem markdown, sem explicação) com estes campos:
{
  "interactable_elements_in_scene": [lista de substantivos/objetos mencionados],
  "important_npcs_in_scene": {nome: breve descrição do NPC na cena},
  "current_location_key": "mesma localização ou nova se mudou",
  "recent_events_summary": [últimos 5 eventos, incluindo este]
}

REGRAS:
- interactable_elements: apenas substantivos concretos (não verbos, adjetivos)
- Exemplos válidos: "cadeira", "janela", "espada", "corvo", "taverneiro"
- Exemplos inválidos: "brilhante", "correr", "noite"
- recent_events: cada item deve ser 1 frase curta descrevendo o evento
```

**Output esperado:**
```json
{
  "interactable_elements_in_scene": ["janela", "corvo", "gárgula", "diário", "figura"],
  "important_npcs_in_scene": {
    "Figura Encapuzada": "Observa o personagem da rua com atenção suspeita"
  },
  "current_location_key": "umbraton",
  "recent_events_summary": [
    "Chegou às portas de Umbraton ao anoitecer",
    "Conversou com o porteiro desconfiado",
    "Um corvo pousou na gárgula e o diário vibrou",
    "Observou a cidade pela janela e avistou figura encapuzada"
  ]
}
```

---

## Configuração do Cliente Gemini

```python
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config={
        "temperature": 0.75,
        "max_output_tokens": 1024,
    },
    safety_settings=[
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
)
```

**Por que BLOCK_NONE?** A narrativa gótica e dramática da plataforma frequentemente inclui temas de morte, medo, violência fantástica e psicologia sombria — necessários para a autenticidade literária.

---

## Tratamento de Erros

```python
try:
    response = model.generate_content(prompt)
    return response.text
except Exception as e:
    # Log silencioso
    return fallback_narrative
```

**Fallbacks:**
- Gemini indisponível → mensagem padrão pedindo para tentar novamente
- Archivista falha → manter estado anterior sem atualizar
- Story Master falha → exibir texto do evento diretamente sem narração IA

---

## Estimativa de Custo

Baseado em uso típico de 1 hora de jogo:

| Persona       | Tokens por chamada | Chamadas/hora | Total/hora |
|---------------|-------------------|---------------|------------|
| Mestre RPG    | ~2.000 in + 500 out| 30            | ~75.000    |
| Story Master  | ~5.000 in + 400 out| 10            | ~54.000    |
| Archivista    | ~1.500 in + 200 out| 30            | ~51.000    |
| **Total**     |                   |               | **~180.000**|

Gemini 1.5-Flash: ~$0.075/1M input tokens, ~$0.30/1M output tokens
**Custo estimado: ~$0.02–0.05 por hora de jogo**

---

## Estratégias de Prompt Engineering

### 1. Personagem fixo no sistema
Cada persona tem instruções de sistema que não mudam entre chamadas, economizando tokens de prompt.

### 2. Contexto mínimo necessário
O Archivista recebe apenas o necessário para extrair estado — não recebe dados de campanha completos.

### 3. Output estruturado para Archivista
JSON puro sem markdown reduz erros de parsing e economiza tokens.

### 4. Temperatura diferenciada por persona

| Persona       | Temperature | Razão                                      |
|---------------|-------------|---------------------------------------------|
| Mestre RPG    | 0.75        | Criativo mas consistente com o mundo         |
| Story Master  | 0.75        | Fiel ao estilo do autor mas com vida         |
| Archivista    | 0.20        | Precisão máxima, zero criatividade necessária|
