import json
from pathlib import Path

from memory_bootstrap import bootstrap_memory


def _legacy_state(location_key: str = "umbraton") -> dict:
    return {
        "player_character": {
            "name": "Aldric",
            "class": "Bardo",
            "hp_current": 12,
            "status": {"hp": 12, "max_hp": 20},
            "inventory": ["alaude"],
        },
        "narration_mood": "tense",
        "resurrection_state": {},
        "world_state": {
            "current_location_key": location_key,
            "active_quests": {"main_quest": "Investigar"},
            "interactable_elements_in_scene": {"npcs": ["figura encapuzada"]},
            "combat_state": {"active": False, "initiative_order": []},
            "scene_npc_signatures": {
                "figura encapuzada": {
                    "referencia_id": "improvisado_figura",
                    "nome": "Figura Encapuzada",
                    "origem": "improvisado",
                    "tipo": "npc_improvisado",
                }
            },
        },
    }


def test_bootstrap_creates_topics_via_wal_when_memory_missing(tmp_path):
    state_path = tmp_path / "estado_do_mundo.json"
    state_path.write_text(json.dumps(_legacy_state()), encoding="utf-8")
    baseline_path = tmp_path / "memory_migration_baseline.json"
    baseline_path.write_text(json.dumps({"memory_mode": "legacy"}), encoding="utf-8")

    result = bootstrap_memory(
        state_path=state_path,
        memory_dir=tmp_path / "memory",
        baseline_path=baseline_path,
        config_path=tmp_path / "config.json",
        campaign_locais_override={"umbraton": {}},
    )

    assert result.status == "bootstrapped"
    memory_dir = tmp_path / "memory"
    assert (memory_dir / "player.md").exists()
    assert (memory_dir / "location.md").exists()
    assert (memory_dir / "mood.md").exists()
    assert (memory_dir / "combat.md").exists()
    assert (memory_dir / "resurrection.md").exists()
    assert (memory_dir / "scene/current_npcs.md").exists()
    assert (memory_dir / "npcs/improvisado_figura.md").exists()
    assert (memory_dir / "MEMORY.md").exists()

    journal = (memory_dir / "turn_journal.jsonl").read_text(encoding="utf-8").splitlines()
    committed = [
        parsed
        for line in journal
        if line.strip()
        for parsed in [json.loads(line)]
        if parsed.get("status") == "committed"
    ]
    assert any(row.get("agent") == "bootstrap" for row in committed)
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert baseline["memory_mode"] == "dual_write"
    assert baseline["bootstrap_session"] == result.session_id
    assert "bootstrap_at" in baseline


def test_bootstrap_aborts_on_invariant_failure_and_does_not_create_memory(tmp_path):
    state_path = tmp_path / "estado_do_mundo.json"
    state_path.write_text(json.dumps(_legacy_state(location_key="torre_fantasma")), encoding="utf-8")
    baseline_path = tmp_path / "memory_migration_baseline.json"
    baseline_original = {"memory_mode": "legacy"}
    baseline_path.write_text(json.dumps(baseline_original), encoding="utf-8")

    result = bootstrap_memory(
        state_path=state_path,
        memory_dir=tmp_path / "memory",
        baseline_path=baseline_path,
        config_path=tmp_path / "config.json",
        campaign_locais_override={"umbraton": {}},
    )

    assert result.status == "aborted"
    assert (tmp_path / "memory").exists() is False
    current_baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert current_baseline == baseline_original


def test_bootstrap_returns_already_bootstrapped_when_memory_exists(tmp_path):
    state_path = tmp_path / "estado_do_mundo.json"
    state_path.write_text(json.dumps(_legacy_state()), encoding="utf-8")
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / "player.md").write_text("existing", encoding="utf-8")

    result = bootstrap_memory(
        state_path=state_path,
        memory_dir=memory_dir,
        baseline_path=tmp_path / "memory_migration_baseline.json",
        config_path=tmp_path / "config.json",
        campaign_locais_override={"umbraton": {}},
    )
    assert result.status == "already_bootstrapped"
