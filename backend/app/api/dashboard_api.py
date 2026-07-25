"""
Dashboard API — dikonsumsi frontend lewat services/*.service.ts.
Prefix "/dashboard" untuk semua endpoint di file ini.

Semua endpoint pakai service_role key (lewat get_supabase()) — frontend
tidak pernah akses Supabase langsung (Opsi A, sudah final).

Lingkup Sprint 3B: CRUD dasar products/customers/orders. Logic pengurangan
stock dan inventory_logs SENGAJA belum disentuh di sini — itu tanggung
jawab sprint pengelolaan pembayaran, dijalankan setelah order benar-benar
dibayar, bukan saat order pertama kali dibuat.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Depends
from supabase import Client

from app.schemas import (
    CustomerCreate,
    CustomerResponse,
    OrderCreate,
    OrderResponse,
    OrderUpdate,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from app.services.supabase_client import get_supabase

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Kolom eksplisit (BUKAN select("*")) — sengaja tidak menarik kolom internal
# seperti products.embedding (vector 768 dimensi, berat & tidak dipakai
# dashboard) dan *.deleted_at (detail implementasi soft-delete, bukan
# sesuatu yang perlu dilihat frontend).
PRODUCT_COLUMNS = "id, name, description, category, price, floor_price, stock, image_url, is_active, created_at, updated_at"
CUSTOMER_COLUMNS = "id, whatsapp_number, name, email, address, created_at, updated_at"
ORDER_COLUMNS = "id, customer_id, conversation_id, product_id, quantity, unit_price, discount_amount, total_amount, status, created_at, updated_at"


# ============================================================
# PRODUCTS
# ============================================================

@router.get("/products", response_model=list[ProductResponse])
def list_products(supabase: Client = Depends(get_supabase)):
    res = (
        supabase.table("products")
        .select(PRODUCT_COLUMNS)
        .is_("deleted_at", "null")
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: UUID, supabase: Client = Depends(get_supabase)):
    res = (
        supabase.table("products")
        .select(PRODUCT_COLUMNS)
        .eq("id", str(product_id))
        .is_("deleted_at", "null")
        .maybe_single()
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return res.data


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, supabase: Client = Depends(get_supabase)):
    if payload.floor_price > payload.price:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="floor_price tidak boleh lebih besar dari price",
        )
    res = supabase.table("products").insert(payload.model_dump(mode="json")).execute()
    return res.data[0]


@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product(product_id: UUID, payload: ProductUpdate, supabase: Client = Depends(get_supabase)):
    data = payload.model_dump(exclude_none=True, mode="json")
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    if "price" in data and "floor_price" in data and data["floor_price"] > data["price"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="floor_price tidak boleh lebih besar dari price",
        )

    res = supabase.table("products").update(data).eq("id", str(product_id)).execute()
    if not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return res.data[0]


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def soft_delete_product(product_id: UUID, supabase: Client = Depends(get_supabase)):
    """Soft delete — set deleted_at, konsisten dengan schema.sql Sprint 2A."""
    res = (
        supabase.table("products")
        .update({"deleted_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", str(product_id))
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return None


# ============================================================
# CUSTOMERS
# ============================================================

@router.get("/customers", response_model=list[CustomerResponse])
def list_customers(supabase: Client = Depends(get_supabase)):
    res = (
        supabase.table("customers")
        .select(CUSTOMER_COLUMNS)
        .is_("deleted_at", "null")
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: UUID, supabase: Client = Depends(get_supabase)):
    res = (
        supabase.table("customers")
        .select(CUSTOMER_COLUMNS)
        .eq("id", str(customer_id))
        .is_("deleted_at", "null")
        .maybe_single()
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return res.data


@router.post("/customers", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreate, supabase: Client = Depends(get_supabase)):
    try:
        res = supabase.table("customers").insert(payload.model_dump(mode="json")).execute()
    except Exception as exc:
        if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Nomor WhatsApp ini sudah terdaftar sebagai pelanggan",
            ) from exc
        raise
    return res.data[0]


# ============================================================
# ORDERS
# ============================================================

@router.get("/orders", response_model=list[OrderResponse])
def list_orders(supabase: Client = Depends(get_supabase)):
    res = supabase.table("orders").select(ORDER_COLUMNS).order("created_at", desc=True).execute()
    return res.data


@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: UUID, supabase: Client = Depends(get_supabase)):
    res = supabase.table("orders").select(ORDER_COLUMNS).eq("id", str(order_id)).maybe_single().execute()
    if not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return res.data


@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreate, supabase: Client = Depends(get_supabase)):
    """
    unit_price diambil dari products.price saat ini (BUKAN dari client) —
    mencegah price tampering, sesuai desain OrderCreate di schemas/order.py.
    """
    product_res = (
        supabase.table("products")
        .select("id, price, floor_price, is_active")
        .eq("id", str(payload.product_id))
        .is_("deleted_at", "null")
        .maybe_single()
        .execute()
    )
    if not product_res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    product = product_res.data

    if not product["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Product is not active"
        )

    customer_res = (
        supabase.table("customers")
        .select("id")
        .eq("id", str(payload.customer_id))
        .is_("deleted_at", "null")
        .maybe_single()
        .execute()
    )
    if not customer_res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    unit_price = float(product["price"])
    subtotal = unit_price * payload.quantity
    if payload.discount_amount > subtotal:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="discount_amount tidak boleh lebih besar dari subtotal (unit_price * quantity)",
        )

    total_amount = subtotal - payload.discount_amount

    # Guardrail floor_price — berlaku di SEMUA jalur pembuatan order (manual
    # dashboard maupun nanti dari AI Negotiation Sprint 5A), bukan cuma satu
    # jalur saja. Konsisten dengan proposal: floor_price tidak pernah dilanggar.
    effective_unit_price = total_amount / payload.quantity
    if effective_unit_price < float(product["floor_price"]):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Total setelah diskon melanggar floor_price produk ini",
        )

    order_data = {
        "customer_id": str(payload.customer_id),
        "conversation_id": str(payload.conversation_id) if payload.conversation_id else None,
        "product_id": str(payload.product_id),
        "quantity": payload.quantity,
        "unit_price": unit_price,
        "discount_amount": payload.discount_amount,
        "total_amount": total_amount,
        "status": "pending",
    }

    res = supabase.table("orders").insert(order_data).execute()
    return res.data[0]


@router.put("/orders/{order_id}", response_model=OrderResponse)
def update_order_status(order_id: UUID, payload: OrderUpdate, supabase: Client = Depends(get_supabase)):
    res = (
        supabase.table("orders")
        .update({"status": payload.status})
        .eq("id", str(order_id))
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return res.data[0]