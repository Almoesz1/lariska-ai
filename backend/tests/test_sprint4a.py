"""
Script Pengujian Sprint 4A — STT, Intent/Entity, State Tracking

Menjalankan pengujian terisolasi untuk 3 modul awal AI Pipeline:
1. Intent & Entity Extraction (Gemini)
2. State Tracking (Supabase DB integration)
3. Whisper STT (opsional jika audio file tersedia)

Jalankan dengan perintah:
cd backend
python -m tests.test_sprint4a
"""

import sys
import os
import logging

# Pastikan path backend masuk sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.pipeline.intent_entity import extract_intent_entity
from app.pipeline.state_tracking import build_context, save_message
from app.services.supabase_client import get_supabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestSprint4A")

def test_sprint_4a():
    print("\n==========================================")
    print("=== TESTING SPRINT 4A: STT, INTENT, STATE TRACKING ===")
    print("==========================================\n")

    # Sample input teks simulasi pesan WhatsApp
    sample_messages = [
        "Halo kak, mau tanya dong kemeja batik ukurannya ready gak?",
        "Bisa kurang gak kak harganya? Kalau Rp 150.000 boleh?",
        "Oke deh aku mau beli 1 pcs mas, tolong invoice ya."
    ]

    test_wa_number = "6281299998888"  # Nomor simulasi testing
    supabase = get_supabase()

    for idx, msg_text in enumerate(sample_messages, 1):
        print(f"\n--- [Uji #{idx}] Input Pesan: \"{msg_text}\" ---")

        # 1. Test Intent & Entity Extraction
        print("1. Testing Intent & Entity Extraction (Gemini)...")
        intent_res = extract_intent_entity(msg_text)
        print(f"   -> Intent: {intent_res.intent.value}")
        print(f"   -> Entities: {intent_res.entities.model_dump()}")
        print(f"   -> Confidence: {intent_res.confidence}")

        # 2. Test State Tracking (Database Supabase)
        print("2. Testing State Tracking & Database Context...")
        context = build_context(supabase, test_wa_number, intent_res)
        print(f"   -> Customer ID: {context.customer_id}")
        print(f"   -> Conversation ID: {context.conversation_id}")
        print(f"   -> Total Order Customer: {context.total_orders}")
        print(f"   -> Product Identified: {context.product_name} (Price: {context.product_price})")

        # 3. Simpan Pesan ke DB
        saved_msg = save_message(
            supabase=supabase,
            conversation_id=context.conversation_id,
            sender_type="customer",
            content_type="text",
            raw_text=msg_text,
            intent=intent_res.intent.value,
            entities=intent_res.entities.model_dump()
        )
        print(f"   -> Message Saved to DB! Message ID: {saved_msg['id']}")

    print("\n==========================================")
    print("=== TEST SPRINT 4A SELESAI ===")
    print("==========================================\n")

if __name__ == "__main__":
    test_sprint_4a()
