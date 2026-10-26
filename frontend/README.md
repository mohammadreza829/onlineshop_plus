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

**callback درگاه همچنان صفحهٔ Django است.** داشتن `/payment/result` به معنی اتصال خودکار callback به Next نیست. با مرور سفارش همان حساب می‌توان نتیجهٔ تأییدشده را دید. برای یکپارچه‌سازی callback، تغییر محدود بک‌اند نیازمند تأیید صاحب پروژه است.

## دارایی‌های قابل بازتولید

`npm ci` با postinstall شش فونت محلی را از package قفل‌شدهٔ Vazirmatn و favicon خنثی را تولید می‌کند؛ `predev` و `prebuild` نیز همین مرحله را اجرا می‌کنند. binaryها در Git commit نمی‌شوند، اما بعد از نصب در `public/` ساخته می‌شوند و با نسخهٔ QA یکسان‌اند. اگر install scriptها را عمداً خاموش کرده‌اید، `npm run prepare:assets` را پیش از اجرا بزنید. هیچ CDN runtime لازم نیست.


## بازطراحی Spatial Atelier

ظاهر سراسری و شوروم واقعی WebGL در `features/showroom/` قرار دارند؛ Next پوستهٔ BFF/مسیرهاست و Three.js/R3F موتور سه‌بعدی. مدل صرفاً مطالعهٔ فرم پارچه است، نه نمایش ۳۶۰ محصول واقعی. رنگ‌ها و عمق اجزا از همان tokenهای `app/globals.css` می‌آیند. راهنمای تصمیم‌ها: `design-system/onlineshop-plus/MASTER.md`؛ نتیجهٔ آخرین تست‌ها و محدودیت‌ها: `docs/spatial-redesign.md`.

`npm ci` / `prepare:assets` مدل محلی و تصویر جایگزین را از منبع متنی با SHA-256 تأییدشده بازتولید می‌کنند؛ build به CDN، کلید 21st یا دریافت مدل بیرونی نیاز ندارد. Binaryهای تولیدشده را جدا commit نکنید. برای نمایش محصولات واقعیِ قابل چرخش، GLB تأییدشدهٔ همان محصول لازم است.
