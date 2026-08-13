export type Product = {
  id: string;
  name: string;
  description: string | null;
  category: string | null;
  price: number;
  floor_price: number;
  stock: number;
  image_url: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};
