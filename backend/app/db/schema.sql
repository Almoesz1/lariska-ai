-- ============================================================
-- LARISKA AI — Database Schema
-- Target: Supabase PostgreSQL (jalankan di SQL Editor)
-- Sprint: 2A — Database Foundation
-- ============================================================
-- Urutan CREATE TABLE mengikuti urutan dependency foreign key:
-- customers, products (tanpa dependency)
-- -> conversations (depends: customers)
-- -> messages, negotiation_logs (depends: conversations, products)
-- -> orders (depends: customers, conversations, products)
-- -> payments, inventory_logs (depends: orders, products)
-- -> customer_memory, recommendations (depends: customers, products, conversations)
-- -> business_insights (independen, agregat)
-- ============================================================

-- ============================================================
-- 1. EXTENSIONS
-- ============================================================

-- pgcrypto menyediakan gen_random_uuid() untuk primary key UUID
create extension if not exists pgcrypto;

-- pgvector untuk product embedding (product recommendation retrieval)
create extension if not exists vector;


-- ============================================================
-- 2. SHARED FUNCTION: auto-update kolom updated_at
-- ============================================================

create or replace function set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

comment on function set_updated_at() is
  'Trigger function generik untuk mengisi kolom updated_at setiap kali row di-UPDATE.';


-- ============================================================
-- 3. TABLE: customers
-- ============================================================

create table customers (
  id uuid primary key default gen_random_uuid(),
  whatsapp_number varchar(20) not null,
  name varchar(255),
  email varchar(255),
  address text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz,

  constraint uq_customers_whatsapp_number unique (whatsapp_number)
);

comment on table customers is
  'Pelanggan UMKM. whatsapp_number adalah identitas utama pelanggan (bukan email).';
comment on column customers.deleted_at is
  'Soft delete — customer tidak pernah dihapus permanen karena direferensikan orders/payments (audit trail).';

create index idx_customers_deleted_at on customers (deleted_at) where deleted_at is null;

create trigger trg_customers_updated_at
  before update on customers
  for each row execute function set_updated_at();


-- ============================================================
-- 4. TABLE: products
-- ============================================================

create table products (
  id uuid primary key default gen_random_uuid(),
  name varchar(255) not null,
  description text,
  category varchar(100),
  price numeric(12,2) not null,
  floor_price numeric(12,2) not null,
  stock integer not null default 0,
  image_url text,
  embedding vector(768),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz,

  constraint chk_products_price_nonneg check (price >= 0),
  constraint chk_products_floor_price_nonneg check (floor_price >= 0),
  constraint chk_products_floor_price_le_price check (floor_price <= price),
  constraint chk_products_stock_nonneg check (stock >= 0)
);

comment on table products is
  'Katalog produk UMKM. floor_price adalah harga minimum yang boleh diberikan Adaptive Scoring Engine saat negosiasi — hard constraint di level database.';
comment on column products.embedding is
  'Vector embedding deskripsi produk (dimensi 768, sesuaikan dengan model embedding yang dipakai), untuk product recommendation via pgvector.';
comment on column products.deleted_at is
  'Soft delete — produk yang pernah ditransaksikan tidak boleh dihapus permanen agar riwayat order/negotiation_logs tetap valid.';

create index idx_products_active_category
  on products (category)
  where deleted_at is null and is_active = true;

create index idx_products_embedding_hnsw
  on products using hnsw (embedding vector_cosine_ops);

create trigger trg_products_updated_at
  before update on products
  for each row execute function set_updated_at();


-- ============================================================
-- 5. TABLE: conversations
-- ============================================================

create table conversations (
  id uuid primary key default gen_random_uuid(),
  customer_id uuid not null references customers(id) on delete restrict,
  channel varchar(20) not null default 'whatsapp',
  status varchar(20) not null default 'open',
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint chk_conversations_status check (status in ('open', 'closed', 'handed_over'))
);

comment on table conversations is
  'Satu sesi percakapan WhatsApp antara pelanggan dan Sales Brain. customer_id RESTRICT — riwayat percakapan tidak boleh hilang saat customer dihapus.';

create index idx_conversations_customer_id on conversations (customer_id);
create index idx_conversations_status on conversations (status);

create trigger trg_conversations_updated_at
  before update on conversations
  for each row execute function set_updated_at();


-- ============================================================
-- 6. TABLE: messages
-- ============================================================

create table messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references conversations(id) on delete cascade,
  sender_type varchar(20) not null,
  content_type varchar(20) not null default 'text',
  raw_text text,
  voice_url text,
  intent varchar(50),
  entities jsonb not null default '{}'::jsonb,
  sentiment varchar(20),
  created_at timestamptz not null default now(),

  constraint chk_messages_sender_type check (sender_type in ('customer', 'ai', 'admin')),
  constraint chk_messages_content_type check (content_type in ('text', 'voice'))
);

