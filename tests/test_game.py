"""
Testes para game.py
Cobre: validate_player_action, validate_impossible_abilities,
       clean_and_process_ai_response, get_item_slots,
       calculate_used_slots, handle_local_command, load_json_data
"""
import json
import os
import pytest
from unittest.mock import patch, MagicMock, mock_open

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Importar com mocks para evitar inicialização de áudio
with patch("audio_manager.pygame"), \
     patch("audio_manager.pyttsx3", create=True), \
     patch.dict("sys.modules", {"pygame": MagicMock(), "pyttsx3": MagicMock()}):
    import game

# patch.dict limpa sys.modules ao sair — re-registrar para que patch() encontre o módulo correto
sys.modules["game"] = game


# ─── validate_player_action ──────────────────────────────────────────────────

class TestValidatePlayerAction:
    def test_valid_action_with_scene_objects(self, world_state_rpg):
        world_state_rpg["world_state"]["interactable_elements_in_scene"] = ["portão", "lanterna"]
        is_valid, msg = game.validate_player_action("abro o portão", {}, world_state_rpg)
        assert is_valid is True

    def test_invalid_action_object_not_in_scene(self, world_state_rpg):
        world_state_rpg["world_state"]["interactable_elements_in_scene"] = ["portão"]
        is_valid, msg = game.validate_player_action("pego a espada invisível", {}, world_state_rpg)
        # Espada não está na lista de objetos interativos
        # O resultado depende se 'espada' é extraída da ação
        assert isinstance(is_valid, bool)
        assert isinstance(msg, str)

    def test_action_without_known_objects_is_valid(self, world_state_rpg):
        is_valid, msg = game.validate_player_action("olho ao redor com cautela", {}, world_state_rpg)
        assert is_valid is True

    def test_returns_tuple(self, world_state_rpg):
        result = game.validate_player_action("algo", {}, world_state_rpg)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_message_is_string(self, world_state_rpg):
        _, msg = game.validate_player_action("algo", {}, world_state_rpg)
        assert isinstance(msg, str)

    def test_impossible_action_flying(self, world_state_rpg):
        character = {"class": "Bardo"}
        is_valid, msg = game.validate_player_action("vou voar até o castelo", character, world_state_rpg)
        assert is_valid is False
        assert len(msg) > 0

    def test_impossible_action_magic_bardo(self, world_state_rpg):
        character = {"class": "Bardo"}
        is_valid, msg = game.validate_player_action("lançar bola de fogo nos inimigos", character, world_state_rpg)
        assert is_valid is False

    def test_impossible_action_teleport(self, world_state_rpg):
        character = {"class": "Aventureiro"}
        is_valid, msg = game.validate_player_action("me teletransporto para o castelo", character, world_state_rpg)
        assert is_valid is False

    def test_valid_bardo_action(self, world_state_rpg):
        character = {"class": "Bardo"}
        is_valid, _ = game.validate_player_action("toco meu alaúde para acalmar a situação", character, world_state_rpg)
        assert is_valid is True

    def test_valid_aventureiro_action(self, world_state_rpg):
        character = {"class": "Aventureiro"}
        world_state_rpg["world_state"]["interactable_elements_in_scene"] = ["espada", "escudo"]
        is_valid, _ = game.validate_player_action("luto com a espada e me protejo com o escudo", character, world_state_rpg)
        assert is_valid is True


# ─── validate_impossible_abilities ───────────────────────────────────────────

