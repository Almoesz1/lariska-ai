"""
LARISKA AI — Sprint 5A
Scoring Engine Orchestrator

Tugas: Menggabungkan prediksi ML dari model_loader.py dengan
Hard Business Guardrails dari guardrails.py.
"""

import logging
from typing import Any, Dict, Union

from app.pipeline.sales_brain.guardrails import ProductConstraint, apply_guardrails
from app.pipeline.sales_brain.model_loader import predict_decision

logger = logging.getLogger(__name__)


def run_scoring_engine(
    features: Union[dict, Any],
    product_price: float,
    floor_price: float,
    max_discount_pct: float = 0.25,
) -> Dict[str, Any]:
    """Eksekusi lengkap Adaptive Scoring Engine:

    1. Prediksi ML (LightGBM/GradientBoosting).
    2. Saring via Hard Guardrails (Floor Price Protection).
    3. Kembalikan paket keputusan terstruktur.
    """
    if hasattr(features, "model_dump"):
        feat_dict = features.model_dump()
    elif hasattr(features, "dict"):
        feat_dict = features.dict()
    else:
        feat_dict = dict(features)

    # 1. Dapatkan prediksi ML
    ml_action, confidence = predict_decision(feat_dict)

    # 2. Susun batasan produk
    constraint = ProductConstraint(
        product_price=product_price,
        floor_price=floor_price,
        max_discount_pct=max_discount_pct,
    )

    # 3. Terapkan Guardrails
    requested_discount = feat_dict.get("discount_requested_pct", 0.0)
    guarded_result = apply_guardrails(
        proposed_action=ml_action,
        requested_discount_pct=requested_discount,
        constraint=constraint,
    )

    return {
        "ml_suggested_action": ml_action,
        "ml_confidence": round(confidence, 4),
        "final_action": guarded_result["final_action"],
        "applied_discount_pct": guarded_result["applied_discount_pct"],
        "final_price": guarded_result["final_price"],
        "guard_reason": guarded_result["guard_reason"],
        "floor_price_locked": guarded_result["floor_price_locked"],
    }