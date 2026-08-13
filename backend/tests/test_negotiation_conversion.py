"""Regression tests for persuasive-but-safe price negotiation."""

from app.pipeline.response_generator import _fallback_response
from app.pipeline.sales_brain.guardrails import ProductConstraint, apply_guardrails
from app.pipeline.state_tracking import get_last_discussed_product_name
from app.schemas.pipeline import IntentType, ScoringDecision, ScoringDecisionType


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
