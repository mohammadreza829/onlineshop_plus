import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mockAPI, product, cart, pageOf } from "./fixtures";

// Fixtures remain in QA only; the application still uses the real Django API.
for (const scheme of ["light", "dark"] as const) {
  test(`spatial home: ${scheme}, responsive, contrast, keyboard and reduced motion`, async ({
    page,
  }) => {
    await mockAPI(page);
    await page.emulateMedia({ colorScheme: scheme });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    for (const width of [375, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.goto("/");
      await expect(page.locator(".product-card")).toHaveCount(1);
      await expect(page.locator(".scene-fallback img")).toBeVisible();
      expect(
        await page
          .locator(".scene-fallback img")
          .evaluate(
            (el: HTMLImageElement) => el.complete && el.naturalWidth > 0,
          ),
      ).toBe(true);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      const result = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze();
      expect(result.violations).toEqual([]);
    }
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.locator(".card-depth").hover();
    await expect(page.locator(".card-depth")).toHaveCSS("transform", "none");
    await page.setViewportSize({ width: 375, height: 850 });
    const trigger = page.getByRole("button", { name: "باز کردن منو" });
    await trigger.click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(trigger).toBeFocused();
    expect(errors).toEqual([]);
  });
  test(`shopping routes: ${scheme}, contrast and reflow`, async ({ page }) => {
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
      "favorites/": pageOf([{ id: 1, product }]),
    });
    for (const width of [390, 1440]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.emulateMedia({ colorScheme: scheme });
      for (const path of [
        "/products",
        "/products/qa-variant",
        "/login",
        "/cart",
        "/checkout",
        "/account/profile",
        "/account/addresses",
        "/account/orders/1",
        "/payment/result?order=1",
      ]) {
        await page.goto(path);
        await expect(page.locator("main")).toBeVisible();
        await page.waitForTimeout(200);
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
          path,
        ).toBe(true);
        const result = await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
          .analyze();
        expect(result.violations, path).toEqual([]);
      }
    }
  });
}

test("21st tilt is progressive, pointer-only and keyboard-safe", async ({
  page,
}) => {
  await mockAPI(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto("/");
  const stage = page.locator(".card-depth");
  await stage.scrollIntoViewIfNeeded();
  const initial = await stage.evaluate((el) => getComputedStyle(el).transform);
  const box = await stage.boundingBox();
  expect(box).not.toBeNull();
  await page.mouse.move(box!.x + box!.width * 0.8, box!.y + box!.height * 0.3);
  await expect
    .poll(async () => stage.evaluate((el) => getComputedStyle(el).transform))
    .not.toBe(initial);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect(stage).toHaveCSS("transform", "none");
  await expect(page.locator("html")).not.toHaveClass(/lenis/);
  await page.getByRole("button", { name: "باز کردن سبد خرید" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Tab");
  expect(
    await page.evaluate(
      () => !!document.activeElement?.closest('[role="dialog"]'),
    ),
  ).toBe(true);
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("button", { name: "باز کردن سبد خرید" }),
  ).toBeFocused();
});
