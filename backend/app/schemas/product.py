"""
Schema products — field HARUS persis sama dengan backend/app/db/schema.sql
(tabel products). Jangan tambah field yang tidak ada di database.

Kolom `embedding` (pgvector) SENGAJA tidak dimasukkan ke schema manapun di
sini — itu diisi oleh AI Pipeline (Sprint 4A/5A retrieval.py), bukan lewat
dashboard API manual.

Kolom `deleted_at` SENGAJA tidak muncul di Response — soft-delete adalah
detail implementasi internal, bukan sesuatu yang perlu dilihat frontend.
Produk yang deleted_at-nya terisi memang sudah difilter di level query
(lihat dashboard_api.py), jadi tidak akan pernah sampai ke Response.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category: str | None = Field(default=None, max_length=100)
    price: float = Field(ge=0)
    floor_price: float = Field(ge=0)
    stock: int = Field(default=0, ge=0)
    sku: str | None = Field(default=None, max_length=64)
    unit_label: str | None = Field(default=None, max_length=80)
    reorder_point: int = Field(default=5, ge=0)
    specifications: dict[str, Any] = Field(default_factory=dict)
    search_aliases: list[str] = Field(default_factory=list)
    image_url: str | None = None
    is_active: bool = True


class ProductCreate(ProductBase):
    """Input untuk POST /dashboard/products.

    id, created_at, updated_at, deleted_at dihasilkan database — tidak boleh
    diisi client.
    """
    pass


class ProductUpdate(BaseModel):
    """Input untuk PUT/PATCH — semua field opsional, cuma field yang dikirim
    yang akan di-update (partial update)."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    category: str | None = Field(default=None, max_length=100)
    price: float | None = Field(default=None, ge=0)
    floor_price: float | None = Field(default=None, ge=0)
    stock: int | None = Field(default=None, ge=0)
    sku: str | None = Field(default=None, max_length=64)
    unit_label: str | None = Field(default=None, max_length=80)
    reorder_point: int | None = Field(default=None, ge=0)
    specifications: dict[str, Any] | None = None
    search_aliases: list[str] | None = None
    image_url: str | None = None
    is_active: bool | None = None


class ProductResponse(ProductBase):
    """Output untuk semua endpoint GET/POST — bentuk data yang dikirim ke
    frontend.

    PENTING: override model_config ke default (extra="ignore"), JANGAN
    warisi extra="forbid" dari ProductBase. Alasannya beda konteks:
    - ProductBase/ProductCreate/ProductUpdate: forbid, karena itu adalah
      INPUT dari client — field asing di sana memang harus ditolak.
    - ProductResponse: data OUTPUT dari Supabase (baca hasil query). Row
      asli dari database wajar punya kolom lain yang tidak diekspos ke
      client (embedding, deleted_at) — itu bukan "field asing yang
      mencurigakan", jadi harus di-ignore, bukan di-forbid.
    """

    model_config = ConfigDict(extra="ignore")

    id: UUID
    created_at: datetime
    updated_at: datetime
