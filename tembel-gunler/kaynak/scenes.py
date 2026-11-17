import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops
from common import *
import rig
from rig import FRONT, BACK, SIDE, SKULL_CU, SKULL_BK, limb, torso, skull, ik, blen, place, seg_matrix

S = rig.build()


def tpt(neck, hip, src, p, width):
    """transform a sheet landmark through the torso mapping."""
    M = seg_matrix(neck, hip, src['neck'], src['hipc'], width)
    return np.asarray(neck, float) + M @ (np.asarray(p, float) - np.asarray(src['neck'], float))


def lens(src, s):
    up = blen(src, 'shL', 'elL') * s
    fo = blen(src, 'elL', 'wrL') * s
    ha = blen(src, 'wrL', 'tipL') * s
    fe = blen(src, 'hipL', 'knL') * s
    sh = blen(src, 'knL', 'anL') * s
    ft = blen(src, 'anL', 'toeL') * s
    return up, fo, ha, fe, sh, ft


def chain(start, angles, lengths):
    pts = [np.asarray(start, float)]
    for a, l in zip(angles, lengths):
        pts.append(pts[-1] + l * dirv(a))
    return pts


# ================================================================== title
def title_layer(t):
    """'Tembel Günler' in a purple 3D extruded style. t = seconds since title start."""
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for word, x, y, delay, size in (('Tembel', 50, 110, 0.0, 180), ('Günler', 190, 300, 0.22, 180)):
        u = t - delay
        if u <= 0:
            continue
        sc = back_out(u / 0.35)
        f = font(FONT_BLACK, size)
        bb = f.getbbox(word)
        tw, th = bb[2] + 30, bb[3] + 60
        mask = Image.new('L', (tw, th), 0)
        ImageDraw.Draw(mask).text((10, 10), word, font=f, fill=255)
        mask = mask.resize((int(tw * 0.70), th), Image.LANCZOS)        # condensed
        mw, mh = mask.size
        word_im = Image.new('RGBA', (mw + 40, mh + 40), (0, 0, 0, 0))
        # extrusion (dark purple), stepped down-right
        for k in range(16, 0, -1):
            ex = Image.new('RGBA', mask.size, (58 - k, 22, 92 - k, 255))
            word_im.paste(ex, (6 + k, 6 + k), mask)
        # outline light rim
        rim = mask.filter(ImageFilter.MaxFilter(5))
        word_im.paste(Image.new('RGBA', mask.size, (236, 214, 255, 255)), (4, 4), rim)
        # face gradient pink -> violet
        gy = np.linspace(0, 1, mh)[:, None, None]
        face = np.concatenate([(255 * (0.95 - 0.35 * gy)) * np.ones((1, mw, 1)),
                               (255 * (0.36 + 0.10 * gy)) * np.ones((1, mw, 1)),
                               (255 * (0.80 + 0.15 * gy)) * np.ones((1, mw, 1)),
                               255 * np.ones((mh, mw, 1))], axis=2)
        word_im.paste(Image.fromarray(face.astype(np.uint8), 'RGBA'), (4, 4), mask)
        # italic skew + slight rotation, scale pop
        word_im = word_im.transform(word_im.size, Image.AFFINE, (1, 0.18, -20, 0, 1, 0), resample=Image.BICUBIC)
        word_im = word_im.rotate(6, resample=Image.BICUBIC, expand=True)
        if sc != 1:
            nw, nh = max(1, int(word_im.width * sc)), max(1, int(word_im.height * sc))
            cx, cy = x + word_im.width / 2, y + word_im.height / 2
            word_im = word_im.resize((nw, nh), Image.BICUBIC)
            px, py = int(cx - nw / 2), int(cy - nh / 2)
        else:
            px, py = x, y
        bob = int(4 * math.sin(t * 2.4 + delay * 5))
        drop_shadow(lay, word_im, (px, py + bob), off=(10, 14), blur=6, op=0.5)
        lay.alpha_composite(word_im, (max(0, px), max(0, py + bob)))
    return lay


# ================================================================== scene 1: lying on the bed
def make_s1_bg():
    bg = pixup(damask(90, 104, 1), (W, 832)).convert('RGBA')
    img = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    img.alpha_composite(bg)
    # shade wall: darker at the bottom (behind the bed) and edges
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    a = np.zeros((H, W), np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    a += np.clip((yy - 450) / 450, 0, 1) * 0.45 + np.clip(np.abs(xx - 360) / 360 - 0.4, 0, 1) * 0.5
    sh.putalpha(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)))
    img.alpha_composite(sh)
    # headboard (wood) behind the pillow side
    hb = pixup(wood(40, 10, 4, base=(98, 56, 30), plank=3, vertical=True), (300, 80))
    warp_onto(img, hb, [(430, 728), (740, 700), (740, 790), (430, 800)])
    # bed top surface (red floral) in perspective
    fl = pixup(floral(150, 70, 1), (600, 280))
    warp_onto(img, fl, [(-60, 790), (780, 770), (780, 1100), (-60, 1130)])
    # mattress side + frame + floor
    side = pixup(floral(150, 12, 9, base=(110, 12, 14), line=(160, 50, 44)), (600, 48))
    warp_onto(img, side, [(-60, 1130), (780, 1100), (780, 1150), (-60, 1182)])
    fr = pixup(wood(80, 6, 7, base=(80, 46, 24), plank=2), (640, 48))
    warp_onto(img, fr, [(-60, 1182), (780, 1150), (780, 1196), (-60, 1230)])
    floor = pixup(wood(36, 12, 8, base=(70, 44, 24), plank=3), (W, 120))
    warp_onto(img, floor, [(-60, 1230), (780, 1196), (780, 1290), (-60, 1290)])
    # pillow
    pil = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pil)
    pd.rounded_rectangle((520, 790, 760, 880), 40, fill=(214, 200, 196, 255))
    pil = pil.filter(ImageFilter.GaussianBlur(2))
    img.alpha_composite(layer_shadow(pil, -6, 10, 8, 0.5))
    img.alpha_composite(pil)
    # framed photo on the wall
    fp = framed_photo(170, 216).rotate(2.0, resample=Image.BICUBIC, expand=True)
    drop_shadow(img, fp, (60, 520), off=(10, 12), blur=7, op=0.6)
    img.alpha_composite(fp, (60, 520))
    return img


S1_BG = None


