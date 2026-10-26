> **یادداشت نسخهٔ بصری جدید:** این گزارش، سابقهٔ پیاده‌سازی فرانت اولیه است. جزئیات بازطراحی Spatial Atelier، موتور WebGL، نسخه‌های وصله‌شده و QA جدید در `frontend/docs/spatial-redesign.md` آمده‌اند؛ عددهای QA زیر تاریخی‌اند، نه نتیجهٔ اجرای جدید.

# گزارش پیاده‌سازی فرانت مشتریان

## ۱. وضعیت واقعی و محدوده

فرانت در `frontend/` پیاده‌سازی شده و به API واقعی Django این پروژه متصل است؛ runtime هیچ mock دائمی ندارد. تحویل اولیه **محلی و بدون commit/push/deploy** بود. مالک سپس انتشار کد در GitHub و commit/push را صریحاً تأیید کرد؛ بخش انتشار زیر مربوط به این تأیید جدید است. استقرار production انجام نشده است. منطق قیمت، موجودی، سفارش، کوپن، پرداخت، مدل‌ها، migrations و callback در این فاز تغییر نکرده‌اند. Django Admin بازطراحی نشده است.

### مبنای ریپو و اختلاف snapshot

Snapshot رایانه در ابتدای کار، branch قدیمی فاز ۴ بود؛ main روی GitHub با SHA `9ec4e3730bf1c06027e7ec013d5b8e6abca1d38d` تأیید شد. fetch مستقیم private repo بدون احراز هویت قابل استفاده نبود. تغییرات ازقبل‌mergeشدهٔ PRهای ۶ و ۷ خوانده و **بدون commit و staging** در working tree بازیابی شدند؛ tree مبنا `249ac30ff8408560b692efd1cdb3b78a28e8eb64` بود. branch محلی کار `frontend/customer-storefront` است و HEAD محلی قدیمی حفظ شده است. بنابراین `git diff HEAD` به‌تنهایی محدودهٔ این فاز نیست و ممکن است backend قبلاً‌mergeشده را نیز نمایش دهد. مقایسه با index مبنای main نشان داد تغییر جدید tracked صرفاً `.dockerignore` و مستندات ریشه است؛ frontend جدید است. هیچ تغییر قبلی کاربر reset یا حذف نشد.

`.dockerignore` فقط cache/build/node_modules/envهای فرانت را از context image بک‌اند بیرون می‌گذارد. این تغییر منطق backend نیست.

## ۲. بخش‌های پیاده‌سازی‌شده

