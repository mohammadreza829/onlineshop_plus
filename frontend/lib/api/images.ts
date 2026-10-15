/** Same-origin media URLs for both SSR catalogue data and BFF JSON responses. */
export function productImageURL(
  value: string,
  upstream: string,
  allowedHosts: string[],
): string | null {
  try {
    const u = new URL(value, upstream);
    if (u.origin === upstream && u.pathname.startsWith("/media/"))
      return "/api/media/" + u.pathname.slice(7).split("/")
        .map(decodeURIComponent).map(encodeURIComponent).join("/");
    return u.protocol === "https:" && allowedHosts.includes(u.hostname)
      ? u.href : null;
  } catch {
    return null;
  }
}

export function mapProductImages(
  value: unknown,
  upstream: string,
  allowedHosts: string[],
): unknown {
  if (Array.isArray(value))
    return value.map((item) => mapProductImages(item, upstream, allowedHosts));
  if (value && typeof value === "object")
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [
      key,
      key === "image" && typeof item === "string"
        ? productImageURL(item, upstream, allowedHosts)
        : mapProductImages(item, upstream, allowedHosts),
    ]));
  return value;
}