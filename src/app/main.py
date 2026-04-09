import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="Dashboard GLPI - SECTIES", page_icon="🎫", layout="wide")

# ==========================================
# 1. CARGA E TRATAMENTO (CACHE)
# ==========================================
@st.cache_data(ttl=600)
def load_data():
    DB_URL = "postgresql://admin:admin123@localhost:5432/dw_glpi"
    engine = create_engine(DB_URL)
    df = pd.read_sql_table("staging_tickets", engine)
    
    df['data_abertura'] = pd.to_datetime(df['data_abertura'])
    df['ano'] = df['data_abertura'].dt.year
    df['mes_num'] = df['data_abertura'].dt.month
    df['data_apenas'] = df['data_abertura'].dt.date
    
    df['bimestre'] = (df['mes_num'] - 1) // 2 + 1
    df['trimestre'] = df['data_abertura'].dt.quarter
    df['semestre'] = (df['mes_num'] - 1) // 6 + 1
    
    df['mes_nome'] = df['mes_num'].map({
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
        7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    })
    
    return df

df = load_data()

# ==========================================
# 2. BARRA LATERAL - CONTROLE DE FILTROS
# ==========================================
st.sidebar.title("🎮 Controles do Dashboard")

modo_filtro = st.sidebar.radio("Escolha o modo de filtragem:", ["Calendário (Ano/Mês/Período)", "Intervalo Livre (De-Até)"], index=0)

st.sidebar.divider()
df_filtrado = df.copy()

# --- Filtros de Tempo ---
if modo_filtro == "Calendário (Ano/Mês/Período)":
    anos_disponiveis = sorted(df['ano'].unique(), reverse=True)
    ano_sel = st.sidebar.selectbox("1. Selecione o Ano", anos_disponiveis)
    df_filtrado = df_filtrado[df_filtrado['ano'] == ano_sel]
    
    tipo_periodo = st.sidebar.selectbox("2. Agrupar por:", ["Mês", "Bimestre", "Trimestre", "Semestre", "Ano Completo"])
    
    if tipo_periodo == "Mês":
        meses_ordem = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        meses_disp = [m for m in meses_ordem if m in df_filtrado['mes_nome'].unique()]
        mes_sel = st.sidebar.selectbox("3. Selecione o Mês", meses_disp)
        df_filtrado = df_filtrado[df_filtrado['mes_nome'] == mes_sel]
    elif tipo_periodo == "Bimestre":
        bim_disp = sorted(df_filtrado['bimestre'].unique())
        bim_sel = st.sidebar.selectbox("3. Selecione o Bimestre", [f"{b}º Bimestre" for b in bim_disp])
        df_filtrado = df_filtrado[df_filtrado['bimestre'] == int(bim_sel[0])]
    elif tipo_periodo == "Trimestre":
        tri_disp = sorted(df_filtrado['trimestre'].unique())
        tri_sel = st.sidebar.selectbox("3. Selecione o Trimestre", [f"{t}º Trimestre" for t in tri_disp])
        df_filtrado = df_filtrado[df_filtrado['trimestre'] == int(tri_sel[0])]
    elif tipo_periodo == "Semestre":
        sem_disp = sorted(df_filtrado['semestre'].unique())
        sem_sel = st.sidebar.selectbox("3. Selecione o Semestre", [f"{s}º Semestre" for s in sem_disp])
        df_filtrado = df_filtrado[df_filtrado['semestre'] == int(sem_sel[0])]
else:
    min_d = df['data_apenas'].min()
    max_d = df['data_apenas'].max()
    intervalo = st.sidebar.date_input("Selecione o período", [min_d, max_d], min_value=min_d, max_value=max_d)
    if len(intervalo) == 2:
        df_filtrado = df_filtrado[(df_filtrado['data_apenas'] >= intervalo[0]) & (df_filtrado['data_apenas'] <= intervalo[1])]

# --- Filtros Operacionais ---
st.sidebar.divider()
st.sidebar.markdown("### 📊 Filtros Operacionais")

