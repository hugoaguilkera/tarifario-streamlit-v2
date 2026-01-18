import streamlit as st
st.write("COTIZACION VERSION NUEVA 2026")
import sqlite3
import pandas as pd
from pathlib import Path

# ===============================
# CONFIG
# ===============================
DB_NAME = "tarifario.db"
TABLA = "tarifario_estandar"


st.title("💰 Cotización")
st.success("Pantalla de impresión cargada")

# ===============================
# DB PATH (CLOUD/LOCAL)
# ===============================
REPO_ROOT = Path(__file__).resolve().parents[1]   # .../tarifario-streamlit-v2
DB_PATH = REPO_ROOT / DB_NAME

if not DB_PATH.exists():
    st.error(f"❌ No encuentro la base: {DB_PATH}")
    st.stop()

# ===============================
# HELPERS
# ===============================
def tabla_columnas(conn, tabla: str) -> set:
    df_cols = pd.read_sql(f"PRAGMA table_info({tabla})", conn)
    return set(df_cols["name"].tolist()) if not df_cols.empty else set()

def safe_distinct(conn, col: str, solo_activa: bool = True) -> list:
    cols = tabla_columnas(conn, TABLA)
    if col not in cols:
        return []
    where = "WHERE ACTIVA = 1" if (solo_activa and "ACTIVA" in cols) else ""
    df = pd.read_sql(f"SELECT DISTINCT {col} FROM {TABLA} {where}", conn)
    return df[col].dropna().astype(str).tolist()

def get_val(row, *cols, default=""):
    for c in cols:
        if c in row.index:
            v = row[c]
            return default if pd.isna(v) else v
    return default

# ===============================
# CONEXIÓN BD
# ===============================
conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)

# ===============================
# COLUMNAS BASE
# ===============================
COL_CLIENTE   = "CLIENTE"
COL_CLAVE     = "ID_TARIFA"
COL_UNIDAD    = "TIPO_UNIDAD"
COL_VIAJE     = "TIPO_DE_VIAJE"
COL_OPERACION = "TIPO_DE_OPERACION"
COL_TRP       = "TRANSPORTISTA"

COL_PAIS_O    = "PAIS_ORIGEN"
COL_ESTADO_O  = "ESTADO_ORIGEN"
COL_CIUDAD_O  = "CIUDAD_ORIGEN"

COL_PAIS_D    = "PAIS_DESTINO"
COL_ESTADO_D  = "ESTADO_DESTINO"
COL_CIUDAD_D  = "CIUDAD_DESTINO"

COL_ALLIN     = "ALL_IN"

# ===============================
# BUSCADOR
# ===============================
st.subheader("🔎 Buscador de tarifas")

clientes    = safe_distinct(conn, COL_CLIENTE)
claves      = safe_distinct(conn, COL_CLAVE)
unidades    = safe_distinct(conn, COL_UNIDAD)
viajes      = safe_distinct(conn, COL_VIAJE)
operaciones = safe_distinct(conn, COL_OPERACION)
trps        = safe_distinct(conn, COL_TRP)

c1, c2, c3, c4, c5, c6 = st.columns(6)
cliente   = c1.selectbox("Cliente", ["Todos"] + sorted(clientes))
clave     = c2.selectbox("Clave", ["Todas"] + sorted(claves))
unidad    = c3.selectbox("Unidad", ["Todas"] + sorted(unidades))
viaje     = c4.selectbox("Viaje", ["Todos"] + sorted(viajes))
operacion = c5.selectbox("Operación", ["Todas"] + sorted(operaciones))
trp       = c6.selectbox("Transportista", ["Todos"] + sorted(trps))

st.markdown("**Ruta**")

paises_o   = safe_distinct(conn, COL_PAIS_O)
estados_o  = safe_distinct(conn, COL_ESTADO_O)
ciudades_o = safe_distinct(conn, COL_CIUDAD_O)

