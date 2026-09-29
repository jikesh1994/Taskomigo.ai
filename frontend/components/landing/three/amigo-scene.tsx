"use client";

// The landing page's 3D layer: one fixed, full-viewport canvas behind the content.
//
// * The amigo (a glossy, iridescent version of the Taskomigo mark) flies to the
//   `[data-amigo-anchor]` box of whichever section is centred on screen, so layout
//   decides where it goes on every screen size. It turns towards the cursor, blinks,
//   and spins when you scroll fast; its orbiting task tokens whirl faster too.
// * A starfield drifts behind it with scroll parallax.
//
// Everything is procedural: no models, textures or HDRs are downloaded.

import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef, type ReactNode, type RefObject } from "react";
import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";
import { pointer } from "@/lib/pointer";

const COLORS = {
  body: "#6d28d9",
  white: "#ffffff",
  pupil: "#1a1033",
  mint: "#34e0a1",
  orange: "#ff9f43",
  pink: "#ff5fa2",
  ink: "#8b5cf6",
};

const BODY_RADIUS = 1.15;
const { damp } = THREE.MathUtils;

/** Shared per-frame motion state, written by the traveller and read by its parts. */
interface Motion {
  spin: number; // rad/s from scroll velocity
}

/** A point on the front of the body sphere, nudged outwards by `lift`. */
function onBody(x: number, y: number, lift = 0): THREE.Vector3 {
  const z = Math.sqrt(Math.max(BODY_RADIUS ** 2 - x * x - y * y, 0));
  return new THREE.Vector3(x, y, z).setLength(BODY_RADIUS + lift);
}

/** Frees a three.js resource (geometry, texture) when it's replaced or unmounted. */
function useDisposed<T extends { dispose: () => void }>(value: T): T {
  useEffect(() => () => value.dispose(), [value]);
  return value;
}

/** Soft studio reflections for the glossy materials, generated locally. */
function Environment() {
  const gl = useThree((state) => state.gl);
  const texture = useDisposed(
    useMemo(() => {
      const pmrem = new THREE.PMREMGenerator(gl);
      const env = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
      pmrem.dispose();
      return env;
    }, [gl]),
  );
  return <primitive object={texture} attach="environment" />;
}

function radialTexture(stops: [number, string][]): THREE.CanvasTexture {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 128;
  const ctx = canvas.getContext("2d");
  if (ctx) {
    const gradient = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
    for (const [offset, color] of stops) gradient.addColorStop(offset, color);
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 128, 128);
  }
  return new THREE.CanvasTexture(canvas);
}

// ------------------------------------------------------------------ the amigo

function Eye({ side }: { side: -1 | 1 }) {
  const eye = useRef<THREE.Group>(null);
  const pupil = useRef<THREE.Mesh>(null);
  const position = useMemo(() => onBody(side * 0.38, 0.3, -0.06), [side]);
  const quaternion = useMemo(
    () => new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), position.clone().normalize()),
    [position],
  );

  useFrame((state, delta) => {
    if (!eye.current || !pupil.current) return;
    const phase = state.clock.elapsedTime % 4.2; // blink every 4.2s for ~140ms
    const blink = phase < 0.14 ? Math.abs(Math.cos((phase / 0.14) * Math.PI)) : 1;
    eye.current.scale.y = damp(eye.current.scale.y, Math.max(blink, 0.08), 40, delta);
    pupil.current.position.x = damp(pupil.current.position.x, pointer.x * 0.07, 8, delta);
    pupil.current.position.y = damp(pupil.current.position.y, pointer.y * 0.08, 8, delta);
  });

  return (
    <group position={position} quaternion={quaternion}>
      <group ref={eye}>
        <mesh scale={[1, 1.3, 0.55]}>
          <sphereGeometry args={[0.2, 48, 48]} />
          <meshPhysicalMaterial color={COLORS.white} roughness={0.12} clearcoat={1} />
        </mesh>
        <mesh ref={pupil} position={[0, 0, 0.09]} scale={[1, 1.2, 0.6]}>
          <sphereGeometry args={[0.095, 32, 32]} />
          <meshStandardMaterial color={COLORS.pupil} roughness={0.2} />
        </mesh>
      </group>
    </group>
  );
}

