"""
LARISKA AI — Sprint 6
WhatsApp Cloud API Client — Send Messages & Media (Async)

Fitur:
- Meta Cloud API v23.0
- Kirim pesan teks biasa
- Kirim pesan interaktif CTA (Call-To-Action Link / QRIS Payment)
- Download media (Voice Note / Audio)
- Read Receipt (Centang Biru)
"""

import logging
import mimetypes
import os
import re
from typing import Any, Dict, Optional, Tuple

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_WA_API_BASE = "https://graph.facebook.com/v23.0"
_TIMEOUT_SECONDS = 30.0


def _clean_phone_number(phone: str) -> str:
    """
    Pastikan nomor telepon hanya berisi angka murni (E.164 tanpa tanda + atau spasi).
    Meta Cloud API mewajibkan format digit murni (contoh: 6285964325731).
    """
    if not phone:
        raise ValueError("Nomor telepon penerima tidak boleh kosong.")

    cleaned = re.sub(r"\D", "", str(phone))

    # Otomatis ubah awalan 08xx menjadi 628xx jika nomor Indonesia
    if cleaned.startswith("0"):
        cleaned = "62" + cleaned[1:]
    # Otomatis tambah 62 jika nomor langsung diawali angka 8 (misal 85964325731)
    elif cleaned.startswith("8") and 9 <= len(cleaned) <= 13:
        cleaned = "62" + cleaned

    return cleaned


def _get_token() -> str:
    """Ambil WhatsApp Access Token dari OS environment / settings dengan pembersihan karakter tersembunyi."""
    raw_token = (
        os.getenv("WHATSAPP_TOKEN")
        or getattr(settings, "whatsapp_token", None)
        or getattr(settings, "WHATSAPP_TOKEN", None)
        or os.getenv("WHATSAPP_ACCESS_TOKEN")
    )
    if not raw_token:
        raise RuntimeError(
            "WHATSAPP_TOKEN / WHATSAPP_ACCESS_TOKEN tidak ditemukan di .env. "
            "Dapatkan dari Meta Developer Console > WhatsApp > API Setup."
        )
    # Bersihkan spasi, enter, atau tanda petik yang tidak sengaja tersalin
    return str(raw_token).strip().strip("\"' \n\r\t")


def _get_phone_id() -> str:
    """Ambil WhatsApp Phone Number ID dari OS environment / settings."""
    raw_phone_id = (
        os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        or getattr(settings, "whatsapp_phone_number_id", None)
        or getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", None)
    )
    if not raw_phone_id:
        raise RuntimeError("WHATSAPP_PHONE_NUMBER_ID tidak ditemukan di .env.")
    return str(raw_phone_id).strip().strip("\"' \n\r\t")


