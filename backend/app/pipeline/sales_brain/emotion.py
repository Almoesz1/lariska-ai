"""
LARISKA AI — Sprint 5A (QA Patch + Rule-Based Fallback)
Emotion Classifier — Tahap 4b AI Pipeline

Perubahan terbaru (respons terhadap 429 RESOURCE_EXHAUSTED yang terjadi
saat testing lokal):
- Sebelumnya, kalau Gemini gagal (network/rate-limit/apapun), classify_emotion()
  langsung fallback ke 'netral' generik. Ini AMAN (tidak crash), tapi
  kehilangan informasi — kalau pelanggan jelas-jelas marah/buru-buru, sistem
  tetap membalas dengan nada netral, padahal ada sinyal jelas di teksnya
  yang sebenarnya bisa dibaca tanpa AI sama sekali.
- Sekarang ada LAPISAN KEDUA sebelum jatuh ke 'netral': rule-based keyword
  classifier (_rule_based_fallback). Ini BUKAN pengganti Gemini — akurasinya
  jauh di bawah model bahasa sungguhan, dan sengaja hanya aktif sebagai
  fallback saat API gagal. Prioritas deteksi: marah > buru_buru > senang >
  santai > netral (kalau tidak ada match) — urutan ini sengaja dibuat
  supaya sinyal yang paling penting untuk ditangani manusia (marah) tidak
  ketiban prioritas sinyal yang kurang kritis.
- SENGAJA TIDAK memasukkan "kak"/"gan" sebagai keyword santai — kedua kata
  itu adalah penanda sapaan sopan yang muncul di HAMPIR SEMUA pesan
  WhatsApp Indonesia (termasuk dari pelanggan yang marah), bukan indikator
  mood yang berguna. Kalau dimasukkan, rule-based ini nyaris selalu
  jatuh ke 'santai' apapun isi pesannya — false positive, bukan fallback
  yang membantu.

Mengklasifikasi emosi pelanggan dari teks pesan.
Output dipakai oleh response_generator.py untuk menyesuaikan nada balasan AI.

5 kelas emosi (sesuai schemas/pipeline.py EmotionType):
- marah     → Nada empati + profesional, hindari basa-basi
- netral    → Nada ramah standar
- santai    → Nada kasual, bisa pakai emoji
- buru_buru → Langsung ke point, tanpa basa-basi panjang
- senang    → Cocok untuk upsell produk tambahan

Referensi proposal Bab 7b: Emotion-Adaptive Response
"""

import logging
import re

from google.genai import types
from pydantic import BaseModel

from app.pipeline.gemini_client import generate_content
from app.schemas.pipeline import EmotionResult, EmotionType, IntentType

logger = logging.getLogger(__name__)

_GEMINI_MODEL = "gemini-3.5-flash-lite"


class _EmotionSchema(BaseModel):
    emotion: EmotionType
    confidence: float
    tone_hint: str


_EMOTION_PROMPT = """Kamu adalah AI klasifikasi emosi untuk sistem penjualan WhatsApp Indonesia.
Analisis emosi pelanggan dari pesan berikut.

Panduan:
- marah: ada komplain, kekecewaan, kata kasar, tanda seru berulang
- netral: pertanyaan biasa tanpa indikator emosi
- santai: pakai emoji, bercanda, sapaan akrab, kalimat informal
- buru_buru: kata seperti "bisa sekarang?", "cepat", "urgent", "besok udah harus ada"
- senang: antusias, banyak emoji positif, menyatakan puas

tone_hint: kalimat singkat 1 baris petunjuk cara membalas, contoh:
"Balas dengan empati dan jangan terlalu banyak basa-basi"
"""

# ============================================================
# Rule-based keyword fallback — HANYA aktif saat Gemini gagal.
# Urutan cek: MARAH > BURU_BURU > SENANG > SANTAI. Regex \b (word boundary)
# dipakai supaya tidak match substring di tengah kata lain secara tidak
# sengaja (mis. "lama" tidak boleh match di dalam "selamanya").
# ============================================================

_MARAH_KEYWORDS = [
    "kecewa", "parah", "jelek", "rugi", "penipu", "tipu", "kapok",
    "komplain", "protes", "buruk", "rusak", "cacat", "menyesal",
    "gaje", "ga jelas", "tidak jelas", "kesal", "kesel", "marah",
]

_BURU_BURU_KEYWORDS = [
    "besok", "cepat", "cepetan", "buru", "buruan", "sekarang", "urgent",
    "mendesak", "asap", "segera", "hari ini juga", "detik ini",
]

_SENANG_KEYWORDS = [
    "makasih banyak", "terima kasih banyak", "puas", "senang", "seneng",
    "mantap", "keren", "bagus banget", "suka banget", "recommended",
]

_SANTAI_KEYWORDS = [
    "hehe", "haha", "wkwk", "santuy", "wkwkwk", "lol", "😂", "😅", "🤣", "😊",
]

