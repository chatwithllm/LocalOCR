"""
Step 5: Create Stub Receipt Upload Endpoint
============================================
PROMPT Reference: Phase 1, Step 5

Provides POST /receipts/upload endpoint that accepts image files directly.
Enables testing the OCR → inventory pipeline without Telegram/Nginx/SSL.
Also serves as the Home Assistant upload channel long-term.

Auth: Bearer token required
"""

import os
import logging
from pathlib import Path
from uuid import uuid4
from datetime import datetime

from flask import Blueprint, request, jsonify, g

logger = logging.getLogger(__name__)

receipts_bp = Blueprint("receipts", __name__, url_prefix="/receipts")

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


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


@receipts_bp.route("/upload", methods=["POST"])
def upload_receipt():
    """Upload a receipt image for OCR processing.

    Accepts multipart/form-data with an 'image' file field.
    Routes to the hybrid OCR processor (extract_receipt_data.py).

    Returns:
        JSON with extracted receipt data or error message.
    """
    from src.backend.create_flask_application import require_auth

    # Validate file presence
    if "image" not in request.files:
        return jsonify({"error": "No image file provided. Use 'image' field."}), 400

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
        logger.info(f"Receipt image saved: {save_path}")
    except Exception as e:
        logger.error(f"Failed to save receipt image: {e}")
        return jsonify({"error": "Failed to save image"}), 500

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
def get_receipt(receipt_id):
    """Retrieve details for a specific receipt/purchase."""
    from src.backend.create_flask_application import require_auth
    from src.backend.initialize_database_schema import Purchase, ReceiptItem, Store

    session = g.db_session
    purchase = session.query(Purchase).filter_by(id=receipt_id).first()
    if not purchase:
        return jsonify({"error": "Receipt not found"}), 404

    store = session.query(Store).filter_by(id=purchase.store_id).first()
    items = session.query(ReceiptItem).filter_by(purchase_id=purchase.id).all()

    return jsonify({
        "id": purchase.id,
        "store": store.name if store else None,
        "total": purchase.total_amount,
        "date": purchase.date.strftime("%Y-%m-%d") if purchase.date else None,
        "items": [
            {
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "extracted_by": item.extracted_by,
            }
            for item in items
        ],
    }), 200
