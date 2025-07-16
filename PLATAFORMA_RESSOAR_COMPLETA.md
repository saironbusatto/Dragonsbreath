# 🎵 Plataforma Ressoar - Documentação Completa

## 🌟 Visão Geral

A **Plataforma Ressoar** é um sistema revolucionário de narrativas interativas que oferece duas experiências distintas de jogo:

- **🗡️ Modo RPG:** Aventuras completas com regras, inventário e liberdade total de ação
- **📖 Modo Conto Interativo:** Histórias clássicas adaptadas com escolhas e múltiplos finais

## 🎮 Seleção de Modo Inicial

Ao iniciar o jogo, o jogador é apresentado à tela de seleção:

```
🎮 PLATAFORMA RESSOAR - SELEÇÃO DE MODO
========================================

1. 🗡️ MODO RPG
   Viva uma aventura com regras, inventário e liberdade de ação.
   • Sistema de Interação Ambiental Dinâmica
   • Inventário com slots limitados
   • Múltiplas campanhas disponíveis
   • Progressão de personagem

2. 📖 MODO CONTO INTERATIVO
   Participe de histórias clássicas com escolhas e finais alternativos.
   • Narrativas baseadas em obras literárias
   • Múltiplas escolhas e consequências
   • Finais alternativos únicos
   • Variáveis narrativas dinâmicas
```

## 🗡️ Modo RPG - Hub de Campanhas

### Características Principais

#### Sistema de Interação Ambiental Dinâmica
- **IA Mestre** povoa cenários com 2-4 objetos específicos interativos
- **IA Arquivista** identifica e rastreia elementos da cena automaticamente
- **Validação Contextual** permite apenas interações com objetos existentes
- **Realismo Emergente** - as regras surgem naturalmente do ambiente

#### Sistema de Slots de Inventário
- **10 slots máximos** por personagem
- **Kits iniciais balanceados** por classe:
  - **Bardo:** 5/10 slots (Alaúde, Adaga, Mochila, Kit Viagem, Kit Iluminação)
  - **Aventureiro:** 7/10 slots (Espada, Escudo, Armadura, Mochila, Corda, Kits)
- **Gerenciamento estratégico** de recursos

#### Hub de Campanhas
```
🗡️ HUB DE CAMPANHAS RPG
========================

1. O Lamento do Bardo
   Classe: Bardo
   Uma história melancólica sobre música e memória...

2. Exemplo Fantasia
   Classe: Aventureiro
   Uma aventura clássica de exploração...
```

### Mecânicas Mantidas
- **Gatilhos narrativos encadeados**
- **Estado do mundo persistente**
- **Sistema de áudio otimizado**
- **Comandos locais** (inventário, status, etc.)
- **Salvamento automático**

## 📖 Modo Conto Interativo

### Estrutura de Arquivos

#### Diretório `contos_interativos/`
```
contos_interativos/
├── o_corvo_poe.txt              # Texto completo da obra
├── o_corvo_poe_eventos.json     # Estrutura de eventos e escolhas
├── outro_conto.txt
└── outro_conto_eventos.json
```

#### Arquivo de Texto (.txt)
Contém:
- Texto completo da obra original (adaptado)
- Descrições de cenas específicas
- Múltiplos finais alternativos
- Prólogo e epílogo

#### Arquivo de Eventos (_eventos.json)
```json
{
  "titulo": "O Corvo",
  "autor": "Adaptação inspirada em Edgar Allan Poe",
  "variaveis_iniciais": {
    "sanidade": 10,
    "esperanca": 5,
    "obsessao": 0,
    "aceitacao": 0
  },
  "evento_inicial": "lamento_inicial",
  "eventos": {
    "lamento_inicial": {
      "descricao_para_ia": "O narrador lamenta a perda de Lenore...",
      "opcoes": [
        {
          "texto": "(A) Tentar encontrar consolo nos livros.",
          "efeito": { "sanidade": 1, "esperanca": 1 },
          "proximo_evento": "batida_misteriosa"
        }
      ]
    }
  }
}
```

### Mestre do Conto (IA Especializada)

#### Prompt Especializado
```
Você é um "Mestre de Contos", um narrador que adapta obras literárias 
para uma experiência interativa.

--- OBRA ORIGINAL ---
{texto_completo_do_conto}

--- MAPA DA HISTÓRIA ---
{eventos_json}

--- ESTADO ATUAL ---
{estado_do_jogo}

MISSÃO:
1. Localize o evento_atual no mapa
2. Narre usando estilo da obra original
3. Se for final, termine a história
4. Se não, apresente opções (A, B, C)
```

