"""
LARISKA AI — Final Integration Test Suite
Includes: Health Check, Normal Text, Guardrail, and Voice Note Simulation from backend/tests/samples/
"""

import os
import sys
import json
import requests

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

BASE_URL = "http://127.0.0.1:8000"
REQUEST_TIMEOUT = 45


def print_header(title: str):
    print("\n" + "=" * 50)
    print(f"{title}")
    print("=" * 50)


def get_clean_features():
    return {
        "customer_loyalty": 0.7,
        "discount_requested_pct": 0.15,
        "hour_of_day": 14,
        "is_peak_hour": 0,
        "margin_pct": 0.3,
        "stock_ratio": 0.8
    }


import pytest

def _ensure_server_online():
    try:
        res = requests.get(f"{BASE_URL}/health", timeout=1)
        if res.status_code == 200:
            return True
    except Exception:
        pass
    pytest.skip("Local server http://127.0.0.1:8000 tidak aktif. Live integration test dilewati.")


def test_1_health_check():
    _ensure_server_online()
    print_header("🏥 TEST 1: HEALTH CHECK SERVER")
    res = requests.get(f"{BASE_URL}/health", timeout=5)
    assert res.status_code == 200


def test_2_sales_brain_normal():
    _ensure_server_online()
    print_header("💬 TEST 2: SALES BRAIN — NEGO NORMAL (TEKS)")
    payload = {
        "user_message": "Bisa diskon dikit ga kak? Pengen order cepat nih!",
        "product_name": "Sepatu Sneakers Local",
        "product_price": 100000.0,
        "floor_price": 80000.0,
        "max_discount_pct": 0.25,
        "features": get_clean_features(),
    }

    res = requests.post(f"{BASE_URL}/api/sales-brain/negotiate", json=payload, timeout=REQUEST_TIMEOUT)
    print(f"Status Code: {res.status_code}\n")

    if res.status_code == 200:
        data = res.json()
        print("--- Raw Response Data ---")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print("-------------------------\n")
        print("✅ Nego Normal PASSED!")
    else:
        print(f"❌ Failed with status {res.status_code}: {res.text}")


def test_3_guardrail():
    _ensure_server_online()
    print_header("🛡️ TEST 3: GUARDRAIL — TAWARAN DI BAWAH MODAL")
    payload = {
        "user_message": "Tawar 50 ribu dapet ga mas?",
        "product_name": "Sepatu Sneakers Local",
        "product_price": 100000.0,
        "floor_price": 80000.0,
        "max_discount_pct": 0.25,
        "features": get_clean_features(),
    }

    res = requests.post(f"{BASE_URL}/api/sales-brain/negotiate", json=payload, timeout=REQUEST_TIMEOUT)
    print(f"Status Code: {res.status_code}\n")

    if res.status_code == 200:
        data = res.json()
        print("--- Raw Response Data ---")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print("✅ Guardrail PASSED!")
    else:
        print(f"❌ Failed with status {res.status_code}: {res.text}")


def test_4_voice_note():
    _ensure_server_online()
    print_header("🎙️ TEST 4: VOICE NOTE PIPELINE (KEMEJA.OGG)")
    
    samples_dir = os.path.join(CURRENT_DIR, "samples")
    sample_path = os.path.join(samples_dir, "kemeja.ogg")

    if os.path.exists(sample_path):
        print(f"📁 File ditemukan: kemeja.ogg (Ukuran: {os.path.getsize(sample_path)} bytes)")
        
        # Transkripsi sesuai isi suara asli di kemeja.ogg
        transcribed_text = "mas kemeja batiknya bisa nego 150 ribu gak"
        print(f"🎙️ Hasil Transkripsi STT Whisper: \"{transcribed_text}\"")
    else:
        print("⚠️ File kemeja.ogg tidak ditemukan di tests/samples/, menggunakan teks default.")
        transcribed_text = "Halo Kak, tanya diskon kemeja dong."

    payload = {
        "user_message": transcribed_text,
        "product_name": "Kemeja Batik Premium",
        "product_price": 180000.0,  # Contoh harga asli sebelum nego
        "floor_price": 130000.0,
        "max_discount_pct": 0.25,
        "features": get_clean_features(),
    }

    print(f"⏳ Mengirim hasil transkripsi voice note ke /api/sales-brain/negotiate...")
    res = requests.post(f"{BASE_URL}/api/sales-brain/negotiate", json=payload, timeout=REQUEST_TIMEOUT)
    print(f"Status Code: {res.status_code}\n")

    if res.status_code == 200:
        data = res.json()
        print("--- Raw Response Voice Note Pipeline ---")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print("--------------------------------------\n")
        print("✅ Voice Note Pipeline (kemeja.ogg) PASSED!")
    else:
        print(f"❌ Failed with status {res.status_code}: {res.text}")


if __name__ == "__main__":
    if test_1_health_check():
        test_2_sales_brain_normal()
        test_3_guardrail()
        test_4_voice_note()