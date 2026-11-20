"""Snow-laden spruce groves (owner rules: groves not even scatter, three random details per plant, varied colour with
smooth gradients, non-deterministic placement details from the decor seed). Left half only; the build mirrors it.
Dark conifer masses are the value anchor that makes the snow read bright without being white (palette guide §4.2)."""
from __future__ import annotations

import math

import numpy as np

from fb_core import MAT

DETAILS = ('lean', 'snag', 'double', 'icicles', 'rime', 'broken_top', 'cones')
LEAVES = ('leaf_a', 'leaf_b', 'leaf_c')


def _jag(rng):
    a = rng.uniform(0.75, 1.0, 7)
    ph = rng.uniform(0, 6.28, 7)
    return lambda ang: 0.82 + 0.18 * float(np.mean(a * np.sin(np.arange(1, 8) * ang + ph)))


def spruce(W, H, rng, x, y, leaf, h=None):
    g = int(H[x, y])
    h = h or int(rng.integers(12, 23))
    details = list(rng.choice(DETAILS, 3, replace=False))
    lean = rng.uniform(-1.6, 1.6, 2) if 'lean' in details else np.zeros(2)
    clear = int(rng.choice([3, 3, 4, 5]))
    top_cut = 3 if 'broken_top' in details else 0
    R0 = 0.22 * h + 1.3 + rng.random()
    period = int(rng.integers(2, 4))
    jag = _jag(rng)
    w = 2 if h >= 19 else 1
    for k in range(0, h - top_cut + 1):                  # trunk (kept straight under the canopy, leaning above)
        f = k / h
        tx, ty = x + int(round(lean[0] * f)), y + int(round(lean[1] * f))
        for dx in range(w):
            for dy in range(w):
                if 0 <= tx + dx < 512 and 0 <= ty + dy < 512:
                    W.m[tx + dx, ty + dy, g - 1 - k] = MAT['bark']
    for k in range(clear, h - top_cut + 1):
        f = (k - clear) / max(h - clear, 1)
        phase = ((k - clear) % period) / period
        r = R0 * (1 - f) ** 1.05 * (1 - 0.32 * phase) + 0.45
        z = g - 1 - k
        cx = x + lean[0] * (k / h) + (w - 1) / 2
        cy = y + lean[1] * (k / h) + (w - 1) / 2
        ri = int(math.ceil(r + 1))
        for px in range(int(cx) - ri, int(cx) + ri + 2):
            for py in range(int(cy) - ri, int(cy) + ri + 2):
                if not (0 <= px < 512 and 0 <= py < 512) or W.m[px, py, z]:
                    continue
                dd = math.hypot(px - cx, py - cy)
                if dd <= r * jag(math.atan2(py - cy, px - cx)):
                    W.m[px, py, z] = MAT[leaf] if (px + py + z) % 5 else MAT[LEAVES[(LEAVES.index(leaf) + 1) % 3]]
    # snow load on the upper face of each tier (whole tier sectors, never single voxels)
    load = 0.75 if 'rime' in details else 0.5
    x0, x1, y0, y1 = x - 8, x + 9, y - 8, y + 9
    for px in range(max(x0, 0), min(x1, 511) + 1):
        for py in range(max(y0, 0), min(y1, 511) + 1):
            col = W.m[px, py, g - h - 3:g]
            for i in range(1, len(col)):
                zz = g - h - 3 + i
                if col[i] in (MAT['leaf_a'], MAT['leaf_b'], MAT['leaf_c']) and col[i - 1] == 0:
                    ang = math.atan2(py - y, px - x)
                    if (math.sin(ang * 2 + px * 0.0) + 1) / 2 < load + 0.25:
                        W.m[px, py, zz] = MAT['leaf_snow']
    if 'double' in details:
        for k in range(h - top_cut - 3, h - top_cut + 2):
            W.m[x + 1, y, g - 1 - k] = MAT[leaf]
    if 'snag' in details:
        zz = g - 1 - int(h * 0.45)
        sgn = 1 if rng.random() < 0.5 else -1
        for i in range(1, 5):
            if 0 <= x + sgn * i < 512:
                if W.m[x + sgn * i, y, zz] == 0 or W.m[x + sgn * i, y, zz] in (MAT['leaf_a'], MAT['leaf_b'], MAT['leaf_c']):
                    W.m[x + sgn * i, y, zz] = MAT['bark']
    if 'icicles' in details:
        z_low = g - 1 - clear
        for px in range(x - 3, x + 4):
            for py in (y - 3, y + 3):
                if 0 <= px < 512 and 0 <= py < 512 and W.m[px, py, z_low] and W.m[px, py, z_low + 1] == 0 and (px + py) % 2:
                    W.m[px, py, z_low + 1] = MAT['berg_c']
    if 'cones' in details:
        for _ in range(4):
            px, py = x + int(rng.integers(-2, 3)), y + int(rng.integers(-2, 3))
            zz = g - 1 - int(rng.integers(clear, max(clear + 1, h - 3)))
            if W.m[px, py, zz] in (MAT['leaf_a'], MAT['leaf_b'], MAT['leaf_c']):
                W.m[px, py, zz] = MAT['dwood']
    if top_cut:
        W.m[x, y, g - 1 - (h - top_cut) - 1] = MAT['bark']
    return {'h': h, 'details': details}


def groves(W, H, keep_out, d, centres):
    lrng, drng = W.lrng, W.drng
    placed, info = [], []
    for gi, (gx, gy, R, n) in enumerate(centres):
        leaf = LEAVES[gi % 3]                                     # each grove leans to one green; tiers mix the others
        tries = 0
        k = 0
        while k < n and tries < n * 12:
            tries += 1
            a, rr = lrng.random() * 6.283, R * math.sqrt(lrng.random())
            x, y = int(gx + rr * math.cos(a)), int(gy + rr * math.sin(a))
            if not (8 < x < 250 and 8 < y < 504):
                continue
            g = int(H[x, y])
            if g >= 61 or d[x, y] < 5 or keep_out(x, y, 8) or W.keep[max(x - 6, 0):x + 7, max(y - 6, 0):y + 7].any():
                continue
            nb = H[x - 2:x + 3, y - 2:y + 3]
            if nb.max() - nb.min() > 2 or W.m[x, y, g] not in (MAT['snow'], MAT['pack'], MAT['ice'], MAT['rock']):
                continue
            if any((x - px) ** 2 + (y - py) ** 2 < 36 for px, py in placed):
                continue
            info.append(spruce(W, H, drng, x, y, leaf))
            placed.append((x, y))
            k += 1
    return {'trees': len(placed), 'details': {dd: sum(dd in t['details'] for t in info) for dd in DETAILS}}


GROVES = [  # (x, y, radius, trees) on the rim hills, flanks and behind the spawn lodge (left half)
    (52, 150, 26, 14), (66, 352, 26, 14), (120, 70, 22, 10), (150, 448, 20, 9), (30, 60, 18, 8),
    (40, 256, 16, 8), (86, 200, 12, 5), (86, 312, 12, 5), (196, 92, 14, 6), (200, 430, 14, 6),
    # framing groves: behind the stations, behind the expedition lodge, beside the observation towers
    (112, 164, 10, 5), (112, 346, 10, 5), (52, 222, 10, 5), (52, 292, 10, 5), (170, 196, 6, 2), (170, 316, 6, 2),
]
