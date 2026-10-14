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
      return (await r.json()).csrf_token as string;
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
  if (method !== "GET") headers.set("X-CSRFToken", await csrf());
  if (options.body !== undefined)
    headers.set("Content-Type", "application/json");
  let r: Response;
  try {
    r = await fetch("/api/shop/" + path, {
      method,
      headers,
      body:
        options.body === undefined ? undefined : JSON.stringify(options.body),
      cache: "no-store",
      credentials: "same-origin",
      signal: options.signal ?? AbortSignal.timeout(25000),
    });
  } catch (e) {
    if (options.signal?.aborted) throw e;
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
