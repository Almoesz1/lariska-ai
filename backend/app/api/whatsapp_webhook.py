import hmac
import hashlib
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Set

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, Response, status
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.pipeline.handover import (
    evaluate_handover,
    execute_handover,
    is_conversation_in_handover,
)
from app.pipeline.intent_entity import extract_intent_entity
from app.pipeline.response_generator import generate_response
from app.pipeline.retrieval import get_recommended_products, save_recommendation_log
from app.pipeline.sales_brain import classify_emotion, run_scoring_engine
from app.pipeline.state_tracking import (
    build_context,
    close_conversation,
    save_message,
    save_negotiation_log,
)
from app.pipeline.stt import transcribe_or_passthrough
from app.schemas.pipeline import IntentType, ScoringDecision, ScoringDecisionType
from app.services.supabase_client import get_supabase
from app.services.whatsapp_client import (
    download_media,
    mark_message_as_read,
    send_interactive_cta,
    send_text_message,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])

# In-memory LRU / Cache sederhana untuk Message Deduplication saat Demo
PROCESSED_MSG_IDS: Set[str] = set()
MAX_CACHE_SIZE = 1000


def _build_scoring_decision(context: Any, intent_result: Any) -> ScoringDecision:
    """Adapt context percakapan ke kontrak scoring engine tanpa melewati guardrail."""
    product_price = float(getattr(context, "product_price", 0.0) or 0.0)
    floor_price = float(getattr(context, "product_floor_price", product_price) or product_price)

    if intent_result.intent != IntentType.NEGO or product_price <= 0:
        return ScoringDecision(
            decision=ScoringDecisionType.NO_NEGO,
            final_price=product_price,
            model_confidence=1.0,
            reasoning="Non-negotiation intent atau produk belum teridentifikasi.",
        )

    offered_price = getattr(intent_result.entities, "offered_price", None)
    requested_discount = 0.0
    if offered_price is not None and offered_price > 0:
        requested_discount = max((product_price - float(offered_price)) / product_price, 0.0)

    now = datetime.now()
    features = {
        "margin_pct": max((product_price - floor_price) / product_price, 0.0),
        # Stock awal belum disimpan di ConversationContext; gunakan 1.0 sesuai
        # kontrak ScoringInput ketika rasio aktual belum tersedia.
        "stock_ratio": 1.0,
        "customer_loyalty": min(max(float(getattr(context, "total_orders", 0) or 0) / 10.0, 0.0), 1.0),
        "discount_requested_pct": min(requested_discount, 1.0),
        "hour_of_day": now.hour,
        "is_peak_hour": 1 if 19 <= now.hour <= 22 else 0,
    }
    raw = run_scoring_engine(
        features=features,
        product_price=product_price,
        floor_price=floor_price,
    )
    final_price = float(raw["final_price"])
    return ScoringDecision(
        decision=ScoringDecisionType(raw["final_action"]),
        final_price=final_price,
        discount_amount=max(product_price - final_price, 0.0),
        discount_pct=float(raw["applied_discount_pct"]),
        model_confidence=float(raw["ml_confidence"]),
        floor_price_enforced=bool(raw["floor_price_locked"]),
        reasoning=str(raw["guard_reason"]),
    )


def _is_duplicate_message(msg_id: str) -> bool:
    """Mengecek dan mencatat ID pesan untuk mencegah pemrosesan ganda."""
    if not msg_id:
        return False
    if msg_id in PROCESSED_MSG_IDS:
        return True
    
    if len(PROCESSED_MSG_IDS) >= MAX_CACHE_SIZE:
        PROCESSED_MSG_IDS.clear()  # Clear cache jika menumpuk
    
    PROCESSED_MSG_IDS.add(msg_id)
    return False


