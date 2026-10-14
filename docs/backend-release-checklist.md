# پایان قابلیت‌های بک‌اند ≠ تایید انتشار واقعی

فازهای ۰ تا ۵ قابلیت‌های بک‌اند نقشه راه را پوشش می‌دهند. تست‌های محلی، Docker و داده مصنوعی، جای اعتبارسنجی سرویس‌دهنده‌ها، امنیت و ظرفیت محیط واقعی را نمی‌گیرند. فرانت باید پس از گفت‌وگو درباره نوع/تکنولوژی با صاحب پروژه آغاز شود؛ انتخابی در این فاز قطعی نشده است.

## گیت‌های باقی‌مانده انتشار

- [ ] تایید نتیجه hosted CI پیش از انتشار؛ بازبینی و ادغام کد جداگانه انجام می‌شود، اما read دسترسی check-runs اتصال فعلی محدود است و موفقیت محلی به معنی موفقیت hosted CI نیست.
- [ ] چرخش و ابطال secretهای ثبت‌شده در تاریخچه قبلی (Django/SMS/DB و هر کلید مرتبط)، تایید نگهداری امن و اصل حداقل دسترسی.
- [ ] دامنه، proxy/TLS، trusted origins/hosts، HSTS متناسب، cookie/CSRF، storage امن media و محدودیت upload.
- [ ] Redis امن/خصوصی، بودجه حافظه و noeviction متناسب با OTP/قفل/صف؛ capacity و outage drill؛ database least privilege.
- [ ] دقیقاً یک beat و worker فعال، health/readiness/heartbeat، سیاست retry/timeout و رسیدگی به unknown payments/needs_review/refund flags.
- [ ] SMS واقعی با template/کلید معتبر و گیرنده مجاز؛ OTP console آزمون، تایید سرویس واقعی نیست. SMS وضعیت/ایمیل/push به طور خودکار پیاده/متصل نشده‌اند.
- [ ] درگاه production با merchant معتبر، callback عمومی TLS و سناریوهای موفق/ناموفق/تکراری/timeout؛ هیچ پول واقعی در تست‌های فاز ۴/۵ جابه‌جا نشده است.
- [ ] سیاست لغو/مرجوعی/بازپرداخت و مسئول رسیدگی؛ لغو سفارش paid، refund بانکی اجرا نمی‌کند. ledger و refund خودکار در قابلیت‌های فعلی ادعا نشده است.
- [ ] backup زمان‌بندی‌شده رمزگذاری‌شده خارج از همان host، retention/RPO/RTO، کپی media و تمرین restore روی محیط مقصد.
- [ ] لاگ/metrics collector و alert با مقصد مجاز و SLO تعیین‌شده؛ log instrumentation به تنهایی on-call/alert delivery نیست.
- [ ] تست بار طولانی‌تر روی اندازه/منابع/داده مقصد: cold cache، spike/soak، نرخ ورودی ثابت، checkout/پرداخت با adapter آزمایشی، backlog worker و outage؛ بار عمومی محلی تنها یک smoke baseline است.
- [ ] بررسی امنیت مستقل: مجوز/IDOR، rate limit، CSRF/session/JWT، XSS/upload، تزریق/secret scan/وابستگی‌ها و سیاست داده/حریم خصوصی.
- [ ] صفحات نهایی فرانت، حالت خطا/ارسال دوباره، دسترس‌پذیری و تست مرورگر سرتاسری بعد از تصمیم مشترک درباره فرانت.

## تمرین backup/restore این فاز

pg_dump/pg_restore روی PostgreSQL مستقل و کاملاً مصنوعی اجرا شد؛ شامل داده‌های کاتالوگ و سفارش پرداخت‌شده آزمایشی، کوپن مصرف‌شده، payment ساختگی، snapshot آیتم/آدرس و رویداد/اعلان. fingerprint و تعداد ردیف ۱۳ جدول منتخب قبل و بعد یکسان بودند. rollback/reapply migration جستجو نیز همین داده‌ها را حفظ و document را بازسازی کرد.

این تمرین شامل media واقعی، backup production، قطع واقعی host، بازیابی Redis/broker، RPO/RTO تضمین‌شده یا تطبیق settlement بانکی نیست. فایل آرشیو آزمون فقط در محیط کامپیوتر نگه داشته شد، وارد GitHub یا Docker image نشد.

نمونه روند عملیاتی (پس از تعیین محیط/مجوز؛ نه روی دیتابیس اصلی به طور آزمایشی):

```bash
# از فایل سرویس/محیط امن برای credentials استفاده کنید، نه درج پسورد در فرمان/گیت.
pg_dump --format=custom --file=/secure/location/shop.dump SOURCE_DB
createdb EMPTY_RESTORE_DB
pg_restore --no-owner --no-privileges --dbname=EMPTY_RESTORE_DB /secure/location/shop.dump
# با env مخصوص RESTORE، migration/check و تطبیق count+fingerprint/مالی/stock را انجام دهید.
```

نام‌ها placeholder هستند؛ از `dropdb`، پاک‌کردن volume یا restore روی دیتابیس زنده برای این بررسی استفاده نکنید. backup شامل داده شخصی/مالی است؛ محدودیت دسترسی، رمزگذاری و پاک‌سازی مطابق سیاست لازم است.
