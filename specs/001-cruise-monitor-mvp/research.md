# Research: Tourism Monitor Cozumel — Cruise Monitor MVP

**Branch**: `001-cruise-monitor-mvp` | **Date**: 2026-04-17

---

## 1. APIQROO — Estrategia de scraping

**Decision**: Playwright async para scraping de datos históricos y programación.

**Rationale**:
- La página usa JavaScript para selects dinámicos (año/mes/status) — requiere browser automation
- El scraper existente (`cruceros-scraper/main.py`) ya funciona y está validado con 10,307 registros
- Se reutiliza el código existente, ajustando el rango de fechas (junio 2025 → presente)
- Para actualizaciones diarias: scrape del tab "Programación" (sin necesidad de selects — carga el mes actual por defecto)
- Para actualizaciones semanales: scrape del tab "Histórico" con año/mes de la semana anterior

**Update cadence confirmada** (observación directa de la interfaz):
- Tab Programación: status del día se actualiza en tiempo real (amarillo → verde al arribar)
- Tab Histórico: pasajeros de la semana anterior disponibles lunes/martes con datos de lun–dom previo

**Alternatives considered**:
- requests + BeautifulSoup: insuficiente, la tabla requiere JS execution
- API directa: no existe API pública de APIQROO

---

## 2. CruiseMapper — Tabla maestra de barcos

**Decision**: Scraping one-shot con Playwright de páginas individuales de barcos. Rate limiting: 2s entre requests.

**Rationale**:
- ~200 barcos únicos en el histórico — scraping único, no periódico
- Cada página de barco (`/ships/{name}-{id}`) contiene: capacidad, naviera, año de construcción, gross tonnage
- No hay API pública
- El mismo browser session de Playwright permite reutilizar cookies/headers para evitar bloqueos

**Data a extraer por barco**:
```
nombre, naviera_operadora, capacidad_double_occupancy, capacidad_max,
año_construccion, gross_tonnage, clase, puerto_base
```

**Matching strategy**: Normalizar nombres (uppercase, quitar prefijos M/S, M/V, etc.) para hacer JOIN con APIQROO

**Alternatives considered**:
- MarineTraffic API: de pago, no justificado para datos estáticos de capacidad
- Wikipedia scraping: incompleto para barcos más recientes

---

## 3. Open-Meteo — Datos climáticos

**Decision**: Open-Meteo Historical Weather API + Forecast API. Gratis, sin API key.

**Rationale**:
- Endpoint: `https://archive-api.open-meteo.com/v1/archive` para histórico
- Coordenadas Cozumel: `latitude=20.5215, longitude=-86.9476`
- Variables relevantes: `temperature_2m_max`, `precipitation_sum`, `windspeed_10m_max`, `weathercode`
- Historial disponible desde 1940 — cubre todo el rango 2015–presente
- Forecast: `https://api.open-meteo.com/v1/forecast` para 7–16 días adelante

**Granularidad**: Diaria (suficiente — los cruceros duran un día entero)

**Alternatives considered**:
- OpenWeatherMap: requiere API key, tiene límites en tier gratuito
- NOAA: más complejo de usar, formato menos amigable

---

## 4. Globe.gl en Streamlit

**Decision**: Embeber Globe.gl vía `st.components.v1.html()` con HTML/JS inline.

**Rationale**:
- Globe.gl es una librería WebGL (Three.js) específicamente diseñada para globos con arcos
- Se embebe como componente HTML en Streamlit pasando datos como JSON
- El flujo: Python prepara datos de arcos (origen_lat, origen_lng, dest_lat, dest_lng, weight) → JSON → HTML template con Globe.gl

**Formato de datos para arcos**:
```json
{
  "arcs": [
    {
      "startLat": 25.7617, "startLng": -80.1918,
      "endLat": 20.5215, "endLng": -86.9476,
      "label": "Miami, FL",
      "count": 847,
      "naviera": "Carnival"
    }
  ]
}
```

**Puertos de origen principales** (a poblar en tabla `origin_ports`):
```
Miami, FL          25.7617, -80.1918
Fort Lauderdale    26.1224, -80.1373
Port Canaveral     28.4158, -80.5983
Tampa, FL          27.9506, -82.4572
Galveston, TX      29.3013, -94.7977
New Orleans, LA    29.9511, -90.0715
Port of Baltimore  39.2904, -76.6122
Southampton, UK    50.9097, -1.4044
Barcelona, ES      41.3851, 2.1734
```

**Mapping barco → puerto origen**: Se construye manualmente para los ~50 barcos más frecuentes basado en conocimiento conocido de itinerarios de navieras.

