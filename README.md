# Online Shop Plus

فروشگاه اینترنتی با Django و Django REST Framework؛ شامل کاتالوگ محصول، سبد خرید مبتنی بر session، ثبت سفارش، آدرس‌های کاربر، ورود با کد پیامکی و پرداخت زرین‌پال.

> وضعیت: بک‌اند و فرانت Next.js موجودند. پروفایل دموی یکپارچهٔ لوکال، پرداخت شبیه‌سازی‌شده و اصلاحات مالی/دسترسی در این branch اضافه شده‌اند؛ [راهنمای دمو](docs/local-demo.md) و [وضعیت بررسی اصلاحات](docs/local-demo-fixes.md) را بخوانید. این تغییرات به معنی تایید انتشار production یا پاس‌شدن تمام CI نیست.

## ساختار اپ‌ها

| اپ           | مسئولیت                                           |
| ------------ | ------------------------------------------------- |
| `shop`       | دسته‌بندی، محصول، ویژگی و تصویر محصول             |
| `cart`       | سبد خرید مبتنی بر session و محاسبهٔ هزینهٔ ارسال  |
| `orders`     | ثبت سفارش، رزرو موجودی، وضعیت سفارش و API سفارش   |
| `payment`    | پرداخت و تأیید تراکنش زرین‌پال                    |
| `addresses`  | آدرس‌های ثبت‌شدهٔ کاربر                           |
| `account`    | مدل کاربر سفارشی، ورود امن پیامکی (OTP) و پروفایل |
| `onlineshop` | تنظیمات و URLهای اصلی                             |

## دموی یکپارچه روی لپ‌تاپ

برای اجرای فرانت و بک‌اند با یک launcher، OTP کنسولی و پرداخت بدون برداشت واقعی، از [راهنمای دموی لوکال](docs/local-demo.md) استفاده کنید. دیتابیس دمو مستقل از دیتابیس قبلی پروژه است.

## اجرای محلی

پیش‌نیاز: Python 3.12+ و PostgreSQL 14+ (یا SQLite برای اجرای سریع)

```bash
git clone https://github.com/mohammadreza829/onlineshop_plus.git
cd onlineshop_plus
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env               # مقادیر را تکمیل کنید
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

برای اجرای سریع بدون PostgreSQL در `.env` مقدار `DJANGO_DB_ENGINE=sqlite` بگذارید.

## جریان خرید و پرداخت

```
سبد خرید ──► ورود با کد پیامکی ──► انتخاب آدرس ──► ثبت سفارش (رزرو موجودی ۱۵ دقیقه) ──► درگاه زرین‌پال
                                                                                         │
                         ┌───────────────────────────── بازگشت از درگاه ◄────────────────┘
                         ▼
           verify (همیشه، حتی اگر Status=NOK)  ──► موفق / ناموفق / نامشخص
