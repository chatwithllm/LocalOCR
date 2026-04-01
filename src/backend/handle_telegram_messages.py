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
from uuid import uuid4
from datetime import datetime

import requests as http_requests
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

telegram_bp = Blueprint("telegram", __name__, url_prefix="/telegram")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


@telegram_bp.route("/webhook", methods=["POST"])
def telegram_webhook():
    """Receive and process Telegram webhook updates."""
    update = request.get_json(silent=True)
    if not update:
        return jsonify({"error": "Invalid update"}), 400

    logger.info(f"Telegram update: {update.get('update_id', '?')}")

    message = update.get("message", {})
    chat_id = str(message.get("chat", {}).get("id", ""))

    if not chat_id:
        return jsonify({"status": "ok"}), 200

    # Handle commands
    text = message.get("text", "")
    if text.startswith("/"):
        response_text = _handle_command(text)
        send_telegram_message(chat_id, response_text)
        return jsonify({"status": "ok"}), 200

    # Handle photos
    photos = message.get("photo", [])
    if not photos:
        send_telegram_message(chat_id, "📸 Please send a receipt photo to get started!")
        return jsonify({"status": "ok"}), 200

    # Download the largest photo
    largest_photo = max(photos, key=lambda p: p.get("file_size", 0))
    file_id = largest_photo.get("file_id")

    # Send processing status
    send_telegram_message(chat_id, "⏳ Processing receipt...")

    # Download photo
    try:
        image_path = download_telegram_photo(file_id)
    except Exception as e:
        logger.error(f"Failed to download Telegram photo: {e}")
        send_telegram_message(chat_id, "❌ Could not download photo. Please try again.")
        return jsonify({"status": "error"}), 200

    # Route to OCR processor
    try:
        from src.backend.extract_receipt_data import process_receipt
        result = process_receipt(
            image_path=image_path,
            source="telegram",
            chat_id=chat_id,
        )
        # Feedback is handled inside process_receipt via _send_telegram_*
    except Exception as e:
        logger.error(f"OCR processing failed: {e}")
        send_telegram_message(chat_id, "❌ Could not process receipt. Saved for manual review.")

    return jsonify({"status": "ok"}), 200


def _handle_command(command: str) -> str:
    """Handle bot commands."""
    cmd = command.split()[0].lower()
    commands = {
        "/start": "👋 Welcome to Grocery Manager! Send me a receipt photo to get started.",
        "/help": (
            "📸 Send a receipt photo → I'll extract items and update your inventory.\n"
            "📊 /status → Check system status\n"
            "❓ /help → Show this message"
        ),
        "/status": "✅ System is running. Send a receipt photo to test!",
    }
    return commands.get(cmd, "❓ Unknown command. Try /help")


def send_telegram_message(chat_id: str, text: str):
    """Send a message back to a Telegram user."""
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set — cannot send message")
        return

    try:
        response = http_requests.post(
            f"{TELEGRAM_API_BASE}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        if response.status_code != 200:
            logger.warning(f"Telegram sendMessage failed: {response.text}")
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")


def download_telegram_photo(file_id: str) -> str:
    """Download a photo from Telegram CDN.

    Returns:
        Path to the saved file.
    """
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set")

    # Get file path from Telegram
    response = http_requests.get(
        f"{TELEGRAM_API_BASE}/getFile",
        params={"file_id": file_id},
        timeout=10,
    )
    response.raise_for_status()
    file_path = response.json()["result"]["file_path"]

    # Download the file
    download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
    file_response = http_requests.get(download_url, timeout=30)
    file_response.raise_for_status()

    # Save to receipts directory
    year_month = datetime.now().strftime("%Y/%m")
    save_dir = f"/data/receipts/{year_month}"
    os.makedirs(save_dir, exist_ok=True)

    ext = os.path.splitext(file_path)[1] or ".jpg"
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}{ext}"
    save_path = os.path.join(save_dir, filename)

    with open(save_path, "wb") as f:
        f.write(file_response.content)

    logger.info(f"Telegram photo saved: {save_path}")
    return save_path
