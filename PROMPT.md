# Implementation Prompt: Grocery Inventory & Savings Management System

**Document Version:** 1.0  
**Created:** 2026-04-01  
**Purpose:** Guide implementation team through all phases  
**Tech Stack:** Python Flask, SQLite, MQTT, Gemini API, Ollama, Docker Compose, Home Assistant

---

## Overview

You are implementing a **privacy-first grocery management system** enabling households to:
1. Upload receipts via **Telegram bot** (primary) or Home Assistant (backup)
2. Process receipts with **hybrid OCR** (Gemini + Ollama fallback)
3. Maintain **real-time shared inventory** across devices (MQTT sync)
4. Get **smart recommendations** (deals + seasonal)
5. Track **spending & savings** via Home Assistant dashboard
6. Deploy anywhere via **Docker Compose** (fully portable)

**All Python files follow naming convention: Verb + Noun (human-readable)**

Example: `extract_receipt_data.py` (not `ocr.py`), `handle_telegram_messages.py` (not `telegram_handler.py`)

---

## Phase 1: Foundation & Infrastructure

> **⚠️ Docker-first development:** Phase 1 establishes the Docker Compose stack as the very first step. All subsequent development and testing happens inside containers to avoid "works on my machine" issues at deployment time.

### Step 1: Create Docker Compose Stack

**File:** `docker-compose.yml`

**What to do:**
- Define services:
  - `backend` (Flask app from `src/backend/`, port 8080)
  - `mqtt` (Mosquitto MQTT broker, port 1883)
  - `ollama` (LLaVA model, port 11434)
- Define volumes: `/data/db`, `/data/receipts`, `/data/ollama`, `/data/backups`
- Environment variables: `.env` file (GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, etc.)
- Networks: internal (services communicate) + bridge (external access via NPM)
- Create `Dockerfile` for backend service with Python dependencies

**Key considerations:**
- Data persistence (volumes survive container restarts)
- Environment variables secure (not in git)
- Health checks for critical services
- Resource limits (Ollama memory-intensive)
- SQLite database lives on a volume (`/data/db`), not inside the container filesystem

**Testing:**
- `docker-compose up` → all services start
- Verify backend accessible at `http://localhost:8080`
- Verify MQTT accessible at `localhost:1883`
- Verify Ollama accessible at `http://localhost:11434`

---

### Step 2: Initialize Database Schema

**File:** `src/backend/initialize_database_schema.py`

**What to do:**
- Create SQLite database at `/data/db/grocery.db` (Docker volume)
- **Enable WAL (Write-Ahead Logging) mode** on database connection (`PRAGMA journal_mode=WAL`) to support concurrent reads + single writer without locking errors
- Define tables with correct schema (see PRD section 4.2), including:
  - `api_token_hash` field on `users` table (for Bearer token auth)
  - `api_usage` table (service_name, date, request_count, token_count) for persisting Gemini rate-limit tracking
- Add indexes on frequently queried columns (product_id, user_id, date)
- Include constraints (foreign keys, unique constraints where needed)
- **Setup Alembic** for schema migrations:
  - Initialize Alembic config (`alembic init`)
  - Create initial migration from current schema
  - Future schema changes go through `alembic revision --autogenerate` + `alembic upgrade head`

**Key considerations:**
- Use SQLAlchemy ORM (required for Alembic integration)
- WAL mode must be set on every new connection (use SQLAlchemy `event.listen` on `connect`)
- Ensure schema supports multi-user (user_id fields)
- Add created_at, updated_at timestamps to all tables
- Test on fresh database (verify schema creation works)

---

### Step 3: Setup Flask Backend API

**File:** `src/backend/create_flask_application.py`

**What to do:**
- Initialize Flask app with blueprint structure
- Configure logging (standard Python logging)
- Setup error handling (400, 401, 403, 404, 500 responses)
- **Implement API authentication middleware:**
  - Require `Authorization: Bearer <token>` header on all endpoints
  - Validate token against hashed tokens in `users` table
  - Exempt `/telegram/webhook` (uses Telegram signature validation instead)
  - Return 401 Unauthorized for missing/invalid tokens
