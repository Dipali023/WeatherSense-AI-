"""
routes/ml.py
Flask Blueprint: /api/ml/*
  GET /api/ml/predict?city=nagpur    — Linear Regression temperature predictions
  GET /api/ml/classify?city=nagpur   — Random Forest condition classification
  GET /api/ml/anomalies?city=nagpur  — Z-Score anomaly detection
  GET /api/ml/metrics?city=nagpur    — All ML results combined
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Blueprint, request, jsonify

from ml.trainer   import train_linear_regression, train_random_forest
from ml.predictor import detect_anomalies
from config import CITIES

ml_bp = Blueprint('ml', __name__, url_prefix='/api/ml')


def _city_or_error(req):
    city = req.args.get('city', 'nagpur').lower().strip()
    if city not in CITIES:
        return None, jsonify({'error': f'Unknown city: {city!r}'}), 400
    return city, None, None


@ml_bp.route('/predict')
def predict():
    city = request.args.get('city', 'nagpur').lower().strip()
    if city not in CITIES:
        return jsonify({'error': f'Unknown city: {city!r}'}), 400
    try:
        result = train_linear_regression(city)
        result['city'] = city
        return jsonify(result)
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@ml_bp.route('/classify')
def classify():
    city = request.args.get('city', 'nagpur').lower().strip()
    if city not in CITIES:
        return jsonify({'error': f'Unknown city: {city!r}'}), 400
    try:
        result = train_random_forest(city)
        result['city'] = city
        return jsonify(result)
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@ml_bp.route('/anomalies')
def anomalies():
    city  = request.args.get('city',  'nagpur').lower().strip()
    hours = min(int(request.args.get('hours', 24)), 168)
    if city not in CITIES:
        return jsonify({'error': f'Unknown city: {city!r}'}), 400
    try:
        result = detect_anomalies(city, hours=hours)
        result['city'] = city
        return jsonify(result)
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@ml_bp.route('/metrics')
def metrics():
    city = request.args.get('city', 'nagpur').lower().strip()
    if city not in CITIES:
        return jsonify({'error': f'Unknown city: {city!r}'}), 400
    try:
        return jsonify({
            'city':             city,
            'linear_regression': train_linear_regression(city),
            'random_forest':     train_random_forest(city),
            'anomaly_detection': detect_anomalies(city, hours=24),
        })
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500
