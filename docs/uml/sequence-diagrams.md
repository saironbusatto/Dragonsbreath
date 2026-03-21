# Diagramas de Sequência

## 1. Inicialização da Plataforma

```mermaid
sequenceDiagram
    participant User
    participant main
    participant AudioManager
    participant GeminiClient
    participant FileSystem

    User->>main: python game.py
    main->>AudioManager: inicializar pygame
    main->>FileSystem: verificar estado_do_mundo.json

    alt Jogo salvo existe
        FileSystem-->>main: world_state data
        main->>User: "Continuar jogo anterior? (s/n)"
        User-->>main: "s"
        main->>main: load_world_state()
    else Novo jogo
        main->>AudioManager: play_ressoar_opening_sequence()
        AudioManager->>User: [Áudio: sequência de abertura]
        main->>User: Exibir menu de modo
        User-->>main: "RPG" ou "Conto"
    end
```

---

## 2. Fluxo Completo — Turno RPG

```mermaid
sequenceDiagram
    participant Player
    participant GameEngine
    participant Validator
    participant GeminiMestre
    participant GeminiArchivista
    participant AudioManager
    participant FileSystem

    Player->>GameEngine: input (texto ou voz)

    alt Comando especial
        GameEngine->>GameEngine: execute_command()
        GameEngine-->>Player: resultado do comando
    else Ação narrativa
        GameEngine->>Validator: extract_objects_from_action(input)
        Validator-->>GameEngine: [objetos encontrados]

        GameEngine->>Validator: validate_player_action(objetos, cena_atual)

        alt Ação inválida
            Validator-->>GameEngine: FAIL + motivo
            GameEngine-->>Player: "Esse objeto não está presente..."
        else Ação válida
            Validator-->>GameEngine: OK

            GameEngine->>GameEngine: calcular probabilidade de gatilho

            opt Gatilho dispara
                GameEngine->>GameEngine: adicionar gatilho ao prompt
            end

            GameEngine->>GeminiMestre: get_gm_narrative(world_state, ação)
            GeminiMestre-->>GameEngine: narrativa + [STATUS/INVENTORY updates]

            GameEngine->>GameEngine: parse [STATUS_UPDATE]
            GameEngine->>GameEngine: parse [INVENTORY_UPDATE]

            par Áudio paralelo
                GameEngine->>AudioManager: trigger_contextual_sfx(narrativa)
                AudioManager->>AudioManager: play_sfx()
            and Narração
                GameEngine->>AudioManager: narrator_speech(narrativa)
                AudioManager-->>Player: [Áudio: narração]
            end

            GameEngine->>GeminiArchivista: update_world_state(world_state, narrativa)
            GeminiArchivista-->>GameEngine: world_state atualizado

            GameEngine->>FileSystem: save_world_state()
            FileSystem-->>GameEngine: OK

            GameEngine->>AudioManager: play_chime()
            AudioManager-->>Player: [Áudio: chime]
        end
    end
```

---

## 3. Fluxo Completo — Turno Conto Interativo

```mermaid
sequenceDiagram
    participant Player
    participant GameEngine
    participant GeminiStoryMaster
    participant AudioManager

    GameEngine->>GameEngine: carregar evento atual

    alt Evento é final
        GameEngine-->>Player: exibir estatísticas finais
        GameEngine->>AudioManager: narrator_speech(conclusão)
    else Evento normal
        GameEngine->>GeminiStoryMaster: get_story_master_narrative(texto_original, evento, vars)
        GeminiStoryMaster-->>GameEngine: narrativa + (A)(B)(C)

        par Saída paralela
            GameEngine->>Player: exibir texto narrativo
        and
            GameEngine->>AudioManager: trigger_contextual_sfx(narrativa)
        and
            GameEngine->>AudioManager: narrator_speech(narrativa)
            AudioManager-->>Player: [Áudio: narração]
        end

        GameEngine->>AudioManager: play_chime()
        AudioManager-->>Player: [Áudio: chime]

        Player->>GameEngine: "A", "B" ou "C"

        GameEngine->>GameEngine: opcao.efeito → aplicar em variáveis
        GameEngine->>GameEngine: current_evento = opcao.proximo_evento

        GameEngine->>GameEngine: (próxima iteração do loop)
    end
```

---

## 4. Sistema TTS com Fallback

