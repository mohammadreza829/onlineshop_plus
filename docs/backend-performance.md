# فاز ۵: جستجو، پیشنهاد، بهینه‌سازی و مشاهده‌پذیری بک‌اند

این فاز هیچ نوع یا تکنولوژی فرانت را انتخاب نمی‌کند. پیش از شروع فرانت، درباره معماری، نوع کلاینت و تکنولوژی آن با صاحب پروژه گفت‌وگو و تصمیم‌گیری می‌شود. پیشنهادهای قبلی نقشه راه، انتخاب قطعی نیستند.

## جستجوی PostgreSQL

`GET /api/v1/products/?search=کیف&ordering=relevance`

- `search_document` با trigger دیتابیس از نام/SKU (وزن A) و توضیح (وزن B) ساخته می‌شود و GIN دارد. create، bulk_create، update و SQL مستقیم این سه ستون همگی document را تازه می‌کنند؛ موجودی/پرداخت به بازنویسی document نیازی ندارند.
- نرمال‌سازی ی/ک عربی، ارقام فارسی/عربی، اعراب عربی، نیم‌فاصله/کشیده و فاصله‌های تکراری؛ حروف لاتین lowercase می‌شوند. query و document یک قرارداد دارند.
- config=`simple` انتخاب شده است؛ stemming فارسی/انگلیسی، غلط‌یابی و prefix autocomplete ادعا نمی‌شود. PostgreSQL جستجوی واژه‌ای `websearch` با AND پیش‌فرض، OR، عبارت نقل‌قول‌شده و حذف با minus دارد. SQL با پارامترهای ORM ارسال می‌شود.
- ترتیب پیش‌فرض قبلی `-created` حفظ شده؛ `ordering=relevance` صریح برای رتبه‌بندی است. بدون query، relevance به جدیدترین تبدیل می‌شود. فیلتر فعال‌بودن، stock، دسته و قیمت همچنان اعمال می‌شود.
- SQLite فقط fallback نرمال‌شده AND+substring برای توسعه دارد؛ معادل websearch، رتبه‌بندی یا GIN نیست.
- migration داده موجود را backfill می‌کند؛ rollback/reapply روی داده مصنوعی بررسی شد. migration فعلی backfill و ساخت index را داخل تراکنش انجام می‌دهد؛ **zero-downtime برای دیتابیس بزرگ ادعا نشده**. در محیط واقعی زمان نگهداری یا rollout چندمرحله‌ای/ساخت concurrent لازم است.
- پس از bulk import، برنامه اجرای واقعی را بررسی کنید و نگهداری معمول `VACUUM (ANALYZE)`/autovacuum را فراهم کنید؛ از اجبار `enable_seqscan=off` به عنوان شاهد بهبود استفاده نکنید. ایندکس‌داشتن به معنی انتخاب همیشگی index نیست، مخصوصاً queryهای بسیار عمومی.

## پیشنهاد محصول

`GET /api/v1/products/{slug}/recommendations/?limit=8`، عمومی، سقف ۲۰.

استراتژی قابل توضیح، نه هوش مصنوعی یا شخصی‌سازی مخفی:

1. فقط کالاهای فعال و دارای موجودی واقعی، غیر از کالای مبدا.
2. همان دسته اول؛ سپس جمع quantity خریدهای پرداخت‌شده ۹۰ روز اخیر، در وضعیت paid/preparing/sent/delivered.
3. امتیاز تاییدشده، جدیدترین و PK برای ترتیب پایدار؛ اگر همان دسته کافی نباشد از کالاهای سایر دسته‌ها پر می‌شود. محصول بدون دسته، affinity دسته ندارد.

هیچ شناسه یا سابقه خرید مشتری از این API بیرون نمی‌رود؛ پاسخ همان فیلدهای عمومی کاتالوگ است.

### کش هدفمند

- Redis/LocMem فقط pool حداکثر ۶۰ **شناسه** پیشنهاد را نگه می‌دارد؛ TTL پیش‌فرض ۶۰ ثانیه، تنظیم `RECOMMENDATIONS_CACHE_SECONDS` در محدوده ۰–۳۰۰، صفر یعنی بدون کش.
- در هر پاسخ، فعال‌بودن، موجودی/قیمت/تخفیف/امتیاز از دیتابیس زنده hydrate می‌شوند. حذف/ناموجودشدن نامزدها، pool را در صورت کمبود دوباره می‌سازد. هیچ payload مالی، سفارش، آدرس، OTP یا پاسخ خصوصی در این کش نیست.
- save/delete کالا، variant، دسته و review بعد از commit، generation کش را تغییر می‌دهند؛ rollback invalidation یا انتشار داده ثبت‌نشده ندارد. در تراکنش باز اصلاً کش مشترک استفاده نمی‌شود.
- bulk update و تغییر وضعیت خرید، signal save/delete این مدل‌ها را ندارند؛ ترتیب پیشنهاد/عضویت pool ممکن است تا TTL قدیمی باشد. برای import بزرگ، `invalidate_recommendations()` بعد از commit صدا زده شود. قیمت/موجودی/فعال‌بودن حتی در این حالت زنده است.
- outage کش در **service پیشنهاد** به query دیتابیس برمی‌گردد؛ این تضمین سلامت کل سایت هنگام قطع Redis نیست. OTP، throttle و session وابستگی‌های جدا دارند و readiness وضعیت خرابی را گزارش می‌کند.
- افزایش ناگهانی cache miss ممکن است چند بار query یکسان بسازد؛ single-flight/distributed stampede lock پیاده نشده است. قبل از انتخاب ظرفیت بزرگ واقعی باید cold-cache/outage workload هم اندازه‌گیری شود.

