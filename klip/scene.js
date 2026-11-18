// Samu — Cennetten Bi Parça · PS2-style procedural music video
import * as THREE from 'three';

const W = 640, H = 360;
THREE.ColorManagement.enabled = false;

// ---------- utils ----------
function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const R = rng(1997);
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, k) => a + (b - a) * k;
const smooth = (a, b, x) => { const k = clamp((x - a) / (b - a)); return k * k * (3 - 2 * k); };
const V = (x, y, z) => new THREE.Vector3(x, y, z);
const col = (h) => new THREE.Color(h);

let BEATS = [];
function beatPulse(t, k = 7) { let b = -10; for (const x of BEATS) { if (x <= t) b = x; else break; } return Math.exp(-(t - b) * k); }
function beatIndex(t) { let i = 0; for (const x of BEATS) { if (x <= t) i++; else break; } return i; }

function ps2(m) {
  return m; // vertex snapping disabled: it made the road and buildings wobble
  m.onBeforeCompile = (sh) => {
    sh.vertexShader = sh.vertexShader.replace('#include <project_vertex>',
      '#include <project_vertex>\n{ vec4 p = gl_Position; vec2 g = vec2(200.0,112.0); p.xy = floor(p.xy / p.w * g + 0.5) / g * p.w; gl_Position = p; }');
  };
  return m;
}
const matCache = {};
function lam(c, o = {}) {
  const key = c + JSON.stringify(o);
  if (!o.unique && matCache[key]) return matCache[key];
  const m = ps2(new THREE.MeshLambertMaterial({ color: col(c), flatShading: true, ...Object.fromEntries(Object.entries(o).filter(([k]) => k !== 'unique')) }));
  matCache[key] = m; return m;
}
function basic(c, o = {}) { return new THREE.MeshBasicMaterial({ color: col(c), ...o }); }
function ctex(w, h, draw, nearest = true) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c);
  if (nearest) { t.magFilter = THREE.NearestFilter; t.minFilter = THREE.LinearMipmapLinearFilter; t.generateMipmaps = true; t.anisotropy = 8; }
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  return t;
}
function mesh(geo, mat, x = 0, y = 0, z = 0, parent) { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); if (parent) parent.add(m); return m; }
const box = (w, h, d) => new THREE.BoxGeometry(w, h, d);
const cyl = (rt, rb, h, n = 7) => new THREE.CylinderGeometry(rt, rb, h, n);

// ---------- renderer ----------
const canvas = document.getElementById('c');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, preserveDrawingBuffer: true });
renderer.setPixelRatio(1); renderer.setSize(W, H, false);
renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
const rt = new THREE.WebGLRenderTarget(W, H, { generateMipmaps: true, minFilter: THREE.LinearMipmapLinearFilter, magFilter: THREE.LinearFilter });
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(50, W / H, 0.05, 210);
scene.fog = new THREE.Fog(0x4a525c, 3, 55);

// sky
const skyU = { top: { value: col('#0b0f1a') }, hor: { value: col('#39424f') }, bot: { value: col('#1a1e26') } };
const sky = new THREE.Mesh(new THREE.SphereGeometry(150, 24, 16), new THREE.ShaderMaterial({
  side: THREE.BackSide, depthWrite: false, depthTest: false, fog: false, uniforms: skyU,
  vertexShader: 'varying vec3 vD; void main(){ vD = normalize(position); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }',
  fragmentShader: 'uniform vec3 top,hor,bot; varying vec3 vD; void main(){ float y=vD.y; vec3 c = y>0.0 ? mix(hor,top,pow(clamp(y*1.6,0.0,1.0),0.7)) : mix(hor,bot,pow(clamp(-y*2.0,0.0,1.0),0.6)); gl_FragColor=vec4(c,1.0);} '
}));
sky.renderOrder = -10; scene.add(sky);

// lights
const hemi = new THREE.HemisphereLight(0x8090b0, 0x202025, 1.6); scene.add(hemi);
const moon = new THREE.DirectionalLight(0xa8b8d8, 1.4); moon.position.set(-20, 30, 10); scene.add(moon);
const heroLight = new THREE.PointLight(0xffc888, 0, 16, 1); scene.add(heroLight);
const fillLight = new THREE.PointLight(0xff9fc8, 0, 10, 1); scene.add(fillLight);

// ---------- textures ----------
const glowTex = ctex(64, 64, (g) => { const r = g.createRadialGradient(32, 32, 0, 32, 32, 32); r.addColorStop(0, 'rgba(255,255,255,1)'); r.addColorStop(0.25, 'rgba(255,255,255,0.55)'); r.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = r; g.fillRect(0, 0, 64, 64); }, false);
const streakTex = ctex(16, 64, (g) => { const r = g.createLinearGradient(0, 0, 0, 64); r.addColorStop(0, 'rgba(255,255,255,0)'); r.addColorStop(0.5, 'rgba(255,255,255,1)'); r.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = r; g.fillRect(0, 0, 16, 64); const s = g.createLinearGradient(0, 0, 16, 0); g.globalCompositeOperation = 'destination-in'; s.addColorStop(0, 'rgba(0,0,0,0)'); s.addColorStop(0.5, 'rgba(0,0,0,1)'); s.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = s; g.fillRect(0, 0, 16, 64); }, false);
const cloudTex = ctex(128, 128, (g) => {
  const r2 = rng(7);
  for (let i = 0; i < 22; i++) {
    const x = 30 + r2() * 68, y = 44 + r2() * 44, rad = 14 + r2() * 26;
    const r = g.createRadialGradient(x, y, 0, x, y, rad); r.addColorStop(0, 'rgba(255,255,255,0.55)'); r.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = r; g.fillRect(0, 0, 128, 128);
  }
}, false);
const roadTex = ctex(64, 128, (g, w, h) => {
  const r2 = rng(3); g.fillStyle = '#26282c'; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 900; i++) { const v = 30 + r2() * 25; g.fillStyle = `rgb(${v},${v},${v + 3})`; g.fillRect(r2() * w | 0, r2() * h | 0, 1, 1); }
  g.fillStyle = '#b8b6a8'; g.fillRect(31, 0, 2, 56);
  g.fillStyle = '#8f8d82'; g.fillRect(2, 0, 1, h); g.fillRect(61, 0, 1, h);
  for (let i = 0; i < 6; i++) { g.fillStyle = 'rgba(10,12,16,0.5)'; g.beginPath(); g.ellipse(r2() * w, r2() * h, 4 + r2() * 8, 3 + r2() * 10, 0, 0, 7); g.fill(); }
});
const facadeTex = [], facadeEm = [];
for (let v = 0; v < 4; v++) {
  const r2 = rng(100 + v);
  const base = ['#3a3d45', '#463f3a', '#34383a', '#4a4650'][v];
  const lit = [];
  for (let i = 0; i < 16; i++) lit.push(r2() < 0.33 ? (r2() < 0.7 ? '#ffcf8a' : '#cfe0ff') : null);
  facadeTex.push(ctex(64, 64, (g) => { g.fillStyle = base; g.fillRect(0, 0, 64, 64); for (let i = 0; i < 16; i++) { const x = (i % 4) * 16 + 4, y = (i >> 2) * 16 + 3; g.fillStyle = lit[i] || '#15171c'; g.fillRect(x, y, 8, 10); g.fillStyle = 'rgba(0,0,0,0.25)'; g.fillRect(x, y + 5, 8, 1); } }));
  facadeEm.push(ctex(64, 64, (g) => { g.fillStyle = '#000'; g.fillRect(0, 0, 64, 64); for (let i = 0; i < 16; i++) { if (!lit[i]) continue; const x = (i % 4) * 16 + 4, y = (i >> 2) * 16 + 3; g.fillStyle = lit[i]; g.fillRect(x, y, 8, 10); } }));
}
const dropsTex = ctex(128, 128, (g) => {
  const r2 = rng(11);
  for (let i = 0; i < 45; i++) { const x = r2() * 128, y = r2() * 128, s = 0.6 + r2() * 1.6; g.fillStyle = 'rgba(200,215,235,0.35)'; g.beginPath(); g.ellipse(x, y, s, s * 1.3, 0, 0, 7); g.fill(); g.fillStyle = 'rgba(255,255,255,0.7)'; g.fillRect(x - s * 0.4 | 0, y - s * 0.5 | 0, 1, 1); if (r2() < 0.3) { g.fillStyle = 'rgba(200,215,235,0.2)'; g.fillRect(x - 0.5, y, 1, 6 + r2() * 14); } }
});

