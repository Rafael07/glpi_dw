import os
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
from dotenv import load_dotenv

# Configuração da página
st.set_page_config(page_title="Dashboard GLPI - SECTIES", page_icon="🎫", layout="wide")

load_dotenv()
DB_URL = "postgresql://admin:admin123@localhost:5432/dw_glpi"

# ==========================================
# 1. CARGA DE DADOS (CAMADA SILVER)
# ==========================================
@st.cache_data(ttl=600)
def load_data():
    engine = create_engine(DB_URL)
    
    # Lendo as tabelas modeladas
    df_tickets = pd.read_sql_table("silver_tickets", engine)
    df_tec = pd.read_sql_table("silver_ticket_tecnicos", engine)
    df_req = pd.read_sql_table("silver_ticket_requerentes", engine)
    
    # Tratamento de datas na Fato principal
    df_tickets['data_abertura'] = pd.to_datetime(df_tickets['data_abertura'])
    df_tickets['ano'] = df_tickets['data_abertura'].dt.year
    df_tickets['mes_num'] = df_tickets['data_abertura'].dt.month
    df_tickets['data_apenas'] = df_tickets['data_abertura'].dt.date
    
    df_tickets['bimestre'] = (df_tickets['mes_num'] - 1) // 2 + 1
    df_tickets['trimestre'] = df_tickets['data_abertura'].dt.quarter
    df_tickets['semestre'] = (df_tickets['mes_num'] - 1) // 6 + 1
    
    df_tickets['mes_nome'] = df_tickets['mes_num'].map({
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
        7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    })
    
    return df_tickets, df_tec, df_req

df_tickets, df_tec, df_req = load_data()

# ==========================================
# 2. BARRA LATERAL - CONTROLE DE FILTROS
# ==========================================
st.sidebar.title("🎮 Controles do Dashboard")

modo_filtro = st.sidebar.radio("Escolha o modo de filtragem:", ["Calendário (Ano/Mês/Período)", "Intervalo Livre (De-Até)"], index=0)

st.sidebar.divider()
df_filtrado = df_tickets.copy()

# --- Filtros de Tempo ---
if modo_filtro == "Calendário (Ano/Mês/Período)":
    anos_disponiveis = sorted(df_tickets['ano'].unique(), reverse=True)
    ano_sel = st.sidebar.selectbox("1. Selecione o Ano", anos_disponiveis)
    df_filtrado = df_filtrado[df_filtrado['ano'] == ano_sel]
    
    tipo_periodo = st.sidebar.selectbox("2. Agrupar por:", ["Mês", "Bimestre", "Trimestre", "Semestre", "Ano Completo"])
    
    if tipo_periodo == "Mês":
        meses_ordem = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        meses_disp = [m for m in meses_ordem if m in df_filtrado['mes_nome'].unique()]
        if meses_disp:
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
    min_d = df_tickets['data_apenas'].min()
    max_d = df_tickets['data_apenas'].max()
    intervalo = st.sidebar.date_input("Selecione o período", [min_d, max_d], min_value=min_d, max_value=max_d)
    if len(intervalo) == 2:
        df_filtrado = df_filtrado[(df_filtrado['data_apenas'] >= intervalo[0]) & (df_filtrado['data_apenas'] <= intervalo[1])]

# --- Filtros Operacionais ---
st.sidebar.divider()
st.sidebar.markdown("### 📊 Filtros Operacionais")

lista_cat = ["Todas"] + sorted(df_tickets['categoria'].unique().tolist())
cat_sel = st.sidebar.selectbox("Categoria", lista_cat)
if cat_sel != "Todas":
    df_filtrado = df_filtrado[df_filtrado['categoria'] == cat_sel]

# Sincronizando os dados de Técnicos e Requerentes com os filtros aplicados
tickets_filtrados_ids = df_filtrado['id'].tolist()
df_tec_filtrado = df_tec[df_tec['ticket_id'].isin(tickets_filtrados_ids)]
df_req_filtrado = df_req[df_req['ticket_id'].isin(tickets_filtrados_ids)]

