'use client';

import { useEffect, useRef } from 'react';

/**
 * Full-screen animated background: small retail items (chips, chocolate,
 * phones, electronics, bags …) drift randomly across the page. When the
 * pointer moves, nearby items are pulled toward it and swirl around the
 * cursor, so the background reacts to the mouse.
 *
 * - Pure canvas, no dependencies, no images (sprites are drawn with paths).
 * - Sits behind the app (`fixed`, `pointer-events: none`); the pointer is read
 *   from `window`, so it works over every card and page.
 * - Respects `prefers-reduced-motion` and pauses when the tab is hidden.
 */

type SpriteKind =
  | 'chips'
  | 'chocolate'
  | 'phone'
  | 'bulb'
  | 'headphones'
  | 'can'
  | 'bag'
  | 'battery'
  | 'plug'
  | 'cookie'
  | 'candy'
  | 'laptop'
  | 'watch'
  | 'cart';

const KINDS: SpriteKind[] = [
  'chips', 'chocolate', 'phone', 'bulb', 'headphones', 'can', 'bag',
  'battery', 'plug', 'cookie', 'candy', 'laptop', 'watch', 'cart',
];

const SPRITE = 100; // logical sprite box (px); rendered at devicePixelRatio

/* ---------- sprite painters (each draws inside a 100×100 box) ---------- */

type Paint = (c: CanvasRenderingContext2D) => void;

function rr(c: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  c.beginPath();
  c.moveTo(x + r, y);
  c.arcTo(x + w, y, x + w, y + h, r);
  c.arcTo(x + w, y + h, x, y + h, r);
  c.arcTo(x, y + h, x, y, r);
  c.arcTo(x, y, x + w, y, r);
  c.closePath();
}

