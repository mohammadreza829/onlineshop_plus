"use client";
import Image from "next/image";
import { Tilt } from "@/components/ui/tilt";
import Link from "next/link";
import { Shirt, ArrowUpLeft } from "lucide-react";
import type { Product, ProductDetail } from "@/lib/api/types";
import { useApi } from "@/lib/api/hooks";
import { toman } from "@/lib/format";
export function ProductCard({ product: p }: { product: Product }) {
  const d = useApi<ProductDetail>(
    "products/" + encodeURIComponent(p.slug) + "/",
  );
  const image = d.data?.images.find((i) => i.is_primary) ?? d.data?.images[0];
  return (
    <article className="product-card">
      <Tilt className="card-depth" strength={5}>
        <Link
          href={"/products/" + encodeURIComponent(p.slug)}
          className="product-media"
          aria-label={"مشاهدهٔ " + p.name}
        >
          {image?.image ? (
            <Image
              src={image.image}
              alt={image.description || p.name}
              width={480}
              height={640}
              unoptimized
              loading="lazy"
            />
          ) : (
            <span className="placeholder">
              <Shirt size={36} strokeWidth={1} />
              <span>تصویر ثبت نشده</span>
            </span>
          )}
        </Link>
      </Tilt>
      <div className="card-meta">
        <div>
          <p className="subtle small">{p.category?.name ?? "لباس"}</p>
          <h3>
            <Link href={"/products/" + encodeURIComponent(p.slug)}>
              {p.name}
            </Link>
          </h3>
          {p.inventory <= 0 && <span className="badge">ناموجود</span>}
        </div>
        <div className="price">
          {toman(p.final_price)}
          <ArrowUpLeft
            size={14}
            className="desktop-only"
            style={{ marginTop: 8 }}
          />
        </div>
      </div>
    </article>
  );
}
export function ProductGrid({ products }: { products: Product[] }) {
  return (
    <div className="product-grid">
      {products.map((p) => (
        <ProductCard product={p} key={p.id} />
      ))}
    </div>
  );
}
