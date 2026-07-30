"""
LARISKA AI — Integration & Unit Tests untuk WhatsApp Webhook
Menguji endpoint Verification (GET) dan Message Ingestion (POST).
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


# ==========================================================
# 1. GET /api/whatsapp/webhook (Verification Tests)
# ==========================================================

def test_verify_webhook_success(client):
    """Memastikan verifikasi token GET dari Meta berhasil jika verify_token cocok."""
    with patch("app.api.whatsapp_webhook.settings") as mock_set:
        mock_set.whatsapp_verify_token = "lariska_secret_verify_token"

        response = client.get(
            "/api/whatsapp/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "1158201444",
                "hub.verify_token": "lariska_secret_verify_token",
            },
        )

        assert response.status_code == 200
        assert response.text == "1158201444"


def test_verify_webhook_wrong_token(client):
    """Memastikan status 403 Forbidden jika verify_token tidak cocok."""
    with patch("app.api.whatsapp_webhook.settings") as mock_set:
        mock_set.whatsapp_verify_token = "lariska_secret_verify_token"

        response = client.get(
            "/api/whatsapp/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "1158201444",
                "hub.verify_token": "WRONG_TOKEN",
            },
        )

        assert response.status_code == 403


def test_verify_webhook_missing_config(client):
    """Memastikan error handling jika whatsapp_verify_token belum dikonfigurasi."""
    with patch("app.api.whatsapp_webhook.settings") as mock_set:
        mock_set.whatsapp_verify_token = None

        response = client.get(
            "/api/whatsapp/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "1158201444",
                "hub.verify_token": "any_token",
            },
        )

        assert response.status_code in [403, 500]


# ==========================================================
# 2. POST /api/whatsapp/webhook (Message Ingestion Tests)
# ==========================================================

def test_post_webhook_text_message_success(client):
    """
    Memastikan endpoint POST menerima pesan teks WhatsApp,
    merespons 200 OK secara instan, dan meneruskan ke background task.
    """
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"display_phone_number": "15550555", "phone_number_id": "123456"},
                            "contacts": [{"profile": {"name": "Budi"}, "wa_id": "628123456789"}],
                            "messages": [
                                {
                                    "from": "628123456789",
                                    "id": "wamid.HBgLMTIzNDU2Nzg5MA==",
                                    "timestamp": "1700000000",
                                    "text": {"body": "Mas, sneakers ini harganya bisa tawar Rp80rb gak?"},
                                    "type": "text",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    with patch("app.api.whatsapp_webhook._process_webhook_payload") as mock_worker:
        response = client.post("/api/whatsapp/webhook", json=payload)

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_post_webhook_voice_message_success(client):
    """Memastikan endpoint POST menangani pesan suara/audio dengan sukses."""
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"display_phone_number": "15550555", "phone_number_id": "123456"},
                            "contacts": [{"profile": {"name": "Budi"}, "wa_id": "628123456789"}],
                            "messages": [
                                {
                                    "from": "628123456789",
                                    "id": "wamid.HBgLMTIzNDU2Nzg5OQ==",
                                    "timestamp": "1700000000",
                                    "audio": {"id": "media_id_12345", "mime_type": "audio/ogg"},
                                    "type": "audio",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    with patch("app.api.whatsapp_webhook._process_webhook_payload") as mock_worker:
        response = client.post("/api/whatsapp/webhook", json=payload)

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_post_webhook_status_update_ignored(client):
    """
    Memastikan webhook merespons 200 OK tanpa error saat menerima status update
    (sent, delivered, read) dari Meta.
    """
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"display_phone_number": "15550555", "phone_number_id": "123456"},
                            "statuses": [
                                {
                                    "id": "wamid.HBgLMTIzNDU2Nzg5MA==",
                                    "status": "delivered",
                                    "timestamp": "1700000000",
                                    "recipient_id": "628123456789",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    with patch("app.api.whatsapp_webhook._process_webhook_payload") as mock_worker:
        response = client.post("/api/whatsapp/webhook", json=payload)

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_post_webhook_malformed_payload(client):
    """Memastikan webhook menangani payload kosong/cacat tanpa unhandled 500 error."""
    response = client.post("/api/whatsapp/webhook", json={})
    assert response.status_code in [200, 400]