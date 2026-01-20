import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="Captura de tarifas", layout="wide")

DB_NAME = "tarifario.db"
REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / DB_NAME

st.title("🟩 Captura de tarifas y costos")

# 🔴 RESET DE SESSION (solo debug)
if st.button("RESET ESTADO"):
    st.session_state.clear()
    st.rerun()

# =====================================================
# HELPERS SQL (NO TRUENA)  ✅ ← AQUÍ VA
# =====================================================
def _connect():
    if DB_PATH.exists():
        uri = f"file:{DB_PATH.as_posix()}?mode=ro&immutable=1"
        return sqlite3.connect(uri, uri=True, check_same_thread=False)
    return sqlite3.connect(str(DB_PATH), check_same_thread=False)

def table_exists(table: str) -> bool:
    try:
        with _connect() as conn:
            r = pd.read_sql(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                conn,
                params=(table,)
            )
        return not r.empty
    except Exception:
        return False

def get_columns(table: str) -> list[str]:
    try:
        with _connect() as conn:
            info = pd.read_sql(f"PRAGMA table_info({table})", conn)
        return info["name"].tolist() if "name" in info.columns else []
    except Exception:
        return []

def df_sql(query: str, params=()):
    try:
        with _connect() as conn:
            return pd.read_sql(query, conn, params=params)
    except Exception as e:
        st.warning(f"⚠️ No se pudo leer SQL.\n{e}")
        return pd.DataFrame()

# =====================================================
# BLOQUE 0 - BUSCADOR RÁPIDO DE TARIFAS (EDICIÓN / NUEVA)
# =====================================================
st.subheader("🔍 Buscar tarifa existente para modificar")

if not DB_PATH.exists():
    st.error(f"❌ No existe el archivo de BD: {DB_PATH}")
    st.stop()

if not table_exists("tarifario_estandar"):
    st.warning("⚠️ No existe la tabla tarifario_estandar.")
    df_existentes = pd.DataFrame(
        columns=["ID_TARIFA","TRANSPORTISTA","CLIENTE","CIUDAD_ORIGEN","CIUDAD_DESTINO","ALL_IN","ACTIVA"]
    )
else:
    cols = set(get_columns("tarifario_estandar"))

    deseadas = [
        "ID_TARIFA",
        "TRANSPORTISTA",
        "CLIENTE",
        "TIPO_UNIDAD",
        "PAIS_ORIGEN","ESTADO_ORIGEN","CIUDAD_ORIGEN",
        "PAIS_DESTINO","ESTADO_DESTINO","CIUDAD_DESTINO",
        "ALL_IN",
        "ACTIVA"
    ]

    select_cols = [c for c in deseadas if c in cols]

    # 🔥 FIX CLAVE: NO FILTRAR ACTIVA AQUÍ
    where = "WHERE ID_TARIFA IS NOT NULL"

    sql = f"""
        SELECT {", ".join(select_cols)}
        FROM tarifario_estandar
        {where}
        ORDER BY ID_TARIFA DESC
    """

    df_existentes = df_sql(sql)

    if df_existentes.empty:
        st.info("No hay tarifas registradas.")
        df_existentes = pd.DataFrame(
            columns=["ID_TARIFA","TRANSPORTISTA","CLIENTE","CIUDAD_ORIGEN","CIUDAD_DESTINO","ALL_IN","ACTIVA"]
        )

# ---------------- FILTROS ----------------
transportistas_list = ["Todos"] + sorted(
    df_existentes["TRANSPORTISTA"].dropna().unique().tolist()
)

clientes_list = ["Todos"] + sorted(
    df_existentes["CLIENTE"].dropna().unique().tolist()
)

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

if filtro_transportista != "Todos":
    df_existentes = df_existentes[df_existentes["TRANSPORTISTA"] == filtro_transportista]

if filtro_cliente != "Todos":
    df_existentes = df_existentes[
        (df_existentes["CLIENTE"] == filtro_cliente) |
        (df_existentes["CLIENTE"].isna()) |
        (df_existentes["CLIENTE"] == "") |
        (df_existentes["CLIENTE"] == "SIN CLIENTE")
    ]

# ---------------- SELECT TARIFA ----------------
ids = df_existentes["ID_TARIFA"].astype(str).tolist()
opciones_tarifa = ["NUEVA"] + ids

