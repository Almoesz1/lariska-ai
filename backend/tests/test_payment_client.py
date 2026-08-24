from unittest.mock import MagicMock, patch

from app.services.payment_client import create_qris_payment


def test_midtrans_item_total_equals_gross_amount_for_non_divisible_bundle() -> None:
    snap = MagicMock()
    snap.create_transaction.return_value = {
        "token": "sandbox-token",
        "redirect_url": "https://app.sandbox.midtrans.com/snap/v2/vtweb/token",
    }

    with patch("app.services.payment_client._get_snap", return_value=snap):
        create_qris_payment(
            order_id="e3cae1f6-1234-4567-8901-abcdef123456",
            amount=70_000,
            customer_name="Mustofa",
            customer_phone="6285964325731",
            product_name="Kopi Arabica",
            quantity=3,
        )

    payload = snap.create_transaction.call_args.args[0]
    item_total = sum(item["price"] * item["quantity"] for item in payload["item_details"])
    assert payload["transaction_details"]["gross_amount"] == 70_000
    assert item_total == 70_000
    assert payload["item_details"][0]["name"] == "Kopi Arabica (3 unit)"