// ---------- faces ----------
function faceTex(kind, smile) {
  return ctex(256, 128, (g) => {
    const r2 = rng(kind === 'samu' ? 5 : 9);
    const girl = kind === 'girl';
    const skin = girl ? '#eec4a6' : '#d8a284';
    g.fillStyle = skin; g.fillRect(0, 0, 256, 128);
    // soft shading toward the back
    const sh = g.createLinearGradient(0, 0, 256, 0);
    sh.addColorStop(0, 'rgba(120,60,40,0.10)'); sh.addColorStop(0.25, 'rgba(0,0,0,0)'); sh.addColorStop(0.5, 'rgba(120,60,40,0.12)'); sh.addColorStop(0.75, 'rgba(90,40,30,0.18)'); sh.addColorStop(1, 'rgba(120,60,40,0.10)');
    g.fillStyle = sh; g.fillRect(0, 0, 256, 128);
    const fx = 64;
    if (girl) { for (const s of [-1, 1]) { const r = g.createRadialGradient(fx + s * 17, 73, 0, fx + s * 17, 73, 9); r.addColorStop(0, 'rgba(235,120,130,0.45)'); r.addColorStop(1, 'rgba(235,120,130,0)'); g.fillStyle = r; g.fillRect(0, 0, 256, 128); } }
    // eyes
    for (const s of [-1, 1]) {
      const ex = fx + s * 13, ey = 61;
      g.fillStyle = '#f2ece6'; g.beginPath(); g.ellipse(ex, ey, 5, smile ? 2 : 2.6, 0, 0, 7); g.fill();
      g.fillStyle = girl ? '#3b2416' : '#3a2a16'; g.beginPath(); g.arc(ex + 0.5, ey, 2.2, 0, 7); g.fill();
      g.fillStyle = '#0b0705'; g.fillRect(ex, ey - 1, 2, 2);
      g.fillStyle = '#fff'; g.fillRect(ex + 1, ey - 1, 1, 1);
      g.fillStyle = '#1a120d'; g.fillRect(ex - 5, ey - 3, 10, girl ? 2 : 1);
      if (girl) { g.fillRect(ex + s * 4, ey - 4, 2 * s, 1); g.fillRect(ex + s * 5, ey - 5, s, 1); }
      if (smile) { g.fillStyle = 'rgba(120,60,40,0.35)'; g.fillRect(ex + s * 5 - (s < 0 ? 3 : 0), ey + 1, 3, 1); g.fillRect(ex + s * 6 - (s < 0 ? 2 : 0), ey + 3, 2, 1); }
      // brows
      g.fillStyle = girl ? '#3a2a20' : '#17110d';
      for (let i = 0; i < 14; i++) { const bx = ex - 6 + i; const by = 53 - Math.sin(i / 13 * Math.PI) * 1.6 + (s * (i - 7) > 0 ? 0.6 : 0); g.fillRect(bx, by, 1, girl ? 1 : 3); }
    }
    // nose
    g.fillStyle = 'rgba(120,60,40,0.25)'; g.fillRect(fx - 1, 62, 2, 11); g.fillStyle = 'rgba(70,30,20,0.55)'; g.fillRect(fx - 4, 74, 2, 1); g.fillRect(fx + 2, 74, 2, 1);
    // beard (samu)
    if (!girl) {
      for (let y = 56; y < 124; y++) for (let x = fx - 54; x <= fx + 54; x++) {
        const dx = Math.abs(x - fx);
        const top = dx < 9 ? 79 : dx < 24 ? 76 : dx < 40 ? 70 : 58;
        if (y < top) continue;
        if (dx < 7 && y > 82 && y < 88) continue;
        const d = (y < top + 3 ? 0.45 : 0.82);
        if (r2() < d) { const v = r2(); g.fillStyle = v < 0.5 ? '#2a1e16' : v < 0.85 ? '#3b2b20' : '#59402e'; g.fillRect(x, y, 1, 1); }
      }
      g.fillStyle = '#21170f'; g.fillRect(fx - 9, 79, 18, 3);
    }
    // mouth
    g.fillStyle = girl ? '#c25a6c' : '#9a5848';
    if (smile) { g.fillRect(fx - 7, 85, 14, 2); g.fillRect(fx - 9, 84, 2, 1); g.fillRect(fx + 7, 84, 2, 1); g.fillRect(fx - 10, 83, 1, 1); g.fillRect(fx + 9, 83, 1, 1); g.fillStyle = '#f4ece4'; g.fillRect(fx - 5, 85, 10, 1); }
    else { g.fillRect(fx - 6, 85, 12, 2); }
    if (girl) { g.fillStyle = '#d97585'; g.fillRect(fx - 5, 87, 10, 2); }
    // hair
    const hc = girl ? '#2e2119' : '#14110e';
    g.fillStyle = hc;
    for (let x = 0; x < 256; x++) {
      const dx = Math.min(Math.abs(x - fx), 256 - Math.abs(x - fx));
      let hy;
      if (girl) hy = dx < 30 ? 33 + (dx < 3 ? -4 : 0) : dx < 44 ? 40 : 128;
      else hy = dx < 14 ? 31 : dx < 30 ? 28 + (dx - 14) * 0.15 : dx < 44 ? 46 : 64 + Math.min(1, (dx - 44) / 30) * 26;
      g.fillRect(x, 0, 1, hy);
      if (!girl && dx >= 40) { for (let y = hy; y < hy + 10; y++) if (r2() < 0.6 - (y - hy) * 0.06) { g.fillStyle = '#2b2622'; g.fillRect(x, y, 1, 1); g.fillStyle = hc; } }
    }
  });
}

// ---------- humans ----------
function makeHuman(kind) {
  const girl = kind === 'girl';
  const root = new THREE.Group();
  const body = new THREE.Group(); root.add(body);
  const s = girl ? 0.9 : 1.0; const lw = girl ? 0.82 : 1.0; body.scale.setScalar(s);
  const C = girl
    ? { top: '#ddd3c4', sleeve: '#ddd3c4', pants: '#1e1d22', shoe: '#e4e2dc', skin: '#e8bfa2', hair: '#2a1d16' }
    : { top: '#3f4b2b', sleeve: '#3f4b2b', pants: '#202329', shoe: '#18181a', skin: '#d8a284', hair: '#14110e' };
  const hips = new THREE.Group(); hips.position.y = 0.93; body.add(hips);
  const legs = [];
  for (const sd of [-1, 1]) {
    const th = new THREE.Group(); th.position.set(sd * 0.1, 0, 0); hips.add(th);
    mesh(cyl(0.085 * lw, 0.064 * lw, 0.46), lam(C.pants), 0, -0.23, 0, th);
    const kn = new THREE.Group(); kn.position.y = -0.46; th.add(kn);
    mesh(cyl(0.062 * lw, 0.046 * lw, 0.43), lam(C.pants), 0, -0.215, 0, kn); mesh(new THREE.SphereGeometry(0.064 * lw, 6, 4), lam(C.pants), 0, 0, 0, kn);
    mesh(box(0.11 * lw, 0.07, 0.25), lam(C.shoe), 0, -0.45, 0.05, kn);
    legs.push({ th, kn });
  }
  const chest = new THREE.Group(); hips.add(chest);
  const tw = girl ? 0.31 : 0.42;
  { const tor = mesh(new THREE.CylinderGeometry(tw / 2, tw / 2 * (girl ? 0.72 : 0.86), 0.6, 8), lam(C.top), 0, 0.3, 0, chest); tor.scale.z = (girl ? 0.19 : 0.23) / tw; const sh = mesh(new THREE.SphereGeometry(tw / 2, 8, 4, 0, Math.PI * 2, 0, Math.PI / 2), lam(C.top), 0, 0.58, 0, chest); sh.scale.set(1, 0.32, (girl ? 0.19 : 0.23) / tw); }
  mesh(box(tw * 0.85, 0.16, 0.2), lam(C.pants), 0, 0.02, 0, chest);
  if (girl) {
    const coat = mesh(new THREE.CylinderGeometry(0.17, 0.25, 0.6, 8, 1, true), lam(C.top, { side: THREE.DoubleSide }), 0, -0.22, 0, chest);
    coat.scale.z = 0.75;
    mesh(box(0.2, 0.05, 0.05), lam('#c9b79c'), 0, 0.08, 0.1, chest); // belt
  } else {
    mesh(box(0.2, 0.06, 0.03), lam('#c48f72'), 0, 0.57, 0.105, chest); // open collar skin
    for (let i = 0; i < 3; i++) mesh(box(0.02, 0.02, 0.01), lam('#d6d0c0'), 0.0, 0.47 - i * 0.12, 0.118, chest);
  }
  mesh(new THREE.CylinderGeometry(0.05, 0.055, 0.12, 6), lam(C.skin), 0, 0.63, 0, chest);
  const head = new THREE.Group(); head.position.y = 0.76; chest.add(head);
  const hr = girl ? 0.108 : 0.116;
  const fN = new THREE.MeshLambertMaterial({ map: faceTex(kind, false) }), fS = new THREE.MeshLambertMaterial({ map: faceTex(kind, true) });
  ps2(fN); ps2(fS);
  const skull = mesh(new THREE.SphereGeometry(hr, 14, 10), fN, 0, 0, 0, head);
  skull.scale.set(0.88, 1.13, 1.0);
  const nose = mesh(box(girl ? 0.02 : 0.026, girl ? 0.042 : 0.055, girl ? 0.022 : 0.03), lam(C.skin), 0, -0.02, hr * 0.92, head);
  nose.rotation.x = -0.25;
  for (const sd of [-1, 1]) { const e = mesh(new THREE.SphereGeometry(0.028, 6, 4), lam(C.skin), sd * hr * 0.88, -0.005, -0.01, head); e.scale.set(0.45, 1.1, 0.8); }
  if (girl) {
    const cap = mesh(new THREE.SphereGeometry(hr * 1.09, 14, 8, 0, Math.PI * 2, 0, Math.PI * 0.5), lam(C.hair), 0, 0.012, -0.008, head); cap.scale.set(0.92, 1.13, 1.02);
    { const hb = mesh(new THREE.CylinderGeometry(0.118, 0.14, 0.5, 10, 1, true, Math.PI * 0.5, Math.PI), lam(C.hair, { side: THREE.DoubleSide }), 0, -0.2, -0.005, head); hb.scale.z = 0.9; } mesh(new THREE.SphereGeometry(0.1, 8, 6), lam(C.hair), 0, -0.02, -0.05, head).scale.set(1.0, 1.1, 0.8);
    for (const sd of [-1, 1]) { const st = mesh(box(0.05, 0.36, 0.07), lam(C.hair), sd * 0.1, -0.15, 0.02, head); st.rotation.z = sd * 0.06; }
  } else {
    const cap = mesh(new THREE.SphereGeometry(hr * 1.05, 14, 7, 0, Math.PI * 2, 0, Math.PI * 0.36), lam(C.hair), 0, 0.01, -0.01, head); cap.scale.set(0.9, 1.13, 1.0);
    const r3 = rng(31);
    for (let i = 0; i < 9; i++) { const tf = mesh(new THREE.IcosahedronGeometry(0.042, 0), lam(C.hair), (r3() - 0.5) * 0.11, 0.098 + r3() * 0.018 - Math.abs(i - 3) * 0.004, 0.06 - i * 0.017, head); tf.scale.set(1.1, 0.55, 1.0); tf.rotation.set(r3(), r3(), r3()); }
    const beard = mesh(new THREE.SphereGeometry(hr * 1.035, 14, 6, 0.15, Math.PI - 0.3, Math.PI * 0.69, Math.PI * 0.25), lam('#2c2119'), 0, 0, 0, head);
    beard.scale.set(0.9, 1.13, 1.02);
  }
  const arms = [];
  for (const sd of [-1, 1]) {
    const sh = new THREE.Group(); sh.position.set(sd * (tw / 2 + 0.05), 0.54, 0); chest.add(sh);
    mesh(cyl(0.056 * lw, 0.046 * lw, 0.32, 6), lam(C.sleeve), 0, -0.15, 0, sh); mesh(new THREE.SphereGeometry(0.058 * lw, 6, 4), lam(C.sleeve), 0, 0, 0, sh);
    const el = new THREE.Group(); el.position.y = -0.3; sh.add(el);
    mesh(cyl(0.046 * lw, 0.036 * lw, 0.28, 6), lam(C.sleeve), 0, -0.13, 0, el);
    mesh(box(0.06 * lw, 0.09, 0.08), lam(C.skin), 0, -0.3, 0, el);
    arms.push({ sh, el });
  }
  root.userData = { kind, body, hips, chest, head, skull, fN, fS, legs, arms, s };
  scene.add(root);
  return root;
}
// pose: legs[0]/arms[0] are the right side (-x), [1] left (+x)
function pose(h, p = {}) {
  const u = h.userData, w = p.walk || 0, ph = p.phase || 0;
  const sit = p.sit ? 1 : 0;
  u.hips.position.y = 0.93 + Math.abs(Math.sin(ph)) * 0.03 * w;
  u.legs.forEach((L, i) => {
    const sgn = i === 0 ? 1 : -1;
    const a = Math.sin(ph) * 0.5 * w * sgn;
    L.th.rotation.set(sit ? -1.45 : a, 0, sit ? (i === 0 ? 0.08 : -0.08) : 0);
    L.kn.rotation.x = sit ? 1.4 : Math.max(0, a) * 1.1 + 0.05 * w;
  });
  u.arms.forEach((A, i) => {
    const sgn = i === 0 ? -1 : 1;
    A.sh.rotation.set(Math.sin(ph) * 0.45 * w * sgn * -1 * -1, 0, (i === 0 ? -0.06 : 0.06));
    A.el.rotation.x = -0.25 - 0.2 * w;
  });
  const set = (A, v) => { if (!v) return; A.sh.rotation.set(v[0], v[3] || 0, v[1]); A.el.rotation.x = v[2]; };
  set(u.arms[0], p.armR); set(u.arms[1], p.armL);
  u.chest.rotation.set(p.lean || 0, p.twist || 0, 0);
  u.head.rotation.set(p.pitch || 0, p.yaw || 0, p.roll || 0);
  u.skull.material = p.smile ? u.fS : u.fN;
}
function place(h, x, y, z, yaw) { h.position.set(x, y, z); h.rotation.set(0, yaw, 0); h.visible = true; }
const yawTo = (ax, az, bx, bz) => Math.atan2(bx - ax, bz - az);

