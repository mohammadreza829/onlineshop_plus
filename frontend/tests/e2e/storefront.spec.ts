import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mockAPI, product, order, pageOf, address, cart } from "./fixtures";

test("real local Django journey: two variants, cookies, OTP, address, coupon, order and verified callback", async ({
  page,
  context,
  request,
}) => {
  const phone = "0912" + String(Date.now()).slice(-7);
  const persianPhone = phone.replace(/\d/g, (d) => "۰۱۲۳۴۵۶۷۸۹"[Number(d)]);
  const addressTitle = "خانهٔ تست " + Date.now();
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/products/qa-variant");
  await expect(
    page.getByRole("heading", { name: product.name, exact: true }),
  ).toBeVisible();
  const add = page.getByRole("button", { name: "افزودن به سبد", exact: true });
  await expect(add).toBeDisabled();
  await page.getByRole("button", { name: "مشکی", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "L — ناموجود", exact: true }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "M", exact: true }).click();
  await add.click();
  await expect(
    page.getByText("انتخاب شما به سبد اضافه شد.", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: "کرم", exact: true }).click();
  await page.getByRole("button", { name: "L", exact: true }).click();
  await add.click();
  await page.goto("/cart");
  await expect(page.locator(".cart-line")).toHaveCount(2);
  await expect(page.getByText("رنگ: مشکی / سایز: M")).toBeVisible();
  await page.reload();
  await expect(page.locator(".cart-line")).toHaveCount(2);
  await page
    .getByRole("button", { name: "حذف پیراهن تست متنوع مشکی M", exact: true })
    .click();
  await expect(page.locator(".cart-line")).toHaveCount(1);
  await page.getByRole("link", { name: "ادامهٔ خرید", exact: true }).click();
  await page.getByRole("link", { name: "ورود به حساب", exact: true }).click();
  await page.getByLabel("شمارهٔ همراه", { exact: true }).fill(persianPhone);
  await page
    .getByRole("button", { name: "دریافت کد تایید", exact: true })
    .click();
  await page.getByLabel("کد تایید شش‌رقمی").fill("۱۲۳۴۵۶");
  await page.getByRole("button", { name: "تایید و ورود", exact: true }).click();
  await expect(page).toHaveURL(/\/checkout/);
  await page.getByRole("button", { name: "آدرس جدید", exact: true }).click();
  await page.getByLabel("عنوان آدرس", { exact: true }).fill(addressTitle);
  await page.getByLabel("نام تحویل‌گیرنده", { exact: true }).fill("گیرنده تست");
  await page
    .getByLabel("شمارهٔ تحویل‌گیرنده", { exact: true })
    .fill(persianPhone);
  await page.getByLabel("شهر", { exact: true }).fill("تهران");
  await page.getByLabel("کد پستی", { exact: true }).fill("۱۲۳۴۵۶۷۸۹۰");
  await page
    .getByRole("combobox", { name: "استان", exact: true })
    .selectOption("tehran");
  await page
    .getByLabel("نشانی دقیق", { exact: true })
    .fill("نشانی فقط برای تست ایزوله");
  await page.getByRole("button", { name: "ذخیرهٔ آدرس", exact: true }).click();
  await page.getByRole("radio", { name: addressTitle }).check();
  await page.getByLabel("کد تخفیف (اختیاری)").fill("INVALID");
  await page
    .getByRole("button", { name: "ثبت سفارش و رزرو", exact: true })
    .click();
  await expect(page.locator(".notice[role=alert]")).toBeVisible();
  await page.getByLabel("کد تخفیف (اختیاری)").fill("QA10");
  let checkouts = 0;
  page.on("request", (r) => {
    if (r.url().includes("/api/shop/orders/create/")) checkouts++;
  });
  await page
    .getByRole("button", { name: "ثبت سفارش و رزرو", exact: true })
    .click({ clickCount: 2 });
  await expect(page).toHaveURL(/payment\/result\?order=/);
  expect(checkouts).toBe(1);
  await expect(page.getByText("تخفیف کوپن:", { exact: false })).toBeVisible();
  const orderId = new URL(page.url()).searchParams.get("order");
  let authority = "";
  await page.route("https://gw.test/**", async (route) => {
    authority = new URL(route.request().url()).pathname.split("/").at(-1) ?? "";
    await route.fulfill({
      contentType: "text/html",
      body: "<html><body>Isolated gateway test double</body></html>",
    });
  });
  await page
    .getByRole("button", { name: "دریافت نشانی درگاه و پرداخت", exact: true })
    .click();
  await expect(page).toHaveURL(/gw\.test/);
  const callback = await request.get(
    "http://127.0.0.1:8100/payment/verify/?Authority=" +
      authority +
      "&Status=NOK",
  );
  expect(callback.ok()).toBe(true);
  await page.goto("/payment/result?order=" + orderId);
  await expect(
    page.getByRole("heading", { name: "پرداخت در سرور ثبت شده است." }),
  ).toBeVisible();
  await expect(
    page.getByText("سبد خودکار پاک نشده است", { exact: false }),
  ).toBeVisible();
  await page.goto("/cart");
  await expect(page.locator(".cart-line")).toHaveCount(1);
  const before = (await context.cookies()).find((c) =>
    c.name.endsWith("refresh"),
  )?.value;
  await context.clearCookies({ name: /access$/ });
  await page.goto("/account/profile");
  await expect(
    page.getByRole("heading", { name: "مشخصات من", exact: true }),
  ).toBeVisible();
  const after = (await context.cookies()).find((c) =>
    c.name.endsWith("refresh"),
  )?.value;
  expect(Boolean(before && after && before !== after)).toBe(true);
  const cookies = await context.cookies();
  const auth = cookies.filter(
    (c) => c.name.includes("access") || c.name.includes("refresh"),
  );
  expect(auth).toHaveLength(2);
  expect(auth.every((c) => c.httpOnly)).toBe(true);
  expect(
    await page.evaluate(() =>
      Object.keys(localStorage).some((k) => /token|refresh|access/i.test(k)),
    ),
  ).toBe(false);
  expect(errors).toEqual([]);
});

