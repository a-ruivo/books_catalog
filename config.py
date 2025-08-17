import streamlit as st

CSV_PATH = "livros.csv"
REPO = "a-ruivo/books_catalog"
GITHUB_TOKEN = st.secrets["github_token"]
TTL = 86400  # 24 horas