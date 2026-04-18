"""
Cleaner — Tourism Monitor Cozumel
Limpieza y normalización del DataFrame crudo de APIQROO.
"""

import re
import logging
from datetime import date

import pandas as pd

logger = logging.getLogger(__name__)

# Prefijos a eliminar del nombre del barco (orden importa: más largo primero)
_SHIP_PREFIXES = [
    r"^M\.S\.\s*",
    r"^M\.V\.\s*",
    r"^M/S\s*",
    r"^M/V\s*",
    r"^MS\s+",
    r"^MV\s+",
    r"^S/S\s*",
    r"^SS\s+",
]
_PREFIX_PATTERN = re.compile("|".join(_SHIP_PREFIXES), re.IGNORECASE)

_DAY_MAP = {
    "monday": "Lunes", "tuesday": "Martes", "wednesday": "Miércoles",
    "thursday": "Jueves", "friday": "Viernes", "saturday": "Sábado",
    "sunday": "Domingo",
    "lunes": "Lunes", "martes": "Martes", "miércoles": "Miércoles",
    "miercoles": "Miércoles", "jueves": "Jueves", "viernes": "Viernes",
    "sábado": "Sábado", "sabado": "Sábado", "domingo": "Domingo",
}


def normalize_ship_name(name: str) -> str:
    """
    Normaliza el nombre de un barco:
    - Quita prefijos M/S, M/V, M.S., M.V., MS, MV, SS, S/S
    - Convierte a mayúsculas
    - Limpia espacios extra

    Ejemplo: "M/V MSC WORLD AMERICA" → "MSC WORLD AMERICA"
    """
    if not name or not isinstance(name, str):
        return ""
    cleaned = _PREFIX_PATTERN.sub("", name.strip())
    return cleaned.strip().upper()


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia y normaliza el DataFrame crudo de APIQROO.

    Transformaciones:
    - Parsea fecha (D/M/YYYY → date)
    - Normaliza crucero_norm (quita prefijos)
    - Parsea pasajeros (string '6,079' → int 6079)
    - Detecta pasajeros_pendiente (Arribado + pasajeros=0)
    - Extrae dia_semana de fecha_dia
    - Estandariza terminal y status

    Returns: DataFrame limpio listo para enriquecimiento o almacenamiento.
    """
    if df.empty:
        return df

    result = df.copy()

    # ── FECHA ────────────────────────────────────────────────
    if "fecha" in result.columns:
        result["fecha"] = pd.to_datetime(
            result["fecha"], format="%d/%m/%Y", errors="coerce"
        ).dt.date
        nulls = result["fecha"].isna().sum()
        if nulls > 0:
            logger.warning(f"clean: {nulls} fechas no parseables — descartadas")
        result = result.dropna(subset=["fecha"])

    # ── DÍA DE LA SEMANA ─────────────────────────────────────
    if "fecha_dia" in result.columns and "fecha" in result.columns:
        result["dia_semana"] = result["fecha_dia"].apply(_extract_day_of_week)
    elif "fecha" in result.columns:
        # Derivar del objeto date
        _day_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        result["dia_semana"] = pd.to_datetime(result["fecha"]).dt.weekday.map(
            lambda i: _day_es[i]
        )

    # ── CRUCERO NORMALIZADO ──────────────────────────────────
    if "crucero" in result.columns:
        result["crucero_norm"] = result["crucero"].apply(normalize_ship_name)

    # ── PASAJEROS ────────────────────────────────────────────
    if "pasajeros" in result.columns:
        result["pasajeros"] = result["pasajeros"].apply(_parse_passengers)

    # ── PASAJEROS PENDIENTE ──────────────────────────────────
    # Arribado + pasajeros=0 → dato no publicado aún (lag semanal APIQROO)
    if "status" in result.columns and "pasajeros" in result.columns:
        result["pasajeros_pendiente"] = (
            (result["status"] == "Arribado") & (result["pasajeros"] == 0)
        )

    # ── TERMINAL: limpiar espacios extra ────────────────────
    if "puerto" in result.columns:
        result = result.rename(columns={"puerto": "terminal"})
    if "terminal" in result.columns:
        result["terminal"] = result["terminal"].str.strip().str.upper()

    # ── STATUS ───────────────────────────────────────────────
    if "status" in result.columns:
        result["status"] = result["status"].astype(str).str.strip().str.capitalize()
        # Map variaciones conocidas
        status_map = {
            "Arribado": "Arribado",
            "Cancelado": "Cancelado",
            "Programado": "Programado",
        }
        result["status"] = result["status"].map(status_map)
        # Filas sin status válido → descartar con warning
        nulls = result["status"].isna().sum()
        if nulls > 0:
            logger.warning(f"clean: {nulls} filas con status inválido/NaN — descartadas")
            result = result.dropna(subset=["status"])

    logger.info(f"clean: {len(result)} registros después de limpieza")
    return result


# ─── HELPERS ────────────────────────────────────────────────────────────

def _parse_passengers(val) -> int:
    """Parsea pasajeros: '6,079' → 6079, None → 0."""
    if pd.isna(val) if not isinstance(val, str) else False:
        return 0
    if isinstance(val, (int, float)):
        return int(val)
    cleaned = str(val).replace(",", "").replace(".", "").strip()
    try:
        return int(cleaned)
    except (ValueError, TypeError):
        return 0


def _extract_day_of_week(fecha_dia: str) -> str:
    """
    Extrae día de semana de strings mixtos como:
    'Thursday, 01 de october de 2015' → 'Jueves'
    'Wednesday, 15 de abril de 2026' → 'Miércoles'
    """
    if not fecha_dia or not isinstance(fecha_dia, str):
        return ""
    day_raw = fecha_dia.split(",")[0].strip().lower()
    return _DAY_MAP.get(day_raw, day_raw.capitalize())
