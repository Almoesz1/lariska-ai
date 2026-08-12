"""
LARISKA AI - Application Configuration
Konfigurasi tersentralisasi menggunakan Pydantic Settings v2.
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
    # Supabase (Database & State Management)
    # =====================================================
    supabase_url: str = Field(validation_alias="SUPABASE_URL")
    supabase_anon_key: str = Field(validation_alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field(validation_alias="SUPABASE_SERVICE_ROLE_KEY")
    database_url: str = Field(validation_alias="DATABASE_URL")

    # =====================================================
    # WhatsApp Business Cloud API
    # =====================================================
    whatsapp_token: Optional[str] = Field(default=None, validation_alias="WHATSAPP_TOKEN")
    whatsapp_phone_number_id: Optional[str] = Field(default=None, validation_alias="WHATSAPP_PHONE_NUMBER_ID")
    whatsapp_verify_token: Optional[str] = Field(default=None, validation_alias="WHATSAPP_VERIFY_TOKEN")
    whatsapp_app_secret: Optional[str] = Field(default=None, validation_alias="WHATSAPP_APP_SECRET")

    # =====================================================
    # AI & LLM Engine (Google Gemini & Fallback Routing)
    # =====================================================
    llm_provider: str = Field(default="gemini", validation_alias="LLM_PROVIDER")

    openai_api_key: Optional[str] = Field(default=None, validation_alias="OPENAI_API_KEY")
    google_api_key: Optional[str] = Field(default=None, validation_alias="GOOGLE_API_KEY")
    gemini_api_key: Optional[str] = Field(default=None, validation_alias="GEMINI_API_KEY")
    llm_api_key: Optional[str] = Field(default=None, validation_alias="LLM_API_KEY")

    def get_effective_google_api_key(self) -> Optional[str]:
        """Mengambil Google API Key aktif dari environment variable yang tersedia."""
        return self.gemini_api_key or self.google_api_key or self.llm_api_key or self.openai_api_key

    # Konfigurasi Model Gemini
    gemini_model: str = Field(default="gemini-3.5-flash-lite", validation_alias="GEMINI_MODEL")
    gemini_fallback_models: List[str] = Field(
        default_factory=lambda: [
            "gemini-3.5-flash-lite",
            "gemini-3.5-flash",
            "gemini-flash-latest"
        ],
        validation_alias="GEMINI_FALLBACK_MODELS"
    )

    # RAG Vector & Audio Configuration
    embedding_model_path: str = Field(default="text-embedding-004", validation_alias="EMBEDDING_MODEL_PATH")
    whisper_model_path: str = Field(default="base", validation_alias="WHISPER_MODEL_PATH")

    # =====================================================
    # Sales Brain / Dynamic Negotiation & Scoring Engine
    # =====================================================
    model_artifacts_dir: Optional[str] = Field(default=None, validation_alias="MODEL_ARTIFACTS_DIR")

    # =====================================================
    # Payment Gateway (Midtrans Integration)
    # =====================================================
    midtrans_server_key: Optional[str] = Field(default=None, validation_alias="MIDTRANS_SERVER_KEY")
    midtrans_client_key: Optional[str] = Field(default=None, validation_alias="MIDTRANS_CLIENT_KEY")
    midtrans_is_production: bool = Field(default=False, validation_alias="MIDTRANS_IS_PRODUCTION")

    # =====================================================
    # App & Environment
    # =====================================================
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    app_secret_key: str = Field(validation_alias="APP_SECRET_KEY")
    backend_cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8000"],
        validation_alias="BACKEND_CORS_ORIGINS",
    )
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()