class WhatsAppClient:
    """
    Class Wrapper Client untuk WhatsApp Cloud API.
    """

    def __init__(self, token: Optional[str] = None, phone_number_id: Optional[str] = None):
        self._custom_token = token
        self._custom_phone_id = phone_number_id

    @property
    def token(self) -> str:
        if self._custom_token:
            return self._custom_token.strip().strip("\"' \n\r\t")
        return _get_token()

    @property
    def phone_number_id(self) -> str:
        if self._custom_phone_id:
            return self._custom_phone_id.strip().strip("\"' \n\r\t")
        return _get_phone_id()

    def get_headers(self) -> Dict[str, str]:
        """Buat HTTP Header otentikasi Meta API."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def send_text_message(self, to: str, text: str) -> Dict[str, Any]:
        """Kirim pesan teks ke nomor WhatsApp pelanggan secara asinkron."""
        clean_to = _clean_phone_number(to)
        url = f"{_WA_API_BASE}/{self.phone_number_id}/messages"

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_to,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": text,
            },
        }

        log_text = f"'{text[:60]}...'" if len(text) > 60 else f"'{text}'"
        masked_token = f"{self.token[:8]}...{self.token[-6:]}" if len(self.token) > 14 else "INVALID"
        logger.info(f"[WhatsAppClient] Sending text to {clean_to} (Token: {masked_token}): {log_text}")

        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            try:
                response = await client.post(url, headers=self.get_headers(), json=payload)
                response.raise_for_status()
                result = response.json()
                msg_id = result.get("messages", [{}])[0].get("id", "unknown")
                logger.info(f"[WhatsAppClient] Text message sent successfully. ID: {msg_id}")
                return result
            except httpx.HTTPStatusError as exc:
                err_detail = exc.response.text
                try:
                    err_json = exc.response.json()
                    err_detail = err_json.get("error", {}).get("message", exc.response.text)
                except Exception:
                    pass

                if exc.response.status_code == 401:
                    logger.error(
                        f"[WhatsAppClient] ❌ Meta 401 Unauthorized: Access Token KADALUARSA/INVALID. "
                        f"Detail: {err_detail}. Silakan regenerate token di Meta Developer Console > WhatsApp > API Setup."
                    )
                else:
                    logger.error(f"[WhatsAppClient] Meta API Error ({exc.response.status_code}): {err_detail}")
                raise
            except Exception as exc:
                logger.error(f"[WhatsAppClient] Unexpected error sending text: {exc}")
                raise

    async def send_text(self, to: str, text: str) -> Dict[str, Any]:
        """Alias untuk send_text_message."""
        return await self.send_text_message(to, text)

    async def send_interactive_cta(
        self, to: str, body_text: str, button_label: str, payment_url: str
    ) -> Dict[str, Any]:
        """Kirim pesan interaktif dengan tombol CTA (Call-to-Action) untuk Link Pembayaran/QRIS."""
        clean_to = _clean_phone_number(to)
        url = f"{_WA_API_BASE}/{self.phone_number_id}/messages"

        clean_label = button_label[:20] if button_label else "Bayar Sekarang"
        clean_body = body_text[:1024] if body_text else "Silakan selesaikan pembayaran."

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_to,
            "type": "interactive",
            "interactive": {
                "type": "cta_url",
                "body": {"text": clean_body},
                "action": {
                    "name": "cta_url",
                    "parameters": {
                        "display_text": clean_label,
                        "url": payment_url,
                    },
                },
            },
        }

        logger.info(f"[WhatsAppClient] Sending CTA to {clean_to}: Label='{clean_label}' -> URL={payment_url}")

        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            try:
                response = await client.post(url, headers=self.get_headers(), json=payload)
                response.raise_for_status()
                result = response.json()
                logger.info(f"[WhatsAppClient] CTA Message sent successfully to {clean_to}")
                return result
            except httpx.HTTPStatusError as exc:
                err_detail = exc.response.text
                try:
                    err_json = exc.response.json()
                    err_detail = err_json.get("error", {}).get("message", exc.response.text)
                except Exception:
                    pass
                logger.error(f"[WhatsAppClient] Meta CTA Error ({exc.response.status_code}): {err_detail}")
                raise
            except Exception as exc:
                logger.error(f"[WhatsAppClient] Unexpected error sending CTA: {exc}")
                raise

    async def download_media(self, media_id: str) -> Tuple[bytes, str]:
        """Download file media (Voice Note / Audio) dari WhatsApp menggunakan media_id."""
        headers = self.get_headers()

        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            meta_resp = await client.get(f"{_WA_API_BASE}/{media_id}", headers=headers)
            meta_resp.raise_for_status()
            media_info = meta_resp.json()

            media_url = media_info.get("url")
            mime_type = media_info.get("mime_type", "audio/ogg")

            if not media_url:
                raise RuntimeError(f"Gagal mendapatkan URL unduhan untuk media_id={media_id}")

            download_resp = await client.get(media_url, headers=headers)
            download_resp.raise_for_status()

        clean_mime = mime_type.split(";")[0].strip().lower()
        ext = mimetypes.guess_extension(clean_mime) or ".ogg"
        if "ogg" in clean_mime:
            ext = ".ogg"
        elif any(k in clean_mime for k in ["mp4", "aac", "m4a"]):
            ext = ".m4a"

        filename = f"voice_note_{media_id[:8]}{ext}"
        logger.info(
            f"[WhatsAppClient] Downloaded media {media_id[:8]}: {len(download_resp.content)} bytes, mime={mime_type}"
        )

        return download_resp.content, filename

    async def mark_message_as_read(self, message_id: str) -> None:
        """Tandai pesan pelanggan sebagai 'sudah dibaca' (centang biru)."""
        if not message_id:
            return

        try:
            url = f"{_WA_API_BASE}/{self.phone_number_id}/messages"
            payload = {
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id,
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(url, headers=self.get_headers(), json=payload)
            logger.debug(f"[WhatsAppClient] Marked message {message_id} as read.")
        except Exception as exc:
            logger.warning(f"[WhatsAppClient] Non-fatal: Failed to mark message {message_id} as read: {exc}")


# Standalone functions
_default_client = WhatsAppClient()

async def send_text_message(to: str, text: str) -> Dict[str, Any]:
    # Selalu gunakan instance baru/dynamic token
    return await WhatsAppClient().send_text_message(to, text)

async def send_interactive_cta(
    to: str, body_text: str, button_label: str, payment_url: str
) -> Dict[str, Any]:
    return await WhatsAppClient().send_interactive_cta(to, body_text, button_label, payment_url)

async def download_media(media_id: str) -> Tuple[bytes, str]:
    return await WhatsAppClient().download_media(media_id)

async def mark_message_as_read(message_id: str) -> None:
    await WhatsAppClient().mark_message_as_read(message_id)

send_text = send_text_message