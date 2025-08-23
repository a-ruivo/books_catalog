import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import plotly.graph_objects as go
from PIL import Image
import os
import unicodedata
from requests.utils import quote

from config import CSV_PATH, REPO, GITHUB_TOKEN, TTL

def adicionar_preco_medio(df, nova_coluna="preco_medio"):
    def buscar_preco(title, year, publisher):
        # Garantir que os valores são strings
        titulo_formatado = quote(str(title).lower())
        publisher_formatado = quote(str(publisher).lower().replace(" ", "-"))
        year_formatado = quote(str(year))

        url2 = (
            f"https://www.estantevirtual.com.br/busca?q={titulo_formatado}&searchField=titulo-autor&editora={publisher_formatado}"
        )

        url3 = (
            f"https://www.estantevirtual.com.br/busca?q={titulo_formatado}&searchField=titulo-autor"
        )
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            response2 = requests.get(url2, headers=headers, timeout=10)
            response2.raise_for_status()
        except Exception as e:
            print(f"Erro ao buscar '{title}': {e}")
            return None
        try:
            response3 = requests.get(url3, headers=headers, timeout=10)
            response3.raise_for_status()
        except Exception as e:
            print(f"Erro ao buscar '{title}': {e}")
            return None

        soup2 = BeautifulSoup(response2.text, "html.parser")
        precos2 = []
        for tag2 in soup2.find_all("span", string=re.compile(r"R\$")):
            texto2 = tag2.get_text(strip=True)
            valor2 = re.sub(r"[^\d,]", "", texto2)
            try:
                valor_float2 = float(valor2.replace(",", "."))
                precos2.append(valor_float2)
            except ValueError as ve2:
                print(f"Erro ao converter '{valor2}' para float: {ve2}")
                continue
        soup3 = BeautifulSoup(response3.text, "html.parser")
        precos3 = []
        for tag3 in soup3.find_all("span", string=re.compile(r"R\$")):
            texto3 = tag3.get_text(strip=True)
            valor3 = re.sub(r"[^\d,]", "", texto3)
            try:
                valor_float3 = float(valor3.replace(",", "."))
                precos3.append(valor_float3)
            except ValueError as ve3:
                print(f"Erro ao converter '{valor3}' para float: {ve3}")
                continue

        if precos2:
            media = round(sum(precos2) / len(precos2), 2)
            print(f"Preço médio para '{title}': R$ {media}")
            return media
        else:
            if precos3:
                media = round(sum(precos3) / len(precos3), 2)
                print(f"Preço médio para '{title}': R$ {media}")
                return media
            else:
                print(f"Nenhum preço encontrado para '{title}'")
                return 0
    df1 = df[df['preco_correto'] == 'yes']
    df2 = df[df['preco_correto'] != 'yes']

    df2[nova_coluna] = df2.apply(
        lambda row: buscar_preco(row["title"], row["year"], row["publisher"]),
        axis=1
    )

    df = pd.concat([df1, df2], ignore_index=True).drop_duplicates()

    return df

def autenticar():
    senha_correta = st.secrets["senha_app"]
    senha_digitada = st.text_input("Enter the password to edit the collection", type="password")
    if senha_digitada == senha_correta:
        st.session_state["autenticado"] = True
    elif senha_digitada:
        st.error("Wrong password.")

def formatar_nome_arquivo(titulo):
    # Normaliza acentos
    titulo_normalizado = unicodedata.normalize("NFKD", titulo)
    # Remove acentos e converte para ASCII
    titulo_sem_acentos = titulo_normalizado.encode("ASCII", "ignore").decode("utf-8")
    # Substitui cedilha manualmente (caso não tenha sido removido)
    titulo_sem_acentos = titulo_sem_acentos.replace("ç", "c").replace("Ç", "C")
    # Substitui caracteres não permitidos por "_"
    return re.sub(r"[^\w\-]", "_", titulo_sem_acentos.strip()).lower()



def gerar_grafico_barra(contagem, titulo, altura=1000):
    fig = go.Figure()
    for categoria, qtd in contagem.items():
        fig.add_trace(go.Bar(
            x=[qtd],
            y=[str(categoria)],
            orientation='h',
            marker=dict(color="#D3D3D3", line=dict(width=0)),
            text=str(qtd),
            textposition='outside',
            cliponaxis=False,
            insidetextanchor='end',
            hoverinfo='none',
            textfont=dict(size=16, color="white")
        ))
    fig.update_layout(
        title_text=titulo,
        title_x=0.0,
        height=altura,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        xaxis=dict(visible=False, showticklabels=False, showgrid=False, ticks=""),
        yaxis=dict(showticklabels=True, title=None),
        margin=dict(l=100, r=80, t=40, b=30),
        showlegend=False
    )
    return fig