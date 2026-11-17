import math, sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops
from sprites import build, J

W, H = 1080, 864
FPS = 30
DUR = 5.0
OUT = sys.argv[1] if len(sys.argv) > 1 else 'frames'
ONLY = [float(x) for x in sys.argv[2:]]  # optional list of times for stills

SP = build()
FONT_B = '/usr/share/fonts/opentype/inter/Inter-SemiBold.otf'
FONT_L = '/usr/share/fonts/opentype/inter/Inter-Thin.otf'
FONT_M = '/usr/share/fonts/opentype/inter/Inter-Medium.otf'

# ---------------------------------------------------------------- timeline
RINGS = [  # ring start, finger contact, reach duration, clock text
    (0.30, 0.98, 0.24, '07:00'),
    (1.70, 2.12, 0.17, '07:09'),
    (2.95, 3.20, 0.12, '07:18'),
]
HOLD, BACK = 0.05, 0.30


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def arm_blend(t):
    """0 = resting on chest, 1 = finger on the phone."""
    v = 0.0
    for tr, tc, rd, _ in RINGS:
        if tc - rd <= t <= tc:
            u = (t - (tc - rd)) / rd
            v = max(v, u ** 1.6)  # accelerate into the tap
        elif tc < t <= tc + HOLD:
            v = 1.0
        elif tc + HOLD < t <= tc + HOLD + BACK:
            v = max(v, 1 - ease_out((t - tc - HOLD) / BACK))
    return v


def phone_state(t):
    """returns (ringing, screen_brightness, pressed, clock text, idx)"""
    for i, (tr, tc, rd, clk) in enumerate(RINGS):
        if tr <= t < tc:
            fade_in = smooth((t - tr) / 0.06)
            return True, fade_in, 0.0, clk, i
        if tc <= t < tc + 0.32:
            u = (t - tc) / 0.32
            return False, 1 - smooth((u - 0.35) / 0.65), 1 - u, clk, i
    return False, 0.0, 0.0, '07:00', -1


# ---------------------------------------------------------------- geometry helpers
def rot(th):
    c, s = math.cos(th), math.sin(th)
    return np.array([[c, -s], [s, c]])


def place(dst, sprite, M, src_anchor, dst_anchor, resample=Image.BICUBIC):
    """Composite RGBA `sprite` (with origin offset) onto dst using 2x2 matrix M:
    screen = dst_anchor + M @ (q - src_anchor),  q = original-image coords."""
    img, (ox, oy) = sprite
    sw, sh = img.size
    src = np.array(src_anchor, float)
    D = np.array(dst_anchor, float)
    corners = np.array([[ox, oy], [ox + sw, oy], [ox, oy + sh], [ox + sw, oy + sh]], float)
    sc = (M @ (corners - src).T).T + D
    x0, y0 = np.floor(sc.min(0)).astype(int) - 2
    x1, y1 = np.ceil(sc.max(0)).astype(int) + 2
    Mi = np.linalg.inv(M)
    # output pixel (px,py) in patch -> screen (px+x0, py+y0) -> q -> local (q - o)
    off = src - np.array([ox, oy]) + Mi @ (np.array([x0, y0], float) - D)
    data = (Mi[0, 0], Mi[0, 1], off[0], Mi[1, 0], Mi[1, 1], off[1])
    patch = img.transform((x1 - x0, y1 - y0), Image.AFFINE, data, resample=resample)
    dst.alpha_composite(patch, (int(x0), int(y0))) if x0 >= 0 and y0 >= 0 else paste_clip(dst, patch, x0, y0)


def paste_clip(dst, patch, x0, y0):
    cx, cy = max(0, -x0), max(0, -y0)
    if cx >= patch.width or cy >= patch.height:
        return
    dst.alpha_composite(patch.crop((cx, cy, patch.width, patch.height)), (x0 + cx, y0 + cy))


