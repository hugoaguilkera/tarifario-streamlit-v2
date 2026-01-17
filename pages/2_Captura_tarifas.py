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
# =====================================================
# BLOQUE 0 - BUSCADOR RÁPIDO DE TARIFAS (EDICIÓN / NUEVA)
# =====================================================
st.subheader("🔍 Buscar tarifa existente para modificar")

# --- Carga base (solo ACTIVA=1) ---
with sqlite3.connect(DB_NAME) as conn:
    df_existentes = pd.read_sql(
        """
        SELECT
            ID_TARIFA,
            TRANSPORTISTA,
            CLIENTE,
            TIPO_UNIDAD,

            PRECIO_VIAJE_SENCILLO,
            PRECIO_VIAJE_REDONDO,
            TARIFA_VIAJE_SENCILLO,
            TARIFA_VIAJE_REDONDO,
            TARIFA_VIAJE_FULL,

            USA_FREIGHT,
            MEXICAN_FREIGHT,
            CROSSING,
            BORDER_CROSSING,
            ADUANAS_ARANCELES,
            INSURANCE,
            PEAJES,
            MANIOBRAS,

            PAIS_ORIGEN,
            ESTADO_ORIGEN,
            CIUDAD_ORIGEN,
            PAIS_DESTINO,
            ESTADO_DESTINO,
            CIUDAD_DESTINO,

            ALL_IN
        FROM tarifario_estandar
        WHERE ACTIVA = 1
          AND ID_TARIFA IS NOT NULL
        """,
        conn
    )

# --- Defensa si viene vacío ---
if df_existentes.empty:
    st.warning("No hay tarifas ACTIVAS con ID_TARIFA en la base.")
    df_existentes = pd.DataFrame(columns=[
        "ID_TARIFA","TRANSPORTISTA","CLIENTE","CIUDAD_ORIGEN","CIUDAD_DESTINO","ALL_IN"
    ])

# ---------------- FILTROS DE BÚSQUEDA ----------------
transportistas_list = ["Todos"] + sorted(df_existentes.get("TRANSPORTISTA", pd.Series()).dropna().unique().tolist())
clientes_list = ["Todos"] + sorted(df_existentes.get("CLIENTE", pd.Series()).dropna().unique().tolist())

filtro_transportista = st.selectbox(
    "Filtrar por transportista",
    transportistas_list,
    key="filtro_transportista"
)

filtro_cliente = st.selectbox(
    "Filtrar por cliente",
    clientes_list,
    key="filtro_cliente"
)

if filtro_transportista != "Todos" and "TRANSPORTISTA" in df_existentes.columns:
    df_existentes = df_existentes[df_existentes["TRANSPORTISTA"] == filtro_transportista]

if filtro_cliente != "Todos" and "CLIENTE" in df_existentes.columns:
    df_existentes = df_existentes[df_existentes["CLIENTE"] == filtro_cliente]

# Orden final (solo si existen columnas)
orden_cols = [c for c in ["TRANSPORTISTA", "PAIS_ORIGEN", "CIUDAD_ORIGEN"] if c in df_existentes.columns]
if orden_cols:
    df_existentes = df_existentes.sort_values(orden_cols).reset_index(drop=True)

# ---------------- OPCIONES SELECT ----------------
ids = df_existentes["ID_TARIFA"].dropna().astype(str).tolist() if "ID_TARIFA" in df_existentes.columns else []
opciones_tarifa = ["NUEVA"] + ids

def etiqueta_tarifa(x: str) -> str:
    if x == "NUEVA":
        return "➕ NUEVA TARIFA"
    # Buscar fila (defensivo)
    fila = df_existentes[df_existentes["ID_TARIFA"].astype(str) == str(x)]
    if fila.empty:
        return f"{x} | (no encontrada)"
    fila = fila.iloc[0]
    trp = str(fila.get("TRANSPORTISTA", ""))
    ori = str(fila.get("CIUDAD_ORIGEN", ""))
    des = str(fila.get("CIUDAD_DESTINO", ""))
    return f"{trp} | {ori} | {des}"

tarifa_id_sel = st.selectbox(
    "Selecciona tarifa",
    opciones_tarifa,
    format_func=etiqueta_tarifa,
    key="tarifa_id_captura"
)

# ---------------- MODO NUEVA ----------------
if tarifa_id_sel == "NUEVA":
    tarifa_base = None
    st.session_state["tarifa_base_tmp"] = None
    st.session_state["tarifa_cargada"] = False
    st.info("🆕 Modo captura de tarifa nueva")

# ---------------- MODO EDICIÓN ----------------
else:
    fila = df_existentes[df_existentes["ID_TARIFA"].astype(str) == str(tarifa_id_sel)]
    if fila.empty:
        st.warning("La tarifa seleccionada no se encontró en el filtrado actual.")
        tarifa_base = None
        st.session_state["tarifa_base_tmp"] = None
        st.session_state["tarifa_cargada"] = False
    else:
        tarifa_base = fila.iloc[0]
        st.session_state["tarifa_base_tmp"] = tarifa_base
        st.session_state["tarifa_cargada"] = False

        st.caption(
            f"Tarifa seleccionada | Transportista: {tarifa_base.get('TRANSPORTISTA','')} | "
            f"ALL IN: {tarifa_base.get('ALL_IN','')}"
        )

# =====================================================
# BOTÓN - ADMINISTRAR CATÁLOGOS
# =====================================================
if st.button("🛠️ Administrar catálogos", key="btn_ir_catalogos"):
    # ✅ Debe ser exactamente el nombre del archivo en /pages del repo
    st.switch_page("pages/1_Administrar_catalogos.py")

# =====================================================
# BLOQUE A - DATOS DEL SERVICIO
# =====================================================
st.subheader("📌 Datos del servicio")

with sqlite3.connect(DB_NAME) as conn:
    c1, c2, c3 = st.columns(3)

    tipo_operacion = c1.selectbox(
        "Tipo operación",
        pd.read_sql(
            "SELECT TIPO_OPERACION FROM CAT_TIPO_OPERACION ORDER BY TIPO_OPERACION",
            conn
        )["TIPO_OPERACION"].tolist(),
        key="tipo_operacion"
    )

    tipo_viaje = c2.selectbox(
        "Tipo viaje",
        ["SENCILLO", "REDONDO"],
        key="tipo_viaje"
    )

    c3.empty()

st.caption(f"DB PATH: {os.path.abspath(DB_NAME)}")
