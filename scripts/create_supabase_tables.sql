-- ============================================================
-- DDL: Tourism Monitor Cozumel
-- Ejecutar en Supabase SQL Editor (una sola vez)
-- ============================================================

-- Habilitar extensión para UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── SHIPS_MASTER ────────────────────────────────────────────
-- Tabla maestra de barcos (scraped de CruiseMapper)
-- Se actualiza trimestralmente de forma manual.

CREATE TABLE IF NOT EXISTS ships_master (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre              TEXT NOT NULL UNIQUE,      -- crucero_norm (normalizado)
    nombre_display      TEXT,                       -- nombre legible para UI
    naviera             TEXT,
    grupo_naviera       TEXT,                       -- "Carnival Corp", "RCL", "MSC", etc.
    capacidad_double    INTEGER,                    -- pasajeros en doble ocupación (denominador load factor)
    capacidad_max       INTEGER,
    anio_construccion   INTEGER,
    gross_tonnage       INTEGER,
    clase               TEXT,
    longitud_m          NUMERIC(6, 1),
    cruisemapper_url    TEXT,
    scraped_at          TIMESTAMPTZ DEFAULT NOW(),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ships_master_nombre ON ships_master(nombre);
CREATE INDEX IF NOT EXISTS idx_ships_master_naviera ON ships_master(grupo_naviera);

-- ─── ORIGIN_PORTS ───────────────────────────────────────────
-- Puertos de origen de las navieras (para globo 3D)

CREATE TABLE IF NOT EXISTS origin_ports (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre      TEXT NOT NULL,
    ciudad      TEXT,
    estado      TEXT,
    pais        TEXT,
    latitud     NUMERIC(9, 6) NOT NULL,
    longitud    NUMERIC(9, 6) NOT NULL,
    codigo_puerto TEXT
);

-- ─── WEATHER_DAILY ──────────────────────────────────────────
-- Datos climáticos diarios de Cozumel (Open-Meteo)

CREATE TABLE IF NOT EXISTS weather_daily (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fecha               DATE NOT NULL UNIQUE,
    temp_max_c          NUMERIC(4, 1),
    temp_min_c          NUMERIC(4, 1),
    precipitacion_mm    NUMERIC(6, 1),
    viento_max_kmh      NUMERIC(5, 1),
    weather_code        INTEGER,
    es_huracan          BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_weather_fecha ON weather_daily(fecha);

-- ─── CRUISE_VISITS ──────────────────────────────────────────
-- Tabla principal: cada fila = un barco en un puerto en una fecha

CREATE TABLE IF NOT EXISTS cruise_visits (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Datos de APIQROO
    fecha               DATE NOT NULL,
    dia_semana          TEXT,
    terminal            TEXT NOT NULL,
    bandera             TEXT,
    crucero             TEXT NOT NULL,              -- nombre original de APIQROO
    crucero_norm        TEXT NOT NULL,              -- normalizado (sin prefijos M/S M/V)
    eta                 TIME,
    etd                 TIME,
    status              TEXT NOT NULL CHECK (status IN ('Arribado', 'Cancelado', 'Programado')),
    pasajeros           INTEGER DEFAULT 0,
    pasajeros_pendiente BOOLEAN DEFAULT FALSE,      -- Arribado + pasajeros=0 → dato aún no publicado

    -- Datos enriquecidos (JOIN con ships_master)
    grupo_naviera       TEXT,
    gross_tonnage       INTEGER,
    capacidad_double    INTEGER,
    load_factor         NUMERIC(5, 2),              -- (pasajeros / capacidad_double) * 100

    -- Metadatos
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),

    -- Constraint único para upsert
    CONSTRAINT uq_cruise_visit UNIQUE (fecha, terminal, crucero_norm)
);

-- Índices para queries frecuentes del dashboard
CREATE INDEX IF NOT EXISTS idx_cv_fecha        ON cruise_visits(fecha);
CREATE INDEX IF NOT EXISTS idx_cv_crucero_norm ON cruise_visits(crucero_norm);
CREATE INDEX IF NOT EXISTS idx_cv_status       ON cruise_visits(status);
CREATE INDEX IF NOT EXISTS idx_cv_terminal     ON cruise_visits(terminal);
CREATE INDEX IF NOT EXISTS idx_cv_naviera      ON cruise_visits(grupo_naviera);
CREATE INDEX IF NOT EXISTS idx_cv_fecha_status ON cruise_visits(fecha, status);

-- ─── QUARANTINE ─────────────────────────────────────────────
-- Registros que fallaron validación del pipeline

CREATE TABLE IF NOT EXISTS cruise_visits_quarantine (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    raw_data        JSONB,
    error_reason    TEXT,
    stage           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─── UPDATED_AT TRIGGER ─────────────────────────────────────

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_cruise_visits_updated_at
    BEFORE UPDATE ON cruise_visits
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER trg_ships_master_updated_at
    BEFORE UPDATE ON ships_master
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ─── RLS (Row Level Security) ───────────────────────────────
-- Dashboard es público (solo lectura). Pipeline usa service role key.

ALTER TABLE cruise_visits         ENABLE ROW LEVEL SECURITY;
ALTER TABLE ships_master          ENABLE ROW LEVEL SECURITY;
ALTER TABLE weather_daily         ENABLE ROW LEVEL SECURITY;
ALTER TABLE origin_ports          ENABLE ROW LEVEL SECURITY;

-- Lectura pública para el dashboard
CREATE POLICY "Public read cruise_visits"
    ON cruise_visits FOR SELECT USING (true);

CREATE POLICY "Public read ships_master"
    ON ships_master FOR SELECT USING (true);

CREATE POLICY "Public read weather_daily"
    ON weather_daily FOR SELECT USING (true);

CREATE POLICY "Public read origin_ports"
    ON origin_ports FOR SELECT USING (true);
