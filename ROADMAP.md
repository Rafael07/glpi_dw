# Roadmap do Projeto — GLPI Data Warehouse

Este documento registra o estado atual de implementação e as evoluções planejadas para o projeto. O objetivo é que qualquer pessoa que clone o repositório entenda imediatamente o que está funcional, o que está em progresso e o que ainda precisa ser construído para que o projeto seja considerado maduro do ponto de vista de Engenharia de Dados.

> **Legenda:** ✅ Implementado · 🔄 Em andamento · 🔲 Planejado · 💡 Ideia em avaliação

---

## 1. Ingestão de Dados (Extração)

| Status | Item |
|--------|------|
| ✅ | Extração de tickets via API REST do GLPI com paginação automática |
| ✅ | Extração de usuários (técnicos e requerentes) |
| ✅ | Extração de localizações/departamentos |
| ✅ | Validação de contratos com Pydantic antes da carga |
| ✅ | Tratamento de múltiplos técnicos/requerentes por ticket (IDs concatenados) |
| ✅ | Renovação automática de token de sessão do GLPI |
| 🔲 | **Carga incremental** — hoje toda execução faz full load (`if_exists='replace'`). Implementar controle de watermark por `data_abertura` ou `date_mod` para ingerir apenas registros novos/alterados |
| 🔲 | Extração do status do ticket (`status_id`) com mapeamento para rótulos legíveis (ex: 1=Novo, 2=Em andamento, 5=Resolvido, 6=Fechado) |
| 🔲 | Extração de categorias como dimensão separada (hoje é string desnormalizada no ticket) |
| 💡 | Extração de SLA e tempo de resolução por ticket para métricas de performance |

---

## 2. Transformação e Modelagem (Silver)

| Status | Item |
|--------|------|
| ✅ | Tabela fato `silver_tickets` com nomes de técnicos, requerentes e localização |
| ✅ | Dimensão explodida `silver_ticket_tecnicos` (1 linha por ticket-técnico) |
| ✅ | Dimensão explodida `silver_ticket_requerentes` (1 linha por ticket-requerente) |
| ✅ | Dimensão `silver_locations` (localizações limpas) |
| ✅ | Transformações executadas por push-down no PostgreSQL (sem movimentação de dados) |
| ✅ | Recriação idempotente das tabelas a cada execução (`DROP + CREATE`) |
| 🔲 | **Carga incremental na Silver** — hoje é full rebuild. Ao implementar incremental na staging, a silver também precisará de estratégia de merge/upsert |
| 🔲 | Dimensão de status com mapeamento de IDs para rótulos |
| 🔲 | Cálculo de tempo de resolução (campo `date_mod` vs `data_abertura`) |
| 🔲 | Camada **Gold** — tabelas agregadas prontas para consumo direto (ex: volume mensal por localização, taxa de resolução por técnico) |
| 💡 | Migração das transformações para **dbt** (dependência já declarada no `pyproject.toml`), ganhando versionamento de modelos, testes de qualidade nativos e documentação automática |

---

## 3. Orquestração

| Status | Item |
|--------|------|
| ✅ | Execução manual via scripts Python na ordem correta |
| 🔲 | **Orquestração com Apache Airflow** — diretório `dags/` já reservado. Criar uma DAG com as seguintes tasks em sequência: `get_session → ingest_users → ingest_tickets → ingest_locations → build_silver` |
| 🔲 | Agendamento diário automático da DAG (ex: toda madrugada) |
| 🔲 | Alertas por e-mail ou webhook em caso de falha na pipeline |
| 🔲 | Retry automático com backoff exponencial em caso de falha na API |
| 💡 | Avaliar substituição do Airflow por **Prefect** ou **Dagster** para projetos menores (menor overhead operacional) |

---

## 4. Qualidade de Dados

| Status | Item |
|--------|------|
| ✅ | Validação de schema com Pydantic na ingestão |
| ✅ | Tratamento de valores nulos (categoria, técnico, localização) com defaults legíveis |
| 🔲 | **Testes automatizados** — estrutura de testes com `pytest` já está nas dependências de dev, mas não há nenhum teste escrito. Implementar testes para: transformações SQL, lógica de paginação e validações do schema |
| 🔲 | Testes de qualidade de dados na Silver (ex: verificar se há tickets sem localização, técnico ou categoria acima de um threshold aceitável) |
| 🔲 | Controle de linhas: logar quantos registros entraram vs. quantos foram carregados por execução |
| 💡 | Se migrar para dbt, usar `dbt test` para testes de unicidade, not-null e integridade referencial nativamente |

