import Link from "next/link";
import {
  ArrowUpLeft,
  MoveDown,
  Layers3,
  ArrowDownLeft,
  ScanLine,
} from "lucide-react";
import { HomeCatalog } from "@/features/catalog/home";
import { Showroom } from "@/features/showroom/showroom";
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
    <div className="container home-page">
      <section className="immersive-hero" aria-labelledby="home-title">
        <div className="hero-issue" aria-hidden="true">
          <span lang="en" dir="ltr">
            PLUS / EXPERIMENTAL SHOWROOM
          </span>
          <span>پوشش از زاویه‌ای دیگر</span>
        </div>
        <div className="immersive-grid">
          <div className="immersive-copy">
            <p className="eyebrow">
              <span className="status-dot" /> استایل، در بُعدی تازه
            </p>
            <h1 id="home-title">
              از قاب
              <br />
              معمولی،
              <br />
              <em>بیرون بزن.</em>
            </h1>
            <p className="immersive-description">
              لباس‌ها را کشف کن. جزئیات را ببین.
              <br />
              انتخاب بعدی، به سبک خودت.
            </p>
            <div className="hero-cta">
              <Link className="button" href="/products">
                ورود به فروشگاه <ArrowUpLeft size={20} aria-hidden="true" />
              </Link>
              <Link className="immersive-secondary" href="#latest">
                تازه‌ترین‌ها <ArrowDownLeft size={18} aria-hidden="true" />
              </Link>
            </div>
          </div>
          <Showroom />
        </div>
        <div className="immersive-bottom">
          <span>
            <ScanLine size={16} aria-hidden="true" /> فرم را بچرخان؛ جزئیات را
            کشف کن.
          </span>
          <Link href="#latest" aria-label="رفتن به تازه‌ترین لباس‌ها">
            <MoveDown size={18} aria-hidden="true" /> پایین‌تر را ببین
          </Link>
          <span lang="en" dir="ltr">
            FASHION, REFRAMED.
          </span>
        </div>
      </section>
      <div className="editorial-strip">
        <span lang="en" dir="ltr">
          NOT JUST ANOTHER LOOK.
        </span>
        <p>
          لباس برای پوشیدن.
          <br />
          <span className="subtle">جزئیات برای کشف‌کردن.</span>
        </p>
        <Layers3 size={32} strokeWidth={1} aria-hidden="true" />
      </div>
      <HomeCatalog initialProducts={products} initialCategories={categories} />
      <section className="browse-banner" aria-labelledby="browse-title">
        <div>
          <p className="eyebrow">انتخاب بعدی شما</p>
          <h2 id="browse-title">جایی برای سلیقهٔ شما.</h2>
          <p className="subtle">
            همهٔ لباس‌ها را یک‌جا ببینید؛ با رنگ و سایز دلخواهتان.
          </p>
        </div>
        <Link className="button" href="/products">
          رفتن به فروشگاه <ArrowUpLeft size={20} aria-hidden="true" />
        </Link>
      </section>
    </div>
  );
}
