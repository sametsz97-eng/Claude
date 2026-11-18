"""'ASLA PES ETME' - the moustached skeleton adaptation (PS2 / survival-horror look)."""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tembel-gunler', 'kaynak'))
from common import *          # noqa
import rig
from rig import FRONT, SIDE, SKULL_CU, limb, torso, skull, ik, blen

S = rig.build()
CLIP_DIR = os.environ.get('CLIP_DIR', 'clip')       # cleaned frames of the second video (720x406)
CLIP_N = len([f for f in os.listdir(CLIP_DIR) if f.endswith('.png')]) if os.path.isdir(CLIP_DIR) else 0


def tpt(neck, hip, src, p, width):
    M = rig.seg_matrix(neck, hip, src['neck'], src['hipc'], width)
    return np.asarray(neck, float) + M @ (np.asarray(p, float) - np.asarray(src['neck'], float))


def darken(layer, k):
    a = np.asarray(layer).astype(np.float32)
    a[..., :3] *= k
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')


def light_mask(cx, cy, rx, ry, blur):
    m = Image.new('L', (W, H), 0)
    ImageDraw.Draw(m).ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=255)
    return np.asarray(m.filter(ImageFilter.GaussianBlur(blur))).astype(np.float32) / 255


def apply_light(img, lights, ambient):
    """multiply image by ambient + sum of coloured light masks."""
    a = np.asarray(img.convert('RGB')).astype(np.float32)
    L = np.zeros_like(a) + ambient
    for m, col in lights:
        L += m[..., None] * np.array(col, np.float32)
    return Image.fromarray(np.clip(a * L, 0, 255).astype(np.uint8)).convert('RGBA')


def clip_frame(t):
    if CLIP_N == 0:
        return Image.new('RGB', (720, 406), (40, 40, 40))
    i = int(min(max(t * 30, 0), CLIP_N - 1)) + 1
    return Image.open(os.path.join(CLIP_DIR, f'{i:04d}.png')).convert('RGB')


# ================================================================== scene 1: sitting on the bed, face in hands
def make_s1_bg():
    img = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)
    wall = pixup(damask(90, 110, 11, c1=(40, 44, 40), c2=(54, 58, 52), c3=(64, 68, 60)), (W, 820))
    img.paste(wall, (0, 0))
    # window with cold moonlight, far right
    d.rectangle((560, 230, 700, 520), fill=(26, 32, 46))
    for x in (560, 628, 696):
        d.rectangle((x - 4, 230, x + 4, 520), fill=(44, 46, 50))
    d.rectangle((556, 372, 704, 380), fill=(44, 46, 50))
    # bed: mattress top + side
    fl = pixup(floral(120, 40, 4, base=(70, 14, 16), line=(110, 40, 36)), (W + 120, 200))
    warp_onto(img, fl, [(-60, 800), (W + 60, 800), (W + 60, 950), (-60, 950)])
    side = pixup(floral(120, 10, 5, base=(52, 10, 12), line=(84, 30, 28)), (W + 120, 70))
    warp_onto(img, side, [(-60, 950), (W + 60, 950), (W + 60, 1030), (-60, 1030)])
    # floor + patterned rug (bottom right like a game prop)
    fw = pixup(wood(40, 14, 3, base=(46, 30, 18), plank=3), (W, 200))
    img.paste(fw, (0, 1030))
    rug = Image.new('RGBA', (60, 24), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rug)
    rd.rectangle((0, 0, 59, 23), fill=(150, 150, 146, 255))
    for k in range(0, 60, 6):
        rd.ellipse((k, 4, k + 5, 9), outline=(30, 30, 30, 255))
        rd.ellipse((k + 3, 13, k + 8, 18), outline=(30, 30, 30, 255))
    rd.rectangle((0, 0, 59, 23), outline=(30, 30, 30, 255))
    warp_onto(img, pixup(rug, (360, 144)), [(470, 1130), (820, 1110), (860, 1300), (420, 1300)])
    return img