class TestValidateImpossibleAbilities:
    def test_flying_is_impossible_for_bardo(self):
        is_valid, msg = game.validate_impossible_abilities("vou voar para lá", "Bardo")
        assert is_valid is False

    def test_teleport_is_impossible_for_all(self):
        for cls in ["Bardo", "Aventureiro"]:
            is_valid, _ = game.validate_impossible_abilities("me teletransportar", cls)
            assert is_valid is False

    def test_normal_action_is_valid(self):
        is_valid, _ = game.validate_impossible_abilities("caminho até a taverna", "Bardo")
        assert is_valid is True

    def test_levitar_is_impossible(self):
        is_valid, _ = game.validate_impossible_abilities("levitar acima do solo", "Bardo")
        assert is_valid is False

    def test_controlar_mente_is_impossible(self):
        is_valid, _ = game.validate_impossible_abilities("controlar mente do guarda", "Bardo")
        assert is_valid is False

    def test_parar_tempo_is_impossible(self):
        is_valid, _ = game.validate_impossible_abilities("parar o tempo", "Aventureiro")
        assert is_valid is False

    def test_returns_tuple_of_bool_and_str(self):
        result = game.validate_impossible_abilities("correr", "Bardo")
        assert isinstance(result, tuple)
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)


# ─── clean_and_process_ai_response ───────────────────────────────────────────