def bone_matrix(a, b, src_a, src_b, width_scale=1.0):
    """matrix mapping the source segment src_a->src_b onto screen segment a->b."""
    sv = np.array(src_b, float) - np.array(src_a, float)
    dv = np.array(b, float) - np.array(a, float)
    ls, ld = np.linalg.norm(sv), np.linalg.norm(dv)
    ang = math.atan2(dv[1], dv[0]) - math.atan2(sv[1], sv[0])
    k = ld / ls
    # scale along bone by k, across by k*width_scale (in source frame), then rotate
    u = sv / ls
    n = np.array([-u[1], u[0]])
    S = k * np.outer(u, u) + k * width_scale * np.outer(n, n)
    return rot(ang) @ S


def ik(sh, target, l1, l2, bend):
    sh = np.array(sh, float); target = np.array(target, float)
    d = target - sh
    dist = min(np.linalg.norm(d), l1 + l2 - 1e-3)
    dist = max(dist, abs(l1 - l2) + 1e-3)
    base = math.atan2(d[1], d[0])
    cos_a = (l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist)
    a = math.acos(max(-1, min(1, cos_a)))
    el = sh + l1 * np.array([math.cos(base + bend * a), math.sin(base + bend * a)])
    wr = sh + d / np.linalg.norm(d) * dist
    return el, wr


