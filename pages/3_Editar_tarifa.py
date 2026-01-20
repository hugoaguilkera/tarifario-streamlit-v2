# =====================================================
# EDITAR TARIFA – NIVEL ERP (SAP STYLE)
# Autor: Ingeniero Hugo
# =====================================================

import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime

# -----------------------------------------------------
# CONFIG
# -----------------------------------------------------
st.set_page_config(page_title="Editar tarifa", layout="wide")

DB_NAME = "tarifario.db"
REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / DB_NAME

st.title("✏️ Edición de tarifa (Versionado ERP)")
st.caption("✔ No se edita en vivo | ✔ Historial intacto | ✔ Nueva versión")

# -----------------------------------------------------
# VALIDACIÓN DE CONTEXTO
# -----------------------------------------------------
if "id_tarifa_editar" not in st.session_state:
    st.warning("Debes seleccionar una tarifa desde **Captura de tarifas**.")
    st.stop()

id_tarifa = st.session_state["id_tarifa_editar"]

# -----------------------------------------------------
# CARGA TARIFA BASE
# -----------------------------------------------------
with sqlite3.connect(str(DB_PATH)) as conn:
    df_base = pd.read_sql(
        "SELECT * FROM tarifario_estandar WHERE ID_TARIFA = ?",
        conn,
        params=(id_tarifa,)
    )

if df_base.empty:
    st.error("La tarifa no existe o fue eliminada.")
    st.stop()

tarifa_base = df_base.iloc[0]

st.success(f"Editando tarifa ID {id_tarifa} | Versión {tarifa_base.get('VERSION', 1)}")

# -----------------------------------------------------
# FORMULARIO (ERP STYLE)
# -----------------------------------------------------
st.subheader("📌 Datos principales")

c1, c2, c3 = st.columns(3)

transportista = c1.text_input(
    "Transportista",
    value=str(tarifa_base["TRANSPORTISTA"])
)

cliente = c2.text_input(
    "Cliente",
    value=str(tarifa_base["CLIENTE"])
)

tipo_unidad = c3.text_input(
    "Tipo unidad",
    value=str(tarifa_base["TIPO_UNIDAD"])
)

st.divider()

st.subheader("📍 Ruta")

c1, c2 = st.columns(2)

ciudad_origen = c1.text_input(
    "Ciudad origen",
    value=str(tarifa_base["CIUDAD_ORIGEN"])
)

ciudad_destino = c2.text_input(
    "Ciudad destino",
    value=str(tarifa_base["CIUDAD_DESTINO"])
)

st.divider()

st.subheader("💰 Costos")

def nf(x):
    try:
        return float(x)
    except:
        return 0.0

c1, c2, c3, c4 = st.columns(4)

usa_freight = c1.number_input("USA Freight", value=nf(tarifa_base["USA_FREIGHT"]))
mexican_freight = c2.number_input("Mexican Freight", value=nf(tarifa_base["MEXICAN_FREIGHT"]))
crossing = c3.number_input("Crossing", value=nf(tarifa_base["CROSSING"]))
border_crossing = c4.number_input("Border Crossing", value=nf(tarifa_base["BORDER_CROSSING"]))

c5, c6, c7, c8 = st.columns(4)

aduanas = c5.number_input("Aduanas", value=nf(tarifa_base["ADUANAS_ARANCELES"]))
insurance = c6.number_input("Seguro", value=nf(tarifa_base["INSURANCE"]))
peajes = c7.number_input("Peajes", value=nf(tarifa_base["PEAJES"]))
maniobras = c8.number_input("Maniobras", value=nf(tarifa_base["MANIOBRAS"]))

all_in = (
    usa_freight + mexican_freight + crossing + border_crossing +
    aduanas + insurance + peajes + maniobras
)

st.metric("ALL IN", f"${all_in:,.2f}")

st.divider()

st.subheader("🧾 Motivo del cambio (OBLIGATORIO)")
motivo = st.text_area(
    "Describe por qué se genera esta nueva versión",
    placeholder="Ejemplo: incremento de peajes Q2 / renegociación proveedor"
)

if not motivo.strip():
    st.warning("El motivo es obligatorio para versionar.")
    st.stop()

# -----------------------------------------------------
# GUARDADO ERP (VERSIONADO REAL)
# -----------------------------------------------------
st.subheader("💾 Guardar nueva versión")

if st.button("Guardar nueva versión"):
    with sqlite3.connect(str(DB_PATH)) as conn:
        cur = conn.cursor()

        # 1️⃣ Desactivar versión anterior
        cur.execute(
            "UPDATE tarifario_estandar SET ACTIVA = 0 WHERE ID_TARIFA = ?",
            (id_tarifa,)
        )

        # 2️⃣ Insertar nueva versión
        cur.execute(
            """
            INSERT INTO tarifario_estandar (
                VERSION,
                ACTIVA,
                FECHA_CAMBIO,
                MOTIVO_CAMBIO,

                TRANSPORTISTA,
                CLIENTE,
                TIPO_UNIDAD,

                CIUDAD_ORIGEN,
                CIUDAD_DESTINO,

                USA_FREIGHT,
                MEXICAN_FREIGHT,
                CROSSING,
                BORDER_CROSSING,
                ADUANAS_ARANCELES,
                INSURANCE,
                PEAJES,
                MANIOBRAS,
                ALL_IN
            )
            VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(tarifa_base.get("VERSION", 1)) + 1,
                datetime.now().isoformat(timespec="seconds"),
                motivo,

                transportista,
                cliente,
                tipo_unidad,

                ciudad_origen,
                ciudad_destino,

                usa_freight,
                mexican_freight,
                crossing,
                border_crossing,
                aduanas,
                insurance,
                peajes,
                maniobras,
                all_in
            )
        )

        conn.commit()

    st.success("✅ Nueva versión creada correctamente (ERP Style)")
    st.session_state.pop("id_tarifa_editar", None)
    st.switch_page("pages/2_Captura_tarifas.py")


