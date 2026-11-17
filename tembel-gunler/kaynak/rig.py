"""Cut-out skeleton rig built from the character sheet (front / back / side views)."""
import math
import numpy as np
from PIL import Image, ImageFilter

SRC = '/root/.claude/uploads/5b3cb9ae-c2e8-5f6d-b2b9-f7062ebc6a0d/e70de43e-image.png'
IM = Image.open(SRC).convert('RGB')
A = np.asarray(IM).astype(np.float32)
LUM = A[..., 0] * .3 + A[..., 1] * .55 + A[..., 2] * .15


def _flood_bg(low):
    bg = np.zeros_like(low)
    bg[0], bg[-1], bg[:, 0], bg[:, -1] = low[0], low[-1], low[:, 0], low[:, -1]
    while True:
        n = bg.copy()
        n[1:] |= bg[:-1]; n[:-1] |= bg[1:]; n[:, 1:] |= bg[:, :-1]; n[:, :-1] |= bg[:, 1:]
        n &= low
        if (n == bg).all():
            return bg
        bg = n


def cut(box, lo=29, hi=37, gamma=1.0, kill=None, fill=False, protect=None, feather=0.7):
    x0, y0, x1, y1 = box
    a = A[y0:y1, x0:x1]
    lum = LUM[y0:y1, x0:x1]
    if fill:
        low = lum < lo
        if protect is not None:
            yy, xx = np.mgrid[y0:y1, x0:x1]
            for (cx, cy, rx, ry) in protect:
                low &= ~(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 < 1)
        al = np.where(_flood_bg(low), 0.0, 1.0).astype(np.float32)
    else:
        al = np.clip((lum - lo) / (hi - lo), 0, 1) ** gamma
    if kill is not None:
        yy, xx = np.mgrid[y0:y1, x0:x1]
        al = al * kill(xx, yy)
    alpha = Image.fromarray((al * 255).astype(np.uint8))
    if feather:
        alpha = alpha.filter(ImageFilter.GaussianBlur(feather))
    rgb = Image.fromarray(a.astype(np.uint8))
    rgb.putalpha(alpha)
    return rgb, (x0, y0)


def seg_box(a, b, hw=24, pad=8):
    return (int(min(a[0], b[0]) - hw), int(min(a[1], b[1]) - pad), int(max(a[0], b[0]) + hw), int(max(a[1], b[1]) + pad))


# ------------------------------------------------------------------ landmarks (sheet coords)
FRONT = dict(
    neck=(205, 128), hipc=(197, 452),
    shR=(96, 190), elR=(95, 364), wrR=(80, 503), tipR=(78, 612),
    shL=(310, 190), elL=(311, 364), wrL=(324, 503), tipL=(326, 612),
    hipR=(130, 470), knR=(130, 683), anR=(128, 932), toeR=(125, 1045),
    hipL=(262, 470), knL=(258, 683), anL=(258, 932), toeL=(262, 1045),
)
BACK = dict(
    neck=(730, 118), hipc=(732, 445),
    shL=(640, 192), elL=(641, 358), wrL=(645, 498), tipL=(640, 584),
    shR=(818, 192), elR=(820, 358), wrR=(824, 498), tipR=(830, 584),
    hipL=(697, 468), knL=(690, 683), anL=(688, 962), toeL=(690, 1030),
    hipR=(768, 468), knR=(776, 683), anR=(778, 962), toeR=(778, 1030),
)
SIDE = dict(neck=(478, 118), hipc=(500, 440), sh=(484, 192), el=(488, 368), wr=(494, 500), tip=(505, 592))
SKULL_CU = dict(chin=(1047, 262), crown=(1047, 30))     # close-up front skull with moustache
SKULL_BK = dict(chin=(730, 112), crown=(730, 24))       # back of the head
SKULL_SD = dict(chin=(500, 112), crown=(492, 24))       # side skull (faces right)


def _kill_front_torso(X, Y):
    k = np.ones(X.shape, np.float32)
    k[(Y > 205) & ((X < 121) | (X > 289))] = 0
    k[(Y > 185) & ((X < 100) | (X > 302))] = 0
    k[(Y > 470)] = 0
    return k


def _kill_back_torso(X, Y):
    k = np.ones(X.shape, np.float32)
    k[(Y > 205) & ((X < 656) | (X > 806))] = 0
    k[(Y > 470)] = 0
    return k


