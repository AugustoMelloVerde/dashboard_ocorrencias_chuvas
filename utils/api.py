import requests
import pandas as pd
import streamlit as st
from datetime import datetime
from config import API_URL


# ✅ MAPEAMENTO DE PRIORIDADES
MAPA_PRIORIDADES = {
    '4': 'BAIXO',
    '3': 'MÉDIA',
    '2': 'ALTA',
    '1': 'MUITO ALTA',
    4: 'BAIXO',
    3: 'MÉDIA',
    2: 'ALTA',
    1: 'MUITO ALTA'
}


# ✅ FUNÇÃO PARA EXTRAIR BAIRRO
def extrair_bairro(location):
    """
    Extrai o bairro do campo location
    
    Estrutura esperada: "Rua, Bairro, Rio de Janeiro - RJ, CEP, Brasil"
    Exemplo: "Rua do Fialho, Glória, Rio de Janeiro - RJ, 20241-160, Brasil"
    
    Retorna: "Glória"
    """
    if pd.isna(location) or location == "":
        return "N/A"
    
    try:
        location_str = str(location).strip()
        
        # Dividir por vírgulas
        partes = [p.strip() for p in location_str.split(",")]
        
        # Se houver pelo menos 3 partes, o bairro está na segunda posição
        # Estrutura: [Rua, Bairro, Rio de Janeiro - RJ, CEP, Brasil]
        if len(partes) >= 3:
            # O bairro está na posição 1 (segunda posição)
            bairro = partes.strip()
            
            # Validar se realmente é um bairro (não contém "Rio de Janeiro" ou "RJ")
            if "Rio de Janeiro" not in bairro and "RJ" not in bairro:
                return bairro if bairro else "N/A"
        
        # Se tiver menos de 3 partes, retornar N/A
        return "N/A"
            
    except Exception as e:
        print(f"Erro ao extrair bairro: {e}")
        return "N/A"


@st.cache_data(ttl=30, show_spinner=False)
def buscar_dados_api():
    """Conecta à API e retorna os dados em tempo real"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"❌ Erro na API: {str(e)}")
        return None



def processar_dados(dados_brutos):
    """Converte dados JSON da API em DataFrame e padroniza colunas"""
    if dados_brutos is None:
        return pd.DataFrame()
    
    try:
        # Converter para DataFrame
        if isinstance(dados_brutos, dict):
            if 'data' in dados_brutos:
                dados_lista = dados_brutos['data']
            elif 'ocorrencias' in dados_brutos:
                dados_lista = dados_brutos['ocorrencias']
            else:
                dados_lista = [dados_brutos]
        else:
            dados_lista = dados_brutos
        
        df = pd.DataFrame(dados_lista)
        
        # Padronizar nomes de colunas (converter para minúsculas)
        df.columns = df.columns.str.lower()
        
        # ✅ CORRIGIR NOMES DE COLUNAS PARA MATCH COM A API
        # Renomear 'priority' para 'prioridade' (se existir)
        if 'priority' in df.columns and 'prioridade' not in df.columns:
            df.rename(columns={'priority': 'prioridade'}, inplace=True)
        
        # Renomear 'agencyeventtypecode' para 'pop' (POPs)
        if 'agencyeventtypecode' in df.columns and 'pop' not in df.columns:
            df.rename(columns={'agencyeventtypecode': 'pop'}, inplace=True)
        
        # ✅ EXTRAIR BAIRRO DO CAMPO LOCATION (se não existir ou estiver vazio)
        if 'location' in df.columns:
            # Se bairro não existe ou está vazio, extrair de location
            if 'bairro' not in df.columns or df['bairro'].isna().all():
                df['bairro'] = df['location'].apply(extrair_bairro)
            else:
                # Se existe mas tem valores vazios, preencher com dados de location
                mask_vazio = df['bairro'].isna() | (df['bairro'] == '') | (df['bairro'] == 'nan')
                df.loc[mask_vazio, 'bairro'] = df.loc[mask_vazio, 'location'].apply(extrair_bairro)
        
        # Garantir que existem as colunas necessárias
        colunas_necessarias = ['latitude', 'longitude', 'prioridade', 'bairro', 'pop']
        for col in colunas_necessarias:
            if col not in df.columns:
                # Adicionar coluna vazia se não existir
                df[col] = 'N/A'
        
        # Converter para tipos de dados apropriados
        if 'latitude' in df.columns:
            df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        if 'longitude' in df.columns:
            df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
        
        # ✅ MAPEAR PRIORIDADE: CONVERTER NÚMEROS PARA TEXTO
        if 'prioridade' in df.columns:
            # Primeiro converter para string
            df['prioridade'] = df['prioridade'].astype(str).str.strip()
            
            # Depois mapear usando o dicionário
            df['prioridade'] = df['prioridade'].map(MAPA_PRIORIDADES)
            
            # Se não encontrou no mapa, manter original em maiúscula
            df['prioridade'] = df['prioridade'].fillna(
                df['prioridade'].astype(str).str.upper()
            )
            
            # Substituir valores não encontrados por N/A
            df['prioridade'] = df['prioridade'].replace(['NAN', 'NONE'], 'N/A')
        
        # ✅ CONVERTER BAIRRO PARA STRING
        if 'bairro' in df.columns:
            df['bairro'] = df['bairro'].astype(str).str.strip()
            df['bairro'] = df['bairro'].replace('nan', 'N/A')
        
        # ✅ CONVERTER POP PARA STRING
        if 'pop' in df.columns:
            df['pop'] = df['pop'].astype(str).str.strip()
            df['pop'] = df['pop'].replace('nan', 'N/A')
        
        # Remover linhas com dados inválidos de lat/lon
        df = df.dropna(subset=['latitude', 'longitude'])
        
        return df
        
    except Exception as e:
        st.error(f"❌ Erro ao processar: {str(e)}")
        print(f"Erro detalhado: {e}")  # Para debug no console
        return pd.DataFrame()



def obter_filtros_unicos(df):
    """Extrai valores únicos para filtros"""
    if df.empty:
        return {
            'prioridades': [],
            'bairros': [],
            'pops': []
        }
    
    # ✅ EXTRAIR VALORES ÚNICOS PARA OS FILTROS
    # Converter para string e remover 'N/A' dos filtros
    prioridades = sorted([p for p in df['prioridade'].unique() if p != 'N/A' and str(p) != 'nan']) if 'prioridade' in df.columns else []
    bairros = sorted([b for b in df['bairro'].unique() if b != 'N/A' and str(b) != 'nan']) if 'bairro' in df.columns else []
    pops = sorted([p for p in df['pop'].unique() if p != 'N/A' and str(p) != 'nan']) if 'pop' in df.columns else []
    
    return {
        'prioridades': prioridades,
        'bairros': bairros,
        'pops': pops
    }
