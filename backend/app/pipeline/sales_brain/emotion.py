"""
LARISKA AI — Sprint 5A
Emotion Classifier — Tahap 4b AI Pipeline

Mengklasifikasi emosi pelanggan dari teks pesan menggunakan Gemini 1.5 Flash.
Output dipakai oleh response_generator.py untuk menyesuaikan nada balasan AI.

4 kelas emosi utama (sesuai proposal Bab 7b):
- marah     → Nada empati + profesional, hindari basa-basi
- netral    → Nada ramah standar
- santai    → Nada kasual, bisa pakai emoji
- buru_buru → Langsung ke point, tanpa basa-basi panjang
- senang    → Cocok untuk upsell produk tambahan

Implementasi: 1 prompt tambahan ke Gemini (bukan model baru) — sesuai proposal:
"1 langkah klasifikasi tambahan di pipeline, effort-nya kecil"
"""

import json
import logging
from typing import Optional

import google.generativeai as genai

from app.core.config import settings
from app.schemas.pipeline import EmotionResult, EmotionType

logger = logging.getLogger(__name__)

# Reuse Gemini model dari intent_entity (singleton di module level)
_emotion_model = None


def _get_emotion_model():
    global _emotion_model
    if _emotion_model is not None:
        return _emotion_model

    api_key = settings.get_effective_google_api_key()
    if not api_key:
        raise RuntimeError("API key Gemini tidak ditemukan di .env (set GOOGLE_API_KEY atau LLM_API_KEY).")

    genai.configure(api_key=api_key)
    _emotion_model = genai.GenerativeModel(
        model_name="gemini-flash-latest",
        generation_config=genai.types.GenerationConfig(
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )
    return _emotion_model


_EMOTION_PROMPT = """Kamu adalah AI klasifikasi emosi untuk sistem penjualan WhatsApp Indonesia.
Analisis emosi pelanggan dari pesan berikut dan kembalikan JSON:

{
  "emotion": "<salah satu: marah|netral|santai|buru_buru|senang>",
  "confidence": <float 0.0-1.0>,
  "tone_hint": "<kalimat singkat 1 baris: petunjuk cara membalas, contoh: 'Balas dengan empati dan jangan terlalu banyak basa-basi'>"
}

Panduan:
- marah: ada komplain, kekecewaan, kata kasar, tanda seru berulang
- netral: pertanyaan biasa tanpa indikator emosi
- santai: pakai emoji, bercanda, sapaan akrab, kalimat informal
- buru_buru: kata seperti "bisa sekarang?", "cepat", "urgent", "besok udah harus ada"
- senang: antusias, banyak emoji positif, menyatakan puas

PENTING: Kembalikan HANYA JSON, tidak ada teks lain.
"""


def classify_emotion(text: str) -> EmotionResult:
    """
    Klasifikasi emosi dari teks pesan pelanggan.

    Args:
        text: Teks pesan (bisa hasil STT atau teks langsung).

    Returns:
        EmotionResult dengan emotion, confidence, dan tone_hint.
    """
    model = _get_emotion_model()
    prompt = f"{_EMOTION_PROMPT}\n\nPesan:\n\"{text}\""

    logger.info(f"[Emotion] Classifying: '{text[:60]}...' " if len(text) > 60 else f"[Emotion] Classifying: '{text}'")

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()

        # Bersihkan markdown code block jika ada
        if raw.startswith("```"):
            raw = raw.strip("`").strip()
            if raw.startswith("json"):
                raw = raw[4:].strip()

        data = json.loads(raw)

        try:
            emotion = EmotionType(data.get("emotion", "netral"))
        except ValueError:
            emotion = EmotionType.NETRAL

        result = EmotionResult(
            emotion=emotion,
            confidence=float(data.get("confidence", 1.0)),
            tone_hint=data.get("tone_hint", ""),
        )
        logger.info(f"[Emotion] Result: {result.emotion.value} (conf={result.confidence:.2f})")
        return result

    except (json.JSONDecodeError, Exception) as exc:
        logger.warning(f"[Emotion] Fallback to netral due to error: {exc}")
        return EmotionResult(
            emotion=EmotionType.NETRAL,
            confidence=0.5,
            tone_hint="Balas dengan ramah dan profesional.",
        )
