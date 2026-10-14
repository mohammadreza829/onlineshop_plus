import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
for (const name of [
  ".env.development.local",
  ".env.local",
  ".env.development",
  ".env",
]) {
  const p = resolve(root, name);
  if (existsSync(p)) process.loadEnvFile(p);
}
const required = ["APP_ORIGIN", "DJANGO_ORIGIN", "BFF_COOKIE_SECRET"];
const missing = required.filter((k) => !process.env[k]);
if (missing.length || (process.env.BFF_COOKIE_SECRET ?? "").length < 32) {
  console.error(
    "Development configuration incomplete. Run npm run setup:dev; set a secret of at least 32 characters. No secrets printed.",
  );
  process.exit(1);
}
try {
  const app = new URL(process.env.APP_ORIGIN);
  if (
    !["http:", "https:"].includes(app.protocol) ||
    app.origin !== process.env.APP_ORIGIN
  )
    throw new Error("invalid");
} catch {
  console.error(
    "APP_ORIGIN must be an HTTP(S) origin with no trailing slash. No secrets printed.",
  );
  process.exit(1);
}
try {
  const u = new URL(process.env.DJANGO_ORIGIN);
  if (
    !["http:", "https:"].includes(u.protocol) ||
    u.username ||
    u.password ||
    u.pathname !== "/" ||
    u.search ||
    u.hash
  )
    throw new Error("invalid");
  const r = await fetch(new URL("/api/v1/client-options/", u), {
    redirect: "error",
    signal: AbortSignal.timeout(2500),
  });
  if (r.ok) console.log("Django API is reachable.");
  else
    console.warn(
      "Django replied but API readiness is not confirmed (HTTP " +
        r.status +
        ").",
    );
} catch {
  console.warn(
    "Django is not reachable. Start the LOCAL backend in a second terminal: python manage.py runserver 127.0.0.1:8000",
  );
}
console.log(
  "Browser origin must exactly match APP_ORIGIN in your local configuration. Both Django and Next must be running.",
);

if (process.env.BFF_REDIS_URL) {
  const { createClient } = await import("redis");
  const client = createClient({
    url: process.env.BFF_REDIS_URL,
    socket: { connectTimeout: 2000, reconnectStrategy: false },
  });
  client.on("error", () => {});
  try {
    await client.connect();
    await client.ping();
    console.log("BFF Redis is reachable.");
  } catch {
    console.warn(
      "Configured BFF Redis is unavailable. Start it, or explicitly use BFF_REDIS_URL= and BFF_COORDINATION=memory for SINGLE-PROCESS DEVELOPMENT only.",
    );
  } finally {
    if (client.isOpen) client.destroy();
  }
} else if (process.env.BFF_COORDINATION !== "memory") {
  console.warn(
    "No BFF coordinator configured. Development requires explicit BFF_COORDINATION=memory; production requires shared Redis.",
  );
}
