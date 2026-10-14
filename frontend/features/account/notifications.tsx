"use client";
import Link from "next/link";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { useApi } from "@/lib/api/hooks";
import type { Page, Notification } from "@/lib/api/types";
import { date, statusLabels } from "@/lib/format";
import { Loading, ErrorNotice, Empty } from "@/components/ui/states";
export function Notifications() {
  const [offset, setOffset] = useState(0),
    path = "notifications/?limit=20&offset=" + offset,
    q = useApi<Page<Notification>>(path),
    client = useQueryClient();
  const read = useMutation({
    mutationFn: (id: number) =>
      api("notifications/" + id + "/read/", { method: "POST" }),
    onSuccess: () => client.invalidateQueries({ queryKey: [path] }),
  });
  return (
    <div className="stack">
      <h2>اعلان‌های من</h2>
      <p className="small subtle">
        این اعلان‌ها داخل حساب هستند؛ پیامک یا push نیستند.
      </p>
      {q.isPending ? (
        <Loading />
      ) : q.isError ? (
        <ErrorNotice error={q.error} retry={() => q.refetch()} />
      ) : q.data.results.length ? (
        q.data.results.map((n) => (
          <article className="panel stack" key={n.id}>
            <div className="spread">
              <Link href={"/account/orders/" + n.order_id}>
                سفارش <bdi dir="ltr">{n.order_number}</bdi>
              </Link>
              {!n.read_at && <span className="badge">جدید</span>}
            </div>
            <p>{statusLabels[n.event.status] ?? "به‌روزرسانی سفارش"}</p>
            <time className="small subtle">{date(n.created)}</time>
            {!n.read_at && (
              <button
                className="text-link"
                disabled={read.isPending}
                onClick={() => read.mutate(n.id)}
              >
                خواندم
              </button>
            )}
          </article>
        ))
      ) : (
        <Empty
          title="اعلانی ندارید"
          description="تغییر وضعیت سفارش‌های شما اینجا نمایش داده می‌شود."
        />
      )}
      {q.data && (offset > 0 || q.data.next) && (
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
            disabled={!q.data.next}
            onClick={() => setOffset(offset + 20)}
          >
            بعد
          </button>
        </nav>
      )}
      {read.isError && <ErrorNotice error={read.error} />}
    </div>
  );
}
