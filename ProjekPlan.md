# LARISKA AI — Project Master Plan (Sprint 3 → Final)
### Technical Lead / Software Architect Document

Tim: 1 AI/ML Engineer, Backend Engineer 1, Backend Engineer 2, Frontend Engineer 1, Frontend Engineer 2.
Prinsip: setiap sprint didesain supaya minimal 2 role bisa kerja paralel tanpa saling tunggu. Kalau sebuah role tidak punya dependency blocking, dia dikasih track kerja sendiri (ditandai huruf: 3A/3B/3C, dst).

---

## Ringkasan Alur Sprint & Dependency

```
Sprint 3A (AI/ML)         Sprint 3B (Backend 1+2)      Sprint 3C (Frontend 1+2)
     │                          │                              │
     │                          ├──────────────┬───────────────┤
     ▼                          ▼               ▼               ▼
Sprint 5A (AI+BE1) ◀── Sprint 4A (AI+BE1)   Sprint 4C (BE2)   Sprint 4B (FE1+FE2)
     │                          │               │               │
     │                          ▼               │               │
     │                    (pipeline siap)        │               │
     ▼                                            ▼               ▼
Sprint 6 (BE2+Integrasi) ──────────────────▶ Sprint 5B/5C (FE1/FE2)
     │
     ▼
Sprint 7 (AI+BE1) ── paralel dengan Sprint 6 (mulai setelah 5A selesai)
     │
     ▼
Sprint 8 (AI, semua bantu ukur)
     │
     ▼
Sprint 9 (Semua — Hardening)
     │
     ▼
Sprint 10 (Semua — Demo Rehearsal) — FINAL
```

Sprint dengan huruf sama (3A/3B/3C, 4A/4B/4C, 5A/5B/5C) berjalan **paralel** — tidak saling menunggu, hanya sama-sama menunggu sprint berangka lebih kecil selesai.

---

## SPRINT 3A — AI/ML Foundation: Adaptive Scoring Engine

**Tujuan:** Menghasilkan model ML kecil yang benar-benar dilatih untuk mengambil keputusan negosiasi (hold_price/discount/bonus/counter_offer) — ini kontribusi AI jujur yang dibahas di proposal, harus mulai duluan karena paling lama.

**Alasan urutan:** Tidak bergantung pada sprint manapun (hanya butuh skema database dari Sprint 2A untuk tahu struktur fitur), jadi bisa mulai hari pertama bersamaan dengan 3B/3C.

**Dependency:** Sprint 2A (Database Foundation) — selesai. Tidak ada dependency lain.

**Deliverables:**
- `ml/data/synthetic_negotiation_data.csv`
- `ml/model_artifacts/scoring_model.pkl`
- `ml/model_artifacts/training_metadata.json` (angka evaluasi asli)

**Folder dibuat:** tidak ada folder baru (sudah ada dari Sprint 2A).
**File dibuat:** `ml/generate_synthetic_data.py`, `ml/train_scoring_model.py`, `ml/evaluate_model.py`, `ml/requirements.txt`
**File dimodifikasi:** tidak ada.

**Output demo akhir sprint:** model bisa di-load dan menghasilkan prediksi dari 1 baris fitur contoh, plus laporan akurasi/precision/recall.

**Definition of Done:**
- [ ] Dataset sintetis ter-generate dan tersimpan
- [ ] Model terlatih dan tersimpan sebagai `.pkl`
- [ ] Metrik evaluasi (accuracy, precision, recall, F1) tercatat di `training_metadata.json`
- [ ] Model bisa di-load ulang dan menghasilkan prediksi konsisten

**Risiko:** Dataset sintetis terlalu "mudah" sehingga model overfit (akurasi >95% tidak realistis) atau terlalu random sehingga model tidak belajar apa-apa (akurasi ~25%, setara tebak acak dari 4 kelas).
**Mitigasi:** Tambahkan noise terkontrol (~8%) di label generation supaya tidak sempurna; kalau akurasi terlalu rendah, kurangi noise atau perjelas aturan heuristik; laporkan angka apa adanya, bukan yang "terlihat bagus".

