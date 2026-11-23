/**
 * WebGL scene for the animated retail background.
 *
 * Lots of small, realistically shaded products drift slowly with a gentle 3D
 * tumble. Near the pointer they are pulled in, swirl around it and spin up.
 * Physics runs in screen pixels; each frame positions are converted so the
 * perspective camera projects every item exactly onto its screen position
 * (depth only changes apparent size and parallax).
 */
import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { buildProductTemplates, TEMPLATE_KEYS } from './products3d';

export interface RetailScene {
  resize(): void;
  setPointer(x: number, y: number, active: boolean): void;
  setDark(dark: boolean): void;
  start(): void;
  stop(): void;
  renderStatic(): void;
  dispose(): void;
}

interface Item {
  obj: THREE.Object3D;
  sx: number; sy: number;       // screen position (px)
  vx: number; vy: number;       // screen velocity (px/s)
  z: number;                    // depth (world units, + = toward camera)
  size: number;                 // base on-screen size (px)
  phase: number; phaseSpeed: number;
  wx: number; wy: number; wz: number; // tumble (rad/s)
  scale: number;                // eased hover scale
}

const FOV = 30;
const rand = (a: number, b: number) => a + Math.random() * (b - a);

export function createRetailScene(
  canvas: HTMLCanvasElement,
  opts: { dark: boolean },
): RetailScene {
  const renderer = new THREE.WebGLRenderer({
    canvas, alpha: true, antialias: true, powerPreference: 'high-performance',
  });
  renderer.setClearColor(0x000000, 0);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  const envTex = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environment = envTex;

  const camera = new THREE.PerspectiveCamera(FOV, 1, 10, 8000);
  const key = new THREE.DirectionalLight(0xffffff, 1.3);
  key.position.set(-400, 600, 900);
  scene.add(key, new THREE.HemisphereLight(0xffffff, 0x9fd5b4, 0.5));

  const { templates, dispose: disposeAssets } = buildProductTemplates();

  let W = 1, H = 1, camZ = 1000;
  const pointer = { x: -9999, y: -9999, active: false };
  let items: Item[] = [];
  let raf = 0;
  let running = false;
  let last = 0;
  let t = 0;
  const RADIUS = 250;

  const setDark = (dark: boolean) => {
    renderer.toneMappingExposure = dark ? 0.9 : 1.05;
    scene.environmentIntensity = dark ? 0.85 : 1;
  };
  setDark(opts.dark);

  const depthK = (z: number) => (camZ - z) / camZ; // world-x per screen-px at depth z

  const build = () => {
    items.forEach((i) => scene.remove(i.obj));
    const mobile = W < 700;
    const count = Math.max(24, Math.min(mobile ? 34 : 78, Math.round((W * H) / 24000)));
    const keys = [...TEMPLATE_KEYS].sort(() => Math.random() - 0.5);
    items = Array.from({ length: count }, (_, n) => {
      const obj = templates.get(keys[n % keys.length])!.clone();
      obj.rotation.set(rand(0, 6.28), rand(0, 6.28), rand(0, 6.28));
      scene.add(obj);
      return {
        obj,
        sx: rand(0, W), sy: rand(0, H),
        vx: 0, vy: 0,
        z: rand(-450, 170),
        size: rand(26, 46),
        phase: rand(0, Math.PI * 2),
        phaseSpeed: rand(0.2, 0.7),
        wx: rand(-0.45, 0.45), wy: rand(-0.55, 0.55), wz: rand(-0.3, 0.3),
        scale: 1,
      };
    });
  };

  const place = (it: Item) => {
    const k = depthK(it.z);
    it.obj.position.set((it.sx - W / 2) * k, (H / 2 - it.sy) * k, it.z);
    it.obj.scale.setScalar(it.size * it.scale);
  };

  const resize = () => {
    W = window.innerWidth; H = window.innerHeight;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    renderer.setSize(W, H, false);
    camera.aspect = W / H;
    camZ = (H / 2) / Math.tan((FOV * Math.PI) / 360);
    camera.position.set(0, 0, camZ);
    camera.far = camZ + 2000;
    camera.updateProjectionMatrix();
    const needsRebuild = items.length === 0 || Math.abs(items.length - Math.round((W * H) / 24000)) > 12;
    if (needsRebuild) build();
    else items.forEach((i) => { i.sx = Math.min(i.sx, W); i.sy = Math.min(i.sy, H); });
    items.forEach(place);
  };

  const step = (dt: number) => {
    t += dt;
    const margin = 70;
    for (const it of items) {
      // 1) organic drift: heading slowly random-walks
      it.phase += (Math.sin(t * it.phaseSpeed + it.sx * 0.004) * 0.9 + (Math.random() - 0.5) * 0.5) * dt;
      const depthF = 0.6 + 0.4 * ((it.z + 450) / 620);
      const cruise = 14 * depthF;
      let tx = Math.cos(it.phase) * cruise;
      let ty = Math.sin(it.phase) * cruise;

      // 2) pointer: pull in, orbit, keep a little distance
      let near = 0;
      if (pointer.active) {
        const dx = pointer.x - it.sx, dy = pointer.y - it.sy;
        const d = Math.hypot(dx, dy) || 1;
        if (d < RADIUS) {
          near = 1 - d / RADIUS;
          const nx = dx / d, ny = dy / d;
          const pull = near * 240 * depthF;
          const ring = d < 60 ? -(60 - d) * 5 : 0;
          tx += nx * (pull + ring) - ny * near * 80 * depthF;
          ty += ny * (pull + ring) + nx * near * 80 * depthF;
        }
      }
      const k = 1 - Math.exp(-3.2 * dt);
      it.vx += (tx - it.vx) * k;
      it.vy += (ty - it.vy) * k;
      it.sx += it.vx * dt;
      it.sy += it.vy * dt;

      // 3D tumble, faster near the pointer
      const spin = 1 + near * 3.2;
      it.obj.rotation.x += it.wx * dt * spin;
      it.obj.rotation.y += it.wy * dt * spin;
      it.obj.rotation.z += it.wz * dt * spin;
      it.scale += ((1 + near * 0.35) - it.scale) * (1 - Math.exp(-6 * dt));

      // wrap around the edges
      if (it.sx < -margin) it.sx = W + margin; else if (it.sx > W + margin) it.sx = -margin;
      if (it.sy < -margin) it.sy = H + margin; else if (it.sy > H + margin) it.sy = -margin;
      place(it);
    }
  };

  const frame = (now: number) => {
    if (!running) return;
    const dt = Math.min((now - last) / 1000, 0.05);
    last = now;
    step(dt);
    renderer.render(scene, camera);
    raf = requestAnimationFrame(frame);
  };

  resize();

  return {
    resize,
    setPointer(x, y, active) { pointer.x = x; pointer.y = y; pointer.active = active; },
    setDark,
    start() {
      if (running) return;
      running = true; last = performance.now();
      raf = requestAnimationFrame(frame);
    },
    stop() { running = false; cancelAnimationFrame(raf); },
    renderStatic() { renderer.render(scene, camera); },
    dispose() {
      running = false; cancelAnimationFrame(raf);
      items.forEach((i) => scene.remove(i.obj));
      disposeAssets();
      envTex.dispose(); pmrem.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
    },
  };
}
