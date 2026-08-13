import { apiFetch } from "@/services/api";
import type { Order } from "@/types/order";

export function getOrders(): Promise<Order[]> {
  return apiFetch<Order[]>("/dashboard/orders");
}
