"use client";
import { Suspense, useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, useThree, useLoader } from "@react-three/fiber";
import * as THREE from "three";
import { readCloth, weaveTexture } from "./cloth";
import type { ViewCommand } from "./types";

function Textile({
  color,
  view,
  automatic,
  onReady,
}: {
  color: string;
  view: ViewCommand;
  automatic: boolean;
  onReady: () => void;
}) {
  const invalidate = useThree((state) => state.invalidate);
  const group = useRef<THREE.Group>(null),
    ready = useRef(false),
    targetAngle = useRef(-0.32),
    revision = useRef(0);
  const buffer = useLoader(THREE.FileLoader, "/models/cloth.mesh", (loader) =>
    loader.setResponseType("arraybuffer"),
  ) as unknown as ArrayBuffer;
  const geometry = useMemo(() => readCloth(buffer), [buffer]),
    weave = useMemo(() => weaveTexture(), []);
  useEffect(
    () => () => {
      geometry.dispose();
      weave.dispose();
    },
    [geometry, weave],
  );
  useEffect(() => {
    if (view.revision !== revision.current) {
      targetAngle.current = view.reset
        ? -0.32
        : (group.current?.rotation.y ?? targetAngle.current) + view.offset;
      revision.current = view.revision;
    } else if (!automatic) {
      // Pause freezes the visible pose; it must not rewind to the initial view.
      targetAngle.current = group.current?.rotation.y ?? targetAngle.current;
    }
    invalidate();
  }, [view, automatic, invalidate]);
  useFrame((state, dt) => {
    if (!ready.current) {
      ready.current = true;
      onReady();
    }
    if (!group.current) return;
    if (automatic) targetAngle.current += Math.min(dt, 0.05) * 0.14;
    const target = targetAngle.current;
    group.current.rotation.y = THREE.MathUtils.damp(
      group.current.rotation.y,
      target,
      7,
      Math.min(dt, 0.05),
    );
    if (automatic || Math.abs(group.current.rotation.y - target) > 0.001)
      state.invalidate();
  });
  return (
    <group ref={group} rotation={[0, -0.32, 0]}>
      <mesh geometry={geometry} castShadow receiveShadow>
        <meshPhysicalMaterial
          color={color}
          roughness={0.73}
          metalness={0.025}
          sheen={1}
          sheenColor="#d8e9bf"
          sheenRoughness={0.65}
          bumpMap={weave}
          bumpScale={0.0025}
          side={THREE.DoubleSide}
        />
      </mesh>
    </group>
  );
}
function CameraMotion({ active }: { active: boolean }) {
  useFrame(({ camera, pointer }, dt) => {
    if (!active) return;
    camera.position.x = THREE.MathUtils.damp(
      camera.position.x,
      pointer.x * 0.2,
      4,
      Math.min(dt, 0.05),
    );
    camera.position.y = THREE.MathUtils.damp(
      camera.position.y,
      0.6 + pointer.y * 0.12,
      4,
      Math.min(dt, 0.05),
    );
    camera.lookAt(0, -0.12, 0);
  });
  return null;
}
function ContextGuard({ onLost }: { onLost: () => void }) {
  const gl = useThree((s) => s.gl);
  useEffect(() => {
    const element = gl.domElement;
    element.addEventListener("webglcontextlost", onLost);
    return () => element.removeEventListener("webglcontextlost", onLost);
  }, [gl, onLost]);
  return null;
}
export default function ShowroomScene({
  color,
  view,
  automatic,
  onReady,
  onLost,
}: {
  color: string;
  view: ViewCommand;
  automatic: boolean;
  onReady: () => void;
  onLost: () => void;
}) {
  return (
    <Canvas
      shadows
      dpr={[1, 1.5]}
      frameloop="demand"
      camera={{ position: [0, 0.6, 5.9], fov: 38 }}
      gl={{ antialias: true, alpha: true, powerPreference: "low-power" }}
      onCreated={({ gl }) => {
        gl.domElement.setAttribute("role", "img");
        gl.domElement.setAttribute(
          "aria-label",
          "مدل سه‌بعدی پارچه با چین‌های حجمی و نورپردازی واقعی",
        );
      }}
    >
      <ContextGuard onLost={onLost} />
      <CameraMotion active={automatic} />
      <ambientLight intensity={0.8} />
      <hemisphereLight args={["#f1f2e5", "#203028", 1.1]} />
      <spotLight
        position={[-3, 5, 4]}
        intensity={75}
        angle={0.6}
        penumbra={1}
        castShadow
        shadow-mapSize={[1024, 1024]}
        shadow-bias={-0.0005}
      />
      <directionalLight position={[3, 1, 1]} intensity={1.8} color="#d9e5c0" />
      <pointLight position={[0, 2, -3]} color="#c6e79c" intensity={18} />
      <Suspense fallback={null}>
        <Textile
          color={color}
          view={view}
          automatic={automatic}
          onReady={onReady}
        />
      </Suspense>
      <mesh position={[0, -1.23, 0]} receiveShadow castShadow>
        <cylinderGeometry args={[1.42, 1.5, 0.18, 96]} />
        <meshStandardMaterial
          color="#34483c"
          metalness={0.42}
          roughness={0.38}
        />
      </mesh>
      <mesh position={[0, -1.13, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[1.36, 1.38, 96]} />
        <meshBasicMaterial color="#c6e79c" />
      </mesh>
      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, -1.33, 0]}
        receiveShadow
      >
        <planeGeometry args={[50, 50]} />
        <shadowMaterial transparent opacity={0.28} />
      </mesh>
    </Canvas>
  );
}
