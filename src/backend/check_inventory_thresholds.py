"""
Step 15: Add Low-Stock Alert System
=====================================
PROMPT Reference: Phase 4, Step 15

Checks inventory against per-product thresholds every 5 minutes.
Publishes MQTT alerts and avoids duplicate alerts (24-hour repeat interval).

MQTT Topic: home/grocery/alerts/low_stock
"""

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Track last alert time per product to avoid duplicates
_last_alert_times = {}


def check_all_thresholds():
    """Check all inventory items against their thresholds.

    Runs every 5 minutes via APScheduler.
    Publishes MQTT alert for items below threshold.
    """
    # TODO: Implement
    # session = get_db_session()
    # items = session.query(Inventory).filter(
    #     Inventory.threshold.isnot(None),
    #     Inventory.quantity < Inventory.threshold
    # ).all()
    #
    # for item in items:
    #     if _should_alert(item.product_id):
    #         _publish_low_stock_alert(item)
    #         _last_alert_times[item.product_id] = datetime.now(timezone.utc)
    logger.warning("Threshold checking not yet implemented")


def _should_alert(product_id: int) -> bool:
    """Check if we should send an alert (24-hour dedup)."""
    last_alert = _last_alert_times.get(product_id)
    if last_alert is None:
        return True
    return datetime.now(timezone.utc) - last_alert > timedelta(hours=24)


def _publish_low_stock_alert(item):
    """Publish a low-stock alert via MQTT."""
    # TODO: Implement
    # from src.backend.publish_mqtt_events import publish_low_stock_alert
    # publish_low_stock_alert(
    #     product_id=item.product_id,
    #     product_name=item.product.name,
    #     current_qty=item.quantity,
    #     threshold=item.threshold,
    # )
    pass


def set_threshold(product_id: int, threshold: float):
    """Set the low-stock threshold for a product."""
    # TODO: Implement
    # session = get_db_session()
    # item = session.query(Inventory).filter_by(product_id=product_id).first()
    # item.threshold = threshold
    # session.commit()
    pass