def build():
    S = {}
    S['torso_f'] = cut((95, 118, 312, 490), lo=31, hi=40, gamma=0.7, kill=_kill_front_torso)
    S['torso_b'] = cut((625, 96, 835, 490), lo=31, hi=40, gamma=0.7, kill=_kill_back_torso)
    S['skull_cu'] = cut((955, 22, 1140, 270), lo=33, fill=True, protect=[(1047, 207, 64, 21)], feather=1.0)
    S['skull_bk'] = cut((688, 18, 774, 116), lo=31, hi=40)
    S['side_full'] = cut((430, 18, 580, 1060), lo=31, hi=40, gamma=0.8)
    S['side_upper'] = cut((430, 18, 580, 600), lo=31, hi=40, gamma=0.8)
    for view, L in (('f', FRONT), ('b', BACK)):
        for s in 'LR':
            for name, a, b, hw in (('hum', 'sh', 'el', 20), ('for', 'el', 'wr', 22), ('hand', 'wr', 'tip', 26),
                                   ('fem', 'hip', 'kn', 26), ('shin', 'kn', 'an', 24), ('foot', 'an', 'toe', 40)):
                pa, pb = L[a + s], L[b + s]
                box = seg_box(pa, pb, hw)
                if name == 'hum':
                    box = (box[0], box[1] + 6, box[2], box[3])
                S[f'{name}{s}_{view}'] = (cut(box), pa, pb)
    for name, a, b, hw in (('hum', 'sh', 'el', 20), ('for', 'el', 'wr', 20), ('hand', 'wr', 'tip', 26)):
        S[f'{name}_s'] = (cut(seg_box(SIDE[a], SIDE[b], hw)), SIDE[a], SIDE[b])
    return S


# ------------------------------------------------------------------ placement
def rot(th):
    c, s = math.cos(th), math.sin(th)
    return np.array([[c, -s], [s, c]])


def place(dst, sprite, M, src_anchor, dst_anchor, alpha=1.0):
    img, (ox, oy) = sprite
    sw, sh = img.size
    src = np.array(src_anchor, float)
    D = np.array(dst_anchor, float)
    corners = np.array([[ox, oy], [ox + sw, oy], [ox, oy + sh], [ox + sw, oy + sh]], float)
    sc = (M @ (corners - src).T).T + D
    x0, y0 = np.floor(sc.min(0)).astype(int) - 2
    x1, y1 = np.ceil(sc.max(0)).astype(int) + 2
    W, H = dst.size
    if x1 < 0 or y1 < 0 or x0 > W or y0 > H:
        return
    Mi = np.linalg.inv(M)
    off = src - np.array([ox, oy]) + Mi @ (np.array([x0, y0], float) - D)
    patch = img.transform((x1 - x0, y1 - y0), Image.AFFINE,
                          (Mi[0, 0], Mi[0, 1], off[0], Mi[1, 0], Mi[1, 1], off[1]), resample=Image.BICUBIC)
    if alpha < 1:
        patch.putalpha(patch.getchannel('A').point(lambda v: int(v * alpha)))
    cx, cy = max(0, -x0), max(0, -y0)
    patch = patch.crop((cx, cy, patch.width, patch.height))
    dst.alpha_composite(patch, (int(x0 + cx), int(y0 + cy)))


def seg_matrix(a, b, src_a, src_b, width=1.0):
    """similarity-ish matrix mapping src segment onto screen segment; width scales the cross axis."""
    sv = np.subtract(src_b, src_a).astype(float)
    dv = np.subtract(b, a).astype(float)
    ls, ld = np.linalg.norm(sv), max(np.linalg.norm(dv), 1e-3)
    u = sv / ls
    n = np.array([-u[1], u[0]])
    k = ld / ls
    S = k * np.outer(u, u) + width * np.outer(n, n)
    ang = math.atan2(dv[1], dv[0]) - math.atan2(sv[1], sv[0])
    return rot(ang) @ S


def bone(dst, S, key, a, b, width):
    """draw bone sprite `key` from screen point a to b. `width` = absolute cross-scale."""
    sp, sa, sb = S[key]
    place(dst, sp, seg_matrix(a, b, sa, sb, width), sa, a)


def limb(dst, S, view, side, kind, pts, width):
    names = ('hum', 'for', 'hand') if kind == 'arm' else ('fem', 'shin', 'foot')
    for n, a, b in zip(names, pts[:-1], pts[1:]):
        bone(dst, S, f'{n}{side}_{view}', a, b, width)


def torso(dst, S, key, neck, hip, width, src):
    sp = S[key]
    M = seg_matrix(neck, hip, src['neck'], src['hipc'], width)
    place(dst, sp, M, src['neck'], neck)


def skull(dst, S, key, chin, angle, size, src):
    """angle: direction chin->crown in radians (screen), size: chin->crown length in px."""
    sp = S[key]
    crown = np.array(chin) + size * np.array([math.cos(angle), math.sin(angle)])
    sv = np.subtract(src['crown'], src['chin'])
    k = size / np.linalg.norm(sv)
    M = seg_matrix(chin, crown, src['chin'], src['crown'], k)
    place(dst, sp, M, src['chin'], chin)


def ik(sh, target, l1, l2, bend):
    sh = np.array(sh, float); target = np.array(target, float)
    d = target - sh
    dist = float(np.clip(np.linalg.norm(d), abs(l1 - l2) + 1e-3, l1 + l2 - 1e-3))
    base = math.atan2(d[1], d[0])
    ca = (l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist)
    a = math.acos(max(-1, min(1, ca)))
    el = sh + l1 * np.array([math.cos(base + bend * a), math.sin(base + bend * a)])
    return el, sh + d / max(np.linalg.norm(d), 1e-6) * dist


def blen(L, a, b):
    return float(np.linalg.norm(np.subtract(L[b], L[a])))
