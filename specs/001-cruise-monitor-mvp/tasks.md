# Tasks: Tourism Monitor Cozumel — Cruise Monitor MVP

**Input**: Design documents from `/specs/001-cruise-monitor-mvp/`
**Branch**: `001-cruise-monitor-mvp`
**Generated**: 2026-04-17

**Organization**: Tareas agrupadas por User Story para implementación y prueba independiente.
**Tests**: No incluidos (no solicitados en la spec).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Se puede ejecutar en paralelo (archivos diferentes, sin dependencias)
- **[Story]**: User Story correspondiente (US1–US7)

---

## Phase 1: Setup (Infraestructura base)

**Purpose**: Inicializar el proyecto, dependencias y estructura de carpetas.

- [x] T001 Crear `pyproject.toml` con todas las dependencias del plan (playwright, pandas, statsmodels, scikit-learn, plotly, pydeck, streamlit, supabase-py, openmeteo-requests, rapidfuzz, httpx, python-dotenv)
- [x] T002 Crear `.env.example` con variables: `SUPABASE_URL`, `SUPABASE_KEY`, `COZUMEL_LAT`, `COZUMEL_LNG`
- [x] T003 [P] Crear estructura completa de carpetas: `src/collectors/`, `src/processors/`, `src/analysis/`, `src/db/`, `src/pipeline/`, `dashboards/pages/`, `dashboards/components/`, `data/raw/`, `data/processed/`, `data/logs/`, `scripts/`, `tests/unit/`, `tests/integration/`, `tests/fixtures/`, `docker/`
- [x] T004 [P] Crear `docker/Dockerfile` con `python:3.11-slim` para ARM64, instalar playwright chromium y dependencias del proyecto
- [x] T005 [P] Crear `.gitignore` cubriendo: `.env`, `data/raw/*.csv`, `data/processed/`, `data/logs/`, `.venv/`, `__pycache__/`, `.playwright/`
- [x] T006 [P] Copiar `data/raw/cruceros_cozumel_04.csv` desde `/Users/alexiscureno/Documents/Projects-code/cruceros-scraper/cruceros_cozumel_04.csv`

---

## Phase 2: Foundational (Prerrequisitos bloqueantes)

**Purpose**: Base de datos, pipeline core y datos históricos. DEBE completarse antes de cualquier User Story.

**⚠️ CRÍTICO**: Nada de las US puede iniciarse hasta completar esta fase.

### Base de datos

- [x] T007 Crear `src/db/client.py` con cliente Supabase: funciones `upsert_cruise_visits(df)`, `upsert_ships_master(df)`, `upsert_weather_daily(df)`, `query_visits_by_date(date)`, `query_visits_range(date_from, date_to, filters)`
- [x] T008 Crear `src/db/queries.py` con queries reutilizables: `get_today_visits()`, `get_monthly_series(year_from, year_to)`, `get_naviera_market_share(date_from, date_to)`, `get_terminal_distribution()`, `get_ships_without_capacity()`
- [x] T009 Crear script `scripts/create_supabase_tables.sql` con DDL completo para las 4 tablas: `cruise_visits`, `ships_master`, `weather_daily`, `origin_ports` — con constraints, índices y upsert policies según `data-model.md`

### Pipeline core

- [x] T010 Crear `src/processors/cleaner.py` con función `clean(df) -> df`: parsear fecha D/M/YYYY, normalizar `crucero_norm` (quitar prefijos M/S M/V), parsear pasajeros string→int, detectar `pasajeros_pendiente`, extraer `dia_semana`
- [x] T011 Crear `src/processors/enricher.py` con función `enrich(df, ships_df, weather_df) -> df`: JOIN con `ships_master` por `crucero_norm` (fuzzy match con rapidfuzz threshold 85%), JOIN con `weather_daily` por `fecha`, calcular `load_factor`
- [x] T012 [P] Crear `src/processors/load_factor.py` con función `calculate_load_factor(pasajeros, capacidad_double) -> float | None`: retorna None si capacidad_double es None o 0, retorna porcentaje calculado en los demás casos
- [x] T013 Crear `src/pipeline/orchestrator.py` — ya existe la base, completar stubs de fases vacías conectando con módulos reales de `src/collectors/` y `src/processors/`

