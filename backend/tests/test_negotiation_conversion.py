"""Regression tests for persuasive-but-safe price negotiation."""

from types import SimpleNamespace
from unittest.mock import patch

from app.api.whatsapp_webhook import _build_scoring_decision
from app.pipeline.response_generator import _fallback_response
from app.pipeline.sales_brain.guardrails import ProductConstraint, apply_guardrails
from app.pipeline.state_tracking import get_last_discussed_product_name, get_last_requested_quantity
from app.schemas.pipeline import EmotionType, IntentType, ScoringDecision, ScoringDecisionType


def test_hold_price_with_safe_margin_becomes_counter_offer():
    result = apply_guardrails(
        proposed_action="hold_price",
        requested_discount_pct=(23000 - 10000) / 23000,
        constraint=ProductConstraint(product_price=23000, floor_price=15000),
    )

    assert result["final_action"] == "counter_offer"
    assert 15000 <= result["final_price"] < 23000


def test_counter_offer_fallback_is_persuasive_and_price_safe():
    reply = _fallback_response(
        IntentType.NEGO,
        ScoringDecision(
            decision=ScoringDecisionType.COUNTER_OFFER,
            final_price=17250,
            discount_amount=5750,
            discount_pct=0.25,
            reasoning="safe counter offer",
        ),
    )

    assert "Rp17,250" in reply
    assert "menawar" in reply.lower()
    assert "pesanan" in reply.lower()


def test_recovers_product_from_conversation_memory_for_follow_up_offer():
    class Query:
        def select(self, *_args, **_kwargs): return self
        def eq(self, *_args, **_kwargs): return self
        def order(self, *_args, **_kwargs): return self
        def limit(self, *_args, **_kwargs): return self
        def execute(self):
            return type("Result", (), {"data": [{"entities": {"product_name": "Kopi Arabica"}}]})()

    class Supabase:
        def table(self, name):
            assert name == "messages"
            return Query()

    assert get_last_discussed_product_name(Supabase(), "conversation-id") == "Kopi Arabica"


def test_recovers_quantity_from_conversation_memory_for_checkout():
    class Query:
        def select(self, *_args, **_kwargs): return self
        def eq(self, *_args, **_kwargs): return self
        def order(self, *_args, **_kwargs): return self
        def limit(self, *_args, **_kwargs): return self
        def execute(self):
            return type("Result", (), {"data": [{"entities": {"quantity": 2}}]})()

    class Supabase:
        def table(self, name):
            assert name == "messages"
            return Query()

    assert get_last_requested_quantity(Supabase(), "conversation-id") == 2


def test_bundle_offer_is_converted_to_per_unit_discount_for_guardrails():
    context = SimpleNamespace(product_price=25000, product_floor_price=20000, total_orders=0)
    intent = SimpleNamespace(
        intent=IntentType.NEGO,
        entities=SimpleNamespace(quantity=2, offered_price=45000),
    )
    emotion = SimpleNamespace(emotion=EmotionType.NETRAL)
    captured = {}

    def fake_engine(*, features, product_price, floor_price):
        captured.update(features)
        return {
            "final_action": "discount",
            "final_price": 22500,
            "applied_discount_pct": 0.1,
            "ml_confidence": 0.9,
            "floor_price_locked": False,
            "guard_reason": "safe",
        }

    with patch("app.api.whatsapp_webhook.run_scoring_engine", fake_engine):
        decision = _build_scoring_decision(context, intent, emotion)

    assert captured["discount_requested_pct"] == 0.1
    assert decision.final_price == 22500
