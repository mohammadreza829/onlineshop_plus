# فرانت مشتریان Online Shop Plus

Next.js App Router + React + TypeScript strict؛ فارسی و RTL. Runtime فقط API واقعی Django را می‌خواند. Fixtureها صرفاً در `tests/` هستند. انتشار کد روی GitHub با تأیید مالک انجام می‌شود؛ این به معنی deploy یا آمادگی انتشار عمومی نیست.

## اجرای توسعه

پیش‌نیاز: Node.js 24 (نسخهٔ بررسی‌شده)، npm، Django همین ریپو طبق README ریشه، Redis قابل دسترس برای BFF.

```bash
cd frontend
npm ci
cp .env.example .env.local
```

در `.env.local`، `APP_ORIGIN` را دقیقاً برابر origin مرورگر و `DJANGO_ORIGIN` را برابر origin ثابت Django قرار دهید. `BFF_COOKIE_SECRET` را با دستور زیر **فقط در فایل محلی** تولید کنید؛ خروجی را ارسال یا commit نکنید:

```bash
node -e "const fs=require('fs'),c=require('crypto');const p='.env.local';fs.writeFileSync(p,fs.readFileSync(p,'utf8').replace(/^BFF_COOKIE_SECRET=.*$/m,'BFF_COOKIE_SECRET='+c.randomBytes(48).toString('base64url')))"
npm run dev
```

مرورگر: `http://localhost:3000`. تفاوت `localhost` و `127.0.0.1` در Origin مهم است. مقدار `.env.example` برای همین URL است. درگاه را به محیط واقعی انتخاب‌شده تنظیم کنید؛ default مثال sandbox است. SMS/پرداخت واقعی را برای بررسی توسعه فعال نکنید.

توسعهٔ تک‌فرآیندی فقط: اگر Redis ندارید، `BFF_REDIS_URL` را خالی و `BFF_COORDINATION=memory` تنظیم کنید. این حالت در build production مجاز نیست. استقرار چندفرآیندی به Redis مشترک و secret مشترک نیاز دارد.

```bash
npm run typecheck
npm run lint
npm run test
npm run build
npm run start
npm audit
```

تست Redis واقعی اختیاری است و بدون URL آن، یک تست skip می‌شود:

```bash
REDIS_QA_URL=redis://127.0.0.1:6379/6 npm run test
```

## برگشت پرداخت و خطای درخواست امن

در `.env` **ریشهٔ Django**، مقدار زیر باید دقیقاً با `APP_ORIGIN` در `frontend/.env.local` برابر باشد (بدون اسلش آخر):

```dotenv
FRONTEND_ORIGIN=http://localhost:3000
```

در production مقدار HTTPS واقعی لازم است. در توسعه default همین `localhost:3000` است؛ در استقرار مستقل legacy، خالی‌بودن آن قالب‌های قدیمی را حفظ می‌کند. API پرداخت از callback جداگانهٔ `/payment/storefront/verify/` استفاده می‌کند: ابتدا verify سرور، سپس redirect به `/payment/result?order=ID`. وضعیت/مبلغ فقط از API متعلق به کاربر خوانده می‌شود؛ `Status=OK` اثبات پرداخت نیست. هیچ URL بازگشت دلخواه از مرورگر پذیرفته نمی‌شود. callbackهای پرداخت‌هایی که **پیش از این اصلاح** شروع شده‌اند، عوض نمی‌شوند؛ آنها را دوباره پرداخت نکنید و از سفارش‌های حساب بررسی کنید.

توکن CSRF منقضی‌شده/جایگزین‌شده فقط پس از پاسخ صریح BFF مبنی بر رد درخواست **پیش از ارسال به Django** یک بار بازیابی می‌شود. خطای شبکه، خطای upstream، origin متفاوت و عملیات مبهم خودکار تکرار نمی‌شوند. در توسعه، تفاوت `localhost`/`127.0.0.1` فقط روی همان پورت، پیش از mount مصرف‌کنندگان API با ناوبری کامل مرورگر به `APP_ORIGIN` اصلاح می‌شود؛ CSRF و کنترل Origin همچنان فعال‌اند. پورت متفاوت را حدس نمی‌زنیم.

برای مشاهدهٔ OTP در ترمینال قابل اعتماد خودتان، فقط در توسعهٔ محلی `DJANGO_DEBUG=True`، `SMS_BACKEND=console`، `SMS_ASYNC=False` و `SMS_CONSOLE_SHOW_OTP=True` را در محیط Django تنظیم کنید. کد با برچسب `[local development OTP]` و بدون شماره چاپ می‌شود؛ فیلتر JSON بقیهٔ لاگ‌ها دست‌نخورده است. این گزینه پیش‌فرض خاموش است و با DEBUG=False اجازهٔ شروع برنامه نمی‌دهد؛ آن را روی سرور عمومی/مشترک فعال نکنید.

