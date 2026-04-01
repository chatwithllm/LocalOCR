"""
Step 5: Create Stub Receipt Upload Endpoint
============================================
PROMPT Reference: Phase 1, Step 5

Provides POST /receipts/upload endpoint that accepts image and PDF files directly.
Enables testing the OCR → inventory pipeline without Telegram/Nginx/SSL.
Also serves as the Home Assistant upload channel long-term.

Auth: Bearer token required
"""

import os
import logging
import json
from pathlib import Path
from uuid import uuid4
from datetime import datetime

from flask import Blueprint, request, jsonify, g, send_file

from src.backend.create_flask_application import require_auth

logger = logging.getLogger(__name__)

receipts_bp = Blueprint("receipts", __name__, url_prefix="/receipts")

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".pdf"}


def _get_receipts_root() -> str:
    """Return the receipt storage root.

    Prefer RECEIPTS_DIR when set. Otherwise use /data/receipts for containerized
    deployments if /data exists, and fall back to a repo-local data directory for
    local development runs.
    """
    configured = os.getenv("RECEIPTS_DIR")
    if configured:
        return configured

    container_path = Path("/data/receipts")
    if container_path.parent.exists():
        return str(container_path)

    repo_root = Path(__file__).resolve().parents[2]
    return str(repo_root / "data" / "receipts")


def _resolve_receipt_path(image_path: str) -> Path | None:
    """Return a safe local path for a stored receipt image."""
    if not image_path:
        return None

    path = Path(image_path)
    if not path.is_absolute():
        path = Path(_get_receipts_root()) / path

    try:
        resolved = path.resolve(strict=True)
        root = Path(_get_receipts_root()).resolve()
        resolved.relative_to(root)
    except Exception:
        return None

    return resolved


def _detect_receipt_file_type(image_path: str | None) -> str | None:
    """Infer the stored receipt file type from its path."""
    if not image_path:
        return None
    ext = Path(image_path).suffix.lower().lstrip(".")
    return ext or None


def _parse_raw_ocr_json(raw_value: str | None) -> dict | None:
    """Parse stored OCR JSON safely for review flows."""
    if not raw_value:
        return None
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        logger.warning("Failed to parse stored OCR JSON for receipt review.")
        return None


@receipts_bp.route("/upload", methods=["POST"])
@require_auth
def upload_receipt():
    """Upload a receipt file for OCR processing.

    Accepts multipart/form-data with an 'image' file field.
    Routes to the hybrid OCR processor (extract_receipt_data.py).

    Returns:
        JSON with extracted receipt data or error message.
    """
    # Validate file presence
    if "image" not in request.files:
        return jsonify({"error": "No receipt file provided. Use 'image' field."}), 400

    image_file = request.files["image"]
    if image_file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    # Validate file type
    ext = os.path.splitext(image_file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({
            "error": f"Unsupported file type: {ext}",
            "allowed": list(ALLOWED_EXTENSIONS),
        }), 400

    # Save to receipts directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{uuid4().hex[:8]}{ext}"
    year_month = datetime.now().strftime("%Y/%m")
    save_dir = os.path.join(_get_receipts_root(), year_month)
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, filename)

    try:
        image_file.save(save_path)
        logger.info(f"Receipt file saved: {save_path}")
    except Exception as e:
        logger.error(f"Failed to save receipt image: {e}")
        return jsonify({"error": "Failed to save receipt file"}), 500

    # Get user ID from auth context
    user_id = None
    current_user = getattr(g, "current_user", None)
    if current_user:
        user_id = current_user.id

    # Route to hybrid OCR processor
    try:
        from src.backend.extract_receipt_data import process_receipt
        result = process_receipt(
            image_path=save_path,
            source="upload",
            user_id=user_id,
        )

        status_code = {
            "processed": 200,
            "review": 200,
            "failed": 422,
            "not_implemented": 202,
        }.get(result["status"], 200)

        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"OCR processing failed: {e}")
        return jsonify({
            "error": "OCR processing failed",
            "message": str(e),
            "image_path": save_path,
        }), 500


