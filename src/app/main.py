import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px

# Configuração inicial da página
st.set_page_config(page_title="Dashboard GLPI - SECTIES", page_icon="🎫", layout="wide")

# ==========================================
# 1. CARGA E TRATAMENTO DE DADOS (CACHE)
# ==========================================
@st.cache_data(ttl=600)
def load_data():
    DB_URL = "postgresql://admin:admin123@localhost:5432/dw_glpi"
    engine = create_engine(DB_URL)
    df = pd.read_sql_table("staging_tickets", engine)
    
    # Converte data
    df['data_abertura'] = pd.to_datetime(df['data_abertura'])
    
    # Dicionário para garantir a ordem e os nomes em PT-BR
    meses_ptbr = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    
    # Extrai Ano e Mês
    df['ano'] = df['data_abertura'].dt.year
    df['mes_num'] = df['data_abertura'].dt.month
    df['mes_nome'] = df['mes_num'].map(meses_ptbr)
    
    # Coluna oculta para ordenar o gráfico de linha cronologicamente
    df['periodo_ordenacao'] = df['data_abertura'].dt.to_period('M').astype(str)
    
    return df

df = load_data()

# ==========================================
# 2. BARRA LATERAL (FILTROS)
# ==========================================
st.sidebar.header("🔍 Filtros de Análise")
st.sidebar.markdown("*Nota: Na camada atual (Staging), Técnicos e Requerentes aparecem como IDs. Os nomes reais entrarão na camada Silver.*")

# --- Filtro de Ano ---
# Pega os anos únicos, ordena do maior para o menor
lista_anos = ["Todos"] + sorted(list(df['ano'].dropna().unique()), reverse=True)
ano_selecionado = st.sidebar.selectbox("Ano", lista_anos)

# --- Filtro de Mês ---
# Lista padrão com os 12 meses na ordem correta
todos_os_meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 
                  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
# Filtra apenas os meses que realmente existem nos dados para não mostrar opções vazias
meses_existentes = [m for m in todos_os_meses if m in df['mes_nome'].unique()]
lista_meses = ["Todos"] + meses_existentes
mes_selecionado = st.sidebar.selectbox("Mês", lista_meses)

# --- Filtros de Negócio ---
lista_categorias = ["Todas"] + sorted(list(df['categoria'].astype(str).unique()))
cat_selecionada = st.sidebar.selectbox("Categoria", lista_categorias)

lista_requerentes = ["Todos"] + list(df['requerente_id'].dropna().unique())
req_selecionado = st.sidebar.selectbox("Requerente (ID)", lista_requerentes)

lista_tecnicos = ["Todos"] + list(df['tecnico_id'].dropna().unique())
tec_selecionado = st.sidebar.selectbox("Técnico (ID)", lista_tecnicos)

# ==========================================
# 3. APLICAÇÃO DOS FILTROS
# ==========================================
df_filtrado = df.copy()

if ano_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['ano'] == ano_selecionado]

if mes_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['mes_nome'] == mes_selecionado]

if cat_selecionada != "Todas":
    df_filtrado = df_filtrado[df_filtrado['categoria'] == cat_selecionada]

if req_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['requerente_id'] == req_selecionado]

if tec_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['tecnico_id'] == tec_selecionado]

# ==========================================
# 4. CONSTRUÇÃO DA INTERFACE (MAIN)
# ==========================================
st.title("📊 Dashboard de Chamados - GLPI (Staging)")

# KPIs
col1, col2, col3 = st.columns(3)
total_chamados = len(df_filtrado)
total_categorias = df_filtrado['categoria'].nunique()
chamados_sem_categoria = len(df_filtrado[df_filtrado['categoria'] == "Sem categoria"])

col1.metric("Chamados no Período", total_chamados)
col2.metric("Categorias Afetadas", total_categorias)
col3.metric("Sem Categoria Definida", chamados_sem_categoria)

st.divider()

# Gráficos
col_grafico1, col_grafico2 = st.columns(2)

with col_grafico1:
    st.subheader("Volume por Categoria (Top 10)")
    if not df_filtrado.empty:
        df_cat = df_filtrado['categoria'].value_counts().head(10).reset_index()
        df_cat.columns = ['Categoria', 'Quantidade']
        fig_cat = px.bar(df_cat, x='Quantidade', y='Categoria', orientation='h', color_discrete_sequence=['#1f77b4'])
        fig_cat.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_cat, use_container_width=True)
    else:
        st.info("Nenhum dado para exibir com os filtros atuais.")

st.divider()

# Tabela
st.subheader("Dados Filtrados")
st.dataframe(
    df_filtrado[['id', 'titulo', 'categoria', 'data_abertura', 'status_id', 'requerente_id', 'tecnico_id']], 
    use_container_width=True,
    hide_index=True
)