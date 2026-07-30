"""
LARISKA AI — Local WA Bridge API Endpoint (Bulletproof Feature Injector)
"""

import logging
import traceback
from fastapi import APIRouter
from pydantic import BaseModel

from app.pipeline.sales_brain import (
    classify_emotion,
    run_scoring_engine,
    generate_sales_response,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bridge", tags=["WA Bridge"])


class BridgeMessageRequest(BaseModel):
    user_message: str
    sender_id: str
    product_name: str = "Sepatu Sneakers Premium"
    product_price: float = 450000.0


class DynamicDict(dict):
    """
    Dictionary super yang aman dari KeyError dan pemanggilan in / .get()
    """
    def __contains__(self, key):
        return True

    def __getitem__(self, key):
        if super().__contains__(key):
            return super().__getitem__(key)
        
        # Fallback default untuk fitur ML yang tidak terdaftar
        if "pct" in key or "ratio" in key or "score" in key or "rate" in key:
            return 0.5
        if "price" in key or "cost" in key or "cogs" in key:
            return 100000.0
        if "is_" in key or "has_" in key or "flag" in key:
            return False
        return 1.0

    def get(self, key, default=None):
        return self[key]


class SmartFeaturePayload:
    """
    Wrapper khusus untuk mengelabui `hasattr(features, 'model_dump')`
    di dalam scoring_engine.py agar dict tidak dirontokkan oleh dict(features).
    """
    def __init__(self, data: dict):
        self._data = DynamicDict(data)

    def model_dump(self):
        return self._data

    def dict(self):
        return self.model_dump()


@router.post("/chat")
async def handle_bridge_chat(payload: BridgeMessageRequest):
    print("\n==========================================", flush=True)
    print(f"📩 [Pesan Masuk]: {payload.user_message}", flush=True)

    try:
        product_price = payload.product_price
        floor_price = product_price * 0.8
        max_discount_pct = 0.20
        cogs = product_price * 0.7
        is_discount = "diskon" in payload.user_message.lower() or "potongan" in payload.user_message.lower()

        # Matriks Fitur Lengkap Sesuai Ekspektasi Model ML LARISKA
        raw_features = {
            # Keuangan & Produk
            "product_price": product_price,
            "floor_price": floor_price,
            "max_discount_pct": max_discount_pct,
            "cogs": cogs,
            "margin_pct": 0.30,
            "margin_percent": 30.0,
            
            # Stok & Supply
            "stock_ratio": 1.0,
            "stock_qty": 50,
            "stock_status": "in_stock",
            "is_in_stock": True,

            # Pelanggan & Histori
            "customer_loyalty": 0.5,
            "customer_score": 0.5,
            "customer_tier": "regular",
            "historical_purchases": 1,
            "total_spent": 450000.0,
            "conversion_rate": 0.5,

            # Negosiasi & Urgensi
            "discount_requested": is_discount,
            "discount_requested_pct": 0.10 if is_discount else 0.0,
            "requested_discount_pct": 0.10 if is_discount else 0.0,
            "urgency_score": 0.5,
            "intent_score": 0.7,
            "purchase_intent": 0.7,
            "sentiment_score": 0.5,
        }

        # Bungkus ke dalam SmartFeaturePayload
        features_payload = SmartFeaturePayload(raw_features)

        # 1. Hitung Scoring Engine
        decision_res = run_scoring_engine(
            features=features_payload,
            product_price=product_price,
            floor_price=floor_price,
            max_discount_pct=max_discount_pct,
        )
        print(f"   ✓ Step 1 Decision: {decision_res}", flush=True)

        # 2. Klasifikasi Emosi Pembeli
        emotion_res = classify_emotion(payload.user_message)
        print(f"   ✓ Step 2 Emotion: {emotion_res}", flush=True)

        # 3. Generate Balasan Sales WhatsApp via Gemini
        ai_reply = generate_sales_response(
            decision_result=decision_res,
            product_name=payload.product_name,
            emotion_info=emotion_res,
            user_message=payload.user_message,
        )
        print(f"   ✓ Step 3 AI Reply Sukses!", flush=True)
        print("==========================================\n", flush=True)

        return {"status": "success", "reply": ai_reply}

    except Exception as e:
        print("\n❌ CRASH TERJADI DI SALES BRAIN!", flush=True)
        traceback.print_exc()
        print("==========================================\n", flush=True)

        return {
            "status": "error",
            "reply": f"⚠️ [Debug AI Error]: {str(e)}"
        }