export const filterKeys = [
  "search",
  "category",
  "stock",
  "min_price",
  "max_price",
  "ordering",
  "limit",
  "offset",
] as const;
export function catalogQuery(input: URLSearchParams) {
  const out = new URLSearchParams();
  for (const k of filterKeys) {
    const v = input.get(k);
    if (v) out.set(k, v);
  }
  if (!out.has("limit")) out.set("limit", "12");
  return out;
}
export function internalRedirect(value: string | null | undefined) {
  if (
    !value ||
    !value.startsWith("/") ||
    value.startsWith("//") ||
    /[\\\r\n]/.test(value)
  )
    return "/account";
  try {
    const u = new URL(value, "https://local.invalid");
    const p = u.pathname;
    if (!(
      p === "/checkout" ||
      p === "/cart" ||
      p === "/products" ||
      p.startsWith("/products/") ||
      p === "/account" ||
      p.startsWith("/account/") ||
      p === "/payment/result"
    ))
      return "/account";
    return p + u.search;
  } catch {
    return "/account";
  }
}
export function gatewayURL(value: string, hosts: string[]) {
  const u = new URL(value);
  if (
    u.protocol !== "https:" ||
    u.username ||
    u.password ||
    u.port ||
    !hosts.includes(u.hostname)
  )
    throw new Error("نشانی درگاه معتبر نیست.");
  return u.href;
}
