# API Reference

## Authentication

All endpoints (except `/telegram/webhook` and `/health`) require a Bearer token:

```
Authorization: Bearer <your-api-token>
```

Generate tokens: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

Unauthorized requests receive `401 Unauthorized`.

---

## Endpoints

### Health Check

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | None | Service health status |

**Response:**
```json
{"status": "healthy", "service": "grocery-backend"}
```

---

### Receipt Management

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/telegram/webhook` | Telegram signature | Receive Telegram bot updates |
| POST | `/receipts/upload` | Bearer token | Upload receipt image for OCR |
| GET | `/receipts/{id}` | Bearer token | Retrieve receipt details |

#### POST `/receipts/upload`

Upload a receipt image for OCR processing.

**Request:** `multipart/form-data`
```bash
curl -X POST http://localhost:8080/receipts/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "image=@receipt.jpg"
```

**Response (202):**
```json
{
  "status": "processed",
  "store": "Whole Foods",
  "date": "2026-04-01",
  "items": [
    {"name": "Organic Milk", "quantity": 1, "unit_price": 3.20, "category": "dairy"}
  ],
  "total": 45.67,
  "confidence": 0.92,
  "ocr_engine": "gemini"
}
```

---

### Product Catalog

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/products` | Bearer token | List all products (paginated) |
| GET | `/products/search?q=milk` | Bearer token | Search products |
| POST | `/products/create` | Bearer token | Add new product |
| PUT | `/products/{id}/update` | Bearer token | Update product |
| DELETE | `/products/{id}` | Bearer token | Remove product |

---

### Inventory

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/inventory` | Bearer token | List current inventory |
| POST | `/inventory/add-item` | Bearer token | Add item with quantity |
| PUT | `/inventory/{id}/consume` | Bearer token | Decrease quantity by 1 |
| PUT | `/inventory/{id}/update` | Bearer token | Set quantity directly |
| DELETE | `/inventory/{id}` | Bearer token | Remove from inventory |

#### POST `/inventory/add-item`

```json
{
  "product_id": 1,
  "quantity": 2.0,
  "location": "Fridge"
}
```

---

### Analytics

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/analytics/spending?period=monthly` | Bearer token | Spending by period |
| GET | `/analytics/spending?category=dairy` | Bearer token | Spending by category |
| GET | `/analytics/price-history?product_id=1` | Bearer token | Price trends |
| GET | `/analytics/deals-captured?period=monthly` | Bearer token | Savings from deals |
| GET | `/analytics/store-comparison` | Bearer token | Cross-store price comparison |

---

### Budget

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/budget/set-monthly` | Bearer token | Set monthly budget |
| GET | `/budget/status` | Bearer token | Budget vs actual spending |

#### POST `/budget/set-monthly`

```json
{
  "month": "2026-04",
  "budget_amount": 600.00
}
```

---

### Recommendations

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/recommendations` | Bearer token | Get current recommendations |

---

## MQTT Topics

| Topic | Direction | Payload |
|-------|-----------|---------|
| `home/grocery/inventory/{product_id}` | Backend → HA | `{product_id, name, quantity, location, updated_by, timestamp}` |
| `home/grocery/alerts/low_stock` | Backend → HA | `{product_id, name, current, threshold, alert_type}` |
| `home/grocery/alerts/budget` | Backend → HA | `{budget_amount, spent, percentage, alert_type}` |
| `home/grocery/recommendations/daily` | Backend → HA | `{recommendations: [...], count, timestamp}` |

---

## Error Responses

| Code | Meaning |
|------|---------|
| 400 | Bad request — missing or invalid parameters |
| 401 | Unauthorized — missing or invalid Bearer token |
| 403 | Forbidden — insufficient permissions |
| 404 | Not found — resource doesn't exist |
| 500 | Internal server error |
| 501 | Not implemented — endpoint stub not yet built |
