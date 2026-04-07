"""
Fixtures compartilhadas para toda a suíte de testes da Plataforma Ressoar.
"""
import json
import os
import shutil
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch


# ─── Fixtures: World State ────────────────────────────────────────────────────

@pytest.fixture
def world_state(tmp_path):
    """
    Save de mundo isolado por teste.
    Copia o template e evita tocar no estado real do projeto.
    """
    src = Path("estado_do_mundo_template.json")
    dst = tmp_path / "estado_do_mundo.json"
    shutil.copy(src, dst)
    return dst

@pytest.fixture
def world_state_rpg():
    """Estado do mundo completo para testes de RPG."""
    return {
        "game_mode": "rpg",
        "player_character": {
            "name": "Aldric",
            "class": "Bardo",
            "current_act": 1,
            "status": {"hp": 20, "max_hp": 20},
            "max_slots": 10,
            "inventory": ["Alaúde de Madeira", "Adaga de Ferro", "Mochila"],
            "desejo": "Descobrir a verdade sobre a praga musical"
        },
        "world_state": {
            "current_location_key": "umbraton",
            "immediate_scene_description": "Você está nas portas de Umbraton.",
            "active_quests": {"main_quest": "Investigar a praga musical"},
            "important_npcs_in_scene": {},
            "recent_events_summary": ["Aldric chegou a Umbraton"],
            "interactable_elements_in_scene": ["portão", "gárgula", "lanterna", "pedras"],
            "gatilhos_ativos": {"umbraton": ["corvo_na_gargula"]},
            "gatilhos_usados": {"umbraton": []}
        },
        "rodadas_sem_gatilho": 0
    }


@pytest.fixture
def campaign_locais_minimal():
    """Conjunto mínimo de locais para testes unitários de invariantes."""
    return {
        "umbraton": {},
        "taverna_corvo_ferido": {},
        "cemiterio_antigo": {},
    }


@pytest.fixture
def world_state_aventureiro():
    """Estado do mundo com personagem Aventureiro."""
    return {
        "game_mode": "rpg",
        "player_character": {
            "name": "Thorin",
            "class": "Aventureiro",
            "current_act": 1,
            "status": {"hp": 25, "max_hp": 25},
            "max_slots": 10,
            "inventory": ["Espada Longa", "Escudo", "Armadura de Couro", "Mochila", "Corda"],
            "desejo": "Recuperar o Cristal Perdido"
        },
        "world_state": {
            "current_location_key": "pedraverde",
            "immediate_scene_description": "Você está na Vila de Pedraverde.",
            "active_quests": {"main_quest": "Recuperar o cristal"},
            "important_npcs_in_scene": {},
            "recent_events_summary": ["Thorin chegou a Pedraverde"],
            "interactable_elements_in_scene": ["poço", "taverna", "estábulo", "mercado"],
            "gatilhos_ativos": {"pedraverde": []},
            "gatilhos_usados": {"pedraverde": []}
        },
        "rodadas_sem_gatilho": 0
    }


@pytest.fixture
def world_state_low_hp(world_state_rpg):
    """Estado com HP baixo para testar limites."""
    ws = dict(world_state_rpg)
    ws["player_character"] = dict(world_state_rpg["player_character"])
    ws["player_character"]["status"] = {"hp": 3, "max_hp": 20}
    return ws


@pytest.fixture
def world_state_full_inventory(world_state_rpg):
    """Estado com inventário cheio (10 slots)."""
    ws = dict(world_state_rpg)
    ws["player_character"] = dict(world_state_rpg["player_character"])
    ws["player_character"]["inventory"] = [
        "Alaúde de Madeira",   # 2 slots
        "Espada Longa",        # 2 slots
        "Escudo",              # 2 slots
        "Armadura de Couro",   # 2 slots
        "Mochila",             # 1 slot
        "Adaga de Ferro",      # 1 slot
    ]
    return ws


@pytest.fixture
def world_state_empty_scene(world_state_rpg):
    """Estado com cena sem elementos interativos."""
    ws = dict(world_state_rpg)
    ws["world_state"] = dict(world_state_rpg["world_state"])
    ws["world_state"]["interactable_elements_in_scene"] = []
    return ws


# ─── Fixtures: Campaign Data ──────────────────────────────────────────────────

