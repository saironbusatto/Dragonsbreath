# Diagrama de Atividades

## 1. Atividade Principal — Sessão de Jogo

```mermaid
flowchart TD
    START([Iniciar]) --> LOAD{Save existe?}

    LOAD -->|Sim| ASK{Continuar?}
    LOAD -->|Não| OPEN[Sequência de abertura]

    ASK -->|Sim| LOAD_STATE[Carregar estado]
    ASK -->|Não| OPEN

    OPEN --> MODE{Selecionar modo}
    LOAD_STATE --> ROUTE{Qual modo?}

    MODE -->|RPG| SEL_CAMP[Selecionar campanha]
    MODE -->|Conto| SEL_STORY[Selecionar conto]

    ROUTE -->|rpg| RPG_LOOP[Loop RPG]
    ROUTE -->|story| STORY_LOOP[Loop Conto]

    SEL_CAMP --> INIT_RPG[Inicializar personagem + mundo]
    INIT_RPG --> RPG_LOOP

    SEL_STORY --> LOAD_STORY[Carregar texto + eventos]
    LOAD_STORY --> STORY_LOOP

    RPG_LOOP --> RPG_END{Saiu com chikito?}
    STORY_LOOP --> STORY_END{Evento final?}

    RPG_END -->|Sim| END([Fim])
    STORY_END -->|Sim| STATS[Exibir estatísticas]
    STATS --> END

    RPG_END -->|Não| RPG_LOOP
    STORY_END -->|Não| STORY_LOOP
```

---

## 2. Atividade — Processamento de Ação RPG

```mermaid
flowchart TD
    INPUT[Receber input do jogador] --> IS_CMD{É comando especial?}

    IS_CMD -->|inventario| SHOW_INV[Exibir inventário]
    IS_CMD -->|status/vida| SHOW_HP[Exibir HP]
    IS_CMD -->|chikito| SAVE_EXIT[Salvar e sair]
    IS_CMD -->|Não| EXTRACT[Extrair objetos da ação]

    SHOW_INV --> INPUT
    SHOW_HP --> INPUT
    SAVE_EXIT --> END([Fim])

    EXTRACT --> VALIDATE{Todos objetos<br/>estão na cena?}

    VALIDATE -->|Não| ERR[Exibir erro amigável]
    ERR --> INPUT

    VALIDATE -->|Sim| TRIGGER{Calcular P gatilho<br/>P = 0.3 + rounds×0.1}

    TRIGGER -->|random() < P| FIRE_TRIGGER[Adicionar gatilho ao prompt]
    TRIGGER -->|Não disparou| BUILD_PROMPT[Construir prompt]

    FIRE_TRIGGER --> MOVE_TRIGGER[Mover gatilho para usados]
    MOVE_TRIGGER --> NEXT_TRIGGER[Ativar próximo na cadeia]
    NEXT_TRIGGER --> RESET_COUNTER[rodadas_sem_gatilho = 0]
    RESET_COUNTER --> BUILD_PROMPT

    BUILD_PROMPT --> CALL_GEMINI[Chamar Gemini Mestre]

    CALL_GEMINI --> PARSE[Parsear resposta]

    PARSE --> HAS_STATUS{[STATUS_UPDATE]?}
    HAS_STATUS -->|Sim| UPDATE_HP[Atualizar HP]
    HAS_STATUS -->|Não| HAS_INV{[INVENTORY_UPDATE]?}
    UPDATE_HP --> HAS_INV

    HAS_INV -->|Sim| UPDATE_INV[Atualizar inventário]
    HAS_INV -->|Não| AUDIO

    UPDATE_INV --> AUDIO

    AUDIO --> PLAY_SFX[Disparar SFX contextuais]
    AUDIO --> NARRATE[Narrar em voz TTS]

    PLAY_SFX --> ARCHIVISTA[Chamar Gemini Archivista]
    NARRATE --> ARCHIVISTA

    ARCHIVISTA --> UPDATE_STATE[Atualizar world_state]
    UPDATE_STATE --> INC_COUNTER[Incrementar rodadas_sem_gatilho]
    INC_COUNTER --> SAVE[Salvar estado em JSON]
    SAVE --> CHIME[Tocar chime]
    CHIME --> INPUT
```

