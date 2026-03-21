# Diagramas de Estado

## 1. Estado da Plataforma (Geral)

```mermaid
stateDiagram-v2
    [*] --> Inicializando

    Inicializando --> VerificandoSave : pygame inicializado

    VerificandoSave --> CarregandoJogo : save encontrado + usuário confirma
    VerificandoSave --> SequenciaAbertura : sem save / novo jogo

    SequenciaAbertura --> SelecaoModo : abertura concluída

    CarregandoJogo --> ModoRPG : game_mode == "rpg"
    CarregandoJogo --> ModoConto : game_mode == "story"

    SelecaoModo --> ModoRPG : jogador escolhe RPG
    SelecaoModo --> ModoConto : jogador escolhe Conto

    ModoRPG --> Encerrado : comando "chikito"
    ModoConto --> Encerrado : evento final atingido
    ModoConto --> SelecaoModo : conto concluído

    Encerrado --> [*]
```

---

## 2. Estado do Loop RPG

```mermaid
stateDiagram-v2
    [*] --> AguardandoInput

    AguardandoInput --> ProcessandoComando : input é comando especial
    AguardandoInput --> ExtraindoObjetos : input é ação narrativa
    AguardandoInput --> Saindo : input é "chikito"

    ProcessandoComando --> ExibindoInventario : cmd inventário
    ProcessandoComando --> ExibindoStatus : cmd status/saúde/vida
    ExibindoInventario --> AguardandoInput
    ExibindoStatus --> AguardandoInput

    ExtraindoObjetos --> ValidandoAcao

    ValidandoAcao --> ErroAcaoInvalida : objeto não encontrado na cena
    ValidandoAcao --> VerificandoGatilhos : ação válida

    ErroAcaoInvalida --> AguardandoInput : feedback ao jogador

    VerificandoGatilhos --> GatilhoAtivado : P >= random
    VerificandoGatilhos --> ChamandoMestre : sem gatilho

    GatilhoAtivado --> ChamandoMestre : gatilho adicionado ao prompt

    ChamandoMestre --> ProcessandoNarrativa : Gemini responde

    ProcessandoNarrativa --> AtualizandoHP : [STATUS_UPDATE] detectado
    ProcessandoNarrativa --> AtualizandoInventario : [INVENTORY_UPDATE] detectado
    ProcessandoNarrativa --> ExecutandoAudio

    AtualizandoHP --> ExecutandoAudio
    AtualizandoInventario --> ExecutandoAudio

    ExecutandoAudio --> AtualizandoEstado : áudio concluído

    AtualizandoEstado --> SalvandoEstado : Archivista processou

    SalvandoEstado --> AguardandoInput : estado salvo em JSON

    Saindo --> [*]
```

---

## 3. Estado do Conto Interativo

```mermaid
stateDiagram-v2
    [*] --> CarregandoConto

    CarregandoConto --> EventoInicio : arquivos carregados

    EventoInicio --> GerandoNarrativa

    GerandoNarrativa --> ExibindoNarrativa : Gemini respondeu

    ExibindoNarrativa --> NarrandoAudio : texto exibido
    NarrandoAudio --> AguardandoEscolha : narração concluída

    AguardandoEscolha --> AplicandoEfeito : jogador escolheu A/B/C
    AguardandoEscolha --> AguardandoEscolha : escolha inválida

    AplicandoEfeito --> AtualizandoVariaveis

    AtualizandoVariaveis --> VerificandoFinal : variáveis atualizadas

    VerificandoFinal --> ExibindoEstatisticas : evento é final_*
    VerificandoFinal --> GerandoNarrativa : não é final

    ExibindoEstatisticas --> [*]
```

---

## 4. Estado do Sistema de Áudio

```mermaid
stateDiagram-v2
    [*] --> Ocioso

    Ocioso --> TentandoGoogleTTS : text_to_speech() chamado

    TentandoGoogleTTS --> ReproduziindoAudio : Google Cloud disponível
    TentandoGoogleTTS --> TentandoPyttsx3 : Google Cloud falhou

    TentandoPyttsx3 --> ReproduziindoAudio : pyttsx3 disponível
    TentandoPyttsx3 --> TentandoElevenLabs : pyttsx3 falhou

    TentandoElevenLabs --> ReproduziindoAudio : ElevenLabs disponível
    TentandoElevenLabs --> SemAudio : ElevenLabs falhou

    ReproduziindoAudio --> Ocioso : reprodução concluída
    SemAudio --> Ocioso : texto só exibido no terminal

    Ocioso --> ReproduziindoSFX : play_sfx() chamado
    ReproduziindoSFX --> Ocioso : SFX concluído

    Ocioso --> CapturandoVoz : speech_to_text() chamado
    CapturandoVoz --> ProcessandoVoz : voz capturada
    ProcessandoVoz --> Ocioso : texto retornado
```

---

## 5. Estado dos Gatilhos (por Localização)

```mermaid
stateDiagram-v2
    [*] --> NaoInicializado

    NaoInicializado --> ProntoParaDisparar : gatilho adicionado em gatilhos_ativos

    ProntoParaDisparar --> Aguardando : rodada passa sem disparo
    ProntoParaDisparar --> Disparado : probabilidade atingida

    Aguardando --> ProntoParaDisparar : próxima rodada
    note right of Aguardando
        P = min(0.9, 0.3 + rounds × 0.1)
        Aumenta a cada rodada
    end note

    Disparado --> IntegrandoNarrativa : texto do gatilho adicionado ao prompt

    IntegrandoNarrativa --> Consumido : narrativa narrada ao jogador

    Consumido --> EncadeandoProximo : tem proximo_gatilho definido
    Consumido --> [*] : não tem próximo

    EncadeandoProximo --> ProntoParaDisparar : próximo gatilho ativado
```

---

## 6. Estado do Inventário

```mermaid
stateDiagram-v2
    [*] --> InventarioDisponivel

    InventarioDisponivel --> AdicionandoItem : pegar item
    InventarioDisponivel --> RemovendoItem : largar/usar item

    AdicionandoItem --> VerificandoEspaco

    VerificandoEspaco --> ItemAdicionado : slots_usados + item.slots <= max_slots
    VerificandoEspaco --> InventarioCheio : slots insuficientes

    InventarioCheio --> OfertandoTroca : sugerir item para largar
    OfertandoTroca --> RemovendoItem : jogador escolhe item
    OfertandoTroca --> InventarioDisponivel : jogador cancela

    ItemAdicionado --> InventarioDisponivel : slot atualizado
    RemovendoItem --> InventarioDisponivel : item removido

    InventarioDisponivel --> ExibindoInventario : comando "inventário"
    ExibindoInventario --> InventarioDisponivel : exibição concluída
```

---

## 7. Estado da Persistência

```mermaid
stateDiagram-v2
    [*] --> SemSave

    SemSave --> CriandoEstadoInicial : novo jogo iniciado
    CriandoEstadoInicial --> EstadoEmMemoria : create_initial_world_state()

    SemSave --> CarregandoEstado : arquivo encontrado + confirmado
    CarregandoEstado --> EstadoEmMemoria : load_world_state()

    EstadoEmMemoria --> SalvandoEstado : fim de cada turno
    SalvandoEstado --> EstadoEmMemoria : save_world_state() concluído

    EstadoEmMemoria --> EstadoEmMemoria : mutações durante o jogo
    note right of EstadoEmMemoria
        Todas as mutações acontecem
        em memória. Persistência
        ocorre ao final de cada turno.
    end note

    EstadoEmMemoria --> [*] : jogo encerrado (chikito)
```
