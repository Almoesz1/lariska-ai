"""
LARISKA AI — Sprint 5A
Model Loader — Adaptive Scoring Engine

Load model LightGBM (scoring_model.pkl) dan LabelEncoder (label_encoder.pkl)
dari artefak hasil training Sprint 3A. 

Model di-load SEKALI saat server start (lazy singleton) — tidak ditraining ulang saat runtime.
Ini sesuai proposal Bab 6: "saat live, model ini di-inference (bukan training ulang)".

Path model: ml/model_artifacts/ (relatif dari root project)
"""

import logging
import os
import pickle
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ============================================================
# Path resolution
# ============================================================

# Root project: d:/Project/lariska-ai/
# File ini ada di: backend/app/pipeline/sales_brain/model_loader.py
# Model ada di:   ml/model_artifacts/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent  # 5 level up
_MODEL_DIR = _PROJECT_ROOT / "ml" / "model_artifacts"

MODEL_PATH = _MODEL_DIR / "scoring_model.pkl"
ENCODER_PATH = _MODEL_DIR / "label_encoder.pkl"

# Lazy singletons
_model = None
_encoder = None


def _load_model():
    """Load LightGBM model dari .pkl file."""
    global _model
    if _model is not None:
        return _model

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"[ModelLoader] scoring_model.pkl tidak ditemukan di {MODEL_PATH}. "
            "Jalankan ml/train_scoring_model.py terlebih dahulu."
        )

    logger.info(f"[ModelLoader] Loading scoring model dari {MODEL_PATH}...")
    with open(MODEL_PATH, "rb") as f:
        _model = pickle.load(f)
    logger.info(f"[ModelLoader] Model loaded: {type(_model).__name__}")
    return _model


def _load_encoder():
    """Load LabelEncoder dari .pkl file."""
    global _encoder
    if _encoder is not None:
        return _encoder

    if not ENCODER_PATH.exists():
        raise FileNotFoundError(
            f"[ModelLoader] label_encoder.pkl tidak ditemukan di {ENCODER_PATH}."
        )

    logger.info(f"[ModelLoader] Loading label encoder dari {ENCODER_PATH}...")
    with open(ENCODER_PATH, "rb") as f:
        _encoder = pickle.load(f)
    logger.info(f"[ModelLoader] Encoder classes: {list(_encoder.classes_)}")
    return _encoder


def get_model_and_encoder():
    """
    Public API — ambil model + encoder yang sudah di-load.
    Keduanya di-cache setelah load pertama.
    """
    model = _load_model()
    encoder = _load_encoder()
    return model, encoder


def predict_decision(features: list[float]) -> tuple[str, float]:
    """
    Jalankan inferensi model untuk satu baris fitur.

    Args:
        features: List 6 nilai sesuai urutan feature_names di training_metadata.json:
                  [margin_pct, stock_ratio, customer_loyalty,
                   discount_requested_pct, hour_of_day, is_peak_hour]

    Returns:
        Tuple (decision_label: str, confidence: float)
        decision_label adalah salah satu dari: 'hold_price', 'discount', 'bonus', 'counter_offer'
    """
    model, encoder = get_model_and_encoder()

    X = np.array(features).reshape(1, -1)
    pred_idx = model.predict(X)[0]
    proba = model.predict_proba(X)[0]
    confidence = float(proba.max())

    # Decode label index → string
    decision = encoder.inverse_transform([pred_idx])[0]

    logger.info(
        f"[ModelLoader] Prediction: {decision} (confidence={confidence:.3f}) | "
        f"features={[round(f, 3) for f in features]}"
    )
    return decision, confidence


def warmup():
    """
    Pre-load model saat server startup — panggil dari main.py @app.on_event('startup').
    Menghindari cold start di request pertama.
    """
    try:
        get_model_and_encoder()
        # Test prediction dengan dummy features
        predict_decision([0.3, 0.8, 0.5, 0.2, 14, 0])
        logger.info("[ModelLoader] Model warmup completed successfully.")
    except Exception as exc:
        logger.error(f"[ModelLoader] Warmup failed (non-fatal): {exc}")
