"""
LARISKA AI - Gemini Client Wrapper (Production & Competition Grade)
Client GenAI tangguh dengan Automatic Fallback Rotation, Exponential Backoff + Jitter,
Dukungan Native Structured Output Schema, Resilient Embedding Extraction, 
serta Dual Sync/Async Hybrid Execution.
"""

import asyncio
import logging
import random
from functools import lru_cache
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class GeminiResult(str):
    """
    Subclass `str` dengan atribut tambahan `.parsed`, `.text`, dan `.raw_response`.
    Memastikan kompatibilitas penuh saat digunakan sebagai string biasa maupun 
    objek respon terstruktur dari Gemini API.
    """

    def __new__(
        cls,
        text: str = "",
        parsed: Any = None,
        raw_response: Any = None
    ):
        val = text or ""
        if not val and parsed is not None:
            val = str(parsed)
        obj = super().__new__(cls, val)
        obj.text = val
        obj.parsed = parsed
        obj.raw_response = raw_response
        return obj

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(f"'GeminiResult' object has no attribute '{name}'")
        if self.raw_response and hasattr(self.raw_response, name):
            return getattr(self.raw_response, name)
        raise AttributeError(f"'GeminiResult' object has no attribute '{name}'")


@lru_cache(maxsize=4)
def _get_client(api_key: Optional[str] = None) -> genai.Client:
    """Mendapatkan atau mengreuse instance Client Google GenAI (Thread-safe & Cached)."""
    effective_key = api_key or settings.get_effective_google_api_key()
    if not effective_key:
        raise RuntimeError("Google API Key tidak ditemukan di environment variables.")
    return genai.Client(api_key=effective_key)


def _clean_model_list(primary_model: Optional[str] = None) -> List[str]:
    """
    Menyusun dan memvalidasi daftar rotasi model Gemini.
    Mengeliminasi model deprecated (seperti gemini-1.5-flash dan gemini-2.0-flash) yang memicu 404 NOT_FOUND.
    """
    base_primary = primary_model or getattr(settings, "gemini_model", "gemini-3.5-flash-lite")
    fallback_list = getattr(settings, "gemini_fallback_models", [])

    raw_list = [base_primary] + (fallback_list if isinstance(fallback_list, list) else [])
    cleaned: List[str] = []

    for m in raw_list:
        if not m:
            continue
        # Filter out model 1.5 & 2.0 legacy yang mengembalikan 404 NOT_FOUND
        if "1.5" in m or "2.0" in m:
            continue
        if m not in cleaned:
            cleaned.append(m)

    # List fallback default modern jika daftar kosong
    if not cleaned:
        cleaned = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-flash-latest"]

    return cleaned


def _sync_generate_content(
    prompt: Optional[str] = None,
    contents: Optional[Any] = None,
    system_instruction: Optional[str] = None,
    config: Optional[types.GenerateContentConfig] = None,
    model: Optional[str] = None,
    schema: Optional[Type[T]] = None,
    **kwargs: Any,
) -> GeminiResult:
    """Versi sinkron untuk pemanggilan tanpa await."""
    text_input = prompt or contents or kwargs.get("contents")
    if not text_input:
        raise ValueError("Parameter 'prompt' atau 'contents' wajib diisi.")

    client = _get_client()
    models_to_try = _clean_model_list(model)

    if config is None:
        config = types.GenerateContentConfig()

    if system_instruction:
        config.system_instruction = system_instruction

    if schema:
        config.response_mime_type = "application/json"
        config.response_schema = schema

    last_error = None
    for model_name in models_to_try:
        try:
            logger.info(f"[GeminiClient] Requesting content generation (sync) using model: '{model_name}'")
            response = client.models.generate_content(
                model=model_name,
                contents=text_input,
                config=config,
            )
            if response:
                text_val = response.text.strip() if getattr(response, "text", None) else ""
                parsed_val = getattr(response, "parsed", None)
                return GeminiResult(text=text_val, parsed=parsed_val, raw_response=response)
        except APIError as exc:
            last_error = exc
            err_msg = str(exc)
            if exc.code == 404 or "NOT_FOUND" in err_msg:
                logger.warning(f"[GeminiClient] Model '{model_name}' 404 NOT_FOUND. Skipping...")
            else:
                logger.warning(f"[GeminiClient] Sync API Error on model '{model_name}': {exc}. Trying fallback...")
            continue
        except Exception as exc:
            last_error = exc
            logger.error(f"[GeminiClient] Sync error on model '{model_name}': {exc}")
            continue

    raise last_error or RuntimeError("Gagal mendapatkan respon dari Gemini API (Sync).")


