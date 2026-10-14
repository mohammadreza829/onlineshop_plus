import {
  createCipheriv,
  createDecipheriv,
  createHash,
  createHmac,
  randomBytes,
  timingSafeEqual,
} from "node:crypto";
const key = (secret: string) => createHash("sha256").update(secret).digest();
export function seal(value: unknown, secret: string) {
  const iv = randomBytes(12),
    c = createCipheriv("aes-256-gcm", key(secret), iv);
  const data = Buffer.concat([c.update(JSON.stringify(value)), c.final()]);
  return Buffer.concat([iv, c.getAuthTag(), data]).toString("base64url");
}
export function unseal<T>(
  value: string | undefined,
  secret: string,
): T | undefined {
  try {
    if (!value) return;
    const b = Buffer.from(value, "base64url"),
      c = createDecipheriv("aes-256-gcm", key(secret), b.subarray(0, 12));
    c.setAuthTag(b.subarray(12, 28));
    return JSON.parse(
      Buffer.concat([c.update(b.subarray(28)), c.final()]).toString(),
    ) as T;
  } catch {
    return;
  }
}
export function sign(value: string, secret: string) {
  return createHmac("sha256", secret).update(value).digest("base64url");
}
export function equal(a: string, b: string) {
  const x = Buffer.from(a),
    y = Buffer.from(b);
  return x.length === y.length && timingSafeEqual(x, y);
}
export function csrf(secret: string) {
  const nonce = randomBytes(32).toString("base64url");
  return nonce + "." + sign(nonce, secret);
}
export function validCSRF(token: string, secret: string) {
  const [nonce, signature] = token.split(".");
  return !!nonce && !!signature && equal(sign(nonce, secret), signature);
}
export function tokenExpiry(token: string) {
  try {
    const exp = JSON.parse(
      Buffer.from(token.split(".")[1], "base64url").toString(),
    ).exp;
    return typeof exp === "number" ? exp : 0;
  } catch {
    return 0;
  }
}
