"""
LARISKA AI — Unit Tests untuk WhatsApp Cloud API Client
Menguji pengiriman pesan teks, CTA, unduh media, dan mark-as-read dengan Mock HTTP.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

from app.services.whatsapp_client import (
    send_text_message,
    send_interactive_cta,
    send_interactive_list,
    download_media,
    mark_message_as_read,
)


@pytest.fixture
def mock_config():
    with patch("app.services.whatsapp_client.settings") as mock_set:
        mock_set.whatsapp_token = "test_token_123"
        mock_set.whatsapp_phone_number_id = "10987654321"
        yield mock_set


@pytest.mark.asyncio
async def test_send_text_message_success(mock_config):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "messaging_product": "whatsapp",
        "contacts": [{"wa_id": "628123456789"}],
        "messages": [{"id": "wamid.HBgLMTIzNDU2Nzg5MA=="}],
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        res = await send_text_message("628123456789", "Halo dari Lariska AI!")

        assert res["messages"][0]["id"] == "wamid.HBgLMTIzNDU2Nzg5MA=="
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "628123456789" in str(kwargs["json"])
        assert "Halo dari Lariska AI!" in str(kwargs["json"])


@pytest.mark.asyncio
async def test_send_interactive_cta_success(mock_config):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"messages": [{"id": "wamid.CTA123"}]}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        res = await send_interactive_cta(
            to="628123456789",
            body_text="Silakan bayar tagihan Anda",
            button_label="Bayar Sekarang 💳",
            payment_url="https://checkout.midtrans.com/123",
        )

        assert res["messages"][0]["id"] == "wamid.CTA123"
        mock_post.assert_called_once()
        kwargs = mock_post.call_args[1]
        assert kwargs["json"]["interactive"]["action"]["parameters"]["url"] == "https://checkout.midtrans.com/123"


@pytest.mark.asyncio
async def test_send_interactive_list_success(mock_config):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"messages": [{"id": "wamid.LIST123"}]}
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await send_interactive_list(
            to="628123456789",
            body_text="Pilih kategori produk.",
            button_label="Lihat kategori",
            sections=[{"title": "Kategori", "rows": [{"id": "catalog_category:FNB", "title": "Makanan & Minuman"}]}],
        )
        assert result["messages"][0]["id"] == "wamid.LIST123"
        assert mock_post.call_args[1]["json"]["interactive"]["type"] == "list"


@pytest.mark.asyncio
async def test_download_media_success(mock_config):
    meta_response = MagicMock()
    meta_response.raise_for_status.return_value = None
    meta_response.json.return_value = {
        "url": "https://lookaside.fbsbx.com/whatsapp_learning/media/123",
        "mime_type": "audio/ogg; codecs=opus",
    }

    download_response = MagicMock()
    download_response.raise_for_status.return_value = None
    download_response.content = b"fake_audio_binary_data"

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [meta_response, download_response]

        content, filename = await download_media("media_id_999")

        assert content == b"fake_audio_binary_data"
        assert filename.startswith("voice_note_media_id")
        assert filename.endswith(".ogg")
        assert mock_get.call_count == 2


@pytest.mark.asyncio
async def test_mark_message_as_read_non_fatal(mock_config):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = Exception("Network Glitch")

        # Harus berjalan mulus tanpa melempar Exception
        await mark_message_as_read("wamid.12345")
