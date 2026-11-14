"""Elderveil sky decor (opt-in, owner asked for it) and the sky-level corner tag. Placed AFTER the mirror.

Four floating ruin islets, each different (a broken balcony, a half arch, a stair fragment, a gnarled islet tree),
each with a hanging root and a cyan rune light, and a flock of crows (13-wide silhouettes). kit sky.place enforces
the rules: >= 60 from the platform, not over a spawn square, >= 8 air below, 2 voxels of clear air round it;
every piece is recorded as expected floating. Collapse caveat: a player block touching a piece, once broken, drops
the whole piece for the rest of the round.

Sky tag (knowledge base §12 rule 5): the name on a 2-voxel pale stone plate at z 7-8 (the highest allowed: nothing at
z <= 6) over the north-west cliff crest, dark underside, ONE stalk down to the ground near its west end (tethered:
not floating). Only what is under the plate is cleared.
"""
from __future__ import annotations

import math

import numpy as np

from aosmap.kit import sky

ROCK = [(104, 100, 98), (118, 112, 106), (92, 90, 92)]
STONE = (196, 190, 176)
CYAN = (95, 255, 255)
ROOT = (96, 74, 54)


def _base(t, x, y, z, r, depth):
    """Inverted rocky cone under an islet top at z (top surface), radius r."""
    pts = []
    for k in range(depth):
        rr = r * (1 - k / depth) ** 0.8 + 0.4
        for X in range(int(x - rr) - 1, int(x + rr) + 2):
            for Y in range(int(y - rr) - 1, int(y + rr) + 2):
                if math.hypot(X - x, Y - y) <= rr + 0.3 * math.sin(X * 1.7 + Y):
                    c = ROCK[(X + Y + k) % 3] if k else (92, 120, 64)
                    t.set(X, Y, z + k, c, 'sky')
                    pts.append((X, Y, z + k))
    return pts


def _root(t, x, y, z, n):
    pts = []
    for k in range(n):
        t.set(x, y, z + k, ROOT, 'sky')
        pts.append((x, y, z + k))
    return pts


def islet_balcony(t, x, y, z):
    pts = _base(t, x, y, z, 5.0, 6)
    for X in range(x - 4, x + 5):
        for Y in (y - 3, y + 3):
            if (X - x) % 2 == 0 and X != x + 2:
                for k in (1, 2):
                    t.set(X, Y, z - k, STONE, 'sky')
                    pts.append((X, Y, z - k))
    for X in range(x - 4, x + 5):
        if X != x + 2:
            for Y in (y - 3, y + 3):
                t.set(X, Y, z - 3, STONE, 'sky')
                pts.append((X, Y, z - 3))
    t.set(x - 4, y - 3, z - 4, CYAN, 'sky')
    pts.append((x - 4, y - 3, z - 4))
    pts += _root(t, x, y, z + 6, 5)
    return pts


def islet_arch(t, x, y, z):
    pts = _base(t, x, y, z, 4.0, 5)
    for X in (x - 3, x + 3):
        for k in range(1, 7 if X < x else 4):
            for Y in (y, y + 1):
                t.set(X, Y, z - k, STONE, 'sky')
                pts.append((X, Y, z - k))
    for X in range(x - 3, x + 1):
        for Y in (y, y + 1):
            t.set(X, Y, z - 7, STONE, 'sky')
            pts.append((X, Y, z - 7))
    t.set(x, y, z - 7, CYAN, 'sky')
    pts.append((x, y, z - 7))
    pts += _root(t, x - 1, y + 1, z + 5, 6)
    return pts


def islet_stair(t, x, y, z):
    pts = _base(t, x, y, z, 5.0, 6)
    for i in range(5):
        for Y in (y - 1, y, y + 1):
            for k in range(1, i + 2):
                t.set(x - 3 + i, Y, z - k, STONE, 'sky')
                pts.append((x - 3 + i, Y, z - k))
    t.set(x + 1, y, z - 6, CYAN, 'sky')
    pts.append((x + 1, y, z - 6))
    pts += _root(t, x + 2, y - 2, z + 6, 4)
    return pts


