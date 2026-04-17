"""
Queries reutilizables — Tourism Monitor Cozumel
Funciones de alto nivel sobre las tablas de Supabase.
"""

import logging
from datetime import date, timedelta
from typing import Optional

import pandas as pd

from .client import get_client, _to_df

logger = logging.getLogger(__name__)


def get_today_visits() -> pd.DataFrame:
    """Cruceros de hoy ordenados por terminal y ETA."""
    return _query_visits_date(date.today())


def get_monthly_series(
    year_from: int = 2015,
    year_to: Optional[int] = None,
    exclude_pending: bool = True,
    exclude_cancelled: bool = False,
) -> pd.DataFrame:
    """
    Serie mensual de pasajeros y visitas.
    Retorna df con columnas: year, month, year_month, total_visits, total_passengers, avg_passengers.
    """
    if year_to is None:
        year_to = date.today().year

    client = get_client()
    query = (
        client.table("cruise_visits")
        .select("fecha,pasajeros,pasajeros_pendiente,status")
        .gte("fecha", f"{year_from}-01-01")
        .lte("fecha", f"{year_to}-12-31")
    )
    if exclude_pending:
        query = query.eq("pasajeros_pendiente", False)
    if exclude_cancelled:
        query = query.neq("status", "Cancelado")

    response = query.execute()
    df = _to_df(response.data)

    if df.empty:
        return df

    df["fecha"] = pd.to_datetime(df["fecha"])
    df["year"] = df["fecha"].dt.year
    df["month"] = df["fecha"].dt.month
    df["year_month"] = df["fecha"].dt.to_period("M").astype(str)

    monthly = (
        df.groupby(["year", "month", "year_month"])
        .agg(
            total_visits=("fecha", "count"),
            total_passengers=("pasajeros", "sum"),
        )
        .reset_index()
        .sort_values("year_month")
    )
    monthly["avg_passengers"] = (
        monthly["total_passengers"] / monthly["total_visits"]
    ).round(0)
    return monthly


def get_naviera_market_share(
    date_from: date,
    date_to: date,
    metric: str = "visits",
) -> pd.DataFrame:
    """
    Market share por naviera en un período.
    metric: 'visits' | 'passengers'
    """
    client = get_client()
    response = (
        client.table("cruise_visits")
        .select("grupo_naviera,pasajeros,status")
        .gte("fecha", date_from.isoformat())
        .lte("fecha", date_to.isoformat())
        .eq("status", "Arribado")
        .eq("pasajeros_pendiente", False)
        .execute()
    )
    df = _to_df(response.data)
    if df.empty:
        return df

    if metric == "passengers":
        result = (
            df.groupby("grupo_naviera")["pasajeros"]
            .sum()
            .reset_index()
            .rename(columns={"pasajeros": "total"})
        )
    else:
        result = (
            df.groupby("grupo_naviera")
            .size()
            .reset_index(name="total")
        )

    result["share_pct"] = (result["total"] / result["total"].sum() * 100).round(1)
    return result.sort_values("total", ascending=False)


def get_terminal_distribution(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> pd.DataFrame:
    """Distribución de visitas y pasajeros por terminal."""
    client = get_client()
    query = (
        client.table("cruise_visits")
        .select("terminal,pasajeros,status,pasajeros_pendiente")
        .eq("status", "Arribado")
        .eq("pasajeros_pendiente", False)
    )
    if date_from:
        query = query.gte("fecha", date_from.isoformat())
    if date_to:
        query = query.lte("fecha", date_to.isoformat())

    response = query.execute()
    df = _to_df(response.data)
    if df.empty:
        return df

    return (
        df.groupby("terminal")
        .agg(
            total_visits=("terminal", "count"),
            total_passengers=("pasajeros", "sum"),
        )
        .reset_index()
        .sort_values("total_visits", ascending=False)
    )


def get_ships_without_capacity() -> pd.DataFrame:
    """Barcos en cruise_visits sin entrada en ships_master (para enriquecimiento manual)."""
    client = get_client()
    response = (
        client.table("cruise_visits")
        .select("crucero_norm")
        .is_("capacidad_double", "null")
        .execute()
    )
    df = _to_df(response.data)
    if df.empty:
        return df

    return (
        df["crucero_norm"]
        .value_counts()
        .reset_index()
        .rename(columns={"crucero_norm": "nombre", "count": "visits_sin_capacidad"})
    )


# ─── HELPERS ────────────────────────────────────────────────────────────

def _query_visits_date(target_date: date) -> pd.DataFrame:
    client = get_client()
    response = (
        client.table("cruise_visits")
        .select("*")
        .eq("fecha", target_date.isoformat())
        .order("terminal")
        .order("eta")
        .execute()
    )
    return _to_df(response.data)
