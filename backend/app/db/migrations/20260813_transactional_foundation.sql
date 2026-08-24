-- LARISKA AI — Transactional Foundation Migration
-- Aman dijalankan berulang di Supabase SQL Editor.
-- Tidak mengubah kontrak Sales Brain, floor price, maupun data historis.

begin;

-- Katalog universal (tetap kompatibel dengan katalog lama).
alter table products
  add column if not exists sku varchar(64),
  add column if not exists unit_label varchar(80),
  add column if not exists reorder_point integer not null default 5,
  add column if not exists specifications jsonb not null default '{}'::jsonb,
  add column if not exists search_aliases text[] not null default '{}'::text[];

-- 1. Audit dan idempotensi webhook (Meta / Midtrans).
create table if not exists webhook_events (
  id uuid primary key default gen_random_uuid(),
  provider varchar(30) not null,
  external_event_id varchar(255) not null,
  event_type varchar(80) not null,
  processing_status varchar(20) not null default 'received',
  payload jsonb not null default '{}'::jsonb,
  processed_at timestamptz,
  last_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint chk_webhook_events_provider check (provider in ('meta_whatsapp', 'midtrans')),
  constraint chk_webhook_events_status check (processing_status in ('received', 'processing', 'processed', 'failed')),
  constraint uq_webhook_events_provider_external unique (provider, external_event_id)
);

create index if not exists idx_webhook_events_retry
  on webhook_events (processing_status, updated_at)
  where processing_status in ('received', 'processing', 'failed');

drop trigger if exists trg_webhook_events_updated_at on webhook_events;
create trigger trg_webhook_events_updated_at
  before update on webhook_events
  for each row execute function set_updated_at();

-- Atomically claim one event. A stale processing claim may be retried after 5 minutes.
create or replace function claim_webhook_event(
  p_provider varchar,
  p_external_event_id varchar,
  p_event_type varchar,
  p_payload jsonb default '{}'::jsonb
) returns boolean
language plpgsql
as $$
declare
  v_id uuid;
begin
  insert into webhook_events (provider, external_event_id, event_type, processing_status, payload)
  values (p_provider, p_external_event_id, p_event_type, 'processing', coalesce(p_payload, '{}'::jsonb))
  on conflict (provider, external_event_id) do update
    set processing_status = 'processing',
        payload = excluded.payload,
        last_error = null,
        updated_at = now()
    where webhook_events.processing_status in ('received', 'failed')
       or (
         webhook_events.processing_status = 'processing'
         and webhook_events.updated_at < now() - interval '5 minutes'
       )
  returning id into v_id;

  return v_id is not null;
end;
$$;

-- 2. Jejak pesan Meta untuk deduplikasi yang dapat diaudit.
alter table messages
  add column if not exists external_message_id varchar(255),
  add column if not exists provider_metadata jsonb not null default '{}'::jsonb;

create unique index if not exists uq_messages_external_message_id
  on messages (external_message_id)
  where external_message_id is not null;

-- 3. Snapshot penerima/pengiriman: riwayat order tidak berubah saat profil customer berubah.
alter table orders
  add column if not exists recipient_name varchar(255),
  add column if not exists recipient_phone varchar(20),
  add column if not exists shipping_address text,
  add column if not exists payment_status_snapshot varchar(20) not null default 'pending';

-- Isi snapshot historis dari profil yang ada tanpa menghapus nilai yang sudah tersimpan.
update orders o
set recipient_name = coalesce(o.recipient_name, c.name),
    recipient_phone = coalesce(o.recipient_phone, c.whatsapp_number),
    shipping_address = coalesce(o.shipping_address, c.address)
from customers c
where c.id = o.customer_id
  and (o.recipient_name is null or o.recipient_phone is null or o.shipping_address is null);

create index if not exists idx_orders_payment_status_snapshot
  on orders (payment_status_snapshot, created_at desc);

-- 4. Order item siap untuk keranjang multi-produk tanpa mengubah jalur order satu-produk saat ini.
create table if not exists order_items (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references orders(id) on delete restrict,
  product_id uuid not null references products(id) on delete restrict,
  variant_id uuid,
  product_name_snapshot varchar(255) not null,
  sku_snapshot varchar(64),
  unit_label_snapshot varchar(80),
  quantity integer not null,
  unit_price numeric(12,2) not null,
  discount_amount numeric(12,2) not null default 0,
  total_amount numeric(12,2) not null,
  created_at timestamptz not null default now(),
  constraint chk_order_items_quantity_positive check (quantity > 0),
  constraint chk_order_items_price_nonneg check (unit_price >= 0 and discount_amount >= 0 and total_amount >= 0),
  constraint chk_order_items_total_matches check (total_amount = (unit_price * quantity) - discount_amount)
);

-- Backfill seluruh order lama sebagai satu item; aman bila dijalankan ulang.
insert into order_items (
  order_id, product_id, product_name_snapshot, sku_snapshot, unit_label_snapshot,
  quantity, unit_price, discount_amount, total_amount, created_at
)
select o.id, o.product_id, p.name, p.sku, p.unit_label,
       o.quantity, o.unit_price, o.discount_amount, o.total_amount, o.created_at
from orders o
join products p on p.id = o.product_id
where not exists (select 1 from order_items oi where oi.order_id = o.id);

create index if not exists idx_order_items_order on order_items (order_id);
create index if not exists idx_order_items_product on order_items (product_id);

