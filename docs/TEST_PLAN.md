# Plano de Testes — Plataforma Ressoar

## Visão Geral

| Métrica              | Valor                        |
| -------------------- | ---------------------------- |
| Total de testes      | 243                          |
| Arquivos de teste    | 6                            |
| Módulos cobertos     | 5 (game, audio, world, camp, integração) |
| Tipos de teste       | Unitário + Integração        |
| Framework            | pytest                       |
| Mocking              | unittest.mock                |
| APIs externas        | Sempre mockadas nos testes   |

---

## Como Executar

```bash
# Todos os testes
pytest tests/

# Com verbose (ver nome de cada teste)
pytest tests/ -v

# Com relatório de cobertura
pytest tests/ --cov=. --cov-report=html

# Módulo específico
pytest tests/test_game.py -v
pytest tests/test_campaign_manager.py -v
pytest tests/test_world_state_manager.py -v
pytest tests/test_audio_manager.py -v
pytest tests/test_integration.py -v

# Por palavra-chave
pytest tests/ -k "inventory" -v
pytest tests/ -k "validate" -v
pytest tests/ -k "trigger" -v

# Parar no primeiro erro
pytest tests/ -x

# Mostrar print() durante os testes
pytest tests/ -s
```

---

## Estrutura de Arquivos de Teste

```
tests/
├── conftest.py                  # Fixtures compartilhadas (world states, campaign data, mocks)
├── test_campaign_manager.py     # Testes de campaign_manager.py
├── test_world_state_manager.py  # Testes de world_state_manager.py
├── test_game.py                 # Testes de game.py (motor principal)
├── test_audio_manager.py        # Testes de audio_manager.py
└── test_integration.py          # Testes de integração entre módulos
```

---

## Fixtures Disponíveis (conftest.py)

| Fixture                      | Descrição                                              |
| ---------------------------- | ------------------------------------------------------ |
| `world_state_rpg`            | Estado completo de RPG com personagem Bardo            |
| `world_state_aventureiro`    | Estado RPG com personagem Aventureiro                  |
| `world_state_low_hp`         | Estado com HP crítico (3/20)                           |
| `world_state_full_inventory` | Estado com inventário cheio (10/10 slots)              |
| `world_state_empty_scene`    | Estado com lista de interativos vazia                  |
| `campaign_config`            | Config completo com 2 campanhas                        |
| `campaign_npcs`              | Dados de NPCs simulados                                |
| `campaign_items_comuns`      | Itens comuns com slots corretos                        |
| `campaign_items_magicos`     | Itens mágicos com raridades                            |
| `campaign_locais`            | Localizações com gatilhos                              |
| `story_eventos`              | Mapa completo de eventos de conto                      |
| `story_state`                | Estado de conto interativo em andamento                |
| `mock_openai_response`       | Mock de resposta narrativa da OpenAI                   |
| `mock_openai_archivista_response` | Mock de resposta JSON do Archivista               |
| `mock_audio`                 | Mock completo do sistema de áudio                      |
| `tmp_save_file`              | Arquivo temporário para save do jogo                   |
| `tmp_config_file`            | Config temporário em diretório temporário              |

---

## Cobertura de Testes por Módulo

### campaign_manager.py

| Função                   | Casos testados                                                  |
| ------------------------ | --------------------------------------------------------------- |
| `load_config`            | Retorno dict, FileNotFoundError, JSON inválido, default         |
| `get_current_campaign`   | Campanha existente, campanha inexistente, tipo dict             |
| `get_campaign_files`     | Retorna 5 chaves, caminhos corretos, campanha ausente           |
| `get_player_template`    | Chaves obrigatórias, HP Bardo=20, HP Aventureiro=25, default    |
| `get_world_template`     | Chaves obrigatórias, localização inicial, default               |
| `list_available_campaigns`| Lista, 2 campanhas, id+name, IDs corretos, config vazio        |
| `switch_campaign`        | Retorna True, False para inexistente, atualiza current_campaign |
| `load_campaign_data`     | JSON válido, FileNotFoundError, JSON inválido, tipo dict        |
| `load_campaign_text`     | Carrega texto, FileNotFoundError, tipo str                      |

### world_state_manager.py

| Função                           | Casos testados                                               |
| -------------------------------- | ------------------------------------------------------------ |
| `create_initial_world_state`     | Tipo dict, nome, classe, HP, ato 1, inventário, chaves WS, localização, eventos, unicode, max_slots |
| `load_world_state`               | None sem arquivo, dict com arquivo, dados corretos, JSON inválido, preserva nested |
| `save_world_state`               | Cria arquivo, JSON válido, roundtrip, sobrescreve, unicode    |
| `update_world_state`             | Retorna dict, sem API key, JSON inválido, tem interativos, exceção API |
| `get_openai_response_archivista` | Retorna str, sem API key, exceção, encaminha prompt          |

