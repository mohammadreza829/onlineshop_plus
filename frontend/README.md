# فرانت مشتریان Online Shop Plus

Next.js App Router + React + TypeScript strict؛ فارسی و RTL. Runtime فقط API واقعی Django را می‌خواند. Fixtureها صرفاً در `tests/` هستند. انتشار کد روی GitHub با تأیید مالک انجام می‌شود؛ این به معنی deploy یا آمادگی انتشار عمومی نیست.

## اجرای لپ‌تاپ با دادهٔ دمو — مسیر پیشنهادی

[راهنمای کامل PowerShell](../docs/laptop-setup.md): بک‌اند با `python manage_laptop.py` از ریشه و فرانت با `npm run dev:local` از همین پوشه. SQLite و تصاویر/secretها در `.local/` جدا هستند؛ Redis، worker و پیامک واقعی لازم نیستند. سید `seed_demo` کاتالوگ ساختگی ۳۶محصولی می‌سازد. این مسیر `.env` موجود را تغییر نمی‌دهد و پرداخت آنلاین را فعال نمی‌کند.

راهنمای `npm run dev` زیر برای تنظیمات دستی توسعه است؛ برای مشکل SMS.ir فعلی، مسیر لپ‌تاپ بالا را انتخاب کنید.

## اجرای توسعه — دو ترمینال لازم است

پیش‌نیاز: Node.js 24 و npm، و بک‌اند Django طبق [README ریشه](../README.md). نصب وابستگی‌ها فقط برای بار اول در **همین پوشه** یا بعد از تغییر dependency/lockfile لازم است؛ برای هر بار اجرا `npm ci` نزنید.

### ترمینال اول: بک‌اند

از ریشهٔ ریپو و پس از نصب Python dependencies و migrate:

```powershell
.\.venv\Scripts\Activate.ps1
python manage.py runserver 127.0.0.1:8000
```

برای توسعهٔ ساده، `.env` **ریشه** باید تنظیمات توسعه داشته باشد: `DJANGO_DEBUG=True`، `DJANGO_DB_ENGINE=sqlite`، `CACHE_URL=`، `SMS_BACKEND=console` و `SMS_ASYNC=False`. از secret محلی تصادفی استفاده کنید و هیچ کلید SMS/درگاه واقعی را برای تست فعال نکنید. تنظیمات موجود production را با این مقادیر بازنویسی نکنید؛ محیط توسعه را جدا کنید. کد OTP توسعه در لاگ Django است؛ آن را در چت/گیت قرار ندهید.

### ترمینال دوم: فرانت

از ریشهٔ ریپو در PowerShell:

```powershell
cd frontend
npm ci
npm run dev
```

برای دفعات بعد فقط `npm run dev` کافی است. صفحه: **http://127.0.0.1:3000**.

`predev` اکنون این سه کار را انجام می‌دهد:

1. `setup:dev`: فقط در توسعه، گزینه‌های مفقود را به `.env.local` اضافه و secret محلی تولید می‌کند؛ انتخاب‌های موجود و فایل‌های env با اولویت بالاتر حفظ می‌شوند. مقدار secret چاپ نمی‌شود. تنظیم نامعتبر موجود را بی‌اجازه عوض نمی‌کند.
2. `prepare:assets`: فونت فارسی، favicon و تصویر سبک hero را محلی تولید می‌کند.
3. `doctor`: origin/secret را بررسی می‌کند و با درخواست **فقط خواندنی**، دسترسی به Django و Redis تنظیم‌شده را گزارش می‌دهد. خاموش‌بودن Django را با تغییر ظاهر یا دادهٔ نمایشی پنهان نمی‌کند.

پیش‌فرض تازهٔ توسعه `APP_ORIGIN=http://127.0.0.1:3000`، `DJANGO_ORIGIN=http://127.0.0.1:8000` و هماهنگ‌کنندهٔ memory **تک‌فرآیندی** است؛ Redis برای این اجرای ساده لازم نیست. اگر `.env.local` قدیمی به Redis اشاره می‌کند، انتخاب شما حفظ می‌شود: یا همان Redis را روشن کنید، یا آگاهانه `BFF_REDIS_URL=` و `BFF_COORDINATION=memory` بگذارید. memory در production ممنوع است.

