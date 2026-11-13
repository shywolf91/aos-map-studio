"""Opt-in floating sky decor (owner rule: only when asked).

Merged from wkh_sky / sph_sky (moon, flock silhouettes, _stamp with diagonal-join fill, _place search, sky_objects
records) and Bloomhop main.sky_decor (clouds). Placement rules [USER]: >= 60 voxels from the platform, never over
a spawn square, >= 8 voxels of air below, placed AFTER mirroring and orphan cleanup. Each piece is recorded in
cv.expect_floating so checks list it as expected. Collapse caveat: a player block touching a piece, once broken,
drops the whole piece for the rest of the round.
"""
from __future__ import annotations

import math

import numpy as np

from .params import BABEL_DEFAULT

BIRD_SHAPE = ['......b......',
              '......#......',
              '#############',
              '#.#.##.##.#.#',
              '.....###.....',
              '.....#.#.....']
BAT_SHAPE = ['......#.#......',
             '###..#e#e#..###',
             '###############',
             '.###..###..###.',
             '..#...#.#...#..']


class _Probe:
    def __init__(self):
        self.pts = []

    def set(self, x, y, z, c, mat=None):
        self.pts.append((int(x), int(y), int(z)))


def stamp(target, shape, x, y, z, heading, colours, tips_up=1):
    """2D silhouette in the horizontal plane, rotated to `heading` (radians). colours: {'#': rgb, 'b': rgb, ...}."""
    fx, fy = math.cos(heading), math.sin(heading)
    sx, sy = -fy, fx
    rows, cols = len(shape), len(shape[0])
    pts = []
    for i, row in enumerate(shape):
        f = rows // 2 - i
        for j, ch in enumerate(row):
            if ch == '.':
                continue
            w = j - cols // 2
            px, py = int(round(x + f * fx + w * sx)), int(round(y + f * fy + w * sy))
            pts.append((px, py, z, colours.get(ch, colours['#'])))
            if tips_up and abs(w) >= cols // 2 - tips_up + 1:
                pts.append((px, py, z - 1, colours['#']))
    have = {(p[0], p[1]) for p in pts}
    for (px, py, pz, c) in list(pts):                       # fill diagonal-only joins -> one component
        for (dx, dy) in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            if (px + dx, py + dy) in have and (px + dx, py) not in have and (px, py + dy) not in have:
                pts.append((px + dx, py, z, colours['#']))
                have.add((px + dx, py))
    for (a, b, c_, col) in pts:
        target.set(a, b, c_, col, 'sky')
    return [p[:3] for p in pts]


def moon(target, cx, cy, zc, R=15.0, r=13.0, offset=7.0, thick=2, face=(256, 256),
         body=(232, 226, 200), rim=(250, 246, 226), dark=(198, 192, 170)):
    nx, ny = face[0] - cx, face[1] - cy
    L = math.hypot(nx, ny) or 1.0
    nx, ny = nx / L, ny / L
    ux, uy = -ny, nx
    vox = {}
    a = -R
    while a <= R:
        b = -R
        while b <= R:
            if a * a + b * b <= R * R and (a - offset) ** 2 + (b + 2.0) ** 2 > r * r:
                for t in range(thick):
                    x = int(round(cx + a * ux + (t - 0.5) * nx))
                    y = int(round(cy + a * uy + (t - 0.5) * ny))
                    z = int(round(zc - b))
                    crater = math.hypot(a + 9, b - 6) < 3.2 or math.hypot(a + 12, b + 7) < 2.4
                    vox[(x, y, z)] = dark if crater else (rim if R - math.hypot(a, b) < 1.3 else body)
            b += 0.5
        a += 0.5
    for (x, y, z), c in vox.items():
        target.set(x, y, z, c, 'sky')
    return list(vox)


