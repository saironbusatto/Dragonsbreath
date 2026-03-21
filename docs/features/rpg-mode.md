# Modo RPG

## Visão Geral

O Modo RPG é um sistema de narrativa interativa de mundo aberto onde o jogador escreve (ou fala) livremente o que seu personagem faz, e um Mestre de Jogo com IA (Gemini) responde com narrativas ricas e consequentes.

A característica central é a **Validação Semântica de Ações**: o jogador só pode interagir com objetos explicitamente presentes na cena descrita.

---

## Sistema de Validação Semântica

### Problema Resolvido
Em jogos de RPG com IA pura, o jogador pode fazer coisas absurdas como "pego a espada invisível" ou "uso o jetpack" sem que o sistema detecte inconsistências.

### Solução Implementada
Após cada narrativa do Mestre, o AI Archivista extrai os objetos interativos mencionados. Antes de processar qualquer ação, o sistema verifica se os objetos mencionados pelo jogador realmente existem na cena.

```
Cena: "Você entra na taverna. Uma mesa de carvalho ocupa o centro,
       sobre ela um cálice de vinho e uma vela acesa. O taverneiro
       limpa um copo atrás do balcão."

Objetos disponíveis: [mesa, cálice, vinho, vela, taverneiro, copo, balcão]

Ação VÁLIDA: "Pego o cálice e olho para o taverneiro"
Ação INVÁLIDA: "Pego a espada que está no chão"
→ "Não há espada no chão. Você vê: mesa, cálice, vela, taverneiro..."
```

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
Gatilhos são eventos narrativos pré-escritos que injetam cenas dramáticas no jogo sem depender da ação do jogador. Garantem dinamismo mesmo em períodos de exploração passiva.

### Cadeia de Gatilhos
Gatilhos podem encadear uns nos outros, criando arcos narrativos progressivos:

```
[Ato 1 — Umbraton]

corvo_na_gargula
"Um corvo pousa em uma gárgula e grasna. Seu diário vibra."
    │ proximo_gatilho
    ▼
diario_vibra
"O diário vibra com mais intensidade. Parece querer ser aberto."
    │ proximo_gatilho
    ▼
(null — cadeia encerrada)
```

### Probabilidade Crescente
```
Rodada 1: P = 30%  (pode ou não disparar)
Rodada 2: P = 40%  (sem gatilho na rodada anterior)
Rodada 3: P = 50%  (sem gatilho nas 2 anteriores)
...
Rodada 7: P = 90%  (máximo — quase garantido)

Quando dispara → P resetada para 30%
```

### Localização dos Gatilhos
Cada localização tem sua própria lista de gatilhos. Ao mudar de localização, os gatilhos da nova área ficam disponíveis.

---

## Classes de Personagem

### Bardo
**Filosofia:** Personagem de suporte, investigação e interação social.

| Aspecto        | Detalhe                                     |
|----------------|---------------------------------------------|
| HP Inicial     | 20                                          |
| Slots Iniciais | 6/10 usados                                 |
| Estilo de jogo | Resolução criativa, persuasão, arte         |
| Fraquezas      | Combate direto, força bruta                 |

**Pode:**
- Tocar instrumentos musicais de formas criativas
- Persuadir, enganar e convencer NPCs
- Investigar e deduzir pistas
- Contar histórias que distraem ou inspiram

**Não pode:**
- Usar magia diretamente
- Voar ou movimentar-se sobrenaturalmente
- Ressuscitar mortos
- Usar força bruta em situações que exigem poder físico excepcional

### Aventureiro
**Filosofia:** Personagem robusto de exploração e combate.

| Aspecto        | Detalhe                                     |
|----------------|---------------------------------------------|
| HP Inicial     | 25                                          |
| Slots Iniciais | 10/10 usados (inventário cheio no início)   |
| Estilo de jogo | Combate, exploração, força                  |
| Fraquezas      | Situações sociais sutis, magia              |

**Pode:**
- Combater com armas e escudo
- Explorar terrenos perigosos
- Usar ferramentas e sobreviver ao ar livre
- Intimidar fisicamente

**Não pode:**
- Usar magia
- Voar
- Habilidades sobrenaturais

---

## Sistema de HP e Combate

O sistema de HP é controlado via tags na narrativa do Mestre:

```
Mestre narra: "A criatura ataca você causando [STATUS_UPDATE: hp_change=-5]..."
game.py parseia: world_state["player_character"]["status"]["hp"] -= 5

Bardo usa poção: "Você bebe a poção [STATUS_UPDATE: hp_change=+10]..."
game.py parseia: world_state["player_character"]["status"]["hp"] += 10
```

O HP nunca ultrapassa `max_hp` e nunca cai abaixo de 0 (morte = fim de jogo).

---

## Progressão de Atos

O `current_act` avança quando o Mestre narra uma transição de ato. O sistema detecta isso e carrega o contexto do novo ato.

```
Ato 1 → Ato 2: após completar a missão principal do Ato 1
Ato 2 → Ato 3: após completar a missão principal do Ato 2
```

Cada ato tem:
- Novas localizações disponíveis
- Novos gatilhos ativos
- NPCs diferentes ou em situações diferentes
- Missões atualizadas

---

## Comandos Disponíveis (RPG)

| Comando           | Efeito                                          |
|-------------------|-------------------------------------------------|
| `inventário`      | Lista todos os itens com slots usados/total     |
| `inventario`      | (sem acento) mesmo efeito                       |
| `status`          | Exibe HP atual / HP máximo + classe             |
| `saúde`           | Mesmo que status                                |
| `vida`            | Mesmo que status                                |
| `chikito`         | Salva o jogo e encerra                          |
| Qualquer outra coisa | Processada como ação narrativa pelo Mestre |

---

## Fluxo de um Turno Completo

```
1. [CHIME] — sistema sinaliza que está pronto

2. Jogador: "Vou até a janela e olho para a rua lá embaixo"

3. Sistema extrai objetos: ["janela", "rua"]

4. Sistema verifica: "janela" ∈ cena atual? SIM → OK

5. Sistema calcula: P_gatilho = 0.5, random() = 0.3 → DISPARA!
   → Adiciona ao prompt: "Um corvo pousa na gárgula e grasna"

6. Gemini gera:
   "Você se aproxima da janela envelhecida, cujos vidros refletem
   a luz amarelada das lanternas. Lá embaixo, Umbraton respira
   pesadamente — carroças passam, figuras encurvadas caminham.

   De repente, um corvo pousa na gárgula ao lado da janela e
   emite um grasnido agudo. Ao mesmo tempo, seu diário na mochila
   vibra — uma vez, duas vezes.

   Na rua abaixo, você avista uma figura encapuzada que para e
   olha diretamente para cima, na sua direção.

   O que você faz?"

7. SFX: "corvo" detectado → toca creepy-crow-caw.mp3

8. TTS: narra o texto em voz pt-BR Neural2-B

9. Archivista extrai: interactable = ["janela", "vidros", "lanternas",
                                       "carroças", "corvo", "gárgula",
                                       "diário", "figura encapuzada"]

10. Estado salvo em estado_do_mundo.json

11. [CHIME] — pronto para próxima ação
```
