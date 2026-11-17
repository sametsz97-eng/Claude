import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops, ImageOps

W, H = 720, 1280
FONT_BLACK = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
FONT_B = '/usr/share/fonts/opentype/inter/Inter-Bold.otf'
FONT_SB = '/usr/share/fonts/opentype/inter/Inter-SemiBold.otf'
FONT_M = '/usr/share/fonts/opentype/inter/Inter-Medium.otf'
FONT_HAND = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
PHOTO = '/root/.claude/uploads/5b3cb9ae-c2e8-5f6d-b2b9-f7062ebc6a0d/a7fa7f29-image.jpg'


def font(path, size):
    return ImageFont.truetype(path, int(size))


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def back_out(x, s=1.9):
    x = min(max(x, 0.0), 1.0)
    x -= 1
    return x * x * ((s + 1) * x + s) + 1


def lerp(a, b, u):
    return np.asarray(a, float) + (np.asarray(b, float) - np.asarray(a, float)) * u


def dirv(deg):
    r = math.radians(deg)
    return np.array([math.cos(r), math.sin(r)])


def noise(w, h, cell, seed):
    rng = np.random.default_rng(seed)
    n = rng.random((h // cell + 3, w // cell + 3)).astype(np.float32)
    im = Image.fromarray((n * 255).astype(np.uint8)).resize(((w // cell + 3) * cell, (h // cell + 3) * cell), Image.BICUBIC)
    return np.asarray(im.crop((cell, cell, cell + w, cell + h))).astype(np.float32) / 255.0


def to_img(arr):
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def pixup(img, size):
    """PS2-style: upscale a low-res texture with nearest neighbour."""
    return img.resize(size, Image.NEAREST)


# ------------------------------------------------------------------ textures (low-res, pixelated)
def damask(w, h, seed=0, c1=(52, 88, 48), c2=(84, 124, 72), c3=(110, 150, 92)):
    """green damask wallpaper at low resolution (w x h texels)."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    tw, th = 22.0, 30.0
    row = np.floor(yy / th)
    u = ((xx + (row % 2) * tw / 2) % tw) / tw
    v = (yy % th) / th
    dx = np.abs(u - 0.5) * 2
    shape = np.cos(dx * 3.0 + np.sin(v * 2 * np.pi) * 1.4) * np.sin(v * np.pi) - dx * 0.6
    leaf = np.sin(v * 4 * np.pi + dx * 5) * 0.35
    val = shape + leaf
    out = np.zeros((h, w, 3), np.float32) + np.array(c1)
    out[val > 0.15] = c2
    out[val > 0.55] = c3
    out *= (0.9 + 0.2 * noise(w, h, 4, seed))[..., None]
    return to_img(out)


def floral(w, h, seed=1, base=(150, 18, 20), line=(214, 82, 70)):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ts = 34.0
    row = np.floor(yy / ts)
    u = ((xx + (row % 2) * ts / 2) % ts) / ts - 0.5
    v = (yy % ts) / ts - 0.5
    r = np.sqrt(u * u + v * v)
    th = np.arctan2(v, u)
    petal = 0.36 * np.abs(np.cos(2.5 * th)) + 0.05
    ring = np.abs(r - petal) < 0.045
    centre = r < 0.06
    # stems / leaves between flowers
    stem = np.abs(np.sin((u + v) * 9) * 0.08 - (u - v) * 0.2) < 0.02
    out = np.zeros((h, w, 3), np.float32) + np.array(base)
    out[ring | centre | (stem & (r > 0.4))] = line
    out *= (0.88 + 0.22 * noise(w, h, 5, seed))[..., None]
    return to_img(out)


def wood(w, h, seed=2, base=(110, 70, 38), plank=16, vertical=False):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    a, b = (xx, yy) if vertical else (yy, xx)
    rng = np.random.default_rng(seed)
    idx = np.floor(a / plank).astype(int)
    tone = rng.uniform(0.75, 1.15, idx.max() + 2)[idx]
    streak = 0.85 + 0.15 * np.sin(b * 0.35 + np.sin(a * 0.9) * 2 + idx * 3)
    seam = (a % plank) < 1
    out = np.array(base, np.float32)[None, None, :] * (tone * streak)[..., None]
    out[seam] *= 0.55
    out *= (0.9 + 0.2 * noise(w, h, 3, seed))[..., None]
    return to_img(out)


def homography(src_quad, dst_quad):
    """coefficients for PIL PERSPECTIVE: maps output(dst) -> input(src)."""
    A_, B_ = [], []
    for (x, y), (u, v) in zip(dst_quad, src_quad):
        A_.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B_.append(u)
        A_.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B_.append(v)
    return np.linalg.solve(np.array(A_, float), np.array(B_, float))


def warp_onto(dst, tex, quad, resample=Image.NEAREST):
    """warp RGBA/RGB texture onto quad (TL, TR, BR, BL) of dst."""
    tex = tex.convert('RGBA')
    w, h = tex.size
    coeffs = homography([(0, 0), (w, 0), (w, h), (0, h)], quad)
    out = tex.transform(dst.size, Image.PERSPECTIVE, tuple(coeffs), resample=resample)
    m = Image.new('L', dst.size, 0)
    ImageDraw.Draw(m).polygon([tuple(p) for p in quad], fill=255)
    out.putalpha(ImageChops.multiply(out.getchannel('A'), m))
    dst.alpha_composite(out)


# ------------------------------------------------------------------ framed photo (PS2 texture style)
def framed_photo(w, h, seed=5):
    ph = Image.open(PHOTO).convert('RGB')
    ph = ph.crop((130, 30, 560, 600))                  # head + shoulders of the man
    border = int(min(w, h) * 0.13)
    mat = int(border * 0.35)
    iw, ih = w - 2 * (border + mat), h - 2 * (border + mat)
    # low-res + posterize -> PS2 texture look
    lo = ph.resize((max(8, iw // 3), max(8, ih // 3)), Image.BILINEAR)
    lo = ImageOps.posterize(lo, 4)
    lo = lo.resize((iw, ih), Image.NEAREST)
    arr = np.asarray(lo).astype(np.float32)
    arr = arr * np.array([1.02, 0.97, 0.88]) * 0.92          # warm aged print
    lo = to_img(arr)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # wooden/gold frame with bevel (pixelated)
    ft = wood(max(4, w // 4), max(4, h // 4), seed, base=(120, 82, 36), plank=3, vertical=True).resize((w, h), Image.NEAREST)
    fm = Image.new('L', (w, h), 0)
    ImageDraw.Draw(fm).rectangle((0, 0, w - 1, h - 1), fill=255)
    im.paste(ft, (0, 0), fm)
    for i in range(border):
        k = i / border
        col = (int(190 - 90 * k), int(140 - 70 * k), int(60 - 30 * k), 255) if i < border * 0.5 else (int(100 + 60 * k), int(64 + 40 * k), int(28 + 20 * k), 255)
        if i % 3 == 0:
            d.rectangle((i, i, w - 1 - i, h - 1 - i), outline=col)
    d.rectangle((border, border, w - 1 - border, h - 1 - border), fill=(214, 204, 178, 255))   # mat
    im.paste(lo, (border + mat, border + mat))
    # inner shadow + glass glare
    gl = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(gl)
    gd.polygon([(border + mat, border + mat + ih * 0.15), (border + mat + iw * 0.45, border + mat), (border + mat + iw * 0.62, border + mat), (border + mat, border + mat + ih * 0.42)], fill=(255, 255, 255, 34))
    gd.rectangle((border + mat, border + mat, border + mat + iw, border + mat + 3), fill=(0, 0, 0, 70))
    im.alpha_composite(gl)
    return im


def drop_shadow(dst, sprite, pos, off=(8, 10), blur=8, op=0.55, color=(10, 6, 4)):
    sh = Image.new('RGBA', sprite.size, color + (0,))
    sh.putalpha(sprite.getchannel('A').point(lambda v: int(v * op)))
    pad = blur * 3
    big = Image.new('RGBA', (sprite.width + 2 * pad, sprite.height + 2 * pad), (0, 0, 0, 0))
    big.alpha_composite(sh, (pad, pad))
    big = big.filter(ImageFilter.GaussianBlur(blur))
    x, y = int(pos[0] + off[0] - pad), int(pos[1] + off[1] - pad)
    cx, cy = max(0, -x), max(0, -y)
    dst.alpha_composite(big.crop((cx, cy, big.width, big.height)), (x + cx, y + cy))


def layer_shadow(layer, dx, dy, blur, op, color=(10, 6, 4)):
    al = layer.getchannel('A').filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * op))
    sh = Image.new('RGBA', layer.size, color + (0,))
    sh.putalpha(al)
    return ImageChops.offset(sh, dx, dy)


def brighten(layer, gain=1.25, lift=10, tint=(1.0, 0.98, 0.9)):
    a = np.asarray(layer).astype(np.float32)
    a[..., :3] = (a[..., :3] * gain + lift) * np.array(tint)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')


# ------------------------------------------------------------------ city outside the window
def city(w, h, seed=3, px=4):
    lw, lh = w // px, h // px
    yy = np.mgrid[0:lh, 0:lw][0].astype(np.float32) / lh
    top = np.array([150, 110, 190], np.float32)
    mid = np.array([236, 160, 214], np.float32)
    low = np.array([252, 214, 230], np.float32)
    sky = np.where(yy[..., None] < 0.5, top + (mid - top) * (yy[..., None] / 0.5), mid + (low - mid) * ((yy[..., None] - 0.5) / 0.5))
    img = to_img(sky)
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(seed)
    # far towers (bluish), near blocks (salmon)
    for layer, (col, win, n, hmin, hmax) in enumerate([((120, 104, 160), (170, 160, 210), 9, 0.35, 0.75), ((196, 112, 120), (250, 190, 190), 6, 0.20, 0.50)]):
        x = -rng.integers(0, 10)
        while x < lw:
            bw = int(rng.integers(lw // 9, lw // 4))
            bh = int(lh * rng.uniform(hmin, hmax))
            y0 = lh - bh
            d.rectangle((x, y0, x + bw, lh), fill=col)
            for wy in range(y0 + 2, lh - 1, 3):
                for wx in range(x + 2, x + bw - 1, 3):
                    if rng.random() < 0.8:
                        d.point((wx, wy), fill=win)
            x += bw + int(rng.integers(0, 4))
    return pixup(img, (w, h))


# ------------------------------------------------------------------ final PS2-ish grade
def post(img, fi, grade=(1.0, 1.0, 1.0), vign=0.45, gain=1.0):
    arr = np.asarray(img.convert('RGB')).astype(np.float32) / 255.0
    arr = arr * np.array(grade) * gain
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.75)) ** 2)
    arr *= (1 - vign * np.clip(r - 0.3, 0, 1) ** 1.5)[..., None]
    rng = np.random.default_rng(fi)
    arr += rng.standard_normal((H, W, 1)).astype(np.float32) * 0.014
    # mild colour quantisation with dithering (PS2 16-bit-ish feel)
    q = 48.0
    arr = np.floor(arr * q + rng.random((H, W, 1)).astype(np.float32)) / q
    return Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))


# ------------------------------------------------------------------ Istanbul skyline outside the window
def istanbul(w, h, px=4, horizon=0.66, mosques=((0.70, 1.0),), galata=0.18, bridge=0.92, maiden=0.40, seed=3):
    """pixel-art Istanbul at sunset: Bosphorus, mosques with domes + minarets, Galata Tower,
    Bosphorus Bridge, Maiden's Tower. Positions are fractions of the width."""
    lw, lh = w // px, h // px
    hz = int(lh * horizon)
    yy = np.mgrid[0:lh, 0:lw][0].astype(np.float32) / max(1, hz)
    top = np.array([128, 96, 178], np.float32)
    mid = np.array([232, 150, 206], np.float32)
    low = np.array([255, 196, 170], np.float32)
    v = np.clip(yy, 0, 1)[..., None]
    sky = np.where(v < 0.6, top + (mid - top) * (v / 0.6), mid + (low - mid) * ((v - 0.6) / 0.4))
    img = to_img(sky)
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(seed)
    # sun
    sx, sy, sr = lw * 0.58, hz - lh * 0.06, max(3, lw * 0.06)
    d.ellipse((sx - sr, sy - sr, sx + sr, sy + sr), fill=(255, 226, 190))
    U = max(2.0, lw / 24.0)                       # skyline unit
    far = (150, 96, 156)
    near = (52, 28, 72)
    lit = (255, 206, 150)
    # far shore (Asian side): low hills with tiny houses
    pts = [(0, hz)]
    for x in range(0, lw + 4, 4):
        pts.append((x, hz - 2 - U * (0.9 + 0.6 * math.sin(x * 0.11) + 0.4 * math.sin(x * 0.37))))
    pts.append((lw, hz))
    d.polygon(pts, fill=far)
    # Bosphorus Bridge (far, right)
    if bridge is not None:
        bx = lw * bridge
        span = lw * 0.5
        t1, t2 = bx - span / 2, bx + span / 2
        deck = hz - U * 1.6
        th = U * 4.5
        for tx in (t1, t2):
            d.rectangle((tx - 0.6, deck - th, tx + 0.6, deck + U), fill=far)
        d.line([(t1 - span * 0.3, deck), (t2 + span * 0.3, deck)], fill=far, width=1)
        cab = [(t1 + (t2 - t1) * k / 20, deck - th + th * 0.95 * (1 - (2 * k / 20 - 1) ** 2)) for k in range(21)]
        d.line(cab, fill=(150, 98, 152), width=1)
    # water
    for y in range(hz, lh):
        k = (y - hz) / max(1, lh - hz)
        d.line([(0, y), (lw, y)], fill=(int(150 - 60 * k), int(100 - 40 * k), int(170 - 40 * k)))
    for _ in range(int(lw * 0.8)):
        y = rng.integers(hz + 1, lh)
        x = rng.uniform(0, lw)
        L = rng.uniform(2, 6)
        near_sun = abs(x - sx) < lw * 0.12
        d.line([(x, y), (x + L, y)], fill=(255, 210, 190) if near_sun else (190, 140, 200))
    # Maiden's Tower on a rock in the water
    if maiden is not None:
        mx, my = lw * maiden, hz + (lh - hz) * 0.35
        d.ellipse((mx - U * 1.6, my - U * 0.3, mx + U * 1.6, my + U * 0.6), fill=near)
        d.rectangle((mx - U * 0.9, my - U * 1.2, mx + U * 0.9, my), fill=near)
        d.rectangle((mx - U * 0.35, my - U * 2.8, mx + U * 0.35, my - U * 1.2), fill=near)
        d.polygon([(mx - U * 0.5, my - U * 2.8), (mx + U * 0.5, my - U * 2.8), (mx, my - U * 3.8)], fill=near)
    # historic peninsula: continuous low city band on the near shore
    base = hz
    band = [(0, base)]
    for x in range(0, lw + 3, 3):
        band.append((x, base - U * (1.2 + 0.5 * rng.random())))
    band.append((lw, base))
    d.polygon(band, fill=near)

    def mosque(cx, scale):
        R = U * 2.6 * scale
        by = base - U * 1.0
        d.rectangle((cx - R * 1.9, by - R * 0.55, cx + R * 1.9, base), fill=near)
        for k in (-1, 1):                                            # half domes / small domes
            d.pieslice((cx + k * R * 1.05 - R * 0.7, by - R * 1.3, cx + k * R * 1.05 + R * 0.7, by + R * 0.1), 180, 360, fill=near)
            d.pieslice((cx + k * R * 1.7 - R * 0.35, by - R * 0.9, cx + k * R * 1.7 + R * 0.35, by - R * 0.2), 180, 360, fill=near)
        d.rectangle((cx - R * 0.95, by - R * 1.05, cx + R * 0.95, by - R * 0.5), fill=near)   # drum
        d.pieslice((cx - R, by - R * 2.0, cx + R, by - R * 0.1), 180, 360, fill=near)        # main dome
        d.line([(cx, by - R * 1.05), (cx, by - R * 1.35)], fill=near, width=1)              # finial
        for k, hgt in ((-2.6, 3.4), (-2.2, 3.0), (2.2, 3.0), (2.6, 3.4)):                   # minarets
            mxx = cx + k * R * 0.95
            top_y = by - R * hgt
            wdt = max(0.6, R * 0.09)
            d.rectangle((mxx - wdt, top_y, mxx + wdt, base), fill=near)
            d.line([(mxx - wdt - 1, top_y + R * 0.9), (mxx + wdt + 1, top_y + R * 0.9)], fill=near)   # balcony
            d.line([(mxx - wdt - 1, top_y + R * 1.6), (mxx + wdt + 1, top_y + R * 1.6)], fill=near)
            d.polygon([(mxx - wdt, top_y), (mxx + wdt, top_y), (mxx, top_y - R * 0.7)], fill=near)
        for wx in np.arange(cx - R * 1.7, cx + R * 1.7, 2.0):                                # warm lit windows
            if rng.random() < 0.6:
                d.point((wx, by - R * 0.25), fill=lit)

    for mx, sc in mosques:
        mosque(lw * mx, sc)
    # Galata Tower
    if galata is not None:
        gx = lw * galata
        gw, gh = U * 0.8, U * 6.5
        d.rectangle((gx - gw, base - gh, gx + gw, base), fill=near)
        d.rectangle((gx - gw - 0.6, base - gh - U * 0.3, gx + gw + 0.6, base - gh + U * 0.4), fill=near)
        d.polygon([(gx - gw - 0.6, base - gh - U * 0.3), (gx + gw + 0.6, base - gh - U * 0.3), (gx, base - gh - U * 2.6)], fill=near)
        for k in range(3):
            d.point((gx - gw * 0.5 + k * gw * 0.5, base - gh + U * 1.0), fill=lit)
    # scattered lit windows along the city band
    for _ in range(int(lw * 0.5)):
        d.point((rng.uniform(0, lw), base - rng.uniform(0.3, 1.1) * U), fill=lit)
    return pixup(img, (w, h))
