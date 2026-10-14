import type { Page } from "@playwright/test";
export const product = {
  id: 2,
  sku: "QA-VARIANT",
  name: "پیراهن تست متنوع",
  slug: "qa-variant",
  price: "200000",
  off: 0,
  final_price: "200000",
  inventory: 40,
  category: {
    id: 1,
    name: "لباس‌های تست ایزوله",
    slug: "qa-clothes",
    parent: null,
  },
  rating_average: null,
  rating_count: 0,
  description: "توضیح محصول آزمایشی",
  features: [],
  images: [],
  variants: [
    {
      id: 1,
      sku: "QA-BLACK-M",
      color: "مشکی",
      size: "M",
      price: "210000",
      final_price: "210000",
      inventory: 20,
      is_active: true,
    },
    {
      id: 2,
      sku: "QA-BLACK-L",
      color: "مشکی",
      size: "L",
      price: "220000",
      final_price: "220000",
      inventory: 0,
      is_active: true,
    },
    {
      id: 3,
      sku: "QA-CREAM-L",
      color: "کرم",
      size: "L",
      price: "230000",
      final_price: "230000",
      inventory: 20,
      is_active: true,
    },
  ],
};
export const order = {
  id: 1,
  order_number: "ORD-QA",
  first_name: "تست",
  last_name: "ایزوله",
  phone: "09120000001",
  address: "آدرس fixture",
  postal_code: "1234567890",
  post_price: "100000",
  total_price: "289000",
  coupon_code: "QA10",
  coupon_discount: "21000",
  carrier: "",
  tracking_code: "",
  status: "pending",
  status_display: "در انتظار پرداخت",
  is_paid: false,
  ref_id: "",
  reserved_until: "2099-01-01T00:00:00Z",
  is_payable: true,
  items: [
    {
      id: 1,
      product: 2,
      product_name: product.name,
      product_sku: product.sku,
      variant: 1,
      variant_sku: "QA-BLACK-M",
      variant_color: "مشکی",
      variant_size: "M",
      price: "210000",
      quantity: 1,
      total_price: "210000",
    },
  ],
  created: "2026-10-14T00:00:00Z",
};
export const pageOf = <T>(results: T[]) => ({
  count: results.length,
  next: null,
  previous: null,
  results,
});
export const address = {
  id: 1,
  title: "خانهٔ تست",
  receiver_name: "گیرنده تست",
  receiver_phone: "09120000001",
  province: "tehran",
  city: "تهران",
  full_address: "نشانی fixture ایزوله",
  postal_code: "1234567890",
  is_default: true,
};
export function cart(items: unknown[] = []) {
  return {
    items,
    subtotal: "210000",
    discount: "0",
    post_price: "100000",
    total_price: "310000",
    item_count: items.length,
    is_empty: !items.length,
  };
}
export async function mockAPI(
  page: Page,
  overrides: Record<string, unknown> = {},
) {
  await page.route("**/api/shop/**", async (route) => {
    const url = new URL(route.request().url()),
      path = url.pathname.replace("/api/shop/", "");
    let data: unknown =
      path === "csrf/"
        ? { csrf_token: "qa-only" }
        : path === "me/"
          ? {
              id: 1,
              phone: "09120000001",
              first_name: "تست",
              last_name: "ایزوله",
            }
          : path === "client-options/"
            ? {
                currency: "TOMAN",
                time_zone: "Asia/Tehran",
                cart_quantity_max: 100,
                cart_lines_max: 100,
                pagination_default: 20,
                pagination_max: 100,
                provinces: [{ value: "tehran", label: "تهران" }],
              }
            : path === "products/"
              ? pageOf([product])
              : path === "categories/"
                ? pageOf([product.category])
                : path === "products/qa-variant/"
                  ? product
                  : path === "products/qa-simple/"
                    ? {
                        ...product,
                        id: 1,
                        slug: "qa-simple",
                        name: "پیراهن تست ساده",
                        variants: [],
                      }
                    : path.includes("/recommendations/")
                      ? []
                      : path.includes("/reviews/")
                        ? pageOf([])
                        : path === "cart/"
                          ? cart()
                          : path === "addresses/"
                            ? pageOf([address])
                            : path === "orders/"
                              ? pageOf([order])
                              : path === "orders/1/"
                                ? order
                                : path.includes("/tracking/")
                                  ? pageOf([])
                                  : path === "notifications/" ||
                                      path === "favorites/"
                                    ? pageOf([])
                                    : {};
    if (path in overrides) data = overrides[path];
    await route.fulfill({ status: 200, json: data });
  });
}
