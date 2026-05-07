import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Configurações
load_dotenv()
DB_URL = f"postgresql://{os.getenv('DW_USER', 'admin')}:{os.getenv('DW_PASSWORD', 'admin123')}@{os.getenv('DW_HOST', 'localhost')}:{os.getenv('DW_PORT', '5432')}/{os.getenv('DW_DATABASE', 'dw_glpi')}"

def build_silver_layer():
    print("Iniciando a transformação para a camada Silver (ELT)...")
    engine = create_engine(DB_URL)
    
    with engine.begin() as conn:
        # ---------------------------------------------------------
        # 1. Criar Tabela "Explodida" de Técnicos
        # ---------------------------------------------------------
        print("🔧 Construindo silver_ticket_tecnicos...")
        conn.execute(text("""
            DROP TABLE IF EXISTS silver_ticket_tecnicos CASCADE;
            CREATE TABLE silver_ticket_tecnicos AS
            SELECT 
                t.id AS ticket_id,
                TRIM(tec_id) AS tecnico_id,
                COALESCE(u.nome_completo, 'Técnico Desconhecido') AS tecnico_nome
            FROM staging_tickets t
            CROSS JOIN LATERAL unnest(string_to_array(t.tecnico_id, ',')) AS tec_id
            LEFT JOIN staging_users u ON TRIM(tec_id) = u.id::varchar
            WHERE tec_id != '' AND tec_id IS NOT NULL;
        """))

        # ---------------------------------------------------------
        # 2. Criar Tabela "Explodida" de Requerentes
        # ---------------------------------------------------------
        print("🧑‍💻 Construindo silver_ticket_requerentes...")
        conn.execute(text("""
            DROP TABLE IF EXISTS silver_ticket_requerentes CASCADE;
            CREATE TABLE silver_ticket_requerentes AS
            SELECT 
                t.id AS ticket_id,
                TRIM(req_id) AS requerente_id,
                COALESCE(u.nome_completo, 'Requerente Desconhecido') AS requerente_nome
            FROM staging_tickets t
            CROSS JOIN LATERAL unnest(string_to_array(t.requerente_id, ',')) AS req_id
            LEFT JOIN staging_users u ON TRIM(req_id) = u.id::varchar
            WHERE req_id != '' AND req_id IS NOT NULL;
        """))

        # ---------------------------------------------------------
        # 3. Criar a Tabela Principal (silver_tickets) com Nomes
        # ---------------------------------------------------------
        print("🎫 Construindo fato principal silver_tickets...")
        conn.execute(text("""
            DROP TABLE IF EXISTS silver_tickets CASCADE;
            CREATE TABLE silver_tickets AS
            WITH tec_agrupado AS (
                SELECT ticket_id, string_agg(tecnico_nome, ', ') AS tecnicos_nomes
                FROM silver_ticket_tecnicos
                GROUP BY ticket_id
            ),
            req_agrupado AS (
                SELECT ticket_id, string_agg(requerente_nome, ', ') AS requerentes_nomes
                FROM silver_ticket_requerentes
                GROUP BY ticket_id
            )
            SELECT
                t.id,
                t.titulo,
                t.categoria,
                t.data_abertura,
                COALESCE(t.localizacao, 'Sem Localização') AS localizacao,
                COALESCE(r.requerentes_nomes, 'Sem Requerente') AS requerentes,
                COALESCE(te.tecnicos_nomes, 'Sem Técnico') AS tecnicos
            FROM staging_tickets t
            LEFT JOIN tec_agrupado te ON t.id = te.ticket_id
            LEFT JOIN req_agrupado r ON t.id = r.ticket_id;
        """))

        # ---------------------------------------------------------
        # 4. Criar Tabela de Localizações (Dimensão)
        # ---------------------------------------------------------
        print("📍 Construindo silver_locations...")
        conn.execute(text("""
            DROP TABLE IF EXISTS silver_locations CASCADE;
            CREATE TABLE silver_locations AS
            SELECT id, name
            FROM staging_locations;
        """))

    print("🚀 Camada Silver construída com sucesso no banco de dados!")

if __name__ == "__main__":
    build_silver_layer()