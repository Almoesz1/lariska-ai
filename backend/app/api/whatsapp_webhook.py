import os
import hmac
import hashlib
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

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
    get_last_requested_quantity,
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

# Bounded FIFO Cache untuk Message Deduplication
PROCESSED_MSG_IDS: Dict[str, bool] = {}
MAX_CACHE_SIZE = 2000


def _is_duplicate_message(msg_id: str) -> bool:
    """Mengecek dan mencatat ID pesan menggunakan bounded FIFO dict."""
    if not msg_id:
        return False
    if msg_id in PROCESSED_MSG_IDS:
        return True

    if len(PROCESSED_MSG_IDS) >= MAX_CACHE_SIZE:
        oldest_key = next(iter(PROCESSED_MSG_IDS))
        PROCESSED_MSG_IDS.pop(oldest_key, None)

    PROCESSED_MSG_IDS[msg_id] = True
    return False


def _build_scoring_decision(
    context: Any, 
    intent_result: Any, 
    emotion_result: Any
) -> ScoringDecision:
    """
    Adaptasi context & sentiment percakapan ke Scoring Engine (ML Adaptive Pricing Model).
    Memasukkan parameter emosi pelanggan untuk penyesuaian strategi negosiasi.
    """
    product_price = float(getattr(context, "product_price", 0.0) or 0.0)
    floor_price = float(getattr(context, "product_floor_price", product_price) or product_price)

    if intent_result.intent != IntentType.NEGO or product_price <= 0:
        return ScoringDecision(
            decision=ScoringDecisionType.NO_NEGO,
            final_price=product_price,
            model_confidence=1.0,
            reasoning="Non-negotiation intent atau produk belum teridentifikasi.",
        )

    quantity = max(int(getattr(intent_result.entities, "quantity", None) or 1), 1)
    offered_price = getattr(intent_result.entities, "offered_price", None)
    requested_discount = 0.0
    if offered_price is not None and offered_price > 0:
        # Harga yang pelanggan sebutkan lazimnya adalah TOTAL bundle
        # (contoh: "dua pcs 45 ribu"), sedangkan model bekerja per unit.
        offered_unit_price = float(offered_price) / quantity
        requested_discount = max((product_price - offered_unit_price) / product_price, 0.0)

    # Bobot emosi untuk scoring engine (Frustrasi/Kecewa meningkatkan kepekaan diskon)
    emotion_val = getattr(emotion_result, "emotion", None)
    emotion_name = getattr(emotion_val, "value", str(emotion_val)).lower() if emotion_val else "neutral"
    
    sentiment_score = 0.5  # Neutral default
    if emotion_name in ["frustrated", "angry", "disappointed"]:
        sentiment_score = 0.1  # Butuh penanganan diskon/insentif lebih tinggi
    elif emotion_name in ["happy", "excited", "satisfied"]:
        sentiment_score = 0.9

    now = datetime.now()
    features = {
        "margin_pct": max((product_price - floor_price) / product_price, 0.0),
        "stock_ratio": 1.0,
        "customer_loyalty": min(max(float(getattr(context, "total_orders", 0) or 0) / 10.0, 0.0), 1.0),
        "discount_requested_pct": min(requested_discount, 1.0),
        "sentiment_score": sentiment_score,
        "hour_of_day": now.hour,
        "is_peak_hour": 1 if 19 <= now.hour <= 22 else 0,
    }

    raw = run_scoring_engine(
        features=features,
        product_price=product_price,
        floor_price=floor_price,
    )
    
    final_price = float(raw.get("final_price", product_price))
    return ScoringDecision(
        decision=ScoringDecisionType(raw.get("final_action", "hold_price")),
        final_price=final_price,
        discount_amount=max(product_price - final_price, 0.0),
        discount_pct=float(raw.get("applied_discount_pct", 0.0)),
        model_confidence=float(raw.get("ml_confidence", 0.85)),
        floor_price_enforced=bool(raw.get("floor_price_locked", False)),
        reasoning=str(raw.get("guard_reason", "ML Decision Executed")),
    )


