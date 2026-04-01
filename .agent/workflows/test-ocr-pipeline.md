---
description: Test the OCR pipeline by uploading a receipt image
---

# Test OCR Pipeline

## Prerequisites
- Docker Compose stack running (`docker-compose ps` shows all healthy)
- `GEMINI_API_KEY` set in `.env`
- A receipt image file (JPEG, PNG, or WebP)

## Steps

// turbo
1. Verify backend is healthy
```bash
curl http://localhost:8080/health
```

2. Upload a receipt image via the stub endpoint
```bash
curl -X POST http://localhost:8080/receipts/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "image=@/path/to/receipt.jpg" \
  -v
```

3. Check the response:
   - **202 Accepted** — image saved, OCR processing triggered
   - **200 OK** — OCR complete, check extracted data
   - **400 Bad Request** — invalid file or missing image
   - **401 Unauthorized** — invalid or missing Bearer token

4. Verify the image was saved:
```bash
docker exec grocery-backend ls -la /data/receipts/
```

5. Check backend logs for OCR processing:
```bash
docker-compose logs --tail=50 backend
```

6. Test Gemini OCR directly (if implemented):
```bash
docker exec grocery-backend python -c "
from src.backend.call_gemini_vision_api import extract_receipt_via_gemini
result = extract_receipt_via_gemini('/data/receipts/YOUR_IMAGE.jpg')
print(result)
"
```

7. Test Ollama fallback (if implemented):
```bash
docker exec grocery-backend python -c "
from src.backend.call_ollama_vision_api import check_ollama_health
print('Ollama healthy:', check_ollama_health())
"
```

## Expected Output

Successful OCR should return JSON like:
```json
{
  "store": "Whole Foods",
  "date": "2026-04-01",
  "items": [
    {"name": "Organic Milk", "quantity": 1, "unit_price": 3.20, "category": "dairy"}
  ],
  "total": 45.67,
  "confidence": 0.92
}
```

## Troubleshooting
- **Gemini 429 error** → Rate limited, should fall back to Ollama
- **Ollama timeout** → Model may not be pulled. Run: `docker exec grocery-ollama ollama pull llava:7b`
- **Low confidence (<0.40)** → Receipt image may be blurry, try a clearer photo
