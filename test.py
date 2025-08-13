import streamlit as st
import pandas as pd
import requests
import time
import base64
import os

st.set_page_config(page_title="Books Collection", layout="wide")

# Verificação de senha
def autenticar():
    senha_correta = st.secrets["senha_app"]
    senha_digitada = st.text_input("Enter the password to edit the collection", type="password")
    if senha_digitada == senha_correta:
        st.session_state["autenticado"] = True
    elif senha_digitada:
        st.error("Wrong password.")

# Configurações do GitHub
GITHUB_TOKEN = st.secrets["github_token"]
REPO = "a-ruivo/books_catalog"
CSV_PATH = "livros_com_precos.csv"

# Funções auxiliares
def buscar_openlibrary(isbn):
    url = "https://openlibrary.org/api/books"
    params = {
        "bibkeys": f"ISBN:{isbn}",
        "format": "json",
        "jscmd": "data"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        dados = response.json().get(f"ISBN:{isbn}")
        if dados:
            return {
                "fonte": "Open Library",
                "titulo": dados.get("title"),
                "autores": ", ".join([a["name"] for a in dados.get("authors", [])]),
                "editora": ", ".join([e["name"] for e in dados.get("publishers", [])]),
                "ano": dados.get("publish_date"),
                "paginas": dados.get("number_of_pages"),
                "capa2": f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
            }
    return None

def buscar_brasilapi(isbn):
    url = f"https://brasilapi.com.br/api/isbn/v1/{isbn}"
    response = requests.get(url)
    if response.status_code == 200:
        dados = response.json()
        return {
            "fonte": "BrasilAPI",
            "titulo": dados.get("title"),
            "autores": ", ".join(dados.get("authors", [])),
            "editora": dados.get("publisher"),
            "ano": dados.get("year"),
            "paginas": dados.get("pages"),
            "capa2": None
        }
    return None

def buscar_dados(isbn):
    for func in [buscar_openlibrary, buscar_brasilapi]:
        resultado = func(isbn)
        if resultado:
            return resultado
    return {
        "fonte": None,
        "titulo": None,
        "autores": None,
        "editora": None,
        "ano": None,
        "paginas": None,
        "capa2": None
    }

def processar_planilha(caminho_entrada, caminho_saida):
    df_novo = pd.read_excel(caminho_entrada)
    if "isbn" not in df_novo.columns:
        raise ValueError("A planilha deve conter uma coluna chamada 'isbn'.")

    # Carregar CSV existente se houver
    if os.path.exists(caminho_saida):
        df_existente = pd.read_csv(caminho_saida, encoding="utf-8-sig")
        isbn_existentes = set(df_existente["isbn"].astype(str))
    else:
        df_existente = pd.DataFrame()
        isbn_existentes = set()

    total = len(df_novo)
    novos_registros = []

    for i, linha in df_novo.iterrows():
        isbn = str(linha["isbn"]).strip()
        if isbn not in isbn_existentes:
            dados = buscar_dados(isbn)
            novos_registros.append(pd.concat([linha, pd.Series(dados)]))

        if (i + 1) % 20 == 0 or (i + 1) == total:
            print(f"Progresso: {i + 1}/{total} ISBNs processados")

    if novos_registros:
        df_novos = pd.DataFrame(novos_registros)
        df_final = pd.concat([df_existente, df_novos], ignore_index=True)
        df_final.to_csv(caminho_saida, index=False, encoding="utf-8-sig")
        print(f"{len(novos_registros)} novos registros adicionados.")
    else:
        print("Nenhum novo ISBN encontrado para adicionar.")

def salvar_csv_em_github(df_novo, repo, path, token):
    import base64, requests, pandas as pd
    from io import StringIO

    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}"}

    # Verifica se o arquivo já existe
    r_get = requests.get(url, headers=headers)
    if r_get.status_code == 200:
        conteudo_atual = base64.b64decode(r_get.json()["content"]).decode()
        sha = r_get.json()["sha"]
        df_atual = pd.read_csv(StringIO(conteudo_atual))

        # Junta os dados novos com os existentes
        df_final = pd.concat([df_atual, df_novo], ignore_index=True)
    else:
        sha = None
        df_final = df_novo

    # Prepara conteúdo para upload
    conteudo_csv = df_final.to_csv(index=False)
    conteudo_base64 = base64.b64encode(conteudo_csv.encode()).decode()

    data = {
        "message": "Atualização incremental via Streamlit",
        "content": conteudo_base64,
        "branch": "main"
    }
    if sha:
        data["sha"] = sha

    r_put = requests.put(url, headers=headers, json=data)

    if r_put.status_code in [200, 201]:
        return True, "Arquivo salvo com sucesso!"
    else:
        try:
            erro = r_put.json().get("message", "Erro desconhecido")
        except Exception:
            erro = "Erro ao decodificar resposta da API"
        return False, erro

