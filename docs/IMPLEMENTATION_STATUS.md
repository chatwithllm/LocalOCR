# Implementation Status

> Use this file as the current restart point for the project. It summarizes what is done, what is verified working, what is partial, and what should happen next on a new machine.

## Current Snapshot

- Backend is running on port `8080`
- Web dashboard is served by Flask at `/` and `/dashboard`
- Receipt upload works through the authenticated `/receipts/upload` endpoint for images and PDFs
- Gemini OCR is working with the current `google-genai` SDK and `gemini-2.5-flash`
- PDF receipts now use both image rendering and PDF text-layer extraction so summary fields like date and total can be recovered more reliably
- Docker Compose is configured as the primary app runtime with restart policies for backend, MQTT, and Ollama
- SQLite is being used locally with WAL mode enabled
- The repo is not production-finished yet, but it is in a usable development state

## Verified Working

These flows were manually verified in the current environment:

- `GET /health`
- Web dashboard loads on port `8080`
- Products tab:
  list, search, create, delete
- Inventory tab:
  list, add, consume, delete
- Budget tab:
  set monthly budget, read budget status
- Analytics tab:
  frontend now matches the backend response shape
- Recommendations tab:
  endpoint and UI load correctly; can be empty if there is not enough history
- Upload Receipt tab:
  authenticated upload works for images and PDFs and renders OCR results
- Gemini OCR:
  verified directly and through the live upload path
- Receipts tab:
  supports image preview, PDF viewing, OCR re-run, and review approval
- Telegram PDF flow:
  verified end to end from the real bot chat, including confirm-before-process
- Verified real PDF extraction result:
  `COSTCO WHOLESALE`, `2026-03-30`, total `478.42`, `36` items, classified as `grocery`

## Completed Implementation Areas

### Foundation

- Flask app factory exists and registers the main blueprints
- `.env` is auto-loaded for local development runs
- SQLite schema exists and is initialized through SQLAlchemy
- Bearer-token auth is enabled for application endpoints

### OCR Pipeline

- Direct receipt upload endpoint is implemented
- Gemini OCR is implemented and migrated to `google-genai`
- OpenAI OCR fallback code exists
- Ollama OCR fallback code exists
- Hybrid receipt processing persists purchases, items, price history, and inventory updates
- PDF summary extraction can be recovered from the PDF text layer when Gemini misses header/footer fields
- Telegram webhook handler is implemented
- Telegram confirmation flow is implemented before OCR begins
- Telegram webhook registration/status helper is implemented
- Review receipts now persist raw OCR data and can be approved from the web app
- Operator-focused Docker setup guide exists for non-developer deployment

### Core App Features

- Product catalog CRUD endpoints exist
- Inventory CRUD endpoints exist
- Budget endpoints exist
- Analytics endpoints exist
- Recommendations endpoint exists
- Frontend tabs for dashboard, inventory, products, upload, budget, analytics, recommendations, and settings are wired to the current backend responses

## Partial / In Progress

These areas exist but are not fully validated or fully complete:

- Nginx Proxy Manager / public webhook routing
- Home Assistant dashboard and automations
- MQTT end-to-end validation in a real Home Assistant setup
- Daily recommendation scheduler validation
- Backup and restore validation on a clean machine
- Alembic migration workflow
- Automated end-to-end test coverage
- Real bot validation for Telegram photo receipts
- Rich browser-level validation of the review editor UI beyond manual smoke use

## Known Gaps

- The app has working manual smoke coverage, but not a recent full automated verification run
- Some modules are still more “implemented enough for use” than “fully polished”
- The Home Assistant configuration files are present, but not validated as part of the latest work
- PDF conversion depends on `pdftoppm` being present; Docker now installs it, and local hosts need Poppler installed too
- Dense PDFs may still produce imperfect product names/categories even when summary fields are now recovered correctly

## Recommended Next Steps

1. Run a clean-machine setup using this repo plus `.env.example`
2. Validate `docker-compose up -d` from scratch
3. Run the receipt upload flow against Gemini on the fresh environment
4. Validate MQTT publishing with a real broker/Home Assistant consumer
5. Test the Telegram confirmation flow with a real photo receipt
6. Add or refresh automated tests for products, inventory, upload, and analytics

## Fresh Start Checklist

```bash
git clone <your-repo-url>
cd "Inventory Management"
cp .env.example .env
```

Set at least:

```bash
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
INITIAL_ADMIN_TOKEN=...
```

Then start with one of:

### Docker

```bash
docker-compose up -d
curl http://localhost:8080/health
```

### Local Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.backend.create_flask_application
```

## Files To Read First On Resume

- `README.md`
- `CONTINUITY.md`
- `docs/IMPLEMENTATION_STATUS.md`
- `docs/API_REFERENCE.md`
- `src/backend/create_flask_application.py`
- `src/frontend/index.html`

## Important Notes

- Do not commit `.env` or any real secrets
- `GEMINI_MODEL` is now configurable and defaults to `gemini-2.5-flash`
- The current upload response shape includes OCR data under `data`
- Inventory responses return an `inventory` array, not `items`
