#!/usr/bin/env python3
"""
get_session.py - Obtém token de sessão do GLPI e atualiza o arquivo .env

Este script solicita um token de sessão da API GLPI usando app_token e user_token
definidos no arquivo .env e atualiza automaticamente o arquivo com o novo token obtido.
"""

import os
import sys
import requests
from dotenv import load_dotenv, set_key, find_dotenv

def get_session_token(base_url, app_token, user_token):
    """
    Obtém um token de sessão da API GLPI.

    Parâmetros:
    -----------
    base_url : str
        URL base da instalação GLPI (sem barra final)
    app_token : str
        Token de aplicação GLPI
    user_token : str
        Token de usuário GLPI

    Retorna:
    --------
    str ou None
        Token de sessão se bem-sucedido, None caso contrário
    """
    # URL para inicializar a sessão
    url = f"{base_url}/apirest.php/initSession/"

    # Cabeçalho da requisição
    headers = {
        "App-Token": app_token,
        "Authorization": f"user_token {user_token}"
    }

    try:
        # Realiza a requisição GET para obter o token de sessão
        print(f"Solicitando token de sessão de: {url}")
        response = requests.get(url, headers=headers)

        # Verifica o status da resposta
        if response.status_code == 200:
            session_token = response.json().get("session_token")
            print(f"Token de sessão obtido com sucesso!")
            return session_token
        else:
            print(f"Erro ao obter token de sessão. Código: {response.status_code}")
            print(f"Resposta: {response.text}")
            return None
    except Exception as e:
        print(f"Exceção ao obter token de sessão: {str(e)}")
        return None

def update_env_file(session_token):
    """
    Atualiza o arquivo .env com o novo token de sessão.'

    Parâmetros:
    -----------
    session_token : str
        Token de sessão a ser armazenado no arquivo .env
    
    Retorna:
    --------
    bool
        True se atualizado com sucesso, False caso contrário
    """
    try:
        # Localiza o arquivo .env
        dotenv_path = find_dotenv()
        if not dotenv_path:
            # Se não encontrar, cria na raiz do projeto
            dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
            if not os.path.exists(dotenv_path):
                with open(dotenv_path, 'w') as f:
                    f.write("# Arquivo .env gerado automaticamente\n")
        
        # Atualiza a variável no arquivo .env
        set_key(dotenv_path, "GLPI_SESSION_TOKEN", session_token)
        print(f"Arquivo .env atualizado com o novo token de sessão em: {dotenv_path}")
        return True
    except Exception as e:
        print(f"Erro ao atualizar arquivo .env: {str(e)}")
        return False

if __name__ == "__main__":
    # Carregar variáveis de ambiente existentes
    load_dotenv()
    
    # Obter valores diretamente do arquivo .env
    base_url = os.getenv("GLPI_BASE_URL")
    app_token = os.getenv("GLPI_APP_TOKEN")
    user_token = os.getenv("GLPI_USER_TOKEN")
    
    # Verificar se todos os parâmetros necessários estão disponíveis
    missing = []
    if not base_url: missing.append("GLPI_BASE_URL")
    if not app_token: missing.append("GLPI_APP_TOKEN")
    if not user_token: missing.append("GLPI_USER_TOKEN")
    
    if missing:
        print(f"Erro: Variáveis de ambiente obrigatórias ausentes: {', '.join(missing)}")
        print("Adicione essas variáveis ao arquivo .env antes de executar este script.")
        sys.exit(1)
    
    print(f"Usando configurações do arquivo .env:")
    print(f"  URL base: {base_url}")
    print(f"  Tokens: Configurados\n")
    
    # Obter o token de sessão
    session_token = get_session_token(base_url, app_token, user_token)
    
    if session_token:
        # Atualizar o arquivo .env
        if update_env_file(session_token):
            print("Token de sessão atualizado com sucesso no arquivo .env.")
        else:
            print("Falha ao atualizar o arquivo .env, mas o token foi obtido.")

    else:
        print("Não foi possível obter o token de sessão. Verifique as variáveis no arquivo .env e tente novamente.")
        sys.exit(1)