// ---------- umbrella ----------
function makeUmbrella() {
  const g = new THREE.Group();
  const canopy = mesh(new THREE.SphereGeometry(0.62, 10, 4, 0, Math.PI * 2, 0, Math.PI * 0.34), new THREE.MeshLambertMaterial({ color: 0xdfe8f4, transparent: true, opacity: 0.45, side: THREE.DoubleSide, depthWrite: false }), 0, 0.88, 0, g);
  canopy.scale.y = 0.7;
  const rim = mesh(new THREE.TorusGeometry(0.545, 0.008, 3, 10), basic('#f5f8ff'), 0, 0.88 + 0.62 * Math.cos(Math.PI * 0.34) * 0.7, 0, g); rim.rotation.x = Math.PI / 2;
  mesh(new THREE.CylinderGeometry(0.008, 0.008, 1.32, 4), lam('#c8ccd4'), 0, 0.3, 0, g);
  mesh(new THREE.TorusGeometry(0.03, 0.008, 3, 6, Math.PI), lam('#3a2c22'), 0.03, -0.35, 0, g).rotation.z = Math.PI;
  scene.add(g); return g;
}

// ---------- car ----------
function makeCar() {
  const car = new THREE.Group();
  const paint = lam('#6a7888');
  mesh(box(1.76, 0.5, 4.1), paint, 0, 0.55, 0, car);
  mesh(box(1.74, 0.16, 1.3), paint, 0, 0.86, -1.35, car); // hood
  mesh(box(1.74, 0.16, 0.6), paint, 0, 0.86, 1.72, car); // trunk lip
  mesh(box(1.8, 0.14, 4.16), lam('#2a2e34'), 0, 0.32, 0, car); // bumper band
  // cabin frame
  const frame = lam('#3f4955');
  mesh(box(1.5, 0.06, 1.75), frame, 0, 1.44, 0.4, car);
  const pil = (x, z, rx) => { const m = mesh(box(0.07, 0.62, 0.08), frame, x, 1.15, z, car); m.rotation.x = rx; };
  for (const sd of [-1, 1]) { pil(sd * 0.75, -0.7, -0.75); pil(sd * 0.76, 0.35, 0); pil(sd * 0.75, 1.42, 0.55); }
  mesh(box(1.72, 0.04, 2.8), frame, 0, 0.87, 0.35, car); // belt line
  // glass
  const glassM = new THREE.MeshBasicMaterial({ color: 0x9fb4c8, transparent: true, opacity: 0.16, side: THREE.DoubleSide, depthWrite: false });
  const dropsM = new THREE.MeshBasicMaterial({ map: dropsTex, transparent: true, opacity: 0.9, side: THREE.DoubleSide, depthWrite: false });
  const glass = [];
  const pane = (w, h, x, y, z, rx, ry) => { const gg = new THREE.PlaneGeometry(w, h); const a = mesh(gg, glassM, x, y, z, car); a.rotation.set(rx, ry, 0, 'YXZ'); const b = mesh(gg, dropsM, x, y, z, car); b.rotation.copy(a.rotation); glass.push(b); };
  pane(1.46, 0.78, 0, 1.16, -0.68, -0.80, 0); // windshield
  pane(1.4, 0.68, 0, 1.17, 1.48, 0.62, 0); // rear
  for (const sd of [-1, 1]) pane(1.75, 0.54, sd * 0.78, 1.16, 0.4, 0, Math.PI / 2);
  // wheels
  const wheelG = new THREE.CylinderGeometry(0.33, 0.33, 0.24, 10); wheelG.rotateZ(Math.PI / 2);
  const wheels = [];
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) { const wm = mesh(wheelG, lam('#111214'), sx * 0.82, 0.33, sz * 1.35, car); wheels.push(wm); mesh(new THREE.CylinderGeometry(0.17, 0.17, 0.25, 8).rotateZ(Math.PI / 2), lam('#8a9096'), sx * 0.83, 0.33, sz * 1.35, car); }
  // lights
  const headM = basic('#fff6e0'), tailM = basic('#ff2a2a'), hazM = basic('#ff9a20');
  const heads = [], tails = [], haz = [];
  for (const sd of [-1, 1]) {
    mesh(box(0.38, 0.12, 0.04), headM, sd * 0.6, 0.68, -2.06, car);
    mesh(box(0.34, 0.12, 0.04), tailM, sd * 0.62, 0.7, 2.06, car);
    const hg = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: 0xfff0d0, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true })); hg.position.set(sd * 0.6, 0.68, -2.15); hg.scale.setScalar(1.4); car.add(hg); heads.push(hg);
    const tg = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: 0xff2020, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: 0.8 })); tg.position.set(sd * 0.62, 0.7, 2.15); tg.scale.setScalar(1.0); car.add(tg); tails.push(tg);
    for (const sz of [-1, 1]) {
      const hz = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: 0xffa020, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true })); hz.position.set(sd * 0.86, 0.72, sz * 2.0); hz.scale.setScalar(1.3); car.add(hz); haz.push(hz);
    }
  }
  // beams
  const beams = [];
  for (const sd of [-1, 1]) {
    const cg = new THREE.ConeGeometry(2.4, 16, 12, 1, true); cg.translate(0, -8, 0); cg.rotateX(-Math.PI / 2); cg.rotateX(Math.PI);
    const bm = mesh(cg, new THREE.MeshBasicMaterial({ color: 0xfff0c8, transparent: true, opacity: 0.05, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }), sd * 0.6, 0.68, -2.1, car);
    bm.rotation.x = -0.06; beams.push(bm);
  }
  // door (driver, -x)
  const door = new THREE.Group(); door.position.set(-0.9, 0, -0.55); car.add(door);
  mesh(box(0.06, 0.56, 1.12), paint, 0, 0.6, 0.56, door);
  mesh(box(0.03, 0.5, 1.05), lam('#2b2d31'), 0.04, 0.6, 0.56, door);
  // interior
  const inner = new THREE.Group(); car.add(inner);
  const trim = lam('#3a3c40'), roofIn = lam('#b8b3aa', { side: THREE.DoubleSide }), seatM = lam('#26272b');
  mesh(new THREE.PlaneGeometry(1.5, 1.75).rotateX(Math.PI / 2), roofIn, 0, 1.405, 0.4, inner);
  for (const sd of [-1, 1]) mesh(new THREE.PlaneGeometry(2.6, 0.62).rotateY(-sd * Math.PI / 2), lam('#3a3c40', { side: THREE.DoubleSide }), sd * 0.84, 0.58, 0.3, inner);
  mesh(box(1.6, 0.04, 2.6), lam('#1c1d20'), 0, 0.28, 0.3, inner);
  mesh(box(1.6, 0.3, 0.5), lam('#2a2b2f'), 0, 0.92, -0.85, inner); // dash
  mesh(box(0.25, 0.08, 0.04), basic('#5fd0ff'), 0, 0.99, -0.6, inner); // radio glow
  for (const sd of [-1, 1]) { mesh(box(0.5, 0.14, 0.5), seatM, sd * 0.38, 0.5, 0.3, inner); const bk = mesh(box(0.5, 0.65, 0.12), seatM, sd * 0.38, 0.85, 0.6, inner); bk.rotation.x = 0.15; mesh(box(0.26, 0.18, 0.1), seatM, sd * 0.38, 1.27, 0.66, inner); }
  mesh(box(1.5, 0.5, 0.4), seatM, 0, 0.62, 1.25, inner); // rear bench
  const wheel = mesh(new THREE.TorusGeometry(0.18, 0.025, 4, 12), lam('#151517'), -0.38, 1.0, -0.38, inner); wheel.rotation.x = -0.45;
  // wipers
  const wipers = [];
  for (const sd of [-1, 0.15]) { const p = new THREE.Group(); p.position.set(sd * 0.55, 0.9, -0.97); p.rotation.x = -0.8; car.add(p); const arm = mesh(box(0.62, 0.015, 0.015), lam('#0d0d0e'), 0.31, 0, 0.02, p); wipers.push(p); }
  // smoke
  const smoke = [];
  for (let i = 0; i < 14; i++) { const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: cloudTex, color: 0x9a9a9e, transparent: true, depthWrite: false, opacity: 0.0 })); car.add(sp); smoke.push(sp); }
  car.userData = { heads, tails, haz, beams, door, inner, glass, wipers, smoke, wheels };
  scene.add(car);
  return car;
}

