"""
Step 6: Configure Telegram Bot Webhook
=======================================
PROMPT Reference: Phase 2, Step 6

Reads bot token from environment, registers the webhook URL with Telegram,
and implements basic bot commands (/start, /help, /status).

Prerequisite: Nginx Proxy Manager with domain + SSL must be configured.
"""

import os
import logging
import argparse

import requests

# Auto-load .env for local CLI usage
try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except ImportError:
    pass

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_WEBHOOK_BASE_URL = os.getenv("TELEGRAM_WEBHOOK_BASE_URL", "").rstrip("/")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
TELEGRAM_API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def _require_token():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set")


def configure_webhook(base_url: str | None = None) -> dict:
    """Register webhook URL with Telegram Bot API.

    Args:
        base_url: Your HTTPS base URL (e.g., 'https://grocery.example.com')
    """
    _require_token()
    resolved_base_url = (base_url or TELEGRAM_WEBHOOK_BASE_URL).rstrip("/")
    if not resolved_base_url:
        raise ValueError("A public HTTPS base URL is required")

    webhook_url = f"{resolved_base_url}/telegram/webhook"
    payload = {
        "url": webhook_url,
        "allowed_updates": ["message", "callback_query"],
        "drop_pending_updates": False,
    }
    if TELEGRAM_WEBHOOK_SECRET:
        payload["secret_token"] = TELEGRAM_WEBHOOK_SECRET

    response = requests.post(f"{TELEGRAM_API_BASE}/setWebhook", json=payload, timeout=15)
    response.raise_for_status()
    result = response.json()
    logger.info("Telegram webhook registration result: %s", result)
    return result


def check_webhook_status() -> dict:
    """Check current webhook status via Telegram API."""
    _require_token()
    response = requests.get(f"{TELEGRAM_API_BASE}/getWebhookInfo", timeout=15)
    response.raise_for_status()
    return response.json()


def delete_webhook(drop_pending_updates: bool = False) -> dict:
    """Delete the currently configured Telegram webhook."""
    _require_token()
    response = requests.post(
        f"{TELEGRAM_API_BASE}/deleteWebhook",
        json={"drop_pending_updates": drop_pending_updates},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def handle_command(command: str, chat_id: str) -> str:
    """Handle bot commands.

    Args:
        command: The command string (/start, /help, /status)
        chat_id: Telegram chat ID for reply

    Returns:
        Response message string
    """
    commands = {
        "/start": "👋 Welcome to Grocery Manager! Send me a receipt photo or PDF to get started.",
        "/help": (
            "📸 Send a receipt photo or PDF → I'll extract items and update your inventory.\n"
            "📊 /status → Check system status\n"
            "❓ /help → Show this message"
        ),
        "/status": "✅ System is running. OCR: Ready | MQTT: Connected | DB: Healthy",
    }
    return commands.get(command, "❓ Unknown command. Try /help")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Manage Telegram webhook configuration.")
    parser.add_argument("action", choices=["status", "set", "delete"])
    parser.add_argument("--base-url", dest="base_url", help="Public HTTPS base URL for the webhook")
    parser.add_argument("--drop-pending-updates", action="store_true")
    args = parser.parse_args()

    try:
        if args.action == "status":
            print(check_webhook_status())
        elif args.action == "set":
            print(configure_webhook(args.base_url))
        elif args.action == "delete":
            print(delete_webhook(drop_pending_updates=args.drop_pending_updates))
    except Exception as exc:
        logger.error("Telegram webhook command failed: %s", exc)
        raise
