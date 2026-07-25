"""
LARISKA AI — Sprint 4C
Payment Client — Midtrans Sandbox Integration

Mengintegrasikan Midtrans Snap API untuk membuat QRIS payment link.
Digunakan saat pelanggan setuju harga dan minta invoice/QRIS.

Mode: Sandbox (MIDTRANS_IS_PRODUCTION=false di .env)
Fitur: Buat transaksi, generate QRIS/payment link, simpan ke tabel payments

Referensi proposal Bab 5 Tier 1: Invoice + QRIS sandbox
"""

import logging
from typing import Optional
from uuid import uuid4

import midtransclient

from app.core.config import settings

logger = logging.getLogger(__name__)

# ============================================================
# Midtrans Client — lazy singleton
# ============================================================

_snap_client = None
_core_api_client = None


def _get_snap():
    global _snap_client
    if _snap_client is not None:
        return _snap_client

    server_key = settings.midtrans_server_key
    if not server_key:
        raise RuntimeError(
            "MIDTRANS_SERVER_KEY tidak ada di .env. "
            "Daftar di https://dashboard.midtrans.com untuk mendapatkan sandbox key."
        )

    _snap_client = midtransclient.Snap(
        is_production=settings.midtrans_is_production,
        server_key=server_key,
        client_key=settings.midtrans_client_key,
    )
    logger.info(
        f"[PaymentClient] Midtrans Snap initialized "
        f"(production={settings.midtrans_is_production})"
    )
    return _snap_client


def _get_core_api():
    global _core_api_client
    if _core_api_client is not None:
        return _core_api_client

    server_key = settings.midtrans_server_key
    if not server_key:
        raise RuntimeError("MIDTRANS_SERVER_KEY tidak ada di .env.")

    _core_api_client = midtransclient.CoreApi(
        is_production=settings.midtrans_is_production,
        server_key=server_key,
        client_key=settings.midtrans_client_key,
    )
    return _core_api_client


# ============================================================
# Create Payment Transaction
# ============================================================

def create_qris_payment(
    order_id: str,
    amount: float,
    customer_name: str,
    customer_phone: str,
    product_name: str,
    quantity: int = 1,
) -> dict:
    """
    Buat transaksi QRIS via Midtrans Snap API.

    Args:
        order_id: UUID order dari tabel orders (dipakai sebagai Midtrans order_id).
        amount: Total pembayaran dalam Rupiah (tanpa desimal).
        customer_name: Nama pelanggan untuk detail transaksi.
        customer_phone: Nomor WA pelanggan.
        product_name: Nama produk untuk detail item.
        quantity: Jumlah unit.

    Returns:
        Dict dengan keys: 'token', 'redirect_url', 'payment_url'
        - token: Midtrans Snap token (untuk embed di frontend)
        - redirect_url: URL langsung ke payment page
        - payment_url: Alias redirect_url (nama lebih deskriptif)

    Raises:
        RuntimeError: Jika Midtrans API error.
    """
    snap = _get_snap()

    # Midtrans mengharuskan amount berupa integer (Rupiah penuh)
    amount_int = int(round(amount))

    # order_id unik per transaksi — gunakan order_id dari database
    # kalau ada retry, tambahkan suffix unik
    midtrans_order_id = f"LARISKA-{order_id[:8].upper()}"

    param = {
        "transaction_details": {
            "order_id": midtrans_order_id,
            "gross_amount": amount_int,
        },
        "item_details": [
            {
                "id": order_id[:8],
                "price": amount_int // quantity,
                "quantity": quantity,
                "name": product_name[:50],  # Midtrans max 50 chars
            }
        ],
        "customer_details": {
            "first_name": customer_name or "Pelanggan",
            "phone": customer_phone,
        },
        "enabled_payments": ["qris"],  # Hanya QRIS untuk demo
        "expiry": {
            "unit": "hour",
            "duration": 24,  # QRIS expired dalam 24 jam
        },
    }

    logger.info(
        f"[PaymentClient] Creating QRIS for order {midtrans_order_id}, "
        f"amount=Rp{amount_int:,}"
    )

    try:
        transaction = snap.create_transaction(param)
        result = {
            "token": transaction.get("token"),
            "redirect_url": transaction.get("redirect_url"),
            "payment_url": transaction.get("redirect_url"),
            "midtrans_order_id": midtrans_order_id,
        }
        logger.info(f"[PaymentClient] QRIS created: {result['redirect_url']}")
        return result
    except Exception as exc:
        logger.error(f"[PaymentClient] Midtrans error: {exc}")
        raise RuntimeError(f"Gagal membuat QRIS: {exc}") from exc


def check_transaction_status(midtrans_order_id: str) -> dict:
    """
    Cek status transaksi Midtrans (polling dari dashboard admin atau webhook fallback).

    Returns:
        Dict dengan keys: 'transaction_status', 'fraud_status', 'payment_type'
    """
    core = _get_core_api()
    try:
        status = core.transactions.status(midtrans_order_id)
        logger.info(
            f"[PaymentClient] Status {midtrans_order_id}: "
            f"{status.get('transaction_status')}"
        )
        return status
    except Exception as exc:
        logger.error(f"[PaymentClient] Status check error: {exc}")
        raise


def parse_midtrans_status(transaction_status: str, fraud_status: Optional[str] = None) -> str:
    """
    Konversi Midtrans transaction_status ke status internal LARISKA:
    'pending' | 'success' | 'failed' | 'expired'

    Referensi: https://docs.midtrans.com/reference/get-transaction-status
    """
    if transaction_status == "settlement" or transaction_status == "capture":
        if fraud_status in (None, "accept"):
            return "success"
        return "failed"
    if transaction_status == "pending":
        return "pending"
    if transaction_status in ("deny", "cancel", "failure"):
        return "failed"
    if transaction_status == "expire":
        return "expired"
    return "pending"
