import { site } from "@/config/site";
import Link from "next/link";
import Image from "next/image";
import {
  ArrowUpLeft,
  ArrowDown,
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
    <div className="home immersive-home">
      <section
        className="immersive-hero"
        data-hero
        aria-labelledby="home-title"
      >
        <div className="hero-picture" data-parallax>
          <Image
            src="/editorial/immersive.webp"
            alt="چیدمان تصویری پوشاک و پارچه در فضای معماری؛ تصویر تزئینی تولیدشده با هوش مصنوعی، نه محصول کاتالوگ"
            width={1376}
            height={768}
            preload
            fetchPriority="high"
            unoptimized
            sizes="100vw"
          />
        </div>
        <div className="hero-shade" />
        <div className="container hero-layout">
          <div className="hero-topline" data-enter>
            <span className="orb" aria-hidden="true" />
            <span>{site.hero.eyebrow}</span>
            <bdi dir="ltr">/ 01</bdi>
          </div>
          <h1 className="hero-title" id="home-title">
            <span className="hero-title-line" data-enter>
              {site.hero.title}
            </span>
            <span className="hero-title-line outline-word" data-enter>
              {site.hero.accent}
            </span>
          </h1>
          <p className="hero-desc" data-enter>
            {site.hero.description}
          </p>
          <div className="hero-actions" data-enter>
            <Link className="button lime" href="/products" data-magnetic>
              {site.hero.cta}
              <ArrowUpLeft size={21} />
            </Link>
            <Link className="text-link" href="/products?ordering=-created">
              تازه‌رسیده‌ها
              <ArrowUpLeft size={18} />
            </Link>
          </div>
          <div className="hero-bottom">
            <p className="hero-art-note">
              <bdi dir="ltr">{site.hero.artLabel}</bdi>تصویر مفهومی با هوش
              مصنوعی؛ نه کالای کاتالوگ
            </p>
            <a className="scroll-hint" href="#discover">
              کمی پایین‌تر، انتخاب‌های بیشتر
              <ArrowDown size={18} />
            </a>
            <p className="hero-count" dir="ltr">
              <span>01</span> — EXPLORE
            </p>
          </div>
        </div>
      </section>
      <div className="kinetic-strip" aria-hidden="true">
        <div className="kinetic-track">
          {[0, 1].map((i) => (
            <span key={i}>
              YOUR STYLE. YOUR STORY. <i>✳</i>
              <em>شبیه هیچ‌کس، جز خودت.</em>
              <i>✳</i> LESS NOISE. MORE YOU. <i>✳</i>
            </span>
          ))}
        </div>
      </div>
      <div className="container" id="discover">
        <section className="browse-intro" data-reveal>
          <div>
            <p className="eyebrow">ساده‌تر ببین. بهتر انتخاب کن.</p>
            <h2>
              خوب پوشیدن،
              <br />
              از خودت شروع می‌شود.
            </h2>
          </div>
          <p>
            برای سلیقهٔ تو قانون ثابتی نیست. مدل‌ها را ببین، جزئیات را بخوان و
            چیزی را انتخاب کن که دوستش داری.
          </p>
        </section>
        <HomeCatalog
          initialProducts={products}
          initialCategories={categories}
        />
        <div
          className="experience-strip"
          aria-label="راهنمای انتخاب"
          data-reveal
        >
          <div>
            <SlidersHorizontal size={20} />
            <span>جست‌وجوی ساده‌تر</span>
          </div>
          <div>
            <Palette size={20} />
            <span>رنگ و سایز دلخواه</span>
          </div>
          <div>
            <ShoppingBag size={20} />
            <span>همهٔ انتخاب‌ها، یک‌جا</span>
          </div>
        </div>
        <section className="editorial-note" data-reveal>
          <div>
            <p className="eyebrow">تفاوت، در جزئیات است.</p>
            <h2>
              جزئیات را ببین.
              <br />
              تفاوت را حس کن.
            </h2>
            <Link href="/products" className="text-link">
              لباس بعدی‌ات را پیدا کن
              <ArrowUpLeft size={18} />
            </Link>
          </div>
          <div className="editorial-type" aria-hidden="true" dir="ltr">
            <span>NOT JUST</span>
            <span>ANOTHER</span>
            <span>LOOK.</span>
          </div>
        </section>
      </div>
    </div>
  );
}
