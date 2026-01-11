import streamlit as st
from core.services import cargar_bd_completa

st.title("Tarifario")
st.subheader("Tablas disponibles en la BD")

df = cargar_bd_completa()
st.dataframe(df)







