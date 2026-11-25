"""Anoreksiya nervoza farkındalık Reels videosu: illüstrasyonlu, seslendirmeli.

Çıktı: anoreksiya_reels.mp4 (1080x1920, 9:16, 24 fps, <65 sn)
Gerekenler: python3, pillow, numpy, ffmpeg ve ses/ klasöründeki .wav dosyaları
(ses dosyaları edge-tts ile üretildi; bkz. ses/lines.tsv).
"""
import math
import subprocess
import wave
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
SES = HERE / "ses"
OUT = HERE / "anoreksiya_reels.mp4"
SRT_OUT = HERE / "anoreksiya_reels.srt"

W, H, FPS = 1080, 1920, 24
F_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
F_BI = "/usr/share/fonts/truetype/liberation/LiberationSans-BoldItalic.ttf"
F_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

SKIN = (228, 190, 164)
SKIN_D = (196, 152, 126)
HAIR = (52, 36, 30)
SWEAT = (146, 150, 158)
SWEAT_D = (112, 116, 124)

# ----------------------------------------------------------------------------
# Zaman çizelgesi (ses sürelerinden hesaplanır)
# ----------------------------------------------------------------------------
TEXTS = {}
for line in (SES / "lines.tsv").read_text(encoding="utf-8").strip().splitlines():
    k, _v, _r, _p, txt = line.split("\t")
    TEXTS[k] = txt


def wav_dur(k):
    with wave.open(str(SES / f"{k}.wav")) as w:
        return w.getnframes() / w.getframerate()


ORDER = [  # (anahtar, önceki boşluk)
    ("d1", None), ("vo1", 0.30), ("d2", 0.30), ("d3", 0.25), ("vo2", 0.30),
    ("d4", 0.30), ("d5", 0.25), ("vo3", 0.30), ("vo4", 0.30), ("vo5", 0.30), ("vo6", 1.40),
]
AUDIO = {}
t = 2.5
for k, gap in ORDER:
    if gap is not None:
        t += gap
    AUDIO[k] = (t, t + wav_dur(k))
    t = AUDIO[k][1]
CARD_START = AUDIO["vo6"][1] + 0.35
TOTAL = round(CARD_START + 4.6, 2)
assert TOTAL <= 65.0, TOTAL


def end(k, pad=0.15):
    return AUDIO[k][1] + pad


SCENES = [  # (isim, başlangıç, bitiş)
    ("hook", 0.0, AUDIO["d1"][0]),
    ("mirror", AUDIO["d1"][0], end("d1")),
    ("kitchen", end("d1"), end("vo1")),
    ("breakfast", end("vo1"), end("d3")),
    ("cafe_top", end("d3"), end("vo2")),
    ("cafe_cup", end("vo2"), end("d5")),
    ("scale_night", end("d5"), end("vo3")),
    ("phone", end("vo3"), end("vo4")),
    ("bed", end("vo4"), end("vo5")),
    ("face", end("vo5"), CARD_START),
    ("card", CARD_START, TOTAL),
]


# ----------------------------------------------------------------------------
# Altyazılar
# ----------------------------------------------------------------------------
def split_chunks(text, maxline=30):
    import re
    parts = [p.strip() for p in re.split(r"(?<=[.,:?])\s+", text) if p.strip()]
    chunks = []

    def two_lines(words):
        s = " ".join(words)
        if len(s) <= maxline:
            return s
        best = min(range(1, len(words)), key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))))
        return " ".join(words[:best]) + "\n" + " ".join(words[best:])

    for p in parts:
        words = p.split()
        n = max(1, math.ceil(len(p) / (2 * maxline)))
        size = math.ceil(len(words) / n)
        for i in range(0, len(words), size):
            chunks.append(two_lines(words[i:i + size]))
    merged = []
    for c in chunks:  # çok kısa parçaları birleştir
        if merged and len(c) < 16 and len(merged[-1]) + len(c) <= 2 * maxline and "\n" not in merged[-1]:
            merged[-1] = merged[-1] + "\n" + c
        else:
            merged.append(c)
    return merged


SUBS = []  # (başlangıç, bitiş, metin, diyalog_mu)
for k, (a, b) in AUDIO.items():
    chunks = split_chunks(TEXTS[k])
    total_chars = sum(len(c) for c in chunks)
    tt = a
    for c in chunks:
        d = (b - a) * len(c) / total_chars
        SUBS.append((tt, tt + d, c, k.startswith("d")))
        tt += d


