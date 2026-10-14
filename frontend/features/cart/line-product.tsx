"use client";
import { useStored } from "@/lib/api/storage";
import { useApi } from "@/lib/api/hooks";
import type { CartItem, Page, Product, ProductDetail } from "@/lib/api/types";
export function useCartProduct(item: CartItem) {
  const stored = useStored("osp.publicProductIndex");
  let known: string | undefined;
  try {
    const candidate = stored ? JSON.parse(stored)[item.product_id] : undefined;
    if (typeof candidate === "string") known = candidate;
  } catch {
    /* Public index is optional, never an authority. */
  }
  const lookup = useApi<Page<Product>>(
    "products/?search=" +
      encodeURIComponent(item.name.slice(0, 200)) +
      "&limit=100",
    !known,
  );
  const slug =
    known ?? lookup.data?.results.find((p) => p.id === item.product_id)?.slug;
  const detail = useApi<ProductDetail>(
    "products/" + encodeURIComponent(slug ?? "missing") + "/",
    !!slug,
  );
  return {
    slug,
    product: detail.data,
    variant: detail.data?.variants.find((v) => v.id === item.variant_id),
  };
}
export function CartVariant({ item }: { item: CartItem }) {
  const { variant } = useCartProduct(item);
  if (!item.variant_id) return null;
  return (
    <span className="small subtle">
      {variant
        ? `رنگ: ${variant.color || "بدون رنگ"} / سایز: ${variant.size || "بدون سایز"}`
        : "جزئیات این تنوع در حال دریافت یا در کاتالوگ در دسترس نیست؛ انتخاب با شناسهٔ مستقل حفظ می‌شود."}
    </span>
  );
}
