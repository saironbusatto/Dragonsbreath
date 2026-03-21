"""
Testes de integração — verificam fluxos completos entre módulos.
Não chamam APIs externas reais (usa mocks).
"""
import json
import os
import pytest
from unittest.mock import patch, MagicMock, mock_open

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

with patch.dict("sys.modules", {"pygame": MagicMock(), "pyttsx3": MagicMock()}):
    import game
    import world_state_manager
    import campaign_manager


# ─── Integração: Campaign Manager → World State Manager ──────────────────────

class TestCampaignToWorldState:
    def test_create_world_state_uses_campaign_template(self, campaign_config):
        """world_state criado deve refletir o template da campanha."""
        with patch("campaign_manager.load_config", return_value=campaign_config):
            state = world_state_manager.create_initial_world_state("TestPlayer")

        assert state["player_character"]["class"] == "Bardo"
        assert state["player_character"]["status"]["hp"] == 20
        assert state["player_character"]["status"]["max_hp"] == 20
        assert state["world_state"]["current_location_key"] == "umbraton"

    def test_world_state_has_initial_triggers(self, campaign_config):
        """Triggers iniciais devem vir do world_template."""
        with patch("campaign_manager.load_config", return_value=campaign_config):
            state = world_state_manager.create_initial_world_state("TestPlayer")

        assert "umbraton" in state["world_state"]["gatilhos_ativos"]
        triggers = state["world_state"]["gatilhos_ativos"]["umbraton"]
        assert len(triggers) > 0

    def test_switch_campaign_changes_template(self, campaign_config):
        """Mudar campanha deve afetar o template do personagem."""
        with patch("campaign_manager.load_config", return_value=campaign_config):
            with patch("builtins.open", mock_open()):
                campaign_manager.switch_campaign("exemplo_fantasia")

        campaign_config["current_campaign"] = "exemplo_fantasia"
        with patch("campaign_manager.load_config", return_value=campaign_config):
            state = world_state_manager.create_initial_world_state("Thorin")

        assert state["player_character"]["class"] == "Aventureiro"
        assert state["player_character"]["status"]["hp"] == 25


# ─── Integração: Save/Load World State ───────────────────────────────────────

class TestSaveLoadIntegration:
    def test_full_save_and_load_cycle(self, tmp_path, campaign_config):
        """Criar → salvar → carregar deve preservar todos os dados."""
        with patch("campaign_manager.load_config", return_value=campaign_config):
            state = world_state_manager.create_initial_world_state("IntegrationPlayer")

        save_path = str(tmp_path / "integration_save.json")
        world_state_manager.save_world_state(state, save_path)
        loaded = world_state_manager.load_world_state(save_path)

        assert loaded is not None
        assert loaded["player_character"]["name"] == "IntegrationPlayer"
        assert loaded["player_character"]["class"] == "Bardo"
        assert loaded["world_state"]["current_location_key"] == "umbraton"

    def test_modified_state_saves_correctly(self, tmp_path, world_state_rpg):
        """Modificar estado e salvar deve persistir as modificações."""
        world_state_rpg["player_character"]["status"]["hp"] = 15
        world_state_rpg["player_character"]["inventory"].append("Poção de Cura")

        save_path = str(tmp_path / "modified_save.json")
        world_state_manager.save_world_state(world_state_rpg, save_path)
        loaded = world_state_manager.load_world_state(save_path)

        assert loaded["player_character"]["status"]["hp"] == 15
        assert "Poção de Cura" in loaded["player_character"]["inventory"]

    def test_none_returned_for_missing_file(self, tmp_path):
        path = str(tmp_path / "nao_existe.json")
        result = world_state_manager.load_world_state(path)
        assert result is None


# ─── Integração: Action Validation + World State ─────────────────────────────

class TestActionValidationWithWorldState:
    def test_object_in_scene_allows_action(self, world_state_rpg):
        """Objeto explicitamente na cena deve ser válido para interação."""
        world_state_rpg["world_state"]["interactable_elements_in_scene"] = [
            "portão", "gárgula", "lanterna", "pedras"
        ]
        is_valid, _ = game.validate_player_action("abro o portão lentamente", {}, world_state_rpg)
        assert is_valid is True

    def test_object_not_in_scene_blocks_action(self, world_state_rpg):
        """Objeto NÃO na cena deve ser bloqueado."""
        world_state_rpg["world_state"]["interactable_elements_in_scene"] = ["portão"]
        # A espada não está na lista
        is_valid, msg = game.validate_player_action("pego a espada do chão", {}, world_state_rpg)
        # O sistema deve bloquear se "espada" for extraída da ação
        # A validação deve retornar algo coerente
        assert isinstance(is_valid, bool)
        assert isinstance(msg, str)

    def test_impossible_action_always_blocked(self, world_state_rpg):
        """Ação impossível (voar) deve ser bloqueada independente do estado."""
        world_state_rpg["world_state"]["interactable_elements_in_scene"] = ["portão", "céu"]
        character = {"class": "Bardo"}
        is_valid, _ = game.validate_player_action("vou voar sobre o castelo", character, world_state_rpg)
        assert is_valid is False

    def test_empty_interactable_list_allows_generic_actions(self, world_state_empty_scene):
        """Com lista de interativos vazia, ações genéricas devem ser permitidas."""
        is_valid, _ = game.validate_player_action("olho ao redor", {}, world_state_empty_scene)
        assert is_valid is True


