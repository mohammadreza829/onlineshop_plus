# وضعیت اصلاحات دموی لوکال

## محدوده

مبنای تغییرات: main با SHA `21bc2e0e71b23973f5780f89fa3507006905c898`.
تغییرات برای دموی لوکال تک‌فرآیندی‌اند؛ main بدون بررسی CI merge نشده است.
شماره‌ها به گزارش ممیزی همین گفت‌وگو اشاره دارند.

| مورد | تغییر انجام‌شده |
| --- | --- |
| A01 | API عملیاتی با مجوز تغییر سفارش؛ فروش با مجوز view_sales؛ لغو paid در سرویس با مجوز مالی |
| A02 | اکشن‌های Admin مجوز تغییر/تصمیم تخصصی دارند؛ actor در سرویس دوباره بررسی می‌شود |
| A03 | غیرسوپریوزر حق واگذاری قدرت یا تغییر حساب ممتاز را ندارد؛ افزودن کاربر مدیریتی فقط superuser |
| A04 | مالک و snapshot سفارش در Admin فقط خواندنی؛ callback هر دو مالک Order و Payment را بررسی می‌کند |
| F01 | موفقیت Payment پیش از fulfillment ثبت می‌شود؛ خطای اعلان نیاز reconciliation می‌گذارد |
| F02 | authority فعال reuse می‌شود؛ unknown مانع پرداخت تازه است؛ checkout_key برای replay ثبت سفارش |
| F03 | RefundRequest و ثبت سند بانکی با مجوز مالی؛ این برنامه بازپرداخت بانکی خودکار انجام نمی‌دهد |
| F04 | روابط مالی PROTECT و حذف در Admin مسدود؛ حساب را غیرفعال کنید |
| S01 | آیتم حذف‌شده fulfillment را به needs_review می‌برد، نه تامین‌شده |
| S02 | رزرو پیشین قبل از اعتبارسنجی replacement آزاد می‌شود؛ clean تعداد را بی‌خبر کم نمی‌کند |
| S03 | review_reason و تصمیم صریح کوپن با actor/reason و اکشن Admin |
| U01 | callback دیگر سبد کامل را پاک نمی‌کند؛ حذف شرطی خودکار اقلام خرید هنوز اضافه نشده |
| U02 | خلاصه مالی owner-only و پیام refund/unknown/reconciliation؛ پیام legacy علت ساختگی ندارد |
| O01 | برای دمو loopback و اجرای یک‌فرآیندی؛ طراحی client-IP معتبر production هنوز گیت آینده است |
| O02 | origin ثابت callback و redirect ثابت به نتیجه Next؛ localhost payment fake و بدون پول واقعی |
| O03 | media در DEBUG دموی محلی موجود است؛ media/CDN production هنوز گیت آینده است |
| Q01 | workflow فرانت: نصب، typecheck، lint، unit، build و Playwright با Django QA ایزوله |

## شواهد واقعی این نوبت

- ۱۶ regression test با Django 6.0.9 و دیتابیس واقعی SQLite ایزوله موفق شدند؛
  مدل‌ها و سرویس‌های اصلی استفاده شدند، gateway test double است و هیچ SMS/بانکی تماس گرفته نشد.
- یک تست round-trip از DemoGateway، صفحه پرداخت محلی، callback و redirect به Next استفاده کرد.
  این تست Django HTTP client است، نه مرورگر واقعی Next.
- دو migration روی ساختار قبلی مدل‌ها در SQLite اعمال شدند؛ تطابق state مدل Order/Payment بررسی شد.
- Ruff lint و format و compile کد Python بررسی شدند.
- syntax فایل‌های تغییرکرده فرانت با esbuild بررسی می‌شود؛ این جای typecheck یا npm build کامل نیست.
- نتایج کل regression پروژه، CI PostgreSQL/Redis، build و E2E مرورگر روی GitHub باید جدا بررسی شوند.
  افزودن workflow به معنی موفقیت run نیست؛ وضعیت نهایی از Checks همان PR مشخص می‌شود.

## باقی‌مانده و مرز ادعا

- ادعای کشف یا رفع همه باگ‌های ناشناخته پروژه نداریم؛ این PR موارد مشخص ممیزی را هدف گرفته است.
- crash/recovery گسترده، هم‌زمانی PostgreSQL و همه داده‌های تاریخی این محیط کامل تست نشده‌اند.
- پرداخت‌های قدیمیِ بدون authority یا بازپرداخت دستیِ بدون سند باید توسط مسئول مالی تطبیق داده شوند؛
  migration هیچ سند بانکی یا نتیجه بازپرداخت تاریخی را حدس نمی‌زند.
- provider واقعی، SMS واقعی، client-IP پشت proxy، media production و multi-replica خارج از هدف دمو هستند.
- دموی آماده برای اجرای محلی با تایید production تفاوت دارد. secret و DB دمو هرگز commit نشوند.
