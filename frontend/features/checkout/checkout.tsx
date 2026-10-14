"use client";
import { toman, number } from "@/lib/format";
import { CartVariant } from "@/features/cart/line-product";
import { useRef, useState } from "react";
import { useStored, storeSession } from "@/lib/api/storage";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useApi } from "@/lib/api/hooks";
import { api } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import type { Cart, Checkout } from "@/lib/api/types";
import { Addresses } from "@/features/account/addresses";
import { CartSummary } from "@/features/cart/cart";
import { Empty, ErrorNotice, Loading } from "@/components/ui/states";
export const pendingCheckoutKey = "osp.pendingCheckout";
export function CheckoutView() {
  const q = useApi<Cart>("cart/"),
    [selected, setSelected] = useState<number>(),
    [coupon, setCoupon] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState<unknown>(),
    lock = useRef(false),
    router = useRouter();
  const stored = useStored(pendingCheckoutKey, true);
  let recovery: { orderId?: number; startedAt: number } | null = null;
  try {
    recovery = stored ? JSON.parse(stored) : null;
  } catch {
    /* Unavailable or invalid browser storage is treated as absent. */
  }
  async function submit() {
    if (lock.current || !selected || recovery) return;
    lock.current = true;
    setBusy(true);
    setError(undefined);
    const marker = { startedAt: Date.now(), checkoutKey: crypto.randomUUID() };
    if (!storeSession(pendingCheckoutKey, marker)) {
      setError(
        new Error(
          "ذخیرهٔ وضعیت بازیابی در این مرورگر ممکن نیست؛ ثبت سفارش آغاز نشد.",
        ),
      );
      lock.current = false;
      setBusy(false);
      return;
    }
    try {
      const result = await api<Checkout>("orders/create/", {
        method: "POST",
        body: {
          address_id: selected,
          checkout_key: marker.checkoutKey,
          ...(coupon.trim() ? { coupon_code: coupon.trim() } : {}),
        },
      });
      const saved = { ...marker, orderId: result.order.id };
      storeSession(pendingCheckoutKey, saved);
      router.push("/payment/result?order=" + result.order.id);
    } catch (e) {
      setError(e);
      if (
        e instanceof ApiError &&
        [400, 401, 403, 404, 405, 429].includes(e.status)
      ) {
        storeSession(pendingCheckoutKey, null);
      } else storeSession(pendingCheckoutKey, marker);
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  if (q.isPending) return <Loading />;
  if (q.isError)
    return <ErrorNotice error={q.error} retry={() => q.refetch()} />;
  if (recovery)
    return (
      <div className="panel stack">
        <h2>ابتدا سفارش قبلی را بررسی کنید.</h2>
        <p>
          برای جلوگیری از سفارش تکراری، ثبت خودکار دوباره انجام نمی‌شود. درخواست
          قبلی ممکن است در سرور ثبت شده باشد.
        </p>
        {recovery.orderId && (
          <Link
            className="button"
            href={"/payment/result?order=" + recovery.orderId}
          >
            بازیابی سفارش ثبت‌شده
          </Link>
        )}
        <Link className="button secondary" href="/account/orders">
          بررسی سفارش‌های من
        </Link>
        <button
          className="text-link"
          onClick={() => {
            if (
              window.confirm(
                "سفارش‌های قبلی را بررسی کرده‌اید و می‌خواهید ثبت سفارش جدید را خودتان آغاز کنید؟",
              )
            ) {
              storeSession(pendingCheckoutKey, null);
            }
          }}
        >
          پس از بررسی، شروع سفارش جدید
        </button>
      </div>
    );
  if (!q.data.items.length)
    return (
      <Empty
        title="سبد خرید خالی است"
        description="پیش از ثبت سفارش، لباس موردنظرتان را به سبد اضافه کنید."
        href="/products"
      />
    );
  return (
    <div className="two-col">
      <div className="stack">
        <Addresses select={setSelected} selected={selected} />
        <div className="panel stack">
          <h2>مرور انتخاب‌ها</h2>
          {q.data.items.map((i) => (
            <div className="spread" key={`${i.product_id}:${i.variant_id}`}>
              <span>
                {i.name} × {number(i.quantity)}
                <br />
                <CartVariant item={i} />
              </span>
              <span className="small" style={{ whiteSpace: "nowrap" }}>
                {toman(i.total_price)}
              </span>
            </div>
          ))}
          <label className="field">
            کد تخفیف (اختیاری)
            <input
              dir="ltr"
              value={coupon}
              onChange={(e) => setCoupon(e.target.value)}
              maxLength={40}
              pattern="[a-zA-Z0-9_-]*"
            />
          </label>
          <p className="small subtle">
            اعتبار و مبلغ تخفیف هنگام ثبت سفارش بررسی می‌شود.
          </p>
        </div>
      </div>
      <CartSummary cart={q.data}>
        <button
          className="button"
          disabled={!selected || busy}
          onClick={submit}
        >
          {busy ? "در حال ثبت سفارش…" : "ثبت سفارش و رزرو"}
        </button>
        <p className="small subtle">
          مبلغ نهایی و مهلت رزرو پس از ثبت، از پاسخ سفارش نمایش داده می‌شوند.
          ثبت سفارش به معنی پرداخت نیست.
        </p>
        {error !== undefined && <ErrorNotice error={error} />}
      </CartSummary>
    </div>
  );
}
