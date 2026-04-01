"""
Step 12: Handle Receipt Image Processing
==========================================
PROMPT Reference: Phase 3, Step 12

Manages receipt image storage, thumbnails, duplicate detection, and
retention policy cleanup. Images stored at /data/receipts/{year}/{month}/.

Retention: 12 months by default (configurable via RECEIPT_RETENTION_MONTHS)
Cleanup: Weekly scheduled job deletes old images, preserves DB records
"""

import os
import hashlib
import logging
from uuid import uuid4
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

RECEIPTS_DIR = "/data/receipts"
RETENTION_MONTHS = int(os.getenv("RECEIPT_RETENTION_MONTHS", "12"))


def save_receipt_image(image_path: str, source: str = "upload") -> dict:
    """Save a receipt image with organized directory structure.

    Args:
        image_path: Path to the original image file.
        source: "telegram" or "upload"

    Returns:
        Dict with saved file metadata.
    """
    # TODO: Implement
    # - Generate UUID + timestamp filename
    # - Organize: /data/receipts/{year}/{month}/{filename}
    # - Create thumbnail (compressed for Home Assistant UI)
    # - Check for duplicates via hash
    # - Associate with receipt record in database
    logger.warning("save_receipt_image not yet implemented")
    return {"status": "not_implemented", "path": image_path}


def generate_thumbnail(image_path: str, max_size: tuple = (400, 400)) -> str:
    """Create a compressed thumbnail for Home Assistant UI."""
    # TODO: Implement with Pillow
    # from PIL import Image
    # img = Image.open(image_path)
    # img.thumbnail(max_size)
    # thumb_path = image_path.replace(".", "_thumb.")
    # img.save(thumb_path, quality=70, optimize=True)
    # return thumb_path
    return ""


def detect_duplicate(image_path: str) -> bool:
    """Check if an identical image has already been processed (hash-based)."""
    # TODO: Implement
    # file_hash = _compute_file_hash(image_path)
    # Check DB for existing record with same hash
    return False


def _compute_file_hash(file_path: str) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def cleanup_old_images():
    """Delete receipt images older than retention period.

    Database records are preserved — only image files are deleted.
    Runs weekly via scheduler.
    """
    cutoff_date = datetime.now() - timedelta(days=RETENTION_MONTHS * 30)
    deleted_count = 0

    # TODO: Implement
    # Walk /data/receipts/ directories
    # For each file older than cutoff_date:
    #   - Delete file
    #   - Log deletion for audit trail
    #   - Increment deleted_count

    logger.info(f"Retention cleanup: deleted {deleted_count} images older than {cutoff_date.date()}")
    return deleted_count