### Colector APIQROO

- [x] T014 Crear `src/collectors/apiqroo.py` con funciones: `scrape_programacion() -> df` (scrape tab Programación del mes actual), `scrape_historico_month(year, month) -> df` (scrape tab Histórico con selectores de APIQROO), `scrape_historico_range(date_from, date_to) -> df` (itera mes a mes con delay 1s entre requests). Usar selectores de `.claude/mental-models/apiqroo-data.yaml`

### Carga de datos históricos

- [x] T015 Crear `scripts/seed_historical.py`: leer `data/raw/cruceros_cozumel_04.csv`, limpiar con `cleaner.clean()`, validar con hook `pre_store_validation.validate()`, upsert en Supabase tabla `cruise_visits`. Log final: registros insertados/actualizados/errores
- [x] T016 Crear `scripts/update_gap.py`: scrape APIQROO histórico para rango junio 2025 → mes anterior al actual, limpiar, validar, upsert. Este script llena el gap de datos faltantes
- [x] T017 Crear `scripts/seed_weather.py`: llamar Open-Meteo Historical API para coordenadas Cozumel (lat=20.5215, lng=-86.9476), fechas 2015-10-01 → hoy, variables: temp_max, temp_min, precipitation_sum, windspeed_10m_max, weathercode. Upsert en `weather_daily`

**Checkpoint**: Base de datos poblada — `cruise_visits` con 10k+ registros, `weather_daily` con datos históricos. Pipeline core funcional.

---

## Phase 3: US1 — Vista del día actual (P1) 🎯 MVP

**Goal**: Dashboard muestra cruceros de hoy con terminal, status, ETA/ETD y pasajeros.

**Independent Test**: `streamlit run dashboards/app.py` → ver cruceros de hoy correctamente agrupados por terminal con status visual.

- [x] T018 Crear `dashboards/app.py`: entry point Streamlit con navegación multipágina, título "Tourism Monitor · Cozumel", sidebar con logo y navegación a las 5 páginas
- [x] T019 [US1] Crear `dashboards/pages/01_Hoy.py`: layout principal con métricas KPI en la parte superior (total barcos hoy, total pasajeros hoy, terminales activas, cancelaciones), tabla de cruceros del día agrupada por terminal con colores de status (verde/amarillo/rojo)
- [x] T020 [US1] Crear `dashboards/components/kpi_cards.py`: componente reutilizable para mostrar 4 KPIs en fila con `st.metric()` — total barcos, pasajeros, terminales activas, tasa cancelación
- [x] T021 [US1] Agregar lógica de data en `dashboards/pages/01_Hoy.py`: llamar `query_visits_by_date(date.today())`, manejar caso sin datos ("Sin cruceros programados hoy"), distinguir visualmente `pasajeros_pendiente=True` con nota "Pasajeros pendientes de reporte"

**Checkpoint**: US1 completo y testeable — dashboard muestra actividad real del día.

---

## Phase 4: US2 — Explorador histórico con filtros (P2)

**Goal**: Usuario puede filtrar el histórico por año, mes, naviera y terminal. Todas las visualizaciones se actualizan al cambiar filtros.

**Independent Test**: Seleccionar año 2019 + naviera Carnival → gráficas y tabla muestran solo esos datos.

