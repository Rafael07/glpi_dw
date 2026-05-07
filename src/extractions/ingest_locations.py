import os
import sys
import requests
import pandas as pd
from loguru import logger
from dotenv import load_dotenv
from sqlalchemy import create_engine

# ==========================================
# 1. CONFIGURAÇÃO DE OBSERVABILIDADE E AMBIENTE
# ==========================================
# Adiciona o loguru para escrever no arquivo unificado do projeto
logger.add(
    "logs/ingestion.log", 
    rotation="10 MB", 
    retention="7 days", 
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
)

load_dotenv()

GLPI_URL = os.getenv("GLPI_BASE_URL")
APP_TOKEN = os.getenv("GLPI_APP_TOKEN")
SESSION_TOKEN = os.getenv("GLPI_SESSION_TOKEN") # O ideal é importar do seu get_session.py
DB_URL = f"postgresql://{os.getenv('DW_USER', 'admin')}:{os.getenv('DW_PASSWORD', 'admin123')}@{os.getenv('DW_HOST', 'localhost')}:{os.getenv('DW_PORT', '5432')}/{os.getenv('DW_DATABASE', 'dw_glpi')}"

# ==========================================
# 2. FUNÇÃO DE EXTRAÇÃO DA API
# ==========================================
def fetch_locations() -> list:
    """Busca todas as localizações na API do GLPI."""
    if not all([GLPI_URL, APP_TOKEN, SESSION_TOKEN]):
        logger.error("Credenciais do GLPI não encontradas nas variáveis de ambiente.")
        sys.exit(1)

    url = f"{GLPI_URL.rstrip('/')}/apirest.php/Location/"
    headers = {
        "App-Token": APP_TOKEN,
        "Session-Token": SESSION_TOKEN,
        "Content-Type": "application/json"
    }
    
    # Range amplo para trazer todas de uma vez (geralmente localizações não passam de 1000)
    params = {
        "range": "0-999",
        "expand_dropdowns": "true"
    }

    try:
        logger.info(f"Fazendo requisição para extrair Localizações de: {url}")
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        locations = response.json()
        
        if isinstance(locations, list):
            logger.info(f"Extração concluída: {len(locations)} localizações encontradas.")
            return locations
        else:
            logger.warning(f"Resposta inesperada da API (não é uma lista). Tipo: {type(locations)}")
            return []
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao buscar localizações na API: {str(e)}")
        sys.exit(1)

# ==========================================
# 3. FUNÇÃO DE CARGA NO BANCO DE DADOS
# ==========================================
def load_to_database(locations_data: list):
    """Carrega a lista de dicionários no PostgreSQL usando Pandas."""
    if not locations_data:
        logger.warning("Nenhum dado de localização para carregar no banco.")
        return

    try:
        logger.info("Convertendo dados para DataFrame Pandas...")
        df_locations = pd.DataFrame(locations_data)

        # Remove colunas com tipos não serializáveis (listas/dicts) e caches internos do GLPI
        cols_drop = [c for c in ['links', 'sons_cache', 'ancestors_cache'] if c in df_locations.columns]
        df_locations.drop(columns=cols_drop, inplace=True)
        
        logger.info("Conectando ao banco de dados PostgreSQL...")
        engine = create_engine(DB_URL)
        
        # Carregando na Staging
        df_locations.to_sql('staging_locations', engine, if_exists='replace', index=False)
        logger.success(f"Tabela 'staging_locations' atualizada com sucesso no banco de dados!")
        
    except Exception as e:
        logger.error(f"Erro ao gravar dados no PostgreSQL: {str(e)}")
        sys.exit(1)

# ==========================================
# 4. EXECUÇÃO PRINCIPAL
# ==========================================
if __name__ == "__main__":
    logger.info("--- INICIANDO PIPELINE DE INGESTÃO DE LOCALIZAÇÕES ---")
    
    dados_brutos = fetch_locations()
    load_to_database(dados_brutos)
    
    logger.info("--- PIPELINE DE INGESTÃO DE LOCALIZAÇÕES FINALIZADO ---")