// ---------- world ----------
const world = new THREE.Group(); scene.add(world);
const sinkGroup = new THREE.Group(); world.add(sinkGroup);
const roadLen = 1500, roadZ0 = 60;
const roadMat = ps2(new THREE.MeshPhongMaterial({ map: roadTex, shininess: 70, specular: 0x555a66 }));
roadTex.repeat.set(1, roadLen / 14);
const road = mesh(new THREE.PlaneGeometry(9, roadLen).rotateX(-Math.PI / 2), roadMat, 0, 0, roadZ0 - roadLen / 2, world);
const curbM = lam('#5b5e63'), walkM = lam('#46484d');
for (const sd of [-1, 1]) { mesh(box(3, 0.15, roadLen), walkM, sd * 6.0, 0.075, roadZ0 - roadLen / 2, sinkGroup); mesh(box(0.2, 0.17, roadLen), curbM, sd * 4.55, 0.085, roadZ0 - roadLen / 2, sinkGroup); }
mesh(new THREE.PlaneGeometry(400, roadLen).rotateX(-Math.PI / 2), lam('#191b1f'), 0, -0.02, roadZ0 - roadLen / 2, sinkGroup);
// buildings
{
  const r2 = rng(42);
  for (const sd of [-1, 1]) {
    let z = roadZ0;
    while (z > roadZ0 - roadLen) {
      const w = 7 + r2() * 7, h = 7 + r2() * 22, d = 10;
      const v = (r2() * 4) | 0;
      const geo = box(d, h, w);
      const uv = geo.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * w / 16, uv.getY(i) * h / 16);
      const m = ps2(new THREE.MeshLambertMaterial({ map: facadeTex[v], emissive: 0xffffff, emissiveMap: facadeEm[v], emissiveIntensity: 0.85 }));
      mesh(geo, m, sd * (7.6 + d / 2 + r2() * 1.5), h / 2, z - w / 2, sinkGroup);
      z -= w + 0.3 + r2() * 1.5;
    }
  }
}
// lamps
const lampGlowMat = new THREE.SpriteMaterial({ map: glowTex, color: 0xffd9a0, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true });
const coneMat = new THREE.MeshBasicMaterial({ color: 0xffd9a0, transparent: true, opacity: 0.045, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
const reflMat = new THREE.MeshBasicMaterial({ map: streakTex, color: 0xffc070, transparent: true, opacity: 0.45, blending: THREE.AdditiveBlending, depthWrite: false });
const lamps = [];
function makeLamp(x, z, sd, parent = world) {
  const g = new THREE.Group(); g.position.set(x, 0, z); parent.add(g);
  mesh(new THREE.CylinderGeometry(0.07, 0.1, 6.2, 6), lam('#2b2e33'), 0, 3.1, 0, g);
  mesh(box(1.3, 0.08, 0.08), lam('#2b2e33'), -sd * 0.62, 6.15, 0, g);
  mesh(box(0.42, 0.1, 0.22), basic('#fff0c8'), -sd * 1.2, 6.08, 0, g);
  const gl = new THREE.Sprite(lampGlowMat); gl.position.set(-sd * 1.2, 6.0, 0); gl.scale.setScalar(3.2); g.add(gl);
  const cn = new THREE.Mesh(new THREE.ConeGeometry(2.3, 6, 12, 1, true), coneMat); cn.position.set(-sd * 1.2, 3.0, 0); g.add(cn);
  const rf = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 6).rotateX(-Math.PI / 2), reflMat); rf.position.set(-sd * 1.2, 0.02, 2.6); g.add(rf);
  lamps.push({ g, gl, cn, rf }); return g;
}

// ---------- car path ----------
const LANE = 1.9;
const pathT = [], pathZ = [];
{
  const vel = (t) => t < 2.4 ? 0 : t < 5.4 ? 9 * smooth(2.4, 5.4, t) : t < 16.4 ? 9 : t < 18 ? lerp(9, 17, smooth(16.4, 18, t)) : t < 20.6 ? 17 : t < 23 ? 17 * (1 - smooth(20.6, 23, t)) : 0;
  let z = 2, dt = 1 / 240;
  for (let t = 0; t <= 30; t += dt) { pathT.push(t); pathZ.push(z); z -= vel(t) * dt; }
}
function carZ(t) { const i = clamp(Math.floor(t * 240), 0, pathZ.length - 1); return pathZ[i]; }
const ZS = carZ(24);
const PARK = { x: 2.75, z: ZS, yaw: -0.22, roll: 0.05 };
for (const sd of [-1, 1]) for (let z = roadZ0 - 10 - (sd > 0 ? 12 : 0); z > roadZ0 - roadLen; z -= 24) { if (sd < 0 && Math.abs(z - (ZS - 4.6)) < 9) continue; makeLamp(sd * 5.4, z, sd); }
const heroLamp = makeLamp(-5.4, ZS - 4.6, -1);
// no-parking sign
{ const g = new THREE.Group(); g.position.set(4.9, 0.15, ZS + 2.6); sinkGroup.add(g); mesh(new THREE.CylinderGeometry(0.03, 0.03, 2.2, 5), lam('#7a7d82'), 0, 1.1, 0, g); const st = ctex(32, 32, (gg) => { gg.fillStyle = '#1a4fd0'; gg.beginPath(); gg.arc(16, 16, 15, 0, 7); gg.fill(); gg.strokeStyle = '#e02020'; gg.lineWidth = 4; gg.beginPath(); gg.arc(16, 16, 13, 0, 7); gg.stroke(); gg.beginPath(); gg.moveTo(6, 6); gg.lineTo(26, 26); gg.stroke(); gg.beginPath(); gg.moveTo(26, 6); gg.lineTo(6, 26); gg.stroke(); }); const sg = mesh(new THREE.CircleGeometry(0.3, 10), new THREE.MeshLambertMaterial({ map: st, side: THREE.DoubleSide }), 0, 2.0, 0, g); sg.rotation.y = Math.PI / 2 + 0.6; }

// low ground mist
const mistMat = new THREE.SpriteMaterial({ map: cloudTex, color: 0x9aa2ac, transparent: true, depthWrite: false, opacity: 0.22 });
const mist = new THREE.Group(); sinkGroup.add(mist);
{ const r2 = rng(88); for (let i = 0; i < 230; i++) { const sp = new THREE.Sprite(mistMat); sp.position.set((r2() - 0.5) * 22, 0.4 + r2() * 1.4, 14 - r2() * 260); const s = 5 + r2() * 7; sp.scale.set(s, s * 0.35, 1); mist.add(sp); } }
// clouds
const cloudMats = ['#e8e6ea', '#e2d2da', '#cfcbdc', '#e6dccf'].map((c) => new THREE.SpriteMaterial({ map: cloudTex, color: col(c), transparent: true, depthWrite: false, opacity: 0 }));
const clouds = new THREE.Group(); scene.add(clouds);
{
  const r2 = rng(77);
  for (let i = 0; i < 260; i++) {
    const sp = new THREE.Sprite(cloudMats[(r2() * 4) | 0]);
    const z = ZS + 80 - r2() * 900;
    const band = r2();
    let x, y;
    if (band < 0.45) { x = (r2() - 0.5) * 90; y = -9 + r2() * 7; } else { const sd = r2() < 0.5 ? -1 : 1; x = sd * (8 + r2() * 50); y = -4 + r2() * 30; }
    sp.position.set(x, y, z); const s = 10 + r2() * 22; sp.scale.set(s, s * 0.6, 1); clouds.add(sp);
  }
}
// sparkles
const SPN = 260;
const spGeo = new THREE.BufferGeometry(); spGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(SPN * 3), 3));
const sparkles = new THREE.Points(spGeo, new THREE.PointsMaterial({ color: 0xfff2fa, size: 2, sizeAttenuation: false, transparent: true, opacity: 0.9, blending: THREE.AdditiveBlending, depthWrite: false }));
scene.add(sparkles);
const spSeed = []; { const r2 = rng(55); for (let i = 0; i < SPN; i++) spSeed.push([r2(), r2(), r2(), r2()]); }
function updateSparkles(t, c, rad, amt) {
  sparkles.visible = amt > 0.01; sparkles.material.opacity = amt;
  const a = spGeo.attributes.position.array;
  for (let i = 0; i < SPN; i++) { const s = spSeed[i]; const y = ((s[1] * 6 + t * (0.15 + s[3] * 0.3)) % 6); a[i * 3] = c.x + (s[0] - 0.5) * rad * 2 + Math.sin(t * 0.7 + i) * 0.2; a[i * 3 + 1] = c.y - 1 + y; a[i * 3 + 2] = c.z + (s[2] - 0.5) * rad * 2 + Math.cos(t * 0.6 + i) * 0.2; }
  spGeo.attributes.position.needsUpdate = true;
}
// rain
const RN = 2600;
const rainGeo = new THREE.BufferGeometry(); rainGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(RN * 6), 3));
const rain = new THREE.LineSegments(rainGeo, new THREE.LineBasicMaterial({ color: 0xc8d8f0, transparent: true, opacity: 0.38, depthWrite: false }));
rain.frustumCulled = false; scene.add(rain);
const rSeed = []; { const r2 = rng(66); for (let i = 0; i < RN; i++) rSeed.push([r2(), r2(), r2()]); }
let rainClock = 0, lastT = 0;
function updateRain(cam, amt, len) {
  rain.visible = amt > 0.01; rain.material.opacity = 0.38 * amt;
  const a = rainGeo.attributes.position.array, BX = 36, BY = 22, BZ = 36;
  for (let i = 0; i < RN; i++) {
    const s = rSeed[i];
    const x = cam.x + ((((s[0] * BX - cam.x) % BX) + BX) % BX) - BX / 2;
    const z = cam.z + ((((s[2] * BZ - cam.z) % BZ) + BZ) % BZ) - BZ / 2;
    const y = cam.y - BY / 2 + ((((s[1] * BY - rainClock * 14) % BY) + BY) % BY);
    a[i * 6] = x; a[i * 6 + 1] = y; a[i * 6 + 2] = z; a[i * 6 + 3] = x + 0.04; a[i * 6 + 4] = y + len; a[i * 6 + 5] = z;
  }
  rainGeo.attributes.position.needsUpdate = true;
}

// ---------- text ----------
function textMesh(lines, o) {
  const c = document.createElement('canvas'); c.width = o.cw || 1024; c.height = o.ch || 256;
  const g = c.getContext('2d'); g.textAlign = 'center'; g.textBaseline = 'middle';
  if (o.clipTop) { g.beginPath(); g.rect(0, 0, c.width, c.height * o.clipTop); g.clip(); }
  lines.forEach((ln, i) => {
    g.font = ln.font; if (ln.stroke) { g.lineJoin = 'round'; g.lineWidth = ln.stroke; g.strokeStyle = ln.strokeColor || '#000'; g.strokeText(ln.text, c.width / 2, ln.y * c.height); } const y = ln.y * c.height;
    if (ln.glow) { g.shadowColor = ln.glow; g.shadowBlur = ln.blur || 24; g.fillStyle = ln.color; g.fillText(ln.text, c.width / 2, y); g.fillText(ln.text, c.width / 2, y); }
    g.shadowBlur = 0; g.fillStyle = ln.color; g.fillText(ln.text, c.width / 2, y);
  });
  const t = new THREE.CanvasTexture(c); t.minFilter = THREE.LinearFilter; t.generateMipmaps = false;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(o.w, o.w * c.height / c.width), new THREE.MeshBasicMaterial({ map: t, transparent: true, depthWrite: o.depthWrite ?? false, fog: false, opacity: 0 }));
  return m;
}
const ov = new THREE.Scene();
const ovCam = new THREE.OrthographicCamera(-W / 2, W / 2, H / 2, -H / 2, 0, 10);
const ovs = {};