def buscar_preco_medio(titulo):
    url = f"https://www.estantevirtual.com.br/busca?q={requests.utils.quote(titulo)}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Erro ao buscar '{titulo}': {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    precos = []

    for tag in soup.find_all("span", string=re.compile(r"R\$")):
        texto = tag.get_text(strip=True)
        valor = re.sub(r"[^\d,]", "", texto).replace(",", ".")
        try:
            precos.append(float(valor))
        except:
            continue

    if precos:
        return round(sum(precos) / len(precos), 2)
    return None

# Abas principais
aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs(["Collection", "Login", "Add Book", "Import File", "Book Manager", "Wish List"])

with aba1:
    try:
        @st.cache_data
        def carregar_dados():
            return pd.read_csv(CSV_PATH)

        # Carregar dados
        df = carregar_dados()

        # Conversões e limpeza
        df = df.astype(str)
        df["preco_medio_estante_virtual"] = df["preco_medio_estante_virtual"].astype(float)

        # Filtros
        st.sidebar.title("Filters")

        ordenar_por = st.sidebar.selectbox("Order by", ["Title", "Author","Price"])
        ordem = st.sidebar.radio("Ordem", ["Ascendente", "Desc"])

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

        # Métricas
        total_livros = len(df)
        valor_total = df["preco_medio_estante_virtual"].sum()

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
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")

with aba2:
    st.header("Login to add cards")
    if "autenticado" not in st.session_state or not st.session_state["autenticado"]:
        autenticar()
        st.stop()

with aba3:
    st.header("Add card mannualy or by code")

    modo = st.radio("Mode", ["Manual", "Search by code"])

    if modo == "Buscar por código":
        codigo_colecao = st.text_input("Collection code")
        numero_carta = st.text_input("Card number")
        padrao = st.number_input("Regular quantity", min_value=0)
        foil = st.number_input("Foil quantity", min_value=0)
        buscar = st.button("Search and save")

        if buscar and codigo_colecao and numero_carta:
            identificador = [{"set": codigo_colecao.lower(), "collector_number": numero_carta}]
            dados = buscar_detalhes_em_lote(identificador)
            if dados:
                carta = dados[0]
                cotacao = get_usd_to_brl()
                preco_usd = float(carta.get("prices", {}).get("usd") or 0)
                preco_foil = float(carta.get("prices", {}).get("usd_foil") or 0)
                preco_brl = round(preco_usd * cotacao, 2)
                preco_brl_foil = round(preco_foil * cotacao, 2)
                imagem = carta.get("image_uris", {}).get("normal")

                nova = pd.DataFrame([{
                    "nome": carta.get("name"),
                    "tipo": carta.get("type_line"),
                    "preco_brl": preco_brl,
                    "preco_brl_foil": preco_brl_foil,
                    "padrao": padrao,
                    "foil": foil,
                    "imagem": imagem,
                    "colecao": codigo_colecao.lower(),
                    "numero": numero_carta,
                    "colecao_nome": carta.get("set_name"),
                    "icone_colecao": carta.get("set_icon_svg_uri"),
                    "raridade": carta.get("rarity"),
                    "cores": ", ".join(carta.get("colors", [])),
                    "mana_cost": carta.get("mana_cost"),
                    "nome_2": None
                }])
                try:
                    df_existente = pd.read_csv(CSV_PATH)
                    df_final = pd.concat([df_existente, nova], ignore_index=True)
                except:
                    df_final = nova

                sucesso = salvar_csv_em_github(df_final, REPO, CSV_PATH, GITHUB_TOKEN)
                if sucesso:
                    st.success("Card add!")
                else:
                    st.error("Error.")
            else:
                st.error("Card not found in API.")
    else:
        with st.form("form_carta"):
            nome = st.text_input("Card name")
            tipo = st.text_input("Type")
            preco_brl = st.number_input("Price (BRL)", min_value=0.0)
            preco_brl_foil = st.number_input("Price Foil (BRL)", min_value=0.0)
            padrao = st.number_input("Regular quantity", min_value=0)
            foil = st.number_input("Foil quantity", min_value=0)
            imagem = st.text_input("Image URL")
            colecao = st.text_input("Collection code")
            numero = st.text_input("Card number")
            colecao_nome = st.text_input("Collection name")
            icone_colecao = st.text_input("Collection icon URL")
            raridade = st.selectbox("Rarity", ["common", "uncommon", "rare", "mythic"])
            cores = st.text_input("Colors (ex: W, U, B, R, G, C, L)")
            mana_cost = st.text_input("Mana cost (ex: {1}{G}{G})")
            nome_2 = st.text_input("Alternative name or secundary face (optional)")
            enviado = st.form_submit_button("Add card")

        if enviado:
            nova_carta = pd.DataFrame([{
                "nome": nome, "tipo": tipo, "preco_brl": preco_brl, "preco_brl_foil": preco_brl_foil,
                "padrao": padrao, "foil": foil, "imagem": imagem, "colecao": colecao,
                "numero": numero, "colecao_nome": colecao_nome, "icone_colecao": icone_colecao,
                "raridade": raridade, "cores": cores, "mana_cost": mana_cost, "nome_2": nome_2
            }])
            try:
                df_existente = pd.read_csv(CSV_PATH)
                df_final = pd.concat([df_existente, nova_carta], ignore_index=True)
            except:
                df_final = nova_carta

            sucesso, mensagem = salvar_csv_em_github(df_final, REPO, CSV_PATH, GITHUB_TOKEN)

            if sucesso:
                st.success("Cards add!")
            else:
                st.error(f"Erro ao salvar no GitHub: {mensagem}")

