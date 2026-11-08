"""Handler death_house.py: regras de saque/navegação só dentro da Death House."""
import json
from pathlib import Path
from unittest.mock import patch

import campaign_manager
import game

ROOT = Path(__file__).resolve().parent.parent
CURSE_FILES = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))["campaigns"]["curse_of_strahd"]["files"]


def _state(location: str) -> dict:
    return {"world_state": {"current_location_key": location}}


def _handler():
    with patch("campaign_manager.get_campaign_files", return_value=CURSE_FILES):
        return campaign_manager.load_campaign_handler("death_house")


def test_handler_is_discovered_for_curse_of_strahd():
    assert hasattr(_handler(), "build_gm_context_block")


def test_rules_injected_inside_death_house():
    block = _handler().build_gm_context_block(_state("area_29_encontro_fantasmas"))
    assert "REGRAS DA DEATH HOUSE" in block
    assert "saque" in block.lower() and "micro-evento" in block


def test_no_rules_outside_death_house():
    handler = _handler()
    assert handler.build_gm_context_block(_state("vila_barovia")) == ""
    assert handler.build_gm_context_block({}) == ""


def test_rules_reach_gm_campaign_block():
    with patch("campaign_manager.get_campaign_files", return_value=CURSE_FILES), \
         patch("game.load_campaign_handler", side_effect=campaign_manager.load_campaign_handler):
        block = game._build_campaign_gm_block({**_state("area_1a_entrada"), "time_of_day_counter": 0})
    assert "REGRAS DA DEATH HOUSE" in block