lista_cat = ["Todas"] + sorted(df['categoria'].unique().tolist())
cat_sel = st.sidebar.selectbox("Categoria", lista_cat)
if cat_sel != "Todas":
    df_filtrado = df_filtrado[df_filtrado['categoria'] == cat_sel]

lista_req = ["Todos"] + sorted(list(set([x.strip() for val in df['requerente_id'].dropna().astype(str) for x in val.split(',')])))
req_sel = st.sidebar.selectbox("Requerente (ID)", lista_req)
if req_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado['requerente_id'].astype(str).str.contains(req_sel, na=False)]

lista_tec = ["Todos"] + sorted(list(set([x.strip() for val in df['tecnico_id'].dropna().astype(str) for x in val.split(',')])))
tec_sel = st.sidebar.selectbox("Técnico (ID)", lista_tec)
if tec_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado['tecnico_id'].astype(str).str.contains(tec_sel, na=False)]

# ==========================================
# 3. VISUALIZAÇÃO (ABAS)
# ==========================================
st.title("🎫 Dashboard GLPI - Análise de Suporte")

tab1, tab2, tab3 = st.tabs(["📋 Visão Detalhada", "📈 Comparativos (MoM/YoY)", "👥 Análise de Equipe"])

# --- ABA 1: VISÃO DETALHADA ---
with tab1:
    col1, col2, col3 = st.columns(3)
    col1.metric("Tickets no Período", len(df_filtrado))
    col2.metric("Categorias", df_filtrado['categoria'].nunique())
    col3.metric("Tickets s/ Categoria", len(df_filtrado[df_filtrado['categoria'] == "Sem categoria"]))
    st.divider()
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Top 10 Categorias")
        df_cat = df_filtrado['categoria'].value_counts().head(10).reset_index()
        df_cat.index = df_cat.index + 1
        df_cat['categoria_lbl'] = df_cat.index.astype(str) + ". " + df_cat['categoria']
        fig1 = px.bar(df_cat, x='count', y='categoria_lbl', orientation='h', labels={'count':'Quantidade', 'categoria_lbl':''})
        fig1.update_yaxes(autorange="reversed")
        st.plotly_chart(fig1, use_container_width=True)
        
    with c2:
        st.subheader("Volume por Dia")
        df_day = df_filtrado.groupby('data_apenas').size().reset_index(name='qtd')
        fig2 = px.line(df_day, x='data_apenas', y='qtd', markers=True, labels={'data_apenas': 'Data', 'qtd': 'Qtd. Chamados'})
        fig2.update_yaxes(tickformat="d")
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Lista de Chamados")
    st.dataframe(df_filtrado[['id', 'titulo', 'categoria', 'data_abertura', 'requerente_id', 'tecnico_id']], use_container_width=True, hide_index=True)

# --- ABA 2: COMPARATIVOS ---
with tab2:
    st.header("Análise de Performance")
    if modo_filtro == "Calendário (Ano/Mês/Período)":
        ano_anterior = ano_sel - 1
        total_ano_atual = len(df[df['ano'] == ano_sel])
        total_ano_ant = len(df[df['ano'] == ano_anterior])
        diff_yoy = total_ano_atual - total_ano_ant
        
        m1, m2 = st.columns(2)
        m1.metric(f"Total em {ano_sel}", total_ano_atual, delta=f"{diff_yoy} vs {ano_anterior}", delta_color="inverse")
        
        st.subheader("Comparativo Mensal: Este Ano vs. Ano Passado")
        comp_df = df[df['ano'].isin([ano_sel, ano_anterior])]
        df_comp = comp_df.groupby(['mes_num', 'ano']).size().reset_index(name='chamados')
        fig_comp = px.line(df_comp, x='mes_num', y='chamados', color='ano', markers=True, labels={'mes_num': 'Mês (Número)', 'chamados': 'Qtd Chamados', 'ano': 'Ano'})
        fig_comp.update_xaxes(tickmode='linear', tick0=1, dtick=1)
        st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.warning("Selecione o modo 'Calendário' na barra lateral e escolha um Ano para ver as análises comparativas.")

