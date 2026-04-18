"""
Tourism Monitor · Cozumel — Entry Point
Dashboard principal de Streamlit con navegación multipágina.
"""

import streamlit as st

st.set_page_config(
    page_title="Tourism Monitor · Cozumel",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── SIDEBAR ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚢 Tourism Monitor")
    st.markdown("**Cozumel, Q. Roo**")
    st.divider()
    st.page_link("app.py", label="Inicio", icon="🏠")
    st.page_link("pages/01_Hoy.py", label="Vista del Día", icon="📅")
    st.page_link("pages/02_Historico.py", label="Histórico", icon="📊")
    st.page_link("pages/03_Mapa.py", label="Mapa AIS", icon="🗺️")
    st.divider()
    st.caption("Datos: APIQROO · CruiseMapper · Open-Meteo")
    st.caption("Actualización: diaria 7am CST")

# ── LANDING PAGE ─────────────────────────────────────────────────────────
st.title("🚢 Tourism Monitor · Cozumel")
st.markdown("Monitoreo en tiempo real de cruceros en el Puerto de Cozumel.")
st.markdown("**Selecciona una sección en el sidebar** o navega directamente:")

col1, col2, col3 = st.columns(3)

with col1:
    st.page_link(
        "pages/01_Hoy.py",
        label="📅 Vista del Día  \nCruceros de hoy: terminales, status, ETA/ETD y pasajeros.",
        width="stretch",
    )

with col2:
    st.page_link(
        "pages/02_Historico.py",
        label="📊 Explorador Histórico  \nFiltra por año, naviera y terminal. 2015 → hoy.",
        width="stretch",
    )

with col3:
    st.page_link(
        "pages/03_Mapa.py",
        label="🗺️ Mapa AIS  \nPosiciones en tiempo real de barcos en el área de Cozumel.",
        width="stretch",
    )