---

## 5. Dashboard e Visualizações

| Status | Item |
|--------|------|
| ✅ | Filtros por período: ano, mês, bimestre, trimestre, semestre e intervalo livre |
| ✅ | Filtro por categoria, localização e técnico |
| ✅ | Visão detalhada: top 10 categorias, volume por dia, lista de chamados |
| ✅ | Comparativo anual (YoY): tickets do ano atual vs. ano anterior por mês |
| ✅ | Análise por localização: ranking de localizações e top 3 categorias por localização/técnico |
| ✅ | Cache de dados com TTL de 10 minutos para evitar queries repetidas |
| 🔲 | Métrica de **tempo médio de resolução** por localização e por técnico |
| 🔲 | Gráfico de distribuição por **status do ticket** (aberto, em andamento, resolvido, fechado) |
| 🔲 | Visão de **SLA**: percentual de tickets resolvidos dentro do prazo |
| 🔲 | Heatmap de volume por dia da semana × hora de abertura |
| 🔲 | Filtro por técnico na aba de análise por localização para cruzar as duas dimensões |
| 💡 | Exportação dos dados filtrados para CSV/Excel diretamente pelo dashboard |
| 💡 | Migrar visualizações para **Metabase** ou **Apache Superset** para suportar múltiplos usuários sem escalar o Streamlit |

---

## 6. KPIs Sugeridos

Indicadores relevantes a implementar nas próximas iterações, sem uso de dados pessoais:

| KPI | Descrição |
|-----|-----------|
| **Volume por período** | Total de chamados abertos por dia, semana, mês ✅ (parcial) |
| **Distribuição por categoria** | Quais tipos de problema geram mais chamados ✅ |
| **Ranking de localização** | Quais departamentos abrem mais chamados ✅ |
| **Desempenho por técnico** | Volume atendido por técnico no período ✅ (parcial) |
| **Tempo médio de resolução (TMR)** | Média de dias/horas entre abertura e fechamento 🔲 |
| **Taxa de reabertura** | Percentual de chamados fechados e reabertos 🔲 |
| **Conformidade de SLA** | % de tickets resolvidos dentro do prazo definido por categoria 🔲 |
| **Backlog acumulado** | Chamados abertos há mais de X dias sem resolução 🔲 |
| **Tendência de crescimento** | Variação percentual de volume mês a mês (MoM) 🔲 |

---

## 7. Segurança e Acesso

