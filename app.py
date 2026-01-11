import streamlit as st
from core.db import get_connection

st.title("Tarifario v2")

if st.button("Probar conexión"):
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        conn.close()
        st.success("Conexión OK")
    except Exception as e:
        st.error(e)
