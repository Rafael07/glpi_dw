import os
import requests
from loguru import logger
from sqlalchemy import create_engine
import pandas as pd
from dotenv import load_dotenv
from schemas import TicketSchema # Importa o contrato que criamos

def run_ingestion():
    load_dotenv()
    
    # 1. Configurações
    DB_URL = f"postgresql://admin:admin123@localhost:5432/dw_glpi"
    API_URL = f"{os.getenv('GLPI_BASE_URL')}/apirest.php/search/Ticket"
    HEADERS = {
        "App-Token": os.getenv('GLPI_APP_TOKEN'),
        "Session-Token": os.getenv('GLPI_SESSION_TOKEN')
    }
    
    # 2. Busca os dados (Aumentamos o range para o primeiro gráfico)
    params = {"range": "0-100", "expand_dropdowns": "true"}
    
    try:
        logger.info("Buscando dados no GLPI...")
        response = requests.get(API_URL, headers=HEADERS, params=params)
        response.raise_for_status()
        tickets_raw = response.json().get("data", [])

        # 3. Validação com Pydantic (O Inspetor de Qualidade)
        valid_tickets = []
        for item in tickets_raw:
            try:
                ticket = TicketSchema(**item)
                valid_tickets.append(ticket.dict())
            except Exception as e:
                logger.warning(f"Ticket {item.get('2')} ignorado por erro de formato: {e}")

        # 4. Carga no Banco (Usando Pandas para facilitar o 'to_sql')
        if valid_tickets:
            df = pd.DataFrame(valid_tickets)
            engine = create_engine(DB_URL)
            
            # Criamos uma tabela na camada 'staging'
            df.to_sql("staging_tickets", engine, if_exists="replace", index=False)
            logger.success(f"Ingestão concluída! {len(df)} tickets salvos em staging_tickets.")
        
    except Exception as e:
        logger.error(f"Erro na ingestão: {e}")

if __name__ == "__main__":
    run_ingestion()