-- 5. Varian produk untuk ukuran, warna, volume, dan SKU terpisah.
create table if not exists product_variants (
  id uuid primary key default gen_random_uuid(),
  product_id uuid not null references products(id) on delete restrict,
  sku varchar(64) not null,
  name varchar(255) not null,
  attributes jsonb not null default '{}'::jsonb,
  price_adjustment numeric(12,2) not null default 0,
  floor_price_adjustment numeric(12,2) not null default 0,
  stock integer not null default 0,
  reorder_point integer not null default 0,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint chk_product_variants_stock_nonneg check (stock >= 0 and reorder_point >= 0),
  constraint chk_product_variants_price_nonneg check (price_adjustment >= 0 and floor_price_adjustment >= 0),
  constraint uq_product_variants_sku unique (sku)
);

create index if not exists idx_product_variants_product_active
  on product_variants (product_id)
  where is_active = true;
drop trigger if exists trg_product_variants_updated_at on product_variants;
create trigger trg_product_variants_updated_at
  before update on product_variants
  for each row execute function set_updated_at();

alter table order_items
  drop constraint if exists fk_order_items_variant;
alter table order_items
  add constraint fk_order_items_variant
  foreign key (variant_id) references product_variants(id) on delete restrict;

-- 6. Reservasi stok: checkout dapat menahan inventaris sebelum Midtrans settlement.
create table if not exists inventory_reservations (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references orders(id) on delete restrict,
  product_id uuid not null references products(id) on delete restrict,
  variant_id uuid references product_variants(id) on delete restrict,
  quantity integer not null,
  status varchar(20) not null default 'active',
  expires_at timestamptz not null,
  released_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint chk_inventory_reservations_quantity check (quantity > 0),
  constraint chk_inventory_reservations_status check (status in ('active', 'confirmed', 'released', 'expired')),
  constraint uq_inventory_reservations_order_product unique (order_id, product_id)
);

create index if not exists idx_inventory_reservations_active
  on inventory_reservations (product_id, expires_at)
  where status = 'active';
drop trigger if exists trg_inventory_reservations_updated_at on inventory_reservations;
create trigger trg_inventory_reservations_updated_at
  before update on inventory_reservations
  for each row execute function set_updated_at();

-- Stok direservasi di DB dengan row-lock sehingga dua checkout tidak dapat oversell.
create or replace function reserve_inventory(
  p_order_id uuid,
  p_product_id uuid,
  p_quantity integer,
  p_expires_at timestamptz
) returns boolean
language plpgsql
as $$
declare
  v_stock integer;
  v_reserved integer;
begin
  if p_quantity <= 0 then
    raise exception 'quantity harus lebih besar dari 0';
  end if;

  select stock into v_stock from products where id = p_product_id and is_active = true and deleted_at is null for update;
  if not found then
    return false;
  end if;
  select coalesce(sum(quantity), 0) into v_reserved
  from inventory_reservations
  where product_id = p_product_id and status = 'active' and expires_at > now();
  if v_stock - v_reserved < p_quantity then
    return false;
  end if;
  insert into inventory_reservations (order_id, product_id, quantity, status, expires_at)
  values (p_order_id, p_product_id, p_quantity, 'active', p_expires_at)
  on conflict (order_id, product_id) do update
    set quantity = excluded.quantity, status = 'active', expires_at = excluded.expires_at, released_at = null;
  return true;
end;
$$;

-- Settlement memotong stok dan menulis audit dalam satu transaksi DB.
create or replace function confirm_inventory_sale(
  p_order_id uuid,
  p_product_id uuid,
  p_quantity integer
) returns table (stock_before integer, stock_after integer, inventory_applied boolean)
language plpgsql
as $$
declare
  v_before integer;
  v_reservation_status varchar;
begin
  select stock into v_before from products where id = p_product_id for update;
  if not found or v_before < p_quantity then
    raise exception 'stok tidak mencukupi untuk settlement order %', p_order_id;
  end if;
  select status into v_reservation_status from inventory_reservations
  where order_id = p_order_id and product_id = p_product_id for update;
  if v_reservation_status = 'confirmed' then
    return query select v_before, v_before, false;
    return;
  end if;
  update products set stock = stock - p_quantity where id = p_product_id;
  insert into inventory_logs (product_id, change_type, quantity_change, stock_before, stock_after, reference_order_id)
  values (p_product_id, 'sale', -p_quantity, v_before, v_before - p_quantity, p_order_id);
  if v_reservation_status is not null then
    update inventory_reservations set status = 'confirmed', released_at = now()
    where order_id = p_order_id and product_id = p_product_id;
  end if;
  return query select v_before, v_before - p_quantity, true;
end;
$$;

-- 7. Ledger notifikasi pembayaran; payload asli tetap tersedia untuk audit sengketa.
create table if not exists payment_events (
  id uuid primary key default gen_random_uuid(),
  payment_id uuid references payments(id) on delete set null,
  provider varchar(30) not null default 'midtrans',
  external_event_id varchar(255) not null,
  event_type varchar(80) not null,
  transaction_status varchar(50),
  payload jsonb not null default '{}'::jsonb,
  received_at timestamptz not null default now(),
  processed_at timestamptz,
  constraint uq_payment_events_provider_external unique (provider, external_event_id)
);

create index if not exists idx_payment_events_payment on payment_events (payment_id, received_at desc);

commit;
