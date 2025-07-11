# RPG Modular com IA - Sistema de Estado do Mundo

Sistema avançado de RPG de texto com IA usando **Estado do Mundo** e **Gatilhos Narrativos Encadeados**.
Suporta múltiplas campanhas intercambiáveis com eventos dinâmicos e progressivos.

## 🚀 Como Jogar

### Instalação Rápida
1. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```
   Ou execute: `install_audio.bat`

2. **Configure as APIs no arquivo .env:**
   ```
   GEMINI_API_KEY=sua_chave_gemini
   ELEVENLABS_API_KEY=sua_chave_elevenlabs
   ```

3. **Execute o jogo:**
   ```bash
   python game.py
   ```

### Alternativas de Execução
- **Script automático:** `start_game.bat` (Windows)
- **Com verificação:** `python iniciar_jogo.py`

## 🎮 Comandos no Jogo

### Comandos Básicos
- `inventário` - Ver seus itens
- `status` - Ver sua saúde e HP
- `chikito` - Salvar e sair

### Sistema de Áudio 🎵
- **Narração por voz**: O Mestre fala usando ElevenLabs
- **Reconhecimento de voz**: Fale suas ações ou digite
- **Entrada híbrida**: Microfone + teclado sempre disponíveis

### Comandos Avançados
- `usar [item]` - Consumir poções ou itens
- `descartar [item]` - Remover itens do inventário
- `reiniciar` - Começar novo jogo

### Interação com IA
- **Qualquer outra ação** vai para a IA Mestre do Jogo
- **Exemplos:** "Olho ao redor", "Falo com o taverneiro", "Entro na taverna"

## 🏗️ Arquitetura do Sistema

### Arquivos Principais
- **`game.py`** - Motor principal do jogo
- **`world_state_manager.py`** - Gerenciamento do estado do mundo
- **`campaign_manager.py`** - Sistema modular de campanhas
- **`iniciar_jogo.py`** - Script de verificação e inicialização

### Sistema de Duas IAs
1. **IA Mestre do Jogo** - Narra eventos e responde às ações
2. **IA Arquivista** - Atualiza o estado do mundo silenciosamente

## 🌍 Sistema de Estado do Mundo

### Estrutura do Estado
```json
{
  "player_character": {
    "name": "Nome do Jogador",
    "class": "Bardo",
    "current_act": 1,
    "status": {"hp": 20, "max_hp": 20},
    "inventory": ["item1", "item2"],
    "desejo": "Objetivo principal do personagem"
  },
  "world_state": {
    "current_location_key": "local_atual",
    "immediate_scene_description": "Descrição da cena",
    "active_quests": {"quest_id": "descrição"},
    "important_npcs_in_scene": {"npc_id": "status"},
    "recent_events_summary": ["evento1", "evento2"],
    "gatilhos_ativos": {"local": ["gatilho1", "gatilho2"]},
    "gatilhos_usados": {"local": ["gatilho_usado"]}
  }
}
```

### Vantagens do Sistema
- **Custo reduzido**: Chamadas de API sempre pequenas
- **Sem limite de tokens**: Jogo pode durar indefinidamente
- **Memória persistente**: Estado conciso e relevante
- **Narrativa consistente**: IA foca no estado atual

## 🎭 Sistema de Gatilhos Narrativos

### Gatilhos Encadeados
```json
{
  "corvo_na_gargula": {
    "descricao": "Um corvo de olhos brancos o encara do topo de uma gárgula.",
    "proximo": "diario_vibra"
  },
  "diario_vibra": {
    "descricao": "Seu diário vibra levemente, como se algo estivesse reagindo a ele.",
    "proximo": null
  }
}
```

### Sistema de Chance Progressiva
- **Base**: 30% de chance por turno
- **Acúmulo**: +10% por rodada sem evento
- **Máximo**: 90% (mantém imprevisibilidade)
- **Reset**: Volta a 30% após evento

### Tipos de Gatilhos
- **Independentes**: Eventos únicos sem sequência
- **Encadeados**: Criam narrativas progressivas
- **Específicos por local**: Cada lugar tem sua atmosfera

## 🗺️ Sistema Modular de Campanhas

### Estrutura de Campanhas
```
campanhas/
├── lamento_do_bardo/          # Campanha sombria sobre peste e dragão
│   ├── npcs.json             # Personagens não-jogáveis
│   ├── itens_magicos.json    # Itens mágicos e artefatos
│   ├── itens_comuns.json     # Itens consumíveis e comuns
│   ├── locais.json           # Locações com gatilhos
│   └── campanha.md           # História e narrativa
└── exemplo_fantasia/          # Aventura clássica de fantasia
    ├── npcs.json
    ├── itens_magicos.json
    ├── itens_comuns.json
    ├── locais.json
    └── campanha.md