### game.py

| Função                           | Casos testados                                                 |
| -------------------------------- | -------------------------------------------------------------- |
| `extract_objects_from_action`    | Objetos conhecidos, lista, vazio, whitespace, string curta, móveis, arquitetura, NPCs, case-insensitive, múltiplos |
| `validate_player_action`         | Válida com objetos na cena, inválida, sem objetos conhecidos, tuple, string, voar, magia Bardo, teleporte, ação Bardo válida |
| `validate_impossible_abilities`  | Voar, teleporte, ação normal, levitar, controlar mente, parar tempo, tuple bool+str |
| `get_realistic_alternative`      | Retorna str, não vazio, classes diferentes                     |
| `clean_and_process_ai_response`  | Remove STATUS tag, aplica dano, cura, clamp max, clamp 0, remove INVENTORY tag, adiciona item, remove item, extrai/limpa MOOD tag, fallback mood normal, preserva narrativa, sem tags, tuple |
| `trigger_contextual_sfx`         | Corvo, taverna, chuva, grito, sem keyword, só 1 SFX, moeda, vazio |
| `get_item_slots`                 | Item conhecido, desconhecido retorna 1, tipo int, exceção retorna 1 |
| `calculate_used_slots`           | Inventário vazio, 1 slot, 2 slots, múltiplos, tipo int         |
| `can_pick_up_item`               | Pode pegar, inventário cheio, tuple, string, item 2 slots sem espaço |
| `handle_local_command`           | inventário, inventario, status, vida, saúde, ação narrativa, chikito, chama print_inventory, chama print_status |
| `load_json_data`                 | JSON válido, FileNotFoundError, JSON inválido, tipo dict, nested |
| `get_gm_narrative`               | Retorna str, fallback sem key, fallback erro API, stripped     |
| `get_story_master_narrative`     | Retorna str, sem key, erro API                                 |

### audio_manager.py

| Função                         | Casos testados                                                |
| ------------------------------ | ------------------------------------------------------------- |
| `play_sfx`                     | SFX conhecido, SFX desconhecido, arquivo não existe, biblioteca de SFX, inicializa mixer |
| `play_chime`                   | Chama play_sfx("chime"), não crasha                          |
| `narrator_speech`              | Chama text_to_speech com voice_type="narrator", texto correto |
| `master_speech`                | Chama text_to_speech com voice_type="master", texto correto  |
| `text_to_speech`               | Não crasha, Google primeiro, fallback local, fallback elevenlabs, voice_type, caching, texto vazio |
| `text_to_speech_local`         | Retorna bool, False em exceção                               |
| `text_to_speech_elevenlabs`    | False sem API key, False em erro de rede, False em 401       |
| `speech_to_text`               | Retorna str, fallback em erro de microfone, fallback UnknownValue, toca chime |

---

## Testes de Integração

| Cenário                                  | Verificação                                              |
| ---------------------------------------- | -------------------------------------------------------- |
| Campaign → WorldState (template)         | world_state reflete classe, HP e localização da campanha |
| Campaign → WorldState (triggers)         | Triggers iniciais do template estão ativos              |
| Switch Campaign → WorldState             | Mudar campanha muda template do personagem              |
| Criar → Salvar → Carregar               | Roundtrip completo preserva todos os dados              |
| Estado modificado → Salvar              | Modificações de HP e inventário persistem               |
| Arquivo ausente → Carregar              | Retorna None sem exceção                                |
| Objeto na cena → Ação válida            | Validação permite interação                              |
| Objeto fora da cena → Ação bloqueada   | Validação bloqueia interação                            |
| Ação impossível → Sempre bloqueada     | Voar/teleporte bloqueados independente do estado        |
| AI response → Atualiza inventário      | Tag INVENTORY_UPDATE adiciona/remove itens              |
| AI response → Atualiza HP              | Tag STATUS_UPDATE modifica HP com clamp                 |
| HP letal → Clamp em zero               | HP nunca fica negativo                                  |
| Cura excessiva → Clamp em max          | HP nunca ultrapassa max_hp                              |
| Story choice → Atualiza variáveis     | Efeitos das escolhas aplicados corretamente             |
| Story choice → Avança evento           | proximo_evento mapeado corretamente                     |
| Final sem opcoes → Encerra história   | Eventos final_* têm lista vazia                         |
| Trigger probability → Aumenta         | P cresce 10% por rodada sem trigger                     |
| Trigger probability → Cap em 90%      | Máximo de 90% respeitado                                |
| Trigger disparado → Move para usados  | Trigger sai de ativos e vai para usados                 |
| Estrutura de arquivos                  | config.json, campanhas/, contos/, sons/ existem         |
| Validade JSON dos arquivos             | Todos os JSONs das campanhas são válidos                |

