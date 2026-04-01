"""
Step 8: Implement Telegram Webhook Handler
===========================================
PROMPT Reference: Phase 2, Step 8

Handles incoming Telegram webhook POST requests. Extracts photos from
messages, saves them, routes to OCR, and sends feedback to the user.

Feedback paths:
    ✅ Success: "Processed: $X.XX at Store | Y items"
    ⚠️ Low confidence: "Low confidence — please review in Home Assistant"
    ❌ Failure: "Could not process receipt. Saved for manual review."

Auth: Telegram signature validation (not Bearer token)
"""

import os
import logging

from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

telegram_bp = Blueprint("telegram", __name__, url_prefix="/telegram")


@telegram_bp.route("/webhook", methods=["POST"])
def telegram_webhook():
    """Receive and process Telegram webhook updates.

    Telegram sends JSON updates when users interact with the bot.
    This endpoint extracts photos, processes them via OCR, and
    sends appropriate feedback to the user.
    """
    # TODO: Validate Telegram webhook signature
    # TODO: Parse update JSON
    # TODO: Extract chat_id and photo
    # TODO: Download largest photo from Telegram CDN
    # TODO: Save to /data/receipts/
    # TODO: Send "⏳ Processing receipt..." status message
    # TODO: Route to extract_receipt_data.process_receipt()
    # TODO: Send result feedback (success/warning/error)

    update = request.get_json(silent=True)
    if not update:
        return jsonify({"error": "Invalid update"}), 400

    logger.info(f"Telegram webhook received update: {update.get('update_id', 'unknown')}")

    # Placeholder response
    return jsonify({"status": "ok"}), 200


def send_telegram_message(chat_id: str, text: str):
    """Send a message back to a Telegram user.

    Args:
        chat_id: Telegram chat ID
        text: Message text to send
    """
    # TODO: Implement using python-telegram-bot
    # from telegram import Bot
    # bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
    # bot.send_message(chat_id=chat_id, text=text)
    logger.info(f"TODO: Send to {chat_id}: {text[:50]}...")


def download_telegram_photo(file_id: str, save_dir: str) -> str:
    """Download a photo from Telegram CDN.

    Args:
        file_id: Telegram file ID for the photo
        save_dir: Directory to save the downloaded file

    Returns:
        Path to the saved file
    """
    # TODO: Implement using python-telegram-bot
    # bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
    # file = bot.get_file(file_id)
    # file_path = os.path.join(save_dir, f"{file_id}.jpg")
    # file.download_to_drive(file_path)
    # return file_path
    logger.info(f"TODO: Download photo {file_id}")
    return ""
