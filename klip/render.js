// usage: node render.js frames t1,t2,... outdir   |  node render.js video out.mp4 [start end]
const http = require('http'), fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const root = __dirname;
const types = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.woff2': 'font/woff2' };
const srv = http.createServer((q, r) => { const f = path.join(root, decodeURIComponent(q.url.split('?')[0])); fs.readFile(f, (e, d) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, { 'content-type': types[path.extname(f)] || 'application/octet-stream' }); r.end(d); }); });
(async () => {
  await new Promise((ok) => srv.listen(0, ok));
  const port = srv.address().port;
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.log('[page]', m.text()); });
  page.on('pageerror', (e) => console.log('[pageerror]', e.message));
  await page.goto(`http://localhost:${port}/index.html`);
  await page.waitForFunction(() => window.READY === true, null, { timeout: 60000 });
  await page.waitForTimeout(300);
  const mode = process.argv[2];
  if (mode === 'frames') {
    const ts = process.argv[3].split(',').map(Number), out = process.argv[4]; fs.mkdirSync(out, { recursive: true });
    for (const t of ts) {
      const t0 = Date.now();
      // warm the rain clock a little
      await page.evaluate((t) => { for (let k = 10; k > 0; k--) window.renderAt(Math.max(0, t - k / 30)); }, t);
      const d = await page.evaluate((t) => window.frameJPEG(t, 0.95), t);
      fs.writeFileSync(path.join(out, `f_${t.toFixed(2).padStart(6, '0')}.jpg`), Buffer.from(d.split(',')[1], 'base64'));
      console.log('t', t, Date.now() - t0, 'ms');
    }
  } else {
    const out = process.argv[3], start = +(process.argv[4] || 0), end = +(process.argv[5] || 150), fps = 30;
    const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-', '-vf', 'scale=1280:720:flags=neighbor', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    const n0 = Math.round(start * fps), n1 = Math.round(end * fps); const T0 = Date.now();
    for (let n = n0; n < n1; n++) {
      const d = await page.evaluate((t) => window.frameJPEG(t, 0.94), n / fps);
      if (!ff.stdin.write(Buffer.from(d.split(',')[1], 'base64'))) await new Promise((ok) => ff.stdin.once('drain', ok));
      if (n % 150 === 0) console.log(`frame ${n}/${n1} ${((Date.now() - T0) / 1000).toFixed(0)}s`);
    }
    ff.stdin.end(); await new Promise((ok) => ff.on('close', ok));
  }
  await browser.close(); srv.close();
})();
