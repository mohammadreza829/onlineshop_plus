"use client";
import Link from "next/link";
import { useSyncExternalStore } from "react";
const subscribe = () => () => {};
const clientSnapshot = () => true;
const serverSnapshot = () => false;
import { ArrowUpLeft } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import type { Category, Product, Page } from "@/lib/api/types";
import { ProductGrid } from "./card";
import { Empty, ErrorNotice, Loading } from "@/components/ui/states";
export function HomeCatalog({
  initialProducts,
  initialCategories,
}: {
  initialProducts?: Page<Product>;
  initialCategories?: Page<Category>;
}) {
  // Header may populate shared cache before a streamed page hydrates. Keep the
  // server loading state until hydration when SSR data was unavailable.
  const hydrated = useSyncExternalStore(
    subscribe,
    clientSnapshot,
    serverSnapshot,
  );
  const categories = useQuery({
      queryKey: ["categories/?roots_only=true&limit=100"],
      queryFn: ({ signal }) =>
        api<Page<Category>>("categories/?roots_only=true&limit=100", {
          signal,
        }),
      initialData: initialCategories,
    }),
    products = useQuery({
      queryKey: ["products/?ordering=-created&limit=8"],
      queryFn: ({ signal }) =>
        api<Page<Product>>("products/?ordering=-created&limit=8", { signal }),
      initialData: initialProducts,
    });
  return (
    <>
      <section className="section categories-section">
        <div className="section-head">
          <div>
            <p className="eyebrow">از کجا شروع کنیم؟</p>
            <h2>در میان دسته‌ها</h2>
          </div>
          <Link className="text-link small" href="/products">
            دیدن همه
            <ArrowUpLeft size={18} />
          </Link>
        </div>
        {categories.isPending || (!hydrated && !initialCategories) ? (
          <Loading />
        ) : categories.isError ? (
          <ErrorNotice
            error={categories.error}
            retry={() => categories.refetch()}
          />
        ) : categories.data.results.length ? (
          <nav className="category-list" aria-label="دسته‌های لباس">
            {categories.data.results.map((c, index) => (
              <Link
                key={c.id}
                href={"/products?category=" + encodeURIComponent(c.slug)}
              >
                <span className="category-index" aria-hidden="true">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span>{c.name}</span>
                <ArrowUpLeft size={18} aria-hidden="true" />
              </Link>
            ))}
          </nav>
        ) : (
          <p className="subtle">هنوز دسته‌ای در فروشگاه ثبت نشده است.</p>
        )}
      </section>
      <section id="latest" className="section latest-section">
        <div className="section-head">
          <div>
            <p className="eyebrow">تازه به فروشگاه رسیده</p>
            <h2>تازه‌ترین لباس‌ها</h2>
          </div>
          <Link className="text-link small" href="/products?ordering=-created">
            مشاهدهٔ کاتالوگ
            <ArrowUpLeft size={18} />
          </Link>
        </div>
        {products.isPending || (!hydrated && !initialProducts) ? (
          <Loading />
        ) : products.isError ? (
          <ErrorNotice
            error={products.error}
            retry={() => products.refetch()}
          />
        ) : products.data.results.length ? (
          <ProductGrid products={products.data.results} />
        ) : (
          <Empty
            title="کاتالوگ در انتظار اولین انتخاب‌هاست"
            description="هنوز محصولی ثبت نشده است. لباس‌ها پس از اضافه‌شدن به فروشگاه، همین‌جا نمایش داده می‌شوند."
          />
        )}
      </section>
    </>
  );
}
