"""Application settings loaded from environment / .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "RestoPilot API"
    debug: bool = True

    # Multi-tenant: id of the demo store used for local runs.
    default_store_id: int = 1

    # When True, all external calls (StepFun OCR/audio, WhatsApp sending) are mocked.
    mock_mode: bool = True

    # SQLite for the MVP; swap to a Postgres URL for multi-tenant production.
    database_url: str = "sqlite:///./restopilot.db"

    # --- WhatsApp (Meta Cloud API) ---
    whatsapp_verify_token: str = "restopilot-dev-token"
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""

    # --- Twilio (alternative WhatsApp provider) ---
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = "whatsapp:+14155238886"

    # --- StepFun (perception layer) ---
    stepfun_api_key: str = ""
    stepfun_base_url: str = "https://api.stepfun.com/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
