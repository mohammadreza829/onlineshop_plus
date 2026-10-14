# اعتبارسنجی تحویل بک‌اند به فرانت

## دامنهٔ تحویل

فاز ۵ از طریق PR #6 با commit ادغام `40a6134c4ad82e722da1da171caee3274167b18c` وارد main شد. این تکمیل جداگانه، bootstrap عمومی، CSRF قابل استفاده با HttpOnly cookie، تغییر مقدار مطلق سبد، حذف خط غیرفعال و سیاست no-store را اضافه می‌کند. هیچ نوع فرانت، معماری token storage یا CORS انتخاب نشده است.

## شواهد اجرایی

- PostgreSQL + Redis واقعی: **۱۹۹ تست موفق، بدون skip**.
- SQLite + LocMem: **۱۸۹ موفق و ۱۰ skip** مخصوص PostgreSQL/Redis؛ مجموع ۱۹۹.
- Docker با PostgreSQL 16، Redis 7، web/worker/beat/migrate واقعی: **۱۹۹ تست موفق، بدون skip**؛ stack آماده شد. build با `--network host` و اجرای Compose با `--no-build` به دلیل محدودیت bridge همین محیط انجام شد، نه تغییر روش شبکهٔ production.
- OpenAPI با `--validate --fail-on-warn` بدون هشدار تولید شد. فایل ثابت `docs/openapi-v1.yaml` با schema تولیدی در تست مقایسه می‌شود؛ محدودیت read-only ترتیب تصویر صریح است تا inference عددی SQLite/PostgreSQL قرارداد را تغییر ندهد.
- ruff check/format، pip check، Django system check و makemigrations --check موفق؛ migration جدیدی لازم نیست.
- امکان خواندن جزئیات hosted GitHub Actions در اتصال فعلی قبلاً با 403 محدود بود؛ موفقیت تست‌های محلی/Docker به عنوان موفقیت hosted CI گزارش نمی‌شود.

## سناریوهای افزوده

- حفظ cookie سبد مهمان → OTP واقعی در منطق داخلی → JWT → ساخت آدرس → checkout با variant و coupon → شروع پرداخت فقط POST → callback بدون session، حتی با Status=NOK → callback تکراری و کسر/مصرف تنها یک بار → دریافت سفارش/پیگیری/اعلان → پاک‌کردن صریح سبد → جلوگیری از دسترسی کاربر دیگر → refresh rotation/logout.
- پرداخت UNKNOWN و سپس بازیابی موفق روی همان سفارش، بدون رزرو/کسر دوباره.
- مقدار مطلق سبد، تکرار/کاهش/صفر، clamp به موجودی، عدم اعتماد به قیمت ارسالی، ورودی نامعتبر، تفکیک variant، خط ناموجود و methodهای ممنوع در alias قدیمی.
- CSRF session: بدون token رد، با token موفق، Origin نامعتبر با همان token رد؛ bootstrap با cookie HttpOnly.
- گزینه‌های کلاینت دقیقاً whitelist و همان استان‌های موجود، بدون افشای تنظیم محرمانه یا هدر CORS؛ no-store روی پاسخ‌های عمومی/خصوصی/خطا/legacy.

فقط transport پیامک و gateway در جریان خرید mock هستند؛ سرویس‌های سفارش، موجودی، کوپن، OTP، token و callback واقعاً اجرا می‌شوند. این تست مرورگر/UI نیست و هیچ پیامک واقعی، پرداخت production یا تضمین نبود باگ/ممیزی امنیت محسوب نمی‌شود.

## بازتولید

```bash
ruff check .
ruff format --check .
python -m pip check
python manage.py makemigrations --check --dry-run
python manage.py spectacular --validate --fail-on-warn --file /tmp/schema.yaml
# env شامل PostgreSQL آزمایشی و Redis مشترک؛ نه دیتابیس production
python manage.py test --noinput
DJANGO_DB_ENGINE=sqlite CACHE_URL='' python manage.py test --noinput
```

[راهنمای اتصال](frontend-handoff.md) و [گیت‌های انتشار](backend-release-checklist.md) مرجع باقی‌مانده‌ها هستند. frontend همچنان منتظر گفت‌وگو درباره نوع و معماری است.