def cloud(target, cx, cy, cz, length, seed=0, top=(234, 236, 242), bottom=(198, 206, 226)):
    """Puffy cloud; `seed` (int) fixes its shape so a probe placement and the real one match."""
    rng = np.random.default_rng(seed)
    pts = []
    n = int(rng.integers(4, 6))
    for k in range(n):
        ox = (k - (n - 1) / 2) * length / n + rng.uniform(-1, 1)
        oy = rng.uniform(-2, 2)
        r = length / n * rng.uniform(0.8, 1.15)
        rz = r * 0.62
        for x in range(int(cx + ox - r - 1), int(cx + ox + r + 2)):
            for y in range(int(cy + oy - r - 1), int(cy + oy + r + 2)):
                for z in range(int(cz - rz - 1), int(cz + rz + 2)):
                    d = ((x - cx - ox) / r) ** 2 + ((y - cy - oy) / (r * 0.8)) ** 2 + ((z - cz) / rz) ** 2
                    if d <= 1:
                        t = min(1.0, max(0.0, (z - (cz - rz)) / (2 * rz)))
                        c = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
                        target.set(x, y, z, c, 'sky')
                        pts.append((x, y, z))
    return pts


def _clear(cv, pts, margin=2):
    a = np.array(pts)
    x0, y0, z0 = a.min(0) - margin
    x1, y1, z1 = a.max(0) + margin
    if z0 < 2 or x0 < 0 or y0 < 0 or x1 > 511 or y1 > 511 or z1 > 61:
        return False
    return not cv.solid[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1].any()


def rule_check(pts, cv=None, params=BABEL_DEFAULT, min_platform=60, min_air=8):
    a = np.array(pts)
    (x0, x1), (y0, y1) = params['platform_x'], params['platform_y']
    bx0, bx1, by0, by1 = a[:, 0].min(), a[:, 0].max(), a[:, 1].min(), a[:, 1].max()
    dx = max(x0 - bx1, bx0 - x1, 0)
    dy = max(y0 - by1, by0 - y1, 0)
    h = params['spawn_half']
    over = any(not (bx1 < bx - h or bx0 > bx + h or by1 < by - h or by0 > by + h) for bx, by in params['bases'])
    air = 64
    if cv is not None:
        zb = a[:, 2].max()
        for x in range(bx0, bx1 + 1):
            for y in range(by0, by1 + 1):
                below = np.nonzero(cv.solid[x, y, zb + 1:])[0]
                if len(below):
                    air = min(air, int(below[0]))
    return {'platform_dist': round(float(math.hypot(dx, dy)), 1), 'over_spawn_square': bool(over),
            'air_below_min': air, 'ok': math.hypot(dx, dy) >= min_platform and not over and air >= min_air}


def place(cv, name, fn, x, y, z, *args, params=BABEL_DEFAULT, **kw):
    """fn(target, x, y, z, *args, **kw) -> points (moon, cloud, bird, bat or your own).
    Place a floating piece at the nearest spot (searching outward/up) with 2 voxels of clear air around it and
    passing the placement rules; record it in cv.expect_floating. Returns the record."""
    for r in range(0, 9):
        for (dx, dy, dz) in ((0, 0, -r), (r, 0, 0), (-r, 0, 0), (0, r, 0), (0, -r, 0), (0, 0, r)):
            pr = _Probe()
            fn(pr, x + dx, y + dy, z + dz, *args, **kw)
            if pr.pts and _clear(cv, pr.pts) and rule_check(pr.pts, cv, params)['ok']:
                pts = fn(cv, x + dx, y + dy, z + dz, *args, **kw)
                a = np.array(pts)
                rec = {'name': name, 'voxels': len(pts), 'x': [int(a[:, 0].min()), int(a[:, 0].max())],
                       'y': [int(a[:, 1].min()), int(a[:, 1].max())], 'z': [int(a[:, 2].min()), int(a[:, 2].max())]}
                cv.expect_floating.append(rec)
                return rec
    raise RuntimeError(f'no clear spot for {name} near {(x, y, z)} that meets the sky placement rules')


def bird(target, x, y, z, heading, colour=(40, 36, 44), beak=(200, 150, 60)):
    return stamp(target, BIRD_SHAPE, x, y, z, heading, {'#': colour, 'b': beak})


def bat(target, x, y, z, heading, colour=(46, 38, 50), eye=(230, 80, 60)):
    return stamp(target, BAT_SHAPE, x, y, z, heading, {'#': colour, 'e': eye})
