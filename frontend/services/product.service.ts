import { apiFetch } from "@/services/api";
import type { Product } from "@/types/product";

export type ProductPayload = Omit<Product, "id" | "created_at" | "updated_at">;

export function getProducts(): Promise<Product[]> {
  return apiFetch<Product[]>("/dashboard/products");
}

export function createProduct(payload: ProductPayload): Promise<Product> {
  return apiFetch<Product>("/dashboard/products", { method: "POST", body: JSON.stringify(payload) });
}

export function updateProduct(id: string, payload: Partial<ProductPayload>): Promise<Product> {
  return apiFetch<Product>(`/dashboard/products/${id}`, { method: "PUT", body: JSON.stringify(payload) });
}
