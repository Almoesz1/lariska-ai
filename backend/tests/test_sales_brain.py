import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 1. Pastikan folder 'backend' masuk ke sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# 2. Coba muat file .env dari folder backend atau root jika ada
env_backend = BACKEND_DIR / ".env"
env_root = BACKEND_DIR.parent / ".env"

if env_backend.exists():
    load_dotenv(env_backend)
elif env_root.exists():
    load_dotenv(env_root)

# 3. Fallback Mock Environment (Mencegah Pydantic Settings ValidationError)
os.environ.setdefault("SUPABASE_URL", "https://mock.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "mock-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "mock-service-role-key")
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lariska")
os.environ.setdefault("APP_SECRET_KEY", "super-secret-key-for-testing-12345678")

# BARU IMPORT APP SETELAH ENVIRONMENT DILENGKAPI
from app.pipeline.sales_brain import (
    run_scoring_engine,
    classify_emotion,
    generate_sales_response,
    model_warmup,
)


def main():
    print("==========================================")
    print("🚀 TESTING SALES BRAIN PIPELINE (SPRINT 5A)")
    print("==========================================\n")

    # 1. Test Warmup Model ML
    print("1️⃣ Memuat & Warmup Model ML...")
    model_warmup()
    print("✅ Model ML & Encoder siap di memori!\n")

    # 2. Test Scoring Engine + Guardrails
    print("2️⃣ Simulasi Negosiasi (Scoring Engine + Guardrails)...")
    sample_features = {
        "margin_pct": 0.30,            # Margin 30%
        "stock_ratio": 0.80,           # Stok masih 80%
        "customer_loyalty": 0.70,      # Pelanggan lumayan loyal
        "discount_requested_pct": 0.15, # Minta diskon 15%
        "hour_of_day": 14,             # Jam 14:00
        "is_peak_hour": 0,
    }

    score_res = run_scoring_engine(
        features=sample_features,
        product_price=100000,
        floor_price=80000,
        max_discount_pct=0.25,
    )

    print("   📊 Hasil Scoring Engine:")
    for key, val in score_res.items():
        print(f"      - {key:<20}: {val}")
    print()

    # 3. Test Emotion Classifier & Response Generator
    print("3️⃣ Analisis Emosi & Generate Balasan Sales...")
    user_msg = "Bisa diskon dikit ga kak? Pengen order cepat nih!"
    print(f"   💬 Pesan Pembeli: \"{user_msg}\"")

    emotion = classify_emotion(user_msg)
    print(f"   🎭 Emosi Terdeteksi: {emotion.emotion.value} (confidence={emotion.confidence})")
    print(f"   💡 Tone Hint: {emotion.tone_hint}")

    reply = generate_sales_response(
        decision_result=score_res,
        product_name="Sepatu Sneakers Local",
        emotion_info=emotion,
        user_message=user_msg,
    )

    print(f"\n   🤖 Balasan AI WhatsApp:\n   \"{reply}\"")
    print("\n==========================================")
    print("✅ SEMUA KOMPONEN SALES BRAIN BERJALAN NORMAL!")
    print("==========================================")


if __name__ == "__main__":
    main()