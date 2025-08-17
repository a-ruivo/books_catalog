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
    def buscar_preco(title,year,publisher):
        titulo_formatado = title.replace(" ", "+")
        publisher_formatado = quote(publisher.lower().replace(" ", "-"))
        url = f"https://www.estantevirtual.com.br/busca?q={requests.utils.quote(titulo_formatado)}&ano-de-publicacao={requests.utils.quote(year)}&editora={requests.utils.quote(publisher_formatado)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
        except Exception as e:
            print(f"Erro ao buscar '{title}': {e}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        precos = []
        for tag in soup.find_all("span", string=re.compile(r"R\$")):
            texto = tag.get_text(strip=True)
            valor = re.sub(r"[^\d,]", "", texto)
            try:
                valor_float = float(valor.replace(",", "."))
                precos.append(valor_float)
            except ValueError as ve:
                print(f"Erro ao converter '{valor}' para float: {ve}")
                continue

        if precos:
            media = round(sum(precos) / len(precos), 2)
            print(f"Preço médio para '{title}': R$ {media}")
            return media
        else:
            print(f"Nenhum preço encontrado para '{title}'")
            return None

    df[nova_coluna] = df.apply(lambda row: buscar_preco(row["title"], row["year"], row["publisher"]), axis=1)
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