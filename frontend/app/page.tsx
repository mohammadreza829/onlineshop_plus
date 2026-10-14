import { site } from "@/config/site";
import Link from "next/link";
import { ArrowUpLeft } from "lucide-react";
import { HomeCatalog } from "@/features/catalog/home";
import { HomeMotion } from "@/lib/motion/home-motion";
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
    <div className="container">
      <section className="hero" aria-labelledby="home-title">
        <div className="hero-frame">
          <div className="hero-copy">
            <p className="eyebrow">{site.hero.eyebrow}</p>
            <h1 id="home-title">
              {site.hero.title}
              <br />
              <em>{site.hero.accent}</em>
            </h1>
            <p className="subtle">{site.hero.description}</p>
            <Link className="button" href="/products">
              {site.hero.cta}
              <ArrowUpLeft size={20} />
            </Link>
          </div>
          <div className="hero-art" aria-hidden="true">
            <span className="art-number">لباس / انتخاب</span>
            <span className="type-mark">{site.hero.artWord}</span>
            <span className="art-label" lang="en" dir="ltr">
              {site.hero.artLabel}
            </span>
          </div>
        </div>
        <div className="hero-bottom">
          <span>کاتالوگ لباس · انتخاب رنگ و سایز</span>
          <span>جزئیات هر انتخاب، پیش از خرید</span>
        </div>
        <HomeMotion />
      </section>
      <HomeCatalog initialProducts={products} initialCategories={categories} />
    </div>
  );
}
