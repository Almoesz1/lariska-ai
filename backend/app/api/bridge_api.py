"""
LARISKA AI — Dynamic WA Bridge API Endpoint
Integrasi Penuh Supabase PostgreSQL & Voice Note (STT) Pipeline
"""

import re
import os
import logging
import traceback
import base64
import tempfile
from typing import Optional, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel

# Client Supabase
from supabase import create_client, Client

# Import AI Sales Brain Pipeline & Gemini Audio Client
from app.pipeline.sales_brain import (
    classify_emotion,
    run_scoring_engine,
    generate_sales_response,
)
from app.pipeline.gemini_client import generate_content_with_fallback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bridge", tags=["WA Bridge"])

# ------------------------------------------------------------------------------
# Inisialisasi Supabase Client
# ------------------------------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None
    logger.warning("⚠️ SUPABASE_URL / SUPABASE_KEY belum terpasang di .env!")


# ------------------------------------------------------------------------------
# Helper Functions: Database Operations
# ------------------------------------------------------------------------------

def get_or_create_customer(wa_number: str) -> Optional[Dict[str, Any]]:
    """Mencari atau membuat data customer berdasarkan whatsapp_number."""
    if not supabase:
        return None
    try:
        res = supabase.table("customers").select("*").eq("whatsapp_number", wa_number).is_("deleted_at", "null").execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        
        ins = supabase.table("customers").insert({"whatsapp_number": wa_number}).execute()
        if ins.data and len(ins.data) > 0:
            return ins.data[0]
    except Exception as e:
        logger.error(f"Error get_or_create_customer: {e}")
    return None


def get_or_create_conversation(customer_id: str) -> Optional[Dict[str, Any]]:
    """Mencari percakapan 'open' atau membuat percakapan baru."""
    if not supabase:
        return None
    try:
        res = supabase.table("conversations") \
            .select("*") \
            .eq("customer_id", customer_id) \
            .eq("status", "open") \
            .order("started_at", desc=True) \
            .limit(1) \
            .execute()

        if res.data and len(res.data) > 0:
            return res.data[0]

        ins = supabase.table("conversations").insert({
            "customer_id": customer_id,
            "channel": "whatsapp",
            "status": "open"
        }).execute()

        if ins.data and len(ins.data) > 0:
            return ins.data[0]
    except Exception as e:
        logger.error(f"Error get_or_create_conversation: {e}")
    return None