**Task AI/ML Engineer:** kerjakan seluruhnya (solo track, tidak ada anggota lain yang overlap di sprint ini).

---

## SPRINT 3B — Backend Core Foundation

**Tujuan:** Membangun fondasi FastAPI: koneksi Supabase (service_role), config loader, schema Pydantic, dan endpoint dashboard dasar (products/customers/orders).

**Alasan urutan:** Semua sprint backend & AI Pipeline berikutnya butuh ini sebagai fondasi (config, koneksi DB, schema). Tidak bergantung pada Sprint 3A/3C sehingga bisa paralel.

**Dependency:** Sprint 2A (Database Foundation) — selesai.

**Deliverables:** `dashboard_api.py` yang bisa diakses lewat `/docs` (Swagger UI otomatis FastAPI) dan mengembalikan data asli dari Supabase.

**Folder dibuat:** tidak ada folder baru (`backend/app/core`, `services`, `schemas`, `api` sudah ada).
**File dibuat:** `backend/app/core/config.py`, `backend/app/services/supabase_client.py`, `backend/app/schemas/product.py`, `customer.py`, `order.py`, `__init__.py`, `backend/app/api/dashboard_api.py`
**File dimodifikasi:** `backend/app/main.py`, `backend/requirements.txt`

**Output demo akhir sprint:** buka `http://localhost:8000/docs`, jalankan `GET /api/products` → data asli dari seed muncul.

**Definition of Done:**
- [ ] `.env` ter-load tanpa error
- [ ] Koneksi ke Supabase berhasil (bisa query products)
- [ ] Endpoint CRUD products (GET list, GET by id, POST, PUT, DELETE/soft-delete)
- [ ] Endpoint GET customers, GET orders
- [ ] Swagger docs (`/docs`) menampilkan semua endpoint dengan schema yang benar

**Risiko:** Salah handle UUID/tipe data numeric saat serialisasi Pydantic ↔ Supabase (mirip bug `round()` di seed.sql — tipe data sering jadi sumber bug).
**Mitigasi:** Uji tiap endpoint manual lewat Swagger UI sebelum lanjut sprint berikutnya, bukan asumsi "kodenya benar karena tidak error saat nulis".

**Pembagian tugas:**
| Siapa | Kerjakan | File |
|---|---|---|
| Backend Engineer 1 | Config, koneksi Supabase, semua schema Pydantic | `core/config.py`, `services/supabase_client.py`, `schemas/*.py` |
| Backend Engineer 2 | Endpoint dashboard_api (products CRUD, customers, orders), wiring ke main.py | `api/dashboard_api.py`, `main.py` |

Urutan: Backend 1 selesaikan `config.py` + `supabase_client.py` + schema dulu (± 1-2 jam), baru Backend 2 mulai `dashboard_api.py` karena butuh import dari situ. Untuk tidak saling tunggu total, Backend 2 bisa mulai nulis endpoint dengan schema sementara (dummy class) lalu swap begitu Backend 1 selesai.

---

## SPRINT 3C — Frontend UI Foundation (Mock Data)

**Tujuan:** Membangun UI dashboard (products, customers, orders, insights) dengan data mock yang strukturnya SAMA PERSIS dengan Pydantic schema dari 3B — supaya nanti tinggal ganti sumber data, bukan ganti struktur komponen.

**Alasan urutan:** Tidak bergantung pada backend selesai — inilah yang membuat Frontend 1 & 2 tidak menganggur menunggu Sprint 3B.

**Dependency:** Sprint 2A (untuk tahu struktur tabel/field). Tidak bergantung pada 3A/3B.

**Deliverables:** Semua halaman dashboard bisa dibuka dan menampilkan data (mock), styling sudah rapi.

**Folder dibuat:** tidak ada baru.
**File dimodifikasi:** `app/(dashboard)/products/page.tsx`, `customers/page.tsx`, `orders/page.tsx`, `insights/page.tsx`, `hooks/useProducts.ts`, `useCustomers.ts`, `useOrders.ts`, `services/product.service.ts`, `order.service.ts`, (buat baru) `services/customer.service.ts`

