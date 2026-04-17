# Quickstart: Tourism Monitor Cozumel MVP

**Branch**: `001-cruise-monitor-mvp` | **Date**: 2026-04-17

Guía para levantar el proyecto desde cero en desarrollo local y en producción (Jetson).

---

## Pre-requisitos

- Python 3.11+
- `uv` (package manager — ya usado en proyectos anteriores)
- Docker (para producción en Jetson)
- Cuenta en Supabase (free tier)
- `cloudflared` instalado en Jetson (para producción)

---

## Setup inicial (desarrollo local)

### 1. Clonar y configurar entorno
```bash
cd /Users/alexiscureno/Documents/Projects-code/tourism-monitor
uv sync
uv run playwright install chromium
```

### 2. Variables de entorno
```bash
cp .env.example .env
# Editar .env con:
# SUPABASE_URL=https://xxx.supabase.co
# SUPABASE_KEY=your-anon-key
```

### 3. Crear tablas en Supabase
```bash
# Correr el SQL de migrations/ en el SQL Editor de Supabase
```

### 4. Cargar datos históricos (one-time)
```bash
uv run python scripts/seed_historical.py
# Lee data/raw/cruceros_cozumel_04.csv → inserta en cruise_visits
# ~10,307 registros, tarda ~2-3 minutos
```

### 5. Actualizar gap (junio 2025 → hoy)
```bash
uv run python scripts/update_weekly.py --from 2025-06 --to 2026-04
# Scrape APIQROO histórico para el rango faltante
# ~3,300 registros estimados, tarda ~15-20 minutos
```

### 6. Poblar tabla maestra de barcos (one-time)
```bash
uv run python scripts/scrape_ships_master.py
# Scrape CruiseMapper para ~200 barcos únicos
# Con rate limiting de 2s, tarda ~7-8 minutos
```

### 7. Cargar datos climáticos históricos (one-time)
```bash
uv run python scripts/seed_weather.py --from 2015-10-01 --to today
# Carga Open-Meteo histórico para Cozumel
# ~3,800 días, tarda ~30 segundos (API rápida)
```

### 8. Levantar dashboard
```bash
uv run streamlit run dashboards/app.py
# Abre http://localhost:8501
```

---

## Cron jobs (GitHub Actions)

Los workflows en `.github/workflows/` corren automáticamente:

| Workflow | Schedule | Qué hace |
|---|---|---|
| `daily_update.yml` | Diario 7am CST | Scrape Programación → actualiza status del día |
| `weekly_update.yml` | Lunes 6am CST | Scrape Histórico semana anterior → actualiza pasajeros |

**Requiere** secrets en GitHub:
- `SUPABASE_URL`
- `SUPABASE_KEY`

---

## Deploy en Jetson Orin Nano

### Build y run con Docker
```bash
# En el Jetson:
git clone https://github.com/tu-usuario/tourism-monitor
cd tourism-monitor
cp .env.example .env  # llenar con keys de Supabase

docker build -t tourism-monitor .
docker run -d --restart unless-stopped \
  --env-file .env \
  -p 8501:8501 \
  --name tourism-monitor \
  tourism-monitor
```

### Cloudflare Tunnel (exponer al mundo)
```bash
# Ya configurado una sola vez:
cloudflared tunnel route dns tourism-monitor monitor.axologic.com
cloudflared tunnel run tourism-monitor &
# O como servicio systemd para que arranque automático
```

### Verificar
```bash
# Local:    http://localhost:8501
# Público:  https://monitor.axologic.com
```

---

## Estructura de datos clave

```
data/raw/cruceros_cozumel_04.csv    ← histórico existente (no modificar)
data/processed/                      ← outputs del pipeline (generados)
```

---

## Comandos de desarrollo frecuentes

```bash
# Actualizar manualmente datos de hoy
uv run python scripts/update_daily.py

# Re-scrapear un mes específico del histórico
uv run python scripts/update_weekly.py --from 2026-03 --to 2026-03

# Correr tests
uv run pytest tests/

# Ver logs del container en Jetson
docker logs -f tourism-monitor
```
