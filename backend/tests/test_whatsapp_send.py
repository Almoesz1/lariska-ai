"""
LARISKA AI -- Diagnostic Test: WhatsApp Send Message
Jalankan: python -m tests.test_whatsapp_send
"""
import asyncio
import os
import sys


def main():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

    from app.core.config import settings

    print("\n" + "="*55)
    print("LARISKA AI -- WHATSAPP DIAGNOSTIC TEST")
    print("="*55)

    phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID") or getattr(settings, "whatsapp_phone_number_id", None)
    wa_token = os.getenv("WHATSAPP_TOKEN") or getattr(settings, "whatsapp_token", None)
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN") or getattr(settings, "whatsapp_verify_token", None)
    gemini_key = settings.get_effective_google_api_key()
    gemini_model = settings.gemini_model

    print("\n[INFO] Konfigurasi Aktif:")
    print("  WHATSAPP_PHONE_NUMBER_ID : " + ("OK: " + str(phone_id) if phone_id else "TIDAK ADA -- KRITIS!"))
    print("  WHATSAPP_TOKEN           : " + ("OK: " + wa_token[:16] + "..." if wa_token else "TIDAK ADA -- KRITIS!"))
    print("  WHATSAPP_VERIFY_TOKEN    : " + ("OK: " + str(verify_token) if verify_token else "TIDAK ADA"))
    print("  GEMINI_API_KEY           : " + ("OK (" + gemini_key[:12] + "...)" if gemini_key else "TIDAK ADA -- KRITIS!"))
    print("  GEMINI_MODEL             : " + gemini_model)

    missing = []
    if not phone_id:
        missing.append("WHATSAPP_PHONE_NUMBER_ID")
    if not wa_token:
        missing.append("WHATSAPP_TOKEN")
    if not gemini_key:
        missing.append("GEMINI_API_KEY / GOOGLE_API_KEY")

    if missing:
        print("\n[ERROR] MASALAH KRITIS DITEMUKAN!")
        print("  Env var berikut BELUM diset di backend/.env:")
        for m in missing:
            print("  -> " + m)
        sys.exit(1)

    print("\n[OK] Semua konfigurasi kritis tersedia!")
    print("\n[INPUT] Masukkan nomor WhatsApp tujuan test (format 62xxx, contoh 6285964325731): ", end="")
    test_to_number = input().strip()

    if not test_to_number or not test_to_number.isdigit():
        print("[ERROR] Nomor tidak valid. Format harus berupa angka saja.")
        sys.exit(1)

    test_message = "Halo! Ini pesan test dari LARISKA AI Backend. Jika pesan ini diterima, koneksi WhatsApp Cloud API berhasil!"

    async def run_test():
        from app.services.whatsapp_client import send_text_message
        print("[INFO] Mengirim pesan ke " + test_to_number + "...")
        try:
            result = await send_text_message(test_to_number, test_message)
            msg_id = result.get("messages", [{}])[0].get("id", "unknown")
            print("\n[SUCCESS] Pesan terkirim!")
            print("  Message ID : " + msg_id)
            print("  Response   : " + str(result))
            print("\n  Cek WhatsApp nomor " + test_to_number + " -- pesan harus muncul dalam beberapa detik.")
        except Exception as e:
            print("\n[FAILED] Gagal kirim pesan: " + type(e).__name__ + ": " + str(e))
            raise

    asyncio.run(run_test())


if __name__ == "__main__":
    main()
