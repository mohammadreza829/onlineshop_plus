import { it, expect } from "vitest";
import { productStructuredData, safeJSON } from "@/lib/api/structured-data";
import type { ProductDetail } from "@/lib/api/types";
const p: ProductDetail = {
  id: 1,
  sku: "A",
  name: "لباس",
  slug: "a",
  price: "100",
  final_price: "90",
  off: 10,
  inventory: 1,
  category: null,
  rating_average: null,
  rating_count: 0,
  description: "<script>alert(1)</script>",
  images: [],
  features: [],
  variants: [],
};
it("uses actual price in IRR for schema and does not invent ratings", () => {
  const d = productStructuredData(p, "https://real.test/products/a");
  expect(d).not.toHaveProperty("aggregateRating");
  expect(d.offers).toHaveProperty("price", "900");
  expect(d.offers).toHaveProperty("priceCurrency", "IRR");
});
it("safely embeds JSON without executable markup", () =>
  expect(
    safeJSON({ value: "</script><script>alert(1)</script>" }),
  ).not.toContain("<"));
