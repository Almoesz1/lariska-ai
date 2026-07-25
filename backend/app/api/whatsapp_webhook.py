"""
LARISKA AI — Sprint 6
WhatsApp Webhook — Receive & Process Incoming Messages

Ini adalah INTI integrasi end-to-end LARISKA AI.
Endpoint ini menerima semua pesan WhatsApp masuk → jalankan seluruh AI Pipeline → kirim balasan.

Flow lengkap (sesuai proposal Bab 4):
  WhatsApp masuk (teks/voice)
    ↓ [1] STT (jika voice note)
    ↓ [2] Intent/Entity Extraction (Gemini JSON)
    ↓ [3] State Tracking (get/create customer & conversation, build context)
    ↓ [4a] Scoring Engine (LightGBM + hard rules)
    ↓ [4b] Emotion Classifier (Gemini)
    ↓ [5] Retrieval (pgvector / category fallback)
    ↓ [6] Response Generator (Gemini → natural language)
    ↓ WhatsApp reply terkirim

Endpoint:
  GET /api/whatsapp/webhook — verifikasi webhook Meta (setup awal)
  POST /api/whatsapp/webhook — terima pesan masuk

Referensi proposal Bab 4: AI Pipeline, Demo Script Bab 13
"""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.core.config import settings
from app.pipeline.intent_entity import extract_intent_entity
from app.pipeline.response_generator import generate_response
from app.pipeline.retrieval import get_recommended_products, save_recommendation_log
from app.pipeline.sales_brain import classify_emotion, run_scoring_engine
from app.pipeline.state_tracking import (
    build_context,
    save_message,
    save_negotiation_log,
    close_conversation,
)
from app.pipeline.stt import transcribe_or_passthrough
from app.schemas.pipeline import IntentType, ScoringDecisionType
from app.services.supabase_client import get_supabase
from app.services.whatsapp_client import (
    download_media,
    mark_message_as_read,
    send_interactive_cta,
    send_text_message,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])


# ============================================================
# GET — Verifikasi Webhook (Setup awal Meta Developer Console)
# ============================================================

@router.get("/webhook")
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
):
    """
    Verifikasi webhook WhatsApp Cloud API.
    Meta akan GET endpoint ini saat kamu setup webhook di Developer Console.
    Harus return hub.challenge jika verify_token cocok.
    """
    verify_token = settings.whatsapp_verify_token
    if not verify_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="WHATSAPP_VERIFY_TOKEN tidak dikonfigurasi."
        )

    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        logger.info("[WhatsAppWebhook] Webhook verified successfully.")
        return int(hub_challenge)

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Verify token tidak cocok."
    )


# ============================================================
# POST — Terima & Proses Pesan Masuk
# ============================================================

@router.post("/webhook")
async def receive_message(request: Request):
    """
    Entry point semua pesan WhatsApp masuk.
    Meta mengirim POST ke sini untuk setiap event (pesan, status update, dll).

    Penting: Selalu return 200 OK segera, bahkan jika ada error di pipeline.
    Jika endpoint return non-200, Meta akan retry → flood.
    Semua error handling bersifat soft-fail.
    """
    try:
        body = await request.json()
    except Exception:
        # Tetap return 200 — jangan reject webhook dari Meta
        return {"status": "ok"}

    logger.debug(f"[WhatsAppWebhook] Payload: {str(body)[:500]}")

    try:
        await _process_webhook_payload(body)
    except Exception as exc:
        # Pipeline error → log, tapi tetap return 200
        logger.exception(f"[WhatsAppWebhook] Pipeline error (non-fatal): {exc}")

    return {"status": "ok"}


async def _process_webhook_payload(body: dict) -> None:
    """
    Parse payload webhook Meta dan ekstrak data pesan masuk.
    Meta bisa kirim multiple entries/changes dalam satu payload.
    """
    entries = body.get("entry", [])
    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            value = change.get("value", {})

            # Hanya proses event 'messages' (bukan status update, delivery, dll)
            messages = value.get("messages", [])
            contacts = value.get("contacts", [])

            for message in messages:
                contact = contacts[0] if contacts else {}
                await _handle_single_message(message, contact, value)


