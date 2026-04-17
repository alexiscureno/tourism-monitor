"""
Seed Historical Data — Tourism Monitor Cozumel
Carga el CSV histórico (cruceros_cozumel_04.csv) en Supabase.

Uso:
    uv run python scripts/seed_historical.py
    uv run python scripts/seed_historical.py --dry-run
"""

import argparse
import logging
import sys
from pathlib import Path

# Asegurar que src/ esté en el path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from dotenv import load_dotenv

from src.processors.cleaner import clean
from src.pipeline.hooks.pre_store_validation import validate
from src.db.client import upsert_cruise_visits

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

CSV_PATH = Path("data/raw/cruceros_cozumel_04.csv")
BATCH_SIZE = 500


def main(dry_run: bool = False) -> None:
    logger.info("=" * 55)
    logger.info("Seed Historical Data — Cruise Visits")
    logger.info(f"CSV: {CSV_PATH}")
    logger.info(f"Dry run: {dry_run}")
    logger.info("=" * 55)

    # ── CARGAR CSV ───────────────────────────────────────────
    if not CSV_PATH.exists():
        logger.error(f"CSV no encontrado: {CSV_PATH}")
        sys.exit(1)

    df_raw = pd.read_csv(CSV_PATH)
    logger.info(f"CSV cargado: {len(df_raw)} registros")

    # ── LIMPIAR ──────────────────────────────────────────────
    df_clean = clean(df_raw)
    logger.info(f"Después de limpieza: {len(df_clean)} registros")

    # ── VALIDAR ──────────────────────────────────────────────
    try:
        validate(df_clean, stage="seed_historical")
    except ValueError as e:
        logger.error(f"Validación fallida: {e}")
        logger.error("Abortando seed.")
        sys.exit(1)

    # ── UPSERT EN LOTES ──────────────────────────────────────
    if dry_run:
        logger.info("[DRY RUN] No se insertará nada en Supabase.")
        logger.info(f"Registros que se insertarían: {len(df_clean)}")
        return

    total_new = 0
    total_updated = 0
    total_errors = 0

    batches = [
        df_clean.iloc[i : i + BATCH_SIZE]
        for i in range(0, len(df_clean), BATCH_SIZE)
    ]

    for i, batch in enumerate(batches, 1):
        try:
            new, updated = upsert_cruise_visits(batch)
            total_new += new
            total_updated += updated
            logger.info(
                f"  Lote {i}/{len(batches)}: {len(batch)} registros → "
                f"{new} nuevos, {updated} actualizados"
            )
        except Exception as e:
            logger.error(f"  Lote {i} fallido: {e}")
            total_errors += len(batch)

    # ── RESUMEN ──────────────────────────────────────────────
    logger.info("=" * 55)
    logger.info(f"✅ Seed completado")
    logger.info(f"   Nuevos:      {total_new}")
    logger.info(f"   Actualizados: {total_updated}")
    logger.info(f"   Errores:     {total_errors}")
    logger.info("=" * 55)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed historical cruise data to Supabase")
    parser.add_argument("--dry-run", action="store_true", help="No escribir en Supabase")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
