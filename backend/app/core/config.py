"""Application configuration — loaded from environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────
    APP_NAME: str = "AI Business Employee"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    APP_SECRET_KEY: str = "CHANGE_ME"

    # ── Database ─────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://aiemployee:aiemployee_secret@localhost:5432/ai_employee_db"

    # ── Redis ────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── CORS ─────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ]

    # ── JWT ──────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── Google / Gemini ──────────────────────────────────────────────
    GOOGLE_API_KEY: str = ""
    GOOGLE_CLOUD_PROJECT: str = ""
    GOOGLE_CLOUD_REGION: str = "us-central1"
    GEMINI_MODEL: str = "gemini-1.5-pro"
    GEMINI_FAST_MODEL: str = "gemini-1.5-flash"
    EMBEDDING_MODEL: str = "models/text-embedding-004"

    # ── Twilio ───────────────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    TWILIO_WHATSAPP_NUMBER: str = ""

    # ── Escalation ───────────────────────────────────────────────────
    # Phone Twilio <Dial>s when AI escalates to a human (team / call centre)
    ESCALATION_PHONE: str = ""
    # WhatsApp number that receives team alert on escalation / hot lead
    TEAM_WHATSAPP_PHONE: str = ""
    # Seconds before Dial gives up
    ESCALATION_DIAL_TIMEOUT: int = 30

    # ── HubSpot ──────────────────────────────────────────────────────
    HUBSPOT_ACCESS_TOKEN: str = ""
    HUBSPOT_PORTAL_ID: str = ""

    # ── Google Calendar ──────────────────────────────────────────────
    GOOGLE_CALENDAR_CREDENTIALS_JSON: str = ""
    GOOGLE_CALENDAR_TOKEN_JSON: str = ""
    GOOGLE_CALENDAR_ID: str = "primary"

    # ── Brevo (Email) ─────────────────────────────────────────────────
    BREVO_API_KEY: str = ""
    BREVO_SENDER_EMAIL: str = "noreply@aiemployee.app"

    # ── Rate limiting (Redis) ─────────────────────────────────────────
    # Max inbound webhook hits per phone number per window
    RATE_LIMIT_CALLS_PER_MINUTE: int = 5
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


settings = Settings()
