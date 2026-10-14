import "server-only";
import { configuration } from "@/lib/auth/bff";
export async function publicAPI<T>(path: string): Promise<T | undefined> {
  if (!/^(products\/|categories\/)/.test(path))
    throw new Error("Public read only");
  try {
    const c = configuration();
    const r = await fetch(c.upstream + "/api/v1/" + path, {
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(5000),
    });
    if (!r.ok) return;
    return (await r.json()) as T;
  } catch {
    return;
  }
}
export function siteURL() {
  const value = process.env.SITE_URL;
  if (!value) return;
  try {
    const u = new URL(value);
    return u.protocol === "https:" ? u : undefined;
  } catch {
    return;
  }
}
