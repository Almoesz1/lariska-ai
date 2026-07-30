"""
LARISKA AI — Centralized Gemini Client Helper
"""
from google import genai
from app.core.config import settings

def get_gemini_client() -> genai.Client:
    api_key = settings.get_effective_google_api_key()
    if not api_key:
        raise ValueError("GOOGLE_API_KEY atau LLM_API_KEY belum dikonfigurasi di .env")
    return genai.Client(api_key=api_key)