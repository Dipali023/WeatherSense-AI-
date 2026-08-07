"""
services/scheduler.py
APScheduler background job — auto-fetches weather for all cities every 15 minutes.
Uses BackgroundScheduler so Flask's main thread is not blocked.
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler

logger    = logging.getLogger(__name__)
scheduler = BackgroundScheduler(timezone='Asia/Kolkata')


def start_scheduler():
    from services.weather_fetcher import fetch_all_cities
    scheduler.add_job(
        fetch_all_cities,
        trigger='interval',
        minutes=15,
        id='weather_fetch_job',
        name='Fetch all cities weather',
        replace_existing=True,
    )
    scheduler.start()
    logger.info("APScheduler started — auto-fetching weather every 15 minutes")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")