lista_req = ["Todos"] + sorted(df_req_filtrado['requerente_nome'].unique().tolist())
req_sel = st.sidebar.selectbox("Requerente", lista_req)
if req_sel != "Todos":
    # Se escolher um requerente, filtra as tabelas novamente
    tickets_do_req = df_req_filtrado[df_req_filtrado['requerente_nome'] == req_sel]['ticket_id']
    df_filtrado = df_filtrado[df_filtrado['id'].isin(tickets_do_req)]
    tickets_filtrados_ids = df_filtrado['id'].tolist()
    df_tec_filtrado = df_tec_filtrado[df_tec_filtrado['ticket_id'].isin(tickets_filtrados_ids)]
    df_req_filtrado = df_req_filtrado[df_req_filtrado['ticket_id'].isin(tickets_filtrados_ids)]

lista_tec = ["Todos"] + sorted(df_tec_filtrado['tecnico_nome'].unique().tolist())
tec_sel = st.sidebar.selectbox("Técnico", lista_tec)
if tec_sel != "Todos":
    tickets_do_tec = df_tec_filtrado[df_tec_filtrado['tecnico_nome'] == tec_sel]['ticket_id']
    df_filtrado = df_filtrado[df_filtrado['id'].isin(tickets_do_tec)]
    tickets_filtrados_ids = df_filtrado['id'].tolist()
    df_tec_filtrado = df_tec_filtrado[df_tec_filtrado['ticket_id'].isin(tickets_filtrados_ids)]
    df_req_filtrado = df_req_filtrado[df_req_filtrado['ticket_id'].isin(tickets_filtrados_ids)]

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
        if not df_filtrado.empty:
            df_cat = df_filtrado['categoria'].value_counts().head(10).reset_index()
            df_cat.index = df_cat.index + 1
            df_cat['categoria_lbl'] = df_cat.index.astype(str) + ". " + df_cat['categoria']
            fig1 = px.bar(df_cat, x='count', y='categoria_lbl', orientation='h', labels={'count':'Quantidade', 'categoria_lbl':''})
            fig1.update_yaxes(autorange="reversed")
            st.plotly_chart(fig1, width='stretch')
        
    with c2:
        st.subheader("Volume por Dia")
        if not df_filtrado.empty:
            df_day = df_filtrado.groupby('data_apenas').size().reset_index(name='qtd')
            fig2 = px.line(df_day, x='data_apenas', y='qtd', markers=True, labels={'data_apenas': 'Data', 'qtd': 'Qtd. Chamados'})
            fig2.update_yaxes(tickformat="d")
            st.plotly_chart(fig2, width='stretch')

    st.subheader("Lista de Chamados")
    # Agora a lista de chamados vai exibir os NOMES limpinhos gerados pela Silver!
    st.dataframe(df_filtrado[['id', 'titulo', 'categoria', 'data_abertura', 'requerentes', 'tecnicos']], width='stretch', hide_index=True)

# --- ABA 2: COMPARATIVOS ---
with tab2:
    st.header("Análise de Performance")
    if modo_filtro == "Calendário (Ano/Mês/Período)":
        ano_anterior = ano_sel - 1
        total_ano_atual = len(df_tickets[df_tickets['ano'] == ano_sel])
        total_ano_ant = len(df_tickets[df_tickets['ano'] == ano_anterior])
        diff_yoy = total_ano_atual - total_ano_ant
        
        m1, m2 = st.columns(2)
        m1.metric(f"Total em {ano_sel}", total_ano_atual, delta=f"{diff_yoy} vs {ano_anterior}", delta_color="inverse")
        
        st.subheader("Comparativo Mensal: Este Ano vs. Ano Passado")
        comp_df = df_tickets[df_tickets['ano'].isin([ano_sel, ano_anterior])]
        df_comp = comp_df.groupby(['mes_num', 'ano']).size().reset_index(name='chamados')
        if not df_comp.empty:
            fig_comp = px.line(df_comp, x='mes_num', y='chamados', color='ano', markers=True, labels={'mes_num': 'Mês (Número)', 'chamados': 'Qtd Chamados', 'ano': 'Ano'})
            fig_comp.update_xaxes(tickmode='linear', tick0=1, dtick=1)
            st.plotly_chart(fig_comp, width='stretch')
    else:
        st.warning("Selecione o modo 'Calendário' na barra lateral e escolha um Ano para ver as análises comparativas.")

