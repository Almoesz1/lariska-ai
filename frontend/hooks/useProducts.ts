"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/services/api";
import { getProducts } from "@/services/product.service";
import type { Product } from "@/types/product";

export function useProducts() {
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setProducts(await getProducts());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Produk tidak dapat dimuat.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 0);
    return () => window.clearTimeout(timer);
  }, [refresh]);

  return { products, isLoading, error, refresh };
}
