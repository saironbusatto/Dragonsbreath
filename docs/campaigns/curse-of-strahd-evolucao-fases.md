# Curse of Strahd — Evolução das Fases 1-7

## Objetivo

Este documento consolida as mudanças implementadas para elevar o Mestre IA ao estilo narrativo cinematográfico, consistente e punitivo de Baróvia, com foco em:

- contrato narrativo forte;
- continuidade de interpretação de NPCs;
- combate cinematográfico;
- ritmo emocional anti-fadiga;
- ressurreição com custo narrativo;
- QA de ponta a ponta para campanha modular.

---

## Fase 1 — Contrato Narrativo (Prompt v2)

Implementado:

- regra inegociável de narração em segunda pessoa no presente;
- "brevidade forçada" (1-4 frases);
- lente cinematográfica condensada em 5 camadas;
- regra "Você certamente pode tentar." para agência sem prometer sucesso;
- narrativa informada pelos dados, sem humilhar jogador em falhas.

Resultado:

- prompt do Mestre padronizado e protegido por testes de regressão.

---

## Fase 2 — NPCs Preparados + Improvisados com Memória Persistente

Implementado:

- assinatura de NPC com raiz:
  - motivação principal;
  - intenção na interação;
  - linguagem corporal;
  - voz textual;
  - camada externa/camada oculta;
- persistência dessas assinaturas no estado do mundo;
- comportamento consistente entre sessões longas.

Resultado:

- NPCs críticos de Baróvia (ex.: Strahd, Rictavio/Van Richten, Vistani) com atuação estável.

---

## Fase 3 — Combate Cinematográfico + [HDYWDTDT]

Implementado:

- estado tático de combate (`combat_state`) com identificação de ameaça significativa;
- regra de clímax para gatilho `[HDYWDTDT]` apenas em final letal relevante;
- remoção da tag no texto final e destaque do momento no backend/frontend;
- gradiente visual de dano em vez de HP numérico exposto.

Resultado:

- combate mais dramático, com autoridade narrativa entregue ao jogador no golpe final.

---

## Fase 4 — Ritmo Emocional e Espaço Negativo (ma)

Implementado:

- rastreador de pacing (`emotional_pacing`) com:
  - `consecutive_high_tension_turns`;
  - `force_relief_next`;
  - `negative_space_beats`;
- silêncio físico opcional em picos dramáticos;
- tag `[PAUSE_BEAT]` com interceptação de backend para pausa real no áudio.

Resultado:

- redução de fadiga de horror e melhor cadência entre pressão e alívio.

---

## Fase 5 — Ressurreição com Peso Narrativo

Implementado:

- interceptação de morte (`hp == 0`) para cena de limbo baroviano;
- oferenda emocional obrigatória antes da rolagem;
- escala de dificuldade por morte:
  - 1a morte: DC 12;
  - 2a morte: DC 15;
  - 3a+ morte: DC 18;
- consequências persistentes:
  - loucura de ressurreição;
  - Dark Gift;
  - corrupção total em falha crítica;
- persistência de:
  - `death_count`;
  - `resurrection_flaws`;
  - `alignment`.

Resultado:

- mortalidade com custo dramático real, coerente com Baróvia.

---

## Fase 6/7 — Ajuste Fino + QA Narrativo Completo

Cenários validados:

1. Strahd em padrão "gato e rato" com saída estratégica de combate.
2. Coleta de artefatos Tarokka (Tomo, Símbolo, Espada) sem bloqueio semântico indevido.
3. Calibragem de classe:
   - Bardo com vantagem social;
   - Aventureiro com desvantagem em persuasão.
4. Anti-fadiga:
   - sequência de tensão forçando batida de alívio.
5. Pós-morte completo:
   - 4 mortes com DC escalado;
   - persistência de Dark Gift e corrupção.

Resultado final:

- suíte completa: `243 passed`.

---

## Arquivos-Chave Impactados

- `game.py`
- `world_state_manager.py`
- `web_api.py`
- `static/index.html`
- `campanhas/curse_of_strahd/npcs.json`
- `tests/test_game.py`
- `tests/test_world_state_manager.py`
- `tests/test_integration.py`

---

## Estado Atual do Sistema

- contrato narrativo e pacing estão acoplados ao loop principal;
- backend já trata `HDYWDTDT` e `PAUSE_BEAT` para UX de tensão;
- ressurreição está integrada a CLI/API com persistência;
- QA de Baróvia cobre stress narrativo, semântica de cena e regressão mecânica.
