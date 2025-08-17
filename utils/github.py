import requests, base64, pandas as pd
from io import StringIO
import streamlit as st
from config import CSV_PATH, REPO, GITHUB_TOKEN, TTL

def carregar_csv_do_github(repo, path, token):
    import base64, requests, pandas as pd
    from io import StringIO

    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}"}

    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        conteudo_base64 = r.json()["content"]
        conteudo_csv = base64.b64decode(conteudo_base64).decode()
        return pd.read_csv(StringIO(conteudo_csv))
    else:
        raise Exception(f"Erro ao carregar CSV do GitHub: {r.status_code} - {r.text}")

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
        try:
            df_atual = pd.read_csv(StringIO(conteudo_atual))
        except Exception as e:
            return False, f"Erro ao ler CSV existente: {e}"

        # Remove duplicatas com base em colunas-chave (ajuste conforme necessário)
        df_final = pd.concat([df_atual, df_novo], ignore_index=True).drop_duplicates()
    else:
        sha = None
        df_final = df_novo

    # Prepara conteúdo para upload
    try:
        conteudo_csv = df_final.to_csv(index=False)
        conteudo_base64 = base64.b64encode(conteudo_csv.encode()).decode()
    except Exception as e:
        return False, f"Erro ao converter DataFrame para CSV: {e}"

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


def alterar_csv_em_github(df_novo, repo, path, token):
    import base64, requests

    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}"}

    # Verifica se o arquivo já existe para obter o SHA
    r_get = requests.get(url, headers=headers)
    sha = r_get.json()["sha"] if r_get.status_code == 200 else None

    # Prepara conteúdo para upload
    conteudo_csv = df_novo.to_csv(index=False)
    conteudo_base64 = base64.b64encode(conteudo_csv.encode()).decode()

    data = {
        "message": "Substituição completa via Streamlit",
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