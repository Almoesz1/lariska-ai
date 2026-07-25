"""
LARISKA AI — Sprint 5A
Adaptive Scoring Engine — Tahap 4a AI Pipeline (INTI Sales Brain)

Ini adalah kontribusi AI utama LARISKA — sistem pengambilan keputusan bisnis yang
menggabungkan model ML terlatih (LightGBM dari Sprint 3A) + hard business rules.

Alur kerja:
1. Terima ConversationContext + IntentEntityResult
2. Susun ScoringInput (6 fitur) dari context
3. Jalankan inferensi LightGBM → decision + confidence
4. WAJIB enforce hard rule floor_price (bukan dari LLM, dari kode)
5. Hitung final_price yang valid
6. Return ScoringDecision

GUARDRAIL KRITIS (proposal Bab 9):
- floor_price TIDAK PERNAH dilanggar — ini hardcoded, bukan di prompt
- Diskon maksimum 40% (hard cap tambahan)
- Jika model prediksi 'discount' tapi hasilnya < floor_price → fallback ke 'counter_offer'

Referensi proposal Bab 6 & 7a: Adaptive Scoring Engine
"""

import logging
from datetime import datetime

from app.pipeline.sales_brain.model_loader import predict_decision
from app.schemas.pipeline import (
    ConversationContext,
    IntentEntityResult,
    IntentType,
    ScoringDecision,
    ScoringDecisionType,
    ScoringInput,
)

logger = logging.getLogger(__name__)

# ============================================================
# Business Rules Constants
# ============================================================

MAX_DISCOUNT_PCT = 0.40      # Hard cap diskon maksimum 40%
MAX_NEGO_ROUNDS = 3          # Setelah 3x nego → HOLD_PRICE paksa
BONUS_THRESHOLD_STOCK = 0.3  # Stock < 30% → tidak tawarkan bonus (stok terbatas)
PEAK_HOURS = {19, 20, 21, 22}  # Jam peak: 19.00 - 22.00

# Skor loyalitas threshold
LOYALTY_NEW_CUSTOMER = 0.0    # 0 order
LOYALTY_REGULAR = 0.3         # >= 3 order
LOYALTY_VIP = 0.7             # >= 7 order


def compute_scoring_input(
    context: ConversationContext,
    intent_result: IntentEntityResult,
) -> ScoringInput:
    """
    Susun ScoringInput dari ConversationContext + IntentEntityResult.
    6 fitur harus PERSIS sama dengan feature_names di training_metadata.json.
    """
    now = datetime.now()
    hour = now.hour

    # --- margin_pct: (price - floor_price) / price ---
    price = context.product_price or 0.0
    floor_price = context.product_floor_price or 0.0
    if price > 0:
        margin_pct = (price - floor_price) / price
    else:
        margin_pct = 0.0

    # --- stock_ratio: stock / max_stock (estimasi) ---
    # Karena tidak ada kolom max_stock, gunakan heuristik:
    # stock > 50 → ratio 1.0, stock < 5 → ratio 0.1
    stock = context.product_stock or 0
    stock_ratio = min(stock / 50.0, 1.0) if stock > 0 else 0.0

    # --- customer_loyalty: berdasarkan total orders ---
    total_orders = context.total_orders
    customer_loyalty = min(total_orders / 10.0, 1.0)

    # --- discount_requested_pct: (price - offered_price) / price ---
    offered_price = intent_result.entities.offered_price
    if offered_price and price > 0:
        discount_requested_pct = max((price - offered_price) / price, 0.0)
        discount_requested_pct = min(discount_requested_pct, 1.0)  # cap 100%
    else:
        discount_requested_pct = 0.0

    # --- hour_of_day & is_peak_hour ---
    is_peak_hour = 1 if hour in PEAK_HOURS else 0

    scoring_input = ScoringInput(
        margin_pct=round(margin_pct, 4),
        stock_ratio=round(stock_ratio, 4),
        customer_loyalty=round(customer_loyalty, 4),
        discount_requested_pct=round(discount_requested_pct, 4),
        hour_of_day=hour,
        is_peak_hour=is_peak_hour,
    )

    logger.debug(f"[ScoringEngine] ScoringInput: {scoring_input.model_dump()}")
    return scoring_input


def _compute_final_price(
    decision: ScoringDecisionType,
    price: float,
    floor_price: float,
    discount_requested_pct: float,
    customer_loyalty: float,
) -> tuple[float, float, float]:
    """
    Hitung harga final berdasarkan keputusan model.
    Selalu enforce floor_price — ini adalah guardrail proposal Bab 9.

    Returns:
        (final_price, discount_amount, discount_pct)
    """
    if decision == ScoringDecisionType.HOLD_PRICE or decision == ScoringDecisionType.NO_NEGO:
        return price, 0.0, 0.0

    if decision == ScoringDecisionType.DISCOUNT:
        # Diskon adaptif: setengah dari apa yang diminta, tapi tidak lebih dari MAX_DISCOUNT_PCT
        # Customer loyal dapat sedikit lebih banyak diskon
        loyalty_bonus = 0.05 if customer_loyalty >= LOYALTY_VIP else 0.0
        raw_discount = (discount_requested_pct / 2.0) + loyalty_bonus
        actual_discount_pct = min(raw_discount, MAX_DISCOUNT_PCT)
        final_price = price * (1 - actual_discount_pct)

        # ===== GUARDRAIL KRITIS =====
        if final_price < floor_price:
            # Tidak bisa kasih diskon sebesar itu → counter offer di floor
            logger.warning(
                f"[ScoringEngine] GUARDRAIL: discount would breach floor_price "
                f"({final_price:.0f} < {floor_price:.0f}). Switching to counter_offer at floor."
            )
            final_price = floor_price * 1.02  # Sedikit di atas floor (tidak menjual rugi)
            actual_discount_pct = (price - final_price) / price
            decision = ScoringDecisionType.COUNTER_OFFER

        discount_amount = price - final_price
        return final_price, round(discount_amount, 2), round(actual_discount_pct, 4)

    if decision == ScoringDecisionType.COUNTER_OFFER:
        # Tawarkan harga di tengah antara harga yang diminta customer dan floor_price
        offered_price_estimate = price * (1 - discount_requested_pct)
        counter_price = (offered_price_estimate + price) / 2  # Tengah-tengah
        counter_price = max(counter_price, floor_price * 1.01)  # Minimal 1% di atas floor
        counter_price = min(counter_price, price)  # Tidak boleh lebih dari harga asli

        discount_amount = price - counter_price
        discount_pct = discount_amount / price
        return round(counter_price, 2), round(discount_amount, 2), round(discount_pct, 4)

    if decision == ScoringDecisionType.BONUS:
        # Harga tetap, tapi ada bonus produk tambahan (tidak ada diskon harga)
        return price, 0.0, 0.0

    return price, 0.0, 0.0


