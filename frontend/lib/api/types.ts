export type Page<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};
export type Category = {
  id: number;
  name: string;
  slug: string;
  parent: number | null;
};
export type Product = {
  id: number;
  sku: string;
  name: string;
  slug: string;
  price: string;
  off: number;
  final_price: string;
  inventory: number;
  category: Category | null;
  rating_average: number | null;
  rating_count: number;
};
export type Variant = {
  id: number;
  sku: string;
  color: string;
  size: string;
  price: string;
  final_price: string;
  inventory: number;
  is_active: boolean;
};
export type ProductDetail = Product & {
  description: string;
  variants: Variant[];
  features: { id: number; name: string; value: string }[];
  images: {
    id: number;
    image: string;
    description: string;
    is_primary: boolean;
    order: number;
  }[];
};
export type CartItem = {
  product_id: number;
  variant_id: number | null;
  name: string;
  price: string;
  quantity: number;
  total_price: string;
};
export type Cart = {
  items: CartItem[];
  subtotal: string;
  discount: string;
  post_price: string;
  total_price: string;
  item_count: number;
  is_empty: boolean;
  quantity_clamped?: boolean;
};
export type User = {
  id: number;
  phone: string;
  first_name: string;
  last_name: string;
};
export type Address = {
  id: number;
  title: string;
  receiver_name: string;
  receiver_phone: string;
  province: string;
  city: string;
  full_address: string;
  postal_code: string;
  is_default: boolean;
};
export type ClientOptions = {
  currency: string;
  time_zone: string;
  cart_quantity_max: number;
  cart_lines_max: number;
  pagination_default: number;
  pagination_max: number;
  provinces: { value: string; label: string }[];
};
export type OrderItem = {
  id: number;
  product: number;
  product_name: string;
  product_sku: string;
  variant: number | null;
  variant_sku: string;
  variant_color: string;
  variant_size: string;
  price: string;
  quantity: number;
  total_price: string;
};
export type Order = {
  id: number;
  order_number: string;
  first_name: string;
  last_name: string;
  phone: string;
  address: string;
  postal_code: string;
  post_price: string;
  total_price: string;
  coupon_code: string;
  coupon_discount: string;
  carrier: string;
  tracking_code: string;
  status: string;
  status_display: string;
  is_paid: boolean;
  ref_id: string;
  reserved_until: string | null;
  is_payable: boolean;
  review_reason?: string;
  payment_summary?: {
    status: string;
    needs_refund: boolean;
    needs_reconciliation: boolean;
    refund_status: string | null;
  } | null;
  items: OrderItem[];
  created: string;
};
export type Checkout = {
  message: string;
  reserved_until: string;
  order: Order;
};
export type Review = {
  id: number;
  rating: number;
  text: string;
  created: string;
  updated: string;
  status?: string;
};
export type OrderEvent = {
  id: number;
  sequence: number;
  kind: string;
  previous_status: string;
  status: string;
  carrier: string;
  tracking_code: string;
  created: string;
};
export type Notification = {
  id: number;
  order_id: number;
  order_number: string;
  event: OrderEvent;
  read_at: string | null;
  created: string;
};
