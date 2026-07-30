"""
LARISKA AI — Sprint 5A (QA Patch)
Model Loader — Adaptive Scoring Engine

Perubahan:
- FIX CRITICAL (C1): joblib.load() digunakan untuk membaca artefak
  yang dibuat oleh train_scoring_model.py (joblib.dump()).
- FIX FEATURE NAMES WARNING: Mengubah input NumPy Array menjadi pandas.DataFrame
  dengan kolom yang sesuai feature_order untuk menghilangkan UserWarning dari Sklearn/LightGBM.
- FIX PYDANTIC INPUT: predict_decision() sekarang mendukung input dict maupun objek ScoringInput.
- Feature order dibaca dari training_metadata.json.
- Warmup fail-fast.
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
    Ambil urutan fitur yang dipakai saat training.
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
    Args:
        features: dict atau objek ScoringInput yang berisi:
        {
            margin_pct,
            stock_ratio,
            customer_loyalty,
            discount_requested_pct,
            hour_of_day,
            is_peak_hour
        }

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
        if feature_name not in feat_dict:
            raise ValueError(
                f"Feature '{feature_name}' tidak ditemukan."
            )
        row[feature_name] = feat_dict[feature_name]

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