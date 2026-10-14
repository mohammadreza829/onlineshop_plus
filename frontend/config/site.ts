/** Public copy and temporary identity. No invented policies, ratings or promises. */
export const site = {
  name: "آنلاین شاپ پلاس",
  latinName: "ONLINE SHOP PLUS",
  description: "انتخاب لباس، به سادگی.",
  legalContentReady: false,
  hero: {
    eyebrow: "یک نگاه تازه به انتخاب لباس",
    title: "سبک شما،",
    accent: "انتخاب شما.",
    description:
      "میان لباس‌ها بگردید، جزئیات را ببینید و رنگ و سایز مناسب خودتان را انتخاب کنید.",
    cta: "مشاهدهٔ لباس‌ها",
    artLabel: "THE EVERYDAY EDIT",
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
