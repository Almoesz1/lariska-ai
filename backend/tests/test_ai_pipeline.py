import sys
import os
import asyncio
import logging
import re
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Paksa sys.path agar folder root 'backend' terdeteksi
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Impor Pydantic Schema Resmi LARISKA AI
from app.schemas.pipeline import (
    IntentType,
    EmotionType,
    ScoringDecisionType,
    ScoringDecision,
    ConversationContext,
    EntityResult,
    IntentEntityResult,
    EmotionResult,
)

# Impor Modul Pipeline AI
from app.pipeline.intent_entity import extract_intent_entity
from app.pipeline.sales_brain import classify_emotion, run_scoring_engine
from app.pipeline.response_generator import generate_response
from app.pipeline.retrieval import get_recommended_products

console = Console()
logging.basicConfig(level=logging.ERROR)

# Default aman untuk CI/lokal: tidak mengonsumsi kuota Gemini.
# Mode live dijalankan eksplisit dengan LARISKA_AI_PIPELINE_MODE=live.
PIPELINE_MODE = os.getenv("LARISKA_AI_PIPELINE_MODE", "offline").strip().lower()
LIVE_MODE = PIPELINE_MODE == "live"
LIVE_PACING_SECONDS = float(os.getenv("LARISKA_AI_PIPELINE_PACING_SECONDS", "35"))


def _offline_intent_entity(text: str) -> IntentEntityResult:
    """Stub deterministik untuk memverifikasi kontrak pipeline tanpa API."""
    normalized = text.lower()
    if any(term in normalized for term in ("diskon", "ditawar", "bisa rp", "harga mati")):
        intent = IntentType.NEGO
    elif any(term in normalized for term in ("transfer", "invoice", "bungkus", "checkout")):
        intent = IntentType.CHECKOUT
    elif any(term in normalized for term in ("komplain", "lama", "belum sampe", "belum sampai")):
        intent = IntentType.KOMPLAIN
    elif any(term in normalized for term in ("bahan", "warna", "ukuran", "spesifikasi")):
        intent = IntentType.TANYA_PRODUK
    elif any(term in normalized for term in ("ready", "stok")):
        intent = IntentType.TANYA_STOK
    else:
        intent = IntentType.LAINNYA

    offered_price = None
    price_matches = re.findall(r"(?:rp\s*)?(\d+(?:[.]\d{3})?)\s*(?:ribu|rb)?", normalized)
    if intent == IntentType.NEGO and price_matches:
        raw_price = price_matches[-1].replace(".", "")
        multiplier = 1000 if "ribu" in normalized or "rb" in normalized else 1
        offered_price = float(raw_price) * multiplier

    return IntentEntityResult(
        intent=intent,
        entities=EntityResult(offered_price=offered_price),
        confidence=1.0,
        raw_text=text,
    )


def _offline_emotion(text: str) -> EmotionResult:
    normalized = text.lower()
    if "lama" in normalized or "!" in text:
        return EmotionResult(
            emotion=EmotionType.MARAH,
            confidence=1.0,
            tone_hint="Balas dengan empati dan langsung ke inti masalah.",
        )
    if any(term in normalized for term in ("sekarang", "detik ini", "cepat")):
        return EmotionResult(
            emotion=EmotionType.BURU_BURU,
            confidence=1.0,
            tone_hint="Balas langsung ke inti jawaban.",
        )
    return EmotionResult(
        emotion=EmotionType.NETRAL,
        confidence=1.0,
        tone_hint="Balas ramah dan profesional.",
    )


def _offline_response(scoring: ScoringDecision) -> str:
    """Balasan lokal yang menampilkan harga hasil Sales Brain, bukan harga LLM."""
    if scoring.decision == ScoringDecisionType.NO_NEGO:
        return "[OFFLINE] Kontrak pipeline valid; tidak ada perubahan harga."
    return (
        f"[OFFLINE] Keputusan Sales Brain: {scoring.decision.value}; "
        f"harga final Rp{scoring.final_price:,.0f}."
    )


