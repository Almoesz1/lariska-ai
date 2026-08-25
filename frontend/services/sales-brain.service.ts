import { API_BASE_URL, apiFetch, ApiError } from "@/services/api";
import type { Product } from "@/types/product";
import type { NegotiationResponse } from "@/types/sales-brain";

export type LocalDemoResponse = NegotiationResponse & {
  intent: string;
  conversation_id: string;
  pipeline: string[];
  is_voice_input: boolean;
  transcript?: string;
};

export type CheckoutResponse = { order_id: string; payment_url: string; amount: number; status: string };

/** Dashboard mengirim teks, ID produk, dan ID sesi saja. Harga/floor/stok/features
 * diambil serta dihitung ulang oleh server, sehingga ini bukan mock chat. */
export function runLocalDemo(product: Product, sessionId: string, userMessage: string): Promise<LocalDemoResponse> {
  return apiFetch<LocalDemoResponse>("/api/sales-brain/demo/message", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId, product_id: product.id, user_message: userMessage,
    }),
  });
}

export async function transcribeAndRunLocalDemo(product: Product, sessionId: string, audio: File): Promise<LocalDemoResponse> {
  const body = new FormData();
  body.append("session_id", sessionId); body.append("product_id", product.id); body.append("audio", audio);
  let response: Response;
  try { response = await fetch(`${API_BASE_URL}/api/sales-brain/demo/voice`, { method: "POST", body, cache: "no-store" }); }
  catch { throw new ApiError("Backend belum dapat dihubungi. Pastikan FastAPI berjalan di port 8000.", 0); }
  if (response.ok) return response.json() as Promise<LocalDemoResponse>;
  const payload = await response.json().catch(() => null);
  throw new ApiError(typeof payload?.detail === "string" ? payload.detail : "Voice note tidak dapat diproses.", response.status);
}

export function createDemoCheckout(product: Product, sessionId: string): Promise<CheckoutResponse> {
  return apiFetch<CheckoutResponse>("/api/sales-brain/demo/checkout", {
    // Quantity dipulihkan server dari negosiasi terakhir agar invoice sama
    // persis dengan kesepakatan chat, bukan default browser = satu unit.
    method: "POST", body: JSON.stringify({ session_id: sessionId, product_id: product.id }),
  });
}

// Kompatibilitas pemanggil lama; UI menggunakan runLocalDemo.
export function negotiate(product: Product, userMessage: string): Promise<NegotiationResponse> {
  return runLocalDemo(product, "legacy-local-demo", userMessage);
}
