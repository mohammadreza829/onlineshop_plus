import { it, expect } from "vitest";
import {
  mkdtempSync,
  mkdirSync,
  copyFileSync,
  readFileSync,
  writeFileSync,
  existsSync,
  rmSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { spawnSync } from "node:child_process";
function setup(initial?: string, production = false) {
  const dir = mkdtempSync(resolve(tmpdir(), "osp-setup-"));
  mkdirSync(resolve(dir, "scripts"));
  copyFileSync(
    resolve("scripts/setup-dev.mjs"),
    resolve(dir, "scripts/setup-dev.mjs"),
  );
  if (initial !== undefined) writeFileSync(resolve(dir, ".env.local"), initial);
  const env: NodeJS.ProcessEnv = {
    ...process.env,
    NODE_ENV: production ? "production" : "development",
  };
  for (const key of [
    "APP_ORIGIN",
    "DJANGO_ORIGIN",
    "BFF_COOKIE_SECRET",
    "BFF_REDIS_URL",
    "BFF_COORDINATION",
    "PAYMENT_HOSTS",
  ])
    delete env[key];
  const run = () =>
    spawnSync(process.execPath, [resolve(dir, "scripts/setup-dev.mjs")], {
      encoding: "utf8",
      env,
    });
  return {
    dir,
    run,
    file: resolve(dir, ".env.local"),
    cleanup: () => rmSync(dir, { recursive: true, force: true }),
  };
}
it("first-run generates stable private local configuration, never prints its secret", () => {
  const s = setup();
  try {
    const result = s.run();
    expect(result.status).toBe(0);
    const text = readFileSync(s.file, "utf8");
    const secret = text.match(/^BFF_COOKIE_SECRET=(.+)$/m)![1];
    expect(secret.length).toBeGreaterThanOrEqual(32);
    expect(result.stdout + result.stderr).not.toContain(secret);
    expect(text).toContain("APP_ORIGIN=http://127.0.0.1:3000");
    expect(text).toContain("BFF_COORDINATION=memory");
    expect(s.run().status).toBe(0);
    expect(readFileSync(s.file, "utf8")).toBe(text);
  } finally {
    s.cleanup();
  }
});
it("preserves explicit origins and Redis while repairing a blank secret", () => {
  const s = setup(
    'APP_ORIGIN=http://localhost:4000\nDJANGO_ORIGIN=http://localhost:9000\nBFF_REDIS_URL=redis://localhost:6379/3\nBFF_COOKIE_SECRET=""\n',
  );
  try {
    expect(s.run().status).toBe(0);
    const text = readFileSync(s.file, "utf8");
    expect(text).toContain("APP_ORIGIN=http://localhost:4000");
    expect(text).toContain("BFF_REDIS_URL=redis://localhost:6379/3");
    expect(text).not.toContain('BFF_COOKIE_SECRET=""');
  } finally {
    s.cleanup();
  }
});
it("preserves whitespace-formatted env choices and fills an exported blank secret", () => {
  const s = setup(
    'export APP_ORIGIN = http://localhost:4000\nexport BFF_COOKIE_SECRET = ""\n',
  );
  try {
    expect(s.run().status).toBe(0);
    const text = readFileSync(s.file, "utf8");
    expect(text).toContain("export APP_ORIGIN = http://localhost:4000");
    expect(text.match(/APP_ORIGIN/g)).toHaveLength(1);
    expect(text).not.toContain('export BFF_COOKIE_SECRET = ""');
  } finally {
    s.cleanup();
  }
});
it("refuses automatic defaults in production", () => {
  const s = setup(undefined, true);
  try {
    expect(s.run().status).not.toBe(0);
    expect(existsSync(s.file)).toBe(false);
  } finally {
    s.cleanup();
  }
});

it("respects settings from other Next environment files rather than shadowing them", () => {
  const s = setup();
  try {
    writeFileSync(
      resolve(s.dir, ".env.development.local"),
      "APP_ORIGIN=http://localhost:4000\nBFF_COOKIE_SECRET=existing-secret-longer-than-thirty-two-characters\n",
    );
    expect(s.run().status).toBe(0);
    const text = readFileSync(s.file, "utf8");
    expect(text).not.toContain("APP_ORIGIN=");
    expect(text).not.toContain("BFF_COOKIE_SECRET=");
  } finally {
    s.cleanup();
  }
});