@pytest.fixture
def campaign_config():
    """Config completo simulado."""
    return {
        "current_campaign": "lamento_do_bardo",
        "campaigns": {
            "lamento_do_bardo": {
                "name": "O Lamento do Bardo",
                "description": "Uma história sombria sobre peste e memória",
                "files": {
                    "npcs": "campanhas/lamento_do_bardo/npcs.json",
                    "itens_magicos": "campanhas/lamento_do_bardo/itens_magicos.json",
                    "itens_comuns": "campanhas/lamento_do_bardo/itens_comuns.json",
                    "locais": "campanhas/lamento_do_bardo/locais.json",
                    "campanha": "campanhas/lamento_do_bardo/campanha.md"
                },
                "player_template": {
                    "class": "Bardo",
                    "starting_hp": 20,
                    "max_slots": 10,
                    "starting_inventory": ["Alaúde de Madeira", "Adaga de Ferro", "Mochila", "Kit Viagem", "Kit Iluminação"]
                },
                "world_template": {
                    "initial_description": "Você chega aos portões de Umbraton.",
                    "initial_quest": "Investigar a praga musical",
                    "initial_location": "umbraton",
                    "initial_triggers": {
                        "umbraton": ["corvo_na_gargula", "crianca_correndo"]
                    }
                }
            },
            "exemplo_fantasia": {
                "name": "A Busca pelo Cristal Perdido",
                "description": "Aventura clássica de fantasia",
                "files": {
                    "npcs": "campanhas/exemplo_fantasia/npcs.json",
                    "itens_magicos": "campanhas/exemplo_fantasia/itens_magicos.json",
                    "itens_comuns": "campanhas/exemplo_fantasia/itens_comuns.json",
                    "locais": "campanhas/exemplo_fantasia/locais.json",
                    "campanha": "campanhas/exemplo_fantasia/campanha.md"
                },
                "player_template": {
                    "class": "Aventureiro",
                    "starting_hp": 25,
                    "max_slots": 10,
                    "starting_inventory": ["Espada Longa", "Escudo", "Armadura de Couro", "Mochila", "Corda"]
                },
                "world_template": {
                    "initial_description": "Você chega à Vila de Pedraverde.",
                    "initial_quest": "Recuperar o Cristal Perdido",
                    "initial_location": "pedraverde",
                    "initial_triggers": {}
                }
            }
        }
    }


@pytest.fixture
def campaign_npcs():
    """Dados de NPCs simulados."""
    return {
        "npcs": {
            "kael": {
                "nome": "Kael",
                "aparencia_facil": "Bardo sábio e carismático",
                "verdade_oculta": "Dragão negro ancião",
                "papel": "antagonista_principal",
                "ato_aparicao": 1
            },
            "lysenn": {
                "nome": "Lysenn",
                "aparencia_facil": "Ex-aprendiz cego e fugitivo",
                "verdade_oculta": "Sabe a verdade sobre Kael",
                "papel": "aliado",
                "ato_aparicao": 1
            },
            "virella": {
                "nome": "Virella",
                "aparencia_facil": "Sacerdotisa carismática",
                "verdade_oculta": "Sob influência mágica de Kael",
                "papel": "cultista",
                "ato_aparicao": 2
            }
        }
    }


@pytest.fixture
def campaign_items_comuns():
    """Dados de itens comuns simulados."""
    return {
        "itens_comuns": {
            "pocao_cura": {"nome": "Poção de Cura", "slots": 1, "efeito": "+10 HP"},
            "alaude_madeira": {"nome": "Alaúde de Madeira", "slots": 2},
            "adaga_ferro": {"nome": "Adaga de Ferro", "slots": 1},
            "mochila": {"nome": "Mochila", "slots": 1},
            "espada_longa": {"nome": "Espada Longa", "slots": 2},
            "escudo": {"nome": "Escudo", "slots": 2},
            "armadura_couro": {"nome": "Armadura de Couro", "slots": 2},
            "corda": {"nome": "Corda", "slots": 1},
            "kit_viagem": {"nome": "Kit Viagem", "slots": 1},
            "kit_iluminacao": {"nome": "Kit Iluminação", "slots": 1}
        }
    }


@pytest.fixture
def campaign_items_magicos():
    """Dados de itens mágicos simulados."""
    return {
        "itens_magicos": {
            "anel_sussurro": {"nome": "Anel do Sussurro", "slots": 1, "raridade": "Incomum"},
            "lira_mentiras": {"nome": "Lira das Mentiras", "slots": 2, "raridade": "Incomum"},
            "cristal_memoria": {"nome": "Cristal de Memória", "slots": 1, "raridade": "Raro"}
        }
    }


@pytest.fixture
def campaign_locais():
    """Dados de locais simulados."""
    return {
        "locais": {
            "umbraton": {
                "nome": "Umbraton",
                "descricao": "Cidade gótica envolta em névoa",
                "ato_aparicao": 1,
                "gatilhos": [
                    {
                        "id": "corvo_na_gargula",
                        "descricao": "Um corvo pousa em uma gárgula",
                        "sfx": "corvo",
                        "proximo": "diario_vibra"
                    },
                    {
                        "id": "diario_vibra",
                        "descricao": "O diário vibra intensamente",
                        "sfx": None,
                        "proximo": None
                    }
                ]
            },
            "taverna_corvo_ferido": {
                "nome": "Taverna do Corvo Ferido",
                "descricao": "Taverna escura e antiga",
                "ato_aparicao": 1,
                "gatilhos": [
                    {
                        "id": "taverneiro_se_cala",
                        "descricao": "O taverneiro para de falar",
                        "sfx": None,
                        "proximo": "figura_encapuzada"
                    }
                ]
            }
        }
    }