# --- ABA 3: ANÁLISE DE EQUIPE ---
with tab3:
    st.header("Análise de Requerentes e Técnicos")
    
    # "Explodindo" as listas de IDs para separar os chamados múltiplos
    df_tec_exp = df_filtrado.copy()
    df_tec_exp['tecnico_id'] = df_tec_exp['tecnico_id'].astype(str).str.split(',')
    df_tec_exp = df_tec_exp.explode('tecnico_id')
    df_tec_exp['tecnico_id'] = df_tec_exp['tecnico_id'].str.strip()
    df_tec_exp = df_tec_exp[~df_tec_exp['tecnico_id'].isin(['nan', 'None', ''])]
    
    df_req_exp = df_filtrado.copy()
    df_req_exp['requerente_id'] = df_req_exp['requerente_id'].astype(str).str.split(',')
    df_req_exp = df_req_exp.explode('requerente_id')
    df_req_exp['requerente_id'] = df_req_exp['requerente_id'].str.strip()
    df_req_exp = df_req_exp[~df_req_exp['requerente_id'].isin(['nan', 'None', ''])]

    # --- Ranking Geral (Gráficos de Barras Retomados) ---
    c_tec, c_req = st.columns(2)
    with c_tec:
        st.subheader("Top Técnicos (Volume)")
        if not df_tec_exp.empty:
            df_tec_counts = df_tec_exp['tecnico_id'].value_counts().head(10).reset_index()
            fig_tec = px.bar(df_tec_counts, x='count', y='tecnico_id', orientation='h', labels={'count':'Chamados Atendidos', 'tecnico_id':'ID do Técnico'})
            fig_tec.update_yaxes(autorange="reversed", type='category')
            st.plotly_chart(fig_tec, use_container_width=True)
        else:
            st.info("Sem dados de técnicos.")
            
    with c_req:
        st.subheader("Top Requerentes (Volume)")
        if not df_req_exp.empty:
            df_req_counts = df_req_exp['requerente_id'].value_counts().head(10).reset_index()
            fig_req = px.bar(df_req_counts, x='count', y='requerente_id', orientation='h', labels={'count':'Chamados Abertos', 'requerente_id':'ID do Requerente'})
            fig_req.update_yaxes(autorange="reversed", type='category')
            st.plotly_chart(fig_req, use_container_width=True)
        else:
            st.info("Sem dados de requerentes.")

    st.divider()

    # --- Detalhamento Individual (Gráficos de Pizza - Top 3) ---
    st.markdown("### 🔍 Perfil de Categorias por Indivíduo (Top 3)")
    c_det_tec, c_det_req = st.columns(2)
    
    with c_det_tec:
        st.markdown("**Selecione um Técnico:**")
        lista_ids_tec = sorted(df_tec_exp['tecnico_id'].unique())
        if lista_ids_tec:
            tec_especifico = st.selectbox("ID Técnico", lista_ids_tec, label_visibility="collapsed")
            # Filtra os dados apenas para o técnico selecionado e pega as top 3 categorias
            df_tec_ind = df_tec_exp[df_tec_exp['tecnico_id'] == tec_especifico]
            top3_cat_tec = df_tec_ind['categoria'].value_counts().head(3).reset_index()
            
            fig_pie_tec = px.pie(top3_cat_tec, values='count', names='categoria', hole=0.3, title=f"Top 3 Categorias - Téc. {tec_especifico}")
            fig_pie_tec.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie_tec, use_container_width=True)
            
    with c_det_req:
        st.markdown("**Selecione um Requerente:**")
        lista_ids_req = sorted(df_req_exp['requerente_id'].unique())
        if lista_ids_req:
            req_especifico = st.selectbox("ID Requerente", lista_ids_req, label_visibility="collapsed")
            # Filtra os dados apenas para o requerente selecionado e pega as top 3 categorias
            df_req_ind = df_req_exp[df_req_exp['requerente_id'] == req_especifico]
            top3_cat_req = df_req_ind['categoria'].value_counts().head(3).reset_index()
            
            fig_pie_req = px.pie(top3_cat_req, values='count', names='categoria', hole=0.3, title=f"Top 3 Categorias - Req. {req_especifico}")
            fig_pie_req.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie_req, use_container_width=True)