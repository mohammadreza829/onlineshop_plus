import { describe, expect, it } from "vitest";
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, rmSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { tmpdir } from "node:os";
import { spawnSync } from "node:child_process";
function fixture() {
  const temp = mkdtempSync(join(tmpdir(), "shop-laptop-")), root = join(temp, "frontend");
  for (const dir of ["scripts", "node_modules/next/dist/bin"]) mkdirSync(join(root, dir), { recursive: true });
  writeFileSync(join(root, "scripts/dev-local.mjs"), readFileSync(resolve("scripts/dev-local.mjs")));
  for (const name of ["prepare-assets.mjs", "doctor.mjs"]) writeFileSync(join(root, "scripts", name), "");
  writeFileSync(join(root, "node_modules/next/dist/bin/next"), `console.log(JSON.stringify({app:process.env.APP_ORIGIN,django:process.env.DJANGO_ORIGIN,redis:process.env.BFF_REDIS_URL,coord:process.env.BFF_COORDINATION,secretLength:process.env.BFF_COOKIE_SECRET.length,mode:process.env.NODE_ENV}));`);
  const run = (env: Record<string, string> = {}) => spawnSync(process.execPath, [join(root, "scripts/dev-local.mjs")], { cwd: root, encoding: "utf8", timeout: 10000, env: { ...process.env, NODE_ENV: "development", ...env } });
  return { temp, root, run, clean: () => rmSync(temp, { recursive: true, force: true }) };
}
describe("explicit laptop frontend profile", () => {
  it("uses loopback and memory despite stale configuration, without rewriting env or printing secrets", () => {
    const f = fixture();
    try {
      const source = "APP_ORIGIN=https://existing.invalid\n";
      writeFileSync(join(f.root, ".env.local"), source);
      const result = f.run({ APP_ORIGIN: "https://stale.invalid", DJANGO_ORIGIN: "https://stale.invalid", BFF_REDIS_URL: "redis://stale.invalid", BFF_COORDINATION: "redis" });
      expect(result.status).toBe(0);
      const values = JSON.parse(result.stdout.trim().split("\n").at(-1)!);
      expect(values).toMatchObject({ app: "http://127.0.0.1:3000", django: "http://127.0.0.1:8000", redis: "", coord: "memory", mode: "development" });
      expect(values.secretLength).toBeGreaterThan(32);
      const secret = readFileSync(join(f.temp, ".local/bff-secret"), "utf8");
      expect(result.stdout + result.stderr).not.toContain(secret);
      expect(readFileSync(join(f.root, ".env.local"), "utf8")).toBe(source);
      expect(f.run().status).toBe(0);
      expect(readFileSync(join(f.temp, ".local/bff-secret"), "utf8")).toBe(secret);
    } finally { f.clean(); }
  });
  it("refuses production before creating private runtime files", () => {
    const f = fixture();
    try { expect(f.run({ NODE_ENV: "production" }).status).toBe(1); expect(existsSync(join(f.temp, ".local"))).toBe(false); }
    finally { f.clean(); }
  });
});

describe("SSR and BFF product images", () => {
  it("rewrites nested list images through the same-origin proxy", async () => {
    const { mapProductImages } = await import("@/lib/api/images");
    expect(mapProductImages({ results: [{ image: "http://127.0.0.1:8000/media/products/demo.webp" }] }, "http://127.0.0.1:8000", [])).toEqual({ results: [{ image: "/api/media/products/demo.webp" }] });
  });
  it("rejects untrusted image hosts and invalid URLs", async () => {
    const { productImageURL } = await import("@/lib/api/images");
    expect(productImageURL("https://untrusted.invalid/a.webp", "http://127.0.0.1:8000", [])).toBeNull();
    expect(productImageURL("javascript:alert(1)", "http://127.0.0.1:8000", [])).toBeNull();
    expect(productImageURL("https://cdn.test/a.webp", "http://127.0.0.1:8000", ["cdn.test"])).toBe("https://cdn.test/a.webp");
  });
});
