# اصلاح ورود و مسیر برگشت پرداخت

## تغییرات محدود

- بازیابی CSRF: توکن در حافظهٔ تب ممکن بود با کوکی یا کلید جدید هماهنگ نباشد. BFF اکنون رد CSRF را **پیش از forward** با هدر اختصاصی مشخص می‌کند؛ client فقط برای همین پاسخ یک بار bootstrap و retry می‌کند. خطای شبکه، origin متفاوت، 401/429/5xx یا 403 سرویس Django replay نمی‌شوند. CSRF، Origin دقیق، HttpOnly و cookieهای امن همچنان فعال‌اند.
- خطای Origin پیام مشخص با نشانی تنظیم‌شده دارد. فقط در توسعه، `LocalOrigin` پیش از mount مصرف‌کنندگان API، loopback متفاوت روی **همان پورت** را با ناوبری کامل مرورگر به `APP_ORIGIN` می‌برد. hostname عمومی، port متفاوت و production مشمول این رفتار نیستند.
- `AuthGate` query مقصد (از جمله `order`) را در مسیر ورود نگه می‌دارد؛ redirect داخلی همچنان allowlist دارد.
- فرم phone/code با key مستقل، هشدار uncontrolled→controlled را رفع می‌کند. ویژگی scroll-behavior مورد انتظار Next به html اضافه شده؛ رفتار اسکرول تغییر نکرده است.
- API شروع پرداخت اکنون callback جداگانهٔ `/payment/storefront/verify/` می‌سازد. verify مالی همان `process_callback` موجود است؛ سپس 303 به `FRONTEND_ORIGIN/payment/result?order=ID`. پاسخ‌های success/failed/unknown از طریق API صاحب سفارش نمایش داده می‌شوند. callback ناقص/ناشناخته به نتیجهٔ بدون order برمی‌گردد، نه ادعای موفقیت.
- `FRONTEND_ORIGIN` فقط از تنظیم سرور خوانده و اعتبارسنجی می‌شود؛ `next`، `Status` یا origin مرورگر مقصد را تعیین نمی‌کنند. authority/JWT/مبلغ/کد مرجع به URL نتیجه اضافه نمی‌شوند. خواندن جزئیات نیازمند احراز هویت و مالکیت در API است.
- URL callback قدیمی، قالب‌های legacy و Admin تغییر نکرده‌اند. با FRONTEND_ORIGIN خالی، fallback legacy حفظ می‌شود. سبد storefront پاک نمی‌شود تا انتخاب‌های جدید کاربر از بین نروند.
- گزینهٔ `SMS_CONSOLE_SHOW_OTP` پیش‌فرض خاموش است. فقط با DEBUG و SMS console در ترمینال محلی قابل اعتماد کد را بدون شماره چاپ می‌کند. با DEBUG=False شروع برنامه را منع می‌کند و در runtime نیز guard دارد؛ فیلتر عمومی لاگ غیرفعال نشده است.

## اجرا روی لپ‌تاپ

- `.env` ریشه: `DJANGO_DEBUG=True`، `DJANGO_DB_ENGINE=sqlite`، `FRONTEND_ORIGIN=http://localhost:3000`، `SMS_BACKEND=console`، `SMS_ASYNC=False`؛ نمایش کد فقط با opt-in بالا.
- `frontend/.env.local`: `APP_ORIGIN=http://localhost:3000`، `DJANGO_ORIGIN=http://127.0.0.1:8000`؛ secret محلی ثابت و محرمانه، memory فقط توسعهٔ تک‌فرآیندی و Redis URL خالی.
- هر دو سرور پس از تغییر env باید restart شوند. دیتابیس، secretهای موجود و تنظیمات پرداخت overwrite نمی‌شوند. هیچ migration یا dependency جدیدی لازم نیست.
- پرداخت‌هایی که پیش از تغییر شروع شده‌اند URL callback قبلی دارند. آنها را دوباره پرداخت نکنید؛ وضعیت را از سفارش‌های حساب بررسی کنید.

## QA همین اصلاح

- Django روی SQLite موقت: 207 تست، 197 موفق و 10 skip وابسته به محیط؛ بدون شکست. تست‌های callback شامل نبود session، عدم اعتماد به Status، عدم open redirect، callback تکراری، نتیجه نامشخص/ناموفق، callback ناقص، حفظ سبد و fallback legacy هستند. API شروع پرداخت نیز انتخاب callback جدید را بررسی می‌کند.
- Frontend: TypeScript، ESLint و production build موفق. 71 unit/integration موفق، 1 تست Redis skip. بازیابی محدود CSRF و عدم replay عملیات مبهم تست شده‌اند.
- مرورگر توسعه با Django واقعیِ ایزوله: سه آزمون موفق؛ CSRF حذف‌شده → رد پیش از forward → bootstrap → ورود؛ canonical loopback؛ و مسیر دو variant/سبد/OTP/آدرس/کوپن/سفارش/درگاه آزمایشی/verify/303 به صفحهٔ جدید/refresh JWT. randomness و ارسال OTP و provider درگاه فقط در harness تست جایگزین شده‌اند، نه runtime محصول.
- 27 آزمون UI/مرورگر روی production build موفق شدند (در کنار سه آزمون توسعه، 30 آزمون مرورگر در دو محیط). مجموعهٔ UI production جدا از backend fixture واقعی اجرا می‌شود تا initialData سمت سرور و mockهای مرورگر با هم مخلوط نشوند. مسیرهای ۱۴ صفحه، login مقصددار، وضعیت‌های پرداخت، RTL/reflow/axe، منو و WebGL در این مجموعه‌اند.

## محدودیت‌ها

این QA روی محیط agent و Chromium انجام شده، نه localhost لپ‌تاپ مالک. Redis واقعی، PostgreSQL/concurrency، درگاه بیرونی/پول واقعی، SMS واقعی، staging و مرورگر/دستگاه واقعی در این دور بررسی نشده‌اند. public origin callback و trusted client-IP برای استقرار همچنان باید تنظیم و تست شوند. پرداخت sandbox واقعی بدون تأیید مالک انجام نشده است. تغییرات در برنچ طراحی هستند؛ merge/deploy انجام نشده‌اند.