# ---------------------------------------------------------------- static background
def noise_tex(w, h, scale, seed):
    rng = np.random.default_rng(seed)
    n = rng.random((h // scale + 2, w // scale + 2)).astype(np.float32)
    im = Image.fromarray((n * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    return np.asarray(im).astype(np.float32) / 255.0


def make_background():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # bed sheet (pale olive like the reference, a bit dimmer -> early morning)
    sheet = np.array([176, 174, 140], np.float32)
    g = 0.86 + 0.14 * (1 - yy / H) * 0.6 + 0.10 * (xx / W)
    n = noise_tex(W, H, 90, 1) * 0.06 + noise_tex(W, H, 23, 2) * 0.03
    img = sheet[None, None, :] * (g + n)[..., None]
    # wrinkles: soft diagonal folds
    fold = np.zeros((H, W), np.float32)
    rng = np.random.default_rng(7)
    lay = Image.new('L', (W, H), 128)
    d = ImageDraw.Draw(lay)
    for _ in range(14):
        x = rng.uniform(-100, W); y = rng.uniform(300, H + 100)
        ang = rng.uniform(-0.9, -0.3); L = rng.uniform(120, 340)
        pts = [(x + i / 8 * L * math.cos(ang), y + i / 8 * L * math.sin(ang) + 10 * math.sin(i)) for i in range(9)]
        d.line(pts, fill=int(rng.choice([95, 160])), width=int(rng.uniform(6, 14)))
    lay = lay.filter(ImageFilter.GaussianBlur(9))
    fold = (np.asarray(lay).astype(np.float32) - 128) / 128.0
    img *= (1 + 0.22 * fold)[..., None]
    # headboard / wall strip at the top (diagonal like the reference camera)
    edge = 150 - xx * 0.10
    wall = np.array([92, 78, 90], np.float32) * (0.85 + 0.25 * noise_tex(W, H, 120, 3))[..., None]
    m = np.clip((edge - yy) / 3.0, 0, 1)[..., None]
    img = img * (1 - m) + wall * m
    # mattress edge shadow under the wall
    sh = np.clip(1 - np.abs(yy - edge - 8) / 22.0, 0, 1) * (yy > edge)
    img *= (1 - 0.35 * sh)[..., None]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert('RGBA')


def make_pillow():
    lay = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(lay)
    cx, cy, ang = 205, 405, math.radians(-14)
    pts = []
    for i in range(200):
        t = 2 * math.pi * i / 200
        c, s = math.cos(t), math.sin(t)
        x = 250 * np.sign(c) * abs(c) ** 0.45
        y = 150 * np.sign(s) * abs(s) ** 0.55
        y += 18 * math.sin(3 * t)
        pts.append((cx + x * math.cos(ang) - y * math.sin(ang), cy + x * math.sin(ang) + y * math.cos(ang)))
    d.polygon(pts, fill=255)
    mask = lay.filter(ImageFilter.GaussianBlur(3))
    inner = np.asarray(lay.filter(ImageFilter.GaussianBlur(40))).astype(np.float32) / 255
    base = np.array([214, 214, 206], np.float32)
    n = noise_tex(W, H, 40, 9) * 0.05
    col = base * (0.62 + 0.42 * inner + n)[..., None]
    # dent where the head rests
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dent = np.exp(-(((xx - 265) / 120) ** 2 + ((yy - 390) / 85) ** 2))
    col *= (1 - 0.22 * dent)[..., None]
    rgba = np.dstack([np.clip(col, 0, 255), np.asarray(mask)]).astype(np.uint8)
    pil = Image.fromarray(rgba, 'RGBA')
    shadow = Image.new('RGBA', (W, H), (40, 35, 25, 0))
    shadow.putalpha(lay.filter(ImageFilter.GaussianBlur(22)).point(lambda v: int(v * 0.55)))
    return pil, shadow


def make_blanket():
    lay = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(lay)
    edge = [(770, 40), (778, 150), (792, 260), (770, 360), (742, 450), (748, 560), (790, 680), (840, 790), (868, H + 20)]
    d.polygon(edge + [(W + 20, H + 20), (W + 20, 40)], fill=255)
    mask = lay.filter(ImageFilter.GaussianBlur(1.5))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    base = np.array([92, 58, 44], np.float32)
    # fold lines: soft curved ridges/valleys running mostly along the body
    fl = Image.new('L', (W, H), 128)
    fd = ImageDraw.Draw(fl)
    rng = np.random.default_rng(21)
    for _ in range(22):
        x = rng.uniform(760, W + 40); y = rng.uniform(-40, H)
        ang = rng.uniform(1.0, 2.2); L = rng.uniform(150, 420)
        pts = [(x + i / 10 * L * math.cos(ang) + 25 * math.sin(i * 0.7), y + i / 10 * L * math.sin(ang)) for i in range(11)]
        fd.line(pts, fill=int(rng.choice([70, 190])), width=int(rng.uniform(10, 26)), joint='curve')
    f1 = (np.asarray(fl.filter(ImageFilter.GaussianBlur(11))).astype(np.float32) - 128) / 128
    f2 = (np.asarray(fl.filter(ImageFilter.GaussianBlur(3))).astype(np.float32) - 128) / 128
    f = 0.80 + 0.30 * f1 + 0.12 * f2 + (noise_tex(W, H, 6, 12) - 0.5) * 0.10
    # distance-from-edge: rolled hem near the edge, darker crease behind it
    dist = np.asarray(lay.filter(ImageFilter.GaussianBlur(20))).astype(np.float32) / 255
    hem = np.clip(1 - np.abs(dist - 0.62) / 0.16, 0, 1)
    crease = np.clip(1 - np.abs(dist - 0.88) / 0.07, 0, 1)
    f = f * (1 + 0.35 * hem - 0.30 * crease)
    col = base * f[..., None]
    rgba = np.dstack([np.clip(col, 0, 255), np.asarray(mask)]).astype(np.uint8)
    pil = Image.fromarray(rgba, 'RGBA')
    shadow = Image.new('RGBA', (W, H), (30, 20, 10, 0))
    shadow.putalpha(ImageChops.offset(lay, -16, 12).filter(ImageFilter.GaussianBlur(16)).point(lambda v: int(v * 0.7)))
    return pil, shadow


# ---------------------------------------------------------------- phone
PW, PH = 230, 470  # flat phone texture size (portrait)


def rounded(d, box, r, fill):
    d.rounded_rectangle(box, r, fill=fill)


def phone_texture(bright, pressed, clock):
    im = Image.new('RGBA', (PW, PH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rounded(d, (0, 0, PW - 1, PH - 1), 38, (22, 22, 26, 255))      # frame
    rounded(d, (6, 6, PW - 7, PH - 7), 33, (6, 6, 8, 255))          # glass
    scr = Image.new('RGBA', (PW - 18, PH - 18), (0, 0, 0, 255))
    if bright > 0.01:
        sd = ImageDraw.Draw(scr)
        sw, sh = scr.size
        # dark wallpaper gradient
        for y in range(sh):
            v = y / sh
            sd.line([(0, y), (sw, y)], fill=(int(18 + 20 * v), int(16 + 12 * v), int(30 + 30 * v), 255))
        f_small = ImageFont.truetype(FONT_M, 17)
        f_time = ImageFont.truetype(FONT_L, 70)
        f_btn = ImageFont.truetype(FONT_B, 24)
        sd.text((sw / 2, 62), 'Alarm', font=f_small, fill=(230, 230, 235), anchor='mm')
        sd.text((sw / 2, 118), clock, font=f_time, fill=(255, 255, 255), anchor='mm')
        # snooze ("Ertele") pill - orange like iOS
        bc = (255, 159, 10) if pressed < 0.5 else (255, 205, 120)
        by = 330
        sd.rounded_rectangle((26, by - 30, sw - 26, by + 30), 30, fill=bc)
        sd.text((sw / 2, by), 'Ertele', font=f_btn, fill=(40, 22, 0), anchor='mm')
        sd.text((sw / 2, 410), 'Durdurmak için kaydır', font=ImageFont.truetype(FONT_M, 13), fill=(200, 200, 205), anchor='mm')
        sd.rounded_rectangle((sw / 2 - 45, sh - 14, sw / 2 + 45, sh - 9), 3, fill=(230, 230, 230))
        arr = np.asarray(scr).astype(np.float32)
        arr[..., :3] *= bright
        scr = Image.fromarray(arr.astype(np.uint8))
    else:
        # dark glass with faint reflection
        sd = ImageDraw.Draw(scr)
        sd.polygon([(0, 40), (scr.width, 0), (scr.width, 90), (0, 150)], fill=(24, 24, 30, 255))
    m = Image.new('L', scr.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, scr.width - 1, scr.height - 1), 30, fill=255)
    im.paste(scr, (9, 9), m)
    # dynamic island
    rounded(d, (PW / 2 - 34, 18, PW / 2 + 34, 38), 10, (0, 0, 0, 255))
    return (im, (0, 0))


PHONE_C = np.array([330.0, 735.0])
PHONE_ANG = math.radians(-62)          # rotation of the portrait phone on screen
PHONE_M = np.diag([1.0, 0.78]) @ rot(PHONE_ANG) * 0.52   # 0.78 = top-down foreshortening
BTN_LOCAL = np.array([PW / 2, 9 + 330])


def phone_point(local, jitter=(0, 0)):
    return PHONE_C + np.array(jitter) + PHONE_M @ (np.array(local) - np.array([PW / 2, PH / 2]))


# ---------------------------------------------------------------- skeleton rig
BODY_TH = math.radians(-80)
BODY_S = 1.72
NECK = np.array([372.0, 402.0])


def body_pt(q, s):
    return NECK + s * rot(BODY_TH) @ (np.array(q, float) - np.array(J['neck']))


L_UP = BODY_S * np.linalg.norm(np.subtract(J['elL'], J['shL']))
L_FO = BODY_S * np.linalg.norm(np.subtract(J['wrL'], J['elL']))
L_HA = BODY_S * np.linalg.norm(np.subtract(J['tipL'], J['wrL']))


def draw_arm(layer, side, sh, el, wr, tip, wscale=1.0):
    k = 'L' if side == 'L' else 'R'
    place(layer, SP['hum' + k], bone_matrix(sh, el, J['sh' + k], J['el' + k], wscale), J['sh' + k], sh)
    place(layer, SP['for' + k], bone_matrix(el, wr, J['el' + k], J['wr' + k], wscale), J['el' + k], el)
    place(layer, SP['hand' + k], bone_matrix(wr, tip, J['wr' + k], J['tip' + k], wscale), J['wr' + k], wr)


def tap_arm(t, s, jitter):
    shL = body_pt(J['shL'], s)
    # resting: hand lies across the chest, fingers drooping toward the bed
    rest_tip_dir = math.radians(158)
    rest_wr = NECK + np.array([268, 188]) + np.array([0, 3 * math.sin(t * 2 * math.pi / 2.6)])
    tip_target = phone_point(BTN_LOCAL, jitter)
    tap_dir = math.radians(122)
    b = arm_blend(t)
    # fingertip-driven: hand direction blends, wrist = tip - hand
    hd = rest_tip_dir + (tap_dir - rest_tip_dir) * b
    hand_v = L_HA * np.array([math.cos(hd), math.sin(hd)])
    rest_tip = rest_wr + L_HA * np.array([math.cos(rest_tip_dir), math.sin(rest_tip_dir)])
    tip = rest_tip + (tip_target - rest_tip) * b
    # arc: lift the hand toward the camera (up/left) in mid-flight
    tip = tip + np.array([-30, -45]) * math.sin(math.pi * b)
    wr = tip - hand_v
    el, wr = ik(shL, wr, L_UP, L_FO, bend=-1)
    tip = wr + hand_v
    return shL, el, wr, tip, b


def bottom_arm(t, s):
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    shR = body_pt(J['shR'], s)
    elR = shR + L_UP * np.array([math.cos(math.radians(44)), math.sin(math.radians(44))])
    wrR = elR + L_FO * np.array([math.cos(math.radians(12)), math.sin(math.radians(12))])
    tipR = wrR + L_HA * np.array([math.cos(math.radians(20)), math.sin(math.radians(20))])
    draw_arm(lay, 'R', shR, elR, wrR, tipR)
    return lay


def skeleton_layer(t):
    s = BODY_S * (1 + 0.010 * math.sin(t * 2 * math.pi / 2.6))
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    M = s * rot(BODY_TH)
    # bottom (right) arm lying on the sheet, toward the camera
    shR = body_pt(J['shR'], s)
    elR = shR + L_UP * np.array([math.cos(math.radians(52)), math.sin(math.radians(52))])
    wrR = elR + L_FO * np.array([math.cos(math.radians(8)), math.sin(math.radians(8))])
    tipR = wrR + L_HA * np.array([math.cos(math.radians(28)), math.sin(math.radians(28))])
    place(lay, SP['torso'], M, J['neck'], NECK)
    # skull: chin at the top of the neck, slight tilt down onto the pillow
    hs = s * 95 / 232 * 1.42
    hb = 1.5 * math.sin(t * 2 * math.pi / 2.6)
    chin = NECK + rot(BODY_TH) @ np.array([0, -2]) * s + np.array([0, hb])
    place(lay, SP['skull'], hs * rot(BODY_TH + math.radians(-6)), J['chin_skull'], chin)
    return lay


# ---------------------------------------------------------------- compose
BG = make_background()
PILLOW, PILLOW_SH = make_pillow()
BLANKET, BLANKET_SH = make_blanket()
VIG = None


def vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W * 0.45) / (W * 0.62)) ** 2 + ((yy - H * 0.5) / (H * 0.62)) ** 2)
    return np.clip(1 - 0.55 * np.clip(r - 0.45, 0, 1) ** 1.4, 0, 1)


VIG = vignette()
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)


def frame(t, fi):
    ringing, bright, pressed, clock, idx = phone_state(t)
    jitter = (0.0, 0.0)
    jrot = 0.0
    if ringing:
        jitter = (2.2 * math.sin(t * 2 * math.pi * 23), 1.6 * math.sin(t * 2 * math.pi * 31 + 1))
        jrot = math.radians(1.2) * math.sin(t * 2 * math.pi * 19)

    img = BG.copy()
    img.alpha_composite(PILLOW_SH, (10, 14))
    img.alpha_composite(PILLOW)

    # phone
    ph = phone_texture(bright, pressed, clock)
    pm = rot(jrot) @ PHONE_M
    psh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    place(psh, ph, pm, (PW / 2, PH / 2), PHONE_C + np.array(jitter) + np.array([6, 8]))
    a = np.asarray(psh)[..., 3]
    sh_img = Image.new('RGBA', (W, H), (20, 15, 5, 0))
    sh_img.putalpha(Image.fromarray(a).filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * 0.6)))
    img.alpha_composite(sh_img)
    place(img, ph, pm, (PW / 2, PH / 2), PHONE_C + np.array(jitter))

    # skeleton + shadow
    sk = skeleton_layer(t)
    s = BODY_S * (1 + 0.010 * math.sin(t * 2 * math.pi / 2.6))
    shL, el, wr, tip, b = tap_arm(t, s, jitter)
    arm = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw_arm(arm, 'L', shL, el, wr, tip)

    def shadow_of(layer, dx, dy, blur, op):
        al = layer.getchannel('A').filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * op))
        sh = Image.new('RGBA', (W, H), (25, 18, 10, 0))
        sh.putalpha(al)
        return ImageChops.offset(sh, dx, dy)

    ba = bottom_arm(t, s)
    img.alpha_composite(shadow_of(ba, 10, 12, 6, 0.5))
    img.alpha_composite(ba)
    img.alpha_composite(shadow_of(sk, 12, 14, 7, 0.55))
    img.alpha_composite(sk)
    img.alpha_composite(BLANKET_SH)
    img.alpha_composite(BLANKET)
    lift = 1 - b  # arm closer to the bed at the tap -> tighter shadow
    img.alpha_composite(shadow_of(arm, int(14 + 22 * math.sin(math.pi * b)), int(16 + 26 * math.sin(math.pi * b)), 6 + 6 * math.sin(math.pi * b), 0.5))
    img.alpha_composite(arm)

    # z z z while asleep
    calm = 1.0
    for tr, tc, rd, _ in RINGS:
        if tr - 0.1 <= t <= tc + 0.5:
            calm = min(calm, 1 - smooth((t - tr + 0.1) / 0.15) * (1 - smooth((t - tc - 0.25) / 0.25)))
    if calm > 0.02:
        zl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        zd = ImageDraw.Draw(zl)
        for k in range(3):
            ph_ = ((t * 0.55 + k / 3.0) % 1.0)
            x = 250 + 70 * ph_ + 10 * math.sin(ph_ * 6 + k)
            y = 300 - 170 * ph_
            size = int(20 + 22 * ph_)
            al = int(230 * calm * math.sin(math.pi * ph_))
            zd.text((x, y), 'z', font=ImageFont.truetype(FONT_B, size), fill=(240, 240, 250, al), anchor='mm', stroke_width=2, stroke_fill=(30, 30, 40, al))
        img.alpha_composite(zl)

    # ---- grade: dim cool morning + phone glow
    arr = np.asarray(img.convert('RGB')).astype(np.float32) / 255.0
    grade = np.array([0.80, 0.82, 0.92], np.float32) * 0.86
    arr = arr * grade
    if bright > 0.01:
        pc = PHONE_C + np.array(jitter)
        r2 = ((XX - pc[0]) ** 2 + ((YY - pc[1]) * 1.3) ** 2)
        glow = np.exp(-r2 / (2 * 230.0 ** 2)) * 0.75 + np.exp(-r2 / (2 * 70.0 ** 2)) * 0.45
        flick = 0.92 + 0.08 * math.sin(t * 40)
        g = (glow * bright * flick)[..., None]
        arr = arr * (1 + g * np.array([0.9, 0.85, 0.75])) + g * np.array([0.08, 0.06, 0.03])
    arr *= VIG[..., None]
    arr *= min(1.0, (DUR - t) / 0.2)
    # PS2-ish: slight desaturation + grain
    lum = arr.mean(-1, keepdims=True)
    arr = lum + (arr - lum) * 0.85
    rng = np.random.default_rng(fi)
    arr += (rng.standard_normal((H, W, 1)).astype(np.float32) * 0.018)
    out = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))
    # tap ripple
    for tr, tc, rd, _ in RINGS:
        if tc <= t <= tc + 0.25:
            u = (t - tc) / 0.25
            p = phone_point(BTN_LOCAL)
            rl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            rr = 8 + 40 * u
            ImageDraw.Draw(rl).ellipse((p[0] - rr, p[1] - rr * 0.8, p[0] + rr, p[1] + rr * 0.8), outline=(255, 230, 190, int(200 * (1 - u))), width=3)
            out = Image.alpha_composite(out.convert('RGBA'), rl).convert('RGB')
    return out


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    if ONLY:
        for t in ONLY:
            frame(t, int(t * FPS)).save(f'{OUT}/still_{t:.2f}.png')
    else:
        n = int(round(DUR * FPS))
        for i in range(n):
            frame(i / FPS, i).save(f'{OUT}/f_{i:04d}.png')
            if i % 30 == 0:
                print(i, flush=True)
