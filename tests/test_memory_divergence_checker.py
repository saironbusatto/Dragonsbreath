import json

from memory_divergence_checker import check_divergence, update_dual_write_status


def _legacy_state(hp: int = 12) -> dict:
    return {
        "player_character": {
            "hp_current": hp,
            "status": {"hp": hp, "max_hp": 20},
        },
        "narration_mood": "tense",
        "world_state": {
            "current_location_key": "umbraton",
            "combat_state": {"active": False, "initiative_order": []},
            "scene_npc_signatures": {
                "figura encapuzada": {"referencia_id": "improvisado_figura"}
            },
        },
    }


def _write_synced_topics(memory_dir, hp: int = 12):
    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / "npcs").mkdir(parents=True, exist_ok=True)
    (memory_dir / "player.md").write_text(f"hp_current: {hp}\n", encoding="utf-8")
    (memory_dir / "MEMORY.md").write_text("current_location_key: umbraton\n", encoding="utf-8")
    (memory_dir / "combat.md").write_text("combat_active: false\n", encoding="utf-8")
    (memory_dir / "mood.md").write_text("narration_mood: tense\n", encoding="utf-8")
    (memory_dir / "npcs/improvisado_figura.md").write_text("# npc\n", encoding="utf-8")


def test_divergence_clean_report_increments_counter(tmp_path):
    memory_dir = tmp_path / "memory"
    baseline_path = tmp_path / "memory_migration_baseline.json"
    _write_synced_topics(memory_dir, hp=12)
    legacy = _legacy_state(hp=12)
    baseline_path.write_text(
        json.dumps(
            {
                "memory_mode": "dual_write",
                "dual_write_clean_sessions": 2,
                "dual_write_min_sessions": 20,
                "last_divergence_at": None,
            }
        ),
        encoding="utf-8",
    )

    report = check_divergence(memory_dir, legacy)
    assert report.clean is True
    updated = update_dual_write_status(baseline_path, report, min_sessions=20)
    assert updated["dual_write_clean_sessions"] == 3
    assert updated["last_divergence_at"] is None


def test_hp_divergence_resets_counter(tmp_path):
    memory_dir = tmp_path / "memory"
    baseline_path = tmp_path / "memory_migration_baseline.json"
    _write_synced_topics(memory_dir, hp=20)
    legacy = _legacy_state(hp=12)
    baseline_path.write_text(
        json.dumps(
            {
                "memory_mode": "dual_write",
                "dual_write_clean_sessions": 7,
                "dual_write_min_sessions": 20,
                "last_divergence_at": None,
            }
        ),
        encoding="utf-8",
    )

    report = check_divergence(memory_dir, legacy)
    assert report.clean is False
    assert any(d.field == "hp_current" for d in report.divergences)
    updated = update_dual_write_status(baseline_path, report, min_sessions=20)
    assert updated["dual_write_clean_sessions"] == 0
    assert updated["last_divergence_at"] is not None


def test_threshold_reached_marks_ready_but_does_not_change_mode(tmp_path):
    memory_dir = tmp_path / "memory"
    baseline_path = tmp_path / "memory_migration_baseline.json"
    _write_synced_topics(memory_dir, hp=12)
    legacy = _legacy_state(hp=12)
    baseline_path.write_text(
        json.dumps(
            {
                "memory_mode": "dual_write",
                "dual_write_clean_sessions": 19,
                "dual_write_min_sessions": 20,
                "last_divergence_at": None,
            }
        ),
        encoding="utf-8",
    )

    report = check_divergence(memory_dir, legacy)
    updated = update_dual_write_status(baseline_path, report, min_sessions=20)
    assert updated["dual_write_clean_sessions"] == 20
    assert updated["dual_write_threshold_reached"] is True
    assert updated["promotion_recommended"] is True
    assert updated["memory_mode"] == "dual_write"