- [ ] T022 [US2] Crear `dashboards/pages/02_historico.py`: sidebar con filtros `st.selectbox` para año (2015–2026), mes, naviera (lista dinámica de navieras), terminal, status. Botón "Limpiar filtros"
- [ ] T023 [US2] Implementar sección de métricas en `dashboards/pages/02_historico.py`: mostrar totales del período filtrado (visitas, pasajeros, promedio/visita, tasa cancelación) usando `query_visits_range()` con los filtros activos
- [ ] T024 [US2] Implementar tabla de datos filtrados en `dashboards/pages/02_historico.py`: `st.dataframe()` con columnas: fecha, crucero, terminal, naviera, pasajeros, load_factor, status. Paginada, ordenable
- [ ] T025 [P] [US2] Implementar gráfica de barras mensual en `dashboards/pages/02_historico.py`: pasajeros por mes para el período filtrado usando plotly bar chart con color por naviera
- [ ] T026 [P] [US2] Implementar gráfica de distribución por terminal en `dashboards/pages/02_historico.py`: pie chart o bar chart horizontal de visitas por terminal en el período filtrado

**Checkpoint**: US2 completo — filtros interactivos funcionan y actualizan todas las visualizaciones.

---

## Phase 5: US3 — Tendencias estacionales y anomalías (P2)

**Goal**: Visualizaciones de serie de tiempo completa (2015–hoy), estacionalidad mensual, market share de navieras, y anomalías anotadas (COVID, huracanes).

**Independent Test**: Ver gráfica de serie de tiempo con caída visible en 2020 anotada como "COVID-19".

- [ ] T027 [US3] Crear `src/analysis/seasonality.py`: función `get_monthly_series(df) -> df` que agrega pasajeros por año-mes, función `get_seasonal_pattern(df) -> df` que calcula promedio por mes del año (ene–dic) para visualizar estacionalidad típica
- [ ] T028 [US3] Crear `src/analysis/anomaly.py`: función `detect_anomalies(series) -> df` usando IsolationForest de scikit-learn en la serie mensual de pasajeros, función `annotate_known_anomalies(df) -> df` que añade columna `anomaly_label` para COVID (2020-03 a 2021-03) y huracanes conocidos
- [ ] T029 [US3] Crear `dashboards/pages/03_analisis.py`: sección "Serie de tiempo completa" con plotly line chart de pasajeros mensuales 2015–hoy, con bandas de anotación para períodos anómalos (COVID en rojo, huracanes en naranja)
- [ ] T030 [P] [US3] Agregar sección "Estacionalidad" en `dashboards/pages/03_analisis.py`: gráfica de caja (box plot) por mes del año mostrando distribución histórica de pasajeros — revela alta/baja temporada visualmente
- [ ] T031 [P] [US3] Agregar sección "Market share navieras" en `dashboards/pages/03_analisis.py`: gráfica de área apilada mostrando evolución del market share de cada naviera por año, pie chart del período completo

**Checkpoint**: US3 completo — tendencias y anomalías visibles, estacionalidad documentada visualmente.

---

## Phase 6: US4 — Load Factor (P3)

**Goal**: Calcular y mostrar porcentaje de ocupación por barco cruzando pasajeros APIQROO con capacidad CruiseMapper.

**Independent Test**: Seleccionar "MSC World America" → ver load factor histórico promedio calculado correctamente.

- [ ] T032 Crear `src/collectors/cruisemapper.py`: función `scrape_ship_specs(ship_name, ship_url) -> dict` que extrae capacidad_double, capacidad_max, año_construccion, gross_tonnage, naviera de una página de barco en CruiseMapper con delay 2s entre requests
- [ ] T033 Crear `scripts/scrape_ships_master.py`: obtener lista de barcos únicos de `cruise_visits` (crucero_norm), buscar URL en CruiseMapper por nombre, scrapear specs de cada uno, upsert en `ships_master`. Log: barcos encontrados/no encontrados
- [ ] T034 [US4] Agregar sección "Load Factor" en `dashboards/pages/02_historico.py` (o nueva subsección): top 10 barcos por visitas con su load factor promedio, histograma de distribución de load factors históricos
- [ ] T035 [P] [US4] Agregar métrica de load factor promedio a los KPIs de `dashboards/pages/01_hoy.py`: "Ocupación estimada hoy" calculada con capacidades de ships_master para los barcos del día

