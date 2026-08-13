import { apiFetch } from "@/services/api";
import type { Customer } from "@/types/customer";

export function getCustomers(): Promise<Customer[]> {
  return apiFetch<Customer[]>("/dashboard/customers");
}
