import pandas as pd
from core.db import get_connection
from core.queries import SQL_TARIFARIO_BASE

def cargar_bd_completa():
    conn = get_connection()
    df = pd.read_sql(SQL_TARIFARIO_BASE, conn)
    conn.close()
    return df





