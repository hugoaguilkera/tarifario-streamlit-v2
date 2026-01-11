import streamlit as st
from core.services import cargar_bd_completa

st.set_page_config(page_title="Tarifario Pactra", layout="wide")

st.title("Tarifario")
st.subheader("Tablas disponibles en la BD")

# Cargar datos reales desde SQLite
df = cargar_bd_completa()

# Conteo de registros
st.caption(f"Registros totales: {len(df):,}")

# Mostrar solo columnas clave
cols = ["ID_TARIFA", "FECHA_VIGENCIA_INI", "FECHA_VIGENCIA_FIN"]
st.dataframe(df[cols], use_container_width=True, height=500)

# Botón para refrescar datos (si hay cache)
if st.button("🔄 Refrescar BD"):
    try:
        cargar_bd_completa.clear()
    except:
        pass
    st.rerun()













