'use client';

import { useEffect, useRef } from 'react';
import type { RetailScene } from '@/components/canvas/scene3d';

/**
 * Full-screen animated background of small, realistic 3D retail products
 * (snacks, chocolate, phones, electronics, bags …). They drift and tumble on
 * their own and react to the pointer: nearby items are pulled in, orbit the
 * cursor and spin up.
 *
 * - Three.js is loaded lazily after first paint (code-split), so it never
 *   blocks the login/dashboard from rendering.
 * - Sits behind the app (`fixed`, `pointer-events: none`); the pointer is read
 *   from `window`, so it works over every card and page.
 * - Respects `prefers-reduced-motion`, pauses when the tab is hidden, and
 *   silently does nothing if WebGL is unavailable.
 */
export default function RetailCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const glowRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const isDark = () => document.documentElement.classList.contains('dark');

    let scene: RetailScene | null = null;
    let cancelled = false;
    let idleTimer: ReturnType<typeof setTimeout> | undefined;

    const onMove = (e: PointerEvent) => {
      scene?.setPointer(e.clientX, e.clientY, true);
      const g = glowRef.current;
      if (g) {
        g.style.transform = `translate3d(${e.clientX - 320}px, ${e.clientY - 320}px, 0)`;
        g.style.opacity = '1';
      }
      clearTimeout(idleTimer);
      idleTimer = setTimeout(onLeave, 6000);
    };
    const onLeave = () => {
      scene?.setPointer(-9999, -9999, false);
      if (glowRef.current) glowRef.current.style.opacity = '0';
    };
    const onResize = () => { scene?.resize(); if (reduceMotion) scene?.renderStatic(); };
    const onVisibility = () => {
      if (!scene || reduceMotion) return;
      if (document.hidden) scene.stop(); else scene.start();
    };

    const themeObserver = new MutationObserver(() => {
      scene?.setDark(isDark());
      if (reduceMotion) scene?.renderStatic();
    });
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });

    // Load Three.js after the page is interactive.
    const boot = async () => {
      try {
        const { createRetailScene } = await import('@/components/canvas/scene3d');
        if (cancelled) return;
        scene = createRetailScene(canvas, { dark: isDark() });
        if (reduceMotion) {
          scene.renderStatic();
        } else {
          scene.start();
          window.addEventListener('pointermove', onMove, { passive: true });
          document.addEventListener('pointerleave', onLeave);
          window.addEventListener('blur', onLeave);
          document.addEventListener('visibilitychange', onVisibility);
        }
        window.addEventListener('resize', onResize);
        canvas.style.opacity = '1';
      } catch {
        /* WebGL unavailable — the page simply keeps its gradient background */
      }
    };
    const w = window as Window & { requestIdleCallback?: (cb: () => void) => number };
    if (w.requestIdleCallback) w.requestIdleCallback(() => { void boot(); });
    else setTimeout(() => { void boot(); }, 150);

    return () => {
      cancelled = true;
      clearTimeout(idleTimer);
      themeObserver.disconnect();
      window.removeEventListener('pointermove', onMove);
      document.removeEventListener('pointerleave', onLeave);
      window.removeEventListener('blur', onLeave);
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('resize', onResize);
      scene?.dispose();
    };
  }, []);

  return (
    <>
      {/* soft light that follows the pointer */}
      <div
        ref={glowRef}
        aria-hidden="true"
        className="pointer-events-none fixed left-0 top-0 z-0 h-[640px] w-[640px] rounded-full opacity-0 transition-opacity duration-500"
        style={{
          background:
            'radial-gradient(closest-side, rgb(var(--glow-a) / 0.28), rgb(var(--glow-a) / 0.08) 55%, transparent)',
          willChange: 'transform',
        }}
      />
      <canvas
        ref={canvasRef}
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 z-0 h-full w-full opacity-0 transition-opacity duration-1000"
      />
    </>
  );
}
