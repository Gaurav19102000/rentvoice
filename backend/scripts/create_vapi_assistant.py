"""Creates the voice assistant in your Vapi account, wired to this backend.

Usage:  python -m scripts.create_vapi_assistant
Needs:  VAPI_API_KEY and PUBLIC_BACKEND_URL in .env
Then:   copy the printed id into VAPI_ASSISTANT_ID, and pick a voice in the Vapi dashboard.
"""
import httpx

from app.config import settings
from app.voice import VAPI_BASE, assistant_config

if not settings.vapi_api_key:
    raise SystemExit("Set VAPI_API_KEY in .env first")

server_url = settings.public_backend_url.rstrip("/") + "/api/vapi/webhook"
cfg = assistant_config(server_url)
if settings.vapi_webhook_secret:
    cfg["server"]["secret"] = settings.vapi_webhook_secret

r = httpx.post(f"{VAPI_BASE}/assistant", json=cfg,
               headers={"Authorization": f"Bearer {settings.vapi_api_key}"}, timeout=30)
if r.status_code >= 400:
    print(r.status_code, r.text)
    raise SystemExit("Vapi rejected the config. Paste the system prompt & tools from app/voice.py into the dashboard instead.")
print("Assistant created. VAPI_ASSISTANT_ID =", r.json()["id"])
print("Webhook URL:", server_url)
