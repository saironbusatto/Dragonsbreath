import os
print("=== TESTE DE DEBUG ===")

# Teste 1: API Key
api_key = os.environ.get('GEMINI_API_KEY')
print(f"API Key configurada: {'Sim' if api_key else 'Não'}")

# Teste 2: Importações
try:
    import campaign_manager
    print("campaign_manager: OK")
except Exception as e:
    print(f"campaign_manager: ERRO - {e}")

try:
    import world_state_manager
    print("world_state_manager: OK")
except Exception as e:
    print(f"world_state_manager: ERRO - {e}")

# Teste 3: Config
try:
    from campaign_manager import load_config
    config = load_config()
    print(f"Config carregado: {config.get('current_campaign', 'ERRO')}")
except Exception as e:
    print(f"Config: ERRO - {e}")

# Teste 4: Game
try:
    import game
    print("game.py: OK")
except Exception as e:
    print(f"game.py: ERRO - {e}")

print("=== FIM DO TESTE ===")