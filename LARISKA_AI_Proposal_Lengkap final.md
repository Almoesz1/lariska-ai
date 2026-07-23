# LARISKA AI — Proposal Final untuk AI Innovation Challenge (Compfest 18)

## One-Sentence Positioning
> **LARISKA AI adalah Sales Brain pertama yang memberi UMKM Indonesia tenaga penjual digital — memahami pelanggan, mengambil keputusan bisnis secara adaptif, dan terus disempurnakan dari data transaksi nyata.**

Catatan penting: kata "terus disempurnakan" merujuk pada siklus retraining periodik model dari data yang terkumpul (dijelaskan di Bagian 6), **bukan** klaim *online/real-time learning* saat demo. Jangan pernah menyatakan di depan juri bahwa model "belajar langsung saat itu juga" kalau memang tidak — ini jenis overclaim yang paling gampang dibongkar.

---

## 1. Ringkasan Eksekutif

LARISKA AI adalah **Sales Intelligence Platform** untuk UMKM Indonesia. Intinya adalah **Sales Brain** — sistem pengambilan keputusan bisnis yang menggabungkan pipeline NLU terstruktur, model ML kecil yang benar-benar dilatih, dan LLM untuk komunikasi natural. WhatsApp adalah kanal pengiriman, bukan identitas produk.

**Fokus MVP (hackathon):**
1. WhatsApp integration
2. AI Pipeline penuh (STT → Intent/Entity → State Tracking → Sales Brain → Response)
3. Sales Brain dengan Adaptive Scoring Engine + model ML kecil terlatih (kontribusi AI nyata)
4. Voice Intelligence (Bahasa Indonesia)
5. Emotion-Adaptive Response
6. Business Copilot dengan rekomendasi aktif
7. AI Evaluation dengan metrik terukur

**Yang sengaja TIDAK diklaim sebagai sudah jadi:** reinforcement learning penuh, digital twin personal per toko, bahasa daerah penuh, pricing berbasis cuaca/payday. Semua ini dijelaskan sebagai roadmap dengan alasan teknis yang jujur.

---

## 2. Problem Statement

UMKM menyumbang >60% PDB Indonesia dan menyerap mayoritas tenaga kerja, namun mayoritas transaksi masih manual lewat WhatsApp oleh pemilik usaha yang juga mengurus produksi dan pengiriman.

**Masalah konkret:**
- Respon lambat → pelanggan pindah ke kompetitor.
- Preferensi konsumen Indonesia: voice note > teks, bahasa campur (Indonesia + daerah + slang + typo), negosiasi hampir selalu terjadi sebelum closing.
- Chatbot template tidak mampu menangani ambiguitas bahasa, tidak bisa nego secara adaptif, tidak mengingat pelanggan, tidak mengambil keputusan bisnis.

**Aksi sebelum submit:** cari 1 data resmi (BPS/Kemenkop UKM/APJII) soal UMKM yang berjualan via WhatsApp dan dampak respon lambat terhadap penjualan — 1 angka kredibel di slide pembuka jauh lebih kuat daripada klaim generik.

---

## 3. Solusi: LARISKA AI

Bukan chatbot. LARISKA AI adalah sistem pengambilan keputusan bisnis yang kebetulan berkomunikasi lewat WhatsApp. Positioning ini harus konsisten di seluruh proposal, slide, dan demo — jangan sekalipun menyebut kata "chatbot" saat presentasi.

---

## 4. AI Pipeline (Arsitektur Sistem)

Ini yang membedakan "AI beneran" dari "wrapper LLM" di mata juri teknis — pecah sistem jadi tahapan yang jelas, masing-masing punya tanggung jawab spesifik dan bisa dijelaskan/dievaluasi terpisah:

```
WhatsApp (teks/voice)
    ↓
[1] Speech Recognition (Whisper) — hanya jika input voice note
    ↓
[2] Intent Classification + Entity Extraction (LLM structured output/JSON mode)
    → intent: tanya_harga | nego | tanya_stok | komplain | checkout, dst.
    → entity: nama produk, jumlah, harga yang ditawar, dst.
    ↓
[3] Conversation State Tracking (disimpan di database per nomor WA)
    → riwayat tawar-menawar, produk yang dibahas, tahap percakapan saat ini
    ↓
[4] Sales Brain
    a. Adaptive Scoring Engine (rule + model ML kecil terlatih — lihat Bagian 6)
    b. Emotion Classifier (marah/netral/santai/terburu-buru)
    → output: keputusan bisnis (HOLD_PRICE / DISCOUNT(x%) / BONUS / COUNTER_OFFER) + gaya nada balasan
    ↓
[5] Retrieval (pgvector) — untuk rekomendasi produk relevan bila diperlukan
    ↓
[6] LLM Response Generation — menyusun bahasa natural dari keputusan di atas (LLM TIDAK menentukan angka/keputusan bisnis)
    ↓
WhatsApp (balasan ke pelanggan)
```

