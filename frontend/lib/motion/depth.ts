/** Bounded pointer depth; invalid coordinates resolve to the neutral pose. */
export function depthPose(x: number, y: number, compact = false) {
  const unit = (v: number) =>
    Number.isFinite(v) ? Math.max(0, Math.min(1, v)) : 0.5;
  const scale = compact ? 0.45 : 1;
  return {
    rotateX: (0.5 - unit(y)) * 5 * scale,
    rotateY: (unit(x) - 0.5) * 7 * scale,
    x: (unit(x) - 0.5) * 16 * scale,
    y: (unit(y) - 0.5) * 10 * scale,
  };
}
export function sceneCanMove(
  reduced: boolean,
  paused: boolean,
  visible: boolean,
) {
  return !reduced && !paused && visible;
}
