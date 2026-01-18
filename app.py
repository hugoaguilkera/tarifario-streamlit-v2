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

# ⚠️ set_page_config SOLO UNA VEZ Y AL INICIO
st.set_page_config(
    page_title="Tarifario Pactra",
    layout="wide",
)

st.title("📊 Tarifario Pactra")

# ===============================
# MODO DE OPERACIÓN (ERP)
# ===============================
modo = st.radio(
    "🧭 Modo de operación",
    ["Consulta", "Administración"],
    horizontal=True
)

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
    df = pd.read_sql("SELECT * FROM tarifario_estandar", conn)
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

# =====================================================
# BLOQUE 5.5 - EDICIÓN VERSIONADA + HISTORIAL
# =====================================================

if modo == "Administración":

    df_activo = st.session_state.get("df_filtrado", pd.DataFrame())

    st.divider()
    st.subheader("✏️ Editar tarifa (versionado ERP)")

    if df_activo.empty or "ID_TARIFA" not in df_activo.columns:
        st.info("Realiza una búsqueda para poder editar tarifas.")
    else:
        df_activo = df_activo[df_activo["ID_TARIFA"].notna()]

        if df_activo.empty:
            st.info("No hay tarifas válidas para edición.")
        else:
            tarifa_id = st.selectbox(
                "Selecciona la tarifa (ID_TARIFA)",
                sorted(df_activo["ID_TARIFA"].unique()),
                key="tarifa_id_sel"
            )

            st.session_state["tarifa_id"] = tarifa_id

            tarifa_df = df_activo[df_activo["ID_TARIFA"] == tarifa_id]

            if tarifa_df.empty:
                st.warning("La tarifa seleccionada no está disponible para edición.")
            else:
                tarifa = tarifa_df.iloc[0]

                with st.form("editar_tarifa_form"):
                    nuevo_precio = st.number_input(
                        "Precio viaje sencillo",
                        value=float(tarifa.get("PRECIO_VIAJE_SENCILLO", 0) or 0),
                        step=100.0
                    )

                    nuevo_allin = st.number_input(
                        "ALL IN",
                        value=float(tarifa.get("ALL_IN", 0) or 0),
                        step=100.0
                    )

                    motivo = st.text_input(
                        "Motivo del cambio (obligatorio)",
                        placeholder="Ej. ajuste por diesel / negociación cliente"
                    )

                    guardar = st.form_submit_button("💾 Guardar nueva versión")

                if guardar:
                    if not motivo.strip():
                        st.warning("⚠️ El motivo del cambio es obligatorio.")
                    else:
                        with sqlite3.connect(DB_NAME) as conn:
                            cur = conn.cursor()

                            # 0️⃣ Calcular nueva versión
                            cur.execute(
                                "SELECT COALESCE(MAX(VERSION), 0) + 1 FROM tarifario_estandar WHERE ID_TARIFA = ?",
                                (tarifa_id,)
                            )
                            nueva_version = cur.fetchone()[0]

                            # 1️⃣ Desactivar versión actual
                            cur.execute("""
                                UPDATE tarifario_estandar
                                SET ACTIVA = 0
                                WHERE ID_TARIFA = ? AND ACTIVA = 1
                            """, (tarifa_id,))

                            # 2️⃣ Insertar nueva versión
                            cur.execute("""
                                INSERT INTO tarifario_estandar (
                                    ID_TARIFA,
                                    VERSION,
                                    ACTIVA,
                                    PRECIO_VIAJE_SENCILLO,
                                    ALL_IN,
                                    FECHA_CAMBIO,
                                    USUARIO_CAMBIO,
                                    MOTIVO_CAMBIO,
                                    CLIENTE,
                                    TRANSPORTISTA,
                                    TIPO_DE_OPERACION,
                                    TIPO_DE_VIAJE,
                                    TIPO_UNIDAD,
                                    PAIS_ORIGEN,
                                    ESTADO_ORIGEN,
                                    CIUDAD_ORIGEN,
                                    PAIS_DESTINO,
                                    ESTADO_DESTINO,
                                    CIUDAD_DESTINO
                                )
                                SELECT
                                    ID_TARIFA,
                                    ?,
                                    1,
                                    ?,
                                    ?,
                                    datetime('now'),
                                    'Ingeniero Hugo',
                                    ?,
                                    CLIENTE,
                                    TRANSPORTISTA,
                                    TIPO_DE_OPERACION,
                                    TIPO_DE_VIAJE,
                                    TIPO_UNIDAD,
                                    PAIS_ORIGEN,
                                    ESTADO_ORIGEN,
                                    CIUDAD_ORIGEN,
                                    PAIS_DESTINO,
                                    ESTADO_DESTINO,
                                    CIUDAD_DESTINO
                                FROM tarifario_estandar
                                WHERE ID_TARIFA = ?
                                ORDER BY VERSION DESC
                                LIMIT 1
                            """, (nueva_version, nuevo_precio, nuevo_allin, motivo, tarifa_id))

                            conn.commit()

                        st.success(f"✅ Nueva versión creada (v{nueva_version})")
                        st.rerun()

                st.divider()
                st.subheader("📜 Historial de versiones")

                with sqlite3.connect(DB_NAME) as conn:
                    historial = pd.read_sql(
                        """
                        SELECT
                            VERSION,
                            PRECIO_VIAJE_SENCILLO,
                            ALL_IN,
                            ACTIVA,
                            FECHA_CAMBIO,
                            USUARIO_CAMBIO,
                            MOTIVO_CAMBIO
                        FROM tarifario_estandar
                        WHERE ID_TARIFA = ?
                        ORDER BY VERSION DESC
                        """,
                        conn,
                        params=(tarifa_id,)
                    )

                st.dataframe(historial, use_container_width=True)


