import { randomUUID } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { parseString } from "set-cookie-parser";
import type { Coordinator } from "./coordination";
import {
  csrf,
  equal,
  seal,
  sign,
  tokenExpiry,
  unseal,
  validCSRF,
} from "./crypto";
import { filteredQuery, routeRule } from "./routes";
import { gatewayURL } from "@/lib/api/filters";

type Pair = { access: string; refresh: string };
export type BFFConfig = {
  origin: string;
  upstream: string;
  secret: string;
  secure: boolean;
  paymentHosts: string[];
  imageHosts: string[];
  sessionName: string;
  csrfName: string;
  localDemo?: boolean;
};
export function configuration(): BFFConfig {
  const origin = process.env.APP_ORIGIN,
    upstream = process.env.DJANGO_ORIGIN,
    secret = process.env.BFF_COOKIE_SECRET;
  if (!origin || !upstream || !secret || secret.length < 32)
    throw new Error("BFF configuration missing");
  const o = new URL(origin),
    u = new URL(upstream);
  if (
    !["http:", "https:"].includes(u.protocol) ||
    u.username ||
    u.password ||
    u.pathname !== "/" ||
    u.search ||
    u.hash
  )
    throw new Error("Invalid upstream");
  if (
    o.origin !== origin ||
    (process.env.NODE_ENV === "production" &&
      o.protocol !== "https:" &&
      process.env.BFF_LOCAL_HTTP !== "1")
  )
    throw new Error("Invalid application origin");
  if (process.env.NODE_ENV === "production" && !process.env.PAYMENT_HOSTS)
    throw new Error("Explicit payment hosts required");
  const localDemo = process.env.LOCAL_DEMO === "1";
  if (
    localDemo &&
    (process.env.NODE_ENV === "production" ||
      !["127.0.0.1", "localhost"].includes(o.hostname) ||
      !["127.0.0.1", "localhost"].includes(u.hostname))
  )
    throw new Error("Local demo must run in development on loopback origins");
  return {
    localDemo,
    origin,
    upstream: u.origin,
    secret,
    secure: o.protocol === "https:",
    paymentHosts: (process.env.PAYMENT_HOSTS ?? "sandbox.zarinpal.com")
      .split(",")
      .filter(Boolean),
    imageHosts: (process.env.PRODUCT_IMAGE_HOSTS ?? "")
      .split(",")
      .filter(Boolean),
    sessionName: process.env.DJANGO_SESSION_COOKIE_NAME ?? "sessionid",
    csrfName: process.env.DJANGO_CSRF_COOKIE_NAME ?? "csrftoken",
  };
}
export function names(config: BFFConfig) {
  const prefix = config.secure ? "__Host-osp_" : "osp_";
  return {
    access: prefix + "access",
    refresh: prefix + "refresh",
    sid: prefix + "sid",
    csrf: prefix + "csrf",
    cart: prefix + "django_session",
    djangoCSRF: prefix + "django_csrf",
  };
}
export async function handleBFF(
  req: NextRequest,
  path: string,
  c: BFFConfig,
  store: Coordinator,
  fetcher: typeof fetch = fetch,
): Promise<NextResponse> {
  const n = names(c),
    changes: ((r: NextResponse) => void)[] = [];
  function set(name: string, value: string, maxAge: number) {
    changes.push((r) =>
      r.cookies.set(name, value, {
        httpOnly: true,
        secure: c.secure,
        sameSite: "lax",
        path: "/",
        maxAge,
      }),
    );
  }
  function clearAuth() {
    for (const k of [n.access, n.refresh, n.sid]) set(k, "", 0);
  }
  function response(data: unknown, status = 200) {
    const r =
      status === 204
        ? new NextResponse(null, { status })
        : NextResponse.json(data, { status });
    r.headers.set("Cache-Control", "private, no-store");
    r.headers.set("Vary", "Cookie");
    for (const change of changes) change(r);
    return r;
  }
  function fail(status: number, detail: string) {
    return response({ detail }, status);
  }
  const cookie = (name: string) => req.cookies.get(name)?.value;
  if (req.headers.get("sec-fetch-site") === "cross-site")
    return fail(403, "درخواست بین‌سایتی مجاز نیست.");
  if (path === "csrf/" && req.method === "GET") {
    const existing = cookie(n.csrf);
    const token =
      existing && validCSRF(existing, c.secret) ? existing : csrf(c.secret);
    set(n.csrf, token, 86400);
    return response({ csrf_token: token });
  }
  const rule = routeRule(path);
  if (!rule) return fail(404, "مسیر مجاز نیست.");
  if (!rule.methods.includes(req.method))
    return fail(405, "روش درخواست مجاز نیست.");
  if (!["GET", "HEAD"].includes(req.method)) {
    const origin = req.headers.get("origin"),
      token = req.headers.get("x-csrftoken") ?? "",
      expected = cookie(n.csrf) ?? "";
    if (
      origin !== c.origin ||
      !expected ||
      !equal(token, expected) ||
      !validCSRF(token, c.secret)
    )
      return fail(403, "درخواست امن معتبر نیست. صفحه را تازه کنید.");
  }
  let body: unknown;
  if (!["GET", "HEAD", "DELETE"].includes(req.method)) {
    if (Number(req.headers.get("content-length") ?? 0) > 32768)
      return fail(413, "درخواست بیش از حد بزرگ است.");
    const text = await req.text();
    if (Buffer.byteLength(text) > 32768)
      return fail(413, "درخواست بیش از حد بزرگ است.");
    if (text) {
      if (!req.headers.get("content-type")?.startsWith("application/json"))
        return fail(415, "فقط JSON پذیرفته می‌شود.");
      try {
        body = JSON.parse(text);
      } catch {
        return fail(400, "JSON نامعتبر است.");
      }
    }
  }
  async function upstream(
    p: string,
    method: string,
    data?: unknown,
    access?: string,
  ) {
    const headers = new Headers({ Accept: "application/json" });
    if (data !== undefined) headers.set("Content-Type", "application/json");
    if (access) headers.set("Authorization", "Bearer " + access);
    const cookies: string[] = [];
    for (const [local, remote] of [
      [n.cart, c.sessionName],
      [n.djangoCSRF, c.csrfName],
    ]) {
      const value = unseal<string>(cookie(local), c.secret);
      if (value && /^[a-zA-Z0-9_-]+$/.test(value))
        cookies.push(remote + "=" + value);
    }
    if (cookies.length) headers.set("Cookie", cookies.join("; "));
    const result = await fetcher(c.upstream + "/api/v1/" + p, {
      method,
      headers,
      body: data === undefined ? undefined : JSON.stringify(data),
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(15000),
    });
    // Fetch getSetCookie returns individual header values. Never split a combined header by commas.
    for (const header of result.headers.getSetCookie()) {
      const parsed = parseString(header);
      if (!parsed) continue;
      const local =
        parsed.name === c.sessionName
          ? n.cart
          : parsed.name === c.csrfName
            ? n.djangoCSRF
            : null;
      if (local) {
        const max =
          parsed.maxAge ??
          (parsed.expires
            ? Math.floor((parsed.expires.valueOf() - Date.now()) / 1000)
            : 1209600);
        set(
          local,
          max <= 0 ? "" : seal(parsed.value, c.secret),
          Math.min(Math.max(max, 0), 1209600),
        );
      }
    }
    return result;
  }
  let access = unseal<string>(cookie(n.access), c.secret),
    refresh = unseal<string>(cookie(n.refresh), c.secret),
    sid = unseal<string>(cookie(n.sid), c.secret);
  function save(pair: Pair, id: string) {
    access = pair.access;
    refresh = pair.refresh;
    sid = id;
    const now = Math.floor(Date.now() / 1000);
    set(
      n.access,
      seal(pair.access, c.secret),
      Math.max(0, Math.min(300, tokenExpiry(pair.access) - now)),
    );
    set(
      n.refresh,
      seal(pair.refresh, c.secret),
      Math.max(0, Math.min(86400, tokenExpiry(pair.refresh) - now)),
    );
    set(n.sid, seal(id, c.secret), 86400);
  }
  async function rotate() {
    if (!sid || !refresh) return false;
    const id = sid,
      old = refresh;
    return store.lock(id, async () => {
      if (await store.get("revoked:" + id)) return false;
      const key = "rotation:" + id + ":" + sign(old, c.secret),
        cached = await store.get(key);
      let pair = cached ? unseal<Pair>(cached, c.secret) : undefined;
      if (!pair) {
        const r = await upstream("auth/token/refresh/", "POST", {
          refresh: old,
        });
        if (!r.ok) {
          if (r.status >= 500 || r.status === 429)
            throw new Error("Refresh temporarily unavailable");
          return false;
        }
        pair = (await r.json()) as Pair;
        if (!pair.access || !pair.refresh) return false;
        await store.put(key, seal(pair, c.secret), 30);
      }
      save(pair, id);
      return true;
    });
  }
  try {
    if (path === "auth/otp/verify/") {
      const r = await upstream(path, "POST", body);
      const data = await r.json();
      if (!r.ok) {
        const out = response(data, r.status);
        const retry = r.headers.get("retry-after");
        if (retry) out.headers.set("Retry-After", retry);
        return out;
      }
      if (typeof data.access !== "string" || typeof data.refresh !== "string")
        return fail(502, "پاسخ ورود معتبر نیست.");
      if (sid) await store.put("revoked:" + sid, "1", 86700);
      save(data, randomUUID());
      return response({ authenticated: true });
    }
    if (sid && (await store.get("revoked:" + sid))) {
      access = undefined;
      refresh = undefined;
      clearAuth();
    }
    if (path === "auth/logout/") {
      if (sid) {
        const id = sid;
        await store.lock(id, async () => {
          // Resolve any already-completed rotation before blacklisting the current token.
          if (refresh) {
            const cached = await store.get(
              "rotation:" + id + ":" + sign(refresh, c.secret),
            );
            const pair = cached ? unseal<Pair>(cached, c.secret) : undefined;
            if (pair) {
              access = pair.access;
              refresh = pair.refresh;
            }
          }
          if (
            refresh &&
            (!access || tokenExpiry(access) < Date.now() / 1000 + 5)
          ) {
            const r = await upstream("auth/token/refresh/", "POST", {
              refresh,
            });
            if (r.ok) {
              const pair = (await r.json()) as Pair;
              access = pair.access;
              refresh = pair.refresh;
            }
          }
          await store.put("revoked:" + id, "1", 86700);
          if (access && refresh) {
            const r = await upstream(
              "auth/logout/",
              "POST",
              { refresh },
              access,
            );
            if (!r.ok && r.status !== 401)
              throw new Error("logout unavailable");
          }
        });
      }
      clearAuth();
      return response(null, 204);
    }
    if (
      !rule.public &&
      (!access || tokenExpiry(access) < Date.now() / 1000 + 15)
    ) {
      if (!(await rotate())) {
        clearAuth();
        return fail(401, "برای ادامه دوباره وارد شوید.");
      }
    }
    const query = filteredQuery(req.nextUrl.searchParams, rule.query);
    // Public catalog/auth data never needs a bearer; cart may still use a valid bearer.
    const publicCatalog = !!rule.public;
    let r = await upstream(
      path + (query ? "?" + query : ""),
      req.method,
      body,
      publicCatalog ? undefined : access,
    );
    // Only reads retry after an explicit 401. Financial mutations are never automatically replayed.
    if (
      r.status === 401 &&
      req.method === "GET" &&
      !rule.public &&
      (await rotate())
    )
      r = await upstream(
        path + (query ? "?" + query : ""),
        "GET",
        undefined,
        access,
      );
    if (r.status === 401 && !rule.public) clearAuth();
    if (r.status === 204) return response(null, 204);
    let data: unknown;
    try {
      data = await r.json();
    } catch {
      return fail(502, "پاسخ سرویس معتبر نیست.");
    }
    if (r.status >= 500)
      return fail(
        r.status === 503 ? 503 : 502,
        "سرویس موقتاً در دسترس نیست. نتیجهٔ عملیات را بررسی کنید.",
      );
    if (r.ok && /orders\/[1-9]\d*\/payment\/$/.test(path)) {
      const payment = data as { payment_url: string; demo?: boolean };
      try {
        payment.payment_url = gatewayURL(
          payment.payment_url,
          c.paymentHosts,
          c.localDemo ? c.upstream : undefined,
        );
        if (c.localDemo && new URL(payment.payment_url).origin === c.upstream)
          payment.demo = true;
      } catch {
        return fail(502, "نشانی درگاه مورد تایید نیست.");
      }
    }
    function sanitize(value: unknown): unknown {
      if (Array.isArray(value)) return value.map(sanitize);
      if (value && typeof value === "object") {
        const obj: Record<string, unknown> = {};
        for (const [key, v] of Object.entries(value)) {
          if (
            ["access", "refresh", "payment_api_url"].includes(key) ||
            (path === "orders/create/" && key === "payment_url")
          )
            continue;
          if (key === "image" && typeof v === "string") {
            try {
              const u = new URL(v, c.upstream);
              obj[key] =
                u.origin === c.upstream && u.pathname.startsWith("/media/")
                  ? "/api/media/" +
                    u.pathname
                      .slice(7)
                      .split("/")
                      .map(decodeURIComponent)
                      .map(encodeURIComponent)
                      .join("/")
                  : u.protocol === "https:" && c.imageHosts.includes(u.hostname)
                    ? u.href
                    : null;
            } catch {
              obj[key] = null;
            }
          } else if (
            (key === "next" || key === "previous") &&
            typeof v === "string"
          ) {
            try {
              const u = new URL(v);
              obj[key] = "?" + u.searchParams.toString();
            } catch {
              obj[key] = null;
            }
          } else obj[key] = sanitize(v);
        }
        return obj;
      }
      return value;
    }
    const out = response(sanitize(data), r.status);
    const retry = r.headers.get("retry-after");
    if (retry) out.headers.set("Retry-After", retry);
    return out;
  } catch {
    if (path === "auth/logout/") clearAuth();
    return fail(
      503,
      "ارتباط با سرویس کامل نشد؛ نتیجهٔ عملیات را پیش از تکرار بررسی کنید.",
    );
  }
}
