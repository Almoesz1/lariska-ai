import { apiFetch } from "@/services/api";
import type { Product } from "@/types/product";

export function getProducts(): Promise<Product[]> {
  return apiFetch<Product[]>("/dashboard/products");
}
