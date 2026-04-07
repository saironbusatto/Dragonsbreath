from memory_invariants import validate_state_invariants


def _base_state():
    return {
        "player_character": {
            "status": {"hp": 10, "max_hp": 20}
        },
        "world_state": {
            "current_location_key": "umbraton",
            "combat_state": {"active": True, "initiative_order": ["aldric", "lobo"]},
            "scene_npc_signatures": {},
        },
    }


def test_valid_state_with_active_combat_has_zero_violations(tmp_path, campaign_locais_minimal):
    state = _base_state()
    checked, violations = validate_state_invariants(
        state=state,
        campaign_locais=campaign_locais_minimal,
        memory_dir=tmp_path / "memory",
    )
    assert checked
    assert violations == []


def test_combat_consistency_fails_when_inactive_with_initiative(tmp_path, campaign_locais_minimal):
    state = _base_state()
    state["world_state"]["combat_state"] = {"active": False, "initiative_order": ["aldric"]}
    _, violations = validate_state_invariants(state, campaign_locais_minimal, tmp_path / "memory")
    assert any(v.code == "combat_ghost_initiative" for v in violations)


def test_hp_resurrection_fails_when_stage_defined_and_hp_positive(tmp_path, campaign_locais_minimal):
    state = _base_state()
    state["resurrection_state"] = {"stage": "awaiting_offering"}
    state["player_character"]["hp_current"] = 8
    _, violations = validate_state_invariants(state, campaign_locais_minimal, tmp_path / "memory")
    assert any(v.code == "resurrection_with_living_player" for v in violations)


def test_location_exists_fails_when_location_not_in_campaign(tmp_path, campaign_locais_minimal):
    state = _base_state()
    state["world_state"]["current_location_key"] = "torre_fantasma"
    _, violations = validate_state_invariants(state, campaign_locais_minimal, tmp_path / "memory")
    assert any(v.code == "ghost_location" for v in violations)


def test_npc_file_present_fails_without_file_and_without_pending(tmp_path, campaign_locais_minimal):
    state = _base_state()
    state["world_state"]["scene_npc_signatures"] = {
        "figura encapuzada": {"referencia_id": "improvisado_figura"}
    }
    _, violations = validate_state_invariants(state, campaign_locais_minimal, tmp_path / "memory")
    assert any(v.code == "npc_missing_topic_file" for v in violations)


def test_npc_file_present_does_not_fail_when_pending(tmp_path, campaign_locais_minimal):
    state = _base_state()
    state["world_state"]["scene_npc_signatures"] = {
        "figura encapuzada": {"referencia_id": "improvisado_figura"}
    }
    state["__pending_npc_topic_files"] = ["improvisado_figura"]
    _, violations = validate_state_invariants(state, campaign_locais_minimal, tmp_path / "memory")
    assert not any(v.code == "npc_missing_topic_file" for v in violations)


def test_two_violations_are_reported_together(tmp_path, campaign_locais_minimal):
    state = _base_state()
    state["world_state"]["current_location_key"] = "torre_fantasma"
    state["world_state"]["combat_state"] = {"active": False, "initiative_order": ["aldric"]}
    _, violations = validate_state_invariants(state, campaign_locais_minimal, tmp_path / "memory")
    codes = {v.code for v in violations}
    assert "ghost_location" in codes
    assert "combat_ghost_initiative" in codes