S1_BG = None


def sitting_skeleton(t, neck, s, sob):
    """hunched front-view skeleton sitting, elbows on knees, both hands covering the (bowed) face."""
    up, fo, ha = (blen(FRONT, 'shL', 'elL') * s, blen(FRONT, 'elL', 'wrL') * s, blen(FRONT, 'wrL', 'tipL') * s)
    fe, shn, ft = (blen(FRONT, 'hipL', 'knL') * s, blen(FRONT, 'knL', 'anL') * s, blen(FRONT, 'anL', 'toeL') * s)
    torso_len = 324 * s * 0.66                       # leaning forward -> foreshortened
    hip = neck + np.array([0, torso_len])
    wd = s
    M = rig.seg_matrix(neck, hip, FRONT['neck'], FRONT['hipc'], wd)
    P = lambda k: np.asarray(neck, float) + M @ (np.asarray(FRONT[k], float) - np.asarray(FRONT['neck'], float))
    sk = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    # legs: thighs come towards the camera (very short), shins go down to the floor
    for side, kx in (('R', -1), ('L', 1)):
        h_ = P('hip' + side)
        kn = h_ + np.array([kx * 46, fe * 0.40])               # knees spread, thighs foreshortened
        an = kn + np.array([-kx * 14, shn * 0.92])
        toe = an + np.array([kx * 10, ft * 0.5])
        limb(sk, S, 'f', side, 'leg', [h_, kn, an, toe], s * 1.05)
    torso(sk, S, 'torso_f', neck, hip, wd, FRONT)
    # skull bowed forward: drawn lower, chin hidden behind the hands
    chin = neck + np.array([0, 66 + sob * 1.5])
    skull(sk, S, 'skull_cu', chin, math.radians(-90 + 3 * math.sin(t * 1.1)), 95 * s * 1.45, SKULL_CU)
    face_c = chin + np.array([0, -0.5 * 95 * s * 1.45])
    arms = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for side, sgn in (('R', -1), ('L', 1)):
        shp = P('sh' + side) + np.array([0, sob * 3])
        kn = P('hip' + side) + np.array([sgn * 40, fe * 0.36])          # elbow rests on the knee
        el = shp + up * (kn - shp) / np.linalg.norm(kn - shp)
        tgt = chin + np.array([sgn * 26 * s, 14])
        wr = el + fo * (tgt - el) / np.linalg.norm(tgt - el)
        tip = wr + ha * 1.05 * dirv(-90 - sgn * 10)
        limb(arms, S, 'f', side, 'arm', [shp, el, wr, tip], s * 1.2)
    sk.alpha_composite(layer_shadow(arms, 0, 8, 6, 0.6))
    sk.alpha_composite(arms)
    return sk, hip, face_c


def scene1(t):
    global S1_BG
    if S1_BG is None:
        S1_BG = make_s1_bg()
    img = S1_BG.copy()
    s = 0.95
    sob = math.sin(t * 2 * math.pi * 2.1) * (0.6 + 0.4 * math.sin(t * 1.7))
    neck = np.array([330.0, 690.0 + sob * 2])
    sk, hip, face = sitting_skeleton(t, neck, s, sob)
    sk = brighten(sk, 1.15, 6, tint=(1.0, 0.96, 0.86))
    img.alpha_composite(layer_shadow(sk, 18, 14, 14, 0.6))
    img.alpha_composite(sk)
    lights = [(light_mask(330, 760, 330, 420, 120), (0.75, 0.72, 0.62)),
              (light_mask(640, 380, 140, 220, 60), (0.25, 0.32, 0.45))]
    img = apply_light(img, lights, 0.10)
    # slow push-in
    z = 1 + 0.06 * smooth(t / 3.6)
    cw, ch = int(W / z), int(H / z)
    x0, y0 = int((W - cw) * 0.45), int((H - ch) * 0.5)
    img = img.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.BICUBIC)
    return post(img, int(t * 30), grade=(1.0, 0.95, 0.85), vign=0.7, gain=0.95)


