import google.generativeai as genai
import json
import os
import re
import random
from dotenv import load_dotenv
from world_state_manager import update_world_state, create_initial_world_state, load_world_state, save_world_state
from campaign_manager import get_campaign_files, load_campaign_data, get_current_campaign
import audio_manager

load_dotenv()

MAX_INVENTORY_SLOTS = 5
QUEST_ITEM_KEYWORDS = ['moeda', 'chave', 'nota', 'mapa', 'pergaminho', 'cristal', 'símbolo', 'anel', 'diapasão']

def get_gm_narrative(world_state: dict, player_action: str, game_context: dict) -> str:
    try:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("ERRO: GEMINI_API_KEY não encontrada")
            return "O Mestre do Jogo não consegue se conectar aos planos astrais. O que você faz?"
        genai.configure(api_key=api_key)
    except Exception as e:
        print(f"ERRO na configuração da API: {e}")
        return "O Mestre do Jogo não consegue se conectar aos planos astrais. O que você faz?"

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
6. NUNCA ofereça opções múltiplas escolha. O jogador pode fazer QUALQUER coisa.
7. Considere o desejo ou objetivo do personagem ao narrar eventos.
8. Nunca se repita — traga algo novo ou surpreendente a cada ação.
9. Descreva a cena e termine SEM perguntar "O que você faz?"

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

def speak_inventory(character: dict):
    inventory = character.get('inventory', [])
    if not inventory:
        audio_manager.text_to_speech("Seu inventário está vazio.")
    else:
        items_text = "Seus itens são: " + ", ".join(inventory)
        audio_manager.text_to_speech(items_text)

def speak_status(character: dict):
    status = character.get('status', {'hp': 20, 'max_hp': 20})
    hp = status.get('hp', 20)
    max_hp = status.get('max_hp', 20)
    status_text = f"Sua saúde atual é {hp} de {max_hp} pontos de vida."
    audio_manager.text_to_speech(status_text)

def handle_local_command(player_action: str, character: dict) -> bool:
    action_lower = player_action.lower()

    if any(keyword in action_lower for keyword in ['inventário', 'inventario', 'bolsa', 'itens']):
        speak_inventory(character)
        return True

    if any(keyword in action_lower for keyword in ['status', 'saúde', 'vida', 'hp']):
        speak_status(character)
        return True

    return False

# Define command constants
EXIT_COMMAND = 'chikito'


def handle_narrative_triggers(world_state):
    # Extracted logic for choosing and activating a narrative trigger
    # Placeholder for actual implementation
    pass





def new_game_loop(world_state: dict, save_filepath: str, game_context: dict):
    # Garante que existe o campo rodadas_sem_gatilho
    if "rodadas_sem_gatilho" not in world_state:
        world_state["rodadas_sem_gatilho"] = 0

    while True:
        # Som de chime já indica que está ouvindo
        player_action = audio_manager.speech_to_text()
        if not player_action:
            continue
        action_lower = player_action.lower()

        if action_lower == 'chikito':
            save_world_state(world_state, save_filepath)
            audio_manager.text_to_speech("Jogo salvo. Obrigado por jogar!")
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
        
        # Verifica se o jogador quer tocar música
        if any(word in player_action.lower() for word in ['tocar', 'toco', 'alaúde', 'música', 'cantar', 'canto']):
            audio_manager.play_sfx(f"familiar{random.randint(1,3)}")
        
        # Adiciona efeitos sonoros baseados no contexto
        if any(word in cleaned_response.lower() for word in ['taverna', 'bar', 'bebida']):
            audio_manager.play_sfx("tavern")
        elif any(word in cleaned_response.lower() for word in ['corvo', 'corvos', 'pássaro']):
            audio_manager.play_sfx("crow")
        elif any(word in cleaned_response.lower() for word in ['moeda', 'ouro', 'dinheiro']):
            audio_manager.play_sfx("coin")
        elif any(word in cleaned_response.lower() for word in ['fome', 'comé', 'comer']):
            audio_manager.play_sfx("fome")
        elif any(word in cleaned_response.lower() for word in ['familiar', 'conhecido', 'reconhece']):
            audio_manager.play_sfx(f"familiar{random.randint(1,3)}")
        elif any(word in cleaned_response.lower() for word in ['criança', 'correndo', 'passos']):
            audio_manager.play_sfx("crianca")
        elif any(word in cleaned_response.lower() for word in ['grito', 'grita', 'berro', 'terror']):
            audio_manager.play_sfx("scream")
        
        audio_manager.text_to_speech(cleaned_response)
        
        # Toca chime após a narração para indicar que pode falar
        audio_manager.play_chime()

        # Atualização simples do estado (sem IA Arquivista para economizar quota)
        world_state['world_state']['recent_events_summary'] = [
            f"Jogador: {player_action}",
            f"Mestre: {cleaned_response[:100]}..."
        ][-3:]  # Mantém apenas os 3 últimos eventos
        
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

