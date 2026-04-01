"""
Step 10: Integrate Ollama LLaVA Fallback
=========================================
PROMPT Reference: Phase 3, Step 10

Fallback OCR engine using self-hosted Ollama with LLaVA model.
Triggered when Gemini is rate-limited or returns errors.
No rate limits — always available as long as Ollama container is running.

Endpoint: http://ollama:11434/api/generate
Target Speed: <15 seconds per receipt
Model: llava:7b
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
Analyze this receipt image and extract the following information as JSON.
Return ONLY the raw JSON object — no markdown, no code fences, no explanation.

{
    "store": "Store name",
    "store_location": "Store address if visible, or null",
    "date": "YYYY-MM-DD",
    "time": "HH:MM or null",
    "items": [
        {
            "name": "Product name",
            "quantity": 1,
            "unit_price": 0.00,
            "category": "one of: dairy, produce, meat, seafood, bakery, beverages, snacks, frozen, canned, condiments, household, personal_care, other"
        }
    ],
    "subtotal": 0.00,
    "tax": 0.00,
    "total": 0.00,
    "confidence": 0.85
}

Rules:
- Extract ALL line items visible on the receipt
- Use the most specific product name visible
- If quantity is not clear, default to 1
- Confidence should reflect receipt readability (0.0 to 1.0)
- If you cannot read a field, set it to null
- Return ONLY valid JSON
"""


# ---------------------------------------------------------------------------
# Ollama OCR Function
# ---------------------------------------------------------------------------

def extract_receipt_via_ollama(image_path: str) -> dict:
    """Extract receipt data from an image using Ollama LLaVA.

    Args:
        image_path: Path to the receipt image file.

    Returns:
        Dictionary with extracted receipt data.

    Raises:
        Exception: On API errors or connection failures.
    """
    # Read and encode image as base64
    with open(image_path, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "model": "llava:7b",
        "prompt": RECEIPT_EXTRACTION_PROMPT,
        "images": [image_base64],
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 4096,
        },
    }

    logger.info("Sending receipt to Ollama LLaVA for OCR...")

    response = requests.post(
        f"{OLLAMA_ENDPOINT}/api/generate",
        json=payload,
        timeout=60,  # Ollama can be slow (5-15 sec)
    )
    response.raise_for_status()

    result_text = response.json().get("response", "")

    # Strip markdown code fences if present
    text = result_text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3].strip()
        if text.startswith("json"):
            text = text[4:].strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Ollama returned invalid JSON: {e}\nRaw: {text[:500]}")
        raise ValueError(f"Ollama OCR returned invalid JSON: {e}")

    # Defaults
    result.setdefault("confidence", 0.75)
    result.setdefault("items", [])
    result.setdefault("total", 0.0)

    logger.info(
        f"Ollama OCR: {result.get('store', '?')} | "
        f"${result.get('total', 0):.2f} | "
        f"{len(result.get('items', []))} items | "
        f"confidence: {result.get('confidence', 0):.2f}"
    )

    return result


def check_ollama_health() -> bool:
    """Check if Ollama service is running and responsive."""
    try:
        response = requests.get(f"{OLLAMA_ENDPOINT}/api/tags", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


def is_model_available(model_name: str = "llava:7b") -> bool:
    """Check if a specific model is downloaded in Ollama."""
    try:
        response = requests.get(f"{OLLAMA_ENDPOINT}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return any(m.get("name", "").startswith(model_name.split(":")[0])
                       for m in models)
    except requests.RequestException:
        pass
    return False


def pull_llava_model():
    """Pull the LLaVA model if not already downloaded."""
    if is_model_available():
        logger.info("LLaVA model already available.")
        return True

    logger.info("Pulling LLaVA model (this may take several minutes)...")
    try:
        response = requests.post(
            f"{OLLAMA_ENDPOINT}/api/pull",
            json={"name": "llava:7b"},
            timeout=600,  # Model download can take minutes
            stream=True,
        )
        response.raise_for_status()
        for line in response.iter_lines():
            if line:
                status = json.loads(line).get("status", "")
                if "pulling" in status or "success" in status:
                    logger.info(f"  Ollama: {status}")
        logger.info("LLaVA model pulled successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to pull LLaVA model: {e}")
        return False


# ---------------------------------------------------------------------------
# Entry point for testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    healthy = check_ollama_health()
    logger.info(f"Ollama health: {'✅ OK' if healthy else '❌ FAILED'}")

    model_ready = is_model_available()
    logger.info(f"LLaVA model: {'✅ Available' if model_ready else '❌ Not downloaded'}")

    if len(sys.argv) >= 2 and healthy and model_ready:
        result = extract_receipt_via_ollama(sys.argv[1])
        print(json.dumps(result, indent=2))