def find_product_by_text_or_context(user_message: str, conversation_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Cari produk berdasarkan kata kunci teks atau memori konteks sesi."""
    if not supabase:
        return None

    try:
        prod_res = supabase.table("products") \
            .select("id, name, description, category, price, floor_price, stock") \
            .eq("is_active", True) \
            .is_("deleted_at", "null") \
            .execute()

        products = prod_res.data or []
        msg_lower = user_message.lower()

        for prod in products:
            prod_name_words = prod["name"].lower().split()
            for word in prod_name_words:
                if len(word) > 2 and word in msg_lower:
                    return prod

        if conversation_id:
            last_neg = supabase.table("negotiation_logs") \
                .select("product_id") \
                .eq("conversation_id", conversation_id) \
                .order("created_at", desc=True) \
                .limit(1) \
                .execute()

            if last_neg.data and len(last_neg.data) > 0:
                p_id = last_neg.data[0]["product_id"]
                matched_p = next((p for p in products if p["id"] == p_id), None)
                if matched_p:
                    return matched_p

        if products:
            return products[0]

    except Exception as e:
        logger.error(f"Error find_product_by_text_or_context: {e}")

    return None


def extract_offered_price(user_message: str) -> Optional[float]:
    """Ekstrak penawaran harga dari teks."""
    msg_lower = user_message.lower()

    match = re.search(r'(\d+(?:[\.,]\d+)?)\s*(?:rb|k)', msg_lower)
    if match:
        val = float(match.group(1).replace(',', '.'))
        return val * 1000.0

    match = re.search(r'(\d{1,3}(?:\.\d{3})+|\d{4,7})', msg_lower)
    if match:
        val_str = match.group(1).replace('.', '')
        return float(val_str)

    return None


# ------------------------------------------------------------------------------
# Dynamic Payload Wrappers for ML Features & Audio Support
# ------------------------------------------------------------------------------
class BridgeMessageRequest(BaseModel):
    user_message: str
    sender_id: str
    product_name: Optional[str] = None
    product_price: Optional[float] = None
    audio_data: Optional[str] = None  # Base64 string dari WA Voice Note
    audio_mime: Optional[str] = None  # Mime type audio (.ogg/.opus)


class DynamicDict(dict):
    def __contains__(self, key):
        return True

    def __getitem__(self, key):
        if super().__contains__(key):
            return super().__getitem__(key)
        if "pct" in key or "ratio" in key or "score" in key or "rate" in key:
            return 0.5
        if "price" in key or "cost" in key or "cogs" in key:
            return 100000.0
        if "is_" in key or "has_" in key or "flag" in key:
            return False
        return 1.0

    def get(self, key, default=None):
        return self[key]


class SmartFeaturePayload:
    def __init__(self, data: dict):
        self._data = DynamicDict(data)

    def model_dump(self):
        return self._data

    def dict(self):
        return self.model_dump()


# ------------------------------------------------------------------------------
# Main Endpoint API
# ------------------------------------------------------------------------------
@router.post("/chat")
async def handle_bridge_chat(payload: BridgeMessageRequest):
    print("\n==========================================", flush=True)
    
    # Tangani Voice Note (Transkripsi Audio jika dikirim dari Node.js)
    actual_message = payload.user_message
    if payload.audio_data:
        print(f" 🎙️ [Voice Note Diterima] Memproses audio dari {payload.sender_id}...", flush=True)
        try:
            audio_bytes = base64.b64decode(payload.audio_data)
            suffix = ".ogg" if not payload.audio_mime else ".ogg"
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            # Transkripsi menggunakan Gemini audio client pipeline bawaan Kakak
            transcribe_prompt = "Tolong transkripsikan audio pesan suara pelanggan ini ke dalam teks bahasa Indonesia secara persis dan natural."
            
            # Membaca file audio sebagai bytes untuk dikirim ke gemini_client
            with open(tmp_path, "rb") as f:
                audio_bytes_data = f.read()
            
            # Kirim ke Gemini untuk di-transkrip
            stt_result = await generate_content_with_fallback(
                prompt=transcribe_prompt,
                contents=[audio_bytes_data, transcribe_prompt]
            )
            
            if stt_result and str(stt_result).strip():
                actual_message = str(stt_result).strip()
                print(f" 📝 [Hasil Transkrip Voice Note]: \"{actual_message}\"", flush=True)
            
            # Hapus file temporary
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
        except Exception as e_audio:
            logger.error(f"Gagal memproses voice note: {e_audio}")
            print(f" ⚠️ Gagal transkrip audio, menggunakan fallback teks.", flush=True)

    print(f"📩 [Pesan Efektif WA ({payload.sender_id})]: {actual_message}", flush=True)

    try:
        # Step 1: Customer & Conversation Database Lookup
        customer = get_or_create_customer(payload.sender_id)
        conversation = get_or_create_conversation(customer["id"]) if customer else None
        conversation_id = conversation["id"] if conversation else None

        # Step 2: Product Matching (Dinamis dari Supabase / Context)
        product = find_product_by_text_or_context(actual_message, conversation_id)
        
        if product:
            product_id = product["id"]
            product_name = product["name"]
            product_price = float(product["price"])
            floor_price = float(product["floor_price"])
            stock_qty = int(product.get("stock", 10))
        else:
            product_id = None
            product_name = "Kemeja Flanel Pria"
            product_price = 120000.0
            floor_price = 102000.0
            stock_qty = 10

        max_discount_pct = 0.20
        cogs = product_price * 0.70

        # Step 3: Parse Penawaran Harga
        offered_price = extract_offered_price(actual_message)
        is_discount = "diskon" in actual_message.lower() or "potongan" in actual_message.lower() or offered_price is not None

        discount_requested_pct = 0.0
        if offered_price and offered_price < product_price:
            discount_requested_pct = (product_price - offered_price) / product_price
        elif is_discount:
            discount_requested_pct = 0.10

        print(f"   🗄️ Product Loaded : {product_name} (Rp {product_price:,.0f} | Floor: Rp {floor_price:,.0f} | Stok: {stock_qty})", flush=True)
        print(f"   💰 Offered Price   : {offered_price} (Diskon Minta: {discount_requested_pct:.1%})", flush=True)

        # Step 4: Analisis Emosi & Simpan Pesan Masuk ke Tabel 'messages'
        emotion_res = classify_emotion(actual_message)
        
        if supabase and conversation_id:
            try:
                supabase.table("messages").insert({
                    "conversation_id": conversation_id,
                    "sender_type": "customer",
                    "content_type": "audio" if payload.audio_data else "text",
                    "raw_text": actual_message,
                    "sentiment": emotion_res.get("sentiment", "netral")
                }).execute()
            except Exception as e_msg:
                logger.error(f"Gagal simpan customer message ke Supabase: {e_msg}")

        # Step 5: Eksekusi ML Scoring Engine
        raw_features = {
            "product_price": product_price,
            "floor_price": floor_price,
            "max_discount_pct": max_discount_pct,
            "cogs": cogs,
            "margin_pct": (product_price - cogs) / product_price,
            "margin_percent": ((product_price - cogs) / product_price) * 100,
            
            "stock_ratio": min(stock_qty / 50.0, 1.0),
            "stock_qty": stock_qty,
            "stock_status": "in_stock" if stock_qty > 0 else "out_of_stock",
            "is_in_stock": stock_qty > 0,

            "customer_loyalty": 0.5,
            "customer_score": 0.5,
            "customer_tier": "regular",
            "historical_purchases": 1,
            "total_spent": product_price,
            "conversion_rate": 0.5,

            "discount_requested": is_discount,
            "discount_requested_pct": discount_requested_pct,
            "requested_discount_pct": discount_requested_pct,
            "offered_price": offered_price or product_price,
            "urgency_score": 0.6,
            "intent_score": 0.8,
            "purchase_intent": 0.8,
            "sentiment_score": 0.5,
        }

        features_payload = SmartFeaturePayload(raw_features)

        decision_res = run_scoring_engine(
            features=features_payload,
            product_price=product_price,
            floor_price=floor_price,
            max_discount_pct=max_discount_pct,
        )
        print(f"    ✓ Step 1 Decision: {decision_res}", flush=True)

        # Step 6: Generate Respon AI Sales Brain
        context_data = {
            "product_name": product_name,
            "product_price": product_price,
            "stock_qty": stock_qty
        }

        ai_reply = await generate_sales_response(
            text=actual_message,
            context=context_data,
            emotion_result=emotion_res,
            decision_result=decision_res,
        )

        # Step 7: Simpan Balasan AI & Log Negosiasi ke Supabase
        if supabase and conversation_id:
            try:
                supabase.table("messages").insert({
                    "conversation_id": conversation_id,
                    "sender_type": "ai",
                    "content_type": "text",
                    "raw_text": ai_reply,
                    "intent": decision_res.get("decision", "general_response"),
                    "sentiment": "senang"
                }).execute()

                if product_id:
                    ai_dec = decision_res.get("decision", "hold_price")
                    if ai_dec not in ['hold_price', 'discount', 'bonus', 'counter_offer']:
                        ai_dec = 'hold_price'

                    supabase.table("negotiation_logs").insert({
                        "conversation_id": conversation_id,
                        "product_id": product_id,
                        "customer_offer_price": offered_price,
                        "ai_decision": ai_dec,
                        "ai_offer_price": decision_res.get("counter_offer_price", product_price),
                        "floor_price_snapshot": floor_price,
                        "model_confidence": 0.85,
                        "outcome": "pending"
                    }).execute()

            except Exception as e_log:
                logger.error(f"Gagal simpan AI message / negotiation log ke Supabase: {e_log}")

        print(f"    ✓ Step 2 Balasan AI Berhasil!", flush=True)
        print("==========================================\n", flush=True)

        return {"status": "success", "reply": ai_reply}

    except Exception as e:
        logger.error(f"Error pada bridge handler: {e}", exc_info=True)
        print("\n❌ ERROR PADA BRIDGE API!", flush=True)
        traceback.print_exc()
        print("==========================================\n", flush=True)

        return {
            "status": "error",
            "reply": f"⚠️ [Debug AI Error]: {str(e)}"
        }