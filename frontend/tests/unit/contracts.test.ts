import { describe, it, expect } from "vitest";
import { ascii, phone, toman, lineKey, cartFingerprint } from "@/lib/format";
import { internalRedirect, gatewayURL, catalogQuery } from "@/lib/api/filters";
import { ApiError, errorText } from "@/lib/api/errors";
import { variantFor, sizesFor } from "@/features/product/variants";
import type { Variant } from "@/lib/api/types";
const variants: Variant[] = [
  {
    id: 1,
    sku: "a",
    color: "مشکی",
    size: "M",
    price: "100",
    final_price: "90",
    inventory: 2,
    is_active: true,
  },
  {
    id: 2,
    sku: "b",
    color: "مشکی",
    size: "L",
    price: "110",
    final_price: "99",
    inventory: 0,
    is_active: true,
  },
  {
    id: 3,
    sku: "c",
    color: "کرم",
    size: "L",
    price: "120",
    final_price: "108",
    inventory: 4,
    is_active: false,
  },
];
describe("real client contracts", () => {
  it("normalizes Persian and Arabic digits", () =>
    expect(ascii("۱۲٣٤۵۶۷۸۹۰")).toBe("1234567890"));
  it.each([
    "۰۹۱۲۱۲۳۴۵۶۷",
    "+98 9121234567",
    "00989121234567",
    "989121234567",
    "9121234567",
  ])("normalizes phone %s", (v) => expect(phone(v)).toBe("09121234567"));
  it("formats whole Toman using integer arithmetic", () => {
    expect(toman("12345678901234567890")).toContain(
      "۱۲٬۳۴۵٬۶۷۸٬۹۰۱٬۲۳۴٬۵۶۷٬۸۹۰",
    );
    expect(toman("1.5")).toBe("مبلغ نامعتبر");
  });
  it("keeps two variants as independent cart lines", () =>
    expect(lineKey({ product_id: 1, variant_id: 1 })).not.toBe(
      lineKey({ product_id: 1, variant_id: 2 }),
    ));
  it("fingerprints lines independent of order, with quantity changes detectable", () => {
    const a = [
      { product_id: 1, variant_id: 2, quantity: 1 },
      { product_id: 1, variant_id: 3, quantity: 2 },
    ];
    expect(cartFingerprint(a)).toBe(cartFingerprint([...a].reverse()));
    expect(cartFingerprint(a)).not.toBe(
      cartFingerprint([{ ...a[0], quantity: 2 }, a[1]]),
    );
  });
  it("never selects unavailable/inactive variants", () => {
    expect(variantFor(variants, "مشکی", "M")?.id).toBe(1);
    expect(variantFor(variants, "مشکی", "L")).toBeUndefined();
    expect(variantFor(variants, "کرم", "L")).toBeUndefined();
    expect(sizesFor(variants, "مشکی")).toEqual(["M", "L"]);
  });
  it("only forwards supported filter keys", () =>
    expect(
      catalogQuery(
        new URLSearchParams("search=لباس&size=L&offset=12"),
      ).toString(),
    ).toBe("search=%D9%84%D8%A8%D8%A7%D8%B3&offset=12&limit=12"));
  it.each([
    "https://evil.test",
    "//evil.test",
    "/\\evil.test",
    "/admin",
    "/api/shop/me/",
    "javascript:alert(1)",
  ])("rejects unsafe login destination %s", (v) =>
    expect(internalRedirect(v)).toBe("/account"),
  );
  it("keeps valid owned destination", () =>
    expect(internalRedirect("/payment/result?order=1")).toBe(
      "/payment/result?order=1",
    ));
  it.each([
    "http://sandbox.zarinpal.com/a",
    "https://sandbox.zarinpal.com.evil.test/a",
    "https://user@sandbox.zarinpal.com/a",
    "https://sandbox.zarinpal.com:444/a",
    "javascript:alert(1)",
  ])("rejects unsafe gateway %s", (v) =>
    expect(() => gatewayURL(v, ["sandbox.zarinpal.com"])).toThrow(),
  );
  it("accepts exact HTTPS gateway host only", () =>
    expect(
      gatewayURL("https://sandbox.zarinpal.com/pg/StartPay/A", [
        "sandbox.zarinpal.com",
      ]),
    ).toContain("/StartPay/A"));
  it("maps nested field and detail errors without stack output", () => {
    expect(
      errorText({ phone: ["شماره نامعتبر"], detail: "دوباره بررسی کنید" }, 400),
    ).toContain("شماره نامعتبر");
    expect(new ApiError(503, "SECRET STACK").message).not.toContain("SECRET");
    expect(new ApiError(429, {}, 12).retryAfter).toBe(12);
  });
});

it("supports a real variant with blank color/size only after explicit choice", () => {
  const v = { ...variants[0], color: "", size: "" };
  expect(variantFor([v], undefined, undefined)).toBeUndefined();
  expect(variantFor([v], "", "")?.id).toBe(v.id);
});

it("local setup diagnostics are actionable without displaying arbitrary server errors", () => {
  expect(
    errorText(
      { code: "LOCAL_SETUP_REQUIRED", detail: "private server text" },
      503,
    ),
  ).toContain("npm run doctor");
  expect(errorText({ detail: "private server text" }, 503)).not.toContain(
    "private server text",
  );
});