**Output demo akhir sprint:** `npm run dev` → seluruh halaman dashboard bisa dibuka, tabel/kartu terisi data mock yang formatnya identik dengan field database (products: name, price, floor_price, stock, dst).

**Definition of Done:**
- [ ] Semua halaman dashboard render tanpa error
- [ ] Struktur data mock 1:1 dengan Pydantic schema Sprint 3B (field name, tipe)
- [ ] `services/*.service.ts` sudah punya fungsi fetch yang tinggal diarahkan ke backend (base URL dari `.env.local`)

**Risiko:** Struktur mock data frontend tidak sinkron dengan schema backend asli → rework besar saat wiring (Sprint 4B).
**Mitigasi:** Frontend 1/2 WAJIB baca `backend/app/db/schema.sql` (bukan menebak field), samakan nama & tipe field persis.

**Pembagian tugas:**
| Siapa | Kerjakan |
|---|---|
| Frontend Engineer 1 | Halaman `products`, `orders` + service & hook terkait |
| Frontend Engineer 2 | Halaman `customers`, `insights` + service & hook terkait, plus `services/customer.service.ts` (belum ada, perlu dibuat) |

---

## SPRINT 4A — AI Pipeline Tahap 1-3 (STT, Intent/Entity, State Tracking)

**Tujuan:** Membangun 3 tahap awal AI Pipeline: Speech Recognition, Intent/Entity Extraction, Conversation State Tracking — bisa diuji terpisah lewat input teks/voice dummy, belum tersambung WhatsApp.

**Alasan urutan:** Butuh `supabase_client.py` dan schema dari 3B untuk menulis ke tabel `messages`/`conversations`. Tidak butuh model dari 3A di tahap ini (model dipakai nanti di Sprint 5A).

**Dependency:** Sprint 3B (Backend Core).

**Deliverables:** Fungsi yang bisa menerima teks/voice, mengembalikan intent+entity terstruktur, dan menyimpan ke database.

**File dibuat:** `backend/app/pipeline/__init__.py`, `stt.py`, `intent_entity.py`, `state_tracking.py`
**File dimodifikasi:** tidak ada.

**Output demo akhir sprint:** script test yang kirim 1 kalimat teks & 1 file voice note contoh → tampil hasil intent/entity + tersimpan di tabel `messages`.

**Definition of Done:**
- [ ] STT mengembalikan teks dari file voice note contoh
- [ ] Intent/Entity extraction mengembalikan JSON terstruktur dari teks
- [ ] State tracking berhasil membuat/mengambil `conversation` dan menyimpan `message` ke Supabase

**Risiko:** Akurasi STT Bahasa Indonesia untuk voice note kasual/berisik lebih rendah dari ekspektasi.
**Mitigasi:** Uji dengan 5-10 sample suara nyata secepatnya (bukan di akhir sprint), catat Word Error Rate aktual untuk Sprint 8 nanti.

**Pembagian tugas:**
| Siapa | Kerjakan |
|---|---|
| AI/ML Engineer | `intent_entity.py` (desain prompt structured output) + validasi akurasi STT |
| Backend Engineer 1 | `stt.py` (integrasi Whisper) + `state_tracking.py` (koneksi ke Supabase) |

---

## SPRINT 4B — Dashboard Wiring (Frontend → Backend Asli)

**Tujuan:** Mengganti data mock di Sprint 3C dengan data asli dari `dashboard_api.py`.

**Alasan urutan:** Butuh Sprint 3B (endpoint sudah ada) dan Sprint 3C (komponen UI sudah ada) selesai.

**Dependency:** Sprint 3B, Sprint 3C.

**Deliverables:** Dashboard berfungsi penuh dengan data asli dari Supabase (lewat backend).

**File dimodifikasi:** `services/*.service.ts` (ganti mock jadi fetch asli), `hooks/*.ts`, `frontend/.env.local`

**Output demo akhir sprint:** buka dashboard → data products/customers/orders yang tampil adalah data seed asli dari Supabase.

**Definition of Done:**
- [ ] Semua halaman fetch data asli, tidak ada mock tersisa
- [ ] Loading state & error state ditangani (bukan blank screen kalau backend down)
- [ ] CRUD products dari UI benar-benar mengubah data di Supabase

