// Generates plan.html (floor plan + section) as SVG
const fs = require('fs');
const S = 62;               // px per metre
const OX = 120, OY = 190;   // plan origin (x=-5, z=-6)
const X = x => OX + (x + 5) * S, Y = z => OY + (z + 6) * S;
let o = [];
const rect = (x0, z0, x1, z1, cls) => o.push(`<rect x="${X(Math.min(x0, x1))}" y="${Y(Math.min(z0, z1))}" width="${Math.abs(x1 - x0) * S}" height="${Math.abs(z1 - z0) * S}" class="${cls}"/>`);
const line = (x0, z0, x1, z1, cls) => o.push(`<line x1="${X(x0)}" y1="${Y(z0)}" x2="${X(x1)}" y2="${Y(z1)}" class="${cls}"/>`);
const text = (x, z, t, cls = 'lbl', extra = '') => o.push(`<text x="${X(x)}" y="${Y(z)}" class="${cls}" ${extra}>${t}</text>`);

// floors
rect(-4.8, 3.0, 4.8, 5.8, 'terr');
rect(-4.8, -5.8, 4.8, 3.0, 'floor');
// stairs
for (let i = 0; i <= 16; i++) line(-4.8, -1.6 - i * 0.25, -3.0, -1.6 - i * 0.25, 'thin');
line(-3.9, -1.75, -3.9, -5.4, 'arrow');
// exterior walls with openings (axis, a0,a1,c, openings[[a,b,kind]])
function wall(axis, a0, a1, c, t, ops, cls = 'wall') {
  let cur = a0; const seg = (s0, s1) => { if (s1 - s0 > 0.001) axis === 'x' ? rect(s0, c - t / 2, s1, c + t / 2, cls) : rect(c - t / 2, s0, c + t / 2, s1, cls); };
  for (const [a, b, k] of ops.sort((p, q) => p[0] - q[0])) {
    seg(cur, a); cur = b;
    if (k === 'w' || k === 'd') {
      if (axis === 'x') { rect(a, c - t / 2, b, c + t / 2, 'winbg'); line(a, c - 0.03, b, c - 0.03, 'win'); line(a, c + 0.03, b, c + 0.03, 'win'); }
      else { rect(c - t / 2, a, c + t / 2, b, 'winbg'); line(c - 0.03, a, c - 0.03, b, 'win'); line(c + 0.03, a, c + 0.03, b, 'win'); }
    }
  }
  seg(cur, a1);
}
wall('x', -5, 5, -5.9, 0.2, [[-4.4, -3.6, 'w'], [-1.7, -0.3, 'w'], [1.6, 2.4, 'w'], [3.6, 4.4, 'w']]);
wall('z', -5.8, 5.8, 4.9, 0.2, [[0.0, 1.4, 'w'], [-2.4, -1.7, 'w'], [3.8, 5.3, 'o']]);
wall('z', -5.8, 5.8, -4.9, 0.2, [[-0.6, 1.0, 'w'], [3.8, 5.3, 'o']]);
wall('x', -4.8, 4.8, 3.0, 0.2, [[-4.3, -0.9, 'd'], [1.7, 3.9, 'd']]);
rect(-4.8, 5.8, 4.8, 6.0, 'para');
for (const x of [-1.65, 1.65]) rect(x - 0.06, 5.84, x + 0.06, 5.96, 'post');
// interior
const iw = (axis, a0, a1, c, ops = []) => wall(axis, a0, a1, c, 0.1, ops.map(([a, b]) => [a, b, 'o']), 'iwall');
iw('z', -1.5, 3.0, 1.0);
iw('x', 1.0, 4.8, -1.5, [[1.3, 2.2]]);
iw('x', -3.0, 4.8, -2.6, [[-1.1, -0.2], [1.4, 2.2], [3.5, 4.3]]);
iw('z', -5.8, -1.5, -3.0);
iw('z', -5.8, -2.6, 1.0); iw('z', -5.8, -2.6, 3.0);
// door swings
const swing = (hx, hz, r, a0, a1) => { const p = a => [X(hx + r * Math.cos(a)), Y(hz + r * Math.sin(a))]; const [x0, y0] = p(a0), [x1, y1] = p(a1); o.push(`<path d="M${X(hx)},${Y(hz)} L${x0},${y0} A${r * S},${r * S} 0 0 1 ${x1},${y1}" class="swing"/>`); };
swing(1.3, -1.45, 0.85, 0, Math.PI / 2);
swing(-1.1, -2.55, 0.85, 0, Math.PI / 2);
swing(1.4, -2.65, 0.75, 0, -Math.PI / 2);
swing(3.5, -2.65, 0.75, 0, -Math.PI / 2);
// sliding door marks
for (const [a, b] of [[-4.3, -0.9], [1.7, 3.9]]) { line(a, 3.08, (a + b) / 2 + 0.1, 3.08, 'slide'); line((a + b) / 2 - 0.1, 2.92, b, 2.92, 'slide'); }
// furniture (light)
const f = (x0, z0, x1, z1) => rect(x0, z0, x1, z1, 'furn');
f(0.35, -1.4, 0.95, 1.6); f(0.3, -1.45, 0.95, -0.8);            // kitchen + fridge
o.push(`<circle cx="${X(0.65)}" cy="${Y(0.6)}" r="${0.18 * S}" class="furn"/>`); o.push(`<circle cx="${X(0.65)}" cy="${Y(0.0)}" r="${0.18 * S}" class="furn"/>`);
f(-1.9, 1.0, -0.5, 1.9);                                           // dining
f(-4.75, -0.6, -4.0, 2.2); f(-3.6, 0.2, -2.9, 1.4);                 // sofa + coffee table
f(3.0, 0.0, 4.75, 1.6); f(2.5, -1.45, 4.7, -0.85);                 // bed1 + wardrobe
f(-2.6, -5.75, -1.0, -3.75); f(0.3, -5.0, 0.95, -3.0);             // bed2 + wardrobe
f(1.1, -5.75, 1.95, -4.85); f(2.4, -3.6, 2.9, -3.0); f(2.45, -5.6, 2.95, -5.0); // shower, wc, sink
f(3.1, -5.75, 3.7, -5.15); f(4.3, -5.75, 4.75, -3.0);              // washer + shelves
f(-3.3, 4.0, -1.3, 4.9); f(1.0, 3.95, 3.6, 4.9); f(1.7, 5.15, 2.9, 5.6); // terrace furniture
// labels
const room = (x, z, n, a) => { text(x, z, n, 'room'); text(x, z + 0.42, a, 'area'); };
room(-2.3, 0.0, 'SALON + MUTFAK', '≈ 25,3 m²');
room(2.6, 0.45, 'YATAK ODASI 1', '≈ 16,3 m²');
room(-1.0, -4.6, 'YATAK ODASI 2', '≈ 12,3 m²');
room(2.0, -4.3, 'BANYO', '≈ 6,0 m²');
room(3.95, -4.35, 'DEPO', '≈ 5,5 m²');
text(1.0, -1.95, 'KORİDOR ≈ 8 m²', 'area');
text(-3.9, -1.0, 'MERDİVEN', 'area'); text(-3.9, -0.65, '(iniş ↑)', 'area');
room(0, 4.55, 'KAPALI TERAS', '≈ 26 m²  ·  seramik / deck');
text(0, 5.55, 'alçak duvar 50 cm + çelik korkuluk (toplam 1,05 m)', 'note');
text(-4.95, 4.55, 'açıklık', 'note', `transform="rotate(-90 ${X(-4.95)} ${Y(4.55)})"`);
text(4.95, 4.55, 'açıklık', 'note', `transform="rotate(90 ${X(4.95)} ${Y(4.55)})"`);
// dimensions
const dimH = (x0, x1, z, t) => { line(x0, z, x1, z, 'dim'); line(x0, z - 0.12, x0, z + 0.12, 'dim'); line(x1, z - 0.12, x1, z + 0.12, 'dim'); text((x0 + x1) / 2, z - 0.1, t, 'dimt'); };
const dimV = (z0, z1, x, t) => { line(x, z0, x, z1, 'dim'); line(x - 0.12, z0, x + 0.12, z0, 'dim'); line(x - 0.12, z1, x + 0.12, z1, 'dim'); const cx = X(x) - 6, cy = Y((z0 + z1) / 2); o.push(`<text x="${cx}" y="${cy}" class="dimt" transform="rotate(-90 ${cx} ${cy})">${t}</text>`); };
dimH(-5, 5, -6.9, '10,00 m');
dimH(-5, -3, -6.4, '2,00'); dimH(-3, 1, -6.4, '4,00'); dimH(1, 3, -6.4, '2,00'); dimH(3, 5, -6.4, '2,00');
dimH(-5, 1, 6.7, '6,00'); dimH(1, 5, 6.7, '4,00');
dimV(-6, 6, 6.1, '12,00 m');
dimV(-6, -2.6, 5.5, '3,40'); dimV(-2.6, -1.5, 5.5, '1,10'); dimV(-1.5, 3, 5.5, '4,50'); dimV(3, 6, 5.5, '3,00');
dimV(-6, -1.5, -5.6, '4,50');
// orientation
o.push(`<text x="${X(0)}" y="${Y(-6) - 82}" class="side">BAHÇE (arka)</text>`);
o.push(`<text x="${X(0)}" y="${Y(6) + 95}" class="side">YOL  ·  DENİZ ve DAĞ MANZARASI ↓</text>`);
const plan = o.join('\n');

