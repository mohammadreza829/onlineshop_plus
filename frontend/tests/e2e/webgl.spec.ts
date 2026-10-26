import { test, expect } from "@playwright/test";
import { mockAPI } from "./fixtures";

test("real WebGL volume: material changes, camera controls, pause and fallback", async ({
  page,
}) => {
  await mockAPI(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(page.locator(".webgl-stage")).toHaveClass(/is-ready/);
  const canvas = page.locator(".webgl-stage canvas");
  await expect(canvas).toHaveAttribute("role", "img");
  const first = await canvas.screenshot();
  await page.getByRole("button", { name: "استخوانی", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "استخوانی", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.waitForTimeout(300);
  expect(Buffer.compare(first, await canvas.screenshot())).not.toBe(0);
  const material = await canvas.screenshot();
  await page.getByRole("button", { name: "چرخش به چپ", exact: true }).click();
  await page.waitForTimeout(900);
  expect(Buffer.compare(material, await canvas.screenshot())).not.toBe(0);
  await expect(
    page.getByRole("button", { name: "شروع چرخش خودکار", exact: true }),
  ).toBeDisabled();
  await page.emulateMedia({ reducedMotion: "no-preference" });
  const auto = page.getByRole("button", {
    name: "شروع چرخش خودکار",
    exact: true,
  });
  await expect(auto).toBeEnabled();
  await auto.click();
  await expect(
    page.getByRole("button", { name: "توقف چرخش خودکار", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect(
    page.getByRole("button", { name: "شروع چرخش خودکار", exact: true }),
  ).toBeDisabled();
  await canvas.evaluate((el: HTMLCanvasElement) => {
    el.getContext("webgl2")?.getExtension("WEBGL_lose_context")?.loseContext();
  });
  await expect(page.locator(".webgl-stage")).not.toHaveClass(/is-ready/);
  await expect(
    page.getByText(
      "نمای سه‌بعدی در این دستگاه در دسترس نیست؛ فروشگاه همچنان قابل استفاده است.",
    ),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "ورود به فروشگاه", exact: true }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
