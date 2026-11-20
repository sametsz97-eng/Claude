"""'Geç Kaldığın Zaman' - the moustached skeleton oversleeps (PS2 look)."""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tembel-gunler', 'kaynak'))
from common import *          # noqa
import rig
from rig import FRONT, SKULL_CU, limb, torso, skull, ik, blen

S = rig.build()
TITLE = 'Geç Kaldığın Zaman:'
EYES = ((1009, 147), (1082, 147))        # eye sockets on the close-up skull (sheet coords)


def lens(src, s):
    return tuple(blen(src, a, b) * s for a, b in (('shL', 'elL'), ('elL', 'wrL'), ('wrL', 'tipL'),
                                                    ('hipL', 'knL'), ('knL', 'anL'), ('anL', 'toeL')))


def tpt(neck, hip, src, p, width):
    M = rig.seg_matrix(neck, hip, src['neck'], src['hipc'], width)
    return np.asarray(neck, float) + M @ (np.asarray(p, float) - np.asarray(src['neck'], float))


def chain(start, angles, lengths):
    pts = [np.asarray(start, float)]
    for a, l in zip(angles, lengths):
        pts.append(pts[-1] + l * dirv(a))
    return pts


def skull_pt(chin, angle, size, p):
    """screen position of a sheet point on the close-up skull drawn with skull()."""
    crown = np.array(chin) + size * dirv(math.degrees(angle))
    sv = np.subtract(SKULL_CU['crown'], SKULL_CU['chin'])
    M = rig.seg_matrix(chin, crown, SKULL_CU['chin'], SKULL_CU['crown'], size / np.linalg.norm(sv))
    return np.asarray(chin, float) + M @ (np.subtract(p, SKULL_CU['chin']).astype(float)), size / np.linalg.norm(sv)


def googly(dst, chin, angle, size, pop, t):
    """cartoon eyes popping out of the sockets (shock)."""
    d = ImageDraw.Draw(dst)
    for k, e in enumerate(EYES):
        c, sc = skull_pt(chin, angle, size, e)
        r = 19 * sc * (0.6 + 0.6 * pop)
        d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=(250, 250, 250, 255), outline=(10, 10, 10, 255), width=max(2, int(r * 0.12)))
        pr = r * 0.48
        j = np.array([math.sin(t * 40 + k), math.cos(t * 37 + k)]) * r * 0.08
        d.ellipse((c[0] - pr + j[0], c[1] - pr + j[1], c[0] + pr + j[0], c[1] + pr + j[1]), fill=(8, 8, 8, 255))


def title(img):
    f = font(FONT_SB, 72)
    bb = f.getbbox(TITLE)
    tw, th = bb[2] + 20, bb[3] + 30
    m = Image.new('L', (tw, th), 0)
    ImageDraw.Draw(m).text((10, 10), TITLE, font=f, fill=255)
    m = m.resize((int(tw * 0.82), th), Image.LANCZOS)            # condensed like the meme font
    x, y = (W - m.width) // 2, 150
    sh = Image.new('RGBA', m.size, (0, 0, 0, 0))
    sh.putalpha(m.filter(ImageFilter.GaussianBlur(4)).point(lambda v: int(v * 0.85)))
    img.alpha_composite(sh, (x + 3, y + 4))
    img.paste(Image.new('RGBA', m.size, (255, 255, 255, 255)), (x, y), m)


# ------------------------------------------------------------------ shared bedroom background (wide)
def make_room():
    bg = pixup(damask(90, 104, 1), (W, 832)).convert('RGBA')
    img = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    img.alpha_composite(bg)
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    a = np.clip((yy - 450) / 450, 0, 1) * 0.45 + np.clip(np.abs(xx - 360) / 360 - 0.4, 0, 1) * 0.5
    sh.putalpha(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)))
    img.alpha_composite(sh)
    hb = pixup(wood(40, 10, 4, base=(98, 56, 30), plank=3, vertical=True), (300, 80))
    warp_onto(img, hb, [(430, 728), (740, 700), (740, 790), (430, 800)])
    fl = pixup(floral(150, 70, 1), (600, 280))
    warp_onto(img, fl, [(-60, 790), (780, 770), (780, 1100), (-60, 1130)])
    side = pixup(floral(150, 12, 9, base=(110, 12, 14), line=(160, 50, 44)), (600, 48))
    warp_onto(img, side, [(-60, 1130), (780, 1100), (780, 1150), (-60, 1182)])
    fr = pixup(wood(80, 6, 7, base=(80, 46, 24), plank=2), (640, 48))
    warp_onto(img, fr, [(-60, 1182), (780, 1150), (780, 1196), (-60, 1230)])
    floor = pixup(wood(36, 12, 8, base=(70, 44, 24), plank=3), (W, 120))
    warp_onto(img, floor, [(-60, 1230), (780, 1196), (780, 1290), (-60, 1290)])
    return img


