# Lampiran Teknis — Dataset, Model, Guardrail, dan Status MVP LARISKA AI

Dokumen ini menjawab pertanyaan teknis mengenai dataset, pelatihan model, evaluasi, integrasi LLM, guardrail, dan status MVP LARISKA AI. Isinya diturunkan dari artefak dan kode proyek yang tersedia per 24 Agustus 2026. Angka evaluasi tidak merepresentasikan kinerja pada transaksi UMKM riil; model saat ini dilatih menggunakan data sintetis berbasis heuristik bisnis sebagai bootstrap MVP.

---

## A. Dataset dan Data Generation

### A1. Nama dataset final

Nama final yang digunakan dalam proposal dan dokumentasi adalah **Synthetic Conversational Commerce Decision Dataset (SCCDD) v1**.

Nama file fisik yang digunakan model adalah `ml/data/synthetic_negotiation_data.csv`. Dataset memuat 5.000 observasi keputusan negosiasi e-commerce/UMKM dan digunakan untuk melatih *Adaptive Pricing Decision Model*.

Istilah “synthetic” harus tetap dicantumkan. Dataset bukan data transaksi riil dan tidak boleh diklaim sebagai hasil survei atau rekaman percakapan UMKM.

### A2. Struktur generator dan alur data

Struktur artefak:

```text
ml/
├── generate_synthetic_data.py
├── train_scoring_model.py
├── evaluate_model.py
├── data/
│   └── synthetic_negotiation_data.csv
└── model_artifacts/
    ├── scoring_model.pkl
    ├── label_encoder.pkl
    └── training_metadata.json
```

Alur reproduksi:

```text
generate_synthetic_data.py
  ├─ generate_raw_features()
  ├─ label_action() / heuristik bisnis
  ├─ inject controlled label noise (8%)
  └─ synthetic_negotiation_data.csv

train_scoring_model.py
  ├─ validasi data
  ├─ stratified train-test split
  ├─ LabelEncoder
  ├─ lightgbm.LGBMClassifier
  ├─ evaluasi metrik dan feature importance
  └─ model + encoder + metadata

evaluate_model.py
  ├─ muat ulang artefak
  ├─ evaluasi ulang test set yang identik
  └─ demo prediksi satu kasus
```

Library utama: `numpy`, `pandas`, `scikit-learn`, `lightgbm`, dan `joblib`. Seluruh randomisasi memakai `numpy.random.default_rng(42)` agar dapat direproduksi.

Perintah reproduksi dari folder `ml/`:

```bash
python generate_synthetic_data.py
python train_scoring_model.py
python evaluate_model.py
```

### A3. Enam fitur model

Generator langsung membuat enam fitur yang menjadi input model. Tidak ada normalisasi, standardisasi, atau preprocessing numerik tambahan sebelum masuk ke LightGBM.

| Fitur | Makna | Sumber pada runtime MVP |
|---|---|---|
| `margin_pct` | ruang margin produk: `(harga - floor_price) / harga` | harga dan floor price dari katalog Supabase |
| `stock_ratio` | kondisi stok yang dinormalisasi ke 0–1 | stok produk Supabase; pada MVP dinormalisasi terhadap ambang operasional 10 unit |
| `customer_loyalty` | tingkat loyalitas 0–1 | jumlah order pelanggan, dibatasi pada 10 order |
| `discount_requested_pct` | persentase diskon yang diminta | parser nominal tawaran dan jumlah unit pelanggan |
| `hour_of_day` | jam lokal saat negosiasi | waktu sistem backend |
| `is_peak_hour` | indikator jam ramai | 1 pada pukul 18.00–21.00, selainnya 0 |

`sentiment_score` juga dapat dihitung di backend sebagai enrichment dari klasifikasi emosi, tetapi artefak model v1 menggunakan enam fitur di atas agar kontrak training dan inferensi konsisten.

### A4. Distribusi fitur sintetis

