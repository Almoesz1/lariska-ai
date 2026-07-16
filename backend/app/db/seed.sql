-- ============================================================
-- LARISKA AI — Seed Data
-- Jalankan SETELAH schema.sql berhasil dieksekusi.
-- Data sintetis untuk demo UMKM Indonesia (fashion, F&B, sparepart,
-- aksesoris, elektronik, kebutuhan harian) — saling berelasi
-- sehingga dashboard langsung punya data begitu di-run.
-- ============================================================

-- ============================================================
-- 1. PRODUCTS (30 produk)
-- ============================================================

insert into products (name, description, category, price, floor_price, stock, is_active)
select
  p.name,
  'Produk UMKM berkualitas — ' || p.name,
  p.category,
  p.price,
  round(p.price * 0.85, -3),
  (10 + (row_number() over ()) * 3 % 40)::int,
  true
from (
  select * from (values
    ('Kemeja Flanel Pria', 'Fashion', 120000::numeric),
    ('Dress Batik Wanita', 'Fashion', 185000),
    ('Sepatu Futsal Sintetis', 'Fashion', 250000),
    ('Tas Selempang Kanvas', 'Fashion', 95000),
    ('Kaos Polos Cotton Combed 30s', 'Fashion', 55000),
    ('Celana Jeans Slim Fit Pria', 'Fashion', 175000),
    ('Jaket Hoodie Unisex', 'Fashion', 150000),
    ('Sandal Jepit Karet', 'Fashion', 35000),
    ('Kopi Robusta Gayo 250g', 'F&B', 45000),
    ('Gula Aren Premium 500g', 'F&B', 28000),
    ('Keripik Singkong Balado 200g', 'F&B', 18000),
    ('Sambal Bawang Homemade 150g', 'F&B', 22000),
    ('Kerupuk Udang Sidoarjo 250g', 'F&B', 25000),
    ('Teh Herbal Celup Kotak', 'F&B', 20000),
    ('Sparepart Rem Cakram Motor Matic', 'Sparepart', 85000),
    ('Oli Mesin Motor 1 Liter', 'Sparepart', 65000),
    ('Filter Udara Motor Universal', 'Sparepart', 35000),
    ('Kabel Gas Motor Universal', 'Sparepart', 30000),
    ('Busi Racing Motor', 'Sparepart', 40000),
    ('Topi Baseball Cap', 'Aksesoris', 45000),
    ('Dompet Kulit Pria', 'Aksesoris', 95000),
    ('Ikat Pinggang Kulit', 'Aksesoris', 75000),
    ('Kacamata Hitam UV Protection', 'Aksesoris', 65000),
    ('Bantal Leher Travel', 'Aksesoris', 40000),
    ('Powerbank 10000mAh', 'Elektronik', 150000),
    ('Case HP Silikon Custom', 'Elektronik', 25000),
    ('Charger USB-C Fast Charging', 'Elektronik', 55000),
    ('Botol Minum Tumbler 500ml', 'Kebutuhan Harian', 45000),
    ('Tumbler Stainless Steel 1L', 'Kebutuhan Harian', 85000),
    ('Hand Sanitizer 100ml', 'Kebutuhan Harian', 15000)
  ) as t(name, category, price)
) p;


-- ============================================================
-- 2. CUSTOMERS (20 pelanggan)
-- ============================================================

insert into customers (whatsapp_number, name, email, address)
select
  '62812' || lpad((1000000 + (row_number() over ()) * 137)::text, 7, '0'),
  c.name,
  lower(replace(c.name, ' ', '.')) || '@example.com',
  c.address
from (
  select * from (values
    ('Budi Santoso', 'Jl. Merdeka No. 12, Surabaya'),
    ('Siti Nurhaliza', 'Jl. Pahlawan No. 5, Gresik'),
    ('Andi Wijaya', 'Jl. Diponegoro No. 8, Malang'),
    ('Dewi Lestari', 'Jl. Ahmad Yani No. 21, Sidoarjo'),
    ('Rudi Hartono', 'Jl. Sudirman No. 3, Surabaya'),
    ('Rina Susanti', 'Jl. Gajah Mada No. 17, Gresik'),
    ('Agus Setiawan', 'Jl. Veteran No. 9, Malang'),
    ('Maya Puspita', 'Jl. Kartini No. 14, Sidoarjo'),
    ('Eko Prasetyo', 'Jl. Basuki Rahmat No. 6, Surabaya'),
    ('Wulan Sari', 'Jl. Panglima Sudirman No. 11, Gresik'),
    ('Hendra Gunawan', 'Jl. Raya Darmo No. 22, Surabaya'),
    ('Fitri Handayani', 'Jl. Kenjeran No. 4, Surabaya'),
    ('Joko Susilo', 'Jl. Ijen No. 19, Malang'),
    ('Ratna Sari', 'Jl. Majapahit No. 2, Sidoarjo'),
    ('Bambang Wibowo', 'Jl. Rungkut No. 15, Surabaya'),
    ('Indah Permata', 'Jl. Wonokromo No. 7, Surabaya'),
    ('Dedi Kurniawan', 'Jl. Semeru No. 10, Gresik'),
    ('Sri Wahyuni', 'Jl. Bromo No. 13, Malang'),
    ('Yanto Saputra', 'Jl. Arjuna No. 18, Sidoarjo'),
    ('Lina Marlina', 'Jl. Anjasmoro No. 20, Surabaya')
  ) as t(name, address)
) c;