async def _verify_signature(request: Request, raw_body: bytes) -> None:
    """Verifikasi HMAC SHA256 Signature dari Meta."""
    app_secret = getattr(settings, "whatsapp_app_secret", None)
    if not app_secret:
        return  # Skip verifikasi jika app_secret belum di-set di env

    signature_header = request.headers.get("X-Hub-Signature-256", "")
    if not signature_header or not signature_header.startswith("sha256="):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid X-Hub-Signature-256 header."
        )

    expected_signature = hmac.new(
        key=app_secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256
    ).hexdigest()

    incoming_signature = signature_header.split("sha256=")[1]
    if not hmac.compare_digest(expected_signature, incoming_signature):
        logger.error("[WhatsAppWebhook] Payload signature verification failed!")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signature payload mismatch."
        )


# ============================================================
# GET — Meta Webhook Verification Endpoint
# ============================================================

@router.get("/webhook")
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
):
    """
    Verifikasi webhook dari Meta Developer Console.
    Mewajibkan kembalian HTTP Response ber-header text/plain berisi hub.challenge.
    """
    verify_token = getattr(settings, "whatsapp_verify_token", None)
    if not verify_token:
        logger.error("[WhatsAppWebhook] WHATSAPP_VERIFY_TOKEN missing in config.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="WHATSAPP_VERIFY_TOKEN tidak dikonfigurasi.",
        )

    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        logger.info("[WhatsAppWebhook] Webhook verified successfully!")
        if hub_challenge is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing hub.challenge",
            )
        return Response(content=hub_challenge, media_type="text/plain")

    logger.warning("[WhatsAppWebhook] Webhook verification failed. Token mismatch.")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Verify token tidak cocok.",
    )


# ============================================================
# POST — Non-Blocking Real-Time Message Receiver
# ============================================================

@router.post("/webhook")
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    """
    Entry point semua pesan WhatsApp masuk.
    Merespons HTTP 200 OK ke Meta dalam < 100ms dan menjalankan AI pipeline di BackgroundTasks.
    """
    raw_body = await request.body()
    
    # 1. Verifikasi Signature (Jika app_secret terkonfigurasi)
    try:
        await _verify_signature(request, raw_body)
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        logger.warning(f"[WhatsAppWebhook] Signature check skipped/failed: {exc}")

    # 2. Parse JSON
    try:
        body = await request.json()
    except Exception as exc:
        logger.warning(f"[WhatsAppWebhook] Failed to parse JSON body: {exc}")
        return {"status": "ok"}

    # 3. Quick Check: Abaikan jika ini hanya status update (sent/delivered/read)
    entry = body.get("entry", [{}])[0]
    changes = entry.get("changes", [{}])[0]
    value = changes.get("value", {})
    
    if "messages" not in value or not value.get("messages"):
        # Payload hanya status update, abaikan tanpa memicu heavy worker
        return {"status": "ok"}

    logger.debug(f"[WhatsAppWebhook] Received payload from Meta: {str(body)[:200]}")

    # Delegasikan eksekusi pipeline ke background task
    background_tasks.add_task(_process_webhook_payload, body)

    return {"status": "ok"}


# ============================================================
# BACKGROUND PIPELINE WORKERS
# ============================================================

async def _process_webhook_payload(body: Dict[str, Any]) -> None:
    """Parse payload webhook Meta dan ekstrak data pesan masuk."""
    try:
        entries = body.get("entry", [])
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages", [])
                contacts = value.get("contacts", [])

                for message in messages:
                    contact = contacts[0] if contacts else {}
                    await _handle_single_message(message, contact, value)
    except Exception as exc:
        logger.exception(f"[WhatsAppWebhook] Background processing error: {exc}")


