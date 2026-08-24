import { apiFetch } from "@/services/api";
import type { Order, OrderStatus } from "@/types/order";

export function getOrders(): Promise<Order[]> {
  return apiFetch<Order[]>("/dashboard/orders");
}

export function updateOrderStatus(orderId: string, status: OrderStatus): Promise<Order> {
  return apiFetch<Order>(`/dashboard/orders/${orderId}`, {
    method: "PUT",
    body: JSON.stringify({ status }),
  });
}