**Risiko:** CORS error antara frontend (localhost:3000) dan backend (localhost:8000).
**Mitigasi:** Sudah diantisipasi di `main.py` Sprint 3B (CORS middleware), tinggal pastikan origin sesuai saat testing.

**Pembagian tugas:** Frontend Engineer 1 & 2 lanjutkan halaman masing-masing dari Sprint 3C.

---

## SPRINT 4C — Payment & Order Completion Flow

**Tujuan:** Integrasi Midtrans/Xendit sandbox untuk QRIS, update status order otomatis, dan pencatatan `inventory_logs` saat order sukses.

**Alasan urutan:** Hanya butuh skema `orders`/`payments`/`inventory_logs` dari 3B, tidak bergantung pipeline AI — bisa paralel penuh dengan 4A/4B.

**Dependency:** Sprint 3B.

**Deliverables:** Endpoint untuk membuat invoice + link QRIS sandbox, webhook callback payment, trigger update stok.

**File dibuat:** `backend/app/services/payment_client.py`, `backend/app/api/payment_webhook.py`
**File dimodifikasi:** `backend/app/api/dashboard_api.py` (endpoint create order → trigger payment), `main.py`

**Output demo akhir sprint:** buat order via API → dapat link/kode QRIS sandbox → simulasikan bayar → status order & stok ter-update otomatis.

**Definition of Done:**
- [ ] Order baru otomatis membuat record `payments` berstatus pending
- [ ] Webhook callback dari Midtrans/Xendit sandbox berhasil ubah status jadi success
- [ ] `inventory_logs` tercatat otomatis saat order status jadi completed

**Risiko:** Webhook sandbox butuh URL publik (ngrok) — bisa lupa di-refresh URL-nya.
**Mitigasi:** Dokumentasikan langkah setup ngrok di README, cek ulang sebelum tiap sesi testing.

**Pembagian tugas:** Backend Engineer 2 (solo track sprint ini, karena Backend 1 sedang di 4A).

---

## SPRINT 5A — Sales Brain Assembly

**Tujuan:** Menggabungkan model ML (3A) + pipeline (4A) jadi Adaptive Scoring Engine yang utuh: menerima state percakapan, menghasilkan keputusan bisnis, dan memicu response generation.

**Alasan urutan:** Butuh model dari 3A dan pipeline tahap 1-3 dari 4A sudah ada.

**Dependency:** Sprint 3A, Sprint 4A.

**Deliverables:** Fungsi end-to-end: input teks/voice pelanggan → output keputusan negosiasi + balasan natural.

**File dibuat:** `backend/app/pipeline/sales_brain/__init__.py`, `model_loader.py`, `scoring_engine.py`, `emotion.py`, `backend/app/pipeline/retrieval.py`, `response_generator.py`
**File dimodifikasi:** tidak ada.

**Output demo akhir sprint:** script test kirim pesan nego teks → keluar balasan AI yang sudah melalui scoring engine (bukan LLM bebas menentukan harga).

**Definition of Done:**
- [ ] `model_loader.py` berhasil load `scoring_model.pkl` dari Sprint 3A
- [ ] `scoring_engine.py` menghasilkan keputusan yang tidak pernah melanggar floor_price (test dengan kasus ekstrem)
- [ ] `emotion.py` mengklasifikasi sentimen dari pesan
- [ ] `response_generator.py` menyusun balasan natural sesuai keputusan + emosi

**Risiko:** Fitur input yang dipakai saat training (Sprint 3A) tidak persis sama dengan fitur yang tersedia real-time dari pipeline (Sprint 4A) — mismatch feature.
**Mitigasi:** AI/ML Engineer dan Backend 1 samakan definisi fitur SEBELUM mulai coding sprint ini (30 menit sync), bukan sesudah.

**Pembagian tugas:**
| Siapa | Kerjakan |
|---|---|
| AI/ML Engineer | `model_loader.py`, `scoring_engine.py`, `emotion.py` |
| Backend Engineer 1 | `retrieval.py` (pgvector), `response_generator.py`, wiring ke pipeline tahap 1-3 |

---

