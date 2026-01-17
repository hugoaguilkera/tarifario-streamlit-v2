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

# =====================================================
# 🚛 TRANSPORTISTAS
# =====================================================
st.divider()
st.subheader("🚛 Transportistas")

# --- Alta ---
c1, c2 = st.columns([3, 1])
with c1:
    nuevo_transportista = st.text_input(
        "Nuevo transportista",
        placeholder="Ej. 100 LOGISTICS / UNIMEX / ARLEX",
        key="cat_nuevo_transportista"
    )
with c2:
    if st.button("➕ Agregar transportista", key="cat_btn_add_transportista"):
        nuevo = (nuevo_transportista or "").strip().upper()

        if not nuevo:
            st.warning("Escribe un nombre de transportista.")
        else:
            existe = df_sql(
                "SELECT 1 FROM CAT_TRANSPORTISTAS WHERE TRANSPORTISTA = ? LIMIT 1",
                (nuevo,)
            )
            if not existe.empty:
                st.warning("⚠️ El transportista ya existe.")
            else:
                exec_sql(
                    "INSERT INTO CAT_TRANSPORTISTAS (TRANSPORTISTA, ACTIVO) VALUES (?, 1)",
                    (nuevo,)
                )
                st.success("✅ Transportista agregado correctamente.")
                st.rerun()

# --- Tabla (activos e inactivos) ---
df_transportistas = df_sql(
    """
    SELECT TRANSPORTISTA, ACTIVO
    FROM CAT_TRANSPORTISTAS
    ORDER BY TRANSPORTISTA
    """
)
st.dataframe(df_transportistas, use_container_width=True)

# =====================================================
# 🚫 Desactivar transportista
# =====================================================
st.subheader("🚫 Desactivar transportista")

df_trp_activos = df_sql(
    "SELECT TRANSPORTISTA FROM CAT_TRANSPORTISTAS WHERE ACTIVO = 1 ORDER BY TRANSPORTISTA"
)

if df_trp_activos.empty:
    st.info("No hay transportistas activos.")
else:
    transportista_off = st.selectbox(
        "Selecciona transportista a desactivar",
        df_trp_activos["TRANSPORTISTA"].tolist(),
        key="cat_transportista_off"
    )

    confirmar_trp = st.checkbox(
        "Confirmo que quiero desactivar este transportista",
        key="cat_conf_trp_off"
    )

    if st.button("❌ Desactivar", key="cat_btn_off_transportista"):
        if not confirmar_trp:
            st.error("Debes confirmar antes de desactivar.")
        else:
            exec_sql(
                "UPDATE CAT_TRANSPORTISTAS SET ACTIVO = 0 WHERE TRANSPORTISTA = ?",
                (transportista_off,)
            )
            st.success("✅ Transportista desactivado.")
            st.rerun()

# =====================================================
# ♻️ Reactivar transportista
# =====================================================
st.subheader("♻️ Reactivar transportista")

df_trp_inactivos = df_sql(
    "SELECT TRANSPORTISTA FROM CAT_TRANSPORTISTAS WHERE ACTIVO = 0 ORDER BY TRANSPORTISTA"
)

if df_trp_inactivos.empty:
    st.info("No hay transportistas inactivos.")
else:
    transportista_on = st.selectbox(
        "Selecciona transportista a reactivar",
        df_trp_inactivos["TRANSPORTISTA"].tolist(),
        key="cat_transportista_on"
    )

    if st.button("✅ Reactivar", key="cat_btn_on_transportista"):
        exec_sql(
            "UPDATE CAT_TRANSPORTISTAS SET ACTIVO = 1 WHERE TRANSPORTISTA = ?",
            (transportista_on,)
        )
        st.success("✅ Transportista reactivado.")
        st.rerun()

# =====================================================
# 📌 NOTA PROFESIONAL
# =====================================================
st.caption(
    "Este módulo es el punto único para dar de alta nuevos valores. "
    "Las pantallas de captura SOLO seleccionan."
)
# =====================================================
# ⚙️ TIPO DE OPERACIÓN
# =====================================================
st.divider()
st.subheader("⚙️ Tipo de operación")

