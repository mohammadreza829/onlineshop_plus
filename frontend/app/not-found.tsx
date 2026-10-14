import Link from "next/link";
export default function NotFound() {
  return (
    <div className="container page">
      <div className="empty">
        <p className="eyebrow">۴۰۴ / پیدا نشد</p>
        <h1>این صفحه در فروشگاه نیست.</h1>
        <p>ممکن است نشانی تغییر کرده باشد یا دیگر در دسترس نباشد.</p>
        <Link className="button secondary" href="/products">
          بازگشت به فروشگاه
        </Link>
      </div>
    </div>
  );
}
