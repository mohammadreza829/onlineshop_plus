import type { Product } from "./types";
const key = "osp.publicProductIndex";
export function rememberProduct(p: Pick<Product, "id" | "slug">) {
  try {
    const all = JSON.parse(localStorage.getItem(key) ?? "{}") as Record<
      string,
      string
    >;
    all[p.id] = p.slug;
    localStorage.setItem(
      key,
      JSON.stringify(Object.fromEntries(Object.entries(all).slice(-500))),
    );
  } catch {
    /* Unavailable or invalid browser storage is treated as absent. */
  }
}
export function knownSlug(id: number) {
  try {
    const value = JSON.parse(localStorage.getItem(key) ?? "{}")[id];
    return typeof value === "string" ? value : undefined;
  } catch {
    return;
  }
}
