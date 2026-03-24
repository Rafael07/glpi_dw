import requests
import json
from loguru import logger
from dotenv import load_dotenv
import os

# 1. Configuração do Loguru (Simples e Poderoso)
logger.add("logs/discovery.log", rotation="1 MB", level="INFO")

def discovery_glpi():
    load_dotenv()
    
    url = f"{os.getenv('GLPI_BASE_URL')}/apirest.php/search/Ticket"
    headers = {
        "App-Token": os.getenv('GLPI_APP_TOKEN'),
        "Session-Token": os.getenv('GLPI_SESSION_TOKEN'),
        "Content-Type": "application/json"
    }
    
    # Vamos pegar apenas 1 ticket para não inundar o terminal
    params = {
        "range": "0-0",
        "expand_dropdowns": "true",
        "get_full_count": "true"
    }

    logger.info(f"Iniciando descoberta na URL: {url}")

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        raw_data = response.json()
        
        # O GLPI Search costuma retornar uma lista dentro da chave 'data'
        if "data" in raw_data and len(raw_data["data"]) > 0:
            sample_ticket = raw_data["data"][0]
            
            logger.success("Ticket recuperado com sucesso!")
            print("\n--- ESTRUTURA DO TICKET (RAW) ---")
            print(json.dumps(sample_ticket, indent=4, ensure_ascii=False))
            print("---------------------------------\n")
            
            logger.info("Verifique acima qual ID corresponde à 'Categoria' (ex: campo '7').")
        else:
            logger.warning("Conexão ok, mas nenhum ticket foi retornado. O banco está vazio?")

    except Exception as e:
        logger.error(f"Falha na descoberta: {e}")

if __name__ == "__main__":
    discovery_glpi()