"use client";
import Image from "next/image";
import Link from "next/link";
import { Shirt } from "lucide-react";
import type { Product } from "@/lib/api/types";
import { toman } from "@/lib/format";
export function ProductCard({ product: p }: { product: Product }) {
  return (
    <article className="product-card">
      <Link
        href={"/products/" + encodeURIComponent(p.slug)}
        className="product-media"
        aria-label={"مشاهدهٔ " + p.name}
      >
        {p.off > 0 && <span className="product-discount">{p.off}٪ تخفیف</span>}
        {p.image ? (
          <Image
            src={p.image}
            alt={p.name}
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
          {p.off > 0 && <del className="old-price">{toman(p.price)}</del>}
          {toman(p.final_price)}
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