def etiqueta_tarifa(x):
    if x == "NUEVA":
        return "➕ NUEVA TARIFA"
    fila = df_existentes[df_existentes["ID_TARIFA"].astype(str) == x].iloc[0]
    estado = "🟢" if fila.get("ACTIVA", 1) == 1 else "🔴"
    return f"{estado} {fila['TRANSPORTISTA']} | {fila['CIUDAD_ORIGEN']} → {fila['CIUDAD_DESTINO']} | {fila['ALL_IN']}"

tarifa_id_sel = st.selectbox(
    "Selecciona tarifa",
    opciones_tarifa,
    index=1 if len(ids) > 0 else 0,
    format_func=etiqueta_tarifa,
    key="tarifa_id_sel"
)

# ---------------- CONTROL DE MODO ----------------
if tarifa_id_sel == "NUEVA":
    st.session_state["tarifa_base_tmp"] = None
    st.session_state["tarifa_cargada"] = False
    st.session_state.pop("id_tarifa_editar", None)
    st.info("🆕 Captura de tarifa nueva")
else:
    fila = df_existentes[df_existentes["ID_TARIFA"].astype(str) == tarifa_id_sel]
    st.session_state["tarifa_base_tmp"] = fila.iloc[0]
    st.session_state["tarifa_cargada"] = False
    st.session_state["id_tarifa_editar"] = int(fila.iloc[0]["ID_TARIFA"])

# =====================================================
# BLOQUE 0.1 - CARGA SEGURA DE TARIFA EN SESSION_STATE
# =====================================================
CAMPOS_SESSION = [
    "pais_origen","estado_origen","ciudad_origen",
    "pais_destino","estado_destino","ciudad_destino",
    "tipo_unidad",
    "precio_viaje_sencillo","precio_viaje_redondo",
    "tarifa_viaje_sencillo","tarifa_viaje_redondo","tarifa_viaje_full",
    "usa_freight","mexican_freight","crossing","border_crossing",
    "aduanas_aranceles","insurance","peajes","maniobras"
]

DEFAULTS = {c: 0.0 for c in CAMPOS_SESSION}
DEFAULTS.update({
    "pais_origen":"", "estado_origen":"", "ciudad_origen":"",
    "pais_destino":"", "estado_destino":"", "ciudad_destino":"",
    "tipo_unidad":""
})

for c in CAMPOS_SESSION:
    st.session_state.setdefault(c, DEFAULTS[c])

st.session_state.setdefault("tarifa_cargada", False)

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

if (
    st.session_state.get("tarifa_base_tmp") is not None
    and not st.session_state["tarifa_cargada"]
):
    tarifa_base = st.session_state["tarifa_base_tmp"]
    for campo_ui, campo_bd in MAPEO_SESSION_BD.items():
        st.session_state[campo_ui] = tarifa_base.get(campo_bd, DEFAULTS[campo_ui])
    st.session_state["tarifa_cargada"] = True
    st.session_state["tarifa_base_tmp"] = None
else:
    tarifa_base = None


# =====================================================
# BOTÓN - ADMINISTRAR CATÁLOGOS
# =====================================================
if st.button("🛠️ Administrar catálogos", key="btn_ir_catalogos"):
    st.switch_page("pages/1_Administrar_catalogos.py")

if st.button("✏️ Editar tarifa"):
    if tarifa_id_sel == "NUEVA":
        st.warning("Selecciona una tarifa existente para editar.")
    else:
        if "id_tarifa_editar" not in st.session_state:
            st.error("No se encontró ID de tarifa para edición.")
        else:
            st.switch_page("pages/3_Editar_tarifa.py")

# =====================================================
# BLOQUE A - DATOS DEL SERVICIO
# =====================================================
st.subheader("📌 Datos del servicio")

# si no existen catálogos, no truena
df_ops = df_sql("SELECT TIPO_OPERACION FROM CAT_TIPO_OPERACION ORDER BY TIPO_OPERACION")
ops_list = df_ops["TIPO_OPERACION"].tolist() if "TIPO_OPERACION" in df_ops.columns and not df_ops.empty else ["EXPORTACIÓN", "IMPORTACIÓN"]

c1, c2, c3 = st.columns(3)

tipo_operacion = c1.selectbox("Tipo operación", ops_list, key="tipo_operacion")
tipo_viaje = c2.selectbox("Tipo viaje", ["SENCILLO", "REDONDO"], key="tipo_viaje")
c3.empty()

