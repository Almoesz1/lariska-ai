export type Product = {
  id: string;
  name: string;
  description: string | null;
  category: string | null;
  price: number;
  floor_price: number;
  stock: number;
  sku: string | null;
  unit_label: string | null;
  reorder_point: number;
  specifications: Record<string, unknown>;
  search_aliases: string[];
  image_url: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};
