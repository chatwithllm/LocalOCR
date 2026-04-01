# Nginx Proxy Manager Setup

## Purpose

Nginx Proxy Manager routes external HTTPS traffic to the Flask backend,
enabling Telegram webhook delivery. **Only needed if using Telegram bot.**

> ⚠️ If you're only using the stub upload endpoint, you do NOT need Nginx Proxy Manager.

---

## Prerequisites

- Nginx Proxy Manager already installed and running
- A registered domain name (e.g., `grocery.yourdomain.com`)
- Port 80 and 443 forwarded on your router to the NPM host

---

## Setup Steps

### 1. Open NPM Dashboard

Navigate to your Nginx Proxy Manager admin panel (usually `http://your-server-ip:81`).

### 2. Add Proxy Host

| Field | Value |
|-------|-------|
| **Domain Names** | `grocery.yourdomain.com` |
| **Scheme** | `http` |
| **Forward Hostname/IP** | `localhost` (or Docker host IP) |
| **Forward Port** | `8080` |
| **Block Common Exploits** | ✅ Enabled |
| **Websockets Support** | ✅ Enabled |

### 3. Enable SSL

In the **SSL** tab:
- Select **Request a new SSL Certificate**
- Check **Force SSL**
- Check **HTTP/2 Support**
- Agree to Let's Encrypt terms
- Click **Save**

### 4. Verify HTTPS

```bash
curl https://grocery.yourdomain.com/health
# Should return: {"status": "healthy", "service": "grocery-backend"}
```

### 5. Register Telegram Webhook

```bash
# Replace with your bot token and domain
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://grocery.yourdomain.com/telegram/webhook"

# Verify webhook
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| SSL certificate fails | Ensure ports 80/443 are forwarded, domain DNS points to your IP |
| 502 Bad Gateway | Verify backend is running: `docker-compose ps` |
| Telegram webhook not receiving | Check webhook URL matches exactly, verify SSL is valid |
| Connection refused | Ensure NPM can reach `localhost:8080` (Docker network) |

---

## Renewal

Let's Encrypt certificates auto-renew via NPM. No manual action needed.
If renewal fails, check that port 80 is still accessible from the internet.