def create_mock_context(
    product_name: str = "Sepatu Sneakers LARISKA Pro",
    product_price: float = 550000.0,
    product_floor_price: float = 400000.0,
    negotiation_round: int = 1,
) -> ConversationContext:
    return ConversationContext(
        conversation_id="conv_test_999",
        customer_id="cust_test_123",
        whatsapp_number="6281234567890",
        customer_name="Barak",
        total_orders=3,
        product_id="prod_sepatu_01",
        product_name=product_name,
        product_price=product_price,
        product_floor_price=product_floor_price,
        product_stock=10,
        product_category="Footwear",
        negotiation_round=negotiation_round,
    )


def build_scoring_features(ctx: ConversationContext, intent_res: any) -> dict:
    price = ctx.product_price or 1.0
    floor = ctx.product_floor_price or 0.0
    margin_pct = max((price - floor) / price, 0.0) if price > 0 else 0.0

    offered_price = None
    if hasattr(intent_res, "entities") and hasattr(intent_res.entities, "offered_price"):
        offered_price = intent_res.entities.offered_price

    if offered_price and offered_price > 0 and price > 0:
        discount_requested_pct = max((price - offered_price) / price, 0.0)
    else:
        discount_requested_pct = 0.0

    current_hour = datetime.now().hour
    is_peak = 1 if 19 <= current_hour <= 22 else 0

    return {
        "margin_pct": margin_pct,
        "stock_ratio": 1.0,
        "customer_loyalty": min((ctx.total_orders or 0) / 10.0, 1.0),
        "discount_requested_pct": discount_requested_pct,
        "hour_of_day": current_hour,
        "is_peak_hour": is_peak,
    }


# ============================================================
# SKENARIO PENGUJIAN
# ============================================================
TEST_SCENARIOS = [
    {
        "name": "Skenario 1: Tanya Produk & Spesifikasi",
        "input_text": "Halo kak, sepatu sneakers yang bahan kulit sintetis ready warna apa aja ya?",
        "context": create_mock_context(),
    },
    {
        "name": "Skenario 2: Nego Harga Layak (Di atas Floor Price)",
        "input_text": "Harga 550 ribu bisa ditawar jadi 480 ribu ga kak? Saya mau ambil sekarang nih.",
        "context": create_mock_context(negotiation_round=1),
    },
    {
        "name": "Skenario 3: Nego Sadis (Di bawah Floor Price Rp 400.000)",
        "input_text": "Bisa Rp 300.000 ga? Kalau bisa saya transfer detik ini juga.",
        "context": create_mock_context(negotiation_round=2),
    },
    {
        "name": "Skenario 4: Pelanggan Emosi / Komplain",
        "input_text": "Lama banget balesnya! Kemarin katanya pengiriman cuma 1 hari, ini kok belum sampe?!",
        "context": create_mock_context(),
    },
    {
        "name": "Skenario 5: Niat Checkout / Beli Direct",
        "input_text": "Oke siap saya bungkus 1 pasang ukuran 42 warna hitam ya. Kirim invoice-nya.",
        "context": create_mock_context(),
    },
]


