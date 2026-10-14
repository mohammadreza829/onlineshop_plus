import { Suspense } from "react";
import type { Metadata } from "next";
import { AuthGate } from "@/features/auth/gate";
import { PaymentResult } from "@/features/checkout/result";
import { Loading } from "@/components/ui/states";
export const metadata: Metadata = {
  title: "وضعیت سفارش و پرداخت",
  robots: { index: false, follow: false },
};
export default function Page() {
  return (
    <div className="container page">
      <AuthGate>
        <Suspense fallback={<Loading />}>
          <PaymentResult />
        </Suspense>
      </AuthGate>
    </div>
  );
}
