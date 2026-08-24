"""
Test suite untuk endpoint /dashboard/customers (dashboard_api.py).
"""


class TestListCustomers:
    def test_returns_array_of_customers(self, client_factory, sample_customer):
        client = client_factory(customers=[sample_customer])
        response = client.get("/dashboard/customers")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert data[0]["id"] == sample_customer["id"]
        assert "deleted_at" not in data[0]

    def test_returns_empty_array_when_no_customers(self, client_factory):
        client = client_factory(customers=[])
        response = client.get("/dashboard/customers")

        assert response.status_code == 200
        assert response.json() == []


class TestGetCustomer:
    def test_found_returns_single_customer(self, client_factory, sample_customer):
        client = client_factory(customers=sample_customer)
        response = client.get(f"/dashboard/customers/{sample_customer['id']}")

        assert response.status_code == 200
        assert response.json()["whatsapp_number"] == sample_customer["whatsapp_number"]

    def test_not_found_returns_404(self, client_factory):
        client = client_factory(customers=None)
        response = client.get("/dashboard/customers/22222222-2222-2222-2222-222222222222")

        assert response.status_code == 404
        assert response.json()["detail"] == "Customer not found"


class TestCreateCustomer:
    def test_success_returns_201(self, client_factory, sample_customer):
        client = client_factory(customers=[sample_customer])
        payload = {
            "whatsapp_number": "6281234567890",
            "name": "Budi Santoso",
            "email": "budi@example.com",
            "address": "Surabaya",
        }
        response = client.post("/dashboard/customers", json=payload)

        assert response.status_code == 201
        assert response.json()["whatsapp_number"] == "6281234567890"

    def test_duplicate_whatsapp_returns_409(self, client_factory):
        """Endpoint menangkap Exception dari Supabase yang pesannya mengandung
        'duplicate'/'unique' (UNIQUE constraint whatsapp_number di schema.sql),
        lalu mengubahnya jadi 409 Conflict — bukan 500 mentah."""
        duplicate_error = Exception(
            'duplicate key value violates unique constraint "customers_whatsapp_number_key"'
        )
        client = client_factory(customers=duplicate_error)
        payload = {"whatsapp_number": "6281234567890", "name": "Budi Duplikat"}
        response = client.post("/dashboard/customers", json=payload)

        assert response.status_code == 409
        assert "sudah terdaftar" in response.json()["detail"]

    def test_rejects_unknown_field(self, client_factory):
        """CustomerCreate extra='forbid' — field asing harus ditolak,
        termasuk field yang sengaja tidak boleh diisi client (mis. deleted_at)."""
        client = client_factory()
        payload = {"whatsapp_number": "6281234567890", "deleted_at": None}
        response = client.post("/dashboard/customers", json=payload)

        assert response.status_code == 422

    def test_missing_whatsapp_number_rejected(self, client_factory):
        client = client_factory()
        payload = {"name": "Tanpa Nomor WA"}
        response = client.post("/dashboard/customers", json=payload)

        assert response.status_code == 422