"use client";
import { useId, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { SlidersHorizontal, Search, ArrowLeft, ArrowRight } from "lucide-react";
import { useApi } from "@/lib/api/hooks";
import type { Page, Product, Category } from "@/lib/api/types";
import { catalogQuery } from "@/lib/api/filters";
import { ascii, number } from "@/lib/format";
import { ProductGrid } from "./card";
import { Empty, ErrorNotice, Loading } from "@/components/ui/states";
import { Sheet } from "@/components/ui/sheet";
function Filters({ close }: { close?: () => void }) {
  const q = useSearchParams(),
    router = useRouter(),
    id = useId();
  const categories = useApi<Page<Category>>("categories/?limit=100");
  function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget),
      p = new URLSearchParams(q.toString());
    for (const key of [
      "category",
      "stock",
      "min_price",
      "max_price",
      "ordering",
    ]) {
      const value = ascii(String(f.get(key) ?? "")).trim();
      if (value) p.set(key, value);
      else p.delete(key);
    }
    p.delete("offset");
    router.push("/products?" + p.toString());
    close?.();
  }
  return (
    <form className="filter-form" onSubmit={submit} key={q.toString()}>
      <label className="field" htmlFor={id + "category"}>
        دسته‌بندی
        <select
          id={id + "category"}
          name="category"
          defaultValue={q.get("category") ?? ""}
        >
          <option value="">همهٔ دسته‌ها</option>
          {categories.data?.results.map((c) => (
            <option key={c.id} value={c.slug}>
              {c.name}
            </option>
          ))}
        </select>
      </label>
      {categories.isError && <p className="small">دریافت دسته‌ها ممکن نشد.</p>}
      <label className="field" htmlFor={id + "stock"}>
        موجودی
        <select
          id={id + "stock"}
          name="stock"
          defaultValue={q.get("stock") ?? ""}
        >
          <option value="">همه</option>
          <option value="available">موجود</option>
          <option value="out">ناموجود</option>
        </select>
      </label>
      <label className="field" htmlFor={id + "min"}>
        حداقل قیمت پایه (تومان)
        <input
          name="min_price"
          id={id + "min"}
          inputMode="numeric"
          defaultValue={q.get("min_price") ?? ""}
        />
      </label>
      <label className="field" htmlFor={id + "max"}>
        حداکثر قیمت پایه (تومان)
        <input
          name="max_price"
          id={id + "max"}
          inputMode="numeric"
          defaultValue={q.get("max_price") ?? ""}
        />
      </label>
      <p className="subtle small">
        فیلتر و ترتیب قیمت بر اساس قیمت پایه، پیش از تخفیف و انتخاب تنوع است.
      </p>
      <label className="field" htmlFor={id + "order"}>
        مرتب‌سازی
        <select
          name="ordering"
          id={id + "order"}
          defaultValue={q.get("ordering") ?? "-created"}
        >
          <option value="-created">تازه‌ترین</option>
          <option value="price">قیمت پایه: کم به زیاد</option>
          <option value="-price">قیمت پایه: زیاد به کم</option>
          <option value="name">نام محصول</option>
          <option value="relevance">مرتبط‌ترین جست‌وجو</option>
        </select>
      </label>
      <button className="button" type="submit">
        اعمال فیلتر
      </button>
      <button
        type="button"
        className="text-link"
        onClick={() => {
          router.push("/products");
          close?.();
        }}
      >
        پاک‌کردن فیلترها
      </button>
    </form>
  );
}
export function Catalog() {
  const search = useSearchParams(),
    router = useRouter(),
    params = catalogQuery(new URLSearchParams(search.toString())),
    q = useApi<Page<Product>>("products/?" + params.toString());
  const offset = Number(params.get("offset") ?? 0),
    limit = Number(params.get("limit") ?? 12);
  function page(delta: number) {
    const p = new URLSearchParams(search.toString());
    p.set("offset", String(Math.max(0, offset + delta * limit)));
    router.push("/products?" + p.toString());
  }
  function find(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const p = new URLSearchParams(search.toString()),
      v = String(new FormData(e.currentTarget).get("search") ?? "").trim();
    if (v) p.set("search", v);
    else p.delete("search");
    p.delete("offset");
    router.push("/products?" + p.toString());
  }
  return (
    <div className="catalog-layout">
      <aside className="filters desktop-only" aria-label="فیلتر محصولات">
        <Filters />
      </aside>
      <section aria-label="محصولات">
        <div className="catalog-toolbar">
          <form onSubmit={find} key={search.get("search")}>
            <label className="sr-only" htmlFor="catalog-search">
              جست‌وجوی لباس
            </label>
            <input
              className="input"
              id="catalog-search"
              name="search"
              placeholder="جست‌وجوی لباس…"
              maxLength={200}
              defaultValue={search.get("search") ?? ""}
            />
            <button className="button secondary" aria-label="جست‌وجو">
              <Search size={20} />
            </button>
          </form>
          <div className="mobile-only">
            <Sheet
              title="فیلتر و ترتیب"
              trigger={
                <button className="button secondary">
                  <SlidersHorizontal size={18} />
                  فیلتر
                </button>
              }
            >
              {(close) => (
                <div className="stack">
                  <Filters close={close} />
                </div>
              )}
            </Sheet>
          </div>
          {q.data && (
            <span className="subtle small" aria-live="polite">
              {number(q.data.count)} محصول
            </span>
          )}
        </div>
        {q.isPending ? (
          <Loading />
        ) : q.isError ? (
          <ErrorNotice error={q.error} retry={() => q.refetch()} />
        ) : q.data.results.length ? (
          <ProductGrid products={q.data.results} />
        ) : (
          <Empty
            title="لباسی با این انتخاب پیدا نشد"
            description="جست‌وجو یا فیلترها را تغییر دهید. موجودی نمایش‌داده‌شده از فروشگاه دریافت می‌شود."
          />
        )}
        {q.data && q.data.count > limit && (
          <nav className="pagination" aria-label="صفحه‌بندی">
            <button
              className="icon-button"
              aria-label="صفحه قبل"
              disabled={offset <= 0}
              onClick={() => page(-1)}
            >
              <ArrowRight size={20} />
            </button>
            <span className="small">
              صفحهٔ {number(Math.floor(offset / limit) + 1)}
            </span>
            <button
              className="icon-button"
              aria-label="صفحه بعد"
              disabled={!q.data.next}
              onClick={() => page(1)}
            >
              <ArrowLeft size={20} />
            </button>
          </nav>
        )}
      </section>
    </div>
  );
}
