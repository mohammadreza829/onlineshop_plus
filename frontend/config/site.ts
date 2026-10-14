/** Temporary brand and public editorial copy: no invented promises/contact/legal data. */
export const site = {
  name: "آنلاین شاپ پلاس",
  latinName: "ONLINE SHOP PLUS",
  description: "فروشگاه اینترنتی لباس",
  legalContentReady: false,
  hero: {
    eyebrow: "آنلاین شاپ پلاس / کاتالوگ لباس",
    title: "فروشگاه",
    accent: "لباس",
    description:
      "محصولات، رنگ‌ها و سایزهای موجود را ببینید و انتخاب خود را به سبد اضافه کنید.",
    cta: "مشاهدهٔ لباس‌ها",
    artWord: "پوشش",
    artLabel: "CLOTHING CATALOG",
  },
  /** Current Django default; synchronize if deployment overrides OTP_RESEND_COOLDOWN_SECONDS. 429 Retry-After remains authoritative. */
  otpResendSeconds: 60,
} as const;
export const accountLinks = [
  ["/account/profile", "مشخصات من"],
  ["/account/addresses", "آدرس‌ها"],
  ["/account/orders", "سفارش‌ها"],
  ["/account/favorites", "علاقه‌مندی‌ها"],
  ["/account/notifications", "اعلان‌ها"],
] as const;