st.caption(f"DB PATH: {DB_PATH}")
# =====================================================
# BLOQUE B - RUTA (NORMALIZADA Y SEGURA) ✅ (CLOUD/LOCAL)
# =====================================================

st.subheader("📍 Ruta")

with sqlite3.connect(str(DB_PATH), check_same_thread=False) as conn:

    # ---------- PAÍSES ----------
    df_paises = pd.read_sql(
        "SELECT ID_PAIS, PAIS FROM CAT_PAISES WHERE ACTIVO = 1 ORDER BY PAIS",
        conn
    )

    if df_paises.empty:
        st.error("No hay países activos en CAT_PAISES.")
        st.stop()

    df_paises["PAIS"] = df_paises["PAIS"].astype(str).str.strip().str.upper()
    paises = df_paises["PAIS"].tolist()

    # ---------- PAÍS ORIGEN ----------
    pais_origen_prev = (st.session_state.get("pais_origen") or "").strip().upper()
    pais_origen = st.selectbox(
        "País origen",
        paises,
        index=paises.index(pais_origen_prev) if pais_origen_prev in paises else 0,
        key="pais_origen"
    )

    if st.session_state.get("pais_origen_prev") and st.session_state["pais_origen_prev"] != pais_origen:
        st.session_state["estado_origen"] = None
        st.session_state["ciudad_origen"] = None
    st.session_state["pais_origen_prev"] = pais_origen

    fila_pais_origen = df_paises[df_paises["PAIS"] == pais_origen]
    if fila_pais_origen.empty:
        st.error("País origen inválido.")
        st.stop()
    id_pais_origen = int(fila_pais_origen.iloc[0]["ID_PAIS"])

    # ---------- ESTADO ORIGEN ----------
    df_estados_origen = pd.read_sql(
        """
        SELECT ID_ESTADO, ESTADO
        FROM CAT_ESTADOS_NEW
        WHERE ID_PAIS = ? AND ACTIVO = 1
        ORDER BY ESTADO
        """,
        conn,
        params=(id_pais_origen,)
    )

    if df_estados_origen.empty:
        st.warning("No hay estados activos para el país origen.")
        estado_origen = None
        id_estado_origen = None
    else:
        df_estados_origen["ESTADO"] = df_estados_origen["ESTADO"].astype(str).str.strip()
        estados_origen = df_estados_origen["ESTADO"].tolist()

        estado_origen_prev = st.session_state.get("estado_origen")
        estado_origen = st.selectbox(
            "Estado origen",
            estados_origen,
            index=estados_origen.index(estado_origen_prev) if estado_origen_prev in estados_origen else 0,
            key="estado_origen"
        )

        if st.session_state.get("estado_origen_prev") and st.session_state["estado_origen_prev"] != estado_origen:
            st.session_state["ciudad_origen"] = None
        st.session_state["estado_origen_prev"] = estado_origen

        fila_estado_origen = df_estados_origen[df_estados_origen["ESTADO"] == estado_origen]
        id_estado_origen = int(fila_estado_origen.iloc[0]["ID_ESTADO"]) if not fila_estado_origen.empty else None

    # ---------- CIUDAD ORIGEN ----------
    if not id_estado_origen:
        ciudad_origen = None
        st.info("Selecciona estado origen.")
    else:
        df_ciudades_origen = pd.read_sql(
            """
            SELECT ID_CIUDAD, CIUDAD
            FROM CAT_CIUDADES
            WHERE ID_ESTADO = ? AND ACTIVO = 1
            ORDER BY CIUDAD
            """,
            conn,
            params=(id_estado_origen,)
        )

        if df_ciudades_origen.empty:
            ciudad_origen = None
            st.warning("No hay ciudades activas para el estado origen.")
        else:
            df_ciudades_origen["CIUDAD"] = df_ciudades_origen["CIUDAD"].astype(str).str.strip()
            ciudades_origen = df_ciudades_origen["CIUDAD"].tolist()

            ciudad_origen_prev = st.session_state.get("ciudad_origen")
            ciudad_origen = st.selectbox(
                "Ciudad origen",
                ciudades_origen,
                index=ciudades_origen.index(ciudad_origen_prev) if ciudad_origen_prev in ciudades_origen else 0,
                key="ciudad_origen"
            )

    st.divider()

    # ---------- PAÍS DESTINO ----------
    pais_destino_prev = (st.session_state.get("pais_destino") or "").strip().upper()
    pais_destino = st.selectbox(
        "País destino",
        paises,
        index=paises.index(pais_destino_prev) if pais_destino_prev in paises else 0,
        key="pais_destino"
    )

    if st.session_state.get("pais_destino_prev") and st.session_state["pais_destino_prev"] != pais_destino:
        st.session_state["estado_destino"] = None
        st.session_state["ciudad_destino"] = None
    st.session_state["pais_destino_prev"] = pais_destino

    fila_pais_destino = df_paises[df_paises["PAIS"] == pais_destino]
    if fila_pais_destino.empty:
        st.error("País destino inválido.")
        st.stop()
    id_pais_destino = int(fila_pais_destino.iloc[0]["ID_PAIS"])

    # ---------- ESTADO DESTINO ----------
    df_estados_destino = pd.read_sql(
        """
        SELECT ID_ESTADO, ESTADO
        FROM CAT_ESTADOS_NEW
        WHERE ID_PAIS = ? AND ACTIVO = 1
        ORDER BY ESTADO
        """,
        conn,
        params=(id_pais_destino,)
    )

    if df_estados_destino.empty:
        estado_destino = None
        id_estado_destino = None
        st.warning("No hay estados activos para el país destino.")
    else:
        df_estados_destino["ESTADO"] = df_estados_destino["ESTADO"].astype(str).str.strip()
        estados_destino = df_estados_destino["ESTADO"].tolist()

        estado_destino_prev = st.session_state.get("estado_destino")
        estado_destino = st.selectbox(
            "Estado destino",
            estados_destino,
            index=estados_destino.index(estado_destino_prev) if estado_destino_prev in estados_destino else 0,
            key="estado_destino"
        )

        if st.session_state.get("estado_destino_prev") and st.session_state["estado_destino_prev"] != estado_destino:
            st.session_state["ciudad_destino"] = None
        st.session_state["estado_destino_prev"] = estado_destino

        fila_estado_destino = df_estados_destino[df_estados_destino["ESTADO"] == estado_destino]
        id_estado_destino = int(fila_estado_destino.iloc[0]["ID_ESTADO"]) if not fila_estado_destino.empty else None

    # ---------- CIUDAD DESTINO ----------
    if not id_estado_destino:
        ciudad_destino = None
        st.info("Selecciona estado destino.")
    else:
        df_ciudades_destino = pd.read_sql(
            """
            SELECT ID_CIUDAD, CIUDAD
            FROM CAT_CIUDADES
            WHERE ID_ESTADO = ? AND ACTIVO = 1
            ORDER BY CIUDAD
            """,
            conn,
            params=(id_estado_destino,)
        )

        if df_ciudades_destino.empty:
            ciudad_destino = None
            st.warning("No hay ciudades activas para el estado destino.")
        else:
            df_ciudades_destino["CIUDAD"] = df_ciudades_destino["CIUDAD"].astype(str).str.strip()
            ciudades_destino = df_ciudades_destino["CIUDAD"].tolist()

            ciudad_destino_prev = st.session_state.get("ciudad_destino")
            ciudad_destino = st.selectbox(
                "Ciudad destino",
                ciudades_destino,
                index=ciudades_destino.index(ciudad_destino_prev) if ciudad_destino_prev in ciudades_destino else 0,
                key="ciudad_destino"
            )

    st.divider()

    # ---------- TIPO DE UNIDAD ----------
    df_unidades = pd.read_sql(
        "SELECT TIPO_UNIDAD FROM CAT_TIPO_UNIDAD ORDER BY TIPO_UNIDAD",
        conn
    )

    if df_unidades.empty:
        st.error("No hay registros en CAT_TIPO_UNIDAD.")
        st.stop()

    unidades = df_unidades["TIPO_UNIDAD"].astype(str).str.strip().tolist()
    tipo_unidad_prev = st.session_state.get("tipo_unidad")

    tipo_unidad = st.selectbox(
        "Tipo de unidad",
        unidades,
        index=unidades.index(tipo_unidad_prev) if tipo_unidad_prev in unidades else 0,
        key="tipo_unidad"
    )

