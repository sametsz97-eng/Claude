import * as THREE from 'three';
import { Sky } from 'three/addons/objects/Sky.js';

const P = new URLSearchParams(location.search);
const VIEW = P.get('view') || 'front';
const W = +(P.get('w') || 1600), H = +(P.get('h') || 1000);

// ---------- renderer ----------
const renderer = new THREE.WebGLRenderer({ antialias: true, logarithmicDepthBuffer: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(W, H);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.7;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();

// ---------- utils ----------
const ss = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
function hash(i, j) { let n = Math.imul(i, 374761393) + Math.imul(j, 668265263); n = Math.imul(n ^ (n >>> 13), 1274126177); return ((n ^ (n >>> 16)) >>> 0) / 4294967296; }
function vnoise(x, y) {
  const i = Math.floor(x), j = Math.floor(y), fx = x - i, fy = y - j;
  const u = fx * fx * (3 - 2 * fx), v = fy * fy * (3 - 2 * fy);
  const a = hash(i, j), b = hash(i + 1, j), c = hash(i, j + 1), d = hash(i + 1, j + 1);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}
function fbm(x, y, o = 5) { let s = 0, a = 0.5, f = 1, n = 0; for (let k = 0; k < o; k++) { s += a * vnoise(x * f, y * f); n += a; a *= 0.5; f *= 2.03; } return s / n; }
function ridged(x, y, o = 5) { let s = 0, a = 0.5, f = 1, n = 0; for (let k = 0; k < o; k++) { s += a * (1 - Math.abs(2 * vnoise(x * f, y * f) - 1)); n += a; a *= 0.5; f *= 2.1; } return s / n; }
function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

function canvasTex(size, draw, rep) {
  const c = document.createElement('canvas'); c.width = c.height = size;
  draw(c.getContext('2d'), size);
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; if (rep) t.repeat.set(rep[0], rep[1]);
  return t;
}
const R = rng(7);
const tileTex = canvasTex(512, (g, s) => {
  const n = 6, w = s / n;
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
    const k = 0.9 + R() * 0.15; g.fillStyle = `rgb(${190 * k | 0},${150 * k | 0},${118 * k | 0})`; g.fillRect(i * w, j * w, w, w);
  }
  g.strokeStyle = '#d8cfc2'; g.lineWidth = 4; for (let i = 0; i <= n; i++) { g.beginPath(); g.moveTo(i * w, 0); g.lineTo(i * w, s); g.stroke(); g.beginPath(); g.moveTo(0, i * w); g.lineTo(s, i * w); g.stroke(); }
});
const woodTex = canvasTex(512, (g, s) => {
  const n = 8, w = s / n;
  for (let i = 0; i < n; i++) { const k = 0.85 + R() * 0.25; g.fillStyle = `rgb(${196 * k | 0},${160 * k | 0},${118 * k | 0})`; g.fillRect(0, i * w, s, w - 2); g.fillStyle = 'rgba(90,60,30,.5)'; g.fillRect(0, i * w + w - 2, s, 2); }
  for (let k = 0; k < 400; k++) { g.fillStyle = `rgba(110,75,40,${R() * 0.12})`; g.fillRect(R() * s, R() * s, 40 + R() * 120, 1); }
});
const plasterTex = canvasTex(256, (g, s) => {
  g.fillStyle = '#fff'; g.fillRect(0, 0, s, s);
  for (let k = 0; k < 6000; k++) { const v = 225 + R() * 30; g.fillStyle = `rgba(${v},${v},${v},.5)`; g.fillRect(R() * s, R() * s, 2, 2); }
}, [3, 3]);
const stoneTex = canvasTex(512, (g, s) => {
  g.fillStyle = '#9a9385'; g.fillRect(0, 0, s, s);
  let y = 0; while (y < s) { const h = 40 + R() * 40; let x = -R() * 60; while (x < s) { const w = 60 + R() * 90; const k = 0.75 + R() * 0.4; g.fillStyle = `rgb(${165 * k | 0},${150 * k | 0},${128 * k | 0})`; g.fillRect(x + 3, y + 3, w - 6, h - 6); x += w; } y += h; }
});
// sea normal map (tileable sines)
function seaNormal() {
  const s = 256, d = new Uint8Array(s * s * 4); const waves = [];
  const rr = rng(3); for (let k = 0; k < 14; k++) waves.push([Math.round((rr() * 2 - 1) * 9), Math.round((rr() * 2 - 1) * 9), rr() * 6.28, 1 / (1 + k * 0.3)]);
  for (let y = 0; y < s; y++) for (let x = 0; x < s; x++) {
    let dx = 0, dy = 0;
    for (const [kx, ky, ph, a] of waves) { const ang = 2 * Math.PI * (kx * x + ky * y) / s + ph; const c = Math.cos(ang) * a; dx += c * kx; dy += c * ky; }
    const nx = -dx * 0.05, ny = -dy * 0.05, l = Math.hypot(nx, ny, 1); const i = (y * s + x) * 4;
    d[i] = (nx / l * 0.5 + 0.5) * 255; d[i + 1] = (ny / l * 0.5 + 0.5) * 255; d[i + 2] = (1 / l * 0.5 + 0.5) * 255; d[i + 3] = 255;
  }
  const t = new THREE.DataTexture(d, s, s); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.generateMipmaps = true; t.minFilter = THREE.LinearMipmapLinearFilter; t.magFilter = THREE.LinearFilter; t.needsUpdate = true; t.repeat.set(1500, 1500); return t;
}

const M = (c, o = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.9, ...o });
const mat = {
  plaster: M(0xf0e6d0, { map: plasterTex }), plasterGround: M(0xe6d9bd, { map: plasterTex }), plasterIn: M(0xf6f3ec),
  stone: M(0xffffff, { map: stoneTex }), concrete: M(0xb4b0a6), coping: M(0xd9d4c8, { roughness: 0.6 }),
  roof: M(0x9b3a27, { roughness: 0.42, metalness: 0.35 }), roofUnder: M(0xc9ccce, { roughness: 0.5, metalness: 0.2 }), roofEdge: M(0x7e2c1d, { roughness: 0.45, metalness: 0.35 }),
  steel: M(0x2a2c2f, { roughness: 0.5, metalness: 0.6 }), galv: M(0xa7adb3, { roughness: 0.35, metalness: 0.8 }),
  frame: M(0xf5f5f3, { roughness: 0.45 }), glass: M(0x1d2b35, { roughness: 0.04, metalness: 0.95 }),
  tile: M(0xffffff, { map: tileTex, roughness: 0.75 }), wood: M(0xffffff, { map: woodTex, roughness: 0.7 }),
  door: M(0x6b4528, { roughness: 0.6 }), asphalt: M(0x46474a, { roughness: 0.95 }), curb: M(0xcfcac0),
  sofa: M(0x5f7387), bed: M(0xeee8de), darkwood: M(0x5a3b22, { roughness: 0.6 }), lightwood: M(0xc9a77c, { roughness: 0.7 }),
  white: M(0xf2f2f0, { roughness: 0.4 }), counter: M(0x3a3a3a, { roughness: 0.4 }), cushion: M(0xd9c9a8),
  pot: M(0xa8573a), plant: M(0x4f6b32, { flatShading: true }), chair: M(0x3b3b3b, { roughness: 0.6 }),
};

