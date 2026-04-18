"""
Explorador Histórico — Tourism Monitor · Cozumel
Análisis de cruceros desde 2015 con filtros por naviera, terminal y período.
"""

import sys
from datetime import date
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

st.set_page_config(
    page_title="Histórico · Tourism Monitor",
    page_icon="📊",
    layout="wide",
)

# ─── CARGA DE DATOS ──────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def _load_all() -> pd.DataFrame:
    """Carga todos los cruise_visits de Supabase."""
    try:
        from src.db.client import get_client
        client = get_client()
        all_rows = []
        offset, limit = 0, 1000
        while True:
            resp = (
                client.table("cruise_visits")
                .select("fecha,terminal,crucero_norm,grupo_naviera,pasajeros,pasajeros_pendiente,status")
                .range(offset, offset + limit - 1)
                .execute()
            )
            if not resp.data:
                break
            all_rows.extend(resp.data)
            if len(resp.data) < limit:
                break
            offset += limit

        df = pd.DataFrame(all_rows)
        df["fecha"] = pd.to_datetime(df["fecha"])
        df["year"] = df["fecha"].dt.year
        df["month"] = df["fecha"].dt.month
        df["year_month"] = df["fecha"].dt.to_period("M").astype(str)
        df["pasajeros"] = pd.to_numeric(df["pasajeros"], errors="coerce").fillna(0)
        df["pasajeros_pendiente"] = df["pasajeros_pendiente"].fillna(False)
        df["grupo_naviera"] = df["grupo_naviera"].fillna("Otras")
        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()


# ─── LAYOUT ──────────────────────────────────────────────────────────────
st.title("📊 Explorador Histórico")
st.caption("Cruceros en Cozumel · 2015 → presente")

df_full = _load_all()
if df_full.empty:
    st.stop()

# ─── SIDEBAR FILTROS ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 Filtros")

    # Rango de años
    min_year = int(df_full["year"].min())
    max_year = int(df_full["year"].max())
    year_range = st.slider(
        "Período",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year),
    )

    # Naviera
    navieras = sorted(df_full["grupo_naviera"].dropna().unique().tolist())
    navieras_sel = st.multiselect(
        "Naviera",
        options=navieras,
        default=[],
        placeholder="Todas",
    )

    # Terminal
    terminales = sorted(df_full["terminal"].dropna().unique().tolist())
    terminal_sel = st.multiselect(
        "Terminal",
        options=terminales,
        default=[],
        placeholder="Todas",
    )

    # Status
    status_sel = st.multiselect(
        "Status",
        options=["Arribado", "Programado", "Cancelado"],
        default=["Arribado"],
    )

    st.divider()
    excl_covid = st.checkbox("Excluir COVID (2020-2021)", value=True)
    excl_pendiente = st.checkbox("Excluir pasajeros pendientes", value=True)

    st.divider()
    if st.button("🔄 Recargar datos"):
        st.cache_data.clear()
        st.rerun()

# ─── APLICAR FILTROS ─────────────────────────────────────────────────────
df = df_full.copy()

df = df[df["year"].between(year_range[0], year_range[1])]

if navieras_sel:
    df = df[df["grupo_naviera"].isin(navieras_sel)]

if terminal_sel:
    df = df[df["terminal"].isin(terminal_sel)]

if status_sel:
    df = df[df["status"].isin(status_sel)]

if excl_covid:
    df = df[~df["year"].isin([2020, 2021])]

if excl_pendiente:
    df_pax = df[~df["pasajeros_pendiente"]]
else:
    df_pax = df

# ─── KPIs ────────────────────────────────────────────────────────────────
total_visitas = len(df)
total_pasajeros = int(df_pax["pasajeros"].sum())
avg_pax_visita = int(df_pax["pasajeros"].mean()) if not df_pax.empty else 0
navieras_unicas = df["grupo_naviera"].nunique()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Visitas", f"{total_visitas:,}")
col2.metric("Total Pasajeros", f"{total_pasajeros:,}")
col3.metric("Promedio Pax/Barco", f"{avg_pax_visita:,}")
col4.metric("Navieras", navieras_unicas)

