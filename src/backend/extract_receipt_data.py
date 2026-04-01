"""
Step 11: Implement Hybrid OCR Processor
========================================
PROMPT Reference: Phase 3, Step 11

Orchestrates the Gemini → Ollama fallback logic for receipt processing.
Validates OCR output, auto-updates inventory on success, and ensures
Telegram users always receive feedback (when triggered via Telegram).

Fallback chain: Gemini → Ollama → Manual Review
Confidence threshold: ≥0.40 (aligned with scaled confidence formulas)
"""

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Hybrid OCR Processor
# ---------------------------------------------------------------------------

def process_receipt(image_path: str, source: str = "upload", chat_id: str = None) -> dict:
    """Process a receipt image through the hybrid OCR pipeline.

    Args:
        image_path: Path to the receipt image file.
        source: Origin of the receipt — "telegram" or "upload"
        chat_id: Telegram chat ID (only set when source="telegram")

    Returns:
        Dictionary with processed receipt data and status.
    """
    result = {
        "status": "pending",
        "image_path": image_path,
        "source": source,
        "ocr_engine": None,
        "data": None,
        "confidence": 0.0,
    }

    # --- Step 1: Try Gemini ---
    # TODO: Implement
    # try:
    #     from src.backend.call_gemini_vision_api import extract_receipt_via_gemini
    #     data = extract_receipt_via_gemini(image_path)
    #     result["ocr_engine"] = "gemini"
    #     result["data"] = data
    #     result["confidence"] = data.get("confidence", 0.0)
    #     logger.info(f"Gemini OCR succeeded (confidence: {result['confidence']})")
    # except Exception as e:
    #     logger.warning(f"Gemini OCR failed: {e}. Falling back to Ollama.")
    #     gemini_failed = True

    # --- Step 2: Fallback to Ollama ---
    # TODO: Implement (only if Gemini failed)
    # if gemini_failed:
    #     try:
    #         from src.backend.call_ollama_vision_api import extract_receipt_via_ollama
    #         data = extract_receipt_via_ollama(image_path)
    #         result["ocr_engine"] = "ollama"
    #         result["data"] = data
    #         result["confidence"] = data.get("confidence", 0.0)
    #         logger.info(f"Ollama OCR succeeded (confidence: {result['confidence']})")
    #     except Exception as e:
    #         logger.error(f"Ollama OCR also failed: {e}")

    # --- Step 3: Validate & Route ---
    # TODO: Implement
    # if result["data"] and result["confidence"] >= 0.40:
    #     validated = _validate_receipt_data(result["data"])
    #     if validated:
    #         result["status"] = "processed"
    #         _auto_update_inventory(result["data"])
    #         if source == "telegram" and chat_id:
    #             _send_telegram_success(chat_id, result["data"])
    #     else:
    #         result["status"] = "review"
    # elif result["data"] and result["confidence"] < 0.40:
    #     result["status"] = "review"
    #     if source == "telegram" and chat_id:
    #         _send_telegram_warning(chat_id)
    # else:
    #     result["status"] = "failed"
    #     if source == "telegram" and chat_id:
    #         _send_telegram_error(chat_id)

    logger.warning("Hybrid OCR processor not yet implemented")
    result["status"] = "not_implemented"
    return result


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_receipt_data(data: dict) -> bool:
    """Validate that OCR output contains all required fields.

    Required: store, date, items[], total
    """
    required_fields = ["store", "date", "items", "total"]
    for field in required_fields:
        if field not in data or data[field] is None:
            logger.warning(f"Validation failed: missing field '{field}'")
            return False

    if not isinstance(data["items"], list) or len(data["items"]) == 0:
        logger.warning("Validation failed: items must be a non-empty list")
        return False

    return True


# ---------------------------------------------------------------------------
# Inventory Auto-Update
# ---------------------------------------------------------------------------

def _auto_update_inventory(receipt_data: dict):
    """Auto-add items from a processed receipt to inventory."""
    # TODO: Implement
    # from src.backend.manage_inventory import add_item_to_inventory
    # for item in receipt_data["items"]:
    #     add_item_to_inventory(
    #         product_name=item["name"],
    #         quantity=item["quantity"],
    #         category=item.get("category"),
    #     )
    pass


# ---------------------------------------------------------------------------
# Telegram Feedback
# ---------------------------------------------------------------------------

def _send_telegram_success(chat_id: str, data: dict):
    """Send success confirmation to Telegram user."""
    # TODO: from src.backend.handle_telegram_messages import send_telegram_message
    # msg = f"✅ Processed: ${data['total']:.2f} at {data['store']} | {len(data['items'])} items"
    # send_telegram_message(chat_id, msg)
    pass


def _send_telegram_warning(chat_id: str):
    """Send low-confidence warning to Telegram user."""
    # TODO: send_telegram_message(chat_id, "⚠️ Low confidence — please review in Home Assistant")
    pass


def _send_telegram_error(chat_id: str):
    """Send failure error to Telegram user."""
    # TODO: send_telegram_message(chat_id, "❌ Could not process receipt. Saved for manual review.")
    pass
