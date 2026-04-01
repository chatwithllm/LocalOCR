"""
Step 4: Configure MQTT Broker Connection
=========================================
PROMPT Reference: Phase 1, Step 4

Initializes and manages the MQTT client connection to the Mosquitto broker.
Provides publish/subscribe helpers used by all modules that need real-time sync.

Broker: mosquitto:1883 (Docker service name)
QoS: 1 (at least once delivery)
Retain: True for inventory state
"""

import os
import json
import logging
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MQTT Topics
# ---------------------------------------------------------------------------

TOPICS = {
    "inventory": "home/grocery/inventory/{product_id}",
    "low_stock": "home/grocery/alerts/low_stock",
    "recommendations": "home/grocery/recommendations/daily",
    "budget_alert": "home/grocery/alerts/budget",
}

# ---------------------------------------------------------------------------
# MQTT Client Management
# ---------------------------------------------------------------------------

_client = None


def _on_connect(client, userdata, flags, rc, properties=None):
    """Callback when connected to MQTT broker."""
    if rc == 0:
        logger.info("Connected to MQTT broker successfully.")
    else:
        logger.error(f"MQTT connection failed with code: {rc}")


def _on_disconnect(client, userdata, rc, properties=None):
    """Callback when disconnected from MQTT broker."""
    if rc != 0:
        logger.warning(f"Unexpected MQTT disconnect (rc={rc}). Will auto-reconnect.")


def _on_message(client, userdata, msg):
    """Callback when a message is received."""
    logger.debug(f"MQTT message received: {msg.topic} → {msg.payload.decode()}")


def get_mqtt_client():
    """Get or create the MQTT client singleton."""
    global _client
    if _client is None:
        _client = setup_mqtt_connection()
    return _client


def setup_mqtt_connection():
    """Initialize and connect the MQTT client."""
    broker = os.getenv("MQTT_BROKER", "mqtt")
    port = int(os.getenv("MQTT_PORT", 1883))

    client = mqtt.Client(
        client_id="grocery-backend",
        protocol=mqtt.MQTTv5
    )

    # Callbacks
    client.on_connect = _on_connect
    client.on_disconnect = _on_disconnect
    client.on_message = _on_message

    # Auto-reconnect
    client.reconnect_delay_set(min_delay=1, max_delay=60)

    try:
        client.connect(broker, port, keepalive=60)
        client.loop_start()  # Non-blocking background loop
        logger.info(f"MQTT client connecting to {broker}:{port}")
    except Exception as e:
        logger.error(f"Failed to connect to MQTT broker: {e}")

    return client


def publish_message(topic: str, payload: dict, retain: bool = True):
    """Publish a JSON message to an MQTT topic.

    Args:
        topic: MQTT topic string
        payload: Dictionary to serialize as JSON
        retain: Whether broker should retain the message (default: True)
    """
    client = get_mqtt_client()
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()
    message = json.dumps(payload)

    result = client.publish(topic, message, qos=1, retain=retain)
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        logger.debug(f"Published to {topic}: {message[:100]}...")
    else:
        logger.error(f"Failed to publish to {topic}: rc={result.rc}")

    return result


def disconnect_mqtt():
    """Gracefully disconnect the MQTT client."""
    global _client
    if _client:
        _client.loop_stop()
        _client.disconnect()
        _client = None
        logger.info("MQTT client disconnected.")


# ---------------------------------------------------------------------------
# Entry point for testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    client = setup_mqtt_connection()
    publish_message("home/grocery/test", {"message": "MQTT connection test"})
    logger.info("Test message published. Press Ctrl+C to exit.")
    try:
        import time
        time.sleep(5)
    except KeyboardInterrupt:
        pass
    finally:
        disconnect_mqtt()
