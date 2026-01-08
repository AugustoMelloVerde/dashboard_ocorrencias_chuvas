import streamlit as st
import pandas as pd
from datetime import datetime
from utils.api import buscar_dados_api, processar_dados, obter_filtros_unicos
from utils.visualizacoes import criar_grafico_barras, criar_mapa_folium, criar_mapa_calor
from config import TEMPO_ATUALIZACAO, TIPOS_MAPA, LISTA_POPS, POPS_DEFAULT

st.set_page_config(
    page_title="Dashboard Ocorrências",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main { padding: 1rem; }
    [data-testid="stSidebar"] { background-color: #f0f2f6; }
    .metric-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    @media (max-width: 640px) {
        .main { padding: 0.5rem; }
    }
    </style>
""", unsafe_allow_html=True)

if 'ultima_atualizacao' not in st.session_state:
    st.session_state.ultima_atualizacao = None
if 'contador_atualizacoes' not in st.session_state:
    st.session_state.contador_atualizacoes = 0

col1, col2 = st.columns([1, 1])
with col1:
    st.title("🚨 Ocorrências de Chuvas - Conservação")
    st.markdown("**Sistema de Monitoramento em Tempo Real**")

# ============= SIDEBAR =============
# ✅ ESPAÇO PARA LOGO (opcional)
st.sidebar.markdown("---")
# st.sidebar.write("📋 **LOGO DA SUA ORGANIZAÇÃO AQUI**")
# Se quiser adicionar uma imagem, descomente:
st.sidebar.image("logo.png", width=200)
st.sidebar.markdown("---")

st.sidebar.title("⚙️ Filtros")

with st.spinner("Carregando dados da API..."):
    dados_brutos = buscar_dados_api()

df = processar_dados(dados_brutos)
st.session_state.contador_atualizacoes += 1
st.session_state.ultima_atualizacao = datetime.now()

filtros = obter_filtros_unicos(df)

# ✅ FILTROS SEM SELEÇÃO DEFAULT (vazio por padrão)
prioridades_selecionadas = st.sidebar.multiselect(
    "🎯 Prioridades",
    options=filtros['prioridades'],
    default=[]
)

bairros_selecionados = st.sidebar.multiselect(
    "📍 Bairros",
    options=filtros['bairros'],
    default=[]
)

# ✅ POPs FIXA - COM LISTA COMPLETA SEMPRE VISÍVEL
# Extrair apenas os códigos dos POPs (POP01, POP02, etc)
pops_codigos = [pop.split(":")[0].strip() for pop in LISTA_POPS]

# Combinar com dados da API (se houver novos POPs)
if filtros['pops'] and len(filtros['pops']) > 0:
    pops_disponiveis = sorted(list(set(pops_codigos + filtros['pops'])))
else:
    pops_disponiveis = pops_codigos

pops_selecionados = st.sidebar.multiselect(
    "🏢 POPs",
    options=pops_disponiveis,
    default=POPS_DEFAULT
)

tipo_mapa = st.sidebar.radio("🗺️ Tipo de Mapa", TIPOS_MAPA, index=0)

st.sidebar.markdown("---")

# ✅ BOTÃO DE ATUALIZAR NA SIDEBAR
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("🔄 Atualizar Agora", use_container_width=True, key="btn_atualizar"):
        st.rerun()

with col2:
    st.metric("Atualizações", st.session_state.contador_atualizacoes)

# Informações de atualização
with st.sidebar:
    st.metric("Intervalo", f"{TEMPO_ATUALIZACAO}s")
    
    if st.session_state.ultima_atualizacao:
        hora = st.session_state.ultima_atualizacao.strftime("%H:%M:%S")
        st.caption(f"⏰ Última atualização: {hora}")

# ============= APLICAR FILTROS =============
df_filtrado = df.copy()

# ✅ SÓ FILTRA SE HOUVER SELEÇÃO
if prioridades_selecionadas and 'prioridade' in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado['prioridade'].isin([p.upper() for p in prioridades_selecionadas])]

if bairros_selecionados and 'bairro' in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado['bairro'].isin(bairros_selecionados)]

if pops_selecionados and 'pop' in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado['pop'].isin([str(p) for p in pops_selecionados])]

# ============= MÉTRICAS =============
st.markdown("### 📊 Ocorrências")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total de Ocorrências", len(df_filtrado))

with col2:
    if 'prioridade' in df_filtrado.columns:
        alta_critica = len(df_filtrado[df_filtrado['prioridade'].isin(['ALTA', 'CRÍTICA', 'MUITO ALTA'])])
        st.metric("Alta/Crítica", alta_critica)

#with col3:
#    bairros_unicos = df_filtrado['bairro'].nunique() if 'bairro' in df_filtrado.columns else 0
#    st.metric("Bairros Afetados", bairros_unicos)



# ============= MAPAS =============
st.markdown("### 🗺️ Georreferenciamento")

tab1, tab2 = st.tabs(["📍 Mapa de Pontos", "🔥 Mapa de Calor"])

with tab1:
    if not df_filtrado.empty:
        mapa_pontos = criar_mapa_folium(df_filtrado, tipo_mapa)
        st.components.v1.html(mapa_pontos._repr_html_(), height=500)
    else:
        st.warning("Sem dados para exibir no mapa")

with tab2:
    if not df_filtrado.empty:
        mapa_calor = criar_mapa_calor(df_filtrado, tipo_mapa)
        st.components.v1.html(mapa_calor._repr_html_(), height=500)
    else:
        st.warning("Sem dados para exibir no mapa")

# ============= TABELA =============
st.markdown("### 📋 Dados Detalhados")

if not df_filtrado.empty:
    colunas_exibicao = [col for col in df_filtrado.columns if col not in ['id', 'geometry']]
    df_exibicao = df_filtrado[colunas_exibicao].head(50)
    st.dataframe(df_exibicao, use_container_width=True, height=400)
else:
    st.warning("Nenhum dado disponível com os filtros selecionados")


# ============= GRÁFICOS =============
st.markdown("### 📈 Análises")

col1, col2 = st.columns(2)

with col1:
    st.subheader("")
    if not df_filtrado.empty and 'prioridade' in df_filtrado.columns:
        contagem_prioridade = df_filtrado['prioridade'].value_counts()
        
        if not contagem_prioridade.empty:
            fig_prioridade = criar_grafico_barras(df_filtrado, 'prioridade')
            st.plotly_chart(fig_prioridade, use_container_width=True)
        else:
            st.info("Nenhuma ocorrência com dados de prioridade")
    else:
        st.warning("Sem dados para exibir")

#with col2:
#    st.subheader("")
#    if not df_filtrado.empty and 'bairro' in df_filtrado.columns:
#        contagem_bairro = df_filtrado['bairro'].value_counts()
#        
#        if not contagem_bairro.empty:
#            fig_bairro = criar_grafico_barras(df_filtrado, 'bairro')
#            st.plotly_chart(fig_bairro, use_container_width=True)
#        else:
#            st.info("Nenhuma ocorrência com dados de bairro")
#    else:
#        st.warning("Sem dados para exibir") 



# ============= RODAPÉ =============
st.markdown("---")

col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    st.caption(f"📡 API: {len(df)} ocorrências carregadas")

with col3:
    st.caption("Desenvolvido por EGDPI - Conservação")

# Auto-refresh a cada TEMPO_ATUALIZACAO segundos
st.markdown(f"""
    <script>
    setTimeout(function() {{
        window.location.reload();
    }}, {TEMPO_ATUALIZACAO * 1000});
    </script>
""", unsafe_allow_html=True)