# =====================================================
# BLOQUE C - DATOS COMERCIALES ✅ ROBUSTO (CLOUD/LOCAL)
# =====================================================
st.subheader("👤 Datos comerciales")

with sqlite3.connect(str(DB_PATH), check_same_thread=False) as conn:

    col_cli, col_trp = st.columns(2)

    # ---------- CLIENTES (solo activos) ----------
    df_cli = pd.read_sql(
        "SELECT CLIENTE FROM CAT_CLIENTES WHERE ACTIVO = 1 ORDER BY CLIENTE",
        conn
    )

    lista_clientes = ["SIN CLIENTE"] + df_cli["CLIENTE"].astype(str).tolist()

    cliente_default = "SIN CLIENTE"
    if tarifa_base is not None:
        cli_tmp = str(tarifa_base.get("CLIENTE", "")).strip()
        if cli_tmp in lista_clientes:
            cliente_default = cli_tmp

    cliente = col_cli.selectbox(
        "Cliente",
        lista_clientes,
        index=lista_clientes.index(cliente_default),
        key="cliente"
    )

    # ---------- TRANSPORTISTAS (solo activos) ----------
    df_trp = pd.read_sql(
        "SELECT TRANSPORTISTA FROM CAT_TRANSPORTISTAS WHERE ACTIVO = 1 ORDER BY TRANSPORTISTA",
        conn
    )

    lista_transportistas = df_trp["TRANSPORTISTA"].astype(str).tolist()

    if not lista_transportistas:
        st.error("❌ No hay transportistas activos en CAT_TRANSPORTISTAS.")
        st.stop()

    transportista_default = lista_transportistas[0]
    if tarifa_base is not None:
        trp_tmp = str(tarifa_base.get("TRANSPORTISTA", "")).strip()
        if trp_tmp in lista_transportistas:
            transportista_default = trp_tmp

    transportista = col_trp.selectbox(
        "Transportista",
        lista_transportistas,
        index=lista_transportistas.index(transportista_default),
        key="transportista"
    )