async def _handle_single_message(message: Dict[str, Any], contact: Dict[str, Any], value: Dict[str, Any]) -> None:
    """Proses satu pesan WhatsApp melalui seluruh AI Pipeline dengan isolasi Threadpool."""
    msg_id = message.get("id", "")
    from_number = message.get("from", "")
    msg_type = message.get("type", "text")
    customer_name = contact.get("profile", {}).get("name", "")

    # Cek Deduplikasi Pesan (Mencegah double reply saat demo)
    if _is_duplicate_message(msg_id):
        logger.info(f"[WhatsAppWebhook] Duplicate message detected (id={msg_id[:8]}). Skipping.")
        return

    logger.info(
        f"[WhatsAppWebhook] Processing message: from={from_number} type={msg_type} id={msg_id[:8]}"
    )

    # Mark as read (Centang Biru)
    await mark_message_as_read(msg_id)

    supabase = get_supabase()

    # ------------------------------------------------------------
    # TAHAP 1 — Handling Audio / Voice Note & Text Extraction
    # ------------------------------------------------------------
    raw_text = None
    audio_bytes = None
    audio_filename = "audio.ogg"
    voice_url = None

    if msg_type == "text":
        raw_text = message.get("text", {}).get("body", "")
    elif msg_type == "audio":
        audio_info = message.get("audio", {})
        media_id = audio_info.get("id")
        if media_id:
            try:
                audio_bytes, audio_filename = await download_media(media_id)
                voice_url = f"wa_media://{media_id}"
            except Exception as exc:
                logger.error(f"[WhatsAppWebhook] Audio download failed: {exc}")
                await send_text_message(
                    from_number,
                    "Maaf, voice note tidak bisa diproses saat ini. Coba kirim pesan teks ya 🙏",
                )
                return
    else:
        await send_text_message(
            from_number,
            "Maaf, kami hanya dapat memproses pesan teks dan voice note saat ini 😊",
        )
        return

    if not raw_text and not audio_bytes:
        logger.warning(f"[WhatsAppWebhook] Empty message payload from {from_number}. Aborting.")
        return

    # STT Whisper Transcribe (Running in Threadpool)
    try:
        whisper_model = getattr(settings, "whisper_model_path", "base")
        text, is_voice = await run_in_threadpool(
            transcribe_or_passthrough,
            text=raw_text,
            audio_bytes=audio_bytes,
            audio_filename=audio_filename,
            model_size=whisper_model,
        )
    except Exception as exc:
        logger.error(f"[WhatsAppWebhook] STT Execution Error: {exc}")
        await send_text_message(
            from_number,
            "Maaf, kami kesulitan memahami voice note Anda. Mohon coba kirimkan pesan teks ya! 🙏",
        )
        return

    if not text or not text.strip():
        logger.warning(f"[WhatsAppWebhook] Transcribed text is empty. Skipping.")
        return

    # ------------------------------------------------------------
    # TAHAP 2 — Intent & Entity Extraction
    # ------------------------------------------------------------
    intent_result = await run_in_threadpool(extract_intent_entity, text)

    # ------------------------------------------------------------
    # TAHAP 3 — Emotion Classifier
    # ------------------------------------------------------------
    emotion_result = await run_in_threadpool(classify_emotion, text)

    # ------------------------------------------------------------
    # TAHAP 4 — State Tracking & Context Building
    # ------------------------------------------------------------
    context = await run_in_threadpool(build_context, supabase, from_number, intent_result)

    if customer_name and getattr(context, "customer_name", None) != customer_name:
        try:
            await run_in_threadpool(
                lambda: supabase.table("customers")
                .update({"name": customer_name})
                .eq("id", context.customer_id)
                .execute()
            )
        except Exception as exc:
            logger.debug(f"[WhatsAppWebhook] Customer name update non-fatal error: {exc}")

    # Simpan pesan pelanggan ke Database
    await run_in_threadpool(
        save_message,
        supabase=supabase,
        conversation_id=context.conversation_id,
        sender_type="customer",
        content_type="voice" if is_voice else "text",
        raw_text=text,
        voice_url=voice_url,
        intent=intent_result.intent.value,
        entities=intent_result.entities.model_dump(),
        sentiment=emotion_result.emotion.value,
    )

    # ------------------------------------------------------------
    # TAHAP 4b — Handover & Escalation Check (Human-in-the-Loop)
    # ------------------------------------------------------------
    already_handover = await run_in_threadpool(
        is_conversation_in_handover, supabase, context.conversation_id
    )
    if already_handover:
        logger.info(
            f"[WhatsAppWebhook] Percakapan {context.conversation_id[:8]} dalam mode handover. AI standby."
        )
        return

    handover_eval = await run_in_threadpool(
        evaluate_handover, intent_result=intent_result, context=context
    )
    if handover_eval.should_handover:
        await run_in_threadpool(
            execute_handover,
            supabase=supabase,
            conversation_id=context.conversation_id,
            evaluation=handover_eval,
        )
        
        handover_msg = (
            "Baik Kak, terima kasih atas informasinya 🙏\n\n"
            "Pesan Kakak sudah kami teruskan ke Tim CS/Admin kami. "
            "Mohon tunggu sebentar ya, tim kami akan segera membalas!"
        )
        await send_text_message(from_number, handover_msg)

        await run_in_threadpool(
            save_message,
            supabase=supabase,
            conversation_id=context.conversation_id,
            sender_type="ai",
            content_type="text",
            raw_text=handover_msg,
        )
        return

    # ------------------------------------------------------------
    # TAHAP 5a — Adaptive Scoring Engine (LightGBM)
    # ------------------------------------------------------------
    scoring_decision = await run_in_threadpool(_build_scoring_decision, context, intent_result)

    # ------------------------------------------------------------
    # TAHAP 5b — Product Retrieval & Recommendations (pgvector)
    # ------------------------------------------------------------
    recommended_products = []
    should_recommend = intent_result.intent in (
        IntentType.REKOMENDASI,
        IntentType.TANYA_PRODUK,
        IntentType.GREETING,
    )

    if should_recommend or (
        intent_result.intent == IntentType.NEGO
        and scoring_decision.decision
        in (ScoringDecisionType.DISCOUNT, ScoringDecisionType.BONUS)
    ):
        recommended_products = await run_in_threadpool(
            get_recommended_products,
            customer_id=context.customer_id,
            current_product_id=context.product_id,
            current_category=context.product_category,
            limit=3,
        )
        for prod in recommended_products:
            await run_in_threadpool(
                save_recommendation_log,
                customer_id=context.customer_id,
                product_id=prod["id"],
                conversation_id=context.conversation_id,
                reason=f"intent={intent_result.intent.value}",
            )

    # ------------------------------------------------------------
    # TAHAP 6 — Sales Response Generator (Gemini)
    # ------------------------------------------------------------
    reply_text = await run_in_threadpool(
        generate_response,
        context=context,
        intent_result=intent_result,
        emotion_result=emotion_result,
        scoring_decision=scoring_decision,
        recommended_products=recommended_products,
    )

    # Log negosiasi jika ada penawaran harga
    if intent_result.intent == IntentType.NEGO and getattr(context, "product_id", None):
        offered_p = getattr(intent_result.entities, "offered_price", None)
        final_p = getattr(scoring_decision, "final_price", None)
        floor_p = getattr(context, "product_floor_price", 0.0) or 0.0
        conf_score = getattr(scoring_decision, "model_confidence", 0.0)
        dec_val = getattr(scoring_decision.decision, "value", "hold_price") if scoring_decision else "hold_price"

        await run_in_threadpool(
            save_negotiation_log,
            supabase=supabase,
            conversation_id=context.conversation_id,
            product_id=context.product_id,
            customer_offer_price=offered_p,
            ai_decision=dec_val,
            ai_offer_price=final_p,
            floor_price_snapshot=floor_p,
            model_confidence=conf_score,
            outcome="pending",
        )

    # Simpan balasan AI
    await run_in_threadpool(
        save_message,
        supabase=supabase,
        conversation_id=context.conversation_id,
        sender_type="ai",
        content_type="text",
        raw_text=reply_text,
    )

    # ------------------------------------------------------------
    # TAHAP 7 — Delivery: Reply / Midtrans Checkout
    # ------------------------------------------------------------
    if intent_result.intent == IntentType.CHECKOUT and getattr(context, "product_id", None):
        await _handle_checkout(
            supabase=supabase,
            from_number=from_number,
            context=context,
            scoring_decision=scoring_decision,
            reply_text=reply_text,
        )
    else:
        await send_text_message(from_number, reply_text)

    # Tutup percakapan setelah checkout dipicu
    if intent_result.intent == IntentType.CHECKOUT:
        try:
            await run_in_threadpool(close_conversation, supabase, context.conversation_id)
        except Exception as exc:
            logger.warning(f"[WhatsAppWebhook] Non-fatal close conversation error: {exc}")

    logger.info(
        f"[WhatsAppWebhook] Pipeline finished successfully for {from_number} | "
        f"Intent={intent_result.intent.value} | Emotion={emotion_result.emotion.value}"
    )