## SPRINT 5B — Business Copilot & Insights UI

**Tujuan:** Membangun UI halaman `insights` menampilkan laporan & rekomendasi Business Copilot (masih boleh pakai data mock terstruktur, backend-nya baru jadi di Sprint 7).

**Dependency:** Sprint 4B (pola wiring sudah établished).

**File dimodifikasi:** `app/(dashboard)/insights/page.tsx`, komponen chart terkait.

**Output demo akhir sprint:** halaman insights menampilkan card "ringkasan hari ini" + rekomendasi, siap di-swap ke data asli nanti.

**DoD:** UI insights lengkap, responsif, siap terima data asli.

**Tugas:** Frontend Engineer 1.

---

## SPRINT 5C — Customer Memory & Recommendations UI

**Tujuan:** UI untuk menampilkan riwayat/memori pelanggan dan rekomendasi produk yang pernah diberikan AI (di halaman `customers`, detail per pelanggan).

**Dependency:** Sprint 4B.

**File dimodifikasi:** `app/(dashboard)/customers/page.tsx` (tambah detail view), komponen terkait.

**Output demo akhir sprint:** klik 1 pelanggan → muncul riwayat memori & rekomendasi yang pernah diberikan.

**DoD:** UI detail pelanggan lengkap.

**Tugas:** Frontend Engineer 2.

---

## SPRINT 6 — WhatsApp Cloud API Integration

**Tujuan:** Menyambungkan seluruh AI Pipeline (Sprint 4A + 5A) ke WhatsApp Cloud API secara end-to-end.

**Alasan urutan:** Ini titik penyatuan semua pipeline backend — harus setelah Sales Brain (5A) selesai dan diuji terpisah, dan setelah Payment Flow (4C) selesai untuk loop transaksi lengkap.

**Dependency:** Sprint 5A, Sprint 4C.

**Deliverables:** Kirim voice note/teks ke nomor WA sandbox → dapat balasan AI yang sudah melalui pipeline lengkap → bisa checkout & bayar.

**File dibuat:** `backend/app/api/whatsapp_webhook.py`, `backend/app/services/whatsapp_client.py`
**File dimodifikasi:** `main.py`

**Output demo akhir sprint:** demo end-to-end pertama kali — kirim pesan WA sungguhan, dapat balasan AI sungguhan.

**Definition of Done:**
- [ ] Webhook verifikasi berhasil terdaftar di Meta Developer Console
- [ ] Pesan masuk WA memicu seluruh pipeline dan balasan terkirim kembali ke WA
- [ ] Alur checkout dari WA (Sprint 4C) berfungsi end-to-end

**Risiko:** Rate limit / policy WhatsApp Cloud API sandbox, atau delay ngrok.
**Mitigasi:** Siapkan video rekaman demo sebagai cadangan begitu 1x berhasil end-to-end, jangan andalkan live-only.

**Pembagian tugas:** Backend Engineer 2 (lead integrasi), dibantu Backend Engineer 1 untuk debugging pipeline kalau ada masalah di sisi AI Pipeline.

---

## SPRINT 7 — Business Copilot Service (Backend)

**Tujuan:** Scheduled job yang meringkas data harian + memberi rekomendasi aktif (bukan cuma laporan pasif), menulis ke tabel `business_insights`.

**Alasan urutan:** Butuh data `negotiation_logs`/`orders`/`messages` yang sudah terisi dari pipeline asli (Sprint 5A ke atas), bukan cuma data seed.

**Dependency:** Sprint 5A.

**Deliverables:** Endpoint/cron yang menghasilkan insight harian otomatis.

**File dibuat:** `backend/app/services/business_copilot.py`, endpoint trigger di `dashboard_api.py` (atau scheduled job terpisah).

**Output demo akhir sprint:** trigger manual → muncul insight baru di tabel `business_insights` dengan rekomendasi konkret (bukan generic).

**DoD:**
- [ ] Query agregat data harian berjalan benar
- [ ] Threshold rule untuk rekomendasi (misal "produk X ditawar >N kali, konversi rendah → sarankan promo") berfungsi
- [ ] Narasi LLM dari data agregat masuk akal dan spesifik

