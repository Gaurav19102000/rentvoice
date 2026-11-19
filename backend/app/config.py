import os
from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    database_url = os.getenv("DATABASE_URL", "sqlite:///./rentvoice.db")
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    public_backend_url = os.getenv("PUBLIC_BACKEND_URL", "http://localhost:8000")
    admin_token = os.getenv("ADMIN_TOKEN", "change-me")
    demo_mode = _bool("DEMO_MODE", True)
    listing_ttl_days = int(os.getenv("LISTING_TTL_DAYS", "30"))

    vapi_api_key = os.getenv("VAPI_API_KEY", "")
    vapi_public_key = os.getenv("VAPI_PUBLIC_KEY", "")
    vapi_assistant_id = os.getenv("VAPI_ASSISTANT_ID", "")
    vapi_phone_number_id = os.getenv("VAPI_PHONE_NUMBER_ID", "")
    vapi_webhook_secret = os.getenv("VAPI_WEBHOOK_SECRET", "")

    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
    llm_model = os.getenv("LLM_MODEL", "claude-haiku-5-5")

    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_from = os.getenv("TWILIO_FROM_NUMBER", "")

    @property
    def phone_calls_enabled(self) -> bool:
        return bool(self.vapi_api_key and self.vapi_assistant_id and self.vapi_phone_number_id)

    @property
    def web_calls_enabled(self) -> bool:
        return bool(self.vapi_public_key and self.vapi_assistant_id)


settings = Settings()
