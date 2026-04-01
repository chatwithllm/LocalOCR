"""
Step 20: Create MQTT Real-Time Sync Handler
=============================================
PROMPT Reference: Phase 7, Step 20

Centralized MQTT publishing functions used by all modules that need
real-time sync. Every state change publishes a retained JSON message.

QoS: 1 (at least once delivery)
Retain: True (Home Assistant sees last state on reconnect)

Topics:
    home/grocery/inventory/{product_id}  — inventory updates
    home/grocery/alerts/low_stock        — low-stock alerts
    home/grocery/alerts/budget           — budget threshold alerts
    home/grocery/recommendations/daily   — daily recommendations
"""

import logging
from datetime import datetime, timezone

from src.backend.setup_mqtt_connection import publish_message, TOPICS

logger = logging.getLogger(__name__)


def publish_inventory_update(product_id: int, name: str, quantity: float,
                              location: str, updated_by: str):
    """Publish an inventory state change."""
    topic = TOPICS["inventory"].format(product_id=product_id)
    payload = {
        "product_id": product_id,
        "name": name,
        "quantity": quantity,
        "location": location,
        "updated_by": updated_by,
    }
    publish_message(topic, payload, retain=True)
    logger.info(f"Published inventory update: {name} → {quantity}")


def publish_low_stock_alert(product_id: int, product_name: str,
                             current_qty: float, threshold: float):
    """Publish a low-stock alert."""
    topic = TOPICS["low_stock"]
    payload = {
        "product_id": product_id,
        "name": product_name,
        "current": current_qty,
        "threshold": threshold,
        "alert_type": "low_stock",
    }
    publish_message(topic, payload, retain=False)
    logger.info(f"Published low-stock alert: {product_name} ({current_qty} < {threshold})")


def publish_budget_alert(budget_amount: float, spent: float, percentage: float):
    """Publish a budget threshold alert."""
    topic = TOPICS["budget_alert"]
    payload = {
        "budget_amount": budget_amount,
        "spent": spent,
        "percentage": round(percentage, 1),
        "alert_type": "budget",
    }
    publish_message(topic, payload, retain=False)
    logger.info(f"Published budget alert: {percentage:.1f}% spent")


def publish_recommendations(recommendations: list):
    """Publish daily recommendations."""
    topic = TOPICS["recommendations"]
    payload = {
        "recommendations": recommendations,
        "count": len(recommendations),
    }
    publish_message(topic, payload, retain=True)
    logger.info(f"Published {len(recommendations)} recommendations")