# ─── Fixtures: Story Mode ─────────────────────────────────────────────────────

@pytest.fixture
def story_eventos():
    """Mapa de eventos de conto interativo simulado."""
    return {
        "titulo": "O Corvo",
        "autor": "Edgar Allan Poe",
        "variaveis_iniciais": {
            "sanidade": 5,
            "esperanca": 5,
            "obsessao": 2,
            "aceitacao": 3
        },
        "evento_inicial": "inicio",
        "eventos": {
            "inicio": {
                "descricao_para_ia": "Abertura — meia-noite, quarto escuro, batidas na porta.",
                "opcoes": [
                    {
                        "texto": "(A) Abrir a porta",
                        "efeito": {"esperanca": 1},
                        "proximo_evento": "porta_aberta"
                    },
                    {
                        "texto": "(B) Hesitar",
                        "efeito": {"obsessao": 1},
                        "proximo_evento": "silencio"
                    },
                    {
                        "texto": "(C) Mergulhar nos livros",
                        "efeito": {"aceitacao": 1},
                        "proximo_evento": "livros"
                    }
                ]
            },
            "porta_aberta": {
                "descricao_para_ia": "A porta se abre para a escuridão.",
                "opcoes": [
                    {
                        "texto": "(A) Chamar pelo nome dela",
                        "efeito": {"obsessao": 1, "sanidade": -1},
                        "proximo_evento": "final_desespero"
                    },
                    {
                        "texto": "(B) Fechar a porta",
                        "efeito": {"aceitacao": 1},
                        "proximo_evento": "final_aceitacao"
                    }
                ]
            },
            "silencio": {
                "descricao_para_ia": "O silêncio pesa sobre a câmara.",
                "opcoes": [
                    {
                        "texto": "(A) Continuar na escuridão",
                        "efeito": {"sanidade": -1},
                        "proximo_evento": "final_desespero"
                    }
                ]
            },
            "livros": {
                "descricao_para_ia": "Você encontra conforto nos livros.",
                "opcoes": [
                    {
                        "texto": "(A) Deixar ir",
                        "efeito": {"aceitacao": 2},
                        "proximo_evento": "final_aceitacao"
                    }
                ]
            },
            "final_desespero": {
                "descricao_para_ia": "A alma aprisionada pelo luto eterno.",
                "opcoes": []
            },
            "final_aceitacao": {
                "descricao_para_ia": "A paz que vem ao honrar a memória.",
                "opcoes": []
            }
        }
    }


@pytest.fixture
def story_state():
    """Estado de um conto em andamento."""
    return {
        "game_mode": "conto",
        "story_state": {
            "story_name": "o_corvo_poe",
            "evento_atual": "inicio",
            "variaveis_narrativas": {
                "sanidade": 5,
                "esperanca": 5,
                "obsessao": 2,
                "aceitacao": 3
            },
            "historico_escolhas": []
        }
    }


# ─── Fixtures: Mocks ──────────────────────────────────────────────────────────

@pytest.fixture
def mock_openai_response():
    """Mock de resposta da OpenAI API."""
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message.content = "O Mestre narra: você entra na taverna sombria. Uma vela tremeluz sobre a mesa de carvalho. O que você faz?"
    return mock


@pytest.fixture
def mock_openai_archivista_response():
    """Mock de resposta da OpenAI para o Archivista (JSON)."""
    state = {
        "player_character": {
            "name": "Aldric",
            "class": "Bardo",
            "current_act": 1,
            "status": {"hp": 20, "max_hp": 20},
            "max_slots": 10,
            "inventory": ["Alaúde de Madeira", "Adaga de Ferro", "Mochila"],
            "desejo": "Descobrir a verdade"
        },
        "world_state": {
            "current_location_key": "umbraton",
            "immediate_scene_description": "Você está na taverna.",
            "active_quests": {"main_quest": "Investigar"},
            "important_npcs_in_scene": {"Taverneiro": "Olha para você"},
            "recent_events_summary": ["Entrou na taverna"],
            "interactable_elements_in_scene": ["mesa", "vela", "taverneiro", "balcão"],
            "gatilhos_ativos": {"umbraton": []},
            "gatilhos_usados": {"umbraton": []}
        },
        "rodadas_sem_gatilho": 1
    }
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message.content = json.dumps(state)
    return mock


@pytest.fixture
def mock_audio():
    """Mock completo do sistema de áudio."""
    with patch("audio_manager.text_to_speech") as m_tts, \
         patch("audio_manager.play_sfx") as m_sfx, \
         patch("audio_manager.play_chime") as m_chime:
        yield {"tts": m_tts, "sfx": m_sfx, "chime": m_chime}


@pytest.fixture
def tmp_save_file(tmp_path):
    """Arquivo temporário para save do jogo."""
    return str(tmp_path / "test_save.json")


@pytest.fixture
def tmp_config_file(tmp_path, campaign_config):
    """Arquivo temporário de config.json."""
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(campaign_config), encoding="utf-8")
    return str(config_path)
