"""
Script Pengujian Sprint 5A — Sales Brain Assembly

Perubahan setelah Quality Gate review:
- predict_decision() sekarang dipanggil dengan dict, bukan list posisional
  (sinkron dengan model_loader.py yang sudah diperbaiki).
- Tambah 3 regression test untuk bug KRITIS yang ditemukan saat audit:
  1. Decision label harus konsisten setelah guardrail floor_price switch
     DISCOUNT -> COUNTER_OFFER (sebelumnya: label tetap salah bilang
     "discount" walau sistem sebenarnya sudah menolak dan counter-offer).
  2. Model predict() gagal tidak boleh crash dengan UnboundLocalError.
  3. BONUS harus di-downgrade saat stock kritis rendah (guardrail yang
     sebelumnya didefinisikan tapi tidak pernah benar-benar dipakai).

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
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.schemas.pipeline import (
    ConversationContext,
    EntityResult,
    IntentEntityResult,
    IntentType,
    ScoringDecisionType,
)
from app.pipeline.sales_brain.model_loader import predict_decision
from app.pipeline.sales_brain import scoring_engine as se_module
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
    sample_features = {
        "margin_pct": 0.35, "stock_ratio": 0.8, "customer_loyalty": 0.5,
        "discount_requested_pct": 0.2, "hour_of_day": 14, "is_peak_hour": 0,
    }
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
        total_orders=5,
        product_id="mock-prod-123",
        product_name="Kemeja Batik Premium",
        product_price=200000.0,
        product_floor_price=160000.0,
        product_stock=20,
        product_category="Fashion",
        negotiation_round=1,
    )

    mock_intent = IntentEntityResult(
        intent=IntentType.NEGO,
        entities=EntityResult(
            product_name="Kemeja Batik Premium",
            offered_price=150000.0,
        ),
        confidence=0.98,
        raw_text="Bisa 150rb gak mas untuk kemeja batiknya?",
    )

    scoring_res = se_module.run_scoring_engine(mock_context, mock_intent)
    print(f"   -> Harga Normal: Rp {mock_context.product_price:,.0f}")
    print(f"   -> Harga Penawaran Pelanggan: Rp {mock_intent.entities.offered_price:,.0f}")
    print(f"   -> Floor Price (Hard Guardrail): Rp {mock_context.product_floor_price:,.0f}")
    print(f"   -> Decision Output: {scoring_res.decision.value}")
    print(f"   -> Final Price (AI Offer): Rp {scoring_res.final_price:,.0f}")
    print(f"   -> Floor Price Enforced: {scoring_res.floor_price_enforced} (Harga final >= Floor Price: {scoring_res.final_price >= mock_context.product_floor_price})")
    assert scoring_res.final_price >= mock_context.product_floor_price, "GUARDRAIL GAGAL: final_price < floor_price!"

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
    assert reply_text and len(reply_text.strip()) > 0, "Response generator mengembalikan teks kosong!"

    # ============================================================
    # REGRESSION TEST 1 — Bug kritis: decision label harus konsisten
    # setelah guardrail floor_price men-downgrade DISCOUNT -> COUNTER_OFFER
    # ============================================================
    print("\n--- [Regression Test 1] Konsistensi decision label setelah guardrail switch ---")
    guardrail_context = ConversationContext(
        conversation_id="c1", customer_id="cust1", whatsapp_number="628",
        total_orders=8,  # loyalty tinggi -> loyalty_bonus aktif -> diskon makin besar
        product_id="p1", product_name="Test Produk",
        product_price=200000.0, product_floor_price=190000.0,  # margin SANGAT tipis
        product_stock=20, negotiation_round=1,
    )
    guardrail_intent = IntentEntityResult(
        intent=IntentType.NEGO,
        entities=EntityResult(offered_price=100000.0),  # minta diskon 50% (jauh di bawah floor)
        confidence=0.9, raw_text="boleh setengah harga gak?",
    )
    with patch.object(se_module, "predict_decision", return_value=("discount", 0.9)):
        result1 = se_module.run_scoring_engine(guardrail_context, guardrail_intent)

    assert result1.final_price >= guardrail_context.product_floor_price, (
        f"GUARDRAIL GAGAL: final_price {result1.final_price} < floor_price {guardrail_context.product_floor_price}"
    )
    assert result1.decision == ScoringDecisionType.COUNTER_OFFER, (
        f"BUG: guardrail switch harusnya mengubah decision jadi 'counter_offer', "
        f"tapi hasilnya masih '{result1.decision.value}'. Ini akan bikin negotiation_logs "
        f"dan response_generator salah mengira sistem memberi diskon, padahal menolak."
    )
    print(f"   -> PASS: decision='{result1.decision.value}', final_price=Rp{result1.final_price:,.0f} (konsisten)")

    # ============================================================
    # REGRESSION TEST 2 — Bug kritis: model gagal tidak boleh crash
    # ============================================================
    print("\n--- [Regression Test 2] Model predict() gagal tidak crash (UnboundLocalError) ---")
    fail_context = ConversationContext(
        conversation_id="c2", customer_id="cust2", whatsapp_number="628",
        total_orders=1, product_id="p2", product_name="Test 2",
        product_price=100000.0, product_floor_price=80000.0,
        product_stock=10, negotiation_round=1,
    )
    fail_intent = IntentEntityResult(
        intent=IntentType.NEGO,
        entities=EntityResult(offered_price=90000.0),
        confidence=0.9, raw_text="boleh kurang?",
    )
    with patch.object(se_module, "predict_decision", side_effect=RuntimeError("model corrupt")):
        result2 = se_module.run_scoring_engine(fail_context, fail_intent)  # TIDAK BOLEH raise

    assert result2.decision == ScoringDecisionType.HOLD_PRICE
    assert result2.final_price == fail_context.product_price
    print(f"   -> PASS: fallback ke '{result2.decision.value}' tanpa crash")

    # ============================================================
    # REGRESSION TEST 3 — BONUS harus di-downgrade saat stock kritis rendah
    # ============================================================
    print("\n--- [Regression Test 3] BONUS ditolak saat stock kritis rendah ---")
    lowstock_context = ConversationContext(
        conversation_id="c3", customer_id="cust3", whatsapp_number="628",
        total_orders=8, product_id="p3", product_name="Test 3",
        product_price=100000.0, product_floor_price=80000.0,
        product_stock=1,  # SANGAT rendah
        negotiation_round=1,
    )
    lowstock_intent = IntentEntityResult(
        intent=IntentType.NEGO,
        entities=EntityResult(offered_price=95000.0),
        confidence=0.9, raw_text="ada bonus gak kalau ambil ini?",
    )
    with patch.object(se_module, "predict_decision", return_value=("bonus", 0.9)):
        result3 = se_module.run_scoring_engine(lowstock_context, lowstock_intent)

    assert result3.decision != ScoringDecisionType.BONUS, (
        "BUG: BONUS tetap diberikan meski stock kritis rendah — "
        "BONUS_THRESHOLD_STOCK tidak di-enforce."
    )
    print(f"   -> PASS: bonus di-downgrade jadi '{result3.decision.value}' saat stock kritis rendah")

    print("\n==========================================")
    print("=== TEST SPRINT 5A SELESAI — SEMUA ASSERTION LOLOS ===")
    print("==========================================\n")


if __name__ == "__main__":
    test_sprint_5a()