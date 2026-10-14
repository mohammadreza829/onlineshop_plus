import type { Metadata } from "next";
import { AuthGate } from "@/features/auth/gate";
import { AccountNav } from "@/features/account/nav";
export const metadata: Metadata = {
  title: "حساب کاربری",
  robots: { index: false, follow: false },
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="container page">
      <div className="section-head">
        <div>
          <p className="eyebrow">فضای شخصی شما</p>
          <h1>حساب کاربری</h1>
        </div>
      </div>
      <AuthGate>
        <div className="account-shell">
          <AccountNav />
          <section className="account-content">{children}</section>
        </div>
      </AuthGate>
    </div>
  );
}