// ---------- post ----------
const postU = { tDiffuse: { value: rt.texture }, flash: { value: 0 }, ab: { value: 0 }, bloom: { value: 0.7 }, vig: { value: 0.9 }, sat: { value: 1 }, tint: { value: V(1, 1, 1) }, fade: { value: 1 }, flashCol: { value: V(1, 1, 1) }, grain: { value: 0.03 }, seed: { value: 0 } };
const post = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial({
  uniforms: postU, depthTest: false, depthWrite: false,
  vertexShader: 'varying vec2 vUv; void main(){ vUv=uv; gl_Position=vec4(position.xy,0.0,1.0);} ',
  fragmentShader: `uniform sampler2D tDiffuse; uniform float flash,ab,bloom,vig,sat,fade,grain,seed; uniform vec3 tint,flashCol; varying vec2 vUv;
  float bayer(vec2 p){ int x=int(mod(p.x,4.0)), y=int(mod(p.y,4.0)); int i=x+y*4; float m[16]=float[16](0.,8.,2.,10.,12.,4.,14.,6.,3.,11.,1.,9.,15.,7.,13.,5.); return m[i]/16.0; }
  float hash(vec2 p){ return fract(sin(dot(p,vec2(12.9898,78.233))+seed)*43758.5453); }
  void main(){
    vec2 uv=vUv; vec3 c;
    c.r = texture(tDiffuse, uv+vec2(ab,0.0)).r; c.g = texture(tDiffuse, uv).g; c.b = texture(tDiffuse, uv-vec2(ab,0.0)).b;
    vec3 b = textureLod(tDiffuse, uv, 2.5).rgb*0.35 + textureLod(tDiffuse, uv, 4.0).rgb*0.4 + textureLod(tDiffuse, uv, 5.5).rgb*0.25;
    b = max(b-0.32,0.0)*1.8; c += b*bloom;
    float l = dot(c, vec3(0.299,0.587,0.114)); c = mix(vec3(l), c, sat); c *= tint;
    vec2 d = uv-0.5; c *= 1.0 - vig*dot(d,d)*1.6;
    c += (hash(gl_FragCoord.xy)-0.5)*grain;
    c = mix(c, flashCol, flash);
    c = c*0.93 + vec3(0.035,0.033,0.03); c *= fade;
    c *= 0.95 + 0.05*sin(gl_FragCoord.y*3.14159);
    c += (bayer(gl_FragCoord.xy)-0.5)/28.0; c = floor(clamp(c,0.0,1.0)*31.0+0.5)/31.0;
    gl_FragColor = vec4(c,1.0);
  }`
}));
const postScene = new THREE.Scene(); postScene.add(post);
const postCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

// ---------- actors ----------
const samu = makeHuman('samu');
const girl = makeHuman('girl');
const umb = makeUmbrella();
const car = makeCar();
const TITLE_L = [{ text: 'cennetten bi parça', font: 'italic 600 170px Corm', color: '#fffaf6', stroke: 6, strokeColor: 'rgba(40,20,30,0.55)', glow: 'rgba(255,190,200,0.95)', blur: 34, y: 0.56 }];
const TITLE_O = { w: 6.2, cw: 1400, ch: 280 };
let titleBack = textMesh(TITLE_L, TITLE_O);
let titleFront = textMesh(TITLE_L, { ...TITLE_O, clipTop: 0.56 });
scene.add(titleBack, titleFront);

function overlay(id, lines, w, x, y, cw = 1024) {
  if (!ovs[id]) { const m = textMesh(lines, { w, cw, ch: 256 }); ov.add(m); ovs[id] = m; }
  const m = ovs[id]; m.position.set(x, y, 0); m.visible = true; return m;
}

// ---------- shot helpers ----------
const tmpA = V(0, 0, 0), tmpB = V(0, 0, 0);
function cam(p, l, fov = 50, roll = 0) { camera.position.copy(p); camera.up.set(Math.sin(roll), Math.cos(roll), 0); camera.lookAt(l); camera.fov = fov; camera.updateProjectionMatrix(); }
function rel(obj, lp) { obj.updateMatrixWorld(true); return obj.localToWorld(lp.clone()); }
function headPos(h, off = V(0, 0, 0)) { h.updateMatrixWorld(true); return h.userData.head.localToWorld(off.clone()); }
function shake(t, a) { return V(Math.sin(t * 37.1) * a + Math.sin(t * 13.3) * a, Math.sin(t * 29.7) * a, 0); }

function parkCar(x, z, yaw, roll = 0) { car.position.set(x, roll ? 0.06 : 0, z); car.rotation.set(0, yaw, roll); }
function seat(h, side) { car.add(h); h.position.set(side * 0.38, 0.6 - 0.93 * h.userData.s, 0.32); h.rotation.set(0, Math.PI, 0); h.visible = true; }
function unseat(h) { scene.add(h); }
function setDream(d) { DREAM = d; }
let DREAM = 0, SINK = 0;

const N = { top: col('#141820'), hor: col('#4a525c'), bot: col('#1c1f24'), fog: col('#4a525c') };
const D = { top: col('#2c2b44'), hor: col('#9c8c98'), bot: col('#b9a6ae'), fog: col('#8f8290') };

function reset() {
  DREAM = 0; SINK = 0;
  for (const h of [samu, girl]) { unseat(h); h.visible = false; pose(h, {}); }
  umb.visible = false; car.visible = true; car.userData.door.rotation.y = 0;
  parkCar(PARK.x, PARK.z, PARK.yaw, PARK.roll);
  titleBack.visible = titleFront.visible = false;
  for (const k in ovs) ovs[k].visible = false;
  Object.assign(FX, { rain: 1, rainSpeed: 1, rainLen: 0.55, flash: 0, ab: 0.0008, bloom: 0.7, sat: 0.9, tint: [0.97, 0.98, 1.02], vig: 0.9, fade: 1, flashCol: [1, 1, 1], spark: 0, sparkC: V(0, 0, 0), sparkR: 4, hazard: false, smoke: 0, heads: true, beams: 1, wiper: false, hero: 1, fill: 0, drops: 1, dropsOff: 0, lampPulse: 0 });
}
const FX = {};

// ---------- shots ----------
const shots = [];
const shot = (a, b, fn) => shots.push({ a, b, fn });

function driving(t) { car.position.set(LANE, 0, carZ(t)); car.rotation.set(0, 0, 0); }

// A — intro: title locked to the car, the car pulls away and the words stay in the fog
shot(0, 7.6, (t, lt) => {
  driving(t); seat(samu, -1); pose(samu, { sit: true, armR: [-1.1, 0.1, -0.5], armL: [-1.1, -0.1, -0.5], yaw: -0.15 });
  const sw = shake(t, 0.006);
  cam(V(LANE - 0.1, 1.08 + lt * 0.012, 8.6 - lt * 0.1).add(sw), V(LANE - 0.05, 1.0, -20), 44);
  titleBack.visible = titleFront.visible = true;
  titleBack.position.set(LANE, 1.0, 2.6); titleFront.position.copy(titleBack.position);
  const o = smooth(0.3, 1.5, lt) * (1 - smooth(6.6, 7.5, lt));
  titleBack.material.opacity = o; titleFront.material.opacity = o;
  FX.fade = smooth(0, 1.0, lt); FX.wiper = true; FX.vig = 1.1;
});
// B — interior profile (like the car photo)
shot(7.6, 12.5, (t, lt) => {
  driving(t); seat(samu, -1);
  pose(samu, { sit: true, armL: [-0.75, 1.15, -0.25], armR: [-1.1, 0.12, -0.55], yaw: -0.1 + 0.25 * smooth(1.5, 3.5, lt), pitch: 0.03 });
  const hp = headPos(samu);
  const p = rel(car, V(0.3, 1.3, -0.25 - lt * 0.02)); cam(p, hp.clone().add(V(-0.05, -0.04, 0)), 48);
  FX.tint = [0.85, 0.95, 1.1]; FX.fill = 0.7; fillLight.position.copy(rel(car, V(0.2, 1.3, -0.6)));
});
// C — windshield POV with wipers
shot(12.5, 16.4, (t, lt) => {
  driving(t); seat(samu, -1); pose(samu, { sit: true, armR: [-1.1, 0.12, -0.55], armL: [-1.1, -0.12, -0.55] });
  samu.visible = false;
  cam(rel(car, V(-0.38, 1.28, 0.42)), rel(car, V(-0.3, 1.0, -8)), 62);
  FX.wiper = true;
});
// D — accelerating
shot(16.4, 18.3, (t, lt) => {
  driving(t); seat(samu, -1); pose(samu, { sit: true, armR: [-1.2, 0.12, -0.5], armL: [-1.2, -0.12, -0.5], lean: 0.1 });
  const p = rel(car, V(-2.0, 0.45, 1.6)).add(shake(t, 0.03)); cam(p, rel(car, V(-0.4, 0.7, -3.5)), 70, 0.05);
  FX.rainLen = 1.1; FX.ab = 0.002;
});
shot(18.3, 19.9, (t, lt) => {
  driving(t); seat(samu, -1); pose(samu, { sit: true, armR: [-1.2, 0.12, -0.5], armL: [-1.2, -0.12, -0.5] });
  const z0 = carZ(18.3) - 34; cam(V(LANE - 1.6, 0.35, z0), V(LANE, 0.9, carZ(t)).add(V(0, 0, 0)), 58);
  FX.rainLen = 0.9;
});
// E — bad parking, hazards, stepping out
shot(19.9, 23.9, (t, lt) => {
  const k = smooth(20.4, 23.0, t);
  car.position.set(lerp(LANE, PARK.x, k), lerp(0, 0.06, smooth(22.2, 22.6, t)), Math.max(carZ(t), PARK.z));
  car.rotation.set(0, lerp(0, PARK.yaw, k) + Math.sin(k * Math.PI) * -0.12, lerp(0, PARK.roll, smooth(22.2, 22.6, t)));
  FX.hazard = t > 21.6;
  const door = smooth(22.5, 23.0, t); car.userData.door.rotation.y = -1.05 * door;
  if (t < 22.9) { seat(samu, -1); pose(samu, { sit: true, armR: [-1.1, 0.1, -0.5], armL: [-1.1, -0.1, -0.5] }); }
  else {
    const e = smooth(22.9, 23.7, t); unseat(samu);
    const lp = rel(car, V(lerp(-0.6, -1.55, e), 0, 0.15));
    place(samu, lp.x, 0, lp.z, car.rotation.y + Math.PI - lerp(0.4, 1.45, e));
    pose(samu, { walk: 0.4 * (1 - e), phase: t * 6, yaw: -0.3 * e });
  }
  const p = V(PARK.x + 6.5 - lt * 0.6, 7.2 - lt * 0.4, PARK.z + 13 - lt * 0.6);
  cam(p, V(PARK.x - 0.5, 0.6, PARK.z - 1), 44);
  FX.heads = t < 22.8;
});

// hero positions
const S0 = { x: 1.15, z: ZS + 0.05 };
const G0 = { x: -5.0, z: ZS - 4.0 };
const MID = { x: -1.95, z: ZS - 1.9 };
const dirSG = (() => { const dx = G0.x - S0.x, dz = G0.z - S0.z, l = Math.hypot(dx, dz); return { x: dx / l, z: dz / l }; })();
const SM = { x: MID.x - dirSG.x * 0.42, z: MID.z - dirSG.z * 0.42 };
const GM = { x: MID.x + dirSG.x * 0.42, z: MID.z + dirSG.z * 0.42 };
const yawSG = yawTo(S0.x, S0.z, G0.x, G0.z), yawGS = yawSG + Math.PI;
function girlUmbrella(h, tilt = 0) {
  h.updateMatrixWorld(true);
  const p = rel(h, V(-0.13, 1.03, 0.24)); umb.position.copy(p); umb.rotation.set(tilt, h.rotation.y, 0); umb.visible = true;
}
const umbArm = [-0.55, 0.25, -1.35];
function heroScene(t) {
  parkCar(PARK.x, PARK.z, PARK.yaw, PARK.roll); car.userData.door.rotation.y = -1.05; FX.hazard = true; FX.heads = false;
  heroLight.position.set(-4.4, 5.6, ZS - 4.6);
}