comment on table messages is
  'Log tiap pesan dalam percakapan. Kolom intent/entities/sentiment adalah output tahap 2 & 4b AI Pipeline (Intent/Entity Extraction, Emotion Classifier) — sekaligus jadi data mentah evaluasi AI. Tabel append-only, tanpa updated_at.';
comment on column messages.conversation_id is
  'ON DELETE CASCADE — pesan tidak bermakna tanpa percakapan induknya.';

create index idx_messages_conversation_created on messages (conversation_id, created_at);
create index idx_messages_intent on messages (intent) where intent is not null;


-- ============================================================
-- 7. TABLE: orders
-- ============================================================
-- Catatan desain: MVP hackathon merepresentasikan 1 produk per order
-- (tanpa tabel order_items), sesuai keputusan scope Sprint 2A.

create table orders (
  id uuid primary key default gen_random_uuid(),
  customer_id uuid not null references customers(id) on delete restrict,
  conversation_id uuid references conversations(id) on delete set null,
  product_id uuid not null references products(id) on delete restrict,
  quantity integer not null default 1,
  unit_price numeric(12,2) not null,
  discount_amount numeric(12,2) not null default 0,
  total_amount numeric(12,2) not null,
  status varchar(20) not null default 'pending',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint chk_orders_quantity_positive check (quantity > 0),
  constraint chk_orders_unit_price_nonneg check (unit_price >= 0),
  constraint chk_orders_discount_nonneg check (discount_amount >= 0),
  constraint chk_orders_total_nonneg check (total_amount >= 0),
  constraint chk_orders_status check (status in ('pending', 'paid', 'shipped', 'completed', 'cancelled')),
  constraint chk_orders_total_matches
    check (total_amount = (unit_price * quantity) - discount_amount)
);

comment on table orders is
  'Pesanan pelanggan. Desain MVP: 1 order = 1 produk (quantity bisa >1). Roadmap: pecah jadi order_items untuk multi-produk per order.';
comment on column orders.customer_id is
  'ON DELETE RESTRICT — data finansial tidak boleh hilang saat customer dihapus.';
comment on column orders.conversation_id is
  'ON DELETE SET NULL — order tetap valid walau riwayat percakapan asalnya dihapus.';

create index idx_orders_customer_id on orders (customer_id);
create index idx_orders_status on orders (status);
create index idx_orders_product_id on orders (product_id);
create index idx_orders_conversation_id on orders (conversation_id) where conversation_id is not null;

create trigger trg_orders_updated_at
  before update on orders
  for each row execute function set_updated_at();


-- ============================================================
-- 8. TABLE: payments
-- ============================================================

create table payments (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references orders(id) on delete restrict,
  method varchar(30) not null,
  status varchar(20) not null default 'pending',
  amount numeric(12,2) not null,
  provider_reference varchar(255),
  paid_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint chk_payments_method check (method in ('qris', 'bank_transfer', 'cod')),
  constraint chk_payments_status check (status in ('pending', 'success', 'failed', 'expired')),
  constraint chk_payments_amount_nonneg check (amount >= 0)
);

comment on table payments is
  'Transaksi pembayaran per order. status terpisah dari orders.status karena siklus hidup pembayaran bisa retry (tidak selalu 1:1 sinkron dengan status order).';
comment on column payments.provider_reference is
  'Transaction ID dari payment gateway (Midtrans/Xendit), untuk rekonsiliasi & webhook callback.';

create index idx_payments_order_id on payments (order_id);
create unique index uq_payments_provider_reference
  on payments (provider_reference)
  where provider_reference is not null;

create trigger trg_payments_updated_at
  before update on payments
  for each row execute function set_updated_at();


-- ============================================================
-- 9. TABLE: negotiation_logs
-- ============================================================

create table negotiation_logs (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references conversations(id) on delete cascade,
  product_id uuid not null references products(id) on delete restrict,
  customer_offer_price numeric(12,2),
  ai_decision varchar(30) not null,
  ai_offer_price numeric(12,2),
  floor_price_snapshot numeric(12,2) not null,
  model_confidence numeric(4,3),
  outcome varchar(20) not null default 'pending',
  created_at timestamptz not null default now(),

  constraint chk_negotiation_customer_offer_nonneg check (customer_offer_price >= 0),
  constraint chk_negotiation_ai_offer_nonneg check (ai_offer_price >= 0),
  constraint chk_negotiation_floor_snapshot_nonneg check (floor_price_snapshot >= 0),
  constraint chk_negotiation_ai_decision check (ai_decision in ('hold_price', 'discount', 'bonus', 'counter_offer')),
  constraint chk_negotiation_outcome check (outcome in ('accepted', 'rejected', 'pending')),
  constraint chk_negotiation_model_confidence check (model_confidence is null or model_confidence between 0 and 1)
);

