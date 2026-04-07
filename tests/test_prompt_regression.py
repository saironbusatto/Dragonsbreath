import json
from pathlib import Path

from memory_bootstrap import bootstrap_memory
from memory_loader import MemoryLoader


def measure_legacy_prompt(world_state: dict) -> int:
    legacy_like_payload = {
        "world_state": world_state,
        "game_context": {
            "npcs": world_state.get("world_state", {}).get("scene_npc_signatures", {}),
            "items": {"itens_comuns": ["alaude", "adaga", "tocha", "mochila"]},
            "locais": {
                world_state.get("world_state", {}).get("current_location_key", "desconhecido"): {
                    "descricao": "local atual",
                    "gatilhos": ["som_distante", "vento_gelido", "corvo_na_torre"],
                }
            },
            "locais_segredos": {
                "armadilhas": ["fresta_oculta", "piso_falso"],
                "segredos": ["simbolo_antigo", "passagem_ritual"],
            },
        },
        "system_rules_excerpt": "Narre em segunda pessoa, mood obrigatório, anti-repetição, tags de status/inventário, controle de cena e assinaturas de NPC.",
    }
    payload = json.dumps(legacy_like_payload, ensure_ascii=False, indent=2)
    return max(0, len(payload) // 4)


def test_prompt_regression_turn_standard(tmp_path):
    world_state = {
        "narration_mood": "tense",
        "player_character": {
            "name": "Aldric",
            "class": "Bardo",
            "hp_current": 12,
            "status": {"hp": 12, "max_hp": 20},
            "inventory": ["alaude", "adaga", "mochila", "kit viagem", "chave antiga"],
        },
        "world_state": {
            "current_location_key": "taverna_corvo_ferido",
            "active_quests": {"main_quest": "Descobrir a verdade"},
            "combat_active": False,
            "combat_state": {"active": False, "initiative_order": []},
            "scene_npc_signatures": {
                "figura encapuzada": {
                    "referencia_id": "improvisado_figura_encapuzada",
                    "nome": "Figura Encapuzada",
                    "origem": "improvisado",
                    "tipo": "npc_improvisado",
                    "moral_tonalidade": "ambigua",
                    "arquetipo_social": "habitante",
                    "motivacao_principal": "Observar o heroi",
                    "voz_textual": "Sussurrante",
                }
            },
            "interactable_elements_in_scene": {
                "objetos": ["balcao", "vela", "lareira"],
                "npcs": ["figura encapuzada"],
                "npc_itens": {},
                "containers": {},
                "saidas": ["porta norte"],
                "chao": []
            }
        }
    }

    state_path = tmp_path / "estado_do_mundo.json"
    baseline_path = tmp_path / "memory_migration_baseline.json"
    state_path.write_text(json.dumps(world_state), encoding="utf-8")
    baseline_path.write_text(json.dumps({"memory_mode": "legacy"}), encoding="utf-8")

    boot = bootstrap_memory(
        state_path=state_path,
        memory_dir=tmp_path / "memory",
        baseline_path=baseline_path,
        config_path=tmp_path / "config.json",
        campaign_locais_override={"taverna_corvo_ferido": {}},
    )
    assert boot.status == "bootstrapped"

    legacy_ctx_size = measure_legacy_prompt(world_state)

    loader = MemoryLoader(memory_dir=tmp_path / "memory")
    turn_ctx = loader.load_turn_context(world_state)
    new_ctx_size = turn_ctx.token_estimate

    assert new_ctx_size < legacy_ctx_size
    assert turn_ctx.player is not None
    assert turn_ctx.location is not None
    assert turn_ctx.loaded_files
