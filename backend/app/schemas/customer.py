"""
Schema customers — field HARUS persis sama dengan backend/app/db/schema.sql
(tabel customers).

`whatsapp_number` SENGAJA tidak bisa diubah lewat CustomerUpdate — itu adalah
identitas utama pelanggan (UNIQUE constraint di database). Kalau nomor WA
pelanggan benar-benar berganti, itu secara bisnis adalah pelanggan baru,
bukan update field pada pelanggan lama.

Kolom `deleted_at` sengaja tidak muncul di Response — sama alasannya dengan
product.py: soft-delete adalah detail implementasi internal, dan record yang
deleted_at-nya terisi sudah difilter di level query (lihat dashboard_api.py).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CustomerBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    whatsapp_number: str = Field(min_length=8, max_length=20)
    name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    address: str | None = None


class CustomerCreate(CustomerBase):
    """Input untuk POST /dashboard/customers.

    id, created_at, updated_at, deleted_at dihasilkan database — tidak boleh
    diisi client.
    """
    pass


class CustomerUpdate(BaseModel):
    """Partial update. whatsapp_number SENGAJA tidak ada di sini — lihat
    penjelasan di docstring modul. Kalau client coba kirim whatsapp_number
    di sini, request akan DITOLAK (extra="forbid"), bukan diam-diam
    diabaikan."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    address: str | None = None


class CustomerResponse(CustomerBase):
    """Output untuk semua endpoint GET/POST customers.

    Sama seperti ProductResponse — override ke extra="ignore" (default),
    JANGAN warisi extra="forbid" dari CustomerBase. Row asli dari database
    punya kolom deleted_at yang tidak diekspos ke client; itu bukan field
    asing yang harus ditolak, cuma tidak perlu ditampilkan."""

    model_config = ConfigDict(extra="ignore")

    id: UUID
    created_at: datetime
    updated_at: datetime