def run_scoring_engine(
    context: ConversationContext,
    intent_result: IntentEntityResult,
) -> ScoringDecision:
    """
    Jalankan Adaptive Scoring Engine — entry point dari sales_brain/__init__.py.

    Flow:
    1. Kalau bukan intent nego → langsung NO_NEGO (tidak perlu model)
    2. Kalau nego round sudah >= MAX_NEGO_ROUNDS → HOLD_PRICE paksa
    3. Kalau produk tidak ditemukan → HOLD_PRICE (tidak ada konteks harga)
    4. Susun ScoringInput → predict via LightGBM → enforce guardrail → return ScoringDecision
    """
    price = context.product_price
    floor_price = context.product_floor_price

    # --- Case 1: Non-nego intent → tidak perlu scoring ---
    if intent_result.intent != IntentType.NEGO:
        return ScoringDecision(
            decision=ScoringDecisionType.NO_NEGO,
            final_price=price or 0.0,
            discount_amount=0.0,
            discount_pct=0.0,
            model_confidence=None,
            floor_price_enforced=True,
            reasoning=f"Intent adalah '{intent_result.intent.value}', bukan nego.",
        )

    # --- Case 2: Tidak ada produk terdefinisi ---
    if not price or not floor_price:
        logger.warning("[ScoringEngine] No product context for nego. Defaulting to HOLD_PRICE.")
        return ScoringDecision(
            decision=ScoringDecisionType.HOLD_PRICE,
            final_price=0.0,
            discount_amount=0.0,
            discount_pct=0.0,
            model_confidence=None,
            floor_price_enforced=True,
            reasoning="Produk belum teridentifikasi dalam konteks percakapan.",
        )

    # --- Case 3: Terlalu banyak nego rounds → paksa HOLD_PRICE ---
    if context.negotiation_round >= MAX_NEGO_ROUNDS:
        logger.info(f"[ScoringEngine] Max nego rounds ({MAX_NEGO_ROUNDS}) reached. Forcing HOLD_PRICE.")
        return ScoringDecision(
            decision=ScoringDecisionType.HOLD_PRICE,
            final_price=price,
            discount_amount=0.0,
            discount_pct=0.0,
            model_confidence=1.0,
            floor_price_enforced=True,
            reasoning=f"Sudah {context.negotiation_round}x nego. Harga sudah final.",
        )

    # --- Case 4: Jalankan model ML ---
    scoring_input = compute_scoring_input(context, intent_result)
    features = [
        scoring_input.margin_pct,
        scoring_input.stock_ratio,
        scoring_input.customer_loyalty,
        scoring_input.discount_requested_pct,
        scoring_input.hour_of_day,
        scoring_input.is_peak_hour,
    ]

    try:
        decision_str, confidence = predict_decision(features)
        decision = ScoringDecisionType(decision_str)
    except Exception as exc:
        logger.error(f"[ScoringEngine] Model predict failed: {exc}. Fallback to HOLD_PRICE.")
        decision = ScoringDecisionType.HOLD_PRICE
        confidence = 0.0

    # --- Hitung final_price dengan guardrail ---
    final_price, discount_amount, discount_pct = _compute_final_price(
        decision=decision,
        price=price,
        floor_price=floor_price,
        discount_requested_pct=scoring_input.discount_requested_pct,
        customer_loyalty=scoring_input.customer_loyalty,
    )

    # Reasoning untuk logging & debugging demo
    reasoning = (
        f"Model: {decision_str} (conf={confidence:.2f}) | "
        f"Margin: {scoring_input.margin_pct:.1%} | "
        f"Stock: {scoring_input.stock_ratio:.1%} | "
        f"Loyalty: {scoring_input.customer_loyalty:.1%} | "
        f"DiskonDiminta: {scoring_input.discount_requested_pct:.1%}"
    )

    result = ScoringDecision(
        decision=decision,
        final_price=final_price,
        discount_amount=discount_amount,
        discount_pct=discount_pct,
        model_confidence=confidence,
        floor_price_enforced=True,
        reasoning=reasoning,
    )

    logger.info(
        f"[ScoringEngine] Decision: {decision.value} | "
        f"Price: {price:.0f} → {final_price:.0f} | "
        f"Discount: {discount_pct:.1%} | "
        f"Confidence: {confidence:.2f}"
    )
    return result
