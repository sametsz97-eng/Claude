#!/usr/bin/env bash
# Tarayıcı demosunu (sahte backend, lib/demo/main_demo.dart) kendi kendine yeten
# statik bir klasör olarak derler: build/web_demo/
#  * CanvasKit CDN yerine yerelden yüklenir (--no-web-resources-cdn)
#  * Emoji fontu indirilip yanına konur; dış ağa hiç istek gitmez
#  * Service worker kapalı
# Kullanım: app/ içinde  ./tool/build_web_demo.sh
set -euo pipefail
cd "$(dirname "$0")/.."
FLUTTER="${FLUTTER:-flutter}"
OUT=build/web_demo

"$FLUTTER" build web -t lib/demo/main_demo.dart --no-web-resources-cdn --release
rm -rf "$OUT"
mkdir -p "$OUT/canvaskit/chromium"
cp build/web/main.dart.js build/web/flutter_bootstrap.js build/web/favicon.png "$OUT/"
cp -r build/web/assets "$OUT/"
cp build/web/canvaskit/canvaskit.js build/web/canvaskit/canvaskit.wasm "$OUT/canvaskit/"
cp build/web/canvaskit/chromium/canvaskit.js build/web/canvaskit/chromium/canvaskit.wasm "$OUT/canvaskit/chromium/"

# Yedek fontların yolunu yerel "fonts/" klasörüne çevir, service worker'ı kapat
python3 - "$OUT/flutter_bootstrap.js" <<'PY'
import re, sys
p = sys.argv[1]
s = open(p).read()
s, n = re.subn(r"_flutter\.loader\.load\(\{.*?\}\);\s*$",
               "_flutter.loader.load({ config: { fontFallbackBaseUrl: 'fonts/' } });\n",
               s, flags=re.S)
assert n == 1, "flutter_bootstrap.js beklenen biçimde değil"
open(p, "w").write(s)
PY

# Emoji fontunu indir (motorun beklediği sürüm yolunu main.dart.js'ten oku)
EMOJI=$(grep -o 'notocoloremoji/v[0-9]*/[A-Za-z0-9_-]*' build/web/main.dart.js | head -1)
mkdir -p "$OUT/fonts/$(dirname "$EMOJI")"
for i in $(seq 0 30); do
  url="https://fonts.gstatic.com/s/$EMOJI.$i.woff2"
  curl -sf -o "$OUT/fonts/$EMOJI.$i.woff2" "$url" || { rm -f "$OUT/fonts/$EMOJI.$i.woff2"; break; }
done

cat > "$OUT/index.html" <<'HTML'
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Anonim Sohbet Demo</title>
  <link rel="icon" type="image/png" href="favicon.png">
</head>
<body style="margin:0;background:#e8e5f5">
  <div id="loading" style="font:15px system-ui,sans-serif;color:#3b3554;text-align:center;padding:40vh 16px 0">Uygulama yükleniyor…</div>
  <script>
    window.addEventListener('flutter-first-frame', function () {
      var el = document.getElementById('loading'); if (el) el.remove();
    });
  </script>
  <script src="flutter_bootstrap.js" async></script>
</body>
</html>
HTML
du -sh "$OUT"