def islet_tree(t, x, y, z):
    pts = _base(t, x, y, z, 4.0, 5)
    for k in range(1, 6):
        t.set(x, y, z - k, ROOT, 'sky')
        pts.append((x, y, z - k))
    for X in range(x - 3, x + 4):
        for Y in range(y - 3, y + 4):
            for k in range(5, 9):
                if (X - x) ** 2 + (Y - y) ** 2 + ((k - 7) * 1.6) ** 2 <= 10:
                    c = (178, 170, 82) if k <= 6 else (78, 116, 56)
                    t.set(X, Y, z - k, c, 'sky')
                    pts.append((X, Y, z - k))
    t.set(x + 1, y, z - 2, CYAN, 'sky')
    pts.append((x + 1, y, z - 2))
    pts += _root(t, x - 2, y, z + 5, 7)
    return pts


ISLETS = [('islet balcony', islet_balcony, (78, 150, 18)), ('islet arch', islet_arch, (446, 136, 19)),
          ('islet stair', islet_stair, (120, 452, 19)), ('islet tree', islet_tree, (404, 404, 20))]


def _ceiling(fn):
    """Wrap an islet so a probe placement with any voxel at z <= 6 is rejected (sky.place then searches on)."""
    def f(t, x, y, z, *a, **kw):
        if isinstance(t, sky._Probe):
            pts = fn(t, x, y, z, *a, **kw)
            if min(p[2] for p in pts) < 7:
                t.pts = []
                return []
            return pts
        return fn(t, x, y, z, *a, **kw)
    return f


def place_sky(cv, S, rng):
    recs, glow = [], []
    for (name, fn, (x, y, z)) in ISLETS:
        r = None
        for (dx, dy, dz) in ((0, 0, 0), (0, 0, 4), (24, 0, 2), (-24, 0, 2), (0, 24, 2), (0, -24, 2), (30, 30, 4)):
            try:                                           # trees grow from the veg seed: try a few nearby spots
                r = sky.place(cv, name, _ceiling(fn), x + dx, y + dy, z + dz)
                break
            except RuntimeError:
                continue
        if r is None:
            continue
        recs.append(r)
        for X in range(r['x'][0], r['x'][1] + 1):
            for Y in range(r['y'][0], r['y'][1] + 1):
                for Z in range(r['z'][0], r['z'][1] + 1):
                    if cv.solid[X, Y, Z] and tuple(int(v) for v in cv.rgb[X, Y, Z]) == CYAN:
                        glow.append((X, Y, Z, CYAN))
    heading = 0.35
    for i, (dx, dy, dz) in enumerate(((0, 0, 0), (-16, 10, 1), (-14, -12, -1), (-30, 4, 2), (-28, -22, 0),
                                      (-44, 14, 1), (-46, -8, 3))):
        r = sky.place(cv, f'crow {i}', sky.bird, 300 + dx, 70 + dy, 14 + dz, heading,
                      colour=(44, 42, 50), beak=(80, 74, 66))
        recs.append(r)
    return recs, glow


def sky_tag(cv, S, text=None):
    """Name plate at z 7-8 over the NW cliff crest with one stalk to the ground."""
    from aosmap.pixelfont import text_mask
    m = text_mask([(text or S['name']).upper()])
    x0, y0 = S['art']['tag_xy']
    w, h = m.shape
    X0, X1, Y0, Y1 = x0 - 2, x0 + w + 1, y0 - 2, y0 + h + 1
    zt, zb = 7, 8
    cleared = 0
    for x in range(X0, X1 + 1):
        for y in range(Y0, Y1 + 1):
            g = int(cv.H[x, y])
            for z in range(0, min(g, zb + 3)):
                if cv.solid[x, y, z]:
                    cv.clear(x, y, z)
                    cleared += 1
            cv.set(x, y, zt, (200, 194, 180), 'tag')
            cv.set(x, y, zb, (70, 64, 60), 'tag')
    for (i, j) in zip(*np.nonzero(m)):
        cv.set(x0 + i, y0 + j, zt, (66, 74, 60), 'tag')
    sx, sy = X0 + 2, (Y0 + Y1) // 2
    for z in range(zb + 1, int(cv.H[sx, sy])):
        cv.set(sx, sy, z, (70, 64, 60), 'tag')
    return {'box': [X0, X1, Y0, Y1, zt, zb], 'stalk': [sx, sy], 'cleared_voxels': cleared,
            'note': 'tethered by one stalk (not floating); excluded from the mirror check'}