def tutorial_introduction():
    """Introdução narrada com tutorial do jogo"""
    # Introdução universal do Ressoar
    audio_manager.play_sfx("logo")  # Som de abertura
    
    ressoar_intro = """Existe um som que só você pode emitir.

Um timbre único, uma frequência que é só sua.

Bem-vindo a Ressoar.

Este não é um lugar para seguir caminhos, mas para criar ecos.

Cada passo seu deixará uma marca. Cada feito seu será lembrado.

O mundo é todo ouvidos. O que ele vai escutar de você?"""
    
    audio_manager.text_to_speech(ressoar_intro)
    
    # Pega informações da campanha atual
    campaign = get_current_campaign()
    campaign_name = campaign.get('name', 'Aventura Desconhecida')
    campaign_desc = campaign.get('description', '')
    
    # Introdução específica da campanha
    campaign_intro = f"""Você tem a história de: {campaign_name}.

{campaign_desc}

Nas brumas sombrias de Umbraton, uma cidade gótica assolada por uma praga misteriosa, você desperta como um bardo em busca da verdade. Sua esposa morreu em circunstâncias estranhas, e sussurros falam de um dragão disfarçado entre os mortais.

Este é um RPG totalmente por voz. Eu, o Mestre, narrarei tudo e você responderá falando suas ações.

Sempre que ouvir um som de sino, significa que o jogo está pronto para ouvir sua ação.

Comandos úteis: diga 'inventário' para seus itens, 'status' para sua saúde, e 'chikito' para salvar e sair.

Agora, me diga seu nome, corajoso bardo."""
    
    audio_manager.text_to_speech(campaign_intro)
    
    # Pede o nome usando reconhecimento de voz
    player_name = audio_manager.speech_to_text()
    while not player_name or len(player_name.strip()) < 2:
        audio_manager.text_to_speech("Não consegui ouvir seu nome claramente. Pode repetir?")
        player_name = audio_manager.speech_to_text()
    
    return player_name.strip()

def main():
    save_filepath = 'estado_do_mundo.json'
    
    world_state = load_world_state(save_filepath)
    
    if world_state:
        # Descreve a situação atual ao continuar
        current_scene = world_state.get('world_state', {}).get('immediate_scene_description', 'Você continua sua jornada...')
        continue_text = f"Continuando sua jornada... {current_scene}"
        audio_manager.text_to_speech(continue_text)
        
        # Toca chime para indicar que pode falar
        audio_manager.play_chime()
        
        current_act = world_state.get('player_character', {}).get('current_act', 1)
    else:
        player_name = tutorial_introduction()
        
        world_state = create_initial_world_state(player_name)
        current_act = 1
        
        # Cena de abertura personalizada baseada na campanha
        campaign = get_current_campaign()
        initial_desc = campaign.get('world_template', {}).get('initial_description', 'Sua aventura começa...')
        
        # Toca ambientação de chuva e corvos
        audio_manager.play_sfx("rain")
        audio_manager.play_sfx("crow")
        
        opening_text = f"Muito bem, {player_name}. {initial_desc} As ruas cobertas de névoa ecoam com lamentos distantes, e você sente o peso do seu alaúde nas costas. A taverna 'O Corvo Solitário' brilha fracamente à sua frente, prometendo respostas... ou mais mistérios. O que você faz?"
        
        audio_manager.text_to_speech(opening_text)
        
        # Atualiza estado inicial
        world_state['world_state']['immediate_scene_description'] = opening_text
        
        # Salva o estado inicial
        save_world_state(world_state, save_filepath)
    
    game_context = load_game_context_for_act(current_act, world_state)
    new_game_loop(world_state, save_filepath, game_context)

if __name__ == "__main__":
    main()