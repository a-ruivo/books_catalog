import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import plotly.graph_objects as go
from PIL import Image
import os

from config import CSV_PATH, REPO, GITHUB_TOKEN
from utils.github import salvar_csv_em_github, alterar_csv_em_github, carregar_csv_do_github
from utils.helpers import adicionar_preco_medio, autenticar, formatar_nome_arquivo, gerar_grafico_barra

if "aba_atual" not in st.session_state:
    st.session_state["aba_atual"] = "Books"

st.set_page_config(page_title="Book Collection", layout="wide")

aba_atual = st.sidebar.radio("Pages", ["Books", "Dashboard", "Add Book", "Book Manager"])
st.session_state["aba_atual"] = aba_atual

# Carrega a imagem da pasta local
image = Image.open("docs/capa.png")

# Exibe a imagem no topo
st.image(image, use_container_width=True)

st.markdown("""
    <style>
        .stApp {
            background-color: #272525;
        }
    </style>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([4, 2, 2])

with col1:
    st.markdown("""
    **Made by Allan Ruivo Wildner | https://github.com/a-ruivo**  
    """)

with col2:
    reprocessar = st.button("Refresh Data", help="Reprocess the data from the CSV file and update the collection.")

    if reprocessar:
        st.session_state.pop("df", None)
        df = carregar_csv_do_github(REPO, CSV_PATH, GITHUB_TOKEN)

        # Remove duplicatas antes de qualquer processamento
        df = df.drop_duplicates(keep="last")

        # Mantém apenas as colunas relevantes
        df = df.loc[:, ["isbn", "genre", "cover", "title", "authors", "publisher", "year", "price", "collection", "volume", "pages", "type"]]

        df_com_precos = adicionar_preco_medio(df)
        # Salva no GitHub e atualiza o estado
        alterar_csv_em_github(df_com_precos, REPO, CSV_PATH, GITHUB_TOKEN)
        st.session_state["df"] = df_com_precos
        st.success("Data updated!")

    else:
        if "df" not in st.session_state:
            st.session_state["df"] = carregar_csv_do_github(REPO, CSV_PATH, GITHUB_TOKEN)

with col3:
    # Executa autenticação uma vez
    if "autenticado" not in st.session_state:
        autenticar()

    acesso_restrito = not st.session_state.get("autenticado", False)

if st.session_state["aba_atual"] == "Books":
    st.header("Books")
    df = st.session_state["df"]

    # Conversões e limpeza
    df = df.astype(str)
    df["preco_medio"] = df["preco_medio"].astype(float)
    df["nome_arquivo"] = df["title"].apply(formatar_nome_arquivo)

    # Métricas
    total_livros = len(df)
    valor_total = df["preco_medio"].sum()

    # Filtros
    ordenar_por = st.sidebar.selectbox("Ordenar por", ["Title", "Genre", "Author", "Price", "Publisher", "Year", "Collection", "Type"], index=0)
    ordem = st.sidebar.radio("Ordem", ["Ascending", "Descending"], index=0)
    coluna_ordem = {
        "Title": "title",
        "Author": "authors",
        "Price": "preco_medio",
        "Genre": "genre",
        "Publisher": "publisher",
        "Year": "year",
        "Collection": "collection",
        "Type": "type"
    }[ordenar_por]
    df = df.sort_values(by=coluna_ordem, ascending=(ordem == "Ascending"))

    # Filtro por gênero
    generos = sorted(df["genre"].dropna().unique())
    genero_escolhido = st.sidebar.multiselect("Genre", ["All"] + generos, default=["All"])
    if "All" not in genero_escolhido:
        df = df[df["genre"].isin(genero_escolhido)]

    # Filtro por ano
    anos = sorted(df["year"].dropna().unique())
    ano_escolhido = st.sidebar.multiselect("Year", ["All"] + anos, default=["All"])
    if "All" not in ano_escolhido:
        df = df[df["year"].isin(ano_escolhido)]

    # Filtro por tipo
    tipo = st.sidebar.radio("Type", ["Collection", "Wishlist"])
    df = df[df["type"] == tipo]

    # Filtro por coleção
    colecoes = sorted(df["collection"].dropna().unique())
    colecao_escolhida = st.sidebar.multiselect("Collection", ["All"] + colecoes, default=["All"])
    if "All" not in colecao_escolhida:
        df = df[df["collection"].isin(colecao_escolhida)]

    # Filtro por autor
    autor_busca = st.sidebar.text_input("Search by author")
    if autor_busca:
        df = df[df["authors"].str.contains(autor_busca, case=False, na=False)]

    # Filtro por título
    titulo_busca = st.sidebar.text_input("Search by title")
    if titulo_busca:
        df = df[df["title"].str.contains(titulo_busca, case=False, na=False)]

    # Filtro por valor
    valor_maximo = float(df["preco_medio"].dropna().max())
    if pd.isna(valor_maximo) or valor_maximo == 0.0:
        valor_maximo = 1.0
    valor_min, valor_max = st.sidebar.slider("Book Price (BRL)", 0.0, valor_maximo, (0.0, valor_maximo))
    if valor_min == valor_max:
        valor_max += 1.0
    df = df[(df["preco_medio"] >= valor_min) & (df["preco_medio"] <= valor_max)]

    # Métricas visuais
    col1, col2 = st.columns(2)
    col1.metric("Books Total:", f"{total_livros:,}")
    col2.metric("Total Value:", f"R$ {valor_total:,.2f}")
    st.markdown("---")

    # Exibição dos livros
    num_colunas = 4
    for i in range(0, len(df), num_colunas):
        linha = df.iloc[i:i+num_colunas]
        cols = st.columns(len(linha))
        for idx, livro in enumerate(linha.itertuples()):
            with cols[idx]:
                # Tenta carregar imagem local
                imagem_exibida = False
                for ext in [".jpg", ".png"]:
                    caminho_imagem = f"images/{livro.nome_arquivo}{ext}"
                    if os.path.exists(caminho_imagem):
                        st.image(caminho_imagem, use_container_width=True, caption=livro.title)
                        imagem_exibida = True
                        break
                # Se não houver imagem local, tenta usar a da API
                if not imagem_exibida and pd.notna(livro.cover):
                    st.image(livro.cover, use_container_width=True, caption=livro.title)

                # Detalhes do livro
                with st.expander("Details", expanded=False):
                    st.markdown(f"**Author:** {livro.authors}")
                    st.markdown(f"**Genre:** {livro.genre}")
                    st.markdown(f"**Publisher:** {livro.publisher}")
                    st.markdown(f"**Price:** R$ {livro.preco_medio:.2f}")
                    titulo_formatado = livro.title.replace(" ", "+")
                    url_estante = f"https://www.estantevirtual.com.br/busca?q={titulo_formatado}"
                    st.markdown(f"[🔍 See price in Estante Virtual]({url_estante})", unsafe_allow_html=True)
                    st.markdown(f"**Published in year:** {livro.year}")

elif st.session_state["aba_atual"] == "Dashboard":
    st.header("Dashboard")
    df = st.session_state["df"]

    # Conversões e limpeza
    df = df.astype(str)
    df["preco_medio"] = df["preco_medio"].astype(float)

    # Filtros
    ordenar_por = st.sidebar.selectbox("Ordenar por", ["Title", "Genre", "Author", "Price", "Publisher", "Year", "Collection", "Type"], index=0)
    ordem = st.sidebar.radio("Ordem", ["Ascending", "Descending"], index=0)
    coluna_ordem = {
        "Title": "title",
        "Author": "authors",
        "Price": "preco_medio",
        "Genre": "genre",
        "Publisher": "publisher",
        "Year": "year",
        "Collection": "collection",
        "Type": "type"
    }[ordenar_por]
    df = df.sort_values(by=coluna_ordem, ascending=(ordem == "Ascending"))

    # Filtros múltiplos
    filtros = {
        "Genre": "genre",
        "Year": "year",
        "Collection": "collection"
    }
    for label, coluna in filtros.items():
        opcoes = sorted(df[coluna].dropna().unique())
        selecionados = st.sidebar.multiselect(label, ["All"] + opcoes, default=["All"])
        if "All" not in selecionados:
            df = df[df[coluna].isin(selecionados)]

    tipo = st.sidebar.radio("Type", ["Collection", "Wishlist"])
    df = df[df["type"] == tipo]

    autor_busca = st.sidebar.text_input("Search by author")
    if autor_busca:
        df = df[df["authors"].str.contains(autor_busca, case=False, na=False)]

    titulo_busca = st.sidebar.text_input("Search by title")
    if titulo_busca:
        df = df[df["title"].str.contains(titulo_busca, case=False, na=False)]

    valor_maximo = float(df["preco_medio"].dropna().max())
    if pd.isna(valor_maximo) or valor_maximo == 0.0:
        valor_maximo = 1.0
    valor_min, valor_max = st.sidebar.slider("Book Price (BRL)", 0.0, valor_maximo, (0.0, valor_maximo))
    if valor_min == valor_max:
        valor_max += 1.0
    df = df[(df["preco_medio"] >= valor_min) & (df["preco_medio"] <= valor_max)]

    # Métricas
    total_livros = len(df)
    valor_total = df["preco_medio"].sum()
    col1, col2 = st.columns(2)
    col1.metric("Books Total:", f"{total_livros:,}")
    col2.metric("Total Value:", f"R$ {valor_total:,.2f}")
    st.markdown("---")

    # Prepara contagens
    df["livros"] = 1  # cada linha representa um livro

    # Gera gráficos
    fig1 = gerar_grafico_barra(df.groupby("publisher")["livros"].sum().sort_values(), "Publisher distribution", altura=3000)
    fig2 = gerar_grafico_barra(df.groupby("genre")["livros"].sum().sort_values(), "Genre distribution", altura=3000)
    fig3 = gerar_grafico_barra(df.groupby("year")["livros"].sum().sort_values(), "Year distribution", altura=3000)
    fig4 = gerar_grafico_barra(df.groupby("authors")["livros"].sum().sort_values(), "Authors distribution", altura=1000)

    # Exibe gráficos
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig1, use_container_width=True)
        st.plotly_chart(fig2, use_container_width=True)
    with col2:
        st.plotly_chart(fig3, use_container_width=True)
        st.plotly_chart(fig4, use_container_width=True)

elif st.session_state["aba_atual"] == "Add Book":
    st.header("Add book to collection")
    df_existente = st.session_state["df"]

    if acesso_restrito:
        st.warning("Enter the password to access this page.")
        st.stop()

    with st.form("form_books"):
        title_form = st.text_input("Title")
        isbn_form = st.text_input("ISBN")
        genre_form = st.text_input("Genre")
        author_form = st.text_input("Author")
        publisher_form = st.text_input("Publisher")
        year_form = st.text_input("Year")
        collection_form = st.text_input("Collection")
        volume_form = st.text_input("Volume")
        pages_form = st.text_input("Pages")
        type_form = st.selectbox("Choose a type", ["Collection", "Wishlist"])
        imagem_upload = st.file_uploader("Upload image (PNG or JPEG)", type=["png", "jpg", "jpeg"])
        enviado = st.form_submit_button("Add book")

    if enviado:
        campos_obrigatorios = [
            title_form, isbn_form, genre_form, author_form, publisher_form,
            year_form, collection_form, volume_form, pages_form, type_form
        ]
        if any(campo in [None, "", 0] for campo in campos_obrigatorios) or imagem_upload is None:
            st.warning("Por favor, preencha todos os campos obrigatórios e envie uma imagem.")
        else:
            nome_arquivo = formatar_nome_arquivo(title_form)
            caminho_local = f"images/{nome_arquivo}.jpg"

            imagem_bytes = imagem_upload.read()
            st.image(imagem_bytes, caption="Preview", use_container_width=True)
            with open(caminho_local, "wb") as f:
                f.write(imagem_bytes)

            nova_carta = pd.DataFrame([{
                "title": title_form,
                "isbn": isbn_form,
                "genre": genre_form,
                "authors": author_form,
                "publisher": publisher_form,
                "year": year_form,
                "collection": collection_form,
                "volume": volume_form,
                "pages": pages_form,
                "type": type_form,
                "cover": f"https://raw.githubusercontent.com/a-ruivo/books_catalog/main/images/{nome_arquivo}.jpg"
            }])

            nova_carta = adicionar_preco_medio(nova_carta)

            ja_existe = (
                (df_existente["title"] == title_form) &
                (df_existente["type"] == type_form)
            ).any()

            if ja_existe:
                st.warning("This book already is in the collection.")
            else:
                df_form = pd.concat([df_existente, nova_carta], ignore_index=True)
                sucesso, mensagem = salvar_csv_em_github(df_form, REPO, CSV_PATH, GITHUB_TOKEN)
                if sucesso:
                    st.session_state["df"] = df_form
                    st.success("Book added!")
                else:
                    st.error(f"Error saving in GitHub: {mensagem}")

elif st.session_state["aba_atual"] == "Book Manager":
    st.header("Book Manager")

    if acesso_restrito:
        st.warning("Enter the password to access this page.")
        st.stop()

    if "df" not in st.session_state:
        st.session_state["df"] = carregar_csv_do_github(REPO, CSV_PATH, GITHUB_TOKEN)

    df_manager = st.session_state["df"]

    df_editado = st.data_editor(
        df_manager,
        num_rows="dynamic",
        use_container_width=True,
        key="editor"
    )

    if st.button("Save"):
        sucesso, mensagem = alterar_csv_em_github(df_editado, REPO, CSV_PATH, GITHUB_TOKEN)
        if sucesso:
            st.session_state["df"] = df_editado
            st.success("Changes saved!")
        else:
            st.error(f"Error saving in GitHub: {mensagem}")
