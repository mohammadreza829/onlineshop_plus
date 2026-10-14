import { randomUUID } from "node:crypto";
import { createClient } from "redis";
export interface Coordinator {
  get(key: string): Promise<string | null>;
  put(key: string, value: string, seconds: number): Promise<void>;
  lock<T>(key: string, work: () => Promise<T>): Promise<T>;
}
export class MemoryCoordinator implements Coordinator {
  private values = new Map<string, { value: string; until: number }>();
  private locks = new Map<string, Promise<unknown>>();
  async get(key: string) {
    const x = this.values.get(key);
    if (x && x.until > Date.now()) return x.value;
    this.values.delete(key);
    return null;
  }
  async put(key: string, value: string, seconds: number) {
    this.values.set(key, { value, until: Date.now() + seconds * 1000 });
  }
  async lock<T>(key: string, work: () => Promise<T>) {
    const previous = this.locks.get(key) ?? Promise.resolve();
    const current = previous.catch(() => {}).then(work);
    this.locks.set(key, current);
    try {
      return await current;
    } finally {
      if (this.locks.get(key) === current) this.locks.delete(key);
    }
  }
}
let redis: ReturnType<typeof createClient> | undefined;
let connecting: Promise<unknown> | undefined;
async function connection(url: string) {
  if (!redis) {
    redis = createClient({
      url,
      socket: { connectTimeout: 3000, reconnectStrategy: false },
    });
    redis.on("error", () => {});
  }
  if (!redis.isOpen) {
    connecting ??= redis.connect().finally(() => {
      connecting = undefined;
    });
    await connecting;
  }
  return redis;
}
export class RedisCoordinator implements Coordinator {
  constructor(private url: string) {}
  async get(key: string) {
    return (await connection(this.url)).get("osp:bff:" + key);
  }
  async put(key: string, value: string, seconds: number) {
    await (
      await connection(this.url)
    ).set("osp:bff:" + key, value, { EX: seconds });
  }
  async lock<T>(key: string, work: () => Promise<T>) {
    const r = await connection(this.url),
      k = "osp:bff:lock:" + key,
      id = randomUUID(),
      until = Date.now() + 20000;
    while (!(await r.set(k, id, { NX: true, EX: 45 }))) {
      if (Date.now() > until) throw new Error("coordination busy");
      await new Promise((resolve) => setTimeout(resolve, 50));
    }
    try {
      return await work();
    } finally {
      await r.eval(
        "if redis.call('get',KEYS[1]) == ARGV[1] then return redis.call('del',KEYS[1]) else return 0 end",
        { keys: [k], arguments: [id] },
      );
    }
  }
}
const memory = new MemoryCoordinator();
export function coordinator() {
  if (process.env.BFF_REDIS_URL)
    return new RedisCoordinator(process.env.BFF_REDIS_URL);
  if (
    process.env.BFF_COORDINATION === "memory" &&
    process.env.NODE_ENV !== "production"
  )
    return memory;
  throw new Error("BFF_REDIS_URL is required; memory is development only");
}
