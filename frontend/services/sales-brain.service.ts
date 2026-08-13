import { apiFetch } from "@/services/api";
import type { Product } from "@/types/product";
import type { NegotiationResponse } from "@/types/sales-brain";

export function negotiate(product: Product, userMessage: string): Promise<NegotiationResponse> {
  const offered = extractOffer(userMessage, product.price);
  return apiFetch<NegotiationResponse>("/api/sales-brain/negotiate", {
    method: "POST",
    body: JSON.stringify({
      user_message: userMessage,
      product_name: product.name,
      product_price: product.price,
      floor_price: product.floor_price,
      max_discount_pct: Math.max(0, Math.min(0.25, (product.price - product.floor_price) / product.price)),
      features: {
        margin_pct: Math.max(0, (product.price - product.floor_price) / product.price),
        stock_ratio: product.stock > 0 ? 1 : 0,
        customer_loyalty: 0.3,
        discount_requested_pct: Math.max(0, Math.min(1, (product.price - offered) / product.price)),
        hour_of_day: new Date().getHours(),
        is_peak_hour: Number(new Date().getHours() >= 19 && new Date().getHours() <= 22),
      },
    }),
  });
}

function extractOffer(message: string, basePrice: number): number {
  const match = message.toLowerCase().match(/(?:rp\s*)?(\d+(?:[.]\d{3})?)\s*(ribu|rb)?/);
  if (!match) return basePrice;
  const amount = Number(match[1].replaceAll(".", ""));
  return Number.isFinite(amount) ? amount * (match[2] ? 1000 : 1) : basePrice;
}
