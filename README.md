# Pipeline de Dados e Dashboard GLPI

Este projeto implementa um pipeline de Engenharia de Dados (ELT) focado em extrair, tratar e visualizar indicadores do sistema de chamados GLPI. A solução consome a API REST do GLPI, valida e persiste os dados em um banco PostgreSQL, realiza transformações diretamente no banco (*push-down*) e serve as análises por meio de um dashboard interativo construído com Streamlit.

---

## Arquitetura e Fluxo de Dados

O projeto segue uma arquitetura em camadas inspirada na *Modern Data Stack*:

```
API GLPI → Staging (Bronze) → Silver → Dashboard (App)
```

### Staging (Bronze)
Scripts de extração consomem a API REST do GLPI com paginação automática e validação de contratos via Pydantic. Os dados brutos são carregados diretamente nas tabelas de staging no PostgreSQL.

| Tabela               | Origem                        | Descrição                              |
|----------------------|-------------------------------|----------------------------------------|
| `staging_tickets`    | `/apirest.php/search/Ticket`  | Todos os chamados com técnicos, requerentes e localização |
| `staging_users`      | `/apirest.php/User`           | Cadastro de usuários (nome, login)     |
| `staging_locations`  | `/apirest.php/Location`       | Localizações/departamentos cadastrados |

### Silver
Transformações executadas inteiramente em SQL dentro do PostgreSQL (sem movimentação de dados). As tabelas Silver são recriadas a cada execução, garantindo idempotência.

| Tabela                      | Descrição                                                        |
|-----------------------------|------------------------------------------------------------------|
| `silver_tickets`            | Fato principal com nomes de técnicos, requerentes e localização  |
| `silver_ticket_tecnicos`    | Dimensão explodida: 1 linha por ticket-técnico                   |
| `silver_ticket_requerentes` | Dimensão explodida: 1 linha por ticket-requerente                |
| `silver_locations`          | Dimensão de localizações (id, nome)                              |

O GLPI armazena múltiplos técnicos e requerentes como IDs separados por vírgula. A transformação usa `CROSS JOIN LATERAL + unnest()` para explodir esses valores em linhas individuais e `string_agg()` para reagrupar os nomes na tabela fato.

### App (Dashboard)
Interface analítica construída com Streamlit e Plotly que consome a camada Silver. Permite filtrar por período, localização e técnico, e exibe métricas de volume, comparativos anuais e análise por localização/departamento.

---

## Tecnologias

