"""
Script Pengujian Sprint 4A — STT, Intent/Entity, State Tracking

Perubahan dari versi awal setelah Quality Gate review:
- Tambah pesan #4 (greeting) — kasus yang paling sering muncul di awal
  demo nyata, dan yang sebelumnya BERISIKO memicu bug C1 kalau sampai ke
  save_negotiation_log() tanpa guard.
- Tambah blok test eksplisit untuk save_negotiation_log() — SEBELUMNYA
  fungsi ini sama sekali tidak pernah dites di sini, jadi bug C1 (ai_decision
  'no_nego' melanggar CHECK constraint negotiation_logs) tidak akan pernah
  ketahuan dari script ini. Sekarang ada test yang membuktikan guard-nya
  bekerja: percobaan simpan 'no_nego' harus di-skip (bukan crash).

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

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.pipeline.intent_entity import extract_intent_entity
from app.pipeline.state_tracking import build_context, save_message, save_negotiation_log
from app.services.supabase_client import get_supabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestSprint4A")


def test_sprint_4a():
    print("\n==========================================")
    print("=== TESTING SPRINT 4A: STT, INTENT, STATE TRACKING ===")
    print("==========================================\n")

    sample_messages = [
        "Halo kak, mau tanya dong kemeja batik ukurannya ready gak?",
        "Bisa kurang gak kak harganya? Kalau Rp 150.000 boleh?",
        "Oke deh aku mau beli 1 pcs mas, tolong invoice ya.",
        # Kasus greeting murni — paling sering muncul di awal demo nyata,
        # dan intent-nya HARUS jadi 'greeting' (bukan 'nego') supaya guard
        # C1 di save_negotiation_log() punya kasus nyata untuk diuji.
        "Halo min",
    ]

    test_wa_number = "6281299998888"
    supabase = get_supabase()

    for idx, msg_text in enumerate(sample_messages, 1):
        print(f"\n--- [Uji #{idx}] Input Pesan: \"{msg_text}\" ---")

        print("1. Testing Intent & Entity Extraction (Gemini)...")
        intent_res = extract_intent_entity(msg_text)
        print(f"   -> Intent: {intent_res.intent.value}")
        print(f"   -> Entities: {intent_res.entities.model_dump()}")
        print(f"   -> Confidence: {intent_res.confidence}")

        print("2. Testing State Tracking & Database Context...")
        context = build_context(supabase, test_wa_number, intent_res)
        print(f"   -> Customer ID: {context.customer_id}")
        print(f"   -> Conversation ID: {context.conversation_id}")
        print(f"   -> Total Order Customer: {context.total_orders}")
        print(f"   -> Product Identified: {context.product_name} (Price: {context.product_price})")

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

    # ============================================================
    # TEST KHUSUS: Guard C1 — save_negotiation_log() dengan ai_decision
    # yang TIDAK valid untuk CHECK constraint database (no_nego).
    # Sebelum patch, ini akan mencoba INSERT dan Supabase/Postgres akan
    # menolak dengan constraint violation -> request gagal.
    # Setelah patch, fungsi ini harus SKIP insert dan return dict kosong.
    # ============================================================
    print("\n--- [Uji Khusus] Guard C1: save_negotiation_log dengan ai_decision='no_nego' ---")
    result = save_negotiation_log(
        supabase=supabase,
        conversation_id=context.conversation_id,
        product_id=context.product_id or "00000000-0000-0000-0000-000000000000",
        customer_offer_price=None,
        ai_decision="no_nego",
        ai_offer_price=None,
        floor_price_snapshot=0,
    )
    assert result == {}, (
        f"GAGAL: save_negotiation_log('no_nego') seharusnya di-skip (dict kosong), "
        f"tapi malah mengembalikan: {result}. Guard C1 TIDAK berfungsi — "
        f"kemungkinan CHECK constraint di database akan menolak insert ini."
    )
    print("   -> PASS: 'no_nego' berhasil di-skip, TIDAK dikirim ke database.")

    print("\n==========================================")
    print("=== TEST SPRINT 4A SELESAI — SEMUA ASSERTION LOLOS ===")
    print("==========================================\n")


if __name__ == "__main__":
    test_sprint_4a()