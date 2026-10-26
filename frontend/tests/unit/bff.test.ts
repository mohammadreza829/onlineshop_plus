import { describe, it, expect, vi } from "vitest";
import { NextRequest } from "next/server";
import { handleBFF, names, type BFFConfig } from "@/lib/auth/bff";
import { MemoryCoordinator } from "@/lib/auth/coordination";
import { csrf, seal, unseal } from "@/lib/auth/crypto";
import { routeRule } from "@/lib/auth/routes";
const c: BFFConfig = {
    origin: "https://shop.test",
    upstream: "http://django.test",
    secret: "test-only-key-".repeat(4),
    secure: true,
    paymentHosts: ["sandbox.zarinpal.com"],
    imageHosts: [],
    sessionName: "sessionid",
    csrfName: "csrftoken",
  },
  n = names(c);
const jwt = (seconds: number) =>
  "header." +
  Buffer.from(
    JSON.stringify({ exp: Math.floor(Date.now() / 1000) + seconds }),
  ).toString("base64url") +
  ".test";
function request(
  path: string,
  method = "GET",
  body?: unknown,
  jar: Record<string, string> = {},
  origin = c.origin,
) {
  const token = csrf(c.secret);
  const cookies = { ...jar, [n.csrf]: token };
  return new NextRequest(c.origin + "/api/shop/" + path, {
    method,
    headers: {
      Origin: origin,
      "Content-Type": "application/json",
      "X-CSRFToken": token,
      Cookie: Object.entries(cookies)
        .map(([k, v]) => k + "=" + v)
        .join("; "),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}
function result(data: unknown, status = 200) {
  return new Response(status === 204 ? null : JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
const jar = (access = jwt(300), refresh = jwt(86400)) => ({
  [n.access]: seal(access, c.secret),
  [n.refresh]: seal(refresh, c.secret),
  [n.sid]: seal("session1", c.secret),
});
describe("limited BFF security and auth", () => {
  it("bootstraps signed CSRF as HttpOnly, Secure, host-only cookie", async () => {
    const r = await handleBFF(
      request("csrf/"),
      "csrf/",
      c,
      new MemoryCoordinator(),
    );
    expect(r.status).toBe(200);
    const body = await r.json();
    expect(body.csrf_token).toBeTruthy();
    const h = r.headers.getSetCookie().join(";");
    expect(h).toContain("HttpOnly");
    expect(h).toContain("Secure");
    expect(h).not.toContain("Domain=");
  });
  it.each(["https://evil.test", "null", ""])(
    "rejects mutation Origin %s even with valid token",
    async (origin) => {
      const fetcher = vi.fn();
      const r = await handleBFF(
        request("cart/", "POST", { product_id: 1 }, {}, origin),
        "cart/",
        c,
        new MemoryCoordinator(),
        fetcher,
      );
      expect(r.status).toBe(403);
      expect((await r.json()).code).toBe("bff_origin_mismatch");
      expect(r.headers.get("X-BFF-Rejected-Before-Upstream")).toBeNull();
      expect(fetcher).not.toHaveBeenCalled();
    },
  );
  it("rejects missing and tampered CSRF", async () => {
    const req = request("cart/", "POST", {});
    req.headers.set("X-CSRFToken", "tampered");
    const fetcher = vi.fn();
    const r = await handleBFF(
      req,
      "cart/",
      c,
      new MemoryCoordinator(),
      fetcher,
    );
    expect(r.status).toBe(403);
    expect(r.headers.get("X-BFF-Rejected-Before-Upstream")).toBe("csrf");
    expect(fetcher).not.toHaveBeenCalled();
  });
  it("blocks cross-site reads", async () => {
    const req = request("me/");
    req.headers.set("sec-fetch-site", "cross-site");
    expect(
      (await handleBFF(req, "me/", c, new MemoryCoordinator(), vi.fn())).status,
    ).toBe(403);
  });
  it.each([
    "staff/sales/",
    "https://evil.test/",
    "../me/",
    "products/%2fadmin/",
    "orders/0/",
  ])("has no proxy capability for %s", async (path) => {
    expect(routeRule(path)).toBeUndefined();
    expect(
      (
        await handleBFF(
          request("invalid/"),
          path,
          c,
          new MemoryCoordinator(),
          vi.fn(),
        )
      ).status,
    ).toBe(404);
  });
  it("rejects unsupported method", async () =>
    expect(
      (
        await handleBFF(
          request("orders/1/", "POST", {}),
          "orders/1/",
          c,
          new MemoryCoordinator(),
          vi.fn(),
        )
      ).status,
    ).toBe(405));
  it("does not forward arbitrary URL or client credentials/query", async () => {
    const fetcher = vi.fn<typeof fetch>(async () => result({ results: [] }));
    const r = await handleBFF(
      request("products/?search=a&url=https://evil.test"),
      "products/",
      c,
      new MemoryCoordinator(),
      fetcher,
    );
    expect(r.status).toBe(200);
    expect(fetcher.mock.calls[0][0]).toBe(
      "http://django.test/api/v1/products/?search=a",
    );
  });
  it("preserves multiple Django cookies without commas/domain/name collision", async () => {
    const fetcher = vi.fn<typeof fetch>(async () => {
      const r = result({ items: [] });
      r.headers.append(
        "Set-Cookie",
        "sessionid=abc123; Path=/; HttpOnly; SameSite=Lax",
      );
      r.headers.append(
        "Set-Cookie",
        "csrftoken=xyz456; Expires=Thu, 01 Jan 2037 00:00:00 GMT; Domain=django.test; Path=/",
      );
      r.headers.append("Set-Cookie", "admin=never; Path=/");
      return r;
    });
    const r = await handleBFF(
      request("cart/"),
      "cart/",
      c,
      new MemoryCoordinator(),
      fetcher,
    );
    expect(r.headers.getSetCookie()).toHaveLength(2);
    expect(unseal(r.cookies.get(n.cart)?.value, c.secret)).toBe("abc123");
    expect(unseal(r.cookies.get(n.djangoCSRF)?.value, c.secret)).toBe("xyz456");
    expect(r.headers.getSetCookie().join(";")).not.toContain("Domain=");
  });
  it("forwards only decoded namespaced cart cookie", async () => {
    const fetcher = vi.fn<typeof fetch>(async () => result({ items: [] }));
    await handleBFF(
      request("cart/", "GET", undefined, {
        [n.cart]: seal("cart123", c.secret),
        sessionid: "injected",
        other: "private",
      }),
      "cart/",
      c,
      new MemoryCoordinator(),
      fetcher,
    );
    const h = new Headers(fetcher.mock.calls[0][1]?.headers);
    expect(h.get("cookie")).toBe("sessionid=cart123");
  });
  it("never returns token pair to browser JSON and sets expiring cookies", async () => {
    const pair = { access: jwt(300), refresh: jwt(86400) },
      fetcher = vi.fn<typeof fetch>(async () => result(pair));
    const r = await handleBFF(
      request("auth/otp/verify/", "POST", {
        phone: "09121234567",
        code: "123456",
      }),
      "auth/otp/verify/",
      c,
      new MemoryCoordinator(),
      fetcher,
    );
    expect(await r.json()).toEqual({ authenticated: true });
    expect(r.cookies.get(n.access)?.value).not.toBe(pair.access);
    expect(unseal(r.cookies.get(n.refresh)?.value, c.secret)).toBe(
      pair.refresh,
    );
    expect(r.headers.getSetCookie().join(";")).toContain("HttpOnly");
  });
  it("single-flights ten concurrent refresh requests and rotates BOTH tokens", async () => {
    const old = jwt(-20),
      refresh = jwt(86400),
      pair = { access: jwt(290), refresh: jwt(86390) },
      store = new MemoryCoordinator();
    let count = 0;
    const fetcher = vi.fn<typeof fetch>(
      async (url: string | URL | Request, init?: RequestInit) => {
        if (String(url).includes("token/refresh")) {
          count++;
          await new Promise((resolve) => setTimeout(resolve, 10));
          return result(pair);
        }
        expect(new Headers(init?.headers).get("authorization")).toBe(
          "Bearer " + pair.access,
        );
        return result({ id: 1 });
      },
    );
    const responses = await Promise.all(
      Array.from({ length: 10 }, () =>
        handleBFF(
          request("me/", "GET", undefined, jar(old, refresh)),
          "me/",
          c,
          store,
          fetcher,
        ),
      ),
    );
    expect(count).toBe(1);
    expect(responses.every((r) => r.status === 200)).toBe(true);
    for (const r of responses)
      expect(unseal(r.cookies.get(n.refresh)?.value, c.secret)).toBe(
        pair.refresh,
      );
  });
  it("does not loop on failed refresh", async () => {
    let count = 0;
    const fetcher = vi.fn<typeof fetch>(async () => {
      count++;
      return result({ detail: "bad" }, 401);
    });
    const r = await handleBFF(
      request("me/", "GET", undefined, jar(jwt(-1))),
      "me/",
      c,
      new MemoryCoordinator(),
      fetcher,
    );
    expect(r.status).toBe(401);
    expect(count).toBe(1);
    expect(r.headers.getSetCookie().join(";")).toContain("Max-Age=0");
  });
  it("never automatically replays checkout after 401", async () => {
    const fetcher = vi.fn<typeof fetch>(async () =>
      result({ detail: "bad" }, 401),
    );
    const r = await handleBFF(
      request("orders/create/", "POST", { address_id: 1 }, jar()),
      "orders/create/",
      c,
      new MemoryCoordinator(),
      fetcher,
    );
    expect(r.status).toBe(401);
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it("logout tombstone prevents stale parallel refresh restoring auth", async () => {
    const store = new MemoryCoordinator(),
      cookies = jar();
    const fetcher = vi.fn<typeof fetch>(async () => result(null, 204));
    const r = await handleBFF(
      request("auth/logout/", "POST", {}, cookies),
      "auth/logout/",
      c,
      store,
      fetcher,
    );
    expect(r.status).toBe(204);
    const later = await handleBFF(
      request("me/", "GET", undefined, cookies),
      "me/",
      c,
      store,
      fetcher,
    );
    expect(later.status).toBe(401);
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it("rejects off-host gateway URL", async () => {
    const r = await handleBFF(
      request("orders/1/payment/", "POST", {}, jar()),
      "orders/1/payment/",
      c,
      new MemoryCoordinator(),
      async () => result({ payment_url: "https://evil.test" }),
    );
    expect(r.status).toBe(502);
  });
  it("does not leak upstream traceback/HTML", async () => {
    const r = await handleBFF(
      request("products/"),
      "products/",
      c,
      new MemoryCoordinator(),
      async () => new Response("<html>SECRET</html>", { status: 500 }),
    );
    expect(r.status).toBe(502);
    expect(await r.text()).not.toContain("SECRET");
  });
  it("passes Retry-After and no-store on controlled errors", async () => {
    const r = await handleBFF(
      request("auth/otp/request/", "POST", {}),
      "auth/otp/request/",
      c,
      new MemoryCoordinator(),
      async () =>
        new Response(JSON.stringify({ detail: "slow" }), {
          status: 429,
          headers: { "Retry-After": "60" },
        }),
    );
    expect(r.headers.get("Retry-After")).toBe("60");
    expect(r.headers.get("Cache-Control")).toContain("no-store");
  });
  it("rejects oversized JSON before upstream", async () =>
    expect(
      (
        await handleBFF(
          request("cart/", "POST", { x: "a".repeat(40000) }),
          "cart/",
          c,
          new MemoryCoordinator(),
          vi.fn(),
        )
      ).status,
    ).toBe(413));
});

it("an expired access cookie does not break the cookie-bound public cart", async () => {
  const fetcher = vi.fn<typeof fetch>(async (_url, init) => {
    expect(new Headers(init?.headers).has("authorization")).toBe(false);
    return result({ items: [] });
  });
  const r = await handleBFF(
    request("cart/", "GET", undefined, jar(jwt(-10))),
    "cart/",
    c,
    new MemoryCoordinator(),
    fetcher,
  );
  expect(r.status).toBe(200);
  expect(fetcher).toHaveBeenCalledTimes(1);
});

it("preserves valid CSRF bootstrap across tabs", async () => {
  const req = request("csrf/"),
    expected = req.cookies.get(n.csrf)?.value;
  const r = await handleBFF(req, "csrf/", c, new MemoryCoordinator());
  expect((await r.json()).csrf_token).toBe(expected);
});
it("does not destroy auth cookies on transient refresh outage", async () => {
  const r = await handleBFF(
    request("me/", "GET", undefined, jar(jwt(-1))),
    "me/",
    c,
    new MemoryCoordinator(),
    async () => result({ detail: "unavailable" }, 503),
  );
  expect(r.status).toBe(503);
  expect(r.headers.getSetCookie().join(";")).not.toContain("Max-Age=0");
});
