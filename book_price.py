import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time

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

# 📥 Carregar base de dados
df = pd.read_csv("livros_com_dados.csv")

# 🧠 Criar nova coluna com preços médios
precos_medios = []
for titulo in df["titulo"]:
    preco = buscar_preco_medio(titulo)
    precos_medios.append(preco)
    print(f"{titulo}: R$ {preco if preco else 'Não encontrado'}")
    time.sleep(2)  # respeitar o site

df["preco_medio_estante_virtual"] = precos_medios

# 💾 Salvar novo arquivo
df.to_csv("livros_com_precos.csv", index=False)
print("Arquivo atualizado salvo como 'livros_com_precos.csv'")
