"""
routes/weather.py
Flask Blueprint: /api/weather/*
  GET /api/weather/current?city=nagpur  — fetch fresh reading from Open-Meteo + store
  GET /api/weather/history?city=nagpur&hours=24 — recent readings from DB
  GET /api/weather/cities               — list all supported cities
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Blueprint, request, jsonify, Response
from datetime import datetime, timedelta
import csv
import io

from services.weather_fetcher import (
    fetch_current_weather, fetch_weather_by_coords, fetch_hourly_weather
)
from database.models import WeatherReading, SessionLocal
from config import CITIES

weather_bp = Blueprint('weather', __name__, url_prefix='/api/weather')


@weather_bp.route('/current')
def current():
    city = request.args.get('city', 'nagpur').lower().strip()
    if city not in CITIES:
        return jsonify({'error': f'Unknown city: {city!r}. See /api/weather/cities'}), 400
    try:
        data = fetch_current_weather(city)
        data['city_name'] = CITIES[city]['name']
        return jsonify(data)
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@weather_bp.route('/coords')
def coords():
    try:
        lat = float(request.args.get('lat', 21.1458))
        lon = float(request.args.get('lon', 79.0882))
        data = fetch_weather_by_coords(lat, lon)
        return jsonify(data)
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@weather_bp.route('/hourly')
def hourly():
    city = request.args.get('city', 'nagpur').lower().strip()
    try:
        data = fetch_hourly_weather(city)
        return jsonify(data)
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@weather_bp.route('/history')
def history():
    city  = request.args.get('city',  'nagpur').lower().strip()
    hours = min(int(request.args.get('hours', 24)), 168)   # max 7 days

    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        query  = db.query(WeatherReading).filter(WeatherReading.timestamp >= cutoff)
        if city in CITIES:
            query = query.filter(WeatherReading.city == city)
        rows   = query.order_by(WeatherReading.timestamp.asc()).all()

        city_name = CITIES[city]['name'] if city in CITIES else city
        return jsonify({
            'city':      city,
            'city_name': city_name,
            'hours':     hours,
            'count':     len(rows),
            'readings':  [r.to_dict() for r in rows],
        })
    finally:
        db.close()


@weather_bp.route('/export')
def export_csv():
    city = request.args.get('city', 'nagpur').lower().strip()
    db = SessionLocal()
    try:
        query = db.query(WeatherReading)
        if city in CITIES:
            query = query.filter(WeatherReading.city == city)
        rows = query.order_by(WeatherReading.timestamp.desc()).limit(500).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'City', 'Timestamp', 'Temp_C', 'Humidity_Pct', 'Pressure_hPa', 'Wind_Speed_kmh', 'Rain_mm', 'UV_Index', 'Source'])

        for r in rows:
            writer.writerow([r.id, r.city, r.timestamp.isoformat() if r.timestamp else '', r.temperature, r.humidity, r.pressure, r.wind_speed, r.rain, r.uv_index, r.source])

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=weather_export_{city}.csv'}
        )
    finally:
        db.close()


@weather_bp.route('/cities')
def cities():
    return jsonify({'cities': {k: v['name'] for k, v in CITIES.items()}})