| Fitur | Generator/distribusi | Rentang teoritis | Ringkasan dataset v1 |
|---|---|---:|---:|
| `margin_pct` | uniform | 0,05–0,50 | min 0,0502; maks 0,4999; rerata 0,2730 |
| `stock_ratio` | uniform | 0–1 | min 0,0003; maks 1,0000; rerata 0,4986 |
| `customer_loyalty` | Beta(2,5) | 0–1 | min 0,0061; maks 0,9125; rerata 0,2832 |
| `discount_requested_pct` | uniform | 0–0,60 | min 0,0000; maks 0,5999; rerata 0,2966 |
| `hour_of_day` | integer uniform | 0–23 | rerata 11,5334 |
| `is_peak_hour` | turunan dari jam | 0 atau 1 | rerata 0,1670 |

Distribusi ini adalah asumsi desain yang disengaja, bukan estimasi empiris. Distribusi Beta(2,5) dipilih agar populasi pelanggan baru/bertransaksi sedikit lebih dominan daripada pelanggan sangat loyal; ini masuk akal sebagai titik awal, tetapi akan diganti/ditinjau ulang dengan data pilot yang berizin.

---

## B. Strategi Labeling

### B1. Kelas target

Target `ai_decision` memiliki empat kelas:

| Label | Arti operasional |
|---|---|
| `hold_price` | pertahankan harga dasar; tidak ada diskon aman |
| `counter_offer` | berikan harga tengah yang aman untuk mendorong konversi |
| `discount` | diskon dapat diberikan dalam batas aman |
| `bonus` | harga dipertahankan, tetapi nilai tambah/bonus dapat dipertimbangkan |

### B2. Aturan pembentukan label

Setiap baris memperoleh rasio permintaan diskon terhadap margin:

```text
ratio = discount_requested_pct / max(margin_pct, 0.05)
stock_scarcity = 1 - stock_ratio

willingness =
    0,35 × customer_loyalty
  + 0,25 × stock_ratio
  - 0,10 × is_peak_hour
  + 0,20 × (1 - min(ratio, 1))
```

Kemudian label dasar ditentukan secara deterministik:

```text
IF ratio > 1,8
  THEN counter_offer
ELSE IF ratio > 1,0
  THEN hold_price
ELSE IF willingness > 0,42
    AND stock_scarcity < 0,5
    AND customer_loyalty > 0,35
  THEN bonus
ELSE IF willingness > 0,28
  THEN discount
ELSE
  hold_price
```

Maknanya: permintaan diskon yang jauh melampaui ruang margin tidak diterima mentah-mentah; pelanggan tetap dapat menerima *counter offer*. Diskon lebih mungkin bila nilai hubungan pelanggan dan kondisi stok mendukung. Bonus adalah strategi bernilai tambah pada kondisi yang cukup sehat tanpa menurunkan harga.

### B3. Sumber business rule

Sumber rule adalah **kombinasi desain tim/developer dan prinsip umum strategi pricing**, bukan hasil wawancara UMKM yang diklaim sebagai data primer. Dasar logikanya meliputi perlindungan margin, ketersediaan stok, loyalitas pelanggan, besar permintaan diskon, dan konteks jam ramai.

Untuk proposal, gunakan formulasi berikut:

> “Pada tahap bootstrap, aturan labeling disusun tim sebagai heuristik bisnis yang transparan berdasarkan prinsip margin protection, inventory awareness, dan customer relationship. Aturan ini bukan klaim hasil survei primer. Pada fase pilot, heuristik akan divalidasi bersama mitra UMKM dan model akan ditingkatkan melalui data negosiasi berizin.”

### B4. Distribusi label dataset

| Label | Jumlah | Proporsi |
|---|---:|---:|
| `hold_price` | 2.126 | 42,52% |
| `counter_offer` | 1.351 | 27,02% |
| `discount` | 1.192 | 23,84% |
| `bonus` | 331 | 6,62% |
| **Total** | **5.000** | **100%** |

Distribusi ini tidak sepenuhnya seimbang. Kelas `bonus` memang minoritas karena ia hanya relevan dalam kondisi loyalitas dan kesiapan stok tertentu.