---

## QA Narrativo Final — Curse of Strahd (Fase 6/7)

Coberturas adicionadas:

- Strahd em padrão "gato e rato" com transição de combate para tensão.
- Tarokka artefatos (Tomo, Símbolo, Espada) com validação de coleta e inventário.
- Calibragem Bardo vs Aventureiro em interações sociais de Baróvia.
- Forçamento de alívio via `emotional_pacing` após cadeia de alta tensão.
- Fluxo completo de 4 mortes com DC escalado e persistência de falhas de ressurreição.

Arquivos principais:

- `tests/test_integration.py`
- `tests/test_game.py`
- `tests/test_world_state_manager.py`

---

## Estratégia de Mock

### O que é sempre mockado:
1. **OpenAI API** — `patch("game.OpenAI")` e `patch("world_state_manager.OpenAI")`
2. **pygame** — mockado no nível do módulo antes do import
3. **pyttsx3** — mockado no nível do módulo antes do import
4. **file I/O** — `mock_open()` para evitar dependência de arquivos reais
5. **variáveis de ambiente** — `patch.dict(os.environ, ...)` para simular chaves

### O que usa arquivos reais:
1. **Testes de integração de estrutura** — verificam existência real dos arquivos
2. **Testes de roundtrip** — usam `tmp_path` do pytest para arquivos temporários

---

## Cenários de Erro Cobertos

| Cenário                          | Comportamento esperado                        |
| -------------------------------- | --------------------------------------------- |
| API key ausente                  | Retorna fallback/string de erro               |
| API indisponível (exceção)       | Retorna fallback, não crasha                  |
| JSON inválido no arquivo         | Retorna dict vazio ou estado anterior         |
| Arquivo não encontrado           | Retorna None/dict vazio/string vazia          |
| Pygame não inicializado          | Inicialização lazy acontece automaticamente   |
| Microfone indisponível           | Fallback para input de teclado                |
| Inventário cheio                 | Retorna False + mensagem explicativa          |
| HP acima do máximo               | Clamp em max_hp                               |
| HP abaixo de zero                | Clamp em 0                                    |
| Campanha inexistente             | Retorna dict/list vazio, não crasha           |

---

## Regras de Testes

1. **Nenhum teste chama APIs externas reais** — sempre mock
2. **Nenhum teste modifica arquivos de produção** — use `tmp_path` para I/O
3. **Cada teste é independente** — não depende de ordem de execução
4. **Testes de integração de estrutura** — único caso onde arquivos reais são lidos (somente leitura)
5. **Nomes descritivos** — `test_<o_que_testa>_<condição_se_necessário>`
6. **Uma asserção principal por teste** — facilita identificar o que falhou

---

## Adicionando Novos Testes

### Ao adicionar nova funcionalidade:
1. Criar testes unitários para cada função nova
2. Verificar casos: sucesso, falha, casos extremos (vazio, None, grande)
3. Adicionar fixture em `conftest.py` se precisar de estado compartilhado
4. Adicionar cenário de integração se a função interagir com outros módulos

### Ao adicionar nova campanha:
1. Verificar em `test_integration.py::TestFileStructureIntegration` que os arquivos existem
2. Verificar que o JSON é válido
3. Verificar que o template tem as chaves obrigatórias

### Ao adicionar novo conto:
1. Verificar que arquivos .txt e _eventos.json existem
2. Verificar estrutura do JSON de eventos
3. Verificar que todos os proximo_evento referenciados existem

---

## Cobertura de Código

Para gerar relatório de cobertura:

```bash
# Instalar
pip install pytest-cov

# Gerar relatório HTML
pytest tests/ --cov=. --cov-report=html --cov-omit="tests/*"

# Ver no terminal
pytest tests/ --cov=. --cov-report=term-missing --cov-omit="tests/*"
```

Meta de cobertura: **≥ 80%** nas funções puras (sem I/O e sem API).

---

## CI/CD (Sugestão)

```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.10"
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov
      - run: pytest tests/ -v --cov=. --cov-report=xml
```
