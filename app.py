# =====================================================
# APP STREAMLIT - TARIFARIO REAL (SQLite)
# Autor: Ingeniero Hugo
# =====================================================

# =====================================================
# BLOQUE 1 - IMPORTS Y CONFIGURACIÓN
# =====================================================
import io
import sqlite3

import pandas as pd
import streamlit as st

DB_NAME = "tarifario.db"

st.set_page_config(page_title="Tarifario Pactra", layout="wide")
st.title("📊 Tarifario Pactra")

# =====================================================
# BLOQUE 2 - ESTILOS
# =====================================================
st.markdown(
    """
<style>
.card {
    background: #0b1220;
    padding: 24px;
    border-radius: 14px;
    box-shadow: 0 0 20px rgba(0,255,120,0.2);
}
.metric {
    background: #111827;
    padding: 10px;
    border-radius: 8px;
    color: white;
}
.highlight {
    color: #22c55e;
    font-weight: bold;
}
</style>
""",
    unsafe_allow_html=True,
)
# =====================================================
# BLOQUE 3 - FUNCIONES BD
# =====================================================

@st.cache_data
def cargar_bd_completa() -> pd.DataFrame:
    """
    Carga TODA la BD.
    El filtrado por ACTIVA se hace en los bloques de negocio,
    no aquí (evita romper vistas y reportes).
    """
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql(
        "SELECT * FROM tarifario_estandar",
        conn
    )
    conn.close()
    return df


@st.cache_data
def cargar_rutas() -> pd.DataFrame:
    """
    Catálogo de rutas (sin filtrar por ACTIVA todavía)
    """
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql(
        """
        SELECT DISTINCT
            CIUDAD_ORIGEN AS origen,
            CIUDAD_DESTINO AS destino
        FROM tarifario_estandar
        WHERE CIUDAD_ORIGEN IS NOT NULL
          AND CIUDAD_DESTINO IS NOT NULL
        ORDER BY origen, destino
        """,
        conn,
    )
    conn.close()
    return df


def refrescar_bd():
    cargar_bd_completa.clear()
    cargar_rutas.clear()

# =====================================================
# BLOQUE 4 - LÓGICA DE NEGOCIO
# =====================================================
def obtener_columna_precio(tipo_operacion: str, tipo_viaje: str) -> str:
    if tipo_operacion in ["Exportación", "Importación"]:
        return "PRECIO_VIAJE_SENCILLO"
    if tipo_viaje == "REDONDO":
        return "PRECIO_VIAJE_REDONDO"
    return "PRECIO_VIAJE_SENCILLO"


def calcular_mejor_opcion(df: pd.DataFrame, col_precio: str) -> pd.Series | None:
    df_valida = df[
        df[col_precio].notna()
        & (df[col_precio] > 0)
        & df["ALL_IN"].notna()
        & (df["ALL_IN"] > 0)
    ].copy()

    if df_valida.empty:
        return None

    df_valida["PRECIO_USADO"] = df_valida[col_precio]
    df_valida["PROFIT"] = df_valida["PRECIO_USADO"] - df_valida["ALL_IN"]
    df_valida["MARGEN"] = df_valida["PROFIT"] / df_valida["PRECIO_USADO"]
    return df_valida.sort_values("ALL_IN").iloc[0]

# =====================================================
# BLOQUE 5 - FILTROS + CÁLCULO + RESULTADO (BUSCADOR REAL)
# =====================================================

# -------------------------------
# SESSION STATE
# -------------------------------
if "df_filtrado" not in st.session_state:
    st.session_state["df_filtrado"] = pd.DataFrame()

if "configuracion" not in st.session_state:
    st.session_state["configuracion"] = {}

# -------------------------------
# CATÁLOGOS
# -------------------------------
with sqlite3.connect(DB_NAME) as conn:
    clientes = ["Todos"] + pd.read_sql(
        "SELECT CLIENTE FROM CAT_CLIENTES ORDER BY CLIENTE", conn
    )["CLIENTE"].tolist()

    transportistas = ["Todos"] + pd.read_sql(
        "SELECT DISTINCT TRANSPORTISTA FROM tarifario_estandar ORDER BY TRANSPORTISTA",
        conn
    )["TRANSPORTISTA"].tolist()

    tipos_operacion = ["Todos"] + pd.read_sql(
        "SELECT TIPO_OPERACION FROM CAT_TIPO_OPERACION ORDER BY TIPO_OPERACION",
        conn
    )["TIPO_OPERACION"].tolist()

    tipos_viaje = ["Todos", "SENCILLO", "REDONDO"]

    tipos_unidad = ["Todos"] + pd.read_sql(
        "SELECT TIPO_UNIDAD FROM CAT_TIPO_UNIDAD ORDER BY TIPO_UNIDAD",
        conn
    )["TIPO_UNIDAD"].tolist()

    paises = ["Todos"] + pd.read_sql(
        "SELECT PAIS FROM CAT_PAISES ORDER BY PAIS",
        conn
    )["PAIS"].tolist()

