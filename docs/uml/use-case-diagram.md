# Diagrama de Casos de Uso

## Visão Geral

```mermaid
graph LR
    subgraph Atores["Atores"]
        P[Jogador]
        AI[Gemini AI]
        SYS[Sistema de Áudio]
    end

    subgraph UC_PLAT["Plataforma Ressoar"]

        subgraph UC_MODE["Seleção de Modo"]
            UC1[Iniciar Novo Jogo]
            UC2[Continuar Jogo Salvo]
            UC3[Selecionar Modo RPG]
            UC4[Selecionar Conto Interativo]
        end

        subgraph UC_RPG["Modo RPG"]
            UC5[Escolher Campanha]
            UC6[Nomear Personagem]
            UC7[Executar Ação Narrativa]
            UC8[Verificar Inventário]
            UC9[Verificar Status/HP]
            UC10[Salvar e Sair]
        end

        subgraph UC_STORY["Modo Conto Interativo"]
            UC11[Selecionar Conto]
            UC12[Ouvir Narrativa]
            UC13[Fazer Escolha A/B/C]
            UC14[Ver Estatísticas Finais]
        end

        subgraph UC_AUDIO["Sistema de Áudio"]
            UC15[Ouvir Narração em Voz]
            UC16[Ouvir Efeitos Sonoros]
            UC17[Falar via Microfone]
        end

        subgraph UC_AI["IA — Bastidores"]
            UC18[Gerar Narrativa RPG]
            UC19[Gerar Narrativa Conto]
            UC20[Atualizar Estado do Mundo]
        end

    end

    P --> UC1
    P --> UC2
    P --> UC3
    P --> UC4
    P --> UC5
    P --> UC6
    P --> UC7
    P --> UC8
    P --> UC9
    P --> UC10
    P --> UC11
    P --> UC12
    P --> UC13
    P --> UC14
    P --> UC15
    P --> UC16
    P --> UC17

    AI --> UC18
    AI --> UC19
    AI --> UC20

    UC7 --> UC18
    UC13 --> UC19
    UC18 --> UC20
    UC18 --> UC16
    UC19 --> UC16
    UC18 --> UC15
    UC19 --> UC15
```

---

## Casos de Uso Detalhados

### UC1 — Iniciar Novo Jogo

| Campo        | Descrição                                      |
|--------------|------------------------------------------------|
| **Ator**     | Jogador                                        |
| **Pré-cond.**| Plataforma instalada e configurada             |
| **Fluxo**    | 1. Executar `python game.py` <br> 2. Sem save encontrado <br> 3. Ouvir sequência de abertura <br> 4. Selecionar modo de jogo |
| **Pós-cond.**| Estado inicial criado para o modo escolhido    |

---

### UC2 — Continuar Jogo Salvo

| Campo        | Descrição                                          |
|--------------|----------------------------------------------------|
| **Ator**     | Jogador                                            |
| **Pré-cond.**| `estado_do_mundo.json` presente no diretório       |
| **Fluxo**    | 1. `python game.py` detecta save <br> 2. Pergunta ao jogador se quer continuar <br> 3. Carrega world_state do JSON <br> 4. Retoma no modo/ponto salvo |
| **Pós-cond.**| Jogo continua do estado salvo                      |

---

### UC7 — Executar Ação Narrativa (RPG)

| Campo        | Descrição                                                       |
|--------------|-----------------------------------------------------------------|
| **Ator**     | Jogador, Gemini AI                                              |
| **Pré-cond.**| Jogo RPG em andamento                                           |
| **Fluxo**    | 1. Jogador digita/fala ação <br> 2. Sistema valida objetos mencionados <br> 3. Calcula probabilidade de gatilho <br> 4. Envia prompt para Gemini <br> 5. Recebe narrativa <br> 6. Dispara SFX contextuais <br> 7. Narra em voz <br> 8. Archivista atualiza estado <br> 9. Salva em JSON |
| **Alt. 2a**  | Objeto inválido: exibe mensagem de erro, volta ao input         |
| **Pós-cond.**| Estado atualizado, narrativa narrada, jogo salvo               |

---

### UC13 — Fazer Escolha A/B/C (Conto)

| Campo        | Descrição                                                   |
|--------------|-------------------------------------------------------------|
| **Ator**     | Jogador                                                     |
| **Pré-cond.**| Conto em andamento, evento atual exibido                    |
| **Fluxo**    | 1. Jogador digita A, B ou C <br> 2. Sistema aplica efeitos nas variáveis <br> 3. Avança para próximo evento <br> 4. Verifica se é evento final |
| **Alt.**     | Input inválido: pede novamente                              |
| **Pós-cond.**| Variáveis atualizadas, novo evento carregado                |

---

### UC17 — Falar via Microfone

| Campo        | Descrição                                                        |
|--------------|------------------------------------------------------------------|
| **Ator**     | Jogador                                                          |
| **Pré-cond.**| pyaudio e SpeechRecognition configurados, microfone disponível  |
| **Fluxo**    | 1. Sistema emite chime (pronto para ouvir) <br> 2. Jogador fala <br> 3. Google STT converte para texto <br> 4. Texto processado como entrada normal |
| **Alt.**     | Falha de reconhecimento: solicitar repetição ou usar teclado    |
| **Pós-cond.**| Input de voz convertido em texto e processado normalmente       |

---

### UC20 — Atualizar Estado do Mundo (Archivista)

| Campo        | Descrição                                                           |
|--------------|---------------------------------------------------------------------|
| **Ator**     | Gemini AI (chamado automaticamente pelo sistema)                    |
| **Pré-cond.**| Narrativa do Mestre recebida                                        |
| **Fluxo**    | 1. Sistema envia world_state + narrativa para Gemini Archivista <br> 2. Gemini extrai objetos interativos mencionados <br> 3. Atualiza NPCs na cena <br> 4. Atualiza localização se mudou <br> 5. Adiciona evento ao resumo recente |
| **Pós-cond.**| `interactable_elements_in_scene` atualizado para validação futura  |
