import { test, expect } from "@playwright/test";
import { mockAPI, order } from "./fixtures";

test("real BFF: expired CSRF cookie recovers once during OTP verification", async ({
  page,
  context,
}) => {
  const statuses: number[] = [];
  page.on("response", (r) => {
    if (new URL(r.url()).pathname === "/api/shop/auth/otp/verify/")
      statuses.push(r.status());
  });
  await page.goto(
    "/login?next=" + encodeURIComponent("/payment/result?order=999999"),
  );
  await page
    .getByLabel("شمارهٔ همراه", { exact: true })
    .fill("0913" + String(Date.now()).slice(-7));
  await page
    .getByRole("button", { name: "دریافت کد تایید", exact: true })
    .click();
  await expect(page.getByLabel("کد تایید شش‌رقمی")).toBeVisible();
  await context.clearCookies({ name: "osp_csrf" });
  await page.getByLabel("کد تایید شش‌رقمی").fill("123456");
  await page.getByRole("button", { name: "تایید و ورود", exact: true }).click();
  await expect(page).toHaveURL(/\/payment\/result\?order=999999$/);
  expect(statuses).toEqual([403, 200]);
  await expect(
    page.getByText("این مورد پیدا نشد یا به آن دسترسی ندارید.", {
      exact: true,
    }),
  ).toBeVisible();
});

test("payment login preserves order query and returns to result", async ({
  page,
}) => {
  let authenticated = false;
  await mockAPI(page, {
    "orders/1/": { ...order, status: "paid", is_paid: true, is_payable: false },
  });
  await page.route("**/api/shop/me/", (route) =>
    route.fulfill({
      status: authenticated ? 200 : 401,
      json: authenticated ? { id: 1, first_name: "تست" } : { detail: "login" },
    }),
  );
  await page.route("**/api/shop/auth/otp/verify/", async (route) => {
    authenticated = true;
    await route.fulfill({ json: { authenticated: true } });
  });
  await page.goto("/payment/result?order=1");
  await page.getByRole("link", { name: "ورود به حساب", exact: true }).click();
  await expect(page).toHaveURL(/\/login\?next=/);
  expect(new URL(page.url()).searchParams.get("next")).toBe(
    "/payment/result?order=1",
  );
  await page.getByLabel("شمارهٔ همراه", { exact: true }).fill("09120000001");
  await page
    .getByRole("button", { name: "دریافت کد تایید", exact: true })
    .click();
  await page.getByLabel("کد تایید شش‌رقمی").fill("123456");
  await page.getByRole("button", { name: "تایید و ورود", exact: true }).click();
  await expect(page).toHaveURL(/\/payment\/result\?order=1$/);
  await expect(
    page.getByRole("heading", { name: "پرداخت در سرور ثبت شده است." }),
  ).toBeVisible();
});

test("customer links stay on storefront across fourteen routes", async ({
  page,
}) => {
  await mockAPI(page);
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  for (const path of [
    "/",
    "/products",
    "/products/qa-variant",
    "/cart",
    "/checkout",
    "/account",
    "/account/profile",
    "/account/addresses",
    "/account/orders",
    "/account/orders/1",
    "/account/favorites",
    "/account/notifications",
    "/payment/result?order=1",
    "/login",
  ]) {
    const response = await page.goto(path);
    expect(response?.status(), path).toBe(200);
    await expect(page.locator("header")).toBeVisible();
    const links = await page
      .locator("a[href]")
      .evaluateAll((links) => links.map((a) => (a as HTMLAnchorElement).href));
    for (const href of links) {
      const url = new URL(href);
      expect(url.origin, path + ": " + href).toBe(new URL(page.url()).origin);
      expect(url.pathname).not.toMatch(
        /^\/(?:api|admin|payment\/verify|shop)\//,
      );
    }
  }
  expect(errors).toEqual([]);
});

test("development loopback alias keeps login destination", async ({
  page,
  baseURL,
}) => {
  test.skip(
    process.env.QA_DEVELOPMENT !== "1",
    "Development-only canonicalization",
  );
  const alias = new URL("/login?next=%2Fpayment%2Fresult%3Forder%3D1", baseURL);
  alias.hostname = "localhost";
  await page.goto(alias.href);
  await expect(page).toHaveURL(
    new RegExp("127\\.0\\.0\\.1:" + alias.port + "/login\\?next="),
  );
  expect(new URL(page.url()).searchParams.get("next")).toBe(
    "/payment/result?order=1",
  );
});
