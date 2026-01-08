import pandas as pd
import plotly.graph_objects as go
import folium
from folium.plugins import MarkerCluster, HeatMap
import streamlit as st
from config import COR_PRIORIDADE, CENTRO_MAPA, ZOOM_PADRAO

def criar_grafico_barras(df, coluna_grupo='prioridade'):
    """Cria gráfico de barras horizontais"""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Sem dados")
        return fig
    
    contagem = df[coluna_grupo].value_counts().sort_values(ascending=True)
    
    cores = []
    if coluna_grupo == 'prioridade':
        cores = [COR_PRIORIDADE.get(cat, '#666') for cat in contagem.index]
    
    fig = go.Figure(data=[
        go.Bar(
            y=contagem.index,
            x=contagem.values,
            orientation='h',
            marker=dict(color=cores if cores else '#1f77b4'),
            text=contagem.values,
            textposition='outside'
        )
    ])
    
    fig.update_layout(
        title=f'Ocorrências por {coluna_grupo.capitalize()}',
        xaxis_title='Quantidade',
        yaxis_title=coluna_grupo.capitalize(),
        height=400,
        template='plotly_white',
        showlegend=False
    )
    
    return fig


def criar_mapa_folium(df, tipo_mapa='OpenStreetMap'):
    """Cria mapa interativo com Folium - VERSÃO COM CENTRALIZAÇÃO AUTOMÁTICA"""
    if df.empty:
        return folium.Map(
            location=CENTRO_MAPA,
            zoom_start=ZOOM_PADRAO,
            tiles='OpenStreetMap'
        )
    
    # ✅ CENTRALIZAR NO CENTRO DAS OCORRÊNCIAS
    centro_lat = df['latitude'].mean()
    centro_lon = df['longitude'].mean()
    
    # Calcular zoom automático baseado na dispersão dos dados
    lat_range = df['latitude'].max() - df['latitude'].min()
    lon_range = df['longitude'].max() - df['longitude'].min()
    max_range = max(lat_range, lon_range)
    
    # Ajustar zoom automaticamente
    if max_range > 0.5:
        zoom = 12
    elif max_range > 0.2:
        zoom = 13
    elif max_range > 0.1:
        zoom = 14
    else:
        zoom = 15
    
    # Mapear tipos de mapa corretamente
    mapa_tiles = {
        'OpenStreetMap': 'OpenStreetMap',
        'Stamen Terrain': 'https://tile.opentopomap.org/tiles/opentopomap/{z}/{x}/{y}.png',
        'Stamen Toner': 'https://tiles.stadiamaps.com/tiles/stamen_toner/{z}/{x}/{y}.png',
        'CartoDB Positron': 'CartoDB positron',
        'CartoDB Voyager': 'CartoDB voyager'
    }
    
    # Usar o tipo selecionado ou padrão
    tile_url = mapa_tiles.get(tipo_mapa, 'OpenStreetMap')
    
    # Criar mapa
    if tipo_mapa in ['Stamen Terrain', 'Stamen Toner']:
        mapa = folium.Map(
            location=[centro_lat, centro_lon],
            zoom_start=zoom,
            tiles=tile_url,
            attr='Map tiles by Stadia Maps, Data by OpenStreetMap contributors'
        )
    else:
        mapa = folium.Map(
            location=[centro_lat, centro_lon],
            zoom_start=zoom,
            tiles=tile_url
        )
    
    # Adicionar marcadores com cluster
    marker_cluster = MarkerCluster().add_to(mapa)
    
    # Cores por prioridade
    cores_prioridade = {
        'BAIXO': 'green',
        'MÉDIA': 'orange',
        'ALTA': 'red',
        'MUITO ALTA': 'darkred'
    }
    
    # Adicionar pontos ao mapa
    for idx, row in df.iterrows():
        if pd.notna(row['latitude']) and pd.notna(row['longitude']):
            
            # Determinar cor do marcador
            cor = cores_prioridade.get(str(row.get('prioridade', 'BAIXO')).upper(), 'blue')
            
            # Criar popup com informações
            popup_text = f"""
            <b>Endereço:</b> {row.get('location', 'N/A')}<br>
            <b>Prioridade:</b> {row.get('prioridade', 'N/A')}<br>
            <b>POP:</b> {row.get('pop', 'N/A')}<br>
            <b>Lat/Lon:</b> {row['latitude']:.4f}, {row['longitude']:.4f}
            """
            
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=8,
                popup=folium.Popup(popup_text, max_width=250),
                color=cor,
                fill=True,
                fillColor=cor,
                fillOpacity=0.7,
                weight=2
            ).add_to(mapa)
    
    return mapa


