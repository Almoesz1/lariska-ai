"use client";

import { FormEvent, useMemo, useState } from "react";
import { AlertCircle, Bot, LoaderCircle, Send, ShieldCheck, Sparkles, Tag } from "lucide-react";
import { useProducts } from "@/hooks/useProducts";
import { ApiError } from "@/services/api";
import { negotiate } from "@/services/sales-brain.service";
import type { NegotiationResponse } from "@/types/sales-brain";

type ChatMessage = { role: "customer" | "assistant"; text: string; result?: NegotiationResponse };
const rupiah = new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 });

export default function SalesBrainPage() {
  const { products, isLoading: loadingProducts, error: productsError, refresh } = useProducts();
  const [selectedId, setSelectedId] = useState("");
  const [message, setMessage] = useState("Bisa Rp 300.000? Kalau bisa saya transfer sekarang.");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const product = useMemo(() => products.find((item) => item.id === selectedId) || products[0], [products, selectedId]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!product || !message.trim() || isSending) return;
    const customerText = message.trim();
    setMessages((current) => [...current, { role: "customer", text: customerText }]);
    setMessage(""); setError(null); setIsSending(true);
    try {
      const result = await negotiate(product, customerText);
      setMessages((current) => [...current, { role: "assistant", text: result.suggested_reply, result }]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sales Brain belum dapat memproses pesan ini.");
    } finally { setIsSending(false); }
  }

  return <div className="space-y-7 pb-8">
    <header><p className="mb-2 flex items-center gap-2 text-sm font-bold uppercase tracking-[0.18em] text-[#715bc9]"><Sparkles className="h-4 w-4" /> Proof of Work</p><h1 className="text-4xl font-black tracking-tight text-indigo-950">Live Sales Brain Demo</h1><p className="mt-2 text-slate-600">Pilih produk nyata, kirim penawaran, dan tampilkan guardrail harga yang menjaga margin UMKM.</p></header>
    {productsError && <div className="flex gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-rose-800"><AlertCircle className="h-5 w-5 shrink-0" /><span>{productsError}</span><button onClick={() => void refresh()} className="ml-auto font-bold underline">Coba lagi</button></div>}
    <div className="grid gap-6 xl:grid-cols-[0.9fr_1.4fr]">
      <aside className="rounded-3xl border border-white bg-white/80 p-6 shadow-xl shadow-indigo-100/50 backdrop-blur"><div className="flex items-center gap-2"><Tag className="h-5 w-5 text-[#715bc9]" /><h2 className="text-lg font-black text-indigo-950">Produk aktif</h2></div>{loadingProducts ? <div className="mt-5 h-48 animate-pulse rounded-2xl bg-slate-100" /> : <div className="mt-5 space-y-3">{products.map((item) => <button key={item.id} onClick={() => setSelectedId(item.id)} className={`w-full rounded-2xl border p-4 text-left transition ${product?.id === item.id ? "border-[#715bc9] bg-indigo-50 shadow-sm" : "border-slate-100 bg-white hover:border-indigo-200"}`}><p className="font-bold text-indigo-950">{item.name}</p><p className="mt-1 text-sm text-slate-500">Harga {rupiah.format(item.price)} · Stok {item.stock}</p></button>)}</div>}{product && <div className="mt-6 rounded-2xl bg-amber-50 p-4 text-amber-950"><p className="flex items-center gap-2 text-xs font-black uppercase tracking-wider"><ShieldCheck className="h-4 w-4" /> Hard guardrail</p><p className="mt-2 text-sm">Floor price terkunci di <strong>{rupiah.format(product.floor_price)}</strong>. LLM tidak boleh mengubah angka ini.</p></div>}</aside>
      <section className="flex min-h-[580px] flex-col overflow-hidden rounded-3xl border border-white bg-white/85 shadow-xl shadow-indigo-100/50 backdrop-blur"><div className="border-b border-slate-100 p-6"><div className="flex items-center gap-3"><div className="rounded-2xl bg-[#715bc9] p-3 text-white"><Bot className="h-6 w-6" /></div><div><h2 className="font-black text-indigo-950">Percakapan pelanggan</h2><p className="text-sm text-slate-500">{product ? `${product.name} · ${rupiah.format(product.price)}` : "Pilih produk untuk memulai"}</p></div></div></div><div className="flex-1 space-y-4 overflow-y-auto bg-slate-50/60 p-6">{messages.length === 0 && <div className="mx-auto mt-24 max-w-sm text-center"><Bot className="mx-auto h-12 w-12 text-indigo-200" /><p className="mt-4 font-bold text-indigo-950">Siap mensimulasikan negosiasi</p><p className="mt-2 text-sm text-slate-500">Gunakan contoh tawaran di bawah untuk membuktikan keputusan harga tetap aman.</p></div>}{messages.map((item, index) => <div key={index} className={item.role === "customer" ? "ml-auto max-w-[85%] rounded-2xl rounded-br-sm bg-[#715bc9] p-4 text-white" : "max-w-[88%] rounded-2xl rounded-bl-sm border border-slate-100 bg-white p-4 text-slate-700 shadow-sm"}><p className="whitespace-pre-wrap text-sm leading-relaxed">{item.text}</p>{item.result && <div className="mt-4 grid gap-2 border-t border-slate-100 pt-3 sm:grid-cols-3"><Metric label="Keputusan" value={item.result.decision_result.final_action.replaceAll("_", " ")} /><Metric label="Harga final" value={rupiah.format(item.result.decision_result.final_price)} /><Metric label="Emosi" value={item.result.emotion_info.emotion.replaceAll("_", " ")} /></div>}</div>)}{isSending && <div className="flex items-center gap-2 text-sm font-medium text-slate-500"><LoaderCircle className="h-4 w-4 animate-spin" /> Sales Brain sedang menghitung guardrail…</div>}</div>{error && <div className="mx-6 mb-3 rounded-xl bg-rose-50 p-3 text-sm font-medium text-rose-700">{error}</div>}<form onSubmit={submit} className="border-t border-slate-100 p-5"><div className="flex gap-3"><input value={message} onChange={(event) => setMessage(event.target.value)} disabled={!product || isSending} className="min-w-0 flex-1 rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-[#715bc9] focus:ring-4 focus:ring-indigo-100 disabled:bg-slate-100" placeholder="Contoh: Bisa Rp300.000?" /><button disabled={!product || isSending || !message.trim()} className="inline-flex items-center gap-2 rounded-xl bg-[#715bc9] px-5 py-3 text-sm font-bold text-white shadow-md transition hover:bg-[#5f49b5] disabled:cursor-not-allowed disabled:opacity-50"><Send className="h-4 w-4" /> Kirim</button></div></form></section>
    </div>
  </div>;
}

function Metric({ label, value }: { label: string; value: string }) { return <div className="rounded-xl bg-slate-50 px-3 py-2"><p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{label}</p><p className="mt-1 text-sm font-black capitalize text-indigo-950">{value}</p></div>; }
