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
# =====================================================
# BLOQUE 0.1 - CARGA SEGURA DE TARIFA EN SESSION_STATE
# =====================================================

# 🔒 Campos que vive en session_state (UI)
CAMPOS_SESSION = [
    "pais_origen","estado_origen","ciudad_origen",
    "pais_destino","estado_destino","ciudad_destino",
    "tipo_unidad",
    "precio_viaje_sencillo","precio_viaje_redondo",
    "tarifa_viaje_sencillo","tarifa_viaje_redondo","tarifa_viaje_full",
    "usa_freight","mexican_freight","crossing","border_crossing",
    "aduanas_aranceles","insurance","peajes","maniobras"
]

# 🔒 Defaults (evita None en inputs y errores raros)
DEFAULTS = {
    "pais_origen": "", "estado_origen": "", "ciudad_origen": "",
    "pais_destino": "", "estado_destino": "", "ciudad_destino": "",
    "tipo_unidad": "",

    "precio_viaje_sencillo": 0.0, "precio_viaje_redondo": 0.0,
    "tarifa_viaje_sencillo": 0.0, "tarifa_viaje_redondo": 0.0, "tarifa_viaje_full": 0.0,

    "usa_freight": 0.0, "mexican_freight": 0.0, "crossing": 0.0, "border_crossing": 0.0,
    "aduanas_aranceles": 0.0, "insurance": 0.0, "peajes": 0.0, "maniobras": 0.0
}

# 🔒 Inicialización defensiva (CRÍTICA)
for c in CAMPOS_SESSION:
    if c not in st.session_state:
        st.session_state[c] = DEFAULTS.get(c, "")

# Flag de control
if "tarifa_cargada" not in st.session_state:
    st.session_state["tarifa_cargada"] = False


# 🎯 MAPEO EXPLÍCITO UI -> BD (NUNCA usar .upper())
MAPEO_SESSION_BD = {
    "pais_origen": "PAIS_ORIGEN",
    "estado_origen": "ESTADO_ORIGEN",
    "ciudad_origen": "CIUDAD_ORIGEN",
    "pais_destino": "PAIS_DESTINO",
    "estado_destino": "ESTADO_DESTINO",
    "ciudad_destino": "CIUDAD_DESTINO",
    "tipo_unidad": "TIPO_UNIDAD",
    "precio_viaje_sencillo": "PRECIO_VIAJE_SENCILLO",
    "precio_viaje_redondo": "PRECIO_VIAJE_REDONDO",
    "tarifa_viaje_sencillo": "TARIFA_VIAJE_SENCILLO",
    "tarifa_viaje_redondo": "TARIFA_VIAJE_REDONDO",
    "tarifa_viaje_full": "TARIFA_VIAJE_FULL",
    "usa_freight": "USA_FREIGHT",
    "mexican_freight": "MEXICAN_FREIGHT",
    "crossing": "CROSSING",
    "border_crossing": "BORDER_CROSSING",
    "aduanas_aranceles": "ADUANAS_ARANCELES",
    "insurance": "INSURANCE",
    "peajes": "PEAJES",
    "maniobras": "MANIOBRAS"
}

# =====================================================
# 🔄 CARGA CONTROLADA DE TARIFA (SOLO UNA VEZ)
# =====================================================
if (
    "tarifa_base_tmp" in st.session_state
    and st.session_state["tarifa_base_tmp"] is not None
    and not st.session_state["tarifa_cargada"]
):

    tarifa_base = st.session_state["tarifa_base_tmp"]

    for campo_ui, campo_bd in MAPEO_SESSION_BD.items():
        val = tarifa_base.get(campo_bd, DEFAULTS.get(campo_ui, ""))
        st.session_state[campo_ui] = val if val is not None else DEFAULTS.get(campo_ui, "")

    st.session_state["tarifa_cargada"] = True
    st.session_state["tarifa_base_tmp"] = None  # evita que se “pegue”

else:
    tarifa_base = None
