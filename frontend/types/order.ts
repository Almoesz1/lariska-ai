export type OrderStatus = "pending" | "paid" | "shipped" | "completed" | "cancelled";

export type Order = {
  id: string;
  customer_id: string;
  conversation_id: string | null;
  product_id: string;
  quantity: number;
  unit_price: number;
  discount_amount: number;
  total_amount: number;
  status: OrderStatus;
  created_at: string;
  updated_at: string;
};
