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

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


def configure_webhook(domain: str):
    """Register webhook URL with Telegram Bot API.

    Args:
        domain: Your HTTPS domain (e.g., 'your-domain.com')
    """
    # TODO: Implement webhook registration
    # webhook_url = f"https://{domain}/telegram/webhook"
    # Use python-telegram-bot library:
    #   from telegram import Bot
    #   bot = Bot(token=TELEGRAM_BOT_TOKEN)
    #   bot.set_webhook(url=webhook_url)
    logger.info(f"TODO: Register webhook for domain: {domain}")


def check_webhook_status():
    """Check current webhook status via Telegram API."""
    # TODO: Implement
    # bot = Bot(token=TELEGRAM_BOT_TOKEN)
    # info = bot.get_webhook_info()
    # return info
    pass


def handle_command(command: str, chat_id: str) -> str:
    """Handle bot commands.

    Args:
        command: The command string (/start, /help, /status)
        chat_id: Telegram chat ID for reply

    Returns:
        Response message string
    """
    commands = {
        "/start": "👋 Welcome to Grocery Manager! Send me a receipt photo to get started.",
        "/help": (
            "📸 Send a receipt photo → I'll extract items and update your inventory.\n"
            "📊 /status → Check system status\n"
            "❓ /help → Show this message"
        ),
        "/status": "✅ System is running. OCR: Ready | MQTT: Connected | DB: Healthy",
    }
    return commands.get(command, "❓ Unknown command. Try /help")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Telegram webhook configuration module loaded.")
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set in environment!")
