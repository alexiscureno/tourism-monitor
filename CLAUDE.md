# tourism-monitor Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-04-17

## Active Technologies

- Python 3.11+ (001-cruise-monitor-mvp)

## Project Structure

```text
backend/
frontend/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes

- 001-cruise-monitor-mvp: Added Python 3.11+

<!-- MANUAL ADDITIONS START -->
## Domain Mental Models

Before working on any part of this project, load the relevant mental model:

- **Industria de cruceros**: `.claude/mental-models/cruise-industry.yaml`
  → terminología, navieras, estacionalidad, terminales, anomalías históricas

- **Dataset APIQROO**: `.claude/mental-models/apiqroo-data.yaml`
  → estructura del dataset, quirks, estrategia de scraping, update cadence

- **Pipeline de datos**: `.claude/mental-models/data-pipeline.yaml`
  → flujo collect→validate→process→enrich→store→notify, orquestador, hooks

## Critical Rules (from mental models)

- SIEMPRE upsert (ON CONFLICT DO UPDATE) — nunca INSERT plain
- SIEMPRE normalizar `crucero_norm` antes de JOIN con `ships_master`
- EXCLUIR `pasajeros_pendiente=True` de métricas de pasajeros
- EXCLUIR `status='Cancelado'` de métricas de afluencia
- EXCLUIR período COVID (2020-03 a 2021-03) de modelos de forecasting
- Los cruceristas son day visitors — NO correlacionar con ocupación hotelera

## Data Pipeline Hook

Antes de cualquier store a Supabase, correr:
```python
from .claude.hooks.pre_store_validation import validate
validate(df, stage="nombre_de_etapa")
```
<!-- MANUAL ADDITIONS END -->
