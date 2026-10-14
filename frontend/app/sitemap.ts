import type { MetadataRoute } from "next";
import { publicAPI, siteURL } from "@/lib/api/server";
import type { Page, Product, Category } from "@/lib/api/types";
export const dynamic = "force-dynamic";
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = siteURL();
  if (!base) return [];
  const items: MetadataRoute.Sitemap = [
    { url: base.href },
    { url: new URL("/products", base).href },
  ];
  for (const kind of ["products", "categories"]) {
    let offset = 0;
    for (let page = 0; page < 100; page++) {
      const data = await publicAPI<Page<Product | Category>>(
        kind + "/?limit=100&offset=" + offset,
      );
      if (!data) break;
      for (const item of data.results)
        items.push({
          url: new URL(
            kind === "products"
              ? "/products/" + encodeURIComponent(item.slug)
              : "/products?category=" + encodeURIComponent(item.slug),
            base,
          ).href,
        });
      if (!data.next) break;
      offset += 100;
    }
  }
  return items;
}
