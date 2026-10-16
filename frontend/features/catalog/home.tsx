"use client";
import Link from "next/link";
import { useSyncExternalStore } from "react";

const subscribeHydration = () => () => {};
const browserSnapshot = () => true;
const serverSnapshot = () => false;
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
  const hydrated = useSyncExternalStore(
    subscribeHydration,
    browserSnapshot,
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
  // The header shares the category cache and may hydrate before this streamed boundary.
  // Match the server snapshot for the first hydration render, then show live query data.
  const categoryData = hydrated ? categories.data : initialCategories;
  const productData = hydrated ? products.data : initialProducts;
  const categoryPending = hydrated ? categories.isPending : !initialCategories;
  const productPending = hydrated ? products.isPending : !initialProducts;
  const categoryError = hydrated && categories.isError;
  const productError = hydrated && products.isError;
  if (categoryError && productError)
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
      <section className="section" data-reveal>
        <div className="section-head">
          <div>
            <p className="eyebrow">از اینجا شروع کن</p>
            <h2>برای هر سلیقه، یک مسیر</h2>
          </div>
          <Link className="text-link small" href="/products">
            دیدن همه
            <ArrowUpLeft size={18} />
          </Link>
        </div>
        {categoryPending ? (
          <Loading />
        ) : categoryError ? (
          <ErrorNotice
            error={categories.error}
            retry={() => categories.refetch()}
          />
        ) : categoryData?.results.length ? (
          <nav className="category-list" aria-label="دسته‌های لباس">
            {categoryData.results.map((c) => (
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
      <section className="section" data-reveal style={{ paddingTop: 16 }}>
        <div className="section-head">
          <div>
            <p className="eyebrow">نگاهی به تازه‌ها</p>
            <h2>تازه‌رسیده‌ها</h2>
          </div>
          <Link className="text-link small" href="/products?ordering=-created">
            مشاهدهٔ کاتالوگ
            <ArrowUpLeft size={18} />
          </Link>
        </div>
        {productPending ? (
          <div
            role="status"
            aria-label="دریافت لباس‌ها"
            className="catalog-skeleton"
          >
            {[0, 1, 2, 3].map((i) => (
              <div className="skeleton" key={i} />
            ))}
          </div>
        ) : productError ? (
          <ErrorNotice
            error={products.error}
            retry={() => products.refetch()}
          />
        ) : productData?.results.length ? (
          <ProductGrid products={productData.results} />
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
