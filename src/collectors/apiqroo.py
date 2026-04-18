"""
Colector APIQROO — Tourism Monitor Cozumel
Scraper del Calendario de Cruceros de APIQROO para Cozumel.
URL: https://servicios.apiqroo.com.mx/programacion/

Estructura real de la página (verificada 2026-04-17):
- 2 tablas base (Programación + leyenda)
- Al cargar Histórico: se añaden 2 tablas más (Histórico + leyenda)
- La tabla Histórico está en el índice 2 (0-indexed)
- Columnas Histórico: terminal | bandera | crucero | fecha | eta | etd | status_img | pasajeros
- Status: <img src="assets/images/icon/circle_green/red/yellow.png">
- Meses en el select: zero-padded '01'..'12'
"""

import asyncio
import logging
from datetime import date
from typing import Optional

import pandas as pd
from playwright.async_api import async_playwright, Page, ElementHandle

logger = logging.getLogger(__name__)

APIQROO_URL = "https://servicios.apiqroo.com.mx/programacion/"
REQUEST_DELAY_SECONDS = 1.5

SEL_YEAR = "select#anio"
SEL_MONTH = "select#mes"
SEL_QUERY_BTN = 'button:has-text("Consultar")'
SEL_HISTORICO_TAB = 'text=Histórico'


# ─── PUBLIC API ─────────────────────────────────────────────────────────

def scrape_programacion() -> pd.DataFrame:
    """Scrape tab Programación — cruceros del mes actual (sin pasajeros)."""
    return asyncio.run(_scrape_programacion_async())


def scrape_historico_month(year: int, month: int) -> pd.DataFrame:
    """Scrape tab Histórico para un mes/año. Incluye pasajeros."""
    return asyncio.run(_scrape_historico_async(year, month))


def scrape_historico_range(date_from: date, date_to: Optional[date] = None) -> pd.DataFrame:
    """Scrape Histórico iterando mes a mes con delay entre requests."""
    if date_to is None:
        date_to = date.today()
    return asyncio.run(_scrape_range_async(date_from, date_to))


# ─── ASYNC IMPLEMENTATIONS ──────────────────────────────────────────────

async def _scrape_programacion_async() -> pd.DataFrame:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(APIQROO_URL, wait_until="networkidle", timeout=30000)
            await page.click(SEL_QUERY_BTN)
            await asyncio.sleep(3)
            tables = await page.query_selector_all("table")
            if not tables:
                return pd.DataFrame()
            df = await _parse_historico_table(tables[0])
            logger.info(f"scrape_programacion: {len(df)} registros")
            return df
        finally:
            await browser.close()


async def _scrape_historico_async(year: int, month: int) -> pd.DataFrame:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(APIQROO_URL, wait_until="networkidle", timeout=30000)
            df = await _scrape_historico_page(page, year, month)
            logger.info(f"scrape_historico_month({year}-{month:02d}): {len(df)} registros")
            return df
        finally:
            await browser.close()


async def _scrape_range_async(date_from: date, date_to: date) -> pd.DataFrame:
    all_dfs = []
    months = _generate_month_list(date_from, date_to)
    total = len(months)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(APIQROO_URL, wait_until="networkidle", timeout=30000)

            for i, (year, month) in enumerate(months, 1):
                logger.info(f"  [{i}/{total}] Scrapeando {year}-{month:02d}...")
                try:
                    df = await _scrape_historico_page(page, year, month)
                    if not df.empty:
                        all_dfs.append(df)
                        logger.info(f"    → {len(df)} registros")
                    else:
                        logger.warning(f"    → 0 registros")
                    await asyncio.sleep(REQUEST_DELAY_SECONDS)
                except Exception as e:
                    logger.warning(f"  Error en {year}-{month:02d}: {e} — saltando")
                    continue
        finally:
            await browser.close()

    if not all_dfs:
        return pd.DataFrame()

    result = pd.concat(all_dfs, ignore_index=True)
    if all(c in result.columns for c in ["fecha", "terminal", "crucero"]):
        result = result.drop_duplicates(subset=["fecha", "terminal", "crucero"])

    logger.info(f"scrape_historico_range: {len(result)} registros totales")
    return result


