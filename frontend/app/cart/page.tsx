import { PurchaseSteps } from "@/components/ui/purchase-steps";
import type { Metadata } from "next";
import { CartView } from "@/features/cart/cart";
export const metadata: Metadata = {
  title: "سبد خرید",
  robots: { index: false, follow: false },
};
export default function Page() {
  return (
    <div className="container page">
      <PurchaseSteps current={0} />
      <div className="section-head">
        <div>
          <p className="eyebrow">انتخاب‌های شما</p>
          <h1>سبد خرید</h1>
        </div>
      </div>
      <CartView />
    </div>
  );
}
