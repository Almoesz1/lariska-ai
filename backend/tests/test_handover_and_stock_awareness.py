"""Regression tests for real-time stock features and human handover signals."""

from types import SimpleNamespace
from unittest.mock import patch

from app.api.whatsapp_webhook import _build_scoring_decision
from app.pipeline.handover import evaluate_handover
from app.pipeline.sales_brain.emotion import classify_emotion
from app.schemas.pipeline import (
    ConversationContext,
    EmotionResult,
    EmotionType,
    EntityResult,
    IntentEntityResult,
    IntentType,
)


def test_handover_detects_explicit_request_in_indonesian_text():
    intent = IntentEntityResult(
        intent=IntentType.KOMPLAIN,
        entities=EntityResult(),
        confidence=0.95,
        raw_text="Tolong hubungkan saya ke admin sekarang",
    )
    context = ConversationContext(conversation_id="c", customer_id="u", whatsapp_number="6281")
    result = evaluate_handover(intent, context, EmotionResult(emotion=EmotionType.MARAH))
    assert result.should_handover is True
    assert result.urgency_level == "high"


def test_light_catalog_complaint_does_not_trigger_handover():
    intent = IntentEntityResult(intent=IntentType.KOMPLAIN, entities=EntityResult(), confidence=0.95, raw_text="kecewa")
    context = ConversationContext(conversation_id="c", customer_id="u", whatsapp_number="6281")
    result = evaluate_handover(intent, context, EmotionResult(emotion=EmotionType.MARAH))
    assert result.should_handover is False


def test_serious_complaint_triggers_handover():
    intent = IntentEntityResult(
        intent=IntentType.KOMPLAIN,
        entities=EntityResult(),
        confidence=0.95,
        raw_text="Pesanan belum sampai dan saya minta refund sekarang",
    )
    context = ConversationContext(conversation_id="c", customer_id="u", whatsapp_number="6281")
    result = evaluate_handover(intent, context, EmotionResult(emotion=EmotionType.MARAH))

    assert result.should_handover is True
    assert result.urgency_level == "critical"


def test_negotiation_with_pcs_does_not_trigger_false_cs_handover():
    intent = IntentEntityResult(
        intent=IntentType.NEGO,
        entities=EntityResult(quantity=5, offered_price=20000),
        confidence=0.95,
        raw_text="Terlalu mahal, saya ambil 5 pcs kalau 20 ribu bisa?",
    )
    context = ConversationContext(conversation_id="c", customer_id="u", whatsapp_number="6281")
    result = evaluate_handover(intent, context, EmotionResult(emotion=EmotionType.MARAH))

    assert result.should_handover is False


def test_negotiation_uses_stable_empathy_not_angry_llm_label():
    result = classify_emotion("Kopinya mahal, kalau 20 ribu bisa?", IntentType.NEGO)

    assert result.emotion == EmotionType.NETRAL
    assert result.confidence == 0.9


def test_scoring_uses_actual_low_stock_ratio():
    context = SimpleNamespace(product_price=25000, product_floor_price=20000, product_stock=2, total_orders=0)
    intent = SimpleNamespace(intent=IntentType.NEGO, entities=SimpleNamespace(quantity=1, offered_price=24000))
    emotion = SimpleNamespace(emotion=EmotionType.NETRAL)
    captured = {}

    def fake_engine(*, features, **_kwargs):
        captured.update(features)
        return {"final_action": "hold_price", "final_price": 25000, "applied_discount_pct": 0, "ml_confidence": .9, "floor_price_locked": False, "guard_reason": "safe"}

    with patch("app.api.whatsapp_webhook.run_scoring_engine", fake_engine):
        _build_scoring_decision(context, intent, emotion)

    assert captured["stock_ratio"] == 0.2


def test_scoring_respects_per_unit_offer_in_bundle_negotiation():
    context = SimpleNamespace(product_price=45000, product_floor_price=30000, product_stock=20, total_orders=0)
    intent = SimpleNamespace(
        intent=IntentType.NEGO,
        entities=SimpleNamespace(quantity=5, offered_price=40000),
        raw_text="Saya ambil 5 pcs, per pcs harganya 40 ribu ya",
    )
    emotion = SimpleNamespace(emotion=EmotionType.NETRAL)
    captured = {}

    def fake_engine(*, features, **_kwargs):
        captured.update(features)
        return {"final_action": "counter_offer", "final_price": 40000, "applied_discount_pct": .11, "ml_confidence": .9, "floor_price_locked": False, "guard_reason": "safe"}

    with patch("app.api.whatsapp_webhook.run_scoring_engine", fake_engine):
        _build_scoring_decision(context, intent, emotion)

    assert round(captured["discount_requested_pct"], 3) == round((45000 - 40000) / 45000, 3)