async def _scrape_historico_page(page: Page, year: int, month: int) -> pd.DataFrame:
    """
    Navega al tab Histórico, selecciona año/mes y extrae la tabla correcta.

    Nota: La página usa Bootstrap Select (selectpicker) que oculta los <select>
    nativos. Se usan JS evaluations para setear los valores directamente.
    """
    try:
        # Click en tab Histórico
        await page.click(SEL_HISTORICO_TAB)
        await asyncio.sleep(1.5)  # Esperar animación del tab

        # Setear año y mes via JavaScript (Bootstrap Select oculta los selects)
        await page.evaluate(
            """([year, month]) => {
                const anio = document.querySelector('#anio');
                const mes  = document.querySelector('#mes');
                if (anio) anio.value = year;
                if (mes)  mes.value  = month;
                // Refrescar Bootstrap Select si está disponible
                if (typeof $ !== 'undefined') {
                    try { $('#anio').selectpicker('val', year); } catch(e) {}
                    try { $('#mes').selectpicker('val', month); } catch(e) {}
                }
            }""",
            [str(year), f"{month:02d}"]
        )
        await asyncio.sleep(0.5)

        # Click Consultar
        await page.click(SEL_QUERY_BTN)
        await asyncio.sleep(3)

        # La tabla Histórico está en índice 2 después de cargar (4 tablas en total)
        tables = await page.query_selector_all("table")
        if len(tables) < 3:
            logger.warning(f"Solo {len(tables)} tablas — Histórico no cargó ({year}-{month:02d})")
            return pd.DataFrame()

        df = await _parse_historico_table(tables[2])
        return df

    except Exception as e:
        logger.error(f"_scrape_historico_page({year}-{month:02d}): {e}")
        return pd.DataFrame()


async def _parse_historico_table(table: ElementHandle) -> pd.DataFrame:
    """
    Parsea la tabla Histórico de APIQROO.

    Estructura (8 columnas por fila de datos):
      [0] terminal | [1] bandera | [2] crucero | [3] fecha
      [4] eta      | [5] etd     | [6] status  | [7] pasajeros

    Filas especiales:
      - colspan=8: encabezado de fecha (ej. "Sunday, 01 de june de 2025")
      - cells=0: separador vacío
    """
    rows = await table.query_selector_all("tbody tr")
    records = []
    current_fecha_dia = ""

    for row in rows:
        cells = await row.query_selector_all("td")
        if not cells:
            continue

        first = cells[0]
        colspan = await first.get_attribute("colspan")

        # Fila de encabezado de fecha
        if colspan:
            current_fecha_dia = (await first.inner_text()).strip()
            continue

        # Fila de datos (debe tener exactamente 8 celdas)
        if len(cells) != 8:
            continue

        terminal   = (await cells[0].inner_text()).strip()
        bandera    = (await cells[1].inner_text()).strip()
        crucero    = (await cells[2].inner_text()).strip()
        fecha      = (await cells[3].inner_text()).strip()
        eta        = (await cells[4].inner_text()).strip()
        etd        = (await cells[5].inner_text()).strip()
        pasajeros  = (await cells[7].inner_text()).strip()

        # Status: extraer de img src
        status = await _extract_status(cells[6])

        if not terminal or not crucero or not fecha:
            continue

        records.append({
            "fecha_dia":  current_fecha_dia,
            "puerto":     terminal,
            "bandera":    bandera,
            "crucero":    crucero,
            "fecha":      fecha,
            "eta":        eta,
            "etd":        etd,
            "status":     status,
            "pasajeros":  pasajeros or "0",
        })

    return pd.DataFrame(records)


async def _extract_status(cell: ElementHandle) -> str:
    """Extrae el status desde el src de la imagen dentro de la celda."""
    img = await cell.query_selector("img")
    if img:
        src = await img.get_attribute("src") or ""
        if "circle_green" in src:
            return "Arribado"
        if "circle_red" in src:
            return "Cancelado"
        if "circle_yellow" in src:
            return "Programado"
    # Fallback: texto de la celda
    text = (await cell.inner_text()).strip().lower()
    if "arriba" in text or "green" in text:
        return "Arribado"
    if "cancel" in text or "red" in text:
        return "Cancelado"
    return "Programado"


def _generate_month_list(date_from: date, date_to: date) -> list[tuple[int, int]]:
    months = []
    current = date(date_from.year, date_from.month, 1)
    end = date(date_to.year, date_to.month, 1)
    while current <= end:
        months.append((current.year, current.month))
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return months
