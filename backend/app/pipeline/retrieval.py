"""
LARISKA AI — Sprint 5A & QA Audit
Retrieval — Tahap 5 AI Pipeline (Product Recommendation & Retrieval)

Mencari produk yang relevan berdasarkan vector similarity (pgvector) atau fallback kategori.
Digunakan saat pelanggan meminta rekomendasi produk atau upsell dari Sales Brain.

Priority Order:
1. Vector Similarity (text-embedding-004 via SDK google-genai) jika query_text tersedia.
2. Same-Category Fallback (menampilkan produk sejenis, exclude produk aktif).
3. General Active Products Fallback (top produk aktif terbaru).

Referensi proposal Bab 4, Tahap 5: Retrieval (pgvector)
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

from app.pipeline.gemini_client import embed_content
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# Konstanta Model Embedding Google GenAI
EMBEDDING_MODEL = "text-embedding-004"

# Kata percakapan umum tidak boleh menjadi dasar pencarian katalog. Dengan
# demikian pesan seperti "saya ingin beli kopi" dicocokkan ke "kopi", bukan
# jatuh ke fallback acak hanya karena model embedding sedang tidak tersedia.
_SEARCH_STOPWORDS = {
    "aku", "anda", "apa", "atau", "beli", "bisa", "cari", "dengan", "dong",
    "ingin", "ini", "itu", "kak", "kalau", "lihat", "mau", "pak", "produk",
    "saja", "saya", "tolong", "untuk", "ya", "yang", "nih", "deh",
}


def _normalise_search_text(value: Any) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()
    # Normalisasi kecil untuk gaya chat/STT yang lazim tanpa membiarkan model
    # bahasa menebak nama produk.
    normalized = re.sub(r"\barabika(?:nya)?\b", "arabica", normalized)
    normalized = re.sub(r"\b(\w{4,})nya\b", r"\1", normalized)
    return normalized


def _catalog_text(product: Dict[str, Any]) -> str:
    """Susun teks katalog yang aman untuk pencarian deterministik lokal."""
    aliases = product.get("search_aliases") or []
    if not isinstance(aliases, list):
        aliases = [aliases]
    return " ".join(
        _normalise_search_text(part)
        for part in (
            product.get("name"), product.get("category"), product.get("description"),
            product.get("sku"), " ".join(map(str, aliases)),
        )
    )


def _lexical_catalog_matches(
    products: List[Dict[str, Any]], query_text: str, limit: int
) -> List[Dict[str, Any]]:
    """Cari produk berdasarkan kata katalog sebelum memakai embedding.

    Ini menjaga respons katalog tetap relevan dan hemat kuota saat pelanggan
    menyebut produk langsung, misalnya "kopi", "tumbler", atau "charger".
    """
    normalized_query = _normalise_search_text(query_text)
    tokens = [
        token for token in normalized_query.split()
        if len(token) >= 3 and token not in _SEARCH_STOPWORDS
    ]
    if not tokens:
        return []

    scored: List[tuple[int, Dict[str, Any]]] = []
    for product in products:
        haystack = _catalog_text(product)
        name = _normalise_search_text(product.get("name"))
        matched = [token for token in tokens if token in haystack]
        if not matched:
            continue
        score = len(matched) * 10
        if normalized_query in name or any(name.startswith(token) for token in matched):
            score += 5
        if product.get("stock", 0) > 0:
            score += 1
        scored.append((score, product))

    scored.sort(key=lambda item: (-item[0], str(item[1].get("name", "")).lower()))
    return [product for _, product in scored[:limit]]

def generate_text_embedding(text: str) -> Optional[List[float]]:
    """
    Menghasilkan vector embedding dari teks menggunakan SDK google-genai terbaru.
    """
    try:
        # get_recommended_products dipanggil melalui worker thread, sehingga
        # coroutine embedding harus dieksekusi sampai selesai di thread ini.
        # Sebelumnya coroutine diperlakukan seperti respons SDK dan memunculkan
        # error "coroutine has no attribute embedding".
        values = asyncio.run(embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
        ))
        if values:
            return list(values)
        return None
    except Exception as exc:
        logger.error(f"[Retrieval] Error saat membuat text embedding: {exc}")
        return None


def get_recommended_products(
    customer_id: str,
    current_product_id: Optional[str] = None,
    current_category: Optional[str] = None,
    query_text: Optional[str] = None,
    limit: int = 3,
) -> List[Dict[str, Any]]:
    """
    Ambil produk rekomendasi untuk pelanggan dengan strategi bertingkat (Vector -> Category -> Top Active).

    Args:
        customer_id: ID pelanggan.
        current_product_id: Produk yang sedang dibahas (dikecualikan dari hasil).
        current_category: Kategori produk saat ini (untuk same-category suggestion).
        query_text: Teks query untuk pencarian semantik (pgvector).
        limit: Jumlah rekomendasi maksimal.

    Returns:
        List dictionary berisi data produk.
    """
    supabase = get_supabase()
    PRODUCT_COLS = (
        "id, name, description, category, price, floor_price, stock, image_url, "
        "sku, unit_label, specifications, search_aliases"
    )

    # === Mode 0: Exact/lexical catalog grounding ===
    # Pencarian ini sengaja dilakukan sebelum vector similarity supaya daftar
    # untuk kata produk eksplisit tidak berubah menjadi produk lintas kategori
    # ketika embedding/RPC tidak aktif atau mengembalikan hasil lemah.
    if query_text:
        try:
            catalog_response = (
                supabase.table("products")
                .select(PRODUCT_COLS)
                .eq("is_active", True)
                .is_("deleted_at", "null")
                .execute()
            )
            lexical_results = _lexical_catalog_matches(
                catalog_response.data or [], query_text, limit + 1
            )
            if current_product_id:
                lexical_results = [
                    product for product in lexical_results
                    if product.get("id") != current_product_id
                ]
            if lexical_results:
                logger.info(
                    "[Retrieval] Lexical catalog match: %s products for %r",
                    len(lexical_results), query_text[:60],
                )
                return lexical_results[:limit]
        except Exception as exc:
            logger.warning("[Retrieval] Lexical catalog query failed: %s", exc)

    # === Mode 1: Vector Similarity (pgvector via Supabase RPC) ===
    if query_text:
        embedding = generate_text_embedding(query_text)
        if embedding:
            try:
                rpc_response = supabase.rpc(
                    "match_products",
                    {
                        "query_embedding": embedding,
                        "match_threshold": 0.6,
                        "match_count": limit + 1,
                    },
                ).execute()

                vector_results = rpc_response.data or []
                if current_product_id:
                    vector_results = [
                        p for p in vector_results if p.get("id") != current_product_id
                    ]

                if vector_results:
                    logger.info(
                        f"[Retrieval] Vector-based match: {len(vector_results)} products for '{query_text[:30]}...'"
                    )
                    return vector_results[:limit]
            except Exception as exc:
                logger.warning(f"[Retrieval] Vector RPC query gagal/belum di-setup: {exc}")

    # === Mode 2: Same-Category Products ===
    if current_category:
        try:
            query = (
                supabase.table("products")
                .select(PRODUCT_COLS)
                .eq("category", current_category)
                .eq("is_active", True)
                .is_("deleted_at", "null")
                .order("price", desc=False)
                .limit(limit + 1)
                .execute()
            )
            category_results = query.data or []

            if current_product_id:
                category_results = [
                    p for p in category_results if p.get("id") != current_product_id
                ]

            if category_results:
                logger.info(
                    f"[Retrieval] Category-based: {len(category_results)} products in '{current_category}'"
                )
                return category_results[:limit]
        except Exception as exc:
            logger.warning(f"[Retrieval] Category query failed: {exc}")

    # === Mode 3: General Fallback (Top Produk Aktif Terbaru) ===
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
            all_products = [p for p in all_products if p.get("id") != current_product_id]

        logger.info(f"[Retrieval] General Fallback: {len(all_products)} products returned.")
        return all_products[:limit]

    except Exception as exc:
        logger.error(f"[Retrieval] Semua mode retrieval gagal: {exc}")
        return []


def save_recommendation_log(
    customer_id: str,
    product_id: str,
    conversation_id: str,
    reason: str,
    similarity_score: Optional[float] = None,
) -> None:
    """
    Mencatat log rekomendasi ke tabel `recommendations` untuk evaluasi AI.
    """
    try:
        supabase = get_supabase()
        supabase.table("recommendations").insert({
            "customer_id": customer_id,
            "product_id": product_id,
            "conversation_id": conversation_id,
            "reason": reason,
            "similarity_score": similarity_score,
            "was_accepted": None,  # Diisi saat pelanggan merespons/membeli
        }).execute()
        logger.info(f"[Retrieval] Recommendation logged for product {product_id[:8]}")
    except Exception as exc:
        logger.warning(f"[Retrieval] Failed to log recommendation: {exc}")