---

## C. Controlled Label Noise

### C1. Definisi dan alasan 8%

Setelah label dasar ditentukan, generator melakukan *random label replacement* dengan probabilitas 8%. Ketika terpilih, label diganti secara acak dari empat kelas `hold_price`, `discount`, `bonus`, dan `counter_offer`.

Tujuannya bukan mensimulasikan angka error empiris yang telah terukur, melainkan mencegah data sintetis menjadi aturan yang terlalu sempurna. Tanpa noise, model berisiko menghafal rule generator dan menghasilkan skor 100% yang tidak realistis untuk dipresentasikan sebagai kesiapan dunia nyata.

Angka 8% adalah **asumsi desain bootstrap**, bukan hasil studi ablation 0%/5%/8%/10%. Proposal tidak boleh menyatakan bahwa 8% adalah angka optimal hasil eksperimen. Studi ablation merupakan pekerjaan lanjutan yang direkomendasikan sebelum versi riset/pilot berikutnya.

### C2. Posisi noise dalam proses

Noise diterapkan pada label di fungsi `label_action()` ketika dataset dibangkitkan, **sebelum** stratified train-test split. Setelah itu dataset dibagi 80:20 secara terstratifikasi. Tidak ada noise fitur dan tidak ada perubahan rule pada data yang sudah dibagi.

---

## D. Pengembangan Model

### D1. Model tepat yang digunakan

Artefak v1 menggunakan `lightgbm.LGBMClassifier` (`LGBMClassifier`) untuk klasifikasi multikelas empat tindakan negosiasi. Ada fallback `GradientBoostingClassifier` hanya apabila LightGBM tidak tersedia saat training, tetapi metadata artefak saat ini mencatat library `lightgbm` dan model `LGBMClassifier`.

### D2. Objective dan hyperparameter

Pemanggilan training saat ini adalah:

```python
model = LGBMClassifier(random_state=42)
```

Karena target memiliki empat kelas, LightGBM menangani tugas ini sebagai klasifikasi multikelas. `objective`, `num_class`, `learning_rate`, `n_estimators`, `max_depth`, `num_leaves`, `subsample`, dan `colsample_bytree` **tidak di-override** di skrip; nilainya mengikuti default versi LightGBM yang terpasang ketika artefak dilatih.

Ini penting secara ilmiah: proposal dapat menyebut “LightGBM multiclass dengan konfigurasi baseline reproducible dan `random_state=42`”, tetapi jangan mencantumkan angka hyperparameter khusus yang tidak tersimpan/ditetapkan eksplisit. Tuning hiperparameter dan pencatatan versi library adalah roadmap peningkatan berikutnya.

### D3. Preprocessing dan imbalance

- Enam fitur numerik masuk langsung ke LightGBM; tidak ada normalisasi atau standardisasi, karena model pohon tidak membutuhkannya.
- Label diubah ke integer menggunakan `sklearn.preprocessing.LabelEncoder` dan encoder disimpan sebagai artefak terpisah.
- Split memakai `stratify=y` agar proporsi empat kelas tetap terjaga pada train dan test.
- Tidak ada `class_weight`, `scale_pos_weight`, oversampling, atau undersampling pada v1.

Keterbatasan ini terlihat pada recall kelas `bonus` yang lebih rendah. Pada iterasi berikutnya, tim perlu membandingkan class weighting/oversampling dan mengevaluasi dampaknya pada macro-F1, khususnya kelas bonus.

---

## E. Training dan Evaluasi

### E1. Pembagian data

Dataset berisi 5.000 baris dan dibagi menggunakan `train_test_split(test_size=0.2, random_state=42, stratify=y)`:

| Bagian | Jumlah |
|---|---:|
| Train | 4.000 |
| Test | 1.000 |
| Total | 5.000 |

