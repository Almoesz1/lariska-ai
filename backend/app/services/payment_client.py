"""
LARISKA AI — Sprint 4C & QA Audit
Payment Client — Midtrans Sandbox Integration

Mengintegrasikan Midtrans Snap & Core API untuk membuat QRIS payment link dan mengecek status transaksi.
Digunakan saat pelanggan menyetujui harga dan meminta pembayaran.

Mode: Sandbox / Production (dikontrol via MIDTRANS_IS_PRODUCTION di .env)
Referensi proposal Bab 5 Tier 1: Invoice + QRIS Sandbox
"""

import logging
from typing import Any, Dict, Optional

import midtransclient

from app.core.config import settings

logger = logging.getLogger(__name__)

# Singletons internal untuk Snap dan CoreAPI
_snap_client: Optional[midtransclient.Snap] = None
_core_api_client: Optional[midtransclient.CoreApi] = None


def _get_snap() -> midtransclient.Snap:
    """Mengambil atau menginisialisasi instance Midtrans Snap API."""
    global _snap_client
    if _snap_client is not None:
        return _snap_client

    server_key = settings.midtrans_server_key
    if not server_key:
        raise RuntimeError(
            "MIDTRANS_SERVER_KEY tidak ada di .env. "
            "Dapatkan server key dari Dashboard Midtrans Sandbox."
        )

    _snap_client = midtransclient.Snap(
        is_production=settings.midtrans_is_production,
        server_key=server_key,
        client_key=settings.midtrans_client_key,
    )
    logger.info(
        f"[PaymentClient] Midtrans Snap client initialized (production={settings.midtrans_is_production})"
    )
    return _snap_client


def _get_core_api() -> midtransclient.CoreApi:
    """Mengambil atau menginisialisasi instance Midtrans Core API."""
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


def create_qris_payment(
    order_id: str,
    amount: float,
    customer_name: str,
    customer_phone: str,
    product_name: str,
    quantity: int = 1,
) -> Dict[str, Any]:
    """
    Membuat transaksi QRIS via Midtrans Snap API.

    Args:
        order_id: UUID order dari tabel orders.
        amount: Total harga pembayaran dalam Rupiah.
        customer_name: Nama pelanggan.
        customer_phone: Nomor WhatsApp pelanggan.
        product_name: Nama produk/layanan.
        quantity: Jumlah unit barang.

    Returns:
        Dict berisi 'token', 'redirect_url', 'payment_url', dan 'midtrans_order_id'.
    """
    snap = _get_snap()

    # Midtrans mengharuskan amount berupa integer Rupiah utuh
    amount_int = int(round(amount))
    quantity_safe = max(1, quantity)
    unit_price = amount_int // quantity_safe

    # Format ID transaksi khusus Midtrans
    midtrans_order_id = f"LARISKA-{order_id[:8].upper()}"

    param = {
        "transaction_details": {
            "order_id": midtrans_order_id,
            "gross_amount": amount_int,
        },
        "item_details": [
            {
                "id": order_id[:8],
                "price": unit_price,
                "quantity": quantity_safe,
                "name": product_name[:50],  # Maksimal 50 karakter untuk Midtrans
            }
        ],
        "customer_details": {
            "first_name": customer_name or "Pelanggan",
            "phone": customer_phone,
        },
        "enabled_payments": ["qris"],  # Khusus transaksi QRIS
        "expiry": {
            "unit": "hour",
            "duration": 24,  # QRIS aktif selama 24 jam
        },
    }

    logger.info(
        f"[PaymentClient] Membuat QRIS untuk order {midtrans_order_id}, amount=Rp{amount_int:,}"
    )

    try:
        transaction = snap.create_transaction(param)
        redirect_url = transaction.get("redirect_url")
        result = {
            "token": transaction.get("token"),
            "redirect_url": redirect_url,
            "payment_url": redirect_url,
            "midtrans_order_id": midtrans_order_id,
        }
        logger.info(f"[PaymentClient] QRIS berhasil dibuat: {redirect_url}")
        return result
    except Exception as exc:
        logger.error(f"[PaymentClient] Midtrans error: {exc}")
        raise RuntimeError(f"Gagal membuat transaksi QRIS: {exc}") from exc


def check_transaction_status(midtrans_order_id: str) -> Dict[str, Any]:
    """
    Pengecekan status transaksi ke Midtrans Core API.
    """
    core = _get_core_api()
    try:
        status = core.transactions.status(midtrans_order_id)
        logger.info(
            f"[PaymentClient] Status {midtrans_order_id}: {status.get('transaction_status')}"
        )
        return status
    except Exception as exc:
        logger.error(f"[PaymentClient] Gagal mengecek status transaksi: {exc}")
        raise


def parse_midtrans_status(
    transaction_status: str, fraud_status: Optional[str] = None
) -> str:
    """
    Pemetaan status transaksi Midtrans ke status internal LARISKA AI.
    Returns: 'pending' | 'success' | 'failed' | 'expired'
    """
    if transaction_status in ("settlement", "capture"):
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