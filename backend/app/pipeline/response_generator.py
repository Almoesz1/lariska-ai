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
- Jika keputusan adalah COUNTER_OFFER atau DISCOUNT, fokus membantu pelanggan
  menyetujui harga tersebut; jangan menulis penolakan harga atau menyebut
  harga lain di luar angka final.

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
3. Untuk negosiasi: awali dengan apresiasi minat pelanggan, sebutkan nilai/manfaat
   produk secara singkat, lalu tutup dengan CTA checkout yang hangat.
4. Singkat dan to the point (max 4-5 kalimat untuk pesan normal, lebih panjang hanya jika perlu detail produk)
5. Gunakan emoji secukupnya (1-2 emoji saja, tidak berlebihan)
6. JANGAN sertakan angka harga LAIN selain yang sudah ditetapkan di business_decision

Tulis HANYA teks balasannya saja, tidak ada penjelasan tambahan.
"""


def _format_business_decision(
    decision: Optional[ScoringDecision], product_name: Optional[str], quantity: Optional[int] = None
) -> str:
    if not decision or decision.decision == ScoringDecisionType.NO_NEGO:
        return "Tidak ada negosiasi harga. Jawab pertanyaan pelanggan dengan informatif."

    d = decision
    produk = product_name or "produk ini"
    qty = max(int(quantity or 1), 1)
    bundle = (
        f" untuk {qty} unit dengan total Rp{d.final_price * qty:,.0f}"
        if qty > 1 else f" seharga Rp{d.final_price:,.0f}"
    )

    if d.decision == ScoringDecisionType.HOLD_PRICE:
        return (
            f"Harga {produk} tetap{bundle}; tidak ada ruang aman untuk diskon. "
            "Tetap tanggapi dengan hangat, tonjolkan nilai produk, dan ajak pelanggan checkout."
        )

    if d.decision == ScoringDecisionType.DISCOUNT:
        return (
            f"Setujui diskon untuk {produk}. "
            f"Harga jadi{bundle} "
            f"(diskon {d.discount_pct:.0%} dari harga normal). "
            f"Sampaikan dengan antusias tapi tetap profesional."
        )

    if d.decision == ScoringDecisionType.COUNTER_OFFER:
        return (
            f"Berikan counter-offer yang sudah disetujui untuk {produk}{bundle}. "
            "JANGAN menolak atau menyebut harga normal. Apresiasi minat pelanggan, "
            "sampaikan sebagai harga khusus yang aman untuk toko, beri alasan nilai produk secara singkat, "
            "dan tutup dengan CTA checkout yang ramah."
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
    unit = context.product_unit_label or "unit"
    specifications = context.product_specifications or {}
    spec_text = "; ".join(
        f"{str(key).replace('_', ' ')}: {', '.join(map(str, value)) if isinstance(value, list) else value}"
        for key, value in specifications.items()
        if value not in (None, "", [])
    ) or "Belum ada spesifikasi tambahan."
    return (
        f"Nama: {context.product_name}\n"
        f"Harga Normal: Rp{context.product_price:,.0f}\n"
        f"Stok: {stock_status} ({context.product_stock or 0} {unit})\n"
        f"Deskripsi: {context.product_description or 'Belum ada deskripsi.'}\n"
        f"Spesifikasi katalog: {spec_text}"
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


def _catalog_reply(context: ConversationContext, intent: IntentType) -> Optional[str]:
    """Jawaban faktual cepat untuk pertanyaan katalog yang umum.

    Menghindari satu panggilan LLM tambahan untuk fakta yang sudah tersedia
    di Supabase: stok, harga, dan spesifikasi. Ini membuat balasan lebih
    cepat sekaligus tidak memberi peluang model mengarang detail produk.
    """
    if intent == IntentType.GREETING:
        return "Halo Kak, selamat datang di LARISKA 😊 Saya bisa bantu cari produk, cek detail dan stok, negosiasi harga yang aman, sampai checkout. Pilih kategori di bawah atau tulis produk yang Kakak cari ya."
    if intent not in (IntentType.TANYA_STOK, IntentType.TANYA_HARGA, IntentType.TANYA_PRODUK):
        return None
    if not context.product_name:
        return "Boleh, Kak. Produk yang dimaksud yang mana ya? Sebutkan nama atau jenis produknya, nanti saya cekkan detail, stok, dan harganya."

    name = context.product_name
    unit = context.product_unit_label or "unit"
    stock = int(context.product_stock or 0)
    if intent == IntentType.TANYA_STOK:
        if stock > 0:
            return f"{name} masih ready, Kak—tersedia {stock} {unit}. Kalau cocok, saya juga bisa bantu cek harga atau siapkan pesanannya."
        return f"Maaf Kak, {name} sedang habis. Saya bisa bantu carikan alternatif yang tersedia ya."
    if intent == IntentType.TANYA_HARGA:
        return f"Harga {name} saat ini Rp{float(context.product_price or 0):,.0f} per {unit}. Stok tersedia {stock} {unit}. Kalau ambil lebih dari satu, boleh sampaikan jumlahnya ya, Kak."

    specs = context.product_specifications or {}
    detail = "; ".join(
        f"{str(key).replace('_', ' ')} {', '.join(map(str, value)) if isinstance(value, list) else value}"
        for key, value in specs.items() if value not in (None, "", [])
    )
    description = context.product_description or ""
    body = ". ".join(part.strip(". ") for part in (description, detail) if part)
    return f"{name}: {body or 'detail katalognya sedang kami lengkapi'}. Stok saat ini {stock} {unit}; harga Rp{float(context.product_price or 0):,.0f}."


def _recommendation_reply(products: list[dict]) -> Optional[str]:
    available = [product for product in products if int(product.get("stock") or 0) > 0][:3]
    if not available:
        return None
    lines = ["Ini pilihan yang tersedia saat ini, Kak:"]
    for product in available:
        unit = product.get("unit_label") or "unit"
        lines.append(f"• {product['name']} — Rp{float(product['price']):,.0f}/{unit} (stok {product.get('stock', 0)})")
    lines.append("Balas nama produk yang menarik, nanti saya cekkan detail atau bantu negosiasinya ya 😊")
    return "\n".join(lines)


def _negotiation_reply(
    context: ConversationContext,
    intent_result: IntentEntityResult,
    decision: ScoringDecision,
) -> str:
    """Balasan negosiasi deterministik; angka tidak pernah dibiarkan diubah LLM."""
    if not getattr(context, "product_id", None) or not context.product_name or not context.product_price:
        return (
            "Boleh banget, Kak 😊 Supaya saya hitung penawaran yang tepat dan aman, "
            "pilih atau sebutkan dulu nama produknya ya. Setelah itu saya langsung cek harga, stok, dan opsi negonya."
        )

    quantity = max(int(intent_result.entities.quantity or 1), 1)
    product_name = context.product_name or "produk ini"
    normal_price = float(context.product_price or 0)
    final_price = float(decision.final_price or normal_price)
    total = final_price * quantity

    if decision.decision in (ScoringDecisionType.DISCOUNT, ScoringDecisionType.COUNTER_OFFER):
        return (
            f"Terima kasih sudah menawar, Kak 😊 Untuk *{product_name}*, harga terbaik yang bisa saya amankan "
            f"adalah *Rp{final_price:,.0f}/unit*—total *Rp{total:,.0f}* untuk {quantity} unit. "
            "Kalau cocok, balas *checkout* ya; saya siapkan pembayaran QRIS/bank transfer."
        )

    if decision.decision == ScoringDecisionType.BONUS:
        return (
            f"Untuk *{product_name}*, harga tetap *Rp{final_price:,.0f}/unit*, Kak. "
            "Saya tetap bantu cek bonus atau alternatif yang paling sesuai. Mau lanjut checkout? 😊"
        )

    return (
        f"Saya paham Kak ingin harga yang lebih ringan 😊 Untuk *{product_name}*, harga aman yang bisa saya bantu "
        f"tetap *Rp{final_price:,.0f}/unit* (total *Rp{total:,.0f}* untuk {quantity} unit). "
        "Angka ini dijaga agar kualitas produk tetap terjamin. Kalau cocok, saya siap proses checkout."
    )


def _contextual_acknowledgement_reply(context: ConversationContext) -> str:
    return (
        f"Siap, Kak 😊 Untuk *{context.product_name or 'produk tadi'}* harganya "
        f"Rp{float(context.product_price or 0):,.0f}/unit. Kalau cocok, balas *checkout* atau tulis jumlahnya; "
        "kalau masih ingin menawar, sebutkan nominalnya ya."
    )


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
    # Harga, total, dan keputusan negosiasi adalah data bisnis. Respons untuk
    # jalur ini harus deterministik agar Gemini tidak dapat menyebut angka lain.
    if intent_result.intent == IntentType.NEGO and scoring_decision:
        logger.info("[ResponseGenerator] Mengirim jawaban negosiasi deterministik.")
        return _negotiation_reply(context, intent_result, scoring_decision)

    if intent_result.intent == IntentType.REKOMENDASI:
        recommendation_reply = _recommendation_reply(recommended_products or [])
        if recommendation_reply:
            logger.info("[ResponseGenerator] Mengirim rekomendasi katalog deterministik.")
            return recommendation_reply
        # Kategori/rekomendasi tidak boleh diteruskan ke LLM karena dapat
        # mengarang tautan katalog atau produk yang tidak tersedia.
        return "Maaf Kak, belum ada produk aktif yang cocok di pilihan itu. Boleh pilih kategori lain atau tulis nama produknya ya."

    if intent_result.intent == IntentType.TANYA_HARGA and recommended_products and not context.product_name:
        recommendation_reply = _recommendation_reply(recommended_products)
        if recommendation_reply:
            logger.info("[ResponseGenerator] Mengirim pilihan katalog untuk pertanyaan harga umum.")
            return recommendation_reply

    normalised_message = " ".join((intent_result.raw_text or "").lower().split())
    if (
        normalised_message in {"oke", "ok", "ya", "yaudah", "yaudah deh", "baik", "sip", "setuju"}
        and context.product_name
    ):
        return _contextual_acknowledgement_reply(context)

    factual_reply = _catalog_reply(context, intent_result.intent)
    if factual_reply:
        logger.info("[ResponseGenerator] Mengirim jawaban katalog deterministik.")
        return factual_reply

    prompt = _SYSTEM_TEMPLATE.format(
        shop_name="LARISKA",
        business_decision=_format_business_decision(
            scoring_decision, context.product_name, intent_result.entities.quantity
        ),
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
                temperature=0.35,
                max_output_tokens=280,
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
            return (
                f"Terima kasih sudah minat ya, Kak. Untuk produk ini harga terbaik yang bisa kami jaga "
                f"ada di Rp{decision.final_price:,.0f} agar kualitasnya tetap terjamin. "
                "Kalau cocok, saya bantu siapkan pesanannya sekarang ya 😊"
            )
        if decision.decision == ScoringDecisionType.COUNTER_OFFER:
            return (
                f"Terima kasih sudah menawar, Kak 😊 Khusus untuk Kakak, kami bisa bantu di "
                f"Rp{decision.final_price:,.0f}. Ini sudah harga terbaik yang aman sambil tetap menjaga "
                "kualitas produk—mau saya lanjutkan pesanannya sekarang?"
            )
    if intent == IntentType.GREETING:
        return "Halo! Selamat datang 😊 Ada yang bisa kami bantu?"
    if intent == IntentType.TANYA_HARGA:
        return "Silakan tanya harga produk yang Anda inginkan, kami siap bantu!"
    return "Terima kasih sudah menghubungi kami! Ada yang bisa kami bantu? 😊"
