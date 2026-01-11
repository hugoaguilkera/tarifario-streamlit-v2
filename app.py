# =====================================================
# APP STREAMLIT - TARIFARIO REAL (SQLite)
# Autor: Ingeniero Hugo
# =====================================================

import io
import sqlite3
import pandas as pd
import streamlit as st

# ===============================
# CONFIG
# ===============================
DB_NAME = "tarifario.db"

st.set_page_config(page_title="Tarifario Pactra", layout="wide")
st.title("📊 Tarifario Pactra")

# ===============================
# FUNCIONES BD
# ===============================
def cargar_bd_completa() -> pd.DataFrame:
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql("SELECT * FROM tarifario_estandar", conn)
    conn.close()
    return df


def obtener_columna_precio(tipo_operacion: str, tipo_viaje: str) -> str:
    if tipo_operacion in ["Exportación", "Importación"]:
        return "PRECIO_VIAJE_SENCILLO"
    if tipo_viaje == "REDONDO":
        return "PRECIO_VIAJE_REDONDO"
    return "PRECIO_VIAJE_SENCILLO"


def calcular_mejor_opcion(df: pd.DataFrame, col_precio: str):
    df_ok = df[
        df[col_precio].notna()
        & (df[col_precio] > 0)
        & df["ALL_IN"].notna()
        & (df["ALL_IN"] > 0)
    ].copy()

    if df_ok.empty:
        return None

    df_ok["PROFIT"] = df_ok[col_precio] - df_ok["ALL_IN"]
    df_ok["MARGEN"] = df_ok["PROFIT"] / df_ok[col_precio]
    return df_ok.sort_values("ALL_IN").iloc[0]


# ===============================
# BOTÓN REFRESCAR
# ===============================
if st.button("🔄 Refrescar base de datos"):
    st.rerun()

# ===============================
# CATÁLOGOS
# ===============================
st.divider()
st.subheader("⚙️ Filtros del servicio")

with sqlite3.connect(DB_NAME) as conn:
    tipos_operacion = pd.read_sql(
        "SELECT TIPO_OPERACION FROM CAT_TIPO_OPERACION ORDER BY TIPO_OPERACION",
        conn
    )["TIPO_OPERACION"].tolist()

    tipos_viaje = ["SENCILLO", "REDONDO"]

    tipos_unidad = pd.read_sql(
        "SELECT TIPO_UNIDAD FROM CAT_TIPO_UNIDAD ORDER BY TIPO_UNIDAD",
        conn
    )["TIPO_UNIDAD"].tolist()

    paises = pd.read_sql(
        "SELECT PAIS FROM CAT_PAISES ORDER BY PAIS",
        conn
    )["PAIS"].tolist()

# ===============================
# FILTROS
# ===============================
c1, c2, c3 = st.columns(3)
with c1:
    tipo_operacion = st.selectbox("Tipo de operación", tipos_operacion)
with c2:
    tipo_viaje = st.selectbox("Tipo de viaje", tipos_viaje)
with c3:
    tipo_unidad = st.selectbox("Tipo de unidad", tipos_unidad)

st.subheader("📍 Origen")
with sqlite3.connect(DB_NAME) as conn:
    pais_origen = st.selectbox("País origen", paises)

    estados_origen = pd.read_sql(
        """
        SELECT e.ESTADO
        FROM CAT_ESTADOS_NEW e
        JOIN CAT_PAISES p ON p.ID_PAIS = e.ID_PAIS
        WHERE p.PAIS = ?
        ORDER BY e.ESTADO
        """,
        conn, params=(pais_origen,)
    )["ESTADO"].tolist()

    estado_origen = st.selectbox("Estado origen", estados_origen)

    ciudades_origen = pd.read_sql(
        """
        SELECT c.CIUDAD
        FROM CAT_CIUDADES c
        JOIN CAT_ESTADOS_NEW e ON e.ID_ESTADO = c.ID_ESTADO
        WHERE e.ESTADO = ?
        ORDER BY c.CIUDAD
        """,
        conn, params=(estado_origen,)
    )["CIUDAD"].tolist()

    ciudad_origen = st.selectbox("Ciudad origen", ciudades_origen)

st.subheader("🏁 Destino")
with sqlite3.connect(DB_NAME) as conn:
    pais_destino = st.selectbox("País destino", paises)

    estados_destino = pd.read_sql(
        """
        SELECT e.ESTADO
        FROM CAT_ESTADOS_NEW e
        JOIN CAT_PAISES p ON p.ID_PAIS = e.ID_PAIS
        WHERE p.PAIS = ?
        ORDER BY e.ESTADO
        """,
        conn, params=(pais_destino,)
    )["ESTADO"].tolist()

    estado_destino = st.selectbox("Estado destino", estados_destino)

    ciudades_destino = pd.read_sql(
        """
        SELECT c.CIUDAD
        FROM CAT_CIUDADES c
        JOIN CAT_ESTADOS_NEW e ON e.ID_ESTADO = c.ID_ESTADO
        WHERE e.ESTADO = ?
        ORDER BY c.CIUDAD
        """,
        conn, params=(estado_destino,)
    )["CIUDAD"].tolist()

    ciudad_destino = st.selectbox("Ciudad destino", ciudades_destino)

# ===============================
# BUSCAR
# ===============================
st.divider()
if st.button("🔍 Buscar tarifas"):

    df_filtrado = df_base[
        (df_base["TIPO_DE_OPERACION"] == tipo_operacion)
        & (df_base["TIPO_DE_VIAJE"] == tipo_viaje)
        & (df_base["TIPO_UNIDAD"] == tipo_unidad)
        & (df_base["PAIS_ORIGEN"] == pais_origen)
        & (df_base["ESTADO_ORIGEN"] == estado_origen)
        & (df_base["CIUDAD_ORIGEN"] == ciudad_origen)
        & (df_base["PAIS_DESTINO"] == pais_destino)
        & (df_base["ESTADO_DESTINO"] == estado_destino)
        & (df_base["CIUDAD_DESTINO"] == ciudad_destino)
    ].copy()

    st.subheader("📌 Resultados filtrados")
    st.caption(f"Registros: {len(df_filtrado):,}")
    st.dataframe(df_filtrado, use_container_width=True, height=350)

    st.subheader("🏆 Mejor tarifa")
    col_precio = obtener_columna_precio(tipo_operacion, tipo_viaje)
    mejor = calcular_mejor_opcion(df_filtrado, col_precio)

    if mejor is None:
        st.warning("No hay tarifas válidas.")
    else:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Transportista", mejor["TRANSPORTISTA"])
        c2.metric("Operación", tipo_operacion)
        c3.metric("Viaje", tipo_viaje)
        c4.metric("Precio", f"${mejor[col_precio]:,.0f}")
        c5.metric("ALL IN", f"${mejor['ALL_IN']:,.0f}")
        st.caption(f"Margen estimado: {mejor['MARGEN']*100:.1f}%")

    if not df_filtrado.empty:
        buffer = io.BytesIO()
        df_filtrado.to_excel(buffer, index=False)
        buffer.seek(0)

        st.download_button(
            "⬇ Descargar tarifario filtrado",
            data=buffer,
            file_name="tarifario_filtrado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
# ===============================
# REPORTE COMPLETO (AL FINAL)
# ===============================
st.divider()
st.subheader("📋 Tarifario completo (BD real)")

df_base = cargar_bd_completa()
st.caption(f"Registros totales: {len(df_base):,}")

st.dataframe(
    df_base,
    use_container_width=True,
    height=500
)

















