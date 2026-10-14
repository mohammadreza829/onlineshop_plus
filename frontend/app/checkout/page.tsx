import type { Metadata } from "next";
import { AuthGate } from "@/features/auth/gate";
import { CheckoutView } from "@/features/checkout/checkout";
export const metadata: Metadata = {
  title: "ثبت سفارش",
  robots: { index: false, follow: false },
};
export default function Page() {
  return (
    <div className="container page">
      <div className="section-head">
        <div>
          <p className="eyebrow">گام بعدی / تحویل و ثبت</p>
          <h1>ثبت سفارش</h1>
        </div>
      </div>
      <AuthGate>
        <CheckoutView />
      </AuthGate>
    </div>
  );
}
