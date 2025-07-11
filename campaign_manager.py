import json
import os

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
        campaigns.append({
            'id': key,
            'name': campaign.get('name', key),
            'description': campaign.get('description', 'Sem descrição')
        })
    return campaigns

def switch_campaign(campaign_id: str) -> bool:
    """Troca para uma campanha específica."""
    config = load_config()
    if campaign_id in config.get('campaigns', {}):
        config['current_campaign'] = campaign_id
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    return False