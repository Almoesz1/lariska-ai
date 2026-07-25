"""
Script Pengujian Sprint 5A — Sales Brain Assembly

Menguji 4 komponen Sales Brain:
1. LightGBM Model Loader & Inference
2. Adaptive Scoring Engine (dengan Hard Floor Price Guardrail)
3. Emotion Classifier (Gemini)
4. LLM Response Generator

Jalankan dengan perintah:
cd backend
python -m tests.test_sprint5a
"""

import sys
import os
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.schemas.pipeline import (
    ConversationContext,
    EntityResult,
    IntentEntityResult,
    IntentType,
    ScoringDecisionType,
)
from app.pipeline.sales_brain.model_loader import predict_decision
from app.pipeline.sales_brain.scoring_engine import run_scoring_engine
from app.pipeline.sales_brain.emotion import classify_emotion
from app.pipeline.response_generator import generate_response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestSprint5A")


def test_sprint_5a():
    print("\n==========================================")
    print("=== TESTING SPRINT 5A: SALES BRAIN ASSEMBLY ===")
    print("==========================================\n")

    # 1. Test LightGBM Model Loader & Prediction Direct
    print("1. Testing LightGBM Model Inference Direct...")
    # Features: [margin_pct, stock_ratio, customer_loyalty, discount_requested_pct, hour_of_day, is_peak_hour]
    sample_features = [0.35, 0.8, 0.5, 0.2, 14, 0]
    decision_label, confidence = predict_decision(sample_features)
    print(f"   -> Features Input: {sample_features}")
    print(f"   -> Model Prediction: {decision_label} (Confidence: {confidence:.2f})")

    # 2. Test Adaptive Scoring Engine with Business Context & Floor Price Guardrail
    print("\n2. Testing Adaptive Scoring Engine with Guardrails...")
    mock_context = ConversationContext(
        conversation_id="mock-conv-123",
        customer_id="mock-cust-123",
        whatsapp_number="6281299998888",
        customer_name="Budi",
        total_orders=5,  # Loyal customer
        product_id="mock-prod-123",
        product_name="Kemeja Batik Premium",
        product_price=200000.0,
        product_floor_price=160000.0,  # Floor price strictly 160rb
        product_stock=20,
        product_category="Fashion",
        negotiation_round=1,
    )

    mock_intent = IntentEntityResult(
        intent=IntentType.NEGO,
        entities=EntityResult(
            product_name="Kemeja Batik Premium",
            offered_price=150000.0,  # Menawar 150rb (DI BAWAH floor price 160rb!)
        ),
        confidence=0.98,
        raw_text="Bisa 150rb gak mas untuk kemeja batiknya?",
    )

    scoring_res = run_scoring_engine(mock_context, mock_intent)
    print(f"   -> Harga Normal: Rp {mock_context.product_price:,.0f}")
    print(f"   -> Harga Penawaran Pelanggan: Rp {mock_intent.entities.offered_price:,.0f}")
    print(f"   -> Floor Price (Hard Guardrail): Rp {mock_context.product_floor_price:,.0f}")
    print(f"   -> Decision Output: {scoring_res.decision.value}")
    print(f"   -> Final Price (AI Offer): Rp {scoring_res.final_price:,.0f}")
    print(f"   -> Floor Price Enforced: {scoring_res.floor_price_enforced} (Harga final >= Floor Price: {scoring_res.final_price >= mock_context.product_floor_price})")

    # 3. Test Emotion Classifier
    print("\n3. Testing Emotion Classifier (Gemini)...")
    sample_text_emotion = "Bisa kirim cepat gak sih?! Saya butuh besok banget untuk acara!"
    emotion_res = classify_emotion(sample_text_emotion)
    print(f"   -> Input Teks: \"{sample_text_emotion}\"")
    print(f"   -> Emosi Terdeteksi: {emotion_res.emotion.value}")
    print(f"   -> Tone Hint: {emotion_res.tone_hint}")

    # 4. Test Response Generator
    print("\n4. Testing Response Generator...")
    reply_text = generate_response(
        context=mock_context,
        intent_result=mock_intent,
        emotion_result=emotion_res,
        scoring_decision=scoring_res,
    )
    print("   -> Generated Natural Response:")
    print(f"      \"{reply_text}\"")

    print("\n==========================================")
    print("=== TEST SPRINT 5A SELESAI ===")
    print("==========================================\n")


if __name__ == "__main__":
    test_sprint_5a()