# --- ABA 3: ANÁLISE DE EQUIPE ---
with tab3:
    st.header("Análise de Requerentes e Técnicos")
    
    # Para o Top 3 por Categoria, precisamos fazer um JOIN com a tabela filtrada para trazer o nome da categoria
    df_tec_completo = pd.merge(df_tec_filtrado, df_filtrado[['id', 'categoria']], left_on='ticket_id', right_on='id', how='left')
    df_req_completo = pd.merge(df_req_filtrado, df_filtrado[['id', 'categoria']], left_on='ticket_id', right_on='id', how='left')

    # --- Ranking Geral (Barras) ---
    c_tec, c_req = st.columns(2)
    with c_tec:
        st.subheader("Top Técnicos (Volume)")
        if not df_tec_filtrado.empty:
            df_tec_counts = df_tec_filtrado['tecnico_nome'].value_counts().head(10).reset_index()
            fig_tec = px.bar(df_tec_counts, x='count', y='tecnico_nome', orientation='h', labels={'count':'Chamados', 'tecnico_nome':'Técnico'})
            fig_tec.update_yaxes(autorange="reversed", type='category')
            st.plotly_chart(fig_tec, width='stretch')
        else:
            st.info("Sem dados.")
            
    with c_req:
        st.subheader("Top Requerentes (Volume)")
        if not df_req_filtrado.empty:
            df_req_counts = df_req_filtrado['requerente_nome'].value_counts().head(10).reset_index()
            fig_req = px.bar(df_req_counts, x='count', y='requerente_nome', orientation='h', labels={'count':'Chamados', 'requerente_nome':'Requerente'})
            fig_req.update_yaxes(autorange="reversed", type='category')
            st.plotly_chart(fig_req, width='stretch')
        else:
            st.info("Sem dados.")

    st.divider()

    # --- Detalhamento Individual (Pizza - Top 3) ---
    st.markdown("### 🔍 Perfil de Categorias por Indivíduo (Top 3)")
    c_det_tec, c_det_req = st.columns(2)
    
    with c_det_tec:
        st.markdown("**Selecione um Técnico:**")
        lista_nomes_tec = sorted(df_tec_completo['tecnico_nome'].unique()) if not df_tec_completo.empty else []
        if lista_nomes_tec:
            tec_especifico = st.selectbox("Nome Técnico", lista_nomes_tec, label_visibility="collapsed")
            df_tec_ind = df_tec_completo[df_tec_completo['tecnico_nome'] == tec_especifico]
            top3_cat_tec = df_tec_ind['categoria'].value_counts().head(3).reset_index()
            
            fig_pie_tec = px.pie(top3_cat_tec, values='count', names='categoria', hole=0.3, title=f"Top 3 - {tec_especifico}")
            fig_pie_tec.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie_tec, width='stretch')
            
    with c_det_req:
        st.markdown("**Selecione um Requerente:**")
        lista_nomes_req = sorted(df_req_completo['requerente_nome'].unique()) if not df_req_completo.empty else []
        if lista_nomes_req:
            req_especifico = st.selectbox("Nome Requerente", lista_nomes_req, label_visibility="collapsed")
            df_req_ind = df_req_completo[df_req_completo['requerente_nome'] == req_especifico]
            top3_cat_req = df_req_ind['categoria'].value_counts().head(3).reset_index()
            
            fig_pie_req = px.pie(top3_cat_req, values='count', names='categoria', hole=0.3, title=f"Top 3 - {req_especifico}")
            fig_pie_req.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie_req, width='stretch')