## بودجه کوئری و مبلغ

- `Cart` داده را در عمر همان نمونه/درخواست memo می‌کند؛ ۱۲ خط سبد + clean/iteration/summary/validate در تست با **۲ query** (محصول و variant) خوانده شدند. mutation/clear memo را پاک می‌کند؛ درخواست بعدی قیمت تازه می‌خواند. checkout همچنان قیمت و stock را زیر قفل دوباره می‌خواند.
- پیش‌بارگذاری بی‌مصرف image/features از سبد حذف شده؛ هیچ کش مشترک قیمت/stock اضافه نشده است.
- `CART_MAX_LINES` پیش‌فرض ۱۰۰، محدوده ۱–۵۰۰؛ فقط افزودن خط جدید در سقف رد می‌شود، ویرایش خط موجود مجاز است. خطوط قدیمی بی‌صدا حذف نمی‌شوند.
- داشبورد staff با aggregateهای شرطی **۶ query ثابت** دارد. معنا و خروجی مالی قبلی حفظ شده؛ سود/درآمد خالص یا بازپرداخت انجام‌شده نیست.
- indexهای `(is_paid,paid_at)` سفارش، `(status,verified_at)` پرداخت و `(product,order)` آیتم اضافه شدند. وجود index به تنهایی benchmark بهبود مالی نیست.

## مشاهده‌پذیری

لاگ JSON هر درخواست: request_id، method، مسیر **template route**، status، duration_ms، db_queries، db_duration_ms و slow_query_count. فقط دیتابیس default اندازه‌گیری می‌شود؛ زمان DB شامل اجرای cursor است، نه تمام serialization/network/fetch/queue.

`SLOW_QUERY_MS` پیش‌فرض ۲۵۰؛ لاگ SQL، پارامتر query، بدنه، search term، slug شخصی یا token اضافه نشده است. slow_query_count شمارنده اجراهای عبورکرده از آستانه است، نه یک slow-query profiler یا اجرای EXPLAIN روی هر درخواست.

برای استقرار: لاگ‌ها را با rotation جمع کنید؛ نرخ ۵xx، p95 route، slow query، readiness، heartbeat worker، صف‌های needs_review/unknown/refund flags و استفاده منابع/Redis را پایش و alert کنید. این فاز collector، داشبورد خارجی، Sentry، گیرنده هشدار یا SLO واقعی را بدون انتخاب مقصد مجاز متصل نکرده است.

## تست بار محلی و ایمنی

ابزار `scripts/load_backend.py` فقط GET روی loopback و سرور دارای marker `X-Load-Test: synthetic-only` را می‌پذیرد. از production یا سایت شخص ثالث استفاده نکنید.

تنظیمات جدا `onlineshop.loadtest_settings`، DEBUG=True و PostgreSQL با نام منتهی به `_benchmark` را الزام می‌کند. seeder فقط دیتابیس خالی را می‌پذیرد، پاک‌سازی مخرب ندارد و باید صریح اجرا شود. anonymous rate فقط در همین تنظیمات مصنوعی بالا می‌رود؛ auth/checkout/cart و تنظیمات عادی سایت محدودیت قبلی را حفظ می‌کنند. هیچ provider فراخوانی نمی‌شود.

```bash
# از محیط غیرproduction، با PostgreSQL/Redis مستقل و متغیرهای مناسب محیط آزمایشی:
createdb shop_phase5_benchmark
export DJANGO_DEBUG=True DJANGO_DB_ENGINE=postgresql DJANGO_DB_NAME=shop_phase5_benchmark
export DJANGO_SETTINGS_MODULE=onlineshop.loadtest_settings
export CACHE_URL=redis://127.0.0.1:6379/4 SMS_BACKEND=console SMS_ASYNC=False
python manage.py migrate --noinput
python manage.py seed_backend_benchmark --products 10000 --output /tmp/shop-benchmark-fixtures.json
gunicorn onlineshop.wsgi:application --bind 127.0.0.1:18001 --workers 2 --threads 4 --capture-output --error-logfile /tmp/shop-benchmark-http.log
# در ترمینال دیگر با همین محیط:
python scripts/load_backend.py --fixtures /tmp/shop-benchmark-fixtures.json --requests 1200 --workers 8 --output /tmp/shop-benchmark-run.jsonl
```

هر مسیر raw خروجی تازه/غیرموجود لازم است. JSONL شامل status/latency/scenario/request_id است، نه response body، اطلاعات مشتری یا token. گرم‌کردن جداست. تنظیمات benchmark را در deployment، worker واقعی یا محیط مشترک OTP وارد نکنید.

گزارش نتایج و محدودیت‌های اندازه‌گیری: [phase-5-validation.md](phase-5-validation.md).
