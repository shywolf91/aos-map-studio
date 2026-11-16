"""Opt-in floating sky decor (owner asked): a ghost galleon silhouette, storm clouds, bat flocks and the moon.
Rules [USER]: >= 60 from the platform, never over a spawn square, >= 8 air below, 2 voxels clear round each piece
(aosmap.kit.sky.place enforces them); each piece is recorded in cv.expect_floating. Collapse caveat: a player block
built against a piece, once broken, drops that piece for the rest of the round."""
from __future__ import annotations

import math

from aosmap.kit import sky

HULL = (92, 112, 116)
SAIL = (150, 178, 172)
SAIL2 = (126, 156, 156)
MAST = (104, 120, 122)


def ghost_galleon(target, x, y, z, heading=0.0, L=36):
    """Side-on ghost galleon, 2 voxels thick, in the vertical plane through (x, y) along `heading`: curved hull with a
    raised stern, three masts, torn square sails (holes inside, edges kept so the piece stays one component)."""
    fx, fy = math.cos(heading), math.sin(heading)
    sx, sy = -fy, fx
    cells = {}

    def P(u, h, c):
        cells[(u, h)] = c
    for u in range(L):
        t = u / (L - 1)
        top = 3 + (3 if t > 0.78 else 0) + (1 if t < 0.12 else 0)
        bot = int(round(2.5 * math.sin(math.pi * t) ** 0.6))
        for h in range(-bot, top):
            P(u, h, HULL if h < top - 1 else MAST)
    for i in range(1, 6):                                       # bowsprit
        P(-i, 3 + i // 2, MAST)
        P(-i + 1, 3 + i // 2, MAST)
    for (mu, mh) in ((9, 17), (18, 20), (27, 14)):
        for h in range(3, mh + 1):
            P(mu, h, MAST)
        for (a, b) in ((5, 9), (11, mh - 2)) if mh > 15 else ((5, mh - 2),):
            w = 5 if b > 10 else 4
            for h in range(a, b + 1):
                for du in range(-w, w + 1):
                    edge = abs(du) == w or h in (a, b) or du == 0
                    torn = (abs(du * 7 + h * 3 + mu) % 11) < 3 and not edge
                    if not torn:
                        P(mu + du, h, SAIL if (h + du) % 3 else SAIL2)
    pts = []
    for (u, h), c in cells.items():
        for t in (0, 1):
            px = int(round(x + (u - L / 2) * fx + t * sx))
            py = int(round(y + (u - L / 2) * fy + t * sy))
            target.set(px, py, z - h, c, 'sky')
            pts.append((px, py, z - h))
    return pts


def place_all(cv, rep, S, rng):
    out = []
    out.append(sky.place(cv, 'ghost galleon', ghost_galleon, 150, 30, 26, 0.15))
    out.append(sky.place(cv, 'moon', sky.moon, 256, 500, 18, 15.0, 13.0, 7.0, 2, (256, 256)))
    storm_top, storm_bot = (178, 182, 198), (128, 134, 154)
    for i, (x, y, z, L) in enumerate(((60, 116, 8, 26), (452, 396, 9, 28), (330, 22, 6, 24), (186, 490, 7, 24),
                                      (40, 430, 8, 20), (470, 112, 7, 22))):
        out.append(sky.place(cv, f'storm cloud {i}', sky.cloud, x, y, z, L, seed=300 + i, top=storm_top,
                             bottom=storm_bot))
    for i, (x, y, z, hd) in enumerate(((214, 402, 30, 0.6), (232, 412, 27, 0.9), (296, 404, 29, 2.4),
                                       (280, 420, 33, 2.0), (256, 452, 36, 1.6))):
        out.append(sky.place(cv, f'bat {i}', sky.bat, x, y, z, hd))
    return [{k: o[k] for k in ('name', 'voxels', 'x', 'y', 'z')} for o in out]