c1, c2 = st.columns([3, 1])
with c1:
    nuevo_tipo_operacion = st.text_input(
        "Nuevo tipo de operación",
        placeholder="Ej. EXPORTACIÓN / IMPORTACIÓN / CROSS DOCK",
        key="cat_nuevo_tipo_operacion"
    )
with c2:
    if st.button("➕ Agregar tipo de operación", key="cat_btn_add_tipo_operacion"):
        nuevo = (nuevo_tipo_operacion or "").strip().upper()

        if not nuevo:
            st.warning("Escribe un tipo de operación.")
        else:
            existe = df_sql(
                "SELECT 1 FROM CAT_TIPO_OPERACION WHERE TIPO_OPERACION = ? LIMIT 1",
                (nuevo,)
            )
            if not existe.empty:
                st.warning("⚠️ El tipo de operación ya existe.")
            else:
                exec_sql(
                    "INSERT INTO CAT_TIPO_OPERACION (TIPO_OPERACION) VALUES (?)",
                    (nuevo,)
                )
                st.success("✅ Tipo de operación agregado correctamente.")
                st.rerun()

df_tipo_operacion = df_sql(
    "SELECT TIPO_OPERACION FROM CAT_TIPO_OPERACION ORDER BY TIPO_OPERACION"
)
st.dataframe(df_tipo_operacion, use_container_width=True)
# =====================================================
# 🚚 TIPO DE VIAJE
# =====================================================
st.divider()
st.subheader("🚚 Tipo de viaje")

c1, c2 = st.columns([3, 1])
with c1:
    nuevo_tipo_viaje = st.text_input(
        "Nuevo tipo de viaje",
        placeholder="Ej. SENCILLO / REDONDO / MULTI",
        key="cat_nuevo_tipo_viaje"
    )
with c2:
    if st.button("➕ Agregar tipo de viaje", key="cat_btn_add_tipo_viaje"):
        nuevo = (nuevo_tipo_viaje or "").strip().upper()
        if not nuevo:
            st.warning("Escribe un tipo de viaje.")
        else:
            existe = df_sql(
                "SELECT 1 FROM CAT_TIPO_VIAJE WHERE TIPO_VIAJE = ? LIMIT 1",
                (nuevo,)
            )
            if not existe.empty:
                st.warning("⚠️ El tipo de viaje ya existe.")
            else:
                exec_sql(
                    "INSERT INTO CAT_TIPO_VIAJE (TIPO_VIAJE) VALUES (?)",
                    (nuevo,)
                )
                st.success("✅ Tipo de viaje agregado correctamente.")
                st.rerun()

df_tipo_viaje = df_sql("SELECT TIPO_VIAJE FROM CAT_TIPO_VIAJE ORDER BY TIPO_VIAJE")
st.dataframe(df_tipo_viaje, use_container_width=True)

# =====================================================
# 🆕 ALTA DE PAÍS / ESTADO / CIUDAD
# =====================================================
st.subheader("🆕 Alta de País / Estado / Ciudad")
# -----------------
# 🌍 Alta País
# -----------------
st.markdown("### 🌍 Nuevo país")

nuevo_pais = st.text_input(
    "Nombre del país",
    placeholder="Ej. CAN / USA / MEX",
    key="nuevo_pais"
)

if st.button("➕ Agregar país", key="btn_add_pais"):
    pais = (nuevo_pais or "").strip().upper()

    if not pais:
        st.warning("Escribe un país.")
    else:
        existe = pd.read_sql(
            "SELECT 1 FROM CAT_PAISES WHERE PAIS = ? LIMIT 1",
            conn,
            params=(pais,)
        )

        if not existe.empty:
            st.warning("⚠️ El país ya existe.")
        else:
            conn.execute(
                "INSERT INTO CAT_PAISES (PAIS, ACTIVO) VALUES (?, 1)",
                (pais,)
            )
            conn.commit()
            st.success("✅ País agregado.")
            st.rerun()