**Kenapa struktur ini penting untuk dijelaskan ke juri:** setiap tahap bisa diuji dan diukur terpisah (lihat Bagian 8 — AI Evaluation), dan LLM secara eksplisit hanya bertugas di tahap komunikasi, bukan pengambilan keputusan bisnis — ini justru argumen kuat untuk "AI safety by design", bukan kelemahan.

---

## 5. MVP Scope: Tier 1/2/3 (realistis untuk timeline AIC)

### Tier 1 — Harus jalan penuh saat demo
| Fitur | Status teknis |
|---|---|
| WhatsApp integration | Webhook Cloud API, wajib stabil |
| AI Pipeline lengkap (tahap 1-6 di atas) | Inti sistem |
| Sales Brain + Adaptive Scoring Engine + model ML kecil | Kontribusi AI utama — dilatih SEBELUM hari-H |
| Voice Intelligence (Bahasa Indonesia) | Whisper, sudah matang untuk Bahasa Indonesia |
| Emotion-Adaptive Response | 1 langkah klasifikasi tambahan di pipeline |
| Business Copilot (rekomendasi, bukan cuma laporan) | Scheduled job + threshold rule + LLM narasi |
| Invoice + QRIS sandbox | Menutup loop transaksi |

### Tier 2 — Sebagian real, sebagian disederhanakan tapi tetap jujur dijelaskan
| Fitur | Pendekatan realistis |
|---|---|
| Product Recommendation | Vector similarity di katalog kecil (10-20 produk demo) |
| Customer Memory | Riwayat chat & transaksi per nomor WA, ditampilkan di dashboard |
| Dashboard BI real-time | Data asli dari demo + beberapa data historis yang dilabeli jelas "simulasi" |

### Tier 3 — Roadmap (jelaskan konsep & alasan teknis, jangan klaim sudah jadi)
| Fitur | Kenapa ditunda |
|---|---|
| Bahasa daerah penuh (Jawa, Sunda) | STT/NLU bahasa daerah belum matang, risiko demo gagal |
| Digital Twin personal per toko | Butuh volume data historis besar per toko (cold start problem) |
| Reinforcement learning policy penuh | Butuh data interaksi skala besar + infra training berkelanjutan — di luar scope hackathon |
| Pricing berbasis cuaca/payday | Tambah dependency API eksternal, titik kegagalan demo |

---

## 6. Kontribusi AI yang Jujur: Adaptive Scoring Engine + Model ML Terlatih

Ini jawaban langsung untuk pertanyaan juri "apa kontribusi AI kalian selain integrasi LLM?"

**Bukan** klaim reinforcement learning atau policy learning penuh (lihat alasan di Bagian 5, Tier 3). **Tapi** ini genuinely bukan cuma rule statis:

1. **Kumpulkan/susun dataset sintetis negosiasi** (sebelum hari-H): skenario dengan variabel margin, stok, loyalitas pelanggan, waktu, nilai transaksi → label: aksi optimal (tahan harga / diskon x% / bonus / counter-offer). Bisa dibuat dari kombinasi logika bisnis masuk akal + sedikit data riil dari wawancara UMKM (Bagian 10).
2. **Latih model kecil** (logistic regression atau gradient boosting ringan seperti LightGBM) untuk memprediksi aksi optimal dari fitur-fitur tersebut. Ini dilakukan **sebelum hari-H hackathon**, bukan saat demo.
3. **Saat live**, model ini di-*inference* (bukan training ulang) sebagai bagian dari Adaptive Scoring Engine, dikombinasikan dengan hard business rule (floor price tidak pernah dilanggar, ini tetap hardcoded).
4. **Evaluasi model** dilaporkan sebagai bagian dari AI Evaluation (Bagian 8) — akurasi, precision/recall pada data validasi.

