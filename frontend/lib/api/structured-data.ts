import type { ProductDetail } from "./types";
export function productStructuredData(p: ProductDetail, url: string) {
  const active = p.variants.filter((v) => v.is_active),
    prices = active.map((v) => BigInt(v.final_price) * 10n);
  const stock = p.variants.length
    ? active.some((v) => v.inventory > 0)
    : p.inventory > 0;
  const offers = prices.length
    ? {
        "@type": "AggregateOffer",
        priceCurrency: "IRR",
        lowPrice: String(prices.reduce((a, b) => (a < b ? a : b))),
        highPrice: String(prices.reduce((a, b) => (a > b ? a : b))),
        offerCount: active.length,
        availability: stock
          ? "https://schema.org/InStock"
          : "https://schema.org/OutOfStock",
        url,
      }
    : {
        "@type": "Offer",
        priceCurrency: "IRR",
        price: String(BigInt(p.final_price) * 10n),
        availability: stock
          ? "https://schema.org/InStock"
          : "https://schema.org/OutOfStock",
        url,
      };
  return {
    "@context": "https://schema.org",
    "@type": "Product",
    name: p.name,
    sku: p.sku,
    description: p.description.replace(/<[^>]*>/g, ""),
    category: p.category?.name,
    url,
    ...(!p.variants.length || active.length ? { offers } : {}),
    ...(p.rating_average !== null && p.rating_count > 0
      ? {
          aggregateRating: {
            "@type": "AggregateRating",
            ratingValue: p.rating_average,
            reviewCount: p.rating_count,
            bestRating: 5,
            worstRating: 1,
          },
        }
      : {}),
  };
}
export function safeJSON(value: unknown) {
  return JSON.stringify(value).replace(/</g, "\\u003c");
}