Tidak ada validation set terpisah atau cross-validation pada baseline v1. Test set dipegang untuk evaluasi akhir dan dapat direproduksi karena seed dan stratifikasi disimpan. *Cross-validation* serta validation set akan dipakai saat tuning versi berikutnya agar pemilihan hyperparameter tidak bergantung pada satu split.

### E2. Metrik test set

| Metrik | Nilai |
|---|---:|
| Accuracy | 0,8920 |
| Precision macro | 0,8912 |
| Recall macro | 0,8051 |
| Macro F1 | 0,8320 |
| Precision weighted | 0,8919 |
| Recall weighted | 0,8920 |
| Weighted F1 | 0,8874 |

Per kelas:

| Kelas | Precision | Recall | F1 | Support test |
|---|---:|---:|---:|---:|
| `bonus` | 0,8857 | 0,4697 | 0,6139 | 66 |
| `counter_offer` | 0,9231 | 0,9333 | 0,9282 | 270 |
| `discount` | 0,8714 | 0,8787 | 0,8750 | 239 |
| `hold_price` | 0,8847 | 0,9388 | 0,9110 | 425 |

Interpretasi yang tepat: baseline mampu membedakan sebagian besar pola heuristik sintetis, tetapi recall `bonus` relatif rendah. Oleh karena itu, model digunakan sebagai pemberi rekomendasi tindakan dan **bukan** otoritas harga akhir.

### E3. Confusion matrix

Baris adalah label aktual dan kolom adalah prediksi.

| Aktual \ Prediksi | bonus | counter_offer | discount | hold_price |
|---|---:|---:|---:|---:|
| bonus | 31 | 5 | 16 | 14 |
| counter_offer | 0 | 252 | 1 | 17 |
| discount | 3 | 5 | 210 | 21 |
| hold_price | 1 | 11 | 14 | 399 |

### E4. Feature importance

Nilai berikut adalah *normalized feature importance* dari artefak LightGBM v1.

| Fitur | Importance |
|---|---:|
| `discount_requested_pct` | 24,89% |
| `margin_pct` | 23,25% |
| `stock_ratio` | 21,67% |
| `customer_loyalty` | 19,68% |
| `hour_of_day` | 8,79% |
| `is_peak_hour` | 1,73% |

Hasil ini mendukung desain produk: besarnya diskon yang diminta, ruang margin, stok, dan loyalitas menjadi sinyal paling dominan. Importance bukan bukti kausalitas dan tidak boleh diartikan sebagai pengaruh kausal terhadap perilaku pelanggan riil.

---

## F. Integrasi Gemini, LightGBM, dan Sistem Operasional

### F1. Alur end-to-end

```text
Pesan teks / voice note WhatsApp Cloud API
        │
        ├─ Voice note → Whisper local STT (fallback Gemini audio bila perlu)
        │
        ├─ Gemini → ekstraksi intent dan entitas
        │             (produk, jumlah, nominal tawaran, kategori)
        ├─ Gemini → klasifikasi emosi
        │
        ├─ Backend Python + Supabase → produk, harga, floor price, stok,
        │                               riwayat order dan konteks percakapan
        │
        ├─ Feature builder deterministik → 6 fitur numerik
        ├─ LightGBM → usulan aksi negosiasi + confidence
        ├─ Python hard guardrails → aksi/harga final aman
        │
        ├─ Response generator → teks Indonesia kontekstual
        │   (angka keputusan dimasukkan dari guardrail, tidak ditentukan LLM)
        │
        └─ WhatsApp → respons / invoice Midtrans → webhook pembayaran
                                      │
                                      └─ Supabase order, payment, stok, log
```

### F2. Siapa membentuk fitur runtime

- **Gemini** memahami bahasa: intent, nama produk, kategori, jumlah, dan nominal tawaran; ia juga dipakai untuk klasifikasi emosi serta penyusunan teks natural.
- **Parser/backend Python** memverifikasi dan menghitung fitur angka. Contohnya, nominal total tawaran dibagi jumlah unit kecuali pelanggan menyebut “per pcs/per unit”.
- **Supabase** menyediakan harga, floor price, stok aktual, dan riwayat order pelanggan.
- **Python** menghitung `margin_pct`, `stock_ratio`, `customer_loyalty`, dan `discount_requested_pct` secara deterministik.
- **LightGBM** hanya menghasilkan usulan aksi berdasarkan enam fitur.

