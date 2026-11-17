import numpy as np
from PIL import Image, ImageFilter

SRC = '/root/.claude/uploads/5b3cb9ae-c2e8-5f6d-b2b9-f7062ebc6a0d/e70de43e-image.png'
IM = Image.open(SRC).convert('RGB')
A = np.asarray(IM).astype(np.float32)


def cut(box, lo=30, hi=50, rowfill=False, kill=None, feather=0.8, gamma=1.0):
    """Cut an RGBA sprite from the sheet. Alpha from luminance threshold.
    Returns (sprite, (x0,y0)) so callers can use original-image coords."""
    x0, y0, x1, y1 = box
    a = A[y0:y1, x0:x1]
    lum = a[..., 0] * .3 + a[..., 1] * .55 + a[..., 2] * .15
    al = np.clip((lum - lo) / (hi - lo), 0, 1)
    if rowfill:
        # background = low-lum region connected to the crop border; everything else is opaque
        low = lum < lo
        yy, xx = np.mgrid[y0:y1, x0:x1]
        low &= ~(((xx - 1047) / 64.0) ** 2 + ((yy - 207) / 21.0) ** 2 < 1)  # keep the moustache
        bg = np.zeros_like(low); bg[0, :] = low[0, :]; bg[-1, :] = low[-1, :]; bg[:, 0] = low[:, 0]; bg[:, -1] = low[:, -1]
        while True:
            n = bg.copy()
            n[1:] |= bg[:-1]; n[:-1] |= bg[1:]; n[:, 1:] |= bg[:, :-1]; n[:, :-1] |= bg[:, 1:]
            n &= low
            if (n == bg).all(): break
            bg = n
        al = np.where(bg, 0.0, 1.0).astype(np.float32)
    if kill is not None:
        al *= kill(np.arange(x0, x1)[None, :], np.arange(y0, y1)[:, None])
    al = al ** gamma
    alpha = Image.fromarray((al * 255).astype(np.uint8))
    if feather:
        alpha = alpha.filter(ImageFilter.GaussianBlur(feather))
    rgb = Image.fromarray(a.astype(np.uint8))
    rgb.putalpha(alpha)
    return rgb, (x0, y0)


def torso_kill(X, Y):
    # remove arm pixels that sit beside the ribcage below the shoulders
    k = np.ones(np.broadcast(X, Y).shape, np.float32)
    k[np.broadcast_to((Y > 205) & ((X < 121) | (X > 289)), k.shape)] = 0
    k[np.broadcast_to((Y > 185) & ((X < 100) | (X > 302)), k.shape)] = 0
    k[np.broadcast_to((Y > 330) & ((X < 135) | (X > 278)), k.shape)] = 0
    return k


def build():
    S = {}
    S['torso'] = cut((95, 118, 312, 490), lo=31, hi=40, kill=torso_kill, gamma=0.7)
    # close-up skull with moustache (row-filled so dark sockets / moustache stay opaque)
    def skull_kill(X, Y):
        k = np.ones(np.broadcast(X, Y).shape, np.float32)
        k[np.broadcast_to(Y > 268, k.shape)] = 0
        return k
    S['skull'] = cut((955, 22, 1140, 272), lo=33, hi=40, rowfill=True, kill=skull_kill, feather=1.2)
    # arms (image-left = skeleton's right, image-right = skeleton's left)
    S['humR'] = cut((72, 178, 118, 372), lo=29, hi=37)
    S['forR'] = cut((58, 362, 112, 508), lo=29, hi=37)
    S['handR'] = cut((48, 500, 104, 618), lo=29, hi=37)
    S['humL'] = cut((290, 178, 336, 372), lo=29, hi=37)
    S['forL'] = cut((296, 362, 350, 508), lo=29, hi=37)
    S['handL'] = cut((298, 500, 352, 618), lo=29, hi=37)
    return S


# joint landmarks in original-image coordinates
J = dict(
    neck=(205, 128), chin_skull=(1047, 262), crown_skull=(1047, 30),
    shR=(96, 190), elR=(95, 364), wrR=(80, 503), tipR=(78, 612),
    shL=(310, 190), elL=(311, 364), wrL=(324, 503), tipL=(326, 612),
)

if __name__ == '__main__':
    S = build()
    for k, (sp, o) in S.items():
        bg = Image.new('RGBA', sp.size, (60, 160, 60, 255))
        bg.alpha_composite(sp)
        bg.save(f'sp_{k}.png')