# =====================================================
# BLOQUE D - TARIFAS (PRECARGA CONTROLADA) ✅ ROBUSTO
# =====================================================
st.subheader("💰 Tarifas")

def _to_float(x, default=0.0):
    try:
        if x is None:
            return float(default)
        if isinstance(x, str) and x.strip() == "":
            return float(default)
        return float(x)
    except Exception:
        return float(default)

# Defaults (si no existen columnas en BD, no truena)
moneda_precio_default = "MXN"
moneda_tarifa_default = "USD"

if tarifa_base is not None:
    moneda_precio_default = str(tarifa_base.get("MONEDA_PRECIO", tarifa_base.get("MONEDA", "MXN")) or "MXN").upper().strip()
    moneda_tarifa_default = str(tarifa_base.get("MONEDA_TARIFA", tarifa_base.get("MONEDA", "USD")) or "USD").upper().strip()

c1, c2, c3 = st.columns(3)

precio_sencillo = c1.number_input(
    "Precio viaje sencillo",
    min_value=0.0,
    step=50.0,
    value=_to_float(tarifa_base.get("PRECIO_VIAJE_SENCILLO") if tarifa_base is not None else 0.0),
    key="precio_viaje_sencillo"
)

precio_redondo = c2.number_input(
    "Precio viaje redondo",
    min_value=0.0,
    step=50.0,
    value=_to_float(tarifa_base.get("PRECIO_VIAJE_REDONDO") if tarifa_base is not None else 0.0),
    key="precio_viaje_redondo"
)

moneda = c3.selectbox(
    "Moneda (precio)",
    ["MXN", "USD"],
    index=0 if moneda_precio_default == "MXN" else 1,
    key="moneda_precio"
)

# -----------------------------------------------------
# TARIFAS NEGOCIADAS
# -----------------------------------------------------
st.subheader("📑 Tarifas negociadas")

c1, c2, c3, c4 = st.columns(4)

tarifa_sencillo = c1.number_input(
    "Tarifa viaje sencillo",
    min_value=0.0,
    step=50.0,
    value=_to_float(tarifa_base.get("TARIFA_VIAJE_SENCILLO") if tarifa_base is not None else 0.0),
    key="tarifa_viaje_sencillo"
)