// ---------- section A-A (front-back cut) ----------
o = [];
const s2 = 34, SX = 1010, SY = 900; // origin at z=-6 (back) , y=0
const sx = z => SX + (z + 6.9) * s2, sy = y => SY - y * s2;
const poly = (pts, cls) => o.push(`<polygon points="${pts.map(([z, y]) => `${sx(z)},${sy(y)}`).join(' ')}" class="${cls}"/>`);
const sl = (z0, y0, z1, y1, cls) => o.push(`<line x1="${sx(z0)}" y1="${sy(y0)}" x2="${sx(z1)}" y2="${sy(y1)}" class="${cls}"/>`);
const st = (z, y, t, cls = 'dimt', ex = '') => o.push(`<text x="${sx(z)}" y="${sy(y)}" class="${cls}" ${ex}>${t}</text>`);
sl(-8, 0, 9, 0, 'ground');
poly([[-6, 0], [-5.8, 0], [-5.8, 2.8], [-6, 2.8]], 'secold'); poly([[5.8, 0], [6, 0], [6, 2.8], [5.8, 2.8]], 'secold');
poly([[-6, 2.8], [6, 2.8], [6, 3.0], [-6, 3.0]], 'secslab');
poly([[-6, 3], [-5.8, 3], [-5.8, 5.2], [-6, 5.2]], 'secnew');
poly([[2.9, 3], [3.1, 3], [3.1, 5.2], [2.9, 5.2]], 'secnew');
poly([[5.8, 3], [6, 3], [6, 3.5], [5.8, 3.5]], 'secnew');
sl(5.9, 3.55, 5.9, 4.05, 'rail'); sl(5.75, 4.05, 6.05, 4.05, 'rail');
poly([[5.82, 5.0], [5.98, 5.0], [5.98, 5.2], [5.82, 5.2]], 'secsteel');
const t = Math.tan(15 * Math.PI / 180), rs = y => 5.37 + (6 - Math.abs(y)) * t;
sl(-6.6, rs(-6.6), 0, rs(0), 'roof'); sl(0, rs(0), 6.8, rs(6.8), 'roof');
sl(-6.6, rs(-6.6) - 0.17, 0, rs(0) - 0.17, 'rafter'); sl(0, rs(0) - 0.17, 6.8, rs(6.8) - 0.17, 'rafter');
// dims
const vd = (z, y0, y1, txt) => { sl(z, y0, z, y1, 'dim'); sl(z - 0.15, y0, z + 0.15, y0, 'dim'); sl(z - 0.15, y1, z + 0.15, y1, 'dim'); const cx = sx(z) - 6, cy = sy((y0 + y1) / 2); o.push(`<text x="${cx}" y="${cy}" class="dimt" transform="rotate(-90 ${cx} ${cy})">${txt}</text>`); };
vd(-7.4, 3.0, 5.2, '2,20'); vd(-7.4, 0, 3.0, 'mevcut kat');
vd(0.35, 3.0, rs(0), '≈ 3,98 (mahya)');
st(-3.2, 3.6, 'ODALAR', 'secl'); st(4.45, 3.6, 'TERAS', 'secl'); st(-1, 1.3, 'MEVCUT ZEMİN KAT', 'secl');
st(-3.3, rs(-3.3) + 0.6, 'trapez sac (yalıtımsız)', 'note'); st(3.6, rs(3.6) + 0.6, 'eğim 15° (%27)', 'note');
st(-2.5, rs(-2.5) - 1.1, 'çelik profil makas + aşık', 'note');
st(0, -0.8, 'KESİT A-A (ön-arka)', 'secTitle');
st(-6.3, -0.35, 'BAHÇE', 'note'); st(6.5, -0.35, 'YOL / DENİZ →', 'note');
const section = o.join('\n');

