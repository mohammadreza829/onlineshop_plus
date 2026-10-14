# اعتبارسنجی فاز ۵ بک‌اند

فاز ۴ با PR #5 به main ادغام شد (`905c673592c07ea4408476d6846dd7c65c2de9de`). فاز ۵ در `phase-5/backend-performance` با پنج کامیت معنادار آماده شده است؛ این گزارش تایید استقرار/CI میزبانی‌شده نیست. فرانت شروع نشده و نوع/تکنولوژی آن نیاز به گفت‌وگو و تصمیم مشترک دارد.

## آزمون‌های کد و runtime

- PostgreSQL + Redis واقعی: **187 تست موفق، بدون skip**؛ 25 تست جدید نسبت به فاز ۴.
- Docker + PostgreSQL + Redis: **همان 187 تست موفق، بدون skip**.
- SQLite/LocMem: **177 موفق، 10 skip** (۸ PostgreSQL و ۲ Redis).
- چهار تست رقابت موجودی پایه/variant/سهمیه کوپن/checkout یک مشتری، در پنج اجرای متوالی موفق.
- migrationهای جدید روی دیتابیس محلی و Compose اعمال شدند؛ makemigrations --check بدون تغییر، OpenAPI --validate --fail-on-warn بدون هشدار، pip check و deploy check سخت‌گیرانه با secret موقت بررسی موفق.
- lint و همه hookهای pre-commit موفق. تصویر Docker با --network host ساخته شد (محدودیت bridge محیط آزمایشی)؛ Compose --no-build --wait و readiness واقعی database/cache/worker موفق؛ stack QA پس از بررسی متوقف شد و volumeها حذف نشدند.
- بودجه query ثابت تست شد: سبد ۱۲ خط با clean/iteration/summary/validate دو query؛ warm recommendation service یک query زنده (بدون query lookup مبدا API)؛ داشبورد staff شش query.

تست‌های جدید: نرمال‌سازی فارسی/عربی/ارقام/نیم‌فاصله، تطبیق فیلد و فیلتر فعال، جستجوی SQL نامطمئن، ranking و websearch، trigger bulk/raw SQL، GIN موجود؛ ترتیب پیشنهاد دسته/خرید paid، anchor مخفی، سقف limit و کالای ناموجود؛ cache warm/rollback/commit/outage و عدم cache قیمت یا stock؛ request memo و mutation/سقف سبد؛ query budget داشبورد؛ لاگ DB بدون SQL/پارامتر/slug/query خصوصی؛ guard محیط seed، محدودیت loopback/concurrency و boot تنظیمات benchmark تنها با DB مستقل.

## smoke بار HTTP محلی؛ نه ظرفیت production

داده کاملاً مصنوعی: 10,000 محصول، 5,000 variant، 5,000 نظر تاییدشده آزمایشی و 100 دسته در PostgreSQL مستقل. هیچ مشتری واقعی/سرویس‌دهنده/پول واقعی در این بار وجود ندارد.

- بازه UTC: `2026-10-14T10:21:05.448901+00:00` تا `2026-10-14T10:21:17.868305+00:00`.
- 1200 GET، 8 virtual user closed-loop، دو worker گانیکورن با چهار thread، 40 درخواست warmup خارج از محاسبه.
- چهار مسیر به وزن برابر؛ هر مسیر ۳۰۰ درخواست. **0 خطای status/contract ثبت‌شده**.
- زمان اندازه‌گیری 12.42 ثانیه؛ throughput مشاهده‌شده **96.6 درخواست/ثانیه**؛ p95 کلی **115.4 ms**. این اعداد ظرفیت ثابت/حداکثر، SLO یا عملکرد کاربران اینترنتی نیستند.

| مسیر | درخواست | p50 ms | p95 ms | p99 ms | query هر درخواست |
| --- | ---: | ---: | ---: | ---: | ---: |
| catalog | 300 | 84.6 | 126.0 | 157.1 | 2–2 |
| detail | 300 | 66.1 | 91.1 | 119.1 | 4–4 |
| recommendations | 300 | 78.8 | 115.9 | 128.0 | 2–2 |
| search | 300 | 72.6 | 103.1 | 118.5 | 2–2 |

Client JSONL با request_id به log JSON سرور تطبیق one-to-one داشت؛ تمام 1200 درخواست اندازه‌گیری‌شده پوشش داده شدند. quantile تجربی با interpolation خطی محاسبه شد. کنترل جداگانه raw count/error با نتایج تجمیع برابر بود. status ثابت ۲۰۰ و ستون error کاملاً null در profiler، نتیجه موفقیت پاسخ‌ها هستند نه داده گمشده؛ هیچ ردیفی حذف نشده است.