---

## 3. Atividade — Conto Interativo

```mermaid
flowchart TD
    START[Evento atual carregado] --> IS_FINAL{Evento final_*?}

    IS_FINAL -->|Sim| SHOW_STATS[Exibir variáveis finais]
    SHOW_STATS --> END([Encerrar])

    IS_FINAL -->|Não| BUILD_PROMPT[Construir prompt Story Master<br/>texto original + evento + variáveis]

    BUILD_PROMPT --> CALL_AI[Chamar Gemini Story Master]

    CALL_AI --> SHOW_TEXT[Exibir narrativa + opções A/B/C]

    SHOW_TEXT --> PLAY_SFX[Disparar SFX ambientais]
    SHOW_TEXT --> NARRATE[Narrar em voz TTS]

    PLAY_SFX --> CHIME[Tocar chime]
    NARRATE --> CHIME

    CHIME --> GET_CHOICE[Aguardar escolha A/B/C]

    GET_CHOICE --> IS_VALID{A, B ou C?}
    IS_VALID -->|Não| GET_CHOICE

    IS_VALID -->|Sim| GET_OPCAO[Buscar opção escolhida]

    GET_OPCAO --> APPLY_EFFECT[Aplicar efeito nas variáveis]
    APPLY_EFFECT --> NEXT_EVENT[Avançar para proximo_evento]
    NEXT_EVENT --> START
```

---

## 4. Atividade — Sistema TTS

```mermaid
flowchart TD
    CALL[text_to_speech chamado] --> TRY_GOOGLE[Tentar Google Cloud TTS]

    TRY_GOOGLE --> GOOGLE_OK{Disponível?}

    GOOGLE_OK -->|Sim| GOOGLE_SYNTH[Sintetizar audio pt-BR Neural]
    GOOGLE_SYNTH --> SAVE_MP3[Salvar MP3 temporário]
    SAVE_MP3 --> PLAY[pygame.mixer.play]
    PLAY --> DONE([Concluído])

    GOOGLE_OK -->|Não| TRY_PYTTS[Tentar pyttsx3 local]

    TRY_PYTTS --> PYTTS_OK{Disponível?}
    PYTTS_OK -->|Sim| PYTTS_PLAY[pyttsx3.say + runAndWait]
    PYTTS_PLAY --> DONE

    PYTTS_OK -->|Não| TRY_EL[Tentar ElevenLabs]

    TRY_EL --> EL_KEY{API key configurada?}
    EL_KEY -->|Sim| EL_REQUEST[POST /v1/text-to-speech]
    EL_REQUEST --> EL_OK{Request OK?}

    EL_OK -->|Sim| STREAM[Reproduzir stream de audio]
    STREAM --> DONE

    EL_OK -->|Não| NO_AUDIO[Sem áudio — só texto no terminal]
    EL_KEY -->|Não| NO_AUDIO
    NO_AUDIO --> DONE
```

---

## 5. Atividade — Validação de Ações do Jogador

```mermaid
flowchart TD
    ACTION[Ação recebida: "Pego a espada na mesa"] --> TOKENIZE[Tokenizar string<br/>por espaços/split]

    TOKENIZE --> FILTER_STOP[Remover stop words<br/>artigos, preposições, verbos comuns]

    FILTER_STOP --> EXTRACT_NOUNS[Extrair substantivos candidatos<br/>espada, mesa, corvo, porta...]

    EXTRACT_NOUNS --> CHECK_SCENE[Verificar cada objeto<br/>em interactable_elements_in_scene]

    CHECK_SCENE --> ALL_FOUND{Todos encontrados?}

    ALL_FOUND -->|Sim| VALID[Ação VÁLIDA — prosseguir]

    ALL_FOUND -->|Não| FIND_MISSING[Listar objetos não encontrados]

    FIND_MISSING --> BUILD_ERROR[Construir mensagem de erro:<br/>"X não está presente. Você vê: [cena atual]"]

    BUILD_ERROR --> SHOW_ERROR[Exibir para jogador]
    SHOW_ERROR --> RETRY[Aguardar nova ação]
```
