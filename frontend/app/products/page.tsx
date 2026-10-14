import { Suspense } from "react";
import type { Metadata } from "next";
import { publicAPI, siteURL } from "@/lib/api/server";
import type { Category } from "@/lib/api/types";
import { Catalog } from "@/features/catalog/list";
import { Loading } from "@/components/ui/states";
export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<{ category?: string; search?: string }>;
}): Promise<Metadata> {
  const p = await searchParams,
    category = p.category
      ? await publicAPI<Category>(
          "categories/" + encodeURIComponent(p.category) + "/",
        )
      : undefined,
    base = siteURL();
  return {
    title: category ? category.name + " | لباس" : "فروشگاه لباس",
    description: category
      ? "لباس‌های دستهٔ " + category.name
      : "جست‌وجو و انتخاب لباس از کاتالوگ فروشگاه",
    alternates: base
      ? {
          canonical: new URL(
            "/products" +
              (category
                ? "?category=" + encodeURIComponent(category.slug)
                : ""),
            base,
          ).href,
        }
      : undefined,
    robots: p.search ? { index: false, follow: true } : undefined,
  };
}
export default function Page() {
  return (
    <div className="container page">
      <div className="section-head">
        <div>
          <p className="eyebrow">کاتالوگ / انتخاب شما</p>
          <h1>همهٔ لباس‌ها</h1>
        </div>
      </div>
      <Suspense fallback={<Loading />}>
        <Catalog />
      </Suspense>
    </div>
  );
}
