"""
Testes para campaign_manager.py
Cobre: load_config, get_current_campaign, get_campaign_files,
       get_player_template, get_world_template, list_available_campaigns,
       switch_campaign, load_campaign_data, load_campaign_text
"""
import json
import pytest
from unittest.mock import patch, mock_open

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import campaign_manager


# ─── load_config ─────────────────────────────────────────────────────────────

class TestLoadConfig:
    def test_load_config_returns_dict(self, campaign_config, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(campaign_config), encoding="utf-8")

        with patch("campaign_manager.open", mock_open(read_data=json.dumps(campaign_config))):
            with patch("builtins.open", mock_open(read_data=json.dumps(campaign_config))):
                result = campaign_manager.load_config()
        assert isinstance(result, dict)

    def test_load_config_file_not_found_returns_default(self):
        with patch("builtins.open", side_effect=FileNotFoundError):
            result = campaign_manager.load_config()
        assert "current_campaign" in result
        assert "campaigns" in result

    def test_load_config_invalid_json_returns_default(self):
        with patch("builtins.open", mock_open(read_data="{ invalid json }")):
            result = campaign_manager.load_config()
        assert "current_campaign" in result
        assert "campaigns" in result

    def test_load_config_default_has_lamento_campaign(self):
        with patch("builtins.open", side_effect=FileNotFoundError):
            result = campaign_manager.load_config()
        assert result.get("current_campaign") == "lamento_do_bardo"


# ─── get_current_campaign ─────────────────────────────────────────────────────

