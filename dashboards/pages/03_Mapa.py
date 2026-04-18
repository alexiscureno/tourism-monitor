"""
Mapa AIS — Tourism Monitor · Cozumel
Posiciones en tiempo real de barcos en el área de Cozumel.
"""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import streamlit as st
import pandas as pd
import pydeck as pdk

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

st.set_page_config(
    page_title="Mapa · Tourism Monitor",
    page_icon="🗺️",
    layout="wide",
)

# ─── CONSTANTES ──────────────────────────────────────────────────────────
COZUMEL_LAT = 20.5215
COZUMEL_LON = -86.9476

# Nav status AIS
NAV_STATUS = {
    0: "Navegando",
    1: "Anclado",
    2: "Sin gobierno",
    3: "Maniobra restringida",
    5: "Amarrado",
    8: "Calado",
}

# ─── DATOS ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)  # Refresca cada 30 segundos
def _load_positions() -> pd.DataFrame:
    try:
        from src.db.client import get_client
        client = get_client()
        # Solo posiciones actualizadas en las últimas 2 horas
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        resp = (
            client.table("ship_positions")
            .select("*")
            .gte("updated_at", cutoff)
            .order("updated_at", desc=True)
            .execute()
        )
        if not resp.data:
            return pd.DataFrame()
        df = pd.DataFrame(resp.data)
        df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
        df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
        df["sog"] = pd.to_numeric(df.get("sog", 0), errors="coerce").fillna(0)
        return df.dropna(subset=["lat", "lon"])
    except Exception as e:
        st.error(f"Error cargando posiciones: {e}")
        return pd.DataFrame()


# ─── LAYOUT ──────────────────────────────────────────────────────────────
st.title("🗺️ Mapa AIS — Barcos en Tiempo Real")
st.caption("Área: Caribe occidental · Fuente: aisstream.io · Refresca cada 30s")

col_refresh, col_info = st.columns([1, 3])
with col_refresh:
    if st.button("🔄 Actualizar"):
        st.cache_data.clear()
        st.rerun()

df = _load_positions()

if df.empty:
    st.info(
        "📡 Sin datos AIS recientes.\n\n"
        "Para ver barcos en tiempo real, inicia el colector:\n"
        "```\nuv run python src/collectors/ais_stream.py\n```",
        icon="ℹ️",
    )
else:
    with col_info:
        st.caption(f"**{len(df)} barcos** detectados en las últimas 2 horas")

# ─── MAPA ────────────────────────────────────────────────────────────────
if not df.empty:
    # Color por velocidad: verde=parado, amarillo=lento, rojo=en tránsito
    def _color(sog):
        if sog < 1:
            return [46, 204, 113, 220]    # verde — amarrado/anclado
        elif sog < 8:
            return [241, 196, 15, 220]    # amarillo — maniobra
        else:
            return [231, 76, 60, 220]     # rojo — navegando

    df["color"] = df["sog"].apply(_color)
    df["tooltip_text"] = df.apply(
        lambda r: f"{r.get('ship_name','?')} | {r.get('sog',0):.1f} kn | {NAV_STATUS.get(r.get('nav_status'), 'Desconocido')}",
        axis=1,
    )

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["lon", "lat"],
        get_color="color",
        get_radius=500,
        radius_min_pixels=6,
        radius_max_pixels=20,
        pickable=True,
    )

    # Capa de etiquetas con nombre del barco
    text_layer = pdk.Layer(
        "TextLayer",
        data=df,
        get_position=["lon", "lat"],
        get_text="ship_name",
        get_size=13,
        get_color=[255, 255, 255, 200],
        get_anchor="'middle'",
        get_alignment_baseline="'bottom'",
        get_pixel_offset=[0, -12],
    )

    view = pdk.ViewState(
        latitude=COZUMEL_LAT,
        longitude=COZUMEL_LON,
        zoom=9,
        pitch=0,
    )

    deck = pdk.Deck(
        layers=[layer, text_layer],
        initial_view_state=view,
        tooltip={"text": "{tooltip_text}"},
        map_style="mapbox://styles/mapbox/dark-v10",
    )

    st.pydeck_chart(deck, use_container_width=True)

    # ─── TABLA ───────────────────────────────────────────────────────
    st.divider()
    st.subheader("Detalle de barcos")

    display = df[["ship_name", "lat", "lon", "sog", "destination", "updated_at"]].copy()
    display.columns = ["Barco", "Lat", "Lon", "Velocidad (kn)", "Destino", "Última actualización"]
    display["Velocidad (kn)"] = display["Velocidad (kn)"].round(1)
    display["Lat"] = display["Lat"].round(4)
    display["Lon"] = display["Lon"].round(4)

    st.dataframe(display, use_container_width=True, hide_index=True)
else:
    # Mapa vacío centrado en Cozumel
    view = pdk.ViewState(latitude=COZUMEL_LAT, longitude=COZUMEL_LON, zoom=9)
    st.pydeck_chart(
        pdk.Deck(initial_view_state=view, map_style="mapbox://styles/mapbox/dark-v10"),
        use_container_width=True,
    )

# ─── LEYENDA ─────────────────────────────────────────────────────────────
with st.expander("Leyenda"):
    st.markdown("""
    | Color | Velocidad | Estado |
    |-------|-----------|--------|
    | 🟢 Verde | < 1 kn | Amarrado / Anclado |
    | 🟡 Amarillo | 1–8 kn | Maniobra / Saliendo |
    | 🔴 Rojo | > 8 kn | Navegando |
    """)
    st.caption("Fuente: AIS (Automatic Identification System) vía aisstream.io")
