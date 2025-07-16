# 🎵 Plataforma Ressoar

**Onde cada som conta uma história única.**

A Plataforma Ressoar é um sistema revolucionário de narrativas interativas que oferece duas experiências distintas:

- **🗡️ Modo RPG:** Aventuras completas com regras, inventário e liberdade total de ação
- **📖 Modo Conto Interativo:** Histórias clássicas adaptadas com escolhas e múltiplos finais

## 🚀 Instalação Rápida

1. **Clone o repositório:**
   ```bash
   git clone [url-do-repositorio]
   cd ressoar
   ```

2. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure as APIs:**
   ```bash
   cp .env.example .env
   # Edite .env com suas chaves de API
   ```

4. **Execute a plataforma:**
   ```bash
   python game.py
   ```

## 🔑 APIs Necessárias

- **Gemini API** (obrigatória): Para IA do jogo
- **Google Cloud TTS** (recomendada): Para áudio em português brasileiro
- **ElevenLabs** (opcional): Backup premium para TTS

## 🎮 Experiência de Jogo

### 🗡️ Modo RPG
- **Sistema de Interação Ambiental Dinâmica:** IA povoa cenários com objetos interativos
- **Inventário com Slots:** Sistema estratégico de 10 slots com kits iniciais balanceados
- **Múltiplas Campanhas:** Hub de aventuras com diferentes classes e cenários
- **Progressão Persistente:** Estado do mundo salvo automaticamente

### 📖 Modo Conto Interativo
- **Narrativas Clássicas:** Adaptações de obras literárias com IA especializada
- **Múltiplos Finais:** Escolhas que levam a destinos únicos
- **Variáveis Narrativas:** Sistema dinâmico de sanidade, esperança, etc.
- **Experiência Imersiva:** Áudio contextual e narração completa

### 🎵 Sistema de Áudio Completo
- **TTS Premium:** Google Cloud Neural2 em português brasileiro
- **SFX Contextuais:** Efeitos sonoros disparados automaticamente
- **Narração Completa:** Todas as partes da história são narradas
- **Chimes Indicativos:** Sinais sonoros para orientar interação

## 🎮 Comandos Básicos

### Modo RPG
- `inventário` - Ver seus itens e slots
- `status` - Ver sua saúde e HP
- `usar [item]` - Consumir poções ou itens
- `descartar [item]` - Remover itens do inventário
- `chikito` - Salvar e sair
- **Qualquer outra ação** vai para a IA Mestre do Jogo

### Modo Conto Interativo
- **A, B, C** - Escolher opções durante a narrativa
- **Navegação automática** - Sistema guia através da história

## 🏗️ Estrutura do Projeto

```
ressoar/
├── game.py                          # Motor principal da plataforma
├── audio_manager.py                 # Sistema de áudio completo
├── world_state_manager.py           # Gerenciamento de estado RPG
├── campaign_manager.py              # Sistema de campanhas
├── config.json                     # Configuração de campanhas
├── .env                            # Chaves de API (não commitado)
├── .env.example                    # Exemplo de configuração
├── campanhas/                      # Campanhas RPG
│   ├── lamento_do_bardo/
│   └── exemplo_fantasia/
├── contos_interativos/             # Contos interativos
│   ├── o_corvo_poe.txt
│   └── o_corvo_poe_eventos.json
├── sons/                           # Arquivos de áudio
│   └── sistema/
└── test_plataforma_ressoar.py      # Teste principal
```

## 🔧 Dependências

### Principais
- **Python 3.8+**
- **google-generativeai** - API do Gemini (obrigatória)
- **google-cloud-texttospeech** - TTS em português brasileiro
- **pygame** - Reprodução de áudio
- **python-dotenv** - Carregamento de variáveis de ambiente

### Instalação
```bash
pip install -r requirements.txt
```

## 🚨 Solução de Problemas

### Erro de API Key
```
O Mestre do Jogo não consegue se conectar aos planos astrais.
```
**Solução:** Configure `GEMINI_API_KEY` no arquivo `.env`

### Erro de Importação
```
ModuleNotFoundError: No module named 'google.generativeai'
```
**Solução:** Execute `pip install -r requirements.txt`

### Problemas de Áudio
```
Erro no sistema TTS
```
**Solução:** Verifique configuração do Google Cloud TTS no `.env`

## 🧪 Teste da Plataforma

```bash
python test_plataforma_ressoar.py
```

Este teste verifica:
- ✅ Estrutura de arquivos
- ✅ Configurações de campanhas RPG
- ✅ Estrutura de contos interativos
- ✅ Importações de funções

## 🎮 Comece Sua Aventura!

```bash
# Configuração rápida
cp .env.example .env
# Edite .env com suas chaves
python game.py
```

### 🎯 Características Únicas

- **🎵 Sequência de Abertura Única:** Som especial + narração poética
- **🗡️ Modo RPG Completo:** Sistema ambiental dinâmico + inventário com slots
- **📖 Contos Interativos:** Narrativas clássicas com múltiplos finais
- **🇧🇷 Áudio Premium:** Google Cloud TTS em português brasileiro
- **🎶 SFX Contextuais:** Efeitos sonoros automáticos baseados na narrativa
- **🔔 Chimes Indicativos:** Orientação sonora para interação

**Bem-vindo à Plataforma Ressoar - onde cada som conta uma história única!** 🎵✨

---

*Plataforma Ressoar - onde cada som conta uma história única.*