from kairos_session import generate_session_reentry


def test_generate_session_reentry_creates_file(tmp_path):
    world_state = {
        "narration_mood": "tense",
        "player_character": {
            "name": "Aldric",
            "class": "Bardo",
            "hp_current": 12,
            "status": {"hp": 12, "max_hp": 20},
        },
        "world_state": {
            "current_location_key": "taverna_corvo_ferido",
            "active_quests": {"main_quest": "Descobrir a verdade"},
            "combat_state": {"active": False},
            "scene_npc_signatures": {
                "figura encapuzada": {"referencia_id": "improvisado_figura_encapuzada"}
            },
            "recent_events_summary": ["Aldric entrou na taverna"],
        },
    }
    output = tmp_path / "memory" / "session_reentry.md"
    created = generate_session_reentry(world_state, output_path=output)
    assert created == output
    content = output.read_text(encoding="utf-8")
    assert "Session Reentry" in content
    assert "location: taverna_corvo_ferido" in content
    assert "improvisado_figura_encapuzada" in content

