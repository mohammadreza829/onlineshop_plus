"use client";
import { CartVariant } from "@/features/cart/line-product";
import Link from "next/link";
import { useId } from "react";
import { usePathname } from "next/navigation";
import {
  Heart,
  Menu,
  Search,
  ShoppingBag,
  UserRound,
  ArrowLeft,
  Plus,
} from "lucide-react";
import { site } from "@/config/site";
import { Sheet } from "@/components/ui/sheet";
import { useApi } from "@/lib/api/hooks";
import type { Cart, Category, Page } from "@/lib/api/types";
import { toman, number } from "@/lib/format";
function MiniCart({ close }: { close: () => void }) {
  const q = useApi<Cart>("cart/");
  return (
    <div className="stack">
      {q.isPending ? (
        <p role="status">دریافت سبد…</p>
      ) : q.isError ? (
        <p role="alert">دریافت سبد ممکن نشد؛ صفحهٔ سبد را باز کنید.</p>
      ) : q.data.items.length ? (
        q.data.items.map((i) => (
          <div
            className="mini-cart-line"
            key={`${i.product_id}:${i.variant_id}`}
          >
            <span>
              {i.name} × {number(i.quantity)}
              <br />
              <CartVariant item={i} />
            </span>
            <span className="small">{toman(i.total_price)}</span>
          </div>
        ))
      ) : (
        <div className="mini-cart-empty">
          <ShoppingBag size={40} strokeWidth={1.3} aria-hidden="true" />
          <h3>هنوز انتخابی در سبد نیست</h3>
          <p className="subtle">لباس موردعلاقه‌تان را در فروشگاه پیدا کنید.</p>
        </div>
      )}
      <Link className="button" href="/cart" onClick={close}>
        مشاهدهٔ سبد خرید
        <ArrowLeft size={18} aria-hidden="true" />
      </Link>
    </div>
  );
}
function StoreSearch({
  compact = false,
  close,
}: {
  compact?: boolean;
  close?: () => void;
}) {
  const id = useId();
  return (
    <form
      className={compact ? "store-search compact" : "store-search desktop-only"}
      action="/products"
      onSubmit={close}
      role="search"
      aria-label="جست‌وجوی فروشگاه"
    >
      <label className="sr-only" htmlFor={id}>
        جست‌وجوی فروشگاه
      </label>
      <Search size={20} aria-hidden="true" />
      <input
        id={id}
        name="search"
        placeholder="دنبال چه لباسی می‌گردید؟"
        maxLength={200}
        type="search"
      />
      <button type="submit" aria-label="جست‌وجو در فروشگاه">
        <ArrowLeft size={19} aria-hidden="true" />
      </button>
    </form>
  );
}
export function Header() {
  const categories = useApi<Page<Category>>(
    "categories/?roots_only=true&limit=100",
  );
  const cart = useApi<Cart>("cart/");
  const path = usePathname();
  return (
    <header className="site-header">
      <div className="container header-inner">
        <div className="mobile-only">
          <Sheet
            title="فروشگاه"
            trigger={
              <button className="icon-button" aria-label="باز کردن منو">
                <Menu size={22} aria-hidden="true" />
              </button>
            }
          >
            {(close) => (
              <>
                <StoreSearch compact close={close} />
                <nav className="stack mobile-menu" aria-label="ناوبری موبایل">
                  <Link href="/" onClick={close}>
                    خانه
                  </Link>
                  <Link href="/products" onClick={close}>
                    همهٔ لباس‌ها
                  </Link>
                  {categories.data?.results.map((c) => (
                    <Link
                      key={c.id}
                      href={"/products?category=" + encodeURIComponent(c.slug)}
                      onClick={close}
                    >
                      {c.name}
                    </Link>
                  ))}
                  <Link href="/account" onClick={close}>
                    حساب کاربری
                  </Link>
                  <Link href="/account/favorites" onClick={close}>
                    علاقه‌مندی‌ها
                  </Link>
                </nav>
              </>
            )}
          </Sheet>
        </div>
        <Link href="/" className="brand" aria-label={site.name + "، صفحه اصلی"}>
          <span className="brand-symbol" aria-hidden="true">
            <Plus size={24} strokeWidth={2.5} />
          </span>
          <span className="wordmark">
            {site.name}
            <small lang="en" dir="ltr">
              {site.latinName}
            </small>
          </span>
        </Link>
        <StoreSearch />
        <div className="header-actions">
          <Link
            href="/account/favorites"
            className="icon-button optional"
            aria-label="علاقه‌مندی‌ها"
          >
            <Heart size={21} aria-hidden="true" />
          </Link>
          <Link
            href="/account"
            className="header-account"
            aria-label="حساب کاربری"
          >
            <UserRound size={21} aria-hidden="true" />
            <span className="desktop-only">حساب کاربری</span>
          </Link>
          <Sheet
            title="سبد خرید شما"
            trigger={
              <button
                className="icon-button cart-trigger"
                aria-label="باز کردن سبد خرید"
              >
                <ShoppingBag size={21} aria-hidden="true" />
                {cart.data && cart.data.item_count > 0 && (
                  <span className="cart-count" aria-hidden="true">
                    {number(cart.data.item_count)}
                  </span>
                )}
              </button>
            }
          >
            {(close) => <MiniCart close={close} />}
          </Sheet>
          <span className="sr-only" role="status">
            {cart.data ? `سبد خرید، ${number(cart.data.item_count)} کالا` : ""}
          </span>
        </div>
      </div>
      <div className="header-nav-row">
        <div className="container nav-inner">
          <nav className="desktop-nav" aria-label="ناوبری اصلی">
            <Link href="/" aria-current={path === "/" ? "page" : undefined}>
              خانه
            </Link>
            <Link
              href="/products"
              aria-current={path.startsWith("/products") ? "page" : undefined}
            >
              همهٔ لباس‌ها
            </Link>
            {categories.data?.results.slice(0, 3).map((c) => (
              <Link
                key={c.id}
                href={"/products?category=" + encodeURIComponent(c.slug)}
              >
                {c.name}
              </Link>
            ))}
          </nav>
          <StoreSearch compact />
          <Link
            className="new-arrivals desktop-only"
            href="/products?ordering=-created"
          >
            تازه‌ترین انتخاب‌ها
            <ArrowLeft size={16} aria-hidden="true" />
          </Link>
        </div>
      </div>
    </header>
  );
}
