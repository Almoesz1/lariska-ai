"""
LARISKA AI — Sprint 4C
Payment Webhook — Midtrans Callback Handler

Endpoint yang dipanggil Midtrans saat status pembayaran berubah.
Saat pelanggan bayar QRIS → Midtrans POST ke sini → update tabel payments + orders + inventory_logs.

Setup requirements:
- URL harus publik: gunakan ngrok saat development (contoh: https://xxxx.ngrok.io/api/payment/webhook)
- Daftarkan URL ini di Midtrans Dashboard > Settings > Payment > Notification URL
- SIGNATURE_KEY validasi: SHA512(order_id + status_code + gross_amount + server_key)

Referensi proposal Bab 5 Tier 1: Invoice + QRIS sandbox, loop transaksi lengkap
"""

import hashlib
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status

from app.core.config import settings
from app.services.payment_client import parse_midtrans_status
from app.services.supabase_client import get_supabase

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
    Verifikasi bahwa notifikasi benar-benar dari Midtrans (bukan replay attack).
    Formula: SHA512(order_id + status_code + gross_amount + server_key)
    """
    server_key = settings.midtrans_server_key or ""
    raw_string = f"{order_id}{status_code}{gross_amount}{server_key}"
    expected = hashlib.sha512(raw_string.encode()).hexdigest()
    is_valid = expected == received_signature
    if not is_valid:
        logger.warning(
            f"[PaymentWebhook] Invalid signature for order_id={order_id}. "
            f"Expected={expected[:20]}... Received={received_signature[:20]}..."
        )
    return is_valid


# ============================================================
# Webhook Endpoint
# ============================================================

@router.post("/webhook")
async def midtrans_webhook(request: Request):
    """
    Terima notifikasi pembayaran dari Midtrans.

    Flow setelah payment sukses:
    1. Verifikasi signature Midtrans
    2. Cari payment record berdasarkan provider_reference (midtrans order_id)
    3. Update payments.status
    4. Update orders.status jadi 'paid'
    5. Kurangi products.stock + catat inventory_logs
    6. Return 200 OK (Midtrans retry kalau dapat status lain)
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body bukan JSON valid"
        )

    logger.info(f"[PaymentWebhook] Received: {data}")

    order_id = data.get("order_id", "")
    transaction_status = data.get("transaction_status", "")
    status_code = data.get("status_code", "")
    gross_amount = data.get("gross_amount", "")
    signature_key = data.get("signature_key", "")
    fraud_status = data.get("fraud_status")

    # --- Validasi signature ---
    if not _verify_midtrans_signature(order_id, status_code, gross_amount, signature_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Signature tidak valid"
        )

    # --- Konversi ke internal status ---
    internal_status = parse_midtrans_status(transaction_status, fraud_status)
    logger.info(
        f"[PaymentWebhook] order_id={order_id} "
        f"midtrans_status={transaction_status} → internal={internal_status}"
    )

    supabase = get_supabase()

    # --- Cari payment record berdasarkan provider_reference ---
    payment_res = (
        supabase.table("payments")
        .select("id, order_id, status, amount")
        .eq("provider_reference", order_id)
        .maybe_single()
        .execute()
    )

    if not payment_res.data:
        # Payment record belum ada — ini bisa terjadi saat initial notification
        # Coba cari order berdasarkan order_id format "LARISKA-XXXXXXXX"
        logger.warning(
            f"[PaymentWebhook] Payment record not found for {order_id}. "
            "Skipping (order may not have been created yet)."
        )
        # Return 200 agar Midtrans tidak retry terus
        return {"status": "ok", "message": "payment record not found, skipped"}

    payment = payment_res.data
    payment_id = payment["id"]
    lariska_order_id = payment["order_id"]

    # Idempotent: jika status sudah final, tidak perlu update lagi
    if payment["status"] in ("success", "failed", "expired"):
        logger.info(f"[PaymentWebhook] Payment {payment_id} already in final state: {payment['status']}. Skipping.")
        return {"status": "ok", "message": "already processed"}

    now_iso = datetime.now(timezone.utc).isoformat()

    # --- Update payments ---
    supabase.table("payments").update({
        "status": internal_status,
        "paid_at": now_iso if internal_status == "success" else None,
    }).eq("id", payment_id).execute()
    logger.info(f"[PaymentWebhook] Payment {payment_id} updated to {internal_status}")

    # --- Jika sukses: update order + kurangi stok ---
    if internal_status == "success":
        # Update order status
        supabase.table("orders").update({
            "status": "paid",
        }).eq("id", lariska_order_id).execute()
        logger.info(f"[PaymentWebhook] Order {lariska_order_id} marked as paid")

        # Ambil detail order untuk update stok
        order_res = (
            supabase.table("orders")
            .select("product_id, quantity")
            .eq("id", lariska_order_id)
            .maybe_single()
            .execute()
        )

        if order_res.data:
            product_id = order_res.data["product_id"]
            qty_sold = order_res.data["quantity"]

            # Ambil stok saat ini
            prod_res = (
                supabase.table("products")
                .select("stock")
                .eq("id", product_id)
                .maybe_single()
                .execute()
            )

            if prod_res.data:
                stock_before = prod_res.data["stock"]
                stock_after = max(stock_before - qty_sold, 0)  # Tidak boleh negatif

                # Update stok produk
                supabase.table("products").update({
                    "stock": stock_after
                }).eq("id", product_id).execute()

                # Catat inventory_log
                supabase.table("inventory_logs").insert({
                    "product_id": product_id,
                    "change_type": "sale",
                    "quantity_change": -qty_sold,
                    "stock_before": stock_before,
                    "stock_after": stock_after,
                    "reference_order_id": lariska_order_id,
                }).execute()

                logger.info(
                    f"[PaymentWebhook] Inventory updated: "
                    f"product={product_id[:8]} "
                    f"stock {stock_before} → {stock_after}"
                )

    return {"status": "ok"}


