"use client";
import { ErrorNotice } from "@/components/ui/states";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <div className="container page">
      <h1>دریافت صفحه کامل نشد.</h1>
      <ErrorNotice
        error={
          new Error(
            "لطفاً دوباره تلاش کنید؛ وضعیت سفارش را پیش از تکرار خرید بررسی کنید.",
          )
        }
        retry={reset}
      />
    </div>
  );
}