function boxB(x0, x1, y0, y1, z0, z1, m, parent = scene, cast = true) {
  const g = new THREE.BoxGeometry(Math.abs(x1 - x0), Math.abs(y1 - y0), Math.abs(z1 - z0));
  const me = new THREE.Mesh(g, m); me.position.set((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2);
  me.castShadow = cast; me.receiveShadow = true; parent.add(me); return me;
}
function wbox(axis, s0, s1, y0, y1, n0, n1, m, parent) {
  return axis === 'x' ? boxB(s0, s1, y0, y1, Math.min(n0, n1), Math.max(n0, n1), m, parent) : boxB(Math.min(n0, n1), Math.max(n0, n1), y0, y1, s0, s1, m, parent);
}
// wall along axis ('x' or 'z') from a0..a1, centered at c, openings {a,b,s,e,type,panes}
function wall(axis, a0, a1, c, y0, h, t, openings, m, parent, out = 1, frameMat = mat.frame) {
  const seg = (s0, s1, yy0, yy1) => { if (s1 - s0 > 1e-3 && yy1 - yy0 > 1e-3) wbox(axis, s0, s1, yy0, yy1, c - t / 2, c + t / 2, m, parent); };
  let cur = a0;
  for (const o of [...openings].sort((p, q) => p.a - q.a)) { seg(cur, o.a, y0, y0 + h); seg(o.a, o.b, y0, y0 + o.s); seg(o.a, o.b, y0 + o.e, y0 + h); cur = o.b; }
  seg(cur, a1, y0, y0 + h);
  for (const o of openings) {
    if (o.type === 'open') continue;
    const Y0 = y0 + o.s, Y1 = y0 + o.e, f = 0.06, n0 = c - 0.035 + out * 0.03, n1 = c + 0.035 + out * 0.03;
    const fm = o.fm || frameMat;
    wbox(axis, o.a, o.a + f, Y0, Y1, n0, n1, fm, parent); wbox(axis, o.b - f, o.b, Y0, Y1, n0, n1, fm, parent);
    wbox(axis, o.a, o.b, Y1 - f, Y1, n0, n1, fm, parent); wbox(axis, o.a, o.b, Y0, Y0 + f, n0, n1, fm, parent);
    const p = o.panes || 2; for (let k = 1; k < p; k++) { const x = o.a + (o.b - o.a) * k / p; wbox(axis, x - f / 2, x + f / 2, Y0, Y1, n0, n1, fm, parent); }
    if (o.transom) { const y = Y1 - o.transom; wbox(axis, o.a, o.b, y - f / 2, y + f / 2, n0, n1, fm, parent); }
    const gm = o.panel ? mat.door : mat.glass;
    wbox(axis, o.a + 0.02, o.b - 0.02, Y0 + 0.02, Y1 - 0.02, (n0 + n1) / 2 - 0.006, (n0 + n1) / 2 + 0.006, gm, parent);
    if (o.s > 0.3) wbox(axis, o.a - 0.04, o.b + 0.04, Y0 - 0.04, Y0, c, c + out * (t / 2 + 0.05), mat.coping, parent); // denizlik
  }
}

// ---------- dimensions ----------
const GF = 3.0;          // existing slab top (upper floor level)
const WH = 2.2;          // new wall height
const TOP = GF + WH;     // 5.2
const TH = THREE.MathUtils.degToRad(15), TAN = Math.tan(TH);
const SHEET0 = TOP + 0.17; // sheet height at |z|=6
const RIDGE = SHEET0 + 6 * TAN;
const house = new THREE.Group(); scene.add(house);
const roofG = new THREE.Group(); scene.add(roofG);
const upperG = new THREE.Group(); scene.add(upperG);
const interiorG = new THREE.Group(); scene.add(interiorG);

// ---------- existing ground floor ----------
const T = 0.2;
const gfWin = (a, b) => ({ a, b, s: 0.9, e: 2.2, panes: 2 });
wall('x', -5, 5, 5.9, 0, 2.8, T, [gfWin(-3.6, -1.6), gfWin(1.6, 3.6)], mat.plasterGround, house, 1);
wall('x', -5, 5, -5.9, 0, 2.8, T, [gfWin(-2.6, -1.2), gfWin(0.8, 2.2), { a: 3.4, b: 4.3, s: 0, e: 2.1, panes: 1, panel: true }], mat.plasterGround, house, -1);
wall('z', -5.8, 5.8, 4.9, 0, 2.8, T, [gfWin(1.8, 3.6), { a: -4.6, b: -3.8, s: 1.6, e: 2.2, panes: 1 }, { a: -1.6, b: -0.8, s: 1.6, e: 2.2, panes: 1 }], mat.plasterGround, house, 1);
wall('z', -5.8, 5.8, -4.9, 0, 2.8, T, [gfWin(1.6, 3.2)], mat.plasterGround, house, -1);
// plinth (subasman) stone band
boxB(-5.04, 5.04, 0, 0.45, 5.78, 6.04, mat.stone, house); boxB(-5.04, 5.04, 0, 0.45, -6.04, -5.78, mat.stone, house);
boxB(4.78, 5.04, 0, 0.45, -6.04, 6.04, mat.stone, house); boxB(-5.04, -4.78, 0, 0.45, -6.04, 6.04, mat.stone, house);
// slab band (existing concrete slab edge)
boxB(-5.03, 5.03, 2.8, GF, -6.03, 6.03, mat.concrete, house);
// west annex (1 x 6 m) with entrance
boxB(-6, -5, 0, 2.6, -5.5, 0.5, mat.plasterGround, house);
boxB(-6.15, -4.95, 2.6, 2.75, -5.65, 0.65, mat.concrete, house);
boxB(-6.04, -5.98, 0, 2.1, -2.9, -1.9, mat.door, house);
boxB(-6.5, -6, 0, 0.15, -3.2, -1.6, mat.concrete, house);
// apron
boxB(-7, 6, 0, 0.03, -7, 7, mat.concrete, house, false);

// ---------- NEW UPPER FLOOR (2.20 m walls) ----------
// floor finishes
boxB(-4.8, 4.8, GF, GF + 0.03, 3.0, 5.8, mat.tile, upperG, false);           // terrace tiles
boxB(-3.0, 4.8, GF, GF + 0.02, -5.8, 3.0, mat.wood, upperG, false);          // interior laminate
boxB(-4.8, -3.0, GF, GF + 0.02, -1.5, 3.0, mat.wood, upperG, false);
// exterior walls
const win = (a, b, panes = 2, s = 0.9, e = 1.95) => ({ a, b, s, e, panes });
wall('x', -5, 5, -5.9, GF, WH, T, [win(-4.4, -3.6, 1, 1.0), win(-1.7, -0.3), win(1.6, 2.4, 1, 1.4), win(3.6, 4.4, 1, 1.2)], mat.plaster, upperG, -1);
wall('z', -5.8, 5.8, 4.9, GF, WH, T, [win(0.0, 1.4), win(-2.4, -1.7, 1, 1.0), { a: 3.8, b: 5.3, s: 0.9, e: 1.95, type: 'open' }], mat.plaster, upperG, 1);
wall('z', -5.8, 5.8, -4.9, GF, WH, T, [win(-0.6, 1.0), { a: 3.8, b: 5.3, s: 0.9, e: 1.95, type: 'open' }], mat.plaster, upperG, -1);
// terrace side-opening sills
boxB(4.78, 5.06, GF + 0.86, GF + 0.9, 3.75, 5.35, mat.coping, upperG); boxB(-5.06, -4.78, GF + 0.86, GF + 0.9, 3.75, 5.35, mat.coping, upperG);
// facade wall between interior and terrace (sliding glass doors)
wall('x', -4.8, 4.8, 3.0, GF, WH, T, [{ a: -4.3, b: -0.9, s: 0, e: 2.05, panes: 3 }, { a: 1.7, b: 3.9, s: 0, e: 2.05, panes: 2 }], mat.plaster, upperG, 1, mat.steel);
// front parapet + railing
boxB(-4.8, 4.8, GF, GF + 0.5, 5.8, 6.0, mat.plaster, upperG);
boxB(-4.8, 4.8, GF + 0.5, GF + 0.55, 5.76, 6.04, mat.coping, upperG);
boxB(-4.8, 4.8, GF + 1.03, GF + 1.07, 5.87, 5.93, mat.steel, upperG);
for (let x = -4.7; x <= 4.71; x += 0.12) boxB(x - 0.009, x + 0.009, GF + 0.55, GF + 1.03, 5.89, 5.91, mat.steel, upperG);
// front steel beam + posts carrying roof over terrace
boxB(-4.8, 4.8, TOP - 0.2, TOP, 5.82, 5.98, mat.steel, upperG);
for (const x of [-1.65, 1.65]) boxB(x - 0.05, x + 0.05, GF + 0.5, TOP - 0.2, 5.85, 5.95, mat.steel, upperG);
// concrete tie-beam (hatıl) on wall tops
boxB(-5.0, 5.0, TOP - 0.02, TOP, -6.0, -5.8, mat.concrete, upperG); boxB(4.8, 5.0, TOP - 0.02, TOP, -6, 6, mat.concrete, upperG); boxB(-5.0, -4.8, TOP - 0.02, TOP, -6, 6, mat.concrete, upperG);

// gable triangles
function gable(xc) {
  const s = new THREE.Shape(); s.moveTo(-6, 0); s.lineTo(6, 0); s.lineTo(0, 6 * TAN); s.closePath();
  const g = new THREE.ExtrudeGeometry(s, { depth: T, bevelEnabled: false });
  const m = new THREE.Mesh(g, mat.plaster); m.rotation.y = -Math.PI / 2; m.position.set(xc + T / 2, TOP, 0);
  m.castShadow = m.receiveShadow = true; roofG.add(m);
}
gable(4.9); gable(-4.9);

// ---------- ROOF: steel profiles + trapezoidal sheet ----------
function slope(sign, len) {
  const g = new THREE.Group(); g.position.set(0, RIDGE, 0); g.rotation.x = sign * TH; roofG.add(g);
  const z = v => v * sign;
  const X0 = -5.45, X1 = 5.45;
  boxB(X0, X1, -0.008, -0.003, z(0), z(len), mat.roofUnder, g); boxB(X0, X1, -0.003, 0, z(0), z(len), mat.roof, g);
  for (let x = X0 + 0.12; x < X1; x += 0.25) boxB(x - 0.025, x + 0.025, 0, 0.032, z(0), z(len), mat.roof, g);
  for (let p = 0.15; p < len; p += 0.9) boxB(X0 + 0.05, X1 - 0.05, -0.07, -0.008, z(p - 0.03), z(p + 0.03), mat.galv, g);       // aşık (purlins)
  for (let x = -3.75; x <= 3.76; x += 1.25) boxB(x - 0.03, x + 0.03, -0.17, -0.07, z(0), z(len - 0.05), mat.steel, g);   // makas/rafters
  boxB(X0 - 0.04, X0, -0.08, 0.06, z(0), z(len), mat.roofEdge, g); boxB(X1, X1 + 0.04, -0.08, 0.06, z(0), z(len), mat.roofEdge, g); // rüzgarlık
  // gutter
  const gu = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.075, X1 - X0, 16, 1, false, 0, Math.PI), mat.galv);
  gu.rotation.z = Math.PI / 2; gu.rotation.x = 0; gu.position.set(0, -0.02, z(len + 0.05)); gu.castShadow = true; g.add(gu);
  gu.material = mat.galv; gu.material.side = THREE.DoubleSide;
}
slope(1, 6.8 / Math.cos(TH));
slope(-1, 6.6 / Math.cos(TH));
boxB(-5.5, 5.5, RIDGE - 0.02, RIDGE + 0.06, -0.2, 0.2, mat.roofEdge, roofG); // mahya

