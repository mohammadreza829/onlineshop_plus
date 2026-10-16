import { describe, expect, it } from "vitest";
import { canUseSmoothScroll } from "@/lib/motion/policy";

describe("immersive motion safety policy", () => {
  it.each(["/", "/products", "/products/linen-shirt", "/products/لباس"])(
    "enhances browsing on fine desktop: %s",
    (path) => {
      expect(canUseSmoothScroll(path, true, false)).toBe(true);
    },
  );
  it.each([
    "/checkout",
    "/cart",
    "/login",
    "/payment/result",
    "/account",
    "/account/addresses",
    "/products-not-a-route",
  ])("keeps native scrolling in %s", (path) => {
    expect(canUseSmoothScroll(path, true, false)).toBe(false);
  });
  it("honors reduced motion on desktop", () =>
    expect(canUseSmoothScroll("/", true, true)).toBe(false));
  it("keeps coarse and narrow screens native", () =>
    expect(canUseSmoothScroll("/", false, false)).toBe(false));
});