# -----------------
# 🗺️ Alta Estado
# -----------------
st.markdown("### 🗺️ Nuevo estado")

df_paises_all = pd.read_sql(
    "SELECT ID_PAIS, PAIS FROM CAT_PAISES WHERE ACTIVO = 1 ORDER BY PAIS",
    conn
)

if df_paises_all.empty:
    st.warning("⚠️ No hay países activos. Primero agrega un país.")
else:
    pais_estado = st.selectbox(
        "País del estado",
        df_paises_all["PAIS"].tolist(),
        key="pais_estado"
    )

    nuevo_estado = st.text_input(
        "Nombre del estado",
        placeholder="Ej. ALBERTA / TEXAS / NUEVO LEÓN",
        key="nuevo_estado"
    )

    if st.button("➕ Agregar estado", key="btn_add_estado"):
        estado = (nuevo_estado or "").strip().upper()
        id_pais = int(df_paises_all.loc[df_paises_all["PAIS"] == pais_estado, "ID_PAIS"].iloc[0])

        if not estado:
            st.warning("Escribe un estado.")
        else:
            existe = pd.read_sql(
                """
                SELECT 1
                FROM CAT_ESTADOS_NEW
                WHERE ESTADO = ? AND ID_PAIS = ?
                LIMIT 1
                """,
                conn,
                params=(estado, id_pais)
            )

            if not existe.empty:
                st.warning("⚠️ El estado ya existe para ese país.")
            else:
                conn.execute(
                    """
                    INSERT INTO CAT_ESTADOS_NEW (ESTADO, ID_PAIS, ACTIVO)
                    VALUES (?, ?, 1)
                    """,
                    (estado, id_pais)
                )
                conn.commit()
                st.success("✅ Estado agregado.")
                st.rerun()
# -----------------
# 🏙️ Alta Ciudad
# -----------------
st.markdown("### 🏙️ Nueva ciudad")

df_estados_all = pd.read_sql(
    """
    SELECT E.ID_ESTADO, E.ESTADO, P.PAIS
    FROM CAT_ESTADOS_NEW E
    JOIN CAT_PAISES P ON P.ID_PAIS = E.ID_PAIS
    WHERE E.ACTIVO = 1
    ORDER BY P.PAIS, E.ESTADO
    """,
    conn
)

if df_estados_all.empty:
    st.warning("⚠️ No hay estados activos. Primero agrega un estado.")
else:
    estado_ciudad = st.selectbox(
        "Estado de la ciudad",
        df_estados_all["ESTADO"].tolist(),
        key="estado_ciudad"
    )

    nueva_ciudad = st.text_input(
        "Nombre de la ciudad",
        placeholder="Ej. CALGARY / ATLANTA / MONTERREY",
        key="nueva_ciudad"
    )

    if st.button("➕ Agregar ciudad", key="btn_add_ciudad"):
        ciudad = (nueva_ciudad or "").strip().upper()
        id_estado = int(
            df_estados_all.loc[df_estados_all["ESTADO"] == estado_ciudad, "ID_ESTADO"].iloc[0]
        )

        if not ciudad:
            st.warning("Escribe una ciudad.")
        else:
            existe = pd.read_sql(
                """
                SELECT 1
                FROM CAT_CIUDADES
                WHERE CIUDAD = ? AND ID_ESTADO = ?
                LIMIT 1
                """,
                conn,
                params=(ciudad, id_estado)
            )

            if not existe.empty:
                st.warning("⚠️ La ciudad ya existe para ese estado.")
            else:
                conn.execute(
                    """
                    INSERT INTO CAT_CIUDADES (CIUDAD, ID_ESTADO, ACTIVO)
                    VALUES (?, ?, 1)
                    """,
                    (ciudad, id_estado)
                )
                conn.commit()
                st.success("✅ Ciudad agregada.")
                st.rerun()
