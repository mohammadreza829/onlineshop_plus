"use client";
import { useEffect, useState } from "react";
import { number } from "@/lib/format";
export function Reservation({ until }: { until: string | null }) {
  const [left, setLeft] = useState<number | null>(null);
  useEffect(() => {
    if (!until) return;
    const tick = () =>
      setLeft(
        Math.max(
          0,
          Math.floor((new Date(until).valueOf() - Date.now()) / 1000),
        ),
      );
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [until]);
  if (!until) return null;
  return (
    <p className="notice countdown" role="status">
      {left === null
        ? "دریافت مهلت رزرو…"
        : left > 0
          ? `مهلت رزرو طبق زمان سرور: ${number(Math.floor(left / 60))} دقیقه و ${number(left % 60)} ثانیه`
          : "مهلت نمایش‌داده‌شده به پایان رسیده؛ وضعیت سفارش را دوباره از سرور بررسی کنید."}
    </p>
  );
}