Dengan demikian, Gemini tidak menentukan harga final. Jika NLU menghasilkan nama produk yang tidak benar-benar disebut pelanggan, backend menolaknya agar tidak terjadi keputusan harga untuk produk yang dihalusinasikan.

### F3. Status koneksi model pada MVP

Model benar-benar terhubung dalam alur MVP live, bukan sekadar CSV-to-model demo. Saat pesan negosiasi WhatsApp masuk, backend memuat artefak `scoring_model.pkl`, menjalankan prediksi LightGBM, menerapkan guardrail, mencatat `negotiation_logs`, dan mengirim jawaban berdasarkan payload keputusan tersebut.

---

## G. Guardrail dan Safety

### G1. Floor price protection

Aturan inti:

```text
final_price = max(calculated_price, floor_price)
```

Floor price berasal dari data produk di Supabase. Guardrail juga menghitung:

```text
effective_max_discount = min(
    max_discount_pct,
    (product_price - floor_price) / product_price
)
```

Pada MVP, `max_discount_pct` default adalah 25%, tetapi diskon aktual tetap tidak dapat melampaui ruang antara harga jual dan floor price.

### G2. Perilaku saat prediksi model berisiko

| Kondisi | Tindakan sistem |
|---|---|
| Model menyarankan `discount` tetapi ruang diskon nol | diubah menjadi `hold_price` |
| Model menyarankan diskon melebihi batas | diskon dipangkas pada batas aman |
| Model menyarankan `counter_offer` | backend menawarkan paling banyak setengah diskon yang diminta, lalu membatasi pada batas aman |
| Model menyarankan `hold_price`, tetapi ada tawaran dan margin aman | backend dapat memberi `counter_offer` aman untuk menjaga peluang konversi |
| Harga produk tidak valid | `hold_price`, harga 0, dan alasan dicatat sebagai invalid |

Guardrail lainnya mencakup validasi stok sebelum checkout, reservation/confirmation stok pada pembayaran, validasi status pembayaran Midtrans, idempotensi webhook, serta audit trail negosiasi dan inventory log. LARISKA bukan sistem refund otomatis; refund dan pembatalan operasional penuh belum menjadi fitur yang diklaim selesai pada MVP ini.

---

## H. Status MVP dan Demo

MVP LARISKA AI sudah berjalan sebagai integrasi nyata WhatsApp Cloud API + FastAPI + Supabase + Midtrans Sandbox. Dashboard Next.js menampilkan operasional produk, pelanggan, order, pembayaran, dan insight.

| Fitur | Status MVP | Keterangan |
|---|---|---|
| WhatsApp real integration | Selesai | Meta WhatsApp Cloud API menerima dan membalas pesan |
| Chat AI | Selesai | intent, emosi, konteks, serta respons Bahasa Indonesia |
| Voice note transcription | Selesai | Whisper lokal; fallback cloud jika diperlukan |
| Rekomendasi/kategori produk | Selesai | katalog aktif, kategori, stok, harga, dan satuan dari Supabase |
| Pricing decision | Selesai | LightGBM + hard guardrail Python |
| Negosiasi | Selesai | counter-offer deterministik dan floor-price protected |
| Customer memory | Selesai | konteks percakapan, produk, jumlah, dan riwayat negosiasi |
| Human handover | Selesai | percakapan tertentu dapat dieskalasi ke admin |
| Checkout/invoice | Selesai | invoice dan payment link dikirim melalui WhatsApp |
| Pembayaran | Selesai untuk Sandbox | Midtrans Sandbox; status diproses via webhook |
| Update stok dan inventory log | Selesai | setelah settlement yang tervalidasi |
| Dashboard operasional | Selesai | produk, customer, order, status pembayaran, insight |
| Pelacakan pengiriman | Parsial/roadmap | status order tersedia; integrasi kurir real belum diklaim |
| Cancel order | Parsial | jalur aman backend ada pada kegagalan checkout; UI/flow pembatalan pelanggan belum diposisikan sebagai fitur lengkap |
| Refund otomatis | Belum | bukan klaim MVP |