with aba4:
    st.header("Import cards using Excel")

    arquivo = st.file_uploader("Select the excel file", type=["xlsx"])
    if arquivo:
        df = pd.read_excel(arquivo)
        df = df.dropna(subset=["colecao", "numero"])
        df["colecao"] = df["colecao"].astype(str).str.lower()
        df["numero"] = df["numero"].astype(str)
        df["padrao"] = df.get("padrao", 1)
        df["foil"] = df.get("foil", 0)

        df = df.groupby(["colecao", "numero"], as_index=False).agg({
            "padrao": "sum",
            "foil": "sum",
            **{col: "first" for col in df.columns if col not in ["colecao", "numero", "padrao", "foil"]}
        })

        cotacao = get_usd_to_brl()
        identificadores = [{"set": row["colecao"], "collector_number": row["numero"]} for _, row in df.iterrows()]
        todos_detalhes = []
        for lote in dividir_em_lotes(identificadores, 75):
            todos_detalhes.extend(buscar_detalhes_em_lote(lote))
            time.sleep(0.5)

        detalhes_dict = {}
        for carta in todos_detalhes:
            preco_usd = float(carta.get("prices", {}).get("usd") or 0)
            preco_foil = float(carta.get("prices", {}).get("usd_foil") or 0)
            preco_brl = round(preco_usd * cotacao, 2)
            preco_brl_foil = round(preco_foil * cotacao, 2)
            faces = carta.get("card_faces", [])
            face1 = faces[0] if faces else carta
            face2 = faces[1] if len(faces) > 1 else {}

            detalhes_dict[(carta["set"], carta["collector_number"])] = {
                "nome": face1.get("name"),
                "mana_cost": face1.get("mana_cost"),
                "cores": ", ".join(face1.get("colors", [])),
                "imagem": face1.get("image_uris", {}).get("normal") or carta.get("image_uris", {}).get("normal"),
                "nome_2": face2.get("name"),
                "imagem_2": face2.get("image_uris", {}).get("normal"),
                "colecao_nome": carta.get("set_name"),
                "icone_colecao": carta.get("set_icon_svg_uri"),
                "raridade": carta.get("rarity"),
                "tipo": carta.get("type_line"),
                "preco_brl": preco_brl,
                "preco_brl_foil": preco_brl_foil
            }

        df_detalhes = df.apply(lambda linha: pd.Series(
            detalhes_dict.get((linha["colecao"], linha["numero"]), {})
        ), axis=1)

        df_final = pd.concat([df, df_detalhes], axis=1)
        sucesso, mensagem = salvar_csv_em_github(df_final, REPO, CSV_PATH, GITHUB_TOKEN)

        if sucesso:
            st.success("Cards add!")
        else:
            st.error(f"Erro ao salvar no GitHub: {mensagem}")

with aba5:
    st.header("Card Manager")

    try:
        df = pd.read_csv(CSV_PATH)
        df["padrao"] = df["padrao"].astype(int)
        df["foil"] = df["foil"].astype(int)

        df_editado = st.data_editor(
            df[["nome", "numero", "colecao", "padrao", "foil"]],
            num_rows="dynamic",
            use_container_width=True,
            key="editor"
        )

        if st.button("Save"):
            df_atualizado = df.drop(columns=["padrao", "foil"]).merge(
                df_editado[["numero", "colecao", "padrao", "foil"]],
                on=["numero", "colecao"],
                how="left"
            )
            sucesso = salvar_csv_em_github(df_atualizado, REPO, CSV_PATH, GITHUB_TOKEN)
            if sucesso:
                st.success("Changes saved!")
            else:
                st.error("Error.")
    except:
        st.warning("Data not found.")