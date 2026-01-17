# =====================================================
# PANTALLA 2 - CAPTURA DE TARIFAS Y COSTOS (LIBRE)
# BLOQUE 1 - IMPORTS + CONFIG + DB PATH (CLOUD/LOCAL)
# =====================================================

import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="Captura de tarifas", layout="wide")

DB_NAME = "tarifario.db"
REPO_ROOT = Path(__file__).resolve().parents[1]   # .../tarifario-streamlit-v2
DB_PATH = REPO_ROOT / DB_NAME                     # .../tarifario-streamlit-v2/tarifario.db

st.title("🟩 Captura de tarifas y costos")

# 🔴 RESET DE SESSION (solo debug)
if st.button("RESET ESTADO"):
    st.session_state.clear()
    st.rerun()