// F — "Karşımda bir kadın var"
shot(23.9, 28.2, (t, lt) => {
  heroScene(t);
  place(samu, S0.x, 0, S0.z, yawSG); pose(samu, { yaw: 0.05 });
  place(girl, G0.x, 0.15, G0.z, yawGS - 0.5 + smooth(1.5, 3.5, lt) * 0.5); pose(girl, { armR: umbArm, yaw: -0.2 + smooth(1.5, 3.5, lt) * 0.2 }); girlUmbrella(girl);
  const back = V(S0.x - dirSG.x * 1.6 + 0.45, 1.75, S0.z - dirSG.z * 1.6 + 0.6 + 0.05);
  const p = back.clone().lerp(V(S0.x + 0.2, 1.7, S0.z + 0.35), smooth(0, 4.3, lt) * 0.55);
  cam(V(S0.x - dirSG.x * -1.5 + 0.5, 1.72, S0.z - dirSG.z * -1.5 + 0.2).lerp(V(S0.x - dirSG.x * -0.9 + 0.4, 1.72, S0.z - dirSG.z * -0.9 + 0.15), smooth(0, 4.3, lt)), V(G0.x, 1.4, G0.z), 40 - lt * 1.2);
  FX.rainSpeed = lerp(1, 0.55, smooth(1, 4, lt)); setDream(0.12 * smooth(1, 4, lt));
  FX.hero = 1.4 + beatPulse(t) * 0.3;
});
// G — Samu close-up "Tarif edemem ama"
shot(28.2, 31.9, (t, lt) => {
  heroScene(t);
  place(samu, S0.x, 0, S0.z, yawSG); pose(samu, { smile: lt > 1.4, yaw: -0.08, pitch: -0.02 });
  place(girl, G0.x, 0.15, G0.z, yawGS); pose(girl, { armR: umbArm }); girlUmbrella(girl);
  const hp = headPos(samu);
  const p = rel(samu, V(-0.42 + lt * 0.02, 1.7, 0.62)); cam(p, hp.clone().add(V(0, -0.02, 0)), 34 - lt * 0.8);
  FX.rainSpeed = 0.45; setDream(0.18); FX.fill = 0.6;
  fillLight.position.copy(rel(samu, V(-0.3, 1.9, 1.2)));
});
// H — girl close-up "Cennetten bir parça"
shot(31.9, 35.8, (t, lt) => {
  heroScene(t); setDream(0.25 + 0.2 * smooth(0, 3.9, lt));
  place(samu, S0.x, 0, S0.z, yawSG); pose(samu, {});
  place(girl, G0.x, 0.15, G0.z, yawGS); pose(girl, { armR: umbArm, smile: lt > 1.6, yaw: lerp(-0.5, 0, smooth(0.3, 1.6, lt)), pitch: 0.04 }); girlUmbrella(girl, -0.12 * smooth(0.3, 1.6, lt));
  const hp = headPos(girl);
  const p = rel(girl, V(0.3 - lt * 0.03, 1.55, 0.72)); cam(p, hp.clone().add(V(0, -0.01, 0)), 32);
  FX.rainSpeed = 0.18; FX.rainLen = 0.12; FX.spark = smooth(0.5, 2.5, lt) * 0.9; FX.sparkC = V(G0.x, 1.6, G0.z); FX.sparkR = 2.5;
  FX.fill = 0.7; fillLight.position.copy(rel(girl, V(0.2, 1.8, 1.2)));
});
// I — wide two-shot across the road
shot(35.8, 39.3, (t, lt) => {
  heroScene(t); setDream(0.45);
  place(samu, S0.x, 0, S0.z, yawSG); pose(samu, { smile: true });
  place(girl, G0.x, 0.15, G0.z, yawGS); pose(girl, { armR: umbArm, smile: true }); girlUmbrella(girl);
  const ang = -0.9 + lt * 0.06;
  cam(V(MID.x + Math.sin(ang) * 9.5, 1.3, MID.z + Math.cos(ang) * 9.5), V(MID.x, 1.1, MID.z), 46);
  FX.rainSpeed = 0.2; FX.rainLen = 0.15; FX.spark = 0.6; FX.sparkC = V(MID.x, 1.4, MID.z); FX.sparkR = 5;
});
// J — walking toward each other, the city sinks away
shot(39.3, 46.6, (t, lt) => {
  heroScene(t);
  const k = smooth(0.2, 6.0, lt);
  setDream(lerp(0.45, 0.85, smooth(0, 7.3, lt))); SINK = smooth(1.0, 7.0, lt);
  const sx = lerp(S0.x, SM.x, k), sz = lerp(S0.z, SM.z, k), gx = lerp(G0.x, GM.x, k), gz = lerp(G0.z, GM.z, k);
  place(samu, sx, 0, sz, yawSG); pose(samu, { walk: k < 0.98 ? 0.7 : 0, phase: lt * 4.2, smile: true });
  place(girl, gx, lerp(0.15, 0, smooth(0.1, 0.25, k)), gz, yawGS); pose(girl, { walk: k < 0.98 ? 0.7 : 0, phase: lt * 4.2 + 1, armR: umbArm, smile: true }); girlUmbrella(girl);
  const perp = { x: -dirSG.z, z: dirSG.x };
  cam(V(MID.x + perp.x * 6.5, 0.7 + lt * 0.05, MID.z + perp.z * 6.5), V(MID.x, 1.0, MID.z), 42);
  FX.rainSpeed = 0.2; FX.rainLen = 0.15; FX.spark = 0.7; FX.sparkC = V(MID.x, 1.4, MID.z); FX.sparkR = 5;
});
// K — face to face, rain frozen
shot(46.6, 50.3, (t, lt) => {
  heroScene(t); setDream(0.88); SINK = 1;
  place(samu, SM.x, 0, SM.z, yawSG); pose(samu, { smile: true, pitch: 0.1 });
  place(girl, GM.x, 0, GM.z, yawGS); pose(girl, { armR: [-0.9, 0.5, -1.0], smile: true, pitch: -0.12 });
  umb.visible = true; umb.position.set(MID.x, 1.12, MID.z); umb.rotation.set(0, 0, 0);
  const perp = { x: -dirSG.z, z: dirSG.x };
  const a = lt * 0.12;
  cam(V(MID.x + perp.x * 1.6 * Math.cos(a) + dirSG.x * 1.6 * Math.sin(a), 1.62, MID.z + perp.z * 1.6 * Math.cos(a) + dirSG.z * 1.6 * Math.sin(a)), V(MID.x, 1.58, MID.z), 38);
  FX.rainSpeed = 0.0; FX.rainLen = 0.06; FX.spark = 1; FX.sparkC = V(MID.x, 1.5, MID.z); FX.sparkR = 2.5;
  FX.fill = 0.8; fillLight.position.set(MID.x, 2.4, MID.z);
});
// L — crane up: road in the clouds
shot(50.3, 56.4, (t, lt) => {
  heroScene(t); setDream(1); SINK = 1;
  place(samu, SM.x, 0, SM.z, yawSG); pose(samu, { smile: true });
  place(girl, GM.x, 0, GM.z, yawGS); pose(girl, { armR: [-0.9, 0.5, -1.0], smile: true });
  umb.visible = true; umb.position.set(MID.x, 1.12, MID.z); umb.rotation.set(0, 0, 0);
  const k = smooth(0, 6.1, lt);
  cam(V(MID.x + 2 + k * 12, 1.6 + k * 9, MID.z + 3 + k * 16), V(MID.x, 1.0 - k * 2, MID.z - k * 10), 44 + k * 6);
  FX.rainSpeed = 0.15; FX.rain = 0.6; FX.spark = 0.8; FX.sparkC = V(MID.x, 2, MID.z); FX.sparkR = 8;
});

// M — "ona galiba" beat montage
const MSTART = 56.4, MEND = 68.8;
shot(MSTART, MEND, (t, lt) => {
  heroScene(t); setDream(1); SINK = 1;
  const bi = beatIndex(t); const seg = Math.floor(bi / 4) % 6;
  place(samu, SM.x, 0, SM.z, yawSG); place(girl, GM.x, 0, GM.z, yawGS);
  pose(samu, { smile: true }); pose(girl, { armR: [-0.9, 0.5, -1.0], smile: true });
  umb.visible = true; umb.position.set(MID.x, 1.12, MID.z); umb.rotation.set(0, 0, 0);
  const pulse = beatPulse(t, 9);
  const dr = Math.sin(lt * 0.5) * 0.04;
  if (seg === 0) { pose(samu, { smile: true, yaw: 0.1 }); const hp = headPos(samu); cam(rel(samu, V(-0.45, 1.7, 0.5)), hp, 28 + dr * 20); }
  else if (seg === 1) { const hp = headPos(girl); cam(rel(girl, V(-0.6, 1.9, -0.9)), hp.clone().add(V(0, 0.1, 0)), 38); }
  else if (seg === 2) { cam(rel(car, V(-3.2, 0.7, 4.5)), rel(car, V(0, 0.7, 0)), 40); }
  else if (seg === 3) { pose(samu, { smile: true, armR: [-0.5, -0.3, -0.4] }); pose(girl, { armR: [-0.9, 0.5, -1.0], armL: [-0.5, 0.3, -0.4], smile: true }); cam(V(MID.x, 1.0, MID.z).add(V(-dirSG.z * 1.1, 0, dirSG.x * 1.1)), V(MID.x, 0.95, MID.z), 40); }
  else if (seg === 4) { const hp = headPos(samu); cam(rel(samu, V(-0.45, 1.75, 0.55)), hp, 30); }
  else { const hp = headPos(girl); cam(rel(girl, V(0.35, 1.58, 0.6)), hp, 30); }
  FX.flash = pulse * 0.22; FX.flashCol = [1, 0.93, 0.9]; FX.ab = 0.001 + pulse * 0.006; FX.rainSpeed = 0.1; FX.rain = 0.5; FX.spark = 0.8; FX.sparkC = V(MID.x, 1.6, MID.z); FX.sparkR = 4;
  FX.fill = 0.7; fillLight.position.set(MID.x, 2.4, MID.z);
  if (t > 68.0) FX.flash = smooth(68.0, 68.8, t) * 0.9;
});