**Kenapa ini strategi yang tepat:** kalian benar-benar punya artefak ML yang bisa ditunjukkan (kode training, metrik evaluasi, model file) — ini kontribusi AI yang jujur dan bisa dipertanggungjawabkan, tanpa klaim berlebihan soal "AI yang belajar sendiri secara real-time".

**Roadmap lanjutan (sampaikan sebagai visi, bukan status saat ini):** setelah produk berjalan dan data transaksi riil terkumpul, model ini bisa di-retrain berkala (batch, bukan online) menjadi lebih akurat — inilah makna "terus disempurnakan" di positioning statement.

---

## 7. Signature AI Enhancements

**a) Adaptive Scoring Engine (dulu disebut "negotiation engine")** — nama ini lebih tepat karena mencerminkan kombinasi rule + model ML terlatih, bukan sekadar if-else statis.

**b) Emotion-Adaptive Response** — 1 langkah klasifikasi sentimen (marah/netral/santai/terburu-buru) sebelum LLM menyusun balasan. Efeknya besar secara demo, effort-nya kecil (1 prompt tambahan, bukan model baru).

**c) Business Copilot dengan rekomendasi aktif** — bukan cuma laporan pasif. Contoh output nyata: "Hari ini Produk A ditawar 31 kali dan konversi hanya 12% — saya sarankan turunkan harga floor sebesar 5% untuk 3 hari ke depan" atau "Jam 20.00 adalah jam dengan conversion tertinggi hari ini." Teknisnya: query database + threshold rule sederhana + 1 pemanggilan LLM untuk narasi. Murah dibangun, dampak presentasi besar.

**d) Sales Brain — sinyal stok real-time yang terlihat berubah saat demo** — simulasikan perubahan stok di dashboard saat demo, tunjukkan AI langsung beradaptasi di request berikutnya. Bukti visual "AI sadar kondisi bisnis", bukan cuma cerita di slide.

---

## 8. AI Evaluation & Metrik

Bagian ini WAJIB ada untuk proposal level finalis AI competition. Definisikan metrik sekarang, ukur dengan pengujian kecil (bahkan 20-30 sample sudah cukup untuk laporan awal) — **jangan pernah menulis angka yang belum benar-benar diuji.**

| Metrik | Cara ukur | Target realistis untuk laporan awal |
|---|---|---|
| STT Accuracy (Bahasa Indonesia) | Word Error Rate pada sample voice note uji | Laporkan angka aktual dari 20-30 sample |
| Intent Classification Accuracy | Bandingkan output LLM vs label manual pada test set kecil | Laporkan angka aktual |
| Negotiation Success Rate | % percakapan nego yang berakhir checkout, dari simulasi/pilot | Laporkan angka aktual dari simulasi internal |
| Average Response Time | Waktu dari pesan masuk sampai balasan terkirim | Ukur langsung dari sistem (biasanya < beberapa detik) |
| Average Discount Margin | Rata-rata diskon yang diberikan AI vs floor price | Laporkan dari data simulasi |
| Model Evaluation (Adaptive Scoring Engine) | Akurasi/precision/recall model ML pada data validasi | Laporkan dari proses training di Bagian 6 |
| Customer Satisfaction (kualitatif) | Survei singkat ke UMKM yang diwawancara (Bagian 10) | Kutipan langsung, bukan skor dikarang |

**Prinsip penting:** metrik yang jujur dengan sample kecil jauh lebih kredibel di mata juri teknis daripada angka besar tanpa metodologi jelas.

---

## 9. Guardrail & Keamanan AI

- Floor price & diskon maksimum di-*enforce* di kode (hard rule), bukan di prompt — LLM tidak pernah menentukan angka final.
- Validasi input untuk mendeteksi upaya prompt injection (mis. "abaikan instruksi sebelumnya").
- Rate limiting per nomor WA untuk mencegah abuse/spam nego berulang.
- Fallback ke admin manusia jika confidence rendah — human-in-the-loop.
- Kepatuhan UU PDP: consent penyimpanan data chat & transaksi, transparansi ke pelanggan bahwa mereka berinteraksi dengan AI.

---

## 10. Model Bisnis & Monetisasi

- **Target pasar:** UMKM skala kecil-menengah dengan volume chat tinggi (fashion, F&B, sparepart, dll).
- **Model harga:**
  - Free tier: fitur dasar, limit chat/bulan.
  - Subscription bulanan: fitur penuh (Sales Brain, Business Copilot, dashboard BI).
  - Opsi fee per transaksi sukses untuk UMKM yang sensitif biaya tetap.
