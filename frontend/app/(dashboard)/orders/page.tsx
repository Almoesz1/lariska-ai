"use client";

import { useMemo, useState } from "react";
import { AlertCircle, ArrowUpRight, Package, ReceiptText, RefreshCw, Search, ShoppingCart, WalletCards } from "lucide-react";
import { useCustomers } from "@/hooks/useCustomers";
import { useOrders } from "@/hooks/useOrders";
import { useProducts } from "@/hooks/useProducts";
import type { OrderStatus } from "@/types/order";

const rupiah = new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 });
const statuses: OrderStatus[] = ["pending", "paid", "shipped", "completed", "cancelled"];
const statusStyle: Record<OrderStatus, string> = { pending: "bg-amber-50 text-amber-700 ring-amber-200", paid: "bg-sky-50 text-sky-700 ring-sky-200", shipped: "bg-violet-50 text-violet-700 ring-violet-200", completed: "bg-emerald-50 text-emerald-700 ring-emerald-200", cancelled: "bg-rose-50 text-rose-700 ring-rose-200" };

export default function OrdersPage() {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<OrderStatus | "all">("all");
  const { orders, isLoading: loadingOrders, error: ordersError, refresh: refreshOrders } = useOrders();
  const { products, isLoading: loadingProducts } = useProducts();
  const { customers, isLoading: loadingCustomers } = useCustomers();
  const productById = useMemo(() => new Map(products.map((item) => [item.id, item])), [products]);
  const customerById = useMemo(() => new Map(customers.map((item) => [item.id, item])), [customers]);
  const filtered = useMemo(() => orders.filter((order) => {
    const customer = customerById.get(order.customer_id); const product = productById.get(order.product_id);
    const searchable = `${order.id} ${customer?.name || ""} ${customer?.whatsapp_number || ""} ${product?.name || ""}`.toLowerCase();
    return (filter === "all" || order.status === filter) && searchable.includes(query.toLowerCase());
  }), [orders, customerById, productById, filter, query]);
  const revenue = orders.filter((order) => ["paid", "shipped", "completed"].includes(order.status)).reduce((total, order) => total + order.total_amount, 0);
  const pending = orders.filter((order) => order.status === "pending").reduce((total, order) => total + order.total_amount, 0);
  const average = orders.length ? orders.reduce((total, order) => total + order.total_amount, 0) / orders.length : 0;
  const isLoading = loadingOrders || loadingProducts || loadingCustomers;

  return <div className="space-y-7 pb-10">
    <header className="flex flex-wrap items-end justify-between gap-4"><div><p className="mb-2 text-sm font-bold uppercase tracking-[0.18em] text-[#715bc9]">Operasional transaksi</p><h1 className="text-4xl font-black tracking-tight text-indigo-950">Pesanan yang siap ditindaklanjuti</h1><p className="mt-2 text-slate-600">Order, pelanggan, dan produk dipasangkan dari data Supabase yang sama.</p></div><button onClick={() => void refreshOrders()} className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-3 text-sm font-bold text-indigo-950 shadow-sm ring-1 ring-slate-200 hover:bg-slate-50"><RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} /> Muat ulang</button></header>
    {ordersError && <Notice text={ordersError} />}
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><Metric icon={<WalletCards />} label="Pendapatan terealisasi" value={rupiah.format(revenue)} note="Paid, dikirim, & selesai" /><Metric icon={<ReceiptText />} label="Menunggu pembayaran" value={rupiah.format(pending)} note={`${orders.filter((o) => o.status === "pending").length} order pending`} tone="amber" /><Metric icon={<ShoppingCart />} label="Total pesanan" value={String(orders.length)} note="Seluruh histori order" /><Metric icon={<ArrowUpRight />} label="Rata-rata nilai order" value={rupiah.format(average)} note="Nilai transaksi per order" tone="violet" /></div>
    <section className="rounded-3xl border border-white bg-white/80 p-5 shadow-xl shadow-indigo-100/40 backdrop-blur"><div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between"><div className="relative w-full lg:max-w-md"><Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari order, pelanggan, produk, atau WhatsApp" className="w-full rounded-xl border border-slate-200 bg-white py-3 pl-11 pr-4 text-sm outline-none transition focus:border-[#715bc9] focus:ring-4 focus:ring-indigo-100" /></div><div className="flex flex-wrap gap-2">{(["all", ...statuses] as const).map((status) => <button key={status} onClick={() => setFilter(status)} className={`rounded-xl px-3 py-2 text-xs font-bold capitalize transition ${filter === status ? "bg-[#715bc9] text-white shadow-sm" : "bg-slate-50 text-slate-500 hover:bg-indigo-50 hover:text-[#715bc9]"}`}>{status === "all" ? "Semua" : status}</button>)}</div></div></section>
    {isLoading ? <div className="grid gap-4 md:grid-cols-2">{Array.from({ length: 4 }).map((_, index) => <div key={index} className="h-48 animate-pulse rounded-3xl bg-white/70" />)}</div> : filtered.length === 0 ? <Empty /> : <div className="grid gap-4 md:grid-cols-2">{filtered.map((order) => { const product = productById.get(order.product_id); const customer = customerById.get(order.customer_id); return <article key={order.id} className="rounded-3xl border border-white bg-white/85 p-6 shadow-lg shadow-indigo-100/40 transition hover:-translate-y-0.5 hover:shadow-xl"><div className="flex items-start justify-between gap-4"><div><p className="font-mono text-xs font-bold text-[#715bc9]">#{order.id.slice(0, 8).toUpperCase()}</p><h2 className="mt-2 text-xl font-black text-indigo-950">{customer?.name || "Pelanggan WhatsApp"}</h2><p className="mt-1 text-sm text-slate-500">{customer?.whatsapp_number || "Identitas pelanggan sedang dimuat"}</p></div><span className={`rounded-full px-3 py-1 text-xs font-bold capitalize ring-1 ${statusStyle[order.status]}`}>{order.status}</span></div><div className="mt-5 flex items-center gap-3 rounded-2xl bg-slate-50 p-4"><div className="rounded-xl bg-indigo-50 p-2.5 text-[#715bc9]"><Package className="h-5 w-5" /></div><div className="min-w-0"><p className="truncate font-bold text-indigo-950">{product?.name || "Produk arsip"}</p><p className="mt-1 text-xs text-slate-500">{order.quantity} unit · Harga satuan {rupiah.format(order.unit_price)}</p></div></div><div className="mt-5 grid grid-cols-3 gap-3 border-t border-slate-100 pt-4"><Value label="Diskon" value={rupiah.format(order.discount_amount)} /><Value label="Total" value={rupiah.format(order.total_amount)} strong /><Value label="Dibuat" value={new Date(order.created_at).toLocaleDateString("id-ID", { day: "numeric", month: "short" })} /></div></article>; })}</div>}
  </div>;
}
function Metric({ icon, label, value, note, tone = "indigo" }: { icon: React.ReactNode; label: string; value: string; note: string; tone?: "indigo" | "amber" | "violet" }) { const colors = { indigo: "bg-indigo-50 text-[#715bc9]", amber: "bg-amber-50 text-amber-600", violet: "bg-violet-50 text-violet-600" }; return <div className="rounded-3xl border border-white bg-white/85 p-5 shadow-lg shadow-indigo-100/30"><div className={`mb-4 inline-flex rounded-2xl p-3 ${colors[tone]}`}>{icon}</div><p className="text-xs font-bold uppercase tracking-wider text-slate-400">{label}</p><p className="mt-1 text-2xl font-black text-indigo-950">{value}</p><p className="mt-2 text-xs text-slate-500">{note}</p></div>; }
function Value({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) { return <div><p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{label}</p><p className={`mt-1 text-sm ${strong ? "font-black text-indigo-950" : "font-semibold text-slate-600"}`}>{value}</p></div>; }
function Notice({ text }: { text: string }) { return <div className="flex gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"><AlertCircle className="h-5 w-5 shrink-0" />{text}</div>; }
function Empty() { return <div className="rounded-3xl border border-dashed border-indigo-200 bg-white/60 py-20 text-center"><ShoppingCart className="mx-auto h-12 w-12 text-indigo-300" /><h2 className="mt-4 text-xl font-bold text-indigo-950">Belum ada pesanan pada filter ini</h2><p className="mt-2 text-sm text-slate-500">Data akan muncul otomatis setelah order disimpan ke Supabase.</p></div>; }
