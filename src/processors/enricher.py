"""
Enricher — Tourism Monitor Cozumel
Enriquece cruise_visits con datos de ships_master y weather_daily.
"""

import logging
from typing import Optional

import pandas as pd
from rapidfuzz import process, fuzz

from .load_factor import calculate_load_factor

logger = logging.getLogger(__name__)

FUZZY_THRESHOLD = 85  # Score mínimo para match difuso


def enrich(
    df: pd.DataFrame,
    ships_df: Optional[pd.DataFrame] = None,
    weather_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Enriquece el DataFrame de cruise_visits con:
    - Datos de ships_master: grupo_naviera, gross_tonnage, capacidad_double
    - Load factor calculado
    - (Opcional) datos de weather_daily

    Args:
        df: DataFrame limpio de cruise_visits (salida de cleaner.clean)
        ships_df: DataFrame de ships_master (si None, intenta cargar de Supabase)
        weather_df: DataFrame de weather_daily (si None, se omite)

    Returns:
        DataFrame enriquecido.
    """
    if df.empty:
        return df

    result = df.copy()

    # ── JOIN CON SHIPS_MASTER ────────────────────────────────
    if ships_df is None:
        ships_df = _load_ships_from_db()

    if ships_df is not None and not ships_df.empty:
        result = _join_ships(result, ships_df)
    else:
        logger.warning("enrich: ships_df vacío — load_factor no calculado")
        result["grupo_naviera"] = None
        result["gross_tonnage"] = None
        result["capacidad_double"] = None
        result["load_factor"] = None

    # ── LOAD FACTOR ─────────────────────────────────────────
    if "pasajeros" in result.columns and "capacidad_double" in result.columns:
        # Solo calcular si no es pasajero_pendiente y no es cancelado
        mask = (
            ~result.get("pasajeros_pendiente", pd.Series(False, index=result.index))
            & (result.get("status", pd.Series("Arribado", index=result.index)) != "Cancelado")
        )
        result["load_factor"] = result.apply(
            lambda row: calculate_load_factor(
                row["pasajeros"],
                row.get("capacidad_double"),
            )
            if mask.loc[row.name]
            else None,
            axis=1,
        )

    # ── JOIN CON WEATHER_DAILY (opcional) ───────────────────
    if weather_df is not None and not weather_df.empty and "fecha" in result.columns:
        result = _join_weather(result, weather_df)

    logger.info(
        f"enrich: {len(result)} registros enriquecidos, "
        f"{result['load_factor'].notna().sum() if 'load_factor' in result.columns else 0} con load_factor"
    )
    return result


# ─── HELPERS ────────────────────────────────────────────────────────────

def _join_ships(df: pd.DataFrame, ships_df: pd.DataFrame) -> pd.DataFrame:
    """
    JOIN por crucero_norm. Usa exact match primero, luego fuzzy match.
    Añade: grupo_naviera, gross_tonnage, capacidad_double.
    """
    ships_cols = ["nombre", "grupo_naviera", "gross_tonnage", "capacidad_double"]
    available_cols = [c for c in ships_cols if c in ships_df.columns]
    ships_lookup = ships_df[available_cols].copy()
    ships_lookup = ships_lookup.rename(columns={"nombre": "crucero_norm"})

    # Exact match
    merged = df.merge(ships_lookup, on="crucero_norm", how="left")

    # Fuzzy match para los que no encontraron match exacto
    unmatched_mask = merged["grupo_naviera"].isna() if "grupo_naviera" in merged.columns else pd.Series(True, index=merged.index)
    unmatched_names = merged.loc[unmatched_mask, "crucero_norm"].unique().tolist()

    if unmatched_names and len(ships_lookup) > 0:
        ship_names = ships_lookup["crucero_norm"].tolist()
        fuzzy_map = {}

        for name in unmatched_names:
            if not name:
                continue
            match = process.extractOne(
                name,
                ship_names,
                scorer=fuzz.token_sort_ratio,
                score_cutoff=FUZZY_THRESHOLD,
            )
            if match:
                fuzzy_map[name] = match[0]

        if fuzzy_map:
            logger.info(f"enrich: {len(fuzzy_map)} matches difusos encontrados")
            for original, matched in fuzzy_map.items():
                mask = merged["crucero_norm"] == original
                ship_row = ships_lookup[ships_lookup["crucero_norm"] == matched]
                if not ship_row.empty:
                    for col in [c for c in available_cols if c != "nombre"]:
                        if col in ship_row.columns:
                            merged.loc[mask, col] = ship_row[col].values[0]

    return merged


def _join_weather(df: pd.DataFrame, weather_df: pd.DataFrame) -> pd.DataFrame:
    """JOIN con weather_daily por fecha."""
    weather_cols = ["fecha", "temp_max_c", "temp_min_c", "precipitacion_mm", "viento_max_kmh"]
    available_cols = [c for c in weather_cols if c in weather_df.columns]
    return df.merge(weather_df[available_cols], on="fecha", how="left")


def _load_ships_from_db() -> Optional[pd.DataFrame]:
    """Carga ships_master desde Supabase."""
    try:
        from src.db.client import get_client, _to_df
        client = get_client()
        response = (
            client.table("ships_master")
            .select("nombre,grupo_naviera,gross_tonnage,capacidad_double")
            .execute()
        )
        return _to_df(response.data)
    except Exception as e:
        logger.warning(f"enrich: no pudo cargar ships_master de DB — {e}")
        return None
