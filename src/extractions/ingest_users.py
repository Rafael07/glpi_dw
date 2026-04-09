import os
import requests
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# ==========================================
# 1. CONFIGURAÇÕES
# ==========================================
load_dotenv()

DB_URL = "postgresql://admin:admin123@localhost:5432/dw_glpi"
# Ajuste do endpoint para buscar os Usuários
API_URL = f"{os.getenv('GLPI_BASE_URL')}/apirest.php/User"

HEADERS = {
    "App-Token": os.getenv('GLPI_APP_TOKEN'),
    "Session-Token": os.getenv('GLPI_SESSION_TOKEN')
}

# ==========================================
# 2. EXTRAÇÃO DE DADOS (API GLPI)
# ==========================================
def get_glpi_users():
    print(f"Buscando lista de usuários em {API_URL}...")
    
    # O range=0-9999 garante que vamos puxar até 10 mil usuários em uma única chamada
    params = {
        "range": "0-9999"
    }
    
    users_res = requests.get(API_URL, headers=HEADERS, params=params)
    
    if users_res.status_code != 200:
        raise Exception(f"Erro ao buscar usuários. Status: {users_res.status_code} - {users_res.text}")
        
    return users_res.json()

# ==========================================
# 3. TRANSFORMAÇÃO BÁSICA (Nome Completo)
# ==========================================
def process_users(users_data):
    lista_usuarios = []
    
    for u in users_data:
        # Pega primeiro e último nome e remove espaços vazios
        nome = str(u.get('firstname', '')).strip()
        sobrenome = str(u.get('realname', '')).strip()
        
        # Limpa strings "None" do Python caso venham nulas
        nome = "" if nome == "None" else nome
        sobrenome = "" if sobrenome == "None" else sobrenome
        
        nome_completo = f"{nome} {sobrenome}".strip()
        
        # Se ficou vazio, usa o login ('name' no GLPI)
        if not nome_completo:
            nome_completo = str(u.get('name', 'Desconhecido')).strip()
            
        lista_usuarios.append({
            'id': u.get('id'),
            'login': u.get('name'),
            'nome_completo': nome_completo,
            'is_active': u.get('is_active', 1),
            'is_deleted': u.get('is_deleted', 0)
        })
        
    return pd.DataFrame(lista_usuarios)

# ==========================================
# 4. CARGA NO DATA WAREHOUSE (STAGING)
# ==========================================
def load_to_staging(df):
    print(f"Carregando {len(df)} usuários para a tabela 'staging_users'...")
    engine = create_engine(DB_URL)
    
    # Salva no PostgreSQL
    df.to_sql('staging_users', engine, if_exists='replace', index=False)
    print("🚀 Carga de usuários concluída com sucesso!")

# ==========================================
# EXECUÇÃO DO SCRIPT
# ==========================================
if __name__ == "__main__":
    raw_data = get_glpi_users()
    df_users = process_users(raw_data)
    load_to_staging(df_users)