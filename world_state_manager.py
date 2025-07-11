import json
import google.generativeai as genai
import os
from campaign_manager import get_player_template, get_world_template

def update_world_state(old_state: dict, player_action: str, gm_response: str) -> dict:
    """
    Usa a IA Arquivista para atualizar o estado do mundo baseado nos eventos recentes.
    """
    # Atualização silenciosa do estado
    
    prompt_archivista = f"""Você é um assistente de sistema para um RPG. Sua única tarefa é atualizar um JSON de estado do jogo com base nos eventos recentes.

Analise o JSON do estado antigo, a ação do jogador e a resposta do Mestre do Jogo.
Retorne APENAS o JSON completo e atualizado, sem nenhuma palavra ou explicação extra.

JSON DO ESTADO ANTIGO:
{json.dumps(old_state, indent=4, ensure_ascii=False)}

EVENTOS RECENTES:
- O Jogador fez: "{player_action}"
  (Se houver, evento ambiental: pode considerar isso como um gatilho ou detalhe do ambiente que foi ativado.)
- O Mestre respondeu: "{gm_response}"

INSTRUÇÕES DE ATUALIZAÇÃO:
1. Atualize 'immediate_scene_description' com a situação atual
2. Atualize 'current_location_key' se o jogador mudou de local
3. Adicione/remova NPCs em 'important_npcs_in_scene' conforme necessário
4. Atualize 'active_quests' se missões foram iniciadas/completadas
5. Mantenha 'recent_events_summary' com os 3-4 eventos mais recentes
6. Atualize inventário e status do personagem se necessário

Agora, forneça o novo JSON atualizado:"""
    
    try:
        response = get_gemini_response_archivista(prompt_archivista)
        novo_estado = json.loads(response)
        return novo_estado
    except json.JSONDecodeError:
        # JSON inválido - mantém estado anterior
        return old_state

def get_gemini_response_archivista(prompt: str) -> str:
    """Função específica para chamadas da IA Arquivista."""
    try:
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            return "{}"
        genai.configure(api_key=api_key)
    except Exception as e:
        return "{}"
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    return response.text

def create_initial_world_state(character_name: str) -> dict:
    """Cria o estado inicial do mundo para um novo jogo."""
    player_template = get_player_template()
    world_template = get_world_template()
    
    return {
        "player_character": {
            "name": character_name,
            "class": player_template.get("class", "Aventureiro"),
            "current_act": 1,
            "status": {
                "hp": player_template.get("starting_hp", 20),
                "max_hp": player_template.get("starting_hp", 20)
            },
            "inventory": player_template.get("starting_inventory", []),
            "desejo": world_template.get("initial_quest", "Explorar o mundo")
        },
        "world_state": {
            "current_location_key": world_template.get("initial_location", "local_inicial"),
            "immediate_scene_description": world_template.get("initial_description", "Você inicia uma nova aventura."),
            "active_quests": {
                "main_quest": world_template.get("initial_quest", "Explorar o mundo")
            },
            "important_npcs_in_scene": {},
            "recent_events_summary": [
                f"{character_name} iniciou sua jornada"
            ],
            "gatilhos_ativos": world_template.get("initial_triggers", {}),
            "gatilhos_usados": {loc: [] for loc in world_template.get("initial_triggers", {}).keys()}
        }
    }

def load_world_state(filepath: str) -> dict:
    """Carrega o estado do mundo do arquivo JSON."""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, KeyError):
        # Arquivo corrompido - retorna None
        return None

def save_world_state(state: dict, filepath: str):
    """Salva o estado do mundo no arquivo JSON."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4, ensure_ascii=False)