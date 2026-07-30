"""
LARISKA AI — Sprint 4A (QA Patch)
Conversation State Tracking — Tahap 3 AI Pipeline

Perubahan dari versi awal setelah Quality Gate review:
- save_negotiation_log() sekarang punya GUARD eksplisit: ai_decision yang
  bukan salah satu dari hold_price/discount/bonus/counter_offer (termasuk
  ScoringDecisionType.NO_NEGO) TIDAK akan pernah ditulis ke database. Tanpa
  guard ini, insert akan ditolak Postgres (CHECK constraint di schema.sql,
  final sejak Sprint 2A) dan request gagal dengan 500 generic — skenario
  yang SANGAT mungkin terjadi karena intent non-nego (greeting, tanya_stok,
  dst) adalah kasus umum, bukan edge case.
- get_or_create_customer() sekarang menangani race condition: kalau dua
  pesan nyaris bersamaan dari nomor WA yang sama (mis. webhook retry dari
  Meta) memicu dua insert customer baru, yang kalah race akan kena UNIQUE
  constraint violation (whatsapp_number, schema.sql) — sebelumnya ini
  crash, sekarang di-re-query dan tetap mengembalikan customer yang benar.
  Pola ini sama dengan yang sudah dipakai dashboard_api.py::create_customer.

Bertanggung jawab untuk:
1. Membuat atau melanjutkan sesi percakapan (tabel `conversations`)
2. Menyimpan setiap pesan masuk ke tabel `messages`
3. Menyusun ConversationContext (data produk, loyalitas customer, riwayat nego)
   yang diteruskan ke Sales Brain
4. Mencari produk yang relevan berdasarkan entitas dari intent_entity

Prinsip: state tracking bersifat stateless per-call — semua state disimpan di Supabase,
bukan di memory aplikasi. Ini penting untuk horizontal scaling dan demo yang reliable.

Referensi proposal Bab 4, Tahap 3: Conversation State Tracking (disimpan di database per nomor WA)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from supabase import Client

from app.schemas.pipeline import (
    ConversationContext,
    IntentEntityResult,
    IntentType,
    EmotionType,
    ScoringDecisionType,
)

logger = logging.getLogger(__name__)

# Nilai ai_decision yang diizinkan CHECK constraint negotiation_logs di
# schema.sql (final sejak Sprint 2A) — dipakai save_negotiation_log() untuk
# guard sebelum insert. Kalau schema.sql berubah, sinkronkan set ini.
_VALID_DB_NEGOTIATION_DECISIONS = {"hold_price", "discount", "bonus", "counter_offer"}


# ============================================================
# CUSTOMER — get or create
# ============================================================

def get_or_create_customer(supabase: Client, whatsapp_number: str) -> dict:
    """
    Ambil customer berdasarkan nomor WA, atau buat baru jika belum ada.
    Ini titik entry setiap pesan WhatsApp masuk.
    """
    res = (
        supabase.table("customers")
        .select("id, whatsapp_number, name, created_at")
        .eq("whatsapp_number", whatsapp_number)
        .is_("deleted_at", "null")
        .maybe_single()
        .execute()
    )

    if res and res.data:
        logger.info(f"[StateTracking] Customer found: {res.data['id']} ({whatsapp_number})")
        return res.data

    try:
        new_customer = supabase.table("customers").insert({
            "whatsapp_number": whatsapp_number,
            "name": None,  # Akan diupdate saat pelanggan memperkenalkan diri
        }).execute()
        logger.info(f"[StateTracking] New customer created: {new_customer.data[0]['id']} ({whatsapp_number})")
        return new_customer.data[0]

    except Exception as exc:
        # Race condition: customer sudah dibuat request lain di antara SELECT
        # dan INSERT kita (mis. webhook retry). whatsapp_number UNIQUE
        # constraint (schema.sql) menolak insert kedua — re-query, bukan crash.
        if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
            logger.warning(
                f"[StateTracking] Race saat create customer {whatsapp_number}, re-query."
            )
            res = (
                supabase.table("customers")
                .select("id, whatsapp_number, name, created_at")
                .eq("whatsapp_number", whatsapp_number)
                .maybe_single()
                .execute()
            )
            if res and res.data:
                return res.data
        raise


# ============================================================
# CONVERSATION — get active or create new
# ============================================================

def get_or_create_conversation(supabase: Client, customer_id: str) -> dict:
    """
    Ambil sesi percakapan yang sedang aktif (status='open') untuk customer ini.
    Jika tidak ada → buat sesi baru.

    Policy: satu customer hanya boleh punya satu sesi open sekaligus.
    CATATAN: policy ini belum di-enforce lewat DB constraint (partial unique
    index), jadi secara teori masih ada celah race condition serupa
    get_or_create_customer kalau 2 pesan datang nyaris bersamaan. Risiko
    rendah untuk pola pemakaian WhatsApp normal (1 nomor = 1 pesan pada satu
    waktu) — dicatat sebagai item roadmap, bukan diperbaiki sekarang supaya
    tidak overengineering di luar skenario yang realistis terjadi saat demo.
    """
    res = (
        supabase.table("conversations")
        .select("id, customer_id, status, started_at")
        .eq("customer_id", customer_id)
        .eq("status", "open")
        .order("started_at", desc=True)
        .limit(1)
        .execute()
    )

    if res and res.data:
        conv = res.data[0]
        logger.info(f"[StateTracking] Active conversation: {conv['id']}")
        return conv

    new_conv = supabase.table("conversations").insert({
        "customer_id": customer_id,
        "channel": "whatsapp",
        "status": "open",
    }).execute()

    logger.info(f"[StateTracking] New conversation: {new_conv.data[0]['id']}")
    return new_conv.data[0]


def close_conversation(supabase: Client, conversation_id: str) -> None:
    """Tutup sesi percakapan — dipanggil saat checkout berhasil atau timeout."""
    supabase.table("conversations").update({
        "status": "closed",
        "ended_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", conversation_id).execute()
    logger.info(f"[StateTracking] Conversation closed: {conversation_id}")


# ============================================================
# MESSAGE — save to database
# ============================================================

def save_message(
    supabase: Client,
    conversation_id: str,
    sender_type: str,  # 'customer' | 'ai' | 'admin'
    content_type: str,  # 'text' | 'voice'
    raw_text: Optional[str] = None,
    voice_url: Optional[str] = None,
    intent: Optional[str] = None,
    entities: Optional[dict] = None,
    sentiment: Optional[str] = None,
) -> dict:
    """
    Simpan satu pesan ke tabel `messages`.
    Kolom intent/entities/sentiment diisi setelah pipeline selesai (untuk pesan dari customer).
    """
    data = {
        "conversation_id": conversation_id,
        "sender_type": sender_type,
        "content_type": content_type,
        "raw_text": raw_text,
        "voice_url": voice_url,
        "intent": intent,
        "entities": entities or {},
        "sentiment": sentiment,
    }
    res = supabase.table("messages").insert(data).execute()
    logger.info(
        f"[StateTracking] Message saved: id={res.data[0]['id']} "
        f"sender={sender_type} intent={intent}"
    )
    return res.data[0]


# ============================================================
# NEGOTIATION LOG — save scoring decision
# ============================================================

def save_negotiation_log(
    supabase: Client,
    conversation_id: str,
    product_id: str,
    customer_offer_price: Optional[float],
    ai_decision: str,
    ai_offer_price: Optional[float],
    floor_price_snapshot: float,
    model_confidence: Optional[float] = None,
    outcome: str = "pending",
) -> dict:
    """
    Catat satu putaran negosiasi ke tabel `negotiation_logs`.
    Data ini menjadi sumber AI Evaluation Sprint 8 dan dataset retraining
    model di masa depan.

    GUARD: ai_decision HARUS salah satu dari _VALID_DB_NEGOTIATION_DECISIONS
    (sesuai CHECK constraint schema.sql). ScoringDecisionType.NO_NEGO dan
    nilai lain di luar itu TIDAK ditulis ke database — dikembalikan dict
    kosong, bukan exception, supaya caller (Sales Brain Sprint 5A) tidak
    perlu try/except khusus untuk kasus normal "intent ini memang bukan
    negosiasi, tidak perlu dicatat".
    """
    if ai_decision not in _VALID_DB_NEGOTIATION_DECISIONS:
        logger.debug(
            f"[StateTracking] Skip save_negotiation_log: ai_decision='{ai_decision}' "
            f"bukan keputusan nego valid untuk database — tidak ditulis."
        )
        return {}

    data = {
        "conversation_id": conversation_id,
        "product_id": product_id,
        "customer_offer_price": customer_offer_price,
        "ai_decision": ai_decision,
        "ai_offer_price": ai_offer_price,
        "floor_price_snapshot": floor_price_snapshot,
        "model_confidence": model_confidence,
        "outcome": outcome,
    }
    res = supabase.table("negotiation_logs").insert(data).execute()
    logger.info(
        f"[StateTracking] Negotiation log: decision={ai_decision} "
        f"offer={customer_offer_price} → ai={ai_offer_price}"
    )
    return res.data[0]


# ============================================================
# PRODUCT LOOKUP — cari produk berdasarkan nama
# ============================================================

def find_product_by_name(supabase: Client, product_name: str) -> Optional[dict]:
    """
    Cari produk berdasarkan nama (case-insensitive partial match).
    Dipakai ketika pelanggan menyebut nama produk dalam pesan.

    CATATAN SCOPE: ini pencarian literal substring, BUKAN recommendation
    engine (itu retrieval.py berbasis pgvector, Sprint 5A). Kalau ada
    beberapa produk yang match, tidak ada ranking relevansi — hasil
    pertama yang Postgres kembalikan yang dipakai. Cukup untuk kasus
    pelanggan menyebut nama produk spesifik; tidak cukup untuk "carikan
    produk yang mirip".

    Fallback: kalau tidak ketemu, return None dan pipeline akan minta klarifikasi.
    """
    if not product_name:
        return None

    res = (
        supabase.table("products")
        .select("id, name, description, category, price, floor_price, stock, is_active")
        .ilike("name", f"%{product_name}%")
        .is_("deleted_at", "null")
        .eq("is_active", True)
        .limit(1)
        .execute()
    )

    if res and res.data:
        logger.info(f"[StateTracking] Product found: '{res.data[0]['name']}' for query '{product_name}'")
        return res.data[0]

    logger.warning(f"[StateTracking] Product not found for: '{product_name}'")
    return None


def get_customer_order_count(supabase: Client, customer_id: str) -> int:
    """
    Hitung total order historis pelanggan (untuk skor loyalitas).
    Dipakai sebagai fitur input Adaptive Scoring Engine.
    """
    res = (
        supabase.table("orders")
        .select("id", count="exact")
        .eq("customer_id", customer_id)
        .in_("status", ["paid", "shipped", "completed"])
        .execute()
    )
    count = res.count or 0
    logger.debug(f"[StateTracking] Customer {customer_id} has {count} completed orders.")
    return count


def get_negotiation_round(supabase: Client, conversation_id: str) -> int:
    """
    Hitung berapa kali nego sudah terjadi dalam sesi ini.
    Dipakai untuk membatasi putaran nego (policy bisnis).
    """
    res = (
        supabase.table("negotiation_logs")
        .select("id", count="exact")
        .eq("conversation_id", conversation_id)
        .execute()
    )
    return res.count or 0


def get_last_ai_decision(supabase: Client, conversation_id: str) -> Optional[str]:
    """
    Ambil keputusan AI terakhir dalam sesi ini untuk context Sales Brain.
    """
    res = (
        supabase.table("negotiation_logs")
        .select("ai_decision")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if res and res.data:
        return res.data[0]["ai_decision"]
    return None


# ============================================================
# MAIN — Build ConversationContext (entry point dari webhook)
# ============================================================

def build_context(
    supabase: Client,
    whatsapp_number: str,
    intent_result: IntentEntityResult,
) -> ConversationContext:
    """
    Entry point utama State Tracking.
    Dipanggil dari whatsapp_webhook.py setelah intent_entity selesai.

    Langkah:
    1. Get/create customer
    2. Get/create conversation
    3. Lookup produk dari entitas
    4. Hitung loyalitas & riwayat nego
    5. Return ConversationContext lengkap untuk Sales Brain
    """
    # Step 1: Customer
    customer = get_or_create_customer(supabase, whatsapp_number)
    customer_id = customer["id"]

    # Step 2: Conversation
    conversation = get_or_create_conversation(supabase, customer_id)
    conversation_id = conversation["id"]

    # Step 3: Hitung loyalitas (0.0 - 1.0 berdasarkan jumlah order)
    total_orders = get_customer_order_count(supabase, customer_id)
    # Skala loyalitas: 0 order = 0.0, 10+ order = 1.0 (capped)
    customer_loyalty = min(total_orders / 10.0, 1.0)

    # Step 4: Lookup produk jika disebutkan
    product = None
    product_name_query = intent_result.entities.product_name
    if product_name_query:
        product = find_product_by_name(supabase, product_name_query)

    # Step 5: Riwayat nego
    negotiation_round = get_negotiation_round(supabase, conversation_id)
    last_decision_raw = get_last_ai_decision(supabase, conversation_id)
    last_decision = None
    if last_decision_raw:
        try:
            last_decision = ScoringDecisionType(last_decision_raw)
        except ValueError:
            pass

    context = ConversationContext(
        conversation_id=conversation_id,
        customer_id=customer_id,
        whatsapp_number=whatsapp_number,
        customer_name=customer.get("name"),
        total_orders=total_orders,
        product_id=product["id"] if product else None,
        product_name=product["name"] if product else None,
        product_price=float(product["price"]) if product else None,
        product_floor_price=float(product["floor_price"]) if product else None,
        product_stock=product["stock"] if product else None,
        product_category=product["category"] if product else None,
        negotiation_round=negotiation_round,
        last_ai_decision=last_decision,
    )

    logger.info(
        f"[StateTracking] Context built: "
        f"customer={customer_id[:8]} "
        f"conv={conversation_id[:8]} "
        f"product={context.product_name} "
        f"loyalty={customer_loyalty:.2f} "
        f"nego_round={negotiation_round}"
    )
    return context