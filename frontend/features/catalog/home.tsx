"use client";
import Link from "next/link";
import { ArrowUpLeft, WifiOff } from "lucide-react";
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
  if (categories.isError && products.isError)
    return (
      <section
        className="panel catalog-offline"
        aria-labelledby="catalog-offline-title"
      >
        <WifiOff size={24} aria-hidden="true" />
        <div>
          <h2 id="catalog-offline-title">فعلاً به کاتالوگ دسترسی نداریم</h2>
          <p className="subtle">
            اطلاعات لباس‌ها از فروشگاه دریافت نشد. این وضعیت به معنی خالی‌بودن
            کاتالوگ نیست.
          </p>
          <ErrorNotice error={products.error} />
          <p className="small subtle" style={{ marginTop: 12 }}>
            اگر پروژه را روی لپ‌تاپ اجرا می‌کنید، بک‌اند Django هم باید روشن
            باشد. راهنمای اتصال در README فرانت آمده است.
          </p>
          <div className="row">
            <button
              className="button secondary"
              onClick={() => {
                void categories.refetch();
                void products.refetch();
              }}
            >
              تلاش دوباره
            </button>
            <Link className="text-link" href="/products">
              رفتن به کاتالوگ
              <ArrowUpLeft size={18} />
            </Link>
          </div>
        </div>
      </section>
    );
  return (
    <>
      <section className="section">
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
        {categories.isPending ? (
          <Loading />
        ) : categories.isError ? (
          <ErrorNotice
            error={categories.error}
            retry={() => categories.refetch()}
          />
        ) : categories.data.results.length ? (
          <nav className="category-list" aria-label="دسته‌های لباس">
            {categories.data.results.map((c) => (
              <Link
                key={c.id}
                href={"/products?category=" + encodeURIComponent(c.slug)}
              >
                {c.name}
              </Link>
            ))}
          </nav>
        ) : (
          <p className="subtle">هنوز دسته‌ای در فروشگاه ثبت نشده است.</p>
        )}
      </section>
      <section className="section" style={{ paddingTop: 16 }}>
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
        {products.isPending ? (
          <div
            role="status"
            aria-label="دریافت لباس‌ها"
            className="catalog-skeleton"
          >
            {[0, 1, 2, 3].map((i) => (
              <div className="skeleton" key={i} />
            ))}
          </div>
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