def _handle_status_update(value: Dict[str, Any]) -> None:
    """Mencatat update status pengiriman dari Meta (sent, delivered, read, failed)."""
    statuses = value.get("statuses", [])
    for status_item in statuses:
        status_name = status_item.get("status")
        recipient = status_item.get("recipient_id")
        msg_id = status_item.get("id", "")
        errors = status_item.get("errors")

        logger.info(
            f"[Meta Status Callback] ID={msg_id[:12]} | Recipient={recipient} | Status='{status_name}'"
        )

        if errors:
            for err in errors:
                logger.error(
                    f"[Meta Delivery Failure] Code: {err.get('code')} | Title: '{err.get('title')}' | "
                    f"Message: '{err.get('message')}' | Details: '{err.get('error_data', {}).get('details')}'"
                )


async def _verify_signature(request: Request, raw_body: bytes) -> None:
    """Verifikasi HMAC SHA256 Signature dari Meta Cloud API."""
    app_secret = getattr(settings, "whatsapp_app_secret", None) or os.getenv("WHATSAPP_APP_SECRET")
    if not app_secret:
        return  # Bypass verifikasi jika app_secret belum dikonfigurasi di environment

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


async def _extract_payload_content(
    message: Dict[str, Any]
) -> Tuple[Optional[str], Optional[bytes], str, Optional[str], str]:
    """
    Ekstrak konten teks/media dari berbagai jenis tipe pesan WhatsApp Meta API:
    - Text
    - Interactive (Button Reply / List Reply)
    - Quick Reply Buttons
    - Audio / Voice Note
    - Image/Video/Document (Ekstrak Caption jika ada)
    
    Returns: (raw_text, audio_bytes, audio_filename, voice_url, content_type)
    """
    msg_type = message.get("type", "text")
    raw_text: Optional[str] = None
    audio_bytes: Optional[bytes] = None
    audio_filename: str = "audio.ogg"
    voice_url: Optional[str] = None
    content_type: str = "text"

    if msg_type == "text":
        raw_text = message.get("text", {}).get("body", "")

    elif msg_type == "interactive":
        interactive = message.get("interactive", {})
        i_type = interactive.get("type")
        if i_type == "button_reply":
            raw_text = interactive.get("button_reply", {}).get("title", "")
        elif i_type == "list_reply":
            raw_text = interactive.get("list_reply", {}).get("title", "")

    elif msg_type == "button":
        raw_text = message.get("button", {}).get("text", "")

    elif msg_type == "audio":
        content_type = "voice"
        audio_info = message.get("audio", {})
        media_id = audio_info.get("id")
        if media_id:
            audio_bytes, audio_filename = await download_media(media_id)
            voice_url = f"wa_media://{media_id}"

    elif msg_type in ["image", "video", "document"]:
        # Ekstrak caption jika pengguna mengirim media beserta teks
        raw_text = message.get(msg_type, {}).get("caption", "")
        if not raw_text:
            raw_text = f"[Pengguna mengirimkan file {msg_type}]"

    return raw_text, audio_bytes, audio_filename, voice_url, content_type


# ============================================================
# GET — Meta Webhook Verification Endpoint
# ============================================================