- **Unit economics sederhana:** biaya per percakapan (WA Cloud API + LLM API + inference model) vs harga langganan — tunjukkan margin masuk akal di 1 slide.
- **Validasi awal:** wawancara 5-10 pemilik UMKM sebelum final pitch — catat kutipan langsung, dan kalau memungkinkan jalankan simulasi/pilot kecil untuk mendapat 1-2 metrik nyata (lihat Bagian 8).

---

## 11. Analisis Kompetitor

| Pemain | Kekuatan | Kelemahan dibanding LARISKA AI |
|---|---|---|
| Qiscus, Wati, Chatbiz (chatbot WA komersial) | Integrasi WA mapan, fitur broadcast/CRM | Tidak ada Adaptive Scoring Engine, tidak paham voice note, tidak ada Business Copilot |
| Chatbot rule-based custom | Murah, cepat dibuat | Kaku, tidak ada model ML, tidak belajar dari data |
| Solusi AI generik (plugin ChatGPT dsb) | AI umum kuat | Tidak ada domain-specific decision layer & guardrail bisnis UMKM Indonesia |

---

## 12. Innovation Moat

Jawaban untuk "kalau Meta/Tokopedia bikin fitur sama besok?" — jawab dengan jujur, jangan lebih dari yang benar-benar dibangun:

- **Data proprietary dari transaksi UMKM Indonesia** yang dipakai melatih & menyempurnakan Adaptive Scoring Engine dari waktu ke waktu (dengan consent, sesuai UU PDP).
- **Domain-specific guardrail & decision layer** yang di-tuning untuk UMKM kecil, bukan fitur AI generik skala masal seperti yang biasanya jadi fokus pemain besar.
- **Fokus segmen yang sering diabaikan** pemain besar — UMKM kecil-menengah, bukan enterprise.

---

## 13. Demo Script (pengalaman juri saat mencoba live)

1. Juri kirim **voice note** menawar harga produk.
2. Sistem menampilkan (di layar terpisah/dashboard) proses pipeline secara real-time: STT → intent/entity → emotion detected → Sales Brain memutuskan → balasan terkirim.
3. AI membalas dengan nada sesuai emosi terdeteksi, memberi counter-offer sesuai floor price.
4. Juri minta rekomendasi produk lain → AI merekomendasikan + menawarkan bundle (upsell sederhana).
5. Juri setuju harga → AI membuat invoice + QRIS.
6. Dashboard admin update real-time: stok berkurang, transaksi tercatat.
7. Business Copilot langsung memunculkan insight baru: "Konversi hari ini naik X%, produk ini paling sering ditawar."

**Latihan penting:** rehearse demo ini berkali-kali sebelum final, siapkan fallback manual kalau ada kegagalan teknis live (network/API down) — punya rekaman video demo cadangan adalah praktik standar di kompetisi.

---

## 14. Timeline Eksekusi (cepat, realistis, sesuai jadwal AIC)

> Catatan: tanggal pasti (preliminary, hackathon day, final) ada di guidebook resmi AIC — cek ulang untuk memastikan. Kerangka di bawah mengasumsikan pola umum: submit proposal awal → shortlist → hackathon 1 hari → final pitch.

**Fase A — Sebelum submit proposal (sekarang - deadline preliminary)**
- Finalisasi proposal ini + cari 1 data resmi untuk problem statement.
- Wawancara 3-5 pemilik UMKM (validasi awal, kutipan untuk pitch).
- Siapkan dataset sintetis negosiasi + mulai training model ML kecil (Bagian 6) — ini paling memakan waktu, mulai lebih awal.

**Fase B — Setelah lolos shortlist, sebelum hari-H hackathon**
- Bangun skeleton project: WA Cloud API sandbox, database schema (Supabase), deploy pipeline (Vercel/Railway).
- Selesaikan training & evaluasi model ML kecil, simpan sebagai artefak yang siap di-*load*.
- Bangun AI Pipeline tahap demi tahap (STT → intent/entity → state tracking → Sales Brain → response) — uji tiap tahap terpisah.
- Uji STT dengan sample suara nyata, catat WER aktual.

