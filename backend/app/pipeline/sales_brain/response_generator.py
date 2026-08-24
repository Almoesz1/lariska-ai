"""
LARISKA AI - Sales Brain Response Generator
Modul generator balasan penjualan adaptif berbasis Gemini AI.
Mengintegrasikan analisis Intent, Emosi, Decision Engine (Negosiasi/Pricing), 
serta RAG Rekomendasi Produk.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from app.pipeline.gemini_client import generate_content_with_fallback

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_INSTRUCTION = """
Kamu adalah LARISKA, asisten penjual cerdas (AI Sales Executive) yang ramah, persuasif, empati, dan profesional di WhatsApp.

PRINSIP KOMUNIKASI & PENJUALAN:
1. Gunakan Bahasa Indonesia yang sopan, alami, ramah, dan komunikatif (seperti sales manusia profesional).
2. Gunakan emoticon secukupnya (1–3 per pesan) agar percakapan hangat namun tetap profesional.
3. Selalu pertimbangkan emosi pelanggan saat merespons (misal: berikan empati jika pelanggan frustrasi/kecewa).
4. Dalam konteks Negosiasi (NEGO):
   - Jika tawaran disetujui/diskon diberikan, sampaikan harga akhir dengan antusias sebagai penawaran spesial terbatas.
   - Jika tawaran ditolak / ditahan (HOLD_PRICE), jelaskan keunggulan nilai produk secara santun dan tawarkan alternatif jika ada.
5. Dalam konteks Checkout: Berikan konfirmasi pesanan dengan jelas dan panduan pembayaran secara antusias.
6. Selalu akhiri balasan dengan Call to Action (CTA) yang relevan untuk mendorong konversi penjualan.
"""


def _safe_get(obj: Any, key: str, default: Any = None) -> Any:
    """Helper serbaguna untuk mengambil nilai dari Dict maupun Pydantic Object / Class Instance."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _format_idr(amount: Union[int, float, None]) -> str:
    """Format angka ke format mata uang Rupiah."""
    if amount is None or amount <= 0:
        return "-"
    return f"Rp{int(amount):,}".replace(",", ".")


def _catalog_recommendation_reply(recommendations: List[Dict[str, Any]]) -> str:
    """Balasan katalog berbasis data agar nama/harga/stok tidak dihalusinasi LLM."""
    lines = []
    for item in recommendations[:3]:
        name = item.get("name", "Produk")
        price = _format_idr(item.get("price"))
        stock = item.get("stock")
        unit = item.get("unit_label") or "unit"
        stock_text = f" · stok {stock}" if stock is not None else ""
        lines.append(f"• *{name}* — {price}/{unit}{stock_text}")
    return (
        "Siap, Kak. Ini pilihan yang benar-benar tersedia saat ini:\n\n"
        + "\n".join(lines)
        + "\n\nBalas nama produk yang ingin Kakak cek, atau langsung tulis jumlah dan harga tawaran. Saya bantu sampai checkout 😊"
    )


def _negotiation_reply(
    context: Any, intent_result: Any, decision_type: str, final_price: Any, product_price: Any
) -> str:
    """Narasi negosiasi yang selalu mengikuti keputusan Sales Brain."""
    product_name = _safe_get(context, "product_name", "produk ini")
    quantity = max(int(_safe_get(_safe_get(intent_result, "entities", {}), "quantity", 1) or 1), 1)
    normal = _format_idr(product_price)
    approved = _format_idr(final_price)
    decision = str(decision_type or "").lower()

    if decision in {"discount", "counter_offer", "bonus"} and float(final_price or 0) < float(product_price or 0):
        total = _format_idr(float(final_price) * quantity)
        return (
            f"Terima kasih sudah menawar, Kak 😊 Untuk *{product_name}*, saya bisa amankan "
            f"harga terbaik *{approved}/unit* (total *{total}* untuk {quantity} unit), dari harga normal {normal}. "
            "Kalau cocok, balas *checkout* ya—nanti saya siapkan pembayaran aman via QRIS/bank transfer."
        )

    return (
        f"Saya paham Kak ingin harga yang lebih ringan 😊 Untuk *{product_name}*, tawaran tersebut belum bisa saya setujui "
        f"karena harus tetap menjaga kualitas dan harga aman. Harga terbaik yang bisa saya bantu saat ini *{approved}/unit* "
        f"(harga normal {normal}). Kalau cocok, saya siap proses checkout sekarang."
    )


