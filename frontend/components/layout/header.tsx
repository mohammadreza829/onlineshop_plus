"use client";
import { CartVariant } from "@/features/cart/line-product";
import Link from "next/link";
import {
  Heart,
  Menu,
  Search,
  ShoppingBag,
  UserRound,
  ArrowUpLeft,
  Plus,
} from "lucide-react";
import { usePathname } from "next/navigation";
import { site } from "@/config/site";
import { Sheet } from "@/components/ui/sheet";
import { useApi } from "@/lib/api/hooks";
import type { Cart, Category, Page } from "@/lib/api/types";
import { toman } from "@/lib/format";
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
          <div className="spread" key={`${i.product_id}:${i.variant_id}`}>
            <span>
              {i.name} × {i.quantity}
              <br />
              <CartVariant item={i} />
            </span>
            <span className="small">{toman(i.total_price)}</span>
          </div>
        ))
      ) : (
        <p>سبد خرید شما خالی است.</p>
      )}
      <Link className="button" href="/cart" onClick={close}>
        مشاهدهٔ سبد خرید
        <ArrowUpLeft size={18} />
      </Link>
    </div>
  );
}
export function Header() {
  const pathname = usePathname();
  const categories = useApi<Page<Category>>(
    "categories/?roots_only=true&limit=100",
  );
  return (
    <>
      <div className="announcement">
        <span>
          <i className="dot" />
          سبک شخصی، از دیدن جزئیات شروع می‌شود.
        </span>
        <bdi dir="ltr">NEW PERSPECTIVE / ONLINE SHOP PLUS</bdi>
      </div>
      <header className="site-header">
        <div className="container header-inner">
          <div className="mobile-only">
            <Sheet
              title="فروشگاه"
              trigger={
                <button className="icon-button" aria-label="باز کردن منو">
                  <Menu size={22} />
                </button>
              }
            >
              {(close) => (
                <nav className="stack">
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
              )}
            </Sheet>
          </div>
          <Link
            href="/"
            className="brand-lockup"
            aria-label="صفحهٔ اصلی آنلاین شاپ پلاس"
          >
            <span className="brand-symbol" aria-hidden="true">
              <Plus size={24} strokeWidth={1.2} />
            </span>
            <span className="wordmark">
              {site.name}
              <small lang="en" dir="ltr">
                {site.latinName}
              </small>
            </span>
          </Link>
          <nav className="desktop-nav" aria-label="ناوبری اصلی">
            <Link
              href="/products"
              aria-current={
                pathname.startsWith("/products") ? "page" : undefined
              }
            >
              همهٔ لباس‌ها{" "}
              <span className="nav-index" aria-hidden="true">
                01
              </span>
            </Link>
            {categories.data?.results.slice(0, 2).map((c) => (
              <Link
                key={c.id}
                href={"/products?category=" + encodeURIComponent(c.slug)}
              >
                {c.name}
              </Link>
            ))}
          </nav>
          <div className="header-actions">
            <Link
              href="/products"
              className="icon-button search-trigger"
              aria-label="جست‌وجوی لباس"
            >
              <Search size={20} />
            </Link>
            <Link
              href="/account/favorites"
              className="icon-button optional"
              aria-label="علاقه‌مندی‌ها"
            >
              <Heart size={20} />
            </Link>
            <Link
              href="/account"
              className="icon-button"
              aria-label="حساب کاربری"
            >
              <UserRound size={20} />
            </Link>
            <Sheet
              title="سبد خرید شما"
              trigger={
                <button className="icon-button" aria-label="باز کردن سبد خرید">
                  <ShoppingBag size={21} />
                </button>
              }
            >
              {(close) => <MiniCart close={close} />}
            </Sheet>
          </div>
        </div>
      </header>
    </>
  );
}