```powershell
npm run doctor
```

تفاوت `localhost` و `127.0.0.1` مهم است: origin مرورگر باید دقیقاً با `APP_ORIGIN` برابر باشد. اگر پورت را عوض کردید، env را هم هماهنگ و فرانت را restart کنید. `.env.local` و secretها هرگز commit نمی‌شوند.

### اگر نصب یا اجرا خطا داد

- `npm warn deprecated` به‌تنهایی شکست نصب نیست. نتیجهٔ نهایی و exit code مهم‌اند.
- اگر نصب مدت طولانی بدون پیشرفت ماند، `Ctrl+C` و سپس `npm ci --registry=https://registry.npmjs.org --verbose`؛ شبکه/proxy/registry محلی را بررسی کنید. SSL را خاموش و lockfile را حذف نکنید.
- `ENOENT` فونت: نصب در همان پوشه کامل نشده یا با `--ignore-scripts` انجام شده؛ ابتدا نصب را تکمیل، سپس `npm run prepare:assets` بزنید.
- `503`: خروجی doctor، روشن‌بودن Django و آدرس/پورت آن، و Redis قبلاً انتخاب‌شده را بررسی کنید. خالی‌بودن کاتالوگ با قطع سرویس متفاوت است.
- Hydration همراه `data-bidi` و styleهای RTL: این attribute در کد ما نیست. افزونهٔ مرورگر یکی از علت‌های محتمل است؛ در پروفایل بدون افزونه یا پنجرهٔ خصوصی با افزونه‌های غیرفعال امتحان کنید. اگر باقی ماند، stack تازه برای بررسی لازم است. `suppressHydrationWarning` برای مخفی‌کردن مشکل اضافه نشده است.

## بررسی کیفیت و اجرای production

```bash
npm run typecheck
npm run lint
npm test
npm run build
npm audit
```

`npm run start` بیلد production را اجرا می‌کند، نه توسعهٔ memory. پیش از آن طبق [چک‌لیست انتشار](docs/deployment-checklist.md)، origin HTTPS واقعی، secret و Redis مشترک و host درگاه واقعی را صریح تنظیم کنید. هیچ fallback خودکار توسعه در production فعال نمی‌شود.

تست Redis واقعی بدون URL آن یک skip دارد:

```bash
REDIS_QA_URL=redis://127.0.0.1:6379/6 npm test
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

`npm ci` با postinstall شش فونت محلی را از package قفل‌شدهٔ Vazirmatn و favicon خنثی را تولید می‌کند؛ `predev` و `prebuild` نیز همین مرحله را اجرا می‌کنند. binaryها در Git commit نمی‌شوند، اما بعد از نصب در `public/` ساخته می‌شوند و با نسخهٔ QA یکسان‌اند. اگر install scriptها را عمداً خاموش کرده‌اید، `npm run prepare:assets` را پیش از اجرا بزنید. تصویر hero از `assets/editorial-home.webp.b64` بازسازی می‌شود؛ تصویر تزئینی تولیدشده با AI است و محصول کاتالوگ نیست. فونت لاتین از system fallback استفاده می‌کند تا دانلود اضافه نداشته باشد. هیچ CDN runtime لازم نیست.

## بازطراحی مدرن

نسخهٔ تازه: [راهنمای Immersive و محدودهٔ تست](docs/immersive-redesign.md). GSAP برای انیمیشن ورود، reveal، parallax و دکمهٔ مغناطیسی به‌صورت lazy فعال است؛ Lenis فقط روی دسکتاپ با اشاره‌گر دقیق در خانه و محصولات فعال می‌شود. فرم‌ها، خرید، حساب، موبایل و reduced-motion اسکرول native دارند. Radix مسئول focus trap و scroll lock پنل‌هاست. [گزارش نسخهٔ قبلی](docs/redesign-validation.md) مربوط به بازطراحی قبلی است، نه نتیجهٔ تست این نسخه.
