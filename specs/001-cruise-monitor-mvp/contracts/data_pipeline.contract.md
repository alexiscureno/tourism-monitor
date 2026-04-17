# Data Pipeline Contract

**Feature**: 001-cruise-monitor-mvp | **Date**: 2026-04-17

Define los contratos de datos entre cada módulo del pipeline.

---

## Collector → Processor

### APIQROO Collector output (DataFrame / CSV)
```
fecha_dia    : str   "Thursday, 01 de october de 2015"
puerto       : str   "TERMINAL SSA MEXICO"
bandera      : str   "- ESTADOS UNIDOS"
crucero      : str   "M/S OASIS OF THE SEAS"
fecha        : str   "1/10/2015"  (formato D/M/YYYY)
eta          : str   "06:20"
etd          : str   "17:45"
status       : str   "Arribado" | "Cancelado" | "Programado"
pasajeros    : str   "6,079"  (con coma como separador de miles)
```

### CruiseMapper Ships Collector output (DataFrame)
```
nombre_raw      : str    "MSC World America"
naviera         : str    "MSC Cruises"
grupo_naviera   : str    "MSC Group"
capacidad_double: int    5240
capacidad_max   : int    6774
año_construccion: int    2025
gross_tonnage   : int    215863
longitud_m      : float  333.0
clase           : str    "MSC World"
cruisemapper_url: str    "https://..."
```

### Open-Meteo Collector output (DataFrame)
```
fecha           : date   2026-04-15
temp_max_c      : float  32.1
temp_min_c      : float  25.3
precipitacion_mm: float  0.0
viento_max_kmh  : float  18.5
weather_code    : int    1
```

---

## Processor → Database

### Cleaner output → `cruise_visits`
```
fecha           : date     (parsed from "fecha" field)
dia_semana      : str      (extracted from "fecha_dia")
terminal        : str      (normalized: strip extra spaces)
bandera         : str      (raw)
crucero         : str      (raw)
crucero_norm    : str      (uppercase, stripped prefixes M/S M/V M.S. M.V.)
eta             : time     (parsed HH:MM)
etd             : time     (parsed HH:MM)
status          : str      "Arribado" | "Cancelado" | "Programado"
pasajeros       : int      (parsed: remove commas, convert to int)
pasajeros_pendiente: bool  (True if status=Arribado AND pasajeros=0)
```

### Enricher output → análisis
```
DataFrame con cruise_visits + ships_master joined:
  ...todos los campos de cruise_visits
  naviera         : str    (from ships_master, nullable)
  grupo_naviera   : str    (from ships_master, nullable)
  capacidad_double: int    (from ships_master, nullable)
  load_factor     : float  (calculado, nullable si sin capacidad)
  ...campos de weather_daily joined by fecha
```

---

## Database → Dashboard

### Query: visitas del día actual
```
INPUT:  fecha = today
OUTPUT: List[cruise_visit] con campos: terminal, crucero_norm, naviera, eta, etd, status, pasajeros
```

### Query: métricas por período
```
INPUT:  fecha_inicio, fecha_fin, naviera=None, terminal=None
OUTPUT: {
  total_visitas: int,
  total_pasajeros: int,
  avg_pasajeros: float,
  tasa_cancelacion: float,
  por_naviera: Dict[str, int],
  por_terminal: Dict[str, int]
}
```

### Query: serie de tiempo mensual
```
INPUT:  año_inicio=2015, año_fin=2026
OUTPUT: DataFrame con columnas: año_mes (YYYY-MM), total_pasajeros, total_visitas, avg_load_factor
```

### Query: datos para globo
```
INPUT:  naviera=None (optional filter)
OUTPUT: List[{
  startLat, startLng,  # coordenadas puerto origen
  endLat, endLng,      # coordenadas Cozumel (fijas)
  label,               # nombre del puerto
  count,               # total visitas históricas desde ese puerto
  naviera              # naviera principal desde ese puerto
}]
```
