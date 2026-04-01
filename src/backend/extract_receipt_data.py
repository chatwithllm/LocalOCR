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
from datetime import datetime, timezone

from flask import g

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.80  # Flag for manual review below this
MIN_CONFIDENCE = 0.40        # Reject entirely below this


# ---------------------------------------------------------------------------
# Hybrid OCR Processor
# ---------------------------------------------------------------------------

def process_receipt(image_path: str, source: str = "upload",
                    chat_id: str = None, user_id: int = None) -> dict:
    """Process a receipt image through the hybrid OCR pipeline.

    Args:
        image_path: Path to the receipt image file.
        source: Origin of the receipt — "telegram" or "upload"
        chat_id: Telegram chat ID (only set when source="telegram")
        user_id: ID of the user who uploaded (for audit trail)

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
        "error": None,
    }

    ocr_data = None
    engine_used = None

    # --- Step 1: Try Gemini ---
    try:
        from src.backend.call_gemini_vision_api import extract_receipt_via_gemini
        ocr_data = extract_receipt_via_gemini(image_path)
        engine_used = "gemini"
        logger.info("Gemini OCR succeeded.")
    except Exception as e:
        logger.warning(f"Gemini OCR failed: {e}. Falling back to Ollama.")

        # --- Step 2: Fallback to Ollama ---
        try:
            from src.backend.call_ollama_vision_api import extract_receipt_via_ollama
            ocr_data = extract_receipt_via_ollama(image_path)
            engine_used = "ollama"
            logger.info("Ollama OCR fallback succeeded.")
        except Exception as e2:
            logger.error(f"Ollama OCR also failed: {e2}")
            result["status"] = "failed"
            result["error"] = f"Both OCR engines failed. Gemini: {e}, Ollama: {e2}"

            # Send failure feedback via Telegram
            if source == "telegram" and chat_id:
                _send_telegram_error(chat_id)

            # Save to DB as failed
            _save_receipt_record(image_path, None, None, "failed", 0.0, user_id)
            return result

    # --- Step 3: Validate & Route ---
    if ocr_data:
        result["data"] = ocr_data
        result["ocr_engine"] = engine_used
        result["confidence"] = ocr_data.get("confidence", 0.0)

        is_valid = _validate_receipt_data(ocr_data)

        if is_valid and result["confidence"] >= CONFIDENCE_THRESHOLD:
            # High confidence — auto-process
            result["status"] = "processed"
            purchase_id = _save_to_database(ocr_data, engine_used, image_path, user_id)
            result["purchase_id"] = purchase_id

            if source == "telegram" and chat_id:
                _send_telegram_success(chat_id, ocr_data)

        elif is_valid and result["confidence"] >= MIN_CONFIDENCE:
            # Medium confidence — save but flag for review
            result["status"] = "review"
            purchase_id = _save_to_database(ocr_data, engine_used, image_path, user_id)
            result["purchase_id"] = purchase_id

            if source == "telegram" and chat_id:
                _send_telegram_warning(chat_id)

        else:
            # Low confidence or invalid — manual review
            result["status"] = "review"
            _save_receipt_record(image_path, engine_used, None, "review",
                                result["confidence"], user_id)

            if source == "telegram" and chat_id:
                _send_telegram_warning(chat_id)

    return result


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_receipt_data(data: dict) -> bool:
    """Validate that OCR output contains all required fields."""
    required_fields = ["store", "date", "items", "total"]
    for field in required_fields:
        if field not in data or data[field] is None:
            logger.warning(f"Validation failed: missing field '{field}'")
            return False

    if not isinstance(data["items"], list) or len(data["items"]) == 0:
        logger.warning("Validation failed: items must be a non-empty list")
        return False

    # Validate each item has at least name and unit_price
    for i, item in enumerate(data["items"]):
        if not item.get("name"):
            logger.warning(f"Validation: item {i} missing 'name'")
            return False
        if item.get("unit_price") is None:
            logger.warning(f"Validation: item {i} missing 'unit_price'")
            # Don't fail — some items might be discounts at $0.00

    return True


# ---------------------------------------------------------------------------
# Database Persistence
# ---------------------------------------------------------------------------

def _save_to_database(ocr_data: dict, engine: str, image_path: str,
                       user_id: int = None) -> int:
    """Save validated OCR data to purchases, receipt_items, and price_history."""
    try:
        from src.backend.initialize_database_schema import (
            Purchase, ReceiptItem, Product, Store, PriceHistory, Inventory
        )
        session = g.db_session

        # Find or create store
        store_name = ocr_data.get("store", "Unknown Store")
        store = session.query(Store).filter_by(name=store_name).first()
        if not store:
            store = Store(
                name=store_name,
                location=ocr_data.get("store_location"),
            )
            session.add(store)
            session.flush()

        # Create purchase record
        purchase_date = ocr_data.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        purchase = Purchase(
            store_id=store.id,
            total_amount=ocr_data.get("total", 0.0),
            date=datetime.strptime(str(purchase_date), "%Y-%m-%d"),
            user_id=user_id,
        )
        session.add(purchase)
        session.flush()

        # Process each item
        for item_data in ocr_data.get("items", []):
            product_name = item_data.get("name", "Unknown Item")
            category = item_data.get("category", "other")
            quantity = item_data.get("quantity", 1)
            unit_price = item_data.get("unit_price", 0.0)

            # Find or create product
            product = session.query(Product).filter_by(
                name=product_name, category=category
            ).first()
            if not product:
                product = Product(name=product_name, category=category)
                session.add(product)
                session.flush()

            # Create receipt item
            receipt_item = ReceiptItem(
                purchase_id=purchase.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=unit_price,
                extracted_by=engine,
            )
            session.add(receipt_item)

            # Update price history
            ph = PriceHistory(
                product_id=product.id,
                store_id=store.id,
                price=unit_price,
                date=purchase.date,
            )
            session.add(ph)

            # Auto-update inventory
            _update_inventory(session, product, quantity, user_id)

        session.commit()

        logger.info(
            f"Saved receipt: {store_name} | ${ocr_data.get('total', 0):.2f} | "
            f"{len(ocr_data.get('items', []))} items | purchase_id={purchase.id}"
        )

        # Publish MQTT update for each product
        _publish_inventory_updates(session, ocr_data.get("items", []))

        return purchase.id

    except Exception as e:
        logger.error(f"Failed to save receipt to database: {e}")
        session.rollback()
        raise


def _update_inventory(session, product, quantity, user_id):
    """Add or update inventory for a product."""
    from src.backend.initialize_database_schema import Inventory

    inv = session.query(Inventory).filter_by(product_id=product.id).first()
    if inv:
        inv.quantity += quantity
        inv.updated_by = user_id
    else:
        inv = Inventory(
            product_id=product.id,
            quantity=quantity,
            location="Pantry",  # Default location
            updated_by=user_id,
        )
        session.add(inv)


def _publish_inventory_updates(session, items):
    """Publish MQTT events for all updated products."""
    try:
        from src.backend.publish_mqtt_events import publish_inventory_update
        from src.backend.initialize_database_schema import Product, Inventory

        for item_data in items:
            product = session.query(Product).filter_by(
                name=item_data.get("name", "")
            ).first()
            if product:
                inv = session.query(Inventory).filter_by(
                    product_id=product.id
                ).first()
                if inv:
                    publish_inventory_update(
                        product_id=product.id,
                        name=product.name,
                        quantity=inv.quantity,
                        location=inv.location or "Pantry",
                        updated_by="system",
                    )
    except Exception as e:
        logger.warning(f"Failed to publish MQTT updates: {e}")


def _save_receipt_record(image_path, engine, purchase_id, status, confidence, user_id):
    """Save a minimal receipt record for failed/review items."""
    try:
        from src.backend.initialize_database_schema import TelegramReceipt
        session = g.db_session

        record = TelegramReceipt(
            telegram_user_id=str(user_id or "unknown"),
            image_path=image_path,
            status=status,
            ocr_confidence=confidence,
            ocr_engine=engine,
            purchase_id=purchase_id,
        )
        session.add(record)
        session.commit()
    except Exception as e:
        logger.warning(f"Failed to save receipt record: {e}")


# ---------------------------------------------------------------------------
# Telegram Feedback
# ---------------------------------------------------------------------------

def _send_telegram_success(chat_id: str, data: dict):
    """Send success confirmation to Telegram user."""
    try:
        from src.backend.handle_telegram_messages import send_telegram_message
        item_count = len(data.get("items", []))
        store = data.get("store", "Unknown")
        total = data.get("total", 0)
        msg = f"✅ Processed: ${total:.2f} at {store} | {item_count} items"
        send_telegram_message(chat_id, msg)
    except Exception as e:
        logger.warning(f"Failed to send Telegram success: {e}")


def _send_telegram_warning(chat_id: str):
    """Send low-confidence warning to Telegram user."""
    try:
        from src.backend.handle_telegram_messages import send_telegram_message
        send_telegram_message(chat_id, "⚠️ Low confidence — please review in Home Assistant")
    except Exception as e:
        logger.warning(f"Failed to send Telegram warning: {e}")


def _send_telegram_error(chat_id: str):
    """Send failure error to Telegram user."""
    try:
        from src.backend.handle_telegram_messages import send_telegram_message
        send_telegram_message(chat_id, "❌ Could not process receipt. Saved for manual review.")
    except Exception as e:
        logger.warning(f"Failed to send Telegram error: {e}")