| بخش                | رفتار واقعی                                                                                                                                                                     |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/`                | hero تایپوگرافیک بدون عکس نامعتبر، CTA، دسته‌ها و تازه‌ترین محصولات واقعی؛ GSAP/ScrollTrigger و Lenis انتخابی فقط desktop precision pointer، بدون pin؛ cleanup و reduced-motion |
| `/products`        | search/category/stock/base price/order/pagination واقعی؛ query در URL، back/reload، cancellation پاسخ قدیمی؛ filter drawer موبایل                                               |
| `/products/[slug]` | جزئیات، گالری واقعی/placeholder خنثی، variant رنگ و سایز معتبر، ناموجود، قیمت انتخاب واقعی، quantity، افزودن سبد، علاقه‌مندی، توضیحات plaintext امن، review واقعی و pending     |
| `/cart`            | هویت `product_id + variant_id`، quantity با PATCH مطلق واقعی (نه add)، حذف خط درست، totals سرور، reload session؛ رنگ/سایز از detail عمومی با تطبیق ID دقیق                      |
| `/login`           | فرم RHF/Zod، تبدیل اعداد فارسی/عربی، phone/OTP، timer و Retry-After، جلوگیری از verify تکراری و redirect داخلی allowlisted                                                      |
| `/checkout`        | login gate، آدرس واقعی، coupon فقط هنگام create، totals پاسخ سفارش، lock دوبارکلیک، marker بازیابی پیش از ارسال، عدم retry خودکار درخواست مالی یا سفارش مبهم                    |
| `/payment/result`  | سفارش متعلق به صاحب JWT، پرداخت ثبت‌شده/تأییدنشده/منقضی/لغوشده/needs_review؛ URL درگاه از POST واقعی و HTTPS host allowlist؛ query Status مرجع نیست                             |
| `/account/*`       | پروفایل، CRUD آدرس با استان‌های پشتیبانی‌شده، orders/detail/timeline، favorites و read notifications واقعی؛ reset private cache هنگام خروج و پیام بین تب‌ها                     |
| خطاها              | error boundary، not-found واقعی مسیر و محصول، بررسی owner-order برای 404، loading/empty/error/retry کنترل‌شده                                                                   |
| SEO                | metadata، canonical مشروط به SITE_URL واقعی، sitemap/robots/noindex خصوصی، JSON-LD با داده واقعی؛ مبلغ تومان در structured data به IRR ×۱۰؛ rating ساختگی ندارد                 |

جدول سایز، سیاست فروش، شماره تماس، تضمین، ارسال رایگان، دسته‌های ساختگی و محصول نمایشی production ساخته نشده‌اند. آیکون تب یک نماد خنثی لباس است، نه لوگوی تأییدشدهٔ برند.

## ۳. معماری، امنیت و فایل‌های اصلی

- `app/`: App Router با Server Components مناسب، صفحات و route handlers؛ private payload در cache عمومی/static مشترک قرار نمی‌گیرد.
- `features/`: catalog/product/cart/auth/checkout/account، جدا از layout و primitives.
- `lib/api/`: client، types، errors، hooks و read server-only.
- `lib/auth/routes.ts`: allowlist دقیق مسیر، method و query؛ staff/proxy arbitrary URL وجود ندارد.
- `lib/auth/bff.ts`: upstream ثابت env، timeout/حد body، JSON خطای کنترل‌شده، no-store؛ OTP/JWT از browser response حذف می‌شوند.
- `lib/auth/crypto.ts`: کوکی‌های auth/session رمز‌شده AES-GCM، CSRF امضاشده، مقایسهٔ ثابت‌زمانی.
- `lib/auth/coordination.ts`: Redis shared single-flight refresh، cache کوتاه جفت token رمز‌شده و tombstone logout؛ memory تنها dev تک‌فرآیندی.
- access/refresh/sid HttpOnly، host-only، SameSite=Lax، Secure و `__Host-` روی HTTPS. expiry از JWT سرور با سقف قراردادی؛ token در local/sessionStorage، HTML، query یا log قرار نمی‌گیرد.
- mutationها Origin دقیق و signed CSRF double-submit می‌خواهند. CSRF معتبر موجود بین تب‌ها حفظ می‌شود. Django CSRF globally خاموش نشده است.
- Django session سبد در cookie جدا و رمز‌شده حفظ می‌شود؛ چند Set-Cookie مستقل parse می‌شوند. auth جای session cart نیست. Bearer برای protected routes است؛ public cart با token منقضی گیر نمی‌کند.
- refresh پیشگیرانه و هماهنگ؛ GET پس از 401 حداکثر یک retry، mutation مالی replay نمی‌شود. 5xx refresh کوکی را کورکورانه پاک نمی‌کند؛ invalid refresh logout می‌دهد.
- logout قفل مشترک، blacklist refresh موجود و پاک‌سازی browser/cache دارد. در outage پاک‌شدن browser cookie تضمین revocation سمت سرور نیست.
- `app/api/media/[...path]/route.ts`: تنها raster/media روی origin ثابت، مسیر امن، content-type، سقف ۵MB، timeout و عدم دنبال‌کردن redirect؛ CDN فقط hostnameهای صریح `PRODUCT_IMAGE_HOSTS`.
- `config/site.ts` و `app/globals.css`: تنظیم عمومی، tokens، self-host Vazirmatn/OFL؛ muted برای AA به `#65625D` تنظیم شده است.
- `lib/motion/home-motion.tsx` loader سبک؛ `home-effects.tsx` فقط در دستگاه واجد شرایط بارگذاری می‌شود. Motion برای تعاملات، GSAP تنها hero، native scroll خرید/موبایل؛ یک GSAP ticker برای Lenis.
- `tests/unit/`, `tests/e2e/`, `tests/django_harness.py`: fixture فقط QA و جدای runtime؛ `README.md`، `.env.example` و `docs/` داخل frontend دستورها/انتشار/مجوزها.

CSP originها را محدود می‌کند، اما inline script/style مورد نیاز Next مجاز است؛ این پیاده‌سازی به معنی pentest یا تضمین نبود آسیب‌پذیری نیست.

## ۴. نصب و اجرای محلی

از README ریشه، Django را در محیط توسعه آماده کنید؛ هرگز env پیامک یا پرداخت واقعی را برای تست فعال نکنید. سپس:

```bash
cd frontend
npm ci
cp .env.example .env.local
# تنظیم APP_ORIGIN / DJANGO_ORIGIN / Redis و secret محلی طبق README همین پوشه
npm run dev
```

دستور امن تولید secret در `frontend/README.md` است و مستقیم فایل محلی را ویرایش می‌کند؛ secret در این گزارش وجود ندارد. `APP_ORIGIN` باید دقیقاً با origin مرورگر برابر باشد. دستورهای build، تست Redis و E2E ایزوله به‌طور کامل در همان README آمده‌اند.

نسخه‌های قفل‌شدهٔ اصلی: Next 16.4.0، React 19.3.0، TypeScript 6.0.3، Tailwind 4.3.3، Motion 14.2.0، GSAP 3.15.0، Lenis 1.3.26، TanStack Query 5.104.2، RHF 7.90.0، Zod 4.6.7، Playwright 1.64.0 و Vitest 5.0.4؛ محیط Node 24 و npm 11. نسخه canary به کار نرفته و `package-lock.json` موجود است.

TypeScript 7 با ابزار ESLint انتخاب‌شده سازگار نبود؛ stable 6 استفاده شد. مسیر dependency مربوط به eslint-config-next در audit به braces آسیب‌پذیر می‌رسید؛ downgrade ناسازگار Next یا audit-force انجام نشد. به‌جای آن ESLint 9 با typescript-eslint، react-hooks و jsx-a11y recommended استفاده شد؛ lint بدون خاموش‌کردن عمومی ruleها پاس شد.

## ۵. نتیجهٔ واقعی QA

- production build، typecheck strict و ESLint اجرا و موفق شدند؛ آخرین source/test edits دوباره typecheck/lint شدند.
- **۵۶ تست unit/integration موفق، بدون skip در اجرای دارای Redis واقعی**: BFF ۲۷، قرارداد/فرمت ۲۶، SEO ۲ و coordinator Redis یک تست. بدون `REDIS_QA_URL` همان تست Redis skip می‌شود.
- **۲۰ آزمون Chromium Playwright موفق**: یک journey با backend واقعی محلی + ۱۹ آزمون UI/state/a11y با mock کنترل‌شده. این اعداد تست mock را integration واقعی معرفی نمی‌کنند.
- regression backend: **۱۹۹ تست کشف‌شده، ۱۸۹ موفق و ۱۰ skip روی SQLite**. تست‌های PostgreSQL/concurrency در این نوبت اجرا نشدند.
- `npm audit` همهٔ dependencyها و runtime: **صفر آسیب‌پذیری گزارش‌شده در زمان اجرا**؛ این تضمین امنیت آینده نیست.
- harness جدید `ruff check` پاس؛ تست‌های مالی/OTP ایزوله و بدون ارسال خارجی.
- ۳۷ capture برای ۱۶ route در desktop/mobile و عرض‌های 360/390/768/1024/1440 و overlayها؛ هر تصویر جداگانه بررسی شد. اصلاحات checkout، active account nav و filter capture مجدداً render و بررسی شدند. در captureهای نهاییِ بررسی‌شده page overflow یا pageerror مشاهده نشد. clip ناحیهٔ scrollable تب‌ها به معنی overflow صفحه نیست.
- axe در scope آزمون مرورگر پاس شد؛ این جای تست screen-reader انسانی را نمی‌گیرد. Escape، بازگشت focus، منو، dialog، reduced motion و scroll lock در تست‌های مرورگر پوشش دارند.

### جریان واقعی Django

Django روی loopback 8100 با SQLite موقت و business logic موجود، Next production build روی loopback 3100 و Redis واقعی هماهنگی BFF روی port 6381 اجرا شدند. دو variant یک محصول → دو خط مستقل → حذف درست → حفظ cookie بعد reload → OTP واقعی backend با transport/randomness تست → آدرس → coupon نامعتبر/معتبر → یک create با double click → شروع پرداخت → FakeGateway → callback موجود Django حتی با Status=NOK → paid سفارش → حفظ سبد → refresh واقعی پس از حذف access cookie اجرا شد.

فقط randomness/ارسال OTP و provider درگاه test double هستند؛ JWT، rotation/blacklist، session/cart، validation، order/coupon/reservation و callback منطق واقعی Django بودند. دیتابیس QA و نرخ‌های بالا production نیستند. هیچ SMS یا تماس بانک/زرین‌پال واقعی انجام نشد. آزمون تکراری به‌خاطر آدرس fixture تکراری اصلاح شد و دادهٔ هر run مستقل شد. خطای موقت chunk در rebuild به سرور تستِ قدیمی مربوط بود؛ سرور با build جدید restart و suite نهایی دوباره اجرا شد. اجرای نهایی ۲۰ تست پاس شد و نتیجه در qa-results ثبت شده است.

### کارایی محلی

نتیجهٔ نهایی Lighthouse: Performance **۹۱**، Accessibility **۱۰۰**، Best Practices **۱۰۰**، SEO **۱۰۰**؛ **LCP ۳٫۳ ثانیه، CLS صفر و TBT ۱۳۰ms**. CLS به هدف رسیده، اما **هدف LCP≤2.5s هنوز محقق نشده**؛ این مورد قبل انتشار روی کاتالوگ/تصاویر واقعی و شبکهٔ staging نیازمند بررسی و بهینه‌سازی بیشتر است. شرایط کامل در `frontend/docs/qa-results.json` ثبت شده است. معیار mobile simulated Lighthouse با CPU×۴، RTT 150ms، throughput 1638.4Kbps و viewport 412×823 روی localhost و دو محصول ایزوله است؛ نه آمار کاربران واقعی، کاتالوگ پُر یا production. CLS ناشی از shell بارگذاری/فونت اصلاح شد و فونت self-host preload می‌شود. هدف LCP≤2.5s و CLS≤0.1 فقط در صورت رسیدن در اندازه‌گیری گزارش می‌شود، نه با حدس یا تغییر مصنوعی شرایط تست.

## ۶. موارد اجرا‌نشده و محدودیت‌های دقیق

1. **callback یکپارچه هنوز انجام نشده:** callback HTML و legacy Django حفظ شدند. `/payment/result` صرفاً وضعیت سفارش owner را می‌خواند؛ redirect خودکار callback به Next اضافه نشده است. تغییر محدود backend نیازمند تأیید است.
2. **IP/throttle production:** Next→Django یک اتصال server-to-server است؛ طراحی IP trusted و throttle چند مشتری باید قبل انتشار حل شود. forward کردن header جعلی مرورگر راه‌حل نیست. نرخ‌های بالا در harness هیچ اثباتی برای production نیست.
3. **origin callback عمومی:** Django با origin داخلی ممکن است callback غیرقابل دسترس درگاه بسازد؛ public URL/proxy/config واقعی لازم است.
4. **پاک‌سازی اتمیک سبد:** پس از paid، سبد خودکار پاک نمی‌شود تا اقلام جدید از بین نروند؛ بررسی و حذف صریح وجود دارد. endpoint شرطی برای cleanup صرفاً اقلام پرداخت‌شده در برابر تغییر سبد موجود نیست.
5. **اطلاعات cart/list:** cart snapshot رنگ/سایز/slug ندارد؛ detail عمومی با ID دقیق استفاده می‌شود. نام تغییرکرده/غیرفعال یا بیش از ۱۰۰ match ممکن است resolve نشود؛ پیام شفاف جای label خیالی است. list تصویر thumbnail ندارد و detail محدود per-card گرفته می‌شود؛ بهبود serializer نیازمند تأیید backend است.
6. **پرداخت unknown/failed تفصیلی:** API سفارش وضعیت transaction کامل را برنمی‌گرداند. pending «تأیید ثبت نشده» نمایش می‌دهد؛ نه «قطعاً ناموفق». needs_review و paid_at از status fulfillment جدا هستند.
7. **review eligibility:** فرم توضیح می‌دهد eligibility فقط توسط server کنترل می‌شود و ثبت/ویرایش دوباره pending است؛ backend خریدار غیرمجاز را رد می‌کند. endpoint eligibility پیشینی جدا وجود ندارد؛ UI نباید خرید نکرده را واجد شرایط معرفی کند.
8. PostgreSQL integration این نوبت، Firefox/WebKit/iOS/Android واقعی، screen-reader انسانی، چند replica در staging و crash/recovery گسترده، تصاویر واقعی production، تست live/sandbox provider بیرونی، penetration test و deployment اجرا نشده‌اند.
9. sitemap برای هر resource سقف ایمنی ۱۰۰ صفحه دارد؛ کاتالوگ بزرگ‌تر یا fetch/rate failure می‌تواند coverage ناقص بدهد. قبل انتشار اندازهٔ واقعی را بررسی کنید.
10. درخواست مالی ambiguous replay نمی‌شود؛ marker در sessionStorage فقط زمان/شناسه است، نه PII/token. بررسی دستی سفارش پیش از آغاز دوباره لازم است؛ سمت سرور idempotency key جدید اختراع نشده است.

## ۷. ورودی‌ها و تأییدهای لازم پیش از انتشار

- برند/دامنهٔ نهایی، تصاویر واقعی و محتوای مجاز؛ policies فروش/مرجوعی/حریم خصوصی/تماس تأییدشده، نه متن اختراعی.
- تنظیم SMS، gateway محیط انتخاب‌شده و secretها از کانال امن؛ هیچ credential در chat یا فایل source قرار نگیرد.
- public origin/proxy، Redis مشترک، نرخ/IP معتبر، TLS و jobهای expiry/reconcile موجود.
- تأیید مشخص برای اتصال محدود callback به storefront؛ تصمیم approved دربارهٔ trusted client-IP. پاک‌سازی خودکار سبد و بهبود serializer فقط اگر خواسته و تأیید شوند.
- commit/push/merge مجوز جدا می‌خواهد؛ این brief آن‌ها را ممنوع کرده است.

چک‌لیست اجرایی: `frontend/docs/deployment-checklist.md`. **کد نوشته‌شده + mock پاس‌شده + integration محلی، مساوی آماده‌بودن انتشار عمومی نیست.**

## ۸. شواهد و تحویل

`frontend/docs/qa-results.json` خلاصهٔ ماشینی آخرین اجراست؛ فایل‌های source و lockfile در پوشهٔ frontend قرار دارند. Screenshots فقط fixture ایزوله هستند و داده/موجودی واقعی فروشگاه را نشان نمی‌دهند. بستهٔ تحویل هیچ `.env.local`، cookie، DB، node_modules یا build cache ندارد. patch مستندات و `.dockerignore` نسبت به main تأییدشده جداست؛ backend قدیمی دوباره به بسته افزوده نمی‌شود.

## ۹. آماده‌سازی انتشار در GitHub با تأیید جدید مالک

مالک پس از تحویل اولیه commit/push فرانت را تأیید کرد. فقط frontend، گزارش و تغییر مرتبط README/.dockerignore ارسال می‌شوند؛ backend، migration و env واقعی در این تغییر نیستند. transport متنی GitHub برای binary مناسب نیست؛ بنابراین `scripts/prepare-assets.mjs` با postinstall/predev/prebuild، شش WOFF2 از dependency قفل‌شده و favicon محلی یکسان را بازتولید می‌کند. بازتولید دارایی‌ها با مقایسهٔ hash بررسی شده؛ install script اینترنت یا CDN استفاده نمی‌کند. QA عددهای این گزارش مربوط به اجرای محلی ثبت‌شده است؛ GitHub CI صرفاً پس از بررسی نتیجهٔ واقعی قابل ادعاست.
