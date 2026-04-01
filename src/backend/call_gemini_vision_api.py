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
import logging
import mimetypes
from datetime import date, datetime, timezone

from google import genai
from flask import has_app_context
from google.genai import types
from PIL import Image

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# ---------------------------------------------------------------------------
# OCR Prompt
# ---------------------------------------------------------------------------

RECEIPT_EXTRACTION_PROMPT = """
Analyze this receipt image and extract the following information as JSON.
Return ONLY the raw JSON object — no markdown, no code fences, no explanation.

{
    "store": "Store name",
    "store_location": "Store address if visible, or null",
    "date": "YYYY-MM-DD",
    "time": "HH:MM or null",
    "items": [
        {
            "name": "Product name (be specific, e.g. 'Organic Whole Milk 1 Gal' not just 'Milk')",
            "quantity": 1,
            "unit_price": 0.00,
            "category": "one of: dairy, produce, meat, seafood, bakery, beverages, snacks, frozen, canned, condiments, household, personal_care, other"
        }
    ],
    "subtotal": 0.00,
    "tax": 0.00,
    "total": 0.00,
    "confidence": 0.95
}

Rules:
- Extract ALL line items visible on the receipt
- Use the most specific product name visible on the receipt
- If quantity is not explicitly shown, default to 1
- For BOGO or discount lines, include them as separate items with unit_price = 0.00 or the discounted price
- Confidence should reflect overall receipt readability (0.0 to 1.0)
- If you cannot read a field clearly, set it to null
- Return ONLY valid JSON
"""

# ---------------------------------------------------------------------------
# Gemini OCR Function
# ---------------------------------------------------------------------------

def extract_receipt_via_gemini(image_path: str) -> dict:
    """Extract receipt data from an image using Google Gemini Vision API.

    Args:
        image_path: Path to the receipt image file.

    Returns:
        Dictionary with extracted receipt data.

    Raises:
        ValueError: If GEMINI_API_KEY is not configured.
        Exception: On API errors (caller should handle fallback to Ollama).
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not configured")

    # Load and compress image if needed
    image_bytes, mime_type = _load_and_compress_image(image_path)

    # Call Gemini
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            RECEIPT_EXTRACTION_PROMPT,
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        ],
        config=types.GenerateContentConfig(
            temperature=0.1,  # Low temp for structured extraction
            max_output_tokens=4096,
        ),
    )

    # Track API usage
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        _track_api_usage(response.usage_metadata)

    # Parse JSON from response
    text = response.text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3].strip()
        if text.startswith("json"):
            text = text[4:].strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Gemini returned invalid JSON: {e}\nRaw: {text[:500]}")
        raise ValueError(f"Gemini OCR returned invalid JSON: {e}")

    # Validate required fields
    result.setdefault("confidence", 0.85)
    result.setdefault("items", [])
    result.setdefault("total", 0.0)

    logger.info(
        f"Gemini OCR: {result.get('store', '?')} | "
        f"${result.get('total', 0):.2f} | "
        f"{len(result.get('items', []))} items | "
        f"confidence: {result.get('confidence', 0):.2f} | "
        f"model: {GEMINI_MODEL}"
    )

    return result


# ---------------------------------------------------------------------------
# Rate Limit Tracking (persisted to DB)
# ---------------------------------------------------------------------------

def _track_api_usage(usage_metadata):
    """Persist API usage counters to the api_usage table."""
    if not has_app_context():
        logger.debug("Skipping Gemini API usage tracking outside Flask app context.")
        return

    try:
        from flask import g
        session = g.db_session

        from src.backend.initialize_database_schema import ApiUsage
        today = date.today()

        usage = session.query(ApiUsage).filter_by(
            service_name="gemini", date=today
        ).first()

        if not usage:
            usage = ApiUsage(service_name="gemini", date=today, request_count=0, token_count=0)
            session.add(usage)

        usage.request_count += 1
        if hasattr(usage_metadata, "total_token_count"):
            usage.token_count += usage_metadata.total_token_count

        session.commit()

        # Warn at 80% of daily limits
        if usage.token_count > 1_200_000:  # 80% of 1.5M
            logger.warning(f"Gemini API approaching daily token limit! ({usage.token_count:,} tokens used)")
        if usage.request_count > 69_120:  # 80% of 60/min * 60 * 24
            logger.warning(f"Gemini API approaching daily request limit! ({usage.request_count:,} requests)")

    except Exception as e:
        # Don't let tracking failures break OCR
        logger.warning(f"Failed to track Gemini API usage: {e}")


def get_daily_usage() -> dict:
    """Get current day's Gemini API usage from the database."""
    if not has_app_context():
        return {"service": "gemini", "date": str(date.today()), "requests": 0, "tokens": 0}

    try:
        from flask import g
        from src.backend.initialize_database_schema import ApiUsage
        session = g.db_session
        today = date.today()
        usage = session.query(ApiUsage).filter_by(service_name="gemini", date=today).first()
        if usage:
            return {
                "service": "gemini",
                "date": str(today),
                "requests": usage.request_count,
                "tokens": usage.token_count,
            }
    except Exception:
        pass
    return {"service": "gemini", "date": str(date.today()), "requests": 0, "tokens": 0}


def _load_and_compress_image(image_path: str, max_size_mb: int = 5) -> tuple[bytes, str]:
    """Load an image and compress if larger than max_size_mb."""
    img = Image.open(image_path)

    # Convert RGBA to RGB if needed
    if img.mode == "RGBA":
        img = img.convert("RGB")

    # Compress if file too large
    file_size = os.path.getsize(image_path)
    if file_size > max_size_mb * 1024 * 1024:
        img.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
        logger.info(f"Compressed image from {file_size / 1024 / 1024:.1f}MB")
        img_format = "JPEG"
    else:
        img_format = img.format or "PNG"

    mime_type = mimetypes.guess_type(image_path)[0]
    if img_format == "JPEG":
        mime_type = "image/jpeg"
    elif not mime_type:
        mime_type = "image/png"

    from io import BytesIO

    buffer = BytesIO()
    save_kwargs = {"format": img_format}
    if img_format == "JPEG":
        save_kwargs["quality"] = 90
    img.save(buffer, **save_kwargs)
    return buffer.getvalue(), mime_type


# ---------------------------------------------------------------------------
# Entry point for testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    if not GEMINI_API_KEY:
        logger.error("Set GEMINI_API_KEY environment variable to test.")
        sys.exit(1)
    if len(sys.argv) < 2:
        logger.error("Usage: python call_gemini_vision_api.py <image_path>")
        sys.exit(1)
    result = extract_receipt_via_gemini(sys.argv[1])
    print(json.dumps(result, indent=2))