// ---------- interior partitions + furniture (for cut-away) ----------
const iw = (axis, a0, a1, c, ops = []) => wall(axis, a0, a1, c, GF, WH, 0.1, ops.map(([a, b]) => ({ a, b, s: 0, e: 2.05, type: 'open' })), mat.plasterIn, interiorG);
iw('z', -1.5, 3.0, 1.0);                         // living | bedroom1
iw('x', 1.0, 4.8, -1.5, [[1.3, 2.2]]);            // bedroom1 | corridor
iw('x', -3.0, 4.8, -2.6, [[-1.1, -0.2], [1.4, 2.2], [3.5, 4.3]]);
iw('z', -5.8, -1.5, -3.0);                        // stair | bedroom2
iw('z', -5.8, -2.6, 1.0); iw('z', -5.8, -2.6, 3.0);
// stairs (well) + slab
for (let i = 0; i < 16; i++) boxB(-4.75, -3.1, 0, GF - (i + 1) * 0.1875, -1.6 - i * 0.25 - 0.25, -1.6 - i * 0.25, mat.concrete, interiorG);
boxB(-4.75, -3.1, GF - 0.02, GF + 0.95, -1.56, -1.5, mat.steel, interiorG, false);
// living + kitchen
boxB(0.35, 0.95, GF, GF + 0.9, -1.4, 1.6, mat.white, interiorG); boxB(0.33, 0.95, GF + 0.9, GF + 0.94, -1.4, 1.6, mat.counter, interiorG);
boxB(0.3, 0.95, GF, GF + 2.0, -1.45, -0.8, mat.galv, interiorG);   // fridge
boxB(-1.9, -0.5, GF + 0.72, GF + 0.76, 1.0, 1.9, mat.lightwood, interiorG);
for (const [x, z] of [[-1.6, 0.75], [-0.8, 0.75], [-1.6, 2.15], [-0.8, 2.15]]) boxB(x - 0.2, x + 0.2, GF, GF + 0.45, z - 0.2, z + 0.2, mat.chair, interiorG);
boxB(-4.75, -4.0, GF, GF + 0.42, -0.6, 2.2, mat.sofa, interiorG); boxB(-4.75, -4.55, GF, GF + 0.8, -0.6, 2.2, mat.sofa, interiorG);
boxB(-3.6, -2.9, GF, GF + 0.4, 0.2, 1.4, mat.darkwood, interiorG);
// bedroom 1
boxB(3.0, 4.8, GF, GF + 0.5, 0.0, 1.6, mat.bed, interiorG); boxB(4.7, 4.8, GF, GF + 1.0, -0.05, 1.65, mat.darkwood, interiorG);
boxB(2.5, 4.7, GF, GF + 2.0, -1.45, -0.85, mat.lightwood, interiorG);
// bedroom 2
boxB(-2.6, -1.0, GF, GF + 0.5, -5.75, -3.75, mat.bed, interiorG); boxB(-2.65, -0.95, GF, GF + 1.0, -5.8, -5.7, mat.darkwood, interiorG);
boxB(0.3, 0.95, GF, GF + 2.0, -5.0, -3.0, mat.lightwood, interiorG);
// bath
boxB(1.1, 1.95, GF, GF + 0.06, -5.75, -4.85, mat.white, interiorG);
boxB(2.4, 2.9, GF, GF + 0.42, -3.6, -3.0, mat.white, interiorG);
boxB(2.45, 2.95, GF + 0.75, GF + 0.85, -5.6, -5.0, mat.white, interiorG);
// depo / laundry
boxB(3.1, 3.7, GF, GF + 0.85, -5.75, -5.15, mat.white, interiorG);
boxB(4.3, 4.75, GF, GF + 1.8, -5.75, -3.0, mat.lightwood, interiorG);

