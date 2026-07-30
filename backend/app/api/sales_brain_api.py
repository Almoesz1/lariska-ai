"""
LARISKA AI — Sales Brain API Router
"""

import logging
from fastapi import APIRouter, HTTPException, status

from app.pipeline.sales_brain import (
    classify_emotion,
    generate_sales_response,
    run_scoring_engine,
)
from app.schemas.sales_brain import (
    EmotionDetail,
    NegotiateRequest,
    NegotiateResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sales-brain", tags=["Sales Brain"])


@router.post(
    "/negotiate",
    response_model=NegotiateResponse,
    status_code=status.HTTP_200_OK,
    summary="Proses negosiasi pesan pembeli & hasilkan balasan sales otomatis",
)
def negotiate_sales(payload: NegotiateRequest):
    try:
        # 1. Hitung Scoring Engine & Guardrails
        decision_res = run_scoring_engine(
            features=payload.features,
            product_price=payload.product_price,
            floor_price=payload.floor_price,
            max_discount_pct=payload.max_discount_pct,
        )

        # 2. Klasifikasi Emosi Pembeli
        emotion_res = classify_emotion(payload.user_message)

        # 3. Generate Balasan Sales WhatsApp
        reply = generate_sales_response(
            decision_result=decision_res,
            product_name=payload.product_name,
            emotion_info=emotion_res,
            user_message=payload.user_message,
        )

        return NegotiateResponse(
            suggested_reply=reply,
            decision_result=decision_res,
            emotion_info=EmotionDetail(
                emotion=emotion_res.emotion.value,
                confidence=emotion_res.confidence,
                tone_hint=emotion_res.tone_hint,
            ),
        )

    except Exception as e:
        logger.error(f"[SalesBrainAPI] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal memproses negosiasi: {str(e)}",
        )