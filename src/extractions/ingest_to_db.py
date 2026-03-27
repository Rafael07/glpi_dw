import os
import sys
from pathlib import Path
import requests
from loguru import logger
from sqlalchemy import create_engine
import pandas as pd
from dotenv import load_dotenv
from typing import List, Dict, Any, Callable

# Importa o contrato Pydantic
from schemas import TicketSchema

# ==========================================
# 0. CONFIGURAÇÃO DE LOGS NA RAIZ
# ==========================================
# Resolve o caminho: script -> extractions -> src -> raiz_do_projeto
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = ROOT_DIR / "logs"

# Garante que a pasta 'logs' exista na raiz antes de tentar salvar o arquivo
LOG_DIR.mkdir(exist_ok=True) 
LOG_FILE = LOG_DIR / "ingestion.log"

# Remove o comportamento padrão do Loguru e reconfigura
logger.remove()
logger.add(sys.stdout, level="INFO") # Mantém o print colorido no terminal
logger.add(LOG_FILE, rotation="5 MB", level="INFO") # Salva no arquivo

# ==========================================
# 1. CLASSE DE PAGINAÇÃO (Adaptada para Loguru)
# ==========================================
class Pagination:
    """Gerencia a paginação de resultados da API GLPI de forma genérica."""
    
    def __init__(self, api_method: Callable, limit: int = 50):
        self.api_method = api_method
        self.limit = limit
        self.total_processed = 0

    def get_all_items(self) -> List[Dict[str, Any]]:
        all_items = []
        current_offset = 0
        page = 1

        logger.info(f"Buscando página {page}...")        
        initial_response = self.api_method(current_offset, self.limit)
        
        if not initial_response:
            logger.error("Falha ao buscar a primeira página ou resposta vazia.")
            return []        
        
        if "data" not in initial_response or "total_count" not in initial_response:
            logger.error(f"Resposta inválida da API: {initial_response.keys() if initial_response else 'None'}")
            return []
        
        total_count = initial_response["total_count"]
        all_items.extend(initial_response["data"])
        items_count = len(initial_response["data"])
        self.total_processed = items_count
        
        logger.info(f"Processados {self.total_processed} de {total_count} itens (página {page})")
        
        if total_count <= self.limit or self.total_processed >= total_count:
            logger.info("Todos os itens já foram processados na primeira requisição.")
            return all_items
        
        while self.total_processed < total_count:
            page += 1
            current_offset = self.total_processed
            logger.info(f"Buscando página {page} (offset {current_offset})...")

            response = self.api_method(current_offset, self.limit)

            if not response or "data" not in response:
                logger.error(f"Resposta inválida na página {page}.")
                break

            items = response["data"]
            items_count = len(items)
            
            if items_count == 0:
                logger.info(f"Página {page} sem mais dados, finalizando...")
                break

            all_items.extend(items)
            self.total_processed += items_count
            logger.info(f"Processados {self.total_processed} de {total_count} itens (página {page})")

            if self.total_processed >= total_count:
                logger.info("Todos os itens foram processados com sucesso.")
                break
        
        return all_items

# ==========================================
# 2. LÓGICA DE INGESTÃO
# ==========================================
def run_ingestion():
    load_dotenv()
    
    DB_URL = "postgresql://admin:admin123@localhost:5432/dw_glpi"
    API_URL = f"{os.getenv('GLPI_BASE_URL')}/apirest.php/search/Ticket"
    HEADERS = {
        "App-Token": os.getenv('GLPI_APP_TOKEN'),
        "Session-Token": os.getenv('GLPI_SESSION_TOKEN')
    }

    # Callback que a classe Pagination vai chamar a cada ciclo
    def fetch_glpi_page(offset: int, limit: int) -> dict:
        params = {
            "range": f"{offset}-{offset + limit - 1}",
            "expand_dropdowns": "true"
        }
        
        try:
            response = requests.get(API_URL, headers=HEADERS, params=params)
            
            # Tratamento do erro 400 (Range Excedido) do GLPI
            if response.status_code == 400 and "ERROR_RANGE_EXCEED_TOTAL" in response.text:
                logger.info(f"Fim do range alcançado no offset {offset} (Status 400 capturado).")
                return {"data": [], "total_count": 0}
                
            response.raise_for_status()
            data = response.json()
            
            # O GLPI informa o total real de itens no Header 'Content-Range' (ex: '0-99/736')
            content_range = response.headers.get("Content-Range", "")
            total_count = 0
            if "/" in content_range:
                try:
                    total_count = int(content_range.split("/")[-1])
                except ValueError:
                    pass

            return {
                "data": data.get("data", []),
                "total_count": total_count
            }
        except Exception as e:
            logger.error(f"Erro ao buscar offset {offset}: {e}")
            return None

    # --- INÍCIO DA ORQUESTRAÇÃO ---
    logger.info("Iniciando extração TOTAL de chamados usando paginação inteligente...")
    
    # Instancia o paginador limitando de 100 em 100
    paginator = Pagination(api_method=fetch_glpi_page, limit=100)
    tickets_raw = paginator.get_all_items()
    
    if not tickets_raw:
        logger.warning("Nenhum dado retornado da API ou falha na extração.")
        return

    # --- VALIDAÇÃO COM PYDANTIC ---
    logger.info("Iniciando validação de dados (Pydantic Inspector)...")
    valid_tickets = []
    for item in tickets_raw:
        try:
            ticket = TicketSchema(**item)
            # Usa model_dump() (Pydantic V2) em vez de dict()
            valid_tickets.append(ticket.model_dump()) 
        except Exception as e:
            logger.error(f"Falha de schema no ticket ID '{item.get('2')}': {e}")

    # --- CARGA NO POSTGRESQL ---
    if valid_tickets:
        logger.info("Preparando dataframe para carga no Data Warehouse...")
        df = pd.DataFrame(valid_tickets)
        engine = create_engine(DB_URL)
        
        # O if_exists="replace" garante que não haverá duplicidade entre execuções
        df.to_sql("staging_tickets", engine, if_exists="replace", index=False)
        logger.success(f"Carga finalizada! {len(df)} tickets salvos na tabela 'staging_tickets'.")
    else:
        logger.warning("Nenhum ticket passou na validação de qualidade (Pydantic).")

if __name__ == "__main__":
    run_ingestion()