// ---------- terrace furniture ----------
boxB(-3.3, -1.3, GF + 0.72, GF + 0.77, 4.0, 4.9, mat.wood, upperG);
for (const x of [-3.2, -1.4]) for (const z of [4.05, 4.85]) boxB(x - 0.03, x + 0.03, GF, GF + 0.72, z - 0.03, z + 0.03, mat.steel, upperG);
for (const x of [-2.9, -2.3, -1.7]) for (const [z, d] of [[3.55, -1], [5.35, 1]]) {
  boxB(x - 0.22, x + 0.22, GF + 0.42, GF + 0.46, z - 0.22, z + 0.22, mat.chair, upperG);
  boxB(x - 0.22, x + 0.22, GF + 0.46, GF + 0.9, z + d * 0.2 - 0.02, z + d * 0.2 + 0.02, mat.chair, upperG);
  boxB(x - 0.2, x + 0.2, GF, GF + 0.42, z - 0.02, z + 0.02, mat.chair, upperG);
}
// lounge sofa
boxB(1.0, 3.6, GF, GF + 0.4, 4.1, 4.9, mat.lightwood, upperG); boxB(1.05, 3.55, GF + 0.4, GF + 0.52, 4.15, 4.85, mat.cushion, upperG);
boxB(1.0, 3.6, GF, GF + 0.8, 3.95, 4.15, mat.lightwood, upperG); boxB(1.2, 3.4, GF + 0.52, GF + 0.8, 4.15, 4.3, mat.cushion, upperG);
boxB(1.7, 2.9, GF, GF + 0.35, 5.15, 5.6, mat.lightwood, upperG);
// pots
function pot(x, z, s = 1) {
  const p = new THREE.Mesh(new THREE.CylinderGeometry(0.22 * s, 0.16 * s, 0.45 * s, 16), mat.pot); p.position.set(x, GF + 0.225 * s, z); p.castShadow = true; upperG.add(p);
  const l = new THREE.Mesh(new THREE.IcosahedronGeometry(0.38 * s, 1), mat.plant); l.position.set(x, GF + 0.75 * s, z); l.castShadow = true; upperG.add(l);
}
pot(-4.5, 3.4); pot(4.45, 3.4); pot(0.2, 5.5, 0.8); pot(-4.5, 5.55, 0.8); pot(4.45, 5.55, 0.8);

