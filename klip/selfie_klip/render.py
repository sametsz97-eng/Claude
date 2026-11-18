#!/usr/bin/env python3
"""Samu - Cennetten Bi Parça · arabada gece sürüşü klibi (3:4 dikey).

Tek görselden (temiz.png) sanal kamera hareketleri, geçen sokak lambası
ışıkları, sallanan tespih ve şarkı sözlerine göre zamanlanmış retro oyun
altyazılarıyla klip üretir.

Kullanım:  python3 render.py [cikti.mp4] [baslangic_sn] [bitis_sn]
"""
import json, math, os, re, subprocess, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SONG = os.path.join(ROOT, 'song.m4a')
W, H, FPS = 1080, 1440, 30
SONG_END = 144.52
END = SONG_END + 3.0           # son yazı için 3 sn ek

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'cikti', 'samu_cennetten_bi_parca_araba.mp4')
T0 = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
T1 = float(sys.argv[3]) if len(sys.argv) > 3 else END

rng = np.random.default_rng(7)

# ---------------------------------------------------------------- kaynak
src = cv2.imread(os.path.join(HERE, 'temiz.png')).astype(np.float32) / 255.0  # BGR
SH, SW = src.shape[:2]                     # 2400 x 1792
b, g, r = src[..., 0], src[..., 1], src[..., 2]
v = src.max(axis=2)
# gece gökyüzü: koyu lacivert pikseller -> cam arkası maskesi
sky = ((b > r + 0.06) & (b > g + 0.01) & (v < 0.5) & (v > 0.05)).astype(np.float32)
sky[1150:] = 0
sky = cv2.morphologyEx(sky, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
sky = cv2.GaussianBlur(sky, (0, 0), 3)
lum = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)

# tespih sallanma bölgesi
ROS_X, ROS_TOP, ROS_BOT = 1380, 470, 1300
ros_mask = np.zeros((SH, SW), np.float32)
ros_mask[ROS_TOP:ROS_BOT, ROS_X - 55:ROS_X + 55] = 1
ros_mask = cv2.GaussianBlur(ros_mask, (0, 0), 14)
yy = np.arange(SH, dtype=np.float32)
ros_lever = np.clip((yy - ROS_TOP) / (ROS_BOT - ROS_TOP), 0, 1)
ros_lever = np.sin(ros_lever * math.pi * 0.85)  # alt uç el/direksiyona değiyor
ROS_Y0, ROS_Y1, ROS_X0, ROS_X1 = 420, 1340, ROS_X - 110, ROS_X + 110

# ---------------------------------------------------------------- müzik
BEATS = np.array(json.load(open(os.path.join(ROOT, 'beats.json'))), dtype=np.float64)

def beat_pulse(t, k=7.0):
    i = np.searchsorted(BEATS, t) - 1
    if i < 0: return 0.0
    return math.exp(-(t - BEATS[i]) * k)

def parse_lyrics():
    srt = subprocess.run(['ffmpeg', '-v', 'error', '-i', SONG, '-map', '0:s:0', '-f', 'srt', '-'],
                         capture_output=True, text=True).stdout
    out = []
    for blk in srt.strip().split('\n\n'):
        lines = blk.strip().split('\n')
        if len(lines) < 3: continue
        m = re.findall(r'(\d+):(\d+):(\d+),(\d+)', lines[1])
        a, e = [int(h) * 3600 + int(mi) * 60 + int(s) + int(ms) / 1000 for h, mi, s, ms in m]
        txt = ' '.join(lines[2:]).strip()
        if txt.startswith('[') or e <= a: continue
        out.append([a, e, txt])
    for i, l in enumerate(out):           # uzun satırları kısalt
        nxt = out[i + 1][0] if i + 1 < len(out) else 1e9
        l[1] = min(l[1], nxt, l[0] + 5.2)
    return out

LYRICS = parse_lyrics()

# ---------------------------------------------------------------- altyazı
FONT_DIR = os.path.join(ROOT, 'node_modules', '@fontsource', 'vt323', 'files')
FONT_FILES = [os.path.join(FONT_DIR, f'vt323-{s}-400-normal.woff') for s in ('latin', 'latin-ext')]
CMAPS = [set(TTFont(f).getBestCmap()) for f in FONT_FILES]
FSIZE = 112
FONTS = [ImageFont.truetype(f, FSIZE) for f in FONT_FILES]

