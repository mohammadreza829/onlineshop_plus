import type { Metadata } from "next";
import { Providers } from "@/components/providers";
import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";
import { site } from "@/config/site";
import { siteURL } from "@/lib/api/server";
import { Experience } from "@/components/motion/experience";
import "./globals.css";
export const metadata: Metadata = {
  metadataBase: siteURL(),
  title: { default: site.name, template: `%s | ${site.name}` },
  description: site.description,
  icons: { icon: "/icon.svg" },
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fa" dir="rtl">
      <head>
        {[400, 500, 700].map((weight) => (
          <link
            key={weight}
            rel="preload"
            href={`/fonts/vazirmatn-arabic-${weight}-normal.woff2`}
            as="font"
            type="font/woff2"
            crossOrigin="anonymous"
          />
        ))}
      </head>
      <body>
        <a href="#main" className="skip">
          رفتن به محتوای اصلی
        </a>
        <noscript>
          <section className="noscript-notice" aria-labelledby="noscript-title">
            <h2 id="noscript-title">جاوااسکریپت مرورگر خاموش است.</h2>
            <p>
              برای نمایش کامل فروشگاه، فیلترها، ورود و سبد خرید، جاوااسکریپت را
              فعال کنید. انیمیشن‌ها اختیاری هستند، اما بخش‌های تعاملی سایت به
              جاوااسکریپت نیاز دارند.
            </p>
            <a className="text-link" href="/products">
              رفتن به نشانی کاتالوگ
            </a>
          </section>
        </noscript>
        <Providers>
          <Header />
          <main id="main">
            <Experience>{children}</Experience>
          </main>
          <Footer />
        </Providers>
      </body>
    </html>
  );
}