```mermaid
sequenceDiagram
    participant Caller
    participant AudioManager
    participant GoogleCloudTTS
    participant pyttsx3
    participant ElevenLabs

    Caller->>AudioManager: text_to_speech(texto, voz)

    AudioManager->>GoogleCloudTTS: sintetizar(texto, voz_config)

    alt Google Cloud TTS disponível
        GoogleCloudTTS-->>AudioManager: audio_bytes
        AudioManager->>AudioManager: salvar MP3 temp
        AudioManager->>AudioManager: pygame.mixer.play()
        AudioManager-->>Caller: OK
    else Google Cloud TTS falhou
        AudioManager->>pyttsx3: say(texto)

        alt pyttsx3 disponível
            pyttsx3-->>AudioManager: playback local
            AudioManager-->>Caller: OK
        else pyttsx3 falhou
            AudioManager->>ElevenLabs: POST /v1/text-to-speech

            alt ElevenLabs disponível
                ElevenLabs-->>AudioManager: audio_stream
                AudioManager->>AudioManager: pygame.mixer.play()
                AudioManager-->>Caller: OK
            else ElevenLabs falhou
                AudioManager-->>Caller: (sem áudio, só texto)
            end
        end
    end
```

---

## 5. Validação Semântica de Ações

```mermaid
sequenceDiagram
    participant Player
    participant GameEngine
    participant WorldState
    participant GeminiArchivista

    Player->>GameEngine: "Pego a espada que está em cima da mesa"

    GameEngine->>GameEngine: extract_objects_from_action()
    Note over GameEngine: objetos = ["espada", "mesa"]

    GameEngine->>WorldState: get interactable_elements_in_scene
    WorldState-->>GameEngine: ["cadeira", "janela", "espada", "lareira"]

    GameEngine->>GameEngine: verificar intersecção
    Note over GameEngine: "espada" ∈ cena ✓
    Note over GameEngine: "mesa" ∉ cena ✗

    alt Todos objetos válidos
        GameEngine->>GeminiMestre: [ação prossegue normalmente]
    else Objeto inválido encontrado
        GameEngine-->>Player: "Não há mesa nesta cena. Você vê: cadeira, janela, espada, lareira."
    end

    Note over GeminiArchivista: Após narração, Archivista extrai<br/>novos interactable_elements da cena
    GameEngine->>GeminiArchivista: "Quais objetos há nesta nova cena?"
    GeminiArchivista-->>GameEngine: ["porta", "candelabro", "livro antigo", "espelho"]
    GameEngine->>WorldState: atualizar interactable_elements_in_scene
```

---

## 6. Sistema de Gatilhos Narrativos

```mermaid
sequenceDiagram
    participant GameEngine
    participant WorldState
    participant GeminiMestre

    GameEngine->>WorldState: localização atual?
    WorldState-->>GameEngine: "umbraton"

    GameEngine->>WorldState: gatilhos_ativos["umbraton"]?
    WorldState-->>GameEngine: ["corvo_na_gargula"]

    GameEngine->>WorldState: rodadas_sem_gatilho?
    WorldState-->>GameEngine: 3

    GameEngine->>GameEngine: P = min(0.9, 0.3 + 3 × 0.1) = 0.6
    GameEngine->>GameEngine: random() < 0.6 → DISPARA

    GameEngine->>WorldState: mover "corvo_na_gargula" para gatilhos_usados
    GameEngine->>WorldState: ativar próximo: "diario_vibra"
    GameEngine->>WorldState: rodadas_sem_gatilho = 0

    GameEngine->>GeminiMestre: prompt + [GATILHO: "Um corvo pousa na gárgula..."]
    GeminiMestre-->>GameEngine: narrativa com evento do corvo integrado
```

---

## 7. Seleção e Início de Campanha

```mermaid
sequenceDiagram
    participant Player
    participant GameEngine
    participant CampaignManager
    participant FileSystem
    participant WorldStateManager
    participant GeminiMestre

    Player->>GameEngine: selecionar RPG
    GameEngine->>CampaignManager: listar campanhas disponíveis
    CampaignManager->>FileSystem: ler config.json
    FileSystem-->>CampaignManager: config data
    CampaignManager-->>GameEngine: lista de campanhas

    GameEngine-->>Player: "1. O Lamento do Bardo\n2. A Busca pelo Cristal..."
    Player->>GameEngine: "1"

    GameEngine->>CampaignManager: set_campaign("lamento_do_bardo")
    CampaignManager->>FileSystem: atualizar config.json

    GameEngine->>CampaignManager: load_campaign_data()
    CampaignManager->>FileSystem: ler npcs.json, locais.json, itens_*.json, campanha.md
    FileSystem-->>CampaignManager: todos os dados
    CampaignManager-->>GameEngine: campaign_data

    GameEngine->>GeminiMestre: tutorial_introduction(campaign_data)
    GeminiMestre-->>GameEngine: narração introdutória

    GameEngine-->>Player: [Áudio: narração intro + tutorial]

    Player->>GameEngine: nome do personagem

    GameEngine->>WorldStateManager: create_initial_world_state(template, nome)
    WorldStateManager-->>GameEngine: world_state inicial

    GameEngine->>FileSystem: save_world_state()
    GameEngine->>GameEngine: new_game_loop()
```