```

وضعیت‌های سفارش:

| از                                                           | به                                                                       |
| ------------------------------------------------------------ | ------------------------------------------------------------------------ |
| `pending` (در انتظار پرداخت)                                 | `paid`، `needs_review`، `canceled`، `expired`                            |
| `expired` / `canceled`                                       | `paid` یا `needs_review` (پرداخت دیرهنگام؛ پول گرفته شده و باید ثبت شود) |
| `needs_review` (پرداخت‌شده، نیازمند بررسی موجودی/سهمیه کوپن) | `preparing`، `canceled` (بازگشت وجه)                                     |
| `paid`                                                       | `preparing`، `canceled`                                                  |
| `preparing`                                                  | `sent`، `canceled`                                                       |
| `sent`                                                       | `delivered`                                                              |

تصمیم‌های کلیدی:

- **رزرو موجودی هنگام ثبت سفارش** با یک `UPDATE ... SET inventory = inventory - q WHERE inventory >= q` شرطی؛ دو خرید هم‌زمان نمی‌توانند آخرین کالا را دو بار بفروشند (تست هم‌زمانی واقعی با thread روی PostgreSQL).
- **verify ایدمپوتنت**: ردیف Payment با `select_for_update` قفل می‌شود؛ callback تکراری یا هم‌زمان فقط یک بار درگاه را صدا می‌زند و موجودی را دوباره کم نمی‌کند.
- **هیچ‌وقت rollback بعد از گرفتن پول**: اگر پرداخت بعد از انقضای رزرو برسد و موجودی تمام شده باشد، سفارش `needs_review` می‌شود؛ پرداخت تکراری با `needs_refund` علامت می‌خورد.
- **وضعیت «نامشخص»** برای timeout/خطای شبکهٔ درگاه؛ دستور `reconcile_payments` بعداً دوباره استعلام می‌گیرد.
- مبلغ‌ها در دیتابیس به تومان‌اند و هنگام ارسال به زرین‌پال صریحاً به ریال (×۱۰) تبدیل می‌شوند.
- **OTP امن**: تولید با `secrets`، ذخیرهٔ فقط HMAC کد در cache، انقضای ۲ دقیقه، حداکثر ۵ تلاش، فاصلهٔ ارسال مجدد و سقف ساعتی برای هر شماره و هر IP.

### کارهای زمان‌بندی‌شده (جایگزین بدون beat؛ هم‌زمان با beat اجرا نکنید)

```bash
* * * * *   python manage.py expire_orders          # آزادسازی موجودی سفارش‌های پرداخت‌نشده
*/5 * * * * python manage.py reconcile_payments     # استعلام پرداخت‌های نامشخص/رهاشده
```

## تست

```bash
python manage.py test                     # روی SQLite تست‌های هم‌زمانی skip می‌شوند
DJANGO_DB_ENGINE=postgresql python manage.py test   # همهٔ تست‌ها، از جمله هم‌زمانی
```

گزارش بررسی فاز ۱، دستورات بازتولید و محدودیت‌های انتشار: [اعتبارسنجی فاز ۱](docs/phase-1-validation.md).

## زیرساخت

راهنمای [Docker، Redis، Celery، health check و CI](docs/infrastructure.md). برای اجرای stack محلی پس از تنظیم `.env`:

```bash
docker compose up -d --build --wait
docker compose exec web python manage.py check_infrastructure --with-worker
```

وقتی Celery beat فعال است، cronهای قدیمی انقضای سفارش/استعلام پرداخت را هم‌زمان اجرا نکنید. این تنظیمات به معنی استقرار خودکار production نیستند.

## API

API اصلی نسخه‌دار در `/api/v1/` است؛ ورود OTP/JWT، کاتالوگ، آدرس‌ها، سبد و سفارش‌ها. [قرارداد API و نکات امنیتی](docs/api-v1.md) را پیش از ساخت کلاینت بخوانید. سبد همچنان session/cookie-bound است و با JWT بین دستگاه‌ها همگام نمی‌شود.

برای JWT اجرای `python manage.py migrate` لازم است؛ پاک‌سازی روزانهٔ tokenهای منقضی با `python manage.py flushexpiredtokens`.

مسیرهای زیر alias قدیمی و سازگار باقی مانده‌اند:

- مستندات Swagger: `/api/docs/`
- Schema: `/api/schema/`
- سبد خرید: `/orders/api/v1/cart/`
- سفارش‌ها: `/orders/api/v1/orders/`
- ثبت سفارش: `/orders/api/v1/orders/create/`

## امکانات فروشگاهی

تنوع رنگ/سایز با موجودی و قیمت مستقل، کوپن با رزرو سهمیه، نظر خریدار با تایید مدیر، علاقه‌مندی خصوصی، پیگیری/اعلان داخل حساب و API داشبورد فروش staff. [قرارداد و محدودیت‌ها](docs/shop-features.md) و [گزارش اعتبارسنجی فاز ۴](docs/phase-4-validation.md). بازطراحی یکپارچه فرانت و صفحات جدید همچنان فاز ۶ است و نوع/تکنولوژی آن باید پیش از شروع با صاحب پروژه تعیین شود؛ داشبورد فعلاً API است و اعلان وضعیت، پیامک واقعی نیست.

## عملکرد و آمادگی بک‌اند

[جستجوی فارسی PostgreSQL، پیشنهاد محصول، کش شناسه‌ها و بودجه کوئری](docs/backend-performance.md)، [اعتبارسنجی فاز ۵](docs/phase-5-validation.md) و [گیت‌های انتشار واقعی](docs/backend-release-checklist.md). این فاز فرانت جدیدی نمی‌سازد و هیچ فریمورک فرانت را قطعی نمی‌کند.

## تحویل به فرانت

[راهنمای اتصال و محدودیت‌ها](docs/frontend-handoff.md)، [OpenAPI ثابت](docs/openapi-v1.yaml) و [گزارش تست تحویل](docs/frontend-handoff-validation.md). شامل bootstrap CSRF، گزینه‌های معتبر کلاینت و تغییر مقدار مطلق سبد؛ بدون انتخاب فریمورک یا ساخت UI جدید.

## متغیرهای محیطی

فهرست کامل در `.env.example` است. فایل `.env` و هیچ کلید واقعی نباید commit شود.

## نقشهٔ راه

0. پاک‌سازی و امنیت: انتقال secretها به env، رفع باگ‌های API، requirements و README
1. درستی جریان خرید: state machine سفارش/پرداخت، رزرو موجودی، verify idempotent، OTP امن، تست
2. معماری و API: لایهٔ services/policies، JWT، permission و throttling، API محصولات
3. زیرساخت: Docker، Redis، Celery، GitHub Actions، health check
4. امکانات: variant محصول، کد تخفیف، نظر و امتیاز، علاقه‌مندی، پیگیری سفارش
5. تمایز: جستجوی متنی، پیشنهاد محصول، بهینه‌سازی و تست بار
6. فرانت‌اند نهایی: رابط RTL یکپارچه، design system، صفحه‌های کامل، ریسپانسیو، دسترس‌پذیری و تست مرورگر؛ بعد از همهٔ ارتقاهای بالا

## فرانت مشتریان

راهنمای نصب و تست: [frontend/README.md](frontend/README.md). گزارش واقعی اجرا، محدودیت‌ها و موارد نیازمند تأیید: [FRONTEND_IMPLEMENTATION.md](FRONTEND_IMPLEMENTATION.md). فرانت همراه همین ریپو نصب می‌شود؛ این مرحله به معنی deploy production نیست.