### Alur demo yang direkomendasikan

1. Pelanggan mengirim voice note berisi produk, jumlah, dan tawaran harga.
2. Whisper menampilkan kemampuan STT Bahasa Indonesia.
3. LARISKA mengambil produk/harga/stok nyata, lalu LightGBM memberi usulan tindakan.
4. Hard guardrail memberi counter-offer di atas floor price.
5. Pelanggan menyetujui dan mengetik `checkout`.
6. Sistem mengirim invoice/link Midtrans Sandbox.
7. Setelah pembayaran settlement, webhook mengubah order menjadi `paid`, payment menjadi `success`, dan stok/log inventori diperbarui.
8. Dashboard dipakai untuk menunjukkan bukti jejak order, pembayaran, negosiasi, dan stok.

---

## I. Keterbatasan, Etika Data, dan Roadmap

1. **Dataset saat ini sintetis.** Metrik model menunjukkan kecocokan terhadap test split dari data sintetis yang sama, bukan prediksi keberhasilan negosiasi pada UMKM riil.
2. **Tidak mengklaim data pribadi pelanggan untuk training.** Pesan dan data transaksi harus dikelola sesuai persetujuan, tujuan layanan, dan prinsip minimisasi data.
3. **LLM tidak mengendalikan harga.** Hal ini mengurangi risiko halusinasi atau diskon yang merugikan UMKM.
4. **Pilot dan retraining.** Setelah cukup `negotiation_logs` dan outcome transaksi berizin terkumpul, data dianonimkan, dikurasi, dilabeli/ditinjau bersama mitra UMKM, lalu digunakan untuk evaluasi ulang, ablation noise, cross-validation, imbalance treatment, dan retraining terkontrol.
5. **Metrik bisnis berikutnya.** Selain accuracy model, fase pilot perlu melacak conversion rate, acceptance rate counter-offer, response time, stock-out prevention, escalation rate, dan kepuasan pelaku UMKM/pelanggan.

Dengan posisi ini, LARISKA AI bukan sekadar chatbot: ia adalah *Sales Brain* hibrida yang menggabungkan pemahaman bahasa, keputusan terukur, perlindungan margin, pembayaran, dan observabilitas operasional—dengan batas klaim teknis yang transparan dan roadmap validasi dunia nyata yang jelas.

---

## J. Konfirmasi Teknis Tambahan untuk Formulasi Model

### J1. Formulasi multiclass dan arti label

`LGBMClassifier` digunakan untuk klasifikasi multikelas empat label. Script tidak menetapkan `objective` secara eksplisit; LightGBM menginferensi objective multiclass dari target yang memiliki empat kelas setelah `LabelEncoder`. Urutan kelas encoder artefak adalah `bonus=0`, `counter_offer=1`, `discount=2`, `hold_price=3`.

| Label | Makna bisnis | Perlakuan akhir guardrail |
|---|---|---|
| `hold_price` | ruang diskon tidak cukup atau permintaan terlalu besar | harga dasar dipertahankan; bila ada ruang margin dan tawaran eksplisit, guardrail dapat mengubahnya menjadi counter-offer aman |
| `counter_offer` | permintaan pelanggan belum aman untuk diterima penuh | sistem menawarkan titik tengah diskon yang diminta dan batas aman |
| `discount` | diskon layak dipertimbangkan menurut pola fitur | diskon dibatasi oleh max discount dan floor price |
| `bonus` | nilai tambah lebih sesuai daripada menurunkan harga | harga tidak diturunkan oleh action bonus; representasi bonus spesifik berada pada kebijakan bisnis/operasional |

### J2. Kontrak fitur final

