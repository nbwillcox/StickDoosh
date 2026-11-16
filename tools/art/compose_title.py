"""Compose title candidates d/e/f from generated parts (cut-out dudes on white + an explosion background).

  python tools/art/compose_title.py            # writes assets/raw_art/title_d|e|f.png (+webp, scores)

Layout is built around the real title screen: the CSS logo sits in the calm upper area and the 330px menu column
covers the middle ~20% of the picture, so the squad is packed into two groups (3 left, 2 right) beside the menu,
inside the central 75% of the width (a 4:3 window crops 12.5% off each side with background-size: cover).
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import artlib as A  # noqa: E402
from art_defs import ITEMS  # noqa: E402

W, H = 1280, 720
FEET = 696
# (id, centre x, feet y, height, flip). The left group is mirrored so everybody charges toward the middle.
# Sprites are drawn back to front (by feet y); the middle 512..768 stays clear for the menu column.
LAYOUT = [   # back row stands higher (feet at ~650) so heads peek over the front row, group-photo style
    ('gramps', 235, 650, 300, True),
    ('pete', 335, 714, 205, True),
    ('sgt', 420, 706, 345, True),
    ('major', 1040, 652, 315, False),
    ('brenda', 900, 706, 350, False),
]


def cutout(path):
    im = Image.open(path).convert('RGB')
    a = np.asarray(im)
    near_white = a.min(axis=2) > 232
    lab, n = ndi.label(near_white)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    bg = np.isin(lab, list(border))
    fg = ~bg
    fg = ndi.binary_opening(fg, iterations=1)
    lab2, n2 = ndi.label(fg)
    if n2:
        sizes = ndi.sum(fg, lab2, range(1, n2 + 1))
        keep = [i + 1 for i, s in enumerate(sizes) if s >= max(60, 0.004 * fg.size)]
        fg = np.isin(lab2, keep)
    fg = ndi.binary_fill_holes(fg)
    fg = ndi.binary_erosion(fg, iterations=1)
    alpha = ndi.gaussian_filter(fg.astype(np.float32), 0.8)
    rgba = np.dstack([a, (np.clip(alpha, 0, 1) * 255).astype(np.uint8)])
    out = Image.fromarray(rgba, 'RGBA')
    bb = out.getchannel('A').point(lambda v: 255 if v > 100 else 0).getbbox()
    return out.crop(bb)


def scaled(img, height):
    s = height / img.height
    return img.resize((max(1, int(img.width * s)), height), Image.LANCZOS)


# which way each generated dude faces (read off the images: gun/muzzle flash side)
FACE = {('sgt', 'a'): 'L', ('sgt', 'b'): 'R', ('pete', 'a'): 'L', ('pete', 'b'): 'L',
        ('brenda', 'a'): 'L', ('brenda', 'b'): 'R', ('major', 'a'): 'L', ('major', 'b'): 'R',
        ('gramps', 'a'): 'R', ('gramps', 'b'): 'L'}


def procedural_bg(variant):
    """Comic sunburst + halftone + jagged explosion bursts, no characters (the generated backdrops a-d kept
    drawing little stick people into the empty scene). 'p' = yellow, 'q' = red sunset. Drawn at 2x, downsampled."""
    import math
    import random
    rnd = random.Random(7 if variant == 'p' else 11)
    S = 2
    w, h = W * S, H * S
    c1, c2 = ((255, 225, 77), (255, 177, 26)) if variant == 'p' else ((255, 196, 51), (255, 90, 42))
    cx, cy = w // 2, int(h * 0.64)
    im = Image.new('RGB', (w, h), c1)
    d = ImageDraw.Draw(im)
    n, R = 30, w * 1.2
    for k in range(n):
        if k % 2:
            continue
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        d.polygon([(cx, cy), (cx + R * math.cos(a0), cy + R * math.sin(a0)), (cx + R * math.cos(a1), cy + R * math.sin(a1))], fill=c2)
    a = np.asarray(im).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dist = np.hypot(xx - cx, (yy - cy) * 1.25)
    dn = dist / dist.max()
    glow = np.clip(1.0 - dn * 2.4, 0, 1)[..., None] ** 1.5
    a = a * (1 - 0.8 * glow) + 255 * 0.8 * glow
    sp = 9 * S                                   # halftone dots, bigger toward the edges
    ux, uy = (xx + yy) * 0.7071, (xx - yy) * 0.7071
    gx, gy = (ux % sp) - sp / 2, (uy % sp) - sp / 2
    r = sp * 0.62 * np.clip((dn - 0.18) / 0.8, 0, 1) ** 0.9
    dots = (np.hypot(gx, gy) < r)[..., None]
    shade = np.array([226, 84, 18], np.float32) if variant == 'p' else np.array([176, 28, 24], np.float32)
    a = np.where(dots, a * 0.45 + shade * 0.55, a)
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    gy0 = int(h * 0.795)                         # ground strip + ink line
    d.rectangle([0, gy0, w, h], fill=(255, 244, 208))
    d.line([(0, gy0), (w, gy0)], fill=(20, 16, 24), width=7 * S)
    for gx0, gw in ((90, 150), (430, 90), (780, 120), (1100, 130)):   # speed dashes on the ground
        d.line([(gx0 * S, int(h * 0.93)), ((gx0 + gw) * S, int(h * 0.93))], fill=(226, 205, 160), width=5 * S)

    def burst(bx, by, rad, fills):
        spikes = 15
        for sc, col in fills:
            pts = []
            for i in range(spikes * 2):
                ang = math.pi * i / spikes + 0.3
                rr = rad * sc * (1.0 if i % 2 == 0 else 0.55) * (0.82 + 0.3 * rnd.random())
                pts.append((bx + rr * math.cos(ang), by + rr * 0.92 * math.sin(ang)))
            d.polygon(pts, fill=col, outline=(20, 16, 24), width=5 * S)

    for bx, by, rad in ((165, 482, 150), (1115, 482, 150), (640, 505, 112)):
        burst(bx * S, by * S, rad * S, [(1.0, (255, 106, 26)), (0.72, (255, 214, 10)), (0.4, (255, 255, 240))])
    for _ in range(16):                          # debris chunks
        px, py = rnd.choice((rnd.uniform(40, 330), rnd.uniform(950, 1240))), rnd.uniform(250, 520)
        s = rnd.uniform(9, 20) * S
        ang = rnd.uniform(0, math.pi)
        pts = [(px * S + s * math.cos(ang + k * math.pi / 2) * (1.0 if k % 2 else 1.7),
                py * S + s * math.sin(ang + k * math.pi / 2) * (1.0 if k % 2 else 1.7)) for k in range(4)]
        d.polygon(pts, fill=rnd.choice(((255, 106, 26), (60, 56, 70), (255, 60, 40))), outline=(20, 16, 24), width=3 * S)
    out = im.resize((W, H), Image.LANCZOS)
    out.save(A.raw_png('part_bg', variant))
    return out


def compose(take, dtake, bgtake):
    parts = {}
    for i in ('gramps', 'sgt', 'pete', 'major', 'brenda'):
        p = A.raw_png('part_' + i, dtake.get(i, 'a'))
        if not os.path.exists(p):
            raise SystemExit('missing part ' + p)
        parts[i] = cutout(p)
    if bgtake in ('p', 'q'):
        canvas = procedural_bg(bgtake).convert('RGBA')
    else:
        bgp = A.raw_png('part_bg', bgtake)
        if not os.path.exists(bgp):
            raise SystemExit('missing part ' + bgp)
        canvas = Image.open(bgp).convert('RGBA').resize((W, H), Image.LANCZOS)
    for i, cx, feet, h, flip in sorted(LAYOUT, key=lambda t: t[2]):
        s = scaled(parts[i], h)
        want = 'R' if flip else 'L'      # left group charges right, right group charges left
        if FACE[(i, dtake.get(i, 'a'))] != want:
            s = s.transpose(Image.FLIP_LEFT_RIGHT)
        x, y = int(cx - s.width / 2), int(feet - s.height)
        # sprites carry their own baked-in ground shadow; just clip anything poking out of the canvas
        canvas.alpha_composite(s, (max(0, x), max(0, y)), (max(0, -x), max(0, -y)))
    out = A.raw_png('title', take)
    canvas.convert('RGB').save(out)
    return out


def main():
    it = ITEMS['title']
    recipes = {   # take -> (which take of each dude, which background)
        'd': ({}, 'p'),
        'e': ({i: 'b' for i in ('gramps', 'sgt', 'pete', 'major', 'brenda')}, 'p'),
        'f': ({'sgt': 'b', 'brenda': 'b'}, 'q'),
    }
    if '--bg' in sys.argv:   # force one backdrop take for all recipes (testing)
        bg = sys.argv[sys.argv.index('--bg') + 1]
        recipes = {k: (v[0], bg) for k, v in recipes.items()}
    for take, (dt, bgt) in recipes.items():
        try:
            compose(take, dt, bgt)
        except SystemExit as e:
            print('skip', take, e)
            continue
        m = A.register('title', take, it)
        print('title_%s composed  score %.2f edge_mid=%.3f edge_sides=%.3f top=%.3f bot=%.3f' % (
            take, m['score'], m['edge_mid'], m['edge_sides'], m['edge_top'], m['edge_bot']))


if __name__ == '__main__':
    main()
