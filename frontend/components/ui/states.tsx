"use client";
import Link from "next/link";
import { PackageOpen, RefreshCw } from "lucide-react";
export function Empty({
  title = "هنوز چیزی اینجا نیست",
  description,
  href,
  label = "مشاهدهٔ فروشگاه",
}: {
  title?: string;
  description: string;
  href?: string;
  label?: string;
}) {
  return (
    <div className="empty">
      <PackageOpen size={36} strokeWidth={1} />
      <h2>{title}</h2>
      <p>{description}</p>
      {href && (
        <Link className="button secondary" href={href}>
          {label}
        </Link>
      )}
    </div>
  );
}
export function ErrorNotice({
  error,
  retry,
}: {
  error: unknown;
  retry?: () => void;
}) {
  return (
    <div className="notice error" role="alert">
      <p>
        {error instanceof Error ? error.message : "دریافت اطلاعات ممکن نشد."}
      </p>
      {retry && (
        <button className="text-link" onClick={retry}>
          <RefreshCw size={16} />
          تلاش دوباره
        </button>
      )}
    </div>
  );
}
export function Loading() {
  return (
    <p className="loading-text" role="status">
      در حال دریافت اطلاعات…
    </p>
  );
}
