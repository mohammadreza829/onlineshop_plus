import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, resetCSRF } from "@/lib/api/client";

const json = (value: unknown, status = 200, headers = {}) =>
  new Response(JSON.stringify(value), { status, headers });
beforeEach(() => resetCSRF());
afterEach(() => vi.unstubAllGlobals());

describe("CSRF recovery without ambiguous mutation replay", () => {
  it("renews a stale token and retries only the BFF pre-forward rejection once", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(json({ csrf_token: "old" }))
      .mockResolvedValueOnce(
        json({ code: "bff_csrf_rejected" }, 403, {
          "X-BFF-Rejected-Before-Upstream": "csrf",
        }),
      )
      .mockResolvedValueOnce(json({ csrf_token: "new" }))
      .mockResolvedValueOnce(json({ id: 1 }));
    vi.stubGlobal("fetch", fetcher);
    expect(
      await api("orders/create/", { method: "POST", body: { address_id: 1 } }),
    ).toEqual({ id: 1 });
    expect(fetcher).toHaveBeenCalledTimes(4);
    expect(fetcher.mock.calls[3][1].headers.get("X-CSRFToken")).toBe("new");
    expect(fetcher.mock.calls[3][1].body).toBe('{"address_id":1}');
  });
  it.each([403, 401, 429, 500, 503])(
    "never retries an upstream %s",
    async (status) => {
      const fetcher = vi
        .fn()
        .mockResolvedValueOnce(json({ csrf_token: "token" }))
        .mockResolvedValueOnce(json({ detail: "failure" }, status));
      vi.stubGlobal("fetch", fetcher);
      await expect(
        api("orders/create/", { method: "POST" }),
      ).rejects.toMatchObject({ status });
      expect(fetcher).toHaveBeenCalledTimes(2);
    },
  );
  it("does not retry network ambiguity", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(json({ csrf_token: "token" }))
      .mockRejectedValueOnce(new TypeError("network"));
    vi.stubGlobal("fetch", fetcher);
    await expect(
      api("orders/create/", { method: "POST" }),
    ).rejects.toMatchObject({ status: 0 });
    expect(fetcher).toHaveBeenCalledTimes(2);
  });
  it("stops after one CSRF renewal", async () => {
    const fetcher = vi
      .fn()
      .mockImplementation((url: string) =>
        Promise.resolve(
          url.endsWith("csrf/")
            ? json({ csrf_token: "token" })
            : json({ code: "bff_csrf_rejected" }, 403, {
                "X-BFF-Rejected-Before-Upstream": "csrf",
              }),
        ),
      );
    vi.stubGlobal("fetch", fetcher);
    await expect(api("cart/", { method: "POST" })).rejects.toMatchObject({
      status: 403,
    });
    expect(fetcher).toHaveBeenCalledTimes(4);
  });
});
