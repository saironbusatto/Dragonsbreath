import json

from memory_bootstrap import bootstrap_memory
from memory_loader import MemoryLoader


TOKEN_BUDGET = {
    "mestre_rpg": 2200,
    "archivista": 2100,
    "story_master": 4200,
    "olhos_jogador": 450,
}


def _estimate_tokens(text: str) -> int:
    return max(0, len(text) // 4)


def _sample_world_state() -> dict:
    return {
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
            "scene_npc_signatures": {},
            "interactable_elements_in_scene": {
                "objetos": ["balcao", "vela", "lareira"],
                "npcs": [],
                "npc_itens": {},
                "containers": {},
                "saidas": ["porta norte"],
                "chao": []
            }
        }
    }


def _prepare_turn_ctx(tmp_path):
    world_state = _sample_world_state()
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
    turn_ctx = MemoryLoader(memory_dir=tmp_path / "memory").load_turn_context(world_state)
    return world_state, turn_ctx


def test_budget_mestre_rpg(tmp_path):
    _world_state, turn_ctx = _prepare_turn_ctx(tmp_path)
    assert turn_ctx.token_estimate < TOKEN_BUDGET["mestre_rpg"]


def test_budget_archivista(tmp_path):
    world_state, _turn_ctx = _prepare_turn_ctx(tmp_path)
    prompt = (
        "JSON DO ESTADO ATUAL:\n"
        + json.dumps(world_state, ensure_ascii=False, indent=2)
        + "\nEVENTOS RECENTES:\n- Ação do jogador: \"Observo a sala\"\n- Resposta do Mestre: \"Você ouve passos.\""
    )
    assert _estimate_tokens(prompt) < TOKEN_BUDGET["archivista"]


def test_budget_story_master(tmp_path):
    world_state, _turn_ctx = _prepare_turn_ctx(tmp_path)
    story_text = " ".join(["Noite sombria em Umbraton."] * 400)
    eventos = {"inicio": {"descricao": "A névoa avança", "opcoes": ["A", "B", "C"]}}
    prompt = (
        "OBRA ORIGINAL:\n"
        + story_text
        + "\nMAPA:\n"
        + json.dumps(eventos, ensure_ascii=False, indent=2)
        + "\nESTADO:\n"
        + json.dumps(world_state, ensure_ascii=False, indent=2)
    )
    assert _estimate_tokens(prompt) < TOKEN_BUDGET["story_master"]


def test_budget_olhos_jogador(tmp_path):
    world_state, _turn_ctx = _prepare_turn_ctx(tmp_path)
    ws = world_state["world_state"]
    context = {
        "local_atual": ws["current_location_key"],
        "descricao_da_cena": ws.get("immediate_scene_description", ""),
        "cena": ws.get("interactable_elements_in_scene", {}),
        "narrações_recentes": ws.get("recent_events_summary", []),
    }
    text = json.dumps(context, ensure_ascii=False, indent=2)
    assert _estimate_tokens(text) < TOKEN_BUDGET["olhos_jogador"]

