import { productStructuredData, safeJSON } from "@/lib/api/structured-data";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ProductDetailView } from "@/features/product/detail";
import { configuration } from "@/lib/auth/bff";
import { publicAPI, siteURL } from "@/lib/api/server";
import type { ProductDetail } from "@/lib/api/types";
export const dynamic = "force-dynamic";
export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params,
    p = await publicAPI<ProductDetail>(
      "products/" + encodeURIComponent(slug) + "/",
    );
  const base = siteURL();
  return {
    title: p?.name ?? "لباس",
    description: p?.description?.replace(/<[^>]+>/g, "").slice(0, 160),
    alternates: base
      ? {
          canonical: new URL("/products/" + encodeURIComponent(slug), base)
            .href,
        }
      : undefined,
  };
}
export default async function Page({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  let structured: unknown;
  try {
    const c = configuration(),
      r = await fetch(
        c.upstream + "/api/v1/products/" + encodeURIComponent(slug) + "/",
        {
          cache: "no-store",
          redirect: "error",
          signal: AbortSignal.timeout(5000),
        },
      );
    if (r.status === 404) notFound();
    const base = siteURL();
    if (r.ok && base) {
      const product = (await r.json()) as ProductDetail;
      structured = productStructuredData(
        product,
        new URL("/products/" + encodeURIComponent(slug), base).href,
      );
    }
  } catch (e) {
    if (e instanceof Error && e.message.includes("NEXT_HTTP_ERROR_FALLBACK"))
      throw e;
  }
  return (
    <div className="container page">
      {structured !== undefined && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: safeJSON(structured) }}
        />
      )}
      <ProductDetailView slug={slug} />
    </div>
  );
}
