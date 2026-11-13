# Handoff — mesa multijogador, etapa 2 (motor de grupo)

Atualizado em 2026-11-08. **4a feito (`b5a0755`). 4b feito (`ae846d2` formato e validação em `item_catalog.py`; `975b663` motor confere a cena). Próxima tarefa: passo 4c (rascunho do catálogo da Death House para o usuário revisar).** Comece por ele sem refazer o grilling: as decisões abaixo já foram aprovadas pelo usuário.

## Como trabalhar com o usuário

- Fala português. Quer uma pergunta por vez, com recomendação, quando houver decisão nova. Não assuma decisão que não foi tomada.
- Antes de implementar, confirme o entendimento. O plano do passo 4 abaixo já foi aceito; começar o 4a não precisa de nova confirmação.
- TDD: teste primeiro (vermelho), depois o código. A suíte inteira precisa passar (376 testes no `3a8e31b`).
- Snapshot de `/api/action` em `tests/snapshots/action_responses.json`: se mudar, **mostre o diff ao usuário antes** de regravar com `UPDATE_ACTION_SNAPSHOT=1`.
- Antes de cada commit, verifique em um worktree limpo, sem `.env` e sem chaves de API (`git worktree add <scratchpad>/wt HEAD`, depois rodar o pytest lá).
- Commits pequenos e descritivos em português (`feat(gm_tags): ...`). Push só quando o usuário pedir.
- Nunca mostre os valores do `.env` nem de tokens; só os nomes das variáveis. Áudio nunca é armazenado. Use o CLI `cf` para a Cloudflare.
- Um hook (GateGuard) bloqueia o primeiro Bash, Edit ou Write da sessão: diga o pedido atual e o que o comando faz, depois repita a chamada.

## Contexto

Ressoar é um RPG por voz (FastAPI, sessões em memória, saves em SQLite, login com Clerk). O modo "mesa" roda no PC do usuário, e os amigos entram por link (WebRTC P2P + TURN da Cloudflare, até 5 jogadores).

Etapas:
- 0 e 1: feitas;
- 2: motor de grupo (atual);
- 3: servidor de salas, WebRTC e TURN;
- 4: página `/mesa`;
- 5: o solo continua funcionando.

## O que já existe (passos 1–3, todos no GitHub)

| Commit | Passo | Resumo |
|---|---|---|
| `b503a2a` | 1 | `party.py`: `world_state["party"]`, `ensure_party`, `activate` e `commit_active`. `player_character` é a visão do membro ativo. `ENGINE_KEYS = ("party","flags","facts")`, que ficam escondidas do Mestre e do Arquivista. |
| `33c9784` | 2 | `gm_tags.py`: `extract` e `apply` das tags `[HP] [ITEM] [COND] [FATO] [FLAG] [MODO]`, mais as antigas `STATUS_UPDATE` e `INVENTORY_UPDATE`. Cada tag é conferida, a recusada não muda nada, e cada mudança gera um evento de ficha (`sheet_events` na resposta). O Arquivista não pode mexer na ficha. Flags da campanha são semeadas com `ensure_flags`. |
| `3a8e31b` | 3 | `build_world_memory_block`: as flags e os fatos relevantes (da sala, de NPC em cena, os 5 recentes, no máximo 15) entram no prompt do Mestre. |

Pontos do código:
- `game.py` → `clean_and_process_ai_response(text, ws, roll_result)`: aplica as tags e grava `_sheet_events` e `_tags_rejected`, chaves transitórias que precisam ser retiradas com `pop`.
- `web_api.py` → `_run_turn`: ordem GM → clean → Arquivista em paralelo com o TTS. O Arquivista recebe `gm_response` **cru, com tags**.
- `world_state_manager.py` → `update_world_state`: o Arquivista devolve o JSON completo; o motor restaura `ENGINE_KEYS` e `player_character`.
- Logs: `_record_turn` grava em `turn_logs/`, incluindo `tags_rejected`.
- Ainda não existe contador de turnos no estado; o 4a precisa de um para marcar os fatos.
- O prompt do Mestre (`game.py` ~832) ainda ensina as tags antigas; isso muda no passo 7.

## Decisões aprovadas

**Motor de grupo (Q13–Q23):**
- Flags fixas da campanha e fatos abertos ficam no estado e são salvos.
- Fatos vêm de `[FATO]` e do Arquivista, sem duplicata (mesmo texto normalizado na mesma sala).
- `[FLAG]` só vale se a flag existir e houver rolagem bem-sucedida.
- O grupo pode se separar; nesse caso o jogo vai para turnos alternando os locais.
- O personagem pertence à mesa (link + apelido).
- Jogador desconectado: o personagem fica parado e a vez dele é pulada.
- A ficha muda só por tag e gera evento.
- O Arquivista só cuida do mundo e aponta as tags esquecidas.
- A escala do combate conta os conectados na sala.
- O solo é uma mesa de um jogador.

**Passo 4 (Q24–Q34):**
- **Q24:** item que não existe na cena é sempre recusado.
- **Q26:** todo item tem categoria com campos mecânicos. Lista base do motor: `luz` (alcance, duração, precisa de fogo, chance de apagar), `chave` (`abre`), `consumivel` (efeito em tag, usos), `arma`, `armadura`, `ferramenta` (o que permite: fogo, arrombar...), `recipiente`, `tesouro`, `narrativo`. A campanha pode acrescentar categorias próprias. O motor valida o catálogo ao carregar.
- **Q25 (implícita):** a fonte da verdade é o catálogo; o mapa de cena sozinho não basta.
- **Q27:** relógio de jogo no motor:
  - exploração: +10 minutos por turno;
  - rodada de combate: 6 segundos (passo 5);
  - saltos de tempo pela tag `[TEMPO:+3d]` ou `[TEMPO:+8h]`;
  - ao avançar, o motor gasta as durações e rola a chance de apagar.
