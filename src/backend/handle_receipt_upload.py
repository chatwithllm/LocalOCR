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
from uuid import uuid4
from datetime import datetime

from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

receipts_bp = Blueprint("receipts", __name__, url_prefix="/receipts")


@receipts_bp.route("/upload", methods=["POST"])
def upload_receipt():
    """Upload a receipt image for OCR processing.

    Accepts multipart/form-data with an 'image' file field.
    Routes to the hybrid OCR processor (extract_receipt_data.py).

    Returns:
        JSON with extracted receipt data or error message.
    """
    # TODO: Add @require_auth decorator once auth middleware is wired up

    # Validate file presence
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    image_file = request.files["image"]
    if image_file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    # Validate file type
    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
    ext = os.path.splitext(image_file.filename)[1].lower()
    if ext not in allowed_extensions:
        return jsonify({"error": f"Unsupported file type: {ext}"}), 400

    # Save to receipts directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{uuid4().hex[:8]}{ext}"
    year_month = datetime.now().strftime("%Y/%m")
    save_dir = f"/data/receipts/{year_month}"
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, filename)

    try:
        image_file.save(save_path)
        logger.info(f"Receipt image saved: {save_path}")
    except Exception as e:
        logger.error(f"Failed to save receipt image: {e}")
        return jsonify({"error": "Failed to save image"}), 500

    # TODO: Route to OCR processor
    # from src.backend.extract_receipt_data import process_receipt
    # result = process_receipt(save_path)
    # return jsonify(result), 200

    return jsonify({
        "status": "received",
        "message": "Receipt uploaded successfully. OCR processing not yet implemented.",
        "image_path": save_path,
        "filename": filename,
    }), 202


@receipts_bp.route("/<int:receipt_id>", methods=["GET"])
def get_receipt(receipt_id):
    """Retrieve details for a specific receipt."""
    # TODO: Implement receipt retrieval from database
    return jsonify({"error": "Not yet implemented", "receipt_id": receipt_id}), 501