const painters: Record<SpriteKind, Paint> = {
  chips(c) {
    // wavy potato chip
    c.beginPath();
    c.moveTo(14, 52);
    c.bezierCurveTo(14, 26, 40, 14, 62, 20);
    c.bezierCurveTo(88, 26, 94, 50, 84, 70);
    c.bezierCurveTo(74, 88, 44, 92, 28, 80);
    c.bezierCurveTo(18, 72, 14, 62, 14, 52);
    c.closePath();
    c.fillStyle = '#f6c343';
    c.fill();
    c.lineWidth = 3;
    c.strokeStyle = '#d9962b';
    c.stroke();
    c.strokeStyle = '#e8a93a';
    c.lineWidth = 2.5;
    c.lineCap = 'round';
    c.beginPath();
    c.moveTo(26, 50); c.quadraticCurveTo(46, 38, 70, 46);
    c.moveTo(30, 66); c.quadraticCurveTo(52, 54, 76, 62);
    c.stroke();
    c.fillStyle = '#c9811f';
    [[40, 34], [62, 36], [54, 74], [36, 62]].forEach(([x, y]) => {
      c.beginPath(); c.arc(x, y, 1.8, 0, Math.PI * 2); c.fill();
    });
  },
  chocolate(c) {
    rr(c, 20, 12, 60, 76, 7);
    c.fillStyle = '#6b3f26';
    c.fill();
    c.lineWidth = 2.5;
    c.strokeStyle = '#4a2916';
    c.stroke();
    c.strokeStyle = '#4a2916';
    c.lineWidth = 2;
    c.beginPath();
    for (let i = 1; i < 3; i++) { c.moveTo(20 + i * 20, 12); c.lineTo(20 + i * 20, 88); }
    for (let i = 1; i < 4; i++) { c.moveTo(20, 12 + i * 19); c.lineTo(80, 12 + i * 19); }
    c.stroke();
    // foil wrapper peeking at the bottom
    c.fillStyle = '#d7dde0';
    c.beginPath();
    c.moveTo(20, 74); c.lineTo(80, 74); c.lineTo(80, 82);
    c.arcTo(80, 88, 74, 88, 6); c.lineTo(26, 88); c.arcTo(20, 88, 20, 82, 6);
    c.closePath(); c.fill();
    c.fillStyle = '#e94f5f';
    rr(c, 30, 77, 40, 6, 3); c.fill();
  },
  phone(c) {
    rr(c, 28, 8, 44, 84, 9);
    c.fillStyle = '#25323b';
    c.fill();
    rr(c, 32, 16, 36, 66, 4);
    c.fillStyle = '#35c47c';
    c.fill();
    // screen UI hints
    c.fillStyle = 'rgba(255,255,255,0.85)';
    rr(c, 36, 22, 28, 8, 3); c.fill();
    c.fillStyle = 'rgba(255,255,255,0.5)';
    rr(c, 36, 36, 12, 12, 3); c.fill();
    rr(c, 52, 36, 12, 12, 3); c.fill();
    rr(c, 36, 52, 12, 12, 3); c.fill();
    rr(c, 52, 52, 12, 12, 3); c.fill();
    c.fillStyle = '#0f171c';
    rr(c, 44, 11, 12, 3, 1.5); c.fill();
  },
  bulb(c) {
    c.beginPath();
    c.arc(50, 40, 24, 0, Math.PI * 2);
    c.fillStyle = '#ffe58a';
    c.fill();
    c.lineWidth = 3; c.strokeStyle = '#e0b83a'; c.stroke();
    c.fillStyle = '#ffe58a';
    c.beginPath(); c.moveTo(38, 58); c.lineTo(62, 58); c.lineTo(58, 70); c.lineTo(42, 70); c.closePath(); c.fill(); c.stroke();
    c.fillStyle = '#9aa6ad';
    rr(c, 40, 70, 20, 7, 2); c.fill();
    rr(c, 42, 78, 16, 7, 3); c.fill();
    c.strokeStyle = '#e0b83a'; c.lineWidth = 2.5; c.lineCap = 'round';
    c.beginPath(); c.moveTo(42, 50); c.lineTo(46, 38); c.lineTo(50, 46); c.lineTo(54, 38); c.lineTo(58, 50); c.stroke();
    c.strokeStyle = 'rgba(224,184,58,0.8)'; c.lineWidth = 2.5;
    c.beginPath();
    [[50, 6, 50, 0], [20, 18, 14, 12], [80, 18, 86, 12]].forEach(([x1, y1, x2, y2]) => { c.moveTo(x1, y1); c.lineTo(x2, y2); });
    c.stroke();
  },
  headphones(c) {
    c.strokeStyle = '#2f3a42'; c.lineWidth = 7; c.lineCap = 'round';
    c.beginPath(); c.arc(50, 52, 30, Math.PI, 0); c.stroke();
    c.fillStyle = '#3b9d6b';
    rr(c, 14, 50, 18, 32, 8); c.fill();
    rr(c, 68, 50, 18, 32, 8); c.fill();
    c.fillStyle = '#2f3a42';
    rr(c, 14, 50, 8, 32, 4); c.fill();
    rr(c, 78, 50, 8, 32, 4); c.fill();
  },
  can(c) {
    rr(c, 28, 12, 44, 78, 8);
    c.fillStyle = '#e04b4b';
    c.fill();
    c.fillStyle = '#c93636';
    rr(c, 28, 12, 44, 8, 4); c.fill();
    c.fillStyle = '#e9edef';
    rr(c, 28, 84, 44, 6, 3); c.fill();
    c.fillStyle = 'rgba(255,255,255,0.92)';
    c.beginPath();
    c.moveTo(28, 40); c.bezierCurveTo(44, 30, 56, 52, 72, 42); c.lineTo(72, 58); c.bezierCurveTo(56, 68, 44, 46, 28, 56); c.closePath(); c.fill();
    c.fillStyle = 'rgba(255,255,255,0.35)';
    rr(c, 33, 18, 5, 62, 2.5); c.fill();
  },
  bag(c) {
    c.fillStyle = '#2fa36b';
    c.beginPath();
    c.moveTo(20, 34); c.lineTo(80, 34); c.lineTo(86, 90); c.lineTo(14, 90); c.closePath();
    c.fill();
    c.lineWidth = 2.5; c.strokeStyle = '#1f7a4e'; c.stroke();
    c.strokeStyle = '#1f7a4e'; c.lineWidth = 5; c.lineCap = 'round';
    c.beginPath(); c.moveTo(36, 40); c.bezierCurveTo(36, 8, 64, 8, 64, 40); c.stroke();
    c.fillStyle = 'rgba(255,255,255,0.9)';
    c.beginPath(); c.arc(50, 62, 12, 0, Math.PI * 2); c.fill();
    c.fillStyle = '#2fa36b';
    c.font = 'bold 18px system-ui, sans-serif';
    c.textAlign = 'center'; c.textBaseline = 'middle';
    c.fillText('%', 50, 63);
  },
  battery(c) {
    rr(c, 14, 32, 68, 36, 8);
    c.fillStyle = '#3a4650'; c.fill();
    rr(c, 82, 42, 7, 16, 3); c.fill();
    rr(c, 19, 37, 40, 26, 5);
    c.fillStyle = '#4ed18a'; c.fill();
    c.fillStyle = 'rgba(255,255,255,0.9)';
    c.beginPath(); c.moveTo(48, 36); c.lineTo(36, 52); c.lineTo(45, 52); c.lineTo(40, 64); c.lineTo(56, 47); c.lineTo(47, 47); c.closePath(); c.fill();
  },
  plug(c) {
    rr(c, 28, 38, 44, 34, 9);
    c.fillStyle = '#4b5b66'; c.fill();
    c.fillStyle = '#c5cdd2';
    rr(c, 36, 16, 8, 26, 3); c.fill();
    rr(c, 56, 16, 8, 26, 3); c.fill();
    c.strokeStyle = '#4b5b66'; c.lineWidth = 6; c.lineCap = 'round';
    c.beginPath(); c.moveTo(50, 72); c.bezierCurveTo(50, 90, 74, 80, 78, 94); c.stroke();
    c.fillStyle = '#4ed18a';
    c.beginPath(); c.arc(50, 55, 5, 0, Math.PI * 2); c.fill();
  },
  cookie(c) {
    c.beginPath(); c.arc(50, 50, 34, 0, Math.PI * 2);
    c.fillStyle = '#d9a35c'; c.fill();
    c.lineWidth = 3; c.strokeStyle = '#b97f35'; c.stroke();
    c.fillStyle = '#5a3418';
    [[38, 38, 5], [60, 36, 4.5], [64, 58, 5.5], [42, 62, 5], [50, 48, 4]].forEach(([x, y, r]) => {
      c.beginPath(); c.arc(x, y, r, 0, Math.PI * 2); c.fill();
    });
    c.fillStyle = 'rgba(255,255,255,0.18)';
    c.beginPath(); c.arc(40, 34, 10, 0, Math.PI * 2); c.fill();
  },
  candy(c) {
    c.fillStyle = '#ef6fa3';
    c.beginPath(); c.moveTo(6, 32); c.lineTo(30, 46); c.lineTo(30, 54); c.lineTo(6, 68); c.closePath(); c.fill();
    c.beginPath(); c.moveTo(94, 32); c.lineTo(70, 46); c.lineTo(70, 54); c.lineTo(94, 68); c.closePath(); c.fill();
    rr(c, 28, 34, 44, 32, 16);
    c.fillStyle = '#f8a6c8'; c.fill();
    c.lineWidth = 2.5; c.strokeStyle = '#ef6fa3'; c.stroke();
    c.strokeStyle = '#ffffff'; c.lineWidth = 4; c.lineCap = 'round';
    c.beginPath(); c.moveTo(40, 44); c.lineTo(48, 58); c.moveTo(54, 40); c.lineTo(62, 54); c.stroke();
  },
  laptop(c) {
    rr(c, 20, 22, 60, 40, 5);
    c.fillStyle = '#2f3a42'; c.fill();
    rr(c, 25, 27, 50, 30, 3);
    c.fillStyle = '#5fd6a0'; c.fill();
    c.fillStyle = 'rgba(255,255,255,0.7)';
    rr(c, 30, 33, 22, 4, 2); c.fill();
    rr(c, 30, 41, 34, 3, 1.5); c.fill();
    rr(c, 30, 48, 28, 3, 1.5); c.fill();
    c.fillStyle = '#9aa6ad';
    c.beginPath(); c.moveTo(10, 64); c.lineTo(90, 64); c.lineTo(84, 74); c.lineTo(16, 74); c.closePath(); c.fill();
    c.fillStyle = '#c5cdd2'; rr(c, 42, 64, 16, 3, 1.5); c.fill();
  },
  watch(c) {
    c.fillStyle = '#3a4650';
    rr(c, 36, 4, 28, 26, 5); c.fill();
    rr(c, 36, 70, 28, 26, 5); c.fill();
    rr(c, 24, 26, 52, 48, 14);
    c.fillStyle = '#25323b'; c.fill();
    rr(c, 29, 31, 42, 38, 10);
    c.fillStyle = '#0f171c'; c.fill();
    c.strokeStyle = '#4ed18a'; c.lineWidth = 3; c.lineCap = 'round';
    c.beginPath(); c.arc(50, 50, 10, -Math.PI / 2, Math.PI * 0.9); c.stroke();
    c.fillStyle = '#fff';
    c.beginPath(); c.arc(50, 50, 2, 0, Math.PI * 2); c.fill();
  },
  cart(c) {
    c.strokeStyle = '#2b7a55'; c.lineWidth = 6; c.lineCap = 'round'; c.lineJoin = 'round';
    c.beginPath(); c.moveTo(8, 18); c.lineTo(22, 18); c.lineTo(34, 62); c.lineTo(76, 62); c.stroke();
    c.fillStyle = '#58c08a';
    c.beginPath(); c.moveTo(25, 28); c.lineTo(88, 28); c.lineTo(78, 54); c.lineTo(32, 54); c.closePath(); c.fill();
    c.lineWidth = 3; c.strokeStyle = '#2b7a55'; c.stroke();
    c.fillStyle = '#2b7a55';
    c.beginPath(); c.arc(40, 78, 6, 0, Math.PI * 2); c.fill();
    c.beginPath(); c.arc(70, 78, 6, 0, Math.PI * 2); c.fill();
  },
};

