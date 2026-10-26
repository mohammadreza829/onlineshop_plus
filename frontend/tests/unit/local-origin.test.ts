import { describe, expect, it } from "vitest";
import { localDestination } from "@/components/local-origin";
describe("development loopback navigation", () => {
  it("keeps path, query and fragment on configured loopback origin", () => {
    expect(
      localDestination(
        "http://localhost:3000",
        "http://127.0.0.1:3000/payment/result?order=1#status",
      ),
    ).toBe("http://localhost:3000/payment/result?order=1#status");
  });
  it.each([
    "http://localhost:3000/login",
    "http://evil.test:3000/login",
    "http://127.0.0.1:3001/login",
    "https://127.0.0.1:3000/login",
  ])("never loops or guesses ports for %s", (url) => {
    expect(localDestination("http://localhost:3000", url)).toBeUndefined();
  });
  it("never redirects to a public host or invalid origin", () => {
    expect(
      localDestination("http://evil.test:3000", "http://127.0.0.1:3000/login"),
    ).toBeUndefined();
    expect(
      localDestination("http://localhost:3000/", "http://127.0.0.1:3000/login"),
    ).toBeUndefined();
  });
});
