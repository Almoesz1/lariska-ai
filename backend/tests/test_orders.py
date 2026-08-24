"""
Test suite untuk endpoint /dashboard/orders (dashboard_api.py) — mencakup
guardrail floor_price dan proteksi price-tampering yang jadi inti proposal
LARISKA AI Bagian 6 (floor_price tidak pernah dilanggar siapapun, termasuk
lewat jalur manual dashboard).
"""


class TestListOrders:
    def test_returns_array_of_orders(self, client_factory, sample_order):
        client = client_factory(orders=[sample_order])
        response = client.get("/dashboard/orders")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert data[0]["id"] == sample_order["id"]


class TestGetOrder:
    def test_found_returns_single_order(self, client_factory, sample_order):
        client = client_factory(orders=sample_order)
        response = client.get(f"/dashboard/orders/{sample_order['id']}")

        assert response.status_code == 200
        assert response.json()["status"] == "pending"

    def test_not_found_returns_404(self, client_factory):
        client = client_factory(orders=None)
        response = client.get("/dashboard/orders/33333333-3333-3333-3333-333333333333")

        assert response.status_code == 404
        assert response.json()["detail"] == "Order not found"


class TestCreateOrder:
    def test_success_computes_price_server_side(self, client_factory, sample_product, sample_customer):
        """unit_price & total_amount HARUS dihitung server dari products.price,
        bukan dari client — inti dari proteksi anti price-tampering."""
        created_order = {
            "id": "33333333-3333-3333-3333-333333333333",
            "customer_id": sample_customer["id"],
            "conversation_id": None,
            "product_id": sample_product["id"],
            "quantity": 2,
            "unit_price": 25000,
            "discount_amount": 5000,
            "total_amount": 45000,
            "status": "pending",
            "created_at": "2026-07-01T08:00:00+00:00",
            "updated_at": "2026-07-01T08:00:00+00:00",
        }
        client = client_factory(
            products=sample_product,   # dipanggil via maybe_single -> dict
            customers=sample_customer, # dipanggil via maybe_single -> dict
            orders=[created_order],    # dipanggil via insert -> list
        )
        payload = {
            "customer_id": sample_customer["id"],
            "product_id": sample_product["id"],
            "quantity": 2,
            "discount_amount": 5000,
        }
        response = client.post("/dashboard/orders", json=payload)

        assert response.status_code == 201
        body = response.json()
        assert body["unit_price"] == 25000
        assert body["total_amount"] == 45000
        assert body["status"] == "pending"

    def test_rejects_client_supplied_unit_price(self, client_factory, sample_product, sample_customer):
        """OrderCreate tidak punya field unit_price sama sekali — client yang
        coba kirim harga sendiri harus ditolak di layer validasi (422),
        sebelum sempat menyentuh Supabase sama sekali."""
        client = client_factory(products=sample_product, customers=sample_customer)
        payload = {
            "customer_id": sample_customer["id"],
            "product_id": sample_product["id"],
            "quantity": 1,
            "unit_price": 1,
        }
        response = client.post("/dashboard/orders", json=payload)

        assert response.status_code == 422

    def test_rejects_client_supplied_status(self, client_factory, sample_product, sample_customer):
        """status juga tidak boleh diisi client saat create — order baru
        selalu mulai dari 'pending', ditentukan server."""
        client = client_factory(products=sample_product, customers=sample_customer)
        payload = {
            "customer_id": sample_customer["id"],
            "product_id": sample_product["id"],
            "quantity": 1,
            "status": "paid",
        }
        response = client.post("/dashboard/orders", json=payload)

        assert response.status_code == 422

    def test_product_not_found_returns_404(self, client_factory, sample_customer):
        client = client_factory(products=None, customers=sample_customer)
        payload = {
            "customer_id": sample_customer["id"],
            "product_id": "11111111-1111-1111-1111-111111111111",
            "quantity": 1,
        }
        response = client.post("/dashboard/orders", json=payload)

        assert response.status_code == 404
        assert response.json()["detail"] == "Product not found"

    def test_inactive_product_rejected(self, client_factory, sample_product, sample_customer):
        inactive_product = {**sample_product, "is_active": False}
        client = client_factory(products=inactive_product, customers=sample_customer)
        payload = {
            "customer_id": sample_customer["id"],
            "product_id": sample_product["id"],
            "quantity": 1,
        }
        response = client.post("/dashboard/orders", json=payload)

        assert response.status_code == 422
        assert response.json()["detail"] == "Product is not active"

    def test_customer_not_found_returns_404(self, client_factory, sample_product):
        client = client_factory(products=sample_product, customers=None)
        payload = {
            "customer_id": "22222222-2222-2222-2222-222222222222",
            "product_id": sample_product["id"],
            "quantity": 1,
        }
        response = client.post("/dashboard/orders", json=payload)

        assert response.status_code == 404
        assert response.json()["detail"] == "Customer not found"

    def test_discount_exceeds_subtotal_rejected(self, client_factory, sample_product, sample_customer):
        """discount_amount jauh lebih besar dari subtotal (unit_price * qty)
        harus ditolak dengan pesan spesifik soal subtotal — beda dari
        pelanggaran floor_price (lihat test di bawah)."""
        client = client_factory(products=sample_product, customers=sample_customer)
        payload = {
            "customer_id": sample_customer["id"],
            "product_id": sample_product["id"],
            "quantity": 1,
            "discount_amount": 999999,
        }
        response = client.post("/dashboard/orders", json=payload)

        assert response.status_code == 422
        assert "subtotal" in response.json()["detail"]

    def test_floor_price_guardrail_rejected(self, client_factory, sample_product, sample_customer):
        """Skenario persis dari kasus manual testing sebelumnya:
        price=25000, floor_price=20000, qty=1, discount=10000
        -> effective_unit_price = (25000*1 - 10000) / 1 = 15000
        -> 15000 < floor_price 20000 -> HARUS ditolak 422."""
        client = client_factory(products=sample_product, customers=sample_customer)
        payload = {
            "customer_id": sample_customer["id"],
            "product_id": sample_product["id"],
            "quantity": 1,
            "discount_amount": 10000,
        }
        response = client.post("/dashboard/orders", json=payload)

        assert response.status_code == 422
        assert "floor_price" in response.json()["detail"]

    def test_discount_within_floor_price_accepted(self, client_factory, sample_product, sample_customer):
        """Kebalikan dari test di atas — diskon yang MASIH di atas floor_price
        harus tetap diterima (pastikan guardrail tidak overshoot / terlalu
        ketat menolak transaksi yang sah)."""
        created_order = {
            "id": "33333333-3333-3333-3333-333333333333",
            "customer_id": sample_customer["id"],
            "conversation_id": None,
            "product_id": sample_product["id"],
            "quantity": 1,
            "unit_price": 25000,
            "discount_amount": 3000,
            "total_amount": 22000,
            "status": "pending",
            "created_at": "2026-07-01T08:00:00+00:00",
            "updated_at": "2026-07-01T08:00:00+00:00",
        }
        client = client_factory(
            products=sample_product, customers=sample_customer, orders=[created_order]
        )
        payload = {
            "customer_id": sample_customer["id"],
            "product_id": sample_product["id"],
            "quantity": 1,
            "discount_amount": 3000,
        }
        response = client.post("/dashboard/orders", json=payload)

        assert response.status_code == 201
        assert response.json()["total_amount"] == 22000