# Tanda seru berulang (2+) juga sinyal kuat untuk marah/urgent walau tanpa keyword.
_REPEATED_EXCLAMATION = re.compile(r"!{2,}")


def _contains_any_keyword(text_lower: str, keywords: list[str]) -> bool:
    for kw in keywords:
        if " " in kw or not kw.isascii() or not kw.isalnum():
            # Frasa multi-kata atau emoji/simbol — cek substring biasa,
            # \b tidak relevan untuk emoji dan bisa gagal untuk frasa.
            if kw in text_lower:
                return True
        else:
            if re.search(rf"\b{re.escape(kw)}\b", text_lower):
                return True
    return False


def _rule_based_fallback(text: str) -> EmotionResult:
    """
    Fallback tingkat 2 — dipanggil HANYA saat Gemini gagal total (network,
    rate-limit, parsing). Akurasi jauh di bawah model bahasa sungguhan,
    tapi lebih baik daripada selalu jatuh ke 'netral' generik saat ada
    sinyal jelas di teks (mis. pelanggan yang jelas-jelas marah).
    """
    text_lower = text.lower()

    if _contains_any_keyword(text_lower, _MARAH_KEYWORDS) or _REPEATED_EXCLAMATION.search(text):
        logger.info("[Emotion] Rule-based fallback: terdeteksi 'marah'.")
        return EmotionResult(
            emotion=EmotionType.MARAH,
            confidence=0.4,  # confidence rendah — ini heuristik kasar, bukan model
            tone_hint="Balas dengan empati, minta maaf jika relevan, jangan banyak basa-basi.",
        )

    if _contains_any_keyword(text_lower, _BURU_BURU_KEYWORDS):
        logger.info("[Emotion] Rule-based fallback: terdeteksi 'buru_buru'.")
        return EmotionResult(
            emotion=EmotionType.BURU_BURU,
            confidence=0.4,
            tone_hint="Langsung ke inti jawaban, hindari basa-basi panjang.",
        )

    if _contains_any_keyword(text_lower, _SENANG_KEYWORDS):
        logger.info("[Emotion] Rule-based fallback: terdeteksi 'senang'.")
        return EmotionResult(
            emotion=EmotionType.SENANG,
            confidence=0.4,
            tone_hint="Balas dengan antusias, boleh tawarkan produk tambahan.",
        )

    if _contains_any_keyword(text_lower, _SANTAI_KEYWORDS):
        logger.info("[Emotion] Rule-based fallback: terdeteksi 'santai'.")
        return EmotionResult(
            emotion=EmotionType.SANTAI,
            confidence=0.4,
            tone_hint="Balas dengan nada santai, boleh pakai emoji.",
        )

    logger.info("[Emotion] Rule-based fallback: tidak ada keyword match, default 'netral'.")
    return EmotionResult(
        emotion=EmotionType.NETRAL,
        confidence=0.3,
        tone_hint="Balas dengan ramah dan profesional.",
    )


def classify_emotion(text: str, intent: IntentType | None = None) -> EmotionResult:
    """
    Klasifikasi emosi dari teks pesan pelanggan.

    Alur fallback (TIDAK PERNAH raise ke caller):
    1. Coba Gemini (akurat, tapi bisa gagal karena network/rate-limit).
    2. Kalau Gemini gagal -> rule-based keyword fallback (kasar, tapi lebih
       baik daripada default generik).
    3. Rule-based sendiri selalu punya default 'netral' di ujungnya, jadi
       fungsi ini dijamin selalu mengembalikan EmotionResult yang valid.
    """
    # Negosiasi yang menyebut "mahal" atau "turunin" lazimnya bukan komplain
    # dan tidak boleh berubah menjadi handover karena label emosi LLM yang
    # terlalu agresif. Keputusan harga tetap diambil Sales Brain deterministik.
    if intent == IntentType.NEGO:
        return EmotionResult(
            emotion=EmotionType.NETRAL,
            confidence=0.9,
            tone_hint="Balas empatik dan fokus pada nilai produk serta opsi harga yang sudah disetujui.",
        )

    preview = f"{text[:60]}..." if len(text) > 60 else text
    logger.info(f"[Emotion] Classifying: '{preview}'")

    try:
        response = generate_content(
            model=_GEMINI_MODEL,
            contents=f"{_EMOTION_PROMPT}\n\nPesan:\n\"{text}\"",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_EmotionSchema,
            ),
        )
        parsed: _EmotionSchema | None = response.parsed
        if parsed is None:
            raise ValueError("response.parsed kosong — output tidak memenuhi schema.")

        result = EmotionResult(
            emotion=parsed.emotion,
            confidence=parsed.confidence,
            tone_hint=parsed.tone_hint,
        )
        logger.info(f"[Emotion] Result (Gemini): {result.emotion.value} (conf={result.confidence:.2f})")
        return result

    except Exception as exc:
        logger.warning(f"[Emotion] Gemini gagal ({exc}), pakai rule-based fallback.")
        return _rule_based_fallback(text)
