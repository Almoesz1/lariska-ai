"""Offline contract tests for the Sprint 5A Sales Brain."""

from unittest.mock import patch

from app.pipeline.response_generator import generate_response
from app.pipeline.sales_brain import scoring_engine
from app.schemas.pipeline import (
    ConversationContext,
    EmotionResult,
    EmotionType,
    EntityResult,
    IntentEntityResult,
    IntentType,
    ScoringDecision,
    ScoringDecisionType,
)


def _features(context: ConversationContext, offer: float) -> dict:
    price = context.product_price or 0.0
    floor = context.product_floor_price or price
    return {
        "margin_pct": max((price - floor) / price, 0.0),
        "stock_ratio": 1.0,
        "customer_loyalty": min(context.total_orders / 10.0, 1.0),
        "discount_requested_pct": max((price - offer) / price, 0.0),
        "hour_of_day": 14,
        "is_peak_hour": 0,
    }


def _as_decision(result: dict, price: float) -> ScoringDecision:
    final_price = float(result["final_price"])
    return ScoringDecision(
        decision=ScoringDecisionType(result["final_action"]),
        final_price=final_price,
        discount_amount=max(price - final_price, 0.0),
        discount_pct=float(result["applied_discount_pct"]),
        model_confidence=float(result["ml_confidence"]),
        floor_price_enforced=bool(result["floor_price_locked"]),
        reasoning=str(result["guard_reason"]),
    )


def test_sprint_5a():
    context = ConversationContext(
        conversation_id="mock-conv-123",
        customer_id="mock-cust-123",
        whatsapp_number="6281299998888",
        customer_name="Budi",
        total_orders=5,
        product_id="mock-prod-123",
        product_name="Kemeja Batik Premium",
        product_price=200000.0,
        product_floor_price=160000.0,
        product_stock=20,
        product_category="Fashion",
        negotiation_round=1,
    )
    intent = IntentEntityResult(
        intent=IntentType.NEGO,
        entities=EntityResult(product_name=context.product_name, offered_price=150000.0),
        confidence=0.98,
        raw_text="Bisa 150rb gak mas untuk kemeja batiknya?",
    )

    result = scoring_engine.run_scoring_engine(
        features=_features(context, intent.entities.offered_price or context.product_price),
        product_price=context.product_price,
        floor_price=context.product_floor_price,
    )
    decision = _as_decision(result, context.product_price)
    assert decision.final_price >= context.product_floor_price
    assert decision.decision in {
        ScoringDecisionType.HOLD_PRICE,
        ScoringDecisionType.DISCOUNT,
        ScoringDecisionType.BONUS,
        ScoringDecisionType.COUNTER_OFFER,
    }

    # Guardrail is deterministic even when ML proposes an unsafe discount.
    with patch.object(scoring_engine, "predict_decision", return_value=("discount", 0.9)):
        guarded = scoring_engine.run_scoring_engine(
            features=_features(context, 100000.0),
            product_price=context.product_price,
            floor_price=context.product_floor_price,
        )
    assert guarded["final_price"] >= context.product_floor_price
    assert guarded["floor_price_locked"] is True

    fake_response = type("Response", (), {"text": "Harga terbaik sudah kami siapkan."})()
    emotion = EmotionResult(
        emotion=EmotionType.BURU_BURU,
        confidence=1.0,
        tone_hint="Jawab langsung ke inti.",
    )
    with patch("app.pipeline.response_generator.generate_content", return_value=fake_response):
        reply = generate_response(
            context=context,
            intent_result=intent,
            emotion_result=emotion,
            scoring_decision=decision,
        )
    assert reply == fake_response.text
