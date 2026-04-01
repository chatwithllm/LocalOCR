"""
Step 17: Implement Daily Recommendation Push
==============================================
PROMPT Reference: Phase 5, Step 17

Scheduled task that generates and publishes recommendations daily at 8 AM
(configurable via RECOMMENDATION_TIME env var).

Uses APScheduler for scheduling. Publishes to MQTT topic:
home/grocery/recommendations/daily
"""

import os
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

RECOMMENDATION_TIME = os.getenv("RECOMMENDATION_TIME", "08:00")

_scheduler = None


def start_recommendation_scheduler():
    """Start the daily recommendation scheduler."""
    global _scheduler

    hour, minute = RECOMMENDATION_TIME.split(":")
    hour, minute = int(hour), int(minute)

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        push_daily_recommendations,
        trigger="cron",
        hour=hour,
        minute=minute,
        id="daily_recommendations",
        name="Daily Recommendation Push",
    )
    _scheduler.start()
    logger.info(f"Recommendation scheduler started — daily at {RECOMMENDATION_TIME}")


def push_daily_recommendations():
    """Generate and publish daily recommendations via MQTT."""
    try:
        # TODO: Implement
        # from src.backend.generate_recommendations import generate_all_recommendations
        # from src.backend.publish_mqtt_events import publish_recommendations
        #
        # recommendations = generate_all_recommendations()
        # publish_recommendations(recommendations)
        #
        # logger.info(f"Published {len(recommendations)} daily recommendations")
        logger.warning("Daily recommendation push not yet implemented")
    except Exception as e:
        logger.error(f"Failed to push daily recommendations: {e}")


def stop_recommendation_scheduler():
    """Stop the scheduler gracefully."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Recommendation scheduler stopped.")