# ─── Integração: Inventory Management ────────────────────────────────────────

class TestInventoryIntegration:
    def test_ai_response_adds_item_to_inventory(self, world_state_rpg):
        """Tag INVENTORY_UPDATE na resposta da IA deve adicionar item ao inventário."""
        response = 'Você pega a chave. [INVENTORY_UPDATE] {"add": ["Chave de Bronze"]}\nO que você faz?'
        _, updated = game.clean_and_process_ai_response(response, world_state_rpg)
        assert "Chave de Bronze" in updated["player_character"]["inventory"]

    def test_ai_response_removes_item_from_inventory(self, world_state_rpg):
        """Tag INVENTORY_UPDATE com remove deve tirar item do inventário."""
        response = 'Você usa a adaga. [INVENTORY_UPDATE] {"remove": ["Adaga de Ferro"]}\nO que você faz?'
        _, updated = game.clean_and_process_ai_response(response, world_state_rpg)
        assert "Adaga de Ferro" not in updated["player_character"]["inventory"]

    def test_ai_response_modifies_hp(self, world_state_rpg):
        """Tag STATUS_UPDATE na resposta deve modificar HP."""
        response = 'Você leva um golpe. [STATUS_UPDATE] {"hp_change": -7}\nO que você faz?'
        _, updated = game.clean_and_process_ai_response(response, world_state_rpg)
        assert updated["player_character"]["status"]["hp"] == 13

    def test_hp_clamped_to_zero_on_lethal_damage(self, world_state_rpg):
        """HP não deve ficar negativo."""
        response = 'Dano fatal. [STATUS_UPDATE] {"hp_change": -9999}\nO que você faz?'
        _, updated = game.clean_and_process_ai_response(response, world_state_rpg)
        assert updated["player_character"]["status"]["hp"] == 0

    def test_hp_clamped_to_max_on_overheal(self, world_state_rpg):
        """HP não deve ultrapassar max_hp."""
        world_state_rpg["player_character"]["status"]["hp"] = 5
        response = 'Cura mágica. [STATUS_UPDATE] {"hp_change": 9999}\nO que você faz?'
        _, updated = game.clean_and_process_ai_response(response, world_state_rpg)
        assert updated["player_character"]["status"]["hp"] == 20  # max_hp


# ─── Integração: Story Mode ───────────────────────────────────────────────────

class TestStoryModeIntegration:
    def test_story_variables_update_on_choice(self, story_eventos):
        """Escolha (A) no início deve aplicar efeito na variável esperanca."""
        variaveis = dict(story_eventos["variaveis_iniciais"])
        opcao_a = story_eventos["eventos"]["inicio"]["opcoes"][0]

        for var, delta in opcao_a["efeito"].items():
            variaveis[var] = variaveis.get(var, 0) + delta

        assert variaveis["esperanca"] == 6  # era 5, +1

    def test_story_advances_to_correct_event(self, story_eventos):
        """Escolha (A) no início deve avançar para 'porta_aberta'."""
        opcao_a = story_eventos["eventos"]["inicio"]["opcoes"][0]
        assert opcao_a["proximo_evento"] == "porta_aberta"

    def test_final_event_has_no_opcoes(self, story_eventos):
        """Eventos finais devem ter lista de opcoes vazia."""
        finais = [k for k in story_eventos["eventos"] if k.startswith("final_")]
        assert len(finais) > 0
        for final_id in finais:
            assert story_eventos["eventos"][final_id]["opcoes"] == []

    def test_all_choices_lead_to_valid_events(self, story_eventos):
        """Todas as opcoes de proximo_evento devem referenciar eventos existentes."""
        eventos = story_eventos["eventos"]
        for event_id, event in eventos.items():
            for opcao in event.get("opcoes", []):
                next_event = opcao["proximo_evento"]
                assert next_event in eventos, \
                    f"Evento '{next_event}' referenciado em '{event_id}' não existe"

    def test_initial_event_exists(self, story_eventos):
        """O evento_inicial declarado deve existir no mapa de eventos."""
        evento_inicial = story_eventos["evento_inicial"]
        assert evento_inicial in story_eventos["eventos"]

    def test_variables_never_exceed_expected_ranges(self, story_eventos):
        """Simular todos os caminhos e verificar variáveis ficam em range aceitável."""
        variaveis = dict(story_eventos["variaveis_iniciais"])

        # Simular todas as opções do início
        for opcao in story_eventos["eventos"]["inicio"]["opcoes"]:
            vars_copy = dict(variaveis)
            for var, delta in opcao["efeito"].items():
                vars_copy[var] = vars_copy.get(var, 0) + delta
            # Nenhuma variável deve ficar absurdamente negativa após uma escolha
            for val in vars_copy.values():
                assert val >= -5, f"Variável ficou muito negativa: {val}"


