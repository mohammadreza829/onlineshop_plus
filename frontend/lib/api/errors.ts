export class ApiError extends Error {
  constructor(
    public status: number,
    public data: unknown,
    public retryAfter = 0,
  ) {
    super(errorText(data, status));
    this.name = "ApiError";
  }
}
export function errorText(data: unknown, status = 0): string {
  if (
    status === 503 &&
    data &&
    typeof data === "object" &&
    "code" in data &&
    data.code === "LOCAL_SETUP_REQUIRED"
  )
    return "تنظیمات اجرای محلی کامل نیست؛ در پوشهٔ frontend دستور npm run doctor را اجرا کنید.";
  if (status >= 500)
    return status === 503
      ? "سرویس موقتاً در دسترس نیست. کمی بعد دوباره تلاش کنید."
      : "ارتباط با فروشگاه کامل نشد. نتیجهٔ عملیات را بررسی کنید.";
  if (status === 401) return "برای ادامه وارد حساب خود شوید.";
  if (status === 404) return "این مورد پیدا نشد یا به آن دسترسی ندارید.";
  if (status === 429)
    return "تعداد درخواست‌ها زیاد است؛ تا پایان زمان انتظار صبر کنید.";
  if (typeof data === "string") return data.slice(0, 400);
  if (Array.isArray(data)) return data.map((v) => errorText(v)).join("، ");
  if (data && typeof data === "object")
    return Object.entries(data)
      .map(
        ([k, v]) =>
          `${k === "detail" || k === "non_field_errors" ? "" : k + ": "}${errorText(v)}`,
      )
      .join(" — ");
  return status === 403
    ? "اجازهٔ این عملیات وجود ندارد؛ صفحه را تازه کنید."
    : "درخواست انجام نشد.";
}
