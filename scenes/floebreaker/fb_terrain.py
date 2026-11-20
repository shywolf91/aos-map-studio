"""Floebreaker terrain: island, floes, rim glaciers, flat zones, spawn/tower grounds, icebergs, serac fins."""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from fb_core import MAT, XX, YY, fbm, noise, smooth, sym

BASE = 59                      # ground surface z of the low ice plain (top solid voxel)
SPEC = {
    'name': 'Floebreaker', 'file': 'floebreaker', 'version': '1.0',
    'platform': {'x': (206, 305), 'y': (240, 271), 'z': 1},
    'bases': ((118, 256), (394, 256)),
    'spawn_half': 20,
    'tower_zone': {'blue_x': (128, 211), 'red_x': (301, 384), 'y': (240, 272)},
    'island': {'cx': 256, 'cy': 256, 'rx': 178, 'ry': 196},
    'ship': {'x': (244, 267), 'y': (58, 170), 'note': 'N-S axis, bow north, grounded in pack ice'},
    'whale': {'cx': 255.5, 'y': (310, 424)},
    'boundary_damage': {'left': 28, 'right': 484, 'top': 28, 'bottom': 484, 'damage': 1},
    'tag': {'text': 'Floebreaker', 'x': 396, 'y': 470},
}


def dist(px, py):
    return np.hypot(XX - px, YY - py)


def both(x):
    return (x, 512 - x)


def terrain(W):
    seed = W.seed
    r = np.hypot((XX - 256) / SPEC['island']['rx'], (YY - 256) / SPEC['island']['ry'])
    f = 1.0 - r + 0.20 * fbm(seed + 1, (64, 30, 14), (1, .6, .3))
    # floes: detached ice off the coast
    n2 = fbm(seed + 9, (22, 11), (1, .6))
    f = np.maximum(f, (n2 - 0.30) * 0.9 * smooth(r, 0.85, 1.0) * (1 - smooth(r, 1.25, 1.42)))
    # forced land: spawn grounds, tower zones/corridor, ship ground, north & south flank routes
    for bx, by in SPEC['bases']:
        f = np.maximum(f, 0.35 * smooth(-dist(bx, by), -64, -42))
    band = (np.abs(YY - 256) < 34) & (XX > 84) & (XX < 428)
    f = np.maximum(f, 0.35 * ndi.gaussian_filter(band.astype(float), 6))
    f = np.maximum(f, 0.35 * smooth(-np.hypot((XX - 256) / 48., (YY - 112) / 80.), -1.0, -0.7))
    land = f > 0
    # drop specks, fill pinholes
    lab, n = ndi.label(land)
    if n:
        sz = ndi.sum(land, lab, range(1, n + 1))
        land = np.isin(lab, [i + 1 for i, s in enumerate(sz) if s >= 260])
    sea_lab, n = ndi.label(~land)
    if n:
        sz = ndi.sum(~land, sea_lab, range(1, n + 1))
        big = [i + 1 for i, s in enumerate(sz) if s >= 4000]
        land = ~np.isin(sea_lab, big)
    land = sym(land)
    d = ndi.distance_transform_edt(land)             # voxels to the sea inside land
    # calm zones: spawn squares, tower ground, corridor, ship ground
    calm = np.zeros((512, 512))
    for bx, by in SPEC['bases']:
        calm = np.maximum(calm, smooth(-np.maximum(np.abs(XX - bx), np.abs(YY - by)), -56, -30))
    calm = np.maximum(calm, smooth(-np.maximum(np.abs(YY - 256) * 1.0, np.abs(XX - 256) * 0.45), -38, -26))
    calm = np.maximum(calm, smooth(-np.hypot((XX - 256) / 46., (YY - 114) / 76.), -1.0, -0.78))
    # rolling ice plain
    roll = fbm(seed + 2, (30, 15, 7), (1, .6, .3))
    e = 1.4 + 2.6 * roll
    e = e * (1 - calm) + (0.7 + 1.5 * roll) * calm          # calm zones: gentle +-1 mounds, never flat
    # hills / glaciers: (cx, cy, rx, ry, height) mirrored in x
    hills = [(52, 150, 44, 40, 24), (66, 352, 46, 40, 26), (120, 64, 42, 30, 20), (150, 452, 44, 30, 21),
             (28, 256, 22, 52, 17), (178, 138, 20, 15, 11), (182, 376, 22, 16, 12), (92, 205, 18, 14, 10),
             (96, 318, 17, 14, 10), (214, 60, 22, 18, 12), (206, 450, 22, 16, 13), (30, 60, 28, 26, 16)]
    hl = np.zeros((512, 512))
    rough = fbm(seed + 3, (10, 5), (1, .6))
    for cx, cy, rx, ry, h in hills:
        for x0 in sorted(set(both(cx))):
            rho = np.hypot((XX - x0) / rx, (YY - cy) / ry)
            prof = np.clip(1 - rho, 0, 1) ** 1.15
            hl = np.maximum(hl, h * prof * (1 + 0.22 * rough))
    hl = hl * (1 - calm)
    e = np.maximum(e, hl)
    # terraces on the hills (blue-ice benches)
    terr = np.where(e > 5, 5 + np.round((e - 5) / 2.0) * 2.0, e)
    e = np.where(e > 5, 0.5 * e + 0.5 * terr, e)
    H = np.round(BASE - e).astype(int)
    H = np.clip(H, 5, 61)
    # shore ramp so every coast is walkable back out of the water
    H = np.where(d <= 3, np.maximum(H, 62 - d.astype(int)), H)
    H = np.where(land, H, 63)
    return H, land, d, calm, e