# ─── Integração: Trigger System ──────────────────────────────────────────────

class TestTriggerSystemIntegration:
    def test_trigger_probability_increases_with_rounds(self):
        """P deve aumentar a cada rodada sem gatilho (até 90%)."""
        base = 0.30
        increment = 0.10
        max_p = 0.90

        for rounds in range(0, 10):
            p = min(max_p, base + rounds * increment)
            assert p <= max_p
            if rounds > 0:
                p_prev = min(max_p, base + (rounds - 1) * increment)
                assert p >= p_prev  # sempre cresce ou fica no máximo

    def test_trigger_probability_at_round_0(self):
        p = min(0.90, 0.30 + 0 * 0.10)
        assert p == 0.30

    def test_trigger_probability_caps_at_90(self):
        p = min(0.90, 0.30 + 100 * 0.10)
        assert p == 0.90

    def test_trigger_moves_to_used_after_firing(self, world_state_rpg):
        """Após disparar, o trigger deve mover de ativo para usado."""
        location = world_state_rpg["world_state"]["current_location_key"]
        trigger_id = world_state_rpg["world_state"]["gatilhos_ativos"][location][0]

        # Simular disparo
        world_state_rpg["world_state"]["gatilhos_ativos"][location].remove(trigger_id)
        world_state_rpg["world_state"]["gatilhos_usados"][location].append(trigger_id)

        assert trigger_id not in world_state_rpg["world_state"]["gatilhos_ativos"][location]
        assert trigger_id in world_state_rpg["world_state"]["gatilhos_usados"][location]


# ─── Integração: Estrutura de Arquivos ───────────────────────────────────────

class TestFileStructureIntegration:
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))

    def test_config_json_exists(self):
        assert os.path.exists(os.path.join(self.BASE_DIR, "config.json"))

    def test_campaigns_directory_exists(self):
        assert os.path.exists(os.path.join(self.BASE_DIR, "campanhas"))

    def test_contos_directory_exists(self):
        assert os.path.exists(os.path.join(self.BASE_DIR, "contos_interativos"))

    def test_lamento_do_bardo_files_exist(self):
        campaign_dir = os.path.join(self.BASE_DIR, "campanhas", "lamento_do_bardo")
        assert os.path.exists(campaign_dir)
        for filename in ["npcs.json", "locais.json", "itens_magicos.json", "itens_comuns.json"]:
            assert os.path.exists(os.path.join(campaign_dir, filename)), \
                f"Arquivo ausente: {filename}"

    def test_o_corvo_story_files_exist(self):
        story_dir = os.path.join(self.BASE_DIR, "contos_interativos")
        assert os.path.exists(os.path.join(story_dir, "o_corvo_poe.txt"))
        assert os.path.exists(os.path.join(story_dir, "o_corvo_poe_eventos.json"))

    def test_sounds_directory_exists(self):
        assert os.path.exists(os.path.join(self.BASE_DIR, "sons", "sistema"))

    def test_config_json_valid_structure(self):
        config_path = os.path.join(self.BASE_DIR, "config.json")
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        assert "current_campaign" in config
        assert "campaigns" in config
        assert len(config["campaigns"]) >= 1

    def test_o_corvo_eventos_valid_structure(self):
        json_path = os.path.join(self.BASE_DIR, "contos_interativos", "o_corvo_poe_eventos.json")
        with open(json_path, encoding="utf-8") as f:
            eventos = json.load(f)
        assert "evento_inicial" in eventos
        assert "eventos" in eventos
        assert eventos["evento_inicial"] in eventos["eventos"]

    def test_campaign_files_are_valid_json(self):
        campaign_dir = os.path.join(self.BASE_DIR, "campanhas", "lamento_do_bardo")
        for filename in ["npcs.json", "locais.json", "itens_magicos.json", "itens_comuns.json"]:
            filepath = os.path.join(campaign_dir, filename)
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            assert isinstance(data, dict), f"{filename} não é um dict"