### EXPLAIN واقعی

پس از bulk seed، planner ابتدا Seq Scan انتخاب کرد؛ سپس نگهداری معمول `VACUUM (ANALYZE)` انجام شد. در برنامه بعدی جستجوی واژه کم‌فراوان «نایاب»، `product_search_gin` واقعاً انتخاب شد؛ optimizer با enable_seqscan یا تنظیم اجباری دیگری تغییر داده نشد. زمان اجرای همین query مشاهده‌شده 0.181 ms و خروجی limit آن 20 ردیف بود؛ این query محدود، benchmark همه جستجوها نیست و مقایسه سرعت قبل/بعد ادعا نمی‌شود. بار نهایی بالا پس از همین نگهداری اجرا شد.

### محدودیت اندازه‌گیری

اجرای کوتاه روی یک sandbox مشترک برای client/app/PG/Redis، DEBUG فعال، بدون TLS/proxy/latency شبکه بیرونی، anonymous throttle بالا فقط در تنظیمات مصنوعی؛ بدون spike/soak/constant-arrival، cold-cache/outage باردار، session سبد پر، checkout، OTP یا callback بانکی تحت بار. داده خرید در بار عمومی وجود نداشت (سناریوی مالی restore بعد از پایان بار اضافه شد). بار طولانی‌تر روی محیط مقصد لازم است؛ هیچ درصد بهبود یا ظرفیت مشتری واقعی از این داده استنتاج نشده است.

## backup/restore و migration reversal

pg_dump/pg_restore روی داده مصنوعی مستقل انجام شد. بعد از بار، یک سفارش paid آزمایشی با payment ساختگی و کوپن مصرف‌شده/stock snapshot/event/notification افزوده شد؛ provider فراخوانی نشد. شمارش و fingerprint ردیف‌ها در **13 جدول منتخب** قبل و بعد restore برابر بود. rollback جستجو به shop 0003 و reapply نیز همان fingerprintها را حفظ و search_document را بازسازی کرد.

این backup production، media، RPO/RTO، settlement بانکی یا recovery broker نیست. آرشیو و raw request/log/snapshot در کامپیوتر آزمایشی ماندند و به GitHub/image منتقل نشدند. خلاصه reconciled و provenance: [phase-5-benchmark-summary.json](phase-5-benchmark-summary.json). raw paths در JSON، مسیرهای همان sandbox هستند، نه URL دانلود عمومی؛ ابزارهای seed/load برای بازتولید در مخزن قرار دارند.

## بازتولید QA

```bash
pip install -r requirements-dev.txt
# فقط با DB/Redis آزمایشی و متغیرهای محیط مناسب:
DJANGO_DEBUG=True DJANGO_DB_ENGINE=postgresql CACHE_URL=redis://127.0.0.1:6379/1 python manage.py test --noinput
DJANGO_DEBUG=True DJANGO_DB_ENGINE=sqlite CACHE_URL='' python manage.py test --noinput
python manage.py migrate --noinput
python manage.py makemigrations --check --dry-run
python manage.py spectacular --validate --fail-on-warn --file /tmp/schema.yaml
pre-commit run --all-files
pip check
python manage.py test shop.test_variants.ConcurrentVariantTests orders.test_coupons.ConcurrentCouponTests api.tests.ConcurrentCustomerCheckoutTests orders.tests.ConcurrentCheckoutTests --noinput
```

راهنمای load/ایمنی و قرارداد: [backend-performance.md](backend-performance.md). گیت‌های قبل از انتشار: [backend-release-checklist.md](backend-release-checklist.md).

## نتیجه و باقی‌مانده

قابلیت‌های برنامه‌ریزی‌شده بک‌اند این فاز پیاده و محلی اعتبارسنجی شدند. موفقیت hosted CI با مجوز فعلی تایید نشده؛ بررسی امنیت مستقل، چرخش secretها، سرویس‌دهنده واقعی، TLS/استقرار، ظرفیت محیط مقصد و collector/alert واقعی باقی است. نمونه restore مصنوعی موفق بوده، نه تمرین بازیابی production. هیچ تضمین «بدون باگ» یا پایان همه مسئولیت‌های عملیاتی داده نمی‌شود. تصمیم فرانت فقط پس از گفت‌وگو با صاحب پروژه؛ در این فاز فرانت جدید ساخته نشده است.
