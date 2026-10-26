import * as THREE from "three";
// Microsoft SheenCloth (CC0), remeshed offline to 13,824 triangles.
// Original normals and UVs are preserved. Header: vertex/index counts, then
// Float32 positions, normals, UVs and Uint16 triangle indices (little endian).
export function readCloth(buffer: ArrayBuffer) {
  const header = new DataView(buffer),
    vertices = header.getUint32(0, true),
    indices = header.getUint32(4, true);
  if (vertices !== 7393 || indices !== 41472 || buffer.byteLength !== 319528)
    throw new Error("Invalid cloth asset");
  const g = new THREE.BufferGeometry();
  g.setAttribute(
    "position",
    new THREE.BufferAttribute(
      new Float32Array(buffer, 8, vertices * 3).slice(),
      3,
    ),
  );
  g.setAttribute(
    "normal",
    new THREE.BufferAttribute(
      new Float32Array(buffer, 8 + vertices * 12, vertices * 3),
      3,
    ),
  );
  g.setAttribute(
    "uv",
    new THREE.BufferAttribute(
      new Float32Array(buffer, 8 + vertices * 24, vertices * 2),
      2,
    ),
  );
  g.setIndex(
    new THREE.BufferAttribute(
      new Uint16Array(buffer, 8 + vertices * 32, indices),
      1,
    ),
  );
  g.computeBoundingBox();
  const size = g.boundingBox!.getSize(new THREE.Vector3());
  g.center();
  const scale = 2.85 / size.x;
  g.scale(scale, scale, scale);
  g.computeBoundingBox();
  g.translate(0, -1.1 - g.boundingBox!.min.y, 0);
  g.computeBoundingSphere();
  return g;
}
export function weaveTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 128;
  const ctx = canvas.getContext("2d")!;
  ctx.fillStyle = "#888";
  ctx.fillRect(0, 0, 128, 128);
  for (let i = 0; i < 128; i += 2) {
    ctx.fillStyle = i % 4 ? "#a8a8a8" : "#686868";
    ctx.fillRect(i, 0, 1, 128);
    ctx.fillStyle = "#777";
    ctx.fillRect(0, i, 128, 1);
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(36, 36);
  return texture;
}