**Checkpoint**: US4 completo — load factor calculado para ≥90% de visitas históricas.

---

## Phase 7: US5 — Forecasting (P3)

**Goal**: Proyección de pasajeros para próximos 30 días combinando programación APIQROO con modelo SARIMA.

**Independent Test**: Ver página de forecast con proyección 30 días, barras de cruceros ya programados y banda de confianza del modelo.

- [ ] T036 Crear `src/analysis/forecast.py`: función `build_sarima_model(series_monthly) -> model` con SARIMA(1,1,1)(1,1,1)[12], excluyendo período COVID del fitting. Función `generate_forecast(model, periods=12) -> df` con columnas: fecha, forecast, ci_lower_80, ci_upper_80, ci_lower_95, ci_upper_95
- [ ] T037 [US5] Crear `dashboards/pages/04_forecast.py`: gráfica principal con serie histórica (gris) + programación conocida de APIQROO (azul) + forecast del modelo (línea punteada) + bandas de confianza (área sombreada)
- [ ] T038 [P] [US5] Agregar comparativa año-a-año en `dashboards/pages/04_forecast.py`: línea del mismo período del año anterior superpuesta para contexto. Métricas: "vs mismo período año anterior +X%"

**Checkpoint**: US5 completo — forecast visible con intervalos de confianza y comparativa histórica.

---

## Phase 8: US6 — Mapa de terminales (P3)

**Goal**: Mapa de Cozumel con 4 terminales marcadas, indicando actividad del día actual.

**Independent Test**: Ver mapa con terminales activas de hoy resaltadas en verde, vacías en gris. Hover muestra barco + pasajeros.

- [ ] T039 Crear `dashboards/components/map_cozumel.py`: función `render_terminal_map(visits_today_df)` usando `pydeck` con `st.pydeck_chart()`. Capa de iconos en cada terminal coloreados por actividad (verde=activa, gris=vacía). Coordenadas fijas de terminales desde `cruise-industry.yaml`
- [ ] T040 [US6] Integrar mapa en `dashboards/pages/01_hoy.py`: mostrar `map_cozumel.render_terminal_map()` debajo de los KPIs. Tooltip con nombre del barco, naviera, pasajeros al hacer hover en terminal activa

**Checkpoint**: US6 completo — mapa visual de Cozumel con actividad del día.

---

## Phase 9: US7 — Globo 3D de rutas de origen (P3)

**Goal**: Globo interactivo con arcos animados desde puertos de origen (Miami, Galveston, etc.) hacia Cozumel, grosor proporcional al volumen histórico.

**Independent Test**: Ver globo rotante con al menos 8 arcos de diferentes puertos hacia Cozumel, arco de Miami el más grueso.

- [ ] T041 Crear `scripts/seed_origin_ports.py`: insertar en tabla `origin_ports` los 12 puertos de origen principales con coordenadas (Miami, Fort Lauderdale, Port Canaveral, Tampa, Galveston, New Orleans, Baltimore, Southampton, Barcelona, etc.) y mapeo barco→puerto_base
- [ ] T042 Crear `dashboards/components/globe_routes.py`: función `render_globe(arcs_data: list[dict])` que genera HTML con Globe.gl (CDN), formatea los datos de arcos como JSON, retorna `st.components.v1.html(html_content, height=600)`. Estilo: fondo oscuro, arcos cyan con glow, rotación automática
- [ ] T043 [US7] Crear `dashboards/pages/05_globo.py`: llamar `query_origin_arcs()` de `src/db/queries.py` para obtener datos agregados (origen→cozumel con count y naviera principal), renderizar con `globe_routes.render_globe()`. Métricas laterales: puertos de origen únicos, rutas activas, naviera dominante por puerto
- [ ] T044 [P] [US7] Agregar filtro de naviera en `dashboards/pages/05_globo.py`: selectbox que filtra los arcos por grupo naviero, actualizando el globo para mostrar solo rutas de esa naviera

