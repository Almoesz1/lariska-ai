"""
LARISKA AI — Sprint 5B (Handover & Escalation Engine)
Human-in-the-Loop Management — Tahap 5 AI Pipeline

Bertanggung jawab untuk:
1. Menganalisis apakah percakapan memerlukan pengambilalihan oleh Admin/CS Manusia.
2. Mengevaluasi indikator eskalasi:
   - Permintaan eksplisit pelanggan (e.g. "bicara sama CS", "mana admin")
   - Emosi/sentimen negatif ekstrem (FRUSTRATED, ANGRY)
   - Kebuntuan negosiasi (melebihi batas putaran nego tanpa kesepakatan)
   - Skor kepercayaan AI/Intent berada di bawah ambang batas (low confidence)
3. Mengubah status percakapan menjadi `handed_over` di Supabase dan mengirim log sistem.

Sesuai Schema Database:
- Status Conversation: 'handed_over' (Lolos chk_conversations_status)
- Message Sender Type: 'admin' (Lolos chk_messages_sender_type)
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from supabase import Client

from app.schemas.pipeline import (
    ConversationContext,
    EmotionResult,
    IntentEntityResult,
    IntentType,
    EmotionType,
)

logger = logging.getLogger(__name__)

# Batas maksimum putaran nego sebelum dialihkan ke manusia jika belum closing
MAX_NEGOTIATION_ROUNDS = 5

# Ambang batas kepercayaan intent model (0.0 - 1.0)
MIN_CONFIDENCE_THRESHOLD = 0.60

# Emosi marah tidak otomatis berarti handover. Pelanggan sering memakai
# "gak jelas" untuk mengoreksi katalog/rekomendasi; Sales Brain harus
# meminta maaf dan memperbaiki jawaban dulu. Handover dipakai untuk masalah
# transaksi/produk yang material atau ancaman eskalasi.
_SERIOUS_COMPLAINT_PATTERNS = (
    "penipu", "penipuan", "tipu", "lapor polisi", "lapor konsumen",
    "minta refund", "belum refund", "uang saya", "ganti rugi",
    "barang rusak", "rusak parah", "barang cacat", "salah kirim",
    "pesanan belum sampai", "barang belum sampai", "tidak sesuai pesanan",
)


class HandoverEvaluation(BaseModel):
    """Hasil evaluasi apakah percakapan harus dialihkan ke Admin."""
    should_handover: bool = Field(
        ..., description="True jika percakapan wajib dialihkan ke manusia"
    )
    reason: Optional[str] = Field(
        None, description="Alasan spesifik trigger eskalasi terjadi"
    )
    urgency_level: str = Field(
        "normal", description="Tingkat urgensi eskalasi: 'low' | 'normal' | 'high' | 'critical'"
    )


def evaluate_handover(
    intent_result: IntentEntityResult,
    context: ConversationContext,
    emotion_result: Optional[EmotionResult] = None,
) -> HandoverEvaluation:
    """
    Evaluasi murni (pure function) untuk menentukan perlunya handover.
    Tahan terhadap Null/None Attribute (Defensive Programming).
    
    Rule Hierarchy:
    1. CRITICAL: Intent eksplisit minta admin/human agent.
    2. HIGH/CRITICAL: Sentimen emosi marah/frustrasi berat.
    3. NORMAL: Putaran negosiasi melebihi batas (deadlock).
    4. LOW: Confidence score intent terlalu rendah / fallback.
    """
    # ---------------------------------------------------------------------
    # Rule 1: Permintaan eksplisit ke manusia (Safe Candidate Matching)
    # ---------------------------------------------------------------------
    human_intent_candidates = {
        getattr(IntentType, attr, None)
        for attr in ("HUMAN_AGENT", "HANDOVER", "TALK_TO_AGENT", "HUMAN", "CS_AGENT")
    } - {None}

    raw_intent = getattr(intent_result, "intent", None)
    intent_val = (
        raw_intent.value
        if hasattr(raw_intent, "value")
        else str(raw_intent or "")
    )

    raw_text = (getattr(intent_result, "raw_text", "") or "").lower()
    explicit_human_phrases = (
        "admin", "cs", "customer service", "manusia", "orang asli",
        "operator", "hubungkan", "bicara sama", "ngobrol sama",
    )

    # Kata pendek seperti "cs" harus cocok sebagai kata utuh. Pencarian
    # substring membuat "5 pcs" keliru terbaca sebagai permintaan CS dan
    # memutus negosiasi yang seharusnya masih ditangani Sales Brain.
    def has_human_phrase(text: str) -> bool:
        return any(
            re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text)
            for phrase in explicit_human_phrases
        )
    is_explicit_human_request = (
        raw_intent in human_intent_candidates
        or intent_val.lower() in ("human_agent", "handover", "talk_to_agent", "human", "admin", "cs_agent")
        or has_human_phrase(raw_text)
    )

    if is_explicit_human_request:
        logger.info("[Handover] Triggered: Explicit request for human agent.")
        return HandoverEvaluation(
            should_handover=True,
            reason="Pelanggan meminta secara langsung untuk berbicara dengan admin.",
            urgency_level="high",
        )

    # Checkout adalah sinyal konversi yang eksplisit. Percakapan tidak boleh
    # dialihkan ke admin hanya karena putaran nego sebelumnya sudah banyak;
    # pelanggan harus langsung menerima invoice/link pembayaran.
    if intent_val.lower() == IntentType.CHECKOUT.value:
        return HandoverEvaluation(should_handover=False, reason=None, urgency_level="normal")

    # ---------------------------------------------------------------------
    # Rule 2: Sentimen Emosi Buruk (Marah / Frustrasi)
    # ---------------------------------------------------------------------
    emotion_val = getattr(emotion_result, "emotion", None)
    if emotion_val is not None:
        emotion_str = (
            emotion_val.value
            if hasattr(emotion_val, "value")
            else str(emotion_val)
        ).lower()

        is_price_negotiation = intent_val.lower() == IntentType.NEGO.value
        has_serious_complaint = any(pattern in raw_text for pattern in _SERIOUS_COMPLAINT_PATTERNS)
        if (
            (emotion_val == EmotionType.MARAH or emotion_str in ("marah", "frustrated", "angry"))
            and not is_price_negotiation
            and has_serious_complaint
        ):
            logger.warning(f"[Handover] Triggered: Negative emotion detected ({emotion_val}).")
            return HandoverEvaluation(
                should_handover=True,
                reason=f"Terdeteksi emosi pelanggan {emotion_str.upper()} saat berinteraksi.",
                urgency_level="critical" if emotion_str in ("marah", "angry") else "high",
            )
        if (is_price_negotiation or not has_serious_complaint) and emotion_str in ("marah", "frustrated", "angry"):
            logger.info("[Handover] Negative tone without critical issue; keep Sales Brain active for empathetic recovery.")

    # ---------------------------------------------------------------------
    # Rule 3: Negosiasi Deadlock (Sudah melampaui batas maksimum putaran)
    # ---------------------------------------------------------------------
    nego_round = getattr(context, "negotiation_round", 0) or 0
    if nego_round >= MAX_NEGOTIATION_ROUNDS:
        logger.info(
            f"[Handover] Triggered: Max negotiation rounds ({nego_round}) reached."
        )
        return HandoverEvaluation(
            should_handover=True,
            reason=f"Negosiasi mencapai {nego_round} putaran tanpa kesepakatan final.",
            urgency_level="normal",
        )

    # ---------------------------------------------------------------------
    # Rule 4: Confidence Score Rendah / Null / Fallback AI
    # Safe guard terhadap NoneType agar tidak crash saat perbandingan float
    # ---------------------------------------------------------------------
    confidence = getattr(intent_result, "confidence", None)
    if confidence is None:
        confidence = 0.0

    if confidence < MIN_CONFIDENCE_THRESHOLD:
        # Pesan singkat seperti "jadi ya?" lazim muncul setelah negosiasi.
        # Ketidakpastian NLU saja bukan alasan memutus konteks dan memaksa
        # pelanggan menunggu admin; response layer masih bisa mengklarifikasi.
        logger.info(f"[Handover] Low confidence ({confidence:.2f}); continue with safe clarification.")

    return HandoverEvaluation(should_handover=False, reason=None, urgency_level="normal")


def execute_handover(
    supabase: Client,
    conversation_id: str,
    evaluation: HandoverEvaluation,
) -> Dict[str, Any]:
    """
    Eksekusi proses handover ke database Supabase:
    1. Update status `conversations` menjadi 'handed_over' (Lolos chk_conversations_status).
    2. Catat log eskalasi sistem di tabel `messages` dengan sender_type 'admin' (Lolos chk_messages_sender_type).
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Update status percakapan di Supabase
    conv_res = (
        supabase.table("conversations")
        .update({
            "status": "handed_over",
            "updated_at": now_iso,
        })
        .eq("id", conversation_id)
        .execute()
    )

    # 2. Catat pesan log sistem internal
    system_msg = (
        supabase.table("messages")
        .insert({
            "conversation_id": conversation_id,
            "sender_type": "admin",  # Lolos constraint sender_type in ('customer', 'ai', 'admin')
            "content_type": "text",   # Lolos constraint content_type in ('text', 'voice')
            "raw_text": f"[SYSTEM ESCALATION] Handover dipicu: {evaluation.reason} (Urgency: {evaluation.urgency_level.upper()})",
            "intent": "handover_triggered",
            "entities": {"urgency": evaluation.urgency_level, "reason": evaluation.reason},
        })
        .execute()
    )

    logger.warning(
        f"[Handover] Successfully executed for conversation {conversation_id[:8]}. "
        f"Reason: {evaluation.reason}"
    )

    return {
        "status": "handover_active",
        "conversation": conv_res.data[0] if conv_res.data else {},
        "system_message": system_msg.data[0] if system_msg.data else {},
    }


def is_conversation_in_handover(supabase: Client, conversation_id: str) -> bool:
    """
    Cek cepat apakah percakapan sedang dalam mode handover/admin.
    Mengecek status 'handed_over', 'handover', maupun 'escalated'.
    """
    res = (
        supabase.table("conversations")
        .select("status")
        .eq("id", conversation_id)
        .maybe_single()
        .execute()
    )

    if res and res.data:
        current_status = res.data.get("status", "")
        return current_status in ("handed_over", "handover", "escalated")
    return False
