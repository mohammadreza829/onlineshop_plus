import { ApiError } from "./errors";
let csrfToken: string | undefined;
let bootstrap: Promise<string> | undefined;
async function csrf() {
  if (csrfToken) return csrfToken;
  bootstrap ??= fetch("/api/shop/csrf/", {
    cache: "no-store",
    credentials: "same-origin",
  })
    .then(async (r) => {
      if (!r.ok) throw new ApiError(r.status, null);
      const token: unknown = (await r.json()).csrf_token;
      if (typeof token !== "string" || !token)
        throw new ApiError(502, { detail: "پاسخ اعتبارسنجی معتبر نیست." });
      return token;
    })
    .finally(() => {
      bootstrap = undefined;
    });
  csrfToken = await bootstrap;
  return csrfToken;
}
export function resetCSRF() {
  csrfToken = undefined;
}
export async function api<T>(
  path: string,
  options: { method?: string; body?: unknown; signal?: AbortSignal } = {},
): Promise<T> {
  const method = options.method ?? "GET",
    headers = new Headers({ Accept: "application/json" });
  const mutation = !["GET", "HEAD"].includes(method);
  if (mutation) headers.set("X-CSRFToken", await csrf());
  if (options.body !== undefined)
    headers.set("Content-Type", "application/json");
  const send = () =>
    fetch("/api/shop/" + path, {
      method,
      headers,
      body:
        options.body === undefined ? undefined : JSON.stringify(options.body),
      cache: "no-store",
      credentials: "same-origin",
      signal: options.signal ?? AbortSignal.timeout(25000),
    });
  let r: Response;
  try {
    r = await send();
    if (
      mutation &&
      r.status === 403 &&
      r.headers.get("X-BFF-Rejected-Before-Upstream") === "csrf"
    ) {
      // Never retry timeouts, gateway errors, upstream 403s or ambiguous writes.
      // The BFF guarantees this specific failure never reached Django.
      resetCSRF();
      headers.set("X-CSRFToken", await csrf());
      r = await send();
    }
  } catch (e) {
    if (options.signal?.aborted || e instanceof ApiError) throw e;
    throw new ApiError(0, {
      detail: "ارتباط قطع شد؛ پیش از تکرار عملیات سفارش‌ها را بررسی کنید.",
    });
  }
  const data =
    r.status === 204
      ? undefined
      : await r.json().catch(() => ({ detail: "پاسخ نامعتبر" }));
  if (!r.ok)
    throw new ApiError(
      r.status,
      data,
      Number(r.headers.get("retry-after") ?? 0),
    );
  return data as T;
}