async def _handle_checkout(
    supabase: Any, from_number: str, context: Any, scoring_decision: Any, reply_text: str
) -> None:
    """Menangani Intent Checkout: Buat order & panggil Midtrans QRIS payment."""
    if not getattr(context, "product_id", None) or not getattr(context, "product_price", None):
        await send_text_message(from_number, reply_text)
        return

    try:
        unit_price = context.product_price
        discount_amount = getattr(scoring_decision, "discount_amount", 0.0) or 0.0
        total = max(1.0, unit_price - discount_amount)

        # 1. Insert Order
        order_res = await run_in_threadpool(
            lambda: supabase.table("orders")
            .insert(
                {
                    "customer_id": context.customer_id,
                    "conversation_id": context.conversation_id,
                    "product_id": context.product_id,
                    "quantity": 1,
                    "unit_price": unit_price,
                    "discount_amount": discount_amount,
                    "total_amount": total,
                    "status": "pending",
                }
            )
            .execute()
        )

        order_id = order_res.data[0]["id"]

        # 2. Midtrans Payment Client Call
        from app.services.payment_client import create_qris_payment

        cust_name = getattr(context, "customer_name", None) or "Pelanggan"
        prod_name = getattr(context, "product_name", None) or "Produk"

        payment_result = await run_in_threadpool(
            create_qris_payment,
            order_id=order_id,
            amount=total,
            customer_name=cust_name,
            customer_phone=from_number,
            product_name=prod_name,
            quantity=1,
        )

        # 3. Insert Payment Record
        await run_in_threadpool(
            lambda: supabase.table("payments")
            .insert(
                {
                    "order_id": order_id,
                    "method": "qris",
                    "status": "pending",
                    "amount": total,
                    "provider_reference": payment_result.get("midtrans_order_id", order_id),
                }
            )
            .execute()
        )

        # 4. Kirim teks konfirmasi
        await send_text_message(from_number, reply_text)

        # 5. Kirim Tombol Interactive CTA Link QRIS
        invoice_text = (
            f"🧾 *Invoice #{order_id[:8].upper()}*\n"
            f"Produk: {prod_name}\n"
            f"Total Pembayaran: Rp{total:,.0f}\n\n"
            f"Klik tombol di bawah ini untuk membayar via QRIS/Transfer 👇"
        )
        await send_interactive_cta(
            to=from_number,
            body_text=invoice_text,
            button_label="Bayar Sekarang 💳",
            payment_url=payment_result.get("payment_url", "https://lariska.ai/pay"),
        )

        logger.info(f"[WhatsAppWebhook] Checkout flow succeeded for order: #{order_id[:8]}")

    except Exception as exc:
        logger.error(f"[WhatsAppWebhook] Checkout processing error: {exc}", exc_info=True)
        await send_text_message(
            from_number,
            f"{reply_text}\n\n(Mohon maaf, terjadi kendala saat menyiapkan tautan pembayaran. Tim kami akan segera menghubungi Anda 🙏)",
        )
