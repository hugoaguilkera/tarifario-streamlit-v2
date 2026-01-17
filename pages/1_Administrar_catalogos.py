# =====================================================
# PAGES - ADMINISTRAR CATÁLOGOS
# BLOQUE 1 - IMPORTS + CONFIG + BD (Cloud/Local)
# =====================================================

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Catálogos", layout="wide")

st.title("🛠️ Administración de catálogos")
st.info("Aquí se administran clientes, transportistas y futuros catálogos.")

# --- DB robusto (Cloud y local) ---
REPO_ROOT = Path(__file__).resolve().parents[1]   # repo/
DB_PATH = REPO_ROOT / "tarifario.db"             # repo/tarifario.db

if not DB_PATH.exists():
    st.error(f"❌ No encuentro la BD en: {DB_PATH}")
    st.stop()

conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)

def df_sql(query: str, params: tuple = ()) -> pd.DataFrame:
    return pd.read_sql(query, conn, params=params)

def exec_sql(query: str, params: tuple = ()) -> None:
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()

# (Opcional) Diagnóstico rápido
with st.expander("🔎 Diagnóstico", expanded=False):
    st.caption(f"DB: {DB_PATH}")
    tablas = df_sql("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    st.dataframe(tablas, use_container_width=True)

# Cierre seguro (al final del archivo ponlo también)
# conn.close()


# =====================================================
# BLOQUE 1 - BD: path robusto (Cloud / Local)
# =====================================================
REPO_ROOT = Path(__file__).resolve().parents[1]          # repo/
DB_PATH = REPO_ROOT / "tarifario.db"                    # repo/tarifario.db

st.caption(f"DB: {DB_PATH}")
if not DB_PATH.exists():
    st.error("❌ No encuentro tarifario.db dentro del repo.")
    st.stop()

conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)

def df_sql(query: str, params: tuple = ()) -> pd.DataFrame:
    return pd.read_sql(query, conn, params=params)

def exec_sql(query: str, params: tuple = ()) -> None:
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()

# =====================================================
# BLOQUE 2 - DIAGNÓSTICO (para que NUNCA quede blanco)
# =====================================================
with st.expander("🔎 Diagnóstico"):
    tablas = df_sql("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    st.write("Tablas detectadas:")
    st.dataframe(tablas, use_container_width=True)

## =====================================================
# 👤 CLIENTES
# =====================================================
st.subheader("👤 Clientes")

# --- Alta de cliente ---
c1, c2 = st.columns([3, 1])
with c1:
    nuevo_cliente = st.text_input(
        "Nuevo cliente",
        placeholder="Ej. SUNGWOO / DONGHEE / NIFCO",
        key="cat_nuevo_cliente"
    )
with c2:
    if st.button("➕ Agregar cliente", key="cat_btn_add_cliente"):
        nuevo = (nuevo_cliente or "").strip().upper()

        if not nuevo:
            st.warning("Escribe un nombre de cliente.")
        else:
            existe = df_sql(
                "SELECT 1 FROM CAT_CLIENTES WHERE CLIENTE = ? LIMIT 1",
                (nuevo,)
            )
            if not existe.empty:
                st.warning("⚠️ El cliente ya existe.")
            else:
                exec_sql(
                    "INSERT INTO CAT_CLIENTES (CLIENTE, ACTIVO) VALUES (?, 1)",
                    (nuevo,)
                )
                st.success("✅ Cliente agregado correctamente.")
                st.rerun()

# --- Tabla de clientes ---
df_clientes = df_sql(
    """
    SELECT CLIENTE, ACTIVO
    FROM CAT_CLIENTES
    ORDER BY CLIENTE
    """
)
st.dataframe(df_clientes, use_container_width=True)

# =====================================================
# 🗑️ Desactivar cliente (confirmación)
# =====================================================
st.subheader("🗑️ Desactivar cliente (confirmación)")

df_activos = df_sql(
    "SELECT CLIENTE FROM CAT_CLIENTES WHERE ACTIVO = 1 ORDER BY CLIENTE"
)

if df_activos.empty:
    st.info("No hay clientes activos para desactivar.")
else:
    cliente_desactivar = st.selectbox(
        "Selecciona cliente a desactivar",
        df_activos["CLIENTE"].tolist(),
        key="cat_cliente_desactivar"
    )

    # --- Validar si tiene tarifas ---
    try:
        tarifas = df_sql(
            "SELECT COUNT(*) AS TOTAL FROM tarifario_estandar WHERE CLIENTE = ?",
            (cliente_desactivar,)
        )["TOTAL"].iloc[0]
    except Exception:
        tarifas = "N/A"

    st.warning(
        f"⚠️ Este cliente tiene {tarifas} tarifa(s) registrada(s). "
        "No se borrarán, pero el cliente quedará inactivo."
    )

    confirmacion = st.checkbox(
        "Entiendo el impacto y deseo continuar",
        key="cat_conf_desactivar"
    )

    if st.button("🚫 Desactivar cliente", key="cat_btn_desactivar"):
        if not confirmacion:
            st.error("Debes confirmar antes de continuar.")
        else:
            exec_sql(
                "UPDATE CAT_CLIENTES SET ACTIVO = 0 WHERE CLIENTE = ?",
                (cliente_desactivar,)
            )
            st.success("✅ Cliente desactivado correctamente.")
            st.rerun()

# =====================================================
# ♻️ Reactivar cliente
# =====================================================
st.subheader("♻️ Reactivar cliente")

df_inactivos = df_sql(
    "SELECT CLIENTE FROM CAT_CLIENTES WHERE ACTIVO = 0 ORDER BY CLIENTE"
)

if df_inactivos.empty:
    st.info("No hay clientes inactivos.")
else:
    cliente_reactivar = st.selectbox(
        "Selecciona cliente a reactivar",
        df_inactivos["CLIENTE"].tolist(),
        key="cat_cliente_reactivar"
    )

    if st.button("✅ Reactivar cliente", key="cat_btn_reactivar"):
        exec_sql(
            "UPDATE CAT_CLIENTES SET ACTIVO = 1 WHERE CLIENTE = ?",
            (cliente_reactivar,)
        )
        st.success("✅ Cliente reactivado correctamente.")
        st.rerun()


conn.close()


