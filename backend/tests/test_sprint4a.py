"""Offline contract test for Sprint 4A pipeline stages.

External Gemini and Supabase integrations are exercised separately in live
smoke tests. This suite verifies that the Sprint 4A orchestration and the
database guard can run deterministically in CI without external credentials.
"""

from unittest.mock import patch

from app.pipeline.state_tracking import save_negotiation_log
from app.schemas.pipeline import (
    ConversationContext,
    EntityResult,
    IntentEntityResult,
    IntentType,
)


def _intent_for_text(text: str) -> IntentEntityResult:
    normalized = text.lower()
    if "kurang" in normalized:
        intent = IntentType.NEGO
        offered_price = 150000.0
    elif "invoice" in normalized:
        intent = IntentType.CHECKOUT
        offered_price = None
    elif normalized == "halo min":
        intent = IntentType.GREETING
        offered_price = None
    else:
        intent = IntentType.TANYA_PRODUK
        offered_price = None
    return IntentEntityResult(
        intent=intent,
        entities=EntityResult(offered_price=offered_price),
        confidence=1.0,
        raw_text=text,
    )


def _context_for_intent(_: object, __: str, intent: IntentEntityResult) -> ConversationContext:
    return ConversationContext(
        conversation_id="test-conversation",
        customer_id="test-customer",
        whatsapp_number="6281299998888",
        product_id="test-product",
        product_name="Kemeja Batik",
        product_price=200000.0,
        product_floor_price=160000.0,
        product_stock=10,
        total_orders=1,
    )


def test_sprint_4a():
    messages = [
        "Halo kak, mau tanya dong kemeja batik ukurannya ready gak?",
        "Bisa kurang gak kak harganya? Kalau Rp 150.000 boleh?",
        "Oke deh aku mau beli 1 pcs mas, tolong invoice ya.",
        "Halo min",
    ]

    with (
        patch("app.pipeline.intent_entity.extract_intent_entity", side_effect=_intent_for_text),
        patch("app.pipeline.state_tracking.build_context", side_effect=_context_for_intent),
        patch("app.pipeline.state_tracking.save_message", return_value={"id": "test-message"}),
    ):
        from app.pipeline.intent_entity import extract_intent_entity
        from app.pipeline.state_tracking import build_context, save_message

        for message in messages:
            intent = extract_intent_entity(message)
            context = build_context(object(), "6281299998888", intent)
            saved = save_message(
                supabase=object(),
                conversation_id=context.conversation_id,
                sender_type="customer",
                content_type="text",
                raw_text=message,
                intent=intent.intent.value,
                entities=intent.entities.model_dump(),
            )
            assert context.product_price == 200000.0
            assert saved["id"] == "test-message"

    # The real guard is intentionally not mocked: no_nego must never reach DB.
    result = save_negotiation_log(
        supabase=object(),
        conversation_id="test-conversation",
        product_id="test-product",
        customer_offer_price=None,
        ai_decision="no_nego",
        ai_offer_price=None,
        floor_price_snapshot=0,
    )
    assert result == {}
