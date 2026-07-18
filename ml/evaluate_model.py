"""
Sprint 3A — Langkah 3: Evaluate & Validate Adaptive Scoring Engine.

Tanggung jawab file ini BERBEDA dari train_scoring_model.py:
- train_scoring_model.py MENCIPTAKAN artefak (model, encoder, metadata)
- evaluate_model.py MEMVALIDASI artefak itu bisa dimuat ulang dan dipakai —
  ini adalah simulasi persis dari apa yang akan dilakukan
  backend/app/pipeline/sales_brain/model_loader.py di Sprint 5A.

Jalankan file ini SETELAH train_scoring_model.py berhasil.
"""

from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

BASE_DIR = Path(__file__).parent
MODEL_PATH = BASE_DIR / "model_artifacts" / "scoring_model.pkl"
ENCODER_PATH = BASE_DIR / "model_artifacts" / "label_encoder.pkl"
DATA_PATH = BASE_DIR / "data" / "synthetic_negotiation_data.csv"

FEATURE_COLUMNS = [
    "margin_pct",
    "stock_ratio",
    "customer_loyalty",
    "discount_requested_pct",
    "hour_of_day",
    "is_peak_hour",
]
TARGET_COLUMN = "ai_decision"

# HARUS identik dengan train_scoring_model.py — supaya test set yang
# dihasilkan di sini PERSIS SAMA dengan test set saat training (data yang
# belum pernah dilihat model saat fit()), bukan data training yang dievaluasi
# ulang secara curang.
RANDOM_STATE = 42
TEST_SIZE = 0.2


def load_artifacts():
    """Simulasi persis apa yang akan dilakukan model_loader.py Sprint 5A."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"{MODEL_PATH} tidak ditemukan. Jalankan train_scoring_model.py dulu."
        )
    if not ENCODER_PATH.exists():
        raise FileNotFoundError(
            f"{ENCODER_PATH} tidak ditemukan. Jalankan train_scoring_model.py dulu."
        )

    try:
        model = joblib.load(MODEL_PATH)
    except Exception as exc:
        raise RuntimeError(
            f"scoring_model.pkl ada tapi gagal dimuat (kemungkinan file korup "
            f"atau versi library beda dari saat training): {exc}"
        ) from exc

    try:
        label_encoder = joblib.load(ENCODER_PATH)
    except Exception as exc:
        raise RuntimeError(f"label_encoder.pkl ada tapi gagal dimuat: {exc}") from exc

    return model, label_encoder


def re_evaluate(model, label_encoder) -> None:
    """Evaluasi ulang model terhadap test set yang sama seperti saat training,
    untuk membuktikan hasil training_metadata.json bisa direproduksi, bukan
    angka yang cuma sekali muncul lalu tidak konsisten."""
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"{DATA_PATH} tidak ditemukan.")

    df = pd.read_csv(DATA_PATH)
    X = df[FEATURE_COLUMNS]

    try:
        y = label_encoder.transform(df[TARGET_COLUMN])
    except ValueError as exc:
        raise ValueError(
            "LabelEncoder mismatch — dataset punya label yang tidak dikenal "
            f"encoder yang tersimpan. Kemungkinan dataset sudah diganti setelah "
            f"training terakhir. Detail: {exc}"
        ) from exc

    _, X_test, _, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )

    y_pred = model.predict(X_test)

    print("=== Evaluasi Ulang (test set identik dengan saat training) ===\n")
    print("Confusion Matrix:")
    print(pd.DataFrame(
        confusion_matrix(y_test, y_pred),
        index=[f"actual_{c}" for c in label_encoder.classes_],
        columns=[f"pred_{c}" for c in label_encoder.classes_],
    ))
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=label_encoder.classes_, zero_division=0))


def demo_single_prediction(model, label_encoder) -> None:
    """Bukti bahwa model bisa dipakai untuk 1 prediksi tunggal — ini pola
    yang PERSIS akan dipakai scoring_engine.py saat 1 pesan pelanggan masuk
    secara real-time di Sprint 5A."""
    example_case = pd.DataFrame([{
        "margin_pct": 0.30,             # margin 30% dari harga jual
        "stock_ratio": 0.8,             # stok masih banyak
        "customer_loyalty": 0.7,        # pelanggan cukup loyal
        "discount_requested_pct": 0.15, # pelanggan minta diskon 15%
        "hour_of_day": 14,
        "is_peak_hour": 0,
    }])

    predicted_encoded = model.predict(example_case)[0]
    predicted_label = label_encoder.inverse_transform([predicted_encoded])[0]

    print("\n=== Demo Prediksi Tunggal (simulasi 1 pesan nego real-time) ===")
    print("Input:", example_case.to_dict(orient="records")[0])
    print(f"Prediksi aksi: {predicted_label}")

    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(example_case)[0]
        proba_map = {
            label_encoder.inverse_transform([i])[0]: round(float(p), 4)
            for i, p in enumerate(proba)
        }
        print("Confidence per kelas:", proba_map)


def main() -> None:
    model, label_encoder = load_artifacts()
    print(f"Artefak berhasil dimuat ulang. Kelas label: {list(label_encoder.classes_)}\n")

    re_evaluate(model, label_encoder)
    demo_single_prediction(model, label_encoder)

    print("\nSemua validasi selesai — model_loader.py Sprint 5A bisa memakai pola yang sama persis.")


if __name__ == "__main__":
    main()