// ---------- terrain ----------
function terrainH(x, z) {
  const d = Math.hypot(x / 1.2, z);
  let h = (fbm(x * 0.012 + 5, z * 0.012) - 0.5) * 6 * ss(25, 140, d);
  h -= 48 * ss(18, 260, z);
  const ax = Math.abs(x);
  h += ss(650, 1900, ax + Math.max(0, -z) * 0.2) * (110 + 300 * ridged(x * 0.0013 + 2, z * 0.0013));
  h += ss(40, 900, -z) * (70 + 230 * ridged(x * 0.0017, z * 0.0017 + 7));
  h += ss(4800, 6800, z) * (500 + 1100 * ridged(x * 0.0007 + 11, z * 0.0007));
  return h;
}
const SEA = -26;
function terrainMesh(size, seg, cx, cz, holeR) {
  const g = new THREE.PlaneGeometry(size, size, seg, seg); g.rotateX(-Math.PI / 2);
  const pos = g.attributes.position, col = new Float32Array(pos.count * 3); const c = new THREE.Color();
  const grass = new THREE.Color(0x7d8b45), olive = new THREE.Color(0x5e6c34), dry = new THREE.Color(0x9a9055), rock = new THREE.Color(0x8c8577), sand = new THREE.Color(0xcbb994), forest = new THREE.Color(0x3f5229);
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i) + cx, z = pos.getZ(i) + cz; let h = terrainH(x, z);
    if (holeR && Math.abs(x) < holeR && Math.abs(z) < holeR) h -= 3;
    pos.setX(i, x); pos.setZ(i, z); pos.setY(i, h);
    const n = fbm(x * 0.02, z * 0.02, 3);
    if (h < SEA + 2.5) c.copy(sand);
    else if (h < 40) c.copy(grass).lerp(olive, n).lerp(dry, ss(0.55, 0.8, fbm(x * 0.005, z * 0.005, 3)) * 0.6);
    else if (h < 350) c.copy(olive).lerp(forest, ss(60, 250, h) * 0.8 * n + 0.2).lerp(rock, ss(0.6, 0.85, n) * 0.5);
    else c.copy(forest).lerp(rock, ss(350, 700, h));
    col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b;
  }
  g.setAttribute('color', new THREE.BufferAttribute(col, 3)); g.computeVertexNormals();
  const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1 })); m.receiveShadow = true; scene.add(m); return m;
}
terrainMesh(760, 380, 0, 0, 0);
terrainMesh(26000, 650, 0, 4000, 370);
// sea
const sea = new THREE.Mesh(new THREE.PlaneGeometry(30000, 30000), new THREE.MeshStandardMaterial({ color: 0x0e4f78, roughness: 0.3, metalness: 0.0, envMapIntensity: 0.45, normalMap: seaNormal(), normalScale: new THREE.Vector2(0.3, 0.3) }));
sea.rotation.x = -Math.PI / 2; sea.position.set(0, SEA, 4000); scene.add(sea);

