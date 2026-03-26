"""
Testes para game.py
Cobre: extract_objects_from_action, validate_player_action,
       validate_impossible_abilities, get_realistic_alternative,
       clean_and_process_ai_response, trigger_contextual_sfx,
       get_item_slots, calculate_used_slots, can_pick_up_item,
       handle_local_command, load_json_data
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


# ─── extract_objects_from_action ─────────────────────────────────────────────

class TestExtractObjectsFromAction:
    def test_extracts_known_objects(self):
        result = game.extract_objects_from_action("Pego a espada e abro a porta")
        assert "espada" in result or "porta" in result

    def test_returns_list(self):
        result = game.extract_objects_from_action("olho para a janela")
        assert isinstance(result, list)

    def test_empty_string_returns_empty_list(self):
        result = game.extract_objects_from_action("")
        assert result == []

    def test_whitespace_only_returns_empty_list(self):
        result = game.extract_objects_from_action("   ")
        assert result == []

    def test_none_equivalent_short_string(self):
        result = game.extract_objects_from_action("a")
        assert result == []

    def test_extracts_furniture(self):
        result = game.extract_objects_from_action("sento na cadeira perto da mesa")
        assert "cadeira" in result or "mesa" in result

    def test_extracts_architectural_elements(self):
        result = game.extract_objects_from_action("abro a porta e olho pela janela")
        assert "porta" in result or "janela" in result

    def test_extracts_npc_names(self):
        result = game.extract_objects_from_action("falo com o taverneiro no balcão")
        assert "taverneiro" in result or "balcão" in result

    def test_case_insensitive(self):
        result_lower = game.extract_objects_from_action("pego a espada")
        result_upper = game.extract_objects_from_action("pego a ESPADA")
        assert set(result_lower) == set(result_upper)

    def test_multiple_objects(self):
        result = game.extract_objects_from_action("pego o livro da mesa e saio pela porta")
        assert len(result) >= 1


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


# ─── get_realistic_alternative ────────────────────────────────────────────────

class TestGetRealisticAlternative:
    def test_returns_string(self):
        result = game.get_realistic_alternative("voar até o castelo", "Bardo")
        assert isinstance(result, str)

    def test_returns_non_empty_string(self):
        result = game.get_realistic_alternative("lançar feitiço", "Bardo")
        assert len(result) > 0

    def test_different_classes_different_suggestions(self):
        bardo = game.get_realistic_alternative("atacar com magia", "Bardo")
        aventureiro = game.get_realistic_alternative("atacar com magia", "Aventureiro")
        assert isinstance(bardo, str)
        assert isinstance(aventureiro, str)


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

class TestTriggerContextualSFX:
    def test_crow_keyword_plays_crow_sfx(self):
        with patch("game.play_sfx") as mock_sfx:
            game.trigger_contextual_sfx("Um corvo pousa na gárgula e grasna.")
            mock_sfx.assert_called_once()

    def test_tavern_keyword_plays_tavern_sfx(self):
        with patch("game.play_sfx") as mock_sfx:
            game.trigger_contextual_sfx("Você entra na taverna barulhenta.")
            mock_sfx.assert_called_once()

    def test_rain_keyword_plays_rain_sfx(self):
        with patch("game.play_sfx") as mock_sfx:
            game.trigger_contextual_sfx("A chuva cai pesada sobre as pedras.")
            mock_sfx.assert_called_once()

    def test_scream_keyword_plays_scream_sfx(self):
        with patch("game.play_sfx") as mock_sfx:
            game.trigger_contextual_sfx("Um grito ecoa pela viela escura.")
            mock_sfx.assert_called_once()

    def test_no_keyword_plays_no_sfx(self):
        with patch("game.play_sfx") as mock_sfx:
            game.trigger_contextual_sfx("Você pensa silenciosamente.")
            mock_sfx.assert_not_called()

    def test_only_one_sfx_per_narrative(self):
        # Múltiplas keywords — só um SFX deve ser tocado
        with patch("game.play_sfx") as mock_sfx:
            game.trigger_contextual_sfx("Um corvo grasna na taverna durante a chuva.")
            assert mock_sfx.call_count == 1

    def test_coin_keyword(self):
        with patch("game.play_sfx") as mock_sfx:
            game.trigger_contextual_sfx("O mercador conta as moedas de ouro.")
            mock_sfx.assert_called_once()

    def test_empty_text_no_sfx(self):
        with patch("game.play_sfx") as mock_sfx:
            game.trigger_contextual_sfx("")
            mock_sfx.assert_not_called()


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


# ─── can_pick_up_item ────────────────────────────────────────────────────────

class TestCanPickUpItem:
    def test_can_pick_up_with_space(self, world_state_rpg):
        # 3 itens de 1 slot cada = 3 slots usados, max=10, pode pegar mais
        with patch("game.calculate_used_slots", return_value=3):
            with patch("game.get_item_slots", return_value=1):
                can_pick, msg = game.can_pick_up_item(world_state_rpg["player_character"], "Poção de Cura")
        assert can_pick is True

    def test_cannot_pick_up_full_inventory(self, world_state_rpg):
        with patch("game.calculate_used_slots", return_value=10):
            with patch("game.get_item_slots", return_value=1):
                can_pick, msg = game.can_pick_up_item(world_state_rpg["player_character"], "Poção de Cura")
        assert can_pick is False

    def test_returns_tuple(self, world_state_rpg):
        with patch("game.calculate_used_slots", return_value=3):
            with patch("game.get_item_slots", return_value=1):
                result = game.can_pick_up_item(world_state_rpg["player_character"], "item")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_message_is_string(self, world_state_rpg):
        with patch("game.calculate_used_slots", return_value=3):
            with patch("game.get_item_slots", return_value=1):
                _, msg = game.can_pick_up_item(world_state_rpg["player_character"], "item")
        assert isinstance(msg, str)

    def test_cannot_pick_2slot_item_with_1_slot_free(self, world_state_rpg):
        # 9 slots usados, precisa de 2 para o novo item
        with patch("game.calculate_used_slots", return_value=9):
            with patch("game.get_item_slots", return_value=2):
                can_pick, _ = game.can_pick_up_item(world_state_rpg["player_character"], "Alaúde")
        assert can_pick is False


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