# ================================================================== scene 2: close-up, face buried in the hands
def scene2(t):
    img = Image.new('RGBA', (W, H), (12, 12, 10, 255))
    sob = math.sin(t * 2 * math.pi * 2.3)
    sk = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    jit = np.array([2.0 * math.sin(t * 31), 3.0 * sob])
    size = 640
    chin = np.array([360.0, 930.0]) + jit
    # shoulders / ribs hint at the bottom
    torso(sk, S, 'torso_f', np.array([360.0, 1060.0]) + jit * 0.5, np.array([360.0, 1060.0 + 324 * 3.0]), 3.0, FRONT)
    skull(sk, S, 'skull_cu', chin, math.radians(-90 + 2 * math.sin(t * 1.4)), size, SKULL_CU)
    # two big hands over the face, forearms coming from below
    hands = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for side, sgn in (('R', -1), ('L', 1)):
        wr = np.array([360 + sgn * 120, 1010.0]) + jit
        tip = np.array([360 + sgn * 70, 560.0]) + jit + np.array([0, 6 * sob * sgn])
        el = wr + np.array([sgn * 110, 420])
        rig.bone(hands, S, f'for{side}_f', el, wr, 3.2)
        rig.bone(hands, S, f'hand{side}_f', wr, tip, 3.6)
    hands = brighten(hands, 1.12, 6)
    sk.alpha_composite(layer_shadow(hands, 0, 14, 12, 0.75))
    sk.alpha_composite(hands)
    sk = brighten(sk, 1.1, 4, tint=(1.0, 0.95, 0.82))
    img.alpha_composite(layer_shadow(sk, 0, 18, 20, 0.6))
    img.alpha_composite(sk)
    img = apply_light(img, [(light_mask(330, 640, 420, 520, 140), (0.62, 0.6, 0.5))], 0.10)
    z = 1 + 0.05 * (t / 1.8)
    cw, ch = int(W / z), int(H / z)
    img = img.crop(((W - cw) // 2, (H - ch) // 2, (W - cw) // 2 + cw, (H - ch) // 2 + ch)).resize((W, H), Image.BICUBIC)
    return post(img, int(t * 30) + 300, grade=(1.0, 0.95, 0.82), vign=0.8, gain=0.9)


# ================================================================== scenes 3-4: city at night, ASLA PES ETME billboard
def billboard_tex(w, h):
    im = Image.new('RGB', (w, h), (236, 236, 234))
    d = ImageDraw.Draw(im)
    lines = ('ASLA', 'PES', 'ETME')
    f = font(FONT_BLACK, h * 0.27)
    for k, ln in enumerate(lines):
        d.text((w / 2, h * (0.2 + 0.3 * k)), ln, font=f, fill=(14, 14, 14), anchor='mm')
    # light falloff from the spotlights below + grime
    a = np.asarray(im).astype(np.float32)
    yy = np.linspace(0, 1, h)[:, None, None]
    a *= 0.62 + 0.42 * yy
    a *= (0.92 + 0.1 * noise(w, h, 6, 44))[..., None]
    return to_img(a)


def make_city(big=False):
    lw, lh = (W // 3, H // 3)
    yy = np.mgrid[0:lh, 0:lw][0].astype(np.float32) / lh
    sky = np.array([8, 9, 14], np.float32) + np.array([14, 14, 20], np.float32) * yy[..., None]
    img = to_img(sky)
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(7)
    # far towers
    x = -3
    while x < lw:
        bw = int(rng.integers(14, 34)); top = int(lh * rng.uniform(0.38, 0.6))
        d.rectangle((x, top, x + bw, lh), fill=(16, 16, 20))
        for wy in range(top + 3, lh, 4):
            for wx in range(x + 2, x + bw - 1, 3):
                if rng.random() < 0.18:
                    d.point((wx, wy), fill=(70, 68, 60))
        x += bw + int(rng.integers(1, 5))
    # big lit building, left (rooftop edge glowing like in a PS2 game)
    d.rectangle((4, 110, 64, lh), fill=(30, 28, 26))
    d.rectangle((2, 106, 66, 110), fill=(150, 130, 90))
    for wy in range(116, lh, 5):
        for wx in range(8, 62, 4):
            d.rectangle((wx, wy, wx + 1, wy + 2), fill=(90, 80, 56) if rng.random() < 0.5 else (36, 34, 30))
    # billboard building, centre
    bx0, bx1, btop = 92, 200, 230
    d.rectangle((bx0, btop, bx1, lh), fill=(40, 40, 42))
    for wy in range(btop + 6, lh, 6):
        for wx in range(bx0 + 4, bx1 - 3, 5):
            d.rectangle((wx, wy, wx + 2, wy + 3), fill=(120, 118, 110) if rng.random() < 0.55 else (26, 26, 28))
    # billboard legs
    for lx in (120, 172):
        d.rectangle((lx, 206, lx + 2, btop), fill=(30, 30, 30))
    img = pixup(img, (W, H)).convert('RGBA')
    bb = billboard_tex(240, 150)
    warp_onto(img, bb.resize((80, 50), Image.BILINEAR).resize((240, 150), Image.NEAREST),
              [(318, 556), (562, 546), (562, 664), (318, 670)])
    return img


CITY = None


def scene3(t):
    global CITY
    if CITY is None:
        CITY = make_city()
    img = CITY.copy()
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((280, 500, 600, 720), fill=(255, 250, 230, 40))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(40)))
    z = 1 + 0.10 * smooth(t / 2.0)
    cw, ch = int(W / z), int(H / z)
    x0, y0 = int((W - cw) * 0.62), int((H - ch) * 0.48)
    img = img.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.BICUBIC)
    return post(img, int(t * 30) + 500, grade=(0.95, 0.95, 1.0), vign=0.6)


