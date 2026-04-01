---
description: Set up the development environment from scratch
---

# Setup Dev Environment

## Steps

1. Clone the repository
```bash
git clone https://github.com/chatwithllm/LocalOCR.git
cd LocalOCR
```

2. Create environment file
```bash
cp .env.example .env
```

3. Edit `.env` with real values:
   - `GEMINI_API_KEY` — get from https://ai.google.dev/
   - `INITIAL_ADMIN_TOKEN` — generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
   - `TELEGRAM_BOT_TOKEN` — optional, get from @BotFather on Telegram

// turbo
4. Start Docker Compose stack
```bash
docker-compose up -d
```

// turbo
5. Verify all services are running
```bash
docker-compose ps
```

// turbo
6. Verify backend health
```bash
curl http://localhost:8080/health
```

// turbo
7. Verify MQTT broker
```bash
docker exec grocery-mqtt mosquitto_pub -t "test" -m "setup-test"
```

// turbo
8. Verify Ollama
```bash
curl http://localhost:11434/api/tags
```

9. Pull LLaVA model (first time only, ~2GB download)
```bash
docker exec grocery-ollama ollama pull llava:7b
```

10. Run initial database schema check
```bash
docker exec grocery-backend python -c "from src.backend.initialize_database_schema import initialize_database; initialize_database(); print('✅ DB ready')"
```

## Verification
- All 3 services show "Up (healthy)" in `docker-compose ps`
- `/health` returns `{"status": "healthy"}`
- Ollama lists `llava:7b` in model tags
