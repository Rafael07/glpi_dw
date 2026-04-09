Pipeline de Dados e Dashboard GLPI
==================================

Este projeto implementa um pipeline de Engenharia de Dados (ELT) focado em extrair, tratar e visualizar indicadores do sistema de chamados GLPI. A solução automatiza a extração via API, realiza a modelagem dos dados em um banco PostgreSQL (através de processamento *push-down*) e serve análises de Business Intelligence por meio de um dashboard interativo.

🏗️ Arquitetura e Fluxo de Dados
--------------------------------

A arquitetura do projeto é baseada nos conceitos da *Modern Data Stack*, garantindo performance e separação de responsabilidades:

1.  **Extração (Staging):** Conexão com a API REST do GLPI para consumo de tickets e usuários. Os dados são validados utilizando contratos estruturados antes de serem carregados no banco de dados.

2.  **Transformação (Silver):** Processamento ELT executado diretamente no banco de dados (PostgreSQL). Responsável por normalizar arrays (ex: desmembrar IDs de técnicos e requerentes concatenados) e preparar cruzamentos otimizados.

3.  **Apresentação (App):** Interface analítica interativa que consome a camada Silver já mastigada para exibir métricas operacionais, volume de chamados e performance da equipe.

📂 Estrutura do Repositório
---------------------------

O projeto está organizado com o padrão de desenvolvimento Python, utilizando gerenciamento de dependências moderno.

Plaintext

```
.
├── README.md               # Documentação do projeto
├── dags/                   # Diretório reservado para futura orquestração
├── docker-compose.yml      # Infraestrutura local (banco de dados Postgres, etc.)
├── logs/                   # Arquivos de log de execução (ex: ingestion.log)
├── pyproject.toml          # Configurações do projeto e dependências principais
├── uv.lock                 # Lockfile de dependências (gerenciado pelo uv)
└── src/                    # Código-fonte principal
    ├── app/                # Camada de Visualização (Front-end)
    │   ├── main.py         # Dashboard legado (Staging direta)
    │   └── main_silver.py  # Dashboard otimizado (consome a camada Silver)
    ├── extractions/        # Camada de Ingestão (API -> Staging)
    │   ├── api_call.py     # Lógica de paginação e requisições à API
    │   ├── get_session.py  # Gerenciamento de token e sessão do GLPI
    │   ├── ingest_to_db.py # Script de carga da tabela de tickets
    │   └── ingest_users.py # Script de carga da tabela de usuários
    ├── schemas/            # Contratos de Dados
    │   └── schemas.py      # Modelos Pydantic para validação da API
    └── transform/          # Camada de Modelagem (Staging -> Silver)
        └── build_silver.py # Script ELT com queries de tratamento no banco

```

🚀 Tecnologias Utilizadas
-------------------------

-   **Linguagem:** Python 3.13

-   **Gerenciador de Pacotes:** [uv](https://github.com/astral-sh/uv)

-   **Banco de Dados:** PostgreSQL (via Docker)

-   **Modelagem e ORM:** SQLAlchemy, SQL nativo

-   **Validação de Dados:** Pydantic

-   **Processamento:** Pandas

-   **Visualização de Dados:** Streamlit, Plotly

⚙️ Como Executar o Projeto
--------------------------

Certifique-se de ter o Docker e o gerenciador de pacotes `uv` instalados em sua máquina.

**1\. Subir a infraestrutura:**

Inicie o banco de dados PostgreSQL utilizando o Docker Compose.

Bash

```
docker-compose up -d

```

**2\. Instalar as dependências:**

Utilize o `uv` para sincronizar o ambiente virtual e instalar as bibliotecas.

Bash

```
uv sync

```

**3\. Executar o Pipeline (ELT):**

Atualmente, o pipeline é executado em etapas. Rode os scripts na seguinte ordem para garantir a integridade dos dados:

Bash

```
# Extração para a camada Staging
uv run src/extractions/ingest_users.py
uv run src/extractions/ingest_to_db.py

# Transformação para a camada Silver
uv run src/transform/build_silver.py

```

**4\. Acessar o Dashboard:**

Inicie a aplicação Streamlit apontando para a versão mais atual do painel (Silver).

Bash

```
uv run streamlit run src/app/main_silver.py

```

A aplicação estará disponível no seu navegador, geralmente no endereço `http://localhost:8501`.