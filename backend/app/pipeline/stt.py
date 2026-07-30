"""
LARISKA AI — Sprint 4A (QA Patch)
Speech-to-Text (STT) — Tahap 1 AI Pipeline

Perubahan dari versi awal setelah Quality Gate review:
- Singleton model diganti dari lock manual (tidak thread-safe, dan
  menciptakan pola baru di luar konvensi project) menjadi @lru_cache —
  pola yang SAMA PERSIS dengan services/supabase_client.py::get_supabase().
  functools.lru_cache thread-safe secara native.
- model_size sekarang benar-benar dibaca dari settings.whisper_model_path
  (config.py). Sebelumnya cuma disebut di docstring tapi tidak pernah
  dipakai di kode — dokumentasi menyesatkan.

Mengubah voice note WhatsApp menjadi teks menggunakan Whisper (open-source, self-host).
Mendukung input berupa:
  - bytes audio (dari voice note yang sudah di-download)
  - path file lokal

CATATAN ARSITEKTUR (belum final — perlu konfirmasi eksplisit):
Modul ini pakai Whisper self-hosted (openai-whisper + torch, load model
lokal). Ini butuh binary `ffmpeg` terinstall terpisah di PATH sistem (bukan
lewat pip) — di Windows ini sering jadi sumber masalah setup. Alternatif
Groq Whisper API (cloud) sempat direkomendasikan sebagai opsi lebih ringan
untuk demo hackathon. Kalau tim memutuskan pindah ke Groq, ganti isi
_get_whisper_model() dan transcribe_audio_bytes() jadi HTTP call ke Groq,
signature fungsi publik (transcribe_or_passthrough, dst) tidak perlu berubah.

Referensi proposal Bab 15 Tech Stack: Whisper (open-source, self-host)
"""

import logging
import os
import tempfile
from functools import lru_cache
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache
def _get_whisper_model(model_size: str):
    """
    Lazy singleton untuk Whisper model, di-cache per model_size lewat
    functools.lru_cache (thread-safe, konsisten dengan pola get_supabase()).
    """
    try:
        import whisper
    except ImportError as exc:
        logger.error(
            "[STT] openai-whisper tidak terinstall. Jalankan: pip install openai-whisper"
        )
        raise RuntimeError(
            "openai-whisper tidak terinstall. Jalankan: pip install openai-whisper"
        ) from exc

    logger.info(f"[STT] Loading Whisper model: '{model_size}'...")
    model = whisper.load_model(model_size)
    logger.info("[STT] Whisper model loaded successfully.")
    return model


def transcribe_audio_bytes(
    audio_bytes: bytes,
    filename: str = "audio.ogg",
    language: str = "id",
    model_size: Optional[str] = None,
) -> str:
    """
    Transkripsi audio dari bytes (voice note WhatsApp format .ogg / .mp4 / .wav).

    Args:
        audio_bytes: Raw bytes dari file audio.
        filename: Nama file sementara untuk inferensi tipe format (ekstensi penting!).
        language: Bahasa target. Default 'id' (Bahasa Indonesia).
        model_size: Ukuran Whisper model ('tiny', 'base', 'small', 'medium', 'large').
            Kalau None (default), diambil dari settings.whisper_model_path.

    Returns:
        Teks transkripsi sebagai string.

    Raises:
        RuntimeError: Jika Whisper gagal load atau transkripsi gagal.
    """
    effective_model_size = model_size or settings.whisper_model_path
    model = _get_whisper_model(effective_model_size)

    suffix = os.path.splitext(filename)[-1] or ".ogg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        logger.info(f"[STT] Transcribing audio ({len(audio_bytes)} bytes, lang={language})...")
        result = model.transcribe(tmp_path, language=language, fp16=False)
        text = result.get("text", "").strip()
        preview = f"{text[:100]}..." if len(text) > 100 else text
        logger.info(f"[STT] Transcription result: '{preview}'")
        return text
    except Exception as exc:
        logger.error(f"[STT] Transcription failed: {exc}")
        raise RuntimeError(f"Whisper transcription gagal: {exc}") from exc
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def transcribe_audio_file(
    file_path: str,
    language: str = "id",
    model_size: Optional[str] = None,
) -> str:
    """
    Transkripsi audio dari path file lokal.
    Wrapper convenience untuk transcribe_audio_bytes.
    """
    with open(file_path, "rb") as f:
        audio_bytes = f.read()
    filename = os.path.basename(file_path)
    return transcribe_audio_bytes(
        audio_bytes, filename=filename, language=language, model_size=model_size
    )


def transcribe_or_passthrough(
    text: Optional[str],
    audio_bytes: Optional[bytes],
    audio_filename: str = "audio.ogg",
    model_size: Optional[str] = None,
) -> tuple[str, bool]:
    """
    Fungsi utama yang dipanggil dari whatsapp_webhook.py.
    Jika pesan berupa teks biasa → langsung return teks.
    Jika berupa voice note → jalankan Whisper STT.

    Returns:
        Tuple (teks_hasil, is_voice_input)
    """
    if text:
        return text.strip(), False

    if audio_bytes:
        transcribed = transcribe_audio_bytes(
            audio_bytes,
            filename=audio_filename,
            model_size=model_size,
        )
        return transcribed, True

    raise ValueError("Harus menyediakan salah satu: text atau audio_bytes.")