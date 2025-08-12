import pandas as pd
import requests
import os

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

# Exemplo de uso
processar_planilha("meus_livros.xlsx", "livros_com_dados.csv")