async def generate_content_with_fallback(
    prompt: Optional[str] = None,
    contents: Optional[Any] = None,
    system_instruction: Optional[str] = None,
    config: Optional[types.GenerateContentConfig] = None,
    model: Optional[str] = None,
    schema: Optional[Type[T]] = None,
    max_retries_per_model: int = 2,
    **kwargs: Any,
) -> GeminiResult:
    """
    Memanggil Gemini API asinkron dengan rotasi otomatis ke model cadangan,
    Exponential Backoff + Jitter untuk 429 (Rate Limit), dan Dukungan Native Structured Output.
    """
    text_input = prompt or contents or kwargs.get("contents")
    if not text_input:
        raise ValueError("Parameter 'prompt' atau 'contents' wajib diisi.")

    client = _get_client()
    models_to_try = _clean_model_list(model)

    if config is None:
        config = types.GenerateContentConfig()

    if system_instruction:
        config.system_instruction = system_instruction

    if schema:
        config.response_mime_type = "application/json"
        config.response_schema = schema

    last_error = None

    for model_name in models_to_try:
        for attempt in range(max_retries_per_model):
            try:
                logger.info(
                    f"[GeminiClient] Requesting content generation (async) "
                    f"model: '{model_name}' (attempt {attempt + 1}/{max_retries_per_model})"
                )

                response = await client.aio.models.generate_content(
                    model=model_name,
                    contents=text_input,
                    config=config,
                )

                if response:
                    text_val = response.text.strip() if getattr(response, "text", None) else ""
                    parsed_val = getattr(response, "parsed", None)
                    return GeminiResult(text=text_val, parsed=parsed_val, raw_response=response)

            except APIError as exc:
                last_error = exc
                err_msg = str(exc)
                is_rate_limit = (
                    exc.code in (429, "429")
                    or "RESOURCE_EXHAUSTED" in err_msg
                    or "QUOTA_EXHAUSTED" in err_msg
                )
                is_not_found = exc.code in (404, "404") or "NOT_FOUND" in err_msg

                if is_not_found:
                    logger.warning(f"[GeminiClient] Model '{model_name}' 404 NOT_FOUND. Skipping model...")
                    break  # Lanjut ke model berikutnya dalam rotasi

                elif is_rate_limit:
                    # Exponential Backoff dengan Jitter untuk mencegah Thundering Herd
                    sleep_time = (0.5 * (2 ** attempt)) + random.uniform(0.1, 0.35)
                    logger.warning(
                        f"[GeminiClient] Model '{model_name}' Rate Limit (429). "
                        f"Waiting {sleep_time:.2f}s before retry/fallback..."
                    )
                    await asyncio.sleep(sleep_time)
                    if attempt == max_retries_per_model - 1:
                        continue
                else:
                    logger.warning(f"[GeminiClient] API Error on model '{model_name}': {exc}. Trying fallback...")
                    break
            except Exception as exc:
                last_error = exc
                logger.error(f"[GeminiClient] Unexpected error on model '{model_name}': {exc}")
                break

    logger.error(f"[GeminiClient] Semua model Gemini gagal dihubungi. Error terakhir: {last_error}")
    raise last_error or RuntimeError("Gagal mendapatkan respon dari Gemini API.")


class HybridCall:
    """
    Wrapper fleksibel yang mendukung pemanggilan asinkron (`await`) maupun sinkron.
    """
    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs
        self._result: Optional[GeminiResult] = None
        self._executed = False

    def _get_result(self) -> GeminiResult:
        if not self._executed:
            self._result = _sync_generate_content(*self._args, **self._kwargs)
            self._executed = True
        return self._result  # type: ignore

    def __await__(self):
        async def _coro():
            return await generate_content_with_fallback(*self._args, **self._kwargs)
        return _coro().__await__()

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(f"'HybridCall' object has no attribute '{name}'")
        return getattr(self._get_result(), name)

    def __str__(self) -> str:
        return str(self._get_result())

    def __repr__(self) -> str:
        return repr(self._get_result())


def generate_content(
    prompt: Optional[str] = None,
    contents: Optional[Any] = None,
    system_instruction: Optional[str] = None,
    config: Optional[types.GenerateContentConfig] = None,
    model: Optional[str] = None,
    schema: Optional[Type[T]] = None,
    **kwargs: Any,
) -> Any:
    """
    Entry point utama untuk generate content LARISKA AI.
    Dapat langsung di-await (Async) atau diakses atributnya secara langsung (Sync).
    
    Contoh Async + Pydantic Structured Output:
        res = await generate_content("Extract data", schema=MyPydanticModel)
        print(res.parsed)
    """
    return HybridCall(
        prompt=prompt,
        contents=contents,
        system_instruction=system_instruction,
        config=config,
        model=model,
        schema=schema,
        **kwargs
    )


async def embed_content(
    contents: Union[str, List[str]],
    model: Optional[str] = None,
) -> List[float]:
    """
    Membuat vector embedding dari teks menggunakan model embedding Google Gemini (`text-embedding-004`).
    Mendukung ekstraksi otomatis dari respons SDK secara aman.
    """
    client = _get_client()

    embedding_model = model or getattr(settings, "embedding_model_path", "text-embedding-004")
    if "text-embedding-3" in embedding_model or "openai" in embedding_model.lower():
        embedding_model = "text-embedding-004"

    try:
        response = await client.aio.models.embed_content(
            model=embedding_model,
            contents=contents,
        )
        if response:
            if hasattr(response, "embedding") and response.embedding:
                return list(response.embedding.values)
            elif hasattr(response, "embeddings") and response.embeddings:
                return list(response.embeddings[0].values)
        return []
    except Exception as exc:
        logger.error(f"[GeminiClient] Error generating async embedding with model '{embedding_model}': {exc}")
        try:
            res = client.models.embed_content(
                model=embedding_model,
                contents=contents,
            )
            if res:
                if hasattr(res, "embedding") and res.embedding:
                    return list(res.embedding.values)
                elif hasattr(res, "embeddings") and res.embeddings:
                    return list(res.embeddings[0].values)
        except Exception as e:
            logger.error(f"[GeminiClient] Sync embedding fallback error: {e}")
        return []