import Link from "next/link";
import { site } from "@/config/site";
export function Footer() {
  return (
    <footer className="site-footer">
      <div className="container footer-inner">
        <div>
          <p className="wordmark">{site.name}</p>
          <p className="subtle small" style={{ marginTop: 8 }}>
            {site.description}
          </p>
        </div>
        <nav className="footer-links" aria-label="ناوبری پایین صفحه">
          <Link href="/products">فروشگاه</Link>
          <Link href="/cart">سبد خرید</Link>
          <Link href="/account/orders">سفارش‌های من</Link>
        </nav>
      </div>
    </footer>
  );
}
