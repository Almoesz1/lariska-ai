"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/services/api";
import { getCustomers } from "@/services/customer.service";
import type { Customer } from "@/types/customer";

export function useCustomers() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const refresh = useCallback(async () => {
    setIsLoading(true); setError(null);
    try { setCustomers(await getCustomers()); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Pelanggan tidak dapat dimuat."); }
    finally { setIsLoading(false); }
  }, []);
  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 0);
    return () => window.clearTimeout(timer);
  }, [refresh]);
  return { customers, isLoading, error, refresh };
}