async def run_pipeline_test(scenario: dict):
    title = scenario["name"]
    input_text = scenario["input_text"]
    ctx: ConversationContext = scenario["context"]

    console.print(f"\n[bold cyan]============ {title} ============[/bold cyan]")
    console.print(f"[bold yellow]Input User:[/bold yellow] \"{input_text}\"")

    # 1. Intent & Entity Extraction
    intent_res = _offline_intent_entity(input_text) if not LIVE_MODE else extract_intent_entity(input_text)

    # 2. Emotion Classifier
    emotion_res = _offline_emotion(input_text) if not LIVE_MODE else classify_emotion(input_text)

    # 3. Eksekusi Scoring Engine
    intent_val = getattr(intent_res, "intent", None)
    
    if intent_val != IntentType.NEGO:
        scoring_obj = ScoringDecision(
            decision=ScoringDecisionType.NO_NEGO,
            final_price=ctx.product_price or 0.0,
            discount_amount=0.0,
            discount_pct=0.0,
            model_confidence=1.0,
            floor_price_enforced=True,
            reasoning="Non-negotiation intent",
        )
    else:
        scoring_features = build_scoring_features(ctx, intent_res)
        scoring_raw = run_scoring_engine(
            features=scoring_features,
            product_price=ctx.product_price or 0.0,
            floor_price=ctx.product_floor_price or 0.0,
        )
        
        raw_action = scoring_raw.get("final_action", ScoringDecisionType.HOLD_PRICE)
        action_enum = ScoringDecisionType(raw_action) if isinstance(raw_action, str) else raw_action
        orig_p = ctx.product_price or 0.0
        fin_p = scoring_raw.get("final_price", orig_p)

        scoring_obj = ScoringDecision(
            decision=action_enum,
            final_price=fin_p,
            discount_amount=max(orig_p - fin_p, 0.0),
            discount_pct=scoring_raw.get("applied_discount_pct", 0.0),
            model_confidence=scoring_raw.get("ml_confidence", 1.0),
            floor_price_enforced=scoring_raw.get("floor_price_locked", True),
            reasoning=scoring_raw.get("guard_reason", ""),
        )

    # 4. Product Retrieval
    recommended_prods = []
    if intent_val in (IntentType.REKOMENDASI, IntentType.TANYA_PRODUK):
        if not LIVE_MODE:
            recommended_prods = [
                {"id": "p2", "name": "Running Shoes X", "price": 490000},
                {"id": "p3", "name": "Casual Slip-On", "price": 380000},
            ]
        else:
            try:
                recommended_prods = get_recommended_products(
                    customer_id=ctx.customer_id,
                    current_product_id=ctx.product_id,
                    current_category=ctx.product_category,
                    limit=2,
                )
            except Exception:
                recommended_prods = [
                    {"id": "p2", "name": "Running Shoes X", "price": 490000},
                    {"id": "p3", "name": "Casual Slip-On", "price": 380000},
                ]

    # 5. Sales Response Generator (dengan Retry Delay)
    if LIVE_MODE:
        # Retry 429/5xx ada di layer produksi, sama dengan webhook live.
        response_text = generate_response(
            context=ctx,
            intent_result=intent_res,
            emotion_result=emotion_res,
            scoring_decision=scoring_obj,
            recommended_products=recommended_prods,
        )
        reply_out = response_text.reply_text if hasattr(response_text, "reply_text") else str(response_text)
    else:
        reply_out = _offline_response(scoring_obj)

    # Output Tabel Diagnostik
    table = Table(title="AI Reasoning Breakdown", show_header=True, header_style="bold magenta")
    table.add_column("Komponen Pipeline", style="dim", width=25)
    table.add_column("Hasil Eksekusi & Parameter", style="bold")

    entities_val = getattr(intent_res, "entities", {})
    table.add_row("1. Intent Detected", f"[green]{intent_val}[/green]")
    table.add_row("   Entities", str(entities_val))

    emotion_val = getattr(emotion_res, "emotion", "N/A")
    conf_val = getattr(emotion_res, "confidence", 1.0)
    table.add_row("2. Emotion/Sentiment", f"[yellow]{emotion_val}[/yellow] (Conf: {conf_val:.2f})")

    floor_p = ctx.product_floor_price or 0.0
    orig_p = ctx.product_price or 0.0

    table.add_row("3. Dynamic Pricing Decision", f"[bold red]{scoring_obj.decision.value}[/bold red]")
    table.add_row("   Price Adjusted", f"Rp {orig_p:,.0f} -> [bold green]Rp {scoring_obj.final_price:,.0f}[/bold green] (Floor: Rp {floor_p:,.0f})")
    if scoring_obj.reasoning:
        table.add_row("   Guardrail Reason", f"[dim]{scoring_obj.reasoning}[/dim]")
    table.add_row("4. Recommendations Count", str(len(recommended_prods)))

    console.print(table)
    console.print(Panel(reply_out, title="[bold green]Generated Response (Gemini)[/bold green]", border_style="green"))


async def main():
    console.print(Panel.fit(
        "[bold white]LARISKA AI — Local Pipeline Diagnostic Suite[/bold white]\n"
        f"[dim]Mode: {'LIVE Gemini' if LIVE_MODE else 'OFFLINE mock'} | "
        "Menguji NLU, Emotion, LightGBM Scoring, & Response[/dim]",
        style="blue"
    ))

    for scenario in TEST_SCENARIOS:
        await run_pipeline_test(scenario)
        # Beri jeda 8 detik antar skenario untuk menjaga Quota RPM Gemini Free Tier
        if LIVE_MODE:
            await asyncio.sleep(LIVE_PACING_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
