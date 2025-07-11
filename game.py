import google.generativeai as genai
import json
import os
import re
import random
from world_state_manager import update_world_state, create_initial_world_state, load_world_state, save_world_state
from campaign_manager import get_campaign_files, load_campaign_data, get_current_campaign

MAX_INVENTORY_SLOTS = 5
QUEST_ITEM_KEYWORDS = ['moeda', 'chave', 'nota', 'mapa', 'pergaminho', 'cristal', 'símbolo', 'anel', 'diapasão']

def get_gm_narrative(world_state: dict, player_action: str, game_context: dict) -> str:
    try:
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            print("ERRO: GEMINI_API_KEY não encontrada nas variáveis de ambiente")
            return "O Mestre do Jogo não consegue se conectar aos planos astrais. (API Key não configurada). O que você faz?"
        genai.configure(api_key=api_key)
    except Exception as e:
        print(f"ERRO na configuração da API: {e}")
        return "O Mestre do Jogo não consegue se conectar aos planos astrais. (API Key não configurada). O que você faz?"

    campaign = get_current_campaign()
    campaign_name = campaign.get('name', 'RPG de Aventura')
    
    system_prompt = f"""Você é um Mestre de Jogo narrando "{campaign_name}".

--- ESTADO ATUAL DO MUNDO ---
{json.dumps(world_state, indent=2, ensure_ascii=False)}

--- CONTEXTO DO JOGO ---
NPCs: {json.dumps(game_context.get('npcs', {}), indent=2, ensure_ascii=False)}
Itens: {json.dumps(game_context.get('items', {}), indent=2, ensure_ascii=False)}
Locais: {json.dumps(game_context.get('locais', {}), indent=2, ensure_ascii=False)}
Gatilhos Narrativos Ativos: {json.dumps(game_context.get('gatilhos', []), indent=2, ensure_ascii=False)}

--- AÇÃO DO JOGADOR ---
{player_action}

--- REGRAS ---
1. Narre o resultado da ação baseado no estado do mundo.
2. Use [STATUS_UPDATE] para mudanças de HP: [STATUS_UPDATE] {{"hp_change": -4}}
3. Use [INVENTORY_UPDATE] para itens: [INVENTORY_UPDATE] {{"add": ["item"]}}
4. Sempre gere consequências claras para a ação do jogador.
5. Se estiver explorando, adicione um novo evento (encontro, som, objeto, pista).
6. Ofereça pelo menos uma escolha clara para o jogador.
7. Considere o desejo ou objetivo do personagem ao narrar eventos.
8. Nunca se repita — traga algo novo ou surpreendente a cada ação.
9. Encerre sempre com: "O que você faz?"

Mestre:"""

    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash-latest",
            generation_config={"temperature": 0.75, "max_output_tokens": 1024},
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
        )
        response = model.generate_content(system_prompt)
        return response.text.strip()
    except Exception as e:
        return "O Mestre do Jogo sente uma perturbação na Força... Tente novamente. O que você faz?"

def load_json_data(filepath: str) -> dict:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def load_world_data_for_act(current_act: int) -> tuple[dict, dict, dict]:
    try:
        files = get_campaign_files()
        
        all_npcs = load_campaign_data(files.get('npcs', '')).get('npcs', {})
        all_magic_items = load_campaign_data(files.get('itens_magicos', '')).get('itens_magicos', {})
        all_common_items = load_campaign_data(files.get('itens_comuns', '')).get('itens_comuns', {})
        all_locais = load_campaign_data(files.get('locais', '')).get('locais', {})
    except Exception as e:
        print(f"Erro ao carregar dados da campanha: {e}")
        return {}, {}, {'locais': {}}

    combined_items = {**all_magic_items, **all_common_items}

    active_npcs = {k: v for k, v in all_npcs.items() if v.get('ato_aparicao', 1) <= current_act}
    active_items = {k: v for k, v in combined_items.items() if v.get('ato_aparicao', 1) <= current_act}
    active_locais = {k: v for k, v in all_locais.items() if v.get('ato_aparicao', 1) <= current_act}
    
    # Garante que todos os locais tenham gatilhos
    for key, local in active_locais.items():
        if 'gatilhos' not in local:
            local['gatilhos'] = {}

    return active_npcs, active_items, {'locais': active_locais}

