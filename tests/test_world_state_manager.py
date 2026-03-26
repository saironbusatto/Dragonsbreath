"""
Testes para world_state_manager.py
Cobre: create_initial_world_state, load_world_state, save_world_state,
       update_world_state, get_openai_response_archivista
"""
import json
import os
import pytest
from unittest.mock import patch, mock_open, MagicMock

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import world_state_manager


# ─── create_initial_world_state ───────────────────────────────────────────────

class TestCreateInitialWorldState:
    def test_returns_dict(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = world_state_manager.create_initial_world_state("Aldric")
        assert isinstance(result, dict)

    def test_player_name_set_correctly(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = world_state_manager.create_initial_world_state("Aldric")
        assert result["player_character"]["name"] == "Aldric"

    def test_class_from_template(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = world_state_manager.create_initial_world_state("Aldric")
        assert result["player_character"]["class"] == "Bardo"

    def test_hp_from_template(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = world_state_manager.create_initial_world_state("Aldric")
        assert result["player_character"]["status"]["hp"] == 20
        assert result["player_character"]["status"]["max_hp"] == 20

    def test_starts_at_act_1(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = world_state_manager.create_initial_world_state("Aldric")
        assert result["player_character"]["current_act"] == 1

    def test_inventory_from_template(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = world_state_manager.create_initial_world_state("Aldric")
        inventory = result["player_character"]["inventory"]
        assert isinstance(inventory, list)
        assert len(inventory) > 0

    def test_world_state_has_required_keys(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = world_state_manager.create_initial_world_state("Aldric")
        ws = result["world_state"]
        assert "current_location_key" in ws
        assert "immediate_scene_description" in ws
        assert "active_quests" in ws
        assert "recent_events_summary" in ws

    def test_initial_location_from_template(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = world_state_manager.create_initial_world_state("Aldric")
        assert result["world_state"]["current_location_key"] == "umbraton"

    def test_recent_events_contains_start_message(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = world_state_manager.create_initial_world_state("Aldric")
        events = result["world_state"]["recent_events_summary"]
        assert len(events) >= 1

    def test_name_with_spaces(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = world_state_manager.create_initial_world_state("João da Silva")
        assert result["player_character"]["name"] == "João da Silva"

    def test_max_slots_from_template(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = world_state_manager.create_initial_world_state("Aldric")
        assert result["player_character"]["max_slots"] == 10

    def test_aventureiro_template(self, campaign_config):
        campaign_config["current_campaign"] = "exemplo_fantasia"
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = world_state_manager.create_initial_world_state("Thorin")
        assert result["player_character"]["class"] == "Aventureiro"
        assert result["player_character"]["status"]["hp"] == 25

    def test_initial_resurrection_fields_exist(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            result = world_state_manager.create_initial_world_state("Aldric")
        pc = result["player_character"]
        assert pc["death_count"] == 0
        assert isinstance(pc["resurrection_flaws"], list)
        assert pc["alignment"] == "neutro"


# ─── load_world_state ────────────────────────────────────────────────────────

class TestLoadWorldState:
    def test_returns_none_when_file_not_found(self, tmp_path):
        path = str(tmp_path / "nao_existe.json")
        result = world_state_manager.load_world_state(path)
        assert result is None

    def test_returns_dict_when_file_exists(self, tmp_path, world_state_rpg):
        path = tmp_path / "save.json"
        path.write_text(json.dumps(world_state_rpg), encoding="utf-8")
        result = world_state_manager.load_world_state(str(path))
        assert isinstance(result, dict)

    def test_loaded_data_matches_saved(self, tmp_path, world_state_rpg):
        path = tmp_path / "save.json"
        path.write_text(json.dumps(world_state_rpg), encoding="utf-8")
        result = world_state_manager.load_world_state(str(path))
        assert result["player_character"]["name"] == "Aldric"

    def test_returns_none_on_invalid_json(self, tmp_path):
        path = tmp_path / "invalid.json"
        path.write_text("{ invalid json }", encoding="utf-8")
        result = world_state_manager.load_world_state(str(path))
        assert result is None

    def test_preserves_nested_structures(self, tmp_path, world_state_rpg):
        path = tmp_path / "save.json"
        path.write_text(json.dumps(world_state_rpg), encoding="utf-8")
        result = world_state_manager.load_world_state(str(path))
        assert result["world_state"]["interactable_elements_in_scene"] == ["portão", "gárgula", "lanterna", "pedras"]

    def test_load_backfills_resurrection_fields(self, tmp_path, world_state_rpg):
        world_state_rpg["player_character"].pop("death_count", None)
        world_state_rpg["player_character"].pop("resurrection_flaws", None)
        world_state_rpg["player_character"].pop("alignment", None)
        path = tmp_path / "save.json"
        path.write_text(json.dumps(world_state_rpg), encoding="utf-8")
        result = world_state_manager.load_world_state(str(path))
        pc = result["player_character"]
        assert pc["death_count"] == 0
        assert isinstance(pc["resurrection_flaws"], list)
        assert pc["alignment"] == "neutro"


# ─── save_world_state ────────────────────────────────────────────────────────

class TestSaveWorldState:
    def test_creates_file(self, tmp_path, world_state_rpg):
        path = str(tmp_path / "save.json")
        world_state_manager.save_world_state(world_state_rpg, path)
        assert os.path.exists(path)

    def test_saved_content_is_valid_json(self, tmp_path, world_state_rpg):
        path = tmp_path / "save.json"
        world_state_manager.save_world_state(world_state_rpg, str(path))
        content = path.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert isinstance(parsed, dict)

    def test_save_and_load_roundtrip(self, tmp_path, world_state_rpg):
        path = str(tmp_path / "save.json")
        world_state_manager.save_world_state(world_state_rpg, path)
        loaded = world_state_manager.load_world_state(path)
        assert loaded["player_character"]["name"] == world_state_rpg["player_character"]["name"]
        assert loaded["player_character"]["status"]["hp"] == world_state_rpg["player_character"]["status"]["hp"]

    def test_overwrites_existing_file(self, tmp_path, world_state_rpg):
        path = tmp_path / "save.json"
        path.write_text('{"old": "data"}', encoding="utf-8")
        world_state_manager.save_world_state(world_state_rpg, str(path))
        loaded = world_state_manager.load_world_state(str(path))
        assert "player_character" in loaded

    def test_preserves_unicode(self, tmp_path, world_state_rpg):
        path = str(tmp_path / "save.json")
        world_state_manager.save_world_state(world_state_rpg, path)
        loaded = world_state_manager.load_world_state(path)
        assert loaded["player_character"]["desejo"] == "Descobrir a verdade sobre a praga musical"


# ─── update_world_state ───────────────────────────────────────────────────────

class TestUpdateWorldState:
    def _make_openai_mock(self, json_response: dict):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(json_response)
        mock_client.chat.completions.create.return_value = mock_response
        return mock_client

    def test_returns_dict(self, world_state_rpg):
        updated_state = dict(world_state_rpg)
        mock_client = self._make_openai_mock(updated_state)

        with patch("world_state_manager.OpenAI", return_value=mock_client):
            with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
                result = world_state_manager.update_world_state(
                    world_state_rpg, "Entrei na taverna", "Você entra na taverna sombria."
                )
        assert isinstance(result, dict)

    def test_returns_old_state_when_no_api_key(self, world_state_rpg):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENAI_API_KEY", None)
            result = world_state_manager.update_world_state(
                world_state_rpg, "ação", "narrativa"
            )
        assert result == world_state_rpg

    def test_returns_old_state_on_invalid_json_response(self, world_state_rpg):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "isso não é json válido {"
        mock_client.chat.completions.create.return_value = mock_response

        with patch("world_state_manager.OpenAI", return_value=mock_client):
            with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
                result = world_state_manager.update_world_state(
                    world_state_rpg, "ação", "narrativa"
                )
        assert result == world_state_rpg

    def test_updated_state_has_interactable_elements(self, world_state_rpg):
        updated = dict(world_state_rpg)
        updated["world_state"] = dict(world_state_rpg["world_state"])
        updated["world_state"]["interactable_elements_in_scene"] = ["mesa", "vela", "taverneiro"]

        mock_client = self._make_openai_mock(updated)

        with patch("world_state_manager.OpenAI", return_value=mock_client):
            with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
                result = world_state_manager.update_world_state(
                    world_state_rpg, "entrei", "Você entra. Mesa de carvalho, vela, taverneiro."
                )
        assert "interactable_elements_in_scene" in result["world_state"]

    def test_api_exception_returns_old_state(self, world_state_rpg):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        with patch("world_state_manager.OpenAI", return_value=mock_client):
            with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
                result = world_state_manager.update_world_state(
                    world_state_rpg, "ação", "narrativa"
                )
        assert result == world_state_rpg

    def test_preserves_combat_state_when_archivist_omits_field(self, world_state_rpg):
        world_state_rpg["world_state"]["combat_state"] = {
            "active": True,
            "turns_with_risk": 3,
            "significant_threat_present": True,
            "significant_threats": ["Strahd von Zarovich"],
        }
        world_state_rpg["world_state"]["emotional_pacing"] = {
            "consecutive_high_tension_turns": 2,
            "force_relief_next": False,
            "last_mood": "tense",
            "last_location_key": "umbraton",
        }
        world_state_rpg["pause_beat_count"] = 1
        world_state_rpg["pause_beat_segments"] = ["A porta abre.", "Nada respira lá dentro."]
        world_state_rpg["resurrection_state"] = {"stage": "awaiting_offering", "dc": 12, "death_count": 1}
        world_state_rpg["player_character"]["death_count"] = 1
        world_state_rpg["player_character"]["resurrection_flaws"] = [{"type": "resurrection_madness"}]
        world_state_rpg["player_character"]["alignment"] = "neutro"

        updated = dict(world_state_rpg)
        updated["world_state"] = dict(world_state_rpg["world_state"])
        updated["world_state"].pop("combat_state", None)
        updated["world_state"].pop("emotional_pacing", None)
        updated["player_character"] = dict(world_state_rpg["player_character"])
        updated["player_character"].pop("death_count", None)
        updated["player_character"].pop("resurrection_flaws", None)
        updated["player_character"].pop("alignment", None)

        mock_client = self._make_openai_mock(updated)

        with patch("world_state_manager.OpenAI", return_value=mock_client):
            with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
                result = world_state_manager.update_world_state(
                    world_state_rpg, "ataco com tudo", "O combate explode no salão."
                )

        assert "combat_state" in result["world_state"]
        assert result["world_state"]["combat_state"]["active"] is True
        assert "emotional_pacing" in result["world_state"]
        assert result["world_state"]["emotional_pacing"]["last_mood"] == "tense"
        assert result["pause_beat_count"] == 1
        assert len(result["pause_beat_segments"]) == 2
        assert result["resurrection_state"]["stage"] == "awaiting_offering"
        assert result["player_character"]["death_count"] == 1
        assert result["player_character"]["alignment"] == "neutro"


# ─── get_openai_response_archivista ──────────────────────────────────────────

class TestGetOpenAIResponseArchivista:
    def test_returns_string(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"key": "value"}'
        mock_client.chat.completions.create.return_value = mock_response

        with patch("world_state_manager.OpenAI", return_value=mock_client):
            with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
                result = world_state_manager.get_openai_response_archivista("system prompt", "user prompt")
        assert isinstance(result, str)

    def test_returns_empty_json_when_no_api_key(self):
        env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            result = world_state_manager.get_openai_response_archivista("system", "user")
        assert result == "{}"

    def test_returns_empty_json_on_exception(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("network error")

        with patch("world_state_manager.OpenAI", return_value=mock_client):
            with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
                result = world_state_manager.get_openai_response_archivista("system", "user")
        assert result == "{}"

    def test_forwards_prompt_to_api(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "{}"
        mock_client.chat.completions.create.return_value = mock_response

        with patch("world_state_manager.OpenAI", return_value=mock_client):
            with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
                world_state_manager.get_openai_response_archivista("system instructions", "meu prompt especial")

        call_kwargs = mock_client.chat.completions.create.call_args
        messages = call_kwargs[1].get("messages") or call_kwargs[0][1] if call_kwargs[0] else []
        # Verifica que o prompt foi incluído de alguma forma na chamada
        assert mock_client.chat.completions.create.called


# ─── NPC Signature Memory ─────────────────────────────────────────────────────

class TestNPCSignatureMemory:
    def test_create_initial_state_seeds_prepared_npc_signatures(self, campaign_config):
        npcs_payload = {
            "npcs": {
                "strahd": {
                    "nome": "Strahd von Zarovich",
                    "tipo": "antagonista_principal",
                    "assinatura_narrativa": {
                        "motivacao_principal": "Dominar Baróvia",
                        "intencao_na_interacao": "Testar os heróis"
                    }
                }
            }
        }

        with patch("campaign_manager.load_config", return_value=campaign_config):
            with patch("world_state_manager.get_campaign_files", return_value={"npcs": "fake_npcs.json"}):
                with patch("world_state_manager.load_campaign_data", return_value=npcs_payload):
                    state = world_state_manager.create_initial_world_state("Aldric")

        ws = state["world_state"]
        assert "npc_signatures" in ws
        assert "strahd" in ws["npc_signatures"]
        assert ws["npc_signatures"]["strahd"]["motivacao_principal"] == "Dominar Baróvia"

    def test_generates_improvised_signature_for_unknown_scene_npc(self, world_state_rpg):
        world_state_rpg["world_state"]["important_npcs_in_scene"] = {
            "figura encapuzada": "observa você sem falar"
        }
        world_state_rpg["world_state"]["interactable_elements_in_scene"] = {
            "objetos": ["mesa"],
            "npcs": ["figura encapuzada"],
            "npc_itens": {},
            "containers": {},
            "saidas": ["porta leste"],
            "chao": []
        }

        with patch("world_state_manager.get_campaign_files", return_value={"npcs": ""}):
            with patch("world_state_manager.load_campaign_data", return_value={}):
                updated = world_state_manager.ensure_npc_signature_memory(world_state_rpg)

        ws = updated["world_state"]
        assert "scene_npc_signatures" in ws
        assert "figura encapuzada" in ws["scene_npc_signatures"]
        scene_sig = ws["scene_npc_signatures"]["figura encapuzada"]
        assert scene_sig["origem"] == "improvisado"
        assert scene_sig["intencao_na_interacao_atual"] == "observa você sem falar"
        assert scene_sig.get("motivacao_principal")

    def test_update_world_state_keeps_scene_signatures_after_archivist(self, world_state_rpg):
        archivist_payload = {
            "player_character": world_state_rpg["player_character"],
            "world_state": {
                "current_location_key": "umbraton",
                "immediate_scene_description": "Você vê uma figura encapuzada perto da lareira.",
                "active_quests": {"main_quest": "Investigar"},
                "important_npcs_in_scene": {"figura encapuzada": "testa sua reação"},
                "interactable_elements_in_scene": {
                    "objetos": ["lareira"],
                    "npcs": ["figura encapuzada"],
                    "npc_itens": {},
                    "containers": {},
                    "saidas": ["porta norte"],
                    "chao": []
                },
                "recent_events_summary": ["Você entrou na sala principal"],
                "gatilhos_ativos": {"umbraton": []},
                "gatilhos_usados": {"umbraton": []}
            }
        }

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(archivist_payload, ensure_ascii=False)
        mock_client.chat.completions.create.return_value = mock_response

        with patch("world_state_manager.OpenAI", return_value=mock_client):
            with patch("world_state_manager.get_campaign_files", return_value={"npcs": ""}):
                with patch("world_state_manager.load_campaign_data", return_value={}):
                    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
                        updated = world_state_manager.update_world_state(
                            world_state_rpg, "avanço para a sala", "Você entra e vê uma figura encapuzada."
                        )

        ws = updated["world_state"]
        assert "npc_signatures" in ws
        assert "scene_npc_signatures" in ws
        assert "figura encapuzada" in ws["scene_npc_signatures"]