const html = `<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;background:#fff;font-family:"DejaVu Sans",Arial,sans-serif}
.wall{fill:#2d2d2d}.iwall{fill:#6a6a6a}.para{fill:#9a9a9a}.post{fill:#111}
.floor{fill:#f4ede1}.terr{fill:url(#tile)}.winbg{fill:#fff}.win{stroke:#2a72b8;stroke-width:2}
.thin{stroke:#888;stroke-width:1}.arrow{stroke:#444;stroke-width:1.5;marker-end:url(#ar)}
.swing{fill:none;stroke:#999;stroke-width:1;stroke-dasharray:4 3}.slide{stroke:#2a72b8;stroke-width:3}
.furn{fill:none;stroke:#b9ad99;stroke-width:1.3}
.room{font-size:17px;font-weight:700;text-anchor:middle;fill:#222}.area{font-size:13px;text-anchor:middle;fill:#555}
.note{font-size:12px;text-anchor:middle;fill:#666;font-style:italic}.dim{stroke:#c0392b;stroke-width:1}.dimt{font-size:13px;fill:#c0392b;text-anchor:middle}
.side{font-size:18px;font-weight:700;text-anchor:middle;fill:#3a6a3a;letter-spacing:1px}
.title{font-size:28px;font-weight:700;fill:#222}.sub{font-size:15px;fill:#555}
.ground{stroke:#6b5b3e;stroke-width:3}.secold{fill:#bdb6a8}.secslab{fill:#8f8f8f}.secnew{fill:#c0392b}.secsteel{fill:#222}
.roof{stroke:#9b3a27;stroke-width:4}.rafter{stroke:#333;stroke-width:3}.rail{stroke:#222;stroke-width:2}
.secl{font-size:13px;fill:#444;text-anchor:middle;font-weight:700}.secTitle{font-size:18px;font-weight:700;fill:#222;text-anchor:middle}
.box{fill:#fafafa;stroke:#ddd}.li{font-size:14px;fill:#333}
</style></head><body>
<svg width="1600" height="1080" viewBox="0 0 1600 1080" xmlns="http://www.w3.org/2000/svg">
<defs><pattern id="tile" width="${0.6 * S}" height="${0.6 * S}" patternUnits="userSpaceOnUse"><rect width="${0.6 * S}" height="${0.6 * S}" fill="#ecd9c6" stroke="#d4bfa8" stroke-width="1"/></pattern>
<marker id="ar" markerWidth="10" markerHeight="10" refX="5" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#444"/></marker></defs>
<text x="40" y="52" class="title">ÇATI KATI PLANI — Köy Evi</text>
<text x="40" y="78" class="sub">10 × 12 m · duvar yüksekliği 2,20 m · çelik profil + trapez sac çatı (yalıtımsız) · ölçek ≈ 1/100</text>
${plan}
<g transform="translate(0,0)">
<rect x="880" y="140" width="680" height="390" rx="8" class="box"/>
<text x="905" y="175" class="room" style="text-anchor:start">Mahal listesi</text>
${[['Salon + açık mutfak', '25,3 m²'], ['Yatak odası 1 (manzaralı)', '16,3 m²'], ['Yatak odası 2', '12,3 m²'], ['Banyo / WC', '6,0 m²'], ['Depo / çamaşır', '5,5 m²'], ['Koridor', '8,0 m²'], ['Merdiven (mevcut yerinde)', '8,1 m²'], ['Kapalı teras (denize bakan)', '26,0 m²']].map(([n, a], i) => `<text x="905" y="${210 + i * 27}" class="li">${n}</text><text x="1180" y="${210 + i * 27}" class="li" style="text-anchor:end">${a}</text>`).join('')}
<line x1="905" y1="428" x2="1180" y2="428" stroke="#ccc"/>
<text x="905" y="452" class="li" font-weight="700">İç alan ≈ 82 m² + teras 26 m²</text>
<text x="1205" y="210" class="li">• Ön cephe (yol/deniz) tamamen teras;</text>
<text x="1215" y="230" class="li">salon ve yatak odası 1 cam sürgü</text>
<text x="1215" y="250" class="li">kapıyla terasa açılır.</text>
<text x="1205" y="280" class="li">• Teras yan duvarlarında rüzgâr</text>
<text x="1215" y="300" class="li">kesen kör duvar + pencere boşluğu.</text>
<text x="1205" y="330" class="li">• Çatı terası da örter; önde 2 çelik</text>
<text x="1215" y="350" class="li">dikme + kiriş (HEA/kutu profil).</text>
<text x="1205" y="380" class="li">• Ön saçak 0,80 m, arka 0,60 m,</text>
<text x="1215" y="400" class="li">yanlar 0,45 m.</text>
<text x="1205" y="430" class="li">• Merdiven mevcut yerinde (sol-arka).</text>
<text x="1205" y="460" class="li">• Mahya, döşemeden ≈ 3,98 m.</text>
</g>
${section}
</svg></body></html>`;
fs.writeFileSync('plan.html', html);
