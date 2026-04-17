# Data Model: Tourism Monitor Cozumel — Cruise Monitor MVP

**Branch**: `001-cruise-monitor-mvp` | **Date**: 2026-04-17

---

## Entidades principales

### 1. `cruise_visits` — Visitas de cruceros

Registro único de un barco en una terminal en una fecha. Fuente: APIQROO.

| Campo | Tipo | Descripción | Ejemplo |
|---|---|---|---|
| `id` | UUID | PK autogenerado | `uuid` |
| `fecha` | DATE | Fecha de la visita | `2026-04-15` |
| `dia_semana` | TEXT | Día de la semana | `Wednesday` |
| `terminal` | TEXT | Terminal de atraque | `TERMINAL SSA MEXICO` |
| `bandera` | TEXT | País de bandera | `- ESTADOS UNIDOS` |
| `crucero` | TEXT | Nombre del barco (raw APIQROO) | `M/V MSC WORLD AMERICA` |
| `crucero_norm` | TEXT | Nombre normalizado | `MSC WORLD AMERICA` |
| `eta` | TIME | Hora de arribo estimada | `08:30` |
| `etd` | TIME | Hora de zarpe estimada | `19:00` |
| `status` | TEXT | Estado del crucero | `Arribado` |
| `pasajeros` | INTEGER | Pasajeros reportados | `5240` |
| `pasajeros_pendiente` | BOOLEAN | True si pasajeros=0 y status=Arribado | `false` |
| `created_at` | TIMESTAMPTZ | Timestamp de inserción | `2026-04-15T09:00:00Z` |
| `updated_at` | TIMESTAMPTZ | Última actualización | `2026-04-15T09:00:00Z` |

**Índices**: `fecha`, `crucero_norm`, `status`, `terminal`
**Constraint único**: `(fecha, terminal, crucero_norm)` — evita duplicados

**Reglas de negocio**:
- `pasajeros_pendiente = true` cuando `status = 'Arribado'` AND `pasajeros = 0`
- Solo registros con `status = 'Arribado'` y `pasajeros_pendiente = false` entran al cálculo de métricas
- Registros `status = 'Cancelado'` se conservan pero se excluyen de métricas de afluencia

---

### 2. `ships_master` — Tabla maestra de barcos

Perfil estático de cada barco único. Fuente: CruiseMapper (scraping one-shot).

| Campo | Tipo | Descripción | Ejemplo |
|---|---|---|---|
| `id` | UUID | PK autogenerado | `uuid` |
| `nombre` | TEXT | Nombre normalizado (clave de JOIN) | `MSC WORLD AMERICA` |
| `nombre_display` | TEXT | Nombre para mostrar | `MSC World America` |
| `naviera` | TEXT | Empresa operadora | `MSC Cruises` |
| `grupo_naviera` | TEXT | Grupo corporativo | `MSC Group` |
| `capacidad_double` | INTEGER | Capacidad double occupancy | `5240` |
| `capacidad_max` | INTEGER | Capacidad máxima | `6774` |
| `año_construccion` | INTEGER | Año de construcción | `2025` |
| `gross_tonnage` | INTEGER | Tonelaje bruto (GT) | `215863` |
| `clase` | TEXT | Clase del barco | `MSC World` |
| `longitud_m` | FLOAT | Longitud en metros | `333.0` |
| `puerto_base_id` | UUID | FK → `origin_ports.id` | `uuid` |
| `cruisemapper_url` | TEXT | URL de la página fuente | `https://...` |
| `scraped_at` | TIMESTAMPTZ | Fecha del último scraping | `2026-04-17T10:00:00Z` |

**Índices**: `nombre`, `naviera`, `grupo_naviera`

**Reglas de negocio**:
- `capacidad_double` es el denominador para el cálculo de load factor
- Si `capacidad_double IS NULL`, el load factor no se calcula para ese barco

---

### 3. `weather_daily` — Clima diario Cozumel

Datos meteorológicos diarios para Cozumel. Fuente: Open-Meteo.

| Campo | Tipo | Descripción | Ejemplo |
|---|---|---|---|
| `id` | UUID | PK autogenerado | `uuid` |
| `fecha` | DATE | Fecha (única) | `2026-04-15` |
| `temp_max_c` | FLOAT | Temperatura máxima (°C) | `32.1` |
| `temp_min_c` | FLOAT | Temperatura mínima (°C) | `25.3` |
| `precipitacion_mm` | FLOAT | Precipitación total (mm) | `0.0` |
| `viento_max_kmh` | FLOAT | Velocidad máxima del viento (km/h) | `18.5` |
| `weather_code` | INTEGER | Código WMO de condición | `1` |
| `es_huracan` | BOOLEAN | Flag manual: True si huracán afectó área | `false` |

**Índices**: `fecha` (unique)

---

### 4. `origin_ports` — Puertos de origen

Puertos desde donde zarpa cada crucero antes de llegar a Cozumel.

| Campo | Tipo | Descripción | Ejemplo |
|---|---|---|---|
| `id` | UUID | PK autogenerado | `uuid` |
| `nombre` | TEXT | Nombre del puerto | `Port of Miami` |
| `ciudad` | TEXT | Ciudad | `Miami` |
| `estado` | TEXT | Estado/Provincia | `Florida` |
| `pais` | TEXT | País | `United States` |
| `latitud` | FLOAT | Coordenada geográfica | `25.7617` |
| `longitud` | FLOAT | Coordenada geográfica | `-80.1918` |
| `codigo_puerto` | TEXT | Código LOCODE | `USMIA` |

---

## Relaciones

```
cruise_visits.crucero_norm  ──→  ships_master.nombre
ships_master.puerto_base_id ──→  origin_ports.id
cruise_visits.fecha         ──→  weather_daily.fecha
```

---

## Vistas / Métricas calculadas

Estas no se almacenan — se calculan en tiempo de query o en el procesador Python:

### `load_factor` (por visita)
```sql
(cv.pasajeros::float / sm.capacidad_double) * 100
WHERE cv.pasajeros_pendiente = false
  AND sm.capacidad_double IS NOT NULL
  AND sm.capacidad_double > 0
```

### `pasajeros_diarios` (suma por fecha)
```sql
SUM(pasajeros) 
FROM cruise_visits
WHERE status = 'Arribado' AND pasajeros_pendiente = false
GROUP BY fecha
```

### `market_share_naviera` (por período)
```sql
COUNT(*) / SUM(COUNT(*)) OVER () * 100
FROM cruise_visits cv JOIN ships_master sm ON cv.crucero_norm = sm.nombre
WHERE status = 'Arribado'
GROUP BY sm.naviera
```

---

## Estado de migración de datos

| Fuente | Registros | Acción |
|---|---|---|
| `cruceros_cozumel_04.csv` | 10,307 | Seed inicial a `cruise_visits` |
| APIQROO (gap jun25–abr26) | ~3,300 est. | Scraping actualización |
| CruiseMapper ships | ~200 barcos | Scraping one-shot → `ships_master` |
| Open-Meteo histórico | ~3,800 días | Carga via API → `weather_daily` |
| Origin ports | ~15 puertos | Carga manual → `origin_ports` |
