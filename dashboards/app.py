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
    st.markdown(
        """
        **Navegación**
        - [Vista del Día](01_Hoy)
        - [Explorador Histórico](02_Historico)
        - [Tendencias](03_Tendencias)
        - [Load Factor](04_Load_Factor)
        - [Forecasting](05_Forecasting)
        """
    )
    st.divider()
    st.caption("Datos: APIQROO · CruiseMapper · Open-Meteo")
    st.caption("Actualización: diaria 7am CST")

# ── LANDING PAGE ─────────────────────────────────────────────────────────
st.title("🚢 Tourism Monitor · Cozumel")
st.markdown(
    """
    Monitoreo en tiempo real de cruceros en el Puerto de Cozumel.

    **Selecciona una sección en el sidebar** o navega directamente:
    """
)

col1, col2, col3 = st.columns(3)

with col1:
    st.info(
        """
        **📅 Vista del Día**
        Cruceros de hoy: terminales,
        status, ETA/ETD y pasajeros.
        """
    )

with col2:
    st.info(
        """
        **📊 Explorador Histórico**
        Filtra por año, mes, naviera
        y terminal. 2015 → hoy.
        """
    )

with col3:
    st.info(
        """
        **📈 Tendencias**
        Estacionalidad, market share
        de navieras y anomalías.
        """
    )
