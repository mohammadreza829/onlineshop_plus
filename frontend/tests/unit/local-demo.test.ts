import { describe, expect, it } from "vitest";
import { gatewayURL } from "../../lib/api/filters";

describe("local demo gateway boundary", () => {
  const url = "http://127.0.0.1:8000/payment/demo/DEMO-" + "a".repeat(32) + "/";
  it("requires an explicit loopback demo origin for HTTP", () => {
    expect(() => gatewayURL(url, ["127.0.0.1"])).toThrow();
    expect(gatewayURL(url, [], "http://127.0.0.1:8000")).toBe(url);
  });
  it("rejects other paths, origins and query parameters", () => {
    for (const bad of [
      url.replace("/demo/", "/verify/"),
      url.replace("8000", "9000"),
      url + "?secret=x",
    ])
      expect(() => gatewayURL(bad, [], "http://127.0.0.1:8000")).toThrow();
    expect(() =>
      gatewayURL(
        url.replace("127.0.0.1", "evil.example"),
        [],
        "http://evil.example:8000",
      ),
    ).toThrow();
  });
});
