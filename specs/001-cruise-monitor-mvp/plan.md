# Implementation Plan: Tourism Monitor Cozumel — Cruise Monitor MVP

**Branch**: `001-cruise-monitor-mvp` | **Date**: 2026-04-17 | **Spec**: [spec.md](./spec.md)

---

## Summary

Plataforma de monitoreo de cruceros en Cozumel con pipeline completo de data science: ingestión desde APIQROO (histórico 2015–hoy) y CruiseMapper (tabla maestra de barcos), limpieza y enriquecimiento, análisis de tendencias estacionales, cálculo de load factor, detección de anomalías y forecasting. Dashboard interactivo en Streamlit con mapa local de terminales (pydeck), globo 3D de rutas de origen (Globe.gl), y actualizaciones automáticas vía cron. Desplegado en Jetson Orin Nano + Cloudflare Tunnel → `monitor.axologic.com`.

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- Recolección: `playwright`, `httpx`, `beautifulsoup4`
- Procesamiento: `pandas`, `numpy`
- Análisis: `statsmodels` (SARIMA), `scikit-learn` (IsolationForest), `scipy`
- Visualización: `plotly`, `pydeck` (mapa local), `Globe.gl` vía `st.components.v1.html`
- Dashboard: `streamlit`
- Base de datos: `supabase-py` (cliente PostgreSQL gestionado)
- Clima: `openmeteo-requests`
- Scheduling: GitHub Actions (cron jobs)
- Deploy: Docker + Cloudflare Tunnel

**Storage**: Supabase (PostgreSQL) — tablas: `cruise_visits`, `ships_master`, `weather_daily`, `origin_ports`
**Testing**: `pytest` + `pytest-asyncio`
**Target Platform**: ARM64 Linux — Jetson Orin Nano (JetPack/Ubuntu) + Cloudflare Tunnel
**Project Type**: Data pipeline + dashboard web interactivo
**Performance Goals**: Dashboard carga < 5s · Filtros responden < 2s · MAE forecasting < 15%
**Constraints**: Todas las dependencias deben tener wheels ARM64 · Rate limiting en scraping (delays entre requests) · Jetson 8GB RAM
**Scale/Scope**: ~10,307 registros históricos · ~300 nuevos registros/mes · ~200 perfiles de barcos únicos

---

## Constitution Check

*La constitución del proyecto está en template (sin principios definidos aún). Se aplican principios de sentido común:*

| Gate | Status | Notas |
|---|---|---|
| Dependencias con soporte ARM64 | ✅ | playwright, pandas, statsmodels, streamlit — todas soportan ARM64 |
| Scraping ético (rate limiting) | ✅ | Delays configurables, respeta robots.txt |
| Datos personales | ✅ | No hay PII — solo datos de barcos y puertos |
| Secretos en código | ✅ | Variables de entorno para Supabase keys |
| Complejidad justificada | ✅ | Pipeline de datos justifica la arquitectura por módulos |

---

## Project Structure

### Documentation (this feature)

```text
specs/001-cruise-monitor-mvp/
├── plan.md              ← este archivo
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/           ← Phase 1 output
│   ├── cruise_visits.schema.json
│   ├── ships_master.schema.json
│   └── data_pipeline.contract.md
└── tasks.md             ← Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
tourism-monitor/
├── src/
│   ├── collectors/
│   │   ├── apiqroo.py          ← scraper histórico + programación diaria
│   │   ├── cruisemapper.py     ← scraper tabla maestra de barcos
│   │   └── weather.py          ← cliente Open-Meteo API
│   ├── processors/
│   │   ├── cleaner.py          ← limpieza y normalización de datos
│   │   ├── enricher.py         ← joins: visitas + barcos + clima
│   │   └── load_factor.py      ← cálculo de load factor y métricas
│   ├── analysis/
│   │   ├── seasonality.py      ← descomposición estacional (STL)
│   │   ├── anomaly.py          ← detección de anomalías (IsolationForest)
│   │   └── forecast.py         ← modelo SARIMA / forecasting
│   └── db/
│       ├── client.py           ← cliente Supabase
│       └── queries.py          ← queries reutilizables
├── dashboards/
│   ├── app.py                  ← entry point Streamlit
│   ├── pages/
│   │   ├── 01_hoy.py           ← vista del día actual
│   │   ├── 02_historico.py     ← explorador histórico con filtros
│   │   ├── 03_analisis.py      ← tendencias + anomalías + navieras
│   │   ├── 04_forecast.py      ← pronóstico
│   │   └── 05_globo.py         ← globo 3D de rutas de origen
│   └── components/
│       ├── map_cozumel.py      ← mapa pydeck de terminales
│       └── globe_routes.py     ← componente Globe.gl
├── data/
│   ├── raw/
│   │   └── cruceros_cozumel_04.csv   ← datos históricos existentes
│   └── processed/
├── scripts/
│   ├── seed_historical.py      ← carga inicial datos históricos a Supabase
│   ├── update_daily.py         ← actualización diaria (cron)
│   └── update_weekly.py        ← actualización semanal pasajeros (cron)
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── .github/
│   └── workflows/
│       ├── daily_update.yml    ← cron diario ~7am CST
│       └── weekly_update.yml   ← cron lunes ~6am CST
├── docker/
│   └── Dockerfile              ← imagen ARM64
├── pyproject.toml
├── .env.example
└── README.md
```

**Structure Decision**: Single Python project con separación clara por responsabilidad (collectors → processors → analysis → dashboard). No hay backend API separado — el dashboard lee directo de Supabase. Los cron jobs corren en GitHub Actions (gratis, sin servidor extra).

---

## Complexity Tracking

| Decisión | Por qué | Alternativa rechazada |
|---|---|---|
| Globe.gl vía st.components.html | Único path para WebGL en Streamlit | Plotly globe — menos impresionante visualmente |
| GitHub Actions para cron | Gratis, sin servidor adicional | APScheduler en Jetson — agrega complejidad al proceso principal |
| Supabase vs SQLite | Acceso remoto desde GitHub Actions y Jetson, backups automáticos | SQLite — no funciona con cron jobs en Actions |
| SARIMA vs Prophet | SARIMA es estándar académico, mejor para portfolio de DS | Prophet — menos conocido en entrevistas técnicas |