function Smile() {
  const geometry = useDisposed(
    useMemo(() => {
      const curve = new THREE.CatmullRomCurve3(
        [onBody(-0.5, -0.12, 0.01), onBody(-0.14, -0.5, 0.01), onBody(0.52, 0.02, 0.01)],
        false,
        "catmullrom",
        0.1,
      );
      return new THREE.TubeGeometry(curve, 64, 0.065, 16, false);
    }, []),
  );
  return (
    <mesh geometry={geometry}>
      <meshPhysicalMaterial color={COLORS.white} roughness={0.15} clearcoat={1} />
    </mesh>
  );
}

function Halo() {
  const texture = useDisposed(
    useMemo(
      () =>
        radialTexture([
          [0, "rgba(236, 72, 153, 0.55)"],
          [0.45, "rgba(139, 92, 246, 0.22)"],
          [1, "rgba(139, 92, 246, 0)"],
        ]),
      [],
    ),
  );
  return (
    <sprite position={[0, 0, -1.4]} scale={[5.2, 5.2, 1]}>
      <spriteMaterial map={texture} transparent depthWrite={false} blending={THREE.AdditiveBlending} />
    </sprite>
  );
}

function Body() {
  return (
    <mesh>
      <sphereGeometry args={[BODY_RADIUS, 96, 96]} />
      {/* Deep violet with a subtle oil-slick shimmer; reflections kept low so the
          colour stays saturated instead of washing out to lilac. */}
      <meshPhysicalMaterial
        color={COLORS.body}
        roughness={0.22}
        metalness={0.1}
        clearcoat={1}
        clearcoatRoughness={0.06}
        envMapIntensity={0.55}
        iridescence={0.55}
        iridescenceIOR={1.4}
        iridescenceThicknessRange={[200, 700]}
        sheen={0.25}
        sheenColor="#ff8ad1"
      />
    </mesh>
  );
}

// ------------------------------------------------------------------ orbiting tokens

function useRoundedBox(width: number, height: number, depth: number, radius: number) {
  return useDisposed(
    useMemo(() => new RoundedBoxGeometry(width, height, depth, 4, radius), [width, height, depth, radius]),
  );
}

function Tick({ z, size = 1 }: { z: number; size?: number }) {
  const geometry = useDisposed(
    useMemo(() => {
      const s = size;
      const curve = new THREE.CatmullRomCurve3(
        [new THREE.Vector3(-0.13 * s, 0, z), new THREE.Vector3(-0.03 * s, -0.1 * s, z), new THREE.Vector3(0.14 * s, 0.1 * s, z)],
        false,
        "catmullrom",
        0.05,
      );
      return new THREE.TubeGeometry(curve, 24, 0.035 * s, 10, false);
    }, [z, size]),
  );
  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial color={COLORS.white} roughness={0.3} />
    </mesh>
  );
}

function CheckToken() {
  const box = useRoundedBox(0.5, 0.5, 0.5, 0.14);
  return (
    <group>
      <mesh geometry={box}>
        <meshPhysicalMaterial color={COLORS.mint} roughness={0.25} clearcoat={1} emissive={COLORS.mint} emissiveIntensity={0.15} />
      </mesh>
      <Tick z={0.27} />
    </group>
  );
}

function DocumentToken() {
  const sheet = useRoundedBox(0.56, 0.74, 0.06, 0.03);
  const bar = useRoundedBox(0.34, 0.05, 0.02, 0.01);
  return (
    <group>
      <mesh geometry={sheet}>
        <meshPhysicalMaterial color={COLORS.white} roughness={0.3} clearcoat={0.6} />
      </mesh>
      {[0.2, 0.06, -0.08, -0.22].map((y, i) => (
        <mesh key={y} geometry={bar} position={[i === 3 ? -0.06 : 0, y, 0.04]} scale={[i === 3 ? 0.6 : 1, 1, 1]}>
          <meshStandardMaterial color={i === 0 ? COLORS.pink : COLORS.ink} roughness={0.4} />
        </mesh>
      ))}
    </group>
  );
}

function PauseToken() {
  const box = useRoundedBox(0.5, 0.5, 0.18, 0.08);
  const bar = useRoundedBox(0.07, 0.24, 0.04, 0.02);
  return (
    <group>
      <mesh geometry={box}>
        <meshPhysicalMaterial color={COLORS.orange} roughness={0.25} clearcoat={1} emissive={COLORS.orange} emissiveIntensity={0.12} />
      </mesh>
      <mesh geometry={bar} position={[-0.07, 0, 0.1]}>
        <meshStandardMaterial color={COLORS.white} />
      </mesh>
      <mesh geometry={bar} position={[0.07, 0, 0.1]}>
        <meshStandardMaterial color={COLORS.white} />
      </mesh>
    </group>
  );
}