def clean_and_process_ai_response(response_text: str, world_state: dict) -> tuple[str, dict]:
    character = world_state.get('player_character', {})
    narrative = response_text

    # Processa comandos básicos
    inv_match = re.search(r'\[INVENTORY_UPDATE\]\s*(\{.*?\})', narrative, re.DOTALL)
    if inv_match:
        try:
            update_data = json.loads(inv_match.group(1))
            if 'add' in update_data:
                character.setdefault('inventory', []).extend(update_data['add'])
            if 'remove' in update_data:
                for item in update_data['remove']:
                    if item in character.get('inventory', []):
                        character['inventory'].remove(item)
        except json.JSONDecodeError:
            pass
        narrative = narrative.replace(inv_match.group(0), '').strip()
    
    status_match = re.search(r'\[STATUS_UPDATE\]\s*(\{.*?\})', narrative, re.DOTALL)
    if status_match:
        try:
            update_data = json.loads(status_match.group(1))
            if 'hp_change' in update_data:
                hp_change = int(update_data['hp_change'])
                status = character.setdefault('status', {'hp': 20, 'max_hp': 20})
                current_hp = status.get('hp', 20)
                max_hp = status.get('max_hp', 20)
                new_hp = max(0, min(current_hp + hp_change, max_hp))
                character['status']['hp'] = new_hp
        except (json.JSONDecodeError, ValueError, KeyError):
            pass
        narrative = narrative.replace(status_match.group(0), '').strip()
    
    return narrative, character

def print_inventory(character: dict):
    inventory = character.get('inventory', [])
    print(f"\n--- Sua Bolsa ---")
    if not inventory:
        print("Seu inventário está vazio.")
    else:
        for item in inventory:
            print(f"- {item.capitalize()}")
    print("-------------------\n")

def print_status(character: dict):
    status = character.get('status', {'hp': 20, 'max_hp': 20})
    hp = status.get('hp', 20)
    max_hp = status.get('max_hp', 20)
    print(f"\n--- Saúde: {hp}/{max_hp} HP ---")
    print("---------------------------\n")

def handle_local_command(player_action: str, character: dict) -> bool:
    action_lower = player_action.lower()

    if any(keyword in action_lower for keyword in ['inventário', 'inventario', 'bolsa', 'itens']):
        print_inventory(character)
        return True

    if any(keyword in action_lower for keyword in ['status', 'saúde', 'vida', 'hp']):
        print_status(character)
        return True

    return False

