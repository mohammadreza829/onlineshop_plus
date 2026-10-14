import { it, expect } from "vitest";
import { randomUUID } from "node:crypto";
import { RedisCoordinator } from "@/lib/auth/coordination";
it.skipIf(!process.env.REDIS_QA_URL)(
  "real Redis coordinates independent clients without overlapping refresh sections",
  async () => {
    const url = process.env.REDIS_QA_URL!,
      a = new RedisCoordinator(url),
      b = new RedisCoordinator(url),
      id = "qa-" + randomUUID();
    let active = 0,
      max = 0;
    await Promise.all(
      Array.from({ length: 12 }, (_, i) =>
        (i % 2 ? a : b).lock(id, async () => {
          active++;
          max = Math.max(max, active);
          await new Promise((r) => setTimeout(r, 5));
          active--;
        }),
      ),
    );
    expect(max).toBe(1);
    await a.put(id, "test-only", 1);
    expect(await b.get(id)).toBe("test-only");
    await new Promise((r) => setTimeout(r, 1100));
    expect(await b.get(id)).toBeNull();
  },
);
