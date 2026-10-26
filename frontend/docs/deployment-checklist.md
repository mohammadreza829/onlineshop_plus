# چک‌لیست اتصال و انتشار

کد محلی و تست‌شده است؛ این فهرست به معنی انجام انتشار نیست.

## محیط و اتصال

- [ ] دامنه و نام برند تأییدشده؛ `APP_ORIGIN` و `SITE_URL` واقعی HTTPS و یکسان با storefront. بدون دامنه، canonical/domain ساختگی ایجاد نمی‌شود.
- [ ] Node runtime (نه Edge/static export)، نصب `npm ci`، build و `next start` پشت TLS/reverse proxy؛ bind پیش‌فرض loopback است. این مرحله Docker/CI frontend ایجاد نکرده است.
- [ ] Django و migrations **موجود** مطابق مستندات ریشه آماده باشند؛ در این فاز migration جدید ساخته نشده است.
- [ ] `DJANGO_ORIGIN` ثابت، trusted، بدون path یا credentials؛ شبکهٔ Next به Django دسترسی داشته باشد. CORS مرورگر برای این BFF لازم نیست؛ wildcard credentials اضافه نکنید.
- [ ] secret تصادفی با حداقل ۳۲ کاراکتر، محرمانه و مشترک در replicaها؛ تغییر secret کوکی‌ها و recovery refresh را نامعتبر می‌کند. برنامهٔ rotation و ورود دوباره لازم است.
- [ ] Redis خصوصی مشترک با ACL/TLS/credential مناسب؛ عدم استفاده از memory در production؛ outage موجب fail-closed/503 می‌شود. دو سرویس Django و Redis یک transaction مشترک ندارند؛ بی‌وقفه‌بودن refresh در همهٔ crashها تضمین نشده است.
- [ ] `BFF_LOCAL_HTTP` خاموش، `gw.test` حذف، کوکی Secure/HttpOnly/host-only/Lax روی HTTPS واقعاً بررسی شود.
- [ ] نام‌های cookie واقعی Django با `DJANGO_SESSION_COOKIE_NAME` و `DJANGO_CSRF_COOKIE_NAME` مطابقت کنند. session سبد بین دستگاه‌ها sync نیست.
- [ ] `SMS_CONSOLE_SHOW_OTP=False` در همهٔ محیط‌های عمومی/مشترک؛ opt-in نمایش کد صرفاً برای ترمینال توسعهٔ قابل اعتماد است.
- [ ] log/monitoring/redaction نباید OTP، شماره، JWT، cookie یا پاسخ auth را ثبت کند. هیچ analytics خصوصی در این فاز اضافه نشده است.

## سه تصمیم اتصال پیش از انتشار عمومی

- [ ] **IP معتبر مشتری و throttle:** BFF درخواست را server-to-server می‌فرستد؛ Django معمولاً IP سرویس Next را می‌بیند. طراحی trusted proxy/client-IP و نرخ‌ها باید در بک‌اند با تأیید مالک بررسی شوند. X-Forwarded-For ارسالی مرورگر را کورکورانه forward نکنید. QA نرخ بالا داشت؛ سلامت multi-user throttle production با آن اثبات نشده است.
- [ ] **callback عمومی و یکپارچه:** callback موجود Django حفظ شده. Django ممکن است URL callback را با origin دریافت‌کنندهٔ درخواست بسازد؛ origin صرفاً داخلی BFF برای درگاه بیرونی کافی نیست. public origin/trusted proxy یا callback config باید درست باشد. redirect محدود API از `/payment/storefront/verify/` پس از verify پیاده شده است؛ `FRONTEND_ORIGIN` در Django باید HTTPS و برابر `APP_ORIGIN` باشد. نتیجه مجدداً از سفارش صاحب حساب خوانده می‌شود، نه `Status=OK`. callbackهای legacy مستقل حفظ شده‌اند.
- [ ] **پاک‌سازی سبد:** این فرانت بعد از پرداخت سبد را خودکار خالی نمی‌کند؛ بررسی و حذف انتخابی صریح دارد. endpoint شرطی/اتمیک برای پاک‌سازی فقط اقلام پرداخت‌شده در برابر تغییر سبد وجود ندارد. اگر پاک‌سازی خودکار لازم است، تغییر قرارداد backend نیازمند تأیید است.

