import { test, expect } from "@playwright/test";
import { mockAPI } from "./fixtures";

test("layered poster supports pointer depth, freeze/resume and live reduced motion", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await mockAPI(page);
  await page.goto("/");
  const scene = page.locator(".hero-scene");
  await expect(scene).toHaveAttribute("data-motion", "running");
  await expect(scene).toHaveAttribute("data-depth-enabled", "true");
  for (const layer of ["stage", "garment"])
    await expect
      .poll(() =>
        page
          .locator(`.scene-${layer} img`)
          .evaluate(
            (img: HTMLImageElement) => img.complete && img.naturalWidth > 0,
          ),
      )
      .toBe(true);
  await page.mouse.move(360, 330);
  await expect
    .poll(() => scene.evaluate((el) => el.style.getPropertyValue("--scene-ry")))
    .not.toBe("");
  const moving = await page
    .locator(".scene-garment")
    .evaluate((el) => getComputedStyle(el).transform);
  await expect
    .poll(() =>
      page
        .locator(".scene-garment")
        .evaluate((el) => getComputedStyle(el).transform),
    )
    .not.toBe(moving);
  await page
    .getByRole("button", { name: "توقف حرکت پوستر", exact: true })
    .click();
  await expect(scene).toHaveAttribute("data-motion", "still");
  const frozen = await page
    .locator(".scene-garment")
    .evaluate((el) => getComputedStyle(el).transform);
  await page.waitForTimeout(160);
  expect(
    await page
      .locator(".scene-garment")
      .evaluate((el) => getComputedStyle(el).transform),
  ).toBe(frozen);
  await page
    .getByRole("button", { name: "ادامهٔ حرکت پوستر", exact: true })
    .click();
  await expect(scene).toHaveAttribute("data-motion", "running");
  await page.locator(".site-footer").scrollIntoViewIfNeeded();
  await expect(scene).toHaveAttribute("data-motion", "still");
  await page.evaluate(() => window.scrollTo(0, 0));
  await expect(scene).toHaveAttribute("data-motion", "running");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect(scene).toHaveAttribute("data-motion", "still");
  await expect(scene).toHaveAttribute("data-depth-enabled", "false");
  await page.goto("/checkout");
  await expect(scene).toHaveCount(0);
  await expect(page.locator("html")).not.toHaveClass(/lenis/);
});

test("product depth responds to pointer, resets and disables for reduced motion", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await mockAPI(page);
  await page.goto("/products");
  const tilt = page.locator(".tilt-surface").first();
  await expect(tilt).toHaveAttribute("data-tilt-enabled", "true");
  await tilt.hover({ position: { x: 30, y: 50 } });
  await expect(tilt).toHaveAttribute("data-tilting", "true");
  await expect(page.locator(".card-discover").first()).toHaveCSS(
    "opacity",
    "1",
  );
  await page.mouse.move(10, 150);
  await expect(tilt).not.toHaveAttribute("data-tilting", "true");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect(tilt).toHaveAttribute("data-tilt-enabled", "false");
  await expect(tilt).toHaveCSS("transform", "none");
});

test("touch layout keeps poster depth and product tilt disabled", async ({
  browser,
  baseURL,
}) => {
  const context = await browser.newContext({
    baseURL,
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
  });
  try {
    const page = await context.newPage();
    await mockAPI(page);
    await page.goto("/");
    await expect(page.locator(".hero-scene")).toHaveAttribute(
      "data-depth-enabled",
      "false",
    );
    const target = await page.locator(".scene-control").boundingBox();
    expect(target!.width).toBeGreaterThanOrEqual(44);
    expect(target!.height).toBeGreaterThanOrEqual(44);
    await page.goto("/products");
    await expect(page.locator(".tilt-surface").first()).toHaveAttribute(
      "data-tilt-enabled",
      "false",
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

test("laptop first fold keeps poster controls and calls to action in view", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await mockAPI(page);
  await page.goto("/");
  await expect(page.locator(".hero-actions a").first()).toBeInViewport();
  const control = await page.locator(".scene-control").boundingBox();
  expect(control!.y + control!.height).toBeLessThanOrEqual(768);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});
