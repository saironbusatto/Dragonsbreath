# Modo RPG

## Visão Geral

O Modo RPG é um sistema de narrativa interativa de mundo aberto onde o jogador fala livremente o que seu personagem faz, e um Mestre de Jogo com IA (OpenAI GPT-4o-mini) responde com narrativas imersivas e consequentes.

Características centrais:

- **Validação Semântica de Ações**: o jogador só pode interagir com objetos presentes na cena
- **HUD Narrativo (Olhos do Jogador)**: consultas de inspeção respondidas por voz feminina sem avançar o tempo
- **Sistema de Dados Shadowdark**: rolagens automáticas d20 com vantagem/desvantagem por classe
- **Brevidade Forçada**: narrações de 1-4 frases, nunca repetindo elementos já descritos
- **STT via Whisper**: OpenAI Whisper (`gpt-4o-mini-transcribe`) para alta acurácia em pt-BR

---

## Sistema de Validação Semântica

### Problema Resolvido

Em RPGs com IA pura, o jogador pode interagir com objetos que não existem na cena. A validação semântica impede isso.

### Solução: Mapa Semântico da Cena

Após cada narrativa, o Archivista extrai os elementos em um **dicionário estruturado** (não mais lista plana):

```
Cena narrada: "O taverneiro limpa uma caneca atrás do balcão.
               Uma vela acesa ilumina a porta ao norte."

→ interactable_elements_in_scene:
  objetos:   ["balcão", "vela"]
  npcs:      ["taverneiro"]
  npc_itens: { "taverneiro": ["caneca"] }
  saidas:    ["porta ao norte"]
  containers: {}
  chao:      []
```

A função `_flatten_scene_map()` achata esse dicionário em tokens para validação:
`["balcão", "vela", "taverneiro", "caneca", "porta ao norte"]`

```
Ação VÁLIDA:   "Falo com o taverneiro sobre a caneca"
Ação INVÁLIDA: "Pego a espada do chão"
→ "Não há nenhuma 'espada' aqui para você interagir."
```

### Retrocompatibilidade

`_flatten_scene_map()` aceita tanto o formato novo (dict) quanto o antigo (list), garantindo que saves existentes continuem funcionando.

---

## HUD Narrativo — Olhos do Jogador

### Conceito

Consultas de inspeção são interceptadas **antes** de chegar ao Mestre do Jogo. O tempo do jogo não avança, o Archivista não é chamado, os gatilhos não progridem.

```
Jogador:  "O que eu tenho na mochila?"
Sistema:  detecta → is_inspection_action() → "inventory"
          → get_player_eyes_response() com contexto {inventory, slots}
          → voz FEMININA (pt-BR-Neural2-A)
          → retorna { inspection: true }

Jogador:  "Como estou de saúde?"
Sistema:  detecta → "health"
          → contexto {status, classe}
          → voz feminina

Jogador:  "O que tem ao meu redor?"
Sistema:  detecta → "environment"
          → contexto {local, descrição, mapa semântico completo}
          → "Você está na taverna do Corvo Ferido. O taverneiro
             carrega uma caneca e uma chave enferrujada.
             Há uma porta ao norte e uma escada ao fundo."
```

### Keywords de Inspeção Detectadas

| Tipo | Exemplos |
|------|---------|
| `inventory` | "inventário", "bolsa", "meus itens", "o que eu tenho", "meu equipamento" |
| `health` | "status", "saúde", "como estou", "meu hp", "estou ferido" |
| `environment` | "ao meu redor", "onde estou", "o que tem aqui", "o que eu vejo" |

### Distinção Auditiva

| Voz | Quando | Significado percebido |
|-----|--------|-----------------------|
| Masculina (Neural2-B) | Mestre narra | "O mundo está acontecendo" |
| Feminina (Neural2-A) | Olhos do Jogador | "Minha consciência / interface" |

---

## Sistema de Dados Shadowdark

### Filosofia

Inspirado no Shadowdark RPG: **só role quando há risco real e a falha seria interessante**. Ações rotineiras têm sucesso automático — o Mestre narra livremente.

### Classes de Dificuldade (DC)

