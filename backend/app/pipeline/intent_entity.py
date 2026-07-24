"""
LARISKA AI — Sprint 4A
Intent Classification + Entity Extraction — Tahap 2 AI Pipeline

Menggunakan Gemini (Google AI) dengan structured output (JSON mode) untuk memastikan
output deterministik dan bisa di-parse dengan aman tanpa regex.

Desain penting:
- LLM HANYA bertugas di tahap ini untuk ekstraksi intent/entity.
- LLM TIDAK menentukan harga, diskon, atau keputusan bisnis apapun (itu tugas Sales Brain).
- Output selalu divalidasi dengan Pydantic (IntentEntityResult) sebelum diteruskan ke pipeline.

Referensi proposal Bab 4, Tahap 2: Intent Classification + Entity Extraction (LLM structured output/JSON mode)
"""

import json
import logging
from datetime import datetime

import google.generativeai as genai

from app.core.config import settings
from app.schemas.pipeline import (
    EmotionType,
    EntityResult,
    IntentEntityResult,
    IntentType,
)

logger = logging.getLogger(__name__)

# ============================================================
# Gemini client — lazy singleton
# ============================================================

_gemini_model = None


def _get_gemini_model():
    global _gemini_model
    if _gemini_model is not None:
        return _gemini_model

    api_key = settings.get_effective_google_api_key()
    if not api_key:
        raise RuntimeError(
            "API key Gemini tidak ditemukan di .env. "
            "Tambahkan GOOGLE_API_KEY=<your_key> atau LLM_API_KEY=<your_key> ke file .env."
        )
    genai.configure(api_key=api_key)
    _gemini_model = genai.GenerativeModel(
        model_name="gemini-flash-latest",
        generation_config=genai.types.GenerationConfig(
            temperature=0.1,          # Rendah untuk output deterministik
            response_mime_type="application/json",  # JSON mode
        ),
    )
    logger.info("[IntentEntity] Gemini model initialized (gemini-flash-latest).")
    return _gemini_model


# ============================================================
# Prompt system
# ============================================================

_SYSTEM_PROMPT = """Kamu adalah AI ekstraksi intent dan entitas untuk sistem penjualan UMKM Indonesia.
Analisis pesan pelanggan dan kembalikan JSON dengan format PERSIS seperti ini:

{
  "intent": "<salah satu dari: tanya_harga|nego|tanya_stok|komplain|checkout|tanya_produk|rekomendasi|greeting|lainnya>",
  "entities": {
    "product_name": "<nama produk yang disebutkan, atau null jika tidak ada>",
    "quantity": <jumlah unit sebagai integer, atau null>,
    "offered_price": <harga yang ditawarkan pelanggan sebagai float (angka saja, tanpa Rp/,), atau null>,
    "target_product_category": "<kategori produk bila tanya umum, atau null>"
  },
  "confidence": <float 0.0 - 1.0, seberapa yakin kamu dengan intent ini>
}

Panduan intent:
- tanya_harga: pelanggan bertanya harga produk
- nego: pelanggan menawar harga (ada kata "boleh kurang", "harga mati?", "diskon", angka penawaran, dll)
- tanya_stok: pelanggan bertanya apakah produk tersedia/ready
- komplain: pelanggan mengadukan masalah (produk rusak, pengiriman terlambat, dll)
- checkout: pelanggan menyatakan mau beli / setuju dengan harga / minta invoice
- tanya_produk: pelanggan bertanya detail produk (bahan, ukuran, warna, spesifikasi)
- rekomendasi: pelanggan minta saran produk
- greeting: salam pembuka tanpa pertanyaan spesifik
- lainnya: tidak masuk kategori lain

PENTING:
- Hanya kembalikan JSON. Tidak ada teks di luar JSON.
- offered_price: ekstrak HANYA angka numerik. "150rb" = 150000.0, "150.000" = 150000.0
- Pesan dalam bahasa campur (Indonesia + slang + typo) adalah normal, tangani dengan baik.
"""


def extract_intent_entity(text: str) -> IntentEntityResult:
    """
    Ekstrak intent dan entitas dari teks pesan pelanggan.

    Args:
        text: Teks pesan pelanggan (bisa hasil STT atau teks langsung).

    Returns:
        IntentEntityResult yang sudah divalidasi Pydantic.

    Raises:
        RuntimeError: Jika Gemini gagal atau output tidak bisa di-parse.
    """
    model = _get_gemini_model()

    prompt = f"{_SYSTEM_PROMPT}\n\nPesan pelanggan:\n\"{text}\""

    logger.info(f"[IntentEntity] Extracting from: '{text[:80]}...' " if len(text) > 80 else f"[IntentEntity] Extracting from: '{text}'")

    try:
        response = model.generate_content(prompt)
        raw_json = response.text.strip()

        # Bersihkan kalau ada markdown code block
        if raw_json.startswith("```"):
            raw_json = raw_json.strip("`").strip()
            if raw_json.startswith("json"):
                raw_json = raw_json[4:].strip()

        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        logger.error(f"[IntentEntity] JSON parse error: {exc}. Raw: {response.text[:200]}")
        # Fallback graceful — daripada crash pipeline
        return _fallback_result(text)
    except Exception as exc:
        logger.error(f"[IntentEntity] Gemini error: {exc}")
        return _fallback_result(text)

    try:
        intent_raw = data.get("intent", "lainnya")
        # Normalisasi ke enum value yang valid
        try:
            intent = IntentType(intent_raw)
        except ValueError:
            intent = IntentType.LAINNYA

        entities_raw = data.get("entities", {})
        entities = EntityResult(
            product_name=entities_raw.get("product_name"),
            quantity=entities_raw.get("quantity"),
            offered_price=_safe_float(entities_raw.get("offered_price")),
            target_product_category=entities_raw.get("target_product_category"),
        )

        result = IntentEntityResult(
            intent=intent,
            entities=entities,
            confidence=float(data.get("confidence", 1.0)),
            raw_text=text,
        )

        logger.info(
            f"[IntentEntity] intent={result.intent.value} | "
            f"product={entities.product_name} | "
            f"offered={entities.offered_price} | "
            f"confidence={result.confidence:.2f}"
        )
        return result

    except Exception as exc:
        logger.error(f"[IntentEntity] Pydantic validation error: {exc}")
        return _fallback_result(text)


def _safe_float(value) -> float | None:
    """Konversi nilai apapun ke float, return None jika tidak bisa."""
    if value is None:
        return None
    try:
        # Hapus karakter non-numerik kecuali titik
        if isinstance(value, str):
            cleaned = value.replace(",", "").replace(".", "")
            # Kalau ada format "150.000" (ribuan pakai titik)
            if len(cleaned) > len(value.replace(",", "")):
                cleaned = value.replace(".", "").replace(",", "")
            return float(cleaned)
        return float(value)
    except (ValueError, TypeError):
        return None


def _fallback_result(text: str) -> IntentEntityResult:
    """
    Fallback saat Gemini gagal — kembalikan intent 'lainnya' daripada crash pipeline.
    Sistem tetap bisa merespons (meski kurang akurat) → lebih baik daripada error 500.
    """
    logger.warning("[IntentEntity] Using fallback result (lainnya).")
    return IntentEntityResult(
        intent=IntentType.LAINNYA,
        entities=EntityResult(),
        confidence=0.0,
        raw_text=text,
    )