@router.get("/webhook")
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
):
    """Verifikasi webhook dari Meta Developer Console."""
    verify_token = getattr(settings, "whatsapp_verify_token", None) or os.getenv("WHATSAPP_VERIFY_TOKEN")
    if not verify_token:
        verify_token = "lariska_secret_verify_123"

    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        logger.info("[WhatsAppWebhook] Webhook verified successfully!")
        if hub_challenge is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing hub.challenge",
            )
        return Response(content=hub_challenge, media_type="text/plain")

    logger.warning(f"[WhatsAppWebhook] Verification failed. Token mismatch: {hub_verify_token}")
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
    Entry point semua event WhatsApp dari Meta Cloud API.
    Merespons HTTP 200 OK ke Meta dalam < 100ms dan memproses pipeline AI di BackgroundTasks.
    """
    raw_body = await request.body()

    try:
        await _verify_signature(request, raw_body)
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        logger.warning(f"[WhatsAppWebhook] Signature check skipped/failed: {exc}")

    try:
        body = await request.json()
    except Exception as exc:
        logger.warning(f"[WhatsAppWebhook] Failed to parse JSON body: {exc}")
        return {"status": "ok"}

    try:
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})

        if "messages" in value or "statuses" in value:
            background_tasks.add_task(_process_webhook_payload, body)
    except (IndexError, AttributeError) as exc:
        logger.debug(f"[WhatsAppWebhook] Payload structure ignored: {exc}")

    return {"status": "ok"}


# ============================================================
# BACKGROUND PIPELINE WORKERS
# ============================================================

async def _process_webhook_payload(body: Dict[str, Any]) -> None:
    """Parse payload webhook Meta dan eksekusi event sesuai tipe (messages/statuses)."""
    try:
        entries = body.get("entry", [])
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})

                # 1. Update status pengiriman dari Meta
                if "statuses" in value:
                    _handle_status_update(value)

                # 2. Pesan masuk baru dari pelanggan
                messages = value.get("messages", [])
                contacts = value.get("contacts", [])

                for message in messages:
                    contact = contacts[0] if contacts else {}
                    await _handle_single_message(message, contact, value)
    except Exception as exc:
        logger.exception(f"[WhatsAppWebhook] Background processing error: {exc}")


async def _handle_single_message(message: Dict[str, Any], contact: Dict[str, Any], value: Dict[str, Any]) -> None:
    """Proses satu pesan WhatsApp melalui End-to-End AI Sales Pipeline."""
    msg_id = message.get("id", "")
    from_number = message.get("from", "")
    msg_type = message.get("type", "text")
    customer_name = contact.get("profile", {}).get("name", "")

    if _is_duplicate_message(msg_id):
        logger.info(f"[WhatsAppWebhook] Duplicate message detected (id={msg_id[:8]}). Skipping.")
        return

    logger.info(f"[WhatsAppWebhook] Processing message from={from_number} type={msg_type} id={msg_id[:8]}")

    try:
        # Tanda pesan telah dibaca (centang biru di WA)
        await mark_message_as_read(msg_id)
        supabase = get_supabase()

        # ------------------------------------------------------------
        # TAHAP 1 — Handling & Payload Parsing (Teks / Audio / Media)
        # ------------------------------------------------------------
        try:
            raw_text, audio_bytes, audio_filename, voice_url, content_type = await _extract_payload_content(message)
        except Exception as exc:
            logger.error(f"[WhatsAppWebhook] Media download failed: {exc}")
            await send_text_message(
                from_number,
                "Maaf, kami mengalami kendala mengunduh media Anda. Mohon coba kirimkan dalam bentuk pesan teks ya 🙏"
            )
            return

        if not raw_text and not audio_bytes:
            await send_text_message(
                from_number,
                "Maaf, format pesan ini belum didukung. Silakan kirimkan pertanyaan Anda melalui pesan teks atau voice note 😊"
            )
            return

        # STT Transcribe jika berupa Voice Note
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
                "Maaf Kak, kami kesulitan memproses suara dari voice note tersebut. Boleh bantu ketikkan via pesan teks? 🙏",
            )
            return

        if not text or not text.strip():
            logger.warning(f"[WhatsAppWebhook] Transcribed text is empty. Aborting.")
            return

        # ------------------------------------------------------------
        # TAHAP 2 — Intent & Entity Extraction
        # ------------------------------------------------------------
        intent_result = await run_in_threadpool(extract_intent_entity, text)

        # ------------------------------------------------------------
        # TAHAP 3 — Emotion & Sentiment Analysis
        # ------------------------------------------------------------
        emotion_result = await run_in_threadpool(classify_emotion, text)

        # ------------------------------------------------------------
        # TAHAP 4 — State Tracking & Context Building
        # ------------------------------------------------------------
        context = await run_in_threadpool(build_context, supabase, from_number, intent_result)

        # Sync nama kontak jika diperbarui di profil WA
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

        # Simpan pesan masuk pelanggan ke Supabase
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

        # Pesan lanjutan sering hanya berbunyi "jadi", "kurangin lagi", atau
        # "checkout". Pertahankan jumlah dari tawaran sebelumnya supaya
        # perhitungan bundle, balasan, dan invoice tidak kembali ke 1 unit.
        if not getattr(intent_result.entities, "quantity", None):
            remembered_quantity = await run_in_threadpool(
                get_last_requested_quantity, supabase, context.conversation_id
            )
            if remembered_quantity:
                intent_result.entities.quantity = remembered_quantity

        # ------------------------------------------------------------
        # TAHAP 4b — Handover / Human Agent Escalation Check
        # ------------------------------------------------------------
        already_handover = await run_in_threadpool(
            is_conversation_in_handover, supabase, context.conversation_id
        )
        if already_handover:
            logger.info(f"[WhatsAppWebhook] Conversation {context.conversation_id[:8]} in handover state. AI standby.")
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
                "Baik Kak, terima kasih informasinya 🙏\n\n"
                "Pesan Kakak telah kami teruskan langsung ke Tim Customer Support/Admin kami. "
                "Mohon tunggu sebentar ya, tim kami akan segera membantu Kakak secara personal!"
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
        # TAHAP 5a — ML Adaptive Scoring & Pricing Engine
        # ------------------------------------------------------------
        scoring_decision = await run_in_threadpool(
            _build_scoring_decision, context, intent_result, emotion_result
        )

        # ------------------------------------------------------------
        # TAHAP 5b — Vector Product Retrieval & Recommendations (RAG)
        # ------------------------------------------------------------
        recommended_products: List[Dict[str, Any]] = []
        should_recommend = intent_result.intent in (
            IntentType.REKOMENDASI,
            IntentType.TANYA_PRODUK,
            IntentType.GREETING,
        )

        if should_recommend or (
            intent_result.intent == IntentType.NEGO
            and scoring_decision.decision in (ScoringDecisionType.DISCOUNT, ScoringDecisionType.BONUS)
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
        # TAHAP 6 — Sales Response Generator
        # ------------------------------------------------------------
        reply_text = await run_in_threadpool(
            generate_response,
            context=context,
            intent_result=intent_result,
            emotion_result=emotion_result,
            scoring_decision=scoring_decision,
            recommended_products=recommended_products,
        )

        # Log transaksi negosiasi
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
                ai_offer_price=(final_p * max(int(getattr(intent_result.entities, "quantity", None) or 1), 1)) if final_p else final_p,
                floor_price_snapshot=floor_p,
                model_confidence=conf_score,
                outcome="pending",
            )

        # Simpan jawaban AI ke Supabase
        await run_in_threadpool(
            save_message,
            supabase=supabase,
            conversation_id=context.conversation_id,
            sender_type="ai",
            content_type="text",
            raw_text=reply_text,
        )

        # ------------------------------------------------------------
        # TAHAP 7 — Message Delivery & Checkout Direct Payment Engine
        # ------------------------------------------------------------
        if intent_result.intent == IntentType.CHECKOUT and getattr(context, "product_id", None):
            await _handle_checkout(
                supabase=supabase,
                from_number=from_number,
                context=context,
                scoring_decision=scoring_decision,
                reply_text=reply_text,
                intent_result=intent_result,
            )
        else:
            await send_text_message(from_number, reply_text)

        # Tutup sesi percakapan secara terstruktur jika transaksi telah checkout
        if intent_result.intent == IntentType.CHECKOUT:
            try:
                await run_in_threadpool(close_conversation, supabase, context.conversation_id)
            except Exception as exc:
                logger.warning(f"[WhatsAppWebhook] Non-fatal close conversation error: {exc}")

        logger.info(
            f"[WhatsAppWebhook] Pipeline finished for {from_number} | "
            f"Intent={intent_result.intent.value} | Emotion={emotion_result.emotion.value}"
        )

    except Exception as exc:
        logger.exception(f"[WhatsAppWebhook] Unhandled error during message processing for {from_number}: {exc}")
        try:
            await send_text_message(
                from_number,
                "Mohon maaf Kak, sistem kami sedang mengalami kendala teknis sementara 🙏 "
                "Tim kami akan segera mengecek dan menghubungi Kakak kembali.",
            )
        except Exception as send_err:
            logger.error(f"[WhatsAppWebhook] Failed to send error fallback message: {send_err}")


async def _handle_checkout(
    supabase: Any, from_number: str, context: Any, scoring_decision: Any, reply_text: str, intent_result: Any
) -> None:
    """
    Menangani Intent Checkout secara lengkap:
    1. Membuat record Order baru.
    2. Membuat Midtrans Instant QRIS / Payment Link.
    3. Mencatat Log Payment.
    4. Mengirimkan pesan konfirmasi beserta Tombol Interactive CTA Payment Link.
    """
    if not getattr(context, "product_id", None) or not getattr(context, "product_price", None):
        await send_text_message(from_number, reply_text)
        return

    try:
        quantity = max(
            int(getattr(getattr(intent_result, "entities", None), "quantity", None) or 0)
            or int(get_last_requested_quantity(supabase, context.conversation_id) or 1),
            1,
        )
        unit_price = float(context.product_price)

        # Checkout dapat terjadi sebagai pesan singkat setelah counter-offer.
        # Ambil total penawaran AI terakhir agar invoice memegang kesepakatan,
        # bukan kembali diam-diam ke harga satuan normal.
        last_nego = (
            supabase.table("negotiation_logs")
            .select("ai_offer_price, ai_decision")
            .eq("conversation_id", context.conversation_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        agreed_total = None
        if last_nego.data and last_nego.data[0].get("ai_decision") in ("discount", "counter_offer"):
            candidate = last_nego.data[0].get("ai_offer_price")
            if candidate is not None:
                agreed_total = float(candidate)

        total = agreed_total if agreed_total is not None else unit_price * quantity
        total = max(total, float(context.product_floor_price or 0.0) * quantity)
        discount_amount = max((unit_price * quantity) - total, 0.0)
        reply_text = (
            f"Baik Kak, saya siapkan {quantity} {getattr(context, 'product_name', 'produk')} "
            f"dengan total *Rp{total:,.0f}*. Silakan lanjutkan pembayarannya ya 😊"
        )

        # 1. Insert Order ke Database
        order_res = await run_in_threadpool(
            lambda: supabase.table("orders")
            .insert(
                {
                    "customer_id": context.customer_id,
                    "conversation_id": context.conversation_id,
                    "product_id": context.product_id,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount_amount": discount_amount,
                    "total_amount": total,
                    "status": "pending",
                }
            )
            .execute()
        )

        order_id = order_res.data[0]["id"]

        # 2. Panggil Client Midtrans QRIS Integration
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
            quantity=quantity,
        )

        # 3. Simpan Record Payment
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

        # 4. Kirim Teks Utama Konfirmasi
        await send_text_message(from_number, reply_text)

        # 5. Kirim WhatsApp Interactive CTA Link Button Pembayaran
        payment_url = payment_result.get("payment_url", "https://lariska.ai/pay")
        invoice_text = (
            f"🧾 *INVOICE PEMBAYARAN #{order_id[:8].upper()}*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"• *Produk:* {prod_name}\n"
            f"• *Jumlah:* {quantity} unit\n"
            f"• *Harga Normal:* Rp{unit_price:,.0f}/unit\n"
            f"• *Diskon Khusus:* Rp{discount_amount:,.0f}\n"
            f"• *Total Tagihan:* *Rp{total:,.0f}*\n\n"
            f"Silakan klik tombol di bawah untuk menyelesaikan pembayaran via QRIS / Bank Transfer:"
        )

        await send_interactive_cta(
            to=from_number,
            body_text=invoice_text,
            button_label="Bayar Sekarang 💳",
            payment_url=payment_url,
        )

        logger.info(f"[WhatsAppWebhook] Direct Checkout & Payment CTA sent successfully for Order #{order_id[:8]}")

    except Exception as exc:
        logger.error(f"[WhatsAppWebhook] Checkout processing error: {exc}", exc_info=True)
        await send_text_message(
            from_number,
            f"{reply_text}\n\n(Mohon maaf, terjadi kendala teknis saat menyiapkan tautan pembayaran. Tim Admin kami akan segera menghubungi Kakak secara pribadi 🙏)",
        )
