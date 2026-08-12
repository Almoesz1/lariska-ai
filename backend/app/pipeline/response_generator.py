"""
LARISKA AI — Sprint 5A
Response Generator — Tahap 6 AI Pipeline (FINAL STEP)

Menyusun balasan natural berbahasa Indonesia berdasarkan keputusan Sales Brain.

PRINSIP KRITIS (sesuai proposal Bab 4 & proposal Bab 6):
- LLM di sini HANYA bertugas menyusun bahasa natural dari keputusan yang sudah dibuat.
- LLM TIDAK menentukan harga, diskon, atau keputusan bisnis.
- Semua angka final sudah dikunci oleh ScoringEngine sebelum prompt dibuat.
- Nada disesuaikan berdasarkan EmotionResult dari emotion.py.

Output: teks balasan yang langsung dikirim ke WhatsApp pelanggan.

Referensi proposal Bab 4, Tahap 6: LLM Response Generation
"""

import logging
from typing import Optional

from google.genai import types

from app.core.config import settings
from app.pipeline.gemini_client import generate_content
from app.schemas.pipeline import (
    ConversationContext,
    EmotionResult,
    EmotionType,
    IntentEntityResult,
    IntentType,
    PipelineResponse,
    ScoringDecision,
    ScoringDecisionType,
)

logger = logging.getLogger(__name__)

# ============================================================
# System Prompt Template
# ============================================================

_SYSTEM_TEMPLATE = """Kamu adalah Sales Assistant AI untuk toko UMKM Indonesia bernama {shop_name}.
Kamu berkomunikasi lewat WhatsApp dengan cara yang alami dan khas Indonesia.

IDENTITASMU:
- Nama: LARISKA (AI Sales Assistant)
- Bahasa: Indonesia sehari-hari (bisa campur sedikit informal, tapi tetap sopan)
- JANGAN bilang kamu AI atau chatbot kepada pelanggan kecuali ditanya langsung

ATURAN KETAT (JANGAN DILANGGAR):
- Harga yang tercantum di prompt adalah harga FINAL — JANGAN negosiasi angka lain
- JANGAN menjanjikan diskon lebih dari yang sudah ditetapkan
- JANGAN memberikan informasi yang tidak ada di konteks

KEPUTUSAN BISNIS YANG SUDAH DIBUAT (kamu hanya merangkainya dalam bahasa natural):
{business_decision}

EMOSI PELANGGAN: {emotion} — {tone_hint}

KONTEKS PERCAKAPAN:
{context_info}

PRODUK YANG DIBAHAS:
{product_info}

REKOMENDASI PRODUK LAIN (jika relevan):
{recommendations}

Tulis balasan WhatsApp yang:
1. Sesuai dengan emosi pelanggan ({emotion})
2. Mengkomunikasikan keputusan bisnis di atas dengan bahasa natural
3. Singkat dan to the point (max 4-5 kalimat untuk pesan normal, lebih panjang hanya jika perlu detail produk)
4. Gunakan emoji secukupnya (1-2 emoji saja, tidak berlebihan)
5. JANGAN sertakan angka harga LAIN selain yang sudah ditetapkan di business_decision

Tulis HANYA teks balasannya saja, tidak ada penjelasan tambahan.
"""


def _format_business_decision(decision: Optional[ScoringDecision], product_name: Optional[str]) -> str:
    if not decision or decision.decision == ScoringDecisionType.NO_NEGO:
        return "Tidak ada negosiasi harga. Jawab pertanyaan pelanggan dengan informatif."

    d = decision
    produk = product_name or "produk ini"

    if d.decision == ScoringDecisionType.HOLD_PRICE:
        return f"Harga {produk} sudah final di harga normal. Tidak bisa diturunkan lagi."

    if d.decision == ScoringDecisionType.DISCOUNT:
        return (
            f"Setujui diskon untuk {produk}. "
            f"Harga jadi: Rp{d.final_price:,.0f} "
            f"(diskon {d.discount_pct:.0%} dari harga normal). "
            f"Sampaikan dengan antusias tapi tetap profesional."
        )

    if d.decision == ScoringDecisionType.COUNTER_OFFER:
        return (
            f"Tawarkan harga tengah untuk {produk}: Rp{d.final_price:,.0f}. "
            f"Ini adalah penawaran terbaik yang bisa diberikan. "
            f"Sampaikan bahwa ini harga special dan berikan sedikit urgensi."
        )

    if d.decision == ScoringDecisionType.BONUS:
        return (
            f"Harga {produk} tetap normal, tapi tawarkan bonus/tambahan. "
            f"Contoh: gratis ongkos kirim, atau bonus produk kecil pelengkap. "
            f"Sampaikan sebagai apresiasi untuk pelanggan."
        )

    return "Jawab pertanyaan pelanggan dengan informatif dan ramah."


