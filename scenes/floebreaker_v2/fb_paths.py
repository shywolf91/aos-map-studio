"""Trampled paths and yards (value structure on the snow field): packed 'track' snow 3-5 wide with soft, noisy edges,
'drift' troughs in the lee of buildings. Left half only (mirrored by the build). Only snow/pack tops are repainted."""
from __future__ import annotations

import numpy as np

from fb_core import MAT

SNOWY = None


def _paint_line(W, H, pts, width=2.0, mat='track', seed=0):
    global SNOWY
    if SNOWY is None:
        SNOWY = {MAT['snow'], MAT['pack'], MAT['drift'], MAT['track']}
    rng = np.random.default_rng(seed)
    for (ax, ay), (bx, by) in zip(pts[:-1], pts[1:]):
        n = int(np.hypot(bx - ax, by - ay)) + 1
        for i in range(n):
            t = i / max(n - 1, 1)
            cx, cy = ax + (bx - ax) * t, ay + (by - ay) * t
            wv = width + 0.8 * np.sin(i * 0.37 + seed) + rng.uniform(-0.3, 0.3)
            r = int(np.ceil(wv)) + 1
            for x in range(int(cx) - r, int(cx) + r + 1):
                for y in range(int(cy) - r, int(cy) + r + 1):
                    if not (0 <= x < 512 and 0 <= y < 512):
                        continue
                    if np.hypot(x - cx, y - cy) > wv:
                        continue
                    g = int(H[x, y])
                    if g < 62 and W.m[x, y, g] in SNOWY:
                        W.m[x, y, g] = MAT[mat]


def yard(W, H, x0, x1, y0, y1, share=0.55, seed=3):
    """Trampled yard: patches of 'track' over a smooth noise mask (connected, never speckle)."""
    from scipy import ndimage as ndi
    rng = np.random.default_rng(seed)
    n = ndi.gaussian_filter(rng.standard_normal((x1 - x0 + 1, y1 - y0 + 1)), 3.0)
    thr = np.quantile(n, 1 - share)
    for i in range(n.shape[0]):
        for j in range(n.shape[1]):
            if n[i, j] >= thr:
                x, y = x0 + i, y0 + j
                g = int(H[x, y])
                if g < 62 and W.m[x, y, g] in (MAT['snow'], MAT['pack']):
                    W.m[x, y, g] = MAT['track']


def paint_paths(W, H):
    yard(W, H, 98, 138, 236, 276, 0.45, 11)                      # spawn yard
    yard(W, H, 120, 168, 196, 214, 0.5, 12)                      # station north forecourt
    yard(W, H, 120, 168, 300, 316, 0.5, 13)                      # station south forecourt
    routes = [
        [(118, 256), (139, 256), (175, 256)],                     # spawn -> arch -> tower zone
        [(118, 236), (118, 222), (134, 210), (140, 200)],         # spawn north exit -> station north door
        [(118, 276), (118, 290), (134, 302), (140, 312)],         # spawn south exit -> station south door
        [(92, 256), (100, 256)],                                  # lodge porch -> spawn
        [(140, 200), (175, 206), (188, 216), (205, 224)],         # station -> tower -> cabin
        [(140, 312), (175, 306), (188, 298), (205, 290)],
        [(160, 196), (200, 180), (232, 170)],                     # station -> ship gangway
        [(160, 316), (200, 330), (238, 340)],                     # station -> whale
        [(100, 120), (150, 112), (200, 118)],                     # north flank trail
        [(100, 396), (150, 404), (200, 396)],                     # south flank trail
    ]
    for i, pts in enumerate(routes):
        _paint_line(W, H, pts, 2.2 if i < 4 else 1.6, 'track', seed=i)
    # plank duckboards between doors (1 wide, flush with the ground: a material change, never a step)
    for pts in ([(132, 196), (132, 214), (118, 222)], [(154, 196), (154, 204)], [(132, 316), (132, 300), (118, 290)],
                [(80, 246), (92, 246)], [(84, 256), (97, 256)]):
        _paint_line(W, H, pts, 0.9, 'floorp', seed=9)
