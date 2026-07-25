"""
LARISKA AI — Sprint 5A
Retrieval — Tahap 5 AI Pipeline (Product Recommendation via pgvector)

Mencari produk yang relevan berdasarkan vector similarity menggunakan pgvector di Supabase.
Digunakan saat pelanggan minta rekomendasi produk atau upsell dari Sales Brain.

Dua mode:
1. Vector similarity (pgvector) — jika product sudah punya embedding
2. Category-based fallback — jika belum ada embedding (awal deployment)

Embedding model: text-embedding-ada-002 (OpenAI) atau text-embedding-3-small
Catatan: Untuk demo, mode 2 (category fallback) sudah cukup kuat karena katalog demo kecil.

Referensi proposal Bab 4, Tahap 5: Retrieval (pgvector)
"""

import logging
from typing import Optional

import google.generativeai as genai

from app.core.config import settings
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)


def get_recommended_products(
    customer_id: str,
    current_product_id: Optional[str] = None,
    current_category: Optional[str] = None,
    query_text: Optional[str] = None,
    limit: int = 3,
) -> list[dict]:
    """
    Ambil produk rekomendasi untuk pelanggan.

    Priority order:
    1. Vector similarity jika query_text ada (dan produk punya embedding)
    2. Same-category products (exclude produk yang sedang dibahas)
    3. Top produk aktif berdasarkan harga (fallback terakhir)

    Args:
        customer_id: ID pelanggan (untuk filter produk yang sudah dibeli).
        current_product_id: Produk yang sedang dibahas (dikecualikan dari rekomendasi).
        current_category: Kategori produk saat ini (untuk same-category suggestion).
        query_text: Teks query untuk vector similarity.
        limit: Jumlah rekomendasi yang dikembalikan.

    Returns:
        List dict produk: id, name, price, floor_price, stock, category
    """
    supabase = get_supabase()

    PRODUCT_COLS = "id, name, description, category, price, floor_price, stock, image_url"

    # === Mode 1: Vector similarity ===
    # Hanya diaktifkan jika ada embedding di database
    # Sementara dinonaktifkan karena embedding model butuh setup terpisah
    # TODO Sprint 5B: aktifkan setelah embedding pipeline setup
    vector_results = []

    # === Mode 2: Same-category products ===
    if current_category:
        try:
            query = (
                supabase.table("products")
                .select(PRODUCT_COLS)
                .eq("category", current_category)
                .eq("is_active", True)
                .is_("deleted_at", "null")
                .order("price", desc=False)
                .limit(limit + 1)  # +1 karena kita mungkin exclude 1 produk
                .execute()
            )
            category_results = query.data or []

            # Exclude produk yang sedang dibahas
            if current_product_id:
                category_results = [
                    p for p in category_results
                    if p["id"] != current_product_id
                ]

            if category_results:
                logger.info(
                    f"[Retrieval] Category-based: {len(category_results)} products "
                    f"in '{current_category}'"
                )
                return category_results[:limit]
        except Exception as exc:
            logger.warning(f"[Retrieval] Category query failed: {exc}")

    # === Mode 3: Fallback — top produk aktif ===
    try:
        query = (
            supabase.table("products")
            .select(PRODUCT_COLS)
            .eq("is_active", True)
            .is_("deleted_at", "null")
            .order("created_at", desc=True)
            .limit(limit + 1)
            .execute()
        )
        all_products = query.data or []

        if current_product_id:
            all_products = [p for p in all_products if p["id"] != current_product_id]

        logger.info(f"[Retrieval] Fallback: {len(all_products)} products returned.")
        return all_products[:limit]

    except Exception as exc:
        logger.error(f"[Retrieval] All retrieval modes failed: {exc}")
        return []


def save_recommendation_log(
    customer_id: str,
    product_id: str,
    conversation_id: str,
    reason: str,
    similarity_score: Optional[float] = None,
) -> None:
    """
    Log rekomendasi ke tabel `recommendations` untuk AI evaluation Sprint 8.
    was_accepted akan diupdate nanti saat customer response diketahui.
    """
    try:
        supabase = get_supabase()
        supabase.table("recommendations").insert({
            "customer_id": customer_id,
            "product_id": product_id,
            "conversation_id": conversation_id,
            "reason": reason,
            "similarity_score": similarity_score,
            "was_accepted": None,  # Belum diketahui
        }).execute()
        logger.info(f"[Retrieval] Recommendation logged for product {product_id[:8]}")
    except Exception as exc:
        logger.warning(f"[Retrieval] Failed to log recommendation: {exc}")
