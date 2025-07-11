#!/usr/bin/env python3
"""
Gerenciador de Campanhas para RPG Modular
"""

from campaign_manager import list_available_campaigns, switch_campaign, get_current_campaign
import os

def show_current_campaign():
    """Mostra a campanha atual."""
    campaign = get_current_campaign()
    print(f"Campanha Atual: {campaign.get('name', 'Não definida')}")
    print(f"Descrição: {campaign.get('description', 'Sem descrição')}")

def list_campaigns():
    """Lista todas as campanhas disponíveis."""
    campaigns = list_available_campaigns()
    if not campaigns:
        print("Nenhuma campanha encontrada.")
        return
    
    print("\nCampanhas Disponíveis:")
    for i, campaign in enumerate(campaigns, 1):
        print(f"{i}. {campaign['name']}")
        print(f"   ID: {campaign['id']}")
        print(f"   Descrição: {campaign['description']}\n")

def change_campaign():
    """Permite trocar de campanha."""
    campaigns = list_available_campaigns()
    if not campaigns:
        print("Nenhuma campanha disponível.")
        return
    
    list_campaigns()
    
    try:
        choice = int(input("Escolha uma campanha (número): ")) - 1
        if 0 <= choice < len(campaigns):
            campaign_id = campaigns[choice]['id']
            if switch_campaign(campaign_id):
                print(f"Campanha alterada para: {campaigns[choice]['name']}")
                print("ATENÇÃO: Você precisará reiniciar o jogo para aplicar as mudanças.")
            else:
                print("Erro ao alterar campanha.")
        else:
            print("Opção inválida.")
    except ValueError:
        print("Por favor, digite um número válido.")

def create_campaign_template():
    """Cria um template para nova campanha."""
    campaign_id = input("ID da nova campanha (sem espaços): ").strip().lower()
    if not campaign_id:
        print("ID inválido.")
        return
    
    campaign_name = input("Nome da campanha: ").strip()
    if not campaign_name:
        print("Nome inválido.")
        return
    
    description = input("Descrição da campanha: ").strip()
    
    # Cria pasta
    campaign_path = f"campanhas/{campaign_id}"
    os.makedirs(campaign_path, exist_ok=True)
    
    # Cria arquivos básicos
    files = {
        'npcs.json': '{"npcs": {}}',
        'itens_magicos.json': '{"itens_magicos": {}}',
        'itens_comuns.json': '{"itens_comuns": {}}',
        'locais.json': '{"locais": {}}',
        'campanha.md': f'# {campaign_name}\n\n{description}\n\n## História\n\n[Escreva sua história aqui]\n'
    }
    
    for filename, content in files.items():
        filepath = os.path.join(campaign_path, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    
    print(f"Template da campanha '{campaign_name}' criado em: {campaign_path}")
    print("Edite os arquivos JSON e Markdown para personalizar sua campanha.")

def main():
    while True:
        print("\n" + "="*50)
        print("GERENCIADOR DE CAMPANHAS")
        print("="*50)
        
        show_current_campaign()
        
        print("\nOpções:")
        print("1. Listar campanhas")
        print("2. Trocar campanha")
        print("3. Criar nova campanha")
        print("4. Sair")
        
        choice = input("\nEscolha uma opção: ").strip()
        
        if choice == '1':
            list_campaigns()
        elif choice == '2':
            change_campaign()
        elif choice == '3':
            create_campaign_template()
        elif choice == '4':
            break
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    main()