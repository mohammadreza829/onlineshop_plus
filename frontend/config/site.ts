/** Temporary brand and public editorial copy: no invented promises/contact/legal data. */
export const site = {
  name: "آنلاین شاپ پلاس",
  latinName: "ONLINE SHOP PLUS",
  description: "فروشگاه اینترنتی لباس",
  legalContentReady: false,
  hero: {
    eyebrow: "پوشش روزمره، نگاه تازه",
    title: "استایل شما،",
    accent: "از زاویه‌ای تازه.",
    description:
      "لباس‌ها را کشف کنید، جزئیات را ببینید و ترکیب دلخواه خودتان را بسازید.",
    cta: "کشف لباس‌ها",
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
