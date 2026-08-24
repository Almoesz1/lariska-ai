"""Diagnostic Gemini live untuk koreksi typo STT.

File ini sengaja bisa dijalankan manual, tetapi tidak boleh melakukan request
API saat pytest melakukan *collection*. Pengujian unit/offline pipeline tetap
berada di suite pytest lain; diagnostic ini dipakai hanya ketika operator
secara sadar meminta verifikasi live dan siap memakai kuota.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.genai import types
from pydantic import BaseModel
from typing import Optional
from app.pipeline.gemini_client import generate_content
from app.schemas.pipeline import IntentType

class EntitySchema(BaseModel):
    product_name: Optional[str] = None
    quantity: Optional[int] = None
    offered_price: Optional[float] = None
    target_product_category: Optional[str] = None

class Schema(BaseModel):
    intent: IntentType
    entities: EntitySchema
    confidence: float

prompt = """Kamu adalah AI ekstraksi intent dan entitas terdepan untuk sistem penjualan e-commerce / UMKM Indonesia.
Analisis pesan pelanggan (termasuk hasil Speech-to-Text Voice Note yang mungkin mengandung typo atau kata tergabung) dan ekstrak intent serta entitas secara presisi.

PANDUAN INTENT:
- tanya_harga: pelanggan bertanya harga produk
- nego: pelanggan menawar harga (ada kata 'boleh kurang', 'harga mati?', 'diskon', angka penawaran, dll)
- tanya_stok: pelanggan bertanya apakah produk tersedia/ready/ukuran ready
- komplain: pelanggan mengadukan masalah (produk rusak, pengiriman terlambat, dll)
- checkout: pelanggan menyatakan mau beli / setuju dengan harga / minta invoice
- tanya_produk: pelanggan bertanya detail produk (bahan, ukuran, warna, spesifikasi) atau mengoreksi/mengklarifikasi produk yang dimaksud
- rekomendasi: pelanggan minta saran produk atau mencari produk tertentu
- greeting: salam pembuka tanpa pertanyaan spesifik
- lainnya: tidak masuk kategori lain

PANDUAN EKSTRAKSI & KOREKSI RALAT (SANGAT PENTING):
1. PENANGANAN KALIMAT KOREKSI / RALAT:
   - Jika pelanggan mengoreksi/meralat nama produk (misal: 'maksud saya X bukan Y', 'salah, harusnya X', 'bukan A tapi B', 'bukan X ya', 'salah ketik maksudnya X'), kamu HARUS mengambil produk X (produk sasaran koreksi/yang dimaksud) dan MENGABAIKAN produk Y (produk yang disangkal/salah).
   - Contoh: 'maksud saya sepatulari ke bukan sepatulah' -> produk yang dimaksud adalah 'sepatu lari'.
   - Jika pesan adalah koreksi produk, pilih intent 'tanya_produk' atau 'rekomendasi' (atau 'nego'/'tanya_harga' jika mengandung unsur nego/harga).

2. NORMALISASI TYPO & KATA GABUNGAN HASIL STT VOICE NOTE:
   - Voice Note STT sering menghasilkan kata tergabung atau typo fonetik. Kamu wajib menormalisasi kata tersebut menjadi istilah produk baku Indonesia dengan spasi yang benar.
   - Contoh normalisasi:
     * 'sepatulari' / 'sepatulari ke' -> 'sepatu lari'
     * 'kemejabatik' -> 'kemeja batik'
     * 'kaospolos' -> 'kaos polos'
     * 'sepatubola' -> 'sepatu bola'
     * 'celanachino' -> 'celana chino'

3. ENTITAS LAINNYA:
   - offered_price: Angka numerik murni penawaran (contoh: '150rb' -> 150000).
   - quantity: Jumlah barang yang ingin dibeli.
"""

test_inputs = [
    "maksud saya sepatulari ke bukan sepatulah",
    "salah mas, harusnya kemejabatik bukan kaospolos",
    "bukan sepatu bola mas tapi sepatulari",
    "eh maaf typo maksud saya celanachino bukan jeans",
    "Bisa kurang gak kak harganya? Kalau Rp 150.000 boleh?"
]

def run_live_diagnostic() -> None:
    for text in test_inputs:
        res = generate_content(
            model="gemini-3.5-flash-lite",
            contents=f"Pesan pelanggan:\n\"{text}\"",
            config=types.GenerateContentConfig(
                system_instruction=prompt,
                response_mime_type="application/json",
                response_schema=Schema,
            ),
        )
        print(f"INPUT : {text}")
        print(f"RESULT: intent={res.parsed.intent} | product={res.parsed.entities.product_name} | conf={res.parsed.confidence}\n")


if __name__ == "__main__":
    run_live_diagnostic()
