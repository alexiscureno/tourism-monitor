"""
Colector APIQROO — Tourism Monitor Cozumel
Scraper del Calendario de Cruceros de APIQROO para Cozumel.
URL: https://servicios.apiqroo.com.mx/programacion/

Usa Playwright para manejar los selects dinámicos de año/mes.
"""

import asyncio
import logging
import time
from datetime import date, timedelta
from typing import Optional

import pandas as pd
from playwright.async_api import async_playwright, Page

logger = logging.getLogger(__name__)

APIQROO_URL = "https://servicios.apiqroo.com.mx/programacion/"
REQUEST_DELAY_SECONDS = 1.5  # Cortesía con el servidor

# Selectores (de .claude/mental-models/apiqroo-data.yaml)
SEL_YEAR = "select#anio"
SEL_MONTH = "select#mes"
SEL_STATUS = "select#status"
SEL_QUERY_BTN = 'button:has-text("Consultar")'
SEL_HISTORICO_TAB = 'text=Histórico'
SEL_TABLE_ROWS = "table tbody tr"

_MONTHS_ES = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}


# ─── PUBLIC API ─────────────────────────────────────────────────────────

def scrape_programacion() -> pd.DataFrame:
    """
    Scrape tab Programación — cruceros del mes actual.
    No tiene datos de pasajeros (se usa para status diario).
    """
    return asyncio.run(_scrape_programacion_async())


def scrape_historico_month(year: int, month: int) -> pd.DataFrame:
    """
    Scrape tab Histórico para un mes/año específico.
    Incluye pasajeros (con rezago semanal para semana en curso).
    """
    return asyncio.run(_scrape_historico_async(year, month))


def scrape_historico_range(
    date_from: date,
    date_to: Optional[date] = None,
) -> pd.DataFrame:
    """
    Scrape Histórico para un rango de fechas iterando mes a mes.
    Incluye delay entre requests para no saturar el servidor.
    """
    if date_to is None:
        date_to = date.today()
    return asyncio.run(_scrape_range_async(date_from, date_to))


# ─── ASYNC IMPLEMENTATIONS ──────────────────────────────────────────────

