---
description: Debug common issues with MQTT, OCR, SQLite, and Docker
---

# Debug Common Issues

## MQTT Not Connecting

// turbo
1. Check MQTT broker status
```bash
docker-compose ps mqtt
```

// turbo
2. Check MQTT logs
```bash
docker-compose logs --tail=30 mqtt
```

3. Test MQTT manually
```bash
# Publish
docker exec grocery-mqtt mosquitto_pub -t "test" -m "debug-test"

# Subscribe (in another terminal)
docker exec grocery-mqtt mosquitto_sub -t "test" -C 1
```

4. Common fixes:
   - Broker not started → `docker-compose up -d mqtt`
   - Config error → check `config/mosquitto/mosquitto.conf`
   - Backend using wrong hostname → must use `mqtt` not `localhost` inside Docker

---

## Gemini API Errors

// turbo
1. Check if API key is set
```bash
docker exec grocery-backend env | grep GEMINI
```

2. Test Gemini directly
```bash
docker exec grocery-backend python -c "
import os
print('Key set:', bool(os.getenv('GEMINI_API_KEY')))
"
```

3. Common issues:
   - **429 Too Many Requests** → Rate limited. Ollama fallback should trigger.
   - **403 Forbidden** → Invalid API key
   - **Slow responses** → Check image size, compress if >5MB

---

## SQLite Locked

// turbo
1. Check WAL mode is enabled
```bash
docker exec grocery-backend python -c "
import sqlite3
conn = sqlite3.connect('/data/db/grocery.db')
print(conn.execute('PRAGMA journal_mode').fetchone())
conn.close()
"
```

2. If not in WAL mode, the `initialize_database_schema.py` event listener may not be working.
   Verify `_set_wal_mode` is attached via `event.listen(engine, 'connect', _set_wal_mode)`.

3. If database is locked during writes:
   - Check for multiple Flask workers (should be 1 worker for SQLite)
   - Check for long-running transactions (add timeouts)

---

## Docker Issues

// turbo
1. Check all container status
```bash
docker-compose ps
```

// turbo
2. View recent logs
```bash
docker-compose logs --tail=50
```

3. Rebuild after code changes
```bash
docker-compose build backend && docker-compose up -d backend
```

4. Full restart
```bash
docker-compose down && docker-compose up -d
```

5. Nuclear option (reset everything, DELETES DATA)
```bash
docker-compose down -v && docker-compose up -d --build
```

---

## Ollama Not Responding

// turbo
1. Check Ollama status
```bash
curl http://localhost:11434/api/tags
```

// turbo
2. Check if model is downloaded
```bash
docker exec grocery-ollama ollama list
```

3. If no model:
```bash
docker exec grocery-ollama ollama pull llava:7b
```

4. If out of memory:
   - Check `docker stats grocery-ollama`
   - Increase memory limit in `docker-compose.yml` (deploy.resources.limits.memory)

---

## Telegram Webhook Not Receiving

1. Check webhook status
```bash
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

2. Common issues:
   - **SSL error** → Nginx Proxy Manager SSL not valid
   - **Wrong URL** → Webhook must point to `https://your-domain.com/telegram/webhook`
   - **Timeout** → Backend must respond within 30 seconds
   - **Not using Telegram** → Use stub upload endpoint instead (no Telegram needed)
