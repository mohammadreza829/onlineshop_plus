import Link from "next/link";
import { ArrowUpLeft } from "lucide-react";
import { site } from "@/config/site";
export function Footer() {
  return (
    <footer className="site-footer">
      <div className="container">
        <div className="footer-topline" dir="ltr">
          <span>WEAR YOUR WAY.</span>
          <span>ONLINE SHOP PLUS ↗</span>
        </div>
        <div className="footer-inner">
          <div>
            <Link href="/" className="wordmark">
              {site.name}
            </Link>
            <p>{site.description}</p>
          </div>
          <nav className="footer-links" aria-label="ناوبری پایین صفحه">
            <Link href="/products">
              کشف فروشگاه <ArrowUpLeft size={16} />
            </Link>
            <Link href="/cart">سبد خرید</Link>
            <Link href="/account/orders">سفارش‌های من</Link>
            <Link href="/account/favorites">علاقه‌مندی‌ها</Link>
          </nav>
        </div>
        <div className="footer-bottom">
          <span>برای انتخاب‌هایی که روایت خودت هستند.</span>
          <bdi dir="ltr">DESIGNED AROUND YOU / RTL</bdi>
        </div>
      </div>
    </footer>
  );
}