# -------------------------------
# CONFIGURACIÓN DEL SERVICIO
# -------------------------------
st.subheader("⚙️ Configuración del servicio")

c1, c2, c3 = st.columns(3)
with c1:
    cliente_sel = st.selectbox("Cliente", clientes)
with c2:
    transportista_sel = st.selectbox("Transportista", transportistas)
with c3:
    tipo_operacion = st.selectbox("Tipo de operación", tipos_operacion)

c4, c5, c6 = st.columns(3)
with c4:
    tipo_viaje = st.selectbox("Tipo de viaje", tipos_viaje)
with c5:
    tipo_unidad = st.selectbox("Tipo de unidad", tipos_unidad)
with c6:
    st.empty()

# -------------------------------
# ORIGEN
# -------------------------------
st.subheader("📍 Origen")
pais_origen = st.selectbox("País origen", paises)
estado_origen = st.text_input("Estado origen", "").strip().upper()
ciudad_origen = st.text_input("Ciudad origen", "").strip().upper()

# -------------------------------
# DESTINO
# -------------------------------
st.subheader("🏁 Destino")
pais_destino = st.selectbox("País destino", paises)
estado_destino = st.text_input("Estado destino", "").strip().upper()
ciudad_destino = st.text_input("Ciudad destino", "").strip().upper()

# -------------------------------
# REPARTO / DESTINOS
# -------------------------------
st.subheader("📦 Reparto")

num_destinos = st.number_input(
    "Número de destinos",
    min_value=1,
    value=1,
    step=1
)

# -------------------------------
# ACCIÓN BUSCAR (ÚNICA Y CORRECTA)
# -------------------------------
if st.button("🔍 Buscar tarifas"):

    df_filtrado = cargar_bd_completa()

    # ✅ Normalizar nombres de columnas (acentos/variantes)
    df_filtrado.columns = [
        c.replace("Ó","O").replace("Á","A").replace("É","E").replace("Í","I").replace("Ú","U")
        for c in df_filtrado.columns
    ]

    # -------- FILTROS DINÁMICOS (ALL = no filtra) --------
    if cliente_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado["CLIENTE"] == cliente_sel]

    if transportista_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado["TRANSPORTISTA"] == transportista_sel]

    if tipo_operacion != "Todos":
        df_filtrado = df_filtrado[df_filtrado["TIPO_DE_OPERACION"] == tipo_operacion]

    if tipo_viaje != "Todos":
        df_filtrado = df_filtrado[df_filtrado["TIPO_DE_VIAJE"] == tipo_viaje]

    if tipo_unidad != "Todos":
        df_filtrado = df_filtrado[df_filtrado["TIPO_UNIDAD"] == tipo_unidad]

    if pais_origen != "Todos":
        df_filtrado = df_filtrado[df_filtrado["PAIS_ORIGEN"] == pais_origen]

    if estado_origen:
        df_filtrado = df_filtrado[df_filtrado["ESTADO_ORIGEN"] == estado_origen]

    if ciudad_origen:
        df_filtrado = df_filtrado[df_filtrado["CIUDAD_ORIGEN"] == ciudad_origen]

    if pais_destino != "Todos":
        df_filtrado = df_filtrado[df_filtrado["PAIS_DESTINO"] == pais_destino]

    if estado_destino:
        df_filtrado = df_filtrado[df_filtrado["ESTADO_DESTINO"] == estado_destino]

    if ciudad_destino:
        df_filtrado = df_filtrado[df_filtrado["CIUDAD_DESTINO"] == ciudad_destino]

    st.session_state["df_filtrado"] = df_filtrado
    st.session_state["configuracion"] = {
        "tipo_operacion": tipo_operacion,
        "tipo_viaje": tipo_viaje,
        "tipo_unidad": tipo_unidad,
    }

# -------------------------------
# RESULTADOS
# -------------------------------
if not st.session_state["df_filtrado"].empty:
    st.divider()
    st.subheader("📋 Resultados")

    df_resultado = st.session_state["df_filtrado"].copy()

    # 🔒 SIN reparto (core estable)
    df_resultado["TOTAL_CON_REPARTO"] = df_resultado["ALL_IN"]

    st.dataframe(
        df_resultado[
            [
                "TRANSPORTISTA",
                "CLIENTE",
                "ALL_IN",
                "TOTAL_CON_REPARTO"
            ]
        ],
        use_container_width=True,
        height=400
    )
else:
    st.info("Aún no hay resultados. Configura filtros y busca.")















