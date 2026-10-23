import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mockAPI } from "./fixtures";

test("header search submits the actual query on desktop and mobile", async ({
  page,
}) => {
  await mockAPI(page);
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    const input = page.getByRole("searchbox", { name: "جست‌وجوی فروشگاه" });
    await input.fill("پیراهن");
    await input.press("Enter");
    await expect(page).toHaveURL(/\/products\?search=/);
    expect(new URL(page.url()).searchParams.get("search")).toBe("پیراهن");
  }
});

test("core shopping pages reflow across compact, tablet and desktop widths", async ({
  page,
}) => {
  await mockAPI(page);
  for (const width of [320, 375, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    for (const route of [
      "/",
      "/products",
      "/products/qa-variant",
      "/cart",
      "/checkout",
      "/account",
    ]) {
      await page.goto(route);
      await expect(page.locator("main")).toBeVisible();
      await expect(page.locator(".loading-state")).toHaveCount(0);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
        `${route} at ${width}`,
      ).toBe(true);
    }
  }
});

test("dark storefront and product pass automated WCAG AA checks", async ({
  page,
}) => {
  await mockAPI(page);
  await page.emulateMedia({ colorScheme: "dark", reducedMotion: "reduce" });
  for (const route of ["/", "/products/qa-variant"]) {
    await page.goto(route);
    await expect(page.locator(".loading-state")).toHaveCount(0);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
      .analyze();
    expect(results.violations).toEqual([]);
  }
});

test("200 percent text remains readable without horizontal page scrolling", async ({
  page,
}) => {
  await mockAPI(page);
  await page.setViewportSize({ width: 390, height: 900 });
  for (const route of ["/", "/products", "/cart", "/login"]) {
    await page.goto(route);
    await page.addStyleTag({ content: "html { font-size: 200% !important; }" });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      route,
    ).toBe(true);
  }
});

test("shared header category cache does not cause streamed home hydration errors", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await mockAPI(page);
  for (let attempt = 0; attempt < 3; attempt++) {
    await page.goto("/");
    await expect(
      page.getByRole("navigation", { name: "دسته‌های لباس" }),
    ).toBeVisible();
    await expect(page.locator(".loading-state")).toHaveCount(0);
  }
  expect(errors).toEqual([]);
});
