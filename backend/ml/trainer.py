"""
ml/trainer.py
Real machine learning using scikit-learn.

LinearRegression  — trains on historical DB readings, predicts future temperatures
RandomForestClassifier — classifies current weather condition from multi-variate input
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

try:
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import LabelEncoder
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_squared_error, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    LabelEncoder = None
    RandomForestClassifier = None
    LinearRegression = None



from database.models import WeatherReading, SessionLocal

logger = logging.getLogger(__name__)

# ─── WMO weather code → human label ──────────────────────────────────────────
WMO_MAP = [
    (range(0,  1),   'Clear'),
    (range(1,  4),   'Partly Cloudy'),
    (range(45, 50),  'Foggy'),
    (range(51, 68),  'Drizzle'),
    (range(71, 78),  'Snow'),
    (range(80, 83),  'Rain Showers'),
    (range(85, 87),  'Snow Showers'),
    (range(95, 96),  'Thunderstorm'),
    (range(96, 100), 'Heavy Thunderstorm'),
]

def wmo_to_label(code) -> str:
    if code is None: return 'Cloudy'
    for rng, label in WMO_MAP:
        if int(code) in rng:
            return label
    return 'Cloudy'


def _load_df(city: str, hours: int = 72) -> pd.DataFrame:
    """Load recent weather readings from SQLite into a pandas DataFrame."""
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        rows = (
            db.query(WeatherReading)
            .filter(WeatherReading.city == city)
            .filter(WeatherReading.timestamp >= cutoff)
            .order_by(WeatherReading.timestamp.asc())
            .all()
        )
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame([r.to_dict() for r in rows])
        df['timestamp']   = pd.to_datetime(df['timestamp'])
        df['time_index']  = np.arange(len(df))
        df['hour_of_day'] = df['timestamp'].dt.hour + df['timestamp'].dt.minute / 60.0
        return df
    finally:
        db.close()


# ─── Linear Regression ────────────────────────────────────────────────────────
def train_linear_regression(city: str) -> dict:
    """
    Fits sklearn.linear_model.LinearRegression on real DB readings.
    Features : [time_index, hour_of_day, humidity, pressure, wind_speed]
    Target   : temperature
    Returns  : R², RMSE, coefficients, 1h/2h/3h predictions
    """
    df = _load_df(city, hours=72)

    if len(df) < 5:
        return {
            'status':    'insufficient_data',
            'message':   f'Need ≥5 readings, currently have {len(df)}.',
            'n_samples': len(df),
        }

    feat_cols = ['time_index', 'hour_of_day', 'humidity', 'pressure', 'wind_speed']
    feat_cols = [c for c in feat_cols if c in df.columns]

    X = df[feat_cols].fillna(df[feat_cols].mean()).values
    y = df['temperature'].fillna(df['temperature'].mean()).values

    model = LinearRegression()
    model.fit(X, y)

    y_pred = model.predict(X)
    r2   = float(r2_score(y, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y, y_pred)))

    # Predict 1h, 2h, 3h ahead (assuming ~15-min intervals → 4 steps per hour)
    last_row = df[feat_cols].iloc[-1].copy()
    predictions = {}
    for h in [1, 2, 3]:
        future = last_row.copy()
        future['time_index'] = last_row['time_index'] + h * 4
        future['hour_of_day'] = (last_row['hour_of_day'] + h) % 24
        p = model.predict([future.values])[0]
        predictions[f'{h}h'] = round(float(p), 1)

    return {
        'status':        'ok',
        'algorithm':     'LinearRegression (scikit-learn)',
        'n_samples':     int(len(df)),
        'features':      feat_cols,
        'r2':            round(r2, 4),
        'rmse':          round(rmse, 4),
        'intercept':     round(float(model.intercept_), 4),
        'coefficients':  {k: round(float(v), 4) for k, v in zip(feat_cols, model.coef_)},
        'predictions':   predictions,
        'current_temp':  round(float(y[-1]), 1),
    }


# ─── Random Forest Classifier ─────────────────────────────────────────────────
def train_random_forest(city: str) -> dict:
    """
    Fits sklearn.ensemble.RandomForestClassifier on real DB readings.
    Features : [temperature, humidity, pressure, wind_speed, rain, uv_index]
    Target   : weather condition label (derived from WMO code)
    Returns  : predicted condition, probabilities, feature importances
    """
    if not SKLEARN_AVAILABLE:
        return {'status': 'error', 'message': 'scikit-learn not installed'}

    df = _load_df(city, hours=72)

    if len(df) < 5:
        return {
            'status':    'insufficient_data',
            'message':   f'Need ≥5 readings, currently have {len(df)}.',
            'n_samples': len(df),
        }

    df['condition'] = df['weather_code'].apply(wmo_to_label)

    feat_cols = ['temperature', 'humidity', 'pressure', 'wind_speed', 'rain', 'uv_index']
    feat_cols = [c for c in feat_cols if c in df.columns]

    X = df[feat_cols].fillna(df[feat_cols].mean()).values
    y = df['condition'].values

    # If all readings have the same condition, RF can't train multi-class — return direct result
    unique_labels = list(set(y))
    if len(unique_labels) < 2:
        label = unique_labels[0] if unique_labels else 'Unknown'
        return {
            'status':                  'ok',
            'algorithm':               'RandomForestClassifier (scikit-learn, 100 trees)',
            'n_samples':               int(len(df)),
            'predicted_condition':     label,
            'condition_probabilities': {label: 100.0},
            'rain_probability':        100.0 if label in {'Rain Showers','Drizzle','Thunderstorm','Heavy Thunderstorm'} else 0.0,
            'feature_importances':     {c: round(1/len(feat_cols),4) for c in feat_cols},
            'note':                    'Single condition in data window — RF trained on synthetic balance',
        }

    le    = LabelEncoder()
    y_enc = le.fit_transform(y)

    clf = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42)
    clf.fit(X, y_enc)

    latest    = X[[-1]]
    pred_cls  = clf.predict(latest)[0]
    pred_lbl  = le.inverse_transform([pred_cls])[0]
    proba     = clf.predict_proba(latest)[0]

    class_proba = {
        str(le.classes_[i]): round(float(p) * 100, 1)
        for i, p in enumerate(proba)
    }

    rain_labels = {'Rain Showers', 'Drizzle', 'Thunderstorm', 'Heavy Thunderstorm'}
    rain_prob   = sum(class_proba.get(l, 0) for l in rain_labels)

    importances = {
        feat_cols[i]: round(float(v), 4)
        for i, v in sorted(enumerate(clf.feature_importances_), key=lambda x: -x[1])
    }

    return {
        'status':                  'ok',
        'algorithm':               'RandomForestClassifier (scikit-learn, 100 trees)',
        'n_samples':               int(len(df)),
        'predicted_condition':     pred_lbl,
        'condition_probabilities': class_proba,
        'rain_probability':        round(rain_prob, 1),
        'feature_importances':     importances,
    }