// N — walking together under one umbrella in the clouds
const dreamRoad = (z) => z;
shot(68.8, 76.2, (t, lt) => {
  setDream(1); SINK = 1; parkCar(PARK.x, PARK.z, PARK.yaw, PARK.roll); FX.hazard = true; FX.heads = false;
  const z = ZS - 6 - lt * 1.15;
  place(samu, -0.75, 0, z, Math.PI); place(girl, -1.3, 0, z + 0.05, Math.PI);
  pose(samu, { walk: 0.6, phase: lt * 4.4, armL: [-0.5, 0.5, -1.4], smile: true, yaw: -0.25 + 0.25 * Math.sin(lt * 0.5) });
  pose(girl, { walk: 0.6, phase: lt * 4.4 + Math.PI, smile: true, yaw: 0.3, armR: [-0.2, 0.25, -0.5] });
  umb.visible = true; umb.position.set(-1.02, 1.2, z - 0.05); umb.rotation.set(0, 0, 0.08);
  cam(V(-1.0 + Math.sin(lt * 0.3) * 0.8, 1.55, z - 3.8 + lt * 0.05), V(-1.0, 1.35, z), 40);
  FX.flash = (1 - smooth(68.8, 69.6, t)) * 0.9; FX.rain = 0.45; FX.rainSpeed = 0.5; FX.spark = 0.5; FX.sparkC = V(-1, 1.5, z); FX.sparkR = 4;
  FX.fill = 0.6; fillLight.position.set(-1, 2.5, z - 2);
});
// O — together in the car, driving on the cloud road
const dz = (t) => ZS - 60 - 14 * (t - 76.2);
function dreamDrive(t) { car.position.set(LANE, 0, dz(t)); car.rotation.set(0, 0, 0); seat(samu, -1); seat(girl, 1); }
shot(76.2, 83.9, (t, lt) => {
  setDream(1); SINK = 1; dreamDrive(t);
  pose(samu, { sit: true, armR: [-1.1, 0.12, -0.55], armL: [-1.1, -0.12, -0.55], smile: true, yaw: lt > 3.5 && lt < 5.5 ? -0.5 : 0 });
  pose(girl, { sit: true, armR: [-0.3, 0, -0.9], armL: [-0.3, 0, -0.9], smile: true, yaw: 0.55 + Math.sin(lt * 0.8) * 0.1, roll: 0.06 });
  cam(rel(car, V(0.0, 1.2, -0.62)), rel(car, V(0, 1.22, 0.5)), 72);
  FX.rain = 0.3; FX.drops = 0.5; FX.fill = 0.35; fillLight.position.copy(rel(car, V(0, 0.95, -0.45)));
});
// P — car on the cloud road, drone orbit
shot(83.9, 90.9, (t, lt) => {
  setDream(1); SINK = 1; dreamDrive(t);
  pose(samu, { sit: true, armR: [-1.1, 0.12, -0.55], armL: [-1.1, -0.12, -0.55], smile: true }); pose(girl, { sit: true, smile: true, yaw: 0.4 });
  const a = 2.4 + lt * 0.22, r = 9 + lt * 0.6;
  cam(car.position.clone().add(V(Math.sin(a) * r, 3.5 + lt * 0.4, Math.cos(a) * r)), car.position.clone().add(V(0, 0.6, -1)), 48);
  FX.rain = 0.3; FX.spark = 0.6; FX.sparkC = car.position.clone(); FX.sparkR = 10;
});
// Q — through the windshield
shot(90.9, 94.0, (t, lt) => {
  setDream(1); SINK = 1; dreamDrive(t);
  pose(samu, { sit: true, armR: [-1.1, 0.12, -0.55], armL: [-1.1, -0.12, -0.55], smile: true, yaw: -0.3, pitch: 0.05 });
  pose(girl, { sit: true, smile: true, yaw: 0.6, roll: 0.1, armL: [-0.3, 0, -0.9] });
  cam(rel(car, V(0.1, 1.25, -2.9)), rel(car, V(0, 1.15, 0.3)), 44);
  FX.rain = 0.3; FX.drops = 0.6; FX.fill = 0.8; fillLight.position.copy(rel(car, V(0, 1.6, -1.5)));
});
// R — breakdown: hands
shot(94.0, 98.0, (t, lt) => {
  setDream(1); SINK = 1; const tt = 94 + lt * 0.15; car.position.set(LANE, 0, dz(94) - lt * 1.2); seat(samu, -1); seat(girl, 1);
  pose(samu, { sit: true, armR: [-0.95, -0.5, -0.5], armL: [-1.1, -0.12, -0.55], smile: true, yaw: -0.3 });
  pose(girl, { sit: true, armL: [-0.95, 0.5, -0.5], armR: [-0.3, 0, -0.9], smile: true, yaw: 0.4 });
  cam(rel(car, V(0.0, 1.32, -1.7 + lt * 0.12)), rel(car, V(0.0, 1.2, 0.3)), 40);
  FX.rain = 0; FX.drops = 0.4; FX.fade = 0.8 + 0.2 * smooth(97, 98, t); FX.sat = 0.75; FX.fill = 0.5; fillLight.position.copy(rel(car, V(0, 1.6, -1.6)));
});
// S — orbit dance in the clouds (high energy)
shot(98.0, 110.0, (t, lt) => {
  setDream(1); SINK = 1; parkCar(PARK.x, PARK.z, PARK.yaw, PARK.roll); FX.hazard = true; FX.heads = false;
  const C = V(MID.x, 0, MID.z);
  const sp = lt * 0.9;
  place(samu, C.x + Math.sin(sp) * 0.45, 0, C.z + Math.cos(sp) * 0.45, sp + Math.PI); place(girl, C.x - Math.sin(sp) * 0.45, 0, C.z - Math.cos(sp) * 0.45, sp);
  pose(samu, { armR: [-1.2, -0.2, -0.3], armL: [-0.3, 0.2, -0.3], smile: true, pitch: 0.08 }); pose(girl, { armR: [-1.2, -0.2, -0.3], armL: [-0.3, 0.2, -0.3], smile: true, pitch: -0.1 });
  const seg = Math.floor((t - 98) / (8 * 0.4644)) % 3, pulse = beatPulse(t, 8);
  if (seg === 0) { const a = -lt * 0.5; cam(V(C.x + Math.sin(a) * 4.5, 1.4, C.z + Math.cos(a) * 4.5), V(C.x, 1.2, C.z), 50); }
  else if (seg === 1) { const a = lt * 0.7; cam(V(C.x + Math.sin(a) * 2.2, 0.35, C.z + Math.cos(a) * 2.2), V(C.x, 1.6, C.z), 60, 0.15 * Math.sin(lt)); }
  else { const a = lt * 0.6; cam(V(C.x + Math.sin(a) * 2.2, 4.2 - Math.sin(lt) * 0.4, C.z + Math.cos(a) * 2.2), V(C.x, 0.6, C.z), 58); }
  FX.rain = 0.7; FX.rainSpeed = -0.6; FX.rainLen = 0.3; FX.spark = 1; FX.sparkC = V(C.x, 1.5, C.z); FX.sparkR = 6;
  FX.flash = pulse * 0.15; FX.flashCol = [1, 0.92, 0.88]; FX.ab = 0.0015 + pulse * 0.004; FX.lampPulse = pulse; FX.fill = 0.8 + pulse; fillLight.position.set(C.x, 2.8, C.z);
});
// T — drop to silence
shot(110.0, 114.0, (t, lt) => {
  setDream(1); SINK = 1; parkCar(PARK.x, PARK.z, PARK.yaw, PARK.roll);
  place(samu, SM.x, 0, SM.z, yawSG); place(girl, GM.x, 0, GM.z, yawGS);
  pose(samu, { smile: true, pitch: 0.1, lean: 0.06 }); pose(girl, { smile: true, pitch: -0.14, armR: [-0.9, 0.5, -1.0] });
  umb.visible = false;
  const perp = { x: -dirSG.z, z: dirSG.x }; const k = smooth(0, 3.6, lt);
  cam(V(MID.x + perp.x * lerp(2.4, 0.9, k), 1.62, MID.z + perp.z * lerp(2.4, 0.9, k)), V(MID.x, 1.6, MID.z), 36);
  FX.rain = 0.3; FX.rainSpeed = 0.0; FX.spark = 0.8; FX.sparkC = V(MID.x, 1.6, MID.z); FX.sparkR = 2;
  FX.fade = 1 - smooth(112.6, 113.7, t); FX.fill = 0.9; fillLight.position.set(MID.x, 2.2, MID.z);
});
// U — burst montage
shot(114.0, 128.0, (t, lt) => {
  setDream(1); SINK = 1;
  const seg = Math.floor(lt / (8 * 0.4644)) % 4, pulse = beatPulse(t, 8);
  if (seg === 0 || seg === 2) {
    const zz = ZS - 300 - (t - 114) * 24; car.position.set(LANE, 0, zz); car.rotation.set(0, 0, 0); seat(samu, -1); seat(girl, 1);
    pose(samu, { sit: true, armR: [-1.1, 0.12, -0.55], armL: [-1.1, -0.12, -0.55], smile: true }); pose(girl, { sit: true, smile: true, yaw: 0.4, armR: [-2.6, 0.2, -0.2] });
    if (seg === 0) cam(rel(car, V(-2.1, 0.5, -3.5)).add(shake(t, 0.03)), rel(car, V(0, 0.9, 1)), 64, -0.06);
    else cam(rel(car, V(2.6, 4.5, 8)), rel(car, V(0, 0.5, -2)), 50);
    FX.rainLen = 1.3; FX.rain = 0.6;
  } else {
    parkCar(PARK.x, PARK.z, PARK.yaw, 0); car.position.y = 0;
    const lp1 = rel(car, V(-0.3, 0.98, -1.15)), lp2 = rel(car, V(0.35, 0.98, -1.15));
    place(samu, lp1.x, lp1.y - 0.93, lp1.z, car.rotation.y); place(girl, lp2.x, lp2.y - 0.93 * 0.92, lp2.z, car.rotation.y);
    pose(samu, { sit: true, armR: [0.2, -0.3, -0.2], armL: [-2.8, 0.1, -0.1], smile: true, pitch: -0.5 });
    pose(girl, { sit: true, armR: [-2.8, -0.2, -0.1], smile: true, pitch: -0.55, roll: 0.15 });
    if (seg === 1) cam(rel(car, V(0.05, 1.3, -5.2)), rel(car, V(0.0, 1.4, -1.1)), 42);
    else { const k = smooth(0, 3.7, (lt % 3.715)); cam(rel(car, V(0, 2.4 + k * 6, -1.0 + k * 1)), rel(car, V(0, 0.8, -1.15)), 46, 0.3 * k); }
    FX.rain = 0.4; FX.rainSpeed = -0.5;
  }
  FX.flash = Math.max(pulse * 0.16, (1 - smooth(114.0, 114.8, t))); FX.flashCol = [1, 0.93, 0.9]; FX.ab = 0.0015 + pulse * 0.004; FX.lampPulse = pulse; FX.spark = 0.6; FX.sparkC = camera.position.clone(); FX.sparkR = 8;
});
// V — reality: broken car, walking away
shot(128.0, 144.5, (t, lt) => {
  parkCar(PARK.x, PARK.z, PARK.yaw, PARK.roll); car.userData.door.rotation.y = 0; FX.hazard = true; FX.heads = false; FX.smoke = smooth(0, 2, lt);
  heroLight.position.set(-4.4, 5.6, ZS - 4.6);
  const z = ZS - 1.5 - smooth(1.5, 16, lt) * 15;
  place(samu, -1.1, 0, z, Math.PI); place(girl, -1.6, 0, z + 0.05, Math.PI);
  pose(samu, { walk: 0.55, phase: lt * 4.2, armL: [-0.5, 0.5, -1.4], yaw: -0.3 }); pose(girl, { walk: 0.55, phase: lt * 4.2 + Math.PI, yaw: 0.25, armR: [-0.2, 0.25, -0.5] });
  umb.visible = true; umb.position.set(-1.35, 1.2, z - 0.05); umb.rotation.set(0, 0, 0.08);
  const k = smooth(0, 9, lt), up = smooth(9, 16.5, lt);
  cam(V(PARK.x + 3 - k * 3.5, 1.4 + up * 9, PARK.z + 8 + k * 1 + up * 6), V(lerp(PARK.x, -1.2, k), lerp(0.8, 1.2, k) + up * 2, lerp(PARK.z, z, k) - up * 12), 46);
  setDream(0.4 * up); FX.rain = 1; FX.sat = 0.75; FX.tint = [0.88, 0.95, 1.12];
  FX.fade = 1 - smooth(143.0, 144.5, t);
});
// W — end card
shot(144.5, 150.01, (t, lt) => {
  FX.fade = 0; car.visible = false;
  const o = smooth(0.3, 1.3, lt) * (1 - smooth(4.6, 5.5, lt));
  const a = overlay('end1', [{ text: 'SAMU', font: '150px VT', color: '#ffffff', glow: 'rgba(255,140,200,0.8)', blur: 14, y: 0.5 }], 300, 0, 22); a.material.opacity = o;
  const b = overlay('end2', [{ text: 'cennetten bi parça', font: 'italic 500 110px Corm', color: '#ffe8f3', glow: 'rgba(255,150,210,0.8)', blur: 20, y: 0.5 }], 360, 0, -32); b.material.opacity = o;
});