## فروش، محتوا و پرداخت

- [ ] تصاویر واقعی کالا، alt/شرح، دسته و قیمت/variant واقعی؛ هیچ fixture تست وارد DB واقعی نشود. تصاویر بدون مجوز hero اضافه نشوند.
- [ ] متن تأییدشدهٔ حریم خصوصی، مرجوعی، شرایط فروش، تماس/نشانی و جدول اندازهٔ واقعی از صاحب فروشگاه دریافت شود. در UI فعلی لینک/ادعای جعلی وجود ندارد.
- [ ] `PRODUCT_IMAGE_HOSTS` فقط hostname دقیق CDN مورد تأیید (بدون URL/port/wildcard)؛ rebuild پس از تغییر آن برای CSP. `/media/` از proxy محدود و سقف ۵MB می‌گذرد؛ host نامعتبر نمایش داده نمی‌شود. فایل SVG پذیرفته نمی‌شود.
- [ ] API فهرست تصویر thumbnail نمی‌دهد؛ کارت‌ها detail محدود دریافت می‌کنند. نرخ و کارایی روی کاتالوگ واقعی بزرگ سنجیده شود؛ افزودن thumbnail به list قراردادِ پیشنهادی است، در این فاز انجام نشده است.
- [ ] lookup رنگ/سایز سبد از detail عمومی و ID دقیق است؛ نام کالای تغییرکرده/غیرفعال یا خارج از ۱۰۰ نتیجهٔ search ممکن است قابل resolve نباشد. fallback شفاف وجود دارد. بهترین بهبود: snapshot labels/slug در cart serializer با تأیید مالک.
- [ ] `PAYMENT_HOSTS` فقط host دقیق HTTPS درگاه همان محیط؛ sandbox/live را هم‌زمان و بی‌دلیل allow نکنید. Merchant و SMS secrets فقط سمت Django/secret manager.
- [ ] resend نمایش ۶۰ ثانیه با تنظیم واقعی `OTP_RESEND_SECONDS` هماهنگ باشد؛ 429/Retry-After سرور همیشه مرجع است.
- [ ] Celery/beat یا cron موجود برای expiry و reconcile طبق مستندات بک‌اند آماده و **دو بار** اجرا نشوند؛ frontend جایگزین reconcile نیست.
- [ ] وضعیت pending بدون تأیید، needs_review، canceled با paid_at و expired واقعاً مرور شوند. API سفارش، جزئیات کامل transaction unknown/failed را نمی‌دهد؛ UI «تأیید ثبت نشده» می‌گوید و حدس نمی‌زند.

## Gateهای QA

- [ ] build/typecheck/lint/unit/Redis/E2E روی نسخهٔ نهایی.
- [ ] تست PostgreSQL و concurrency/regression کامل قبل از انتشار؛ این نوبت regression فقط SQLite بود.
- [ ] iOS Safari/WebKit، Firefox، Android واقعی، screen reader و کاربر فارسی واقعی؛ این نوبت مرورگر sandbox Chromium بود.
- [ ] کاتالوگ پُر، تصویر واقعی، شبکهٔ کند، rate-limit عملی، refresh چند replica و crash/outage؛ fixture کوچک جای performance production نیست.
- [ ] callback روی دامنهٔ staging، پرداخت sandbox با تأیید و بدون پول واقعی؛ QA این نوبت FakeGateway بود و API بیرونی زرین‌پال فراخوانی نشد.
- [ ] ارزیابی CSP دقیق‌تر با nonce/hash در صورت نیاز؛ CSP فعلی محدودیت origin دارد اما inline script/style لازم Next را مجاز می‌گذارد. امنیت کامل/pentest ادعا نشده است.
- [ ] commit/push/PR/merge و deploy فقط بعد از تأیید جداگانه؛ brief فعلی آن‌ها را ممنوع کرده است.