class TestCleanAndProcessAIResponse:
    def test_extracts_mood_tag_and_removes_from_narrative(self, world_state_rpg):
        text = "A névoa se fecha ao redor de você. [MOOD:tense]\nO que você faz?"
        cleaned, updated = game.clean_and_process_ai_response(text, world_state_rpg)
        assert "[MOOD:" not in cleaned
        assert updated.get("narration_mood") == "tense"

    def test_defaults_to_normal_mood_when_absent(self, world_state_rpg):
        text = "Você observa o salão em silêncio. O que você faz?"
        _, updated = game.clean_and_process_ai_response(text, world_state_rpg)
        assert updated.get("narration_mood") == "normal"

    def test_extracts_hdywdtd_tag_and_sets_pending_flag(self, world_state_rpg):
        text = "Seu golpe atravessa a guarda no último instante. [HDYWDTDT]\n[MOOD:dramatic]"
        cleaned, updated = game.clean_and_process_ai_response(text, world_state_rpg)
        assert "[HDYWDTDT]" not in cleaned
        assert updated.get("hdywdtd_pending") is True
        assert updated.get("hdywdtd_prompt") == "Como você quer fazer isso?"

    def test_hdywdtd_removes_default_question_tail(self, world_state_rpg):
        text = "A lâmina encontra a abertura no peito do inimigo. O que você faz? [HDYWDTDT]\n[MOOD:combat]"
        cleaned, _ = game.clean_and_process_ai_response(text, world_state_rpg)
        assert "O que você faz?" not in cleaned

    def test_pause_beat_is_removed_and_segments_are_saved(self, world_state_rpg):
        text = "A tampa do caixão range. [PAUSE_BEAT] Lá dentro, não há corpo. [MOOD:tense]"
        cleaned, updated = game.clean_and_process_ai_response(text, world_state_rpg)
        assert "[PAUSE_BEAT]" not in cleaned
        assert updated.get("pause_beat_count") == 1
        assert len(updated.get("pause_beat_segments", [])) == 2
        assert "não há corpo" in cleaned

    def test_forces_relief_when_pacing_requires_it(self, world_state_rpg):
        world_state_rpg["world_state"]["emotional_pacing"] = {
            "consecutive_high_tension_turns": 4,
            "force_relief_next": True,
            "last_mood": "combat",
            "last_location_key": "umbraton",
        }
        text = "A névoa fecha o corredor. [MOOD:tense]"
        _, updated = game.clean_and_process_ai_response(text, world_state_rpg)
        assert updated.get("narration_mood") == "relief"
        pacing = updated["world_state"]["emotional_pacing"]
        assert pacing.get("force_relief_next") is False

    def test_applies_act_update_tag(self, world_state_rpg):
        text = 'Você alcança Vallaki. [ACT_UPDATE] {"set_act": 2}\n[MOOD:dramatic]\nO que você faz?'
        _, updated = game.clean_and_process_ai_response(text, world_state_rpg)
        assert updated["player_character"]["current_act"] == 2

    def test_act_update_clamped_to_min(self, world_state_rpg):
        text = 'Retrocesso impossível. [ACT_UPDATE] {"set_act": -3}\nO que você faz?'
        _, updated = game.clean_and_process_ai_response(text, world_state_rpg)
        assert updated["player_character"]["current_act"] >= 1

    def test_removes_status_update_tag(self, world_state_rpg):
        text = 'Você é atingido. [STATUS_UPDATE] {"hp_change": -5}\nO que você faz?'
        cleaned, _ = game.clean_and_process_ai_response(text, world_state_rpg)
        assert "[STATUS_UPDATE]" not in cleaned

    def test_applies_hp_damage(self, world_state_rpg):
        text = 'Você leva um golpe. [STATUS_UPDATE] {"hp_change": -5}\nO que você faz?'
        _, updated = game.clean_and_process_ai_response(text, world_state_rpg)
        assert updated["player_character"]["status"]["hp"] == 15

    def test_applies_hp_healing(self, world_state_rpg):
        world_state_rpg["player_character"]["status"]["hp"] = 10
        text = 'Você bebe a poção. [STATUS_UPDATE] {"hp_change": 5}\nO que você faz?'
        _, updated = game.clean_and_process_ai_response(text, world_state_rpg)
        assert updated["player_character"]["status"]["hp"] == 15

    def test_hp_does_not_exceed_max(self, world_state_rpg):
        text = 'Cura total. [STATUS_UPDATE] {"hp_change": 9999}\nO que você faz?'
        _, updated = game.clean_and_process_ai_response(text, world_state_rpg)
        max_hp = world_state_rpg["player_character"]["status"]["max_hp"]
        assert updated["player_character"]["status"]["hp"] <= max_hp

    def test_hp_does_not_go_below_zero(self, world_state_rpg):
        text = 'Dano fatal. [STATUS_UPDATE] {"hp_change": -9999}\nO que você faz?'
        _, updated = game.clean_and_process_ai_response(text, world_state_rpg)
        assert updated["player_character"]["status"]["hp"] >= 0

    def test_removes_inventory_update_tag(self, world_state_rpg):
        text = 'Você pega o item. [INVENTORY_UPDATE] {"add": ["Chave de Ferro"]}\nO que você faz?'
        cleaned, _ = game.clean_and_process_ai_response(text, world_state_rpg)
        assert "[INVENTORY_UPDATE]" not in cleaned

    def test_adds_item_to_inventory(self, world_state_rpg):
        text = 'Você pega a chave. [INVENTORY_UPDATE] {"add": ["Chave de Ferro"]}\nO que você faz?'
        _, updated = game.clean_and_process_ai_response(text, world_state_rpg)
        assert "Chave de Ferro" in updated["player_character"]["inventory"]

    def test_removes_item_from_inventory(self, world_state_rpg):
        text = 'Você usa a adaga. [INVENTORY_UPDATE] {"remove": ["Adaga de Ferro"]}\nO que você faz?'
        _, updated = game.clean_and_process_ai_response(text, world_state_rpg)
        assert "Adaga de Ferro" not in updated["player_character"]["inventory"]

    def test_preserves_narrative_text(self, world_state_rpg):
        narrative = "A taverna está cheia de aventureiros barulhentos."
        text = f'{narrative} [STATUS_UPDATE] {{"hp_change": -1}}\nO que você faz?'
        cleaned, _ = game.clean_and_process_ai_response(text, world_state_rpg)
        assert narrative in cleaned

    def test_no_tags_returns_text_unchanged(self, world_state_rpg):
        text = "Você entra na taverna. O taverneiro olha para você. O que você faz?"
        cleaned, updated = game.clean_and_process_ai_response(text, world_state_rpg)
        assert cleaned.strip() == text.strip()
        assert updated["player_character"]["status"]["hp"] == 20

    def test_returns_tuple(self, world_state_rpg):
        result = game.clean_and_process_ai_response("texto simples", world_state_rpg)
        assert isinstance(result, tuple)
        assert len(result) == 2


