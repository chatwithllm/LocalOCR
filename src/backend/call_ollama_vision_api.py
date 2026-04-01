"""
Step 10: Integrate Ollama LLaVA Fallback
=========================================
PROMPT Reference: Phase 3, Step 10

Fallback OCR engine using self-hosted Ollama with LLaVA model.
Triggered when Gemini is rate-limited or returns errors.
No rate limits — always available as long as Ollama container is running.

Endpoint: http://ollama:11434/api/generate
Target Speed: <15 seconds per receipt
Model: llava:7b-v1.5-quantized (~2GB)
"""

import os
import json
import base64
import logging

import requests

logger = logging.getLogger(__name__)

OLLAMA_ENDPOINT = os.getenv("OLLAMA_ENDPOINT", "http://ollama:11434")

# Same prompt as Gemini for consistent output format
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
    "confidence": 0.85
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
# Ollama OCR Function
# ---------------------------------------------------------------------------

def extract_receipt_via_ollama(image_path: str) -> dict:
    """Extract receipt data from an image using Ollama LLaVA.

    Args:
        image_path: Path to the receipt image file.

    Returns:
        Dictionary with extracted receipt data, or error dict on failure.
    """
    # TODO: Implement Ollama API call
    # # Read and encode image as base64
    # with open(image_path, "rb") as f:
    #     image_base64 = base64.b64encode(f.read()).decode("utf-8")
    #
    # payload = {
    #     "model": "llava:7b",
    #     "prompt": RECEIPT_EXTRACTION_PROMPT,
    #     "images": [image_base64],
    #     "stream": False,
    # }
    #
    # response = requests.post(
    #     f"{OLLAMA_ENDPOINT}/api/generate",
    #     json=payload,
    #     timeout=30,
    # )
    # response.raise_for_status()
    #
    # result_text = response.json().get("response", "")
    # return json.loads(result_text)

    logger.warning("Ollama OCR not yet implemented — returning placeholder")
    return {
        "error": "not_implemented",
        "message": "Ollama LLaVA integration pending implementation"
    }


def check_ollama_health() -> bool:
    """Check if Ollama service is running and responsive."""
    try:
        response = requests.get(f"{OLLAMA_ENDPOINT}/api/tags", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


def pull_llava_model():
    """Pull the LLaVA model if not already downloaded."""
    # TODO: Implement
    # response = requests.post(
    #     f"{OLLAMA_ENDPOINT}/api/pull",
    #     json={"name": "llava:7b"},
    #     timeout=600,  # Model download can take minutes
    # )
    logger.info("TODO: Pull LLaVA model via Ollama API")


# ---------------------------------------------------------------------------
# Entry point for testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    healthy = check_ollama_health()
    logger.info(f"Ollama health check: {'✅ OK' if healthy else '❌ FAILED'}")
