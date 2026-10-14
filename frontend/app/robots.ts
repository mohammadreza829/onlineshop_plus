import type { MetadataRoute } from "next";
import { siteURL } from "@/lib/api/server";
export const dynamic = "force-dynamic";
export default function robots(): MetadataRoute.Robots {
  const base = siteURL();
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: [
        "/api/",
        "/account",
        "/checkout",
        "/cart",
        "/login",
        "/payment/",
      ],
    },
    sitemap: base ? new URL("/sitemap.xml", base).href : undefined,
  };
}
