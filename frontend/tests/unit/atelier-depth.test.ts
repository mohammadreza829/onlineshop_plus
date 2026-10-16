import { describe, expect, it } from "vitest";
import { depthPose, sceneCanMove } from "@/lib/motion/depth";
describe("bounded editorial depth", () => {
  it("keeps the neutral pose centered", () => {
    expect(depthPose(0.5, 0.5)).toEqual({ rotateX: 0, rotateY: 0, x: 0, y: 0 });
  });
  it("clamps out-of-range pointers", () => {
    expect(depthPose(-5, 9)).toEqual(depthPose(0, 1));
  });
  it("neutralizes invalid coordinates", () => {
    expect(depthPose(Number.NaN, Infinity)).toEqual(depthPose(0.5, 0.5));
  });
  it("uses shallower depth for compact presentations", () => {
    expect(Math.abs(depthPose(1, 1, true).rotateY)).toBeLessThan(
      Math.abs(depthPose(1, 1).rotateY),
    );
  });
  it.each([
    [true, false, true],
    [false, true, true],
    [false, false, false],
  ])(
    "stops motion for reduced=%s paused=%s visible=%s",
    (reduced, paused, visible) => {
      expect(sceneCanMove(reduced, paused, visible)).toBe(false);
    },
  );
  it("moves only when allowed and visible", () => {
    expect(sceneCanMove(false, false, true)).toBe(true);
  });
});
