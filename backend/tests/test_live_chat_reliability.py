"""Regresi alur WhatsApp yang harus stabil saat video demo/live chat."""

from types import SimpleNamespace

from app.api.whatsapp_webhook import (
    _enforce_deterministic_negotiation_intent,
    _ground_product_entity_in_customer_text,
    _parse_idr_offer,
)
from app.pipeline.retrieval import _lexical_catalog_matches, _normalise_search_text
from app.pipeline.response_generator import generate_response
from app.pipeline import state_tracking
from app.schemas.pipeline import EntityResult, IntentEntityResult, IntentType


def test_kopi_query_never_falls_back_to_unrelated_catalog() -> None:
    products = [
        {"id": "1", "name": "Kopi Arabica", "category": "FNB", "stock": 50},
        {"id": "2", "name": "Kopi Robusta Gayo 250g", "category": "FNB", "stock": 37},
        {"id": "3", "name": "Sepatu Futsal Sintetis", "category": "Fashion", "stock": 19},
    ]

    results = _lexical_catalog_matches(products, "saya ingin beli kopi", limit=3)

    assert [product["name"] for product in results] == [
        "Kopi Arabica", "Kopi Robusta Gayo 250g"
    ]


def test_arabikanya_maps_to_kopi_arabica_not_general_fallback() -> None:
    products = [
        {"id": "1", "name": "Kopi Arabica", "category": "Coffee", "stock": 50},
        {"id": "2", "name": "Kopi Robusta Gayo 250g", "category": "Coffee", "stock": 37},
        {"id": "3", "name": "Tas Selempang Kanvas", "category": "Fashion", "stock": 22},
    ]

    results = _lexical_catalog_matches(products, "iya berapa jadinya arabikanya", limit=3)

    assert [product["name"] for product in results] == ["Kopi Arabica"]
    assert _normalise_search_text("kopi arabika") == "kopi arabica"


def test_explicit_rupiah_offer_forces_negotiation_guardrail() -> None:
    intent = IntentEntityResult(
        intent=IntentType.LAINNYA,
        entities=EntityResult(),
        confidence=0.1,
        raw_text="masih kemahalan, kalau 20 ribu untuk satu pack gimana?",
    )
    context = SimpleNamespace(product_id="product-1", product_name="Kopi Robusta Gayo")

    _enforce_deterministic_negotiation_intent(intent, context, intent.raw_text)

    assert _parse_idr_offer(intent.raw_text) == 20_000
    assert intent.intent == IntentType.NEGO
    assert intent.entities.offered_price == 20_000


def test_offer_without_product_never_accepts_hallucinated_product_entity() -> None:
    intent = IntentEntityResult(
        intent=IntentType.NEGO,
        entities=EntityResult(product_name="Jaket Hoodie Unisex", quantity=2, offered_price=45_000),
        confidence=0.9,
        raw_text="kalo saya ambil dua 45 aja ya",
    )

    _ground_product_entity_in_customer_text(intent, intent.raw_text)

    assert intent.entities.product_name is None


def test_category_selection_clears_stale_product_memory(monkeypatch) -> None:
    class Query:
        def select(self, *_args): return self
        def eq(self, *_args): return self
        def order(self, *_args, **_kwargs): return self
        def limit(self, *_args): return self
        def execute(self):
            return SimpleNamespace(data=[
                {"entities": {"target_product_category": "Coffee"}},
                {"entities": {"product_name": "Jaket Hoodie Unisex"}},
            ])

    class Supabase:
        def table(self, _name): return Query()

    assert state_tracking.get_last_discussed_product_name(Supabase(), "conv-1") is None


def test_product_on_negotiation_message_wins_over_its_category() -> None:
    class Query:
        def select(self, *_args): return self
        def eq(self, *_args): return self
        def order(self, *_args, **_kwargs): return self
        def limit(self, *_args): return self
        def execute(self):
            return SimpleNamespace(data=[{
                "entities": {"product_name": "Kopi Arabica", "target_product_category": "Coffee"}
            }])

    class Supabase:
        def table(self, _name): return Query()

    assert state_tracking.get_last_discussed_product_name(Supabase(), "conv-1") == "Kopi Arabica"


def test_only_product_in_selected_category_can_be_recovered() -> None:
    class Query:
        def select(self, *_args): return self
        def eq(self, *_args): return self
        def is_(self, *_args): return self
        def limit(self, *_args): return self
        def execute(self): return SimpleNamespace(data=[{"id": "arabica", "name": "Kopi Arabica"}])

    class Supabase:
        def table(self, _name): return Query()

    product = state_tracking.get_single_active_product_in_category(Supabase(), "Coffee")
    assert product["name"] == "Kopi Arabica"


def test_negotiation_reply_uses_engine_price_not_llm_variation() -> None:
    context = SimpleNamespace(
        customer_name="Gary",
        product_id="product-1",
        product_name="Kopi Robusta Gayo 250g",
        product_price=45_000,
        product_stock=37,
    )
    intent = IntentEntityResult(
        intent=IntentType.NEGO,
        entities=EntityResult(quantity=1, offered_price=20_000),
        confidence=1.0,
        raw_text="kalau 20 ribu gimana?",
    )
    decision = SimpleNamespace(decision="counter_offer", final_price=38_000, discount_amount=7_000)

    reply = generate_response(
        context=context,
        intent_result=intent,
        scoring_decision=decision,
        emotion_result=SimpleNamespace(emotion=SimpleNamespace(value="netral"), tone_hint=""),
    )

    assert "Rp38,000/unit" in reply
    assert "checkout" in reply.lower()
    assert "Rp20,000" not in reply


def test_negotiation_without_selected_product_never_returns_zero_price() -> None:
    context = SimpleNamespace(
        customer_name="Gary",
        product_id=None,
        product_name=None,
        product_price=None,
        product_stock=None,
    )
    intent = IntentEntityResult(
        intent=IntentType.NEGO,
        entities=EntityResult(quantity=2, offered_price=18_000),
        confidence=1.0,
        raw_text="aku pengen beli 2 jadi 18 ribu, boleh?",
    )
    decision = SimpleNamespace(decision="no_nego", final_price=0, discount_amount=0)

    reply = generate_response(
        context=context,
        intent_result=intent,
        scoring_decision=decision,
        emotion_result=SimpleNamespace(emotion=SimpleNamespace(value="netral"), tone_hint=""),
    )

    assert "nama produknya" in reply.lower()
    assert "rp0" not in reply.lower()
