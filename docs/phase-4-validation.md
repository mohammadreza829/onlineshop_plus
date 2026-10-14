# گزارش اعتبارسنجی فاز ۴

فاز ۳ با PR #4 به main ادغام شد (`6d5aadbeaabc9a127d302e7a13a991b1efc60b04`). فاز ۴ در `phase-4/shop-features` با پنج کامیت معنادار جدا آماده شده؛ این گزارش، انتشار production یا تایید hosted CI نیست.

## پوشش پیاده‌سازی

1. variant و موجودی/قیمت مستقل، رزرو اتمیک و snapshot سفارش.
2. کوپن، سهمیه رزرو/مصرف/آزاد، rollback و callback دیرهنگام.
3. نظر خریدار با moderation و امتیاز عمومی، علاقه‌مندی خصوصی.
4. رویداد سفارش و اعلان in-app اتمیک، کد رهگیری دستی، staff API و تجمیع فروش.
5. کنترل مرز مبلغ/تاریخ و سبد خراب، اتصال حداقلی HTML، مستندات و اعتبارسنجی نهایی.

## نتایج

- **۱۶۲ تست روی PostgreSQL + Redis واقعی، بدون skip**؛ ۲۸ تست جدید نسبت به فاز ۳.
- **همان ۱۶۲ تست داخل Docker با PostgreSQL + Redis موفق**، بدون skip.
- **SQLite/LocMem: ۱۵۵ موفق و ۷ skip** (۵ PostgreSQL و ۲ Redis؛ ۱۶۲ تست کشف‌شده).
- چهار سناریوی رقابت (آخرین موجودی پایه، آخرین variant، آخرین سهمیه کوپن، دو checkout یک مشتری) در پنج اجرای متوالی موفق؛ تست واحد و محدود هستند، **تست بار محسوب نمی‌شوند**.
- migrationهای جدید روی PostgreSQL و دیتابیس QA Compose اعمال شدند. image جدید روی volume آزمایشی قبلی فاز ۳ اجرا شد؛ migration check هیچ تغییر ثبت‌نشده‌ای گزارش نکرد.
- Docker image با `docker build --network host` ساخته شد؛ runtime Compose با `--no-build --wait` اجرا شد. readiness HTTP: database/cache/worker همگی up. محدودیت شبکه sandbox فاز ۳ همچنان برقرار است.
- lint و تمام hookهای pre-commit، pip check، OpenAPI با `--validate --fail-on-warn` و `check --deploy --fail-level WARNING` با secret موقت و تنظیمات امن مخصوص بررسی موفق.
- stack QA پس از بررسی متوقف شد؛ volumeها حذف نشدند.

سناریوهای جدید: تفکیک خطوط variant، عدم فروش موجودی پایه محصول متنوع، جلوگیری از variant متعلق به محصول دیگر/غیرفعال، حفظ موجودی پایه در پرداخت دیرهنگام، API افزودن/حذف variant و stock کاتالوگ؛ مرز Decimal/rollback، سبد session نامعتبر، خرید HTML؛ کوپن درصدی/ثابت، rounding، سقف مبلغ، حداقل خرید/زمان/فعال‌بودن، سهمیه کاربر/کل، cancel/expire ایدمپوتنت، rollback جایگزینی سفارش، حفظ مبلغ پرداخت و ثبت over-capacity؛ سیاست paid buyer، reset moderation در ویرایش، عدم نمایش اطلاعات شخصی، مالکیت نظر/علاقه‌مندی؛ ترتیب رویداد، عدم اعلان تکراری، rollback خرابی ثبت اعلان، read ایدمپوتنت، ایزوله‌سازی کاربران، مجوز staff و state machine، تفکیک ارزش سفارش از تراکنش واقعی/پرداخت تکراری و تاریخ پرداخت از تاریخ ایجاد.

## بازتولید

```bash
pip install -r requirements-dev.txt
# .env را برای دیتابیس و Redis آزمایشی، نه production، تنظیم کنید.
DJANGO_DEBUG=True DJANGO_DB_ENGINE=postgresql CACHE_URL=redis://127.0.0.1:6379/1 python manage.py test --noinput
DJANGO_DEBUG=True DJANGO_DB_ENGINE=sqlite CACHE_URL='' python manage.py test --noinput
python manage.py migrate --noinput
python manage.py makemigrations --check --dry-run
python manage.py spectacular --validate --fail-on-warn --file /tmp/schema.yaml
pre-commit run --all-files
pip check
python manage.py test shop.test_variants.ConcurrentVariantTests orders.test_coupons.ConcurrentCouponTests api.tests.ConcurrentCustomerCheckoutTests orders.tests.ConcurrentCheckoutTests --noinput
```

داخل stack QA:

```bash
docker compose exec -e DJANGO_DEBUG=True -e HEALTHCHECK_REQUIRE_WORKER=False -e SMS_ASYNC=False -e CACHE_URL=redis://redis:6379/3 web python manage.py test --noinput
```

این فرمان دیتابیس test ایجاد می‌کند؛ فقط در محیط آزمایشی با permission لازم اجرا شود. شماره‌ها، قیمت‌ها و کدهای تست داده مصنوعی هستند؛ کوپن/مشتری واقعی seed نشده و هیچ SMS یا تراکنش مالی واقعی در تست‌های فاز ۴ ارسال نشده است.

## محدودیت‌ها و باقی‌مانده

- نتایج hosted GitHub Actions با مجوز فعلی تایید نشده‌اند؛ تست محلی/کانتینری جای این تایید نیست.
- اعلان وضعیت، فقط رکورد in-app است؛ SMS وضعیت، email و push realtime متصل نشده‌اند. کد حمل ثبت دستی است، نه اتصال به شرکت ارسال.
- داشبورد فعلاً API برای staff است؛ نه UI نهایی، نه سود/درآمد خالص و نه دفتر refund. لغو paid، بازپرداخت واقعی انجام نمی‌دهد.
- تاریخچه پیش از migration جعل نشده؛ برای سفارش قدیمی تنها تغییرات بعدی event دارند. service مرجع است؛ تغییر مستقیم status در SQL رویداد ندارد.
- کاتالوگ قیمت پایه را فیلتر/مرتب می‌کند، نه حداقل قیمت variant؛ جزئیات قیمت هر انتخاب را برمی‌گرداند. سبد هنوز cookie/session-bound است.
- UI صفحات جدید، طراحی RTL یکپارچه و تست مرورگر سرتاسری در فاز ۶ است. فقط مسیر خرید HTML موجود برای variant/کوپن به شکل حداقلی سازگار شد.
- بررسی امنیت مستقل، تست بار، benchmark تجمیع‌ها روی دیتای بزرگ، backup/restore، TLS/استقرار، چرخش کلیدهای قبلاً افشاشده و سرویس‌دهنده‌های واقعی لازم‌اند. هیچ ادعای «بدون باگ» یا آمادگی قطعی production از این تست‌ها نتیجه نمی‌شود.

قرارداد دقیق و سیاست‌های پیش‌فرض: [shop-features.md](shop-features.md).