paises_d   = safe_distinct(conn, COL_PAIS_D)
estados_d  = safe_distinct(conn, COL_ESTADO_D)
ciudades_d = safe_distinct(conn, COL_CIUDAD_D)

o1, o2, o3, d1, d2, d3 = st.columns(6)
pais_o   = o1.selectbox("País O", ["Todos"] + sorted(paises_o))
estado_o = o2.selectbox("Estado O", ["Todos"] + sorted(estados_o))
ciudad_o = o3.selectbox("Ciudad O", ["Todos"] + sorted(ciudades_o))

pais_d   = d1.selectbox("País D", ["Todos"] + sorted(paises_d))
estado_d = d2.selectbox("Estado D", ["Todos"] + sorted(estados_d))
ciudad_d = d3.selectbox("Ciudad D", ["Todos"] + sorted(ciudades_d))

# ===============================
# QUERY
# ===============================
query = f"SELECT * FROM {TABLA} WHERE 1=1"
params = []

def add(col, val, todos="Todos"):
    global query, params
    if val != todos:
        query += f" AND {col}=?"
        params.append(val)

add(COL_CLIENTE, cliente)
add(COL_CLAVE, clave, "Todas")
add(COL_UNIDAD, unidad, "Todas")
add(COL_VIAJE, viaje)
add(COL_OPERACION, operacion, "Todas")
add(COL_TRP, trp)

add(COL_PAIS_O, pais_o)
add(COL_ESTADO_O, estado_o)
add(COL_CIUDAD_O, ciudad_o)

add(COL_PAIS_D, pais_d)
add(COL_ESTADO_D, estado_d)
add(COL_CIUDAD_D, ciudad_d)

# Solo activas si existe ACTIVA
cols = tabla_columnas(conn, TABLA)
if "ACTIVA" in cols:
    query += " AND ACTIVA = 1"

df = pd.read_sql(query, conn, params=params)

# ===============================
# RESULTADOS
# ===============================
st.subheader("📊 Resultados")

if df.empty:
    st.warning("No se encontraron tarifas.")
    conn.close()
    st.stop()

st.dataframe(df, use_container_width=True)

# ===============================
# SELECCIÓN
# ===============================
idx = st.number_input("Fila a imprimir", 0, len(df) - 1, 0)
r = df.iloc[idx]

# ===============================
# CONTROL DE RETORNO
# ===============================
if "mostrar_retorno" not in st.session_state:
    st.session_state["mostrar_retorno"] = True

c_r1, c_r2 = st.columns(2)
if c_r1.button("🔁 Quitar retorno"):
    st.session_state["mostrar_retorno"] = False
if c_r2.button("🔁 Incluir retorno"):
    st.session_state["mostrar_retorno"] = True

# ===============================
# FREIGHTS SEGUROS (OJO: USA_FREIGHT vs US_FREIGHT)
# ===============================
mx_freight = get_val(r, "MEXICAN_FREIGHT", "MEX_FREIGHT", "MX_FREIGHT", default="")
us_freight = get_val(r, "USA_FREIGHT", "US_FREIGHT", "US_FRT", "US_COST", default="")
crossing   = get_val(r, "CROSSING", "CRUCE", default="")

# ===============================
# BLOQUE RETORNO (CONDICIONAL)
# ===============================
retorno_html = ""
if st.session_state["mostrar_retorno"]:
    retorno_html = """
    <br>
    <b>RETORNO</b>
    <table style="width:100%; border-collapse:collapse; margin-top:5px">
    <tr style="background:#f0f0f0">
      <th>ORIGEN</th>
      <th>DESTINO</th>
      <th>REQUERIMIENTO</th>
      <th>MEXICAN FREIGHT</th>
      <th>CROSSING</th>
      <th>US FREIGHT</th>
      <th>ALL IN</th>
    </tr>
    <tr contenteditable="true">
      <td>[Origen Retorno]</td>
      <td>[Destino Retorno]</td>
      <td>[Requerimiento]</td>
      <td align="right">[Mex Freight]</td>
      <td align="right">[Crossing]</td>
      <td align="right">[US Freight]</td>
      <td align="right"><b>[All In]</b></td>
    </tr>
    </table>
    """