@receipts_bp.route("/<int:receipt_id>", methods=["GET"])
@require_auth
def get_receipt(receipt_id):
    """Retrieve details for a specific receipt/purchase."""
    from src.backend.initialize_database_schema import Purchase, ReceiptItem, Store, Product, TelegramReceipt

    session = g.db_session
    purchase = session.query(Purchase).filter_by(id=receipt_id).first()
    receipt_record = (
        session.query(TelegramReceipt)
        .filter(
            (TelegramReceipt.purchase_id == receipt_id) |
            (TelegramReceipt.id == receipt_id)
        )
        .order_by(TelegramReceipt.created_at.desc())
        .first()
    )
    if not purchase and receipt_record and receipt_record.purchase_id:
        purchase = session.query(Purchase).filter_by(id=receipt_record.purchase_id).first()
    if not purchase and not receipt_record:
        return jsonify({"error": "Receipt not found"}), 404

    store = session.query(Store).filter_by(id=purchase.store_id).first() if purchase else None
    items = []
    if purchase:
        items = (
            session.query(ReceiptItem, Product)
            .join(Product, ReceiptItem.product_id == Product.id)
            .filter(ReceiptItem.purchase_id == purchase.id)
            .all()
        )
    raw_ocr_data = _parse_raw_ocr_json(receipt_record.raw_ocr_json if receipt_record else None)

    return jsonify({
        "id": purchase.id if purchase else receipt_record.id,
        "store": store.name if store else None,
        "total": purchase.total_amount if purchase else None,
        "date": purchase.date.strftime("%Y-%m-%d") if purchase and purchase.date else None,
        "status": receipt_record.status if receipt_record else "processed",
        "ocr_engine": receipt_record.ocr_engine if receipt_record else None,
        "confidence": receipt_record.ocr_confidence if receipt_record else None,
        "receipt_type": receipt_record.receipt_type if receipt_record else None,
        "source": "telegram" if receipt_record and not str(receipt_record.telegram_user_id).startswith("upload") else "upload",
        "created_at": receipt_record.created_at.isoformat() if receipt_record and receipt_record.created_at else None,
        "image_url": f"/receipts/{purchase.id if purchase else receipt_record.id}/image" if receipt_record and receipt_record.image_path else None,
        "file_type": _detect_receipt_file_type(receipt_record.image_path if receipt_record else None),
        "raw_ocr_data": raw_ocr_data,
        "items": [
            {
                "product_id": item.product_id,
                "product_name": product.name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "extracted_by": item.extracted_by,
            }
            for item, product in items
        ],
    }), 200


@receipts_bp.route("", methods=["GET"])
@require_auth
def list_receipts():
    """List saved receipt records for review in the web app."""
    from src.backend.initialize_database_schema import TelegramReceipt, Purchase, Store

    session = g.db_session
    limit = request.args.get("limit", 50, type=int)
    records = (
        session.query(TelegramReceipt, Purchase, Store)
        .outerjoin(Purchase, TelegramReceipt.purchase_id == Purchase.id)
        .outerjoin(Store, Purchase.store_id == Store.id)
        .order_by(TelegramReceipt.created_at.desc())
        .limit(max(1, min(limit, 200)))
        .all()
    )

    return jsonify({
        "receipts": [
            {
                "id": purchase.id if purchase else record.id,
                "record_id": record.id,
                "purchase_id": purchase.id if purchase else None,
                "store": store.name if store else None,
                "total": purchase.total_amount if purchase else None,
                "date": purchase.date.strftime("%Y-%m-%d") if purchase and purchase.date else None,
                "status": record.status,
                "ocr_engine": record.ocr_engine,
                "confidence": record.ocr_confidence,
                "receipt_type": record.receipt_type,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "source": "telegram" if not str(record.telegram_user_id).startswith("upload") else "upload",
                "image_url": f"/receipts/{purchase.id if purchase else record.id}/image" if record.image_path else None,
                "file_type": _detect_receipt_file_type(record.image_path),
            }
            for record, purchase, store in records
        ],
        "count": len(records),
    }), 200