- Define blueprint routes: `telegram_bp`, `products_bp`, `inventory_bp`, `receipts_bp`, `analytics_bp`
- Configure CORS if needed
- Port: 8080 (accessed via Nginx Proxy Manager)
- Database connection pooling (SQLAlchemy)

**Key endpoints to structure:**
- `/telegram/webhook` → handled by `handle_telegram_messages.py` (Telegram signature auth)
- `/products/*` → handled by `manage_product_catalog.py` (Bearer token auth)
- `/inventory/*` → handled by `manage_inventory.py` (Bearer token auth)
- `/receipts/*` → handled by `extract_receipt_data.py` (Bearer token auth)
- `/analytics/*` → handled by `calculate_spending_analytics.py` (Bearer token auth)

**Testing:**
- Test Flask app starts without errors
- Test all blueprints load
- Test 401 response for missing/invalid token
- Test 404 response for undefined routes
- Test authenticated request succeeds

---

### Step 4: Configure MQTT Broker Connection

**File:** `src/backend/setup_mqtt_connection.py`

**What to do:**
- Initialize Mosquitto MQTT client (use `paho-mqtt` library)
- Configure broker address: `mosquitto:1883` (Docker service name)
- Define topics:
  - `home/grocery/inventory/{product_id}` (inventory updates)
  - `home/grocery/alerts/low_stock` (low-stock alerts)
  - `home/grocery/recommendations/daily` (daily suggestions)
- Setup callbacks for connect, disconnect, message events
- Implement reconnection logic (auto-reconnect if broker unavailable)
- Test connection by sending test message

**Key considerations:**
- Non-blocking publish (async if heavy load)
- Message payload: JSON format
- QoS: 1 (at least once delivery)
- Retain flag: True for inventory state (so Home Assistant sees last state on reconnect)

**Testing:**
- Connect to MQTT broker successfully
- Publish & subscribe to topics
- Verify message format

---

### Step 5: Create Stub Receipt Upload Endpoint

**File:** `src/backend/handle_receipt_upload.py`

**What to do:**
- Create a `POST /receipts/upload` endpoint that accepts an image file directly
- Save uploaded image to `/data/receipts/` (same path as Telegram receipts)
- Route to OCR processor (`extract_receipt_data.py`) — same pipeline as Telegram
- Return JSON response with extracted data or error
- **Purpose:** Enables testing the entire OCR → inventory pipeline without needing Telegram bot, Nginx Proxy Manager, domain, or SSL configured

**Key considerations:**
- Accepts `multipart/form-data` with image file
- Requires Bearer token authentication (like all non-Telegram endpoints)
- This endpoint remains useful long-term as the Home Assistant upload channel
- Same validation and error handling as the Telegram path

**Testing:**
- Upload a receipt image via `curl` → verify OCR processes it
- Verify inventory updates from stub upload match Telegram upload results
- Test with invalid/corrupt images → verify graceful error response

---

## Phase 2: Telegram Integration & Webhooks

> **Note:** Phase 2 can be deferred if Nginx Proxy Manager / domain / SSL is not yet configured. Use the stub upload endpoint (Step 5) to test OCR and inventory flows in the meantime.

### Step 6: Configure Telegram Bot Webhook

**File:** `src/backend/configure_telegram_webhook.py`

**What to do:**
- Read Telegram bot token from environment variable: `TELEGRAM_BOT_TOKEN`
- Set webhook URL: `https://your-domain.com/telegram/webhook`
- Use Telegram Bot API to register webhook: `setWebhook(url, certificate=None)`
- Implement bot commands: `/start`, `/help`, `/status`
- Test webhook reachability from Telegram servers

