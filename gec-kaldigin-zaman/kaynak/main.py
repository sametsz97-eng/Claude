import sys, os
from multiprocessing import Pool
from PIL import Image
import scenes

FPS = 30
DUR = 8.0
CUTS = [(0.0, scenes.scene_a), (1.53, scenes.scene_b), (3.0, scenes.scene_c), (6.03, scenes.scene_d)]


def render(t):
    st, fn = [c for c in CUTS if c[0] <= t][-1]
    return fn(t - st)


def frame(i):
    t = i / FPS
    im = render(t)
    if t > DUR - 0.5:
        k = max(0.0, (DUR - t) / 0.5)
        im = Image.eval(im, lambda v: int(v * k))
    im.save(f'frames/f_{i:04d}.png')
    return i


if __name__ == '__main__':
    os.makedirs('frames', exist_ok=True)
    if len(sys.argv) > 2 and sys.argv[1] == 'test':
        for t in map(float, sys.argv[2:]):
            render(t).save(f'test_{t:05.2f}.png')
        sys.exit()
    n = int(DUR * FPS)
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 4) as p:
        for _ in p.imap_unordered(frame, range(n), chunksize=8):
            pass
    print('done', n)
