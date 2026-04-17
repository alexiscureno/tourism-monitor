"""
KPI Cards — componente reutilizable para Tourism Monitor
Muestra 4 métricas clave en una fila usando st.metric().
"""

from typing import Optional
import streamlit as st


def render_kpi_cards(
    total_barcos: int,
    total_pasajeros: int,
    terminales_activas: int,
    cancelaciones: int,
    total_programados: Optional[int] = None,
) -> None:
    """
    Renderiza 4 KPI cards en una fila.

    Args:
        total_barcos: número total de barcos programados hoy
        total_pasajeros: suma de pasajeros reportados (excluye pendientes)
        terminales_activas: número de terminales con actividad
        cancelaciones: número de visitas canceladas
        total_programados: total original (para calcular tasa cancelación)
    """
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="🚢 Barcos Hoy",
            value=total_barcos,
        )

    with col2:
        pasajeros_display = f"{total_pasajeros:,}" if total_pasajeros > 0 else "—"
        st.metric(
            label="👥 Pasajeros",
            value=pasajeros_display,
        )

    with col3:
        st.metric(
            label="⚓ Terminales Activas",
            value=terminales_activas,
        )

    with col4:
        if total_programados and total_programados > 0:
            tasa = round(cancelaciones / total_programados * 100, 1)
            delta_str = f"{tasa}% del total"
        else:
            delta_str = None

        st.metric(
            label="❌ Cancelaciones",
            value=cancelaciones,
            delta=delta_str,
            delta_color="inverse",
        )
