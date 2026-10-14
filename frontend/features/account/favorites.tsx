"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ProductCard } from "@/features/catalog/card";
import { useApi } from "@/lib/api/hooks";
import { api } from "@/lib/api/client";
import type { Page, Product } from "@/lib/api/types";
import { Empty, ErrorNotice, Loading } from "@/components/ui/states";
export function Favorites() {
  const [offset, setOffset] = useState(0),
    path = "favorites/?limit=12&offset=" + offset,
    q = useApi<Page<Product>>(path),
    client = useQueryClient();
  const remove = useMutation({
    mutationFn: (id: number) =>
      api("products/" + id + "/favorite/", { method: "DELETE" }),
    onSuccess: () => client.invalidateQueries({ queryKey: [path] }),
  });
  return (
    <div className="stack">
      <h2>علاقه‌مندی‌ها</h2>
      {q.isPending ? (
        <Loading />
      ) : q.isError ? (
        <ErrorNotice error={q.error} retry={() => q.refetch()} />
      ) : q.data.results.length ? (
        <div className="product-grid">
          {q.data.results.map((p) => (
            <div key={p.id}>
              <ProductCard product={p} />
              <button
                className="text-link small"
                disabled={remove.isPending}
                onClick={() => remove.mutate(p.id)}
              >
                حذف از علاقه‌مندی‌ها
              </button>
            </div>
          ))}
        </div>
      ) : (
        <Empty
          title="انتخابی ذخیره نکرده‌اید"
          description="لباس‌هایی را که دوست دارید ذخیره کنید و بعداً دوباره به آن‌ها سر بزنید."
          href="/products"
        />
      )}
      {q.data && (offset > 0 || q.data.next) && (
        <nav className="row">
          <button
            className="button secondary"
            disabled={!offset}
            onClick={() => setOffset(offset - 12)}
          >
            قبل
          </button>
          <button
            className="button secondary"
            disabled={!q.data.next}
            onClick={() => setOffset(offset + 12)}
          >
            بعد
          </button>
        </nav>
      )}
      {remove.isError && <ErrorNotice error={remove.error} />}
    </div>
  );
}