def font_for(ch):
    for f, cm in zip(FONTS, CMAPS):
        if ord(ch) in cm: return f
    return FONTS[0]

def tr_lower(s):
    return s.replace('I', 'ı').replace('İ', 'i').lower()

def split2(s):
    """görseldeki gibi: virgülden ya da ortadan iki satıra böl"""
    if len(s) <= 18: return [s]
    if ',' in s:
        i = s.index(',')
        if 6 <= i <= len(s) - 6: return [s[:i + 1], s[i + 1:].strip()]
    mid = len(s) / 2
    sp = [i for i, c in enumerate(s) if c == ' ']
    i = min(sp, key=lambda k: abs(k - mid))
    return [s[:i], s[i + 1:]]

def draw_text_line(d, x, y, text, fill, stroke=7):
    for ch in text:
        f = font_for(ch)
        d.text((x, y), ch, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
        x += f.getlength(ch)

def line_width(text):
    return sum(font_for(c).getlength(c) for c in text)

def render_sub(text, top=150, colors=((255, 236, 140, 255), (250, 250, 250, 255))):
    img = Image.new('RGBA', (W, 420), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rows = split2(tr_lower(text))
    for k, row in enumerate(rows):
        w = line_width(row)
        draw_text_line(d, (W - w) / 2, 10 + k * 104, row, colors[min(k, 1)])
    a = np.asarray(img).astype(np.float32) / 255.0
    return a[..., [2, 1, 0]], a[..., 3:4]        # BGR, alpha

SUBS = [(a, e, render_sub(t)) for a, e, t in LYRICS]
SUB_Y = 120

def title_card(lines, size_y):
    img = Image.new('RGBA', (W, size_y), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    y = 0
    for text, col in lines:
        w = line_width(text)
        draw_text_line(d, (W - w) / 2, y, text, col)
        y += 100
    a = np.asarray(img).astype(np.float32) / 255.0
    return a[..., [2, 1, 0]], a[..., 3:4]

TITLE = title_card([('cennetten bi parça', (255, 236, 140, 255)), ('samu', (250, 250, 250, 255))], 230)

# ---------------------------------------------------------------- kamera çekimleri
# (merkez x, merkez y, genişlik) kaynak görsel koordinatında, yükseklik = genişlik*4/3
CAM = {
    'W':  (896, 1200, 1792),   # geniş
    'W2': (896, 1150, 1560),
    'M':  (780, 1180, 1150),   # bel üstü
    'F':  (600, 990, 640),     # yüz
    'F2': (560, 1000, 760),
    'E':  (630, 935, 420),     # gözler
    'H':  (1310, 1150, 760),   # direksiyon + tespih
    'R':  (1440, 880, 680),    # ön cam + tespih
    'G':  (1300, 1920, 820),   # vites eli
    'S':  (330, 860, 720),     # yan cam, sokak lambası
    'D':  (1560, 1650, 700),   # torpido / gösterge
}

def cam(name, dz=1.0, dx=0, dy=0):
    x, y, w = CAM[name]
    return (x + dx, y + dy, w * dz)

SHOTS = []  # (başlangıç, kamera_başı, kamera_sonu)
def shot(t, a, b): SHOTS.append((t, a, b))

# intro + verse: uzun, yavaş çekimler
shot(0.0,    cam('W', 1.0),           cam('W', 0.9))
shot(1.915,  cam('F2', 1.05),         cam('F', 1.0))
shot(5.346,  cam('R', 1.0, 40),       cam('R', 0.95, -40))
shot(9.016,  cam('M', 1.0, -30),      cam('M', 0.93, 30))
shot(12.527, cam('E', 1.12),          cam('E', 0.97))
shot(16.436, cam('G', 1.0),           cam('G', 0.85))
shot(18.15,  cam('H', 0.95),          cam('H', 0.8))
shot(19.867, cam('W2', 0.85),         cam('W', 1.0))
# nakarat 1 (sözlerle kesme)
ch1 = [('F', 1.0, 0.9), ('R', 1.0, 0.92), ('M', 0.95, 0.88), ('E', 1.05, 0.95),
       ('W', 1.0, 0.92), ('H', 1.0, 0.9), ('S', 1.0, 0.9), ('F2', 1.0, 0.75)]
starts = [23.936, 28.165, 31.915, 35.824, 39.335, 42.926, 46.596, 50.266]
for t, (n, z0, z1) in zip(starts, ch1): shot(t, cam(n, z0), cam(n, z1))
# post-chorus "ona galiba": her ölçüde kesme
pc = ['E', 'R', 'F', 'H', 'S', 'F2', 'D', 'M']
bar = 4 * 0.4645
for i, n in enumerate(pc):
    t = 56.41 + i * bar * (12.45 / (len(pc) * bar))
    shot(t, cam(n, 1.0, 20), cam(n, 0.9, -20))
# nakarat 2
ch2 = [('M', 1.0, 0.9), ('E', 1.05, 0.95), ('R', 1.0, 0.92), ('F', 1.0, 0.88),
       ('H', 1.0, 0.9), ('W2', 1.0, 0.9), ('S', 1.0, 0.9), ('F2', 1.0, 0.7)]
starts = [68.856, 72.447, 76.197, 79.867, 84.176, 87.207, 90.957, 93.910]
for t, (n, z0, z1) in zip(starts, ch2): shot(t, cam(n, z0), cam(n, z1))
# enstrümantal: uzun sürüş çekimleri
inst = [(98.5, 'W', 'W2'), (105.9, 'R', 'R'), (113.3, 'G', 'G'), (117.0, 'D', 'D'),
        (120.7, 'S', 'S'), (128.1, 'M', 'F2')]
for t, a, bnm in inst:
    shot(t, cam(a, 1.0, -40), cam(bnm, 0.85, 40))
# outro
shot(136.516, cam('W', 1.0),  cam('W2', 0.95))
shot(141.702, cam('F2', 1.0), cam('E', 1.0))
shot(END + 1, None, None)

def ease(x): return x * x * (3 - 2 * x)

def camera_at(t):
    for i in range(len(SHOTS) - 1):
        t0, a, b_ = SHOTS[i]
        t1 = SHOTS[i + 1][0]
        if t0 <= t < t1:
            u = ease((t - t0) / (t1 - t0))
            return tuple(a[k] + (b_[k] - a[k]) * u for k in range(3)), t - t0
    return CAM['W'], 0.0

# ---------------------------------------------------------------- bölüm renkleri
# (başlangıç, renk çarpanı BGR, ek ışık, doygunluk)
SECTIONS = [
    (0.0,    (1.10, 0.98, 0.90), 0.00, 0.85),   # verse: soğuk
    (23.936, (0.92, 1.00, 1.12), 0.03, 1.05),   # nakarat: sıcak turuncu
    (56.41,  (1.10, 0.92, 1.12), 0.04, 1.00),   # ona galiba: pembe rüya
    (68.856, (0.92, 1.00, 1.12), 0.03, 1.08),   # nakarat 2
    (98.5,   (1.08, 1.02, 0.92), 0.01, 0.92),   # enstrümantal: camgöbeği
    (136.516,(1.00, 0.97, 0.97), 0.00, 0.70),   # outro: solgun
]

def section_at(t):
    cur = SECTIONS[0]
    prev = cur
    for s in SECTIONS:
        if t >= s[0]: prev, cur = cur, s
    u = min(1.0, (t - cur[0]) / 0.6) if cur is not prev else 1.0
    mul = np.array([prev[1][k] + (cur[1][k] - prev[1][k]) * u for k in range(3)], np.float32)
    return mul, prev[2] + (cur[2] - prev[2]) * u, prev[3] + (cur[3] - prev[3]) * u

def in_chorus(t):
    return 23.936 <= t < 56.41 or 68.856 <= t < 98.5

# ---------------------------------------------------------------- geçen lambalar
# her lamba: ekrandan geçiş başlangıç zamanı, yükseklik, boyut
LAMPS = []
t = 0.3
while t < END:
    LAMPS.append((t, rng.uniform(640, 860), rng.uniform(26, 44)))
    t += rng.uniform(1.6, 2.6) if t < 98.5 or t > 136 else rng.uniform(1.2, 2.0)
LAMP_TRAVEL = 1.6     # kaynak genişliğini kaç saniyede geçer
SWEEP_DUR = 0.9

def lamp_layer(t):
    """kaynak koordinatında lamba ışığı (gökyüzü maskeli) + iç mekân ışık süpürmesi"""
    glow = np.zeros((SH // 4, SW // 4), np.float32)   # düşük çözünürlük, sonra büyüt
    sweep_x = []
    for (t0, ly, size) in LAMPS:
        u = (t - t0) / LAMP_TRAVEL
        if -0.2 < u < 1.4:
            x = SW * (1.15 - 1.3 * u)    # sağdan sola
            cx, cy, s = x / 4, ly / 4, size / 4
            cv2.circle(glow, (int(cx), int(cy)), max(1, int(s * 0.6)), 1.0, -1, cv2.LINE_AA)
            cv2.ellipse(glow, (int(cx), int(cy)), (int(s * 3.2), int(s * 1.1)), 0, 0, 360, 0.5, -1, cv2.LINE_AA)
        us = (t - t0 - 0.25) / SWEEP_DUR
        if 0 <= us <= 1:
            sweep_x.append(us)
    glow = cv2.GaussianBlur(glow, (0, 0), 2.2) + 0.6 * cv2.GaussianBlur(glow, (0, 0), 9)
    return glow, sweep_x

# ---------------------------------------------------------------- kare üretimi
ox = np.arange(W, dtype=np.float32)
oy = np.arange(H, dtype=np.float32)
vig = 1 - 0.55 * (((ox[None, :] - W / 2) / (W * 0.62)) ** 2 + ((oy[:, None] - H / 2) / (H * 0.62)) ** 2)
vig = np.clip(vig, 0.25, 1)[..., None].astype(np.float32)
GRAIN = [rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32) for _ in range(8)]
scan = (1 - 0.06 * (np.arange(H) % 3 == 0)).astype(np.float32)[:, None, None]

def shake_at(t):
    amp = 2.0
    if 16.436 <= t < 19.867: amp = 6 + 10 * (t - 16.436) / 3.4      # "ara gazladım"
    if in_chorus(t): amp += 5 * beat_pulse(t, 9)
    jolt = 0.0
    if 137.6 <= t < 139.6:                                            # "arabaya bir şey oldu"
        jolt = 45 * math.exp(-(t - 137.6) * 2.2)
    amp += jolt
    return (amp * (math.sin(t * 13.1) * 0.6 + math.sin(t * 31.7 + 1) * 0.4),
            amp * (math.sin(t * 17.3 + 2) * 0.6 + math.sin(t * 27.1) * 0.4)), jolt

def frame(t):
    (cx, cy, cw), since_cut = camera_at(t)
    ch = cw * 4 / 3
    if in_chorus(t):                     # vuruşta hafif zoom
        cw *= 1 - 0.018 * beat_pulse(t, 8); ch = cw * 4 / 3
    (sx, sy), jolt = shake_at(t)
    cx += sx * cw / W; cy += sy * cw / W
    cx = min(max(cx, cw / 2), SW - cw / 2); cy = min(max(cy, ch / 2), SH - ch / 2)
    sc = cw / W
    x0, y0 = cx - cw / 2, cy - ch / 2

    # tespih sallanması: yalnızca tespih bandını remap et
    base = src
    swing = 9 * math.sin(t * 2.1) + 4 * math.sin(t * 5.3 + 1) + jolt * 0.6 * math.sin(t * 9)
    if x0 < ROS_X1 and x0 + cw > ROS_X0 and y0 < ROS_Y1 and y0 + ch > ROS_Y0:
        base = src.copy()
        sub_m = ros_mask[ROS_Y0:ROS_Y1, ROS_X0:ROS_X1]
        lever = ros_lever[ROS_Y0:ROS_Y1, None]
        gx, gy = np.meshgrid(np.arange(ROS_X0, ROS_X1, dtype=np.float32),
                             np.arange(ROS_Y0, ROS_Y1, dtype=np.float32))
        mx = gx - swing * lever * sub_m
        base[ROS_Y0:ROS_Y1, ROS_X0:ROS_X1] = cv2.remap(src, mx, gy, cv2.INTER_LINEAR)

    # geçen lamba ışığı (cam arkası)
    glow, sweeps = lamp_layer(t)
    glow_full = cv2.resize(glow, (SW, SH), interpolation=cv2.INTER_LINEAR)

    M = np.float32([[sc, 0, x0], [0, sc, y0]])
    warp = lambda img, interp=cv2.INTER_LINEAR: cv2.warpAffine(img, M, (W, H), flags=interp | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
    img = warp(base)
    gl = warp(glow_full * sky)
    lu = warp(lum)

    lamp_col = np.array([0.45, 0.75, 1.0], np.float32)   # BGR turuncu
    img = img + gl[..., None] * lamp_col * 2.2

    # iç mekân ışık süpürmesi: kaynak koordinatında sağdan sola eğik bant
    if sweeps:
        srcx = x0 + ox * sc
        srcy = y0 + oy * sc
        band = np.zeros((H, W), np.float32)
        for us in sweeps:
            pos = SW * (1.25 - 1.6 * us)
            d = (srcx[None, :] + 0.35 * (srcy[:, None] - 1200)) - pos
            band += np.exp(-(d / 330) ** 2) * math.sin(math.pi * us)
        strength = 0.42 + (0.15 if in_chorus(t) else 0)
        light = band[..., None] * lamp_col * strength * (0.35 + 0.9 * lu[..., None])
        img = 1 - (1 - img) * (1 - light)   # screen

    # renk
    mul, lift, sat = section_at(t)
    img = img * mul + lift
    gray = img.mean(axis=2, keepdims=True)
    img = gray + (img - gray) * sat
    if in_chorus(t): img = img * (1 + 0.07 * beat_pulse(t, 6))
    if 137.6 <= t < 140.5:   # elektrik gidip geliyor
        fl = 0.55 + 0.45 * (math.sin(t * 47) > -0.2) if t < 139.2 else 0.75 + 0.25 * (t - 139.2) / 1.3
        img = img * fl
        img[..., 2] += 0.05 * (t < 139.2)

    # hafif renk kayması (PS2 / VHS)
    ca = 2 + int(6 * beat_pulse(t, 10)) if in_chorus(t) else 2
    img[..., 2] = np.roll(img[..., 2], ca, axis=1)
    img[..., 0] = np.roll(img[..., 0], -ca, axis=1)

    img = img * vig * scan
    gr = cv2.resize(GRAIN[int(t * FPS) % len(GRAIN)], (W, H), interpolation=cv2.INTER_NEAREST)
    img = img + gr[..., None] * 0.018

    # kesmelerde kısa beyaz flaş (nakarat girişleri) ve diğer kesmelerde parlaklık patlaması
    if 23.936 <= t < 24.4 or 68.856 <= t < 69.3:
        k = 1 - (t - (23.936 if t < 30 else 68.856)) / 0.45
        img = img + (1 - img) * k * 0.85
    elif since_cut < 0.12 and t > 2:
        img = img * (1 + 0.25 * (1 - since_cut / 0.12))

    # altyazı
    for a, e, (sb, sa) in SUBS:
        if a <= t < e:
            h = sb.shape[0]
            region = img[SUB_Y:SUB_Y + h]
            img[SUB_Y:SUB_Y + h] = region * (1 - sa) + sb * sa
            break
    # açılış ve kapanış yazısı
    for (ta, tb) in ((0.4, 6.0), (SONG_END - 0.5, END)):
        if ta <= t < tb:
            al = min(1, (t - ta) / 0.4) * min(1, (tb - t) / 0.6)
            tb_, ta_ = TITLE
            y = H - 360
            img[y:y + tb_.shape[0]] = img[y:y + tb_.shape[0]] * (1 - ta_ * al) + tb_ * ta_ * al

    # açılış/kapanış kararma
    fade = min(1, t / 1.2) * min(1, max(0, (SONG_END - 1.0 - t) / 2.5) + (1 if t < SONG_END - 3.5 else 0))
    if t >= SONG_END - 0.5:
        fade = 0.0
        # kapanışta sadece yazı kalsın
        al = min(1, (t - (SONG_END - 0.5)) / 0.4) * min(1, (END - t) / 0.6)
        out = np.zeros_like(img)
        tb_, ta_ = TITLE
        y = (H - tb_.shape[0]) // 2
        out[y:y + tb_.shape[0]] = tb_ * ta_ * al
        img = out
        fade = 1.0
    img = img * fade
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)

# ---------------------------------------------------------------- çıktı
def main():
    os.makedirs(os.path.dirname(OUT) or '.', exist_ok=True)
    if OUT.endswith('.png'):
        cv2.imwrite(OUT, frame(T0)); return
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
           '-ss', str(T0), '-i', SONG, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'medium', '-crf', '19',
           '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '256k', '-af', 'apad', '-shortest', '-movflags', '+faststart', OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n0, n1 = int(T0 * FPS), int(T1 * FPS)
    for n in range(n0, n1):
        p.stdin.write(frame(n / FPS).tobytes())
        if (n - n0) % 300 == 0: print(f'{n / FPS:6.1f} sn', flush=True)
    p.stdin.close(); p.wait()
    print('Hazır:', OUT)

if __name__ == '__main__':
    main()
