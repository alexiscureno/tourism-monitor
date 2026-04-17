"""
Supabase client — Tourism Monitor Cozumel
Operaciones de lectura y escritura contra las tablas del proyecto.
"""

import os
import logging
from datetime import date
from typing import Optional

import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

_client: Optional[Client] = None


def get_client() -> Client:
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
        _client = create_client(url, key)
    return _client


# ─── CRUISE VISITS ──────────────────────────────────────────────────────

def upsert_cruise_visits(df: pd.DataFrame) -> tuple[int, int]:
    """
    Upsert registros en cruise_visits.
    Retorna (nuevos, actualizados).
    """
    client = get_client()

    records = _df_to_records(df, table="cruise_visits")
    if not records:
        return 0, 0

    # Supabase upsert with ON CONFLICT (fecha, terminal, crucero_norm)
    response = (
        client.table("cruise_visits")
        .upsert(records, on_conflict="fecha,terminal,crucero_norm")
        .execute()
    )

    # Supabase doesn't differentiate insert vs update in response
    # Count based on response data length vs pre-existing records
    count = len(response.data) if response.data else 0
    logger.info(f"upsert_cruise_visits: {count} registros procesados")
    return count, 0


def upsert_ships_master(df: pd.DataFrame) -> tuple[int, int]:
    """Upsert registros en ships_master (ON CONFLICT nombre)."""
    client = get_client()
    records = _df_to_records(df, table="ships_master")
    if not records:
        return 0, 0

    response = (
        client.table("ships_master")
        .upsert(records, on_conflict="nombre")
        .execute()
    )
    count = len(response.data) if response.data else 0
    return count, 0


def upsert_weather_daily(df: pd.DataFrame) -> tuple[int, int]:
    """Upsert registros en weather_daily (ON CONFLICT fecha)."""
    client = get_client()
    records = _df_to_records(df, table="weather_daily")
    if not records:
        return 0, 0

    response = (
        client.table("weather_daily")
        .upsert(records, on_conflict="fecha")
        .execute()
    )
    count = len(response.data) if response.data else 0
    return count, 0


# ─── QUERIES ────────────────────────────────────────────────────────────

def query_visits_by_date(target_date: date) -> pd.DataFrame:
    """Retorna todos los cruceros de una fecha específica."""
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


def query_visits_range(
    date_from: date,
    date_to: date,
    naviera: Optional[str] = None,
    terminal: Optional[str] = None,
    status: Optional[str] = None,
) -> pd.DataFrame:
    """Retorna cruceros en un rango de fechas con filtros opcionales."""
    client = get_client()
    query = (
        client.table("cruise_visits")
        .select("*")
        .gte("fecha", date_from.isoformat())
        .lte("fecha", date_to.isoformat())
    )
    if naviera:
        query = query.eq("grupo_naviera", naviera)
    if terminal:
        query = query.eq("terminal", terminal)
    if status:
        query = query.eq("status", status)

    response = query.order("fecha").execute()
    return _to_df(response.data)


# ─── HELPERS ────────────────────────────────────────────────────────────

def _df_to_records(df: pd.DataFrame, table: str) -> list[dict]:
    """Convierte DataFrame a lista de dicts, serializando fechas y NaN."""
    if df.empty:
        return []

    records = []
    for _, row in df.iterrows():
        record = {}
        for col, val in row.items():
            if pd.isna(val) if not isinstance(val, (list, dict)) else False:
                record[col] = None
            elif hasattr(val, "isoformat"):
                record[col] = val.isoformat()
            else:
                record[col] = val
        records.append(record)
    return records


def _to_df(data: list[dict]) -> pd.DataFrame:
    """Convierte respuesta de Supabase a DataFrame."""
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
    return df
