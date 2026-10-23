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
  // Header shares category cache and may resolve before this streamed section hydrates.
  // Preserve the server snapshot on the first client render; then expose live queries.
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
  const categoryData = hydrated ? categories.data : initialCategories;
  const productData = hydrated ? products.data : initialProducts;
  return (
    <>
      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">از کجا شروع کنیم؟</p>
            <h2>از کدام دسته شروع کنیم؟</h2>
          </div>
          <Link className="text-link small" href="/products">
            دیدن همه
            <ArrowUpLeft size={18} />
          </Link>
        </div>
        {(hydrated ? categories.isPending : !initialCategories) ? (
          <Loading />
        ) : hydrated && categories.isError ? (
          <ErrorNotice
            error={categories.error}
            retry={() => categories.refetch()}
          />
        ) : categoryData!.results.length ? (
          <nav className="category-list" aria-label="دسته‌های لباس">
            {categoryData!.results.map((c) => (
              <Link
                key={c.id}
                href={"/products?category=" + encodeURIComponent(c.slug)}
              >
                {c.name}
                <ArrowUpLeft size={18} aria-hidden="true" />
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
        {(hydrated ? products.isPending : !initialProducts) ? (
          <Loading />
        ) : hydrated && products.isError ? (
          <ErrorNotice
            error={products.error}
            retry={() => products.refetch()}
          />
        ) : productData!.results.length ? (
          <ProductGrid products={productData!.results} />
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