const LYRICS = [
  [1.915, 5.346, 'Gelen olmadı, giden oldu hep'],
  [5.346, 9.016, 'Kaldım kendime sebep kalmadı'],
  [9.016, 12.527, 'Yağmur olmadı, çözüm olmadı'],
  [12.527, 16.436, 'Kalbime serinlik desen olmadı'],
  [16.436, 19.867, 'Bugün zorladım, ara gazladım'],
  [19.867, 23.936, 'Arabayı çok kötü yerde bıraktım ama'],
  [23.936, 28.165, 'Karşımda bir kadın var'],
  [28.165, 31.915, 'Tarif edemem ama'],
  [31.915, 35.824, 'Cennetten bir parça'],
  [35.824, 39.335, 'Aşık oluyorum ona, ona galiba'],
  [39.335, 42.926, 'Karşımda bir kadın var'],
  [42.926, 46.596, 'Tarif edemem ama'],
  [46.596, 50.266, 'Cennetten bir parça'],
  [50.266, 56.2, 'Aşık oluyorum ona, ona galiba'],
  [56.41, 61.0, 'Ona galiba'],
  [62.0, 66.41, 'Ona galiba'],
  [67.42, 68.856, 'Ona galiba'],
  [68.856, 72.447, 'Karşımda bir kadın var'],
  [72.447, 76.197, 'Tarif edemem ama'],
  [76.197, 79.867, 'Cennetten bir parça'],
  [79.867, 84.176, 'Aşık oluyorum ona, ona galiba'],
  [84.176, 87.207, 'Karşımda bir kadın var'],
  [87.207, 90.957, 'Tarif edemem ama'],
  [90.957, 93.91, 'Cennetten bir parça'],
  [93.91, 99.5, 'Aşık oluyorum ona, evet, ona galiba'],
  [136.516, 141.702, 'Ve arabaya bir şey oldu'],
  [141.702, 144.3, 'Kalbime değil']
];
function subtitles(t) {
  LYRICS.forEach((L, i) => {
    if (t < L[0] || t >= L[1]) return;
    const m = overlay('ly' + i, [{ text: L[2], font: 'bold 60px FreeSans', color: '#f4f1e6', stroke: 10, strokeColor: '#0c0c0c', y: 0.5 }], 600, 0, -146, 1500);
    m.material.opacity = smooth(L[0], L[0] + 0.12, t) * (1 - smooth(L[1] - 0.12, L[1], t));
  });
}
// ---------- frame ----------
const tmpC = new THREE.Color();
function applyFX(t) {
  const d = DREAM;
  skyU.top.value.copy(N.top).lerp(D.top, d); skyU.hor.value.copy(N.hor).lerp(D.hor, d); skyU.bot.value.copy(N.bot).lerp(D.bot, d);
  scene.fog.color.copy(N.fog).lerp(D.fog, d); scene.fog.near = lerp(3, 10, d); scene.fog.far = lerp(55, 120, d);
  hemi.color.set(0x8a93a8).lerp(col('#e6d2da'), d); hemi.groundColor.set(0x24252a).lerp(col('#9c8a96'), d); hemi.intensity = lerp(2.0, 1.6, d);
  moon.color.set(0xa8b4c8).lerp(col('#f0e2e6'), d); moon.intensity = lerp(1.6, 1.3, d);
  sinkGroup.position.y = -60 * SINK * SINK; sinkGroup.visible = SINK < 0.98;
  const co = clamp((d - 0.15) / 0.6) * 0.75; for (const m of cloudMats) m.opacity = co; clouds.visible = co > 0.01;
  heroLight.intensity = 9 * FX.hero * (DREAM > 0.9 ? 0.5 : 1);
  fillLight.intensity = 3 * FX.fill;
  lampGlowMat.opacity = 0.9 + FX.lampPulse * 0.5; coneMat.opacity = 0.045 + FX.lampPulse * 0.05 + d * 0.02;
  lampGlowMat.color.set(0xffd9a0).lerp(col('#f2d0d8'), d * 0.4);
  reflMat.opacity = 0.45 * (1 - SINK * 0.4);
  roadMat.color.set(0xffffff).lerp(col('#d8ccd2'), d);
  // car fx
  const u = car.userData;
  const hz = FX.hazard && (Math.floor(t * 2.4) % 2 === 0);
  u.haz.forEach((s) => (s.visible = hz));
  u.heads.forEach((s) => (s.visible = FX.heads)); u.beams.forEach((b) => (b.visible = FX.heads));
  u.glass.forEach((g) => { g.material.opacity = 0.55 * FX.drops; g.material.map.offset.set(0, -t * 0.02); });
  const wp = FX.wiper ? (1 - Math.cos(t * Math.PI * 2 / (4 * 0.4644))) / 2 : 0;
  u.wipers.forEach((w) => (w.rotation.set(-0.8, 0, wp * 1.55, 'XYZ')));
  u.smoke.forEach((s, i) => { const ph = ((t * 0.35 + i / u.smoke.length) % 1); s.visible = FX.smoke > 0.01; s.material.opacity = FX.smoke * 0.35 * Math.sin(ph * Math.PI); s.position.set(Math.sin(i * 3.1) * 0.3 + ph * 0.4, 1.0 + ph * 3.2, -1.4 + Math.cos(i * 1.7) * 0.25); s.scale.setScalar(0.6 + ph * 2.4); });
  // post
  postU.flash.value = FX.flash; postU.ab.value = FX.ab; postU.bloom.value = lerp(FX.bloom, 0.55, d); postU.vig.value = FX.vig; postU.sat.value = lerp(FX.sat, 0.82, d) * 0.92;
  const tn = FX.tint; postU.tint.value.set(lerp(tn[0], 1.04, d), lerp(tn[1], 0.99, d), lerp(tn[2], 0.98, d));
  postU.fade.value = FX.fade; postU.flashCol.value.set(...FX.flashCol); postU.seed.value = (t * 30) % 97;
}

// rain speed needs the shot's FX before integrating; do a lightweight pre-pass
window.renderAt = function (t) {
  reset(); const s = shots.find((x) => t >= x.a && t < x.b) || shots[shots.length - 1]; s.fn(t, t - s.a);
  const sp = FX.rainSpeed; const dtv = t - lastT;
  if (dtv > 0 && dtv < 0.2) rainClock += dtv * sp; else if (dtv !== 0) rainClock = t;
  lastT = t;
  reset(); s.fn(t, t - s.a);
  subtitles(t); applyFX(t);
  sky.position.copy(camera.position);
  updateRain(camera.position, FX.rain, FX.rainLen);
  updateSparkles(t, FX.sparkC, FX.sparkR, FX.spark);
  renderer.setRenderTarget(rt); renderer.setClearColor(0x000000, 1); renderer.clear(); renderer.render(scene, camera);
  renderer.setRenderTarget(null); renderer.autoClear = true; renderer.render(postScene, postCam);
  renderer.autoClear = false; renderer.render(ov, ovCam); renderer.autoClear = true;
};
window.frameJPEG = (t, q = 0.93) => { window.renderAt(t); return canvas.toDataURL('image/jpeg', q); };

async function boot() {
  const fp = './node_modules/@fontsource/';
  const faces = [
    new FontFace('Corm', `url(${fp}cormorant-garamond/files/cormorant-garamond-latin-600-italic.woff2)`, { style: 'italic', weight: '600', unicodeRange: 'U+0000-00FF' }),
    new FontFace('Corm', `url(${fp}cormorant-garamond/files/cormorant-garamond-latin-ext-600-italic.woff2)`, { style: 'italic', weight: '600', unicodeRange: 'U+0100-024F' }),
    new FontFace('Corm', `url(${fp}cormorant-garamond/files/cormorant-garamond-latin-500-italic.woff2)`, { style: 'italic', weight: '500', unicodeRange: 'U+0000-00FF' }),
    new FontFace('Corm', `url(${fp}cormorant-garamond/files/cormorant-garamond-latin-ext-500-italic.woff2)`, { style: 'italic', weight: '500', unicodeRange: 'U+0100-024F' }),
    new FontFace('VT', `url(${fp}vt323/files/vt323-latin-400-normal.woff2)`, { unicodeRange: 'U+0000-00FF' }),
    new FontFace('VT', `url(${fp}vt323/files/vt323-latin-ext-400-normal.woff2)`, { unicodeRange: 'U+0100-024F' }),
  ];
  for (const f of faces) { await f.load(); document.fonts.add(f); }
  BEATS = await (await fetch('./beats.json')).json();
  window.READY = true;
}
// text meshes are built at import time; rebuild title textures after fonts load
boot().then(() => {
  const tb = textMesh(TITLE_L, TITLE_O), tf = textMesh(TITLE_L, { ...TITLE_O, clipTop: 0.56 });
  titleBack.geometry = tb.geometry; titleBack.material = tb.material; titleFront.geometry = tf.geometry; titleFront.material = tf.material;
  titleBack.material.depthTest = true; titleFront.material.depthTest = false; titleFront.renderOrder = 50;
});
