"""
LARISKA AI — Pipeline Pydantic Schemas
Definisi tipe data terstruktur yang mengalir antar tahap AI Pipeline.

Urutan pipeline:
  STT → IntentEntityResult → EmotionResult → ScoringDecision → PipelineResponse

Semua model ini dipakai sebagai 'kontrak data' antar modul pipeline,
sekaligus jadi dokumentasi hidup arsitektur sistem.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ============================================================
# ENUMS — Nilai valid per domain
# ============================================================

class IntentType(str, Enum):
    TANYA_HARGA     = "tanya_harga"
    NEGO            = "nego"
    TANYA_STOK      = "tanya_stok"
    KOMPLAIN        = "komplain"
    CHECKOUT        = "checkout"
    TANYA_PRODUK    = "tanya_produk"
    REKOMENDASI     = "rekomendasi"
    GREETING        = "greeting"
    LAINNYA         = "lainnya"


class EmotionType(str, Enum):
    MARAH       = "marah"
    NETRAL      = "netral"
    SANTAI      = "santai"
    BURU_BURU   = "buru_buru"
    SENANG      = "senang"


class ScoringDecisionType(str, Enum):
    HOLD_PRICE      = "hold_price"
    DISCOUNT        = "discount"
    BONUS           = "bonus"
    COUNTER_OFFER   = "counter_offer"
    # PENTING: NO_NEGO SENGAJA TIDAK ADA di CHECK constraint
    # negotiation_logs.ai_decision (schema.sql, final sejak Sprint 2A) —
    # cuma 'hold_price'/'discount'/'bonus'/'counter_offer' yang diizinkan.
    # Keputusan bertipe NO_NEGO TIDAK BOLEH ditulis ke tabel negotiation_logs
    # sama sekali. Guard ada di state_tracking.py::save_negotiation_log().
    # Kalau menambah pemanggil save_negotiation_log() baru di sprint
    # manapun, JANGAN asumsikan semua ScoringDecisionType valid untuk DB.
    NO_NEGO         = "no_nego"  # Untuk non-negosiasi intent — TIDAK ditulis ke DB


# ============================================================
# TAHAP 1 — STT (Speech-to-Text)
# ============================================================

class STTResult(BaseModel):
    """Output modul stt.py — teks transkripsi dari voice note."""
    text: str
    language: str = "id"
    is_voice_input: bool = False
    duration_seconds: Optional[float] = None


# ============================================================
# TAHAP 2 — Intent & Entity Extraction
# ============================================================

class EntityResult(BaseModel):
    """Entity yang diekstrak dari pesan pelanggan."""
    product_name: Optional[str] = Field(None, description="Nama produk yang disebutkan pelanggan")
    quantity: Optional[int] = Field(None, description="Jumlah unit yang diminta")
    offered_price: Optional[float] = Field(None, description="Harga yang ditawarkan pelanggan saat nego")
    target_product_category: Optional[str] = Field(None, description="Kategori produk bila tanya umum")


class IntentEntityResult(BaseModel):
    """Output modul intent_entity.py — intent + entity terstruktur dari teks."""
    intent: IntentType
    entities: EntityResult
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    raw_text: str


# ============================================================
# TAHAP 4b — Emotion Classifier
# ============================================================

class EmotionResult(BaseModel):
    """Output modul emotion.py — emosi terdeteksi dari teks."""
    emotion: EmotionType
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    tone_hint: str = Field(
        default="",
        description="Petunjuk singkat untuk LLM: cara menyesuaikan nada balasan"
    )


# ============================================================
# TAHAP 4a — Adaptive Scoring Engine
# ============================================================

class ScoringInput(BaseModel):
    """
    Fitur input untuk model LightGBM Adaptive Scoring Engine.
    Harus PERSIS sama dengan feature_names di training_metadata.json:
    ['margin_pct', 'stock_ratio', 'customer_loyalty',
     'discount_requested_pct', 'hour_of_day', 'is_peak_hour']
    """
    margin_pct: float = Field(..., ge=0.0, le=1.0,
        description="(price - floor_price) / price")
    stock_ratio: float = Field(..., ge=0.0, le=1.0,
        description="stock_sekarang / stock_awal (atau 1.0 jika tidak diketahui)")
    customer_loyalty: float = Field(..., ge=0.0, le=1.0,
        description="Skor loyalitas pelanggan: 0=baru, 1=sangat loyal")
    discount_requested_pct: float = Field(..., ge=0.0, le=1.0,
        description="Diskon yang diminta pelanggan: (price - offer) / price")
    hour_of_day: int = Field(..., ge=0, le=23,
        description="Jam saat ini (0-23)")
    is_peak_hour: int = Field(..., ge=0, le=1,
        description="1 jika jam 19-22 (peak hour), else 0")


class ScoringDecision(BaseModel):
    """Output Adaptive Scoring Engine — keputusan bisnis yang akan dieksekusi."""
    decision: ScoringDecisionType
    final_price: float = Field(..., description="Harga final yang ditawarkan AI (>= floor_price selalu)")
    discount_amount: float = Field(default=0.0, ge=0.0)
    discount_pct: float = Field(default=0.0, ge=0.0, le=1.0)
    model_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    floor_price_enforced: bool = Field(
        default=True,
        description="Selalu True — guardrail proposal Bab 9"
    )
    reasoning: str = Field(default="", description="Alasan singkat keputusan (untuk logging)")


# ============================================================
# OUTPUT AKHIR — Pipeline Response ke WhatsApp
# ============================================================

class PipelineResponse(BaseModel):
    """
    Output akhir dari response_generator.py — siap dikirim ke WhatsApp.
    Juga berisi metadata lengkap untuk logging & dashboard.
    """
    reply_text: str = Field(..., description="Teks balasan yang dikirim ke pelanggan")
    intent: IntentType
    emotion: EmotionType
    scoring_decision: Optional[ScoringDecision] = None
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    recommended_product_ids: list[str] = Field(default_factory=list)


# ============================================================
# CONTEXT — Data konteks percakapan untuk pipeline
# ============================================================

class ConversationContext(BaseModel):
    """
    Data konteks yang dikumpulkan state_tracking.py dan diteruskan ke Sales Brain.
    Menggabungkan state database + produk relevan untuk satu langkah pipeline.
    """
    conversation_id: str
    customer_id: str
    whatsapp_number: str
    customer_name: Optional[str] = None
    total_orders: int = Field(default=0, description="Jumlah order historis pelanggan")
    # Produk yang sedang dibahas
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    product_price: Optional[float] = None
    product_floor_price: Optional[float] = None
    product_stock: Optional[int] = None
    product_category: Optional[str] = None
    # Riwayat negosiasi dalam sesi ini
    negotiation_round: int = Field(default=0, description="Putaran nego sesi ini")
    last_ai_decision: Optional[ScoringDecisionType] = None