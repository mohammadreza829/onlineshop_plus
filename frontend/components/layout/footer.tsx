import Link from "next/link";
import { ArrowLeft, Plus } from "lucide-react";
import { site } from "@/config/site";
export function Footer() {
  return (
    <footer className="site-footer">
      <div className="container">
        <div className="footer-inner">
          <div className="footer-brand">
            <span className="brand-symbol" aria-hidden="true">
              <Plus size={24} />
            </span>
            <div>
              <p className="wordmark">{site.name}</p>
              <p className="subtle">لباسی که به روز شما می‌آید.</p>
            </div>
          </div>
          <nav className="footer-column" aria-label="ناوبری پایین صفحه">
            <h2>کشف فروشگاه</h2>
            <Link href="/products">همهٔ لباس‌ها</Link>
            <Link href="/products?ordering=-created">تازه‌ترین‌ها</Link>
            <Link href="/account/favorites">علاقه‌مندی‌ها</Link>
          </nav>
          <nav className="footer-column" aria-label="خرید و حساب">
            <h2>همراه خرید شما</h2>
            <Link href="/cart">سبد خرید</Link>
            <Link href="/account/orders">سفارش‌های من</Link>
            <Link href="/account/addresses">آدرس‌های من</Link>
          </nav>
          <div className="footer-note">
            <p>
              یک انتخاب تازه،
              <br />
              برای روزهای شما.
            </p>
            <Link className="text-link" href="/products">
              گشت‌وگذار در فروشگاه
              <ArrowLeft size={18} aria-hidden="true" />
            </Link>
          </div>
        </div>
        <div className="footer-bottom">
          <span>{site.description}</span>
          <span lang="en" dir="ltr">
            ONLINE SHOP PLUS
          </span>
        </div>
      </div>
    </footer>
  );
}
