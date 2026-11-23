/**
 * Procedural, physically-shaded 3D retail products for the animated background.
 *
 * Everything is generated in code (geometry + canvas-drawn label textures) —
 * no model files or images are downloaded. Each product is built once as a
 * template and then cloned (cheaply, sharing geometry/materials) for every
 * floating instance. Labels use generic, invented names (no real brands).
 */
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';

export type ProductKind =
  | 'chocolate' | 'chips' | 'can' | 'phone' | 'bulb' | 'headphones' | 'battery'
  | 'charger' | 'cookie' | 'candy' | 'laptop' | 'watch' | 'bag' | 'bottle' | 'speaker';

/** Template keys (`kind:variant`) — a few kinds have colour variants. */
export const TEMPLATE_KEYS: string[] = [
  'chocolate:0', 'chocolate:1', 'chips:0', 'chips:1', 'chips:2', 'can:0', 'can:1', 'can:2',
  'phone:0', 'phone:1', 'bulb:0', 'headphones:0', 'battery:0', 'charger:0', 'cookie:0',
  'candy:0', 'candy:1', 'laptop:0', 'watch:0', 'bag:0', 'bag:1', 'bottle:0', 'bottle:1', 'speaker:0',
];

type Ctx = CanvasRenderingContext2D;

function rr(c: Ctx, x: number, y: number, w: number, h: number, r: number) {
  c.beginPath();
  c.moveTo(x + r, y);
  c.arcTo(x + w, y, x + w, y + h, r);
  c.arcTo(x + w, y + h, x, y + h, r);
  c.arcTo(x, y + h, x, y, r);
  c.arcTo(x, y, x + w, y, r);
  c.closePath();
}