### Sistema de Variáveis Narrativas

#### Exemplo: "O Corvo"
- **Sanidade:** Estabilidade mental do protagonista
- **Esperança:** Capacidade de encontrar significado
- **Obsessão:** Fixação na perda
- **Aceitação:** Capacidade de seguir em frente

#### Progressão por Escolhas
```
Jogador: "Digite sua escolha (A, B, C): A"
Sistema: ✅ Escolha A selecionada.
         Sanidade +1, Esperança +1
         Avançando para próximo evento...
```

### Múltiplos Finais

#### "O Corvo" - 4 Finais Possíveis:
1. **Final Desespero:** Alma prisioneira da dor
2. **Final Violência:** Luta fútil contra o destino
3. **Final Aceitação:** Paz através da memória
4. **Final Despertar:** Confronto com demônios internos

## 🔧 Arquitetura Técnica

### Estrutura de Arquivos
```
Dragons Breath/
├── game.py                           # Motor principal + Seleção de modo
├── world_state_manager.py            # Estado RPG + IA Arquivista
├── campaign_manager.py               # Gerenciamento de campanhas
├── config.json                      # Configuração de campanhas
├── campanhas/                       # Campanhas RPG
│   ├── lamento_do_bardo/
│   └── exemplo_fantasia/
├── contos_interativos/              # Contos interativos
│   ├── o_corvo_poe.txt
│   └── o_corvo_poe_eventos.json
├── test_plataforma_ressoar.py       # Testes da plataforma
└── README.md                        # Documentação
```

### Funções Principais

#### Seleção de Modo
- `select_game_mode()` - Escolha entre RPG e Conto
- `main()` - Ponto de entrada da plataforma

#### Modo RPG
- `select_rpg_campaign()` - Hub de campanhas
- `iniciar_modo_rpg()` - Inicia aventura RPG
- `new_game_loop()` - Loop principal RPG

#### Modo Conto
- `select_interactive_story()` - Biblioteca de contos
- `iniciar_modo_conto()` - Inicia conto interativo
- `interactive_story_loop()` - Loop principal de contos
- `get_story_master_narrative()` - IA especializada

## 🎯 Experiência do Usuário

### Fluxo Completo

1. **Início:** "🎵 Bem-vindo à Plataforma RESSOAR 🎵"
2. **Seleção:** Escolha entre RPG ou Conto Interativo
3. **Hub Específico:** Campanhas RPG ou Biblioteca de Contos
4. **Experiência:** Jogo completo no modo escolhido
5. **Finalização:** Retorno ao menu principal

### Continuidade
- **RPG:** Salva estado do mundo automaticamente
- **Contos:** Mantém progresso da história atual
- **Plataforma:** Lembra último modo usado

## 🚀 Benefícios da Plataforma

### Para Jogadores
- **Variedade:** Duas experiências completamente diferentes
- **Qualidade:** Sistemas especializados para cada modo
- **Flexibilidade:** Troca entre modos conforme humor
- **Progressão:** Avanço em ambos os tipos de narrativa

### Para Desenvolvedores
- **Modularidade:** Sistemas independentes mas integrados
- **Escalabilidade:** Fácil adição de novas campanhas/contos
- **Reutilização:** Componentes compartilhados (áudio, IA)
- **Manutenção:** Código organizado por funcionalidade

## 🎭 Casos de Uso

### Modo RPG Ideal Para:
- Sessões longas de jogo
- Exploração livre
- Desenvolvimento de personagem
- Experiências imersivas

### Modo Conto Ideal Para:
- Sessões rápidas (30-60 min)
- Experiências literárias
- Múltiplas tentativas/finais
- Narrativas focadas

## 🔮 Futuro da Plataforma

### Expansões Planejadas
- **Mais Campanhas RPG:** Diferentes classes e cenários
- **Biblioteca Expandida:** Mais obras clássicas adaptadas
- **Modo Híbrido:** Elementos RPG em contos interativos
- **Editor Visual:** Criação de contos pela comunidade
- **Multiplayer:** Experiências compartilhadas

---

*A Plataforma Ressoar representa a evolução natural dos jogos narrativos, oferecendo tanto a liberdade total do RPG quanto a profundidade literária dos contos interativos, tudo em uma experiência unificada e elegante.*