def _contextual_acknowledgement_reply(context: Any) -> str:
    """Jaga konteks saat pelanggan membalas singkat setelah diskusi produk."""
    product_name = _safe_get(context, "product_name", "produk tadi")
    price = _format_idr(_safe_get(context, "product_price", 0))
    return (
        f"Siap, Kak 😊 Untuk *{product_name}* harganya {price}. "
        "Kalau sudah cocok, balas *checkout* atau tulis jumlah yang diinginkan; "
        "kalau masih ingin menawar, sebutkan harga tawarannya ya."
    )


async def generate_sales_response(
    text: Optional[str] = None,
    prompt: Optional[str] = None,
    system_instruction: Optional[str] = None,
    context: Optional[Any] = None,
    intent_result: Optional[Any] = None,
    emotion: Optional[Any] = None,
    emotion_result: Optional[Any] = None,
    scoring_decision: Optional[Any] = None,
    decision_result: Optional[Any] = None,
    recommended_products: Optional[List[Dict[str, Any]]] = None,
    **kwargs: Any,
) -> str:
    """
    Membuat balasan AI Sales berbasis konteks penuh (Intent, Emotion, Recommendation, Negotiation).
    Kompatibel penuh dengan pemanggilan positional/keyword dari router dan pipeline eksekusi.
    """
    try:
        # 1. Ekstraksi Query Teks Pengguna
        user_query = text or prompt or kwargs.get("user_message") or kwargs.get("contents") or ""
        if not user_query and intent_result:
            user_query = _safe_get(intent_result, "raw_text", "") or _safe_get(intent_result, "text", "")
        if not user_query and context:
            user_query = _safe_get(context, "latest_message", "")

        # 2. Ekstraksi Context & Profil Pelanggan
        cust_name = _safe_get(context, "customer_name", "Kakak")
        prod_name = _safe_get(context, "product_name", kwargs.get("product_name", "Produk Kami"))
        prod_price = _safe_get(context, "product_price", kwargs.get("product_price", 0.0))
        stock_qty = _safe_get(context, "product_stock", kwargs.get("stock_qty", 0))
        
        # 3. Ekstraksi Intent
        intent_val = _safe_get(intent_result, "intent", "GREETING")
        if hasattr(intent_val, "value"):
            intent_val = intent_val.value

        # 4. Ekstraksi Emosi Pelanggan
        detected_emotion = (
            emotion 
            or _safe_get(emotion_result, "emotion", None)
            or _safe_get(context, "emotion", "neutral")
        )
        if hasattr(detected_emotion, "value"):
            detected_emotion = detected_emotion.value

        # 5. Ekstraksi Decision / Scoring Engine (Harga & Diskon)
        decision_obj = scoring_decision or decision_result
        decision_type = (
            _safe_get(decision_obj, "final_action", None)
            or _safe_get(decision_obj, "decision", None)
            or _safe_get(decision_obj, "action", "no_nego")
        )
        if hasattr(decision_type, "value"):
            decision_type = decision_type.value

        final_price = _safe_get(decision_obj, "final_price", prod_price)
        discount_amount = _safe_get(decision_obj, "discount_amount", None)
        if discount_amount is None:
            discount_amount = max(0.0, float(prod_price or 0) - float(final_price or 0))
        reasoning = _safe_get(decision_obj, "guard_reason", None) or _safe_get(decision_obj, "reasoning", "")

        # 6. Ekstraksi Rekomendasi Produk (RAG)
        recs = recommended_products or _safe_get(context, "recommended_products", [])
        rec_text = ""
        if recs and isinstance(recs, list):
            rec_items = []
            for item in recs[:3]:
                r_name = item.get("name", "Produk Opsional")
                r_price = _format_idr(item.get("price", 0))
                r_desc = item.get("description", "")
                rec_items.append(f"• *{r_name}* ({r_price}) - {r_desc}")
            if rec_items:
                rec_text = "Rekomendasi Produk Tambahan:\n" + "\n".join(rec_items)

        # Fakta katalog dan keputusan harga tidak boleh dibiarkan berubah oleh
        # variasi LLM. Gemini tetap dipakai untuk dialog umum, tetapi dua jalur
        # ini sengaja deterministik demi pengalaman belanja yang konsisten.
        if str(intent_val).lower() == "rekomendasi" and recs:
            return _catalog_recommendation_reply(recs)
        if str(intent_val).lower() == "nego":
            return _negotiation_reply(
                context, intent_result, str(decision_type), final_price, prod_price
            )
        short_acknowledgements = {"oke", "ok", "ya", "yaudah", "yaudah deh", "baik", "sip", "setuju"}
        if (
            _normalise_message := " ".join(str(user_query).lower().strip().split())
        ) in short_acknowledgements and _safe_get(context, "product_id", None):
            return _contextual_acknowledgement_reply(context)

        # 7. Penyusunan System Instruction & Context Prompt
        base_sys = system_instruction or DEFAULT_SYSTEM_INSTRUCTION
        
        context_prompt = f"""
{base_sys}

=== METADATA TRANSAKSI & PELANGGAN ===
- Nama Pelanggan: {cust_name}
- Produk Diminta: {prod_name}
- Harga Normal Produk: {_format_idr(prod_price)}
- Sisa Stok Produk: {stock_qty} pcs
- Niat Pelanggan (Intent): {intent_val}
- Emosi Pelanggan Terdeteksi: {str(detected_emotion).upper()}

=== KEPUTUSAN HARGA / SCORING ENGINE ===
- Tipe Keputusan: {str(decision_type).upper()}
- Harga Akhir Disetujui: {_format_idr(final_price)}
- Potongan Diskon: {_format_idr(discount_amount)}
- Catatan Pertimbangan: {reasoning}

{rec_text}

=== PETUNJUK KHUSUS NADA BICARA ===
- Jika menanyakan STOK: Langsung infokan bahwa stok tersisa {stock_qty} pcs dan gunakan kalimat urgensi untuk segera mengamankan pesanan.
- Jika emosi FRUSTRATED/DISAPPOINTED: Berikan permohonan maaf dan nada yang sangat mengayomi.
- Jika Intent NEGO & Keputusan DISCOUNT: Beritahukan diskon khusus {_format_idr(discount_amount)} ini dengan antusias dan dorong untuk segera checkout.
- Jika Intent NEGO & Keputusan HOLD_PRICE: Jelaskan secara sopan bahwa harga {_format_idr(prod_price)} sudah merupakan nilai terbaik sesuai kualitas produk.
- Jika Intent CHECKOUT: Dorong pelanggan melakukan pembayaran dengan ramah.

Tolong buatkan pesan balasan WhatsApp yang persuasif dan sesuai dengan konteks di atas untuk merespons pesan pelanggan berikut:
"{user_query}"
"""

        logger.info(
            f"[SalesResponseGenerator] Generating response for intent={intent_val} | "
            f"emotion={detected_emotion} | decision={decision_type}"
        )

        # 8. Eksekusi Gemini Client
        response_result = await generate_content_with_fallback(
            prompt=user_query,
            system_instruction=context_prompt,
        )

        reply_text = str(response_result).strip()
        if reply_text:
            return reply_text

        raise ValueError("Hasil generasi konten Gemini kosong.")

    except Exception as exc:
        logger.error(f"[SalesResponseGenerator] Error generating response: {exc}", exc_info=True)

        # Fallback ramah & adaptif jika terjadi gangguan API
        cust_name_fallback = _safe_get(context, "customer_name", "Kak")
        return (
            f"Halo {cust_name_fallback}! Terima kasih sudah menghubungi LARISKA AI 😊 "
            "Ada yang bisa kami bantu terkait informasi produk atau promo menarik hari ini?"
        )


# Alias untuk kompatibilitas penuh dengan pipeline eksekusi
generate_response = generate_sales_response