/* ---------- particles ---------- */

interface Particle {
  x: number; y: number;
  vx: number; vy: number;
  rot: number; vr: number;
  size: number;      // base on-screen size (px)
  depth: number;     // 0.55 (far) … 1.15 (near): scales size, speed, pull
  phase: number;     // drift direction (radians), random-walks over time
  phaseSpeed: number;
  sprite: HTMLCanvasElement;
  scale: number;     // eased hover scale
}

const rand = (a: number, b: number) => a + Math.random() * (b - a);

export default function RetailCanvas() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    // Pre-render every sprite once (cheap drawImage per frame afterwards).
    const sprites = new Map<SpriteKind, HTMLCanvasElement>();
    KINDS.forEach((k) => {
      const s = document.createElement('canvas');
      s.width = s.height = SPRITE * dpr * 1.5;
      const sc = s.getContext('2d')!;
      sc.scale(dpr * 1.5, dpr * 1.5);
      painters[k](sc);
      sprites.set(k, s);
    });

    let w = 0;
    let h = 0;
    let particles: Particle[] = [];
    const pointer = { x: -9999, y: -9999, active: false, lastMove: 0 };

    const build = () => {
      w = window.innerWidth;
      h = window.innerHeight;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      const count = Math.max(22, Math.min(56, Math.round((w * h) / 30000)));
      const prev = particles;
      particles = Array.from({ length: count }, (_, i) => {
        const old = prev[i];
        const kind = KINDS[i % KINDS.length];
        const depth = rand(0.55, 1.15);
        return {
          x: old ? Math.min(old.x, w) : rand(0, w),
          y: old ? Math.min(old.y, h) : rand(0, h),
          vx: 0, vy: 0,
          rot: rand(0, Math.PI * 2),
          vr: rand(-0.25, 0.25), // rad/sec
          size: rand(42, 70) * depth,
          depth,
          phase: rand(0, Math.PI * 2),
          phaseSpeed: rand(0.2, 0.7),
          sprite: sprites.get(kind)!,
          scale: 1,
        };
      });
      // far items first so near items overlap them
      particles.sort((a, b) => a.depth - b.depth);
    };

    const isDark = () => document.documentElement.classList.contains('dark');

    const RADIUS = 300; // pointer influence radius (px)

    let raf = 0;
    let last = performance.now();
    let t = 0;

    const draw = (stepSeconds: number) => {
      const dark = isDark();
      ctx.clearRect(0, 0, w, h);

      // soft glow following the pointer
      if (pointer.active && !reduceMotion) {
        const g = ctx.createRadialGradient(pointer.x, pointer.y, 0, pointer.x, pointer.y, RADIUS);
        g.addColorStop(0, dark ? 'rgba(80,210,140,0.20)' : 'rgba(47,158,98,0.16)');
        g.addColorStop(1, 'rgba(47,158,98,0)');
        ctx.fillStyle = g;
        ctx.fillRect(pointer.x - RADIUS, pointer.y - RADIUS, RADIUS * 2, RADIUS * 2);
      }

      for (const p of particles) {
        if (stepSeconds > 0) {
          // 1) random organic drift: heading slowly random-walks
          p.phase += (Math.sin(t * p.phaseSpeed + p.x * 0.004) * 0.9 + (Math.random() - 0.5) * 0.6) * stepSeconds;
          const cruise = 16 * p.depth;
          let tx = Math.cos(p.phase) * cruise;
          let ty = Math.sin(p.phase) * cruise;

          // 2) pointer interaction: pull in, orbit, and keep a little distance
          let near = 0;
          if (pointer.active) {
            const dx = pointer.x - p.x;
            const dy = pointer.y - p.y;
            const d = Math.hypot(dx, dy) || 1;
            if (d < RADIUS) {
              near = 1 - d / RADIUS;
              const nx = dx / d;
              const ny = dy / d;
              const pull = near * 260 * p.depth;
              // settle on a ring ~70px from the cursor instead of piling up
              const ring = d < 70 ? -(70 - d) * 5 : 0;
              tx += nx * (pull + ring);
              ty += ny * (pull + ring);
              // tangential swirl so items circle the cursor
              tx += -ny * near * 90 * p.depth;
              ty += nx * near * 90 * p.depth;
            }
          }

          // ease velocity toward the target (spring-like, frame-rate independent)
          const k = 1 - Math.exp(-3.2 * stepSeconds);
          p.vx += (tx - p.vx) * k;
          p.vy += (ty - p.vy) * k;
          p.x += p.vx * stepSeconds;
          p.y += p.vy * stepSeconds;

          // spin faster and grow slightly when close to the pointer
          p.rot += (p.vr + 0.9 * near * (p.vr >= 0 ? 1 : -1)) * stepSeconds;
          p.scale += ((1 + near * 0.32) - p.scale) * (1 - Math.exp(-6 * stepSeconds));
        }

        // wrap around the screen edges
        const m = p.size;
        if (p.x < -m) p.x = w + m;
        else if (p.x > w + m) p.x = -m;
        if (p.y < -m) p.y = h + m;
        else if (p.y > h + m) p.y = -m;

        const s = p.size * p.scale;
        ctx.save();
        ctx.globalAlpha = (dark ? 0.5 : 0.58) * (0.55 + 0.45 * p.depth);
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rot);
        ctx.drawImage(p.sprite, -s / 2, -s / 2, s, s);
        ctx.restore();
      }
    };

    const frame = (now: number) => {
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;
      t += dt;
      // pointer glow/pull fades away if the mouse has been idle off-window
      if (pointer.active && now - pointer.lastMove > 6000) pointer.active = false;
      draw(dt);
      raf = requestAnimationFrame(frame);
    };

    const onMove = (e: PointerEvent) => {
      pointer.x = e.clientX;
      pointer.y = e.clientY;
      pointer.active = true;
      pointer.lastMove = performance.now();
    };
    const onLeave = () => { pointer.active = false; };
    const onResize = () => { build(); if (reduceMotion) draw(0); };
    const onVisibility = () => {
      if (document.hidden) {
        cancelAnimationFrame(raf);
      } else if (!reduceMotion) {
        last = performance.now();
        raf = requestAnimationFrame(frame);
      }
    };

    build();

    if (reduceMotion) {
      draw(0); // single static frame
    } else {
      raf = requestAnimationFrame(frame);
      window.addEventListener('pointermove', onMove, { passive: true });
      document.addEventListener('pointerleave', onLeave);
      window.addEventListener('blur', onLeave);
      document.addEventListener('visibilitychange', onVisibility);
    }
    window.addEventListener('resize', onResize);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('pointermove', onMove);
      document.removeEventListener('pointerleave', onLeave);
      window.removeEventListener('blur', onLeave);
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('resize', onResize);
    };
  }, []);

  return (
    <canvas
      ref={ref}
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 z-0"
    />
  );
}
