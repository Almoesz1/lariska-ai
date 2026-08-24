"""
LARISKA AI — Backend Payment Webhook
File: app/api/payment_webhook.py

Endpoint webhook callback Midtrans & endpoint manual creation payment.
Mengintegrasikan:
1. Validasi SHA512 Signature Key Midtrans.
2. Update tabel payments & orders di Supabase.
3. Otomasi pemotongan stok di products + pencatatan audit di inventory_logs.
4. Otomasi pengiriman notifikasi konfirmasi pembayaran via WhatsApp Client ke pelanggan.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request, status

from app.core.config import settings
from app.services.payment_client import create_qris_payment, parse_midtrans_status
from app.services.supabase_client import get_supabase
from app.services.whatsapp_client import WhatsAppClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payment", tags=["payment"])


# ============================================================
# Signature Verification
# ============================================================

def _verify_midtrans_signature(
    order_id: str,
    status_code: str,
    gross_amount: str,
    received_signature: str,
) -> bool:
    """
    Verifikasi bahwa notifikasi berasal resmi dari Midtrans.
    Formula Midtrans: SHA512(order_id + status_code + gross_amount + server_key)
    """
    server_key = getattr(settings, "midtrans_server_key", None) or getattr(settings, "MIDTRANS_SERVER_KEY", "")
    raw_string = f"{order_id}{status_code}{gross_amount}{server_key}"
    expected = hashlib.sha512(raw_string.encode("utf-8")).hexdigest()
    
    is_valid = expected.lower() == received_signature.lower()
    if not is_valid:
        logger.warning(
            f"[PaymentWebhook] Invalid signature for order_id={order_id}. "
            f"Expected={expected[:20]}... Received={received_signature[:20]}..."
        )
    return is_valid


# ============================================================
# Webhook Endpoint (Midtrans Callback)
# ============================================================

@router.post("/webhook")
async def midtrans_webhook(request: Request) -> Dict[str, Any]:
    """
    Callback handler dari Midtrans ketika status transaksi berubah.

    Alur ketika status = 'success':
    1. Verifikasi Signature SHA512 Midtrans.
    2. Cek payment record di Supabase (by provider_reference).
    3. Update status di tabel payments.
    4. Update status di tabel orders menjadi 'paid'.
    5. Potong stok produk di tabel products & catat audit di inventory_logs.
    6. Ambil kontak pelanggan & kirim notifikasi WhatsApp otomatis.
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body bukan JSON valid"
        )

    logger.info(f"[PaymentWebhook] Received notification: {data}")

    order_id = str(data.get("order_id", ""))
    transaction_status = str(data.get("transaction_status", ""))
    status_code = str(data.get("status_code", ""))
    gross_amount = str(data.get("gross_amount", ""))
    signature_key = str(data.get("signature_key", ""))
    fraud_status = data.get("fraud_status")

    # 1. Validasi Signature
    if not _verify_midtrans_signature(order_id, status_code, gross_amount, signature_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Signature tidak valid"
        )

    # 2. Konversi ke status internal LARISKA
    internal_status = parse_midtrans_status(transaction_status, fraud_status)
    logger.info(
        f"[PaymentWebhook] order_id={order_id} | "
        f"midtrans_status={transaction_status} -> internal={internal_status}"
    )

    supabase = get_supabase()

    # Ledger permanen: Midtrans dapat mengirim ulang notifikasi yang sama.
    # Key memasukkan status agar transisi status yang berbeda tetap tercatat.
    external_event_id = f"{order_id}:{transaction_status}:{status_code}"
    claimed = supabase.rpc(
        "claim_webhook_event",
        {
            "p_provider": "midtrans",
            "p_external_event_id": external_event_id,
            "p_event_type": "payment_notification",
            "p_payload": data,
        },
    ).execute()
    if not claimed.data:
        logger.info(f"[PaymentWebhook] Duplicate Midtrans event {external_event_id}; skipped.")
        return {"status": "ok", "message": "duplicate event skipped"}

    # 3. Cari payment record berdasarkan provider_reference (Midtrans Order ID)
    payment_res = (
        supabase.table("payments")
        .select("id, order_id, status, amount")
        .eq("provider_reference", order_id)
        .maybe_single()
        .execute()
    )

    # Midtrans "Test notification URL" dapat memakai order_id contoh yang
    # memang belum ada di tabel payments. Respons query dapat berupa None
    # tergantung versi client Supabase; webhook wajib tetap membalas 200 agar
    # endpoint tervalidasi, tanpa mengubah transaksi apa pun.
    if not payment_res or not payment_res.data:
        logger.warning(
            f"[PaymentWebhook] Payment record tidak ditemukan untuk provider_reference={order_id}. "
            "Skipping processing."
        )
        return {"status": "ok", "message": "payment record not found, skipped"}

    payment = payment_res.data
    payment_id = payment["id"]
    lariska_order_id = payment["order_id"]

    supabase.table("payment_events").upsert(
        {
            "payment_id": payment_id,
            "provider": "midtrans",
            "external_event_id": external_event_id,
            "event_type": "payment_notification",
            "transaction_status": transaction_status,
            "payload": data,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="provider,external_event_id",
    ).execute()

    # 4. Idempotency Check: Jika status transaksi sudah final, tidak perlu diproses ulang
    if payment["status"] in ("success", "failed", "expired"):
        logger.info(
            f"[PaymentWebhook] Payment {payment_id} sudah berada pada status final: {payment['status']}. Skipped."
        )
        return {"status": "ok", "message": "already processed"}

    now_iso = datetime.now(timezone.utc).isoformat()

    # 5. Update status di tabel payments
    supabase.table("payments").update({
        "status": internal_status,
        "paid_at": now_iso if internal_status == "success" else None,
    }).eq("id", payment_id).execute()
    supabase.table("orders").update({"payment_status_snapshot": internal_status}).eq("id", lariska_order_id).execute()

    logger.info(f"[PaymentWebhook] Status payment {payment_id} berhasil diubah ke '{internal_status}'")

    # 6. Jalankan Logika Bisnis Ketika Pembayaran Sukses
    if internal_status == "success":
        # A. Update status order menjadi 'paid'
        supabase.table("orders").update({
            "status": "paid",
        }).eq("id", lariska_order_id).execute()
        logger.info(f"[PaymentWebhook] Status order {lariska_order_id} diperbarui menjadi 'paid'")

        # B. Ambil detail order
        order_res = (
            supabase.table("orders")
            .select("product_id, quantity, customer_id, total_amount")
            .eq("id", lariska_order_id)
            .maybe_single()
            .execute()
        )

        if order_res.data:
            product_id = order_res.data["product_id"]
            qty_sold = order_res.data["quantity"]
            customer_id = order_res.data["customer_id"]
            total_amount = float(order_res.data.get("total_amount", 0))

            # C. Potong stok + audit dalam satu RPC transaksional.
            prod_res = supabase.table("products").select("name").eq("id", product_id).maybe_single().execute()
            product_name = (prod_res.data or {}).get("name", "Produk LARISKA")
            inventory_res = supabase.rpc(
                "confirm_inventory_sale",
                {"p_order_id": lariska_order_id, "p_product_id": product_id, "p_quantity": qty_sold},
            ).execute()
            if inventory_res.data and inventory_res.data[0].get("inventory_applied"):
                stock_before = inventory_res.data[0]["stock_before"]
                stock_after = inventory_res.data[0]["stock_after"]
                logger.info(
                    f"[PaymentWebhook] Inventory diperbarui: product={product_id[:8]} "
                    f"| Stok: {stock_before} -> {stock_after}"
                )

            # D. Kirim Notifikasi Konfirmasi via WhatsApp
            customer_res = (
                supabase.table("customers")
                .select("whatsapp_number, name")
                .eq("id", customer_id)
                .maybe_single()
                .execute()
            )

            if customer_res.data and customer_res.data.get("whatsapp_number"):
                wa_number = customer_res.data["whatsapp_number"]
                cust_name = customer_res.data.get("name") or "Kak"

                try:
                    wa_client = WhatsAppClient()
                    success_message = (
                        f"Halo {cust_name}! 🎉\n\n"
                        f"Pembayaran Anda untuk *{product_name}* ({qty_sold}x) "
                        f"sebesar *Rp {total_amount:,.0f}* telah berhasil kami terima!\n\n"
                        f"Pesanan Anda sedang diproses oleh tim kami. Terima kasih banyak telah berbelanja di LARISKA! 😊"
                    )
                    await wa_client.send_text(to=wa_number, text=success_message)
                    logger.info(f"[PaymentWebhook] Notifikasi WA berhasil dikirim ke {wa_number}")
                except Exception as wa_err:
                    logger.error(f"[PaymentWebhook] Gagal mengirim notifikasi WA ke {wa_number}: {str(wa_err)}")

    supabase.table("webhook_events").update(
        {"processing_status": "processed", "processed_at": datetime.now(timezone.utc).isoformat()}
    ).eq("provider", "midtrans").eq("external_event_id", external_event_id).execute()
    return {"status": "ok"}


# ============================================================
# Endpoint Trigger Manual Create Payment
# ============================================================

@router.post("/create")
async def create_payment_for_order(request: Request) -> Dict[str, Any]:
    """
    Membuat payment record & memicu integrasi Midtrans untuk menghasilkan URL QRIS.
    Dipanggil dari pipeline Sales Brain AI saat konfirmasi checkout.
    """
    try:
        body = await request.json()
        order_id = body.get("order_id")
    except Exception:
        raise HTTPException(status_code=400, detail="Body JSON tidak valid")

    if not order_id:
        raise HTTPException(status_code=400, detail="Parameter order_id wajib diisi")

    supabase = get_supabase()

    # 1. Ambil Data Order
    order_res = (
        supabase.table("orders")
        .select("id, customer_id, product_id, quantity, total_amount, status")
        .eq("id", order_id)
        .maybe_single()
        .execute()
    )
    if not order_res.data:
        raise HTTPException(status_code=404, detail="Order tidak ditemukan")

    order = order_res.data
    if order["status"] != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Order berstatus '{order['status']}'. Hanya order berstatus 'pending' yang dapat dibayar."
        )

    # 2. Ambil Data Customer & Produk
    customer_res = (
        supabase.table("customers")
        .select("name, whatsapp_number")
        .eq("id", order["customer_id"])
        .maybe_single()
        .execute()
    )
    customer = customer_res.data or {}

    product_res = (
        supabase.table("products")
        .select("name")
        .eq("id", order["product_id"])
        .maybe_single()
        .execute()
    )
    product = product_res.data or {}

    # 3. Panggil Midtrans Client Service
    payment_result = create_qris_payment(
        order_id=order_id,
        amount=float(order["total_amount"]),
        customer_name=customer.get("name", "Pelanggan"),
        customer_phone=customer.get("whatsapp_number", ""),
        product_name=product.get("name", "Produk"),
        quantity=order["quantity"],
    )

    midtrans_order_id = payment_result["midtrans_order_id"]

    # 4. Insert Payment Record ke Supabase
    supabase.table("payments").insert({
        "order_id": order_id,
        "method": "qris",
        "status": "pending",
        "amount": float(order["total_amount"]),
        "provider_reference": midtrans_order_id,
    }).execute()

    logger.info(f"[PaymentWebhook] Payment record berhasil dibuat untuk order_id={order_id}")

    return {
        "order_id": order_id,
        "payment_url": payment_result["payment_url"],
        "midtrans_order_id": midtrans_order_id,
        "amount": float(order["total_amount"]),
        "message": f"Silakan lakukan pembayaran via link berikut: {payment_result['payment_url']}",
    }
