"""
LARISKA AI — Sprint 4A (QA Patch Refined)
Conversation State Tracking — Tahap 3 AI Pipeline

Bertanggung jawab untuk:
1. Membuat atau melanjutkan sesi percakapan (tabel `conversations`)
2. Menyimpan setiap pesan masuk ke tabel `messages`
3. Menyusun ConversationContext (data produk, loyalitas customer, riwayat nego)
   yang diteruskan ke Sales Brain
4. Mencari produk yang relevan berdasarkan entitas dari intent_entity

Prinsip: state tracking bersifat stateless per-call — semua state disimpan di Supabase.

Referensi proposal Bab 4, Tahap 3: Conversation State Tracking
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from supabase import Client

from app.schemas.pipeline import (
    ConversationContext,
    IntentEntityResult,
    ScoringDecisionType,
)

logger = logging.getLogger(__name__)

# Nilai ai_decision yang diizinkan CHECK constraint negotiation_logs di schema.sql
_VALID_DB_NEGOTIATION_DECISIONS = {"hold_price", "discount", "bonus", "counter_offer"}


# ============================================================
# CUSTOMER — get or create
# ============================================================

def get_or_create_customer(supabase: Client, whatsapp_number: str) -> dict:
    """
    Ambil customer berdasarkan nomor WA, atau buat baru jika belum ada.
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
        # Race condition: whatsapp_number UNIQUE constraint -> re-query
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
    Jika tidak ada -> buat sesi baru.
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
    sender_type: str,   # 'customer' | 'ai' | 'admin'
    content_type: str,  # 'text' | 'voice'
    raw_text: Optional[str] = None,
    voice_url: Optional[str] = None,
    intent: Optional[str] = None,
    entities: Optional[dict] = None,
    sentiment: Optional[str] = None,
) -> dict:
    """
    Simpan satu pesan ke tabel `messages`.
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
    GUARD: ai_decision HARUS salah satu dari _VALID_DB_NEGOTIATION_DECISIONS.
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
        f"offer={customer_offer_price} -> ai={ai_offer_price}"
    )
    return res.data[0]


# ============================================================
# PRODUCT LOOKUP — cari produk berdasarkan nama
# ============================================================

def find_product_by_name(supabase: Client, product_name: str) -> Optional[dict]:
    """
    Cari produk berdasarkan nama (case-insensitive partial match).
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


def get_last_discussed_product_name(supabase: Client, conversation_id: str) -> Optional[str]:
    """Ambil produk terakhir yang disebut pelanggan dalam percakapan aktif.

    Pelanggan lazim menawar dengan kalimat singkat seperti "boleh 20 ribu?"
    setelah sebelumnya memilih produk. Karena pesan baru tidak selalu mengulang
    nama produk, state ini dipulihkan dari entities JSONB pada pesan sebelumnya.
    """
    try:
        res = (
            supabase.table("messages")
            .select("entities")
            .eq("conversation_id", conversation_id)
            .eq("sender_type", "customer")
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
    except Exception as exc:
        logger.warning(f"[StateTracking] Tidak dapat memulihkan produk percakapan: {exc}")
        return None

    for message in (res.data or []):
        entities = message.get("entities") or {}
        product_name = entities.get("product_name")
        if isinstance(product_name, str) and product_name.strip():
            return product_name.strip()
    return None


def get_customer_order_count(supabase: Client, customer_id: str) -> int:
    """
    Hitung total order historis pelanggan (untuk skor loyalitas).
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
    """
    # Step 1: Customer
    customer = get_or_create_customer(supabase, whatsapp_number)
    customer_id = customer["id"]

    # Step 2: Conversation
    conversation = get_or_create_conversation(supabase, customer_id)
    conversation_id = conversation["id"]

    # Step 3: Hitung loyalitas (0.0 - 1.0 berdasarkan jumlah order)
    total_orders = get_customer_order_count(supabase, customer_id)
    customer_loyalty = min(total_orders / 10.0, 1.0)

    # Step 4: Lookup produk jika disebutkan. Untuk pesan lanjutan yang hanya
    # memuat nominal tawaran, pulihkan produk terakhir dari memory percakapan.
    product = None
    product_name_query = intent_result.entities.product_name or get_last_discussed_product_name(
        supabase, conversation_id
    )
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
        customer_loyalty=customer_loyalty,  # Terpasang presisi ke Schema
        product_id=product["id"] if product else None,
        product_name=product["name"] if product else None,
        product_price=float(product["price"]) if product and product.get("price") is not None else None,
        product_floor_price=float(product["floor_price"]) if product and product.get("floor_price") is not None else None,
        product_stock=product.get("stock") if product else None,
        product_category=product.get("category") if product else None,
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
