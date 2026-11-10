"""Optional sky layer for Silverpine Hunt (v1.1): a full moon over the frozen lake, a crow flock wheeling over the
kill site and bats tumbling round the trophy tree and the mine headframe.

Intentional FLOATING pieces (opt-in): placed after mirroring and cleanup, each recorded in F['sky_objects'] so the
validator reports them as expected. Caveat: if a player builds a block touching one and that block is destroyed,
pyspades' collapse check drops the piece for the round; a map reload restores it.
Rules: >= 60 voxels from the script platform, nothing above either spawn square, >= 8 air below.
"""
from __future__ import annotations

import math

import numpy as np

import sph_props as P

MOON = {'center': (256, 82), 'zc': 15, 'R': 14.0, 'thick': 2}
CROW_RING = ((256, 142), [(200, 22, 22), (240, 26, 25), (285, 20, 21), (330, 24, 24), (20, 21, 23), (60, 25, 20),
                          (110, 23, 24), (155, 20, 22)])
BAT_RING = ((256, 370), [(20, 22, 16), (80, 24, 19), (140, 21, 15), (200, 25, 18), (260, 22, 14), (320, 24, 17)])
MINE_BATS = []   # v2: the denser forest round the mine leaves no clear air; bats stay at the trophy tree

CROW_SHAPE = ['......b......',
              '......#......',
              '#############',
              '#.#.##.##.#.#',
              '.....###.....',
              '.....#.#.....']
BAT_SHAPE = ['.......#.#.......',
             '####..#e#e#..####',
             '#################',
             '.####..###..####.',
             '..##...#.#...##..',
             '...#.........#...']


def moon(V, spec=MOON):
    """Full Halloween moon standing upright in the x-z plane, facing south over the lake."""
    cx, cy = spec['center']
    R = spec['R']
    vox = {}
    a = -R
    while a <= R:
        b = -R
        while b <= R:
            d = math.hypot(a, b)
            if d <= R:
                for t in range(spec['thick']):
                    x = int(round(cx + a)); y = cy + t; z = int(round(spec['zc'] - b))
                    crater = (math.hypot(a + 5, b - 4) < 3.4 or math.hypot(a - 6, b + 5) < 2.6 or
                              math.hypot(a - 2, b - 8) < 1.8 or math.hypot(a + 8, b + 7) < 2.2 or
                              math.hypot(a - 8, b - 1) < 1.6)
                    vox[(x, y, z)] = P.MOON_DK if crater else (P.MOON_RIM if R - d < 1.3 else P.MOON)
            b += 0.5
        a += 0.5
    for (x, y, z), m in vox.items():
        V.put(x, y, z, m)
    return list(vox)


def _stamp(V, shape, x, y, z, hd, mats, tips_up=0):
    """Write a 2D silhouette in the horizontal plane, rotated to heading hd (radians)."""
    fx, fy = math.cos(hd), math.sin(hd)
    sx, sy = -fy, fx
    rows, cols = len(shape), len(shape[0])
    pts = []
    for i, row in enumerate(shape):
        f = (rows // 2) - i
        for j, ch in enumerate(row):
            if ch == '.':
                continue
            w = j - cols // 2
            px = int(round(x + f * fx + w * sx)); py = int(round(y + f * fy + w * sy))
            pts.append((px, py, z, mats.get(ch, mats['#'])))
            if tips_up and abs(w) >= cols // 2 - tips_up + 1:
                pts.append((px, py, z - 1, mats['#']))          # raised wing tips (dihedral)
    # rounding of a rotated stamp can leave diagonal-only joins: fill them so the piece is one component
    have = {(p[0], p[1]) for p in pts}
    for (px, py, pz, m) in list(pts):
        for (dx, dy) in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            if (px + dx, py + dy) in have and (px + dx, py) not in have and (px, py + dy) not in have:
                pts.append((px + dx, py, z, mats['#'])); have.add((px + dx, py))
    for (a, b, c, m) in pts:
        V.put(a, b, c, m)
    return [p[:3] for p in pts]


def crow(V, x, y, z, hd):
    return _stamp(V, CROW_SHAPE, x, y, z, hd, {'#': P.CROW, 'b': P.CROW_BEAK}, tips_up=1)


def bat(V, x, y, z, hd):
    return _stamp(V, BAT_SHAPE, x, y, z, hd, {'#': P.BAT, 'e': P.BAT_EYE}, tips_up=1)


class _Probe:
    """Collects the points a shape would write, without touching the map."""

    def __init__(self):
        self.pts = []

    def put(self, x, y, z, m):
        self.pts.append((int(x), int(y), int(z)))


def _clear(V, pts, margin=2):
    a = np.array(pts)
    x0, y0, z0 = a.min(0) - margin
    x1, y1, z1 = a.max(0) + margin
    if z0 < 2 or x0 < 0 or y0 < 0 or x1 > 511 or y1 > 511 or z1 > 61:
        return False
    if V.m[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1].any():
        return False
    return not V.m[x0:x1 + 1, y0:y1 + 1, z1 + 1:min(64, z1 + 10)].any()     # >= 8 air under the piece


def _place(V, fn, x, y, z, *args):
    """Place a small floating shape at the nearest spot (searching outward/upward) with 2 voxels of air around."""
    for r in range(0, 16):
        for (dx, dy, dz) in ((0, 0, -r), (r, 0, 0), (-r, 0, 0), (0, r, 0), (0, -r, 0), (0, 0, r)):
            pr = _Probe()
            fn(pr, x + dx, y + dy, z + dz, *args)
            if _clear(V, pr.pts):
                return fn(V, x + dx, y + dy, z + dz, *args)
    raise RuntimeError(f'no clear spot for {fn.__name__} near {(x, y, z)}')


def add_sky(V, F):
    objs = []

    def rec(name, pts):
        a = np.array(pts)
        objs.append({'name': name, 'voxels': len(pts), 'x': [int(a[:, 0].min()), int(a[:, 0].max())],
                     'y': [int(a[:, 1].min()), int(a[:, 1].max())], 'z': [int(a[:, 2].min()), int(a[:, 2].max())]})

    rec('moon', moon(V))
    (kx, ky), ring = CROW_RING
    for i, (ang, rad, z) in enumerate(ring):
        a = math.radians(ang)
        rec(f'crow{i}', _place(V, crow, int(round(kx + rad * math.cos(a))), int(round(ky + rad * math.sin(a))), z,
                               a + math.pi / 2))
    (bx, by), ring = BAT_RING
    for j, (ang, rad, z) in enumerate(ring):
        a = math.radians(ang)
        rec(f'bat{j}', _place(V, bat, int(round(bx + rad * math.cos(a))), int(round(by + rad * math.sin(a))), z,
                              a - math.pi / 2))
    for j, (x, y, z, hdg) in enumerate(MINE_BATS):
        rec(f'minebat{j}', _place(V, bat, x, y, z, math.radians(hdg)))
    F['sky_objects'] = objs
    return objs
