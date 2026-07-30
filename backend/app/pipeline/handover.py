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
3. Mengubah status percakapan menjadi `handover` di Supabase dan mengirim notifikasi real-time.

Prinsip: Handover adalah safety net agar pengalaman pelanggan tetap terjaga
dan tidak terjebak dalam loop percakapan AI yang tidak produktif.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Tuple
from pydantic import BaseModel, Field
from supabase import Client

from app.schemas.pipeline import (
    ConversationContext,
    IntentEntityResult,
    IntentType,
    EmotionType,
)

logger = logging.getLogger(__name__)

# Batas maksimum putaran nego sebelum dialihkan ke manusia jika belum closing
MAX_NEGOTIATION_ROUNDS = 3

# Ambang batas kepercayaan intent model (0.0 - 1.0)
MIN_CONFIDENCE_THRESHOLD = 0.60


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
) -> HandoverEvaluation:
    """
    Evaluasi murni (pure function) untuk menentukan perlunya handover.
    
    Rule Hierarchy:
    1. CRITICAL: Intent eksplisit minta admin/human agent.
    2. HIGH: Sentimen emosi marah/frustrasi berat.
    3. NORMAL: Putaran negosiasi melebihi batas (deadlock).
    4. LOW: Confidence score intent terlalu rendah / ambigu.
    """
    # Rule 1: Permintaan eksplisit ke manusia
    if intent_result.intent == IntentType.HUMAN_AGENT:
        logger.info(f"[Handover] Triggered: Explicit request for human agent.")
        return HandoverEvaluation(
            should_handover=True,
            reason="Pelanggan meminta secara langsung untuk berbicara dengan admin.",
            urgency_level="high",
        )

    # Rule 2: Sentimen Emosi Buruk (Marah / Frustrasi)
    if intent_result.emotion in (EmotionType.FRUSTRATED, EmotionType.ANGRY):
        logger.warning(f"[Handover] Triggered: Negative emotion detected ({intent_result.emotion}).")
        return HandoverEvaluation(
            should_handover=True,
            reason=f"Terdeteksi emosi pelanggan {intent_result.emotion.value.upper()} saat berinteraksi.",
            urgency_level="critical" if intent_result.emotion == EmotionType.ANGRY else "high",
        )

    # Rule 3: Negosiasi Deadlock (Sudah melampaui batas maksimum putaran)
    if context.negotiation_round >= MAX_NEGOTIATION_ROUNDS:
        logger.info(
            f"[Handover] Triggered: Max negotiation rounds ({context.negotiation_round}) reached."
        )
        return HandoverEvaluation(
            should_handover=True,
            reason=f"Negosiasi mencapai {context.negotiation_round} putaran tanpa kesepakatan final.",
            urgency_level="normal",
        )

    # Rule 4: Confidence Score Rendah / Tidak Yakin
    if intent_result.confidence < MIN_CONFIDENCE_THRESHOLD:
        logger.info(
            f"[Handover] Triggered: Low model confidence ({intent_result.confidence:.2f})."
        )
        return HandoverEvaluation(
            should_handover=True,
            reason=f"Tingkat pemahaman AI di bawah standar safe threshold ({intent_result.confidence:.2f}).",
            urgency_level="low",
        )

    return HandoverEvaluation(should_handover=False, reason=None, urgency_level="normal")


def execute_handover(
    supabase: Client,
    conversation_id: str,
    evaluation: HandoverEvaluation,
) -> dict:
    """
    Eksekusi proses handover ke database:
    1. Update status `conversations` menjadi 'handover'
    2. Catat log eskalasi di tabel system / messages
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    # Update status percakapan agar AI berhenti membalas secara otomatis
    conv_res = (
        supabase.table("conversations")
        .update({
            "status": "handover",
            "updated_at": now_iso,
        })
        .eq("id", conversation_id)
        .execute()
    )

    # Catat pesan sistem internal mengenai alasan eskalasi
    system_msg = (
        supabase.table("messages")
        .insert({
            "conversation_id": conversation_id,
            "sender_type": "admin",
            "content_type": "text",
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
    Jika True, pipeline AI harus membiarkan pesan tanpa balasan otomatis.
    """
    res = (
        supabase.table("conversations")
        .select("status")
        .eq("id", conversation_id)
        .maybe_single()
        .execute()
    )

    if res and res.data:
        return res.data.get("status") in ("handover", "admin_takeover")
    return False