class TestUpdateOrderStatus:
    def test_success_updates_status(self, client_factory, sample_order):
        paid_order = {**sample_order, "status": "paid"}
        client = client_factory(orders=paid_order)
        response = client.put(f"/dashboard/orders/{sample_order['id']}", json={"status": "shipped"})

        assert response.status_code == 200
        assert response.json()["status"] == "shipped"

    def test_not_found_returns_404(self, client_factory):
        client = client_factory(orders=None)
        response = client.put(
            "/dashboard/orders/33333333-3333-3333-3333-333333333333", json={"status": "paid"}
        )

        assert response.status_code == 404

    def test_rejects_skipping_operational_stage(self, client_factory, sample_order):
        client = client_factory(orders=sample_order)
        response = client.put(f"/dashboard/orders/{sample_order['id']}", json={"status": "shipped"})

        assert response.status_code == 409
        assert "Transisi pending" in response.json()["detail"]

    def test_invalid_status_value_rejected(self, client_factory):
        """status dibatasi Literal sesuai CHECK constraint di schema.sql —
        value di luar itu harus ditolak sebelum sempat memanggil Supabase."""
        client = client_factory()
        response = client.put(
            "/dashboard/orders/33333333-3333-3333-3333-333333333333",
            json={"status": "lunas_banget"},
        )

        assert response.status_code == 422