Tidak ada fitur ketujuh yang masuk ke artefak `scoring_model.pkl` v1. Urutan finalnya persis:

```text
[margin_pct, stock_ratio, customer_loyalty,
 discount_requested_pct, hour_of_day, is_peak_hour]
```

Definisi runtime:

```text
margin_pct              = max((product_price - floor_price) / product_price, 0)
stock_ratio             = clamp(stock_saat_ini / 10, 0, 1)
customer_loyalty        = clamp(jumlah_order_paid_or_completed / 10, 0, 1)
discount_requested_pct  = clamp((harga_awal - harga_tawaran_per_unit) / harga_awal, 0, 1)
hour_of_day             = jam server lokal, integer 0–23
is_peak_hour            = 1 jika 18 <= hour_of_day <= 21, selainnya 0
```

`margin_pct` pada MVP merupakan **ruang harga aman antara selling price dan floor price**, bukan margin akuntansi berbasis biaya modal. Jika biaya modal kelak tersedia secara andal, definisi dan dataset harus diperbarui lalu model dilatih ulang.

### J3. Preprocessing, hyperparameter, dan tuning

- Fitur numerik tidak di-scale, dinormalisasi, atau ditransformasi sebelum LightGBM. `is_peak_hour` masuk sebagai integer biner `0`/`1`.
- Label di-encode menggunakan `LabelEncoder`; artefak encoder disimpan agar mapping inferensi konsisten.
- Training memakai `LGBMClassifier(random_state=42)`; tidak ada Grid Search, Random Search, atau tuning manual pada v1.
- Karena parameter lain tidak di-override, nilai `n_estimators`, `learning_rate`, `num_leaves`, `max_depth`, `subsample`, dan `colsample_bytree` mengikuti default versi LightGBM pada environment training. `objective` juga diserahkan pada inferensi otomatis LightGBM untuk target multiclass.

Formulasi aman untuk proposal:

> “Model baseline menggunakan LightGBM multiclass dengan konfigurasi default `LGBMClassifier` dan `random_state=42`. Hyperparameter tuning belum dilakukan; tahap berikutnya akan memakai validation/cross-validation dan pencatatan versi library agar eksperimen sepenuhnya terkendali.”

### J4. Output, confidence, dan explainability

Model menghasilkan label prediksi dan probabilitas kelas melalui `predict_proba`; backend mengembalikan `ml_suggested_action` dan `ml_confidence` (probabilitas kelas prediksi) di payload keputusan. Pada v1 tidak ada *confidence threshold* yang menolak prediksi rendah. Hal ini aman karena harga akhir tetap wajib melewati guardrail deterministik, terlepas dari confidence model.

Penjelasan operasional tersedia melalui `guard_reason`, `floor_price_locked`, `applied_discount_pct`, log negosiasi, serta log inventory/payment pada Supabase. Ini adalah **explainability berbasis aturan bisnis**, bukan SHAP. Feature importance yang dilaporkan berasal dari atribut bawaan `feature_importances_` LightGBM, dinormalisasi terhadap total nilai importance; script tidak menetapkan `importance_type` secara eksplisit dan tidak memakai SHAP.

### J5. Uji input percakapan

Pipeline live telah diuji dengan pesan/voice note berisi produk, kuantitas, dan nominal tawaran. Contoh: “Aku mau beli Kopi Arabica 2 bungkus, boleh seharga Rp40.000?” dipetakan menjadi produk Kopi Arabica, kuantitas 2, dan tawaran total Rp40.000; backend mengonversinya menjadi harga tawaran per unit untuk menghitung `discount_requested_pct`, menjalankan LightGBM, dan kemudian mengunci counter-offer pada harga yang tidak melampaui floor price.

Pesan umum seperti “Kak bisa kurang harga nggak?” belum memiliki nominal diskon sehingga tidak cukup untuk menghasilkan `discount_requested_pct` yang bermakna. Dalam kondisi itu LARISKA meminta produk dan/atau nominal tawaran terlebih dahulu, bukan mengarang keputusan harga.
