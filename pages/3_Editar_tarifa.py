import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="Editar tarifa", layout="wide")

DB_NAME = "tarifario.db"
REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / DB_NAME

st.title("✏️ Edición de tarifa (versionado)")

st.info("Esta pantalla es SOLO para editar tarifas existentes. No crea nuevas.")
