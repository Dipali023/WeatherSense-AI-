"""
wsgi.py — Production entry point for gunicorn on Render.com

gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120

This module:
  1. Creates the Flask app
  2. Seeds initial weather data for Nagpur
  3. Starts APScheduler (auto-fetches all cities every 15 min)
"""
import sys, os, logging

# Ensure backend/ is on sys.path so all imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(name)s: %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger('WeatherSenseAI')

# ── Create Flask app ──────────────────────────────────────────────────────────
from app import create_app
app = create_app()

# ── Seed initial data ─────────────────────────────────────────────────────────
logger.info("Seeding initial weather data for Nagpur...")
try:
    from services.weather_fetcher import fetch_current_weather
    reading = fetch_current_weather('nagpur')
    logger.info(
        f"  ✔ Nagpur: {reading.get('temperature')}°C  "
        f"Humidity:{reading.get('humidity')}%  "
        f"Wind:{reading.get('wind_speed')}km/h"
    )
except Exception as e:
    logger.warning(f"  Could not seed initial data: {e}")

# ── Start background scheduler ────────────────────────────────────────────────
from services.scheduler import start_scheduler
start_scheduler()

logger.info("=" * 55)
logger.info("  WeatherSense AI is running on Render!")
logger.info("  API: /api/health")
logger.info("=" * 55)