def scene1(t):
    global S1_BG
    if S1_BG is None:
        S1_BG = make_s1_bg()
    img = S1_BG.copy()
    s = 0.80
    up, fo, ha, fe, shn, ft = lens(FRONT, s)
    br = math.sin(t * 2 * math.pi / 2.8)
    neck = np.array([585.0, 915.0 + 1.5 * br])
    hip = neck + np.array([-322 * s, 14])
    wd = s * 0.85
    P = lambda k: tpt(neck, hip, FRONT, FRONT[k], wd)
    sk = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    # far (upper) leg straight, far arm on the belly
    limb(sk, S, 'f', 'R', 'leg', chain(P('hipR'), [184, 181, -70], [fe, shn, ft * 0.7]), s * 0.9)
    elR, wrR = ik(P('shR'), hip + np.array([80, -22]), up, fo, -1)
    limb(sk, S, 'f', 'R', 'arm', [P('shR'), elR, wrR, wrR + ha * dirv(200)], s * 0.9)
    torso(sk, S, 'torso_f', neck, hip, wd, FRONT)
    skull(sk, S, 'skull_cu', neck + np.array([4, -6]), math.radians(-8 + 2 * br), 95 * s * 1.55, SKULL_CU)
    # near leg: knee up
    limb(sk, S, 'f', 'L', 'leg', chain(P('hipL'), [-148, 150, 182], [fe, shn, ft * 0.8]), s * 0.95)
    # near arm: lazily scratches the ribs around 2.6-3.6 s
    scratch = smooth((t - 2.6) / 0.2) * (1 - smooth((t - 3.6) / 0.2))
    tgt = neck + np.array([-95, 48]) + scratch * np.array([10 * math.sin(t * 28), 6 * math.cos(t * 28)])
    elL, wrL = ik(P('shL'), tgt, up, fo, 1)
    limb(sk, S, 'f', 'L', 'arm', [P('shL'), elL, wrL, wrL + ha * dirv(-150)], s * 0.95)
    sk = brighten(sk, 1.3, 14)
    img.alpha_composite(layer_shadow(sk, 4, 12, 6, 0.6))
    img.alpha_composite(sk)
    if t >= 1.0:
        img.alpha_composite(title_layer(t - 1.0))
    return post(img, int(t * 30), grade=(1.0, 0.97, 0.92), vign=0.5)


