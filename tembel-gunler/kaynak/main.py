import sys, os
from multiprocessing import Pool
import scenes
from common import W, H
from PIL import Image
FPS = 30
DUR = 21.5
CUTS = [(0.0, scenes.scene1), (4.5, scenes.scene2), (9.0, scenes.scene3), (13.5, scenes.scene4), (16.3, scenes.scene5), (18.0, scenes.scene6)]


def frame(i):
    t = i / FPS
    st, fn = [c for c in CUTS if c[0] <= t][-1]
    im = fn(t - st)
    if t > DUR - 0.3:
        k = max(0.0, (DUR - t) / 0.3)
        im = Image.eval(im, lambda v: int(v * k))
    im.save(f'frames/f_{i:04d}.png')
    return i


if __name__ == '__main__':
    os.makedirs('frames', exist_ok=True)
    n = int(round(DUR * FPS))
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 4) as p:
        for i in p.imap_unordered(frame, range(n), chunksize=8):
            pass
    print('done', n)