پس از تغییر `.env` یا `.env.local` هر دو سرور را restart کنید. `BFF_COOKIE_SECRET` را با هر اجرا عوض نکنید؛ یک کلید محلی ثابت و محرمانه نگه دارید.

## تست مرورگر ایزوله (نه production)

ابتدا وابستگی‌های Python ریشه را نصب کنید. Redis تست را جدا از دادهٔ production اجرا کنید. `tests/django_harness.py` دیتابیس SQLite موقت می‌سازد؛ OTP transport، randomness و درگاه فقط در process تست جایگزین می‌شوند. هرگز این harness را روی اینترنت expose نکنید.

ترمینال اول، از ریشهٔ ریپو:

```bash
python frontend/tests/django_harness.py
```

در `.env.local` برای اجرای QA فقط:

```dotenv
APP_ORIGIN=http://127.0.0.1:3100
DJANGO_ORIGIN=http://127.0.0.1:8100
BFF_REDIS_URL=redis://127.0.0.1:6379/5
PAYMENT_HOSTS=gw.test
BFF_LOCAL_HTTP=1
```

Secret واقعی محلی را حفظ کنید. `gw.test` و `BFF_LOCAL_HTTP` مخصوص این تست هستند؛ در production ممنوع‌اند. در ترمینال دوم:

```bash
cd frontend
npm ci
npm run build
npm run start -- --port 3100
```

ترمینال سوم:

```bash
cd frontend
npm run test:e2e
```

Playwright از Chromium نصب‌شده استفاده می‌کند (`CHROMIUM_PATH` برای مسیر متفاوت). در نبود مرورگر، `npx playwright install chromium` را در محیط مجاز اجرا کنید. این suite شامل یک journey واقعی Django و آزمون‌های UI با mock است؛ روی بک‌اند/حساب واقعی اجرا نکنید. پس از اتمام، processهای QA را متوقف کنید. QA throttle بالا و OTP ثابت، رفتار production نیست.

## محل تنظیم و مستندات

- نام/متن عمومی: `config/site.ts`؛ رنگ‌ها: `app/globals.css`.
- امنیت/refresh/session: `lib/auth/`؛ مسیرهای BFF: `app/api/shop/[...path]/route.ts`.
- گزارش دقیق و محدودیت‌ها: [`../FRONTEND_IMPLEMENTATION.md`](../FRONTEND_IMPLEMENTATION.md).
- انتشار: [`docs/deployment-checklist.md`](docs/deployment-checklist.md).
- مجوزها: [`docs/licenses.md`](docs/licenses.md).

**callback پرداخت API به storefront متصل شده است.** بخش «برگشت پرداخت و خطای درخواست امن» و `docs/routing-security-fix.md` را ببینید. مسیرهای legacy برای سازگاری حفظ شده‌اند؛ تنظیم `FRONTEND_ORIGIN` و قابل‌دسترسی‌بودن callback عمومی درگاه برای استقرار واقعی همچنان لازم‌اند.

## دارایی‌های قابل بازتولید

`npm ci` با postinstall شش فونت محلی را از package قفل‌شدهٔ Vazirmatn و favicon خنثی را تولید می‌کند؛ `predev` و `prebuild` نیز همین مرحله را اجرا می‌کنند. binaryها در Git commit نمی‌شوند، اما بعد از نصب در `public/` ساخته می‌شوند و با نسخهٔ QA یکسان‌اند. اگر install scriptها را عمداً خاموش کرده‌اید، `npm run prepare:assets` را پیش از اجرا بزنید. هیچ CDN runtime لازم نیست.


## بازطراحی Spatial Atelier

ظاهر سراسری و شوروم واقعی WebGL در `features/showroom/` قرار دارند؛ Next پوستهٔ BFF/مسیرهاست و Three.js/R3F موتور سه‌بعدی. مدل صرفاً مطالعهٔ فرم پارچه است، نه نمایش ۳۶۰ محصول واقعی. رنگ‌ها و عمق اجزا از همان tokenهای `app/globals.css` می‌آیند. راهنمای تصمیم‌ها: `design-system/onlineshop-plus/MASTER.md`؛ نتیجهٔ آخرین تست‌ها و محدودیت‌ها: `docs/spatial-redesign.md`.

`npm ci` / `prepare:assets` مدل محلی و تصویر جایگزین را از منبع متنی با SHA-256 تأییدشده بازتولید می‌کنند؛ build به CDN، کلید 21st یا دریافت مدل بیرونی نیاز ندارد. Binaryهای تولیدشده را جدا commit نکنید. برای نمایش محصولات واقعیِ قابل چرخش، GLB تأییدشدهٔ همان محصول لازم است.
