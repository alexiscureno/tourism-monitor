"""
AIS Stream Collector — Tourism Monitor Cozumel
Conecta al WebSocket de aisstream.io y guarda posiciones de barcos en Supabase.

Área cubierta: Puerto de Cozumel + Mar Caribe occidental (18°N–22°N, 88°W–85°W)

Uso:
  uv run python src/collectors/ais_stream.py          # corre indefinidamente
  uv run python src/collectors/ais_stream.py --once   # captura 30 msgs y sale
"""

import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

import websockets
import websockets.asyncio.client as ws_client
import websockets.exceptions
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ─── CONFIGURACIÓN ───────────────────────────────────────────────────────
API_KEY = os.environ.get("AISSTREAM_API_KEY", "")

# Bounding box: Caribe occidental — captura barcos en ruta a/desde Cozumel
COZUMEL_BBOX = [[18.0, -88.5], [22.5, -85.0]]

WS_URL = "wss://stream.aisstream.io/v0/stream"

# Tipos de mensaje que nos interesan
# PositionReport = clase A (barcos grandes como cruceros)
# ShipStaticData = nombre, tipo, dimensiones
FILTER_TYPES = ["PositionReport", "ShipStaticData"]

# Ship types AIS para cruceros: 60-69
CRUISE_SHIP_TYPES = set(range(60, 70))

# ─── COLLECTOR ──────────────────────────────────────────────────────────

async def stream_positions(max_messages: int = 0, store_db: bool = True):
    """
    Conecta al stream AIS y procesa mensajes de posición.

    Args:
        max_messages: Si > 0, para después de N mensajes (para tests).
        store_db: Si True, guarda en Supabase ship_positions.
    """
    if not API_KEY:
        raise ValueError("AISSTREAM_API_KEY no configurada en .env")

    subscription = {
        "APIKey": API_KEY,
        "BoundingBoxes": [COZUMEL_BBOX],
        "FilterMessageTypes": FILTER_TYPES,
    }

    count = 0
    retry_delay = 5

    while True:
        try:
            logger.info(f"Conectando a {WS_URL}...")
            async with ws_client.connect(WS_URL, ping_interval=30) as ws:
                await ws.send(json.dumps(subscription))
                logger.info("✅ Conectado al stream AIS — área Caribe occidental")
                retry_delay = 5  # reset on success

                async for raw_msg in ws:
                    try:
                        msg = json.loads(raw_msg)
                        record = _parse_message(msg)
                        if record:
                            _log_vessel(record)
                            if store_db:
                                await _upsert_position(record)
                            count += 1
                            if max_messages > 0 and count >= max_messages:
                                return
                    except Exception as e:
                        logger.warning(f"Error procesando mensaje: {e}")
                        continue

        except websockets.exceptions.InvalidStatus as e:
            if "429" in str(e):
                logger.warning(f"Rate limited (429). Esperando {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 120)
                continue
            else:
                logger.error(f"Conexión rechazada: {e}")
                await asyncio.sleep(retry_delay)
        except Exception as e:
            logger.error(f"Conexión perdida: {e}. Reconectando en {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)


# ─── PARSERS ────────────────────────────────────────────────────────────

def _parse_message(msg: dict) -> dict | None:
    """Extrae los campos relevantes de un mensaje AIS."""
    msg_type = msg.get("MessageType")
    meta = msg.get("MetaData", {})
    message = msg.get("Message", {})

    mmsi = meta.get("MMSI")
    if not mmsi:
        return None

    ship_name = meta.get("ShipName", "").strip()
    lat = meta.get("latitude")
    lon = meta.get("longitude")
    time_utc = meta.get("time_utc") or datetime.now(timezone.utc).isoformat()

    if msg_type == "PositionReport":
        pos = message.get("PositionReport", {})
        return {
            "mmsi": mmsi,
            "ship_name": ship_name,
            "lat": lat,
            "lon": lon,
            "sog": pos.get("Sog"),       # Speed over ground (knots)
            "cog": pos.get("Cog"),       # Course over ground
            "heading": pos.get("TrueHeading"),
            "nav_status": pos.get("NavigationalStatus"),
            "timestamp": time_utc,
            "msg_type": "position",
        }

    elif msg_type == "ShipStaticData":
        static = message.get("ShipStaticData", {})
        ship_type = static.get("Type", 0)
        return {
            "mmsi": mmsi,
            "ship_name": ship_name or static.get("Name", "").strip(),
            "lat": lat,
            "lon": lon,
            "sog": None,
            "cog": None,
            "heading": None,
            "nav_status": None,
            "ship_type": ship_type,
            "destination": static.get("Destination", "").strip(),
            "callsign": static.get("CallSign", "").strip(),
            "timestamp": time_utc,
            "msg_type": "static",
        }

    return None


def _log_vessel(record: dict):
    name = record.get("ship_name", "?")
    lat = record.get("lat", 0) or 0
    lon = record.get("lon", 0) or 0
    sog = record.get("sog", 0) or 0
    dest = record.get("destination", "")
    dest_str = f" → {dest}" if dest else ""
    logger.info(
        f"  {name:<35} Lat={lat:.3f} Lon={lon:.3f} "
        f"SOG={sog:.1f}kn{dest_str}"
    )


async def _upsert_position(record: dict):
    """Guarda/actualiza posición en Supabase ship_positions."""
    from src.db.client import get_client
    client = get_client()

    row = {
        "mmsi": str(record["mmsi"]),
        "ship_name": record.get("ship_name", ""),
        "lat": record.get("lat"),
        "lon": record.get("lon"),
        "sog": record.get("sog"),
        "cog": record.get("cog"),
        "heading": record.get("heading"),
        "nav_status": record.get("nav_status"),
        "destination": record.get("destination", ""),
        "updated_at": record.get("timestamp"),
    }
    # Quitar Nones
    row = {k: v for k, v in row.items() if v is not None}

    client.table("ship_positions").upsert(row, on_conflict="mmsi").execute()


# ─── ENTRY POINT ─────────────────────────────────────────────────────────

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    once = "--once" in sys.argv
    no_db = "--no-db" in sys.argv

    if once:
        logger.info("Modo test: captura 20 mensajes y sale")
        asyncio.run(stream_positions(max_messages=20, store_db=not no_db))
    else:
        # Graceful shutdown con Ctrl+C
        loop = asyncio.new_event_loop()

        def _shutdown():
            logger.info("Cerrando...")
            loop.stop()

        loop.add_signal_handler(signal.SIGINT, _shutdown)
        loop.add_signal_handler(signal.SIGTERM, _shutdown)

        try:
            loop.run_until_complete(stream_positions(store_db=not no_db))
        finally:
            loop.close()


if __name__ == "__main__":
    main()
