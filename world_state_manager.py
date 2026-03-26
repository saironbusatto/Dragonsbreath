import json
import os
from openai import OpenAI
from campaign_manager import get_player_template, get_world_template

def update_world_state(old_state: dict, player_action: str, gm_response: str) -> dict:
    """
    Usa a IA Arquivista para atualizar o estado do mundo baseado nos eventos recentes.
    """
    # Atualização silenciosa do estado
    
    # SYSTEM: papel e instruções fixas do Arquivista
    archivista_system = """Você é o Arquivista — um sistema silencioso que mantém o estado de um RPG.
Sua única tarefa: receber um JSON de estado e eventos recentes, e retornar o JSON atualizado.
Retorne APENAS o JSON completo e válido. Nenhuma palavra, explicação ou markdown extra.

REGRAS DE ATUALIZAÇÃO:
1. Atualize 'immediate_scene_description' com a situação atual.
2. Atualize 'current_location_key' se o jogador mudou de local.
3. Adicione/remova NPCs em 'important_npcs_in_scene' conforme necessário.
4. Atualize 'active_quests' se missões foram iniciadas ou completadas.
5. Mantenha 'recent_events_summary' com os 3-4 eventos mais recentes.
6. Atualize inventário e status do personagem se necessário.
7. MAPA SEMÂNTICO DA CENA: Preencha 'interactable_elements_in_scene' dentro de 'world_state' como um dicionário com estas chaves exatas:
   - "objetos": lista de objetos standalone presentes (ex: ["vela", "balcão", "livro"])
   - "npcs": lista de personagens/criaturas presentes (ex: ["taverneiro", "figura encapuzada"])
   - "npc_itens": dicionário {nome_npc: [itens visíveis]} — SOMENTE se o Mestre mencionou explicitamente (ex: {"taverneiro": ["caneca", "chave"]})
   - "containers": dicionário {container: [conteúdo visível]} — SOMENTE se o Mestre mencionou conteúdo (ex: {"baú": ["moedas"]})
   - "saidas": lista de saídas e passagens (ex: ["porta norte", "escada", "beco lateral"])
   - "chao": itens abandonados ou caídos no chão (ex: ["moeda suja", "papel amassado"])
   REGRAS: Use [] para categorias sem elementos. Extraia APENAS o que foi explicitamente mencionado pelo Mestre neste turno. Ao mudar de local, limpe o mapa e recomece.
   NOMES: Use o termo mais curto e natural. Quando um elemento tiver variações óbvias, registre-as entre parênteses. Ex: "menino (garoto, criança)", "caixa (caixote)", "figura encapuzada (homem, vulto)".

    # USER: o estado atual + o que acabou de acontecer
    archivista_user = f"""JSON DO ESTADO ATUAL:
{json.dumps(old_state, indent=2, ensure_ascii=False)}

EVENTOS RECENTES:
- Ação do jogador: "{player_action}"
- Resposta do Mestre: "{gm_response}"

Retorne o JSON atualizado:"""

    try:
        response = get_openai_response_archivista(archivista_system, archivista_user)
        novo_estado = json.loads(response)
        return novo_estado if novo_estado else old_state
    except json.JSONDecodeError:
        # JSON inválido - mantém estado anterior
        return old_state

def get_openai_response_archivista(system_content: str, user_content: str) -> str:
    """Função específica para chamadas da IA Arquivista."""
    try:
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            return "{}"
        model_name = os.environ.get('OPENAI_MODEL_ARQUIVISTA') or os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user",   "content": user_content},
            ],
            temperature=0.2,
            max_tokens=2048,
        )
        return response.choices[0].message.content
    except Exception:
        return "{}"

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
            "max_slots": player_template.get("max_slots", 10),
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
            "interactable_elements_in_scene": {
                "objetos": [], "npcs": [], "npc_itens": {},
                "containers": {}, "saidas": [], "chao": []
            },
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