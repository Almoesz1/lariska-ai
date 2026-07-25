"""
LARISKA AI — Sprint 6
WhatsApp Cloud API Client — Send Messages

Mengirim pesan kembali ke pelanggan via WhatsApp Cloud API (Meta resmi).
Mendukung: teks biasa, teks dengan tombol CTA (reply button), download media (voice note).

Setup:
1. Buat Meta Developer App di developers.facebook.com
2. Aktifkan WhatsApp Cloud API
3. Isi .env: WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_VERIFY_TOKEN

Referensi proposal Bab 15: WhatsApp Cloud API (Meta, resmi)
"""

import logging
import mimetypes
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# WhatsApp Cloud API base URL
_WA_API_BASE = "https://graph.facebook.com/v19.0"


def _get_headers() -> dict:
    token = settings.whatsapp_token
    if not token:
        raise RuntimeError(
            "WHATSAPP_TOKEN tidak ada di .env. "
            "Dapatkan dari Meta Developer Console > WhatsApp > API Setup."
        )
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _get_phone_id() -> str:
    phone_id = settings.whatsapp_phone_number_id
    if not phone_id:
        raise RuntimeError("WHATSAPP_PHONE_NUMBER_ID tidak ada di .env.")
    return phone_id


def send_text_message(to: str, text: str) -> dict:
    """
    Kirim pesan teks ke nomor WhatsApp.

    Args:
        to: Nomor WA penerima (format internasional tanpa +, contoh: '6281234567890')
        text: Teks pesan (mendukung basic markdown WhatsApp: *bold*, _italic_)

    Returns:
        Response dari WhatsApp API.
    """
    phone_id = _get_phone_id()
    url = f"{_WA_API_BASE}/{phone_id}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": text,
        },
    }

    logger.info(f"[WhatsAppClient] Sending text to {to}: '{text[:60]}...' " if len(text) > 60 else f"[WhatsAppClient] Sending text to {to}: '{text}'")

    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, headers=_get_headers(), json=payload)
        response.raise_for_status()
        result = response.json()
        logger.info(f"[WhatsAppClient] Message sent: {result.get('messages', [{}])[0].get('id', 'unknown')}")
        return result


def send_interactive_cta(to: str, body_text: str, button_label: str, payment_url: str) -> dict:
    """
    Kirim pesan dengan tombol CTA (Call-to-Action) untuk payment link.
    Dipakai saat AI generate invoice + QRIS → tombol "Bayar Sekarang".

    Args:
        to: Nomor WA penerima.
        body_text: Teks utama pesan (berisi detail order).
        button_label: Label tombol (maks 20 karakter).
        payment_url: URL QRIS/payment yang dibuka saat tombol diklik.
    """
    phone_id = _get_phone_id()
    url = f"{_WA_API_BASE}/{phone_id}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "cta_url",
            "body": {"text": body_text},
            "action": {
                "name": "cta_url",
                "parameters": {
                    "display_text": button_label[:20],
                    "url": payment_url,
                },
            },
        },
    }

    logger.info(f"[WhatsAppClient] Sending CTA to {to}: '{button_label}' → {payment_url}")

    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, headers=_get_headers(), json=payload)
        response.raise_for_status()
        return response.json()


def download_media(media_id: str) -> tuple[bytes, str]:
    """
    Download media (voice note) dari WhatsApp menggunakan media_id.
    Diperlukan sebelum voice note bisa di-transkripsi oleh Whisper.

    Args:
        media_id: ID media dari payload webhook WhatsApp.

    Returns:
        Tuple (audio_bytes, filename) — bytes audio dan nama file dengan ekstensi.
    """
    headers = _get_headers()

    # Step 1: Dapatkan URL download dari media_id
    with httpx.Client(timeout=30.0) as client:
        meta_resp = client.get(
            f"{_WA_API_BASE}/{media_id}",
            headers=headers,
        )
        meta_resp.raise_for_status()
        media_url = meta_resp.json().get("url")
        mime_type = meta_resp.json().get("mime_type", "audio/ogg")

        if not media_url:
            raise RuntimeError(f"Tidak bisa mendapatkan URL untuk media_id={media_id}")

        # Step 2: Download bytes dari URL
        download_resp = client.get(media_url, headers=headers)
        download_resp.raise_for_status()

    # Tentukan ekstensi dari MIME type
    ext = mimetypes.guess_extension(mime_type.split(";")[0]) or ".ogg"
    # WhatsApp sering kirim audio/ogg;codecs=opus — normalize ke .ogg
    if "ogg" in mime_type:
        ext = ".ogg"
    elif "mp4" in mime_type or "aac" in mime_type:
        ext = ".mp4"

    filename = f"voice_note_{media_id[:8]}{ext}"
    logger.info(f"[WhatsAppClient] Downloaded media: {len(download_resp.content)} bytes, type={mime_type}")

    return download_resp.content, filename


def mark_message_as_read(message_id: str) -> None:
    """
    Tandai pesan sebagai sudah dibaca (centang biru).
    Best practice: langsung mark read saat pesan diterima webhook.
    """
    try:
        phone_id = _get_phone_id()
        url = f"{_WA_API_BASE}/{phone_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        with httpx.Client(timeout=10.0) as client:
            client.post(url, headers=_get_headers(), json=payload)
        logger.debug(f"[WhatsAppClient] Marked {message_id} as read.")
    except Exception as exc:
        # Non-fatal — tidak perlu crash pipeline hanya karena mark-read gagal
        logger.warning(f"[WhatsAppClient] Failed to mark as read: {exc}")
