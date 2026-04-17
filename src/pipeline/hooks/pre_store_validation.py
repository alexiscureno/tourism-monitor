"""
Pre-store validation hook.
Valida un DataFrame antes de insertar en Supabase.
Levanta ValueError en errores críticos, imprime warnings en no-críticos.
"""

import pandas as pd
from datetime import date, datetime
import sys
import json


VALID_STATUSES = {"Arribado", "Cancelado", "Programado"}
VALID_TERMINALS = {
    "TERMINAL SSA MEXICO",
    "TERMINAL PUERTA MAYA",
    "TERMINAL PUNTA LANGOSTA",
    "FONDEO COZUMEL",
}
DATA_START = date(2015, 10, 1)
MAX_LOAD_FACTOR_WARNING = 130.0


def validate(df: pd.DataFrame, stage: str = "pre_store") -> dict:
    """
    Valida un DataFrame del pipeline.

    Returns:
        dict con keys: errors (list), warnings (list), passed (bool)
    """
    errors = []
    warnings = []
    today = date.today()

    # ── ERRORES CRÍTICOS ────────────────────────────────────────────────

    # Fechas futuras con pasajeros reportados
    if "fecha" in df.columns and "pasajeros" in df.columns:
        future_with_pax = df[
            (df["fecha"] > today) & (df["pasajeros"] > 0)
        ]
        if len(future_with_pax) > 0:
            errors.append(
                f"FECHA_FUTURA_CON_PASAJEROS: {len(future_with_pax)} registros "
                f"con fecha futura y pasajeros > 0"
            )

    # Pasajeros negativos
    if "pasajeros" in df.columns:
        negative = df[df["pasajeros"] < 0]
        if len(negative) > 0:
            errors.append(
                f"PASAJEROS_NEGATIVOS: {len(negative)} registros con pasajeros < 0"
            )

    # Status inválidos
    if "status" in df.columns:
        invalid_status = df[~df["status"].isin(VALID_STATUSES)]
        if len(invalid_status) > 0:
            invalid_vals = invalid_status["status"].unique().tolist()
            errors.append(
                f"STATUS_INVALIDO: valores no reconocidos: {invalid_vals}"
            )

    # Fechas fuera de rango válido
    if "fecha" in df.columns:
        too_old = df[df["fecha"] < DATA_START]
        if len(too_old) > 0:
            errors.append(
                f"FECHA_FUERA_RANGO: {len(too_old)} registros antes de {DATA_START}"
            )

    # ── WARNINGS ────────────────────────────────────────────────────────

    # Terminales no reconocidas
    if "terminal" in df.columns:
        unknown_terminals = df[~df["terminal"].isin(VALID_TERMINALS)]
        if len(unknown_terminals) > 0:
            vals = unknown_terminals["terminal"].unique().tolist()
            warnings.append(
                f"TERMINAL_DESCONOCIDA: {vals} — verificar si es nueva terminal"
            )

    # Load factor sospechoso
    if "load_factor" in df.columns:
        high_lf = df[df["load_factor"] > MAX_LOAD_FACTOR_WARNING]
        if len(high_lf) > 0:
            warnings.append(
                f"LOAD_FACTOR_ALTO: {len(high_lf)} registros con load_factor > "
                f"{MAX_LOAD_FACTOR_WARNING}% — verificar capacidad en ships_master"
            )

    # Registros sin nombre de barco
    if "crucero_norm" in df.columns:
        no_name = df[df["crucero_norm"].isna() | (df["crucero_norm"] == "")]
        if len(no_name) > 0:
            warnings.append(
                f"BARCO_SIN_NOMBRE: {len(no_name)} registros sin crucero_norm"
            )

    result = {
        "stage": stage,
        "timestamp": datetime.now().isoformat(),
        "total_records": len(df),
        "errors": errors,
        "warnings": warnings,
        "passed": len(errors) == 0,
    }

    # Print summary
    status_icon = "✅" if result["passed"] else "❌"
    print(f"\n{status_icon} Pipeline Validation [{stage}]")
    print(f"   Records: {len(df)}")

    for w in warnings:
        print(f"   ⚠️  {w}")

    for e in errors:
        print(f"   ❌ {e}", file=sys.stderr)

    if not result["passed"]:
        raise ValueError(
            f"Pipeline validation failed at stage '{stage}' with "
            f"{len(errors)} error(s): {errors}"
        )

    return result