test("home desktop and 360 mobile: RTL, no overflow, menu keyboard and reduced motion", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 360, height: 800 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const trigger = page.getByRole("button", { name: "باز کردن منو" });
  await trigger.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(trigger).toBeFocused();
  await expect(page.locator("html")).not.toHaveClass(/lenis/);
});

test("catalog search, URL filters, refresh and back", async ({ page }) => {
  await mockAPI(page);
  await page.goto("/products");
  await page
    .getByRole("textbox", { name: "جست‌وجوی لباس", exact: true })
    .fill("تست");
  await page.getByRole("button", { name: "جست‌وجو", exact: true }).click();
  await expect(page).toHaveURL(/search=/);
  await page
    .locator(".desktop-only")
    .getByRole("combobox", { name: "موجودی", exact: true })
    .selectOption("available");
  await page
    .locator(".desktop-only")
    .getByRole("button", { name: "اعمال فیلتر" })
    .click();
  await expect(page).toHaveURL(/stock=available/);
  await page.reload();
  await expect(
    page.getByRole("textbox", { name: "جست‌وجوی لباس", exact: true }),
  ).toHaveValue("تست");
  await page.goBack();
  await expect(
    page.getByRole("textbox", { name: "جست‌وجوی لباس", exact: true }),
  ).toHaveValue("تست");
});

test("simple product needs no variant; two variant lines retain correct identity in mocked cart", async ({
  page,
}) => {
  await mockAPI(page, {
    "cart/": cart([
      {
        product_id: 2,
        variant_id: 1,
        name: product.name,
        price: "210000",
        quantity: 1,
        total_price: "210000",
      },
      {
        product_id: 2,
        variant_id: 3,
        name: product.name,
        price: "230000",
        quantity: 1,
        total_price: "230000",
      },
    ]),
  });
  await page.goto("/products/qa-simple");
  await expect(
    page.getByRole("button", { name: "افزودن به سبد", exact: true }),
  ).toBeEnabled();
  await page.goto("/cart");
  await expect(page.locator(".cart-line")).toHaveCount(2);
  await expect(page.getByText("رنگ: مشکی / سایز: M")).toBeVisible();
  await expect(page.getByText("رنگ: کرم / سایز: L")).toBeVisible();
});