**Checkpoint**: US7 completo — globo 3D impactante con rutas de origen hacia Cozumel.

---

## Phase 10: Automatización y Deploy

**Purpose**: GitHub Actions para actualizaciones automáticas, Docker y Cloudflare Tunnel para deploy en Jetson.

- [ ] T045 Crear `.github/workflows/daily_update.yml`: cron `0 13 * * *` (7am CST), steps: checkout → setup python+uv → install deps → install playwright chromium → `uv run python scripts/update_daily.py`. Secrets: SUPABASE_URL, SUPABASE_KEY
- [ ] T046 Crear `.github/workflows/weekly_update.yml`: cron `0 12 * * 1` (6am CST lunes), mismos steps → `uv run python scripts/update_weekly.py`. Incluye scrape de pasajeros semana anterior
- [ ] T047 [P] Crear `scripts/update_daily.py`: wrapper que llama `PipelineOrchestrator().run(WorkflowType.DAILY_UPDATE)` con logging a `data/logs/daily_{date}.log`
- [ ] T048 [P] Crear `scripts/update_weekly.py`: wrapper que llama `PipelineOrchestrator().run(WorkflowType.WEEKLY_UPDATE)` con logging a `data/logs/weekly_{date}.log`
- [ ] T049 Crear `docker-compose.yml`: servicio `streamlit-app` con imagen del Dockerfile, puerto 8501, env_file .env, restart `unless-stopped`
- [ ] T050 Crear `docs/deploy-jetson.md`: guía paso a paso para deploy en Jetson Orin Nano con Docker + Cloudflare Tunnel → monitor.axologic.com

---

## Phase 11: Polish y refinamiento

**Purpose**: Mejoras transversales, consistencia visual, README y documentación.

- [ ] T051 Crear `README.md`: descripción del proyecto, stack, fuentes de datos, instrucciones de setup (referencia a quickstart.md), screenshots del dashboard
- [ ] T052 [P] Unificar tema visual del dashboard: dark theme en todos los plots plotly (`template="plotly_dark"`), paleta de colores consistente (cyan para highlights, igual que el globo), tipografía uniforme
- [ ] T053 [P] Agregar manejo de errores en todas las páginas del dashboard: `try/except` con `st.error()` si Supabase no responde, `st.warning()` si no hay datos para el período seleccionado
- [ ] T054 [P] Agregar `st.cache_data` con TTL apropiado en todas las queries del dashboard: 5 minutos para datos del día, 1 hora para datos históricos, 24 horas para ships_master
- [ ] T055 Validar quickstart.md ejecutando todos los pasos en orden y corrigiendo cualquier discrepancia con el código real
- [ ] T056 [P] Crear `tests/fixtures/sample_data.py` con DataFrames de muestra para testing manual de los procesadores (cleaner, enricher, load_factor)

---

## Dependencies & Execution Order

### Dependencias entre fases

- **Phase 1 (Setup)**: Sin dependencias — iniciar de inmediato
- **Phase 2 (Foundational)**: Depende de Phase 1 — **BLOQUEA** todas las User Stories
- **Phase 3 (US1)**: Depende de Phase 2 — primer entregable funcional (MVP)
- **Phase 4 (US2)**: Depende de Phase 2 (datos históricos disponibles)
- **Phase 5 (US3)**: Depende de Phase 2 + Phase 4 (reutiliza queries del histórico)
- **Phase 6 (US4)**: Depende de Phase 2 (necesita ships_master scrapeado)
- **Phase 7 (US5)**: Depende de Phase 5 (necesita serie temporal completa)
- **Phase 8 (US6)**: Depende de Phase 3 (reutiliza datos del día)
- **Phase 9 (US7)**: Depende de Phase 2 (necesita datos históricos para agregar por origen)
- **Phase 10 (Deploy)**: Depende de Phase 3 (app funcionando)
- **Phase 11 (Polish)**: Depende de todas las US que se quieran incluir