# ================================================================== scene 2: sitting at the table, drinks a can
def can_sprite():
    w, h = 40, 72
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 4, w - 1, h - 1), 6, fill=(36, 70, 170, 255))
    d.rectangle((0, 24, w - 1, 44), fill=(220, 226, 240, 255))
    d.text((w / 2, 34), 'COLA', font=font(FONT_BLACK, 10), fill=(36, 70, 170), anchor='mm')
    d.ellipse((1, 0, w - 2, 10), fill=(200, 204, 212, 255))
    a = np.asarray(im).astype(np.float32)
    shade = 0.55 + 0.6 * np.sin(np.linspace(0.2, 2.9, w))[None, :]
    a[..., :3] *= shade[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')


CAN = None


def make_s2_bg():
    img = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    yy, xx = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32)
    wall = np.array([106, 94, 104], np.float32) * (0.75 + 0.35 * (1 - yy / (H // 4)))[..., None]
    wall *= (0.92 + 0.12 * noise(W // 4, H // 4, 3, 21))[..., None]
    img.paste(pixup(to_img(wall), (W, H)))
    d = ImageDraw.Draw(img)
    # ceiling line
    d.polygon([(0, 0), (W, 0), (W, 150), (0, 190)], fill=(140, 128, 136))
    # dark doorway on the left
    d.rectangle((0, 260, 70, 1000), fill=(34, 28, 30))
    d.rectangle((70, 250, 84, 1000), fill=(80, 70, 74))
    # window with the pink city
    wx0, wy0, wx1, wy1 = 250, 330, 650, 820
    img.paste(istanbul(wx1 - wx0, wy1 - wy0, px=4, horizon=0.70, mosques=((0.80, 0.85), (0.12, 0.5)), galata=0.33, bridge=0.60, maiden=0.55), (wx0, wy0))
    fr = (210, 200, 206)
    d.rectangle((wx0 - 14, wy0 - 14, wx1 + 14, wy0), fill=fr)
    d.rectangle((wx0 - 14, wy1, wx1 + 14, wy1 + 20), fill=fr)
    d.rectangle((wx0 - 14, wy0, wx0, wy1), fill=fr)
    d.rectangle((wx1, wy0, wx1 + 14, wy1), fill=fr)
    d.rectangle(((wx0 + wx1) // 2 - 6, wy0, (wx0 + wx1) // 2 + 6, wy1), fill=fr)
    d.rectangle((wx0, (wy0 + wy1) // 2 - 6, wx1, (wy0 + wy1) // 2 + 6), fill=fr)
    for i in range(1, 3):
        x = wx0 + (wx1 - wx0) * i / 4
        if i != 2:
            d.line([(x, wy0), (x, wy1)], fill=fr, width=4)
    # window light glow on the wall
    glow = Image.new('L', (W, H), 0)
    ImageDraw.Draw(glow).rectangle((wx0 - 60, wy0 - 60, wx1 + 60, wy1 + 100), fill=90)
    glow = glow.filter(ImageFilter.GaussianBlur(60))
    img = Image.composite(Image.new('RGBA', (W, H), (255, 180, 220, 255)), img, glow)
    # framed photo on the left wall
    fp = framed_photo(140, 178, 6)
    drop_shadow(img, fp, (98, 400), off=(8, 10), blur=6, op=0.6)
    img.alpha_composite(fp, (98, 400))
    return img


def make_s2_fg():
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    tb = pixup(wood(60, 50, 11, base=(74, 46, 34), plank=5), (W, 420))
    warp_onto(fg, tb, [(-40, 868), (760, 852), (900, 1300), (-180, 1300)])
    d = ImageDraw.Draw(fg)
    # pizza box (open lid + base with pizza)
    lid = Image.new('RGBA', (220, 120), (196, 160, 116, 255))
    ImageDraw.Draw(lid).rectangle((8, 8, 212, 112), outline=(150, 40, 30, 255), width=6)
    lid = pixup(lid.resize((55, 30), Image.BILINEAR), (220, 120))
    warp_onto(fg, lid, [(10, 840), (250, 852), (240, 960), (-10, 950)])
    base = Image.new('RGBA', (240, 200), (200, 166, 120, 255))
    bd = ImageDraw.Draw(base)
    bd.ellipse((14, 10, 226, 190), fill=(214, 150, 70, 255))
    bd.ellipse((26, 20, 214, 180), fill=(200, 70, 40, 255))
    rng = np.random.default_rng(4)
    for _ in range(14):
        cx, cy = rng.uniform(50, 190), rng.uniform(40, 160)
        bd.ellipse((cx - 11, cy - 11, cx + 11, cy + 11), fill=(140, 30, 26, 255))
    for _ in range(40):
        cx, cy = rng.uniform(40, 200), rng.uniform(30, 170)
        bd.ellipse((cx - 4, cy - 3, cx + 4, cy + 3), fill=(244, 212, 120, 255))
    base = pixup(base.resize((60, 50), Image.BILINEAR), (240, 200))
    warp_onto(fg, base, [(-10, 950), (240, 960), (300, 1170), (-60, 1160)])
    # cereal box behind
    box = Image.new('RGBA', (90, 120), (230, 190, 40, 255))
    bxd = ImageDraw.Draw(box)
    bxd.rectangle((0, 40, 90, 80), fill=(40, 80, 170, 255))
    box = pixup(box.resize((18, 24)), (90, 120))
    drop_shadow(fg, box, (150, 760), off=(8, 6), blur=5, op=0.5)
    fg.alpha_composite(box, (150, 760))
    return fg


S2_BG = S2_FG = None


def scene2(t):
    global S2_BG, S2_FG, CAN
    if S2_BG is None:
        S2_BG, S2_FG, CAN = make_s2_bg(), make_s2_fg(), can_sprite()
    img = S2_BG.copy()
    s = 0.95
    up, fo, ha, fe, shn, ft = lens(FRONT, s)
    br = math.sin(t * 2 * math.pi / 3.0)
    drink = smooth((t - 1.7) / 0.45) * (1 - smooth((t - 3.0) / 0.5))
    neck = np.array([450.0, 575.0 + 2 * br - 6 * drink])
    hip = neck + np.array([-6, 322 * s])
    P = lambda k: tpt(neck, hip, FRONT, FRONT[k], s)
    sk = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    torso(sk, S, 'torso_f', neck, hip, s, FRONT)
    sk = brighten(sk, 1.2, 8, tint=(1.02, 0.96, 1.0))
    img.alpha_composite(layer_shadow(sk, -10, 8, 14, 0.35))
    img.alpha_composite(sk)
    img.alpha_composite(S2_FG)
    sk = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    # head: tilts back while drinking, idle sway otherwise
    hang = -90 + 4 * math.sin(t * 1.3) + 18 * drink
    skull(sk, S, 'skull_cu', neck + np.array([0, -4]), math.radians(hang), 95 * s * 1.5 * (1 - 0.08 * drink), SKULL_CU)
    # left (screen) arm resting on the table
    elR, wrR = ik(P('shR'), np.array([300.0, 905.0]), up, fo * 0.8, -1)
    limb(sk, S, 'f', 'R', 'arm', [P('shR'), elR, wrR, wrR + ha * 0.65 * dirv(70)], s)
    # right (screen) arm holds the can, lifts it to the mouth
    rest = np.array([610.0, 870.0])
    mouth = neck + np.array([34, -12])
    tgt = lerp(rest, mouth, drink)
    elL, wrL = ik(P('shL'), tgt, up, fo, 1)
    hand_tip = wrL + ha * 0.75 * dirv(-150 - 40 * drink)
    can = CAN.rotate(55 * drink, resample=Image.BICUBIC, expand=True)
    cpos = wrL + np.array([-22, -30]) + drink * np.array([-14, 4])
    sk.alpha_composite(can, (int(cpos[0] - can.width / 2), int(cpos[1] - can.height / 2)))
    limb(sk, S, 'f', 'L', 'arm', [P('shL'), elL, wrL, hand_tip], s)
    sk = brighten(sk, 1.2, 8, tint=(1.02, 0.96, 1.0))
    img.alpha_composite(layer_shadow(sk, 6, 10, 6, 0.45))
    img.alpha_composite(sk)
    return post(img, int(t * 30) + 200, grade=(0.95, 0.9, 1.0), vign=0.6, gain=0.95)


# ================================================================== scene 3: playing Valorant on the laptop
GW, GH = 480, 300
KILLS = [(1.55, 'Jett'), (3.35, 'Reyna')]   # fire times (local scene time)


def aim_state(t):
    """crosshair offset of the world (px in game texture) + firing flag."""
    # idle drift, then flicks onto enemies
    yaw = 18 * math.sin(t * 1.1)
    e1 = smooth((t - 1.30) / 0.12)      # flick right to enemy 1
    e2 = smooth((t - 3.10) / 0.12)      # flick left to enemy 2
    back1 = smooth((t - 2.1) / 0.6)
    yaw += -120 * e1 * (1 - back1) + 150 * e2
    firing = any(ft <= t < ft + 0.22 for ft, _ in KILLS)
    return yaw, firing


def game_frame(t):
    yaw, firing = aim_state(t)
    rec = 0
    for ft, _ in KILLS:
        if ft <= t < ft + 0.25:
            rec = 6 * math.sin((t - ft) * 60) ** 2
    bob = 2 * math.sin(t * 8)
    ox, oy = yaw, bob - rec
    im = Image.new('RGB', (GW, GH))
    d = ImageDraw.Draw(im)
    hz = GH * 0.48 + oy
    # sky + far city (Ascent-ish palette)
    for y in range(GH):
        v = y / GH
        d.line([(0, y), (GW, y)], fill=(int(150 + 60 * v), int(196 + 30 * v), int(226 + 10 * v)))
    d.rectangle((0, hz, GW, GH), fill=(150, 132, 108))
    # far building with doorway
    fx = GW / 2 + ox
    d.polygon([(fx - 150, hz - 110), (fx + 150, hz - 110), (fx + 150, hz + 6), (fx - 150, hz + 6)], fill=(212, 190, 152))
    d.polygon([(fx - 160, hz - 120), (fx + 160, hz - 120), (fx + 150, hz - 108), (fx - 150, hz - 108)], fill=(120, 150, 150))
    d.rectangle((fx - 30, hz - 70, fx + 30, hz + 6), fill=(70, 58, 50))
    for k in (-110, -70, 70, 110):
        d.rectangle((fx + k - 12, hz - 90, fx + k + 12, hz - 60), fill=(90, 130, 140))
    # side walls (corridor)
    d.polygon([(-40 + ox * 0.6, 0), (fx - 170, hz - 140), (fx - 170, hz + 10), (-40 + ox * 0.6, GH)], fill=(196, 168, 128))
    d.polygon([(GW + 40 + ox * 0.6, 0), (fx + 170, hz - 140), (fx + 170, hz + 10), (GW + 40 + ox * 0.6, GH)], fill=(178, 150, 112))
    d.line([(fx - 170, hz - 140), (fx - 170, hz + 10)], fill=(150, 124, 92), width=3)
    d.line([(fx + 170, hz - 140), (fx + 170, hz + 10)], fill=(140, 112, 84), width=3)
    # crates
    d.rectangle((fx + 60, hz - 24, fx + 120, hz + 20), fill=(140, 104, 70), outline=(96, 70, 46), width=3)
    # enemies: dark figure with red highlight outline
    for (ft, name), (ex, appear) in zip(KILLS, [(fx + 120, 1.15), (fx - 150, 2.75)]):
        if appear <= t < ft + 0.55:
            dead = smooth((t - ft - 0.05) / 0.35)
            ey = hz + 2
            sil = Image.new('L', (GW, GH), 0)
            sd = ImageDraw.Draw(sil)
            fall = dead * 30
            sd.ellipse((ex - 8, ey - 62 + fall, ex + 8, ey - 46 + fall), fill=255)
            sd.polygon([(ex - 14, ey - 46 + fall), (ex + 14, ey - 46 + fall), (ex + 11, ey - 14 + fall * 0.5), (ex - 11, ey - 14 + fall * 0.5)], fill=255)
            sd.polygon([(ex - 11, ey - 14), (ex - 1, ey - 14), (ex - 4, ey + 6), (ex - 12, ey + 6)], fill=255)
            sd.polygon([(ex + 1, ey - 14), (ex + 11, ey - 14), (ex + 12, ey + 6), (ex + 4, ey + 6)], fill=255)
            a = 1 - dead
            outline = sil.filter(ImageFilter.MaxFilter(5))
            im.paste((235, 50, 60), (0, 0), outline.point(lambda v: int(v * a)))
            im.paste((40, 34, 44), (0, 0), sil.point(lambda v: int(v * a)))
    # gun viewmodel (generic rifle) bottom right
    gx, gy = GW * 0.70 - rec * 0.5, GH * 0.80 + rec * 2 + bob
    d.polygon([(gx, gy), (gx + 150, gy - 30), (gx + 190, gy + 10), (gx + 190, GH), (gx + 30, GH)], fill=(46, 48, 56))
    d.polygon([(gx + 10, gy + 2), (gx + 120, gy - 20), (gx + 128, gy - 8), (gx + 18, gy + 14)], fill=(70, 210, 200))
    d.polygon([(gx + 70, gy + 30), (gx + 120, gy + 18), (gx + 140, GH), (gx + 80, GH)], fill=(30, 30, 36))
    if firing:
        mx, my = gx - 4, gy - 4
        d.polygon([(mx - 26, my - 4), (mx, my - 14), (mx + 8, my + 4), (mx - 10, my + 18)], fill=(255, 236, 160))
        d.ellipse((mx - 12, my - 8, mx + 4, my + 8), fill=(255, 255, 230))
    # crosshair
    cx, cy = GW / 2, GH / 2
    for x0, y0, x1, y1 in ((cx - 9, cy, cx - 3, cy), (cx + 3, cy, cx + 9, cy), (cx, cy - 9, cx, cy - 3), (cx, cy + 3, cx, cy + 9)):
        d.line([(x0, y0), (x1, y1)], fill=(120, 255, 200), width=2)
    # HUD -----------------------------------------------------------
    fs = font(FONT_B, 14)
    fl = font(FONT_BLACK, 22)
    kills = sum(1 for ft, _ in KILLS if t >= ft + 0.05)
    d.rectangle((GW / 2 - 70, 6, GW / 2 - 30, 30), fill=(40, 190, 170))
    d.text((GW / 2 - 50, 18), str(7 + (1 if kills >= 2 else 0)), font=fs, fill='white', anchor='mm')
    d.rectangle((GW / 2 - 28, 6, GW / 2 + 28, 30), fill=(20, 24, 30))
    secs = max(0, 72 - int(t))
    d.text((GW / 2, 18), f'{secs // 60}:{secs % 60:02d}', font=fs, fill='white', anchor='mm')
    d.rectangle((GW / 2 + 30, 6, GW / 2 + 70, 30), fill=(230, 70, 80))
    d.text((GW / 2 + 50, 18), '5', font=fs, fill='white', anchor='mm')
    for i in range(5):
        d.rectangle((GW / 2 - 78 - (i + 1) * 20, 8, GW / 2 - 80 - i * 20, 28), fill=(40, 160, 150))
        alive = not (i < kills)
        d.rectangle((GW / 2 + 80 + i * 20, 8, GW / 2 + 78 + (i + 1) * 20, 28), fill=(220, 70, 80) if alive else (70, 70, 74))
    # minimap
    d.rounded_rectangle((8, 8, 92, 92), 8, fill=(30, 36, 44))
    d.line([(20, 30), (60, 30), (60, 70), (84, 70)], fill=(120, 130, 140), width=6)
    d.line([(30, 84), (30, 50), (76, 50)], fill=(120, 130, 140), width=6)
    d.polygon([(48, 56), (56, 60), (48, 64)], fill=(110, 240, 220))
    # health / ammo
    d.rectangle((GW / 2 - 90, GH - 34, GW / 2 - 20, GH - 8), fill=(20, 24, 30))
    d.text((GW / 2 - 55, GH - 21), '100', font=fl, fill='white', anchor='mm')
    for i in range(4):
        d.rectangle((GW / 2 - 10 + i * 26, GH - 32, GW / 2 + 12 + i * 26, GH - 10), outline=(200, 210, 220), width=2)
    shots = sum(int(max(0, min(t - ft, 0.22)) / 0.07) for ft, _ in KILLS)
    d.text((GW - 70, GH - 20), f'{25 - shots}', font=fl, fill='white', anchor='rm')
    d.text((GW - 64, GH - 18), '/ 75', font=fs, fill=(200, 200, 205), anchor='lm')
    # kill feed + kill banner
    fy = 40
    for ft, name in KILLS:
        if t >= ft + 0.05:
            d.rectangle((GW - 190, fy, GW - 8, fy + 22), fill=(40, 170, 160))
            d.text((GW - 184, fy + 11), 'iskelet', font=fs, fill='white', anchor='lm')
            d.text((GW - 100, fy + 11), '▬►', font=fs, fill='white', anchor='mm')
            d.text((GW - 14, fy + 11), name, font=fs, fill=(255, 220, 220), anchor='rm')
            fy += 26
    for i, (ft, _) in enumerate(KILLS):
        u = t - ft - 0.05
        if 0 <= u < 1.0:
            a = int(255 * (1 - smooth((u - 0.7) / 0.3)))
            sc = back_out(u / 0.25)
            ban = Image.new('RGBA', (80, 80), (0, 0, 0, 0))
            bd = ImageDraw.Draw(ban)
            bd.polygon([(40, 4), (76, 40), (40, 76), (4, 40)], fill=(230, 60, 70, a), outline=(255, 230, 230, a), width=3)
            bd.text((40, 40), str(i + 1), font=font(FONT_BLACK, 30), fill=(255, 255, 255, a), anchor='mm')
            sz = max(1, int(56 * sc))
            ban = ban.resize((sz, sz), Image.BICUBIC)
            im.paste(ban, (int(GW / 2 - sz / 2), int(GH * 0.70 - sz / 2)), ban)
    return im


def make_s3_bg():
    img = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    img.alpha_composite(pixup(damask(90, 42, 5, c1=(40, 70, 38), c2=(62, 98, 54), c3=(84, 120, 70)), (W, 336)).convert('RGBA'))
    d = ImageDraw.Draw(img)
    # shelf top-left
    d.rectangle((0, 120, 230, 300), fill=(60, 36, 22))
    d.rectangle((10, 132, 220, 288), fill=(36, 22, 14))
    d.rectangle((24, 200, 120, 288), fill=(120, 110, 90))
    # desk (wood planks running away from camera)
    dk = pixup(wood(56, 70, 13, base=(122, 78, 42), plank=7, vertical=True), (560, 700))
    warp_onto(img, dk, [(-60, 330), (780, 330), (1000, 1290), (-280, 1290)])
    sh = Image.new('L', (W, H), 0)
    ImageDraw.Draw(sh).rectangle((0, 320, W, 360), fill=150)
    img = Image.composite(Image.new('RGBA', (W, H), (0, 0, 0, 255)), img, sh.filter(ImageFilter.GaussianBlur(16)))
    d = ImageDraw.Draw(img)
    # mouse pad
    d.rounded_rectangle((520, 700, 712, 930), 12, fill=(40, 42, 48))
    # snacks: cup (top-down), chips bag, crumpled paper
    cup = Image.new('RGBA', (90, 90), (0, 0, 0, 0))
    cd = ImageDraw.Draw(cup)
    cd.ellipse((4, 4, 86, 86), fill=(236, 236, 240, 255))
    cd.ellipse((14, 14, 76, 76), fill=(60, 30, 20, 255))
    cd.line([(44, 44), (70, 10)], fill=(240, 60, 60, 255), width=6)
    cup = pixup(cup.resize((30, 30), Image.BILINEAR), (90, 90))
    drop_shadow(img, cup, (40, 420), off=(10, 14), blur=6, op=0.6)
    img.alpha_composite(cup, (40, 420))
    bag = Image.new('RGBA', (110, 150), (232, 176, 30, 255))
    bgd = ImageDraw.Draw(bag)
    bgd.rectangle((0, 50, 110, 96), fill=(200, 30, 30, 255))
    bgd.text((55, 73), 'CİPS', font=font(FONT_BLACK, 26), fill=(255, 240, 200, 255), anchor='mm')
    bag = pixup(bag.resize((37, 50), Image.BILINEAR), (110, 150)).rotate(-24, resample=Image.NEAREST, expand=True)
    drop_shadow(img, bag, (590, 390), off=(10, 14), blur=6, op=0.6)
    img.alpha_composite(bag, (590, 390))
    paper = Image.new('RGBA', (50, 44), (0, 0, 0, 0))
    ImageDraw.Draw(paper).polygon([(6, 20), (20, 4), (40, 8), (46, 28), (30, 40), (10, 36)], fill=(220, 220, 214, 255))
    drop_shadow(img, paper, (60, 900), off=(6, 8), blur=4, op=0.6)
    img.alpha_composite(paper, (60, 900))
    # laptop base
    base = Image.new('RGBA', (400, 260), (52, 54, 60, 255))
    bd = ImageDraw.Draw(base)
    for r in range(6):
        for c in range(14):
            x = 18 + c * 26.5
            y = 24 + r * 27
            bd.rounded_rectangle((x, y, x + 22, y + 22), 3, fill=(22, 22, 26, 255))
    bd.rounded_rectangle((140, 196, 262, 250), 6, fill=(64, 66, 74, 255))
    warp_onto(img, base, [(178, 640), (552, 640), (604, 930), (126, 930)], resample=Image.BILINEAR)
    lid = Image.new('RGBA', (440, 300), (24, 24, 28, 255))
    warp_onto(img, lid, [(146, 318), (586, 318), (560, 642), (170, 642)], resample=Image.BILINEAR)
    return img


S3_BG = None
SCREEN_Q = [(160, 334), (572, 334), (549, 626), (182, 626)]


def scene3(t):
    global S3_BG
    if S3_BG is None:
        S3_BG = make_s3_bg()
    img = S3_BG.copy()
    gf = game_frame(t)
    warp_onto(img, gf, SCREEN_Q, resample=Image.BILINEAR)
    # screen glow on desk
    yaw, firing = aim_state(t)
    glow = Image.new('L', (W, H), 0)
    ImageDraw.Draw(glow).ellipse((90, 560, 640, 1000), fill=60 + (40 if firing else 0))
    glow = glow.filter(ImageFilter.GaussianBlur(70))
    img = Image.composite(Image.new('RGBA', (W, H), (190, 230, 255, 255)), img, glow)
    s = 1.75
    up, fo, ha, fe, shn, ft = lens(BACK, s)
    neck = np.array([362.0, 1265.0])
    hip = neck + np.array([0, 322 * s])
    P = lambda k: tpt(neck, hip, BACK, BACK[k], s)
    sk = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    torso(sk, S, 'torso_b', neck, hip, s, BACK)
    # left hand: WASD tapping
    tap = 5 * math.sin(t * 31) * (0.5 + 0.5 * math.sin(t * 3))
    lh = np.array([258.0, 780.0 + tap])
    lw = lh + np.array([0, ha * 0.6])
    elL, wrL = ik(P('shL'), lw, up * 0.82, fo * 0.82, -1)
    limb(sk, S, 'b', 'L', 'arm', [P('shL'), elL, wrL, lh], s * 0.95)
    # right hand on the mouse, follows the aim
    mx = 612 - yaw * 0.25
    mouse = np.array([mx, 820.0])
    md = ImageDraw.Draw(sk)
    md.ellipse((mouse[0] - 26, mouse[1] - 40, mouse[0] + 26, mouse[1] + 40), fill=(28, 28, 32, 255))
    md.line([(mouse[0], mouse[1] - 40), (mouse[0], mouse[1] - 12)], fill=(90, 90, 100, 255), width=2)
    rw = mouse + np.array([0, ha * 0.55])
    elR, wrR = ik(P('shR'), rw, up * 0.82, fo * 0.82, 1)
    limb(sk, S, 'b', 'R', 'arm', [P('shR'), elR, wrR, mouse + np.array([0, -20])], s * 0.95)
    # back of the skull, big in the foreground
    skull(sk, S, 'skull_bk', np.array([362.0, 1330.0]), math.radians(-90 + 3 * math.sin(t * 1.7)), 290, SKULL_BK)
    sk = brighten(sk, 1.25, 10, tint=(0.98, 1.0, 1.04))
    img.alpha_composite(layer_shadow(sk, 0, -14, 16, 0.45))
    img.alpha_composite(sk)
    return post(img, int(t * 30) + 400, grade=(0.95, 0.95, 1.0), vign=0.55, gain=0.95)


# ================================================================== scene 4: on the bed with the phone
def make_s4_bg():
    img = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    left = pixup(damask(56, 112, 7), (448, 896))
    right = pixup(damask(40, 112, 8), (320, 896))
    a = np.asarray(right).astype(np.float32) * 0.62
    img.paste(left, (0, 0))
    img.paste(to_img(a), (440, 0))
    d = ImageDraw.Draw(img)
    d.line([(440, 0), (440, 900)], fill=(24, 40, 22), width=4)
    # bed
    fl = pixup(floral(130, 90, 2), (520, 360))
    warp_onto(img, fl, [(-80, 870), (800, 850), (900, 1290), (-200, 1290)])
    # pillow behind the back
    pil = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(pil).rounded_rectangle((440, 640, 720, 900), 50, fill=(200, 186, 182, 255))
    pil = pil.filter(ImageFilter.GaussianBlur(3))
    img.alpha_composite(layer_shadow(pil, -10, 10, 10, 0.5))
    img.alpha_composite(pil)
    # framed photo on the wall above
    fp = framed_photo(176, 224, 9).rotate(-2.5, resample=Image.BICUBIC, expand=True)
    drop_shadow(img, fp, (110, 300), off=(10, 12), blur=7, op=0.6)
    img.alpha_composite(fp, (110, 300))
    return img


S4_BG = None


def phone_im(t):
    w, h = 84, 160
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 12, fill=(30, 30, 34, 255))
    scr = Image.new('RGB', (w - 10, h - 12), (245, 245, 248))
    sd = ImageDraw.Draw(scr)
    scroll = (t * 140) % 120
    for i in range(-1, 4):
        y = i * 60 - scroll % 60 + 10
        sd.rectangle((6, y, w - 16, y + 34), fill=[(250, 160, 180), (150, 190, 250), (250, 210, 120), (170, 220, 170)][(i + int(scroll // 60)) % 4])
        sd.rectangle((6, y + 38, w - 30, y + 42), fill=(200, 200, 205))
    im.paste(scr, (5, 6))
    return im


def scene4(t):
    global S4_BG
    if S4_BG is None:
        S4_BG = make_s4_bg()
    img = S4_BG.copy()
    s = 1.0
    up, fo, ha, fe, shn, ft = lens(FRONT, s)
    br = math.sin(t * 2 * math.pi / 3.0)
    neck = np.array([540.0, 660.0 + 2 * br])
    hip = np.array([470.0, 980.0])
    P = lambda k: tpt(neck, hip, FRONT, FRONT[k], s)
    sk = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    # far leg flat on the bed
    limb(sk, S, 'f', 'L', 'leg', chain(P('hipL'), [150, 165, 120], [fe, shn * 0.9, ft * 0.8]), s)
    torso(sk, S, 'torso_f', neck, hip, s, FRONT)
    skull(sk, S, 'skull_cu', neck + np.array([-4, -6]), math.radians(-104 + 3 * math.sin(t * 1.4)), 95 * s * 1.5, SKULL_CU)
    # near leg crossed, knee up
    limb(sk, S, 'f', 'R', 'leg', chain(P('hipR'), [-160, 120, 160], [fe * 0.9, shn * 0.9, ft * 0.8]), s * 1.05)
    # phone held in front of the chest
    ph = phone_im(t).rotate(12, resample=Image.BICUBIC, expand=True)
    pc = np.array([400.0, 770.0])
    elR, wrR = ik(P('shR'), pc + np.array([-30, 70]), up, fo, -1)
    limb(sk, S, 'f', 'R', 'arm', [P('shR'), elR, wrR, wrR + ha * 0.8 * dirv(-75)], s)
    sk.alpha_composite(ph, (int(pc[0] - ph.width / 2), int(pc[1] - ph.height / 2)))
    thumb = 8 * math.sin(t * 9)
    elL, wrL = ik(P('shL'), pc + np.array([90, 40 + thumb]), up, fo, 1)
    limb(sk, S, 'f', 'L', 'arm', [P('shL'), elL, wrL, wrL + ha * 0.8 * dirv(-160)], s)
    sk = brighten(sk, 1.3, 12)
    img.alpha_composite(layer_shadow(sk, -16, 12, 12, 0.5))
    img.alpha_composite(sk)
    # phone light on the face
    glow = Image.new('L', (W, H), 0)
    ImageDraw.Draw(glow).ellipse((300, 450, 620, 860), fill=45)
    glow = glow.filter(ImageFilter.GaussianBlur(60))
    img = Image.composite(Image.new('RGBA', (W, H), (220, 230, 255, 255)), img, glow)
    return post(img, int(t * 30) + 600, grade=(1.0, 0.96, 0.94), vign=0.5)


# ================================================================== scene 5: POV notebook "Fikirler!"
def make_s5_bg():
    img = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)
    # cabinet (right) + plant (left), bed at the bottom; blurred = depth of field
    cab = pixup(wood(30, 40, 15, base=(110, 70, 40), plank=4, vertical=True), (W, 840))
    img.paste(cab, (0, 0))
    d.rectangle((300, 40, 700, 820), outline=(70, 42, 24), width=10)
    d.line([(500, 40), (500, 820)], fill=(70, 42, 24), width=8)
    d.rectangle((0, 0, 280, 840), fill=(210, 196, 170))
    rng = np.random.default_rng(3)
    for _ in range(26):
        x, y = rng.uniform(20, 260), rng.uniform(40, 560)
        a = rng.uniform(0, math.pi)
        L = rng.uniform(60, 140)
        d.polygon([(x, y), (x + L * math.cos(a) - 14 * math.sin(a), y + L * math.sin(a) * 0.5 + 14 * math.cos(a)),
                   (x + L * 1.2 * math.cos(a), y + L * 1.2 * math.sin(a) * 0.5), (x + L * math.cos(a) + 14 * math.sin(a), y + L * math.sin(a) * 0.5 - 14 * math.cos(a))],
                  fill=(int(rng.uniform(40, 80)), int(rng.uniform(110, 160)), int(rng.uniform(40, 70))))
    d.polygon([(90, 560), (200, 560), (186, 700), (104, 700)], fill=(200, 200, 196))
    fl = pixup(floral(100, 60, 6), (W, 460))
    img.paste(fl, (0, 820))
    return img.filter(ImageFilter.GaussianBlur(5))


def scribble_pts(n):
    pts = []
    for i in range(n):
        a = i * 0.55
        r = 34 + 10 * math.sin(i * 0.37)
        pts.append((110 + r * math.cos(a) + i * 0.12, 520 + r * 0.8 * math.sin(a)))
    return pts


def page_im(t):
    pw, ph = 470, 620
    pg = Image.new('RGBA', (pw, ph), (248, 248, 244, 255))
    d = ImageDraw.Draw(pg)
    for y in range(70, ph, 34):
        d.line([(40, y), (pw, y)], fill=(196, 214, 236), width=1)
    d.line([(64, 0), (64, ph)], fill=(236, 170, 170), width=2)
    for y in range(20, ph, 36):
        d.ellipse((10, y, 26, y + 16), fill=(70, 70, 76))
    pen = (52, 52, 58)
    hf = font(FONT_HAND, 30)
    # doodles
    d.ellipse((90, 60, 150, 116), outline=pen, width=3)              # skull doodle
    d.ellipse((104, 78, 116, 90), fill=pen); d.ellipse((124, 78, 136, 90), fill=pen)
    d.line([(108, 116), (108, 128), (132, 128), (132, 116)], fill=pen, width=3)
    d.line([(170, 110), (190, 92), (205, 112), (222, 90)], fill=pen, width=3)
    gx, gy = 300, 60                                                   # tic-tac-toe
    for k in (1, 2):
        d.line([(gx + 40 * k, gy), (gx + 40 * k, gy + 120)], fill=pen, width=3)
        d.line([(gx, gy + 40 * k), (gx + 120, gy + 40 * k)], fill=pen, width=3)
    for (cx, cy, ch) in ((0, 0, 'x'), (1, 0, 'o'), (2, 0, 'x'), (1, 1, 'x'), (0, 2, 'o'), (2, 2, 'o')):
        d.text((gx + 20 + 40 * cx, gy + 20 + 40 * cy), ch, font=hf, fill=pen, anchor='mm')
    # big wobbly "Fikirler!"
    tm = Image.new('L', (pw, 120), 0)
    ImageDraw.Draw(tm).text((24, 10), 'Fikirler!', font=font(FONT_HAND, 92), fill=255)
    ta = np.asarray(tm).astype(np.float32)
    wob = np.zeros_like(ta)
    for x in range(ta.shape[1]):
        wob[:, x] = np.roll(ta[:, x], int(4 * math.sin(x * 0.05)))
    tm = Image.fromarray(wob.astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))
    pg.paste(Image.new('RGBA', (pw, 120), pen + (255,)), (10, 200), tm)
    d.line([(40, 330), (200, 334), (440, 326)], fill=pen, width=4)
    d.text((70, 380), '???', font=font(FONT_HAND, 52), fill=pen)
    d.arc((280, 380, 360, 450), 20, 160, fill=pen, width=4)            # smiley
    d.ellipse((298, 380, 308, 392), fill=pen); d.ellipse((330, 380, 340, 392), fill=pen)
    # cube
    cx, cy = 340, 500
    d.rectangle((cx, cy, cx + 60, cy + 60), outline=pen, width=3)
    d.rectangle((cx + 22, cy - 22, cx + 82, cy + 38), outline=pen, width=3)
    for (a, b) in (((cx, cy), (cx + 22, cy - 22)), ((cx + 60, cy), (cx + 82, cy - 22)), ((cx + 60, cy + 60), (cx + 82, cy + 38)), ((cx, cy + 60), (cx + 22, cy + 38))):
        d.line([a, b], fill=pen, width=3)
    # scribble being drawn now
    n = int(10 + 120 * min(1.0, t / 1.5))
    pts = scribble_pts(n)
    d.line(pts, fill=pen, width=3, joint='curve')
    return pg, pts[-1]


S5_BG = None


def scene5(t):
    global S5_BG
    if S5_BG is None:
        S5_BG = make_s5_bg()
    img = S5_BG.copy()
    pg, tip = page_im(t)
    ang = -4
    sway = 3 * math.sin(t * 2.2)
    pg_r = pg.rotate(ang + sway * 0.3, resample=Image.BICUBIC, expand=True)
    ox, oy = 150 - (pg_r.width - pg.width) // 2, 560 - (pg_r.height - pg.height) // 2 + int(sway)
    drop_shadow(img, pg_r, (ox, oy), off=(14, 18), blur=12, op=0.55)
    img.alpha_composite(pg_r, (ox, oy))
    # map pencil tip from page coords to screen
    th = math.radians(-(ang + sway * 0.3))
    c = np.array([pg.width / 2, pg.height / 2])
    v = np.array(tip) - c
    tip_s = np.array([ox + pg_r.width / 2, oy + pg_r.height / 2]) + np.array([v[0] * math.cos(th) - v[1] * math.sin(th), v[0] * math.sin(th) + v[1] * math.cos(th)])
    sk = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    # pencil
    pd = ImageDraw.Draw(sk)
    back = tip_s + 300 * dirv(-50)
    nrm = dirv(40) * 11
    pd.polygon([tuple(tip_s), tuple(tip_s + 40 * dirv(-50) + nrm), tuple(back + nrm), tuple(back - nrm), tuple(tip_s + 40 * dirv(-50) - nrm)], fill=(214, 166, 92, 255))
    pd.polygon([tuple(tip_s), tuple(tip_s + 40 * dirv(-50) + nrm), tuple(tip_s + 40 * dirv(-50) - nrm)], fill=(236, 200, 150, 255))
    pd.polygon([tuple(tip_s), tuple(tip_s + 12 * dirv(-50) + nrm * 0.3), tuple(tip_s + 12 * dirv(-50) - nrm * 0.3)], fill=(40, 40, 44, 255))
    # writing hand (bony) gripping the pencil
    s = 1.6
    hand_tip = tip_s + 70 * dirv(-50)
    wr = hand_tip + 150 * dirv(-30)
    rig.bone(sk, S, 'handR_f', wr, hand_tip, s)
    rig.bone(sk, S, 'forR_f', wr + 230 * dirv(-10), wr, s)
    # other hand holding the notebook (bottom-left)
    rig.bone(sk, S, 'handL_f', np.array([110.0, 1290.0]), np.array([200.0, 1130.0 + sway]), s)
    rig.bone(sk, S, 'forL_f', np.array([40.0, 1500.0]), np.array([110.0, 1290.0]), s)
    sk = brighten(sk, 1.3, 14)
    img.alpha_composite(layer_shadow(sk, 18, 20, 10, 0.4))
    img.alpha_composite(sk)
    return post(img, int(t * 30) + 800, grade=(1.0, 0.97, 0.94), vign=0.45)


# ================================================================== scene 6: at the window with a mug
def make_s6_bg():
    img = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    wall = np.array([120, 104, 118], np.float32)
    yy, xx = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32)
    w_ = wall * (0.7 + 0.3 * noise(W // 4, H // 4, 3, 31))[..., None] * (0.8 + 0.3 * (xx / (W // 4)))[..., None]
    img.paste(pixup(to_img(w_), (W, H)))
    x0, y0, x1, y1 = 190, 120, 760, 1240
    img.paste(istanbul(x1 - x0, y1 - y0, px=5, horizon=0.66, mosques=((0.60, 1.0), (0.95, 0.55)), galata=0.28, bridge=0.85, maiden=0.42, seed=11), (x0, y0))
    d = ImageDraw.Draw(img)
    fr = (236, 228, 234)
    d.rectangle((x0 - 24, y0 - 24, x1, y0), fill=fr)
    d.rectangle((x0 - 24, y0, x0, y1), fill=fr)
    for x in (x0 + 190, x0 + 380):
        d.rectangle((x - 9, y0, x + 9, y1), fill=fr)
    d.rectangle((x0, 560, x1, 578), fill=fr)
    d.rectangle((x0 - 30, 1040, x1, 1080), fill=(214, 204, 212))
    glow = Image.new('L', (W, H), 0)
    ImageDraw.Draw(glow).rectangle((x0, y0, x1, y1), fill=110)
    glow = glow.filter(ImageFilter.GaussianBlur(70))
    img = Image.composite(Image.new('RGBA', (W, H), (255, 200, 230, 255)), img, glow)
    return img


S6_BG = None


def mug_im():
    m = Image.new('RGBA', (70, 76), (0, 0, 0, 0))
    d = ImageDraw.Draw(m)
    d.rounded_rectangle((0, 6, 52, 76), 8, fill=(236, 234, 238, 255))
    d.ellipse((0, 0, 52, 14), fill=(90, 50, 30, 255))
    d.arc((40, 22, 70, 58), -90, 90, fill=(236, 234, 238, 255), width=8)
    a = np.asarray(m).astype(np.float32)
    a[..., :3] *= (0.6 + 0.5 * np.linspace(0, 1, 70))[None, :, None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')


MUG = None


def scene6(t):
    global S6_BG, MUG
    if S6_BG is None:
        S6_BG, MUG = make_s6_bg(), mug_im()
    img = S6_BG.copy()
    s = 1.45
    br = math.sin(t * 2 * math.pi / 3.2)
    neck = np.array([196.0, 452.0 + 2 * br])
    hip = neck + np.array([22 * s, 322 * s])
    sk = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    torso(sk, S, 'side_full', neck, hip, s, SIDE)
    # near arm brings the mug forward; small sip lift at ~1.4-2.4 s
    lift = smooth((t - 1.3) / 0.5) * (1 - smooth((t - 2.4) / 0.5))
    sh = tpt(neck, hip, SIDE, SIDE['sh'], s)
    up = blen(SIDE, 'sh', 'el') * s
    fo = blen(SIDE, 'el', 'wr') * s
    ha = blen(SIDE, 'wr', 'tip') * s
    el = sh + up * dirv(95)
    wr = el + fo * dirv(-12 - 40 * lift)
    tip = wr + ha * 0.7 * dirv(-30 - 30 * lift)
    rig.bone(sk, S, 'hum_s', sh, el, s)
    rig.bone(sk, S, 'for_s', el, wr, s)
    mug = MUG.resize((98, 106), Image.BICUBIC).rotate(-25 * lift, resample=Image.BICUBIC, expand=True)
    sk.alpha_composite(mug, (int(wr[0] + 18), int(wr[1] - 70)))
    rig.bone(sk, S, 'hand_s', wr, tip, s)
    sk = brighten(sk, 1.3, 14, tint=(1.04, 0.96, 1.0))
    # pink rim light from the window side
    a = np.asarray(sk).astype(np.float32)
    al = a[..., 3] / 255
    edge = np.clip(al - np.roll(al, 6, axis=1), 0, 1)
    a[..., 0] += edge * 90; a[..., 1] += edge * 50; a[..., 2] += edge * 80
    sk = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')
    img.alpha_composite(sk)
    # slow push-in
    z = 1 + 0.05 * (t / 3.3)
    cw, ch = int(W / z), int(H / z)
    img = img.crop((int((W - cw) * 0.3), int((H - ch) * 0.4), int((W - cw) * 0.3) + cw, int((H - ch) * 0.4) + ch)).resize((W, H), Image.BICUBIC)
    return post(img, int(t * 30) + 1000, grade=(1.0, 0.95, 1.0), vign=0.5)
