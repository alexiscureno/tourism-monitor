# Tourism Monitor — Real Time

## Quick Reference

**Project:** Tourism Monitor — Cozumel Real Time
**Owner:** Alexis Cureno / Axologic
**Status:** Iniciando — definiendo scope y fuentes de datos
**Path:** `/Users/alexiscureno/Documents/Projects-code/tourism-monitor`
**Vault:** `Axologic-Brain/Axologic/Ideas/tourism-monitor.md`

---

## Concepto

Plataforma de monitoreo en tiempo real de actividad turistica en Cozumel.
Datos de cruceros, ocupacion hotelera, afluencia en zonas turísticas.

## Stack Probable

- **Backend:** Python (FastAPI)
- **Data collection:** Scraping + APIs publicas
- **Dashboard:** Streamlit o Dash (similar a SIIIC)
- **Base de datos:** PostgreSQL o SQLite para MVP
- **Deploy:** Docker (Jetson Orin Nano o VPS)

## Estructura del Proyecto

```
tourism-monitor/
├── src/
│   ├── collectors/     ← scrapers y conectores de APIs (cruceros, vuelos, etc.)
│   ├── processors/     ← limpieza, transformacion, agregacion de datos
│   └── api/            ← FastAPI endpoints
├── dashboards/         ← UI / visualizaciones
├── data/
│   ├── raw/            ← datos crudos
│   └── processed/      ← datos limpios
├── scripts/            ← scripts de utilidad
└── docs/               ← documentacion
```

## Fuentes de Datos a Investigar

- [ ] Puerto de Cozumel — llegada de cruceros (datos publicos SCT)
- [ ] SECTUR / DATATUR — estadisticas de ocupacion hotelera
- [ ] APIs de cruceros (Royal Caribbean, Carnival, etc.)
- [ ] Google Trends — busquedas de turismo Cozumel
- [ ] TripAdvisor / booking scraping
- [ ] Datos de trafico aereo (Flightradar24 API)
- [ ] Redes sociales — menciones y check-ins

## Target Users

- Hoteles y tour operators (B2B)
- Gobierno local (SEDETUR, Municipio Cozumel)
- Uso interno Axologic para demos

## MVP Scope (por definir)

- [ ] 1-2 fuentes de datos confiables
- [ ] Dashboard simple con metricas clave
- [ ] Actualizacion diaria (no necesariamente tiempo real en MVP)

## Conexiones

- Experiencia SIIIC: `/Users/alexiscureno/Documents/SIIIC/SIIIC-SYSTEM`
- DataNest: referencia de app movil con datos de campo
