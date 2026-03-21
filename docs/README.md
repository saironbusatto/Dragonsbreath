# Plataforma Ressoar — Documentação Técnica

> Plataforma de narrativas interativas com IA, áudio imersivo e RPG de mundo aberto.

---

## Indice

### Arquitetura
- [Visão Geral da Arquitetura](architecture/overview.md)
- [Fluxo de Dados](architecture/data-flow.md)
- [Stack Tecnológica](architecture/stack.md)

### UML
- [Diagrama de Classes](uml/class-diagram.md)
- [Diagramas de Sequência](uml/sequence-diagrams.md)
- [Diagramas de Estado](uml/state-diagrams.md)
- [Diagrama de Componentes](uml/component-diagram.md)
- [Diagrama de Casos de Uso](uml/use-case-diagram.md)
- [Diagrama de Atividades](uml/activity-diagram.md)

### Entidades & Modelos
- [Entidades do Sistema](entities/entities.md)

### Módulos
- [game.py — Motor Principal](modules/game.md)
- [audio_manager.py — Sistema de Áudio](modules/audio.md)
- [world_state_manager.py — Estado do Mundo](modules/world_state.md)
- [campaign_manager.py — Campanhas](modules/campaign.md)

### Funcionalidades
- [Modo RPG](features/rpg-mode.md)
- [Modo Contos Interativos](features/story-mode.md)

### API & Integrações
- [Integração com IA (Gemini)](api/ai-integration.md)
- [Sistema de Áudio (TTS/SFX)](api/audio-api.md)

### Campanhas
- [O Lamento do Bardo](campaigns/lamento-do-bardo.md)
- [A Busca pelo Cristal Perdido](campaigns/cristal-perdido.md)

---

## Resumo do Projeto

| Atributo       | Valor                                       |
|----------------|---------------------------------------------|
| Nome           | Plataforma Ressoar                          |
| Linguagem      | Python 3.8+                                 |
| IA             | Google Gemini 1.5-Flash                     |
| TTS            | Google Cloud TTS (pt-BR Neural)             |
| Audio Engine   | pygame                                      |
| Modos          | RPG de mundo aberto + Contos Interativos    |
| Campanhas      | 2 campanhas prontas, sistema extensível     |
| Contos         | 1 conto pronto (O Corvo — Poe)              |
| Arquivos Audio | 15 efeitos sonoros MP3                      |
| Entrada        | Texto e reconhecimento de voz               |

---

## Início Rápido

```bash
# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas chaves API

# Executar
python game.py
```
