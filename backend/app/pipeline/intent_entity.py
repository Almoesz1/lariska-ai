"""
LARISKA AI — Sprint 4A (QA Patch Refined)
Intent Classification + Entity Extraction — Tahap 2 AI Pipeline

Desain penting:
- LLM HANYA bertugas ekstraksi intent/entity di tahap ini.
- LLM TIDAK PERNAH menentukan harga, diskon, atau keputusan bisnis apapun
  (itu tugas Sales Brain Sprint 5A, lewat Adaptive Scoring Engine).
- Output selalu divalidasi Pydantic sebelum diteruskan ke pipeline.
- Kegagalan apapun (network, parsing, validasi) di-fallback ke intent
  'lainnya', TIDAK PERNAH crash — graceful degradation.

Referensi proposal Bab 4, Tahap 2: Intent Classification + Entity Extraction
"""

import logging
from typing import Optional
from google.genai import types
from pydantic import BaseModel

from app.core.config import settings
from app.pipeline.gemini_client import generate_content
from app.schemas.pipeline import EntityResult, IntentEntityResult, IntentType

logger = logging.getLogger(__name__)

# Model dipin eksplisit sesuai panduan Google SDK untuk task terstruktur/ekstraksi
def _get_model_name() -> str:
    return getattr(settings, "gemini_model", "gemini-3.5-flash-lite")


# ============================================================
# Schema untuk structured output via Pydantic
# ============================================================

class _GeminiEntitySchema(BaseModel):
    product_name: Optional[str] = None
    quantity: Optional[int] = None
    offered_price: Optional[float] = None
    target_product_category: Optional[str] = None


class _GeminiExtractionSchema(BaseModel):
    intent: IntentType
    entities: _GeminiEntitySchema
    confidence: float


# ============================================================
# System Instruction untuk Gemini Structured Output
# ============================================================

_SYSTEM_PROMPT = """Kamu adalah AI ekstraksi intent dan entitas terdepan untuk sistem penjualan e-commerce / UMKM Indonesia.
Analisis pesan pelanggan (termasuk hasil Speech-to-Text Voice Note yang mungkin mengandung typo atau kata tergabung) dan ekstrak intent serta entitas secara presisi.

PANDUAN INTENT:
- tanya_harga: pelanggan bertanya harga produk
- nego: pelanggan menawar harga (ada kata 'boleh kurang', 'harga mati?', 'diskon', angka penawaran, dll)
- tanya_stok: pelanggan bertanya apakah produk tersedia/ready/ukuran ready
- komplain: pelanggan mengadukan masalah (produk rusak, pengiriman terlambat, dll)
- checkout: pelanggan menyatakan mau beli / setuju dengan harga / minta invoice.
  Variasi bahasa lisan/STT seperti "cekot", "cekout", "chekout", "mana linknya",
  dan "lanjut bayar" juga berarti checkout jika konteks produk sudah ada.
- tanya_produk: pelanggan bertanya detail produk (bahan, ukuran, warna, spesifikasi) atau mengoreksi/mengklarifikasi produk yang dimaksud
- rekomendasi: pelanggan minta saran produk atau mencari produk tertentu
- greeting: salam pembuka tanpa pertanyaan spesifik
- lainnya: tidak masuk kategori lain

PANDUAN EKSTRAKSI & KOREKSI RALAT (SANGAT PENTING):
1. PENANGANAN KALIMAT KOREKSI / RALAT:
   - Jika pelanggan mengoreksi/meralat nama produk (misal: 'maksud saya X bukan Y', 'salah, harusnya X', 'bukan A tapi B', 'bukan X ya', 'salah ketik maksudnya X'), kamu HARUS mengambil produk X (produk sasaran koreksi/yang dimaksud) dan MENGABAIKAN produk Y (produk yang disangkal/salah).
   - Contoh: 'maksud saya sepatulari ke bukan sepatulah' -> produk yang dimaksud adalah 'sepatu lari'.
   - Jika pesan adalah koreksi produk, pilih intent 'tanya_produk' atau 'rekomendasi' (atau 'nego'/'tanya_harga' jika mengandung unsur nego/harga).

2. NORMALISASI TYPO & KATA GABUNGAN HASIL STT VOICE NOTE:
   - Voice Note STT sering menghasilkan kata tergabung atau typo fonetik. Kamu wajib menormalisasi kata tersebut menjadi istilah produk baku Indonesia dengan spasi yang benar.
   - Contoh normalisasi:
     * 'sepatulari' / 'sepatulari ke' -> 'sepatu lari'
     * 'kemejabatik' -> 'kemeja batik'
     * 'kaospolos' -> 'kaos polos'
     * 'sepatubola' -> 'sepatu bola'
     * 'celanachino' -> 'celana chino'

3. ENTITAS LAINNYA:
   - offered_price: Angka numerik murni penawaran (contoh: '150rb' -> 150000).
   - quantity: Jumlah barang yang ingin dibeli.
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

    model_name = _get_model_name()
    try:
        response = generate_content(
            model=model_name,
            contents=f"Pesan pelanggan:\n\"{text}\"",
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=_GeminiExtractionSchema,
            ),
        )
        parsed: Optional[_GeminiExtractionSchema] = getattr(response, "parsed", None)
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
    Fallback saat Gemini gagal — kembalikan intent 'lainnya' daripada crash pipeline.
    """
    logger.warning("[IntentEntity] Using fallback result (lainnya).")
    return IntentEntityResult(
        intent=IntentType.LAINNYA,
        entities=EntityResult(),
        confidence=0.0,
        raw_text=text,
    )
