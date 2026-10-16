import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { join } from "node:path";
import { mockAPI, cart, product } from "./fixtures";

for (const colorScheme of ["light", "dark"] as const) {
  for (const width of [1440, 390]) {
    test(`immersive layout ${colorScheme} ${width}: RTL and functional routes`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 });
      await page.emulateMedia({ colorScheme, reducedMotion: "reduce" });
      await mockAPI(page, {
        "cart/": cart([
          {
            product_id: product.id,
            variant_id: 1,
            name: product.name,
            price: "210000",
            quantity: 1,
            total_price: "210000",
          },
        ]),
      });
      const errors: string[] = [];
      page.on("pageerror", (e) => errors.push(`${page.url()}: ${e.message}`));
      for (const [label, path] of [
        ["home", "/"],
        ["catalogue", "/products"],
        ["product", "/products/qa-variant"],
        ["cart", "/cart"],
        ["checkout", "/checkout"],
        ["login", "/login"],
        ["account", "/account/orders"],
        ["payment", "/payment/result?order=1"],
      ]) {
        await page.goto(path);
        await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
        await expect(page.locator("main")).toBeVisible();
        await expect(page.locator("main h1").first()).toBeVisible();
        await expect(page.locator("main .loading")).toHaveCount(0);
        await expect
          .poll(() =>
            page.evaluate(
              () => document.documentElement.scrollWidth <= innerWidth,
            ),
          )
          .toBe(true);
        await expect(page.locator("html")).not.toHaveClass(/lenis/);
        if (label === "home" || label === "product") {
          const scan = await new AxeBuilder({ page })
            .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
            .analyze();
          expect(scan.violations).toEqual([]);
        }
        if (process.env.IMMERSIVE_QA_CAPTURE) {
          await page.screenshot({
            path: join(
              process.env.IMMERSIVE_QA_CAPTURE,
              `${label}-${colorScheme}-${width}.png`,
            ),
            fullPage: true,
          });
        }
      }
      expect(errors).toEqual([]);
    });
  }
}

test("streamed home matches server snapshot even when header data arrives early", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await mockAPI(page);
  const hydration: string[] = [];
  page.on("pageerror", (e) => hydration.push(e.message));
  for (let visit = 0; visit < 4; visit++) {
    await page.goto("/");
    await expect(page.locator(".category-list")).toContainText(
      product.category.name,
    );
    await expect(page.locator(".product-card").first()).toBeVisible();
  }
  expect(hydration).toEqual([]);
});

test("JavaScript-disabled shell explains interactive requirements", async ({
  browser,
  baseURL,
}) => {
  const context = await browser.newContext({
    baseURL,
    javaScriptEnabled: false,
    viewport: { width: 390, height: 844 },
  });
  try {
    const page = await context.newPage();
    await page.goto("/");
    await expect(page.locator("#noscript-title")).toBeVisible();
    await expect(page.locator(".noscript-notice")).toContainText(
      "به جاوااسکریپت نیاز دارند",
    );
    await expect(page.locator(".noscript-notice a")).toHaveAttribute(
      "href",
      "/products",
    );
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  } finally {
    await context.close();
  }
});
