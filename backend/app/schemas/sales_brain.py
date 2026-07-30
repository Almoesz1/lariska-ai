"""
LARISKA AI — Sales Brain Schemas
"""

from typing import Any, Dict
from pydantic import BaseModel, Field


class NegotiateRequest(BaseModel):
    user_message: str = Field(..., json_schema_extra={"example": "Bisa diskon dikit ga kak? Pengen order cepat nih!"})
    product_name: str = Field(..., json_schema_extra={"example": "Sepatu Sneakers Local"})
    product_price: float = Field(..., json_schema_extra={"example": 100000.0})
    floor_price: float = Field(..., json_schema_extra={"example": 80000.0})
    max_discount_pct: float = Field(0.25, json_schema_extra={"example": 0.25})
    features: Dict[str, Any] = Field(
        ...,
        json_schema_extra={
            "example": {
                "margin_pct": 0.30,
                "stock_ratio": 0.80,
                "customer_loyalty": 0.70,
                "discount_requested_pct": 0.15,
                "hour_of_day": 14,
                "is_peak_hour": 0,
            }
        },
    )


class EmotionDetail(BaseModel):
    emotion: str
    confidence: float
    tone_hint: str


class NegotiateResponse(BaseModel):
    suggested_reply: str
    decision_result: Dict[str, Any]
    emotion_info: EmotionDetail