| Status | Item |
|--------|------|
| ✅ | Credenciais isoladas em `.env` (fora do controle de versão) |
| ✅ | `.env.example` com modelo sem valores sensíveis versionado no repositório |
| 🔲 | **Autenticação no dashboard** — hoje o Streamlit não exige login. Implementar autenticação básica ou integração com SSO para ambientes compartilhados |
| 🔲 | Gerenciamento de segredos via **HashiCorp Vault** ou **AWS Secrets Manager** para ambientes de produção (substituir variáveis de ambiente em texto plano) |
| 🔲 | Princípio do menor privilégio: criar usuário PostgreSQL de leitura exclusiva para o dashboard (hoje usa o mesmo usuário de escrita da pipeline) |
| 🔲 | Rotação automática do token de sessão do GLPI integrada à DAG do Airflow |
| 💡 | Em caso de exposição pública do dashboard, avaliar proxy reverso com HTTPS (Nginx + Let's Encrypt) |

---

## 8. Infraestrutura e Operação

| Status | Item |
|--------|------|
| ✅ | PostgreSQL 15 containerizado com Docker Compose |
| ✅ | Logs estruturados com Loguru (arquivo rotacionado) |
| ✅ | Healthcheck do container PostgreSQL no `docker-compose.yml` |
| ✅ | Variáveis de conexão do banco lidas do `.env` em todos os scripts (sem hardcode) |
| ✅ | **Containerização do dashboard** — `Dockerfile` criado com imagem Python 3.13 + uv; serviço `dashboard` adicionado ao `docker-compose.yml`; deploy na VM resume a: `git clone → cp .env.example .env → docker-compose up -d` |
| 🔲 | **Pipeline também containerizada** — hoje os scripts de extração/transform rodam fora do Docker. Próximo passo: rodar via `docker compose exec` ou adicionar serviço dedicado |
| 🔲 | **Persistência do banco em produção** — volume Docker é local. Avaliar backup automático com `pg_dump` agendado |
| 🔲 | Monitoramento de execução: registrar em tabela de controle cada execução da pipeline com timestamp, status e quantidade de registros processados |
| 💡 | Deploy em nuvem (ex: banco no RDS, pipeline no ECS/Cloud Run, dashboard no Streamlit Cloud) |

---

## Resumo de Maturidade

| Dimensão              | Status Atual | Meta |
|-----------------------|-------------|------|
| Ingestão              | ✅ Funcional (full load) | Incremental + orquestrado |
| Transformação         | ✅ Funcional (full rebuild) | Incremental + dbt |
| Qualidade de Dados    | 🔄 Básica (Pydantic) | Testes automatizados |
| Orquestração          | 🔲 Manual | Airflow agendado |
| Dashboard             | ✅ Funcional | KPIs de SLA + exportação |
| Segurança             | 🔄 Básica (.env) | Autenticação + menor privilégio |
| Infraestrutura        | ✅ Containerizado (DB + Dashboard) | Pipeline containerizada + backup |

---

## Deploy na VM da Empresa — Passo a Passo

Este guia descreve como mover o projeto do ambiente local para a VM provisionada pela empresa. Pré-requisito: a VM deve ter **Docker** e **Git** instalados.

### 1. Preparar a VM

Acesse a VM via SSH e verifique os pré-requisitos:

```bash
ssh usuario@ip-da-vm

docker --version   # Docker 20+ recomendado
git --version
```

Caso o Docker não esteja instalado, siga a documentação oficial para a distribuição Linux da VM: https://docs.docker.com/engine/install/

### 2. Clonar o repositório

```bash
git clone <url-do-repositorio>
cd glpi_dw
```

### 3. Configurar as variáveis de ambiente

```bash
cp .env.example .env
nano .env   # ou vim .env
```

Preencha com as credenciais reais da instância GLPI e defina as configurações do banco:

```env
GLPI_BASE_URL="https://sua-instancia.glpi.com"
GLPI_APP_TOKEN='seu_app_token'
GLPI_USER_TOKEN='seu_user_token'
GLPI_SESSION_TOKEN=''

DW_HOST=postgres_dw       # nome do serviço no Docker Compose — não alterar
DW_PORT=5432
DW_DATABASE=dw_glpi
DW_USER=admin
DW_PASSWORD=senha-segura  # troque para uma senha forte em produção
```

> ⚠️ O arquivo `.env` nunca deve ser commitado. Ele já está no `.gitignore`.

### 4. Construir e subir os containers

```bash
docker-compose up -d --build
```

Este comando:
- Constrói a imagem do dashboard a partir do `Dockerfile`
- Sobe o container do PostgreSQL com healthcheck
- Sobe o container do dashboard Streamlit assim que o banco estiver pronto
- Mantém tudo rodando em background (`-d`)

Verifique se os containers estão de pé:

```bash
docker-compose ps
```

### 5. Rodar o pipeline de ingestão pela primeira vez

Com os containers rodando, execute os scripts de extração dentro do container:

```bash
# Renovar token de sessão
docker compose exec dashboard uv run src/utils/get_session.py

# Extração (staging)
docker compose exec dashboard uv run src/extractions/ingest_users.py
docker compose exec dashboard uv run src/extractions/ingest_to_db.py
docker compose exec dashboard uv run src/extractions/ingest_locations.py

# Transformação (silver)
docker compose exec dashboard uv run src/transform/build_silver.py
```

### 6. Acessar o dashboard

O Streamlit estará disponível na rede interna da empresa em:

```
http://ip-da-vm:8501
```

Qualquer pessoa na mesma rede pode acessar pelo navegador sem instalar nada.

### 7. Atualizar o projeto no futuro

Quando houver novas versões no repositório:

```bash
git pull
docker-compose up -d --build   # reconstrói a imagem com as mudanças
```

### 8. Comandos úteis de operação

```bash
# Ver logs do dashboard em tempo real
docker-compose logs -f dashboard

# Ver logs do banco
docker-compose logs -f postgres_dw

# Parar tudo
docker-compose down

# Parar e apagar os dados do banco (cuidado!)
docker-compose down -v

# Reiniciar apenas o dashboard
docker-compose restart dashboard
```

---

*Última atualização: Maio de 2026*