# ===============================
# COTIZACIÓN EDITABLE
# ===============================
cliente_nom = get_val(r, COL_CLIENTE, default="Cliente")
oper_nom = get_val(r, COL_OPERACION, default="")
unidad_nom = get_val(r, COL_UNIDAD, default="")
viaje_nom = get_val(r, COL_VIAJE, default="")
ori = f"{get_val(r, COL_CIUDAD_O)} , {get_val(r, COL_ESTADO_O)}"
des = f"{get_val(r, COL_CIUDAD_D)} , {get_val(r, COL_ESTADO_D)}"
all_in = get_val(r, COL_ALLIN, default="")

cotizacion_html = f"""
<div id="print-area" style="font-family:Arial; font-size:14px; line-height:1.6">

<p><b>Pactra México</b></p>

<p><b>Estimado(a) {cliente_nom},</b><br>
Esperando se encuentre muy bien.</p>

<p>
En seguimiento a su solicitud, compartimos la cotización correspondiente
al servicio de transporte solicitado:
</p>

<p><b>
Cotización de Servicio de Transporte – Pactra México ({oper_nom})
</b></p>

<table style="width:100%; border-collapse:collapse; margin-top:10px">
<tr style="background:#003A8F; color:white">
  <th>ORIGEN</th>
  <th>DESTINO</th>
  <th>REQUERIMIENTO</th>
  <th>MEXICAN FREIGHT</th>
  <th>CROSSING</th>
  <th>US FREIGHT</th>
  <th>ALL IN</th>
</tr>
<tr>
  <td>{ori}</td>
  <td>{des}</td>
  <td>{unidad_nom} / {viaje_nom}</td>
  <td align="right">{mx_freight}</td>
  <td align="right">{crossing}</td>
  <td align="right">{us_freight}</td>
  <td align="right"><b>{all_in}</b></td>
</tr>
</table>

{retorno_html}

<br>
<b>Condiciones Comerciales:</b>
<ul>
  <li>Las tarifas están expresadas en <b>USD/MXN</b> y no incluyen IVA.</li>
  <li>La tarifa incluye el costo del transporte en unidad tipo <b>53 FT</b>.</li>
  <li>Tiempo libre de maniobras: 3 horas en carga y 3 horas en descarga. Posterior a este tiempo aplicará cargo por demora según tarifa vigente.</li>
  <li>El seguro de mercancía no está incluido. Puede cotizarse adicionalmente bajo solicitud expresa del cliente.</li>
  <li>Las tarifas están sujetas a disponibilidad de unidad y condiciones de ruta al momento de confirmar el servicio.</li>
  <li>Vigencia de la cotización: <b>[X días]</b> a partir de la fecha de emisión.</li>
  <li>No incluye maniobras especiales, custodia, almacenaje ni costos de cruce fronterizo salvo se indique expresamente lo contrario.</li>
  <li>Los tiempos de tránsito son estimados y pueden variar por factores externos como clima, tráfico, inspecciones u otras causas ajenas al control del transportista.</li>
</ul>

<p>
Atentamente,<br>
<b>Pactra México – División Logística Internacional</b>
</p>

</div>
"""

st.components.v1.html(
    f"""
    <style>
    @media print {{
      body * {{ visibility: hidden; }}
      #print-area, #print-area * {{ visibility: visible; }}
      #print-area {{
        position: absolute;
        left: 0;
        top: 0;
        width: 100%;
      }}
      .print-btn {{ display: none; }}
    }}

    .print-btn {{
      background:#003A8F;
      color:white;
      padding:10px 18px;
      border:none;
      border-radius:4px;
      font-size:14px;
      cursor:pointer;
      margin-bottom:15px;
    }}
    </style>

    <button class="print-btn" onclick="window.print()">🖨️ Imprimir / Guardar PDF</button>

    {cotizacion_html}
    """,
    height=820
)

conn.close()