export function buildProductTemplates() {
  const geos: THREE.BufferGeometry[] = [];
  const mats: THREE.Material[] = [];
  const texs: THREE.Texture[] = [];

  const geo = <T extends THREE.BufferGeometry>(g: T): T => { geos.push(g); return g; };
  const mat = <T extends THREE.Material>(m: T): T => { mats.push(m); return m; };
  const tex = (w: number, h: number, draw: (c: Ctx, w: number, h: number) => void, srgb = true) => {
    const cv = document.createElement('canvas');
    cv.width = w; cv.height = h;
    const c = cv.getContext('2d')!;
    draw(c, w, h);
    const t = new THREE.CanvasTexture(cv);
    if (srgb) t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = 4;
    texs.push(t);
    return t;
  };
  const mesh = (g: THREE.BufferGeometry, m: THREE.Material) => new THREE.Mesh(g, m);
  const rbox = (w: number, h: number, d: number, r: number) =>
    geo(new RoundedBoxGeometry(w, h, d, 4, Math.min(r, w / 2 - 0.001, h / 2 - 0.001, d / 2 - 0.001)));

  const std = (p: THREE.MeshStandardMaterialParameters) => mat(new THREE.MeshStandardMaterial(p));
  const phys = (p: THREE.MeshPhysicalMaterialParameters) => mat(new THREE.MeshPhysicalMaterial(p));

  /* ------------------------------------------------------------ chocolate */
  const chocolate = (v: number) => {
    const g = new THREE.Group();
    const cocoa = v === 0 ? '#4a2819' : '#2f1a12';
    const bump = tex(256, 512, (c, w, h) => {
      c.fillStyle = '#000'; c.fillRect(0, 0, w, h);
      const cols = 3, rows = 6, cw = w / cols, ch = h / rows;
      for (let i = 0; i < cols; i++) for (let j = 0; j < rows; j++) {
        const x = i * cw, y = j * ch;
        const gr = c.createLinearGradient(x, y, x + cw, y + ch);
        gr.addColorStop(0, '#fff'); gr.addColorStop(1, '#9a9a9a');
        c.fillStyle = gr; rr(c, x + 7, y + 7, cw - 14, ch - 14, 16); c.fill();
      }
    }, false);
    const body = mesh(rbox(0.62, 1, 0.09, 0.03), phys({
      color: cocoa, roughness: 0.34, clearcoat: 0.55, clearcoatRoughness: 0.35,
      bumpMap: bump, bumpScale: 2.2,
    }));
    g.add(body);

    const wrapTex = tex(256, 128, (c, w, h) => {
      const gr = c.createLinearGradient(0, 0, w, h);
      if (v === 0) { gr.addColorStop(0, '#e0b64a'); gr.addColorStop(1, '#b8872a'); }
      else { gr.addColorStop(0, '#59b88a'); gr.addColorStop(1, '#2b7d5a'); }
      c.fillStyle = gr; c.fillRect(0, 0, w, h);
      c.fillStyle = 'rgba(255,255,255,0.22)';
      for (let x = -20; x < w + 20; x += 26) { c.beginPath(); c.moveTo(x, 0); c.lineTo(x + 14, 0); c.lineTo(x - 6, h); c.lineTo(x - 20, h); c.fill(); }
      c.fillStyle = '#fff'; c.font = '800 54px system-ui, sans-serif'; c.textAlign = 'center'; c.textBaseline = 'middle';
      c.fillText('CHOCO', w / 2, h / 2 - 4);
      c.font = '600 16px system-ui, sans-serif'; c.fillText('MILK  •  70g', w / 2, h / 2 + 34);
    });
    const wrap = mesh(rbox(0.645, 0.46, 0.108, 0.02), std({ map: wrapTex, metalness: 0.85, roughness: 0.28 }));
    wrap.position.y = -0.27;
    g.add(wrap);
    return g;
  };

  /* ---------------------------------------------------------- chips bag */
  const chips = (v: number) => {
    const palettes = [
      ['#ffd24a', '#f0881f', '#d62f2f'],
      ['#7bd88f', '#2f9e62', '#ffd24a'],
      ['#ff8a5c', '#d6362f', '#ffd24a'],
    ][v];
    const art = tex(256, 400, (c, w, h) => {
      const gr = c.createLinearGradient(0, 0, 0, h);
      gr.addColorStop(0, palettes[0]); gr.addColorStop(1, palettes[1]);
      c.fillStyle = gr; c.fillRect(0, 0, w, h);
      c.fillStyle = 'rgba(0,0,0,0.18)';
      for (let x = 0; x < w; x += 6) { c.fillRect(x, 0, 2, 30); c.fillRect(x, h - 30, 2, 30); }
      c.fillStyle = palettes[2]; c.beginPath(); c.ellipse(w / 2, h * 0.5, 104, 84, 0, 0, Math.PI * 2); c.fill();
      c.lineWidth = 6; c.strokeStyle = 'rgba(255,255,255,0.9)'; c.stroke();
      c.fillStyle = '#fff'; c.textAlign = 'center'; c.textBaseline = 'middle';
      c.font = '900 44px system-ui, sans-serif'; c.fillText('CRISPS', w / 2, h * 0.47);
      c.font = '700 15px system-ui, sans-serif'; c.fillText('CLASSIC  SALTED', w / 2, h * 0.58);
      for (const [x, y, r] of [[60, 110, 0.3], [196, 96, -0.4], [150, 316, 0.2], [70, 300, -0.2]]) {
        c.save(); c.translate(x, y); c.rotate(r);
        c.fillStyle = '#f6c343'; c.strokeStyle = '#d9962b'; c.lineWidth = 3;
        c.beginPath(); c.ellipse(0, 0, 30, 22, 0, 0, Math.PI * 2); c.fill(); c.stroke(); c.restore();
      }
    });
    const bagGeo = geo(new THREE.BoxGeometry(0.66, 1, 0.24, 18, 36, 1));
    const p = bagGeo.attributes.position as THREE.BufferAttribute;
    for (let i = 0; i < p.count; i++) {
      let x = p.getX(i); const y = p.getY(i); const z = p.getZ(i);
      const ax = Math.min(Math.abs(x) / 0.33, 1), ay = Math.min(Math.abs(y) / 0.5, 1);
      const s = z >= 0 ? 1 : -1;
      x *= 1 - 0.05 * (1 - ay * ay);
      let nz = 0.012 + 0.108 * Math.pow(Math.max(1 - Math.pow(ax, 2.2), 0), 0.5) * Math.pow(Math.max(1 - Math.pow(ay, 5), 0), 0.45);
      if (ay > 0.9) nz = 0.01 + 0.008 * Math.sin(x * 80);
      p.setXYZ(i, x, y, s * nz);
    }
    geo(bagGeo).computeVertexNormals();
    return new THREE.Group().add(mesh(bagGeo, std({ map: art, metalness: 0.55, roughness: 0.36, side: THREE.DoubleSide })));
  };

  /* ---------------------------------------------------------------- can */
  const can = (v: number) => {
    const g = new THREE.Group();
    const cols = [['#e04040', '#a31e1e'], ['#3fa8e0', '#1e6fa3'], ['#4fc27f', '#1f8453']][v];
    const label = tex(512, 256, (c, w, h) => {
      const gr = c.createLinearGradient(0, 0, 0, h);
      gr.addColorStop(0, cols[0]); gr.addColorStop(1, cols[1]);
      c.fillStyle = gr; c.fillRect(0, 0, w, h);
      c.fillStyle = 'rgba(255,255,255,0.92)';
      for (const ox of [0, 256]) {
        c.beginPath(); c.moveTo(ox, 96); c.bezierCurveTo(ox + 70, 56, ox + 140, 150, ox + 256, 100);
        c.lineTo(ox + 256, 150); c.bezierCurveTo(ox + 140, 200, ox + 70, 106, ox, 146); c.fill();
        c.fillStyle = cols[1]; c.font = '900 52px system-ui, sans-serif'; c.textAlign = 'center'; c.textBaseline = 'middle';
        c.fillText('FIZZ', ox + 128, 124); c.fillStyle = 'rgba(255,255,255,0.92)';
      }
    });
    const body = mesh(geo(new THREE.CylinderGeometry(0.22, 0.22, 0.78, 48, 1, true)),
      std({ map: label, metalness: 0.7, roughness: 0.24 }));
    g.add(body);
    const silver = std({ color: '#d5dade', metalness: 1, roughness: 0.2 });
    const cap = (dir: 1 | -1) => {
      const pts = [[0.22, 0], [0.2, 0.05], [0.17, 0.09], [0.17, 0.1], [0.15, 0.1], [0.15, 0.085], [0, 0.085]]
        .map(([r, y]) => new THREE.Vector2(r, y));
      const m = mesh(geo(new THREE.LatheGeometry(pts, 40)), silver);
      m.position.y = dir * 0.39; if (dir === -1) m.rotation.x = Math.PI;
      return m;
    };
    g.add(cap(1), cap(-1));
    const tab = mesh(rbox(0.14, 0.012, 0.07, 0.01), silver); tab.position.set(0, 0.485, 0); g.add(tab);
    return g;
  };

  /* -------------------------------------------------------------- phone */
  const phone = (v: number) => {
    const g = new THREE.Group();
    const frame = v === 0 ? '#20262e' : '#cfd6dc';
    g.add(mesh(rbox(0.5, 1, 0.055, 0.075), std({ color: frame, metalness: 0.95, roughness: 0.28 })));
    const screen = tex(256, 512, (c, w, h) => {
      c.clearRect(0, 0, w, h);
      c.save(); rr(c, 0, 0, w, h, 34); c.clip();
      const gr = c.createLinearGradient(0, 0, w, h);
      if (v === 0) { gr.addColorStop(0, '#0f7a55'); gr.addColorStop(1, '#0b3d4a'); }
      else { gr.addColorStop(0, '#f5b94a'); gr.addColorStop(1, '#d6523a'); }
      c.fillStyle = gr; c.fillRect(0, 0, w, h);
      c.fillStyle = '#fff'; c.textAlign = 'center'; c.font = '700 58px system-ui, sans-serif'; c.fillText('9:41', w / 2, 112);
      c.font = '500 16px system-ui, sans-serif'; c.fillStyle = 'rgba(255,255,255,0.8)'; c.fillText('Monday, 23 November', w / 2, 140);
      const cols = ['#58c08a', '#f2b01e', '#2bb3c0', '#ef6b5b', '#7c83e8', '#fff', '#8bc34a', '#f58a3a'];
      for (let i = 0; i < 12; i++) {
        const x = 34 + (i % 4) * 52, y = 200 + Math.floor(i / 4) * 66;
        c.fillStyle = cols[i % cols.length]; rr(c, x, y, 40, 40, 11); c.fill();
      }
      c.fillStyle = 'rgba(255,255,255,0.28)'; rr(c, 20, h - 90, w - 40, 64, 20); c.fill();
      c.restore();
    });
    const scr = mesh(geo(new THREE.PlaneGeometry(0.47, 0.96)), mat(new THREE.MeshBasicMaterial({ map: screen, transparent: true, alphaTest: 0.5, toneMapped: false })));
    scr.position.z = 0.0285; g.add(scr);
    const backTex = tex(128, 256, (c, w, h) => {
      const gr = c.createLinearGradient(0, 0, w, h);
      if (v === 0) { gr.addColorStop(0, '#2c8f6a'); gr.addColorStop(1, '#154a43'); } else { gr.addColorStop(0, '#f1f3f5'); gr.addColorStop(1, '#bfc7cf'); }
      c.fillStyle = gr; c.fillRect(0, 0, w, h);
    });
    const back = mesh(geo(new THREE.PlaneGeometry(0.47, 0.96)), phys({ map: backTex, roughness: 0.2, clearcoat: 1, side: THREE.FrontSide }));
    back.rotation.y = Math.PI; back.position.z = -0.0282; g.add(back);
    const plate = mesh(rbox(0.22, 0.22, 0.016, 0.05), std({ color: '#1b1f25', metalness: 0.6, roughness: 0.3 }));
    plate.position.set(-0.1, 0.34, -0.04); g.add(plate);
    for (const [x, y] of [[-0.155, 0.395], [-0.155, 0.285], [-0.065, 0.34]]) {
      const lens = mesh(geo(new THREE.CylinderGeometry(0.036, 0.036, 0.02, 24)), std({ color: '#0a0c10', metalness: 1, roughness: 0.1 }));
      lens.rotation.x = Math.PI / 2; lens.position.set(x, y, -0.052); g.add(lens);
      const ring = mesh(geo(new THREE.TorusGeometry(0.036, 0.006, 10, 28)), std({ color: '#aeb6bd', metalness: 1, roughness: 0.25 }));
      ring.position.set(x, y, -0.062); g.add(ring);
    }
    return g;
  };

  /* --------------------------------------------------------------- bulb */
  const bulb = () => {
    const g = new THREE.Group();
    const pts: THREE.Vector2[] = [new THREE.Vector2(0.0001, 0.47)];
    for (let a = 0.12; a <= 2.45; a += 0.1) pts.push(new THREE.Vector2(0.27 * Math.sin(a), 0.2 + 0.27 * Math.cos(a)));
    pts.push(new THREE.Vector2(0.1, -0.12), new THREE.Vector2(0.1, -0.2));
    const glass = mesh(geo(new THREE.LatheGeometry(pts, 48)), phys({
      color: '#ffffff', roughness: 0.04, clearcoat: 1, transparent: true, opacity: 0.2, side: THREE.DoubleSide, depthWrite: false, envMapIntensity: 1.6,
    }));
    g.add(glass);
    const metal = std({ color: '#b7bec5', metalness: 1, roughness: 0.32 });
    for (let i = 0; i < 3; i++) {
      const ring = mesh(geo(new THREE.TorusGeometry(0.1, 0.017, 10, 32)), metal);
      ring.rotation.x = Math.PI / 2; ring.position.y = -0.22 - i * 0.045; g.add(ring);
    }
    const tip = mesh(geo(new THREE.CylinderGeometry(0.06, 0.04, 0.05, 20)), std({ color: '#7d8389', metalness: 1, roughness: 0.4 }));
    tip.position.y = -0.37; g.add(tip);
    const curve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-0.07, -0.08, 0), new THREE.Vector3(-0.045, 0.1, 0), new THREE.Vector3(-0.022, 0.13, 0), new THREE.Vector3(0, 0.1, 0),
      new THREE.Vector3(0.022, 0.13, 0), new THREE.Vector3(0.045, 0.1, 0), new THREE.Vector3(0.07, -0.08, 0),
    ]);
    const fil = mesh(geo(new THREE.TubeGeometry(curve, 40, 0.007, 6)), mat(new THREE.MeshBasicMaterial({ color: '#ffcf7a', toneMapped: false })));
    g.add(fil);
    const glow = mesh(geo(new THREE.SphereGeometry(0.2, 20, 14)), mat(new THREE.MeshBasicMaterial({ color: '#ffe3a1', transparent: true, opacity: 0.2, depthWrite: false, toneMapped: false })));
    glow.position.y = 0.17; g.add(glow);
    return g;
  };

  /* --------------------------------------------------------- headphones */
  const headphones = () => {
    const g = new THREE.Group();
    const plastic = std({ color: '#1d2228', roughness: 0.5, metalness: 0.2 });
    const accent = std({ color: '#2f9e62', roughness: 0.35, metalness: 0.5 });
    const pad = std({ color: '#2a2f36', roughness: 0.85 });
    const band = mesh(geo(new THREE.TorusGeometry(0.4, 0.035, 14, 56, Math.PI)), plastic); band.position.y = 0.08; g.add(band);
    const padArc = mesh(geo(new THREE.TorusGeometry(0.4, 0.05, 12, 40, Math.PI * 0.5)), pad);
    padArc.rotation.z = Math.PI * 0.25; padArc.position.y = 0.08; g.add(padArc);
    for (const s of [-1, 1]) {
      const cup = mesh(geo(new THREE.CylinderGeometry(0.17, 0.17, 0.12, 36)), plastic);
      cup.rotation.z = Math.PI / 2; cup.position.set(s * 0.4, 0.0, 0); g.add(cup);
      const disc = mesh(geo(new THREE.CylinderGeometry(0.12, 0.12, 0.02, 32)), accent);
      disc.rotation.z = Math.PI / 2; disc.position.set(s * 0.465, 0, 0); g.add(disc);
      const cushion = mesh(geo(new THREE.TorusGeometry(0.115, 0.05, 14, 32)), pad);
      cushion.rotation.y = Math.PI / 2; cushion.position.set(s * 0.335, 0, 0); g.add(cushion);
      const yoke = mesh(geo(new THREE.CylinderGeometry(0.016, 0.016, 0.1, 10)), std({ color: '#9aa3ab', metalness: 1, roughness: 0.3 }));
      yoke.position.set(s * 0.4, 0.08, 0); g.add(yoke);
    }
    return g;
  };

  /* ------------------------------------------------------------ battery */
  const battery = () => {
    const g = new THREE.Group();
    const label = tex(256, 256, (c, w, h) => {
      c.fillStyle = '#16191d'; c.fillRect(0, 0, w, h);
      const gr = c.createLinearGradient(0, 0, w, 0); gr.addColorStop(0, '#2f9e62'); gr.addColorStop(1, '#58c08a');
      c.fillStyle = gr; c.fillRect(0, 0, w, 82);
      c.fillStyle = '#e8b13a'; c.fillRect(0, 82, w, 8);
      c.fillStyle = '#fff'; c.font = '900 64px system-ui, sans-serif'; c.textAlign = 'center'; c.textBaseline = 'middle';
      c.fillText('VOLT', w / 2, 42);
      c.font = '700 40px system-ui, sans-serif'; c.fillStyle = '#e8b13a'; c.fillText('AA', w / 2, 150);
      c.font = '600 18px system-ui, sans-serif'; c.fillStyle = '#cfd6dc'; c.fillText('ALKALINE 1.5V', w / 2, 200);
    });
    g.add(mesh(geo(new THREE.CylinderGeometry(0.145, 0.145, 0.9, 40, 1, true)), std({ map: label, metalness: 0.6, roughness: 0.3 })));
    const steel = std({ color: '#cdd3d8', metalness: 1, roughness: 0.22 });
    const top = mesh(geo(new THREE.CylinderGeometry(0.145, 0.145, 0.03, 40)), steel); top.position.y = 0.46; g.add(top);
    const nub = mesh(geo(new THREE.CylinderGeometry(0.055, 0.055, 0.05, 28)), steel); nub.position.y = 0.5; g.add(nub);
    const bot = mesh(geo(new THREE.CylinderGeometry(0.145, 0.145, 0.03, 40)), steel); bot.position.y = -0.46; g.add(bot);
    return g;
  };

  /* ------------------------------------------------------------ charger */
  const charger = () => {
    const g = new THREE.Group();
    g.add(mesh(rbox(0.5, 0.6, 0.34, 0.07), phys({ color: '#f4f6f7', roughness: 0.32, clearcoat: 0.6 })));
    const brass = std({ color: '#c9ced3', metalness: 1, roughness: 0.25 });
    for (const x of [-0.1, 0.1]) { const prong = mesh(rbox(0.05, 0.18, 0.016, 0.004), brass); prong.position.set(x, 0.38, 0); g.add(prong); }
    const port = mesh(rbox(0.16, 0.05, 0.02, 0.02), std({ color: '#15181c', roughness: 0.6 })); port.position.set(0, -0.05, 0.172); g.add(port);
    const led = mesh(geo(new THREE.SphereGeometry(0.015, 12, 10)), mat(new THREE.MeshBasicMaterial({ color: '#58f0a0', toneMapped: false }))); led.position.set(0.17, 0.2, 0.172); g.add(led);
    const cable = new THREE.CatmullRomCurve3([
      new THREE.Vector3(0, -0.3, 0.1), new THREE.Vector3(0.05, -0.5, 0.22), new THREE.Vector3(0.22, -0.62, 0.1), new THREE.Vector3(0.12, -0.8, -0.05),
    ]);
    g.add(mesh(geo(new THREE.TubeGeometry(cable, 30, 0.025, 8)), std({ color: '#eef0f2', roughness: 0.55 })));
    return g;
  };

  /* ------------------------------------------------------------- cookie */
  const cookie = () => {
    const g = new THREE.Group();
    const cg = geo(new THREE.CylinderGeometry(0.5, 0.5, 0.14, 48, 4));
    const p = cg.attributes.position as THREE.BufferAttribute;
    for (let i = 0; i < p.count; i++) {
      const x = p.getX(i), z = p.getZ(i); let y = p.getY(i);
      const a = Math.atan2(z, x), r = Math.hypot(x, z);
      const k = 1 + 0.035 * Math.sin(a * 5 + 1) + 0.02 * Math.sin(a * 9 + 2);
      if (y > 0) y += 0.018 * Math.sin(x * 14) * Math.cos(z * 12) + 0.012 * (1 - r * 1.4);
      p.setXYZ(i, x * k, y, z * k);
    }
    cg.computeVertexNormals();
    const speck = tex(256, 256, (c, w, h) => {
      c.fillStyle = '#808080'; c.fillRect(0, 0, w, h);
      for (let i = 0; i < 1400; i++) { const v = 90 + Math.random() * 140; c.fillStyle = `rgb(${v},${v},${v})`; c.fillRect(Math.random() * w, Math.random() * h, 2, 2); }
    }, false);
    g.add(mesh(cg, std({ color: '#c98f4e', roughness: 0.92, bumpMap: speck, bumpScale: 3 })));
    const chipMat = std({ color: '#33190f', roughness: 0.5 });
    const rng = (n: number) => { const s = Math.sin(n * 91.7) * 43758.5453; return s - Math.floor(s); };
    for (let i = 0; i < 9; i++) {
      const a = rng(i) * Math.PI * 2, r = 0.08 + rng(i + 20) * 0.32;
      const ch = mesh(geo(new THREE.IcosahedronGeometry(0.06 + rng(i + 40) * 0.03, 0)), chipMat);
      ch.scale.y = 0.55; ch.position.set(Math.cos(a) * r, 0.075, Math.sin(a) * r); ch.rotation.set(rng(i) * 3, rng(i + 1) * 3, 0); g.add(ch);
    }
    g.rotation.x = 0.0;
    return g;
  };

  /* -------------------------------------------------------------- candy */
  const candy = (v: number) => {
    const g = new THREE.Group();
    const stripe = tex(128, 128, (c, w, h) => {
      c.fillStyle = v === 0 ? '#f06fa0' : '#58c08a'; c.fillRect(0, 0, w, h);
      c.fillStyle = 'rgba(255,255,255,0.85)';
      for (let x = -h; x < w + h; x += 32) { c.beginPath(); c.moveTo(x, 0); c.lineTo(x + 14, 0); c.lineTo(x + 14 + h, h); c.lineTo(x + h, h); c.fill(); }
    });
    const body = mesh(geo(new THREE.CapsuleGeometry(0.17, 0.4, 10, 24)), phys({ map: stripe, roughness: 0.22, clearcoat: 1 }));
    body.rotation.z = Math.PI / 2; g.add(body);
    const wrapMat = phys({ color: v === 0 ? '#f6a0c2' : '#9be0bc', roughness: 0.25, clearcoat: 1, transparent: true, opacity: 0.85, side: THREE.DoubleSide });
    for (const s of [-1, 1]) {
      const twist = mesh(geo(new THREE.ConeGeometry(0.06, 0.1, 14)), wrapMat);
      twist.rotation.z = -s * Math.PI / 2; twist.position.x = s * 0.4; g.add(twist);
      const fan = mesh(geo(new THREE.ConeGeometry(0.2, 0.26, 20, 1, true)), wrapMat);
      fan.rotation.z = s * Math.PI / 2; fan.scale.z = 0.3; fan.position.x = s * 0.55; g.add(fan);
    }
    return g;
  };

  /* ------------------------------------------------------------- laptop */
  const laptop = () => {
    const g = new THREE.Group();
    const alu = std({ color: '#b9c1c8', metalness: 1, roughness: 0.3 });
    g.add(mesh(rbox(0.9, 0.04, 0.6, 0.02), alu));
    const keys = tex(256, 160, (c, w, h) => {
      c.fillStyle = '#14181c'; c.fillRect(0, 0, w, h);
      c.fillStyle = '#2c333a';
      for (let r = 0; r < 5; r++) for (let k = 0; k < 14; k++) { rr(c, 8 + k * 17.2, 8 + r * 20, 14, 16, 3); c.fill(); }
      c.fillStyle = '#2c333a'; rr(c, 90, 112, 76, 40, 6); c.fill();
    });
    const kb = mesh(geo(new THREE.PlaneGeometry(0.78, 0.42)), std({ map: keys, roughness: 0.8 }));
    kb.rotation.x = -Math.PI / 2; kb.position.set(0, 0.0212, -0.04); g.add(kb);
    const pivot = new THREE.Group(); pivot.position.set(0, 0.02, -0.3); pivot.rotation.x = -1.95; g.add(pivot);
    const lid = mesh(rbox(0.9, 0.03, 0.6, 0.015), alu); lid.position.z = 0.3; pivot.add(lid);
    const scr = tex(256, 160, (c, w, h) => {
      const gr = c.createLinearGradient(0, 0, w, h); gr.addColorStop(0, '#0f6e50'); gr.addColorStop(1, '#0a3a44');
      c.fillStyle = gr; c.fillRect(0, 0, w, h);
      c.fillStyle = 'rgba(255,255,255,0.9)'; c.fillRect(12, 12, 90, 8);
      const bars = [40, 62, 48, 80, 66, 92, 74];
      bars.forEach((b, i) => { c.fillStyle = i % 2 ? '#58c08a' : '#f2b01e'; c.fillRect(20 + i * 30, 140 - b, 18, b); });
    });
    const screen = mesh(geo(new THREE.PlaneGeometry(0.84, 0.54)), mat(new THREE.MeshBasicMaterial({ map: scr, toneMapped: false })));
    screen.rotation.x = Math.PI / 2; screen.position.set(0, -0.0165, 0.3); pivot.add(screen);
    return g;
  };

  /* -------------------------------------------------------------- watch */
  const watch = () => {
    const g = new THREE.Group();
    const strapMat = std({ color: '#2f9e62', roughness: 0.55 });
    for (const s of [-1, 1]) {
      const strap = mesh(rbox(0.3, 0.5, 0.05, 0.02), strapMat);
      strap.position.set(0, s * 0.48, -0.02); strap.rotation.x = s * 0.12; g.add(strap);
    }
    g.add(mesh(rbox(0.44, 0.52, 0.13, 0.11), std({ color: '#262d34', metalness: 0.9, roughness: 0.3 })));
    const face = tex(256, 256, (c, w, h) => {
      c.clearRect(0, 0, w, h); c.save(); rr(c, 0, 0, w, h, 70); c.clip();
      c.fillStyle = '#05080a'; c.fillRect(0, 0, w, h);
      c.lineWidth = 16; c.lineCap = 'round';
      const rings: [number, string, number][] = [[100, '#58c08a', 0.8], [76, '#f2b01e', 0.55], [52, '#2bb3c0', 0.4]];
      for (const [r, col, f] of rings) { c.strokeStyle = 'rgba(255,255,255,0.1)'; c.beginPath(); c.arc(w / 2, h / 2, r, 0, Math.PI * 2); c.stroke(); c.strokeStyle = col; c.beginPath(); c.arc(w / 2, h / 2, r, -Math.PI / 2, -Math.PI / 2 + f * Math.PI * 2); c.stroke(); }
      c.fillStyle = '#fff'; c.font = '700 40px system-ui, sans-serif'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText('10:09', w / 2, h / 2);
      c.restore();
    });
    const scr = mesh(geo(new THREE.PlaneGeometry(0.39, 0.47)), mat(new THREE.MeshBasicMaterial({ map: face, transparent: true, alphaTest: 0.5, toneMapped: false })));
    scr.position.z = 0.067; g.add(scr);
    const crown = mesh(geo(new THREE.CylinderGeometry(0.035, 0.035, 0.05, 16)), std({ color: '#c9ced3', metalness: 1, roughness: 0.25 }));
    crown.rotation.z = Math.PI / 2; crown.position.set(0.23, 0.1, 0); g.add(crown);
    return g;
  };

  /* ---------------------------------------------------------------- bag */
  const bag = (v: number) => {
    const g = new THREE.Group();
    const art = tex(256, 320, (c, w, h) => {
      c.fillStyle = v === 0 ? '#c9a06b' : '#f4efe6'; c.fillRect(0, 0, w, h);
      c.fillStyle = v === 0 ? 'rgba(0,0,0,0.05)' : 'rgba(0,0,0,0.04)';
      for (let i = 0; i < 600; i++) c.fillRect(Math.random() * w, Math.random() * h, 2, 2);
      c.fillStyle = '#2f9e62'; c.fillRect(0, h - 70, w, 70);
      c.fillStyle = '#fff'; c.beginPath(); c.arc(w / 2, h * 0.46, 56, 0, Math.PI * 2); c.fill();
      c.fillStyle = '#2f9e62'; c.font = '900 70px system-ui, sans-serif'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText('R', w / 2, h * 0.46 + 4);
      c.fillStyle = '#fff'; c.font = '700 22px system-ui, sans-serif'; c.fillText('RETAIL  STORE', w / 2, h - 34);
    });
    g.add(mesh(geo(new THREE.BoxGeometry(0.7, 0.85, 0.32)), std({ map: art, roughness: 0.85 })));
    const rope = std({ color: v === 0 ? '#6b4a2a' : '#2f9e62', roughness: 0.7 });
    for (const z of [0.17, -0.17]) {
      const curve = new THREE.CatmullRomCurve3([
        new THREE.Vector3(-0.17, 0.42, z), new THREE.Vector3(-0.14, 0.6, z * 1.05), new THREE.Vector3(0, 0.68, z * 1.06),
        new THREE.Vector3(0.14, 0.6, z * 1.05), new THREE.Vector3(0.17, 0.42, z),
      ]);
      g.add(mesh(geo(new THREE.TubeGeometry(curve, 30, 0.014, 8)), rope));
    }
    return g;
  };

  /* ------------------------------------------------------------- bottle */
  const bottle = (v: number) => {
    const g = new THREE.Group();
    const profile = (k: number) => [
      [0.0001, -0.5], [0.15 * k, -0.5], [0.17 * k, -0.47], [0.17 * k, 0.14], [0.15 * k, 0.26], [0.075 * k, 0.36], [0.065 * k, 0.4], [0.065 * k, 0.46],
    ].map(([r, y]) => new THREE.Vector2(r, y));
    g.add(mesh(geo(new THREE.LatheGeometry(profile(1), 40)), phys({
      color: '#ffffff', roughness: 0.04, clearcoat: 1, transparent: true, opacity: 0.22, side: THREE.DoubleSide, depthWrite: false, envMapIntensity: 1.5,
    })));
    const liquid = v === 0 ? '#ff9f2e' : '#e0405a';
    g.add(mesh(geo(new THREE.LatheGeometry(profile(0.93).slice(0, 5), 40)), phys({ color: liquid, roughness: 0.15, clearcoat: 0.8, transparent: true, opacity: 0.88 })));
    const lab = tex(256, 128, (c, w, h) => {
      c.fillStyle = '#fff'; c.fillRect(0, 0, w, h);
      c.fillStyle = liquid; c.fillRect(0, 0, w, 26); c.fillRect(0, h - 26, w, 26);
      c.fillStyle = '#1d3a2b'; c.font = '900 40px system-ui, sans-serif'; c.textAlign = 'center'; c.textBaseline = 'middle';
      for (const ox of [0, 128]) c.fillText('FRESH', ox + 64, h / 2 - 2);
    });
    const band = mesh(geo(new THREE.CylinderGeometry(0.1745, 0.1745, 0.34, 40, 1, true)), std({ map: lab, roughness: 0.5 }));
    band.position.y = -0.14; g.add(band);
    const cap = mesh(geo(new THREE.CylinderGeometry(0.07, 0.07, 0.07, 24)), std({ color: v === 0 ? '#2f9e62' : '#f4f6f7', roughness: 0.4 }));
    cap.position.y = 0.5; g.add(cap);
    return g;
  };

  /* ------------------------------------------------------------ speaker */
  const speaker = () => {
    const g = new THREE.Group();
    const grille = tex(256, 128, (c, w, h) => {
      c.fillStyle = '#1b2025'; c.fillRect(0, 0, w, h);
      c.fillStyle = '#3a434b';
      for (let y = 6; y < h; y += 10) for (let x = (y / 10) % 2 ? 4 : 9; x < w; x += 10) { c.beginPath(); c.arc(x, y, 2.2, 0, Math.PI * 2); c.fill(); }
    });
    g.add(mesh(geo(new THREE.CylinderGeometry(0.24, 0.24, 0.66, 44, 1, true)), std({ map: grille, roughness: 0.6, metalness: 0.3 })));
    const rubber = std({ color: '#262c32', roughness: 0.8 });
    const topc = mesh(geo(new THREE.CylinderGeometry(0.245, 0.245, 0.06, 44)), rubber); topc.position.y = 0.33; g.add(topc);
    const botc = mesh(geo(new THREE.CylinderGeometry(0.245, 0.245, 0.06, 44)), rubber); botc.position.y = -0.33; g.add(botc);
    const ring = mesh(geo(new THREE.TorusGeometry(0.245, 0.012, 10, 48)), mat(new THREE.MeshBasicMaterial({ color: '#58f0a0', toneMapped: false })));
    ring.rotation.x = Math.PI / 2; ring.position.y = 0.3; g.add(ring);
    for (const [x, z] of [[-0.09, 0], [0.09, 0], [0, 0.09]]) {
      const b = mesh(geo(new THREE.CylinderGeometry(0.03, 0.03, 0.01, 18)), std({ color: '#c9ced3', metalness: 1, roughness: 0.3 }));
      b.position.set(x, 0.365, z); g.add(b);
    }
    return g;
  };

  /* ------------------------------------------------- assemble + normalise */
  const make = (key: string): THREE.Group => {
    const [kind, vs] = key.split(':');
    const v = Number(vs);
    switch (kind as ProductKind) {
      case 'chocolate': return chocolate(v);
      case 'chips': return chips(v);
      case 'can': return can(v);
      case 'phone': return phone(v);
      case 'bulb': return bulb();
      case 'headphones': return headphones();
      case 'battery': return battery();
      case 'charger': return charger();
      case 'cookie': return cookie();
      case 'candy': return candy(v);
      case 'laptop': return laptop();
      case 'watch': return watch();
      case 'bag': return bag(v);
      case 'bottle': return bottle(v);
      default: return speaker();
    }
  };

  const templates = new Map<string, THREE.Group>();
  for (const key of TEMPLATE_KEYS) {
    const inner = make(key);
    // Centre on its bounding box and scale so the longest side is 1 unit.
    const box = new THREE.Box3().setFromObject(inner);
    const size = box.getSize(new THREE.Vector3());
    const centre = box.getCenter(new THREE.Vector3());
    inner.position.sub(centre);
    const outer = new THREE.Group();
    outer.add(inner);
    outer.scale.setScalar(1 / Math.max(size.x, size.y, size.z, 0.0001));
    const holder = new THREE.Group();
    holder.add(outer);
    templates.set(key, holder);
  }

  return {
    templates,
    dispose() {
      geos.forEach((g) => g.dispose());
      mats.forEach((m) => m.dispose());
      texs.forEach((t) => t.dispose());
    },
  };
}
