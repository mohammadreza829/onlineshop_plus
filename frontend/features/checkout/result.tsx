"use client";
import { useState, useRef } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useApi } from "@/lib/api/hooks";
import { api } from "@/lib/api/client";
import type { Order } from "@/lib/api/types";
import { toman, statusLabels } from "@/lib/format";
import { ErrorNotice, Loading } from "@/components/ui/states";
import { Reservation } from "./reservation";
export function PaymentResult() {
  const params = useSearchParams(),
    id = params.get("order") ?? "",
    [busy, setBusy] = useState(false),
    [error, setError] = useState<unknown>(),
    lock = useRef(false),
    q = useApi<Order>("orders/" + id + "/", /^[1-9]\d*$/.test(id));
  async function pay() {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError(undefined);
    try {
      const data = await api<{ payment_url: string; demo?: boolean }>(
        "orders/" + id + "/payment/",
        { method: "POST" },
      );
      const u = new URL(data.payment_url);
      if (
        u.protocol !== "https:" &&
        !(
          data.demo === true &&
          u.protocol === "http:" &&
          ["127.0.0.1", "localhost"].includes(u.hostname)
        )
      )
        throw new Error("نشانی درگاه معتبر نیست.");
      window.location.assign(u.href);
    } catch (e) {
      setError(e);
      lock.current = false;
      setBusy(false);
    }
  }
  if (!/^[1-9]\d*$/.test(id))
    return (
      <div className="empty">
        <h2>سفارش معتبری مشخص نشده است.</h2>
        <p>پارامتر بازگشت درگاه یا Status به‌تنهایی اثبات پرداخت نیست.</p>
        <Link className="button secondary" href="/account/orders">
          سفارش‌های من
        </Link>
      </div>
    );
  if (q.isPending) return <Loading />;
  if (q.isError)
    return <ErrorNotice error={q.error} retry={() => q.refetch()} />;
  const o = q.data,
    title =
      o.status === "needs_review"
        ? "این سفارش به بررسی نیاز دارد."
        : o.is_paid && o.status !== "canceled"
          ? "پرداخت در سرور ثبت شده است."
          : o.is_paid
            ? "سفارش لغو شده؛ وضعیت مالی نیازمند پیگیری است."
            : o.status === "expired"
              ? "مهلت رزرو به پایان رسیده است."
              : o.status === "canceled"
                ? "این سفارش لغو شده است."
                : "تایید پرداخت هنوز ثبت نشده است.";
  return (
    <div className="panel payment-state stack">
      <p className="eyebrow">وضعیت سفارش / اطلاعات سرور</p>
      <h1 style={{ fontSize: 30 }}>{title}</h1>
      <p>
        شمارهٔ سفارش: <bdi dir="ltr">{o.order_number}</bdi>
      </p>
      <p>وضعیت سفارش: {statusLabels[o.status] ?? o.status_display}</p>
      <strong>مبلغ نهایی: {toman(o.total_price)}</strong>
      {o.payment_summary?.needs_reconciliation && (
        <p className="notice">
          پرداخت ثبت شده؛ تکمیل سفارش در انتظار بازیابی است.
        </p>
      )}
      {o.payment_summary?.needs_refund && (
        <p className="notice">این پرداخت نیازمند پیگیری بازپرداخت است.</p>
      )}
      {o.payment_summary?.refund_status === "confirmed" && (
        <p className="notice">سند بازپرداخت انجام‌شده ثبت شده است.</p>
      )}
      {o.payment_summary?.status === "unknown" && (
        <p className="notice">
          نتیجه مالی نامشخص است؛ پرداخت تازه انجام ندهید.
        </p>
      )}
      {o.coupon_code && <p>تخفیف کوپن: {toman(o.coupon_discount)}</p>}
      {!o.is_paid && o.status === "pending" && (
        <p className="notice">
          اگر از درگاه برگشته‌اید، پرداخت ممکن است هنوز در انتظار تایید یا
          استعلام باشد. پیش از شروع مجدد، وضعیت را بررسی کنید.
        </p>
      )}
      {o.status === "needs_review" && (
        <p className="notice">
          این وضعیت موفقیت عادی خرید نیست؛ پرداخت و تامین سفارش باید توسط عملیات
          بررسی شوند.
        </p>
      )}
      {o.is_paid && (
        <p className="notice">
          سبد خودکار پاک نشده است تا انتخاب‌های تازهٔ شما حذف نشوند. اقلام
          پرداخت‌شده را در سبد بررسی و انتخابی حذف کنید؛ حذف مشروط و اتمیک در
          API فعلی وجود ندارد.
        </p>
      )}
      {o.is_payable && (
        <>
          <Reservation until={o.reserved_until} />
          <button className="button" disabled={busy} onClick={pay}>
            {busy ? "در حال شروع پرداخت…" : "دریافت نشانی درگاه و پرداخت"}
          </button>
          <p className="small subtle">
            در حالت دموی محلی هیچ پولی برداشت نمی‌شود. پس از نتیجهٔ درگاه
            آزمایشی، به همین صفحه برمی‌گردید؛ وضعیت فقط از سرور خوانده می‌شود.
          </p>
        </>
      )}
      <button
        className="button secondary"
        disabled={q.isFetching}
        onClick={() => q.refetch()}
      >
        بررسی دوبارهٔ وضعیت
      </button>
      <div className="row">
        <Link className="text-link" href={"/account/orders/" + o.id}>
          جزئیات سفارش
        </Link>
        <Link className="text-link" href="/cart">
          بررسی سبد خرید
        </Link>
      </div>
      {error !== undefined && <ErrorNotice error={error} />}
    </div>
  );
}
