
# دموی یکپارچه لوکال

این پروفایل برای **یک لپ‌تاپ و اجرای تک‌فرآیندی** است، نه production.
پرداخت شبیه‌سازی است و هیچ پولی برداشت نمی‌شود؛ OTP فقط در ترمینال Django چاپ می‌شود.
دیتابیس دمو در `.local-demo/db.sqlite3` مستقل از دیتابیس قبلی پروژه است.
هیچ دیتابیس یا اطلاعات کاربری قبلی حذف، reset یا seed نمی‌شود.

## نصب و اجرا

Python سازگار با requirements پروژه و Node 24 لازم است.
در venv فعال، از ریشه پروژه:

```bash
pip install -r requirements.txt
cd frontend
npm ci
cd ..
python scripts/run_local_demo.py --setup
python manage.py createsuperuser --settings=onlineshop.demo_settings
python scripts/run_local_demo.py
```

روی Windows به‌جای فرمان‌های activation لینوکس از activation همان venv استفاده کنید؛
launcher خودش npm.cmd را انتخاب می‌کند.
همیشه از `http://127.0.0.1:3000` استفاده کنید، نه ترکیب localhost و 127.0.0.1.
Admin: `http://127.0.0.1:8000/admin/`؛ محصول و تنوع‌های دمو را در Admin بسازید
(نام/قیمت واردشده برای دمو است، نه اطلاعات واقعی فروشگاه).
شماره دلخواه معتبر خود را در فرانت وارد کنید و OTP چاپ‌شده در ترمینال Django را بخوانید.
بعد از سفارش و پرداخت، صفحه آزمایشی موفق/ناموفق/نامشخص را انتخاب کنید.
callback به نتیجه همان سفارش در Next برمی‌گردد؛ query مرورگر اثبات موفقیت نیست.

خروج با Ctrl+C هر دو سرور را متوقف می‌کند.
launcher هر دقیقه expiry و reconciliation را اجرا می‌کند؛ Celery beat/cron را هم‌زمان اجرا نکنید.
برای اجرای جداگانه فرمان‌های demo از `--settings=onlineshop.demo_settings` استفاده کنید.

## مالی و نقش‌ها

- staff بدون permission تخصصی حق تغییر سفارش/دیدن فروش ندارد.
- انبار: `orders.change_order`؛ مالی برای لغو: `orders.change_order` و `orders.cancel_paid_order`؛ مشاهده مالی: `orders.view_sales`
  و `payment.confirm_refundrequest` طبق نیاز.
- Admin به‌صورت پیش‌فرض حذف سفارش/پرداخت/کاربر و تغییر مالک سفارش را نمی‌پذیرد.
- لغو سفارش پرداخت‌شده یک RefundRequest می‌سازد. واردکردن bank_reference در پنل،
  **ثبت سند بازپرداخت انجام‌شده** است، نه انتقال پول توسط برنامه.
- برای coupon_capacity از اکشن پذیرش کوپن در Admin با دلیل صریح استفاده کنید؛
  اجازه `orders.resolve_order_review` لازم است. این اقدام مبلغ پرداخت‌شده را تغییر نمی‌دهد؛ تصمیم پذیرش تخفیف را ثبت می‌کند.
- unknown را دوباره charge نکنید. دموی unknown را با همان لینک درگاه و انتخاب موفقیت بازیابی کنید.
- سبد بعد از پرداخت خودکار پاک نمی‌شود؛ انتخاب‌های جدید محفوظ می‌مانند.

## تست و محدوده

```bash
python manage.py test payment.test_demo_regressions
python manage.py test
cd frontend
npm run typecheck
npm test
npm run build
```

CI نتیجه واقعی روی همان commit را تعیین می‌کند؛ افزودن workflow به معنی پاس‌شدن آن نیست.
SQLite دمو جای تست هم‌زمانی PostgreSQL یا Redis چندفرآیندی را نمی‌گیرد.
تنظیمات demo را deploy نکنید. IP مورد اعتماد پشت proxy، سرو media در production،
provider واقعی، callback عمومی و سنجش چند replica گیت‌های آینده‌اند، نه الزام اجرای این دمو.
