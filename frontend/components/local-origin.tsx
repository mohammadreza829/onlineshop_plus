"use client";
import { useEffect, useSyncExternalStore, type ReactNode } from "react";
import { Loading } from "@/components/ui/states";

const subscribe = () => () => {};
const mountedSnapshot = () => true;
const serverSnapshot = () => false;
const loopback = new Set(["localhost", "127.0.0.1", "[::1]"]);
export function localDestination(
  configured: string | undefined,
  current: string,
) {
  if (!configured) return;
  try {
    const target = new URL(configured),
      source = new URL(current);
    if (
      target.origin !== configured ||
      target.protocol !== "http:" ||
      source.protocol !== "http:" ||
      !loopback.has(target.hostname) ||
      !loopback.has(source.hostname) ||
      source.port !== target.port ||
      source.origin === target.origin
    )
      return;
    target.pathname = source.pathname;
    target.search = source.search;
    target.hash = source.hash;
    return target.href;
  } catch {
    return;
  }
}
// Development only: normalize the hostname BEFORE mounting API consumers.
// Full browser navigation intentionally avoids Next's loopback URL normalization.
// Never accept extra origins at the BFF or move auth cookies between hosts.
export function LocalOrigin({
  origin,
  children,
}: {
  origin?: string;
  children: ReactNode;
}) {
  const mounted = useSyncExternalStore(
    subscribe,
    mountedSnapshot,
    serverSnapshot,
  );
  const target = mounted
    ? localDestination(origin, window.location.href)
    : undefined;
  useEffect(() => {
    if (target) window.location.replace(target);
  }, [target]);
  if (origin && (!mounted || target)) return <Loading />;
  return children;
}