// road + garden walls
boxB(-380, 380, -0.25, 0.04, 9.6, 15.2, mat.asphalt, scene, false);
for (let x = -380; x < 380; x += 6) boxB(x, x + 3, 0.04, 0.045, 12.35, 12.45, mat.curb, scene, false);
const gw = M(0xb3a690);
boxB(-12, -1.6, 0, 0.8, 8.9, 9.2, gw); boxB(1.6, 12, 0, 0.8, 8.9, 9.2, gw);
boxB(-12, 12, 0, 1.0, -18.2, -17.9, gw); boxB(-12.2, -11.9, 0, 0.9, -18.2, 9.2, gw); boxB(11.9, 12.2, 0, 0.9, -18.2, 9.2, gw);
boxB(-1.6, 1.6, 0, 0.04, 7.0, 9.6, mat.concrete, scene, false);

// ---------- vegetation ----------
const trunkG = new THREE.CylinderGeometry(0.12, 0.2, 1.8, 6); trunkG.translate(0, 0.9, 0);
const blobG = new THREE.IcosahedronGeometry(1, 1);
const cypG = new THREE.ConeGeometry(0.7, 7, 8); cypG.translate(0, 3.8, 0);
const oliveTrees = [], cyps = [];
const tr = rng(42);
function okSpot(x, z) { if (Math.abs(x) < 45 && Math.abs(z) < 45) return false; if (z > 8.5 && z < 16.5 && Math.abs(x) < 380) return false; return terrainH(x, z) > SEA + 3; }
for (let k = 0; k < 4000 && oliveTrees.length < 900; k++) {
  const r = 14 + Math.pow(tr(), 1.6) * 360, a = tr() * 6.283; const x = Math.cos(a) * r * 1.3, z = Math.sin(a) * r;
  if (!okSpot(x, z)) continue; oliveTrees.push([x, terrainH(x, z), z, 0.8 + tr() * 0.7]);
}
for (let k = 0; k < 2000 && cyps.length < 120; k++) {
  const r = 16 + Math.pow(tr(), 1.4) * 300, a = tr() * 6.283; const x = Math.cos(a) * r * 1.3, z = Math.sin(a) * r;
  if (!okSpot(x, z)) continue; cyps.push([x, terrainH(x, z), z, 0.7 + tr() * 0.6]);
}
// garden trees by hand
oliveTrees.push([-9.5, 0, -9, 1.0], [9.5, 0, -10, 1.0], [-9.5, 0, 6, 0.8], [9.6, 0, 5.5, 0.75]);
cyps.push([-11, 0, -16.5, 0.9], [11, 0, -16.5, 0.9]);
function inst(geom, m, list, fn) {
  const im = new THREE.InstancedMesh(geom, m, list.length); const o = new THREE.Object3D();
  list.forEach((t, i) => { fn(o, t, i); o.updateMatrix(); im.setMatrixAt(i, o.matrix); });
  im.castShadow = true; im.receiveShadow = true; scene.add(im); return im;
}
const oliveM = M(0x66734a, { flatShading: true }), olive2 = M(0x58693d, { flatShading: true });
inst(trunkG, M(0x5b4a3a), oliveTrees, (o, [x, y, z, s]) => { o.position.set(x, y, z); o.scale.set(s, s, s); o.rotation.set(0, 0, 0); });
inst(blobG, oliveM, oliveTrees, (o, [x, y, z, s], i) => { o.position.set(x, y + 2.3 * s, z); o.scale.set(1.8 * s, 1.2 * s, 1.7 * s); o.rotation.set(0, i, 0); });
inst(blobG, olive2, oliveTrees, (o, [x, y, z, s], i) => { o.position.set(x + 0.7 * s, y + 2.9 * s, z - 0.4 * s); o.scale.set(1.2 * s, 0.9 * s, 1.2 * s); o.rotation.set(0, i * 2, 0); });
inst(cypG, M(0x2f4224, { flatShading: true }), cyps, (o, [x, y, z, s]) => { o.position.set(x, y, z); o.scale.set(s, s * (1 + (x * 13 % 1) * 0.3), s); o.rotation.set(0, 0, 0); });

