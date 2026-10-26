import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { readCloth } from "@/features/showroom/cloth";
describe("CC0 cloth geometry", () => {
  it("rejects malformed buffers", () => {
    expect(() => readCloth(new ArrayBuffer(8))).toThrow("Invalid cloth asset");
  });
  it("preserves finite, compact renderable geometry and a floor-safe position", () => {
    const bytes = readFileSync("public/models/cloth.mesh");
    const g = readCloth(
      bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
    );
    expect(g.getAttribute("position").count).toBe(7393);
    expect(g.getAttribute("normal").count).toBe(7393);
    expect(g.index?.count).toBe(41472);
    expect([...g.getAttribute("position").array].every(Number.isFinite)).toBe(
      true,
    );
    g.computeBoundingBox();
    expect(g.boundingBox!.min.y).toBeCloseTo(-1.1, 4);
    expect(g.boundingBox!.max.x - g.boundingBox!.min.x).toBeCloseTo(2.85, 4);
    g.dispose();
  });
});