-- ============================================================
-- 3. CONVERSATIONS (25 sesi percakapan)
-- ============================================================

insert into conversations (customer_id, channel, status, started_at)
select
  cust.id,
  'whatsapp',
  case when g % 6 = 0 then 'closed' when g % 11 = 0 then 'handed_over' else 'open' end,
  now() - make_interval(days => trunc(random() * 30)::int, mins => trunc(random() * 1440)::int)
from generate_series(1, 25) as g
join lateral (select id from customers order by random() limit 1) cust on true;


-- ============================================================
-- 4. MESSAGES (200 pesan)
-- ============================================================

insert into messages (conversation_id, sender_type, content_type, raw_text, intent, entities, sentiment, created_at)
select
  conv.id,
  case when g % 2 = 0 then 'ai' else 'customer' end,
  case when g % 17 = 0 then 'voice' else 'text' end,
  m.txt,
  m.intent,
  '{}'::jsonb,
  m.sentiment,
  now() - make_interval(days => trunc(random() * 30)::int, mins => trunc(random() * 1440)::int)
from generate_series(1, 200) as g
join lateral (select id from conversations order by random() limit 1) conv on true
join lateral (
  select * from (values
    ('Halo kak, ini masih ready?', 'tanya_stok', 'netral'),
    ('Boleh kurang gak harganya kak?', 'nego', 'santai'),
    ('200 ribu ya kak, bisa?', 'nego', 'santai'),
    ('Oke deal, saya order ya', 'checkout', 'senang'),
    ('Kok lama banget responnya, saya udah nunggu dari tadi', 'komplain', 'marah'),
    ('Ada warna/ukuran lain gak kak?', 'tanya_produk', 'netral'),
    ('Ongkirnya berapa ya ke Sidoarjo', 'tanya_ongkir', 'netral'),
    ('Baik terima kasih infonya', 'lainnya', 'netral'),
    ('Ready ta iki? Piro regane?', 'tanya_harga', 'netral'),
    ('Boleh kurang gak kak, budget mepet nih', 'nego', 'terburu_buru'),
    ('Mantap, langsung saya bayar QRIS', 'checkout', 'senang'),
    ('Ini kok beda sama yang di foto', 'komplain', 'marah'),
    ('Rekomendasiin produk lain dong yang mirip', 'tanya_rekomendasi', 'santai')
  ) as t(txt, intent, sentiment)
  order by random() limit 1
) m on true;


-- ============================================================
-- 5. ORDERS (50 pesanan)
-- ============================================================

insert into orders (customer_id, conversation_id, product_id, quantity, unit_price, discount_amount, total_amount, status, created_at)
select
  o.customer_id, o.conversation_id, o.product_id, o.quantity, o.unit_price,
  o.discount_amount, o.subtotal - o.discount_amount, o.status, o.created_at
from (
  select
    cust.id as customer_id,
    conv.id as conversation_id,
    prod.id as product_id,
    prod.price as unit_price,
    qty.val as quantity,
    (prod.price * qty.val) as subtotal,
    round((prod.price * qty.val * disc.pct)::numeric, 0) as discount_amount,
    st.val as status,
    now() - make_interval(days => trunc(random() * 30)::int, mins => trunc(random() * 1440)::int) as created_at
  from generate_series(1, 50) as g
  join lateral (select id from customers order by random() limit 1) cust on true
  join lateral (select id from conversations order by random() limit 1) conv on true
  join lateral (select id, price from products order by random() limit 1) prod on true
  join lateral (select (1 + trunc(random() * 3))::int as val) qty on true
  join lateral (select (trunc(random() * 4) * 0.05) as pct) disc on true
  join lateral (select (array['pending', 'paid', 'shipped', 'completed', 'cancelled'])[1 + trunc(random() * 5)::int] as val) st on true
) o;


-- ============================================================
-- 6. PAYMENTS (30 pembayaran, dari order yang statusnya lanjut ke pembayaran)
-- ============================================================

insert into payments (order_id, method, status, amount, provider_reference, paid_at, created_at)
select
  ord.id,
  (array['qris', 'bank_transfer', 'cod'])[1 + trunc(random() * 3)::int],
  case when ord.status in ('paid', 'shipped', 'completed') then 'success'
       else (array['pending', 'failed', 'expired'])[1 + trunc(random() * 3)::int] end,
  ord.total_amount,
  'TRX-' || upper(substr(md5(random()::text || ord.id::text), 1, 10)),
  case when ord.status in ('paid', 'shipped', 'completed') then ord.created_at + interval '10 minutes' else null end,
  ord.created_at + interval '5 minutes'