**Key considerations:**
- Webhook must be HTTPS (handled by Nginx Proxy Manager)
- Nginx Proxy Manager must route `/telegram/webhook` → backend:8080
- Bot token kept in `.env` file (never in git)
- Webhook validation (verify requests come from Telegram)

**Testing:**
- Send test message to bot → verify webhook receives it
- Check webhook status via Telegram API
- Test bot commands

---

### Step 7: Setup Nginx Proxy Manager Route

**⚠️ Prerequisite: Nginx Proxy Manager must already be running with a registered domain and valid SSL certificate.**

**Manual setup (via NPM UI - 5 minutes):**
1. Open Nginx Proxy Manager dashboard
2. Add Proxy Host:
   - Domain: your-domain.com
   - Forward to: localhost:8080
   - Enable SSL (Let's Encrypt)
3. Route `/telegram/webhook` → backend:8080
4. Save

**In documentation** (`docs/NGINX_PROXY_MANAGER_SETUP.md`):
- Step-by-step screenshots
- Troubleshooting common issues
- SSL renewal info

---

### Step 8: Implement Telegram Webhook Handler

**File:** `src/backend/handle_telegram_messages.py`

**What to do:**
- Create `/telegram/webhook` POST endpoint (Flask route)
- Validate Telegram webhook signature (security)
- Extract photo from Telegram update
- Download photo from Telegram CDN using `python-telegram-bot` library
- Save temporary file for OCR processing
- Route to OCR processor (`extract_receipt_data.py`)
- Send confirmation message back to Telegram user

**Telegram message handling:**
- Extract `chat_id` (for reply)
- Extract `photo` (latest resolution)
- Save photo to `/data/receipts/` directory
- Send processing status: "⏳ Processing receipt..."
- **On success:** Send confirmation: "✅ Processed: $X.XX at Store | Y items"
- **On low confidence (<80%):** Send warning: "⚠️ Low confidence — please review in Home Assistant"
- **On complete failure (both OCR engines fail):** Send error: "❌ Could not process receipt. Saved for manual review."

**Key considerations:**
- Handle multiple photo sizes from Telegram (use largest)
- Validate JSON payload signature
- Implement error handling (download failures, invalid messages)
- Timeout: 30 sec max for webhook response (Telegram requirement)
- **Always provide user feedback** — never leave the user without a response after uploading

**Testing:**
- Send receipt photo via Telegram bot
- Verify webhook receives update
- Verify bot sends confirmation message on success
- Verify bot sends error message on failure
- Verify bot sends warning on low confidence

---

## Phase 3: Hybrid OCR System

### Step 9: Integrate Gemini Vision API

**File:** `src/backend/call_gemini_vision_api.py`

**What to do:**
- Setup Google Gemini client (use `google-generativeai` library)
- Read API key from environment: `GEMINI_API_KEY`
- Implement function: `extract_receipt_via_gemini(image_path) → json_receipt`
- Prompt design: Extract receipt data from image and return as JSON with store, date, items[], total, confidence
- Handle rate limiting (60 req/min, 1.5M tokens/day)
- **Persist API usage counters** to `api_usage` table in SQLite (survives container restarts)
  - Track daily request count and token usage
  - Warn when approaching limits (>80% of daily quota)
  - Load counters from DB on startup (don't reset on restart)
- Implement retry logic with exponential backoff

**Key considerations:**
- Image preprocessing (compress if >5MB)
- Error handling (API errors, network issues)
- Confidence scoring (model provides confidence)
- Rate limit detection (429 response → trigger fallback)
- Usage tracking must be persistent — in-memory counters alone will lose state on restart

**Testing:**
- Test with 5 real receipts
- Verify JSON output format
- Test rate limit handling
- Verify usage counters persist across restarts
- Benchmark speed (target <3 sec)

---

### Step 10: Integrate Ollama LLaVA Fallback

**File:** `src/backend/call_ollama_vision_api.py`

**What to do:**
- Setup Ollama client (HTTP requests to localhost:11434)
- Pull LLaVA model on first run: `ollama pull llava:7b-v1.5-quantized` (~2GB)
- Implement function: `extract_receipt_via_ollama(image_path) → json_receipt`
- Use same JSON prompt as Gemini
- Handle local processing (may be slower 5-15 sec)

**Key considerations:**
- Ollama endpoint: `http://localhost:11434/api/generate`
- Image encoding (base64 for API)
- Streaming response handling
- Fallback reliability (no rate limits)

**Testing:**
- Test Ollama connection
- Test extraction with 5 receipts
- Verify JSON output format
- Benchmark speed (target <15 sec)

---

### Step 11: Implement Hybrid OCR Processor

**File:** `src/backend/extract_receipt_data.py`

**What to do:**
- Orchestrate Gemini + Ollama fallback logic
- Try Gemini first (fast, accurate)
- If Gemini fails (rate-limit, error) → use Ollama
- If Ollama fails → flag for manual review
- Validate JSON output (required fields)
- Auto-update inventory on success

**Fallback Logic:**
- Try Gemini → success? → return JSON
- If Gemini rate-limited (HTTP 429) → try Ollama
- If Gemini error (500) → try Ollama
- If Ollama success → return JSON
- If both fail → save for manual review

**Validation:**
- Check required fields: store, date, items[], total
- Validate data types (dates, numbers)
- Confidence score >0.40 (flag <0.40 for review) — aligned with scaled confidence formulas

**Key considerations:**
- Track which engine processed each receipt
- Log fallback triggers (for monitoring)
- Handle concurrent requests (queue if heavy load)
- **Always send Telegram feedback** (when triggered via Telegram) — success confirmation, low-confidence warning, or failure error (see Step 8)

**Testing:**
- Test Gemini path (normal case)
- Force rate limit → verify Ollama fallback
- Test invalid receipt image → verify manual review flag
- Test concurrent requests
- Verify Telegram user receives appropriate feedback for all outcomes

---

### Step 12: Handle Receipt Image Processing

**File:** `src/backend/save_receipt_images.py`

**What to do:**
- Save receipt images to `/data/receipts/` (Docker volume)
- Generate unique filenames (UUID + timestamp)
- Create thumbnails for Home Assistant UI (compress images)
- Clean up duplicates (hash-based detection)
- Associate image with receipt record in database
- **Implement retention policy:**
  - Default: 12 months (configurable via `RECEIPT_RETENTION_MONTHS` env var)
  - Scheduled cleanup job (weekly) deletes images older than retention period
  - Database records preserved (only image files deleted)
  - Log deletions for audit trail

**Key considerations:**
- File organization: `/data/receipts/{year}/{month}/{filename}`
- Compression: max 1MB per image
- Retention: configurable period (default 12 months), auto-cleanup to manage disk usage

**Testing:**
- Test image save & retrieval
- Verify thumbnail generation
- Test duplicate detection
- Test retention cleanup (verify old images deleted, DB records retained)

---

## Phase 4: Inventory Management *(parallelizable with Phases 5 & 6)*

> **💡 Phases 4, 5, and 6 are independent data consumers.** They all read from purchase/price history produced by Phase 3 but do not depend on each other. They can be built in parallel by different team members, or in any order.

### Step 13: Create Product Catalog Management

**File:** `src/backend/manage_product_catalog.py`

**What to do:**
- Implement CRUD endpoints:
  - `POST /products/create` → add new product
  - `GET /products` → list all products with pagination
  - `GET /products/search?q=milk` → search products
  - `PUT /products/{id}/update` → modify product
  - `DELETE /products/{id}` → remove product
- Support fields: name, category, barcode, average_price, stores
- Implement autocomplete/search (by name or barcode)

**Key considerations:**
- Handle duplicate products (check by name + category)
- Price tracking (update average_price)
- Store association (product sold at which stores)

**Testing:**
- Test CRUD operations
- Test search/autocomplete
- Test duplicate detection

---

### Step 14: Implement Inventory Tracking

**File:** `src/backend/manage_inventory.py`

**What to do:**
- Implement CRUD endpoints:
  - `GET /inventory` → list current inventory
  - `POST /inventory/add-item` → add product with quantity
  - `PUT /inventory/{id}/consume` → decrease quantity by 1
  - `PUT /inventory/{id}/update` → set quantity
  - `DELETE /inventory/{id}` → remove from inventory
- Track: product_id, quantity, location, last_updated, updated_by_user
- On every change: publish MQTT event `home/grocery/inventory/{product_id}`

**Key considerations:**
- Prevent negative quantities
- Track user who made change (for audit)
- Update timestamp automatically
- Publish MQTT with new state

**Testing:**
- Test add/consume/update/delete operations
- Verify MQTT events published
- Test multi-user concurrent updates (no conflicts)

---

### Step 15: Add Low-Stock Alert System

**File:** `src/backend/check_inventory_thresholds.py`

**What to do:**
- Implement threshold checking (run every 5 minutes via scheduler)
- Per-product configurable thresholds (stored in database)
- When quantity drops below threshold:
  - Publish MQTT alert: `home/grocery/alerts/low_stock`
  - Alert payload: `{product_id, product_name, current_qty, threshold}`
- Alert escalation (repeat every 24 hrs if not met)

**Alert examples:**
- Milk < 0.5L → alert
- Eggs < 6 → alert

**Key considerations:**
- Avoid duplicate alerts (track last alert time)
- 24-hour repeat interval
- User-configurable thresholds per product

**Testing:**
- Test threshold detection
- Verify MQTT alerts published
- Test escalation (repeat after 24 hrs)

---

## Phase 5: Smart Recommendations *(parallelizable with Phases 4 & 6)*

### Step 16: Build Recommendation Engine

**File:** `src/backend/generate_recommendations.py`

**What to do:**
- Implement recommendation logic:
  1. **Price deals:** current_price < avg_price * 0.9
  2. **Seasonal/recurring:** (today - last_purchase) > (avg_frequency * 1.2)
- Calculate confidence score (0.40 threshold)
- Return recommendations: `[{product_id, reason, confidence}]`

**Deal detection algorithm:**
- For each product:
  - prices = all prices in last 3 months (minimum 3 data points required)
  - avg_price = average(prices)
  - if current_price < avg_price * 0.9:
    - confidence = min((avg_price - current_price) / avg_price * 5, 1.0)
    - if confidence >= 0.40: return {product, reason: "deal", confidence}
  - Example: 15.8% discount → confidence = 0.79

**Seasonal detection algorithm:**
- For each product with purchase history:
  - purchase_dates = all dates product was purchased
  - if len(purchase_dates) >= 3:
    - avg_frequency = median(interval between purchases)
    - days_since_last = today - last_purchase_date
    - if days_since_last > avg_frequency * 1.2:
      - confidence = min((days_since_last / avg_frequency - 1.0) * 2.5, 1.0)
      - if confidence >= 0.40: return {product, reason: "seasonal", confidence}
  - Example: 6 days since last, avg 5 days → confidence = 0.50

**Testing:**
- Test deal detection (5 receipts with price variations)
- Test seasonal detection (products bought regularly)
- Verify confidence scores

---

### Step 17: Implement Daily Recommendation Push

**File:** `src/backend/schedule_daily_recommendations.py`

**What to do:**
- Setup scheduled task (8 AM daily, configurable)
- Generate recommendations for entire household
- Publish to MQTT: `home/grocery/recommendations/daily`
- Payload: `{timestamp, recommendations: [{product_id, reason, confidence}]}`

**Implementation options:**
- Use `APScheduler` library (simple)
- Or use Docker cron container

**Key considerations:**
- Configurable time via environment variable
- Handle multiple users (aggregate recommendations)
- Error handling (log failures, don't crash)

**Testing:**
- Test scheduled task triggers at specified time
- Verify MQTT payload format
- Test with multiple household members

---

## Phase 6: Analytics & Spending *(parallelizable with Phases 4 & 5)*

### Step 18: Calculate Spending Analytics

**File:** `src/backend/calculate_spending_analytics.py`

**What to do:**
- Implement analytics endpoints:
  - `GET /analytics/spending?period=monthly` → total spent by month
  - `GET /analytics/spending?category=dairy` → by category
  - `GET /analytics/price-history?product_id=1` → price trends
  - `GET /analytics/deals-captured?period=monthly` → savings from deals
- Calculate metrics:
  - Total amount
  - Average price per unit
  - Min/max prices
  - Deals captured (amount saved vs regular price)

**Key considerations:**
- Support multiple time periods (daily, weekly, monthly, yearly)
- Support filtering (category, store, user)
- Cache results (analytics queries can be heavy)

**Testing:**
- Test spending calculation (vs manual calculation)
- Test price trends (verify min/max correct)
- Test deals calculation (verify savings accurate)

---

### Step 19: Implement Budget Management

**File:** `src/backend/manage_household_budget.py`

**What to do:**
- Endpoints:
  - `POST /budget/set-monthly` → set budget for month
  - `GET /budget/status` → current month budget vs actual
  - Payload: `{month, budget_amount}`
- Calculate: % spent, remaining amount
- Trigger alert at 80% threshold (publish to MQTT)

**Key considerations:**
- Per-month budget (fresh each month)
- Alert when 80% spent (once per month)
- Support household-wide budget

**Testing:**
- Test budget setting & retrieval
- Test % calculation
- Test alert trigger at 80%

---

## Phase 7: Home Assistant Integration

### Step 20: Create MQTT Real-Time Sync Handler

**File:** `src/backend/publish_mqtt_events.py`

**What to do:**
- Every time data changes, publish MQTT event:
  - Inventory update → `home/grocery/inventory/{product_id}`
  - Alert → `home/grocery/alerts/low_stock`
  - Recommendation → `home/grocery/recommendations/daily`
- Payload: JSON with current state
- QoS: 1, Retain: True (Home Assistant sees last state)

**Example payloads:**
- Inventory: `{product_id, name, quantity, location, updated_by, timestamp}`
- Alert: `{product_id, name, current, threshold, alert_type}`
- Recommendation: `{product_id, name, reason, confidence, timestamp}`

**Key considerations:**
- Retain flag (Home Assistant can recover state on reconnect)
- JSON format (easy parsing in Home Assistant)
- Timestamped (for audit trail)

---

### Step 21: Build Home Assistant YAML Dashboard

**File:** `config/home_assistant_dashboard_config.yaml`

**What to do:**
- Create YAML-based Home Assistant dashboard (not custom card yet)
- Components:
  1. **Inventory Card** (list/grid of products)
  2. **Recommendations Card** (daily suggestions)
  3. **Alerts Card** (low-stock warnings)
  4. **Analytics Card** (spending charts)
  5. **Add Item Card** (manual entry)

**Key considerations:**
- Subscribe to MQTT topics
- Update on state change
- Mobile responsive (use auto layout)
- Click actions (navigate to product details)

**Testing:**
- Load dashboard in Home Assistant
- Verify all cards render
- Test click/button actions
- Test mobile responsiveness

---

### Step 22: Implement Home Assistant Automations

**File:** `config/home_assistant_automations.yaml`

**What to do:**
- Automation 1: Low-stock alert → notify household members
- Automation 2: Daily at 8 AM → push recommendations
- Automation 3: Budget threshold → alert
- Automation 4: Weekly summary

**Example automation:**
- Trigger: MQTT message on `home/grocery/alerts/low_stock`
- Action: Send notification to all family devices

---

## Phase 8: Backup & Portability

> **Note:** Docker Compose was set up in Phase 1 (Step 1). This phase focuses on backup/restore and production hardening.

### Step 23: Setup Backup & Restore System

**File:** `scripts/backup_database_and_volumes.sh`

**What to do:**
- Create daily backup script:
  - Backup SQLite database: `/data/db/grocery.db`
  - Backup receipt images: `/data/receipts/`
  - Backup MQTT config (if persistent)
  - Compress to `/data/backups/grocery_backup_$(date +%Y%m%d).tar.gz`
- Schedule via cron or Docker job
- Restore script: `scripts/restore_from_backup.sh`

**Key considerations:**
- Backup retention (keep 30 days)
- Compression (save space)
- Portability (can restore on different machine)

**Testing:**
- Create backup manually
- Restore to new machine
- Verify all data intact

---

## Phase 9: Testing & Validation

### Step 24: End-to-End Testing

**File:** `tests/test_full_receipt_flow.py`

**What to do:**
Test complete workflow:
1. Upload receipt via stub endpoint → verify OCR + inventory update works
2. Send receipt via Telegram → processed in <3 sec
3. Verify Gemini extraction accuracy (5 receipts, 90%+ target)
4. Force Gemini rate-limit → Ollama fallback succeeds
5. Verify MQTT sync <2 sec (multi-device)
6. Verify Home Assistant dashboard updates
7. Verify recommendation generation
8. Verify spending calculations
9. Verify backup/restore
10. Test offline mode (network disconnect → reconnect)

**Testing tools:**
- `pytest` for unit tests
- `pytest-asyncio` for async tests
- Manual testing for UI (Home Assistant)

---

## Environment Variables & Configuration

### `.env.example`
```
# Telegram
TELEGRAM_BOT_TOKEN=your_token_here

# Google Gemini
GEMINI_API_KEY=your_key_here

# MQTT
MQTT_BROKER=mosquitto
MQTT_PORT=1883

# Flask
FLASK_ENV=production
FLASK_PORT=8080

# Database
DATABASE_URL=sqlite:////data/db/grocery.db

# Ollama
OLLAMA_ENDPOINT=http://ollama:11434

# Daily Recommendations
RECOMMENDATION_TIME=08:00  # 8 AM

# Receipt Image Retention
RECEIPT_RETENTION_MONTHS=12  # Auto-cleanup images older than this

# Auth (generate tokens with: python -c "import secrets; print(secrets.token_urlsafe(32))")
# Tokens are stored hashed in the DB; set initial admin token here for first-run setup
INITIAL_ADMIN_TOKEN=your_initial_admin_token_here
```

---

## Key Implementation Principles

1. **Verb + Noun Naming:** All Python files use human-readable naming
2. **Error Handling:** Every API endpoint handles errors gracefully
3. **Authentication:** All API endpoints require Bearer token (except Telegram webhook)
4. **Logging:** All major operations logged (Flask logger)
5. **Testing:** Unit tests for critical functions (OCR, calculations, MQTT)
6. **Documentation:** Code comments explain "why", not "what"
7. **Portability:** No hardcoded paths/IPs (use environment variables, Docker volumes)
8. **Data Persistence:** All critical data goes to volumes (survives container restarts)
9. **Real-Time Sync:** MQTT publishes all state changes (Home Assistant sees live updates)
10. **User Feedback:** Always inform Telegram users of processing outcome (success, warning, or error)
11. **Schema Migrations:** All schema changes go through Alembic (never manual ALTER TABLE)
12. **WAL Mode:** SQLite WAL mode enabled on every connection for safe concurrent access

---

## Success Criteria

✅ Telegram receipt upload → processed <3 sec  
✅ 90%+ OCR accuracy  
✅ <2 sec MQTT sync latency  
✅ Home Assistant dashboard live & responsive  
✅ Budget/spending calculations accurate  
✅ Backup/restore works (portable)  
✅ All tests pass  
✅ Documentation complete  

---

## References

- **PRD:** `PRD.md` (product requirements)
- **Architecture:** `docs/ARCHITECTURE.md`
- **API Reference:** `docs/API_REFERENCE.md`
- **Deployment:** `docs/DEPLOYMENT_GUIDE.md`

---
