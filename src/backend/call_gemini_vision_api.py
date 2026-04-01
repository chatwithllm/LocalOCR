"""
Step 9: Integrate Gemini Vision API
=====================================
PROMPT Reference: Phase 3, Step 9

Primary OCR engine using Google Gemini Vision API. Extracts receipt data
from images and returns structured JSON. Persists usage counters to the
api_usage table for rate-limit tracking across container restarts.

Rate Limits: 60 req/min, 1.5M tokens/day (free tier)
Target Speed: <3 seconds per receipt
"""

import os
import json
import base64
import logging
from datetime import date, datetime, timezone

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ---------------------------------------------------------------------------
# OCR Prompt
# ---------------------------------------------------------------------------

RECEIPT_EXTRACTION_PROMPT = """
Analyze this receipt image and extract the following information as JSON:

{
    "store": "Store name",
    "store_location": "Store address if visible",
    "date": "YYYY-MM-DD",
    "time": "HH:MM if visible",
    "items": [
        {
            "name": "Product name",
            "quantity": 1,
            "unit_price": 0.00,
            "category": "Category (dairy, produce, meat, bakery, beverages, snacks, household, other)"
        }
    ],
    "total": 0.00,
    "confidence": 0.95
}

Rules:
- Extract ALL items visible on the receipt
- Use the most specific product name visible
- If quantity is not clear, default to 1
- Confidence should reflect how readable the receipt is (0.0 to 1.0)
- If you cannot read a field, set it to null
- Return ONLY valid JSON, no markdown or explanation
"""


# ---------------------------------------------------------------------------
# Gemini OCR Function
# ---------------------------------------------------------------------------

def extract_receipt_via_gemini(image_path: str) -> dict:
    """Extract receipt data from an image using Google Gemini Vision API.

    Args:
        image_path: Path to the receipt image file.

    Returns:
        Dictionary with extracted receipt data, or error dict on failure.

    Raises:
        Exception: On API errors (caller should handle fallback to Ollama).
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not configured")

    # TODO: Implement Gemini API call
    # import google.generativeai as genai
    # genai.configure(api_key=GEMINI_API_KEY)
    # model = genai.GenerativeModel("gemini-1.5-flash")
    #
    # # Compress if >5MB
    # image_data = _load_and_compress_image(image_path)
    #
    # response = model.generate_content([RECEIPT_EXTRACTION_PROMPT, image_data])
    # result = json.loads(response.text)
    #
    # # Track usage
    # _track_api_usage(response.usage_metadata)
    #
    # return result

    logger.warning("Gemini OCR not yet implemented — returning placeholder")
    return {
        "error": "not_implemented",
        "message": "Gemini Vision API integration pending implementation"
    }


# ---------------------------------------------------------------------------
# Rate Limit Tracking (persisted to DB)
# ---------------------------------------------------------------------------

def _track_api_usage(usage_metadata):
    """Persist API usage counters to the api_usage table.

    Loads existing counters from DB on startup, increments per request,
    and warns when approaching limits (>80% of daily quota).
    """
    # TODO: Implement
    # session = get_db_session()
    # today = date.today()
    # usage = session.query(ApiUsage).filter_by(
    #     service_name="gemini", date=today
    # ).first()
    # if not usage:
    #     usage = ApiUsage(service_name="gemini", date=today)
    #     session.add(usage)
    # usage.request_count += 1
    # usage.token_count += usage_metadata.total_token_count
    # session.commit()
    #
    # # Warn at 80% of daily limits
    # if usage.request_count > 60 * 60 * 24 * 0.8:  # ~80% of daily req limit
    #     logger.warning("Gemini API approaching daily request limit!")
    # if usage.token_count > 1_500_000 * 0.8:
    #     logger.warning("Gemini API approaching daily token limit!")
    pass


def get_daily_usage() -> dict:
    """Get current day's Gemini API usage from the database."""
    # TODO: Query api_usage table for today's counters
    return {"service": "gemini", "date": str(date.today()), "requests": 0, "tokens": 0}


def _load_and_compress_image(image_path: str, max_size_mb: int = 5):
    """Load an image and compress if larger than max_size_mb."""
    # TODO: Implement with Pillow
    # from PIL import Image
    # img = Image.open(image_path)
    # file_size = os.path.getsize(image_path)
    # if file_size > max_size_mb * 1024 * 1024:
    #     img.thumbnail((1920, 1920))
    #     img.save(image_path, quality=85, optimize=True)
    pass


# ---------------------------------------------------------------------------
# Entry point for testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if not GEMINI_API_KEY:
        logger.error("Set GEMINI_API_KEY environment variable to test.")
    else:
        logger.info("Gemini Vision API module loaded. Ready for testing.")
