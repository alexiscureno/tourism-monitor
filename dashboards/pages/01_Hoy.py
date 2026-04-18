"""
Vista del Día — Tourism Monitor · Cozumel
Muestra los cruceros del día actual agrupados por terminal.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

import streamlit as st
import pandas as pd

# Asegurar que src/ esté accesible desde el dashboard
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

st.set_page_config(
    page_title="Hoy · Tourism Monitor",
    page_icon="📅",
    layout="wide",
)

# ── IMPORTS LAZY (evitar error si supabase no está configurado) ──────────
@st.cache_data(ttl=300)  # Cache 5 min
def _load_today_data(target_date: date) -> pd.DataFrame:
    try:
        from src.db.client import query_visits_by_date
        return query_visits_by_date(target_date)
    except Exception as e:
        st.error(f"Error conectando a Supabase: {e}")
        return pd.DataFrame()


# ── CONSTANTES DE VISUALIZACIÓN ─────────────────────────────────────────
STATUS_COLORS = {
    "Arribado": "🟢",
    "Programado": "🟡",
    "Cancelado": "🔴",
}

TERMINAL_ORDER = [
    "TERMINAL SSA MEXICO",
    "TERMINAL PUERTA MAYA",
    "TERMINAL PUNTA LANGOSTA",
    "FONDEO COZUMEL",
]


# ── LAYOUT ───────────────────────────────────────────────────────────────
st.title("📅 Cruceros de Hoy")

# Selector de fecha (default: hoy)
col_date, col_nav_prev, col_nav_next = st.columns([3, 1, 1])
with col_date:
    selected_date = st.date_input(
        "Fecha",
        value=date.today(),
        min_value=date(2015, 10, 1),
        max_value=date.today() + timedelta(days=30),
        label_visibility="collapsed",
    )
with col_nav_prev:
    if st.button("◀ Ayer"):
        selected_date = selected_date - timedelta(days=1)
with col_nav_next:
    if st.button("Mañana ▶"):
        selected_date = selected_date + timedelta(days=1)

st.caption(f"Mostrando: **{selected_date.strftime('%A, %d de %B de %Y')}**")
st.divider()

# ── CARGAR DATOS ─────────────────────────────────────────────────────────
df = _load_today_data(selected_date)

if df.empty:
    st.info(
        "🚢 Sin cruceros programados para esta fecha.",
        icon="ℹ️",
    )
    st.stop()

# ── KPI CARDS ────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))
from components.kpi_cards import render_kpi_cards

total_barcos = len(df)
cancelados = len(df[df["status"] == "Cancelado"])
terminales_activas = df[df["status"] != "Cancelado"]["terminal"].nunique()

# Pasajeros: excluir pendientes y cancelados
mask_pax = (~df.get("pasajeros_pendiente", pd.Series(False, index=df.index))) & (df["status"] == "Arribado")
total_pasajeros = int(df.loc[mask_pax, "pasajeros"].sum()) if "pasajeros" in df.columns else 0

render_kpi_cards(
    total_barcos=total_barcos,
    total_pasajeros=total_pasajeros,
    terminales_activas=terminales_activas,
    cancelaciones=cancelados,
    total_programados=total_barcos,
)

st.divider()

# ── TABLA POR TERMINAL ───────────────────────────────────────────────────
st.subheader("Actividad por Terminal")

# Ordenar terminales por el orden canónico
terminals_present = df["terminal"].unique().tolist()
terminals_ordered = [t for t in TERMINAL_ORDER if t in terminals_present]
terminals_ordered += [t for t in terminals_present if t not in TERMINAL_ORDER]

def _build_display_df(df_term: pd.DataFrame) -> pd.DataFrame:
    """Construye el DataFrame para visualización."""
    cols_map = {
        "crucero_norm": "Barco",
        "crucero": "Barco",
        "eta": "ETA",
        "etd": "ETD",
        "status": "Status",
        "pasajeros": "Pasajeros",
        "pasajeros_pendiente": "_pendiente",
        "grupo_naviera": "Naviera",
    }

    # Determinar columna de nombre del barco
    name_col = "crucero_norm" if "crucero_norm" in df_term.columns else "crucero"

    rows = []
    for _, row in df_term.iterrows():
        status_icon = STATUS_COLORS.get(row.get("status", ""), "⚪")
        pendiente = row.get("pasajeros_pendiente", False)

        pax = row.get("pasajeros", 0)
        if pendiente:
            pax_display = "⏳ Pendiente"
        elif row.get("status") == "Cancelado":
            pax_display = "—"
        elif pax > 0:
            pax_display = f"{int(pax):,}"
        else:
            pax_display = "0"

        rows.append(
            {
                "Barco": row.get(name_col, "—"),
                "Naviera": row.get("grupo_naviera", "—"),
                "ETA": str(row.get("eta", "—"))[:5],
                "ETD": str(row.get("etd", "—"))[:5],
                "Status": f"{status_icon} {row.get('status', '—')}",
                "Pasajeros": pax_display,
            }
        )

    return pd.DataFrame(rows)


for terminal in terminals_ordered:
    df_term = df[df["terminal"] == terminal].copy()
    if df_term.empty:
        continue

    barcos_term = len(df_term)
    cancelados_term = len(df_term[df_term["status"] == "Cancelado"])
    st.markdown(f"#### ⚓ {terminal.title()}")
    st.caption(f"{barcos_term} barcos · {cancelados_term} cancelaciones")

    display_cols = _build_display_df(df_term)
    st.dataframe(
        display_cols,
        width="stretch",
        hide_index=True,
    )
    st.markdown("")