def criar_mapa_calor(df, tipo_mapa='OpenStreetMap'):
    """Cria mapa de calor (HeatMap) - COM CENTRALIZAÇÃO AUTOMÁTICA"""
    if df.empty:
        return folium.Map(
            location=CENTRO_MAPA,
            zoom_start=ZOOM_PADRAO,
            tiles='OpenStreetMap'
        )
    
    # ✅ CENTRALIZAR NO CENTRO DAS OCORRÊNCIAS
    centro_lat = df['latitude'].mean()
    centro_lon = df['longitude'].mean()
    
    # Calcular zoom automático baseado na dispersão dos dados
    lat_range = df['latitude'].max() - df['latitude'].min()
    lon_range = df['longitude'].max() - df['longitude'].min()
    max_range = max(lat_range, lon_range)
    
    # Ajustar zoom automaticamente
    if max_range > 0.5:
        zoom = 12
    elif max_range > 0.2:
        zoom = 13
    elif max_range > 0.1:
        zoom = 14
    else:
        zoom = 15
    
    # ✅ MAPEAR TIPOS DE MAPA (STAMEN REMOVIDO, MAPBOX ADICIONADO)
    from config import MAPBOX_TOKEN

    mapa_tiles = {
    'OpenStreetMap': 'OpenStreetMap',
    'CartoDB Positron': 'CartoDB positron',
    'CartoDB Voyager': 'CartoDB voyager',
    'MapBox Standard Day': 'https://api.mapbox.com/styles/v1/mapbox/streets-v11/static/{z}/{x}/{y}@2x',
    'MapBox Standard Night': 'https://api.mapbox.com/styles/v1/mapbox/dark-v10/static/{z}/{x}/{y}@2x',
    'MapBox Satellite': 'https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/{z}/{x}/{y}@2x'
    }

    
    # Usar o tipo selecionado ou padrão
    tile_url = mapa_tiles.get(tipo_mapa, 'OpenStreetMap')
    
    # ✅ CRIAR MAPA COM SUPORTE A MAPBOX
    tile_url = mapa_tiles.get(tipo_mapa, 'OpenStreetMap')

    # Para MapBox, adicionar token se disponível
    if 'mapbox.com' in str(tile_url).lower() and MAPBOX_TOKEN:
        tile_url = tile_url.replace('http', 'https')
    if '?' not in tile_url:
        tile_url += f'?access_token={MAPBOX_TOKEN}'

    # Criar mapa
    mapa = folium.Map(
        location=[centro_lat, centro_lon],
        zoom_start=zoom,
        tiles=tile_url if not 'mapbox.com' in str(tile_url).lower() else 'OpenStreetMap',
        attr='© OpenStreetMap contributors'
    )

    # Se for MapBox, adicionar como TileLayer com token
    if 'mapbox.com' in str(tile_url).lower() and MAPBOX_TOKEN:
        folium.TileLayer(
        tiles=tile_url,
        attr='© Mapbox © OpenStreetMap',
        name=tipo_mapa
    ).add_to(mapa)

    
    # Preparar dados para HeatMap
    dados_calor = df[['latitude', 'longitude']].values.tolist()
    
    # Adicionar HeatMap
    HeatMap(dados_calor, radius=20, blur=15, max_zoom=1).add_to(mapa)
    
    return mapa
