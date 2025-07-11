#!/usr/bin/env python3
"""
Script de inicialização para O Lamento do Bardo
Verifica dependências e inicia o jogo
"""

import os
import sys

def verificar_dependencias():
    """Verifica se as dependências estão instaladas."""
    try:
        import google.generativeai as genai
        print("[OK] Google Generative AI instalado")
    except ImportError:
        print("[ERRO] Google Generative AI nao encontrado")
        print("   Execute: pip install google-generativeai")
        return False
    
    return True

def verificar_api_key():
    """Verifica se a API key está configurada."""
    if 'GEMINI_API_KEY' not in os.environ:
        print("[ERRO] GEMINI_API_KEY nao configurada")
        print("   Configure com: set GEMINI_API_KEY=sua_chave_aqui")
        return False
    
    print("[OK] GEMINI_API_KEY configurada")
    return True

def verificar_arquivos():
    """Verifica se os arquivos necessários existem."""
    arquivos_necessarios = [
        'npcs.json',
        'itens_magicos.json', 
        'itens_comuns.json',
        'locais.json',
        'world_state_manager.py'
    ]
    
    todos_ok = True
    for arquivo in arquivos_necessarios:
        if os.path.exists(arquivo):
            print(f"[OK] {arquivo}")
        else:
            print(f"[ERRO] {arquivo} nao encontrado")
            todos_ok = False
    
    return todos_ok

def main():
    print("=== Verificando O Lamento do Bardo ===\n")
    
    print("--- Verificando Dependências ---")
    deps_ok = verificar_dependencias()
    
    print("\n--- Verificando API Key ---")
    api_ok = verificar_api_key()
    
    print("\n--- Verificando Arquivos ---")
    files_ok = verificar_arquivos()
    
    print("\n" + "="*40)
    
    if deps_ok and api_ok and files_ok:
        print("[OK] Tudo pronto! Iniciando o jogo...")
        print("="*40 + "\n")
        
        # Importa e executa o jogo
        try:
            import game
            game.main()
        except KeyboardInterrupt:
            print("\n\n=== Ate a proxima aventura! ===")
        except Exception as e:
            print(f"\n[ERRO] Erro ao executar o jogo: {e}")
    else:
        print("[ERRO] Corrija os problemas acima antes de jogar.")
        input("\nPressione Enter para sair...")

if __name__ == "__main__":
    main()