async def _scrape_programacion_async() -> pd.DataFrame:
    """Scrape la tab Programación del mes actual."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(APIQROO_URL, wait_until="networkidle", timeout=30000)
            await page.wait_for_selector(SEL_QUERY_BTN, timeout=10000)
            await page.click(SEL_QUERY_BTN)
            await page.wait_for_selector(SEL_TABLE_ROWS, timeout=15000)
            df = await _parse_table(page, tab="programacion")
            logger.info(f"scrape_programacion: {len(df)} registros")
            return df
        finally:
            await browser.close()


async def _scrape_historico_async(year: int, month: int) -> pd.DataFrame:
    """Scrape un mes del Histórico."""
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
    """Itera mes a mes y agrega todos los registros."""
    all_dfs = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(APIQROO_URL, wait_until="networkidle", timeout=30000)

            # Generar lista de (año, mes) a scrapear
            months = _generate_month_list(date_from, date_to)
            total = len(months)

            for i, (year, month) in enumerate(months, 1):
                logger.info(f"  [{i}/{total}] Scrapeando {year}-{month:02d}...")
                try:
                    df = await _scrape_historico_page(page, year, month)
                    if not df.empty:
                        all_dfs.append(df)
                    await asyncio.sleep(REQUEST_DELAY_SECONDS)
                except Exception as e:
                    logger.warning(f"  Error en {year}-{month:02d}: {e} — saltando")
                    continue

        finally:
            await browser.close()

    if not all_dfs:
        return pd.DataFrame()

    result = pd.concat(all_dfs, ignore_index=True)
    # Deduplicar (mismo registro puede aparecer en dos meses consecutivos)
    if all(c in result.columns for c in ["fecha", "puerto", "crucero"]):
        result = result.drop_duplicates(subset=["fecha", "puerto", "crucero"])

    logger.info(f"scrape_historico_range: {len(result)} registros totales")
    return result


async def _scrape_historico_page(page: Page, year: int, month: int) -> pd.DataFrame:
    """Navega al tab Histórico, selecciona año/mes y extrae la tabla."""
    try:
        # Click en tab Histórico
        await page.click(SEL_HISTORICO_TAB)
        await page.wait_for_selector(SEL_YEAR, timeout=10000)

        # Seleccionar año
        await page.select_option(SEL_YEAR, str(year))
        await asyncio.sleep(0.3)

        # Seleccionar mes (valor es el número del mes como string)
        await page.select_option(SEL_MONTH, str(month))
        await asyncio.sleep(0.3)

        # Click Consultar
        await page.click(SEL_QUERY_BTN)
        await page.wait_for_selector(SEL_TABLE_ROWS, timeout=15000)
        await asyncio.sleep(0.5)

        df = await _parse_table(page, tab="historico")
        return df

    except Exception as e:
        logger.error(f"_scrape_historico_page({year}-{month:02d}): {e}")
        return pd.DataFrame()


async def _parse_table(page: Page, tab: str) -> pd.DataFrame:
    """
    Extrae los datos de la tabla HTML de APIQROO.

    La tabla tiene filas de fecha (con colspan) que agrupan las filas de barcos.
    Formato columnas histÓrico: fecha_dia | puerto | bandera | crucero | fecha | eta | etd | status | pasajeros
    Formato columnas programación: fecha_dia | puerto | bandera | crucero | fecha | eta | etd | status
    """
    rows = []
    current_date_str = ""
    current_day_str = ""

    tr_elements = await page.query_selector_all(SEL_TABLE_ROWS)

    for tr in tr_elements:
        cells = await tr.query_selector_all("td")
        if not cells:
            continue

        # Fila de fecha agrupadora (tiene colspan)
        first_cell = cells[0]
        colspan = await first_cell.get_attribute("colspan")
        if colspan:
            header_text = (await first_cell.inner_text()).strip()
            # Formato: "Thursday, 01 de october de 2015"
            if "," in header_text:
                parts = header_text.split(",")
                current_day_str = parts[0].strip()
                date_part = parts[1].strip() if len(parts) > 1 else ""
                current_date_str = _parse_header_date(date_part)
            continue

        # Fila de barco normal
        cell_texts = []
        for cell in cells:
            text = (await cell.inner_text()).strip()
            cell_texts.append(text)

        if len(cell_texts) < 7:
            continue

        row = _build_row(cell_texts, current_day_str, current_date_str, tab)
        if row:
            rows.append(row)

    if not rows:
        return pd.DataFrame()

    if tab == "historico":
        cols = ["fecha_dia", "puerto", "bandera", "crucero", "fecha", "eta", "etd", "status", "pasajeros"]
    else:
        cols = ["fecha_dia", "puerto", "bandera", "crucero", "fecha", "eta", "etd", "status"]

    # Alinear columnas con datos disponibles
    df_rows = []
    for row in rows:
        if len(row) == len(cols):
            df_rows.append(dict(zip(cols, row)))
        elif len(row) == len(cols) - 1 and tab == "historico":
            # Sin pasajeros en fila
            row.append("0")
            df_rows.append(dict(zip(cols, row)))

    return pd.DataFrame(df_rows)


def _build_row(
    cells: list[str],
    day_str: str,
    date_str: str,
    tab: str,
) -> list[str] | None:
    """Construye una fila normalizada a partir de las celdas."""
    if len(cells) < 5:
        return None

    fecha_dia = f"{day_str}, {date_str}" if day_str and date_str else date_str

    # Determinar status por imagen/clase o texto
    # En la tabla de APIQROO el status puede estar como texto o como imagen
    # Las celdas típicas: [puerto, bandera, crucero, fecha, eta, etd, [status_img], [pasajeros]]
    if len(cells) >= 7:
        puerto = cells[0]
        bandera = cells[1]
        crucero = cells[2]
        fecha = cells[3]
        eta = cells[4]
        etd = cells[5]
        status_raw = cells[6] if len(cells) > 6 else ""
        pasajeros = cells[7] if len(cells) > 7 else "0"
    else:
        return None

    # Normalizar status
    status = _normalize_status(status_raw)

    if tab == "historico":
        return [fecha_dia, puerto, bandera, crucero, fecha, eta, etd, status, pasajeros]
    else:
        return [fecha_dia, puerto, bandera, crucero, fecha, eta, etd, status]


def _normalize_status(raw: str) -> str:
    """Mapea texto de status al valor canónico."""
    mapping = {
        "circle_green": "Arribado",
        "circle_yellow": "Programado",
        "circle_red": "Cancelado",
        "green": "Arribado",
        "yellow": "Programado",
        "red": "Cancelado",
        "arribado": "Arribado",
        "programado": "Programado",
        "cancelado": "Cancelado",
    }
    return mapping.get(raw.lower().strip(), raw.strip().capitalize() or "Programado")


def _parse_header_date(date_part: str) -> str:
    """
    Parsea '01 de october de 2015' → '1/10/2015'
    o '15 de abril de 2026' → '15/4/2026'
    """
    # Limpiar
    date_part = date_part.strip()
    # Formato: "DD de MES de YYYY"
    parts = date_part.lower().split()
    if len(parts) < 5:
        return date_part

    try:
        day = int(parts[0])
        month_str = parts[2]
        year = int(parts[4])
        month = _MONTHS_ES.get(month_str, 0)
        if month == 0:
            return date_part
        return f"{day}/{month}/{year}"
    except (ValueError, IndexError):
        return date_part


def _generate_month_list(date_from: date, date_to: date) -> list[tuple[int, int]]:
    """Genera lista de (año, mes) entre dos fechas."""
    months = []
    current = date(date_from.year, date_from.month, 1)
    end = date(date_to.year, date_to.month, 1)

    while current <= end:
        months.append((current.year, current.month))
        # Avanzar al siguiente mes
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    return months
