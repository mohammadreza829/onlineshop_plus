/** Keep smooth wheel enhancements out of forms, financial flows and touch devices. */
export function canUseSmoothScroll(
  pathname: string,
  fineDesktop: boolean,
  reducedMotion: boolean,
): boolean {
  return (
    fineDesktop &&
    !reducedMotion &&
    (pathname === "/" ||
      pathname === "/products" ||
      /^\/products\/[^/]+\/?$/.test(pathname))
  );
}
