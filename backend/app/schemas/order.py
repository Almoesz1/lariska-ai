"""
Schema orders — field HARUS persis sama dengan backend/app/db/schema.sql
(tabel orders).

Keputusan desain keamanan (penting): OrderCreate TIDAK menerima unit_price
maupun total_amount dari client. dashboard_api.py yang akan mengambil
unit_price dari products.price saat request diproses, lalu menghitung
total_amount = unit_price * quantity - discount_amount di server. Ini
mencegah client mengirim harga sendiri saat checkout (price tampering) —
konsisten dengan CHECK constraint `total_amount = (unit_price * quantity) -
discount_amount` yang sudah ada di schema.sql, cuma divalidasi lebih awal
di layer API sebelum sampai ke database.

`status` TIDAK bisa diisi lewat OrderCreate (order baru selalu mulai dari
'pending', di-set otomatis oleh server). Perubahan status cuma lewat
OrderUpdate, dibatasi tipe Literal yang nilainya persis sama dengan CHECK
constraint `status` di schema.sql — supaya salah ketik status ditolak oleh
Pydantic sebelum sempat mencapai database.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

OrderStatus = Literal["pending", "paid", "shipped", "completed", "cancelled"]


class OrderCreate(BaseModel):
    """Input untuk POST /dashboard/orders.

    unit_price, total_amount, dan status SENGAJA tidak ada di sini —
    dihitung/di-set oleh server (lihat docstring modul).
    """

    model_config = ConfigDict(extra="forbid")

    customer_id: UUID
    product_id: UUID
    conversation_id: UUID | None = None
    quantity: int = Field(default=1, gt=0)
    discount_amount: float = Field(default=0, ge=0)


class OrderUpdate(BaseModel):
    """Dipakai untuk transisi status order (mis. pending -> paid -> shipped
    -> completed, atau -> cancelled). Field lain order tidak boleh diubah
    setelah dibuat — kalau produk/quantity salah, order harus dibatalkan dan
    dibuat ulang, bukan diedit (menjaga integritas riwayat transaksi)."""

    model_config = ConfigDict(extra="forbid")

    status: OrderStatus


class OrderResponse(BaseModel):
    """Output untuk semua endpoint GET/POST orders."""

    id: UUID
    customer_id: UUID
    conversation_id: UUID | None = None
    product_id: UUID
    quantity: int
    unit_price: float
    discount_amount: float
    total_amount: float
    status: OrderStatus
    created_at: datetime
    updated_at: datetime