def fill(W, H, rock_mask=None):
    z = np.arange(64)[None, None, :]
    solid = z >= H[:, :, None]
    m = np.where(solid, MAT['ice'], 0).astype(np.uint8)
    cap = solid & (z < H[:, :, None] + 2)
    m[cap] = MAT['snow']
    if rock_mask is not None:
        rk = rock_mask[:, :, None] & solid & (z < H[:, :, None] + 3)
        m[rk] = MAT['rock']
    m[:, :, 63] = 0                                  # plane added at export; keeps sea cells empty here
    sea = H >= 63
    m[:, :, 62][sea] = 0
    land = ~sea
    m[:, :, 63][land] = MAT['ice']
    W.m = m


def icebergs(W, H, land):
    """Faceted hexagonal-cone bergs standing on the seabed. Returns list of (cx, cy, r, h)."""
    rng = W.lrng
    sea = ~land
    dsea = ndi.distance_transform_edt(sea)
    out = []
    box = SPEC['boundary_damage']
    tries = 0
    while len(out) < 26 and tries < 4000:
        tries += 1
        cx = int(rng.integers(24, 256)); cy = int(rng.integers(24, 488))
        r = int(rng.integers(13, 30)); h = int(rng.integers(16, 34))
        if dsea[cx, cy] < r * 0.9 + 6:
            continue
        if (384 < cx < 472 and 456 < cy < 488) or (40 < cx < 128 and 456 < cy < 488):   # corner tag clear
            continue
        if cx > 240 and abs(cy - 256) < 60:           # keep the sea off the platform axis clear
            continue
        if any(np.hypot(cx - o[0], cy - o[1]) < (r + o[2]) * 0.85 for o in out):
            continue
        out.append((cx, cy, r, h))
    # pair every berg across the mirror, add a few singles on the middle seam
    pairs = []
    for cx, cy, r, h in out:
        pairs.append((cx, cy, r, h))
        pairs.append((512 - cx, cy, r, h))
    for cx, cy, r, h in pairs:
        berg(W, cx, cy, r, h)
    return pairs


def berg(W, cx, cy, r, h, tilt=0.0):
    x0, x1, y0, y1 = max(cx - r - 1, 0), min(cx + r + 1, 511), max(cy - r - 1, 0), min(cy + r + 1, 511)
    xs, ys = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1), indexing='ij')
    dx, dy = xs - cx, ys - cy
    a = np.abs(dx); b = np.abs(dx * 0.5 + dy * 0.866); c = np.abs(dx * 0.5 - dy * 0.866)
    dd = np.maximum(np.maximum(a, b), c) * 1.08
    ridge = 1.0 + 0.10 * np.sin(np.arctan2(dy, dx) * 3 + cx * 0.37)
    top = 63 - np.round(h * np.clip(1 - dd / (r * ridge), 0, 1) ** 0.85)
    which = np.argmax(np.stack([a, b, c]), axis=0)
    for xi in range(xs.shape[0]):
        for yi in range(xs.shape[1]):
            t = int(top[xi, yi])
            if t >= 63:
                continue
            X, Y = xs[xi, yi], ys[xi, yi]
            mid = MAT['berg_a'] if which[xi, yi] == 0 else (MAT['berg_b'] if which[xi, yi] == 1 else MAT['berg_c'])
            cur = W.m[X, Y, t:63]
            W.m[X, Y, t:63] = np.where(cur == 0, mid, cur)


def fin(W, H, cx, y0, y1, thick, zt, lean=0.0, mat='blueice', seed=0):
    """Serac fin: a tall blade of ice along y between y0..y1 centred on x=cx; zt = top z at its tallest."""
    rng = np.random.default_rng(seed)
    n = y1 - y0 + 1
    ys = np.arange(y0, y1 + 1)
    t = (ys - y0) / max(n - 1, 1)
    prof = np.sin(np.pi * t) ** 0.6
    jag = ndi.gaussian_filter(rng.standard_normal(n), 1.5) * 3
    for i, y in enumerate(ys):
        g = int(H[cx, y])
        top = int(round(g - (g - zt) * prof[i] + jag[i] * prof[i]))
        top = min(top, g - 2)
        off = int(round(lean * (t[i] - 0.5)))
        w0 = cx + off - thick // 2
        for x in range(w0, w0 + thick):
            gx = int(H[x, y]) if 0 <= x < 512 else 62
            tp = min(top, gx - 1) if top < gx else gx
            cur = W.m[x, y, tp:gx]
            W.m[x, y, tp:gx] = MAT[mat]
            if tp < gx:
                W.m[x, y, tp:tp + 1] = MAT['snow'] if thick > 3 and (x == w0 + thick // 2) else MAT[mat]
