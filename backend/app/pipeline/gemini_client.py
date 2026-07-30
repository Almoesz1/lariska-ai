"""Akses Gemini terpusat dengan retry terbatas untuk pipeline LARISKA AI.

Modul ini hanya menangani kegagalan provider yang sementara. Keputusan bisnis
dan fallback pelanggan tetap berada di modul pipeline masing-masing, sehingga
kegagalan Gemini tidak pernah mengubah harga atau melanggar guardrail.
"""

from __future__ import annotations

import logging
import random
import re
import time
from functools import lru_cache
from typing import Any, Callable, TypeVar

import httpx
from google import genai

from app.core.config import settings

logger = logging.getLogger(__name__)

_DEFAULT_MAX_ATTEMPTS = 3
_BASE_BACKOFF_SECONDS = 1.0
_MAX_BACKOFF_SECONDS = 30.0
_T = TypeVar("_T")


@lru_cache
def get_gemini_client() -> genai.Client:
    """Kembalikan satu client SDK terkonfigurasi untuk satu proses."""
    api_key = settings.get_effective_google_api_key()
    if not api_key:
        raise RuntimeError(
            "API key Gemini tidak ditemukan. Set GOOGLE_API_KEY atau LLM_API_KEY."
        )
    return genai.Client(api_key=api_key)


def _status_code(exc: Exception) -> int | None:
    code = getattr(exc, "code", None)
    return code if isinstance(code, int) else None


def is_transient_gemini_error(exc: Exception) -> bool:
    """Hanya error yang aman dicoba ulang tanpa mengubah semantik request."""
    code = _status_code(exc)
    if code == 429 or (code is not None and 500 <= code <= 599):
        return True
    return isinstance(exc, (httpx.TimeoutException, httpx.TransportError, TimeoutError, OSError))


def _retry_after_from_headers(exc: Exception) -> float | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    value = headers.get("Retry-After") or headers.get("retry-after")
    try:
        return max(0.0, float(value)) if value is not None else None
    except (TypeError, ValueError):
        return None


def _find_retry_delay(value: Any) -> float | None:
    """Ekstrak google.rpc.RetryInfo.retryDelay dari bentuk payload SDK apa pun."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"retryDelay", "retry_delay"} and isinstance(item, str):
                match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)s\s*", item)
                if match:
                    return float(match.group(1))
            found = _find_retry_delay(item)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_retry_delay(item)
            if found is not None:
                return found
    return None


def retry_delay_seconds(exc: Exception, retry_index: int) -> float:
    """Prioritaskan instruksi provider; sisanya exponential backoff + jitter."""
    server_delay = _retry_after_from_headers(exc) or _find_retry_delay(
        getattr(exc, "details", None)
    )
    if server_delay is not None:
        return min(server_delay, _MAX_BACKOFF_SECONDS)

    cap = min(_BASE_BACKOFF_SECONDS * (2**retry_index), _MAX_BACKOFF_SECONDS)
    return cap + random.uniform(0.0, min(1.0, cap * 0.25))


def _call_with_retry(operation: Callable[[], _T], operation_name: str, max_attempts: int) -> _T:
    if max_attempts < 1:
        raise ValueError("max_attempts harus minimal 1.")

    for attempt in range(max_attempts):
        try:
            return operation()
        except Exception as exc:
            if not is_transient_gemini_error(exc) or attempt == max_attempts - 1:
                raise

            delay = retry_delay_seconds(exc, attempt)
            logger.warning(
                "[Gemini] %s gagal (%s); retry %s/%s dalam %.2f detik.",
                operation_name,
                _status_code(exc) or type(exc).__name__,
                attempt + 1,
                max_attempts - 1,
                delay,
            )
            time.sleep(delay)

    raise RuntimeError("Retry state tidak valid.")


def generate_content(*, model: str, contents: Any, config: Any = None, max_attempts: int = _DEFAULT_MAX_ATTEMPTS) -> Any:
    """Panggil generasi Gemini dengan retry 429/5xx yang terbatas."""
    return _call_with_retry(
        lambda: get_gemini_client().models.generate_content(
            model=model, contents=contents, config=config
        ),
        "generate_content",
        max_attempts,
    )


def embed_content(*, model: str, contents: Any, max_attempts: int = _DEFAULT_MAX_ATTEMPTS) -> Any:
    """Panggil embedding Gemini dengan kebijakan transient failure yang sama."""
    return _call_with_retry(
        lambda: get_gemini_client().models.embed_content(model=model, contents=contents),
        "embed_content",
        max_attempts,
    )