// neighbour houses
function simpleHouse(x, z, w, d, h, rot, wallC, roofC) {
  const g = new THREE.Group(); const y = terrainH(x, z); g.position.set(x, y - 0.3, z); g.rotation.y = rot; scene.add(g);
  boxB(-w / 2, w / 2, 0, h + 0.3, -d / 2, d / 2, M(wallC, { map: plasterTex }), g);
  const s = new THREE.Shape(); s.moveTo(-d / 2 - 0.4, 0); s.lineTo(d / 2 + 0.4, 0); s.lineTo(0, d * 0.28); s.closePath();
  const rg = new THREE.ExtrudeGeometry(s, { depth: w + 0.6, bevelEnabled: false }); const rm = new THREE.Mesh(rg, M(roofC, { roughness: 0.7 }));
  rm.rotation.y = Math.PI / 2; rm.position.set(-w / 2 - 0.3, h + 0.3, 0); rm.castShadow = rm.receiveShadow = true; g.add(rm);
  for (let i = 0; i < Math.floor(w / 2.5); i++) boxB(-w / 2 + 1.2 + i * 2.5, -w / 2 + 2.2 + i * 2.5, h * 0.35, h * 0.35 + 1.2, d / 2, d / 2 + 0.02, mat.glass, g);
}
simpleHouse(-38, -8, 9, 8, 3.0, 0.15, 0xe9dcc4, 0xa04a32);
simpleHouse(34, -22, 8, 7, 5.6, -0.2, 0xf1ece2, 0x8f3f2c);
simpleHouse(52, 26, 10, 8, 3.0, 0.3, 0xe3d2b4, 0xa5523a);
simpleHouse(-60, 34, 8, 8, 3.0, -0.4, 0xf3eee4, 0x99452f);
simpleHouse(-25, -48, 9, 7, 5.6, 0.1, 0xeae0cc, 0x9a3f2b);
simpleHouse(70, -40, 8, 8, 3.0, 0.5, 0xe6dccb, 0x7e3a2a);
simpleHouse(-90, -20, 10, 8, 3.0, 0.2, 0xefe4d0, 0xa14e36);
simpleHouse(110, 10, 9, 8, 3.0, -0.3, 0xf0e8da, 0x9b4a33);