async def _handle_single_message(message: dict, contact: dict, value: dict) -> None:
    """
    Proses satu pesan WhatsApp melalui seluruh AI Pipeline.
    """
    msg_id = message.get("id", "")
    from_number = message.get("from", "")  # Nomor WA pengirim
    msg_type = message.get("type", "text")  # 'text' | 'audio' | 'image' | dll
    customer_name = contact.get("profile", {}).get("name", "")

    logger.info(
        f"[WhatsAppWebhook] Message received: "
        f"from={from_number} type={msg_type} id={msg_id[:8]}"
    )

    # Mark as read segera (centang biru) — non-blocking
    mark_message_as_read(msg_id)

    supabase = get_supabase()

    # ============================================================
    # TAHAP 1 — STT (atau passthrough untuk teks)
    # ============================================================
    raw_text = None
    audio_bytes = None
    audio_filename = "audio.ogg"
    voice_url = None
    is_voice = False

    if msg_type == "text":
        raw_text = message.get("text", {}).get("body", "")

    elif msg_type == "audio":
        # Voice note — download dulu, lalu STT
        audio_info = message.get("audio", {})
        media_id = audio_info.get("id")
        if media_id:
            try:
                audio_bytes, audio_filename = download_media(media_id)
                voice_url = f"wa_media://{media_id}"  # Reference saja, bukan URL real
            except Exception as exc:
                logger.error(f"[WhatsAppWebhook] Failed to download audio: {exc}")
                send_text_message(
                    from_number,
                    "Maaf, voice note tidak bisa diproses saat ini. Coba kirim pesan teks ya 🙏"
                )
                return
    else:
        # Tipe pesan lain (gambar, video, dokumen) — belum didukung di MVP
        send_text_message(
            from_number,
            "Maaf, kami hanya bisa memproses pesan teks dan voice note saat ini 😊"
        )
        return

    if not raw_text and not audio_bytes:
        logger.warning(f"[WhatsAppWebhook] Empty message from {from_number}. Skipping.")
        return

    # STT / Passthrough
    try:
        text, is_voice = transcribe_or_passthrough(
            text=raw_text,
            audio_bytes=audio_bytes,
            audio_filename=audio_filename,
            model_size=settings.whisper_model_path,
        )
    except Exception as exc:
        logger.error(f"[WhatsAppWebhook] STT error: {exc}")
        send_text_message(from_number, "Maaf, tidak bisa memahami voice note. Coba kirim teks ya! 🙏")
        return

    if not text:
        return

    # ============================================================
    # TAHAP 2 — Intent & Entity Extraction
    # ============================================================
    intent_result = extract_intent_entity(text)

    # ============================================================
    # TAHAP 3 — State Tracking (build context dari database)
    # ============================================================
    context = build_context(supabase, from_number, intent_result)

    # Update nama customer jika baru diketahui
    if customer_name and not context.customer_name:
        try:
            supabase.table("customers").update({"name": customer_name}).eq(
                "id", context.customer_id
            ).execute()
        except Exception:
            pass

    # Simpan pesan customer ke database
    save_message(
        supabase=supabase,
        conversation_id=context.conversation_id,
        sender_type="customer",
        content_type="voice" if is_voice else "text",
        raw_text=text,
        voice_url=voice_url,
        intent=intent_result.intent.value,
        entities=intent_result.entities.model_dump(),
        sentiment=None,  # Akan diisi setelah emotion classifier
    )

    # ============================================================
    # TAHAP 4a — Scoring Engine (Adaptive Scoring — Inti AI)
    # ============================================================
    scoring_decision = run_scoring_engine(context, intent_result)

    # ============================================================
    # TAHAP 4b — Emotion Classifier
    # ============================================================
    emotion_result = classify_emotion(text)

    # Update sentiment di database (update message terakhir yang baru disimpan)
    try:
        supabase.table("messages").update(
            {"sentiment": emotion_result.emotion.value}
        ).eq("conversation_id", context.conversation_id).order(
            "created_at", desc=True
        ).limit(1).execute()
    except Exception:
        pass  # Non-fatal

    # ============================================================
    # TAHAP 5 — Retrieval (Rekomendasi produk)
    # ============================================================
    recommended_products = []
    should_recommend = intent_result.intent in (
        IntentType.REKOMENDASI,
        IntentType.TANYA_PRODUK,
        IntentType.GREETING,
    )

    if should_recommend or (
        intent_result.intent == IntentType.NEGO
        and scoring_decision.decision in (ScoringDecisionType.DISCOUNT, ScoringDecisionType.BONUS)
    ):
        recommended_products = get_recommended_products(
            customer_id=context.customer_id,
            current_product_id=context.product_id,
            current_category=context.product_category,
            limit=3,
        )
        # Log rekomendasi untuk evaluasi Sprint 8
        for prod in recommended_products:
            save_recommendation_log(
                customer_id=context.customer_id,
                product_id=prod["id"],
                conversation_id=context.conversation_id,
                reason=f"intent={intent_result.intent.value}",
            )

    # ============================================================
    # TAHAP 6 — Response Generator
    # ============================================================
    reply_text = generate_response(
        context=context,
        intent_result=intent_result,
        emotion_result=emotion_result,
        scoring_decision=scoring_decision,
        recommended_products=recommended_products,
    )

    # ============================================================
    # Simpan log negosiasi (jika intent nego)
    # ============================================================
    if intent_result.intent == IntentType.NEGO and context.product_id:
        save_negotiation_log(
            supabase=supabase,
            conversation_id=context.conversation_id,
            product_id=context.product_id,
            customer_offer_price=intent_result.entities.offered_price,
            ai_decision=scoring_decision.decision.value,
            ai_offer_price=scoring_decision.final_price if scoring_decision.final_price else None,
            floor_price_snapshot=context.product_floor_price or 0.0,
            model_confidence=scoring_decision.model_confidence,
            outcome="pending",  # Akan diupdate saat checkout
        )

    # ============================================================
    # Simpan pesan AI ke database
    # ============================================================
    save_message(
        supabase=supabase,
        conversation_id=context.conversation_id,
        sender_type="ai",
        content_type="text",
        raw_text=reply_text,
    )

    # ============================================================
    # Kirim balasan ke WhatsApp
    # ============================================================
    if intent_result.intent == IntentType.CHECKOUT and context.product_id:
        # Intent checkout → langsung buat order + payment link
        await _handle_checkout(
            supabase=supabase,
            from_number=from_number,
            context=context,
            scoring_decision=scoring_decision,
            reply_text=reply_text,
        )
    else:
        # Balasan teks biasa
        send_text_message(from_number, reply_text)

    # Tutup conversation jika checkout selesai
    if intent_result.intent == IntentType.CHECKOUT:
        try:
            close_conversation(supabase, context.conversation_id)
        except Exception as exc:
            logger.warning(f"[WhatsAppWebhook] Failed to close conversation: {exc}")

    logger.info(
        f"[WhatsAppWebhook] Pipeline complete: "
        f"from={from_number} "
        f"intent={intent_result.intent.value} "
        f"emotion={emotion_result.emotion.value} "
        f"decision={scoring_decision.decision.value if scoring_decision else 'none'}"
    )


