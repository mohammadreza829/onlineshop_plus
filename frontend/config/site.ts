/** Public copy and temporary identity. No invented policies, ratings or promises. */
export const site = {
  name: "آنلاین شاپ پلاس",
  latinName: "ONLINE SHOP PLUS",
  description: "لباس‌هایی برای سلیقهٔ تو؛ با نگاهی دقیق‌تر به جزئیات.",
  legalContentReady: false,
  hero: {
    eyebrow: "برای سلیقهٔ خودت",
    title: "کمتر تکرار.",
    accent: "بیشتر خودت.",
    description:
      "لباس‌ها را ببین، رنگ و سایز دلخواهت را پیدا کن و انتخابت را با دیدن جزئیات کامل کن.",
    cta: "دیدن مجموعه",
    artLabel: "NEW PERSPECTIVE",
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
