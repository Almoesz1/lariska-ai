"use client";

import { AlertCircle, Package, RefreshCw, Tag } from "lucide-react";
import { useProducts } from "@/hooks/useProducts";

const rupiah = new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 });

export default function ProductsPage() {
  const { products, isLoading, error, refresh } = useProducts();

  return (
    <div className="space-y-8 pb-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-2 text-sm font-bold uppercase tracking-[0.18em] text-[#715bc9]">Katalog real-time</p>
          <h1 className="text-4xl font-black tracking-tight text-indigo-950">Produk & Guardrail Harga</h1>
          <p className="mt-2 text-slate-600">Data dibaca langsung dari katalog Supabase melalui FastAPI.</p>
        </div>
        <button onClick={() => void refresh()} className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-3 text-sm font-bold text-indigo-950 shadow-sm ring-1 ring-slate-200 hover:bg-slate-50">
          <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} /> Muat ulang
        </button>
      </header>

      {error && (
        <div className="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-5 text-rose-800">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
          <div><p className="font-bold">Katalog belum dapat dimuat</p><p className="mt-1 text-sm">{error}</p></div>
        </div>
      )}

      {isLoading ? (
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 6 }).map((_, index) => <div key={index} className="h-72 animate-pulse rounded-3xl bg-white/70" />)}</div>
      ) : !error && products.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-indigo-200 bg-white/60 py-20 text-center"><Package className="mx-auto h-12 w-12 text-indigo-300" /><h2 className="mt-4 text-xl font-bold text-indigo-950">Belum ada produk aktif</h2><p className="mt-2 text-slate-500">Tambahkan produk melalui dashboard API atau seed Supabase.</p></div>
      ) : (
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {products.map((product) => {
            const stockState = product.stock > 5 ? "Stok aman" : product.stock > 0 ? "Stok menipis" : "Stok habis";
            return <article key={product.id} className="rounded-3xl border border-white bg-white/80 p-6 shadow-lg shadow-indigo-100/50 backdrop-blur transition hover:-translate-y-1 hover:shadow-xl">
              <div className="flex items-start justify-between gap-3"><div className="rounded-2xl bg-indigo-50 p-3"><Package className="h-6 w-6 text-[#715bc9]" /></div><span className={`rounded-full px-3 py-1 text-xs font-bold ${product.stock > 5 ? "bg-emerald-100 text-emerald-700" : product.stock > 0 ? "bg-amber-100 text-amber-700" : "bg-rose-100 text-rose-700"}`}>{stockState}: {product.stock}</span></div>
              <p className="mt-6 text-xs font-bold uppercase tracking-wider text-slate-400">{product.category || "Produk"}</p><h2 className="mt-1 text-xl font-black text-indigo-950">{product.name}</h2><p className="mt-2 line-clamp-2 min-h-10 text-sm text-slate-500">{product.description || "Belum ada deskripsi produk."}</p>
              <div className="mt-6 grid grid-cols-2 gap-3 border-t border-slate-100 pt-5"><div><p className="text-xs font-semibold text-slate-400">Harga jual</p><p className="mt-1 font-black text-indigo-950">{rupiah.format(product.price)}</p></div><div className="rounded-xl bg-amber-50 px-3 py-2"><p className="flex items-center gap-1 text-xs font-bold text-amber-700"><Tag className="h-3 w-3" /> Floor price</p><p className="mt-1 font-black text-amber-900">{rupiah.format(product.floor_price)}</p></div></div>
            </article>;
          })}
        </div>
      )}
    </div>
  );
}
