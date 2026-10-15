/** Public copy and temporary identity. No invented policies, ratings or promises. */
export const site = {
  name: "آنلاین شاپ پلاس",
  latinName: "ONLINE SHOP PLUS",
  description: "روایتی تازه از انتخاب لباس؛ جزئیات بیشتر، انتخاب شخصی‌تر.",
  legalContentReady: false,
  hero: {
    eyebrow: "انتخابی که شبیه خودت است",
    title: "خارج از تکرار.",
    accent: "نزدیک به خودت.",
    description:
      "لباس را فقط نبین؛ جزئیاتش را کشف کن. از میان رنگ‌ها، فرم‌ها و انتخاب‌های موجود، روایت خودت را بساز.",
    cta: "کشف لباس‌ها",
    artLabel: "A NEW PERSPECTIVE",
  },
  otpResendSeconds: 60,
} as const;
export const accountLinks = [
  ["/account/profile", "مشخصات من"],
  ["/account/addresses", "آدرس‌ها"],
  ["/account/orders", "سفارش‌ها"],
  ["/account/favorites", "علاقه‌مندی‌ها"],
  ["/account/notifications", "اعلان‌ها"],
] as const;
