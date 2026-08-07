"""
routes/forecast.py
Flask Blueprint: /api/forecast
  GET /api/forecast?city=nagpur  — 7-day forecast (cached 30 min)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta

from services.weather_fetcher import fetch_forecast
from database.models import ForecastCache, SessionLocal
from config import CITIES, FORECAST_CACHE_MINUTES

forecast_bp = Blueprint('forecast', __name__, url_prefix='/api/forecast')


@forecast_bp.route('', strict_slashes=False)
@forecast_bp.route('/', strict_slashes=False)
def get_forecast():
    city = request.args.get('city', 'nagpur').lower().strip()
    if city not in CITIES:
        return jsonify({'error': f'Unknown city: {city!r}'}), 400

    # Check DB cache before hitting API
    db = SessionLocal()
    try:
        cached = db.query(ForecastCache).filter_by(city=city).first()
        if cached:
            age_sec = (datetime.utcnow() - cached.fetched_at).total_seconds()
            if age_sec < FORECAST_CACHE_MINUTES * 60:
                data = json.loads(cached.forecast_json)
                data['from_cache']        = True
                data['cache_age_minutes'] = round(age_sec / 60, 1)
                return jsonify(data)
    finally:
        db.close()

    try:
        data = fetch_forecast(city)
        data['from_cache'] = False
        return jsonify(data)
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500