test("OTP error and Retry-After prevents repeat request", async ({ page }) => {
  await mockAPI(page);
  await page.route("**/api/shop/auth/otp/request/", (route) =>
    route.fulfill({
      status: 429,
      headers: { "Retry-After": "60" },
      json: { detail: "slow" },
    }),
  );
  await page.goto("/login?next=//evil.test");
  await page.getByLabel("شمارهٔ همراه", { exact: true }).fill("09121234567");
  await page.getByRole("button", { name: "دریافت کد تایید" }).click();
  await expect(page.locator(".notice[role=alert]")).toContainText(
    "تعداد درخواست",
  );
  await expect(
    page.getByRole("button", { name: "دریافت کد تایید" }),
  ).toBeDisabled();
});

test("OTP successful mock never leaves unsafe redirect origin", async ({
  page,
}) => {
  await mockAPI(page);
  await page.goto("/login?next=https://evil.test");
  await page.getByLabel("شمارهٔ همراه", { exact: true }).fill("09121234567");
  await page.getByRole("button", { name: "دریافت کد تایید" }).click();
  await page.getByLabel("کد تایید شش‌رقمی").fill("123456");
  await page.getByRole("button", { name: "تایید و ورود" }).click();
  await expect(page).toHaveURL("http://127.0.0.1:3100/account");
});

for (const status of [401, 403, 404, 429, 503])
  test(`controlled ${status} private API error`, async ({ page }) => {
    await mockAPI(page);
    await page.route("**/api/shop/me/", (route) =>
      route.fulfill({ status, json: { detail: "خطای کنترل‌شده" } }),
    );
    await page.goto("/account");
    if (status === 401)
      await expect(
        page.getByRole("link", { name: "ورود به حساب", exact: true }),
      ).toBeVisible();
    else await expect(page.locator(".notice[role=alert]")).toBeVisible();
  });

for (const state of ["paid", "canceled", "pending", "needs_review", "expired"])
  test(`payment ${state} uses backend order not Status query`, async ({
    page,
  }) => {
    const o = {
      ...order,
      status: state,
      is_paid: state === "paid" || state === "needs_review",
      is_payable: state === "pending",
    };
    await mockAPI(page, { "orders/1/": o });
    await page.goto("/payment/result?order=1&Status=OK");
    const title = page.getByRole("heading", { level: 1 });
    if (state === "paid")
      await expect(title).toContainText("پرداخت در سرور ثبت شده");
    if (state === "pending")
      await expect(title).toContainText("تایید پرداخت هنوز");
    if (state === "needs_review") await expect(title).toContainText("بررسی");
    if (state === "canceled") await expect(title).toContainText("لغو");
    if (state === "expired") await expect(title).toContainText("پایان");
  });

test("ambiguous checkout network error is not retried and survives reload", async ({
  page,
}) => {
  await mockAPI(page, {
    "cart/": cart([
      {
        product_id: 2,
        variant_id: 1,
        name: product.name,
        price: "210000",
        quantity: 1,
        total_price: "210000",
      },
    ]),
    "addresses/": pageOf([address]),
  });
  let calls = 0;
  await page.route("**/api/shop/orders/create/", (route) => {
    calls++;
    return route.abort("timedout");
  });
  await page.goto("/checkout");
  await page.getByRole("radio", { name: /خانهٔ تست/ }).check();
  await page
    .getByRole("button", { name: "ثبت سفارش و رزرو" })
    .click({ clickCount: 2 });
  await expect(
    page.getByRole("heading", { name: "ابتدا سفارش قبلی را بررسی کنید." }),
  ).toBeVisible();
  expect(calls).toBe(1);
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "ابتدا سفارش قبلی را بررسی کنید." }),
  ).toBeVisible();
});

