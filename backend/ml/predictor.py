"""
ml/predictor.py
Statistical anomaly detection using scipy Z-Score on real DB data.
Flags readings where |z| > 2.5 standard deviations from mean.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import numpy as np
from datetime import datetime, timedelta
try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    stats = None
    SCIPY_AVAILABLE = False

from database.models import WeatherReading, SessionLocal

logger = logging.getLogger(__name__)

ZSCORE_THRESHOLD = 2.5


def detect_anomalies(city: str, hours: int = 24) -> dict:
    """
    Loads recent readings from DB, computes Z-Score on temperature + humidity.
    Returns a list of flagged anomalous readings with their z-scores.
    """
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        rows   = (
            db.query(WeatherReading)
            .filter(WeatherReading.city == city)
            .filter(WeatherReading.timestamp >= cutoff)
            .order_by(WeatherReading.timestamp.asc())
            .all()
        )
    finally:
        db.close()

    if len(rows) < 5:
        return {
            'status':    'insufficient_data',
            'message':   f'Need ≥5 readings, currently have {len(rows)}.',
            'anomalies': [],
            'n_readings': len(rows),
        }

    temps  = np.array([r.temperature or 0 for r in rows], dtype=float)
    humids = np.array([r.humidity    or 0 for r in rows], dtype=float)

    temp_z  = np.abs(stats.zscore(temps))
    humid_z = np.abs(stats.zscore(humids))

    anomalies = []
    for i, row in enumerate(rows):
        flags = []
        if temp_z[i]  > ZSCORE_THRESHOLD:
            flags.append({
                'metric':  'temperature',
                'value':   round(float(temps[i]),  2),
                'z_score': round(float(temp_z[i]), 2),
            })
        if humid_z[i] > ZSCORE_THRESHOLD:
            flags.append({
                'metric':  'humidity',
                'value':   round(float(humids[i]),  2),
                'z_score': round(float(humid_z[i]), 2),
            })
        if flags:
            anomalies.append({
                'id':        row.id,
                'timestamp': row.timestamp.isoformat() if row.timestamp else None,
                'flags':     flags,
            })

    return {
        'status':            'ok',
        'method':            'Z-Score (scipy.stats.zscore)',
        'threshold':         ZSCORE_THRESHOLD,
        'readings_analyzed': len(rows),
        'anomalies_found':   len(anomalies),
        'anomalies':         anomalies,
        'stats': {
            'temp_mean':  round(float(temps.mean()),  2),
            'temp_std':   round(float(temps.std()),   2),
            'humid_mean': round(float(humids.mean()), 2),
            'humid_std':  round(float(humids.std()),  2),
        },
    }
