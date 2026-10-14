// Explicit Windows-compatible laptop profile. Never rewrites existing .env files.
import { randomBytes } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn, spawnSync } from "node:child_process";

if (process.env.NODE_ENV === "production") {
  console.error("dev:local is development-only; refusing production mode.");
  process.exit(1);
}
const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const data = resolve(root, "..", ".local");
mkdirSync(data, { recursive: true });
const secretPath = resolve(data, "bff-secret");
try {
  writeFileSync(secretPath, randomBytes(48).toString("base64url"), {
    flag: "wx",
    mode: 0o600,
  });
} catch (error) {
  if (error.code !== "EEXIST") throw error;
}
const secret = readFileSync(secretPath, "utf8").trim();
if (secret.length < 32)
  throw new Error("Invalid local BFF secret (not printed).");
const env = {
  ...process.env,
  NODE_ENV: "development",
  APP_ORIGIN: "http://127.0.0.1:3000",
  DJANGO_ORIGIN: "http://127.0.0.1:8000",
  BFF_COOKIE_SECRET: secret,
  BFF_REDIS_URL: "",
  BFF_COORDINATION: "memory",
  BFF_LOCAL_HTTP: "1",
  PAYMENT_HOSTS: "sandbox.zarinpal.com",
};
for (const script of ["prepare-assets.mjs", "doctor.mjs"]) {
  const result = spawnSync(
    process.execPath,
    [resolve(root, "scripts", script)],
    {
      cwd: root,
      env,
      stdio: "inherit",
    },
  );
  if (result.error || result.status !== 0) process.exit(result.status ?? 1);
}
console.log(
  "Laptop profile: http://127.0.0.1:3000 → Django :8000; no Redis required.",
);
const child = spawn(
  process.execPath,
  [
    resolve(root, "node_modules/next/dist/bin/next"),
    "dev",
    "--hostname",
    "127.0.0.1",
    "--port",
    "3000",
  ],
  { cwd: root, env, stdio: "inherit" },
);
child.on("error", () => {
  console.error("Could not start Next. Install frontend dependencies first.");
  process.exitCode = 1;
});
child.on("exit", (code) => {
  process.exitCode = code ?? 1;
});
for (const signal of ["SIGINT", "SIGTERM"])
  process.on(signal, () => child.kill(signal));