comment on table negotiation_logs is
  'Log tiap giliran negosiasi dari Sales Brain / Adaptive Scoring Engine. Sumber data evaluasi (negotiation success rate, avg discount) dan retraining model ML (roadmap).';
comment on column negotiation_logs.floor_price_snapshot is
  'Snapshot floor_price produk pada saat negosiasi terjadi — sengaja terpisah dari products.floor_price yang bisa berubah, demi audit integrity.';
comment on column negotiation_logs.model_confidence is
  'Confidence score dari model ML Adaptive Scoring Engine (0-1), nullable karena fallback rule-based tidak selalu menghasilkan confidence score.';

create index idx_negotiation_logs_conversation_id on negotiation_logs (conversation_id);
create index idx_negotiation_logs_product_id on negotiation_logs (product_id);
create index idx_negotiation_logs_created_at on negotiation_logs (created_at);


-- ============================================================
-- 10. TABLE: customer_memory
-- ============================================================

create table customer_memory (
  id uuid primary key default gen_random_uuid(),
  customer_id uuid not null references customers(id) on delete cascade,
  memory_type varchar(50) not null,
  content jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint chk_customer_memory_type check (memory_type in ('preference', 'purchase_pattern', 'complaint', 'note'))
);

comment on table customer_memory is
  'Tabel fleksibel (memory_type + content JSONB) alih-alih kolom tetap, karena jenis memori akan berkembang seiring roadmap Digital Twin tanpa perlu migrasi skema.';

create index idx_customer_memory_customer_type on customer_memory (customer_id, memory_type);

create trigger trg_customer_memory_updated_at
  before update on customer_memory
  for each row execute function set_updated_at();


-- ============================================================
-- 11. TABLE: recommendations
-- ============================================================

create table recommendations (
  id uuid primary key default gen_random_uuid(),
  customer_id uuid not null references customers(id) on delete cascade,
  product_id uuid not null references products(id) on delete cascade,
  conversation_id uuid references conversations(id) on delete set null,
  reason text,
  similarity_score numeric(4,3),
  was_accepted boolean,
  created_at timestamptz not null default now(),

  constraint chk_recommendations_similarity check (similarity_score is null or similarity_score between 0 and 1)
);

comment on table recommendations is
  'Log tiap kali AI merekomendasikan produk ke pelanggan. was_accepted dipakai untuk mengukur efektivitas rekomendasi (AI Evaluation).';

create index idx_recommendations_customer_id on recommendations (customer_id);
create index idx_recommendations_product_id on recommendations (product_id);


-- ============================================================
-- 12. TABLE: business_insights
-- ============================================================

create table business_insights (
  id uuid primary key default gen_random_uuid(),
  insight_type varchar(50) not null,
  content jsonb not null,
  metric_snapshot jsonb,
  period_start timestamptz,
  period_end timestamptz,
  created_at timestamptz not null default now(),

  constraint chk_business_insights_type check (insight_type in ('daily_summary', 'promo_suggestion', 'peak_hour', 'other'))
);

comment on table business_insights is
  'Output Business Copilot (laporan & rekomendasi harian). Tidak ber-FK langsung ke tabel lain karena sifatnya agregat lintas tabel; direferensikan lewat period_start/period_end.';

create index idx_business_insights_type_created on business_insights (insight_type, created_at);


-- ============================================================
-- 13. TABLE: inventory_logs
-- ============================================================

create table inventory_logs (
  id uuid primary key default gen_random_uuid(),
  product_id uuid not null references products(id) on delete cascade,
  change_type varchar(20) not null,
  quantity_change integer not null,
  stock_before integer not null,
  stock_after integer not null,
  reference_order_id uuid references orders(id) on delete set null,
  created_at timestamptz not null default now(),

  constraint chk_inventory_change_type check (change_type in ('restock', 'sale', 'adjustment')),
  constraint chk_inventory_stock_before_nonneg check (stock_before >= 0),
  constraint chk_inventory_stock_after_nonneg check (stock_after >= 0),
  constraint chk_inventory_stock_consistency check (stock_after = stock_before + quantity_change)
);

comment on table inventory_logs is
  'Audit trail tiap perubahan stok. Mendukung fitur Sales Brain "sadar stok real-time" — Adaptive Scoring Engine membaca stock terkini dari sini/products.stock untuk keputusan negosiasi.';
comment on column inventory_logs.reference_order_id is
  'ON DELETE SET NULL — log stok tetap valid walau order terkait dihapus (RESTRICT di orders sebenarnya mencegah ini, kolom ini untuk jaga-jaga jika kebijakan order berubah).';

create index idx_inventory_logs_product_created on inventory_logs (product_id, created_at);
create index idx_inventory_logs_reference_order on inventory_logs (reference_order_id) where reference_order_id is not null;


-- ============================================================
-- SELESAI — 11 tabel, sesuai ERD Sprint 2A
-- ============================================================