| DC | Nome | Quando usar |
|----|------|-------------|
| 9 | Fácil | Tarefas simples |
| 12 | Normal | Maioria dos desafios (padrão) |
| 15 | Difícil | Ação menciona "pesado", "reforçado", "ferrenho", "habilidoso" |
| 18 | Extremo | Ação menciona "impossível", "invencível", "extremamente" |

### Vantagem e Desvantagem por Classe

| Classe | Vantagem (2d20 → maior) | Desvantagem (2d20 → menor) |
|--------|--------------------------|---------------------------|
| Bardo | persuasão, mentira, música, investigação | força bruta, combate físico |
| Aventureiro | combate, atletismo, intimidação | persuasão, furtividade, magia |

### Verbos que Disparam Rolagem

Exemplos: `convencer`, `mentir`, `enganar`, `escalar`, `arrombar`, `atacar`, `esquivar`, `roubar`, `decifrar`, `desarmar`.

Ações sem risco (sem rolagem): `caminhar`, `entrar em`, `sentar`, `olhar para`, `pegar o` (objeto acessível).

### Fluxo de uma Rolagem

```
1. Jogador: "Tento convencer o guarda de que sou um enviado do Santuário"

2. resolve_action_roll():
   - "convencer" → rolagem necessária
   - "habilidoso" ausente → DC 12
   - Bardo + "convencer" → Vantagem
   - Rola 2d20: [4, 16] → usa 16
   - 16 ≥ 12 → success: true

3. Frontend:
   transcript: "🎲 4 / 16 → 16  ·  DC 12  ·  Vantagem  ·  Sucesso"  (verde)
   som de dados rolando (awaitable)

4. Mestre recebe no prompt:
   [DADOS SHADOWDARK]
   Modificador: Vantagem | Dados: [4, 16] | Usado: 16 | DC: 12
   RESULTADO: SUCESSO — narre o jogador tendo sucesso.
   REGRA ABSOLUTA: narre ESTRITAMENTE conforme o resultado.

5. Mestre (voz masculina): "Silas estreita os olhos por um momento,
   mas sua lábia é perfeita. Ele suspira e desliza a chave pelo
   balcão. O que você faz?"
```

### Resultados Especiais

| Resultado | Condição | Instrução ao Mestre |
|-----------|----------|---------------------|
| Sucesso Crítico | roll == 20 | Narre resultado excepcional, além do esperado |
| Sucesso | roll ≥ DC | Narre o jogador tendo sucesso |
| Falha | roll < DC | Narre fracasso com complicação interessante |
| Falha Crítica | roll == 1 | Narre consequência grave ou reviravolta perigosa |

---

## Sistema de Inventário

### Capacidade por Slots

Cada personagem tem `max_slots` (padrão: 10). Cada item ocupa 1-2 slots.

```
BARDO (max_slots=10):
├── Alaúde          [2 slots]
├── Adaga           [1 slot]
├── Mochila         [1 slot]
├── Kit Viagem      [1 slot]
└── Kit Iluminação  [1 slot]
Total: 6/10 slots usados

AVENTUREIRO (max_slots=10):
├── Espada Longa    [2 slots]
├── Escudo          [2 slots]
├── Armadura Couro  [2 slots]
├── Mochila         [1 slot]
├── Corda           [1 slot]
└── Kits (2x)       [1 slot cada]
Total: 10/10 slots usados
```

### Lógica de Adição de Item

1. Calcular slots necessários para o novo item
2. Calcular slots usados atualmente
3. Se `usados + necessários > max_slots` → inventário cheio
4. Sistema sugere itens para largar
5. Jogador pode recusar → não pega o item

---

## Sistema de Gatilhos Narrativos

### Conceito

Gatilhos são eventos narrativos pré-escritos que injetam cenas dramáticas no jogo sem depender da ação do jogador. Garantem dinamismo mesmo em exploração passiva.

Cada gatilho em `locais.json` possui um campo `sfx` (keyword) que resolve para um URL de som via `_SFX_MAP` no servidor.

### Cadeia de Gatilhos

```
[Ato 1 — Umbraton]

corvo_na_gargula  (sfx: "corvo")
"Um corvo pousa em uma gárgula e grasna. Seu diário vibra."
    │ proximo_gatilho
    ▼
diario_vibra
"O diário vibra com mais intensidade."
    │ proximo_gatilho
    ▼
(null — cadeia encerrada)
```