def write_srt():
    def ts(x):
        ms = int(round(x * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    rows = [(0.15, AUDIO["d1"][0], "Biraz daha kilo verirsem\nkendimi seveceğim.")]
    rows += [(a, b, t_) for a, b, t_, _ in SUBS]
    out = []
    for i, (a, b, t_) in enumerate(rows, 1):
        out.append(f"{i}\n{ts(a)} --> {ts(b)}\n{t_}\n")
    SRT_OUT.write_text("\n".join(out), encoding="utf-8")


# ----------------------------------------------------------------------------
# Çizim yardımcıları
# ----------------------------------------------------------------------------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


class SD:
    """Ölçekli çizim: koordinatlar 1x, çizim sx katında (kenar yumuşatma için)."""

    def __init__(self, img, s=2):
        self.img, self.s = img, s
        self.d = ImageDraw.Draw(img, "RGBA")

    def _c(self, v):
        if isinstance(v, (list, tuple)):
            return type(v)(self._c(x) for x in v)
        return v * self.s

    def ellipse(self, box, **kw):
        self._w(kw); self.d.ellipse(self._c(box), **kw)

    def rect(self, box, r=0, **kw):
        self._w(kw)
        if r:
            self.d.rounded_rectangle(self._c(box), radius=r * self.s, **kw)
        else:
            self.d.rectangle(self._c(box), **kw)

    def poly(self, pts, **kw):
        self._w(kw); self.d.polygon(self._c(pts), **kw)

    def line(self, pts, **kw):
        self._w(kw); self.d.line(self._c(pts), **kw)

    def arc(self, box, a, b, **kw):
        self._w(kw); self.d.arc(self._c(box), a, b, **kw)

    def _w(self, kw):
        if "width" in kw:
            kw["width"] = max(1, int(kw["width"] * self.s))


def hi(w, h, fn, mode="RGBA", bg=(0, 0, 0, 0), s=2):
    img = Image.new(mode, (w * s, h * s), bg)
    fn(SD(img, s), img)
    return img.resize((w, h), Image.LANCZOS)


def vgrad(w, h, top, bot):
    y = np.linspace(0, 1, h)[:, None, None]
    a = np.array(top, float)[None, None] * (1 - y) + np.array(bot, float)[None, None] * y
    return Image.fromarray(np.broadcast_to(a, (h, w, 3)).astype(np.uint8))


def radial(w, h, cx, cy, r, color, alpha):
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
    a = (np.clip(1 - d, 0, 1) ** 2 * alpha).astype(np.uint8)
    img = np.zeros((h, w, 4), np.uint8)
    img[..., :3] = color
    img[..., 3] = a
    return Image.fromarray(img, "RGBA")


def tint(img, rgb, k):
    a = np.asarray(img, float)
    a = a * (1 - k) + np.array(rgb, float) * k * (a / 255.0 + 0.4)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def paste(base, spr, x, y, alpha=1.0):
    if alpha < 1:
        spr = spr.copy()
        spr.putalpha(spr.getchannel("A").point(lambda v: int(v * alpha)))
    base.alpha_composite(spr, (int(x), int(y))) if base.mode == "RGBA" else base.paste(spr, (int(x), int(y)), spr)


# ---- karakter parçaları ----------------------------------------------------
def girl_front(D, cx, cy, sc=1.0, arm_on_belly=1.0):
    """Ayna yansıması: belden yukarı, yüzsüz sade figür."""
    def P(x, y):
        return (cx + x * sc, cy + y * sc)
    # saç arka
    D.ellipse((*P(-120, -150), *P(120, 150)), fill=HAIR)
    D.ellipse((*P(-55, -215), *P(55, -125)), fill=HAIR)  # topuz
    # boyun
    D.rect((*P(-36, 70), *P(36, 160)), fill=SKIN_D)
    # gövde
    D.poly([P(-210, 175), P(210, 175), P(240, 260), P(215, 760), P(-215, 760), P(-240, 260)], fill=SWEAT)
    D.ellipse((*P(-75, 140), *P(75, 205)), fill=SWEAT_D)  # yaka
    D.ellipse((*P(-62, 140), *P(62, 190)), fill=SKIN_D)
    # sol kol (aşağıda)
    D.poly([P(-210, 180), P(-260, 260), P(-270, 700), P(-205, 705), P(-195, 300)], fill=SWEAT_D)
    D.ellipse((*P(-275, 690), *P(-200, 770)), fill=SKIN)
    # sağ kol: dirsek, el karına
    hx, hy = -20 + 220 * (1 - arm_on_belly), 560 + 140 * (1 - arm_on_belly)
    D.poly([P(205, 180), P(262, 260), P(275, 560), P(215, 600), P(195, 300)], fill=SWEAT_D)
    D.poly([P(270, 530), P(220, 600), P(hx + 40, hy + 45), P(hx + 60, hy - 25)], fill=SWEAT_D)
    D.ellipse((*P(hx - 55, hy - 40), *P(hx + 55, hy + 45)), fill=SKIN)
    # yüz (yüzsüz, hafif aşağı bakış: saç perçemi)
    D.ellipse((*P(-88, -110), *P(88, 110)), fill=SKIN)
    D.poly([P(-95, -40), P(-60, -125), P(40, -130), P(100, -60), P(95, -10), P(20, -80), P(-60, -70)], fill=HAIR)


def foot(left):
    def fn(D, _):
        sole = (20, 60, 150, 300)
        D.ellipse(sole, fill=SKIN)
        D.ellipse((40, 220, 140, 300), fill=SKIN_D + (70,))
        toes = [(30, 18, 34), (68, 12, 26), (98, 20, 22), (122, 34, 18), (142, 52, 15)]
        for x, y, r in toes:
            D.ellipse((x - r, y + 20 - r * 0.2, x + r, y + 20 + r * 1.5), fill=SKIN)
    img = hi(170, 310, fn)
    return img if left else img.transpose(Image.FLIP_LEFT_RIGHT)


def hand_sleeve(angle_deg, length=520):
    """Alttan gelen gri kol + el (sprite, yukarı doğru)."""
    def fn(D, _):
        D.rect((40, 120, 160, length), r=30, fill=SWEAT)
        D.rect((40, 110, 160, 170), r=20, fill=SWEAT_D)
        D.ellipse((45, 10, 155, 150), fill=SKIN)
        D.ellipse((140, 60, 185, 120), fill=SKIN)
    img = hi(200, length, fn)
    return img.rotate(angle_deg, expand=True, resample=Image.BICUBIC)


# ----------------------------------------------------------------------------
# Sahneler: her biri statik katman + zamanla değişen öğeler
# ----------------------------------------------------------------------------
@lru_cache(None)
def S_scale(night):
    def fn(D, img):
        tile = (196, 206, 214) if not night else (150, 170, 168)
        D.rect((0, 0, W, H), fill=tile)
        for x in range(0, W + 1, 270):
            D.line(((x, 0), (x, H)), fill=(0, 0, 0, 30), width=4)
        for y in range(0, H + 1, 270):
            D.line(((0, y), (W, y)), fill=(0, 0, 0, 30), width=4)
        D.rect((150, 790, 930, 1630), r=100, fill=(0, 0, 0, 50))  # gölge
        D.rect((160, 760, 920, 1590), r=100, fill=(238, 240, 243))
        D.rect((180, 780, 900, 1570), r=88, outline=(210, 214, 220), width=5)
        D.rect((420, 830, 660, 920), r=22, fill=(32, 36, 42))
    base = hi(W, H, fn, "RGB", (0, 0, 0))
    if night:
        base = tint(base, (60, 110, 120), 0.35)
    return base


def scale_display(level):
    """Rakam yerine okunamaz, bulanık parıltı."""
    g = Image.new("RGBA", (300, 160), (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    for i in range(3):
        d.rounded_rectangle((70 + i * 58, 52, 112 + i * 58, 108), 8, fill=(170, 235, 255, int(230 * level)))
    return g.filter(ImageFilter.GaussianBlur(14))


@lru_cache(None)
def FEET():
    return foot(True), foot(False)


def draw_scale(u, night, dur):
    img = S_scale(night).copy().convert("RGBA")
    land = 1.0 if not night else 1.3
    p = ease((u - 0.15) / (land - 0.15))
    fl, fr = FEET()
    off = (1 - p) * 1100
    paste(img, fl, 330, 1080 + off)
    paste(img, fr, 580, 1080 + off)
    if u > land:
        k = u - land
        lvl = 1.0 if k > 0.6 else (0.4 + 0.6 * (int(k * 8) % 2))
        paste(img, scale_display(lvl), 390, 795)
    if night:  # floresan titremesi
        f = 1 - 0.06 * (math.sin(u * 37) > 0.93)
        img = Image.eval(img, lambda v: int(v * f))
    return img.convert("RGB")


@lru_cache(None)
def S_mirror():
    base = vgrad(W, H, (84, 94, 110), (34, 38, 48)).convert("RGBA")

    def fn(D, img):
        D.rect((150, 230, 930, 1560), r=40, fill=(205, 194, 178))
        D.rect((172, 252, 908, 1538), r=28, fill=(112, 126, 144))
    paste(base, hi(W, H, fn), 0, 0)
    inner = vgrad(736, 1286, (140, 152, 168), (78, 88, 104)).convert("RGBA")
    fig = hi(736, 1286, lambda D, _: girl_front(D, 368, 380, 1.0, 1.0))
    inner.alpha_composite(fig)

    def glare(D, _):
        D.poly([(420, 0), (520, 0), (120, 1286), (20, 1286)], fill=(255, 255, 255, 22))
        D.poly([(600, 0), (640, 0), (240, 1286), (200, 1286)], fill=(255, 255, 255, 14))
    inner.alpha_composite(hi(736, 1286, glare))
    mask = hi(736, 1286, lambda D, _: D.rect((0, 0, 736, 1286), r=28, fill=(255, 255, 255, 255)))
    base.paste(inner, (172, 252), mask)
    base.alpha_composite(radial(W, H, 300, 300, 900, (255, 240, 220), 40))
    return base.convert("RGB")


def plate_sprite():
    def fn(D, _):
        D.ellipse((10, 30, 590, 290), fill=(0, 0, 0, 40))
        D.ellipse((0, 0, 580, 260), fill=(250, 250, 248))
        D.ellipse((40, 20, 540, 240), outline=(225, 225, 222), width=4)
        # simit
        D.ellipse((90, 50, 330, 170), fill=(176, 104, 50))
        D.ellipse((165, 88, 255, 132), fill=(250, 250, 248))
        for i in range(26):
            a = i / 26 * 2 * math.pi
            x, y = 210 + 95 * math.cos(a), 110 + 45 * math.sin(a)
            D.ellipse((x - 4, y - 2, x + 4, y + 3), fill=(245, 225, 170))
        # domates
        for x, y in ((370, 70), (440, 95), (395, 130)):
            D.ellipse((x - 42, y - 26, x + 42, y + 26), fill=(214, 60, 48))
            D.ellipse((x - 28, y - 16, x + 28, y + 16), fill=(236, 110, 90))
        # peynir
        D.poly([(170, 175), (310, 160), (330, 215), (190, 230)], fill=(246, 244, 232), outline=(220, 216, 200))
        # zeytin
        for x, y in ((420, 175), (460, 190), (380, 195)):
            D.ellipse((x - 16, y - 11, x + 16, y + 11), fill=(40, 34, 36))
    return hi(600, 300, fn)


def tea_glass():
    def fn(D, _):
        D.ellipse((0, 280, 200, 330), fill=(240, 240, 236))
        D.poly([(55, 40), (145, 40), (125, 150), (150, 290), (50, 290), (75, 150)], fill=(255, 255, 255, 70),
               outline=(255, 255, 255, 150))
        D.poly([(62, 80), (138, 80), (122, 150), (143, 285), (57, 285), (78, 150)], fill=(150, 42, 22, 230))
    return hi(200, 340, fn)


@lru_cache(None)
def S_kitchen(with_mom):
    base = vgrad(W, H, (220, 186, 146), (150, 112, 82)).convert("RGBA")

    def fn(D, _):
        D.rect((110, 200, 590, 860), fill=(248, 238, 214))
        D.rect((110, 200, 590, 860), outline=(250, 250, 250), width=22)
        D.line(((350, 200), (350, 860)), fill=(250, 250, 250), width=16)
        D.line(((110, 530), (590, 530)), fill=(250, 250, 250), width=16)
        D.poly([(110, 860), (590, 860), (900, 1400), (0, 1400), (0, 1150)], fill=(255, 236, 190, 45))
        if with_mom:
            D.ellipse((640, 600, 900, 900), fill=(70, 50, 44))
            D.ellipse((670, 640, 870, 880), fill=SKIN_D)
            D.ellipse((660, 600, 880, 720), fill=(70, 50, 44))
            D.poly([(560, 940), (960, 940), (1040, 1180), (480, 1180)], fill=(124, 52, 60))
            D.rect((720, 870, 820, 960), fill=SKIN_D)
        D.rect((0, 1150, W, H), fill=(238, 230, 216))
        for x in range(-40, W, 90):
            D.line(((x, 1150), (x + 30, H)), fill=(200, 90, 80, 40), width=8)
        for y in range(1180, H, 90):
            D.line(((0, y), (W, y)), fill=(200, 90, 80, 40), width=8)
        D.rect((0, 1140, W, 1160), fill=(0, 0, 0, 40))
    layer = hi(W, H, fn)
    if with_mom:
        mom = layer.crop((0, 0, W, 1145)).filter(ImageFilter.GaussianBlur(5))
        layer.paste(mom, (0, 0))
    base.alpha_composite(layer)
    base.alpha_composite(radial(W, H, 350, 520, 1000, (255, 230, 180), 70))
    g = tea_glass()
    paste(base, g, 140, 1040)
    paste(base, g, 760, 1010)
    return base.convert("RGB")


def steam(img, x, y, u, n=3, h=260, a=55):
    d = ImageDraw.Draw(img, "RGBA")
    for i in range(n):
        pts = []
        for j in range(40):
            yy = y - j * h / 40
            ph = u * 2.2 + i * 2 + j * 0.18
            pts.append((x + i * 22 - 22 + 18 * math.sin(ph), yy))
        d.line(pts, fill=(255, 255, 255, a - i * 10), width=6)


@lru_cache(None)
def PLATE():
    return plate_sprite()


@lru_cache(None)
def MOM_HAND():
    def fn(D, _):
        D.rect((120, 40, 600, 150), r=40, fill=(124, 52, 60))
        D.ellipse((40, 30, 170, 160), fill=SKIN_D)
    return hi(600, 200, fn)


@lru_cache(None)
def MY_HAND():
    return hand_sleeve(0, 620)


def draw_kitchen(u, dur):
    img = S_kitchen(False).copy().convert("RGBA")
    p = ease(u / 1.3)
    x = 240 + (1 - p) * 900
    paste(img, PLATE(), x, 1300)
    hp = ease((u - 1.3) / 0.9)
    paste(img, MOM_HAND(), x + 500 + hp * 600, 1320)
    steam(img, 240, 1060, u)
    steam(img, 860, 1030, u + 1)
    return img.convert("RGB")


def draw_breakfast(u, dur):
    img = S_kitchen(True).copy().convert("RGBA")
    push_t = AUDIO["d3"][0] - SCENES[3][1] - 0.2
    p = ease((u - push_t) / 1.2)
    plate = PLATE()
    sc = 1 - 0.18 * p
    pl = plate.resize((int(600 * sc), int(300 * sc)), Image.LANCZOS)
    px, py = 240 + 60 * p + 300 * (1 - sc), 1420 - 260 * p
    paste(img, pl, px, py)
    hand = MY_HAND()
    hy = py + 200 if p < 1 else py + 200 + ease((u - push_t - 1.4) / 0.8) * 600
    paste(img, hand, 430, hy + 40 * (1 - ease(u / 0.6)))
    steam(img, 240, 1060, u)
    steam(img, 860, 1030, u + 1)
    return img.convert("RGB")


# ---- kafe ------------------------------------------------------------------
@lru_cache(None)
def S_cafe_top():
    base = vgrad(W, H, (150, 104, 70), (120, 80, 52)).convert("RGBA")
    rng = np.random.default_rng(3)

    def fn(D, _):
        for i in range(60):
            y = rng.uniform(0, H)
            D.line([(x, y + 14 * math.sin(x / 140 + i)) for x in range(0, W + 40, 40)],
                   fill=(90, 58, 36, 50), width=3)
        # telefonlar, su bardakları
        D.rect((80, 1000, 210, 1250), r=22, fill=(30, 30, 34))
        D.ellipse((860, 1060, 980, 1180), fill=(220, 235, 240, 120), outline=(255, 255, 255, 140), width=4)
        D.ellipse((120, 420, 230, 530), fill=(220, 235, 240, 120), outline=(255, 255, 255, 140), width=4)
    base.alpha_composite(hi(W, H, fn))
    base.alpha_composite(radial(W, H, 900, 200, 1300, (255, 230, 190), 60))
    return base.convert("RGB")


@lru_cache(None)
def CAFE_ITEMS():
    def pasta(D, _):
        D.ellipse((10, 14, 370, 374), fill=(0, 0, 0, 45))
        D.ellipse((0, 0, 360, 360), fill=(250, 250, 248))
        rng = np.random.default_rng(5)
        for _ in range(70):
            cx, cy = rng.uniform(110, 250, 2)
            r = rng.uniform(20, 55)
            a = rng.uniform(0, 360)
            D.arc((cx - r, cy - r, cx + r, cy + r), a, a + 160, fill=(236, 200, 110), width=9)
        D.ellipse((140, 140, 230, 220), fill=(200, 60, 40, 200))
        D.rect((250, 250, 270, 380), r=8, fill=(190, 190, 196))

    def toast(D, _):
        D.ellipse((10, 14, 370, 374), fill=(0, 0, 0, 45))
        D.ellipse((0, 0, 360, 360), fill=(250, 250, 248))
        D.poly([(70, 110), (230, 80), (180, 260)], fill=(214, 164, 96), outline=(160, 104, 50), width=10)
        D.poly([(150, 290), (300, 140), (290, 300)], fill=(214, 164, 96), outline=(160, 104, 50), width=10)
        D.ellipse((90, 260, 140, 310), fill=(110, 160, 70))

    def coffee(D, _):
        D.ellipse((10, 14, 260, 264), fill=(0, 0, 0, 45))
        D.ellipse((0, 0, 250, 250), fill=(246, 246, 244))
        D.ellipse((50, 50, 200, 200), fill=(255, 255, 255), outline=(220, 220, 220), width=4)
        D.ellipse((66, 66, 184, 184), fill=(62, 40, 28))
        D.rect((195, 105, 250, 145), r=18, fill=(255, 255, 255))
    return hi(380, 380, pasta), hi(380, 380, toast), hi(270, 270, coffee)


def pop(img, spr, x, y, u, t0):
    p = ease((u - t0) / 0.45)
    if p <= 0:
        return
    sc = 0.85 + 0.15 * p
    s = spr.resize((int(spr.width * sc), int(spr.height * sc)), Image.LANCZOS)
    paste(img, s, x + (spr.width - s.width) / 2, y + (spr.height - s.height) / 2, p)


def draw_cafe_top(u, dur):
    img = S_cafe_top().copy().convert("RGBA")
    pa, to, co = CAFE_ITEMS()
    pop(img, pa, 90, 450, u, 0.4)
    pop(img, to, 600, 520, u, 1.3)
    pop(img, co, 405, 1230, u, 2.6)
    if u > 2.6:
        steam(img, 540, 1330, u, 3, 200, int(50 * ease((u - 2.6) / 1)))
    return img.convert("RGB")


@lru_cache(None)
def S_cafe_cup():
    base = vgrad(W, H, (110, 86, 66), (60, 44, 34)).convert("RGBA")
    rng = np.random.default_rng(9)

    def bokeh(D, _):
        for _ in range(26):
            x, y, r = rng.uniform(0, W), rng.uniform(80, 900), rng.uniform(30, 90)
            D.ellipse((x - r, y - r, x + r, y + r), fill=(255, 214, 160, int(rng.uniform(25, 70))))
        # karşıdaki arkadaş (Ece), bulanık
        D.ellipse((380, 380, 700, 700), fill=(120, 74, 50))
        D.ellipse((420, 420, 660, 690), fill=SKIN_D)
        D.poly([(250, 760), (830, 760), (930, 1150), (150, 1150)], fill=(84, 118, 140))
        D.rect((480, 660, 600, 780), fill=SKIN_D)
    lay = hi(W, H, bokeh).filter(ImageFilter.GaussianBlur(10))
    base.alpha_composite(lay)

    def table(D, _):
        D.rect((0, 1060, W, H), fill=(140, 98, 66))
        D.rect((0, 1050, W, 1075), fill=(90, 60, 40))
        # Ece'nin bıraktığı çatal ve tabağı (bulanık değil, masa önünde)
        D.ellipse((620, 1100, 980, 1190), fill=(240, 238, 232))
        D.rect((640, 1150, 900, 1162), r=6, fill=(190, 190, 196))
    base.alpha_composite(hi(W, H, table))
    return base.convert("RGB")


@lru_cache(None)
def CUP_HANDS():
    def fn(D, _):
        D.ellipse((290, 1330, 790, 1420), fill=(0, 0, 0, 60))
        D.rect((350, 1050, 730, 1380), r=50, fill=(248, 246, 242))
        D.ellipse((350, 1010, 730, 1100), fill=(236, 234, 230))
        D.ellipse((375, 1025, 705, 1088), fill=(70, 44, 30))
        # eller
        D.poly([(0, 1500), (0, 1900), (260, 1900), (380, 1330)], fill=SWEAT)
        D.ellipse((280, 1150, 450, 1380), fill=SKIN)
        D.ellipse((330, 1120, 420, 1220), fill=SKIN)
        D.poly([(W, 1500), (W, 1900), (820, 1900), (700, 1330)], fill=SWEAT)
        D.ellipse((630, 1150, 800, 1380), fill=SKIN)
        D.ellipse((660, 1120, 750, 1220), fill=SKIN)
        D.rect((250, 1380, 420, 1470), r=30, fill=SWEAT_D)
        D.rect((660, 1380, 830, 1470), r=30, fill=SWEAT_D)
    return hi(W, H, fn)


def draw_cafe_cup(u, dur):
    img = S_cafe_cup().copy().convert("RGBA")
    dy = 8 * math.sin(u * 1.3)
    paste(img, CUP_HANDS(), 0, dy)
    steam(img, 540, 1000 + dy, u, 3, 300, 45)
    return img.convert("RGB")


# ---- telefon ---------------------------------------------------------------
def tiny_person(D, x, y, s, hair, shirt, smile=True):
    D.ellipse((x - 26 * s, y - 30 * s, x + 26 * s, y + 26 * s), fill=hair)
    D.ellipse((x - 20 * s, y - 22 * s, x + 20 * s, y + 24 * s), fill=SKIN)
    D.poly([(x - 26 * s, y - 6 * s), (x - 18 * s, y - 28 * s), (x + 20 * s, y - 28 * s), (x + 26 * s, y - 4 * s),
            (x + 10 * s, y - 18 * s), (x - 10 * s, y - 18 * s)], fill=hair)
    D.ellipse((x - 9 * s, y - 2 * s, x - 4 * s, y + 3 * s), fill=(40, 30, 30))
    D.ellipse((x + 4 * s, y - 2 * s, x + 9 * s, y + 3 * s), fill=(40, 30, 30))
    if smile:
        D.arc((x - 10 * s, y + 2 * s, x + 10 * s, y + 16 * s), 15, 165, fill=(150, 60, 60), width=max(1, 2 * s))
    D.rect((x - 34 * s, y + 30 * s, x + 34 * s, y + 120 * s), r=20 * s, fill=shirt)
    D.rect((x - 8 * s, y + 20 * s, x + 8 * s, y + 34 * s), fill=SKIN_D)


def photo(kind, size):
    s = size / 200

    def fn(D, _):
        if kind == "beach":
            D.rect((0, 0, 200 * s, 110 * s), fill=(140, 200, 236))
            D.rect((0, 100 * s, 200 * s, 140 * s), fill=(60, 140, 190))
            D.rect((0, 140 * s, 200 * s, 200 * s), fill=(236, 214, 160))
            D.ellipse((150 * s, 14 * s, 186 * s, 50 * s), fill=(255, 236, 150))
            tiny_person(D, 70 * s, 95 * s, s, HAIR, (240, 120, 110))
            tiny_person(D, 132 * s, 98 * s, s, (150, 100, 60), (90, 170, 160))
        elif kind == "cake":
            D.rect((0, 0, 200 * s, 200 * s), fill=(80, 50, 70))
            D.rect((40 * s, 100 * s, 160 * s, 170 * s), r=10 * s, fill=(246, 186, 200))
            D.rect((40 * s, 100 * s, 160 * s, 118 * s), fill=(255, 240, 244))
            for i in range(5):
                x = 58 * s + i * 21 * s
                D.rect((x, 70 * s, x + 6 * s, 100 * s), fill=(250, 250, 220))
                D.ellipse((x - 2 * s, 56 * s, x + 8 * s, 72 * s), fill=(255, 200, 80))
            D.ellipse((40 * s, 20 * s, 70 * s, 50 * s), fill=(255, 230, 150, 120))
        elif kind == "grad":
            D.rect((0, 0, 200 * s, 200 * s), fill=(110, 150, 200))
            D.rect((0, 150 * s, 200 * s, 200 * s), fill=(90, 150, 90))
            for i, x in enumerate((50, 100, 150)):
                tiny_person(D, x * s, 90 * s, s * 0.8, HAIR if i == 1 else (120, 80, 50), (40, 40, 70))
                D.poly([((x - 26) * s, 68 * s), (x * s, 58 * s), ((x + 26) * s, 68 * s), (x * s, 78 * s)],
                       fill=(20, 20, 30))
        elif kind == "friends":
            D.rect((0, 0, 200 * s, 200 * s), fill=(244, 200, 150))
            tiny_person(D, 50 * s, 90 * s, s * 0.85, (150, 100, 60), (200, 90, 90))
            tiny_person(D, 100 * s, 84 * s, s * 0.85, HAIR, (250, 250, 250))
            tiny_person(D, 150 * s, 90 * s, s * 0.85, (40, 30, 30), (90, 120, 200))
        elif kind == "selfie":
            D.rect((0, 0, 200 * s, 200 * s), fill=(170, 210, 190))
            tiny_person(D, 100 * s, 90 * s, s * 1.6, HAIR, (240, 120, 110))
        elif kind == "city":
            D.rect((0, 0, 200 * s, 200 * s), fill=(250, 190, 140))
            for i, h_ in enumerate((90, 130, 70, 150, 100, 120)):
                D.rect((i * 34 * s, (200 - h_) * s, (i * 34 + 30) * s, 200 * s), fill=(90, 70, 100))
    return hi(size, size, fn, "RGB", (0, 0, 0))


SCR = (290, 410, 790, 1430)  # telefon ekranı (x0,y0,x1,y1) => 500x1020


@lru_cache(None)
def GALLERY():
    kinds = ["friends", "cake", "beach", "city", "selfie", "grad"]
    g = Image.new("RGB", (500, 2400), (8, 8, 10))
    d = ImageDraw.Draw(g)
    d.text((24, 40), "Fotoğraflar", font=ImageFont.truetype(F_BOLD, 40), fill=(240, 240, 240))
    d.text((24, 92), "2021", font=ImageFont.truetype(F_REG, 26), fill=(150, 150, 150))
    for i in range(36):
        r, c = divmod(i, 3)
        g.paste(photo(kinds[(i * 5 + r) % 6], 162), (4 + c * 166, 140 + r * 166))
    return g


@lru_cache(None)
def BIG_BEACH():
    return photo("beach", 1500)


@lru_cache(None)
def S_phone():
    base = vgrad(W, H, (16, 18, 30), (6, 7, 12)).convert("RGBA")

    def fn(D, _):
        for i in range(7):
            y = 1300 + i * 110
            D.line([(x, y + 40 * math.sin(x / 200 + i)) for x in range(0, W + 40, 40)], fill=(40, 48, 72, 120),
                   width=30)
    base.alpha_composite(hi(W, H, fn))
    base.alpha_composite(radial(W, H, 540, 920, 900, (170, 200, 255), 70))

    def ph(D, _):
        D.rect((262, 370, 818, 1470), r=60, fill=(14, 14, 16))
        D.rect((268, 376, 812, 1464), r=56, outline=(60, 60, 66), width=4)
    base.alpha_composite(hi(W, H, ph))
    return base.convert("RGB")


@lru_cache(None)
def PHONE_HANDS():
    def fn(D, _):
        D.poly([(0, 1450), (300, 1260), (420, 1560), (160, H), (0, H)], fill=(70, 74, 84))
        D.poly([(W, 1450), (780, 1260), (660, 1560), (920, H), (W, H)], fill=(70, 74, 84))
        D.ellipse((210, 1180, 330, 1420), fill=(132, 108, 100))
        D.ellipse((750, 1180, 870, 1420), fill=(132, 108, 100))
        D.ellipse((236, 980, 300, 1120), fill=(132, 108, 100))
        D.ellipse((780, 1000, 844, 1140), fill=(132, 108, 100))
    return hi(W, H, fn)


def draw_phone(u, dur):
    img = S_phone().copy()
    sw, sh = SCR[2] - SCR[0], SCR[3] - SCR[1]
    scr = Image.new("RGB", (sw, sh), (8, 8, 10))
    t_open, t_zoom = 3.6, 6.2
    if u < t_open + 0.6:
        off = int(ease(u / t_open) * 520)
        scr.paste(GALLERY().crop((0, off, sw, off + sh)), (0, 0))
    # tıklanan küçük resim: 3. satır ortası => galeride (170,140+2*166+520)
    if u >= t_open:
        p = ease((u - t_open) / 0.6)
        x0, y0, s0 = 170, 140 + 166 * 4 - 520, 162
        x1, y1, s1 = 0, (sh - sw) // 2, sw
        x, y, s = x0 + (x1 - x0) * p, y0 + (y1 - y0) * p, s0 + (s1 - s0) * p
        if p >= 1:
            scr = Image.new("RGB", (sw, sh), (0, 0, 0))
        z = 1 + 2.4 * ease((u - t_zoom) / 4.0)
        big = BIG_BEACH()
        cw = 1500 / z
        cx, cy = 70 / 200 * 1500, 100 / 200 * 1500  # yüzüne doğru
        cx = 750 + (cx - 750) * min(1, (z - 1) / 1.4)
        cy = 750 + (cy - 750) * min(1, (z - 1) / 1.4)
        box = (cx - cw / 2, cy - cw / 2, cx + cw / 2, cy + cw / 2)
        box = (max(0, min(box[0], 1500 - cw)), max(0, min(box[1], 1500 - cw)))
        crop = big.crop((int(box[0]), int(box[1]), int(box[0] + cw), int(box[1] + cw))).resize((int(s), int(s)),
                                                                                                Image.LANCZOS)
        scr.paste(crop, (int(x), int(y)))
        if t_zoom - 0.2 < u < t_zoom + 4.2:  # iki parmak
            d = ImageDraw.Draw(scr, "RGBA")
            sp = 40 + 120 * ease((u - t_zoom) / 4.0)
            for sgn in (-1, 1):
                fx, fy = sw / 2 + sgn * sp * 0.7, sh / 2 + sgn * sp * 0.7
                d.ellipse((fx - 34, fy - 34, fx + 34, fy + 34), fill=(255, 255, 255, 60),
                          outline=(255, 255, 255, 120), width=3)
    mask = hi(sw, sh, lambda D, _: D.rect((0, 0, sw, sh), r=46, fill=(255, 255, 255, 255)))
    img.paste(scr, SCR[:2], mask)
    img = img.convert("RGBA")
    img.alpha_composite(PHONE_HANDS())
    return img.convert("RGB")


# ---- yatak (üstten) --------------------------------------------------------
@lru_cache(None)
def S_bed():
    base = vgrad(W, H, (10, 12, 20), (4, 5, 9)).convert("RGBA")

    def fn(D, _):
        D.rect((120, 180, 960, 1800), r=40, fill=(34, 44, 68))
        D.rect((200, 240, 880, 560), r=80, fill=(52, 64, 92))
        # saç yastıkta dağılmış
        D.ellipse((380, 330, 700, 640), fill=HAIR)
        D.ellipse((430, 380, 650, 620), fill=(150, 126, 120))
        D.poly([(430, 420), (470, 370), (610, 370), (650, 430), (600, 400), (480, 400)], fill=HAIR)
        D.rect((500, 600, 580, 660), fill=(120, 100, 96))
        # gövde
        D.rect((330, 640, 750, 1150), r=90, fill=(84, 88, 98))
        D.rect((270, 680, 360, 1120), r=45, fill=(74, 78, 88))
        D.rect((720, 680, 810, 1120), r=45, fill=(74, 78, 88))
        D.ellipse((300, 1080, 380, 1160), fill=(150, 126, 120))
        D.ellipse((700, 1080, 780, 1160), fill=(150, 126, 120))
        # battaniye
        D.rect((150, 1100, 930, 1780), r=40, fill=(26, 34, 56))
        for i in range(5):
            D.line([(x, 1200 + i * 120 + 30 * math.sin(x / 120 + i)) for x in range(160, 930, 20)],
                   fill=(18, 24, 40), width=10)
        # göğüste telefon
        D.rect((480, 820, 600, 1000), r=16, fill=(16, 16, 20))
    base.alpha_composite(hi(W, H, fn))
    return base.convert("RGB")


def draw_bed(u, dur):
    img = S_bed().copy().convert("RGBA")
    g = 1 - ease((u - 1.2) / 2.0)
    if g > 0:
        img.alpha_composite(radial(W, H, 540, 900, 520, (180, 210, 255), int(110 * g)))
        d = ImageDraw.Draw(img, "RGBA")
        d.rounded_rectangle((490, 832, 590, 988), 10, fill=(180, 210, 255, int(200 * g)))
    return img.convert("RGB")


# ---- final: yüz ------------------------------------------------------------
@lru_cache(None)
def S_face():
    base = vgrad(W, H, (40, 44, 54), (10, 11, 14)).convert("RGBA")

    def fn(D, _):
        D.rect((40, 120, 1040, 1800), r=40, outline=(150, 142, 130), width=24)
        D.ellipse((250, 380, 830, 1330), fill=HAIR)
        D.poly([(200, 1700), (880, 1700), (960, H), (120, H)], fill=SWEAT_D)
        D.rect((470, 1170, 610, 1400), fill=SKIN_D)
        D.ellipse((300, 470, 780, 1240), fill=SKIN)
        D.poly([(300, 830), (300, 520), (420, 400), (640, 390), (790, 520), (785, 760), (700, 560), (520, 560),
                (380, 640)], fill=HAIR)
        D.poly([(150, 1500), (930, 1500), (1000, H), (80, H)], fill=SWEAT)
        D.ellipse((420, 1430, 660, 1560), fill=SKIN_D)
        # kaşlar, burun, ağız
        D.arc((375, 760, 505, 820), 200, 330, fill=(80, 56, 46), width=10)
        D.arc((575, 760, 705, 820), 210, 340, fill=(80, 56, 46), width=10)
        D.line(((540, 900), (528, 1010), (552, 1018)), fill=SKIN_D, width=8)
        D.arc((490, 1070, 590, 1110), 20, 160, fill=(170, 100, 96), width=8)
    base.alpha_composite(hi(W, H, fn))
    # soğuk yan ışık
    sh = np.zeros((H, W, 4), np.uint8)
    sh[..., 3] = np.clip((np.linspace(0, 1, W) - 0.45) * 160, 0, 90).astype(np.uint8)[None, :]
    base.alpha_composite(Image.fromarray(sh, "RGBA"))
    base.alpha_composite(radial(W, H, 300, 500, 900, (200, 220, 255), 40))
    return base.convert("RGB")


def draw_face(u, dur):
    img = S_face().copy().convert("RGBA")
    d = SD(img, 1)
    blink = 0.9 < u < 1.05 or (dur - 4.6) < u < (dur - 4.45)
    for ex in (440, 640):
        if blink:
            d.arc((ex - 45, 840, ex + 45, 880), 10, 170, fill=(60, 40, 36), width=6)
        else:
            d.ellipse((ex - 46, 838, ex + 46, 882), fill=(250, 246, 242))
            d.ellipse((ex - 22, 836, ex + 22, 882), fill=(66, 44, 34))
            d.ellipse((ex - 10, 848, ex + 10, 870), fill=(20, 14, 12))
            d.ellipse((ex - 2, 844, ex + 8, 854), fill=(255, 255, 255, 220))
            d.arc((ex - 50, 826, ex + 50, 880), 190, 350, fill=(60, 40, 36), width=7)
    return img.convert("RGB")


def draw_card(u, dur):
    return Image.new("RGB", (W, H), (6, 6, 8))


DRAW = {
    "hook": lambda u, d: draw_scale(u, False, d),
    "mirror": lambda u, d: S_mirror(),
    "kitchen": draw_kitchen,
    "breakfast": draw_breakfast,
    "cafe_top": draw_cafe_top,
    "cafe_cup": draw_cafe_cup,
    "scale_night": lambda u, d: draw_scale(u, True, d),
    "phone": draw_phone,
    "bed": draw_bed,
    "face": draw_face,
    "card": draw_card,
}
# kamera: (başlangıç zoom, bitiş zoom, odak x, odak y)
CAM = {
    "hook": (1.0, 1.08, 540, 1100), "mirror": (1.0, 1.10, 540, 800), "kitchen": (1.06, 1.0, 540, 1200),
    "breakfast": (1.0, 1.07, 540, 1300), "cafe_top": (1.12, 1.0, 540, 960), "cafe_cup": (1.0, 1.08, 540, 1150),
    "scale_night": (1.0, 1.10, 540, 1100), "phone": (1.0, 1.12, 540, 920), "bed": (1.30, 1.0, 540, 900),
    "face": (1.0, 1.55, 540, 870), "card": (1.0, 1.0, 540, 960),
}


# ----------------------------------------------------------------------------
# Kare oluşturma
# ----------------------------------------------------------------------------
@lru_cache(None)
def VIGNETTE():
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.72)) ** 2)
    return np.clip(1.12 - d * 0.55, 0.45, 1.0)[..., None].astype(np.float32)


@lru_cache(None)
def FONTS():
    return (ImageFont.truetype(F_BOLD, 56), ImageFont.truetype(F_BI, 56), ImageFont.truetype(F_BOLD, 72),
            ImageFont.truetype(F_BOLD, 58), ImageFont.truetype(F_REG, 32))


def center_text(d, y, txt, font, fill, stroke=0, sp=14):
    bb = d.multiline_textbbox((0, 0), txt, font=font, spacing=sp, align="center", stroke_width=stroke)
    d.multiline_text(((W - (bb[2] - bb[0])) / 2, y), txt, font=font, fill=fill, spacing=sp, align="center",
                     stroke_width=stroke, stroke_fill=(0, 0, 0, fill[3] if len(fill) > 3 else 255))
    return bb[3] - bb[1]


def render(fi):
    t = fi / FPS
    si = next((i for i, s in enumerate(SCENES) if s[1] <= t < s[2]), len(SCENES) - 1)
    name, a, b = SCENES[si]
    u, dur = t - a, b - a
    img = DRAW[name](u, dur)
    z0, z1, fx, fy = CAM[name]
    z = z0 + (z1 - z0) * ease(u / dur) if dur > 0 else z0
    if z != 1.0:
        cw, ch = W / z, H / z
        x0 = clamp(fx - cw / 2, 0, W - cw)
        y0 = clamp(fy - ch / 2, 0, H - ch)
        img = img.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))
    # renk/ton + kenar karartma + gren + geçiş
    arr = np.asarray(img, np.float32)
    arr = arr * VIGNETTE()
    fade = 1.0
    if name != "hook":
        fade = min(fade, ease((t - a) / 0.3))
    if name != "card":
        fade = min(fade, ease((b - t) / 0.3)) if si < len(SCENES) - 1 else fade
    rng = np.random.default_rng(fi)
    arr = arr * fade + rng.normal(0, 5, (H // 3, W // 3, 1)).astype(np.float32).repeat(3, 0).repeat(3, 1)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    d = ImageDraw.Draw(img, "RGBA")
    f_sub, f_dlg, f_hook, f_card, f_small = FONTS()
    if name == "hook":
        al = int(255 * ease((t - 0.1) / 0.35))
        center_text(d, 300, "“Biraz daha kilo verirsem\nkendimi seveceğim.”", f_hook, (255, 255, 255, al), 4, 20)
    if name == "card":
        al = int(255 * ease((t - a) / 0.8))
        center_text(d, 620, "Yemekle, kilonla ve bedeninle\nkurduğun ilişki hayatını\nyönetmeye başladıysa,\n\n"
                    "bunu tek başına çözmek\nzorunda değilsin.", f_card, (255, 255, 255, al), 0, 18)
        al2 = int(255 * ease((t - a - 0.6) / 0.8))
        center_text(d, 1290, "Anoreksiya nervoza tedavi gerektiren\nciddi bir yeme bozukluğudur.\n"
                    "Profesyonel destek almak önemlidir.", f_small, (190, 190, 196, al2), 0, 10)
    for sa, sb, txt, dlg in SUBS:
        if sa <= t < sb:
            al = int(255 * min(1, (t - sa) / 0.12, (sb - t) / 0.12))
            col = (255, 228, 168, al) if dlg else (255, 255, 255, al)
            center_text(d, 1330, txt, f_dlg if dlg else f_sub, col, 4, 12)
    return img.tobytes()


# ----------------------------------------------------------------------------
# Ses: konuşma + müzik + efekt
# ----------------------------------------------------------------------------
SR = 44100


def read_wav(path):
    with wave.open(str(path)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
        if w.getnchannels() == 2:
            x = x.reshape(-1, 2).mean(1)
        return x


def build_audio(path):
    n = int(TOTAL * SR) + SR
    voice = np.zeros(n)
    for k, (a, _b) in AUDIO.items():
        x = read_wav(SES / f"{k}.wav")
        s = int(a * SR)
        voice[s:s + len(x)] += x * 0.95

    music = np.zeros(n)

    def note(freq, start, dur, amp):
        s = int(start * SR)
        L = min(int(dur * SR), n - s)
        tt = np.arange(L) / SR
        env = np.exp(-tt * 1.3) * np.minimum(1, tt / 0.012)
        tone = np.sin(2 * np.pi * freq * tt) + 0.3 * np.sin(4 * np.pi * freq * tt) + 0.1 * np.sin(
            6 * np.pi * freq * tt)
        music[s:s + L] += amp * env * tone

    def hz(m):
        return 440 * 2 ** ((m - 69) / 12)

    chords = [[57, 60, 64], [53, 57, 60], [48, 55, 64], [55, 59, 62]]
    beat = 60 / 62
    stop = AUDIO["vo5"][1] + 0.1
    note(hz(69), SCENES[1][1], 4, 0.16)
    tt = SCENES[1][1] + 1.0
    i = 0
    while tt < stop:
        c = chords[(i // 4) % 4]
        if i % 4 == 0:
            note(hz(c[0] - 12), tt, 4, 0.10)
        note(hz(c[i % 3] + 12), tt, 2.5, 0.065)
        tt += beat
        i += 1
    note(hz(69), AUDIO["vo6"][0] + 0.2, 6, 0.06)
    for m in (45, 57, 60, 64):
        note(hz(m), CARD_START, 5, 0.06)
    # yankı
    for dl, g in ((0.23, 0.30), (0.41, 0.18), (0.67, 0.10)):
        dd = int(dl * SR)
        music[dd:] += g * music[:-dd]
    music = music / (np.abs(music).max() + 1e-9) * 0.22

    sfx = np.zeros(n)
    for bt in (1.0, SCENES[6][1] + 1.3):
        s = int(bt * SR)
        L = int(0.13 * SR)
        x = np.arange(L) / SR
        sfx[s:s + L] += 0.18 * np.sin(2 * np.pi * 2100 * x) * np.exp(-x * 18)

    # konuşma altında müziği kıs (ducking)
    env = np.abs(voice)
    k = int(0.25 * SR)
    env = np.convolve(env, np.ones(k) / k, mode="same")
    duck = 1 - 0.55 * np.clip(env * 12, 0, 1)
    mix = voice + music * duck + sfx
    fo = int(1.5 * SR)
    end_i = int(TOTAL * SR)
    mix = mix[:end_i]
    mix[-fo:] *= np.linspace(1, 0, fo)
    mix = mix / max(1.0, np.abs(mix).max() / 0.95)
    pcm = (mix * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(np.repeat(pcm[:, None], 2, 1).tobytes())


def main():
    print("Toplam süre:", TOTAL)
    for s in SCENES:
        print(f"  {s[0]:<12} {s[1]:6.2f} → {s[2]:6.2f}")
    write_srt()
    wav = HERE / "_mix.wav"
    build_audio(wav)
    nframes = int(round(TOTAL * FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", str(wav), "-c:v", "libx264", "-preset", "slow", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(OUT)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool() as pool:
        for i, fr in enumerate(pool.imap(render, range(nframes), chunksize=8)):
            proc.stdin.write(fr)
            if i % 240 == 0:
                print(f"  kare {i}/{nframes}", flush=True)
    proc.stdin.close()
    proc.wait()
    wav.unlink(missing_ok=True)
    print("Hazır:", OUT)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "onizleme":  # python3 video_olustur.py onizleme 1.5 12 ...
        for x in sys.argv[2:]:
            Image.frombytes("RGB", (W, H), render(int(float(x) * FPS))).resize((360, 640)).save(
                HERE / f"_onizleme_{x}.png")
    else:
        main()