**Fase C — Hari-H hackathon (1 hari)**
- **Jangan bangun fitur baru dari nol hari ini.** Fokus: integrasi end-to-end, bugfix, styling dashboard, rehearse demo flow.
- Kerjakan Tier 1 dulu sampai benar-benar stabil, baru sentuh Tier 2 jika waktu tersisa.

**Fase D — Sebelum final pitch**
- Rapikan dashboard BI (Business Copilot, chart, customer memory view).
- Susun AI Evaluation dari hasil pengujian aktual (Bagian 8) — jangan tunda ini sampai menit terakhir.
- Rehearse pitch dengan one-sentence positioning + siapkan jawaban untuk pertanyaan sulit (kontribusi AI, moat, evaluasi, keamanan).
- Siapkan video demo cadangan.

---

## 15. Tech Stack Lengkap (gratis, up-to-date)

| Layer | Rekomendasi | Alasan |
|---|---|---|
| **Frontend (dashboard admin)** | Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui | Modern, cepat dibangun |
| **Chart/BI** | Tremor atau Recharts | Ringan, mudah integrasi React |
| **Hosting frontend** | Vercel (free tier) | Deploy otomatis dari GitHub |
| **Backend/orkestrasi AI** | Python + FastAPI | Ekosistem AI/ML terkuat, mudah integrasi Whisper & model ML |
| **Model ML kecil (Adaptive Scoring)** | scikit-learn / LightGBM (training offline sebelum hari-H) | Ringan, cepat dilatih, mudah dievaluasi |
| **Orkestrasi LLM (opsional)** | LangChain / LlamaIndex | Mempermudah RAG untuk customer memory |
| **Hosting backend** | Railway atau Render (free tier) | Setup cepat |
| **Database** | Supabase (PostgreSQL + Auth + Storage) | Satu platform, free tier lengkap |
| **Auth dashboard admin** | Supabase Auth | Gratis, cepat setup |
| **Vector search** | pgvector (ekstensi Supabase Postgres) | Untuk recommendation & retrieval |
| **WhatsApp integration** | WhatsApp Cloud API (Meta, resmi) — free tier 1000 percakapan/bulan | Legal, aman dari risiko nomor diblokir |
| **Alternatif cepat untuk testing internal** | Baileys (unofficial, open-source) | Hanya untuk dev/testing, jelaskan akan migrasi ke Cloud API resmi |
| **LLM API** | Google Gemini API (free tier besar) / Groq (Llama, cepat & gratis) / OpenRouter | Sesuaikan budget tim |
| **Speech-to-Text** | Whisper (open-source, self-host) | Gratis, akurasi baik untuk Bahasa Indonesia |
| **Embedding model** | Model embedding open-source (mis. multilingual-e5) | Untuk vector search produk |
| **Storage foto produk** | Supabase Storage / Cloudinary (free tier) | Termasuk optimasi gambar |
| **Payment/QRIS** | Midtrans Sandbox / Xendit Sandbox | Simulasi QRIS gratis |
| **Background job/queue** | Upstash Redis (free tier) + BullMQ, atau cron sederhana | Untuk Business Copilot & proses async |
| **CI/CD** | GitHub + GitHub Actions | Gratis untuk repo tim kecil |

---

## 16. Checklist Final Sebelum Submit/Pitch

- [ ] 1 data kuantitatif resmi di problem statement
- [ ] One-sentence positioning konsisten di semua materi
- [ ] AI Pipeline digambar sebagai diagram (bukan cuma teks)
- [ ] Model ML kecil sudah dilatih & dievaluasi, hasil evaluasi asli tercantum
- [ ] AI Evaluation table diisi angka aktual, bukan estimasi
- [ ] Business Copilot menampilkan rekomendasi aktif, bukan cuma laporan
- [ ] Guardrail (floor price hardcoded, anti prompt-injection) siap dijelaskan
- [ ] Innovation Moat siap dijawab dengan jujur saat sesi tanya-jawab
- [ ] Demo direhearse berkali-kali + video cadangan siap
- [ ] Tidak ada klaim fitur yang belum benar-benar berfungsi
- [ ] Kutipan validasi dari wawancara UMKM asli tercantum

---

*Dokumen ini adalah revisi final strategis LARISKA AI untuk AI Innovation Challenge Compfest 18 — disusun agar seimbang antara ambisi inovasi dan kelayakan eksekusi nyata dalam timeline kompetisi.*
