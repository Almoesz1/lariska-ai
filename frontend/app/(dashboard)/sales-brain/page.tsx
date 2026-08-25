"use client";

import { ChangeEvent, FormEvent, useMemo, useRef, useState } from "react";
import { AlertCircle, Bot, CheckCircle2, CircleStop, CreditCard, LoaderCircle, Mic, Radio, RefreshCw, Send, ShieldCheck, Sparkles, Upload } from "lucide-react";
import { useProducts } from "@/hooks/useProducts";
import { ApiError } from "@/services/api";
import { createDemoCheckout, runLocalDemo, transcribeAndRunLocalDemo } from "@/services/sales-brain.service";
import type { NegotiationResponse } from "@/types/sales-brain";

type ChatMessage = { role: "customer" | "assistant"; text: string; result?: NegotiationResponse; transcript?: string; intent?: string };
const rupiah = new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 });

export default function SalesBrainPage() {
  const { products, isLoading, error: productsError, refresh } = useProducts();
  const [selectedId, setSelectedId] = useState("");
  const [message, setMessage] = useState("Kalau saya ambil 2, bisa Rp45.000?");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [isCheckout, setIsCheckout] = useState(false);
  const [checkoutUrl, setCheckoutUrl] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const voiceInputRef = useRef<HTMLInputElement>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const sessionRef = useRef(`demo-${crypto.randomUUID()}`);
  const product = useMemo(() => products.find((item) => item.id === selectedId) || products.find((item) => item.is_active), [products, selectedId]);
  const lastResult = [...messages].reverse().find((item) => item.result)?.result;
  const lastCustomerMessage = [...messages].reverse().find((item) => item.role === "customer")?.text || "";
  const latestPipelineIntent = [...messages].reverse().find((item) => item.role === "assistant" && item.intent)?.intent;
  const checkoutRequested = latestPipelineIntent === "checkout" || /\b(checkout|cekout|cekot|bayar|jadi beli|lanjut pesan)\b/i.test(lastCustomerMessage);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!product || !message.trim() || isSending) return;
    const text = message.trim();
    setMessages((current) => [...current, { role: "customer", text }]); setMessage(""); setError(null); setIsSending(true);
    try { const result = await runLocalDemo(product, sessionRef.current, text); setMessages((current) => [...current, { role: "assistant", text: result.suggested_reply, result, intent: result.intent }]); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Sales Brain belum dapat memproses pesan ini."); }
    finally { setIsSending(false); }
  }
  async function processVoice(audio: File) {
    if (!product || !audio || isSending) return;
    setMessages((current) => [...current, { role: "customer", text: `🎙️ Voice note: ${audio.name}` }]); setError(null); setIsSending(true);
    try { const result = await transcribeAndRunLocalDemo(product, sessionRef.current, audio); setMessages((current) => [...current, { role: "assistant", text: result.suggested_reply, result, transcript: result.transcript, intent: result.intent }]); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Voice note belum dapat diproses."); }
    finally { setIsSending(false); }
  }
  async function submitVoice(event: ChangeEvent<HTMLInputElement>) {
    const audio = event.target.files?.[0]; event.target.value = "";
    if (audio) await processVoice(audio);
  }
  async function toggleRecording() {
    if (isRecording) { recorderRef.current?.stop(); return; }
    if (!product || isSending) return;
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setError("Browser ini belum mendukung rekam suara. Gunakan tombol unggah file audio."); return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, MediaRecorder.isTypeSupported("audio/webm") ? { mimeType: "audio/webm" } : undefined);
      recorderRef.current = recorder; audioChunksRef.current = [];
      recorder.ondataavailable = (event) => { if (event.data.size) audioChunksRef.current.push(event.data); };
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop()); setIsRecording(false);
        const blob = new Blob(audioChunksRef.current, { type: recorder.mimeType || "audio/webm" });
        if (blob.size) void processVoice(new File([blob], "voice-note.webm", { type: blob.type }));
      };
      recorder.start(); setIsRecording(true); setError(null);
    } catch { setError("Izin mikrofon diperlukan untuk merekam voice note. Anda tetap dapat mengunggah file audio."); }
  }
  async function checkout() {
    if (!product || isCheckout) return;
    setError(null); setIsCheckout(true);
    try { const result = await createDemoCheckout(product, sessionRef.current); setCheckoutUrl(result.payment_url); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Invoice belum dapat dibuat."); }
    finally { setIsCheckout(false); }
  }
  function reset() { recorderRef.current?.stop(); setIsRecording(false); setMessages([]); setCheckoutUrl(null); setError(null); sessionRef.current = `demo-${crypto.randomUUID()}`; }

  return <div className="space-y-5 pb-8 sm:space-y-7">
    <header className="relative overflow-hidden rounded-[2rem] bg-gradient-to-br from-indigo-950 via-[#44358f] to-[#715bc9] px-5 py-7 text-white shadow-2xl shadow-indigo-200 sm:px-7 sm:py-9">
      <div className="absolute -right-16 -top-24 h-64 w-64 rounded-full bg-white/10 blur-2xl" />
      <div className="relative flex flex-wrap items-end justify-between gap-5"><div><p className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-indigo-200"><Sparkles className="h-4 w-4" /> Local End-to-End Demo</p><h1 className="text-3xl font-black tracking-tight sm:text-4xl">Inti LARISKA, dapat diuji tanpa nomor Meta</h1><p className="mt-3 max-w-3xl text-sm leading-relaxed text-indigo-100">Dashboard hanya mengganti kanal WhatsApp. NLU Gemini, emosi, LightGBM, Python guardrail, Supabase, Whisper, dan invoice tetap dijalankan oleh backend produksi.</p></div><button onClick={reset} className="inline-flex items-center gap-2 rounded-xl bg-white/10 px-4 py-3 text-sm font-bold ring-1 ring-white/20 hover:bg-white/20"><RefreshCw className="h-4 w-4" /> Sesi baru</button></div>
      <div className="relative mt-6 grid gap-2 text-xs font-semibold sm:grid-cols-3"><Pill n="01" text="NLU, emosi & konteks" /><Pill n="02" text="LightGBM + floor guardrail" /><Pill n="03" text="Voice, invoice & audit" /></div>
    </header>
    {productsError && <div className="flex gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-rose-800"><AlertCircle className="h-5 w-5 shrink-0" /><span>{productsError}</span><button onClick={() => void refresh()} className="ml-auto font-bold underline">Coba lagi</button></div>}
    <div className="grid gap-5 xl:grid-cols-[.8fr_1.5fr_.75fr]">
      <aside className="rounded-3xl border border-white bg-white/85 p-5 shadow-xl shadow-indigo-100/50"><h2 className="font-black text-indigo-950">Katalog nyata</h2><p className="mt-1 text-sm text-slate-500">Produk dibaca ulang dari Supabase di server.</p>{isLoading ? <div className="mt-5 h-44 animate-pulse rounded-2xl bg-slate-100" /> : <div className="mt-5 grid max-h-[480px] gap-3 overflow-y-auto pr-1">{products.filter((item) => item.is_active).map((item) => <button key={item.id} onClick={() => { setSelectedId(item.id); setCheckoutUrl(null); }} className={`rounded-2xl border p-4 text-left transition ${product?.id === item.id ? "border-[#715bc9] bg-indigo-50 shadow-sm" : "border-slate-100 bg-white hover:border-indigo-200"}`}><p className="font-bold text-indigo-950">{item.name}</p><p className="mt-1 text-xs text-slate-500">{item.unit_label || "per unit"} · stok {item.stock}</p><p className="mt-2 text-sm font-bold text-[#715bc9]">{rupiah.format(item.price)}</p></button>)}</div>} {product && <div className="mt-5 rounded-2xl bg-amber-50 p-4 text-sm text-amber-950"><p className="flex items-center gap-2 text-xs font-black uppercase tracking-wider"><ShieldCheck className="h-4 w-4" /> Guardrail aktif</p><p className="mt-2">Floor price <strong>{rupiah.format(product.floor_price)}</strong>. LLM tidak pernah memutuskan harga.</p></div>}</aside>
      <section className="flex min-h-[620px] flex-col overflow-hidden rounded-3xl border border-white bg-white/85 shadow-xl shadow-indigo-100/50"><div className="border-b border-slate-100 p-5"><div className="flex items-center gap-3"><div className="rounded-2xl bg-[#715bc9] p-3 text-white"><Bot className="h-6 w-6" /></div><div><h2 className="font-black text-indigo-950">Percakapan pelanggan</h2><p className="text-sm text-slate-500">{product ? `${product.name} · ${rupiah.format(product.price)}` : "Pilih produk untuk memulai"}</p></div></div><div className="mt-5 flex flex-wrap gap-2"><Scenario text="Kalau saya ambil 2, bisa harga spesial?" setMessage={setMessage} /><Scenario text={`Kak, ${product?.name || "produk ini"} detailnya bagaimana dan masih ready?`} setMessage={setMessage} /><Scenario text="Saya mau checkout sekarang" setMessage={setMessage} /></div></div>
        <div className="flex-1 space-y-4 overflow-y-auto bg-slate-50/60 p-5">{messages.length === 0 && <div className="mx-auto mt-20 max-w-sm text-center"><Bot className="mx-auto h-12 w-12 text-indigo-200" /><p className="mt-4 font-bold text-indigo-950">Uji satu alur yang sama dengan produksi</p><p className="mt-2 text-sm text-slate-500">Pilih produk, lalu coba tanya detail, menawar, unggah voice note, dan buat invoice.</p></div>}{messages.map((item, index) => <article key={index} className={item.role === "customer" ? "ml-auto max-w-[92%] rounded-2xl rounded-br-sm bg-[#715bc9] p-4 text-white" : "max-w-[94%] rounded-2xl rounded-bl-sm border border-slate-100 bg-white p-4 text-slate-700 shadow-sm"}><p className="whitespace-pre-wrap text-sm leading-relaxed">{item.text}</p>{item.transcript && <p className="mt-3 rounded-xl bg-indigo-50 p-3 text-xs font-medium text-indigo-800">Transkripsi Whisper: “{item.transcript}”</p>}{item.result && <div className="mt-4 grid gap-2 border-t border-slate-100 pt-3 sm:grid-cols-3"><Metric label="Keputusan" value={item.result.decision_result.final_action.replaceAll("_", " ")} /><Metric label="Harga final" value={rupiah.format(item.result.decision_result.final_price)} /><Metric label="Emosi" value={item.result.emotion_info.emotion.replaceAll("_", " ")} /></div>}</article>)}{isSending && <div className="flex items-center gap-2 text-sm font-medium text-slate-500"><LoaderCircle className="h-4 w-4 animate-spin" /> Memproses pipeline produksi…</div>}</div>
        {error && <div className="mx-5 mb-3 rounded-xl bg-rose-50 p-3 text-sm font-medium text-rose-700">{error}</div>}
        <form onSubmit={submit} className="border-t border-slate-100 p-4"><input ref={voiceInputRef} type="file" accept="audio/ogg,audio/mpeg,audio/wav,audio/mp4,.ogg,.mp3,.wav,.m4a" onChange={submitVoice} className="hidden" /><div className="flex gap-2"><button type="button" onClick={toggleRecording} disabled={!product || isSending} className={`rounded-xl border px-3 disabled:opacity-50 ${isRecording ? "border-rose-300 bg-rose-50 text-rose-700" : "border-indigo-100 bg-indigo-50 text-[#715bc9]"}`} title={isRecording ? "Hentikan rekaman" : "Rekam voice note"}>{isRecording ? <CircleStop className="h-4 w-4" /> : <Radio className="h-4 w-4" />}</button><button type="button" onClick={() => voiceInputRef.current?.click()} disabled={!product || isSending || isRecording} className="rounded-xl border border-indigo-100 bg-indigo-50 px-3 text-[#715bc9] disabled:opacity-50" title="Unggah audio contoh"><Upload className="h-4 w-4" /></button><input value={message} onChange={(event) => setMessage(event.target.value)} disabled={!product || isSending || isRecording} className="min-w-0 flex-1 rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-[#715bc9] focus:ring-4 focus:ring-indigo-100 disabled:bg-slate-100" placeholder={isRecording ? "Sedang merekam voice note…" : "Tulis pesan pelanggan…"} /><button disabled={!product || isSending || isRecording || !message.trim()} className="inline-flex items-center gap-2 rounded-xl bg-[#715bc9] px-4 py-3 text-sm font-bold text-white disabled:opacity-50"><Send className="h-4 w-4" /> Kirim</button></div><p className="mt-2 flex items-center gap-1.5 text-[11px] text-slate-400"><Mic className="h-3 w-3" /> Rekam langsung untuk alur natural, atau unggah OGG/MP3/WAV/M4A sebagai fixture pengujian panitia.</p></form>
      </section>
      <aside className="space-y-4"><section className="rounded-3xl border border-white bg-white/85 p-5 shadow-xl shadow-indigo-100/40"><p className="text-xs font-bold uppercase tracking-wider text-[#715bc9]">Decision trace</p><h2 className="mt-1 text-lg font-black text-indigo-950">Bukti keputusan</h2>{product ? <div className="mt-5 space-y-3"><Trace label="Harga katalog" value={rupiah.format(product.price)} /><Trace label="Floor price" value={rupiah.format(product.floor_price)} amber /><Trace label="Stok Supabase" value={`${product.stock} ${product.unit_label || "unit"}`} /></div> : <p className="mt-4 text-sm text-slate-500">Pilih produk untuk melihat konteks.</p>}</section>
        <section className="rounded-3xl border border-emerald-100 bg-emerald-50/70 p-5 shadow-lg shadow-emerald-100/40"><p className="text-xs font-bold uppercase tracking-wider text-emerald-700">Bukti Hybrid AI</p><h2 className="mt-1 text-lg font-black text-emerald-950">Komponen yang diuji</h2><div className="mt-4 space-y-2 text-xs font-semibold text-emerald-900"><Feature text="Gemini: intent & entity percakapan" /><Feature text="Whisper: transkripsi voice note" /><Feature text="LightGBM: strategi negosiasi" /><Feature text="Python: floor price & stok" /><Feature text="Supabase: memori, order, audit" /><Feature text="Midtrans: invoice & status bayar" /></div></section>
        <section className="rounded-3xl bg-indigo-950 p-5 text-white shadow-xl shadow-indigo-200"><p className="text-xs font-bold uppercase tracking-wider text-indigo-200">Aksi transaksi</p><p className="mt-2 text-sm leading-6 text-indigo-100">Invoice baru dibuat setelah pelanggan menulis <strong>checkout</strong>, sama seperti alur WhatsApp. Ini mencegah stok terkunci dan tagihan dibuat tanpa persetujuan.</p>{checkoutRequested ? <button onClick={checkout} disabled={!product || isCheckout || Boolean(checkoutUrl)} className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-white px-4 py-3 text-sm font-black text-indigo-950 disabled:opacity-50">{isCheckout ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <CreditCard className="h-4 w-4" />}{isCheckout ? "Membuat invoice…" : checkoutUrl ? "Invoice sudah dibuat" : "Buat invoice pembayaran"}</button> : <div className="mt-4 rounded-xl bg-white/10 p-3 text-xs leading-5 text-indigo-100">Lanjutkan percakapan dengan pesan “checkout” untuk membuka langkah pembayaran.</div>}{checkoutUrl && <a href={checkoutUrl} target="_blank" rel="noreferrer" className="mt-3 flex items-center justify-center rounded-xl bg-emerald-400 px-4 py-3 text-sm font-black text-emerald-950">Buka pembayaran Midtrans</a>}</section>
        {lastResult && <section className="rounded-3xl bg-white p-5 shadow-xl shadow-indigo-100/40"><p className="text-xs font-bold uppercase tracking-wider text-[#715bc9]">Hasil terakhir</p><p className="mt-2 text-xl font-black capitalize text-indigo-950">{lastResult.decision_result.final_action.replaceAll("_", " ")}</p><p className="mt-2 text-sm leading-6 text-slate-600">{lastResult.decision_result.guard_reason}</p><p className="mt-3 flex items-center gap-2 text-xs font-semibold text-emerald-700"><CheckCircle2 className="h-4 w-4" /> Guardrail dievaluasi lebih dulu</p></section>}
      </aside>
    </div>
  </div>;
}

function Pill({ n, text }: { n: string; text: string }) { return <span className="flex items-center gap-2 rounded-xl border border-white/15 bg-white/10 px-3 py-2"><span className="flex h-5 w-5 items-center justify-center rounded-full bg-white text-[10px] font-black text-indigo-950">{n}</span>{text}</span>; }
function Scenario({ text, setMessage }: { text: string; setMessage: (value: string) => void }) { return <button type="button" onClick={() => setMessage(text)} className="rounded-lg bg-indigo-50 px-3 py-2 text-xs font-bold text-[#715bc9] hover:bg-indigo-100">{text}</button>; }
function Metric({ label, value }: { label: string; value: string }) { return <div className="rounded-xl bg-slate-50 px-3 py-2"><p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{label}</p><p className="mt-1 text-sm font-black capitalize text-indigo-950">{value}</p></div>; }
function Trace({ label, value, amber = false }: { label: string; value: string; amber?: boolean }) { return <div className={`rounded-2xl p-3 ${amber ? "bg-amber-50" : "bg-slate-50"}`}><p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{label}</p><p className={`mt-1 text-sm font-black ${amber ? "text-amber-900" : "text-indigo-950"}`}>{value}</p></div>; }
function Feature({ text }: { text: string }) { return <p className="flex items-start gap-2"><CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0" />{text}</p>; }
