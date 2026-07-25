"""
Test suite untuk endpoint /dashboard/products (dashboard_api.py).
Semua request memakai FakeSupabaseClient lewat dependency_overrides —
TIDAK ADA koneksi ke database asli.
"""


class TestListProducts:
    def test_returns_array_of_products(self, client_factory, sample_product):
        client = client_factory(products=[sample_product])
        response = client.get("/dashboard/products")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == sample_product["id"]
        assert data[0]["name"] == sample_product["name"]
        # embedding & deleted_at TIDAK boleh muncul — bukan bagian PRODUCT_COLUMNS
        assert "embedding" not in data[0]
        assert "deleted_at" not in data[0]

    def test_returns_empty_array_when_no_products(self, client_factory):
        client = client_factory(products=[])
        response = client.get("/dashboard/products")

        assert response.status_code == 200
        assert response.json() == []


class TestGetProduct:
    def test_found_returns_single_product(self, client_factory, sample_product):
        client = client_factory(products=sample_product)
        response = client.get(f"/dashboard/products/{sample_product['id']}")

        assert response.status_code == 200
        assert response.json()["id"] == sample_product["id"]

    def test_not_found_returns_404(self, client_factory):
        client = client_factory(products=None)
        response = client.get("/dashboard/products/11111111-1111-1111-1111-111111111111")

        assert response.status_code == 404
        assert response.json()["detail"] == "Product not found"


class TestCreateProduct:
    def test_success_returns_201(self, client_factory, sample_product):
        client = client_factory(products=[sample_product])
        payload = {
            "name": "Kopi Robusta Gayo 250g",
            "price": 25000,
            "floor_price": 20000,
            "stock": 30,
        }
        response = client.post("/dashboard/products", json=payload)

        assert response.status_code == 201
        assert response.json()["id"] == sample_product["id"]

    def test_floor_price_greater_than_price_rejected(self, client_factory):
        """Guardrail bisnis: floor_price tidak boleh > price. Divalidasi di
        route SEBELUM memanggil Supabase — tidak butuh data mock tabel."""
        client = client_factory()
        payload = {"name": "Invalid", "price": 10000, "floor_price": 20000}
        response = client.post("/dashboard/products", json=payload)

        assert response.status_code == 422
        assert "floor_price" in response.json()["detail"]

    def test_rejects_unknown_field(self, client_factory):
        """ProductCreate pakai extra='forbid' — field asing (mis. embedding
        atau typo nama field) harus ditolak di layer validasi."""
        client = client_factory()
        payload = {"name": "Test", "price": 10000, "floor_price": 8000, "embedding": [0.1, 0.2]}
        response = client.post("/dashboard/products", json=payload)

        assert response.status_code == 422

    def test_rejects_negative_price(self, client_factory):
        client = client_factory()
        payload = {"name": "Invalid", "price": -1000, "floor_price": 0}
        response = client.post("/dashboard/products", json=payload)

        assert response.status_code == 422


class TestUpdateProduct:
    def test_success_updates_fields(self, client_factory, sample_product):
        updated = {**sample_product, "price": 28000, "stock": 40}
        client = client_factory(products=[updated])
        response = client.put(
            f"/dashboard/products/{sample_product['id']}", json={"price": 28000, "stock": 40}
        )

        assert response.status_code == 200
        assert response.json()["price"] == 28000
        assert response.json()["stock"] == 40

    def test_not_found_returns_404(self, client_factory):
        client = client_factory(products=[])
        response = client.put(
            "/dashboard/products/11111111-1111-1111-1111-111111111111", json={"price": 1000}
        )

        assert response.status_code == 404

    def test_empty_body_returns_400(self, client_factory):
        client = client_factory()
        response = client.put(
            "/dashboard/products/11111111-1111-1111-1111-111111111111", json={}
        )

        assert response.status_code == 400

    def test_floor_price_violation_rejected(self, client_factory):
        client = client_factory()
        response = client.put(
            "/dashboard/products/11111111-1111-1111-1111-111111111111",
            json={"price": 10000, "floor_price": 20000},
        )

        assert response.status_code == 422
        assert "floor_price" in response.json()["detail"]


class TestDeleteProduct:
    def test_success_returns_204(self, client_factory, sample_product):
        client = client_factory(products=[sample_product])
        response = client.delete(f"/dashboard/products/{sample_product['id']}")

        assert response.status_code == 204
        assert response.content == b""

    def test_not_found_returns_404(self, client_factory):
        client = client_factory(products=[])
        response = client.delete("/dashboard/products/11111111-1111-1111-1111-111111111111")

        assert response.status_code == 404