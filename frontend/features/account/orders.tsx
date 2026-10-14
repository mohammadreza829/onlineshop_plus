"use client";
import Link from "next/link";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useApi } from "@/lib/api/hooks";
import { api } from "@/lib/api/client";
import type { Order, OrderEvent, Page } from "@/lib/api/types";
import { date, toman, number, statusLabels } from "@/lib/format";
import { Empty, ErrorNotice, Loading } from "@/components/ui/states";
import { Reservation } from "@/features/checkout/reservation";
export function Orders() {
  const [offset, setOffset] = useState(0),
    q = useApi<Page<Order>>("orders/?limit=10&offset=" + offset);
  return (
    <div className="stack">
      <h2>سفارش‌های من</h2>
      {q.isPending ? (
        <Loading />
      ) : q.isError ? (
        <ErrorNotice error={q.error} retry={() => q.refetch()} />
      ) : q.data.results.length ? (
        <div className="panel">
          {q.data.results.map((o) => (
            <article className="order-line" key={o.id}>
              <div>
                <Link href={"/account/orders/" + o.id}>
                  <strong dir="ltr">{o.order_number}</strong>
                </Link>
                <p className="small subtle">{date(o.created)}</p>
                <p className="small">{o.status_display}</p>
              </div>
              <div>
                <p>{toman(o.total_price)}</p>
                <Link
                  className="text-link small"
                  href={"/account/orders/" + o.id}
                >
                  جزئیات و پیگیری
                </Link>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <Empty
          title="هنوز سفارشی ثبت نشده است"
          description="پس از انتخاب لباس و ثبت سفارش، جزئیات آن اینجا نمایش داده می‌شود."
          href="/products"
        />
      )}
      {q.data && (q.data.next || offset > 0) && (
        <nav className="row">
          <button
            className="button secondary"
            disabled={!offset}
            onClick={() => setOffset(offset - 10)}
          >
            قبل
          </button>
          <button
            className="button secondary"
            disabled={!q.data.next}
            onClick={() => setOffset(offset + 10)}
          >
            بعد
          </button>
        </nav>
      )}
    </div>
  );
}
export function OrderDetail({ id }: { id: string }) {
  const q = useApi<Order>("orders/" + id + "/"),
    [offset, setOffset] = useState(0),
    tracking = useApi<Page<OrderEvent>>(
      "orders/" + id + "/tracking/?limit=20&offset=" + offset,
      !!q.data,
    ),
    client = useQueryClient();
  const cancel = useMutation({
    mutationFn: () =>
      api<Order>("orders/" + id + "/cancel/", { method: "POST" }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["orders/" + id + "/"] });
      void client.invalidateQueries({
        queryKey: ["orders/" + id + "/tracking/?limit=20&offset=" + offset],
      });
    },
  });
  if (q.isPending) return <Loading />;
  if (q.isError)
    return <ErrorNotice error={q.error} retry={() => q.refetch()} />;
  const o = q.data;
  return (
    <div className="stack">
      <div className="spread order-heading">
        <h2>
          سفارش <bdi dir="ltr">{o.order_number}</bdi>
        </h2>
        <span className="badge">{o.status_display}</span>
      </div>
      <div className="panel stack">
        <p>
          وضعیت مالی:{" "}
          {o.is_paid
            ? "پرداخت در سرور ثبت شده"
            : "پرداخت تاییدشده ثبت نشده است"}
        </p>
        {o.status === "needs_review" && (
          <p className="notice">
            این سفارش به بررسی عملیات نیاز دارد؛ پرداخت ثبت‌شده به معنی
            آماده‌بودن کالا نیست.
          </p>
        )}
        {o.status === "canceled" && o.is_paid && (
          <p className="notice">
            لغو سفارش به معنی انجام بازپرداخت بانکی نیست.
          </p>
        )}
        <p className="subtle small">{date(o.created)}</p>
        {o.items.map((i) => (
          <div className="spread" key={i.id}>
            <div>
              <p>
                {i.product_name} × {number(i.quantity)}
              </p>
              {i.variant && (
                <p className="subtle small">
                  {i.variant_color} / {i.variant_size}
                </p>
              )}
            </div>
            <p>{toman(i.total_price)}</p>
          </div>
        ))}
        <p>هزینهٔ ارسال: {toman(o.post_price)}</p>
        {o.coupon_code && (
          <p>
            کوپن <bdi dir="ltr">{o.coupon_code}</bdi> / تخفیف:{" "}
            {toman(o.coupon_discount)}
          </p>
        )}
        <strong>مبلغ سفارش: {toman(o.total_price)}</strong>
        <p>نشانی: {o.address}</p>
        <p className="small">
          کد پستی: <bdi dir="ltr">{o.postal_code}</bdi>
        </p>
        {o.carrier && (
          <p>
            ارسال با {o.carrier} · رهگیری:{" "}
            <bdi dir="ltr">{o.tracking_code}</bdi>
          </p>
        )}
        {o.is_payable && (
          <>
            <Reservation until={o.reserved_until} />
            <Link className="button" href={"/payment/result?order=" + o.id}>
              ادامهٔ پرداخت و بررسی وضعیت
            </Link>
          </>
        )}
        {!o.is_paid && o.status === "pending" && (
          <button
            className="button secondary"
            disabled={cancel.isPending}
            onClick={() => {
              if (window.confirm("این سفارش پرداخت‌نشده لغو شود؟"))
                cancel.mutate();
            }}
          >
            لغو سفارش پرداخت‌نشده
          </button>
        )}
        {cancel.isError && <ErrorNotice error={cancel.error} />}
      </div>
      <h3>پیگیری سفارش</h3>
      {tracking.isPending ? (
        <Loading />
      ) : tracking.isError ? (
        <ErrorNotice error={tracking.error} retry={() => tracking.refetch()} />
      ) : tracking.data.results.length ? (
        <ol className="timeline">
          {tracking.data.results.map((e) => (
            <li key={e.id}>
              <p>{statusLabels[e.status] ?? "به‌روزرسانی سفارش"}</p>
              <time className="small subtle">{date(e.created)}</time>
              {e.tracking_code && (
                <p className="small">
                  {e.carrier} / <bdi dir="ltr">{e.tracking_code}</bdi>
                </p>
              )}
            </li>
          ))}
        </ol>
      ) : (
        <p className="small subtle">
          برای این سفارش رویدادی ثبت نشده است؛ وضعیت فعلی در بالا آمده است.
        </p>
      )}
      {tracking.data && (offset > 0 || tracking.data.next) && (
        <nav className="row">
          <button
            className="button secondary"
            disabled={!offset}
            onClick={() => setOffset(offset - 20)}
          >
            قبل
          </button>
          <button
            className="button secondary"
            disabled={!tracking.data.next}
            onClick={() => setOffset(offset + 20)}
          >
            بعد
          </button>
        </nav>
      )}
    </div>
  );
}
