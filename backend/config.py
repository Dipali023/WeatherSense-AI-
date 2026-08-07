import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'weather.db')
DB_URI   = f'sqlite:///{DB_PATH}'

OPEN_METEO_BASE        = 'https://api.open-meteo.com/v1'
FETCH_INTERVAL_MINUTES = 15
FORECAST_CACHE_MINUTES = 30

CITIES = {
    'nagpur':     {'name': 'Nagpur, Maharashtra',         'lat': 21.15, 'lon': 79.09},
    'mumbai':     {'name': 'Mumbai, Maharashtra',         'lat': 19.07, 'lon': 72.87},
    'pune':       {'name': 'Pune, Maharashtra',           'lat': 18.52, 'lon': 73.85},
    'delhi':      {'name': 'Delhi, India',                'lat': 28.61, 'lon': 77.20},
    'bangalore':  {'name': 'Bengaluru, Karnataka',        'lat': 12.97, 'lon': 77.59},
    'chennai':    {'name': 'Chennai, Tamil Nadu',         'lat': 13.08, 'lon': 80.27},
    'kolkata':    {'name': 'Kolkata, West Bengal',        'lat': 22.57, 'lon': 88.36},
    'hyderabad':  {'name': 'Hyderabad, Telangana',        'lat': 17.38, 'lon': 78.48},
    'ahmedabad':  {'name': 'Ahmedabad, Gujarat',          'lat': 23.02, 'lon': 72.57},
    'jaipur':     {'name': 'Jaipur, Rajasthan',           'lat': 26.91, 'lon': 75.78},
    'lucknow':    {'name': 'Lucknow, Uttar Pradesh',      'lat': 26.84, 'lon': 80.94},
    'patna':      {'name': 'Patna, Bihar',                'lat': 25.59, 'lon': 85.13},
    'guwahati':   {'name': 'Guwahati, Assam',             'lat': 26.14, 'lon': 91.73},
    'srinagar':   {'name': 'Srinagar, J&K',               'lat': 34.08, 'lon': 74.79},
    'chandigarh': {'name': 'Chandigarh, India',           'lat': 30.73, 'lon': 76.78},
}