**Alternatives considered**:
- pydeck globe view: menos impresionante, menos control visual
- Plotly globe: limitado en personalización visual

---

## 5. Forecasting — Modelo SARIMA

**Decision**: SARIMA (Seasonal ARIMA) con estacionalidad mensual (m=12).

**Rationale**:
- El histórico de 10 años muestra fuerte estacionalidad anual — ideal para SARIMA
- `statsmodels.tsa.statespace.SARIMAX` es el estándar en Python para series temporales
- El período COVID (mar 2020 – mar 2021) se excluye del fitting o se imputa con la media del mismo período de años adyacentes
- Input: serie mensual de pasajeros totales (solo Arribados, sin Cancelados ni pendientes)
- Output: 12 meses de pronóstico con intervalos de confianza 80% y 95%

**Parámetros iniciales a probar**: SARIMA(1,1,1)(1,1,1)[12] — estándar para series mensuales con estacionalidad

**Métricas de validación**: MAE, RMSE en últimos 12 meses como hold-out set (excluyendo COVID)

**Alternatives considered**:
- Prophet (Facebook): más fácil de usar pero menos reconocido en entrevistas de DS
- LSTM: overkill para 10 años de datos mensuales, no aporta valor extra
- Exponential Smoothing (Holt-Winters): válido pero menos sofisticado para portfolio

---

## 6. Detección de anomalías

**Decision**: Combinación de IsolationForest (detección automática) + reglas explícitas (COVID, huracanes).

**Rationale**:
- IsolationForest de scikit-learn: detecta outliers en la distribución de pasajeros diarios/mensuales
- Reglas explícitas: marcar período COVID (2020-03 a 2021-03), meses con huracanes (categoría 3+) usando base de datos NOAA historical hurricanes
- Las anomalías se anotan visualmente en la serie de tiempo como marcadores/bandas

**Alternatives considered**:
- Z-score simple: menos robusto para distribuciones no normales
- Isolation Forest solo: no explica el "por qué" de la anomalía

---

## 7. Deployment en Jetson Orin Nano

**Decision**: Docker + docker-compose + Cloudflare Tunnel (`cloudflared`).

**Rationale**:
- Jetson corre Ubuntu 22.04 (JetPack 6) — soporte completo de Docker
- Base image: `python:3.11-slim` con `--platform linux/arm64`
- Todas las dependencias (pandas, statsmodels, streamlit, playwright) tienen wheels ARM64 en PyPI
- `cloudflared` corre como servicio systemd separado, no dentro del container
- GitHub Actions maneja los cron jobs (gratis) — el Jetson solo corre el dashboard

**docker-compose.yml servicios**:
```
streamlit-app   → puerto 8501 interno, expuesto vía Cloudflare Tunnel
```

**Alternatives considered**:
- Railway/Render: ~$5/mes innecesario si ya tienes Jetson
- Bare metal sin Docker: más difícil de mantener y reproducir

---

## 8. Base de datos — Supabase schema

**Decision**: 4 tablas principales en Supabase (PostgreSQL).

**Tablas**:
```sql
cruise_visits     -- registro por visita de crucero
ships_master      -- perfil estático por barco
weather_daily     -- clima diario Cozumel
origin_ports      -- puertos de origen con coordenadas
```

**Rationale**:
- Supabase free tier: 500MB storage, suficiente para ~10k registros históricos + crecimiento
- Acceso desde GitHub Actions (para cron updates) y desde Jetson (para dashboard)
- Row Level Security desactivado — datos públicos, no hay autenticación de usuarios
- Índices en `cruise_visits.fecha` y `cruise_visits.crucero` para queries del dashboard

**Alternatives considered**:
- SQLite: no accesible desde GitHub Actions sin sync adicional
- PostgreSQL en Jetson: punto único de falla, sin backups automáticos

---

## 9. Resolución de nombres de barcos (APIQROO → CruiseMapper)

**Decision**: Normalización de nombres + fuzzy matching con `rapidfuzz`.

**Rationale**:
- APIQROO usa prefijos inconsistentes: "M/S CARNIVAL VALOR", "M.S. CARNIVAL VALOR", "CARNIVAL VALOR"
- CruiseMapper usa nombres limpios: "Carnival Valor"
- Pipeline: strip prefijos → lowercase → fuzzy match con threshold 85%
- Los no-matches (< 85%) se registran para revisión manual

**Alternatives considered**:
- Match exacto: demasiados falsos negativos por variaciones de nombre
- LLM para matching: overkill para ~200 barcos únicos
