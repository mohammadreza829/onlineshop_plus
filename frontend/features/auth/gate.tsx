"use client";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Suspense, type ReactNode } from "react";
import { internalRedirect } from "@/lib/api/filters";
import { useApi } from "@/lib/api/hooks";
import type { User } from "@/lib/api/types";
import { Loading, ErrorNotice } from "@/components/ui/states";
import { ApiError } from "@/lib/api/errors";
export function AuthGate({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<Loading />}>
      <Gate>{children}</Gate>
    </Suspense>
  );
}
function Gate({ children }: { children: ReactNode }) {
  const q = useApi<User>("me/"),
    path = usePathname(),
    search = useSearchParams(),
    destination = internalRedirect(
      path + (search.size ? "?" + search.toString() : ""),
    );
  if (q.isPending) return <Loading />;
  if (q.isError)
    return q.error instanceof ApiError && q.error.status === 401 ? (
      <div className="empty">
        <h2>حساب شما، انتخاب‌های شما.</h2>
        <p>برای ادامه، با شمارهٔ همراه خود وارد شوید.</p>
        <Link
          className="button"
          href={"/login?next=" + encodeURIComponent(destination)}
        >
          ورود به حساب
        </Link>
      </div>
    ) : (
      <ErrorNotice error={q.error} retry={() => q.refetch()} />
    );
  return children;
}