function Gem() {
  return (
    <mesh>
      <icosahedronGeometry args={[0.24, 0]} />
      <meshPhysicalMaterial color={COLORS.pink} roughness={0.1} clearcoat={1} iridescence={1} flatShading />
    </mesh>
  );
}

interface OrbitProps {
  radius: number;
  height: number;
  offset: number;
  tilt: number;
  scale?: number;
  motion: RefObject<Motion>;
  children: ReactNode;
}

/** Circles the amigo on a tilted ellipse; scrolling makes it whirl faster. */
function Orbit({ radius, height, offset, tilt, scale = 1, motion, children }: OrbitProps) {
  const item = useRef<THREE.Group>(null);
  const angle = useRef(offset);
  useFrame((state, delta) => {
    if (!item.current) return;
    const t = state.clock.elapsedTime;
    angle.current += delta * (0.45 + Math.abs(motion.current?.spin ?? 0) * 0.6);
    const a = angle.current;
    item.current.position.set(
      Math.cos(a) * radius,
      height + Math.sin(a) * tilt + Math.sin(t * 1.7 + offset) * 0.06,
      Math.sin(a) * radius * 0.6,
    );
    item.current.rotation.set(0.35 + Math.sin(t * 0.8 + offset) * 0.2, -a * 0.5 + 0.4, 0.15);
  });
  return (
    <group ref={item} scale={scale}>
      {children}
    </group>
  );
}

// ------------------------------------------------------------------ travelling

interface Target {
  x: number;
  y: number;
  scale: number;
  turn: number;
}

/** Picks the anchor nearest the viewport centre and maps it into world space. */
function readTarget(anchors: HTMLElement[], viewport: { width: number; height: number }): Target | null {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  let best: { el: HTMLElement; rect: DOMRect } | null = null;
  let bestDistance = Infinity;
  for (const el of anchors) {
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) continue; // hidden at this breakpoint
    const distance = Math.abs(rect.top + rect.height / 2 - vh / 2);
    if (distance < bestDistance) {
      bestDistance = distance;
      best = { el, rect };
    }
  }
  if (!best) return null;
  const { el, rect } = best;
  const cx = rect.left + rect.width / 2;
  // Stay (at least half) on screen while waiting for the next section, without being
  // pulled up over the content above an anchor that's still below the fold.
  const cy = Math.min(Math.max(rect.top + rect.height / 2, vh * 0.06), vh * 1.0);
  const pxPerUnit = vh / viewport.height;
  const size = Math.min(rect.width, rect.height) / pxPerUnit;
  const phone = vw < 640 ? 0.78 : 1; // leave room for text on narrow screens
  return {
    x: (cx / vw - 0.5) * viewport.width,
    y: -(cy / vh - 0.5) * viewport.height,
    scale: THREE.MathUtils.clamp((size / 3.3) * Number(el.dataset.amigoScale ?? 1) * phone, 0.22, 1.1),
    turn: Number(el.dataset.amigoTurn ?? 0),
  };
}