// ---------- views ----------
const views = {
  front:   { cam: [11, 4.2, 27], look: [0, 3.6, 0], sun: [-0.55, 0.62, 0.75], fov: 42, t: 'ÖN CEPHE — Yol tarafı (Güney)', s: 'Kapalı teras, cam sürgü kapılar, profil+trapez sac çatı (%27 / 15°)' },
  back:    { cam: [-10, 5.5, -27], look: [0, 3.4, 0], sun: [0.45, 0.6, -0.7], fov: 42, t: 'ARKA CEPHE — Bahçe tarafı (Kuzey)', s: 'Arkada deniz ve dağ manzarası' },
  right:   { cam: [27, 4.5, 6], look: [0, 3.4, 0.5], sun: [0.75, 0.55, 0.45], fov: 42, t: 'SAĞ YAN CEPHE (Doğu)', s: 'Üçgen alın duvarı, 2,20 m duvar + çatı eğimi' },
  left:    { cam: [-27, 4.5, 4], look: [0, 3.4, 0.5], sun: [-0.75, 0.55, 0.4], fov: 42, t: 'SOL YAN CEPHE (Batı)', s: 'Mevcut 1 m genişliğindeki giriş bölümü görünüyor' },
  aerial:  { cam: [-16, 21, -30], look: [3, -2, 22], sun: [-0.3, 0.65, 0.7], fov: 50, t: 'KUŞ BAKIŞI — Deniz yönüne', s: 'Ev arkadan; teras denize ve karşı dağlara bakıyor' },
  terrace: { cam: [-1.2, GF + 1.5, 3.3], look: [3, GF + 1.75, 60], sun: [-0.5, 0.55, 0.7], fov: 62, t: 'TERASTAN MANZARA', s: 'Deniz ve dağ manzarası — oturunca da görünsün diye alçak duvar + korkuluk' },
  cutaway: { cam: [9, 19, 15], look: [0, 2.6, 0], sun: [-0.35, 0.85, 0.4], fov: 42, t: 'ÇATI KATI — 3B PLAN (çatı kaldırılmış)', s: '' },
};
const V = views[VIEW];
if (VIEW === 'cutaway') { roofG.visible = false; }
else interiorG.visible = VIEW === 'terrace';

const sunDir = new THREE.Vector3(...V.sun).normalize();
const sky = new Sky(); sky.scale.setScalar(150000); scene.add(sky);
const setSky = s => { const u = s.material.uniforms; u.turbidity.value = 2.5; u.rayleigh.value = 2.0; u.mieCoefficient.value = 0.004; u.mieDirectionalG.value = 0.8; u.sunPosition.value.copy(sunDir); };
setSky(sky);
const pmrem = new THREE.PMREMGenerator(renderer);
const envScene = new THREE.Scene(); const sky2 = new Sky(); sky2.scale.setScalar(1000); setSky(sky2); envScene.add(sky2);
scene.environment = pmrem.fromScene(envScene, 0.02, 0.1, 5000).texture;
scene.fog = new THREE.Fog(0xb4c8dc, 900, 12000);

const sun = new THREE.DirectionalLight(0xfff1dc, 3.2);
sun.position.copy(sunDir).multiplyScalar(90); sun.target.position.set(0, 2, 0); scene.add(sun.target); scene.add(sun);
sun.castShadow = true; sun.shadow.mapSize.set(4096, 4096);
const sc = sun.shadow.camera; sc.left = -32; sc.right = 32; sc.top = 32; sc.bottom = -32; sc.near = 10; sc.far = 200; sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.02;
scene.add(new THREE.HemisphereLight(0xcfe3ff, 0x6a6448, 0.5));

scene.traverse(o => { if (o.material && o.material.isMeshStandardMaterial && o !== sea) o.material.envMapIntensity = o.material.metalness > 0.5 ? 0.9 : 0.35; });
const camera = new THREE.PerspectiveCamera(V.fov, W / H, 0.2, 300000);
camera.position.set(...V.cam); camera.lookAt(...V.look);
renderer.render(scene, camera);

document.getElementById('cap').innerHTML = V.t + (V.s ? `<small>${V.s}</small>` : '');
if (VIEW === 'cutaway') {
  const L = [
    ['Salon + Mutfak', '≈ 25,3 m²', -2.0, 0.6], ['Yatak Odası 1', '≈ 16,3 m²', 2.6, 0.7], ['Yatak Odası 2', '≈ 12,3 m²', -1.2, -4.4],
    ['Banyo / WC', '≈ 6 m²', 2.0, -4.4], ['Depo / Çamaşır', '≈ 5,5 m²', 4.0, -4.6], ['Merdiven', '', -3.9, -3.6], ['Koridor', '≈ 8 m²', 0.0, -2.05], ['TERAS', '≈ 26 m²', 0, 4.3],
  ];
  for (const [n, a, x, z] of L) {
    const v = new THREE.Vector3(x, GF + 2.4, z).project(camera);
    const d = document.createElement('div'); d.className = 'lbl'; d.innerHTML = n + (a ? `<span>${a}</span>` : '');
    d.style.left = ((v.x + 1) / 2 * W) + 'px'; d.style.top = ((1 - v.y) / 2 * H) + 'px'; document.getElementById('labels').appendChild(d);
  }
}
window.__done = true;