# ============================================================
# Manual trigger untuk create payment (dipanggil dari WhatsApp flow)
# ============================================================

@router.post("/create")
async def create_payment_for_order(request: Request):
    """
    Buat payment record dan return QRIS URL untuk dikirim ke pelanggan WA.
    Dipanggil saat AI pipeline memutuskan checkout.

    Body:
        order_id: UUID order yang sudah ada di tabel orders
    """
    try:
        body = await request.json()
        order_id = body.get("order_id")
    except Exception:
        raise HTTPException(status_code=400, detail="Body JSON tidak valid")

    if not order_id:
        raise HTTPException(status_code=400, detail="order_id diperlukan")

    supabase = get_supabase()

    # Ambil order + customer + product
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
            detail=f"Order berstatus '{order['status']}', hanya order 'pending' yang bisa dibayar."
        )

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

    # Import di sini untuk menghindari circular import
    from app.services.payment_client import create_qris_payment

    payment_result = create_qris_payment(
        order_id=order_id,
        amount=float(order["total_amount"]),
        customer_name=customer.get("name", "Pelanggan"),
        customer_phone=customer.get("whatsapp_number", ""),
        product_name=product.get("name", "Produk"),
        quantity=order["quantity"],
    )

    midtrans_order_id = payment_result["midtrans_order_id"]

    # Simpan payment record ke database
    supabase.table("payments").insert({
        "order_id": order_id,
        "method": "qris",
        "status": "pending",
        "amount": float(order["total_amount"]),
        "provider_reference": midtrans_order_id,
    }).execute()

    logger.info(f"[PaymentWebhook] Payment record created for order {order_id}")

    return {
        "order_id": order_id,
        "payment_url": payment_result["payment_url"],
        "midtrans_order_id": midtrans_order_id,
        "amount": float(order["total_amount"]),
        "message": f"Silakan bayar via link berikut: {payment_result['payment_url']}",
    }
