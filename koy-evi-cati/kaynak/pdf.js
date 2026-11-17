const { chromium } = require('playwright'); const fs=require('fs'); const path=require('path');
const D='/home/user/Claude/koy-evi-cati';
const img=f=>'data:image/png;base64,'+fs.readFileSync(path.join(D,f)).toString('base64');
const pages=[['01-on-cephe.png','Ön Cephe — Yol tarafı'],['02-arka-cephe.png','Arka Cephe — Bahçe tarafı'],['03-sag-cephe.png','Sağ Yan Cephe (Doğu)'],['04-sol-cephe.png','Sol Yan Cephe (Batı)'],['05-terastan-manzara.png','Terastan Manzara'],['06-kus-bakisi.png','Kuş Bakışı — Deniz yönüne'],['07-3b-plan.png','3B Plan (çatı kaldırılmış)']];
const html=`<!doctype html><html><head><meta charset="utf-8"><style>
@page{size:A4 landscape;margin:10mm}body{margin:0;font-family:"DejaVu Sans",Arial,sans-serif;color:#222}
.pg{page-break-after:always;height:188mm;display:flex;flex-direction:column}.pg:last-child{page-break-after:auto}
h1{font-size:26px;margin:0 0 4px}h2{font-size:17px;margin:0 0 6px}.sub{color:#666;font-size:12px;margin-bottom:10px}
.im{flex:1;min-height:0;display:flex;align-items:center;justify-content:center}.im img{max-width:100%;max-height:100%;object-fit:contain}
table{border-collapse:collapse;font-size:12px}td{padding:3px 10px;border-bottom:1px solid #eee}ul{font-size:12px;margin:4px 0;padding-left:18px}li{margin:2px 0}
.cols{display:flex;gap:24px}.foot{font-size:10px;color:#888;margin-top:6px}</style></head><body>
<div class="pg"><h1>Köy Evi — Çatı Katı Projesi</h1><div class="sub">10 × 12 m · 2,20 m duvar · çelik 4 yöne eğimli kırma çatı, profil + trapez sac (yalıtımsız) · denize bakan kapalı teras</div>
<div class="cols"><div><h2>Mahal listesi</h2><table>
${[['Kapalı teras (ön cephe, 3 m derinlik)','26 m²'],['Salon + açık mutfak','25,3 m²'],['Yatak odası 1 (manzaralı)','16,3 m²'],['Yatak odası 2','12,3 m²'],['Banyo / WC','6 m²'],['Depo / çamaşır','5,5 m²'],['Koridor','8 m²'],['<b>İç alan toplam</b>','<b>≈ 82 m² + 26 m² teras</b>']].map(r=>`<tr><td>${r[0]}</td><td>${r[1]}</td></tr>`).join('')}</table></div>
<div><h2>Çatı ve teras</h2><ul>
<li>4 yöne eğimli kırma çatı, her yönde eğim 15° (%27); çelik profil mertek + aşık, üstü kırmızı trapez sac.</li>
<li>Mahya 2 m uzunlukta (ön-arka yönde), kat döşemesinden ≈ 3,71 m. Alın (üçgen) duvarı yok; 4 duvar da 2,20 m düz biter.</li>
<li>Saçak her yönde 0,60 m; 4 tarafta yağmur oluğu.</li>
<li>Teras önü: 50 cm duvar + çelik korkuluk (toplam 1,05 m) — oturunca da deniz görünür.</li>
<li>Teras yan duvarları rüzgâr için tam boy, ortada pencere boşluğu.</li>
<li>Çatı terası da örter; önde 2 çelik dikme + kiriş.</li>
<li>Salon ve yatak odası 1 terasa cam sürgü kapıyla açılır. Merdiven mevcut yerinde (sol-arka).</li></ul>
<h2>Kabuller</h2><ul><li>Ön cephe = yol tarafı (deniz ve dağ manzarası bu yönde).</li><li>Mevcut zemin kat ≈ 3 m yükseklikte modellendi; arazi, deniz ve çevre temsilidir.</li>
<li>Profil/kiriş ölçüleri, rüzgâr yükü ve mevcut döşemenin taşıma kapasitesi yapımdan önce bir inşaat mühendisine kontrol ettirilmelidir.</li></ul></div></div></div>
<div class="pg"><h2>Kat Planı ve Kesit A-A</h2><div class="im"><img src="${img('00-kat-plani-ve-kesit.png')}"></div></div>
${pages.map(([f,t])=>`<div class="pg"><h2>${t}</h2><div class="im"><img src="${img(f)}"></div></div>`).join('')}
</body></html>`;
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.setContent(html,{waitUntil:'load'});
await p.pdf({path:D+'/Koy-Evi-Cati-Kati-Projesi.pdf',format:'A4',landscape:true,printBackground:true});await b.close();})();
