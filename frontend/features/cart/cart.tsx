"use client";
import { useCartProduct } from "./line-product";
import Image from "next/image";
import { Shirt } from "lucide-react";
import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2, ArrowUpLeft } from "lucide-react";
import { useApi } from "@/lib/api/hooks";
import { api } from "@/lib/api/client";
import type { Cart, CartItem } from "@/lib/api/types";
import { lineKey, toman, number } from "@/lib/format";
import { Empty, ErrorNotice, Loading } from "@/components/ui/states";
import { useToast } from "@/components/providers";
function CartLine({ item }: { item: CartItem }) {
  const { slug: resolved, product, variant: v } = useCartProduct(item);
  const image =
    product?.images.find((image) => image.is_primary) ?? product?.images[0];
  const client = useQueryClient(),
    toast = useToast();
  const path = `cart/items/${item.product_id}/`;
  const change = useMutation({
    mutationFn: (quantity: number) =>
      api<Cart>(path, {
        method: "PATCH",
        body: {
          quantity,
          ...(item.variant_id ? { variant_id: item.variant_id } : {}),
        },
      }),
    onSuccess: (cart) => {
      client.setQueryData(["cart/"], cart);
      if (cart.quantity_clamped) toast("تعداد مطابق موجودی فعلی اصلاح شد.");
    },
  });
  const remove = useMutation({
    mutationFn: () =>
      api(path + (item.variant_id ? "?variant_id=" + item.variant_id : ""), {
        method: "DELETE",
      }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["cart/"] }),
  });
  return (
    <article className="cart-line">
      <div className="cart-product">
        <div className="cart-thumbnail" aria-hidden="true">
          {image?.image ? (
            <Image
              src={image.image}
              alt=""
              width={88}
              height={112}
              unoptimized
            />
          ) : (
            <Shirt size={28} strokeWidth={1.3} />
          )}
        </div>
        <div className="cart-product-copy">
          <h3>
            {resolved ? (
              <Link href={"/products/" + encodeURIComponent(resolved)}>
                {item.name}
              </Link>
            ) : (
              item.name
            )}
          </h3>
          {item.variant_id && (
            <p className="small subtle">
              {v
                ? `رنگ: ${v.color} / سایز: ${v.size}`
                : `انتخاب ${number(item.variant_id)} — جزئیات تنوع در حال دریافت یا ناموجود است.`}
            </p>
          )}
          <p className="small subtle">قیمت واحد: {toman(item.price)}</p>
          <strong>{toman(item.total_price)}</strong>
        </div>
      </div>
      <div className="stack">
        <label className="field">
          تعداد
          <select
            className="quantity"
            value={item.quantity}
            disabled={change.isPending || remove.isPending}
            onChange={(e) => change.mutate(Number(e.target.value))}
          >
            {[
              ...Array.from(
                {
                  length: Math.max(
                    1,
                    Math.min(
                      Math.max(
                        item.quantity,
                        v?.inventory ?? product?.inventory ?? item.quantity,
                      ),
                      100,
                    ),
                  ),
                },
                (_, i) => i + 1,
              ),
              ...(item.quantity > 100 ? [item.quantity] : []),
            ].map((n) => (
              <option key={n} value={n}>
                {number(n)}
              </option>
            ))}
          </select>
        </label>
        <button
          className="text-link"
          aria-label={
            "حذف " + item.name + (v ? " " + v.color + " " + v.size : "")
          }
          disabled={remove.isPending || change.isPending}
          onClick={() => remove.mutate()}
        >
          <Trash2 size={16} />
          حذف این انتخاب
        </button>
      </div>
      {change.isError && <ErrorNotice error={change.error} />}{" "}
      {remove.isError && <ErrorNotice error={remove.error} />}
    </article>
  );
}
export function CartSummary({
  cart,
  children,
}: {
  cart: Cart;
  children?: React.ReactNode;
}) {
  return (
    <aside className="panel summary stack">
      <h2 style={{ fontSize: 24 }}>خلاصهٔ سبد</h2>
      <dl>
        <div>
          <dt>جمع کالاها</dt>
          <dd>{toman(cart.subtotal)}</dd>
        </div>
        <div>
          <dt>تخفیف کالاها</dt>
          <dd>{toman(cart.discount)}</dd>
        </div>
        <div>
          <dt>هزینهٔ ارسال</dt>
          <dd>{toman(cart.post_price)}</dd>
        </div>
        <div style={{ borderTop: "1px solid var(--border)", paddingTop: 16 }}>
          <dt>مبلغ کل</dt>
          <dd>
            <strong>{toman(cart.total_price)}</strong>
          </dd>
        </div>
      </dl>
      {children}
    </aside>
  );
}
export function CartView() {
  const q = useApi<Cart>("cart/");
  if (q.isPending) return <Loading />;
  if (q.isError)
    return <ErrorNotice error={q.error} retry={() => q.refetch()} />;
  if (!q.data.items.length)
    return (
      <Empty
        title="سبد شما منتظر انتخاب است"
        description="لباس موردنظرتان را انتخاب کنید؛ سبد روی همین مرورگر حفظ می‌شود."
        href="/products"
      />
    );
  return (
    <div className="two-col">
      <div className="panel">
        <p className="subtle small">
          {number(q.data.item_count)} عدد لباس · سبد این مرورگر
        </p>
        {q.data.items.map((item) => (
          <CartLine key={lineKey(item)} item={item} />
        ))}
      </div>
      <CartSummary cart={q.data}>
        <Link href="/checkout" className="button">
          ادامهٔ خرید
          <ArrowUpLeft size={18} />
        </Link>
        <p className="small subtle">
          موجودی و مبلغ هنگام ثبت سفارش دوباره بررسی می‌شوند.
        </p>
      </CartSummary>
    </div>
  );
}
