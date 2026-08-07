"""
app.py — WeatherSense AI Flask Application Entry Point

Start with:
    python app.py

The app will:
  1. Init SQLite database (weather.db)
  2. Fetch initial weather data for Nagpur (seed)
  3. Start APScheduler (auto-fetches all cities every 15 min)
  4. Serve Flask REST API at http://localhost:5000/api/*
  5. Serve the frontend at http://localhost:5000/
"""
import sys, os
# Ensure imports work from any working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(name)s: %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger('WeatherSenseAI')

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def create_app() -> Flask:
    app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
    CORS(app)   # Allow frontend → API calls on any origin

    # ── Init DB ──────────────────────────────────────────────────────────────
    from database.models import init_db
    init_db()
    logger.info("SQLite database ready: weather.db")

    # ── Register Blueprints ───────────────────────────────────────────────────
    from routes.weather  import weather_bp
    from routes.forecast import forecast_bp
    from routes.ml       import ml_bp

    app.register_blueprint(weather_bp)
    app.register_blueprint(forecast_bp)
    app.register_blueprint(ml_bp)

    # ── Health check ─────────────────────────────────────────────────────────
    @app.route('/api/health')
    def health():
        return jsonify({'status': 'ok', 'message': 'WeatherSense AI backend is running'})

    # ── Serve frontend (index.html + assets) ─────────────────────────────────
    @app.route('/')
    def index():
        return send_from_directory(app.static_folder, 'index.html')

    @app.route('/<path:path>')
    def static_files(path):
        try:
            return send_from_directory(app.static_folder, path)
        except Exception:
            return send_from_directory(app.static_folder, 'index.html')

    return app


if __name__ == '__main__':
    app = create_app()

    # ── Seed initial data ─────────────────────────────────────────────────────
    logger.info("Seeding initial weather data for Nagpur (default city)…")
    try:
        from services.weather_fetcher import fetch_current_weather
        reading = fetch_current_weather('nagpur')
        logger.info(
            f"  ✔ Nagpur: {reading.get('temperature')}°C  "
            f"Humidity:{reading.get('humidity')}%  "
            f"Wind:{reading.get('wind_speed')}km/h"
        )
    except Exception as e:
        logger.warning(f"  Could not seed initial data (no internet?): {e}")

    # ── Start background scheduler ────────────────────────────────────────────
    from services.scheduler import start_scheduler
    start_scheduler()

    # ── Run Flask ─────────────────────────────────────────────────────────────
    logger.info("="*55)
    logger.info("  WeatherSense AI is running!")
    logger.info("  Open: http://localhost:5000")
    logger.info("  API:  http://localhost:5000/api/health")
    logger.info("="*55)
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
