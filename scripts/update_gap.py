"""
Update Gap — Tourism Monitor Cozumel
Llena el gap de datos faltantes (junio 2025 → mes anterior al actual).
Hace scraping de APIQROO Histórico para el rango solicitado.

Uso:
    uv run python scripts/update_gap.py
    uv run python scripts/update_gap.py --from 2025-06-01 --to 2026-04-30
    uv run python scripts/update_gap.py --dry-run
"""

import argparse
import logging
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

# Gap predeterminado: junio 2025 → mes anterior al actual
DEFAULT_FROM = date(2025, 6, 1)


def _default_to() -> date:
    today = date.today()
    # Mes anterior al actual (los datos del mes en curso tienen pasajeros=0)
    if today.month == 1:
        return date(today.year - 1, 12, 31)
    return date(today.year, today.month - 1, 28)


def main(date_from: date, date_to: date, dry_run: bool = False) -> None:
    logger.info("=" * 55)
    logger.info("Update Gap — APIQROO Histórico")
    logger.info(f"Rango: {date_from} → {date_to}")
    logger.info(f"Dry run: {dry_run}")
    logger.info("=" * 55)

    from src.collectors.apiqroo import scrape_historico_range
    from src.processors.cleaner import clean
    from src.pipeline.hooks.pre_store_validation import validate
    from src.db.client import upsert_cruise_visits

    # ── SCRAPE ───────────────────────────────────────────────
    logger.info("Iniciando scraping...")
    df_raw = scrape_historico_range(date_from, date_to)
    logger.info(f"Scraping completado: {len(df_raw)} registros crudos")

    if df_raw.empty:
        logger.warning("No se obtuvieron datos. Verificar fechas y conectividad.")
        return

    # ── LIMPIAR ──────────────────────────────────────────────
    df_clean = clean(df_raw)
    logger.info(f"Después de limpieza: {len(df_clean)} registros")

    # ── VALIDAR ──────────────────────────────────────────────
    try:
        validate(df_clean, stage="update_gap")
    except ValueError as e:
        logger.error(f"Validación fallida: {e}")
        logger.error("Abortando update_gap.")
        sys.exit(1)

    # ── GUARDAR CSV DE BACKUP ────────────────────────────────
    backup_path = Path(f"data/raw/gap_{date_from}_{date_to}.csv")
    df_clean.to_csv(backup_path, index=False)
    logger.info(f"Backup guardado: {backup_path}")

    # ── UPSERT ───────────────────────────────────────────────
    if dry_run:
        logger.info("[DRY RUN] No se insertará nada en Supabase.")
        logger.info(f"Registros que se insertarían: {len(df_clean)}")
        return

    new, updated = upsert_cruise_visits(df_clean)

    logger.info("=" * 55)
    logger.info("✅ Update gap completado")
    logger.info(f"   Nuevos:      {new}")
    logger.info(f"   Actualizados: {updated}")
    logger.info("=" * 55)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fill gap in APIQROO historical data")
    parser.add_argument(
        "--from",
        dest="date_from",
        default=DEFAULT_FROM.isoformat(),
        help=f"Fecha inicio (YYYY-MM-DD), default: {DEFAULT_FROM}",
    )
    parser.add_argument(
        "--to",
        dest="date_to",
        default=_default_to().isoformat(),
        help=f"Fecha fin (YYYY-MM-DD), default: {_default_to()}",
    )
    parser.add_argument("--dry-run", action="store_true", help="No escribir en Supabase")
    args = parser.parse_args()

    main(
        date_from=date.fromisoformat(args.date_from),
        date_to=date.fromisoformat(args.date_to),
        dry_run=args.dry_run,
    )
