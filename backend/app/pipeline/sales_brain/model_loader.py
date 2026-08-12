"""
LARISKA AI — Sprint 5A (QA Patch)
Model Loader — Adaptive Scoring Engine

Perubahan & Fitur:
- FIX CRITICAL: joblib.load() digunakan untuk membaca artefak ML.
- FIX FEATURE NAMES WARNING: Menggunakan pandas.DataFrame dengan kolom eksplisit.
- FIX PYDANTIC INPUT: Support input dict maupun objek ScoringInput.
- AUTO-FILL FALLBACK: Mengisi otomatis fitur yang tidak dikirim oleh client/test
  dengan default value aman agar terhindar dari KeyError / 500 Internal Server Error.
- Warmup fail-fast saat startup.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Union

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ============================================================
# Path Resolution
# ============================================================

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_MODEL_DIR = _PROJECT_ROOT / "ml" / "model_artifacts"

MODEL_PATH = _MODEL_DIR / "scoring_model.pkl"
ENCODER_PATH = _MODEL_DIR / "label_encoder.pkl"
METADATA_PATH = _MODEL_DIR / "training_metadata.json"


# ============================================================
# Default Values Penyelamat Error 500
# ============================================================

DEFAULT_FEATURE_VALUES = {
    "margin_pct": 0.30,
    "stock_ratio": 0.80,
    "customer_loyalty": 0.50,
    "customer_loyalty_tier": "NEW",
    "discount_requested_pct": 0.10,
    "hour_of_day": 14,
    "is_peak_hour": 0,
    "day_of_week": 1,
    "is_weekend": 0,
    "urgency_score": 0.5,
    "basket_size": 1,
    "historical_conversion_rate": 0.5,
    "competitor_price_ratio": 1.0,
    "customer_lifetime_value": 0.0,
    "offered_price": 0.0,
    "total_previous_orders": 0,
}


# ============================================================
# Loaders
# ============================================================

@lru_cache(maxsize=1)
def _load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model tidak ditemukan: {MODEL_PATH}"
        )

    logger.info(f"[ModelLoader] Loading scoring model dari {MODEL_PATH}...")
    model = joblib.load(MODEL_PATH)

    logger.info(
        f"[ModelLoader] Model loaded: {type(model).__name__}"
    )

    return model


@lru_cache(maxsize=1)
def _load_encoder():
    if not ENCODER_PATH.exists():
        raise FileNotFoundError(
            f"Encoder tidak ditemukan: {ENCODER_PATH}"
        )

    encoder = joblib.load(ENCODER_PATH)

    logger.info(
        f"[ModelLoader] Encoder loaded: {list(encoder.classes_)}"
    )

    return encoder


@lru_cache(maxsize=1)
def _load_feature_order():
    """
    Ambil urutan fitur yang dipakai saat training dari metadata.
    """
    if not METADATA_PATH.exists():
        logger.warning(
            "[ModelLoader] training_metadata.json tidak ditemukan. "
            "Menggunakan fallback feature order."
        )

        return [
            "margin_pct",
            "stock_ratio",
            "customer_loyalty",
            "discount_requested_pct",
            "hour_of_day",
            "is_peak_hour",
        ]

    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    feature_names = metadata.get("feature_names")

    if not feature_names:
        raise ValueError(
            "feature_names tidak ditemukan di training_metadata.json"
        )

    logger.info(
        f"[ModelLoader] Feature order: {feature_names}"
    )

    return feature_names


def get_model_and_encoder():
    return _load_model(), _load_encoder()


# ============================================================
# Prediction
# ============================================================

def predict_decision(
    features: Union[dict, Any],
) -> tuple[str, float]:
    """
    Ekstrak fitur, lakukan auto-fill jika ada fitur yang kurang, 
    lalu lakukan prediksi dengan model ML.

    Args:
        features: dict atau objek ScoringInput.

    Returns:
        ("bonus", 0.918)
    """
    # Ekstrak data ke dict jika input berupa Pydantic Model (ScoringInput)
    if hasattr(features, "model_dump"):
        feat_dict = features.model_dump()
    elif hasattr(features, "dict"):
        feat_dict = features.dict()
    elif isinstance(features, dict):
        feat_dict = features
    else:
        feat_dict = dict(features)

    model, encoder = get_model_and_encoder()
    feature_order = _load_feature_order()

    row = {}
    for feature_name in feature_order:
        if feature_name in feat_dict:
            row[feature_name] = feat_dict[feature_name]
        else:
            # Auto-fill fallback jika fitur tidak dikirim
            default_val = DEFAULT_FEATURE_VALUES.get(feature_name, 0.0)
            row[feature_name] = default_val
            logger.warning(
                f"[ModelLoader] Feature '{feature_name}' missing from input. Auto-filled with default: {default_val}"
            )

    # Buat DataFrame dengan nama kolom eksplisit untuk menghindari Warning LightGBM/Sklearn
    X_df = pd.DataFrame([row], columns=feature_order)

    pred_idx = model.predict(X_df)[0]

    confidence = 1.0

    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X_df)[0]
        confidence = float(np.max(proba))

    decision = encoder.inverse_transform([pred_idx])[0]

    logger.info(
        f"[ModelLoader] Prediction={decision} "
        f"(confidence={confidence:.3f})"
    )

    return decision, confidence


# ============================================================
# Startup Warmup
# ============================================================

def warmup():
    """
    Dipanggil saat startup FastAPI.
    Fail-fast jika model rusak.
    """

    logger.info("[ModelLoader] Warmup started...")

    model, encoder = get_model_and_encoder()

    if model is None:
        raise RuntimeError(
            "Model gagal dimuat."
        )

    if encoder is None:
        raise RuntimeError(
            "Encoder gagal dimuat."
        )

    predict_decision(
        {
            "margin_pct": 0.30,
            "stock_ratio": 0.80,
            "customer_loyalty": 0.50,
            "discount_requested_pct": 0.20,
            "hour_of_day": 14,
            "is_peak_hour": 0,
        }
    )

    logger.info(
        "[ModelLoader] Warmup completed successfully."
    )