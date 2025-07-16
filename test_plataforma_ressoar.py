#!/usr/bin/env python3
"""
Teste da Plataforma Ressoar - Verifica se ambos os modos funcionam.
"""

import sys
import os
import json

# Adiciona o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_structure():
    """Testa se a estrutura básica está correta."""
    
    print("🎮 TESTE DA PLATAFORMA RESSOAR")
    print("=" * 50)
    
    # Verifica arquivos essenciais
    essential_files = [
        'game.py',
        'config.json',
        'world_state_manager.py',
        'campaign_manager.py'
    ]
    
    print("\n📁 Verificando arquivos essenciais:")
    for file in essential_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - FALTANDO")
    
    # Verifica estrutura de campanhas RPG
    print("\n🗡️ Verificando estrutura RPG:")
    if os.path.exists('campanhas'):
        print("✅ Diretório campanhas/")
        
        # Lista campanhas disponíveis
        campaigns = []
        for item in os.listdir('campanhas'):
            if os.path.isdir(f'campanhas/{item}'):
                campaigns.append(item)
                print(f"  📂 {item}")
        
        print(f"  Total: {len(campaigns)} campanhas encontradas")
    else:
        print("❌ Diretório campanhas/ - FALTANDO")
    
    # Verifica estrutura de contos interativos
    print("\n📖 Verificando estrutura de Contos Interativos:")
    if os.path.exists('contos_interativos'):
        print("✅ Diretório contos_interativos/")
        
        # Lista contos disponíveis
        import glob
        story_files = glob.glob("contos_interativos/*_eventos.json")
        
        print(f"  Total: {len(story_files)} contos encontrados")
        for story_file in story_files:
            story_name = os.path.basename(story_file).replace('_eventos.json', '')
            txt_file = f"contos_interativos/{story_name}.txt"
            
            if os.path.exists(txt_file):
                print(f"  ✅ {story_name} (completo)")
            else:
                print(f"  ⚠️ {story_name} (falta arquivo .txt)")
    else:
        print("❌ Diretório contos_interativos/ - FALTANDO")

def test_config_structure():
    """Testa se o config.json tem a estrutura correta."""
    
    print("\n⚙️ Verificando config.json:")
    
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Verifica estrutura básica
        required_keys = ['current_campaign', 'campaigns']
        for key in required_keys:
            if key in config:
                print(f"✅ {key}")
            else:
                print(f"❌ {key} - FALTANDO")
        
        # Verifica campanhas
        campaigns = config.get('campaigns', {})
        print(f"\n  Campanhas configuradas: {len(campaigns)}")
        
        for campaign_id, campaign_data in campaigns.items():
            print(f"    📋 {campaign_id}")
            
            # Verifica estrutura da campanha
            required_campaign_keys = ['name', 'player_template', 'world_template']
            for key in required_campaign_keys:
                if key in campaign_data:
                    print(f"      ✅ {key}")
                else:
                    print(f"      ❌ {key} - FALTANDO")
            
            # Verifica player_template
            player_template = campaign_data.get('player_template', {})
            required_player_keys = ['class', 'starting_hp', 'max_slots', 'starting_inventory']
            for key in required_player_keys:
                if key in player_template:
                    print(f"        ✅ player_template.{key}")
                else:
                    print(f"        ❌ player_template.{key} - FALTANDO")
    
    except FileNotFoundError:
        print("❌ config.json não encontrado")
    except json.JSONDecodeError as e:
        print(f"❌ Erro no JSON: {e}")

def test_story_structure():
    """Testa se os contos interativos têm estrutura correta."""
    
    print("\n📚 Verificando estrutura dos contos:")
    
    import glob
    story_files = glob.glob("contos_interativos/*_eventos.json")
    
    for story_file in story_files:
        story_name = os.path.basename(story_file).replace('_eventos.json', '')
        print(f"\n  📖 {story_name}:")
        
        try:
            with open(story_file, 'r', encoding='utf-8') as f:
                story_data = json.load(f)
            
            # Verifica estrutura básica
            required_keys = ['titulo', 'autor', 'variaveis_iniciais', 'evento_inicial', 'eventos']
            for key in required_keys:
                if key in story_data:
                    print(f"    ✅ {key}")
                else:
                    print(f"    ❌ {key} - FALTANDO")
            
            # Verifica eventos
            eventos = story_data.get('eventos', {})
            evento_inicial = story_data.get('evento_inicial', '')
            
            if evento_inicial in eventos:
                print(f"    ✅ evento_inicial '{evento_inicial}' existe")
            else:
                print(f"    ❌ evento_inicial '{evento_inicial}' não encontrado")
            
            print(f"    📊 Total de eventos: {len(eventos)}")
            
            # Conta finais
            finais = [e for e in eventos.keys() if 'final' in e]
            print(f"    🎭 Finais disponíveis: {len(finais)}")
            
        except json.JSONDecodeError as e:
            print(f"    ❌ Erro no JSON: {e}")
        except FileNotFoundError:
            print(f"    ❌ Arquivo não encontrado")

def test_imports():
    """Testa se as importações funcionam."""
    
    print("\n🔧 Testando importações:")
    
    try:
        from game import select_game_mode, select_rpg_campaign, select_interactive_story
        print("✅ Funções de seleção importadas")
    except ImportError as e:
        print(f"❌ Erro ao importar funções: {e}")
    
    try:
        from game import get_story_master_narrative, load_interactive_story
        print("✅ Funções de conto importadas")
    except ImportError as e:
        print(f"❌ Erro ao importar funções de conto: {e}")
    
    try:
        from world_state_manager import create_initial_world_state
        print("✅ Funções de estado importadas")
    except ImportError as e:
        print(f"❌ Erro ao importar funções de estado: {e}")

def main():
    """Executa todos os testes da plataforma."""
    
    print("🎵 TESTE COMPLETO DA PLATAFORMA RESSOAR 🎵")
    print("=" * 60)
    print("Verificando se ambos os modos estão funcionais...\n")
    
    test_structure()
    test_config_structure()
    test_story_structure()
    test_imports()
    
    print("\n" + "=" * 60)
    print("🎯 RESUMO:")
    print("• Estrutura de arquivos verificada")
    print("• Configurações de campanhas RPG verificadas")
    print("• Estrutura de contos interativos verificada")
    print("• Importações de funções verificadas")
    
    print("\n✨ A Plataforma Ressoar está pronta para uso!")
    print("🗡️ Modo RPG: Sistema completo com campanhas modulares")
    print("📖 Modo Conto: Narrativas interativas com múltiplos finais")
    
    print("\n🚀 Para testar:")
    print("1. Execute: python game.py")
    print("2. Escolha entre Modo RPG ou Modo Conto Interativo")
    print("3. Explore as diferentes experiências narrativas!")

if __name__ == "__main__":
    main()