from (select id, total_amount, status, created_at from orders order by random() limit 30) ord;


-- ============================================================
-- 7. NEGOTIATION_LOGS (100 log negosiasi)
-- ============================================================

insert into negotiation_logs (conversation_id, product_id, customer_offer_price, ai_decision, ai_offer_price, floor_price_snapshot, model_confidence, outcome, created_at)
select
  conv.id,
  prod.id,
  round((prod.price * (0.6 + random() * 0.3))::numeric, 0),
  decision.val,
  round((prod.floor_price * (1 + random() * 0.1))::numeric, 0),
  prod.floor_price,
  round((0.6 + random() * 0.4)::numeric, 3),
  (array['accepted', 'rejected', 'pending'])[1 + trunc(random() * 3)::int],
  now() - make_interval(days => trunc(random() * 30)::int, mins => trunc(random() * 1440)::int)
from generate_series(1, 100) as g
join lateral (select id from conversations order by random() limit 1) conv on true
join lateral (select id, price, floor_price from products order by random() limit 1) prod on true
join lateral (select (array['hold_price', 'discount', 'bonus', 'counter_offer'])[1 + trunc(random() * 4)::int] as val) decision on true;


-- ============================================================
-- 8. CUSTOMER_MEMORY (20 entri, 1 per pelanggan)
-- ============================================================

insert into customer_memory (customer_id, memory_type, content, created_at)
select
  c.id,
  (array['preference', 'purchase_pattern', 'complaint', 'note'])[1 + trunc(random() * 4)::int],
  jsonb_build_object(
    'summary', 'Catatan otomatis untuk ' || c.name,
    'generated_by', 'seed_script'
  ),
  now() - make_interval(days => trunc(random() * 15)::int)
from customers c;


-- ============================================================
-- 9. RECOMMENDATIONS (40 entri — tambahan agar dashboard/testing lengkap,
--    di luar daftar minimal Step 5 namun bagian dari 11 tabel skema)
-- ============================================================

insert into recommendations (customer_id, product_id, conversation_id, reason, similarity_score, was_accepted, created_at)
select
  cust.id, prod.id, conv.id,
  'Direkomendasikan berdasarkan kemiripan kategori & riwayat pembelian pelanggan',
  round((0.5 + random() * 0.5)::numeric, 3),
  (random() < 0.4),
  now() - make_interval(days => trunc(random() * 30)::int)
from generate_series(1, 40) as g
join lateral (select id from customers order by random() limit 1) cust on true
join lateral (select id from products order by random() limit 1) prod on true
join lateral (select id from conversations order by random() limit 1) conv on true;


-- ============================================================
-- 10. BUSINESS_INSIGHTS (10 ringkasan harian — Business Copilot)
-- ============================================================

insert into business_insights (insight_type, content, metric_snapshot, period_start, period_end, created_at)
select
  'daily_summary',
  jsonb_build_object(
    'total_chats', 50 + trunc(random() * 100)::int,
    'failed_checkout', trunc(random() * 20)::int,
    'note', 'Ringkasan otomatis harian (data simulasi seed)'
  ),
  jsonb_build_object('conversion_rate', round((0.1 + random() * 0.3)::numeric, 2)),
  (current_date - g),
  (current_date - g + 1),
  now() - (g || ' days')::interval
from generate_series(1, 10) as g;


-- ============================================================
-- 11. INVENTORY_LOGS (40 log perubahan stok)
-- ============================================================

insert into inventory_logs (product_id, change_type, quantity_change, stock_before, stock_after, reference_order_id, created_at)
select
  prod.id,
  ct.val,
  ct.qty,
  base.stock_before,
  greatest(base.stock_before + ct.qty, 0),
  ord.id,
  now() - make_interval(days => trunc(random() * 30)::int)
from generate_series(1, 40) as g
join lateral (select id from products order by random() limit 1) prod on true
join lateral (select (10 + trunc(random() * 40))::int as stock_before) base on true
join lateral (select (array['restock', 'sale', 'adjustment'])[1 + trunc(random() * 3)::int] as val) ct0 on true
join lateral (
  select
    ct0.val as val,
    case
      when ct0.val = 'restock' then (5 + trunc(random() * 10))::int
      when ct0.val = 'sale' then -(1 + trunc(random() * 3))::int
      else (trunc(random() * 6) - 3)::int
    end as qty
) ct on true
left join lateral (select id from orders order by random() limit 1) ord on ct.val = 'sale';


-- ============================================================
-- SELESAI — cek jumlah baris tiap tabel
-- ============================================================

select 'products' as table_name, count(*) from products
union all select 'customers', count(*) from customers
union all select 'conversations', count(*) from conversations
union all select 'messages', count(*) from messages
union all select 'orders', count(*) from orders
union all select 'payments', count(*) from payments
union all select 'negotiation_logs', count(*) from negotiation_logs
union all select 'customer_memory', count(*) from customer_memory
union all select 'recommendations', count(*) from recommendations
union all select 'business_insights', count(*) from business_insights
union all select 'inventory_logs', count(*) from inventory_logs;
