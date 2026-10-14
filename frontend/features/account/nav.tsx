"use client";
import Link from "next/link";
import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { accountLinks } from "@/config/site";
export function AccountNav() {
  const path = usePathname();
  const nav = useRef<HTMLElement>(null);
  useEffect(() => {
    const element = nav.current;
    const active = element?.querySelector<HTMLElement>('[aria-current="page"]');
    if (element && active && element.scrollWidth > element.clientWidth) {
      const frame = element.getBoundingClientRect();
      const item = active.getBoundingClientRect();
      if (item.left < frame.left) element.scrollLeft += item.left - frame.left;
      else if (item.right > frame.right)
        element.scrollLeft += item.right - frame.right;
    }
  }, [path]);
  return (
    <nav ref={nav} className="account-nav" aria-label="حساب کاربری">
      {accountLinks.map(([url, label]) => (
        <Link
          key={url}
          href={url}
          aria-current={path === url ? "page" : undefined}
        >
          {label}
        </Link>
      ))}
    </nav>
  );
}
