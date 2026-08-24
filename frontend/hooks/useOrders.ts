"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/services/api";
import { getOrders } from "@/services/order.service";
import type { Order } from "@/types/order";

export function useOrders() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const refresh = useCallback(async () => {
    setIsLoading(true); setError(null);
    try { setOrders(await getOrders()); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Pesanan tidak dapat dimuat."); }
    finally { setIsLoading(false); }
  }, []);
  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 0);
    return () => window.clearTimeout(timer);
  }, [refresh]);
  return { orders, isLoading, error, refresh };
}
