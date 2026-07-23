"""
LARISKA AI
Application Configuration
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )

    # =====================================================
    # Supabase
    # =====================================================

    supabase_url: str = Field(validation_alias="SUPABASE_URL")

    supabase_anon_key: str = Field(validation_alias="SUPABASE_ANON_KEY")

    supabase_service_role_key: str = Field(
        validation_alias="SUPABASE_SERVICE_ROLE_KEY"
    )

    database_url: str = Field(validation_alias="DATABASE_URL")

    # =====================================================
    # WhatsApp
    # =====================================================

    whatsapp_token: Optional[str] = Field(
        default=None,
        validation_alias="WHATSAPP_TOKEN",
    )

    whatsapp_phone_number_id: Optional[str] = Field(
        default=None,
        validation_alias="WHATSAPP_PHONE_NUMBER_ID",
    )

    whatsapp_verify_token: Optional[str] = Field(
        default=None,
        validation_alias="WHATSAPP_VERIFY_TOKEN",
    )

    # =====================================================
    # LLM
    # =====================================================

    llm_provider: str = Field(
        default="gemini",
        validation_alias="LLM_PROVIDER",
    )

    llm_api_key: Optional[str] = Field(
        default=None,
        validation_alias="LLM_API_KEY",
    )

    # =====================================================
    # Midtrans
    # =====================================================

    midtrans_server_key: Optional[str] = Field(
        default=None,
        validation_alias="MIDTRANS_SERVER_KEY",
    )

    midtrans_client_key: Optional[str] = Field(
        default=None,
        validation_alias="MIDTRANS_CLIENT_KEY",
    )

    midtrans_is_production: bool = Field(
        default=False,
        validation_alias="MIDTRANS_IS_PRODUCTION",
    )

    # =====================================================
    # App
    # =====================================================

    environment: str = Field(
        default="development",
        validation_alias="ENVIRONMENT",
    )

    app_secret_key: str = Field(
        validation_alias="APP_SECRET_KEY",
    )

    backend_cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        validation_alias="BACKEND_CORS_ORIGINS",
    )

    log_level: str = Field(
        default="INFO",
        validation_alias="LOG_LEVEL",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()