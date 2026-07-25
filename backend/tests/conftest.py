"""
Fixture bersama untuk seluruh test suite backend LARISKA AI.

Pendekatan mocking: FastAPI dependency_overrides mengganti get_supabase()
dengan FakeSupabaseClient — TIDAK ADA koneksi ke Supabase asli sama sekali.

FakeSupabaseClient.table(name) mengembalikan ChainMock yang meniru fluent
API supabase-py: .select().eq().is_().order().maybe_single()/.insert()/
.update() semuanya mengembalikan dirinya sendiri (chainable), dan
.execute() mengembalikan hasil yang sudah dikonfigurasi per test lewat
fixture client_factory(**table_data).
"""

import os
from unittest.mock import MagicMock

# Set env vars SEBELUM app.core.config diimpor di manapun — Settings
# di-load sekali di level module (bukan lazy), jadi kalau env vars belum
# ada saat import pertama, seluruh test akan gagal collect (bukan gagal
# run). Test TIDAK butuh .env asli maupun koneksi Supabase sungguhan.
os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("ENVIRONMENT", "test")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.supabase_client import get_supabase


class ChainMock:
    """Mock query builder Supabase yang chainable.

    Semua method filter (select/eq/is_/order/maybe_single/insert/update)
    mengembalikan dirinya sendiri. execute() mengembalikan MagicMock dengan
    `.data` sudah diisi payload yang dikonfigurasi test, ATAU me-raise
    payload kalau payload-nya adalah instance Exception (dipakai untuk
    simulasi error Supabase, misal duplicate key constraint).
    """

    def __init__(self, payload):
        self._payload = payload

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def is_(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def maybe_single(self):
        return self

    def insert(self, *args, **kwargs):
        return self

    def update(self, *args, **kwargs):
        return self

    def execute(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        result = MagicMock()
        result.data = self._payload
        return result


class FakeSupabaseClient:
    """Fake Supabase client. table(name) mengembalikan ChainMock dengan data
    yang sudah ditentukan per tabel untuk skenario test tertentu.

    Setiap endpoint di dashboard_api.py hanya query 1 tabel dengan 1 bentuk
    hasil per request (list untuk list/insert/update, dict untuk
    maybe_single, None untuk not-found) — jadi 1 payload per tabel per test
    sudah cukup, tidak perlu antrian/queue per tabel.
    """

    def __init__(self, **table_data):
        self._table_data = table_data

    def table(self, name):
        return ChainMock(self._table_data.get(name))


@pytest.fixture
def client_factory():
    """Panggil dengan keyword per tabel yang dibutuhkan skenario test, misal:

        client_factory(products=[sample_product])           # list endpoint
        client_factory(products=sample_product)              # maybe_single
        client_factory(products=None)                        # not found
        client_factory(customers=Exception("duplicate key")) # simulasi error

    Mengembalikan TestClient yang siap pakai, dependency get_supabase sudah
    di-override. dependency_overrides dibersihkan otomatis setelah test
    selesai supaya tidak bocor ke test lain.
    """

    def _factory(**table_data):
        fake_client = FakeSupabaseClient(**table_data)
        app.dependency_overrides[get_supabase] = lambda: fake_client
        return TestClient(app)

    yield _factory
    app.dependency_overrides.clear()


@pytest.fixture
def sample_product():
    """1 baris produk lengkap sesuai PRODUCT_COLUMNS di dashboard_api.py
    (tidak menyertakan embedding/deleted_at — memang tidak pernah di-select)."""
    return {
        "id": "11111111-1111-1111-1111-111111111111",
        "name": "Kopi Robusta Gayo 250g",
        "description": "Kopi robusta premium asal Gayo",
        "category": "F&B",
        "price": 25000,
        "floor_price": 20000,
        "stock": 30,
        "image_url": None,
        "is_active": True,
        "created_at": "2026-07-01T08:00:00+00:00",
        "updated_at": "2026-07-01T08:00:00+00:00",
    }


@pytest.fixture
def sample_customer():
    """1 baris customer lengkap sesuai CUSTOMER_COLUMNS."""
    return {
        "id": "22222222-2222-2222-2222-222222222222",
        "whatsapp_number": "6281234567890",
        "name": "Budi Santoso",
        "email": "budi@example.com",
        "address": "Surabaya",
        "created_at": "2026-07-01T08:00:00+00:00",
        "updated_at": "2026-07-01T08:00:00+00:00",
    }


@pytest.fixture
def sample_order():
    """1 baris order lengkap sesuai ORDER_COLUMNS."""
    return {
        "id": "33333333-3333-3333-3333-333333333333",
        "customer_id": "22222222-2222-2222-2222-222222222222",
        "conversation_id": None,
        "product_id": "11111111-1111-1111-1111-111111111111",
        "quantity": 2,
        "unit_price": 25000,
        "discount_amount": 5000,
        "total_amount": 45000,
        "status": "pending",
        "created_at": "2026-07-01T08:00:00+00:00",
        "updated_at": "2026-07-01T08:00:00+00:00",
    }