import { site } from "@/config/site";
import Image from "next/image";
import Link from "next/link";
import { ArrowLeft, Heart, Palette, SlidersHorizontal } from "lucide-react";
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
    <div className="container home-page">
      <section className="hero" aria-labelledby="home-title">
        <div className="hero-frame">
          <div className="hero-copy">
            <p className="eyebrow">{site.hero.eyebrow}</p>
            <h1 id="home-title">
              {site.hero.title}
              <br />
              <em>{site.hero.accent}</em>
            </h1>
            <p className="subtle hero-description">{site.hero.description}</p>
            <div className="row hero-actions">
              <Link className="button" href="/products">
                {site.hero.cta}
                <ArrowLeft size={20} aria-hidden="true" />
              </Link>
              <Link className="text-link" href="/products?ordering=-created">
                تازه‌ترین‌ها
              </Link>
            </div>
          </div>
          <figure className="hero-visual">
            <Image
              src="/images/wardrobe-editorial.webp"
              alt="ترکیب الهام‌بخش پارچه‌های جین، پنبه و بافت در رنگ‌های آبی، سفید و سبز"
              fill
              sizes="(max-width: 767px) 100vw, 55vw"
              priority
            />
            <figcaption>تصویر الهام‌بخش استایل؛ نمایش موجودی نیست.</figcaption>
          </figure>
        </div>
      </section>
      <div className="discovery-strip" aria-label="امکانات فروشگاه">
        <div>
          <Palette size={22} aria-hidden="true" />
          <span>
            انتخاب رنگ و سایز<small>جزئیات هر لباس، پیش از خرید</small>
          </span>
        </div>
        <div>
          <SlidersHorizontal size={22} aria-hidden="true" />
          <span>
            پیدا کردن انتخاب شما<small>جست‌وجو بر اساس دسته و قیمت</small>
          </span>
        </div>
        <div>
          <Heart size={22} aria-hidden="true" />
          <span>
            برای بعد نگه دارید<small>ذخیرهٔ انتخاب‌ها در حساب کاربری</small>
          </span>
        </div>
      </div>
      <HomeCatalog initialProducts={products} initialCategories={categories} />
      <section className="account-invitation">
        <div>
          <p className="eyebrow">انتخاب‌های شما، یک‌جا</p>
          <h2>از پسندیدن تا پوشیدن.</h2>
          <p className="subtle">
            علاقه‌مندی‌ها و سفارش‌هایتان را از حساب کاربری دنبال کنید.
          </p>
        </div>
        <Link className="button secondary" href="/account">
          رفتن به حساب کاربری
          <ArrowLeft size={20} aria-hidden="true" />
        </Link>
      </section>
    </div>
  );
}
