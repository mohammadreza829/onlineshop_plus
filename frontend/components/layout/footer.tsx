import Link from "next/link";
import { ArrowUpLeft } from "lucide-react";
import { site } from "@/config/site";
export function Footer() {
  return (
    <footer className="site-footer">
      <div className="container">
        <div className="footer-inner">
          <div>
            <p className="wordmark">
              <span className="brand-symbol" aria-hidden="true">
                +
              </span>
              {site.name}
            </p>
            <p className="subtle" style={{ marginTop: 16 }}>
              {site.description}؛ برای انتخابی به سلیقهٔ خودتان.
            </p>
          </div>
          <nav className="footer-links" aria-label="ناوبری پایین صفحه">
            <Link href="/products">
              فروشگاه <ArrowUpLeft size={16} aria-hidden="true" />
            </Link>
            <Link href="/cart">
              سبد خرید <ArrowUpLeft size={16} aria-hidden="true" />
            </Link>
            <Link href="/account/orders">
              سفارش‌های من <ArrowUpLeft size={16} aria-hidden="true" />
            </Link>
          </nav>
        </div>
        <div className="footer-bottom">
          <span lang="en" dir="ltr">
            {site.latinName}
          </span>
          <span>پوشش، از زاویه‌ای تازه.</span>
        </div>
      </div>
    </footer>
  );
}