@receipts_bp.route("/<int:receipt_id>/image", methods=["GET"])
@require_auth
def get_receipt_image(receipt_id):
    """Serve the stored image for a processed receipt."""
    from src.backend.initialize_database_schema import TelegramReceipt

    session = g.db_session
    record = (
        session.query(TelegramReceipt)
        .filter(
            (TelegramReceipt.purchase_id == receipt_id) |
            (TelegramReceipt.id == receipt_id)
        )
        .order_by(TelegramReceipt.created_at.desc())
        .first()
    )
    if not record or not record.image_path:
        return jsonify({"error": "Receipt image not found"}), 404

    image_path = _resolve_receipt_path(record.image_path)
    if not image_path:
        return jsonify({"error": "Receipt image not found"}), 404

    return send_file(image_path)


@receipts_bp.route("/<int:receipt_id>/approve", methods=["POST"])
@require_auth
def approve_receipt(receipt_id):
    """Approve a review receipt using edited or stored OCR payload."""
    from src.backend.initialize_database_schema import TelegramReceipt
    from src.backend.extract_receipt_data import _save_to_database, classify_receipt_data

    session = g.db_session
    record = (
        session.query(TelegramReceipt)
        .filter(
            (TelegramReceipt.purchase_id == receipt_id) |
            (TelegramReceipt.id == receipt_id)
        )
        .order_by(TelegramReceipt.created_at.desc())
        .first()
    )
    if not record:
        return jsonify({"error": "Receipt not found"}), 404
    if record.purchase_id:
        return jsonify({"error": "Receipt is already approved", "purchase_id": record.purchase_id}), 409

    payload = request.get_json(silent=True) or {}
    ocr_data = payload.get("data") or _parse_raw_ocr_json(record.raw_ocr_json)
    if not isinstance(ocr_data, dict):
        return jsonify({"error": "No OCR data available for review approval"}), 400

    missing = [field for field in ("store", "date", "items", "total") if not ocr_data.get(field)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    if not isinstance(ocr_data.get("items"), list) or not ocr_data["items"]:
        return jsonify({"error": "At least one receipt item is required"}), 400

    current_user = getattr(g, "current_user", None)
    user_id = current_user.id if current_user else None
    receipt_type = payload.get("receipt_type") or record.receipt_type or classify_receipt_data(ocr_data)
    purchase_id = _save_to_database(
        ocr_data,
        record.ocr_engine or "manual_review",
        record.image_path,
        user_id,
        receipt_type,
    )

    record.purchase_id = purchase_id
    record.status = "processed"
    record.receipt_type = receipt_type
    record.raw_ocr_json = json.dumps(ocr_data)
    session.commit()

    return jsonify({
        "status": "processed",
        "purchase_id": purchase_id,
        "receipt_id": record.id,
        "receipt_type": receipt_type,
    }), 200


@receipts_bp.route("/<int:receipt_id>/reprocess", methods=["POST"])
@require_auth
def reprocess_receipt(receipt_id):
    """Re-run OCR for an existing stored receipt and update its review payload."""
    from src.backend.initialize_database_schema import TelegramReceipt
    from src.backend.extract_receipt_data import process_receipt

    session = g.db_session
    record = (
        session.query(TelegramReceipt)
        .filter(
            (TelegramReceipt.purchase_id == receipt_id) |
            (TelegramReceipt.id == receipt_id)
        )
        .order_by(TelegramReceipt.created_at.desc())
        .first()
    )
    if not record or not record.image_path:
        return jsonify({"error": "Receipt not found"}), 404

    current_user = getattr(g, "current_user", None)
    user_id = current_user.id if current_user else None
    result = process_receipt(
        image_path=record.image_path,
        source="review",
        user_id=user_id,
        receipt_record_id=record.id,
    )

    return jsonify(result), 200
