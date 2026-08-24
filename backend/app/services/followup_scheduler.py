"""
LARISKA AI — Automated Follow-Up & Re-Engagement Engine

Bertanggung jawab untuk:
1. Memindai (scan) percakapan menggantung (idle/abandoned) yang membutuhkan interaksi lanjutan.
2. Memilih templat / trigger balasan AI berdasarkan status negosiasi terakhir.
3. Menghindari spam dengan membatasi frekuensi dan jumlah maksimum follow-up per percakapan.
4. Memperbarui status percakapan setelah pesan follow-up berhasil dijadwalkan / dikirim.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from supabase import Client

logger = logging.getLogger(__name__)

# Konfigurasi waktu idle default (dalam jam) dan batas kirim
DEFAULT_IDLE_HOURS = 24
MAX_FOLLOWUP_COUNT = 2


class FollowUpCandidate(BaseModel):
    """Representasi calon percakapan yang perlu di-follow up."""
    conversation_id: str
    phone_number: str
    last_message_at: datetime
    negotiation_status: Optional[str] = "idle"
    followup_count: int = 0
    last_offered_price: Optional[float] = None
    product_name: Optional[str] = None


class FollowUpMessageResult(BaseModel):
    """Hasil pembuatan pesan follow-up."""
    conversation_id: str
    message_text: str
    followup_type: str  # 'gentle_reminder' | 'discount_incentive' | 'closing_check'


def find_idle_conversations(
    supabase: Client,
    idle_hours: int = DEFAULT_IDLE_HOURS,
    max_limit: int = 50,
) -> List[FollowUpCandidate]:
    """
    Mencari daftar percakapan aktif yang tidak mendapatkan respon dari pembeli
    selama kurun waktu `idle_hours`.
    
    Kriteria:
    - Status percakapan = 'active' (bukan 'handover' atau 'closed')
    - followup_count < MAX_FOLLOWUP_COUNT
    - Waktu update terakhir > idle_hours yang lalu
    """
    cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=idle_hours)).isoformat()

    # Query percakapan menggantung dari database
    res = (
        supabase.table("conversations")
        .select("id, phone_number, updated_at, followup_count, negotiation_status, context_data")
        .eq("status", "active")
        .lt("updated_at", cutoff_time)
        .lt("followup_count", MAX_FOLLOWUP_COUNT)
        .limit(max_limit)
        .execute()
    )

    candidates: List[FollowUpCandidate] = []
    if not res.data:
        return candidates

    for row in res.data:
        context = row.get("context_data") or {}
        candidates.append(
            FollowUpCandidate(
                conversation_id=row["id"],
                phone_number=row["phone_number"],
                last_message_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00")),
                negotiation_status=row.get("negotiation_status", "idle"),
                followup_count=row.get("followup_count", 0),
                last_offered_price=context.get("last_offered_price"),
                product_name=context.get("product_name"),
            )
        )

    logger.info(f"[FollowUpScheduler] Ditemukan {len(candidates)} percakapan idle yang siap di-follow up.")
    return candidates


def generate_followup_message(candidate: FollowUpCandidate) -> FollowUpMessageResult:
    """
    Menghasilkan draf pesan follow-up dinamis berdasarkan konteks terakhir negosiasi.
    """
    # Follow-up Pertama: Gentle Reminder
    if candidate.followup_count == 0:
        if candidate.product_name and candidate.last_offered_price:
            text = (
                f"Halo Kak! 👋 Mau memastikan kembali untuk penawaran produk *{candidate.product_name}* "
                f"di harga Rp {candidate.last_offered_price:,.0f} kemarin.\n\n"
                f"Apakah ada hal yang ingin ditanyakan atau mau langsung kami proses sekarang?"
            )
        else:
            text = (
                "Halo Kak! 👋 Ada yang bisa LARISKA bantu lagi terkait produk yang Kakak cari kemarin? "
                "Stok kami terbatas, lho!"
            )
        followup_type = "gentle_reminder"

    # Follow-up Kedua: Closing Check
    else:
        if candidate.product_name:
            text = (
                f"Halo Kak! Penawaran spesial untuk *{candidate.product_name}* masih berlaku ya hari ini. 😊\n"
                f"Jika Kakak ada kendala atau butuh informasi lebih lanjut, silakan tanyakan ke LARISKA ya!"
            )
        else:
            text = (
                "Halo Kak! Hanya ingin memastikan apakah pertanyaannya sudah terjawab? "
                "Siap bantu kustomisasi atau rekomendasikan produk terbaik untuk Kakak!"
            )
        followup_type = "closing_check"

    return FollowUpMessageResult(
        conversation_id=candidate.conversation_id,
        message_text=text,
        followup_type=followup_type,
    )


def process_scheduled_followups(supabase: Client) -> List[Dict[str, Any]]:
    """
    Fungsi eksekusi utama (biasa dipanggil via CRON job atau Background Task FastAPI).
    1. Scan percakapan menggantung.
    2. Buat pesan follow-up.
    3. Simpan pesan di database `messages`.
    4. Update jumlah `followup_count` dan timestamp percakapan.
    """
    idle_candidates = find_idle_conversations(supabase)
    processed_results = []

    now_iso = datetime.now(timezone.utc).isoformat()

    for candidate in idle_candidates:
        msg_result = generate_followup_message(candidate)

        # 1. Insert pesan AI follow-up ke database messages
        msg_res = (
            supabase.table("messages")
            .insert({
                "conversation_id": candidate.conversation_id,
                "sender_type": "bot",
                "content_type": "text",
                "raw_text": msg_result.message_text,
                "intent": "followup_reengagement",
                "entities": {"followup_type": msg_result.followup_type},
            })
            .execute()
        )

        # 2. Update status percakapan (+1 count, update timestamp)
        supabase.table("conversations").update({
            "followup_count": candidate.followup_count + 1,
            "updated_at": now_iso,
        }).eq("id", candidate.conversation_id).execute()

        processed_results.append({
            "conversation_id": candidate.conversation_id,
            "phone_number": candidate.phone_number,
            "followup_type": msg_result.followup_type,
            "message_id": msg_res.data[0]["id"] if msg_res.data else None,
        })

        logger.info(
            f"[FollowUpScheduler] Follow-up sent to {candidate.phone_number} "
            f"(Count: {candidate.followup_count + 1})"
        )

    return processed_results