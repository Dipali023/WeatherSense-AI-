"""
database/models.py
SQLAlchemy ORM models for WeatherSense AI.
Tables: weather_readings, forecast_cache
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import (
    create_engine, Column, Integer, Float, String, DateTime, Text
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

from config import DB_URI

Base = declarative_base()


class WeatherReading(Base):
    """One real weather observation fetched from Open-Meteo and stored to DB."""
    __tablename__ = 'weather_readings'

    id             = Column(Integer, primary_key=True, autoincrement=True)
    city           = Column(String(50),  nullable=False, index=True)
    timestamp      = Column(DateTime,    default=datetime.utcnow, index=True)
    temperature    = Column(Float)          # °C
    humidity       = Column(Float)          # %
    pressure       = Column(Float)          # hPa
    wind_speed     = Column(Float)          # km/h
    wind_direction = Column(Float)          # degrees
    rain           = Column(Float)          # mm
    uv_index       = Column(Float)
    weather_code   = Column(Integer)        # WMO code
    apparent_temp  = Column(Float)          # feels-like °C
    source         = Column(String(50), default='open_meteo')

    def to_dict(self):
        return {
            'id':            self.id,
            'city':          self.city,
            'timestamp':     self.timestamp.isoformat() if self.timestamp else None,
            'temperature':   self.temperature,
            'humidity':      self.humidity,
            'pressure':      self.pressure,
            'wind_speed':    self.wind_speed,
            'wind_direction':self.wind_direction,
            'rain':          self.rain,
            'uv_index':      self.uv_index,
            'weather_code':  self.weather_code,
            'apparent_temp': self.apparent_temp,
            'source':        self.source,
        }


class ForecastCache(Base):
    """Cached 7-day forecast JSON from Open-Meteo."""
    __tablename__ = 'forecast_cache'

    id            = Column(Integer, primary_key=True, autoincrement=True)
    city          = Column(String(50), nullable=False, index=True)
    fetched_at    = Column(DateTime, default=datetime.utcnow)
    forecast_json = Column(Text)


# ─── Engine & Session ─────────────────────────────────────────────────────────
engine       = create_engine(DB_URI, connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(bind=engine)


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(engine)


def get_db():
    """Dependency-injection helper (yields a session then closes it)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