**Risiko:** Data terlalu sedikit (demo/testing) sehingga insight terasa generic/kosong.
**Mitigasi:** Pastikan data seed + hasil testing pipeline sebelumnya cukup untuk menghasilkan insight yang menarik saat demo.

**Pembagian tugas:** AI/ML Engineer (logic rekomendasi & prompt narasi) + Backend Engineer 1 (query agregat & endpoint). Berjalan paralel dengan Sprint 6 (beda subsistem).

---

## SPRINT 8 — AI Evaluation & Metrics

**Tujuan:** Mengukur metrik nyata yang sudah didefinisikan di proposal (Bagian 8): STT accuracy, intent accuracy, negotiation success rate, response time, avg discount, dst — dengan angka asli dari pengujian, bukan estimasi.

**Alasan urutan:** Baru bisa diukur setelah sistem end-to-end benar-benar jalan (Sprint 6).

**Dependency:** Sprint 6, Sprint 7.

**Deliverables:** Tabel evaluasi terisi angka nyata, siap dipakai di slide pitch.

**File dibuat:** `docs/ai-evaluation-report.md`

**Output demo akhir sprint:** dokumen evaluasi dengan angka yang bisa dipertanggungjawabkan saat sesi tanya-jawab juri.

**DoD:** semua baris di tabel AI Evaluation proposal terisi angka aktual dari sample uji (minimal 20-30 kasus per metrik).

**Risiko:** Angka ternyata tidak sebagus harapan (misal negotiation success rate rendah).
**Mitigasi:** Laporkan apa adanya — kredibilitas jujur lebih baik daripada angka dipoles. Kalau ada waktu, investigasi akar masalah dan perbaiki sebelum final.

**Pembagian tugas:** AI/ML Engineer memimpin, seluruh tim membantu menjalankan skenario uji (masing-masing coba beberapa kasus dari device masing-masing untuk variasi data).

---

## SPRINT 9 — End-to-End Hardening & Bugfixing

**Tujuan:** Uji seluruh alur berkali-kali, temukan dan perbaiki bug, pastikan tidak ada fitur yang "kadang jalan kadang tidak" saat demo.

**Dependency:** Sprint 8 (atau bisa mulai paralel dengan 8 begitu Sprint 6-7 selesai).

**Deliverables:** Sistem stabil untuk demo berulang kali tanpa gagal.

**File dimodifikasi:** bervariasi, sesuai bug yang ditemukan.

**Output demo akhir sprint:** demo end-to-end berhasil dijalankan 5x berturut-turut tanpa gagal oleh anggota tim berbeda.

**DoD:** checklist final proposal (Bagian 16) semua tercentang.

**Risiko:** Bug muncul di menit-menit akhir.
**Mitigasi:** Freeze fitur baru di sprint ini — HANYA bugfix, tidak ada penambahan fitur.

**Pembagian tugas:** Semua anggota tim menguji bagiannya masing-masing + saling silang uji bagian anggota lain (orang yang tidak menulis kode itu yang uji, supaya bug asumsi ketemu).

---

## SPRINT 10 — Demo Rehearsal & Final Pitch Prep (FINAL)

**Tujuan:** Latihan demo berulang, siapkan video cadangan, susun jawaban untuk pertanyaan juri (kontribusi AI, moat, evaluasi, keamanan), finalisasi slide.

**Dependency:** Sprint 9.

**Deliverables:** Tim siap tampil — demo lancar, jawaban tanya-jawab solid, video cadangan ada.

**Output akhir:** Demo Day.

**DoD:** seluruh checklist proposal Bagian 16 (final checklist) selesai, video cadangan direkam, one-sentence positioning dihafal semua anggota.

**Pembagian tugas:** Semua anggota — bagi peran siapa demo, siapa jawab pertanyaan teknis, siapa jawab pertanyaan bisnis.

---

*Dokumen ini adalah pedoman resmi pengembangan LARISKA AI hingga Demo Day. Update sprint-by-sprint seiring progres nyata (terutama angka di Sprint 8 — isi dengan hasil pengujian aktual, jangan diedit dokumen ini dengan angka perkiraan).*