st.divider()

# ─── GRÁFICAS ────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📈 Serie de Tiempo", "🥧 Market Share", "📋 Datos"])

# ── TAB 1: Serie mensual ──────────────────────────────────────────────────
with tab1:
    col_metric = st.radio(
        "Métrica",
        ["Pasajeros", "Visitas"],
        horizontal=True,
        key="ts_metric",
    )

    monthly = (
        df_pax.groupby("year_month")
        .agg(
            pasajeros=("pasajeros", "sum"),
            visitas=("fecha", "count"),
        )
        .reset_index()
        .sort_values("year_month")
    )

    if monthly.empty:
        st.info("Sin datos para los filtros seleccionados.")
    else:
        y_col = "pasajeros" if col_metric == "Pasajeros" else "visitas"
        y_label = "Pasajeros" if col_metric == "Pasajeros" else "Visitas de barcos"

        fig = px.bar(
            monthly,
            x="year_month",
            y=y_col,
            labels={"year_month": "Mes", y_col: y_label},
            color_discrete_sequence=["#3498db"],
        )
        fig.update_layout(
            xaxis_tickangle=-45,
            xaxis_tickfont_size=10,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            margin=dict(t=20, b=60),
        )
        fig.update_xaxes(
            tickmode="array",
            tickvals=monthly["year_month"][::6].tolist(),  # Cada 6 meses
        )
        st.plotly_chart(fig, use_container_width=True)

        # YoY por año
        st.subheader("Por año")
        yearly = (
            df_pax.groupby("year")
            .agg(pasajeros=("pasajeros", "sum"), visitas=("fecha", "count"))
            .reset_index()
        )
        fig2 = px.bar(
            yearly,
            x="year",
            y=y_col,
            labels={"year": "Año", y_col: y_label},
            color_discrete_sequence=["#2ecc71"],
            text_auto=True,
        )
        fig2.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            margin=dict(t=20),
        )
        st.plotly_chart(fig2, use_container_width=True)

# ── TAB 2: Market Share ───────────────────────────────────────────────────
with tab2:
    col_share = st.radio(
        "Métrica",
        ["Pasajeros", "Visitas"],
        horizontal=True,
        key="ms_metric",
    )

    y_col2 = "pasajeros" if col_share == "Pasajeros" else "visitas"

    naviera_agg = (
        df_pax.groupby("grupo_naviera")
        .agg(pasajeros=("pasajeros", "sum"), visitas=("fecha", "count"))
        .reset_index()
        .sort_values(y_col2, ascending=False)
    )

    if naviera_agg.empty:
        st.info("Sin datos.")
    else:
        col_pie, col_bar = st.columns([1, 1])

        with col_pie:
            fig_pie = px.pie(
                naviera_agg.head(10),
                values=y_col2,
                names="grupo_naviera",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                margin=dict(t=20, b=20),
                legend=dict(font_size=11),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_bar:
            fig_bar = px.bar(
                naviera_agg.head(10),
                x=y_col2,
                y="grupo_naviera",
                orientation="h",
                labels={"grupo_naviera": "", y_col2: col_share},
                color_discrete_sequence=["#9b59b6"],
                text_auto=True,
            )
            fig_bar.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                margin=dict(t=20),
                yaxis=dict(categoryorder="total ascending"),
            )
            st.plotly_chart(fig_bar, use_container_width=True)

# ── TAB 3: Tabla ──────────────────────────────────────────────────────────
with tab3:
    st.caption(f"{len(df):,} registros")

    display = df[["fecha", "crucero_norm", "grupo_naviera", "terminal", "status", "pasajeros"]].copy()
    display.columns = ["Fecha", "Barco", "Naviera", "Terminal", "Status", "Pasajeros"]
    display["Fecha"] = display["Fecha"].dt.strftime("%Y-%m-%d")
    display["Pasajeros"] = display["Pasajeros"].astype(int)

    st.dataframe(display, use_container_width=True, hide_index=True)

    csv = display.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Descargar CSV",
        data=csv,
        file_name=f"cozumel_cruceros_{year_range[0]}_{year_range[1]}.csv",
        mime="text/csv",
    )