def new_game_loop(world_state: dict, save_filepath: str, game_context: dict):
    # Garante que existe o campo rodadas_sem_gatilho
    if "rodadas_sem_gatilho" not in world_state:
        world_state["rodadas_sem_gatilho"] = 0
    
    while True:
        player_action = input("> ")
        action_lower = player_action.lower()

        if action_lower == 'chikito':
            save_world_state(world_state, save_filepath)
            print("\nJogo salvo. Obrigado por jogar Dragon's Breath!")
            break

        # Comandos locais
        character = world_state.get('player_character', {})
        if handle_local_command(player_action, character):
            world_state['player_character'] = character
            continue

        # Atualiza contexto com gatilhos do local atual
        current_act = world_state.get('player_character', {}).get('current_act', 1)
        game_context = load_game_context_for_act(current_act, world_state)
        
        # Sistema de gatilhos com chance progressiva
        # Pega local padrão da campanha atual
        campaign = get_current_campaign()
        default_location = campaign.get('world_template', {}).get('initial_location', 'local_inicial')
        
        location_key = world_state["world_state"].get("current_location_key", default_location)
        gatilhos_ativos = world_state["world_state"].get("gatilhos_ativos", {}).get(location_key, [])
        locais_definidos = game_context.get("locais", {})
        gatilhos_definidos = locais_definidos.get(location_key, {}).get("gatilhos", {})
        
        gatilho_escolhido = None
        
        # Cálculo da chance: base + acúmulo por rodadas
        base_chance = 0.3   # 30% fixo
        acumulado = world_state.get("rodadas_sem_gatilho", 0) * 0.1  # +10% por rodada sem evento
        chance_total = min(base_chance + acumulado, 0.9)  # até 90%
        
        # Sorteio
        if gatilhos_ativos and random.random() < chance_total:
            gatilho_id = random.choice(gatilhos_ativos)
            gatilho_escolhido = gatilhos_definidos.get(gatilho_id, {}).get("descricao")
            
            # Marca como usado
            world_state["world_state"]["gatilhos_ativos"][location_key].remove(gatilho_id)
            world_state["world_state"]["gatilhos_usados"].setdefault(location_key, []).append(gatilho_id)
            
            # Ativa o próximo, se houver
            proximo_id = gatilhos_definidos.get(gatilho_id, {}).get("proximo")
            if proximo_id:
                world_state["world_state"]["gatilhos_ativos"][location_key].append(proximo_id)
            
            # Reset contador
            world_state["rodadas_sem_gatilho"] = 0
        else:
            # Não ativou: incrementa
            world_state["rodadas_sem_gatilho"] = world_state.get("rodadas_sem_gatilho", 0) + 1
        
        # Adiciona gatilho à ação do jogador
        action_with_trigger = player_action
        if gatilho_escolhido:
            action_with_trigger = f"{player_action}\n[Gatilho]: {gatilho_escolhido}"
        
        # IA Mestre do Jogo
        gm_response = get_gm_narrative(world_state, action_with_trigger, game_context)
        
        # Processa resposta
        cleaned_response, updated_character = clean_and_process_ai_response(gm_response, world_state)
        world_state['player_character'] = updated_character
        
        print(f"\n{cleaned_response}\n")

        # Atualização do estado do mundo com gatilho incluído
        gatilho_para_arquivista = f"(Evento ambiental: {gatilho_escolhido})" if gatilho_escolhido else ""
        world_state = update_world_state(world_state, f"{player_action} {gatilho_para_arquivista}", gm_response)
        
        # Salva estado
        save_world_state(world_state, save_filepath)

def load_game_context_for_act(current_act: int, world_state: dict = None) -> dict:
    npcs_data, items_data, locais_data = load_world_data_for_act(current_act)
    
    # Pega gatilhos do local atual
    gatilhos = []
    if world_state:
        current_location = world_state.get('world_state', {}).get('current_location_key')
        if current_location and current_location in locais_data.get('locais', {}):
            gatilhos_dict = locais_data['locais'][current_location].get('gatilhos', {})
            gatilhos = [g.get('descricao', '') for g in gatilhos_dict.values()]
    
    return {
        'npcs': npcs_data,
        'items': items_data,
        'locais': locais_data.get('locais', {}),
        'gatilhos': gatilhos
    }

def main():
    save_filepath = 'estado_do_mundo.json'
    
    campaign = get_current_campaign()
    campaign_name = campaign.get('name', 'RPG Modular com IA')
    print(f"=== Bem-vindo a {campaign_name} ===")
    print("... (Diga 'chikito' para salvar e sair)\n")

    world_state = load_world_state(save_filepath)
    
    if world_state:
        print("--- Continuando sua jornada... ---\n")
        current_act = world_state.get('player_character', {}).get('current_act', 1)
    else:
        player_name = input("Qual é o seu nome, viajante? > ").strip()
        while not player_name:
            player_name = input("O nome não pode estar em branco. Qual é o seu nome? > ").strip()
        
        world_state = create_initial_world_state(player_name)
        current_act = 1
        
        campaign = get_current_campaign()
        campaign_name = campaign.get('name', 'sua aventura')
        print(f"\n{player_name}, {campaign_name} começa agora...")
        
        game_context = load_game_context_for_act(current_act, world_state)
        # Contexto sem gatilhos para cena de abertura (foco na apresentação do cenário)
        contexto_sem_gatilhos = {**game_context, "gatilhos": []}
        opening_scene = get_gm_narrative(world_state, "Iniciou a aventura", contexto_sem_gatilhos)
        cleaned_opening, updated_character = clean_and_process_ai_response(opening_scene, world_state)
        world_state['player_character'] = updated_character
        print(f"\n{cleaned_opening}\n")
        
        world_state = update_world_state(world_state, "Iniciou a aventura", opening_scene)
    
    game_context = load_game_context_for_act(current_act, world_state)
    new_game_loop(world_state, save_filepath, game_context)

if __name__ == "__main__":
    main()