# ================================================================== A: close-up, asleep with the head on the bed
def make_a_bg():
    img = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    img.paste(pixup(damask(60, 40, 2), (W, 480)), (0, 0))
    hb = pixup(wood(30, 6, 4, base=(98, 56, 30), plank=2, vertical=True), (W, 80))
    warp_onto(img, hb, [(0, 430), (W, 400), (W, 470), (0, 500)])
    fl = pixup(floral(80, 70, 3), (W + 300, 900))
    warp_onto(img, fl, [(-200, 470), (W + 200, 440), (W + 400, 1300), (-400, 1300)])
    return img


A_BG = None


def scene_a(t):
    global A_BG
    if A_BG is None:
        A_BG = make_a_bg()
    img = A_BG.copy()
    br = math.sin(t * 2 * math.pi / 2.2)
    sk = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    # arm in the foreground (bottom left)
    rig.bone(sk, S, 'humR_f', np.array([-60.0, 1300.0]), np.array([210.0, 1020.0]), 2.6)
    chin = np.array([250.0, 960.0 + 3 * br])
    ang = math.radians(-38 + 1.2 * br)
    skull(sk, S, 'skull_cu', chin, ang, 620, SKULL_CU)
    # second arm (left edge), hand under the cheek
    rig.bone(sk, S, 'forL_f', np.array([-40.0, 560.0]), np.array([150.0, 860.0]), 2.4)
    sk = brighten(sk, 1.25, 10, tint=(1.04, 1.0, 0.86))
    img.alpha_composite(layer_shadow(sk, -10, 24, 18, 0.55))
    img.alpha_composite(sk)
    title(img)
    z = 1 + 0.05 * (t / 1.5)
    cw, ch = int(W / z), int(H / z)
    img = img.crop(((W - cw) // 2, (H - ch) // 2, (W - cw) // 2 + cw, (H - ch) // 2 + ch)).resize((W, H), Image.BICUBIC)
    return post(img, int(t * 30), grade=(1.0, 0.98, 0.94), vign=0.4)


# ================================================================== B: the alarm clock says 11:22
SEG = {'0': 'abcdef', '1': 'bc', '2': 'abged', '3': 'abgcd', '4': 'fgbc', '5': 'afgcd', '6': 'afgedc', '7': 'abc', '8': 'abcdefg', '9': 'abcfgd'}


def seven(d, x, y, w, h, ch, col, th):
    pts = {'a': (x, y, x + w, y + th), 'g': (x, y + h / 2 - th / 2, x + w, y + h / 2 + th / 2), 'd': (x, y + h - th, x + w, y + h),
           'f': (x, y, x + th, y + h / 2), 'b': (x + w - th, y, x + w, y + h / 2),
           'e': (x, y + h / 2, x + th, y + h), 'c': (x + w - th, y + h / 2, x + w, y + h)}
    for s_ in SEG[ch]:
        x0, y0, x1, y1 = pts[s_]
        d.rectangle((x0 + 2, y0 + 2, x1 - 2, y1 - 2), fill=col)


def make_b_bg():
    img = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    img.paste(pixup(damask(50, 50, 6), (W, 700)), (0, 0))
    top = pixup(wood(40, 40, 12, base=(120, 78, 44), plank=6), (W + 400, 700))
    warp_onto(img, top, [(-100, 640), (W + 100, 640), (W + 500, H + 20), (-500, H + 20)])
    d = ImageDraw.Draw(img)
    d.rectangle((0, 620, W, 645), fill=(92, 58, 32))
    # blue lamp base at the right edge, skeleton fingers at the left
    d.rounded_rectangle((640, 120, 760, 640), 30, fill=(40, 50, 170))
    d.rectangle((650, 140, 668, 620), fill=(80, 96, 220))
    return img


B_BG = None


def scene_b(t):
    global B_BG
    if B_BG is None:
        B_BG = make_b_bg()
    img = B_BG.copy()
    hand = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    rig.bone(hand, S, 'handR_f', np.array([-80.0, 560.0]), np.array([90.0, 610.0]), 2.0)
    img.alpha_composite(brighten(hand, 1.25, 10))
    # clock body (buzzing)
    buzz = np.array([3 * math.sin(t * 90), 1.5 * math.sin(t * 71)]) * (1 if (t % 0.5) < 0.3 else 0)
    cx, cy = 360 + buzz[0], 560 + buzz[1]
    clk = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(clk)
    d.rounded_rectangle((cx - 230, cy - 130, cx + 230, cy + 120), 34, fill=(18, 18, 20, 255))
    d.rounded_rectangle((cx - 214, cy - 114, cx + 214, cy + 104), 26, fill=(8, 8, 10, 255))
    d.ellipse((cx - 22, cy - 140, cx + 22, cy - 128), fill=(60, 140, 220, 255))
    lit = (240, 244, 255, 255)
    for k, ch in enumerate('1122'):
        x = cx - 170 + k * 88 + (40 if k >= 2 else 0)
        seven(d, x, cy - 70, 62 if ch != '1' else 20, 140, ch, lit, 14) if ch != '1' else \
            d.rectangle((x + 36, cy - 68, x + 50, cy + 68), fill=lit)
    if (t % 1.0) < 0.6:
        for yy in (cy - 30, cy + 24):
            d.rectangle((cx - 8, yy, cx + 6, yy + 14), fill=lit)
    d.text((cx + 160, cy + 74), 'AM', font=font(FONT_B, 22), fill=lit)
    d.polygon([(cx - 190, cy - 64), (cx - 176, cy - 64), (cx - 183, cy - 80)], fill=lit)
    img.alpha_composite(layer_shadow(clk, 0, 24, 16, 0.6))
    glow = clk.filter(ImageFilter.GaussianBlur(10))
    img.alpha_composite(clk)
    g = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(g).rectangle((cx - 190, cy - 80, cx + 190, cy + 80), fill=(200, 220, 255, 40))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(30)))
    title(img)
    z = 1 + 0.04 * (t / 1.5)
    cw, ch_ = int(W / z), int(H / z)
    img = img.crop(((W - cw) // 2, (H - ch_) // 2, (W - cw) // 2 + cw, (H - ch_) // 2 + ch_)).resize((W, H), Image.BICUBIC)
    return post(img, int(t * 30) + 100, grade=(1.0, 0.98, 0.95), vign=0.45)


# ================================================================== C: lying on the bed -> SHOCK (speed lines, b/w)
ROOM = None


def speed_lines(t, strength, color=(255, 255, 255)):
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rng = np.random.default_rng(int(t * 15))
    c = np.array([W / 2, H / 2])
    for _ in range(int(70 * strength)):
        a = rng.uniform(0, 2 * math.pi)
        r0 = rng.uniform(330, 520) * (1.3 - 0.4 * strength)
        wdt = rng.uniform(0.006, 0.02)
        p1 = c + 1400 * np.array([math.cos(a - wdt), math.sin(a - wdt)])
        p2 = c + 1400 * np.array([math.cos(a + wdt), math.sin(a + wdt)])
        p0 = c + r0 * np.array([math.cos(a), math.sin(a)])
        d.polygon([tuple(p0), tuple(p1), tuple(p2)], fill=color + (255,))
    return lay


def lying(t, jolt, eyes):
    sk = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    s = 0.80
    up, fo, ha, fe, shn, ft = lens(FRONT, s)
    br = math.sin(t * 2 * math.pi / 2.8)
    neck = np.array([585.0, 915.0 + 1.5 * br - 26 * jolt])
    hip = neck + np.array([-322 * s, 14 + 20 * jolt])
    wd = s * 0.85
    P = lambda k: tpt(neck, hip, FRONT, FRONT[k], wd)
    limb(sk, S, 'f', 'R', 'leg', chain(P('hipR'), [184, 181, -70 - 30 * jolt], [fe, shn, ft * 0.7]), s * 0.9)
    elR, wrR = ik(P('shR'), hip + np.array([80, -22 - 60 * jolt]), up, fo, -1)
    limb(sk, S, 'f', 'R', 'arm', [P('shR'), elR, wrR, wrR + ha * dirv(200 - 60 * jolt)], s * 0.9)
    torso(sk, S, 'torso_f', neck, hip, wd, FRONT)
    chin = neck + np.array([4, -6])
    ang = math.radians(-8 + 2 * br - 30 * jolt)
    size = 95 * s * 1.55
    skull(sk, S, 'skull_cu', chin, ang, size, SKULL_CU)
    limb(sk, S, 'f', 'L', 'leg', chain(P('hipL'), [-148 - 10 * jolt, 150, 182], [fe, shn, ft * 0.8]), s * 0.95)
    elL, wrL = ik(P('shL'), neck + np.array([-95, 48 - 120 * jolt]), up, fo, 1)
    limb(sk, S, 'f', 'L', 'arm', [P('shL'), elL, wrL, wrL + ha * dirv(-150 - 40 * jolt)], s * 0.95)
    if eyes > 0:
        googly(sk, chin, ang, size, eyes, t)
    return brighten(sk, 1.3, 14)


def scene_c(t):
    """0-1.4 s calm, 1.4-2.4 s alarm hits: push-in + speed lines, 2.4-3.0 s full b/w shock."""
    global ROOM
    if ROOM is None:
        ROOM = make_room()
    img = ROOM.copy()
    hit = smooth((t - 1.4) / 0.25)
    shock = t >= 2.4
    jolt = hit * (1 + 0.15 * math.sin(t * 50) * (t > 1.4))
    sk = lying(t, jolt, eyes=back_out((t - 1.45) / 0.3) if t > 1.45 else 0)
    img.alpha_composite(layer_shadow(sk, 4, 12, 6, 0.6))
    img.alpha_composite(sk)
    # camera: framed on the skeleton, then a punch towards the skull
    z = 1.55 + 0.04 * t / 1.4 + 0.75 * smooth((t - 1.4) / 0.5) + 0.2 * smooth((t - 2.4) / 0.6)
    fx, fy = 470 + 90 * smooth((t - 1.4) / 0.5), 900
    cw, ch = W / z, H / z
    x0 = min(max(fx - cw / 2, 0), W - cw); y0 = min(max(fy - ch / 2, 0), H - ch)
    shake = (np.array([math.sin(t * 83), math.cos(t * 71)]) * 10 * hit / z) if t > 1.4 else np.zeros(2)
    box = (int(x0 + shake[0]), int(y0 + shake[1]), int(x0 + shake[0] + cw), int(y0 + shake[1] + ch))
    img = img.crop(box).resize((W, H), Image.BICUBIC)
    if shock:
        # manga shock frame: black background, white skeleton, white speed lines
        lay = sk.crop(box).resize((W, H), Image.BICUBIC)
        a = np.asarray(lay).astype(np.float32)
        lum = a[..., :3].mean(-1)
        on = (a[..., 3] > 128) & (lum > 95)
        out = Image.fromarray(np.where(on, 255, 0).astype(np.uint8)).convert('RGBA')
        out.alpha_composite(speed_lines(t, 1.0))
        return out.convert('RGB')
    if t > 1.4:
        img.alpha_composite(speed_lines(t, 0.4 + 0.6 * smooth((t - 1.4) / 1.0)))
    return post(img, int(t * 30) + 300, grade=(1.0, 0.98, 0.94), vign=0.4)


# ================================================================== D: top-down, flailing on the bed in panic
D_BG = None


def scene_d(t):
    global D_BG
    if D_BG is None:
        D_BG = pixup(floral(120, 214, 21), (W, H)).convert('RGBA')
        d = ImageDraw.Draw(D_BG)
        d.rectangle((0, 0, W, 28), fill=(80, 46, 24))
    img = D_BG.copy()
    s = 1.05
    up, fo, ha, fe, shn, ft = lens(FRONT, s)
    fl = math.sin(t * 2 * math.pi * 3.2)                    # frantic flailing
    neck = np.array([350.0 + 6 * fl, 330.0])
    hip = np.array([330.0, 330.0 + 324 * s * 0.98])
    P = lambda k: tpt(neck, hip, FRONT, FRONT[k], s)
    sk = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    # legs: one knee out to the side, the other bent across
    limb(sk, S, 'f', 'R', 'leg', chain(P('hipR'), [130 + 8 * fl, 60, 160], [fe, shn, ft * 0.7]), s)
    limb(sk, S, 'f', 'L', 'leg', chain(P('hipL'), [75 - 10 * fl, 150, 100], [fe, shn * 0.95, ft * 0.7]), s)
    torso(sk, S, 'torso_f', neck, hip, s, FRONT)
    chin = neck + np.array([6, -4])
    ang = math.radians(-78 + 6 * fl)
    size = 95 * s * 1.5
    skull(sk, S, 'skull_cu', chin, ang, size, SKULL_CU)
    googly(sk, chin, ang, size, 1.0, t)
    # right arm up waving next to the head, left arm across the chest + waving hand
    elR = P('shR') + up * dirv(-120 + 12 * fl)
    wrR = elR + fo * dirv(-80 + 20 * fl)
    limb(sk, S, 'f', 'R', 'arm', [P('shR'), elR, wrR, wrR + ha * dirv(-100 + 35 * fl)], s)
    elL, wrL = ik(P('shL'), neck + np.array([-20, 150]), up, fo, 1)
    limb(sk, S, 'f', 'L', 'arm', [P('shL'), elL, wrL, wrL + ha * dirv(-20 - 35 * fl)], s)
    sk = brighten(sk, 1.3, 14)
    img.alpha_composite(layer_shadow(sk, 12, 16, 8, 0.6))
    img.alpha_composite(sk)
    sh = np.array([math.sin(t * 61), math.cos(t * 53)]) * 4
    img = ImageChops.offset(img, int(sh[0]), int(sh[1]))
    return post(img, int(t * 30) + 600, grade=(1.0, 0.97, 0.92), vign=0.45)
