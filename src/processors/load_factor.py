"""
Load factor calculator — Tourism Monitor Cozumel
Calcula el factor de ocupación de un barco de crucero.
"""

from typing import Optional


def calculate_load_factor(
    pasajeros: int,
    capacidad_double: Optional[int],
) -> Optional[float]:
    """
    Calcula el load factor como porcentaje.

    Args:
        pasajeros: número de pasajeros reportados
        capacidad_double: capacidad de doble ocupación del barco

    Returns:
        load_factor en % (puede superar 100 si hay literas extra), o None
        si la capacidad no está disponible.
    """
    if capacidad_double is None or capacidad_double <= 0:
        return None
    if pasajeros < 0:
        return None
    return round((pasajeros / capacidad_double) * 100, 2)
