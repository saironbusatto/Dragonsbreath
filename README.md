# Plataforma Ressoar

Plataforma de narrativas interativas com IA generativa, narração por voz neural e efeitos sonoros contextuais. Dois modos de jogo: RPG de mundo aberto e Contos Interativos baseados em literatura clássica.

---

## Modos de Jogo

### Modo RPG

Aventura open-world onde o jogador escreve livremente o que seu personagem faz. Um Mestre com IA (Gemini) responde com narrativas consequentes, respeitando o estado do mundo, o inventário e as limitações da classe escolhida.

- Sistema de validação semântica — só é possível interagir com objetos presentes na cena atual
- Inventário com slots (capacidade por peso, não por quantidade)
- Gatilhos narrativos com probabilidade crescente, garantindo dinamismo
- Estado persistente salvo automaticamente a cada turno

**Campanhas disponíveis:**

- **O Lamento do Bardo** — narrativa gótica sobre perda, ilusão e o poder da música (classe: Bardo)
- **A Busca pelo Cristal Perdido** — aventura clássica de fantasia (classe: Aventureiro)

### Modo Contos Interativos

Adaptações de obras literárias clássicas com escolhas ramificadas (A/B/C) que influenciam variáveis dinâmicas e determinam o final da história. A IA narra usando o estilo e vocabulário do autor original.

**Contos disponíveis:**

- **O Corvo** (Edgar Allan Poe) — 4 finais possíveis, variáveis: sanidade, esperança, obsessão, aceitação

---

## Instalação

```bash
# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas chaves de API

# Executar
python game.py
```

---

## APIs Necessárias

| API | Obrigatório | Uso |
| --- | --- | --- |
| [Google Gemini](https://ai.google.dev/) | Sim | Narrativa com IA (Mestre, Story Master, Archivista) |
| [Google Cloud TTS](https://cloud.google.com/text-to-speech) | Recomendado | Voz neural pt-BR (~$4/1M chars) |
| [ElevenLabs](https://elevenlabs.io/) | Não | TTS premium alternativo (~$22/1M chars) |

```env
GEMINI_API_KEY=sua_chave_aqui
GOOGLE_APPLICATION_CREDENTIALS=/caminho/para/service-account.json
GOOGLE_CLOUD_PROJECT=seu-projeto-id
ELEVENLABS_API_KEY=sua_chave_aqui  # opcional
```

Se nenhum TTS estiver configurado, a plataforma funciona normalmente exibindo apenas texto.

---

## Comandos

### Comandos do Modo RPG

| Comando | Ação |
| --- | --- |
| `inventário` | Exibe itens e slots usados/total |
| `status` / `saúde` / `vida` | Exibe HP atual e máximo |
| `chikito` | Salva e encerra |
| Qualquer outra entrada | Enviada como ação ao Mestre do Jogo |

### Comandos do Modo Conto

| Comando | Ação |
| --- | --- |
| `A`, `B` ou `C` | Escolhe entre as opções narrativas |

---

## Estrutura do Projeto

```text
Dragonsbreath/
├── game.py                     # Motor principal — loops de jogo e lógica de negócio
├── audio_manager.py            # TTS, SFX e reconhecimento de voz
├── world_state_manager.py      # Estado do mundo RPG e AI Archivista
├── campaign_manager.py         # Carregamento de dados de campanhas
├── config.json                 # Configuração declarativa das campanhas
├── .env.example                # Template de variáveis de ambiente
├── requirements.txt            # Dependências Python
├── test_plataforma_ressoar.py  # Testes de verificação da plataforma
├── estado_do_mundo.json        # Save automático do jogo (gerado em runtime)
├── campanhas/
│   ├── lamento_do_bardo/       # NPCs, locais, itens e narrativa da campanha gótica
│   └── exemplo_fantasia/       # NPCs, locais, itens e narrativa da campanha clássica
├── contos_interativos/
│   ├── o_corvo_poe.txt         # Texto original de referência (estilo do autor)
│   └── o_corvo_poe_eventos.json # Mapa de eventos, escolhas e variáveis dinâmicas
├── sons/sistema/               # 15 efeitos sonoros MP3 disparados contextualmente
└── docs/                       # Documentação técnica completa
```

---

## Stack Tecnológica

- **Python 3.8+**
- **Google Gemini 1.5-Flash** — narrativa com IA (3 personas: Mestre, Story Master, Archivista)
- **Google Cloud TTS** — vozes neurais pt-BR (Neural2-A feminina / Neural2-B masculina, 1.5x velocidade)
- **pygame** — engine de reprodução de áudio
- **SpeechRecognition + pyaudio** — entrada por voz
- **pyttsx3** — TTS local offline (fallback automático)

---

## Testes

```bash
python test_plataforma_ressoar.py
```

Verifica estrutura de arquivos, configurações de campanhas, integridade dos contos e importações de funções.

---

## Documentação Técnica

A pasta [docs/](docs/README.md) contém a documentação completa do sistema:

- [Visão geral da arquitetura](docs/architecture/overview.md)
- [Fluxo de dados](docs/architecture/data-flow.md)
- [Diagrama de classes UML](docs/uml/class-diagram.md)
- [Diagramas de sequência](docs/uml/sequence-diagrams.md)
- [Diagramas de estado](docs/uml/state-diagrams.md)
- [Entidades do sistema](docs/entities/entities.md)
- [Integração com IA](docs/api/ai-integration.md)

---

## Solução de Problemas

**`GEMINI_API_KEY` não configurada**
Configure a chave no arquivo `.env`. Sem ela a plataforma não consegue gerar narrativas.

**`ModuleNotFoundError`**
Execute `pip install -r requirements.txt` para instalar todas as dependências.

**Sem áudio / erro de TTS**
A plataforma funciona sem áudio — verifique o `.env` se quiser ativar TTS. O fallback textual é automático.

**Microfone não reconhecido**
Instale `pyaudio` e verifique os drivers do dispositivo. Entrada por teclado funciona normalmente sem microfone.

---

*Plataforma Ressoar — onde cada som conta uma história única.*
