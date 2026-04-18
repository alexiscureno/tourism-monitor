#!/usr/bin/env python3
"""
seed_ships.py — Seed ships_master con navieras inferidas del nombre del barco.

Lógica:
  1. Saca los crucero_norm únicos de cruise_visits
  2. Asigna grupo_naviera por reglas de nombre
  3. Upserta en ships_master
  4. Actualiza cruise_visits.grupo_naviera en batch

Uso:
  uv run python scripts/seed_ships.py [--dry-run]
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─── REGLAS DE NAVIERA ────────────────────────────────────────────────

# Overrides manuales para barcos con nombre ambiguo o typos
MANUAL_OVERRIDES: dict[str, str] = {
    # Typos frecuentes en APIQROO
    "CRISTAL SERENITY":          "Crystal Cruises",
    "CRISTAL SYMPHONY":          "Crystal Cruises",
    "KONINGSDAN":                "Holland America",
    "MEIN SHIFF 4":              "TUI Cruises",
    "MEIN SHIFF 6":              "TUI Cruises",
    "CROWN PRINCES":             "Princess",
    "CS AIDAVITA":               "AIDA",
    # Nombres sin marca explícita
    "JOURNEY":                   "Azamara",       # Azamara Journey
    "ALLURA":                    "Norwegian",     # Norwegian Allura (2026)
    "ILMA":                      "Norwegian",     # Norwegian Ilma (2024)
    "VISTA":                     "Oceania Cruises",
    "VOYAGER":                   "Oceania Cruises",
    "INSIGNIA":                  "Oceania Cruises",
    "MARINA":                    "Oceania Cruises",
    "NAUTICA":                   "Oceania Cruises",
    "REGATTA":                   "Oceania Cruises",
    "RIVIERA":                   "Oceania Cruises",
    "SIRENA":                    "Oceania Cruises",
    # Fred. Olsen
    "BALMORAL":                  "Fred. Olsen",
    "BLACK WATCH":               "Fred. Olsen",
    "BOUDICCA":                  "Fred. Olsen",
    "BRAEMAR":                   "Fred. Olsen",
    # Phoenix Reisen
    "AMADEA":                    "Phoenix Reisen",
    "AMERA":                     "Phoenix Reisen",
    "ARTANIA":                   "Phoenix Reisen",
    "BERLIN":                    "Phoenix Reisen",
    # Hapag-Lloyd
    "EUROPA":                    "Hapag-Lloyd",
    "EUROPA 2":                  "Hapag-Lloyd",
    "HAMBURG":                   "Hapag-Lloyd",
    # Hurtigruten
    "FRAM":                      "Hurtigruten",
    "RCGS RESOLUTE":             "Hurtigruten",
    "WORLD VOYAGER":             "Hurtigruten",
    # P&O
    "AURORA":                    "P&O Cruises",
    "OCEANA":                    "P&O Cruises",
    "ORIANA":                    "P&O Cruises",
    "VENTURA":                   "P&O Cruises",
    "AMBIENCE":                  "P&O Cruises",  # ex-Pacific Eden, ex-Holland America
    # Sea Cloud
    "S/Y SEA CLOUD":             "Sea Cloud Cruises",
    "S/Y SEA CLOUD II":          "Sea Cloud Cruises",
    "SEA CLOUD SPIRIT":          "Sea Cloud Cruises",
    # Windstar
    "WINDSURF":                  "Windstar",
    "STAR LEGEND":               "Windstar",
    # Otros
    "COLOMBUS":                  "Nicko Cruises",
    "VASCO DA GAMA":             "Nicko Cruises",
    "MARCO POLO":                "Cruise & Maritime",
    "MAGELLAN":                  "Cruise & Maritime",
    "THOMSON DREAM":             "TUI Cruises",
    "OCEAN DREAM":               "Otras",
    "OCEAN VOYAGER":             "Otras",
    "THE WORLD":                 "The World",
    "SERENISSIMA":               "Noble Caledonia",
    "MINERVA":                   "Swan Hellenic",
    "ASUKA II":                  "NYK Cruises",
    "CLUB MED 2":                "Club Med",
    "MARGARITAVILLE AT SEA ISLANDER": "Margaritaville at Sea",
    "VIDANTAWORLD'S ELEGANT":    "Otras",
    "QUEEN ELIZABETH":           "Cunard",
    "OCEAN DREAM":               "Otras",
    "OCEAN VOYAGER":             "Otras",
}

# Barcos RCL conocidos (algunos no terminan en "OF THE SEAS")
RCL_SHIPS = {
    "ADVENTURE OF THE SEAS", "ALLURE OF THE SEAS", "ANTHEM OF THE SEAS",
    "BRILLIANCE OF THE SEAS", "ENCHANTMENT OF THE SEAS", "EMPRESS OF THE SEAS",
    "EXPLORER OF THE SEAS", "FREEDOM OF THE SEAS", "GRANDEUR OF THE SEAS",
    "HARMONY OF THE SEAS", "ICON OF THE SEAS", "INDEPENDENCE OF THE SEAS",
    "JEWEL OF THE SEAS", "LIBERTY OF THE SEAS", "MARINER OF THE SEAS",
    "NAVIGATOR OF THE SEAS", "OASIS OF THE SEAS", "ODYSSEY OF THE SEAS",
    "RADIANCE OF THE SEAS", "RHAPSODY OF THE SEAS", "SERENADE OF THE SEAS",
    "SYMPHONY OF THE SEAS", "UTOPIA OF THE SEAS", "VISION OF THE SEAS",
    "VOYAGER OF THE SEAS", "WONDER OF THE SEAS", "STAR OF THE SEAS",
}

HOLLAND_AMERICA_SHIPS = {
    "EURODAM", "KONINGSDAM", "MAASDAM", "NIEUW AMSTERDAM", "NIEUW STATENDAM",
    "OOSTERDAM", "ROTTERDAM", "VEEDAM", "VEENDAM", "WESTERDAM", "ZUIDERDAM",
}

PRINCESS_KEYWORDS = {
    "PRINCESS", "CORAL PRINCESS", "CARIBBEAN PRINCESS",
}


def infer_grupo_naviera(nombre: str) -> str:
    """Infiere grupo_naviera a partir del nombre normalizado del barco."""
    # Overrides manuales primero
    if nombre in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[nombre]

    n = nombre.upper().strip()

    # ── Carnival Corporation brands ──────────────────────────────
    if n.startswith("CARNIVAL ") or n == "MARDI GRAS":
        return "Carnival"
    if n.startswith("COSTA "):
        return "Costa"
    if n.startswith("AIDA") or n.startswith("CS AIDA"):
        return "AIDA"
    if n.startswith("SEABOURN "):
        return "Seabourn"
    if "PRINCESS" in n:
        return "Princess"
    if n in HOLLAND_AMERICA_SHIPS:
        return "Holland America"
    if n.startswith("NIEUW "):
        return "Holland America"
    if n.startswith("P&O") or n in {"AURORA", "OCEANA", "ORIANA", "VENTURA"}:
        return "P&O Cruises"

    # ── Royal Caribbean Group ────────────────────────────────────
    if n.startswith("CELEBRITY "):
        return "Celebrity Cruises"
    if n.startswith("SILVER "):
        return "Silversea"
    if n.startswith("AZAMARA "):
        return "Azamara"
    if n in RCL_SHIPS or n.endswith(" OF THE SEAS"):
        return "Royal Caribbean"

    # ── Norwegian Cruise Group ───────────────────────────────────
    if n.startswith("NORWEGIAN "):
        return "Norwegian"
    if n.startswith("SEVEN SEAS "):
        return "Regent Seven Seas"

    # ── MSC ──────────────────────────────────────────────────────
    if n.startswith("MSC ") or n.startswith("MSC."):
        return "MSC"

    # ── Disney ───────────────────────────────────────────────────
    if n.startswith("DISNEY "):
        return "Disney"

    # ── Viking ───────────────────────────────────────────────────
    if n.startswith("VIKING "):
        return "Viking"

    # ── TUI ──────────────────────────────────────────────────────
    if n.startswith("MEIN S"):
        return "TUI Cruises"
    if n.startswith("MARELLA "):
        return "Marella Cruises"

    # ── Virgin Voyages ───────────────────────────────────────────
    if n.endswith(" LADY"):
        return "Virgin Voyages"

    # ── Crystal ──────────────────────────────────────────────────
    if n.startswith("CRYSTAL ") or n.startswith("CRISTAL "):
        return "Crystal Cruises"

    # ── Ponant ───────────────────────────────────────────────────
    if n.startswith("LE "):
        return "Ponant"

    # ── Scenic ───────────────────────────────────────────────────
    if n.startswith("SCENIC "):
        return "Scenic"

    # ── Sea Cloud ────────────────────────────────────────────────
    if "SEA CLOUD" in n:
        return "Sea Cloud Cruises"

    return "Otras"


# ─── MAIN ────────────────────────────────────────────────────────────

def main(dry_run: bool = False):
    from src.db.client import get_client, upsert_ships_master

    client = get_client()

    # 1. Obtener crucero_norm únicos
    logger.info("Obteniendo nombres únicos de cruise_visits...")
    all_names: set[str] = set()
    offset, limit = 0, 1000
    while True:
        resp = client.table("cruise_visits").select("crucero_norm").range(offset, offset + limit - 1).execute()
        if not resp.data:
            break
        for r in resp.data:
            if r.get("crucero_norm"):
                all_names.add(r["crucero_norm"])
        if len(resp.data) < limit:
            break
        offset += limit

    logger.info(f"  {len(all_names)} barcos únicos encontrados")

    # 2. Asignar navieras
    records = []
    unclassified = []
    for nombre in sorted(all_names):
        naviera = infer_grupo_naviera(nombre)
        records.append({"nombre": nombre, "grupo_naviera": naviera})
        if naviera == "Otras":
            unclassified.append(nombre)

    if unclassified:
        logger.warning(f"  {len(unclassified)} barcos sin naviera identificada: {unclassified}")

    # Preview
    df = pd.DataFrame(records)
    summary = df.groupby("grupo_naviera")["nombre"].count().sort_values(ascending=False)
    logger.info("\nDistribución por naviera:")
    for naviera, count in summary.items():
        logger.info(f"  {naviera:<30} {count:>3} barcos")

    if dry_run:
        logger.info("\nDry run — no se guardó nada")
        return

    # 3. Upsert en ships_master
    logger.info(f"\nUpserting {len(records)} registros en ships_master...")
    count, _ = upsert_ships_master(df)
    logger.info(f"  ✅ {count} registros procesados en ships_master")

    # 4. Actualizar cruise_visits.grupo_naviera en batch
    logger.info("Actualizando grupo_naviera en cruise_visits...")
    updated_total = 0
    for _, row in df.iterrows():
        resp = (
            client.table("cruise_visits")
            .update({"grupo_naviera": row["grupo_naviera"]})
            .eq("crucero_norm", row["nombre"])
            .execute()
        )
        updated_total += len(resp.data) if resp.data else 0

    logger.info(f"  ✅ {updated_total} registros de cruise_visits actualizados")
    logger.info("\n✅ seed_ships completado")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed ships_master con navieras")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar, no guardar")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
