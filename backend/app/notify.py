"""Optional SMS with the chat link after a call (Twilio REST, no SDK needed)."""
import logging

import httpx

from .config import settings

log = logging.getLogger("rentvoice.notify")


def send_chat_link(phone: str, name: str, chat_token: str) -> bool:
    link = f"{settings.frontend_url}/chat/{chat_token}"
    if not (settings.twilio_sid and settings.twilio_token and settings.twilio_from):
        log.info("SMS disabled; chat link for %s: %s", phone, link)
        return False
    body = f"Hi {name.split()[0]}, your RentVoice shortlist is ready: {link}"
    try:
        r = httpx.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_sid}/Messages.json",
            data={"To": phone, "From": settings.twilio_from, "Body": body},
            auth=(settings.twilio_sid, settings.twilio_token),
            timeout=15,
        )
        r.raise_for_status()
        return True
    except httpx.HTTPError as e:
        log.warning("SMS failed: %s", e)
        return False
