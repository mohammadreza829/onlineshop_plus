export function ascii(value: string) {
  return value.replace(/[۰-۹٠-٩]/g, (c) =>
    String(c.charCodeAt(0) - (c >= "۰" ? 1776 : 1632)),
  );
}
export function phone(value: string) {
  let v = ascii(value).replace(/[\s()-]/g, "");
  if (v.startsWith("+98")) v = "0" + v.slice(3);
  else if (v.startsWith("0098")) v = "0" + v.slice(4);
  else if (v.startsWith("98") && v.length === 12) v = "0" + v.slice(2);
  else if (v.startsWith("9") && v.length === 10) v = "0" + v;
  return v;
}
export function toman(value: string | number) {
  try {
    return new Intl.NumberFormat("fa-IR").format(BigInt(value)) + " تومان";
  } catch {
    return "مبلغ نامعتبر";
  }
}
export function number(value: number) {
  return new Intl.NumberFormat("fa-IR").format(value);
}
export function date(value: string) {
  const d = new Date(value);
  return Number.isNaN(d.valueOf())
    ? "تاریخ نامعتبر"
    : new Intl.DateTimeFormat("fa-IR", {
        dateStyle: "medium",
        timeZone: "Asia/Tehran",
      }).format(d);
}
export function lineKey(item: {
  product_id: number;
  variant_id: number | null;
}) {
  return `${item.product_id}:${item.variant_id ?? "base"}`;
}
export function cartFingerprint(
  items: { product_id: number; variant_id: number | null; quantity: number }[],
) {
  return JSON.stringify(
    items
      .map((i) => [lineKey(i), i.quantity])
      .sort((a, b) => String(a[0]).localeCompare(String(b[0]))),
  );
}
export const statusLabels: Record<string, string> = {
  pending: "در انتظار پرداخت",
  paid: "پرداخت‌شده",
  preparing: "در حال آماده‌سازی",
  sent: "ارسال‌شده",
  delivered: "تحویل‌شده",
  canceled: "لغوشده",
  expired: "منقضی‌شده",
  needs_review: "نیازمند بررسی",
  unknown: "در انتظار تأیید",
};
