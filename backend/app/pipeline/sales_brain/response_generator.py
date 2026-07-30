"""
LARISKA AI — Sprint 5A
Response Generator — Copilot Sales Balasan WhatsApp

Tugas: Mengubah hasil angka kaku dari Scoring Engine & Emotion Classifier
menjadi balasan WhatsApp yang persuasif, ramah, dan adaptif.
"""

import logging
from typing import Any, Dict

from google.genai import types

from app.pipeline.gemini_client import get_gemini_client
from app.schemas.pipeline import EmotionResult

logger = logging.getLogger(__name__)

_GEMINI_MODEL = "gemini-3.5-flash-lite"


def generate_sales_response(
    decision_result: Dict[str, Any],
    product_name: str,
    emotion_info: EmotionResult,
    user_message: str,
) -> str:
    """Generate balasan teks WhatsApp adaptif."""
    final_action = decision_result["final_action"]
    final_price = decision_result["final_price"]
    discount_pct = int(decision_result["applied_discount_pct"] * 100)

    prompt = f"""Kamu adalah LARISKA AI, asisten sales toko online yang sangat lihai, ramah, dan empati.
Tugasmu adalah membalas pesan calon pembeli terkait produk '{product_name}'.

Pesan Pembeli: "{user_message}"
Emosi Pembeli: {emotion_info.emotion.value}
Petunjuk Nada: {emotion_info.tone_hint}

KEPUTUSAN BISNIS (KUNCI MATI):
- Aksi: {final_action.upper()}
- Harga Final: Rp{final_price:,.0f} (HARUS PERSIS SAMA, DILARANG MENGUBAH HARGA INI)
- Diskon Disetujui: {discount_pct}%

PANDUAN RESPON:
- Jika HOLD_PRICE: Sampaikan bahwa harga Rp{final_price:,.0f} sudah best price karena kualitas produk terjamin.
- Jika DISCOUNT: Berikan kabar gembira diskon {discount_pct}% disetujui sehingga harga jadi Rp{final_price:,.0f}.
- Jika COUNTER_OFFER: Tawarkan harga titik tengah terbaik di Rp{final_price:,.0f}.
- Jika BONUS: Tawarkan harga Rp{final_price:,.0f} plus sebutkan bonus suvenir khusus.

Selalu sesuaikan nada balasan dengan petunjuk nada emosi pembeli. Buat balasan singkat (max 3 kalimat), alami khas WhatsApp Indonesia, dan akhiri dengan Call To Action (CTA) pembelian.
"""

    try:
        client = get_gemini_client()
        response = client.models.generate_content(
            model=_GEMINI_MODEL,
            contents=prompt,
        )
        if response.text:
            return response.text.strip()
    except Exception as exc:
        logger.warning(f"[ResponseGenerator] Gemini gagal ({exc}), menggunakan fallback generator.")

    # Fallback Generator jika LLM Limit
    if final_action == "discount":
        return f"Halo Kak! Spesial hari ini diskonnya disetujui ya! Produk {product_name} bisa Kakak dapatkan seharga Rp{final_price:,.0f}. Boleh langsung diselesaikan pembayarannya Kak?"
    elif final_action == "counter_offer":
        return f"Halo Kak, kalau segitu belum dapet nih. Tapi khusus Kakak, saya kasih penawaran terbaik di Rp{final_price:,.0f}. Gimana Kak, mau diambil sekarang?"
    elif final_action == "bonus":
        return f"Halo Kak, produk {product_name} harganya Rp{final_price:,.0f} ya. Tapi khusus pemesanan hari ini, saya kasih bonus suvenir gratis! Mau dikirim hari ini?"
    else:
        return f"Halo Kak, produk {product_name} seharga Rp{final_price:,.0f} ini sudah harga pas dengan kualitas terbaik Kak. Stoknya makin tipis nih, mau diorder sekarang?"