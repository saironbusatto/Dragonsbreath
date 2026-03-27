import importlib.util
import json
import os

FEATURED_CAMPAIGN_ID = "curse_of_strahd"

def load_config() -> dict:
    """Carrega a configuração das campanhas."""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"current_campaign": "lamento_do_bardo", "campaigns": {}}

def get_current_campaign() -> dict:
    """Retorna os dados da campanha atual."""
    config = load_config()
    current_name = config.get('current_campaign', 'lamento_do_bardo')
    return config.get('campaigns', {}).get(current_name, {})

def load_campaign_data(filepath: str) -> dict:
    """Carrega dados de um arquivo da campanha."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def load_campaign_text(filepath: str) -> str:
    """Carrega texto de um arquivo da campanha."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return ""

def get_campaign_files() -> dict:
    """Retorna os caminhos dos arquivos da campanha atual."""
    campaign = get_current_campaign()
    return campaign.get('files', {})

def get_player_template() -> dict:
    """Retorna o template do jogador para a campanha atual."""
    campaign = get_current_campaign()
    return campaign.get('player_template', {
        "class": "Aventureiro",
        "starting_hp": 20,
        "starting_inventory": []
    })

def get_class_template(class_name: str) -> dict | None:
    """Retorna o template de uma classe específica da campanha atual, ou None se não existir."""
    campaign = get_current_campaign()
    class_templates = campaign.get('class_templates', {})
    return class_templates.get(class_name)

def get_world_template() -> dict:
    """Retorna o template do mundo para a campanha atual."""
    campaign = get_current_campaign()
    return campaign.get('world_template', {
        "initial_description": "Você inicia uma nova aventura.",
        "initial_quest": "Explorar o mundo"
    })

def list_available_campaigns() -> list:
    """Lista todas as campanhas disponíveis."""
    config = load_config()
    campaigns = []
    for key, campaign in config.get('campaigns', {}).items():
        # Extrai dados completos das classes (incluindo descrições para a tela de seleção)
        class_templates = campaign.get('class_templates', {})
        if class_templates:
            classes = list(class_templates.keys())
            class_details = [
                {
                    'id': cls_name,
                    'tagline': tpl.get('tagline', ''),
                    'icon': tpl.get('icon', '⚔️'),
                    'voice_intro': tpl.get('voice_intro', cls_name),
                    'description': tpl.get('description', ''),
                    'hp': tpl.get('starting_hp', 20),
                    'slots': tpl.get('slots_iniciais', tpl.get('max_slots', 10)),
                    'max_slots': tpl.get('max_slots', 10),
                }
                for cls_name, tpl in class_templates.items()
            ]
        else:
            default_class = campaign.get('player_template', {}).get('class', 'Aventureiro')
            classes = [default_class]
            class_details = []
        campaigns.append({
            'id': key,
            'name': campaign.get('name', key),
            'description': campaign.get('description', 'Sem descrição'),
            'classes': classes,
            'class_details': class_details,
        })
    campaigns.sort(
        key=lambda c: (
            0 if c.get("id") == FEATURED_CAMPAIGN_ID else 1,
            (c.get("name") or "").lower(),
        )
    )
    return campaigns

def load_campaign_handler(handler_name: str):
    """
    Carrega dinamicamente um módulo de evento da campanha atual.
    Ex.: handler_name="tarokka" → carrega campanhas/curse_of_strahd/tarokka.py
    Retorna o módulo Python ou None se não existir.
    """
    files = get_campaign_files()
    base_path = files.get("npcs", "")
    if not base_path:
        return None
    campaign_dir = os.path.dirname(base_path)
    module_path = os.path.join(campaign_dir, f"{handler_name}.py")
    if not os.path.exists(module_path):
        return None
    try:
        spec = importlib.util.spec_from_file_location(handler_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None


def get_campaign_inspection_patterns() -> dict:
    """
    Retorna padrões de inspeção do HUD registrados pela campanha atual.
    Cada módulo de handler pode expor INSPECTION_KEYWORDS: dict[str, list[str]].
    Agrega todos os handlers ativos encontrados na pasta da campanha.
    """
    files = get_campaign_files()
    base_path = files.get("npcs", "")
    if not base_path:
        return {}
    campaign_dir = os.path.dirname(base_path)
    patterns: dict = {}
    try:
        for fname in os.listdir(campaign_dir):
            if not fname.endswith(".py"):
                continue
            handler_name = fname[:-3]
            mod = load_campaign_handler(handler_name)
            if mod and hasattr(mod, "INSPECTION_KEYWORDS"):
                patterns.update(mod.INSPECTION_KEYWORDS)
    except Exception:
        pass
    return patterns


def call_campaign_post_narrative(world_state: dict, gm_narrative: str) -> dict:
    """
    Chama post_narrative_hook em todos os handlers da campanha que o implementem.
    Chamado após cada resposta do GM, antes do update_world_state.
    """
    files = get_campaign_files()
    base_path = files.get("npcs", "")
    if not base_path:
        return world_state
    campaign_dir = os.path.dirname(base_path)
    try:
        for fname in os.listdir(campaign_dir):
            if not fname.endswith(".py"):
                continue
            mod = load_campaign_handler(fname[:-3])
            if mod and hasattr(mod, "post_narrative_hook"):
                world_state = mod.post_narrative_hook(world_state, gm_narrative)
    except Exception:
        pass
    return world_state


def call_campaign_on_travel(world_state: dict, old_loc: str, new_loc: str) -> dict:
    """
    Chama on_travel em todos os handlers da campanha que o implementem.
    Chamado quando current_location_key muda após update_world_state.
    """
    files = get_campaign_files()
    base_path = files.get("npcs", "")
    if not base_path:
        return world_state
    campaign_dir = os.path.dirname(base_path)
    try:
        for fname in os.listdir(campaign_dir):
            if not fname.endswith(".py"):
                continue
            mod = load_campaign_handler(fname[:-3])
            if mod and hasattr(mod, "on_travel"):
                world_state = mod.on_travel(world_state, old_loc, new_loc)
    except Exception:
        pass
    return world_state


def switch_campaign(campaign_id: str) -> bool:
    """Troca para uma campanha específica."""
    config = load_config()
    if campaign_id in config.get('campaigns', {}):
        config['current_campaign'] = campaign_id
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    return False
