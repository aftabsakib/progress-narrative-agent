from pydantic_settings import BaseSettings
from datetime import date


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_service_key: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    sendgrid_api_key: str = ""
    alert_email_faisal: str = "faisal@tangier.us"
    alert_email_aftab: str = "community@evqlabs.com"
    from_email: str = "agent@tangier.us"
    aaep_window_end: str = "2026-06-30"

    @property
    def aaep_days_remaining(self) -> int:
        end = date.fromisoformat(self.aaep_window_end)
        return (end - date.today()).days

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