tarifa_redondo = c2.number_input(
    "Tarifa viaje redondo",
    min_value=0.0,
    step=50.0,
    value=_to_float(tarifa_base.get("TARIFA_VIAJE_REDONDO") if tarifa_base is not None else 0.0),
    key="tarifa_viaje_redondo"
)

tarifa_full = c3.number_input(
    "Tarifa full (opcional)",
    min_value=0.0,
    step=50.0,
    value=_to_float(tarifa_base.get("TARIFA_VIAJE_FULL") if tarifa_base is not None else 0.0),
    key="tarifa_viaje_full"
)

moneda_tarifa = c4.selectbox(
    "Moneda (tarifa)",
    ["MXN", "USD"],
    index=0 if moneda_tarifa_default == "MXN" else 1,
    key="moneda_tarifa"
)
# =====================================================
# BLOQUE E - COSTOS + ALL IN + INFO + GUARDAR (ROBUSTO)
# =====================================================
st.subheader("📦 Costos")

# --- COSTOS (precarga desde session_state por key) ---
c1, c2, c3, c4 = st.columns(4)
usa_freight = c1.number_input("USA Freight", min_value=0.0, step=50.0, key="usa_freight")
mexican_freight = c2.number_input("Mexican Freight", min_value=0.0, step=50.0, key="mexican_freight")
crossing = c3.number_input("Crossing", min_value=0.0, step=50.0, key="crossing")
border_crossing = c4.number_input("Border Crossing", min_value=0.0, step=50.0, key="border_crossing")

c5, c6, c7, c8 = st.columns(4)
aduanas_aranceles = c5.number_input("Aduanas / Aranceles", min_value=0.0, step=50.0, key="aduanas_aranceles")
insurance = c6.number_input("Seguro", min_value=0.0, step=50.0, key="insurance")
peajes = c7.number_input("Peajes", min_value=0.0, step=50.0, key="peajes")
maniobras = c8.number_input("Maniobras", min_value=0.0, step=50.0, key="maniobras")

# =====================================================
# BLOQUE E.1 - ALL IN (AUTOMÁTICO)
# =====================================================
all_in = (
    float(usa_freight)
    + float(mexican_freight)
    + float(crossing)
    + float(border_crossing)
    + float(aduanas_aranceles)
    + float(insurance)
    + float(peajes)
    + float(maniobras)
)

st.subheader("🧮 ALL IN (Costo total automático)")
st.number_input("ALL IN", value=float(all_in), format="%.2f", disabled=True)

# =====================================================
# BLOQUE E.2 - INFORMACIÓN OPERATIVA ADICIONAL
# =====================================================
st.subheader("📝 Información operativa adicional")

c1, c2 = st.columns(2)

with c1:
    remark = st.text_area("Remark / Observaciones", key="remark")
    requerimiento = st.text_area("Requerimiento especial", key="requerimiento")
    direccion_recoleccion = st.text_input("Dirección de recolección", key="direccion_recoleccion")
    destino_empresa = st.text_input("Empresa destino", key="destino_empresa")

with c2:
    destino_direccion = st.text_input("Dirección destino", key="destino_direccion")
    team_driver = st.checkbox("Team driver", key="team_driver")
    waiting = st.checkbox("Waiting", key="waiting")
    free_time = st.number_input("Free time (horas)", min_value=0, step=1, key="free_time")
    costo_waiting = st.number_input("Costo waiting charge", min_value=0.0, step=100.0, key="costo_waiting")
    trucking_cancel_fee = st.number_input("Trucking cancel fee", min_value=0.0, step=100.0, key="trucking_cancel_fee")

# =====================================================
# BLOQUE E.3 - VALIDACIONES
# =====================================================
st.subheader("💾 Guardar tarifa")

errores = []
if float(precio_sencillo) == 0.0 and float(precio_redondo) == 0.0:
    errores.append("Debes capturar al menos un PRECIO (sencillo o redondo).")

if float(all_in) == 0.0:
    errores.append("Debes capturar el ALL IN (costos).")

if errores:
    st.error(" | ".join(errores))
    st.stop()