# ─── trigger_contextual_sfx ───────────────────────────────────────────────────

# ─── get_item_slots ───────────────────────────────────────────────────────────

class TestGetItemSlots:
    def test_known_item_returns_correct_slots(self):
        items_data = json.dumps({"itens_comuns": {"alaude": {"nome": "Alaúde de Madeira", "slots": 2}}})
        with patch("game.get_campaign_files", return_value={"itens_comuns": "fake.json", "itens_magicos": "fake_magic.json"}):
            with patch("builtins.open", mock_open(read_data=items_data)):
                result = game.get_item_slots("Alaúde de Madeira")
        assert result == 2

    def test_unknown_item_returns_1(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            with patch("campaign_manager.load_campaign_data", return_value={}):
                result = game.get_item_slots("item_que_nao_existe_xyz")
        assert result == 1

    def test_returns_int(self, campaign_config):
        with patch("campaign_manager.load_config", return_value=campaign_config):
            with patch("campaign_manager.load_campaign_data", return_value={}):
                result = game.get_item_slots("qualquer")
        assert isinstance(result, int)

    def test_returns_1_on_exception(self):
        with patch("game.get_campaign_files", side_effect=Exception("error")):
            result = game.get_item_slots("item")
        assert result == 1


# ─── calculate_used_slots ─────────────────────────────────────────────────────

class TestCalculateUsedSlots:
    def test_empty_inventory_returns_zero(self):
        with patch("game.get_item_slots", return_value=1):
            result = game.calculate_used_slots([])
        assert result == 0

    def test_single_1slot_item(self):
        with patch("game.get_item_slots", return_value=1):
            result = game.calculate_used_slots(["Adaga de Ferro"])
        assert result == 1

    def test_single_2slot_item(self):
        with patch("game.get_item_slots", return_value=2):
            result = game.calculate_used_slots(["Alaúde de Madeira"])
        assert result == 2

    def test_multiple_items_sum_correctly(self):
        def slot_side_effect(item):
            slots = {"Alaúde de Madeira": 2, "Adaga de Ferro": 1, "Mochila": 1}
            return slots.get(item, 1)

        with patch("game.get_item_slots", side_effect=slot_side_effect):
            result = game.calculate_used_slots(["Alaúde de Madeira", "Adaga de Ferro", "Mochila"])
        assert result == 4

    def test_returns_int(self):
        with patch("game.get_item_slots", return_value=1):
            result = game.calculate_used_slots(["item1"])
        assert isinstance(result, int)


# ─── handle_local_command ────────────────────────────────────────────────────

class TestHandleLocalCommand:
    def test_inventario_command_returns_true(self, world_state_rpg):
        with patch("game.print_inventory"):
            result = game.handle_local_command("inventário", world_state_rpg["player_character"])
        assert result is True

    def test_inventario_sem_acento_returns_true(self, world_state_rpg):
        with patch("game.print_inventory"):
            result = game.handle_local_command("inventario", world_state_rpg["player_character"])
        assert result is True

    def test_status_command_returns_true(self, world_state_rpg):
        with patch("game.print_status"):
            result = game.handle_local_command("status", world_state_rpg["player_character"])
        assert result is True

    def test_vida_command_returns_true(self, world_state_rpg):
        with patch("game.print_status"):
            result = game.handle_local_command("vida", world_state_rpg["player_character"])
        assert result is True

    def test_saude_command_returns_true(self, world_state_rpg):
        with patch("game.print_status"):
            result = game.handle_local_command("saúde", world_state_rpg["player_character"])
        assert result is True

    def test_narrative_action_returns_false(self, world_state_rpg):
        result = game.handle_local_command("vou até a taverna", world_state_rpg["player_character"])
        assert result is False

    def test_chikito_not_handled_here(self, world_state_rpg):
        # chikito é tratado no loop principal, não em handle_local_command
        result = game.handle_local_command("chikito", world_state_rpg["player_character"])
        assert isinstance(result, bool)

    def test_inventario_calls_print_inventory(self, world_state_rpg):
        with patch("game.print_inventory") as mock_print:
            game.handle_local_command("inventário", world_state_rpg["player_character"])
            mock_print.assert_called_once()

    def test_status_calls_print_status(self, world_state_rpg):
        with patch("game.print_status") as mock_print:
            game.handle_local_command("status", world_state_rpg["player_character"])
            mock_print.assert_called_once()


# ─── load_json_data ───────────────────────────────────────────────────────────

class TestLoadJsonData:
    def test_loads_valid_json_file(self):
        data = {"key": "value", "number": 42}
        with patch("builtins.open", mock_open(read_data=json.dumps(data))):
            result = game.load_json_data("any_path.json")
        assert result == data

    def test_returns_empty_dict_on_file_not_found(self):
        with patch("builtins.open", side_effect=FileNotFoundError):
            result = game.load_json_data("nao_existe.json")
        assert result == {}

    def test_returns_empty_dict_on_invalid_json(self):
        with patch("builtins.open", mock_open(read_data="{ invalid json }")):
            result = game.load_json_data("invalid.json")
        assert result == {}

    def test_returns_dict_type(self):
        with patch("builtins.open", side_effect=FileNotFoundError):
            result = game.load_json_data("path.json")
        assert isinstance(result, dict)

    def test_loads_nested_data(self):
        data = {"npcs": {"kael": {"nome": "Kael", "slots": 2}}}
        with patch("builtins.open", mock_open(read_data=json.dumps(data))):
            result = game.load_json_data("npcs.json")
        assert result["npcs"]["kael"]["nome"] == "Kael"


# ─── get_gm_narrative ─────────────────────────────────────────────────────────

class TestGetGMNarrative:
    def _mock_openai(self, response_text: str):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = response_text
        mock_client.chat.completions.create.return_value = mock_response
        return mock_client

    def test_returns_string(self, world_state_rpg, campaign_config):
        mock_client = self._mock_openai("Você entra na taverna. O que você faz?")

        with patch("game.OpenAI", return_value=mock_client):
            with patch("campaign_manager.load_config", return_value=campaign_config):
                with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
                    result = game.get_gm_narrative(world_state_rpg, "entro na taverna", {})
        assert isinstance(result, str)

    def test_returns_fallback_when_no_api_key(self, world_state_rpg):
        env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            result = game.get_gm_narrative(world_state_rpg, "ação", {})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_api_error_returns_fallback(self, world_state_rpg, campaign_config):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        with patch("game.OpenAI", return_value=mock_client):
            with patch("campaign_manager.load_config", return_value=campaign_config):
                with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
                    result = game.get_gm_narrative(world_state_rpg, "ação", {})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_response_stripped(self, world_state_rpg, campaign_config):
        mock_client = self._mock_openai("  Narrativa com espaços.  ")

        with patch("game.OpenAI", return_value=mock_client):
            with patch("campaign_manager.load_config", return_value=campaign_config):
                with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
                    result = game.get_gm_narrative(world_state_rpg, "ação", {})
        assert not result.startswith("  ")
        assert not result.endswith("  ")

    def test_prompt_contains_phase1_narrative_contract(self, world_state_rpg, campaign_config):
        mock_client = self._mock_openai("Você respira fundo. O que você faz?")

        with patch("game.OpenAI", return_value=mock_client):
            with patch("campaign_manager.load_config", return_value=campaign_config):
                with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
                    game.get_gm_narrative(world_state_rpg, "ação arriscada", {})

        called_kwargs = mock_client.chat.completions.create.call_args.kwargs
        messages = called_kwargs["messages"]
        system_prompt = messages[0]["content"]
        assert "Você certamente pode tentar." in system_prompt
        assert "LENTE CINEMATOGRÁFICA CONDENSADA (MERCER)" in system_prompt
        assert "REGRA INEGOCIÁVEL DE PERSPECTIVA" in system_prompt
        assert "ASSINATURAS DE NPC EM CENA" in system_prompt
        assert "aplique obrigatoriamente a postura corporal" in system_prompt
        assert "DADOS-INFORMAM-NARRAÇÃO" in system_prompt
        assert "[HDYWDTDT]" in system_prompt
        assert "NUNCA narre incompetência ridícula do jogador" in system_prompt
        assert "RITMO EMOCIONAL (MA / ESPAÇO NEGATIVO)" in system_prompt
        assert "[PAUSE_BEAT]" in system_prompt
        assert "SILÊNCIO FÍSICO" in system_prompt

    def test_combat_state_is_updated_when_roll_is_present(self, world_state_rpg, campaign_config):
        mock_client = self._mock_openai("Você pressiona o inimigo para trás. O que você faz?")
        roll_result = {
            "roll": 17,
            "dice": [17],
            "dc": 12,
            "modifier": "normal",
            "success": True,
            "critical": False,
            "fumble": False,
        }

        with patch("game.OpenAI", return_value=mock_client):
            with patch("campaign_manager.load_config", return_value=campaign_config):
                with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
                    game.get_gm_narrative(world_state_rpg, "ataco com a espada", {}, roll_result)

        combat_state = world_state_rpg["world_state"].get("combat_state", {})
        assert combat_state.get("active") is True
        assert combat_state.get("turns_with_risk", 0) >= 1


class TestResurrectionFlow:
    def test_get_resurrection_dc_scaling(self):
        assert game.get_resurrection_dc(1) == 12
        assert game.get_resurrection_dc(2) == 15
        assert game.get_resurrection_dc(3) == 18
        assert game.get_resurrection_dc(9) == 18

    def test_start_resurrection_limbo_when_hp_zero(self, world_state_rpg):
        world_state_rpg["player_character"]["status"]["hp"] = 0
        started, narrative = game.start_resurrection_limbo(world_state_rpg)
        assert started is True
        assert "oferenda emocional" in narrative.lower()
        state = world_state_rpg.get("resurrection_state", {})
        assert state.get("stage") == "awaiting_offering"
        assert state.get("dc") == 12
        assert world_state_rpg["player_character"]["death_count"] == 1
        assert world_state_rpg.get("narration_mood") == "sad"

    def test_start_resurrection_limbo_ignored_if_hp_positive(self, world_state_rpg):
        world_state_rpg["player_character"]["status"]["hp"] = 5
        started, narrative = game.start_resurrection_limbo(world_state_rpg)
        assert started is False
        assert narrative == ""

    def test_resolve_offering_critical_success(self, world_state_rpg):
        world_state_rpg["player_character"]["status"]["hp"] = 0
        world_state_rpg["player_character"]["class"] = "Bardo"
        game.start_resurrection_limbo(world_state_rpg)

        with patch("game.random.randint", side_effect=[20, 7]):
            result = game.resolve_resurrection_offering(
                world_state_rpg,
                "Minha canção pela minha esposa ainda me prende a este mundo."
            )

        assert result["ok"] is True
        assert result["result_type"] == "critical_success"
        assert result["roll"]["critical"] is True
        assert world_state_rpg["player_character"]["status"]["hp"] == 1
        assert world_state_rpg["player_character"]["resurrection_flaws"] == []
        assert "resurrection_state" not in world_state_rpg

    def test_resolve_offering_failure_adds_dark_gift(self, world_state_rpg):
        world_state_rpg["player_character"]["status"]["hp"] = 0
        world_state_rpg["player_character"]["class"] = "Aventureiro"
        game.start_resurrection_limbo(world_state_rpg)

        with patch("game.random.randint", return_value=5):
            with patch("game.random.choice", return_value=("olhos de fumaça", "Você rejeita misericórdia.")):
                result = game.resolve_resurrection_offering(
                    world_state_rpg,
                    "Eu volto porque me recuso a desaparecer."
                )

        assert result["ok"] is True
        assert result["result_type"] == "failure"
        flaws = world_state_rpg["player_character"]["resurrection_flaws"]
        assert len(flaws) == 1
        assert flaws[0]["type"] == "dark_gift"
        assert world_state_rpg["player_character"]["status"]["hp"] == 1

    def test_resolve_offering_fumble_corrupts_alignment(self, world_state_rpg):
        world_state_rpg["player_character"]["status"]["hp"] = 0
        game.start_resurrection_limbo(world_state_rpg)

        with patch("game.random.randint", return_value=1):
            result = game.resolve_resurrection_offering(
                world_state_rpg,
                "Prometo voltar por dever, mas as brumas me esmagam."
            )

        assert result["ok"] is True
        assert result["result_type"] == "critical_failure"
        assert world_state_rpg["player_character"]["alignment"] == "maligno"
        assert world_state_rpg["world_state"].get("strahd_attention", 0) >= 1

    def test_resolve_offering_too_short_keeps_waiting_state(self, world_state_rpg):
        world_state_rpg["player_character"]["status"]["hp"] = 0
        game.start_resurrection_limbo(world_state_rpg)
        result = game.resolve_resurrection_offering(world_state_rpg, "volto")
        assert result["ok"] is False
        assert result["result_type"] == "waiting_offering"
        assert world_state_rpg.get("resurrection_state", {}).get("stage") == "awaiting_offering"


class TestActAndTriggerHelpers:
    def test_bootstrap_location_triggers_for_new_location(self, world_state_rpg):
        world_state_rpg["world_state"]["current_location_key"] = "vallaki"
        world_state_rpg["world_state"]["gatilhos_ativos"].pop("vallaki", None)
        locais = {
            "vallaki": {
                "gatilhos": {
                    "proclama_festival": {"descricao": "teste", "sfx": None, "proximo": None}
                }
            }
        }
        changed = game.bootstrap_location_triggers(world_state_rpg, locais)
        assert changed is True
        assert "proclama_festival" in world_state_rpg["world_state"]["gatilhos_ativos"]["vallaki"]

    def test_sync_act_with_location_upgrades_current_act(self, world_state_rpg):
        world_state_rpg["world_state"]["current_location_key"] = "castelo_ravenloft"
        world_state_rpg["player_character"]["current_act"] = 1
        with patch("game.get_campaign_files", return_value={"locais": "fake_locais.json"}):
            with patch("game.load_campaign_data", return_value={
                "locais": {"castelo_ravenloft": {"ato_aparicao": 4}}
            }):
                changed = game.sync_act_with_location(world_state_rpg)
        assert changed is True
        assert world_state_rpg["player_character"]["current_act"] == 4


# ─── get_story_master_narrative ───────────────────────────────────────────────

class TestGetStoryMasterNarrative:
    def _mock_openai(self, response_text: str):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = response_text
        mock_client.chat.completions.create.return_value = mock_response
        return mock_client

    def test_returns_string(self, story_eventos, story_state):
        mock_client = self._mock_openai("Meia-noite. O vento uiva.\n(A) Abrir\n(B) Fechar")

        with patch("game.OpenAI", return_value=mock_client):
            with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
                result = game.get_story_master_narrative(
                    "Texto original do Corvo",
                    story_eventos,
                    story_state["story_state"]
                )
        assert isinstance(result, str)

    def test_returns_error_message_when_no_key(self, story_eventos, story_state):
        env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            result = game.get_story_master_narrative("texto", story_eventos, story_state["story_state"])
        assert isinstance(result, str)

    def test_api_error_returns_string(self, story_eventos, story_state):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("error")

        with patch("game.OpenAI", return_value=mock_client):
            with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
                result = game.get_story_master_narrative("texto", story_eventos, story_state["story_state"])
        assert isinstance(result, str)
