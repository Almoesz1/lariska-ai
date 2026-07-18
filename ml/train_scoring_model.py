"""
Sprint 3A — Langkah 3: Training Adaptive Scoring Engine.

Melatih model klasifikasi yang memprediksi aksi negosiasi optimal
(hold_price / discount / bonus / counter_offer) dari 6 fitur bisnis
yang dihasilkan generate_synthetic_data.py (Langkah 2).

Model ini akan dipakai Sprint 5A (Sales Brain Assembly) sebagai bagian dari
Adaptive Scoring Engine. PENTING: prediksi model TIDAK PERNAH langsung jadi
keputusan akhir — selalu dikombinasikan dengan hard business rule
(floor_price) di scoring_engine.py, sesuai proposal Bagian 6.

Output:
- model_artifacts/scoring_model.pkl       (model terlatih saja)
- model_artifacts/label_encoder.pkl       (mapping label <-> integer, terpisah
                                             dari model karena harus dipakai
                                             identik saat inference)
- model_artifacts/training_metadata.json  (metrik evaluasi, feature importance,
                                             dan metadata lengkap lainnya)
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

try:
    from lightgbm import LGBMClassifier

    MODEL_NAME = "LGBMClassifier"
    LIBRARY_NAME = "lightgbm"
    ModelClass = LGBMClassifier
except ImportError:
    from sklearn.ensemble import GradientBoostingClassifier

    MODEL_NAME = "GradientBoostingClassifier"
    LIBRARY_NAME = "scikit-learn (fallback — LightGBM tidak terpasang di environment ini)"
    ModelClass = GradientBoostingClassifier


BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "data" / "synthetic_negotiation_data.csv"
MODEL_DIR = BASE_DIR / "model_artifacts"

FEATURE_COLUMNS = [
    "margin_pct",
    "stock_ratio",
    "customer_loyalty",
    "discount_requested_pct",
    "hour_of_day",
    "is_peak_hour",
]
TARGET_COLUMN = "ai_decision"
RANDOM_STATE = 42
TEST_SIZE = 0.2


# ============================================================
# LOAD & VALIDATE
# ============================================================

def load_dataset() -> pd.DataFrame:
    """Baca dataset + validasi struktur. Gagal cepat dengan pesan jelas
    daripada error samar di tengah training."""
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset tidak ditemukan di: {DATA_PATH}\n"
            "Jalankan dulu: python generate_synthetic_data.py"
        )

    df = pd.read_csv(DATA_PATH)

    if df.empty:
        raise ValueError(f"Dataset di {DATA_PATH} kosong (0 baris). Generate ulang datanya.")

    required_columns = FEATURE_COLUMNS + [TARGET_COLUMN]
    missing_columns = [c for c in required_columns if c not in df.columns]
    if missing_columns:
        raise ValueError(
            f"Kolom berikut tidak ditemukan di dataset: {missing_columns}. "
            "Dataset kemungkinan rusak atau berasal dari versi generate_synthetic_data.py "
            "yang berbeda dari yang dipakai script ini."
        )

    null_counts = df[required_columns].isnull().sum()
    if null_counts.any():
        raise ValueError(
            f"Dataset mengandung nilai kosong (NaN):\n{null_counts[null_counts > 0]}\n"
            "Cek ulang generate_synthetic_data.py — seharusnya tidak menghasilkan NaN."
        )

    return df


# ============================================================
# TRAINING
# ============================================================

def train_and_evaluate(df: pd.DataFrame) -> dict:
    X = df[FEATURE_COLUMNS]
    y_raw = df[TARGET_COLUMN]

    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(y_raw)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )

    model = ModelClass(random_state=RANDOM_STATE)

    start_time = time.perf_counter()
    model.fit(X_train, y_train)
    training_time_seconds = round(time.perf_counter() - start_time, 4)

    y_pred = model.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average="macro", zero_division=0
    )

    report_dict = classification_report(
        y_test, y_pred, target_names=label_encoder.classes_, output_dict=True, zero_division=0
    )
    conf_matrix = confusion_matrix(y_test, y_pred).tolist()

    feature_importance = {}
    if hasattr(model, "feature_importances_"):
        raw_importance = model.feature_importances_
        total = float(raw_importance.sum()) or 1.0  # hindari div-by-zero
        feature_importance = {
            col: round(float(val) / total, 4)
            for col, val in zip(FEATURE_COLUMNS, raw_importance)
        }
        feature_importance = dict(
            sorted(feature_importance.items(), key=lambda item: item[1], reverse=True)
        )

    label_mapping = {
        cls: int(label_encoder.transform([cls])[0]) for cls in label_encoder.classes_
    }

    print(f"Model      : {MODEL_NAME} ({LIBRARY_NAME})")
    print(f"Training time: {training_time_seconds}s")
    print(f"Accuracy   : {accuracy:.4f}")
    print(f"Precision  : {precision:.4f} (macro)")
    print(f"Recall     : {recall:.4f} (macro)")
    print(f"F1-score   : {f1:.4f} (macro)")
    print("\nFeature importance (ternormalisasi, urut dari paling berpengaruh):")
    for feat, importance in feature_importance.items():
        print(f"  {feat:<24s} {importance:.4f}")
    print("\nClassification report:")
    print(classification_report(y_test, y_pred, target_names=label_encoder.classes_, zero_division=0))
    print("Confusion matrix (baris=aktual, kolom=prediksi):")
    print(pd.DataFrame(
        conf_matrix,
        index=[f"actual_{c}" for c in label_encoder.classes_],
        columns=[f"pred_{c}" for c in label_encoder.classes_],
    ))

    return {
        "model": model,
        "label_encoder": label_encoder,
        "accuracy": round(float(accuracy), 4),
        "precision_macro": round(float(precision), 4),
        "recall_macro": round(float(recall), 4),
        "f1_macro": round(float(f1), 4),
        "classification_report": report_dict,
        "confusion_matrix": conf_matrix,
        "feature_importance": feature_importance,
        "label_mapping": label_mapping,
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
        "training_time_seconds": training_time_seconds,
    }


# ============================================================
# SAVE ARTIFACTS
# ============================================================

def save_artifacts(result: dict, dataset_rows: int) -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    try:
        joblib.dump(result["model"], MODEL_DIR / "scoring_model.pkl")
    except Exception as exc:
        raise RuntimeError(f"Gagal menyimpan scoring_model.pkl: {exc}") from exc

    try:
        joblib.dump(result["label_encoder"], MODEL_DIR / "label_encoder.pkl")
    except Exception as exc:
        raise RuntimeError(f"Gagal menyimpan label_encoder.pkl: {exc}") from exc

    metadata = {
        "model_name": MODEL_NAME,
        "library": LIBRARY_NAME,
        "dataset_rows": dataset_rows,
        "train_size": result["train_size"],
        "test_size": result["test_size"],
        "training_time_seconds": result["training_time_seconds"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "random_state": RANDOM_STATE,
        "test_split_ratio": TEST_SIZE,
        "feature_names": FEATURE_COLUMNS,
        "label_mapping": result["label_mapping"],
        "accuracy": result["accuracy"],
        "precision_macro": result["precision_macro"],
        "recall_macro": result["recall_macro"],
        "f1_macro": result["f1_macro"],
        "classification_report": result["classification_report"],
        "confusion_matrix": result["confusion_matrix"],
        "feature_importance": result["feature_importance"],
        "note": (
            "Dilatih dari data SINTETIS berbasis heuristik bisnis (lihat "
            "generate_synthetic_data.py), bukan data transaksi riil UMKM. "
            "Roadmap: retrain berkala dari negotiation_logs asli setelah "
            "data produksi terkumpul cukup banyak."
        ),
    }

    try:
        with open(MODEL_DIR / "training_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
    except Exception as exc:
        raise RuntimeError(f"Gagal menyimpan training_metadata.json: {exc}") from exc


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    df = load_dataset()
    result = train_and_evaluate(df)
    save_artifacts(result, dataset_rows=len(df))

    print(f"\nArtefak tersimpan di: {MODEL_DIR}")
    print("  - scoring_model.pkl")
    print("  - label_encoder.pkl")
    print("  - training_metadata.json")
    print(
        "\nCATATAN: gunakan angka evaluasi ini apa adanya di proposal Bagian 8 — "
        "jangan dibulatkan ke atas atau dipoles."
    )


if __name__ == "__main__":
    main()