- **Q28–Q29:** item vinculado (`abre: <flag>`) vale como sucesso automático, **só se a ação do jogador cita o item** (nome ou apelido, normalizado) e o personagem que age está com ele. A flag pode ter `exige_rolagem: true`.
- **Q30:** item escondido tem dificuldade (9, 12, 15 ou 18) e local.
  - Se a fala cita o local, acha sem rolar.
  - Busca vaga rola contra a dificuldade.
  - Teste passivo ao entrar na sala.
  - Repetir é livre e gasta 10 minutos.
- **Q31:** segredos em níveis: 0 oculto (só o motor sabe), 1 pista (texto da campanha), 2 revelado (vira fato).
  - Passivo ou busca parcial (até 3 abaixo da dificuldade) libera a pista.
  - Fala no local certo ou sucesso completo revela.
  - Vale para itens e para o `segredo_oculto` da sala, que **sai do prompt do Mestre**.
  - Segredos de NPC continuam no prompt; o Arquivista aponta quando vazarem.
- **Q32:** NPC e inimigo têm `itens: [ids]`. O item sai por:
  - saque com 0 de HP, sem rolar;
  - troca `[ITEM:npc>Mira:id]`, conferida pelo motor;
  - roubo, com rolagem de Destreza.

  NPC improvisado só recebe itens marcados `livre: true`.
- **Q33:** catalogar primeiro só Curse of Strahd, começando pela Death House. As outras campanhas ficam com `catalogo_estrito: false` no `config.json`, aceitando e registrando no log.
- **Q34:** pendência de tag esquecida é cobrada do Mestre por 1 turno. Se for ignorada, cai e vai para `turn_logs/`.

## Plano do passo 4 (aceito)

1. **4a – Arquivista conferente (FEITO, `b5a0755`).** O Arquivista devolve, numa chave raiz extra (por exemplo `conferencia`), que o motor retira com `pop` antes de guardar o estado:
   - fatos novos, com entidades envolvidas;
   - fatos desfeitos;
   - mudanças de ficha que a narração sugeriu sem tag;
   - segredo de NPC dito explicitamente.

   O motor então:
   - grava os fatos com dedup, entidades e turno (criar o contador de turnos);
   - marca os desfeitos como `active: False`;
   - guarda as pendências e as injeta no prompt do Mestre no turno seguinte, um turno só;
   - registra as ignoradas no log.

   Cuidado: o Arquivista roda em paralelo com o TTS e depois do `clean`, então as pendências valem para o **próximo** turno.
2. **4b – Catálogo com categorias** e validação ao carregar; `catalogo_estrito`; `[ITEM:+]` só com item presente na sala, com o NPC ou `livre`; saque. Mostrar o formato do catálogo ao usuário antes do 4c.
3. **4c – Rascunho do catálogo da Death House** (`campanhas/curse_of_strahd/`) para o usuário revisar.
4. **4d – Chaves e vínculos.**
5. **4e – Segredos em níveis e busca** (passivo, busca vaga, fala no local).
6. **4f – Relógio do jogo.**

Depois: passo 5 (modos livre e de turnos), passo 6 (combate escalado), passo 7 (prompt do Mestre para o grupo, com as tags novas no lugar das antigas).

Dados de hoje:
- Curse of Strahd: 22 de 80 salas têm `itens_fixos` com id; nenhum item do catálogo tem categoria; NPCs sem itens.
- Lamento do Bardo (a campanha ativa) e exemplo_fantasia: sem itens nas salas.

## Estado depois do 4b (2026-11-12)

- **Q35:** item definido uma vez no catálogo (`itens_comuns.json` / `itens_magicos.json`, com `categoria`, `apelidos`, `livre` e os campos da categoria). Salas usam `itens: [{id, qtd, escondido: {dificuldade, local, pista}}]` e NPCs usam `itens: [ids]`.
- **Q36:** item largado fica no chão da sala; `consumivel` é gasto e some.
- `item_catalog.load()` valida a campanha com `catalogo_estrito: true` (nenhuma tem ainda). `item_catalog.scene()` monta o que está ao alcance e `gm_tags.apply(..., scene=)` confere. O saldo de itens por sala e por NPC fica em `world_state["stock"]`, chave do motor.
- Correções da auditoria do 4a em `cdd6470`: pendência já aplicada não é cobrada (evita dano em dobro), limites de tamanho, fato desfeito só na sala, resposta não-objeto do Arquivista.
- **Falta no 4b, para tratar junto do 4c:** o prompt do Mestre ainda lista `itens_fixos` (campo antigo) e não os itens ao alcance do campo novo `itens`. Sem isso, o Mestre de uma campanha estrita não sabe o que pode entregar.
- **Depende do passo 6:** saque só com inimigo a 0 de HP e roubo com rolagem. Hoje o motor só confere que o NPC em cena tem o item.
- **Em aberto da auditoria:** fatos parecidos com textos diferentes se acumulam; não há teste de ponta a ponta de `/api/action` até `turn_logs/`; o Arquivista real não foi testado com a regra 10.