# ============================
# 🌍 PAÍS / ESTADO / CIUDAD (NORMALIZADO)
# ============================
st.divider()
st.subheader("🌍 País / Estado / Ciudad (vista)")

# 🌍 PAÍS
df_paises = pd.read_sql(
    """
    SELECT ID_PAIS, PAIS
    FROM CAT_PAISES
    WHERE ACTIVO = 1
    ORDER BY PAIS
    """,
    conn
)

if df_paises.empty:
    st.error("❌ No hay países activos en el catálogo.")
    st.stop()

pais_sel = st.selectbox(
    "🌍 País",
    df_paises["PAIS"].tolist(),
    key="pais_sel_norm"
)

id_pais = int(df_paises.loc[df_paises["PAIS"] == pais_sel, "ID_PAIS"].iloc[0])

# 🗺️ ESTADO
df_estados = pd.read_sql(
    """
    SELECT ID_ESTADO, ESTADO
    FROM CAT_ESTADOS_NEW
    WHERE ID_PAIS = ?
      AND ACTIVO = 1
    ORDER BY ESTADO
    """,
    conn,
    params=(id_pais,)
)

if df_estados.empty:
    st.warning("⚠️ No hay estados registrados para este país.")
    id_estado = None
else:
    estado_sel = st.selectbox(
        "🗺️ Estado",
        df_estados["ESTADO"].tolist(),
        key="estado_sel_norm"
    )
    id_estado = int(df_estados.loc[df_estados["ESTADO"] == estado_sel, "ID_ESTADO"].iloc[0])

# 🏙️ CIUDAD
if id_estado is None:
    st.info("Selecciona un estado para ver ciudades.")
else:
    df_ciudades = pd.read_sql(
        """
        SELECT ID_CIUDAD, CIUDAD
        FROM CAT_CIUDADES
        WHERE ID_ESTADO = ?
          AND ACTIVO = 1
        ORDER BY CIUDAD
        """,
        conn,
        params=(id_estado,)
    )

    if df_ciudades.empty:
        st.warning("⚠️ No hay ciudades registradas para este estado.")
    else:
        ciudad_sel = st.selectbox(
            "🏙️ Ciudad",
            df_ciudades["CIUDAD"].tolist(),
            key="ciudad_sel_norm"
        )
        id_ciudad = int(df_ciudades.loc[df_ciudades["CIUDAD"] == ciudad_sel, "ID_CIUDAD"].iloc[0])

        # (Opcional) Mostrar IDs para debug / auditoría
        st.caption(f"IDs: país={id_pais} | estado={id_estado} | ciudad={id_ciudad}")
# =====================================================
# 🚚 TIPO DE UNIDAD
# =====================================================
st.divider()
st.subheader("🚚 Tipo de unidad")

nueva_unidad = st.text_input(
    "Nuevo tipo de unidad",
    placeholder="Ej. TORTON / RABON / PLATAFORMA 53 / CAJA REFRIGERADA 48",
    key="nueva_unidad"
)

if st.button("➕ Agregar tipo de unidad", key="btn_add_unidad"):
    unidad = (nueva_unidad or "").strip().upper()

    if not unidad:
        st.warning("Escribe un tipo de unidad.")
    else:
        existe = pd.read_sql(
            "SELECT 1 FROM CAT_TIPO_UNIDAD WHERE TIPO_UNIDAD = ? LIMIT 1",
            conn,
            params=(unidad,)
        )

        if not existe.empty:
            st.warning("⚠️ El tipo de unidad ya existe.")
        else:
            conn.execute(
                "INSERT INTO CAT_TIPO_UNIDAD (TIPO_UNIDAD) VALUES (?)",
                (unidad,)
            )
            conn.commit()
            st.success("✅ Tipo de unidad agregado.")
            st.rerun()

df_unidades = pd.read_sql(
    "SELECT TIPO_UNIDAD FROM CAT_TIPO_UNIDAD ORDER BY TIPO_UNIDAD",
    conn
)
st.dataframe(df_unidades, use_container_width=True)

# Cierre seguro
try:
    conn.close()
except Exception:
    pass