# =====================================================
# BLOQUE 6 - TARIFARIO OFICIAL (SOLO LECTURA)
# =====================================================

if modo == "Administración":

    st.divider()
    st.subheader("📋 Tarifario oficial (solo lectura)")

    ver_bd = st.checkbox(
        "👁️ Mostrar tarifario completo",
        key="ver_bd_checkbox"
    )

    if ver_bd:
        df_bd = cargar_bd_completa()
        st.caption(f"Registros totales: {len(df_bd):,}")

        st.dataframe(
            df_bd,
            use_container_width=True,
            height=450
        )

        buffer = io.BytesIO()
        df_bd.to_excel(buffer, index=False)
        buffer.seek(0)

        st.download_button(
            "⬇ Descargar Excel",
            data=buffer,
            file_name="tarifario_oficial.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_bd_btn",
        )

# =====================================================
# BLOQUE 7 - TARIFARIO ESTÁNDAR (BD REAL)
# =====================================================
# st.divider()
# st.subheader("🗄️ Tarifario estándar (Base oficial)")
#
# df_tarifario = cargar_bd_completa()
# st.caption(f"Total de registros: {len(df_tarifario):,}")
#
# st.dataframe(
#     df_tarifario,
#     use_container_width=True,
#     height=450
# )
#
# buffer_tarifario = io.BytesIO()
# df_tarifario.to_excel(buffer_tarifario, index=False)
# buffer_tarifario.seek(0)
#
# st.download_button(
#     "⬇ Descargar tarifario estándar",
#     data=buffer_tarifario,
#     file_name="tarifario_estandar.sqlite.xlsx",
#     mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#     key="download_tarifario_btn",
# )

# =====================================================
# BLOQUE 8 - EXPORTAR TARIFARIO FILTRADO A EXCEL
# =====================================================
st.divider()
st.subheader("📤 Exportar tarifario filtrado")

df_export = st.session_state.get("df_filtrado", pd.DataFrame())

if not df_export.empty:
    buffer_export = io.BytesIO()
    df_export.to_excel(buffer_export, index=False)
    buffer_export.seek(0)

    st.download_button(
        label="📥 Descargar tarifario filtrado (Excel)",
        data=buffer_export,
        file_name="tarifario_filtrado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_filtrado_btn",
    )
else:
    st.info("No hay datos filtrados para exportar.")















