"""Optional sky layer: crescent moon over the north-east sea + crow and bat flocks around the Wicker King / stem.

These are intentional FLOATING pieces (opt-in): they are placed after mirroring and after cleanup, and each one
is recorded in F['sky_objects'] so the validator reports them as expected floating geometry, not bugs.
Caveat (verified earlier in this project): if a player builds a block touching one and that block is then
destroyed, pyspades' collapse check drops the whole piece for the rest of the round; a map reload restores it.

Placement rules: >= 60 voxels from the script platform, nothing above either spawn square (Babel spawns on the
topmost voxel), >= 8 voxels of air above any walkable surface below.
"""
from __future__ import annotations

import math

import numpy as np

import wkh_props as P

MOON = {'center': (318, 70), 'zc': 16, 'R': 15.0, 'r': 13.0, 'offset': 7.0, 'thick': 2}

# crows circle the Wicker King: (angle deg around the King, radius, z); bats tumble round the stem's hook
KING_RING = (256, 118)
CROWS = [(200, 30, 6), (232, 34, 9), (262, 28, 5), (296, 33, 8), (330, 30, 11), (10, 34, 7), (44, 31, 4),
         (150, 36, 10), (120, 32, 6)]
BATS = [(208, 66, 8, 30), (226, 54, 14, 160), (198, 84, 16, 250), (240, 66, 6, 320), (214, 46, 19, 100),
        (192, 62, 11, 60)]

# seen-from-below silhouettes: rows along the forward axis (first row = front), columns across the wings
CROW_SHAPE = ['......b......',
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


def moon(V, spec=MOON):
    """Thin pale crescent standing upright, its face turned toward the island centre."""
    cx, cy = spec['center']
    nx, ny = 256 - cx, 262 - cy
    L = math.hypot(nx, ny); nx, ny = nx / L, ny / L          # normal toward the island
    ux, uy = -ny, nx                                          # horizontal axis in the moon's plane
    R, r, off = spec['R'], spec['r'], spec['offset']
    vox = {}
    a = -R
    while a <= R:
        b = -R
        while b <= R:
            if a * a + b * b <= R * R and (a - off) ** 2 + (b + 2.0) ** 2 > r * r:
                for t in range(spec['thick']):
                    x = int(round(cx + a * ux + (t - 0.5) * nx))
                    y = int(round(cy + a * uy + (t - 0.5) * ny))
                    z = int(round(spec['zc'] - b))
                    # shading class: rim (outer edge), maria (craters), body
                    d_out = R - math.hypot(a, b)
                    crater = (math.hypot(a + 9, b - 6) < 3.2 or math.hypot(a + 12, b + 7) < 2.4 or
                              math.hypot(a + 4, b + 13) < 2.0)
                    vox[(x, y, z)] = P.MOON_DK if crater else (P.MOON_RIM if d_out < 1.3 else P.MOON)
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
    return not V.m[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1].any()


def _place(V, fn, x, y, z, *args):
    """Place a small floating shape at the nearest spot (searching outward/upward) with 2 voxels of air around."""
    for r in range(0, 9):
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
    kx, ky = KING_RING
    for i, (ang, rad, z) in enumerate(CROWS):
        a = math.radians(ang)
        x, y = kx + rad * math.cos(a), ky + rad * math.sin(a)
        heading = a + math.pi / 2                              # circling counter-clockwise
        rec(f'crow{i}', _place(V, crow, int(round(x)), int(round(y)), z, heading))
    for j, (x, y, z, hdg) in enumerate(BATS):
        rec(f'bat{j}', _place(V, bat, x, y, z, math.radians(hdg)))
    F['sky_objects'] = objs
    return objs
