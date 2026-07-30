"""
LARISKA AI — Sprint 6
WhatsApp Cloud API Client — Send Messages & Media (Async)

Fitur:
- Meta Cloud API v23.0
- Kirim pesan teks biasa
- Kirim pesan interaktif CTA (Call-To-Action Link / QRIS Payment)
- Download media (Voice Note / Audio)
- Read Receipt (Centang Biru)

Desain:
SEMUA fungsi di file ini murni Async (menggunakan httpx.AsyncClient).
"""

import logging
import mimetypes
from typing import Dict, Any, Tuple, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_WA_API_BASE = "https://graph.facebook.com/v23.0"
_TIMEOUT_SECONDS = 30.0


def _get_token() -> str:
    """Ambil WhatsApp Access Token dari konfigurasi settings dengan fallback."""
    token = getattr(settings, "whatsapp_token", None) or getattr(settings, "whatsapp_access_token", None)
    if not token:
        raise RuntimeError(
            "WHATSAPP_TOKEN / WHATSAPP_ACCESS_TOKEN tidak ditemukan di .env. "
            "Dapatkan dari Meta Developer Console > WhatsApp > API Setup."
        )
    return token


def _get_phone_id() -> str:
    """Ambil WhatsApp Phone Number ID dari konfigurasi settings."""
    phone_id = getattr(settings, "whatsapp_phone_number_id", None)
    if not phone_id:
        raise RuntimeError("WHATSAPP_PHONE_NUMBER_ID tidak ditemukan di .env.")
    return phone_id


def _get_headers() -> Dict[str, str]:
    """Buat HTTP Header otentikasi Meta API."""
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Content-Type": "application/json",
    }


async def send_text_message(to: str, text: str) -> Dict[str, Any]:
    """
    Kirim pesan teks ke nomor WhatsApp pelanggan secara asinkron.
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

    log_text = f"'{text[:60]}...'" if len(text) > 60 else f"'{text}'"
    logger.info(f"[WhatsAppClient] Sending text to {to}: {log_text}")

    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
        try:
            response = await client.post(url, headers=_get_headers(), json=payload)
            response.raise_for_status()
            result = response.json()
            msg_id = result.get("messages", [{}])[0].get("id", "unknown")
            logger.info(f"[WhatsAppClient] Text message sent successfully. ID: {msg_id}")
            return result
        except httpx.HTTPStatusError as exc:
            logger.error(
                f"[WhatsAppClient] HTTP Error sending text ({exc.response.status_code}): {exc.response.text}"
            )
            raise
        except Exception as exc:
            logger.error(f"[WhatsAppClient] Unexpected error sending text: {exc}")
            raise


async def send_interactive_cta(
    to: str, body_text: str, button_label: str, payment_url: str
) -> Dict[str, Any]:
    """
    Kirim pesan interaktif dengan tombol CTA (Call-to-Action) untuk Link Pembayaran/QRIS.
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
                    "display_text": button_label[:20],  # Meta max 20 chars limit
                    "url": payment_url,
                },
            },
        },
    }

    logger.info(f"[WhatsAppClient] Sending CTA to {to}: Label='{button_label}' -> URL={payment_url}")

    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
        try:
            response = await client.post(url, headers=_get_headers(), json=payload)
            response.raise_for_status()
            result = response.json()
            logger.info(f"[WhatsAppClient] CTA Message sent successfully to {to}")
            return result
        except httpx.HTTPStatusError as exc:
            logger.error(
                f"[WhatsAppClient] HTTP Error sending CTA ({exc.response.status_code}): {exc.response.text}"
            )
            raise
        except Exception as exc:
            logger.error(f"[WhatsAppClient] Unexpected error sending CTA: {exc}")
            raise


async def download_media(media_id: str) -> Tuple[bytes, str]:
    """
    Download file media (Voice Note / Audio) dari WhatsApp menggunakan media_id.
    Tahap:
    1. Mengambil URL unduhan sementara via Graph API.
    2. Mendownload binary bytes dari URL tersebut.
    """
    headers = _get_headers()

    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
        # Step 1: Request metadata media
        meta_resp = await client.get(f"{_WA_API_BASE}/{media_id}", headers=headers)
        meta_resp.raise_for_status()
        media_info = meta_resp.json()

        media_url = media_info.get("url")
        mime_type = media_info.get("mime_type", "audio/ogg")

        if not media_url:
            raise RuntimeError(f"Gagal mendapatkan URL unduhan untuk media_id={media_id}")

        # Step 2: Request binary content
        download_resp = await client.get(media_url, headers=headers)
        download_resp.raise_for_status()

    # Penentuan ekstensi file berdasarkan mime_type
    clean_mime = mime_type.split(";")[0].strip()
    ext = mimetypes.guess_extension(clean_mime) or ".ogg"
    if "ogg" in clean_mime:
        ext = ".ogg"
    elif "mp4" in clean_mime or "aac" in clean_mime or "m4a" in clean_mime:
        ext = ".mp4"

    filename = f"voice_note_{media_id[:8]}{ext}"
    logger.info(
        f"[WhatsAppClient] Downloaded media {media_id[:8]}: {len(download_resp.content)} bytes, mime={mime_type}"
    )

    return download_resp.content, filename


async def mark_message_as_read(message_id: str) -> None:
    """
    Tandai pesan pelanggan sebagai 'sudah dibaca' (centang biru).
    Kegagalan pada fungsi ini diisolasi agar tidak mengganggu aliran utama.
    """
    if not message_id:
        return

    try:
        phone_id = _get_phone_id()
        url = f"{_WA_API_BASE}/{phone_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(url, headers=_get_headers(), json=payload)
        logger.debug(f"[WhatsAppClient] Marked message {message_id} as read.")
    except Exception as exc:
        logger.warning(f"[WhatsAppClient] Non-fatal: Failed to mark message {message_id} as read: {exc}")