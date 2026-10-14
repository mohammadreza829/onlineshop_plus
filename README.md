# Online Shop Plus

فروشگاه اینترنتی با Django و Django REST Framework؛ شامل کاتالوگ محصول، سبد خرید مبتنی بر session، ثبت سفارش، آدرس‌های کاربر، ورود با کد پیامکی و پرداخت زرین‌پال.

> وضعیت: در حال ارتقای فازبندی‌شده. فاز ۰ (پاک‌سازی و امنیت) در جریان است.

## ساختار اپ‌ها

| اپ | مسئولیت |
|---|---|
| `shop` | دسته‌بندی، محصول، ویژگی و تصویر محصول |
| `cart` | سبد خرید مبتنی بر session و محاسبهٔ هزینهٔ ارسال |
| `orders` | ثبت سفارش، ورود پیامکی (OTP) و API سفارش |
| `payment` | پرداخت و تأیید تراکنش زرین‌پال |
| `addresses` | آدرس‌های ثبت‌شدهٔ کاربر |
| `account` | مدل کاربر سفارشی (ورود با شمارهٔ موبایل) و پروفایل |
| `onlineshop` | تنظیمات و URLهای اصلی |

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

## API

- مستندات Swagger: `/api/docs/`
- Schema: `/api/schema/`
- سبد خرید: `/orders/api/v1/cart/`
- سفارش‌ها: `/orders/api/v1/orders/`
- ثبت سفارش: `/orders/api/v1/orders/create/`

## متغیرهای محیطی

فهرست کامل در `.env.example` است. فایل `.env` و هیچ کلید واقعی نباید commit شود.

## نقشهٔ راه

0. پاک‌سازی و امنیت: انتقال secretها به env، رفع باگ‌های API، requirements و README
1. درستی جریان خرید: state machine سفارش/پرداخت، رزرو موجودی، verify idempotent، OTP امن، تست
2. معماری و API: لایهٔ services/policies، JWT، permission و throttling، API محصولات
3. زیرساخت: Docker، Redis، Celery، GitHub Actions، health check
4. امکانات: variant محصول، کد تخفیف، نظر و امتیاز، علاقه‌مندی، پیگیری سفارش
5. تمایز: جستجوی متنی، پیشنهاد محصول، بهینه‌سازی و تست بار
