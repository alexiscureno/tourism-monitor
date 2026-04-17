"""
Seed Weather Data — Tourism Monitor Cozumel
Carga datos históricos de clima de Cozumel usando Open-Meteo Historical API.
No requiere API key.

Uso:
    uv run python scripts/seed_weather.py
    uv run python scripts/seed_weather.py --from 2015-10-01 --to 2026-04-17
    uv run python scripts/seed_weather.py --dry-run
"""

import argparse
import logging
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Coordenadas Cozumel (de research.md)
DEFAULT_LAT = float(os.getenv("COZUMEL_LAT", "20.5215"))
DEFAULT_LNG = float(os.getenv("COZUMEL_LNG", "-86.9476"))

DATA_START = date(2015, 10, 1)


def main(
    date_from: date,
    date_to: date,
    lat: float,
    lng: float,
    dry_run: bool = False,
) -> None:
    logger.info("=" * 55)
    logger.info("Seed Weather — Open-Meteo Historical API")
    logger.info(f"Coordenadas: {lat}, {lng}")
    logger.info(f"Rango: {date_from} → {date_to}")
    logger.info(f"Dry run: {dry_run}")
    logger.info("=" * 55)

    import openmeteo_requests
    import requests_cache
    from retry_requests import retry
    import pandas as pd

    # Setup Open-Meteo con cache y retry
    cache_session = requests_cache.CachedSession(".cache", expire_after=-1)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    om = openmeteo_requests.Client(session=retry_session)

    params = {
        "latitude": lat,
        "longitude": lng,
        "start_date": date_from.isoformat(),
        "end_date": date_to.isoformat(),
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "windspeed_10m_max",
            "weathercode",
        ],
        "timezone": "America/Cancun",
    }

    logger.info("Llamando Open-Meteo Historical API...")
    try:
        responses = om.weather_api(
            "https://archive-api.open-meteo.com/v1/archive",
            params=params,
        )
    except Exception as e:
        logger.error(f"Error llamando Open-Meteo: {e}")
        sys.exit(1)

    response = responses[0]
    daily = response.Daily()

    df = pd.DataFrame(
        {
            "fecha": pd.date_range(
                start=pd.to_datetime(daily.Time(), unit="s", utc=True),
                end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=daily.Interval()),
                inclusive="left",
            ).date,
            "temp_max_c": daily.Variables(0).ValuesAsNumpy().round(1),
            "temp_min_c": daily.Variables(1).ValuesAsNumpy().round(1),
            "precipitacion_mm": daily.Variables(2).ValuesAsNumpy().round(1),
            "viento_max_kmh": daily.Variables(3).ValuesAsNumpy().round(1),
            "weather_code": daily.Variables(4).ValuesAsNumpy().astype(int),
        }
    )

    # Convertir fecha a string para Supabase
    df["fecha"] = df["fecha"].astype(str)
    df["es_huracan"] = False  # Placeholder — no hay API de huracanes históricos

    logger.info(f"Datos recibidos: {len(df)} días")

    # Guardar backup CSV
    backup = Path(f"data/raw/weather_{date_from}_{date_to}.csv")
    df.to_csv(backup, index=False)
    logger.info(f"Backup: {backup}")

    if dry_run:
        logger.info("[DRY RUN] No se insertará nada en Supabase.")
        logger.info(df.head(5).to_string())
        return

    # Upsert en Supabase
    from src.db.client import upsert_weather_daily

    df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
    new, _ = upsert_weather_daily(df)

    logger.info("=" * 55)
    logger.info("✅ Seed weather completado")
    logger.info(f"   Registros procesados: {new}")
    logger.info("=" * 55)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed weather data from Open-Meteo")
    parser.add_argument(
        "--from",
        dest="date_from",
        default=DATA_START.isoformat(),
        help=f"Fecha inicio (YYYY-MM-DD), default: {DATA_START}",
    )
    parser.add_argument(
        "--to",
        dest="date_to",
        default=date.today().isoformat(),
        help=f"Fecha fin (YYYY-MM-DD), default: hoy",
    )
    parser.add_argument("--lat", type=float, default=DEFAULT_LAT)
    parser.add_argument("--lng", type=float, default=DEFAULT_LNG)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    main(
        date_from=date.fromisoformat(args.date_from),
        date_to=date.fromisoformat(args.date_to),
        lat=args.lat,
        lng=args.lng,
        dry_run=args.dry_run,
    )
