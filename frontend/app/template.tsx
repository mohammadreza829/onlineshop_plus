import type { ReactNode } from "react";
// CSS entrance only; no route-blocking loader, scroll interception or focus trap.
export default function Template({ children }: { children: ReactNode }) {
  return <div className="route-stage">{children}</div>;
}