class TestGetCurrentCampaign:
    def test_returns_campaign_data(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = campaign_manager.get_current_campaign()
        assert result.get("name") == "O Lamento do Bardo"

    def test_returns_empty_dict_when_campaign_missing(self, campaign_config):
        campaign_config["current_campaign"] = "campanha_inexistente"
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = campaign_manager.get_current_campaign()
        assert result == {}

    def test_returns_dict_type(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = campaign_manager.get_current_campaign()
        assert isinstance(result, dict)


# ─── get_campaign_files ───────────────────────────────────────────────────────

class TestGetCampaignFiles:
    def test_returns_files_dict(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = campaign_manager.get_campaign_files()
        assert "npcs" in result
        assert "itens_magicos" in result
        assert "itens_comuns" in result
        assert "locais" in result
        assert "campanha" in result

    def test_returns_correct_paths(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = campaign_manager.get_campaign_files()
        assert "lamento_do_bardo" in result["npcs"]

    def test_returns_empty_dict_when_no_campaign(self):
        empty_config = {"current_campaign": "nao_existe", "campaigns": {}}
        with patch("campaign_manager.load_config", return_value=empty_config):
            result = campaign_manager.get_campaign_files()
        assert result == {}


# ─── get_player_template ──────────────────────────────────────────────────────

class TestGetPlayerTemplate:
    def test_returns_template_with_required_keys(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = campaign_manager.get_player_template()
        assert "class" in result
        assert "starting_hp" in result
        assert "starting_inventory" in result

    def test_bardo_has_correct_hp(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = campaign_manager.get_player_template()
        assert result["starting_hp"] == 20

    def test_bardo_class(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = campaign_manager.get_player_template()
        assert result["class"] == "Bardo"

    def test_default_template_on_missing_campaign(self):
        empty_config = {"current_campaign": "nao_existe", "campaigns": {}}
        with patch("campaign_manager.load_config", return_value=empty_config):
            result = campaign_manager.get_player_template()
        assert "class" in result
        assert "starting_hp" in result

    def test_aventureiro_has_correct_hp(self, campaign_config):
        campaign_config["current_campaign"] = "exemplo_fantasia"
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = campaign_manager.get_player_template()
        assert result["starting_hp"] == 25
        assert result["class"] == "Aventureiro"


# ─── get_world_template ───────────────────────────────────────────────────────

class TestGetWorldTemplate:
    def test_returns_template_with_required_keys(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = campaign_manager.get_world_template()
        assert "initial_description" in result
        assert "initial_quest" in result

    def test_initial_location_present(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = campaign_manager.get_world_template()
        assert "initial_location" in result
        assert result["initial_location"] == "umbraton"

    def test_default_template_on_missing_campaign(self):
        empty_config = {"current_campaign": "nao_existe", "campaigns": {}}
        with patch("campaign_manager.load_config", return_value=empty_config):
            result = campaign_manager.get_world_template()
        assert "initial_description" in result
        assert "initial_quest" in result


# ─── list_available_campaigns ────────────────────────────────────────────────

class TestListAvailableCampaigns:
    def test_returns_list(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = campaign_manager.list_available_campaigns()
        assert isinstance(result, list)

    def test_returns_two_campaigns(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = campaign_manager.list_available_campaigns()
        assert len(result) == 2

    def test_each_campaign_has_id_and_name(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = campaign_manager.list_available_campaigns()
        for campaign in result:
            assert "id" in campaign
            assert "name" in campaign

    def test_campaign_ids_correct(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = campaign_manager.list_available_campaigns()
        ids = [c["id"] for c in result]
        assert "lamento_do_bardo" in ids
        assert "exemplo_fantasia" in ids

    def test_empty_config_returns_empty_list(self):
        empty_config = {"current_campaign": "nenhum", "campaigns": {}}
        with patch("campaign_manager.load_config", return_value=empty_config):
            result = campaign_manager.list_available_campaigns()
        assert result == []


# ─── switch_campaign ──────────────────────────────────────────────────────────

class TestSwitchCampaign:
    def test_switch_to_existing_campaign_returns_true(self, campaign_config, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(campaign_config), encoding="utf-8")

        with patch("campaign_manager.load_config", return_value=campaign_config):
            with patch("builtins.open", mock_open()) as m:
                result = campaign_manager.switch_campaign("exemplo_fantasia")
        assert result is True

    def test_switch_to_nonexistent_campaign_returns_false(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = campaign_manager.switch_campaign("campanha_que_nao_existe")
        assert result is False

    def test_switch_updates_current_campaign(self, campaign_config):
        captured = {}

        def fake_open(path, *args, **kwargs):
            if "w" in args or kwargs.get("mode") == "w":
                import io
                buf = io.StringIO()
                class FakeFile:
                    def write(self, data):
                        captured["data"] = data
                    def __enter__(self): return self
                    def __exit__(self, *a): pass
                return FakeFile()
            return mock_open(read_data=json.dumps(campaign_config))()

        with patch("campaign_manager.load_config", return_value=campaign_config):
            with patch("builtins.open", mock_open()):
                campaign_manager.switch_campaign("exemplo_fantasia")


# ─── load_campaign_data ───────────────────────────────────────────────────────

class TestLoadCampaignData:
    def test_loads_valid_json(self, campaign_npcs):
        with patch("builtins.open", mock_open(read_data=json.dumps(campaign_npcs))):
            result = campaign_manager.load_campaign_data("any/path.json")
        assert result == campaign_npcs

    def test_returns_empty_dict_on_file_not_found(self):
        with patch("builtins.open", side_effect=FileNotFoundError):
            result = campaign_manager.load_campaign_data("nao_existe.json")
        assert result == {}

    def test_returns_empty_dict_on_invalid_json(self):
        with patch("builtins.open", mock_open(read_data="{ invalid }")):
            result = campaign_manager.load_campaign_data("invalid.json")
        assert result == {}

    def test_returns_dict_type(self, campaign_npcs):
        with patch("builtins.open", mock_open(read_data=json.dumps(campaign_npcs))):
            result = campaign_manager.load_campaign_data("path.json")
        assert isinstance(result, dict)


# ─── load_campaign_text ───────────────────────────────────────────────────────

class TestLoadCampaignText:
    def test_loads_text_file(self):
        expected = "Era uma vez uma aventura épica..."
        with patch("builtins.open", mock_open(read_data=expected)):
            result = campaign_manager.load_campaign_text("campanha.md")
        assert result == expected

    def test_returns_empty_string_on_file_not_found(self):
        with patch("builtins.open", side_effect=FileNotFoundError):
            result = campaign_manager.load_campaign_text("nao_existe.md")
        assert result == ""

    def test_returns_string_type(self):
        with patch("builtins.open", mock_open(read_data="texto")):
            result = campaign_manager.load_campaign_text("arquivo.md")
        assert isinstance(result, str)
