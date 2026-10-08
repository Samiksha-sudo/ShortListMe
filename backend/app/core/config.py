from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./shortlistme.db"
    storage_dir: str = "../storage"
    cors_origins: str = "http://localhost:5173"
    jwt_secret: str = "dev-only-change-me-this-is-not-a-real-secret-key"
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    reset_token_minutes: int = 30
    frontend_url: str = "http://localhost:5173"

    # Per-user caps over one window: LLM-backed calls (analysis, match, rewrite, tailoring) and CV uploads.
    rate_limit_window_seconds: int = 600
    rate_limit_llm: int = 20
    rate_limit_upload: int = 30

    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 180.0  # rewriting sends the whole CV, which routinely takes longer than 30s
    llm_max_retries: int = 2

    # Billing: 5 free tailorings per account, then a £20/month plan (price created in the Stripe dashboard).
    free_tailorings: int = 5
    pro_tailorings_per_month: int = 50
    # Comma-separated emails that use the app free of charge with no quota (the owner's own account).
    admin_emails: str = "kadsamiksha347@gmail.com"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""

    mail_from: str = "noreply@shortlistme.local"
    mail_backend: str = "console"  # console | smtp
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    @field_validator("jwt_secret")
    @classmethod
    def _secret_not_empty(cls, v: str) -> str:
        # An empty JWT_SECRET in the environment must not silently sign tokens with an empty key.
        return v.strip() or "dev-only-change-me-this-is-not-a-real-secret-key"


settings = Settings()