def _format_product_info(context: ConversationContext) -> str:
    if not context.product_name:
        return "Belum ada produk spesifik yang dibahas."
    stock_status = "Ready ✅" if (context.product_stock or 0) > 0 else "Stok habis ❌"
    return (
        f"Nama: {context.product_name}\n"
        f"Harga Normal: Rp{context.product_price:,.0f}\n"
        f"Stok: {stock_status} ({context.product_stock or 0} unit)"
    )


def _format_context_info(context: ConversationContext, intent_result: IntentEntityResult) -> str:
    name = context.customer_name or "pelanggan"
    loyalty_label = "VIP 🌟" if context.total_orders >= 7 else ("Pelanggan Setia" if context.total_orders >= 3 else "Pelanggan Baru")
    return (
        f"Nama pelanggan: {name} ({loyalty_label}, {context.total_orders} order sebelumnya)\n"
        f"Intent: {intent_result.intent.value}\n"
        f"Putaran nego sesi ini: {context.negotiation_round}"
    )


def _format_recommendations(products: list[dict]) -> str:
    if not products:
        return "Tidak ada rekomendasi saat ini."
    lines = ["Produk lain yang mungkin menarik:"]
    for p in products[:3]:
        lines.append(f"- {p['name']}: Rp{float(p['price']):,.0f}")
    return "\n".join(lines)


def generate_response(
    context: ConversationContext,
    intent_result: IntentEntityResult,
    emotion_result: EmotionResult,
    scoring_decision: Optional[ScoringDecision],
    recommended_products: Optional[list[dict]] = None,
) -> str:
    """
    Generate teks balasan natural berdasarkan semua keputusan pipeline.

    Args:
        context: ConversationContext dari state_tracking.
        intent_result: Output dari intent_entity.
        emotion_result: Output dari emotion classifier.
        scoring_decision: Output dari scoring_engine (None jika bukan nego).
        recommended_products: Produk rekomendasi dari retrieval (opsional).

    Returns:
        Teks balasan yang siap dikirim ke WhatsApp.
    """
    prompt = _SYSTEM_TEMPLATE.format(
        shop_name="Toko Kami",  # Bisa dikonfigurasi dari settings nanti
        business_decision=_format_business_decision(scoring_decision, context.product_name),
        emotion=emotion_result.emotion.value,
        tone_hint=emotion_result.tone_hint,
        context_info=_format_context_info(context, intent_result),
        product_info=_format_product_info(context),
        recommendations=_format_recommendations(recommended_products or []),
    )

    logger.info(
        f"[ResponseGenerator] Generating reply: "
        f"intent={intent_result.intent.value} "
        f"emotion={emotion_result.emotion.value} "
        f"decision={scoring_decision.decision.value if scoring_decision else 'none'}"
    )

    model_name = getattr(settings, "gemini_model", "gemini-3.5-flash-lite")
    try:
        response = generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=500,
            ),
        )
        reply = response.text.strip()
        logger.info(f"[ResponseGenerator] Reply: '{reply[:100]}...' " if len(reply) > 100 else f"[ResponseGenerator] Reply: '{reply}'")
        return reply
    except Exception as exc:
        logger.error(f"[ResponseGenerator] Gemini error: {exc}")
        # Fallback hardcoded — daripada silent failure
        return _fallback_response(intent_result.intent, scoring_decision)


def _fallback_response(intent: IntentType, decision: Optional[ScoringDecision]) -> str:
    """Fallback saat Gemini gagal — tetap berikan respons bermakna."""
    if intent == IntentType.NEGO and decision:
        if decision.decision == ScoringDecisionType.DISCOUNT:
            return f"Baik, kami setujui harga Rp{decision.final_price:,.0f} untuk Anda. Mau lanjut order? 😊"
        if decision.decision == ScoringDecisionType.HOLD_PRICE:
            return "Maaf, harga sudah final dan tidak bisa diturunkan lagi. Apakah ada yang bisa kami bantu?"
        if decision.decision == ScoringDecisionType.COUNTER_OFFER:
            return f"Gimana kalau Rp{decision.final_price:,.0f}? Itu penawaran terbaik dari kami 🙏"
    if intent == IntentType.GREETING:
        return "Halo! Selamat datang 😊 Ada yang bisa kami bantu?"
    if intent == IntentType.TANYA_HARGA:
        return "Silakan tanya harga produk yang Anda inginkan, kami siap bantu!"
    return "Terima kasih sudah menghubungi kami! Ada yang bisa kami bantu? 😊"
