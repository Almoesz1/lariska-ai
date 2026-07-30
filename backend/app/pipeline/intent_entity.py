"""
LARISKA AI — Sprint 4A (QA Patch)
Intent Classification + Entity Extraction — Tahap 2 AI Pipeline

Perubahan dari versi awal setelah Quality Gate review:
- SDK diganti dari `google-generativeai` (legacy, akan deprecated) ke
  `google-genai` (SDK resmi terbaru per dokumentasi Google saat ini).
  requirements.txt perlu diupdate: hapus google-generativeai, tambah google-genai.
- Model dipin eksplisit ke "gemini-3.5-flash-lite" (GA/stable) — BUKAN alias
  "-latest". Dokumentasi resmi Google: alias -latest menunjuk ke model
  eksperimental, rate limit lebih ketat, dan bisa berpindah versi tanpa
  pemberitahuan — berisiko untuk demo live. gemini-3.5-flash-lite dipilih
  karena task ini murni klasifikasi/ekstraksi terstruktur (bukan reasoning
  kompleks) — sesuai rekomendasi resmi Google untuk kategori use case
  "high-volume extraction, routing, or classification".
- Structured output sekarang pakai response_schema (Pydantic model
  langsung), bukan cuma instruksi format di prompt + parsing manual. Ini
  MENGHILANGKAN kebutuhan fungsi _safe_float() sepenuhnya — offered_price
  dipaksa jadi float oleh Gemini sendiri lewat schema enforcement, tidak
  pernah lewat jalur string-parsing yang rawan salah lagi.
- Parameter temperature dihapus dari generation config, sesuai rekomendasi
  resmi Google untuk seluruh model Gemini 3.x ("strongly recommend not
  changing the default values").

Desain penting (TIDAK berubah dari versi awal — ini prinsip inti proposal):
- LLM HANYA bertugas ekstraksi intent/entity di tahap ini.
- LLM TIDAK PERNAH menentukan harga, diskon, atau keputusan bisnis apapun
  (itu tugas Sales Brain Sprint 5A, lewat Adaptive Scoring Engine).
- Output selalu divalidasi Pydantic sebelum diteruskan ke pipeline.
- Kegagalan apapun (network, parsing, validasi) di-fallback ke intent
  'lainnya', TIDAK PERNAH crash — graceful degradation, konsisten dengan
  filosofi global exception handler di main.py.

Referensi proposal Bab 4, Tahap 2: Intent Classification + Entity Extraction
"""

import logging
from google.genai import types
from pydantic import BaseModel

from app.pipeline.gemini_client import generate_content
from app.schemas.pipeline import EntityResult, IntentEntityResult, IntentType

logger = logging.getLogger(__name__)

# Model dipin eksplisit — lihat penjelasan di docstring modul.
_GEMINI_MODEL = "gemini-3.5-flash-lite"


# ============================================================
# Gemini client — lazy singleton (pola konsisten dengan supabase_client.py)
# ============================================================

# ============================================================
# Schema untuk structured output.
#
# SENGAJA dipisah dari IntentEntityResult (schemas/pipeline.py) — raw_text
# TIDAK diminta ke Gemini sama sekali, kita isi sendiri dari input asli,
# supaya tidak ada risiko Gemini memparafrase ulang teks pelanggan.
# ============================================================

class _GeminiEntitySchema(BaseModel):
    product_name: str | None = None
    quantity: int | None = None
    offered_price: float | None = None
    target_product_category: str | None = None


class _GeminiExtractionSchema(BaseModel):
    intent: IntentType
    entities: _GeminiEntitySchema
    confidence: float


# ============================================================
# Prompt system — tidak perlu lagi mendeskripsikan format JSON manual;
# response_schema yang mem-force struktur output. Prompt cukup berisi
# panduan semantik (kapan intent apa, cara baca angka harga).
# ============================================================

_SYSTEM_PROMPT = """Kamu adalah AI ekstraksi intent dan entitas untuk sistem penjualan UMKM Indonesia.
Analisis pesan pelanggan berikut dan ekstrak intent serta entitas yang relevan.

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

Panduan entitas:
- offered_price: ekstrak HANYA angka numerik murni. "150rb" berarti 150000. "150.000" berarti 150000.
- Pesan dalam bahasa campur (Indonesia + slang + typo) adalah normal, tangani dengan baik.
- confidence: seberapa yakin kamu dengan intent yang dipilih (0.0 - 1.0).
"""


def extract_intent_entity(text: str) -> IntentEntityResult:
    """
    Ekstrak intent dan entitas dari teks pesan pelanggan.

    TIDAK PERNAH raise ke caller — kegagalan apapun (network, parsing,
    validasi) di-fallback ke intent 'lainnya' supaya satu pesan yang sulit
    diparse tidak menjatuhkan seluruh pipeline.
    """
    preview = f"{text[:80]}..." if len(text) > 80 else text
    logger.info(f"[IntentEntity] Extracting from: '{preview}'")

    try:
        response = generate_content(
            model=_GEMINI_MODEL,
            contents=f"{_SYSTEM_PROMPT}\n\nPesan pelanggan:\n\"{text}\"",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_GeminiExtractionSchema,
            ),
        )
        parsed: _GeminiExtractionSchema | None = response.parsed
        if parsed is None:
            raise ValueError("response.parsed kosong — output tidak memenuhi schema.")

    except Exception as exc:
        logger.error(f"[IntentEntity] Gemini error/parse failure: {exc}")
        return _fallback_result(text)

    result = IntentEntityResult(
        intent=parsed.intent,
        entities=EntityResult(
            product_name=parsed.entities.product_name,
            quantity=parsed.entities.quantity,
            offered_price=parsed.entities.offered_price,
            target_product_category=parsed.entities.target_product_category,
        ),
        confidence=parsed.confidence,
        raw_text=text,
    )

    logger.info(
        f"[IntentEntity] intent={result.intent.value} | "
        f"product={result.entities.product_name} | "
        f"offered={result.entities.offered_price} | "
        f"confidence={result.confidence:.2f}"
    )
    return result


def _fallback_result(text: str) -> IntentEntityResult:
    """
    Fallback saat Gemini gagal — kembalikan intent 'lainnya' daripada crash
    pipeline. Sistem tetap bisa merespons (meski kurang akurat) → lebih baik
    daripada error 500 di tengah demo.
    """
    logger.warning("[IntentEntity] Using fallback result (lainnya).")
    return IntentEntityResult(
        intent=IntentType.LAINNYA,
        entities=EntityResult(),
        confidence=0.0,
        raw_text=text,
    )
