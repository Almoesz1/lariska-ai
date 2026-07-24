"""
LARISKA AI — Sprint 4A
Speech-to-Text (STT) — Tahap 1 AI Pipeline

Mengubah voice note WhatsApp menjadi teks menggunakan Whisper (open-source, self-host).
Mendukung input berupa:
  - file path (bytes dari voice note yang sudah di-download)
  - URL audio (didownload dulu, lalu di-transcribe)

Whisper model di-load SEKALI saat aplikasi start (lazy singleton), bukan per request,
untuk menghindari cold start yang memakan waktu ~2-5 detik setiap pesan masuk.

Referensi proposal Bab 15 Tech Stack: Whisper (open-source, self-host)
"""

import io
import logging
import tempfile
import os
from functools import lru_cache
from typing import Optional, Union

logger = logging.getLogger(__name__)

# Lazy import — Whisper berat, hanya di-import saat dibutuhkan
_whisper_model = None
_WHISPER_LOCK = False  # Simple flag untuk mencegah double load


def _get_whisper_model(model_size: str = "base"):
    """
    Lazy singleton untuk Whisper model.
    Di-load hanya saat pertama kali dipanggil, lalu di-cache selamanya.
    model_size diambil dari settings.whisper_model_path (default 'base').
    """
    global _whisper_model, _WHISPER_LOCK
    if _whisper_model is not None:
        return _whisper_model

    if _WHISPER_LOCK:
        # Race condition guard sederhana
        import time
        time.sleep(0.5)
        return _whisper_model

    _WHISPER_LOCK = True
    try:
        import whisper
        logger.info(f"[STT] Loading Whisper model: '{model_size}'...")
        _whisper_model = whisper.load_model(model_size)
        logger.info("[STT] Whisper model loaded successfully.")
    except ImportError:
        logger.error(
            "[STT] openai-whisper tidak terinstall. "
            "Jalankan: pip install openai-whisper"
        )
        raise
    finally:
        _WHISPER_LOCK = False

    return _whisper_model


def transcribe_audio_bytes(
    audio_bytes: bytes,
    filename: str = "audio.ogg",
    language: str = "id",
    model_size: str = "base",
) -> str:
    """
    Transkripsi audio dari bytes (voice note WhatsApp format .ogg / .mp4 / .wav).

    Args:
        audio_bytes: Raw bytes dari file audio.
        filename: Nama file sementara untuk inferensi tipe format (ekstensi penting!).
        language: Bahasa target. Default 'id' (Bahasa Indonesia).
        model_size: Ukuran Whisper model ('tiny', 'base', 'small', 'medium', 'large').

    Returns:
        Teks transkripsi sebagai string.

    Raises:
        RuntimeError: Jika Whisper gagal load atau transkripsi gagal.
    """
    model = _get_whisper_model(model_size)

    # Simpan ke file sementara — Whisper butuh path file, bukan bytes langsung
    suffix = os.path.splitext(filename)[-1] or ".ogg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        logger.info(f"[STT] Transcribing audio ({len(audio_bytes)} bytes, lang={language})...")
        result = model.transcribe(tmp_path, language=language, fp16=False)
        text = result.get("text", "").strip()
        logger.info(f"[STT] Transcription result: '{text[:100]}...' (truncated)" if len(text) > 100 else f"[STT] Transcription: '{text}'")
        return text
    except Exception as exc:
        logger.error(f"[STT] Transcription failed: {exc}")
        raise RuntimeError(f"Whisper transcription gagal: {exc}") from exc
    finally:
        # Selalu bersihkan file temp
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def transcribe_audio_file(
    file_path: str,
    language: str = "id",
    model_size: str = "base",
) -> str:
    """
    Transkripsi audio dari path file lokal.
    Wrapper convenience untuk transcribe_audio_bytes.
    """
    with open(file_path, "rb") as f:
        audio_bytes = f.read()
    filename = os.path.basename(file_path)
    return transcribe_audio_bytes(audio_bytes, filename=filename, language=language, model_size=model_size)


def transcribe_or_passthrough(
    text: Optional[str],
    audio_bytes: Optional[bytes],
    audio_filename: str = "audio.ogg",
    model_size: str = "base",
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
