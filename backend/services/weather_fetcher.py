"""
services/weather_fetcher.py
Fetches real weather data from Open-Meteo API and persists to SQLite.
No API key required — Open-Meteo is 100% free and open.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
import requests
from datetime import datetime, timezone

from config import OPEN_METEO_BASE, CITIES
from database.models import WeatherReading, ForecastCache, SessionLocal

logger = logging.getLogger(__name__)

# ─── Open-Meteo parameter strings ────────────────────────────────────────────
CURRENT_PARAMS = (
    'temperature_2m,relative_humidity_2m,apparent_temperature,'
    'precipitation,weather_code,surface_pressure,wind_speed_10m,'
    'wind_direction_10m,uv_index'
)

FORECAST_PARAMS = (
    'temperature_2m_max,temperature_2m_min,precipitation_sum,'
    'weather_code,wind_speed_10m_max,uv_index_max,'
    'sunrise,sunset,precipitation_probability_max'
)


def fetch_current_weather(city_key: str) -> dict:
    """
    Call Open-Meteo /forecast for current conditions, store in DB, return dict.
    If Open-Meteo fails (e.g. rate limit), fallback to latest stored DB reading.
    """
    city = CITIES.get(city_key)
    if not city:
        raise ValueError(f"Unknown city key: {city_key!r}")

    try:
        resp = requests.get(
            f"{OPEN_METEO_BASE}/forecast",
            params={
                'latitude':  city['lat'],
                'longitude': city['lon'],
                'current':   CURRENT_PARAMS,
                'timezone':  'Asia/Kolkata',
            },
            timeout=10,
        )
        resp.raise_for_status()
        curr = resp.json().get('current', {})

        reading = WeatherReading(
            city          = city_key,
            timestamp     = datetime.now(timezone.utc).replace(tzinfo=None),
            temperature   = curr.get('temperature_2m'),
            humidity      = curr.get('relative_humidity_2m'),
            pressure      = curr.get('surface_pressure'),
            wind_speed    = curr.get('wind_speed_10m'),
            wind_direction= curr.get('wind_direction_10m'),
            rain          = curr.get('precipitation', 0.0),
            uv_index      = curr.get('uv_index', 0.0),
            weather_code  = curr.get('weather_code'),
            apparent_temp = curr.get('apparent_temperature'),
            source        = 'open_meteo',
        )

        db = SessionLocal()
        try:
            db.add(reading)
            db.commit()
            db.refresh(reading)
            result = reading.to_dict()
        finally:
            db.close()

        logger.info(
            f"[{city_key}] Fetched: {reading.temperature}°C  "
            f"Humidity:{reading.humidity}%  Wind:{reading.wind_speed}km/h"
        )
        return result

    except Exception as exc:
        logger.warning(f"[{city_key}] Open-Meteo fetch failed ({exc}), serving latest DB reading…")
        db = SessionLocal()
        try:
            latest = (
                db.query(WeatherReading)
                .filter_by(city=city_key)
                .order_by(WeatherReading.timestamp.desc())
                .first()
            )
            if latest:
                return latest.to_dict()
        finally:
            db.close()
        raise exc


def fetch_weather_by_coords(lat: float, lon: float) -> dict:
    """Fetch current weather by GPS coordinates for auto-detection."""
    resp = requests.get(
        f"{OPEN_METEO_BASE}/forecast",
        params={
            'latitude':  lat,
            'longitude': lon,
            'current':   CURRENT_PARAMS,
            'timezone':  'auto',
        },
        timeout=10,
    )
    resp.raise_for_status()
    curr = resp.json().get('current', {})

    reading = WeatherReading(
        city          = f"gps_{round(lat,2)}_{round(lon,2)}",
        timestamp     = datetime.now(timezone.utc).replace(tzinfo=None),
        temperature   = curr.get('temperature_2m'),
        humidity      = curr.get('relative_humidity_2m'),
        pressure      = curr.get('surface_pressure'),
        wind_speed    = curr.get('wind_speed_10m'),
        wind_direction= curr.get('wind_direction_10m'),
        rain          = curr.get('precipitation', 0.0),
        uv_index      = curr.get('uv_index', 0.0),
        weather_code  = curr.get('weather_code'),
        apparent_temp = curr.get('apparent_temperature'),
        source        = 'gps_geolocation',
    )
    db = SessionLocal()
    try:
        db.add(reading)
        db.commit()
        db.refresh(reading)
        res = reading.to_dict()
        res['city_name'] = f"Location ({round(lat,2)}°, {round(lon,2)}°)"
        return res
    finally:
        db.close()


def fetch_hourly_weather(city_key: str) -> dict:
    """Fetch 24-hour hourly temperature & precipitation forecast."""
    city = CITIES.get(city_key)
    lat, lon = (city['lat'], city['lon']) if city else (21.1458, 79.0882)

    resp = requests.get(
        f"{OPEN_METEO_BASE}/forecast",
        params={
            'latitude':     lat,
            'longitude':    lon,
            'hourly':       'temperature_2m,relative_humidity_2m,precipitation_probability,weather_code',
            'forecast_days': 1,
            'timezone':     'Asia/Kolkata',
        },
        timeout=10,
    )
    resp.raise_for_status()
    hourly = resp.json().get('hourly', {})

    times = [t.split('T')[1][:5] for t in hourly.get('time', [])]
    return {
        'city': city_key,
        'times': times,
        'temperatures': hourly.get('temperature_2m', []),
        'humidity': hourly.get('relative_humidity_2m', []),
        'rain_probability': hourly.get('precipitation_probability', []),
        'weather_codes': hourly.get('weather_code', []),
    }



def fetch_forecast(city_key: str) -> dict:
    """
    Fetch 7-day daily forecast from Open-Meteo, upsert into forecast_cache table.
    Returns structured forecast dict.
    """
    city = CITIES.get(city_key)
    if not city:
        raise ValueError(f"Unknown city key: {city_key!r}")

    resp = requests.get(
        f"{OPEN_METEO_BASE}/forecast",
        params={
            'latitude':     city['lat'],
            'longitude':    city['lon'],
            'daily':        FORECAST_PARAMS,
            'timezone':     'Asia/Kolkata',
            'forecast_days': 7,
        },
        timeout=10,
    )
    resp.raise_for_status()
    daily = resp.json().get('daily', {})

    days = []
    for i, date in enumerate(daily.get('time', [])):
        def _g(key, default=None):
            vals = daily.get(key, [])
            return vals[i] if i < len(vals) else default

        days.append({
            'date':             date,
            'temp_max':         _g('temperature_2m_max'),
            'temp_min':         _g('temperature_2m_min'),
            'precipitation':    _g('precipitation_sum', 0),
            'weather_code':     _g('weather_code', 0),
            'wind_max':         _g('wind_speed_10m_max', 0),
            'uv_max':           _g('uv_index_max', 0),
            'sunrise':          _g('sunrise'),
            'sunset':           _g('sunset'),
            'rain_probability': _g('precipitation_probability_max', 0),
        })

    forecast_data = {
        'city':      city_key,
        'city_name': city['name'],
        'days':      days,
    }

    db = SessionLocal()
    try:
        existing = db.query(ForecastCache).filter_by(city=city_key).first()
        if existing:
            existing.fetched_at   = datetime.utcnow()
            existing.forecast_json = json.dumps(forecast_data)
        else:
            db.add(ForecastCache(
                city          = city_key,
                forecast_json = json.dumps(forecast_data),
            ))
        db.commit()
    finally:
        db.close()

    return forecast_data


def fetch_all_cities():
    """Scheduled job: fetch current weather for every configured city."""
    for city_key in CITIES:
        try:
            fetch_current_weather(city_key)
        except Exception as exc:
            logger.error(f"Scheduler: failed to fetch {city_key}: {exc}")
