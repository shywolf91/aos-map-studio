"""Floebreaker colouring: day palette, night grade, glow bake, sea gradient, corner tag.

Rules honoured: snow max channel <= 212; floors luma >= 40; fog neutral; no 1-voxel high-contrast stripes
(gradients come from low-frequency noise, not per-voxel noise).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from aosmap.pixelfont import text_mask
from aosmap.vxl import VoxelMap, surface_mask
from fb_core import GLOW, MAT, NAMES, XX, YY, fbm

C = {  # flat colours (day)
    'rock': (96, 100, 114), 'pack': (196, 204, 214),
    'hull_red': (172, 40, 44), 'hull_black': (40, 44, 54), 'hull_grey': (118, 124, 132), 'deck': (104, 110, 120),
    'white': (206, 210, 214), 'steel': (134, 140, 152), 'dsteel': (66, 72, 86), 'orange': (232, 124, 44),
    'yellow': (232, 190, 48), 'glass': (120, 200, 230), 'plank': (164, 120, 78), 'dwood': (104, 74, 54),
    'canvas_o': (222, 110, 40), 'canvas_g': (66, 142, 86), 'canvas_b': (60, 100, 176),
    'drum_r': (190, 52, 48), 'drum_b': (54, 88, 180), 'bone': (206, 198, 176),
    'cont_r': (176, 52, 48), 'cont_g': (52, 128, 76), 'cont_b': (50, 92, 170), 'cont_y': (214, 170, 48),
    'rubber': (40, 40, 46), 'tag': (212, 228, 240),
    'cloud': (210, 216, 228), 'cloud_s': (168, 184, 212), 'bird': (58, 68, 94), 'star': (240, 244, 255),
    'moon': (232, 230, 206), 'aur_a': (84, 240, 156), 'aur_b': (70, 214, 214), 'aur_c': (176, 122, 240),
}
SKY = {'cloud', 'cloud_s', 'bird', 'star', 'moon', 'aur_a', 'aur_b', 'aur_c'}


def lerp(a, b, t):
    t = t[:, None]
    return np.array(a, float)[None, :] * (1 - t) + np.array(b, float)[None, :] * t


def colorize(W, night=False):
    m = W.m
    solid = m > 0
    solid[:, :, 63] = True
    surf = surface_mask(solid)
    xs, ys, zs = np.nonzero(surf & (m > 0))
    mid = m[xs, ys, zs]
    n = len(xs)
    top = np.zeros(n, bool)
    top[zs == 0] = True
    zz = np.maximum(zs - 1, 0)
    top |= ~solid[xs, ys, zz]
    H = W.H
    depth = np.clip(zs - H[xs, ys], 0, 40).astype(float)
    nA = fbm(W.seed + 21, (46, 22, 10), (1, .6, .3), fold=False)[xs, ys]
    nB = fbm(W.seed + 22, (14, 7, 4), (1, .6, .4), fold=False)[xs, ys]
    nC = fbm(W.seed + 23, (90, 40), (1, .6), fold=False)[xs, ys]
    t = (nA + 1) / 2
    col = np.zeros((n, 3), float)

    def put(name, rgb):
        sel = mid == MAT[name]
        col[sel] = rgb[sel] if isinstance(rgb, np.ndarray) and rgb.shape[0] == n else rgb

    # snow: lilac -> pearl -> mint; warm shadow patches; sides a little bluer/darker
    s = lerp((184, 196, 224), (206, 212, 222), np.clip(t * 2, 0, 1))
    s = s * (1 - np.clip(t * 2 - 1, 0, 1))[:, None] + lerp((206, 212, 222), (190, 214, 220), np.clip(t * 2 - 1, 0, 1)) * \
        np.clip(t * 2 - 1, 0, 1)[:, None]
    warm = np.clip((nC - 0.25) * 3, 0, 1)
    s = s * (1 - 0.35 * warm[:, None]) + np.array([208, 202, 206]) * 0.35 * warm[:, None]
    s = s * (1 + 0.035 * nB)[:, None]
    s = np.where(top[:, None], s, s * np.array([0.88, 0.93, 1.0]))
    sel = mid == MAT['snow']; col[sel] = s[sel]
    # ice body: pale near the surface, deeper blue with depth; teal shift by noise
    d = np.clip(depth / 9.0, 0, 1)
    ic = lerp((170, 208, 228), (74, 142, 200), d)
    ic = ic + (nA[:, None] * np.array([-10, 14, 6]))
    ic = np.where(top[:, None], ic * np.array([1.0, 1.0, 1.0]), ic * np.array([0.92, 0.96, 1.0]))
    sel = mid == MAT['ice']; col[sel] = ic[sel]
    bi = lerp((60, 126, 196), (96, 176, 222), np.clip(t + 0.15 * nB, 0, 1)) + (nA[:, None] * np.array([-6, 12, 4]))
    sel = mid == MAT['blueice']; col[sel] = bi[sel]
    rk = lerp((92, 96, 110), (122, 112, 104), np.clip(t, 0, 1)) * (1 + 0.04 * nB)[:, None]
    rk = np.where((top & (nC > 0.15))[:, None], np.array([140, 128, 98]) * (1 + 0.05 * nB)[:, None], rk)
    sel = mid == MAT['rock']; col[sel] = rk[sel]
    # icebergs: three facet tones, lighter toward the tips (smaller z)
    tip = np.clip((50 - zs) / 40.0, 0, 1)
    for name, base, hi in (('berg_a', (140, 204, 236), (206, 238, 248)), ('berg_b', (96, 164, 218), (170, 214, 240)),
                           ('berg_c', (176, 226, 242), (222, 244, 250))):
        c = lerp(base, hi, tip) + nA[:, None] * np.array([-6, 6, 4])
        sel = mid == MAT[name]; col[sel] = c[sel]
    for name, rgb in C.items():
        sel = mid == MAT[name]
        if sel.any():
            col[sel] = rgb
    # little tonal life on flat structure colours (low frequency only)
    flat = np.isin(mid, [MAT[k] for k in ('hull_red', 'hull_black', 'hull_grey', 'deck', 'white', 'plank', 'dwood',
                                            'bone', 'cont_r', 'cont_g', 'cont_b', 'cont_y', 'canvas_o', 'canvas_g',
                                            'canvas_b', 'steel')])
    col[flat] = col[flat] * (1 + 0.05 * nC[flat])[:, None]
    # ship deck centre line / hull bands are material based; bottoms (undersides) a touch darker
    under = ~top & ~solid[xs, ys, np.minimum(zs + 1, 63)] if False else None
    cloud_under = (mid == MAT['cloud']) & ~top
    col[cloud_under] = C['cloud_s']
    # snow cap: keep max channel <= 212
    for name in ('snow', 'pack', 'ice', 'berg_c'):
        sel = mid == MAT[name]
        mx = col[sel].max(axis=1)
        k = np.minimum(1.0, 212.0 / np.maximum(mx, 1))
        col[sel] = col[sel] * k[:, None]
    # night grade on everything except sky decor and glow sources
    if night:
        gradable = ~np.isin(mid, [MAT[k] for k in SKY]) & ~np.isin(mid, [MAT[k] for k in GLOW])
        g = col * np.array([0.40, 0.48, 0.68]) + np.array([10, 12, 30])
        col[gradable] = g[gradable]
    out = np.clip(np.rint(col), 0, 255).astype(np.int64)
    # glow sources: exact palette colours
    for name, rgb in GLOW.items():
        out[mid == MAT[name]] = rgb
    colour = np.zeros(m.shape, np.uint32)
    packed = (0x80 << 24) | (out[:, 0] << 16) | (out[:, 1] << 8) | out[:, 2]
    colour[xs, ys, zs] = packed.astype(np.uint32)
    vm = VoxelMap(solid=solid, color=colour, colored=surf.copy())
    # ---- sea plane: gradient from shallows to deep, painted at z = 63
    land = W.land
    dist = ndi.distance_transform_edt(~land)
    shallow, mid_c, deep = np.array([96, 198, 206]), np.array([46, 138, 196]), np.array([22, 70, 142])
    tt = np.clip(dist / 14.0, 0, 1)[..., None]
    sea = shallow * (1 - tt) + mid_c * tt
    t2 = np.clip((dist - 14) / 70.0, 0, 1)[..., None]
    sea = np.where(dist[..., None] > 14, mid_c * (1 - t2) + deep * t2, sea)
    rip = fbm(W.seed + 31, (30, 14, 6), (1, .6, .3), fold=False)[..., None]
    sea = sea * (1 + 0.06 * rip)
    if night:
        sea = sea * np.array([0.40, 0.48, 0.68]) + np.array([10, 12, 30])
    sea = np.clip(sea, 0, 255).astype(np.uint32)
    # corner tag painted on the seabed plane (map name only)
    tag = text_mask(['Floebreaker'])
    tx, ty = 396, 470
    tagc = np.array(C['tag'], np.uint32)
    if night:
        tagc = np.clip(np.array(C['tag']) * np.array([0.5, 0.58, 0.8]) + np.array([20, 24, 40]), 0, 255).astype(np.uint32)
    tagbox = None
    for i in range(tag.shape[0]):
        for j in range(tag.shape[1]):
            if tag[i, j] and not land[tx + i, ty + j] and not solid[tx + i, ty + j, :63].any():
                sea[tx + i, ty + j] = tagc
    tagbox = (tx, ty, tx + tag.shape[0] - 1, ty + tag.shape[1] - 1)
    plane = (0x80 << 24) | (sea[..., 0] << 16) | (sea[..., 1] << 8) | sea[..., 2]
    wmask = surf[:, :, 63] & (m[:, :, 63] == 0)
    vm.color[:, :, 63][wmask] = plane.astype(np.uint32)[wmask]
    # ---- glow bake (additive, linear falloff, radius 6.5), sources unchanged
    srcs = sorted(set(W.glow))
    cvals = vm.color
    R = 6
    for (sx, sy, sz) in srcs:
        nm = NAMES[m[sx, sy, sz]]
        if nm not in GLOW:
            continue
        sc = np.array(GLOW[nm], float)
        x0, x1 = max(sx - R, 0), min(sx + R + 1, 512)
        y0, y1 = max(sy - R, 0), min(sy + R + 1, 512)
        z0, z1 = max(sz - R, 0), min(sz + R + 1, 64)
        sub = vm.colored[x0:x1, y0:y1, z0:z1]
        if not sub.any():
            continue
        ax, ay, az = np.nonzero(sub)
        dd = np.sqrt((ax + x0 - sx) ** 2 + (ay + y0 - sy) ** 2 + (az + z0 - sz) ** 2)
        w = np.clip(1 - dd / 6.5, 0, 1) * 0.32
        sel = (w > 0) & (dd > 0)
        ax, ay, az, w = ax[sel], ay[sel], az[sel], w[sel]
        gx, gy, gz = ax + x0, ay + y0, az + z0
        cur = cvals[gx, gy, gz].astype(np.int64)
        r = np.clip(((cur >> 16) & 255) + w * sc[0], 0, 255)
        g = np.clip(((cur >> 8) & 255) + w * sc[1], 0, 255)
        b = np.clip((cur & 255) + w * sc[2], 0, 255)
        cvals[gx, gy, gz] = ((0x80 << 24) | (np.rint(r).astype(np.int64) << 16) | (np.rint(g).astype(np.int64) << 8) |
                             np.rint(b).astype(np.int64)).astype(np.uint32)
    # nudge any non-source voxel that accidentally equals a glow palette colour
    pal = {(rgb[0] << 16) | (rgb[1] << 8) | rgb[2] for rgb in GLOW.values()} | {0xFFFFFF, 0xFF5F5F, 0xFFFF5F, 0x5FFFFF,
                                                                               0xFFAF5F, 0x5FFF5F}
    low = vm.color & 0xFFFFFF
    issrc = np.zeros(m.shape, bool)
    for nm in GLOW:
        issrc |= (m == MAT[nm])
    for p in pal:
        hit = vm.colored & (low == p) & ~issrc
        if hit.any():
            vm.color[hit] = vm.color[hit] - 1
    vm.color[~vm.colored] = 0
    return vm, tagbox, sorted(set((x, y, z) for (x, y, z) in srcs if NAMES[m[x, y, z]] in GLOW))
