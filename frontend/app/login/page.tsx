import { Suspense } from "react";
import type { Metadata } from "next";
import { Login } from "@/features/auth/login";
import { Loading } from "@/components/ui/states";
export const metadata: Metadata = {
  title: "ورود",
  robots: { index: false, follow: false },
};
export default function Page() {
  return (
    <div className="container page">
      <Suspense fallback={<Loading />}>
        <Login />
      </Suspense>
    </div>
  );
}