### Dependencias dentro de cada fase

- T007 → T008 (queries requieren client)
- T009 → T007 (client requiere schema creado)
- T010 → T011 (enricher requiere cleaner)
- T014 → T015 (seed requiere scraper)
- T015 → T016 (gap update requiere que el seed inicial esté hecho)

### Oportunidades de paralelismo

Dentro de Phase 1: T003, T004, T005, T006 en paralelo
Dentro de Phase 2: T007+T009 (DB) en paralelo con T010+T011 (processors), luego T014 (scraper)
Fases 4–9 (US2–US7): pueden iniciarse en paralelo después de Phase 2 si hay capacidad

---

## Parallel Example: Phase 2

```bash
# Ejecutar en paralelo:
Task T007: "Crear src/db/client.py con cliente Supabase"
Task T009: "Crear scripts/create_supabase_tables.sql"
Task T010: "Crear src/processors/cleaner.py"
Task T012: "Crear src/processors/load_factor.py"

# Luego secuencial:
Task T011: "Crear src/processors/enricher.py" (depende de T010)
Task T014: "Crear src/collectors/apiqroo.py"
Task T015: "Crear scripts/seed_historical.py" (depende de T007, T010, T014)
```

---

## Implementation Strategy

### MVP (Phase 1 + 2 + 3 únicamente)

1. ✅ Phase 1: Setup (estructura + dependencias)
2. ✅ Phase 2: Foundational (DB + pipeline + datos históricos cargados)
3. ✅ Phase 3: US1 (dashboard con vista del día)
4. **PARAR Y VALIDAR**: Dashboard accesible en localhost:8501 mostrando cruceros de hoy
5. Deploy en Jetson → `monitor.axologic.com` online

**El MVP es funcional y publicable al completar Phase 3.**

### Entrega incremental

```
Phase 1+2+3  → MVP online (cruces del día) ← PUBLICAR
+ Phase 4    → Explorador histórico con filtros
+ Phase 5    → Tendencias + anomalías (análisis profundo)
+ Phase 6    → Load factor (ships_master completo)
+ Phase 7    → Forecasting (modelo SARIMA entrenado)
+ Phase 8    → Mapa de terminales
+ Phase 9    → Globo 3D ← elemento WOW final
+ Phase 10   → Automatización completa 24/7
+ Phase 11   → Polish final para portfolio
```

---

## Resumen

| Fase | Tareas | Propósito |
|---|---|---|
| Phase 1: Setup | T001–T006 (6) | Infraestructura base |
| Phase 2: Foundational | T007–T017 (11) | DB + pipeline + datos |
| Phase 3: US1 (P1) | T018–T021 (4) | **MVP — Vista del día** |
| Phase 4: US2 (P2) | T022–T026 (5) | Explorador histórico |
| Phase 5: US3 (P2) | T027–T031 (5) | Tendencias + anomalías |
| Phase 6: US4 (P3) | T032–T035 (4) | Load factor |
| Phase 7: US5 (P3) | T036–T038 (3) | Forecasting SARIMA |
| Phase 8: US6 (P3) | T039–T040 (2) | Mapa terminales |
| Phase 9: US7 (P3) | T041–T044 (4) | Globo 3D rutas |
| Phase 10: Deploy | T045–T050 (6) | GitHub Actions + Docker |
| Phase 11: Polish | T051–T056 (6) | Portfolio ready |
| **Total** | **56 tareas** | |

**MVP mínimo**: T001–T021 (21 tareas) → Dashboard funcional publicado.
**Portfolio completo**: T001–T056 (56 tareas) → Proyecto completo con todas las visualizaciones.