function Traveller() {
  const root = useRef<THREE.Group>(null);
  const spinner = useRef<THREE.Group>(null);
  const head = useRef<THREE.Group>(null);
  const motion = useRef<Motion>({ spin: 0 });
  const anchors = useRef<HTMLElement[]>([]);
  const lastScroll = useRef(0);
  const placed = useRef(false);
  const turn = useRef(0);

  useEffect(() => {
    anchors.current = Array.from(document.querySelectorAll<HTMLElement>("[data-amigo-anchor]"));
    lastScroll.current = window.scrollY;
  }, []);

  useFrame((state, delta) => {
    if (!root.current || !spinner.current || !head.current) return;
    const dt = Math.min(delta, 0.05);
    const target = readTarget(anchors.current, state.viewport);
    if (target) {
      const p = root.current.position;
      if (!placed.current) {
        p.set(target.x, target.y, 0);
        root.current.scale.setScalar(target.scale);
        placed.current = true;
      }
      p.x = damp(p.x, target.x, 2.6, dt);
      p.y = damp(p.y, target.y, 2.6, dt);
      root.current.scale.setScalar(damp(root.current.scale.x, target.scale, 3, dt));
      turn.current = damp(turn.current, target.turn, 3, dt);
    }

    // Scroll velocity → spin, which settles back to facing the viewer.
    const scrollY = window.scrollY;
    const velocity = (scrollY - lastScroll.current) / Math.max(delta, 1 / 240);
    lastScroll.current = scrollY;
    motion.current.spin = damp(motion.current.spin, THREE.MathUtils.clamp(velocity * 0.004, -9, 9), 5, dt);
    const s = spinner.current.rotation;
    s.y += motion.current.spin * dt;
    if (Math.abs(motion.current.spin) < 0.3) {
      s.y = damp(s.y, Math.round(s.y / (Math.PI * 2)) * Math.PI * 2, 2.5, dt);
    }
    // Lean into fast scrolling.
    s.x = damp(s.x, THREE.MathUtils.clamp(velocity * 0.00015, -0.35, 0.35), 4, dt);

    // Look at the cursor (plus the anchor's hint), float gently.
    const t = state.clock.elapsedTime;
    head.current.rotation.y = damp(head.current.rotation.y, pointer.x * 0.32 + turn.current, 4, dt);
    head.current.rotation.x = damp(head.current.rotation.x, -pointer.y * 0.2, 4, dt);
    head.current.position.y = Math.sin(t * 1.3) * 0.08;
    head.current.rotation.z = Math.sin(t * 0.7) * 0.04;
  });

  return (
    <group ref={root}>
      <Halo />
      <group ref={spinner}>
        <group ref={head}>
          <Body />
          <Eye side={-1} />
          <Eye side={1} />
          <Smile />
        </group>
      </group>
      <Orbit radius={1.8} height={0.55} offset={0.4} tilt={0.25} motion={motion}>
        <CheckToken />
      </Orbit>
      <Orbit radius={1.85} height={-0.35} offset={2.5} tilt={0.2} scale={0.9} motion={motion}>
        <DocumentToken />
      </Orbit>
      <Orbit radius={1.75} height={0.1} offset={4.4} tilt={0.3} scale={0.8} motion={motion}>
        <PauseToken />
      </Orbit>
      <Orbit radius={1.95} height={1.05} offset={3.3} tilt={0.15} scale={0.7} motion={motion}>
        <Gem />
      </Orbit>
    </group>
  );
}

// ------------------------------------------------------------------ starfield

const STAR_COLORS = ["#c4b5fd", "#f9a8d4", "#67e8f9", "#fdba74", "#ffffff"];

/** A tall field of coloured points; deterministic, so it's the same sky on every visit. */
function buildStarGeometry(count: number): THREE.BufferGeometry {
  const positions = new Float32Array(count * 3);
  const colors = new Float32Array(count * 3);
  const color = new THREE.Color();
  let seed = 7;
  const rand = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
  for (let i = 0; i < count; i++) {
    positions[i * 3] = (rand() - 0.5) * 22;
    positions[i * 3 + 1] = rand() * 30 - 8;
    positions[i * 3 + 2] = -2 - rand() * 9;
    color.set(STAR_COLORS[i % STAR_COLORS.length]);
    colors.set([color.r, color.g, color.b], i * 3);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  return geometry;
}

function Stars({ count = 700 }: { count?: number }) {
  const group = useRef<THREE.Group>(null);
  const geometry = useDisposed(useMemo(() => buildStarGeometry(count), [count]));
  const sprite = useDisposed(
    useMemo(
      () =>
        radialTexture([
          [0, "rgba(255,255,255,1)"],
          [0.35, "rgba(255,255,255,0.6)"],
          [1, "rgba(255,255,255,0)"],
        ]),
      [],
    ),
  );

  useFrame((state, delta) => {
    if (!group.current) return;
    // Scroll parallax: the sky drifts up more slowly than the page.
    group.current.position.y = damp(group.current.position.y, window.scrollY * 0.0016, 6, delta);
    group.current.rotation.z = Math.sin(state.clock.elapsedTime * 0.05) * 0.03;
    group.current.position.x = damp(group.current.position.x, pointer.x * 0.25, 2, delta);
  });

  return (
    <group ref={group}>
      <points geometry={geometry}>
        <pointsMaterial
          size={0.09}
          map={sprite}
          vertexColors
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
          sizeAttenuation
        />
      </points>
    </group>
  );
}

// ------------------------------------------------------------------ scene

export default function AmigoScene() {
  return (
    <Canvas
      camera={{ position: [0, 0, 7], fov: 36 }}
      dpr={[1, 1.5]}
      gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
      aria-hidden
    >
      <Environment />
      <ambientLight intensity={0.4} />
      <directionalLight position={[-3, 4, 5]} intensity={2.4} />
      <pointLight position={[-4, -1, 2]} intensity={22} color="#ff5fa2" />
      <pointLight position={[4, 2, -2]} intensity={22} color="#22d3ee" />
      <Stars />
      <Traveller />
    </Canvas>
  );
}
