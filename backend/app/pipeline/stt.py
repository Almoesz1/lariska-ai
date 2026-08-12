"""
LARISKA AI — Speech-to-Text (STT) Pipeline (Dual-Engine: Whisper Local + Gemini Cloud Fallback)
"""

import logging
import os
import tempfile
from functools import lru_cache
from typing import Optional, Union

# Daftarkan PATH FFmpeg dari static_ffmpeg jika ada
try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except Exception as e:
    logging.warning(f"[STT] static_ffmpeg init warning: {e}")

from app.core.config import settings
from app.pipeline.gemini_client import generate_content_with_fallback

logger = logging.getLogger(__name__)


@lru_cache
def _get_whisper_model(model_size: str):
    """
    Lazy singleton untuk OpenAI Whisper model.
    """
    try:
        import whisper
    except ImportError as exc:
        logger.error("[STT] openai-whisper tidak terinstall.")
        raise RuntimeError("openai-whisper tidak terinstall.") from exc

    logger.info(f"[STT] Loading Whisper model: '{model_size}'...")
    model = whisper.load_model(model_size)
    logger.info("[STT] Whisper model loaded successfully.")
    return model


def _transcribe_via_gemini(audio_bytes: bytes, mime_type: str = "audio/ogg") -> str:
    """
    Fallback Cloud STT menggunakan Gemini Multimodal Audio Input.
    Mendukung format OGG, MP3, WAV, M4A langsung dari byte audio.
    """
    try:
        from google.genai import types
        logger.info(f"[STT Fallback] Attempting Gemini Audio Transcription ({len(audio_bytes)} bytes)...")
        
        part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
        prompt = (
            "Kamu adalah sistem Speech-to-Text (STT) Bahasa Indonesia. "
            "Tuliskan persis seluruh kalimat yang diucapkan dalam file audio ini. "
            "HANYA kembalikan teks hasil transkripsi tanpa penjelasan, tanpa tanda kutip tambahan, dan tanpa kata sambutan."
        )
        
        # Panggil Gemini via client
        from app.pipeline.gemini_client import _get_client
        client = _get_client()
        
        # Gunakan model Gemini modern yang mendukung audio input
        primary = getattr(settings, "gemini_model", "gemini-3.5-flash-lite")
        models_to_try = [m for m in [primary, "gemini-3.5-flash-lite", "gemini-flash-latest", "gemini-2.5-flash"] if m and "2.0" not in m and "1.5" not in m]
        for m in models_to_try:
            try:
                res = client.models.generate_content(
                    model=m,
                    contents=[part, prompt]
                )
                if res and res.text:
                    transcribed = res.text.strip()
                    logger.info(f"[STT Fallback] Gemini Audio Success ({m}): '{transcribed}'")
                    return transcribed
            except Exception as ge:
                logger.warning(f"[STT Fallback] Gemini model '{m}' failed: {ge}")
                continue
                
    except Exception as exc:
        logger.error(f"[STT Fallback] Gemini audio transcription error: {exc}")
    return ""


def transcribe_audio_file(
    file_path: str,
    language: str = "id",
    model_size: Optional[str] = None,
) -> str:
    """
    Transkripsi file audio dari path file lokal.
    """
    if not os.path.exists(file_path):
        logger.error(f"[STT] File tidak ditemukan: {file_path}")
        raise FileNotFoundError(f"File audio tidak ditemukan: {file_path}")

    effective_model_size = model_size or getattr(settings, "whisper_model_path", "base")

    # 1. Coba OpenAI Whisper (Local)
    try:
        model = _get_whisper_model(effective_model_size)
        logger.info(f"[STT] Transcribing file via Whisper ({effective_model_size}): {file_path}...")
        
        result = model.transcribe(file_path, language=language, fp16=False)
        text = result.get("text", "").strip()

        if text:
            logger.info(f"[STT] Whisper Success: '{text}'")
            return text

    except Exception as exc:
        logger.warning(f"[STT] Whisper transcription failed ({exc}). Trying Gemini Cloud STT Fallback...")

    # 2. Fallback ke Gemini Cloud STT jika Whisper lokal gagal
    try:
        with open(file_path, "rb") as f:
            audio_bytes = f.read()
        ext = os.path.splitext(file_path)[-1].lower()
        mime = "audio/ogg"
        if ext in [".m4a", ".mp4"]:
            mime = "audio/mp4"
        elif ext == ".wav":
            mime = "audio/wav"
        elif ext == ".mp3":
            mime = "audio/mp3"

        cloud_text = _transcribe_via_gemini(audio_bytes, mime_type=mime)
        if cloud_text:
            return cloud_text
    except Exception as exc:
        logger.error(f"[STT] Gemini Cloud Fallback also failed: {exc}")

    raise RuntimeError("Gagal memproses transkripsi audio baik dari Whisper maupun Gemini STT.")


def transcribe_audio_bytes(
    audio_bytes: bytes,
    filename: str = "audio.ogg",
    language: str = "id",
    model_size: Optional[str] = None,
) -> str:
    """
    Transkripsi audio dari byte buffer (WhatsApp media download).
    """
    if not audio_bytes:
        raise ValueError("Byte audio kosong.")

    suffix = os.path.splitext(filename)[-1] or ".ogg"
    
    # 1. Coba Whisper (Local) dulu via TempFile
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            tmp_path = tmp.name

        return transcribe_audio_file(tmp_path, language=language, model_size=model_size)
    except Exception as exc:
        logger.warning(f"[STT] Whisper audio bytes failed: {exc}. Trying Gemini Direct Cloud Fallback...")
        
        # 2. Direct Gemini Fallback dari byte tanpa perlu file
        mime = "audio/ogg"
        if suffix in [".m4a", ".mp4"]:
            mime = "audio/mp4"
        elif suffix == ".wav":
            mime = "audio/wav"
        elif suffix == ".mp3":
            mime = "audio/mp3"

        cloud_text = _transcribe_via_gemini(audio_bytes, mime_type=mime)
        if cloud_text:
            return cloud_text

        raise exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def transcribe_audio(
    input_data: Union[str, bytes],
    language: str = "id",
    model_size: Optional[str] = None,
) -> str:
    if isinstance(input_data, bytes):
        return transcribe_audio_bytes(input_data, language=language, model_size=model_size)
    return transcribe_audio_file(str(input_data), language=language, model_size=model_size)


def transcribe_or_passthrough(
    text: Optional[str],
    audio_bytes: Optional[bytes],
    audio_filename: str = "audio.ogg",
    model_size: Optional[str] = None,
) -> tuple[str, bool]:
    """
    Jika text ada -> passthrough (is_voice=False).
    Jika audio_bytes ada -> jalankan STT pipeline (is_voice=True).
    """
    if text and text.strip():
        return text.strip(), False
    if audio_bytes:
        transcribed = transcribe_audio_bytes(audio_bytes, filename=audio_filename, model_size=model_size)
        return transcribed, True
    raise ValueError("Harus menyediakan salah satu: text atau audio_bytes.")