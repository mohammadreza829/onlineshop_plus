import { site } from "@/config/site";
import Link from "next/link";
import Image from "next/image";
import {
  ArrowUpLeft,
  ArrowLeft,
  SlidersHorizontal,
  ShoppingBag,
  Palette,
} from "lucide-react";
import { HomeCatalog } from "@/features/catalog/home";
import { publicAPI, siteURL } from "@/lib/api/server";
import type { Page, Product, Category } from "@/lib/api/types";
import type { Metadata } from "next";
export const dynamic = "force-dynamic";
export function generateMetadata(): Metadata {
  const base = siteURL();
  return { alternates: base ? { canonical: base.href } : undefined };
}
export default async function Home() {
  const [products, categories] = await Promise.all([
    publicAPI<Page<Product>>("products/?ordering=-created&limit=8"),
    publicAPI<Page<Category>>("categories/?roots_only=true&limit=100"),
  ]);
  return (
    <div className="home">
      <section className="container hero" aria-labelledby="home-title">
        <div className="hero-copy">
          <p className="eyebrow">
            <span className="eyebrow-line" />
            {site.hero.eyebrow}
          </p>
          <h1 id="home-title">
            {site.hero.title}
            <br />
            <span>{site.hero.accent}</span>
          </h1>
          <p className="hero-description">{site.hero.description}</p>
          <div className="hero-actions">
            <Link className="button" href="/products">
              {site.hero.cta}
              <ArrowUpLeft size={19} />
            </Link>
            <Link className="text-link" href="/products?ordering=-created">
              تازه‌ترین‌ها
              <ArrowLeft size={18} />
            </Link>
          </div>
          <div className="hero-note">
            <span lang="en" dir="ltr">
              LESS NOISE. MORE YOU.
            </span>
            <span>جزئیات، پیش از انتخاب.</span>
          </div>
        </div>
        <figure className="hero-visual">
          <Image
            src="/editorial/home.webp"
            width={1264}
            height={848}
            alt="ترکیب بصری پارچه و پوشاک در فضای روشن؛ تصویر editorial، نه محصول کاتالوگ"
            preload
            fetchPriority="high"
            unoptimized
            sizes="(max-width: 767px) 100vw, 55vw"
          />
          <figcaption>
            <span lang="en" dir="ltr">
              {site.hero.artLabel}
            </span>
            <span>تصویر الهام‌بخش، نه کالای کاتالوگ</span>
          </figcaption>
        </figure>
      </section>
      <div className="container experience-strip" aria-label="راهنمای انتخاب">
        <div>
          <SlidersHorizontal size={20} />
          <span>جست‌وجو، مطابق انتخاب شما</span>
        </div>
        <div>
          <Palette size={20} />
          <span>رنگ و سایز از اطلاعات محصول</span>
        </div>
        <div>
          <ShoppingBag size={20} />
          <span>مرور انتخاب‌ها، پیش از سفارش</span>
        </div>
      </div>
      <div className="container">
        <HomeCatalog
          initialProducts={products}
          initialCategories={categories}
        />
      </div>
      <section className="container editorial-note">
        <p className="eyebrow" lang="en" dir="ltr">
          YOUR STYLE, YOUR WAY
        </p>
        <h2>
          انتخاب خوب،
          <br />
          از دیدن جزئیات شروع می‌شود.
        </h2>
        <Link href="/products" className="text-link">
          کشف لباس‌ها
          <ArrowUpLeft size={18} />
        </Link>
      </section>
    </div>
  );
}