| Camada          | Tecnologia                         |
|-----------------|------------------------------------|
| Linguagem       | Python 3.13                        |
| Pacotes         | [uv](https://github.com/astral-sh/uv) |
| Banco de Dados  | PostgreSQL 15 (Docker)             |
| Validação       | Pydantic                           |
| ORM / SQL       | SQLAlchemy + SQL nativo            |
| Processamento   | Pandas                             |
| Dashboard       | Streamlit + Plotly                 |
| Logs            | Loguru                             |

---

## Estrutura do Repositório

```
.
├── docker-compose.yml          # Infraestrutura local (PostgreSQL)
├── pyproject.toml              # Dependências do projeto
├── uv.lock                     # Lockfile gerado pelo uv
├── .env.example                # Modelo de variáveis de ambiente
├── logs/                       # Logs de execução gerados automaticamente
├── dags/                       # Reservado para orquestração futura (Airflow)
└── src/
    ├── app/
    │   └── main.py             # Dashboard principal (consome camada Silver)
    ├── extractions/
    │   ├── ingest_to_db.py     # Extração de tickets com paginação e validação Pydantic
    │   ├── ingest_users.py     # Extração de usuários
    │   └── ingest_locations.py # Extração de localizações/departamentos
    ├── schemas/
    │   └── schemas.py          # Contratos Pydantic para validação da API
    ├── transform/
    │   └── build_silver.py     # Transformações ELT (Staging → Silver)
    └── utils/
        ├── get_session.py      # Renovação do token de sessão do GLPI
        └── api_call.py         # Utilitário de descoberta de campos da API
```

---

## Como Executar

### Pré-requisitos

- [Docker](https://www.docker.com/) instalado e em execução
- [uv](https://github.com/astral-sh/uv) instalado (`curl -sSf https://astral.sh/uv/install.sh | sh`)

### 1. Configurar as variáveis de ambiente

Copie o arquivo de exemplo e preencha com suas credenciais:

```bash
cp .env.example .env
```

Edite o `.env` com os dados da sua instância GLPI e do banco de dados:

```env
# API GLPI
GLPI_BASE_URL="https://sua-instancia.glpi.com"
GLPI_APP_TOKEN='seu_app_token'
GLPI_USER_TOKEN='seu_user_token'
GLPI_SESSION_TOKEN=''          # deixe em branco, será preenchido automaticamente

# PostgreSQL
DW_HOST=host_address
DW_PORT=host_port
DW_DATABASE=db_name
DW_USER=db_user
DW_PASSWORD=db_password

LOG_LEVEL=INFO
```

> O `GLPI_APP_TOKEN` é gerado nas configurações da API do GLPI. O `GLPI_USER_TOKEN` é obtido nas configurações do usuário dentro do GLPI.

### 2. Subir o banco de dados

```bash
docker-compose up -d
```

### 3. Instalar as dependências

```bash
uv sync
```

### 4. Obter o token de sessão

O token de sessão do GLPI expira periodicamente. Execute este script antes de qualquer extração para renovar o token e atualizar o `.env` automaticamente:

```bash
uv run src/utils/get_session.py
```

### 5. Executar o pipeline de extração (Staging)

Os scripts de extração devem ser rodados na seguinte ordem:

```bash
uv run src/extractions/ingest_users.py       # Carrega usuários
uv run src/extractions/ingest_to_db.py       # Carrega tickets (com paginação automática)
uv run src/extractions/ingest_locations.py   # Carrega localizações/departamentos
```

Cada execução substitui completamente a tabela de staging correspondente (`if_exists='replace'`), garantindo que não haja duplicidade.

### 6. Executar a transformação (Silver)

```bash
uv run src/transform/build_silver.py
```

Este script executa todas as transformações SQL diretamente no PostgreSQL, recriando as quatro tabelas da camada Silver do zero.

### 7. Iniciar o dashboard

```bash
uv run streamlit run src/app/main.py
```

Acesse em: `http://localhost:8501`

---

## Detalhes do Pipeline

### Paginação automática de tickets

O script `ingest_to_db.py` implementa uma classe `Pagination` que gerencia automaticamente a paginação da API do GLPI. Ela lê o total de registros pelo header `Content-Range` e busca os dados de 100 em 100 itens, tratando o erro `ERROR_RANGE_EXCEED_TOTAL` (status 400) que o GLPI retorna ao ultrapassar o range.

### Validação com Pydantic

Cada ticket retornado pela API é validado contra o schema `TicketSchema` antes de ser carregado no banco. O schema mapeia os IDs numéricos dos campos do GLPI (ex: `"2"` → `id`, `"7"` → `categoria`, `"83"` → `localizacao`) para campos com nomes legíveis, e normaliza múltiplos técnicos/requerentes em strings separadas por vírgula.

### Renovação de token

O GLPI utiliza um modelo de autenticação em duas etapas: `App-Token` (fixo, configurado na API) + `Session-Token` (temporário, obtido via login). O script `get_session.py` automatiza a renovação, escrevendo o novo token diretamente no `.env`.

---

## Contribuindo

1. Faça um fork do repositório
2. Crie uma branch para sua feature: `git checkout -b feature/minha-feature`
3. Faça suas alterações e commit: `git commit -m 'feat: descrição da mudança'`
4. Envie para o seu fork: `git push origin feature/minha-feature`
5. Abra um Pull Request descrevendo o que foi alterado e por quê

Ao contribuir, certifique-se de nunca commitar o arquivo `.env` com credenciais reais. Use sempre o `.env.example` como referência.
