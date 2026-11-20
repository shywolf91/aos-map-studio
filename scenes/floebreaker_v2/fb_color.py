"""Floebreaker v2 colour: palette-guide winter ramps (docs/colour_palette_guide.md §4), material colours for the
architecture, baked light + AO (aosmap.kit.color.lighting), night grade, glow bake, sea gradient, corner tag.

Day palette ('winter crossing' / 'overcast pass', fitted under the 212 cap): broad snow field luma ~178, packed
tracks and drifts darker, crests only on 'crest' voxels and a few exposed lips (<= 5 %), slate rock as the dark anchor.
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
from scipy import ndimage as ndi

from aosmap.kit.color import lighting
from aosmap.pixelfont import text_mask
from aosmap.vxl import VoxelMap, surface_mask
from fb_core import GLOW, MAT, NAMES, fbm

FLAT = {  # material -> base colour (day). Two-tone pairs are close in value (no high-contrast 1-voxel stripes).
    'rock': (83, 98, 112), 'pack': (150, 162, 172), 'track': (128, 130, 136), 'drift': (156, 170, 180),
    'crest': (200, 208, 210),
    'hull_red': (160, 46, 44), 'hull_black': (46, 50, 60), 'hull_grey': (118, 124, 132), 'deck': (100, 106, 116),
    'white': (196, 198, 200), 'steel': (128, 134, 146), 'dsteel': (66, 72, 86), 'orange': (214, 116, 46),
    'yellow': (214, 176, 52), 'glass': (110, 170, 200), 'plank': (150, 110, 74), 'dwood': (98, 70, 52),
    'canvas_o': (196, 104, 46), 'canvas_g': (70, 124, 84), 'canvas_b': (60, 92, 160),
    'drum_r': (170, 54, 48), 'drum_b': (56, 86, 160), 'bone': (196, 188, 166),
    'cont_r': (160, 56, 50), 'cont_g': (58, 120, 80), 'cont_b': (54, 90, 160), 'cont_y': (200, 160, 54),
    'rubber': (44, 44, 50), 'tag': (206, 212, 214),
    'cloud': (196, 202, 210), 'cloud_s': (160, 172, 192), 'bird': (58, 68, 94), 'star': (240, 244, 255),
    'moon': (226, 224, 202), 'aur_a': (84, 240, 156), 'aur_b': (70, 214, 214), 'aur_c': (176, 122, 240),
    # architecture
    'clad_red_a': (150, 62, 50), 'clad_red_b': (138, 56, 46), 'clad_wood_a': (124, 88, 60), 'clad_wood_b': (112, 79, 54),
    'clad_grey_a': (114, 120, 128), 'clad_grey_b': (104, 110, 118), 'clad_green_a': (76, 106, 88),
    'clad_green_b': (68, 96, 80), 'trim': (200, 194, 180), 'beam': (72, 54, 42), 'stone': (110, 108, 106),
    'stone_b': (94, 94, 98), 'roof_a': (66, 70, 82), 'roof_b': (58, 62, 74), 'ridge': (46, 48, 56),
    'snow_roof': (178, 190, 198), 'floorp': (132, 98, 68), 'flag_r': (176, 52, 44), 'flag_b': (52, 82, 168),
    'leaf_a': (42, 70, 60), 'leaf_b': (52, 80, 66), 'leaf_c': (38, 62, 68), 'bark': (78, 60, 48), 'leaf_snow': (166, 180, 188),
}
SKY = {'cloud', 'cloud_s', 'bird', 'star', 'moon', 'aur_a', 'aur_b', 'aur_c'}
TERRAIN = {'snow', 'ice', 'blueice', 'rock', 'pack', 'track', 'drift', 'crest'}
NIGHT = (np.array([0.42, 0.50, 0.72]), np.array([10, 12, 30]))


def lerp(a, b, t):
    t = np.asarray(t)[:, None]
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
    top |= ~solid[xs, ys, np.maximum(zs - 1, 0)]
    Ht = W.H
    nA = fbm(W.seed + 21, (46, 22, 10), (1, .6, .3), fold=False)[xs, ys]
    nB = fbm(W.seed + 22, (14, 7, 4), (1, .6, .4), fold=False)[xs, ys]
    nC = fbm(W.seed + 23, (90, 40), (1, .6), fold=False)[xs, ys]
    t = np.clip((nA + 1) / 2, 0, 1)
    topz = np.argmax(solid[:, :, :63], axis=2)[xs, ys]
    dtop = np.clip(zs - topz, 0, 18) / 18.0
    # local terrain slope: steep faces show rock or glacier ice, gentle ground carries snow (snow follows form)
    hh = (63 - Ht).astype(float)
    slope = np.maximum(np.abs(np.diff(hh, axis=0, prepend=hh[:1])), np.abs(np.diff(hh, axis=1, prepend=hh[:, :1])))
    steep = ndi.maximum_filter(slope, size=3)[xs, ys] >= 2
    col = np.zeros((n, 3), float)

    def put(name, rgb):
        sel = mid == MAT[name]
        col[sel] = rgb[sel] if (isinstance(rgb, np.ndarray) and rgb.ndim == 2) else rgb

    # snow: field (168,184,192) with a slow hue drift toward cream in places; sides fall to the trough tone
    field = lerp((166, 182, 192), (172, 182, 186), np.clip(t * 1.4 - 0.2, 0, 1))
    field = field * (1 + 0.025 * nB)[:, None]
    trough = np.array([144, 163, 173], float)
    snow_c = np.where(top[:, None], field, trough * (1 + 0.02 * nB)[:, None])
    # lee troughs: a soft darker band where the noise is low (connected patches, never speckle)
    lee = np.clip((-nC - 0.35) * 2.5, 0, 1)
    snow_c = snow_c * (1 - 0.35 * lee[:, None]) + trough * 0.35 * lee[:, None]
    put('snow', snow_c)
    # ice body / cliffs: glacier blue, deeper with depth; steep faces partly slate rock (dark anchor)
    ic = lerp((126, 166, 190), (66, 108, 150), dtop) + nA[:, None] * np.array([-6, 10, 6])
    rockface = (np.array([83, 98, 112]) * (1 + 0.05 * nB)[:, None])
    ice_c = np.where((steep & (nC > 0.1) & ~top)[:, None], rockface, ic)
    put('ice', ice_c)
    bi = lerp((150, 196, 218), (62, 112, 168), np.clip(dtop * 0.9 + 0.12 * nB, 0, 1)) + nA[:, None] * np.array([-8, 12, 4])
    bi = np.where(top[:, None], bi * 1.03, bi)
    put('blueice', bi)
    rk = lerp((80, 94, 108), (104, 106, 112), t) * (1 + 0.05 * nB)[:, None]
    rk = np.where((top & (nC > 0.2))[:, None], np.array([126, 128, 116]) * (1 + 0.04 * nB)[:, None], rk)
    put('rock', rk)
    tip = np.clip((50 - zs) / 40.0, 0, 1)
    for name, base, hi in (('berg_a', (120, 182, 216), (176, 214, 232)), ('berg_b', (86, 148, 200), (146, 192, 222)),
                           ('berg_c', (150, 202, 226), (190, 222, 236))):
        put(name, lerp(base, hi, tip) + nA[:, None] * np.array([-6, 6, 4]))
    for name, rgb in FLAT.items():
        if name in ('rock',):
            continue
        sel = mid == MAT[name]
        if sel.any():
            col[sel] = rgb
    # material tone variation: low-frequency for terrain props, per-board hash for cladding/roof (close tones)
    soft = np.isin(mid, [MAT[k] for k in ('pack', 'track', 'drift', 'hull_red', 'hull_black', 'hull_grey', 'deck',
                                            'white', 'plank', 'dwood', 'bone', 'canvas_o', 'canvas_g', 'stone',
                                            'stone_b', 'floorp', 'leaf_a', 'leaf_b', 'leaf_c', 'bark')])
    col[soft] = col[soft] * (1 + 0.045 * nB[soft])[:, None]
    boards = np.isin(mid, [MAT[k] for k in NAMES if k.startswith('clad_') or k.startswith('roof_')])
    h = ((xs * 7 + ys * 13 + zs * 3) % 9 - 4) / 4.0
    col[boards] = col[boards] * (1 + 0.035 * h[boards])[:, None]
    col[(mid == MAT['cloud']) & ~top] = FLAT['cloud_s']
    # tracks: warmer, browner where most trampled (centre of the trail is not tracked here; noise does it)
    tr = mid == MAT['track']
    col[tr] = col[tr] * (1 - 0.45 * np.clip(nB[tr] + 0.3, 0, 1))[:, None] + np.array([116, 106, 96]) * 0.45 * np.clip(nB[tr] + 0.3, 0, 1)[:, None]
    # snow cap: scale the snow family so no voxel exceeds 212 (keeps the crest-to-field step)
    for name in ('snow', 'pack', 'drift', 'crest', 'snow_roof', 'leaf_snow', 'berg_a', 'berg_b', 'berg_c', 'blueice', 'trim'):
        sel = mid == MAT[name]
        if sel.any():
            mx = col[sel].max(axis=1)
            col[sel] = col[sel] * np.minimum(1.0, 212.0 / np.maximum(mx, 1))[:, None]
    if night:
        gradable = ~np.isin(mid, [MAT[k] for k in SKY]) & ~np.isin(mid, [MAT[k] for k in GLOW])
        col[gradable] = col[gradable] * NIGHT[0] + NIGHT[1]
    # ---- baked light + AO (kit), glow sources and sky decor excluded
    rgb = np.zeros(m.shape + (3,), np.uint8)
    rgb[xs, ys, zs] = np.clip(np.rint(col), 0, 255).astype(np.uint8)
    nolight = np.zeros(m.shape, bool)
    for nm in list(GLOW) + list(SKY):
        nolight |= (m == MAT[nm])
    cv = SimpleNamespace(solid=solid, rgb=rgb, nolight=nolight)
    lighting(cv, sun=(0.07, 0.04, -0.06, -0.03), side_f=0.86, ao_size=5, cover_f=0.84)
    out = cv.rgb[xs, ys, zs].astype(np.int64)
    # snow family back under the 212 cap after lighting (light can lift a crest over it)
    snowlike = np.isin(mid, [MAT[k] for k in ('snow', 'pack', 'drift', 'crest', 'snow_roof', 'leaf_snow', 'berg_a',
                                              'berg_b', 'berg_c', 'blueice', 'trim', 'track')])
    mx = out.max(axis=1)
    over = snowlike & (mx > 212)
    out[over] = np.rint(out[over] * (212.0 / mx[over])[:, None]).astype(np.int64)
    # floors: walkable tops never below luma 40
    L = 0.2126 * out[:, 0] + 0.7152 * out[:, 1] + 0.0722 * out[:, 2]
    low = top & (L < 40) & (L > 0)
    if low.any():
        out[low] = np.clip(np.rint(out[low] * (40.0 / L[low])[:, None]), 0, 255).astype(np.int64)
    for name, c in GLOW.items():
        out[mid == MAT[name]] = c
    colour = np.zeros(m.shape, np.uint32)
    colour[xs, ys, zs] = ((0x80 << 24) | (out[:, 0] << 16) | (out[:, 1] << 8) | out[:, 2]).astype(np.uint32)
    vm = VoxelMap(solid=solid, color=colour, colored=surf.copy())
    # ---- sea plane: cyan shallows -> deep blue, ripples, night grade
    land = W.land
    dist = ndi.distance_transform_edt(~land)
    shallow, mid_c, deep = np.array([84, 170, 184]), np.array([44, 122, 176]), np.array([24, 66, 132])
    tt = np.clip(dist / 14.0, 0, 1)[..., None]
    sea = shallow * (1 - tt) + mid_c * tt
    t2 = np.clip((dist - 14) / 70.0, 0, 1)[..., None]
    sea = np.where(dist[..., None] > 14, mid_c * (1 - t2) + deep * t2, sea)
    rip = fbm(W.seed + 31, (30, 14, 6), (1, .6, .3), fold=False)[..., None]
    sea = sea * (1 + 0.06 * rip)
    if night:
        sea = sea * np.array([0.50, 0.58, 0.78]) + np.array([10, 14, 34])
    sea = np.clip(sea, 0, 255).astype(np.uint32)
    tag = text_mask(['Floebreaker'])
    tx, ty = 396, 470
    tagc = np.array(FLAT['tag'], np.uint32) if not night else np.array([120, 132, 176], np.uint32)
    for i in range(tag.shape[0]):
        for j in range(tag.shape[1]):
            if tag[i, j] and not land[tx + i, ty + j] and not solid[tx + i, ty + j, :63].any():
                sea[tx + i, ty + j] = tagc
    tagbox = (tx, ty, tx + tag.shape[0] - 1, ty + tag.shape[1] - 1)
    plane = (0x80 << 24) | (sea[..., 0] << 16) | (sea[..., 1] << 8) | sea[..., 2]
    wmask = surf[:, :, 63] & (m[:, :, 63] == 0)
    vm.color[:, :, 63][wmask] = plane.astype(np.uint32)[wmask]
    # ---- glow bake (additive, linear falloff, radius 6.5); sources keep their exact palette colour
    srcs = sorted(set((x, y, z) for (x, y, z) in W.glow if NAMES[m[x, y, z]] in GLOW))
    cvals = vm.color
    R = 6
    for (sx, sy, sz) in srcs:
        sc = np.array(GLOW[NAMES[m[sx, sy, sz]]], float)
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
        gx, gy, gz, w = ax[sel] + x0, ay[sel] + y0, az[sel] + z0, w[sel]
        cur = cvals[gx, gy, gz].astype(np.int64)
        r = np.clip(((cur >> 16) & 255) + w * sc[0], 0, 255)
        g = np.clip(((cur >> 8) & 255) + w * sc[1], 0, 255)
        b = np.clip((cur & 255) + w * sc[2], 0, 255)
        cvals[gx, gy, gz] = ((0x80 << 24) | (np.rint(r).astype(np.int64) << 16) | (np.rint(g).astype(np.int64) << 8)
                             | np.rint(b).astype(np.int64)).astype(np.uint32)
    # glow light on snow: keep the snow family under the 212 cap after the bake (sources are not snow)
    snow_ids = [MAT[k] for k in ('snow', 'pack', 'drift', 'crest', 'snow_roof', 'leaf_snow', 'track', 'blueice', 'trim',
                                 'berg_a', 'berg_b', 'berg_c', 'white', 'bone', 'stone', 'steel')]
    sm = vm.colored & np.isin(m, snow_ids)
    if sm.any():
        cc = cvals[sm].astype(np.int64)
        r, g, b = (cc >> 16) & 255, (cc >> 8) & 255, cc & 255
        mxc = np.maximum(np.maximum(r, g), b)
        k = np.minimum(1.0, 212.0 / np.maximum(mxc, 1))
        r, g, b = (np.rint(r * k).astype(np.int64), np.rint(g * k).astype(np.int64), np.rint(b * k).astype(np.int64))
        cvals[sm] = ((0x80 << 24) | (r << 16) | (g << 8) | b).astype(np.uint32)
    pal = {(c[0] << 16) | (c[1] << 8) | c[2] for c in GLOW.values()} | {0xFFFFFF, 0xFF5F5F, 0xFFFF5F, 0x5FFFFF,
                                                                         0xFFAF5F, 0x5FFF5F}
    low24 = vm.color & 0xFFFFFF
    issrc = np.zeros(m.shape, bool)
    for nm in GLOW:
        issrc |= (m == MAT[nm])
    for p in pal:
        hit = vm.colored & (low24 == p) & ~issrc
        if hit.any():
            vm.color[hit] = vm.color[hit] - 1
    vm.color[~vm.colored] = 0
    return vm, tagbox, srcs