test("empty catalog, cart, favorites and notifications are honest", async ({
  page,
}) => {
  await mockAPI(page, { "products/": pageOf([]) });
  for (const [path, text] of [
    ["/products", "لباسی با این انتخاب پیدا نشد"],
    ["/cart", "سبد شما منتظر انتخاب است"],
    ["/account/favorites", "انتخابی ذخیره نکرده‌اید"],
    ["/account/notifications", "اعلانی ندارید"],
  ]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { name: text })).toBeVisible();
  }
});

test("basic WCAG checks on desktop and mobile and dialog", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await mockAPI(page);
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto("/products/qa-variant");
    await expect(
      page.getByRole("heading", { name: product.name, exact: true }),
    ).toBeVisible();
    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(result.violations).toEqual([]);
  }
  await page.getByRole("button", { name: "باز کردن منو" }).click();
  const result = await new AxeBuilder({ page })
    .include('[role="dialog"]')
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  expect(result.violations).toEqual([]);
});

test("progressive motion: dialog lock, route cleanup and live reduced-motion", async ({
  page,
}) => {
  await mockAPI(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto("/");
  await expect(page.locator("html")).toHaveClass(/lenis/);
  await page.getByRole("button", { name: "باز کردن سبد خرید" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.locator("html")).toHaveClass(/lenis-stopped/);
  await page.keyboard.press("Tab");
  await expect
    .poll(() =>
      page.evaluate(() =>
        Boolean(document.activeElement?.closest('[role="dialog"]')),
      ),
    )
    .toBe(true);
  await page.keyboard.press("Escape");
  await expect
    .poll(() =>
      page.evaluate(() => document.body.hasAttribute("data-scroll-locked")),
    )
    .toBe(false);
  await expect(page.locator("html")).not.toHaveClass(/lenis-stopped/);
  await page
    .getByRole("link", { name: "همهٔ لباس‌ها", exact: true })
    .first()
    .click();
  await expect(page).toHaveURL(/\/products$/);
  await expect(page.locator("html")).toHaveClass(/lenis/);
  await page
    .getByRole("link", { name: "حساب کاربری", exact: true })
    .first()
    .click();
  await expect(page.locator("html")).not.toHaveClass(/lenis/);
  await page.goto("/checkout");
  await expect(page.locator("html")).not.toHaveClass(/lenis/);
  await page.goto("/");
  await expect(page.locator("html")).toHaveClass(/lenis/);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect(page.locator("html")).not.toHaveClass(/lenis/);
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await expect(page.locator("html")).toHaveClass(/lenis/);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator("html")).not.toHaveClass(/lenis/);
});

test("catalog service failure stays distinct from an empty catalog", async ({
  page,
}) => {
  await mockAPI(page);
  await page.route("**/api/shop/products/?*", (r) =>
    r.fulfill({ status: 503, json: { code: "LOCAL_SETUP_REQUIRED" } }),
  );
  await page.goto("/products");
  await expect(page.locator(".notice[role=alert]")).toContainText(
    "npm run doctor",
  );
  await expect(
    page.getByRole("heading", { name: "لباسی با این انتخاب پیدا نشد" }),
  ).toHaveCount(0);
});
test("home editorial is accessible and never represented as catalogue merchandise", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  const hydration: string[] = [];
  page.on("console", (message) => {
    if (/hydrat|Minified React error #(418|423|425)/i.test(message.text()))
      hydration.push(message.text());
  });
  page.on("pageerror", (error) => {
    if (/hydrat|Minified React error #(418|423|425)/i.test(error.message))
      hydration.push(error.message);
  });
  await mockAPI(page);
  await page.goto("/");
  await expect(page.locator(".hero-art-note")).toContainText(
    "نه کالای کاتالوگ",
  );
  expect(hydration).toEqual([]);
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(result.violations).toEqual([]);
  }
});