### Probabilidade Crescente

```
Rodada 1: P = 30%
Rodada 2: P = 40%  (sem gatilho na rodada anterior)
...
Rodada 7: P = 90%  (máximo)
Quando dispara → P resetada para 30%
```

---

## Classes de Personagem

### Bardo

| Aspecto | Detalhe |
|---------|---------|
| HP Inicial | 20 |
| Slots Iniciais | 6/10 usados |
| Estilo de jogo | Investigação, persuasão, música |
| Vantagem nos dados | Persuasão, música, engano, investigação |
| Desvantagem nos dados | Força bruta, combate físico |

**Pode:** tocar instrumentos, persuadir, investigar, contar histórias, pequenos truques musicais.

**Não pode:** magia direta, voar, ressuscitar, força bruta excepcional.

### Aventureiro

| Aspecto | Detalhe |
|---------|---------|
| HP Inicial | 25 |
| Slots Iniciais | 10/10 usados |
| Estilo de jogo | Combate, exploração, força |
| Vantagem nos dados | Combate, atletismo, intimidação, sobrevivência |
| Desvantagem nos dados | Persuasão sutil, magia, furtividade |

**Pode:** combater, explorar terrenos perigosos, intimidar, sobreviver ao ar livre.

**Não pode:** magia, voar, habilidades sobrenaturais.

---

## Anti-Repetição Narrativa

O campo `recent_narrations` em `world_state` armazena os primeiros 300 caracteres das últimas 2 narrações. O Mestre do Jogo recebe esses dados no prompt e a **Rule 7 (ANTI-REPETIÇÃO)** instrui a IA a nunca redescrever o que já foi mencionado.

```python
# Atualizado a cada turno em web_api.py:
recent = world_state.get("recent_narrations", [])
recent.append(cleaned_narrative[:300])
world_state["recent_narrations"] = recent[-2:]
```

---

## Fluxo de um Turno Completo

```
[CHIME] — sistema pronto para ouvir

Jogador fala → MediaRecorder grava → POST /api/transcribe (Whisper)
→ texto transcrito → feedback de confirmação (voz feminina lê o que ouviu)
→ jogador confirma (silêncio 4s ou "sim") ou cancela

POST /api/action:

  ┌─ is_inspection_action()? ─────────────────────────────┐
  │  SIM → get_player_eyes_response()                      │
  │        voz feminina, inspection: true                  │
  │        tempo NÃO avança                                │
  └────────────────────────────────────────────────────────┘

  ┌─ validate_player_action()? ───────────────────────────┐
  │  INVÁLIDO → mensagem de erro + som de dissonância      │
  │             voz feminina, valid: false                 │
  └────────────────────────────────────────────────────────┘

  ┌─ resolve_action_roll()? ──────────────────────────────┐
  │  RISCO DETECTADO → rola d20 (±vantagem por classe)     │
  │  resultado injetado no prompt do Mestre               │
  └────────────────────────────────────────────────────────┘

  _select_trigger() → injeta gatilho se P disparar

  get_gm_narrative() → narrativa (1-4 frases)

  Frontend:
  1. 🎲 HUD do dado (se houver rolagem) — verde/vermelho
  2. som de dados rolando (awaitable)
  3. som do gatilho (se houver)
  4. narração TTS voz masculina
  5. SFX sincronizados com posição no texto

  update_world_state() → Archivista atualiza mapa semântico

[CHIME] → microfone abre
```

---

## Comandos de Inspeção (via Olhos do Jogador)

Qualquer frase contendo as keywords abaixo é roteada para o agente Olhos do Jogador — não chega ao Mestre, não conta como turno:

| Consulta | Dados retornados |
|---------|-----------------|
| "inventário", "minha mochila", "o que eu tenho" | inventory + slots usados/total |
| "status", "saúde", "como estou", "meu hp" | hp atual / máximo + classe |
| "ao meu redor", "onde estou", "o que tem aqui" | mapa semântico completo da cena |

**Comando de save (CLI):** `chikito` — salva e encerra.