```

### Configuração de Campanhas
O arquivo `config.json` define:
- **Campanha ativa**
- **Templates de personagem** (classe, HP, inventário inicial)
- **Templates de mundo** (descrição inicial, objetivo principal)
- **Caminhos dos arquivos** de cada campanha

## 🛠️ Gerenciar Campanhas

### Criar Nova Campanha
```bash
python gerenciar_campanhas.py
```

**Opções disponíveis:**
1. **Listar campanhas** - Ver todas as campanhas disponíveis
2. **Trocar campanha** - Mudar para outra campanha
3. **Criar nova campanha** - Gerar template automaticamente

### Personalizar Campanha
1. **Edite os arquivos JSON:**
   - `npcs.json` - Seus personagens únicos
   - `itens_magicos.json` - Artefatos especiais
   - `itens_comuns.json` - Itens básicos e consumíveis
   - `locais.json` - Lugares com gatilhos narrativos

2. **Escreva a história:**
   - `campanha.md` - Narrativa principal e atos

3. **Configure templates:**
   - `config.json` - Personagem inicial e mundo

## 📁 Arquivos de Save

### Salvamento Automático
- **`estado_do_mundo.json`** - Estado completo do jogo
- **Salvamento a cada turno** - Nunca perde progresso
- **Comando `chikito`** - Salva e sai do jogo

### Compatibilidade
- **Saves são específicos por campanha**
- **Trocar campanha requer novo jogo**
- **Estado preserva gatilhos e progressão**

## 🎯 Recursos Avançados

### Sistema de Atos
- **Progressão automática** por atos da campanha
- **Conteúdo filtrado** - NPCs e itens aparecem no ato correto
- **Escalabilidade** - Adicione quantos atos quiser

### Comandos da IA
A IA pode usar comandos especiais:
```
[STATUS_UPDATE] {"hp_change": -4}     # Altera HP do jogador
[INVENTORY_UPDATE] {"add": ["item"]}  # Adiciona/remove itens
```

### Regras da IA Mestre
1. Narra resultado baseado no estado do mundo
2. Gera consequências claras para cada ação
3. Adiciona eventos durante exploração
4. Oferece escolhas claras ao jogador
5. Considera objetivos do personagem
6. Nunca se repete - sempre algo novo
7. Termina com "O que você faz?"

## 🔧 Desenvolvimento

### Estrutura de Arquivos
```
Dragons Breath/
├── game.py                    # Motor principal
├── world_state_manager.py     # Gerenciamento de estado
├── campaign_manager.py        # Sistema de campanhas
├── config.json               # Configuração das campanhas
├── campanhas/                # Campanhas modulares
├── v1/ e v2/                 # Versões antigas
└── README.md                 # Esta documentação
```

### Dependências
- **Python 3.8+**
- **google-generativeai** - API do Gemini
- **pygame** - Reprodução de áudio
- **SpeechRecognition** - Reconhecimento de voz
- **pyaudio** - Captura de áudio do microfone
- **requests** - Comunicação com ElevenLabs
- **python-dotenv** - Carregamento de variáveis de ambiente

### Extensibilidade
- **Adicione novas campanhas** facilmente
- **Crie gatilhos personalizados** por local
- **Defina NPCs únicos** com segredos ocultos
- **Configure itens especiais** com efeitos

## 🎪 Campanhas Incluídas

### O Lamento do Bardo
**Gênero:** Horror Gótico / Mistério
- **História:** Investigação sobre praga misteriosa e dragão disfarçado
- **Atmosfera:** Sombria, melancólica, cheia de segredos
- **Personagem:** Bardo em busca da verdade sobre a morte da esposa
- **Locais:** Umbraton (cidade gótica), tavernas sombrias, bibliotecas assombradas

### A Busca pelo Cristal Perdido
**Gênero:** Fantasia Medieval Clássica
- **História:** Aventura para recuperar artefato mágico perdido
- **Atmosfera:** Heroica, aventureira, com criaturas fantásticas
- **Personagem:** Aventureiro corajoso em missão de salvamento
- **Locais:** Vila pacífica, floresta sombria, masmorras antigas

## 🚨 Solução de Problemas

### Erro de API Key
```
O Mestre do Jogo não consegue se conectar aos planos astrais.
```
**Solução:** Configure `GEMINI_API_KEY` nas variáveis de ambiente

### Erro de Importação
```
ModuleNotFoundError: No module named 'google.generativeai'
```
**Solução:** Execute `pip install google-generativeai`

### Arquivo Corrompido
```
Arquivo de estado corrompido.
```
**Solução:** O jogo apaga automaticamente e inicia novo jogo

## 📈 Roadmap Futuro

### Recursos Planejados
- [ ] **Sistema de combate** tático
- [ ] **Múltiplos finais** por campanha
- [ ] **Editor visual** de campanhas
- [ ] **Compartilhamento** de campanhas
- [ ] **Modo multiplayer** cooperativo
- [ ] **Geração procedural** de eventos
- [ ] **Sistema de reputação** com NPCs
- [ ] **Crafting** de itens personalizados

### Melhorias Técnicas
- [ ] **Interface gráfica** opcional
- [ ] **Suporte a outros modelos** de IA
- [ ] **Sistema de plugins** para extensões
- [ ] **API REST** para integrações
- [ ] **Modo offline** com IA local

---

## 🎮 Comece Sua Aventura!

```bash
# Configuração rápida
set GEMINI_API_KEY=sua_chave_aqui
python game.py
```

**Bem-vindo ao futuro dos RPGs com IA!** 🐉✨