# =====================================================
# BLOQUE E.4 - VALIDAR DUPLICADO (misma ruta/proveedor)
# =====================================================
with sqlite3.connect(str(DB_PATH)) as conn:
    cur = conn.cursor()
    duplicado = cur.execute(
        """
        SELECT COUNT(*)
        FROM tarifario_estandar
        WHERE
            TRANSPORTISTA = ?
            AND TIPO_UNIDAD = ?
            AND PAIS_ORIGEN = ?
            AND ESTADO_ORIGEN = ?
            AND CIUDAD_ORIGEN = ?
            AND PAIS_DESTINO = ?
            AND ESTADO_DESTINO = ?
            AND CIUDAD_DESTINO = ?
            AND ACTIVA = 1
        """,
        (
            transportista,
            tipo_unidad,
            pais_origen,
            estado_origen,
            ciudad_origen,
            pais_destino,
            estado_destino,
            ciudad_destino,
        ),
    ).fetchone()[0]

if duplicado > 0:
    st.warning("⚠️ Ya existe una tarifa ACTIVA con el mismo proveedor y la misma ruta.")
    confirmar = st.checkbox("Confirmo que deseo guardar una nueva versión", key="confirmar_version_nueva")
else:
    confirmar = True

## =====================================================
# BLOQUE E.5 - INSERT FINAL (CON VERSIONADO)
# =====================================================
if st.button("💾 Guardar tarifa", key="btn_guardar_tarifa") and confirmar:
    with sqlite3.connect(str(DB_PATH)) as conn:
        cur = conn.cursor()

        # 🔁 SI VIENE DE EDITAR → DESACTIVA LA TARIFA ANTERIOR
        editando = "id_tarifa_editar" in st.session_state
        if editando:
            cur.execute(
                "UPDATE tarifario_estandar SET ACTIVA = 0 WHERE ID_TARIFA = ?",
                (st.session_state["id_tarifa_editar"],)
            )

        # ➕ INSERT NUEVA VERSIÓN (SIEMPRE ACTIVA = 1)
        cur.execute(
            """
            INSERT INTO tarifario_estandar (
                RESPONSABLE,
                TIPO_DE_OPERACION,
                TIPO_DE_VIAJE,
                TIPO_UNIDAD,
                TRANSPORTISTA,
                CLIENTE,

                PAIS_ORIGEN,
                ESTADO_ORIGEN,
                CIUDAD_ORIGEN,
                PAIS_DESTINO,
                ESTADO_DESTINO,
                CIUDAD_DESTINO,

                TARIFA_VIAJE_SENCILLO,
                TARIFA_VIAJE_REDONDO,
                TARIFA_VIAJE_FULL,

                PRECIO_VIAJE_SENCILLO,
                PRECIO_VIAJE_REDONDO,
                MONEDA,

                USA_FREIGHT,
                MEXICAN_FREIGHT,
                CROSSING,
                BORDER_CROSSING,
                ADUANAS_ARANCELES,
                INSURANCE,
                PEAJES,
                MANIOBRAS,
                ALL_IN,

                REMARK,
                REQUERIMIENTO,
                DIRECCION_DE_RECOLECCION,
                DESTINO_EMPRESA,
                DESTINO_DIRECCION,
                TEAM_DRIVER,
                WAITING,
                COSTO_DE_WAITING_CHARGE,
                FREE_TIME,
                TRUCKING_CANCEL_FEE,
                ACTIVA
            )
            VALUES (?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                tipo_operacion,
                tipo_viaje,
                tipo_unidad,
                transportista,
                cliente,

                pais_origen,
                estado_origen,
                ciudad_origen,
                pais_destino,
                estado_destino,
                ciudad_destino,

                float(tarifa_sencillo),
                float(tarifa_redondo),
                float(tarifa_full),

                float(precio_sencillo),
                float(precio_redondo),
                moneda,

                float(usa_freight),
                float(mexican_freight),
                float(crossing),
                float(border_crossing),
                float(aduanas_aranceles),
                float(insurance),
                float(peajes),
                float(maniobras),
                float(all_in),

                remark,
                requerimiento,
                direccion_recoleccion,
                destino_empresa,
                destino_direccion,
                int(team_driver),
                int(waiting),
                float(costo_waiting),
                int(free_time),
                float(trucking_cancel_fee),
                1  # ACTIVA
            ),
        )

        conn.commit()

    # 🧹 LIMPIEZA DE ESTADO (CLAVE)
    st.session_state.pop("id_tarifa_editar", None)
    st.session_state["tarifa_cargada"] = False

    st.success("✅ Tarifa guardada correctamente")
    st.rerun()
