import streamlit as st
import pandas as pd

st.set_page_config(page_title="Biblioteca de Livros", layout="wide")

@st.cache_data
def carregar_dados():
    return pd.read_csv("livros_com_precos.csv")  # substitua pelo seu arquivo

# Carregar dados
df = carregar_dados()

# Conversões e limpeza
df = df.astype(str)
df["preco_medio_estante_virtual"] = df["preco_medio_estante_virtual"].astype(float)

# Métricas
total_livros = len(df)
valor_total = df["preco_medio_estante_virtual"].sum()

# Filtros
st.sidebar.title("Filtros")

ordenar_por = st.sidebar.selectbox("Ordenar por", ["Título", "Autor","Preço"])
ordem = st.sidebar.radio("Ordem", ["Ascendente", "Descendente"])

coluna_ordem = {
    "Título": "titulo",
    "Autor": "autores",
    "Preço":    "preco_medio_estante_virtual"
}[ordenar_por]

df = df.sort_values(by=coluna_ordem, ascending=(ordem == "Ascendente"))

# Filtro por gênero
generos = sorted(df["genero"].dropna().unique())
genero_escolhido = st.sidebar.multiselect("Gênero", ["Todos"] + generos, default=["Todos"])
if "Todos" not in genero_escolhido:
    df = df[df["genero"].isin(genero_escolhido)]

# Filtro por autor
autor_busca = st.sidebar.text_input("Buscar por autor")
if autor_busca:
    df = df[df["autores"].str.contains(autor_busca, case=False, na=False)]

# Filtro por título
titulo_busca = st.sidebar.text_input("Buscar por título")
if titulo_busca:
    df = df[df["titulo"].str.contains(titulo_busca, case=False, na=False)]

# Filtro por faixa de preço
preco_min, preco_max = st.sidebar.slider("Faixa de preço", 0.0, float(df["preco_medio_estante_virtual"].max()), (0.0, float(df["preco_medio_estante_virtual"].max())))
df = df[(df["preco_medio_estante_virtual"] >= preco_min) & (df["preco_medio_estante_virtual"] <= preco_max)]

# Métricas
st.title("Biblioteca de Allan & Ayla")

col1,col2 = st.columns(2)
col1.metric("Total de Livros:", f"{total_livros:,}")
col2.metric("Valor Total:", f"R$ {valor_total:,.2f}")
st.markdown("---")

# Exibição dos livros
num_colunas = 4
for i in range(0, len(df), num_colunas):
    linha = df.iloc[i:i+num_colunas]
    cols = st.columns(len(linha))
    for idx, livro in enumerate(linha.itertuples()):
        with cols[idx]:
            capa2_valida = getattr(livro, "capa2", "").strip().lower() != "nan"
            capa_url = livro.capa2 if capa2_valida else livro.capa
            if pd.notna(capa_url) and str(capa_url).strip().lower() != "nan":
                st.image(capa_url, use_container_width=True, caption=livro.titulo)
            with st.expander("Detalhes", expanded=False):
                st.markdown(f"**Autor:** {livro.autores}")
                st.markdown(f"**Gênero:** {livro.genero}")
                st.markdown(f"**Editora:** {livro.editora}")
                st.markdown(f"**Preço:** R$ {livro.preco_medio_estante_virtual:.2f}")
                titulo_formatado = livro.titulo.replace(" ", "+")
                url_estante = f"https://www.estantevirtual.com.br/busca?q={titulo_formatado}"
                st.markdown(f"[🔍 Ver preço na Estante Virtual]({url_estante})", unsafe_allow_html=True)
                st.markdown(f"**Ano de publicação:** {livro.ano}")