async def _handle_checkout(supabase, from_number: str, context, scoring_decision, reply_text: str) -> None:
    """
    Handle intent checkout: buat order di database + kirim QRIS payment link.
    """
    if not context.product_id or not context.product_price:
        send_text_message(from_number, reply_text)
        return

    try:
        # Hitung harga final
        unit_price = context.product_price
        discount_amount = scoring_decision.discount_amount if scoring_decision else 0.0
        total = unit_price - discount_amount

        # Buat order
        order_res = supabase.table("orders").insert({
            "customer_id": context.customer_id,
            "conversation_id": context.conversation_id,
            "product_id": context.product_id,
            "quantity": 1,
            "unit_price": unit_price,
            "discount_amount": discount_amount,
            "total_amount": total,
            "status": "pending",
        }).execute()

        order_id = order_res.data[0]["id"]

        # Buat payment via Midtrans
        from app.services.payment_client import create_qris_payment
        payment_result = create_qris_payment(
            order_id=order_id,
            amount=total,
            customer_name=context.customer_name or "Pelanggan",
            customer_phone=from_number,
            product_name=context.product_name or "Produk",
            quantity=1,
        )

        # Simpan payment record
        supabase.table("payments").insert({
            "order_id": order_id,
            "method": "qris",
            "status": "pending",
            "amount": total,
            "provider_reference": payment_result["midtrans_order_id"],
        }).execute()

        # Kirim reply teks dulu
        send_text_message(from_number, reply_text)

        # Kirim CTA button dengan link QRIS
        invoice_text = (
            f"🧾 *Invoice #{order_id[:8].upper()}*\n"
            f"Produk: {context.product_name}\n"
            f"Harga: Rp{total:,.0f}\n\n"
            f"Silakan bayar via QRIS 👇"
        )
        send_interactive_cta(
            to=from_number,
            body_text=invoice_text,
            button_label="Bayar Sekarang 💳",
            payment_url=payment_result["payment_url"],
        )

        logger.info(
            f"[WhatsAppWebhook] Checkout complete: "
            f"order={order_id[:8]} amount=Rp{total:,.0f}"
        )

    except Exception as exc:
        logger.error(f"[WhatsAppWebhook] Checkout error: {exc}")
        # Fallback: kirim balasan teks saja tanpa payment link
        send_text_message(
            from_number,
            f"{reply_text}\n\n(Mohon maaf, sistem pembayaran sedang gangguan. Tim kami akan menghubungi Anda segera 🙏)"
        )