BB = None


def scene4(t):
    global BB
    if BB is None:
        BB = billboard_tex(760, 480)
    img = Image.new('RGBA', (W, H), (8, 8, 11, 255))
    d = ImageDraw.Draw(img)
    # rooftop below: dark concrete, railing, steps
    roof = pixup(to_img(np.array([30, 30, 30], np.float32) * (0.7 + 0.5 * noise(W // 4, 120, 4, 9))[..., None]), (W, 480))
    img.paste(roof, (0, 800))
    for x in range(-20, W + 40, 34):
        d.line([(x, 800), (x - 30, 1280)], fill=(48, 48, 48), width=6)
    d.rectangle((0, 860, W, 872), fill=(64, 64, 62))
    for x in range(10, W, 46):
        d.rectangle((x, 872, x + 6, 1000), fill=(56, 56, 54))
    d.rectangle((0, 1000, W, 1010), fill=(70, 70, 68))
    # steel frame + legs
    d.rectangle((-10, 744, W + 10, 760), fill=(36, 36, 38))
    for lx in (150, 560):
        d.rectangle((lx, 760, lx + 14, 900), fill=(30, 30, 32))
    drift = 8 * math.sin(t * 0.9)
    img.paste(BB, (int(-20 + drift), 270))
    # spotlights flicker slightly
    fl = 1 + 0.03 * math.sin(t * 37) * (t % 0.9 < 0.1)
    img = apply_light(img, [(light_mask(360, 620, 520, 300, 80), (0.6 * fl, 0.6 * fl, 0.58 * fl))], 0.55)
    z = 1 + 0.04 * (t / 2.0)
    cw, ch = int(W / z), int(H / z)
    img = img.crop(((W - cw) // 2, (H - ch) // 2, (W - cw) // 2 + cw, (H - ch) // 2 + ch)).resize((W, H), Image.BICUBIC)
    return post(img, int(t * 30) + 700, grade=(1.0, 1.0, 1.0), vign=0.55)


# ================================================================== scenes 5-6: dark desk, PC screen plays the clip
K = 2                                          # desk is drawn at 2x so we can zoom into the monitor
SCR = [(222 * K, 560 * K), (498 * K, 560 * K), (498 * K, 716 * K), (222 * K, 716 * K)]   # 16:9 screen quad


def make_desk():
    w, h = W * K, H * K
    img = Image.new('RGBA', (w, h), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)
    wall = pixup(damask(120, 140, 31, c1=(26, 34, 28), c2=(34, 44, 36), c3=(40, 50, 40)), (w, int(880 * K)))
    img.paste(wall, (0, 0))
    # desk surface (wood) + front edge
    top = pixup(wood(60, 24, 32, base=(66, 40, 22), plank=4), (w + 200, int(260 * K)))
    warp_onto(img, top, [(-100, 860 * K), (w + 100, 860 * K), (w + 100, 1120 * K), (-100, 1120 * K)])
    d.rectangle((0, 1120 * K, w, h), fill=(22, 14, 8))
    # monitor: bezel, stand
    x0, y0 = SCR[0]; x1, y1 = SCR[2]
    b = 16 * K
    d.rectangle((x0 - b, y0 - b, x1 + b, y1 + b + 8 * K), fill=(22, 22, 24))
    d.rectangle((x0 - b + 3 * K, y0 - b + 3 * K, x1 + b - 3 * K, y1 + b + 5 * K), outline=(40, 40, 44), width=2 * K)
    d.ellipse(((x0 + x1) / 2 - 3 * K, y1 + b - 2 * K, (x0 + x1) / 2 + 3 * K, y1 + b + 4 * K), fill=(60, 140, 60))
    d.rectangle(((x0 + x1) / 2 - 18 * K, y1 + b + 8 * K, (x0 + x1) / 2 + 18 * K, 880 * K), fill=(26, 26, 28))
    d.polygon([((x0 + x1) / 2 - 80 * K, 892 * K), ((x0 + x1) / 2 + 80 * K, 892 * K), ((x0 + x1) / 2 + 60 * K, 876 * K), ((x0 + x1) / 2 - 60 * K, 876 * K)], fill=(30, 30, 32))
    # keyboard
    kb = Image.new('RGBA', (120, 20), (28, 28, 30, 255))
    kd = ImageDraw.Draw(kb)
    for r in range(4):
        for c in range(22):
            kd.rectangle((2 + c * 5.3, 2 + r * 4.4, 5 + c * 5.3, 5 + r * 4.4), fill=(58, 58, 62))
    warp_onto(img, pixup(kb, (480, 80)), [(230 * K, 930 * K), (500 * K, 930 * K), (530 * K, 1000 * K), (200 * K, 1000 * K)])
    # can (left) and a small rock-like eraser
    can = Image.new('RGBA', (20, 40), (0, 0, 0, 0))
    cd = ImageDraw.Draw(can)
    cd.rectangle((0, 2, 19, 39), fill=(28, 52, 120, 255))
    cd.rectangle((0, 14, 19, 24), fill=(170, 176, 196, 255))
    cd.ellipse((0, 0, 19, 5), fill=(150, 152, 160, 255))
    can = pixup(can, (60 * K, 120 * K))
    img.alpha_composite(can, (40 * K, 790 * K))
    d.ellipse((112 * K, 880 * K, 160 * K, 910 * K), fill=(90, 86, 80))
    # desk lamp: base, arm, shade (far left)
    d.ellipse((60 * K, 850 * K, 160 * K, 880 * K), fill=(40, 40, 42))
    d.line([(110 * K, 860 * K), (80 * K, 640 * K)], fill=(50, 50, 52), width=8 * K)
    d.line([(80 * K, 640 * K), (150 * K, 560 * K)], fill=(50, 50, 52), width=8 * K)
    d.polygon([(110 * K, 520 * K), (190 * K, 560 * K), (170 * K, 640 * K), (40 * K, 610 * K)], fill=(150, 150, 146))
    d.polygon([(40 * K, 610 * K), (170 * K, 640 * K), (150 * K, 650 * K), (60 * K, 628 * K)], fill=(255, 250, 232))
    # little speaker LEDs on the wall shelf (like in the original's background)
    for k, c in enumerate([(80, 160, 80), (160, 60, 50), (80, 160, 80)]):
        d.rectangle((300 * K + k * 26 * K, 420 * K, 318 * K + k * 26 * K, 436 * K), fill=c)
    img = img.resize((w // 2, h // 2), Image.NEAREST).resize((w, h), Image.NEAREST)
    # lighting: lamp pool on the desk + dim
    a = np.asarray(img.convert('RGB')).astype(np.float32)
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).ellipse((-60 * K, 600 * K, 400 * K, 1080 * K), fill=255)
    m = np.asarray(m.filter(ImageFilter.GaussianBlur(70 * K))).astype(np.float32) / 255
    a *= (0.32 + 1.1 * m)[..., None]
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert('RGBA')
    gl = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(gl).ellipse((40 * K, 590 * K, 180 * K, 690 * K), fill=(255, 250, 230, 120))
    img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(18 * K)))
    return img


DESK = None


def walker(t):
    """dark side-view skeleton walking past the camera (foreground)."""
    sk = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0))
    s = 2.6 * K
    x = -700 + 1900 * (t / 0.9)
    neck = np.array([x, 420.0 * K + 14 * K * abs(math.sin(t * 9))])
    hip = neck + np.array([22 * s, 322 * s])
    torso(sk, S, 'side_full', neck, hip, s, SIDE)
    sk = darken(sk, 0.4)
    return sk.filter(ImageFilter.BoxBlur(6))


def scene5(t, clip_t):
    """desk scene. t: time since scene start. zoom into the monitor after 2.6 s."""
    global DESK
    if DESK is None:
        DESK = make_desk()
    img = DESK.copy()
    fr = clip_frame(clip_t)
    warp_onto(img, fr, SCR, resample=Image.BILINEAR)
    # screen glow on wall/desk
    sc = np.asarray(fr.resize((8, 4))).reshape(-1, 3).mean(0)
    gl = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(gl).rectangle((SCR[0][0] - 60 * K, SCR[0][1] - 60 * K, SCR[2][0] + 60 * K, SCR[2][1] + 160 * K),
                                 fill=tuple(int(v) for v in sc) + (60,))
    img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(50 * K)))
    if t < 0.9:
        img.alpha_composite(walker(t))
    # camera: wide -> push into the screen
    u = smooth((t - 2.6) / 1.4)
    cx0, cy0, cw0 = W * K / 2, H * K / 2 + 40 * K, W * K
    sx = (SCR[0][0] + SCR[1][0]) / 2
    sy = (SCR[0][1] + SCR[2][1]) / 2 + 10 * K
    cw1 = (SCR[1][0] - SCR[0][0]) * 1.07
    cx, cy, cw = cx0 + (sx - cx0) * u, cy0 + (sy - cy0) * u, cw0 + (cw1 - cw0) * u
    cw = cw * (1 - 0.015 * max(0.0, t - 4.0) / 6)          # slow creep afterwards
    ch = cw * H / W
    img = img.crop((int(cx - cw / 2), int(cy - ch / 2), int(cx + cw / 2), int(cy + ch / 2))).resize((W, H), Image.BICUBIC)
    return post(img, int(t * 30) + 900, grade=(1.0, 0.98, 0.95), vign=0.55)
