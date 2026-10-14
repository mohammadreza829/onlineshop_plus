"use client";
import { useSyncExternalStore } from "react";
const event = "osp-storage";
function subscribe(listener: () => void) {
  window.addEventListener("storage", listener);
  window.addEventListener(event, listener);
  return () => {
    window.removeEventListener("storage", listener);
    window.removeEventListener(event, listener);
  };
}
export function useStored(key: string, session = false) {
  return useSyncExternalStore(
    subscribe,
    () => {
      try {
        return (session ? sessionStorage : localStorage).getItem(key);
      } catch {
        return null;
      }
    },
    () => null,
  );
}
export function storeSession(key: string, value: unknown) {
  try {
    if (value === null) sessionStorage.removeItem(key);
    else sessionStorage.setItem(key, JSON.stringify(value));
    window.dispatchEvent(new Event(event));
    return true;
  } catch {
    return false;
  }
}
