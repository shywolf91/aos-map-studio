"""Colour pass: material ids -> packed colours for every surface voxel.

Palette: charcoal stone, weathered grey, bone/ivory, dark brown earth and dead grass; accents ghost green,
muted purple and blood red. Variation is structured (coherent noise, courses, streaks, height ramps); per-voxel
jitter is small. Noise uses x folded about 256 so both halves match; the hands are on the axis.
"""
from __future__ import annotations

import os
import sys

import numpy as np
from scipy import ndimage as ndi

from gf_core import fbm2, fold_x, hash3, pack_rgb, surface_mask, unpack_rgb
import gf_props as P
from gf_terrain import G, SEED, SPEC

C = {
    P.ROCK: (66, 62, 64), P.DIRT: (86, 70, 54), P.SOIL: (92, 86, 60), P.MOSS: (74, 84, 54),
    P.PATH: (118, 112, 102), P.COURT: (128, 122, 112), P.COURT_EDGE: (84, 80, 82), P.GRAVEL: (112, 106, 98),
    P.MUD: (66, 58, 46), P.POOL: (48, 72, 48), P.REED: (104, 96, 60), P.EARTH_DK: (74, 60, 46),
    P.STONE: (102, 100, 104), P.STONE_DK: (72, 70, 76), P.STONE_LT: (150, 146, 136), P.TRACERY: (144, 140, 130),
    P.ROOF_SLATE: (64, 64, 74), P.RUBBLE: (98, 94, 92), P.TILE_A: (140, 132, 118), P.TILE_B: (72, 70, 76),
    P.STAIR: (104, 100, 96),
    P.BONE: (224, 214, 188), P.BONE_DK: (156, 144, 120), P.SOCKET: (44, 40, 42), P.SKULLROCK: (178, 172, 154),
    P.GLASS_P: (116, 72, 140), P.GLASS_R: (152, 40, 46), P.GLASS_G: (112, 196, 124), P.GHOST: (168, 255, 186),
    P.CANDLE: (238, 232, 196), P.IRON: (44, 44, 50), P.WOOD: (90, 64, 46), P.WOOD_DK: (60, 46, 38),
    P.DEADWOOD: (80, 72, 68), P.BELL: (80, 74, 54), P.GRAVE: (142, 138, 130), P.GRAVE_DK: (110, 108, 106),
    P.CLOTH_TEAM: (58, 82, 156), P.CLOTH_RAG: (102, 92, 82), P.CRACK_GLOW: (104, 214, 136),
    P.TAG: (212, 202, 178), P.BLOOD: (130, 26, 32),
}
TEAM_RED = (160, 40, 40)
EMISSIVE = [P.GHOST, P.CANDLE, P.CRACK_GLOW, P.GLASS_G]


def mix(a, b, t):
    t = np.asarray(t, float)[:, None]
    return np.asarray(a, float) * (1 - t) + np.asarray(b, float) * t


def colorize(m):
    solid = m > 0
    surf = surface_mask(solid)
    surf[:, :, 63] = True
    xs, ys, zs = np.nonzero(surf & solid)
    mat = m[xs, ys, zs]
    fx = np.minimum(xs, 512 - xs)
    rgb = np.zeros((len(xs), 3))
    for k, v in C.items():
        rgb[mat == k] = v

    n_patch = fold_x(fbm2((512, 512), 20, 3, 'patch', SEED))
    n_fine = fold_x(fbm2((512, 512), 5, 2, 'fine', SEED))
    n_big = fold_x(fbm2((512, 512), 70, 2, 'big', SEED))
    npch = n_patch[xs, ys]; nfin = n_fine[xs, ys]; nbig = n_big[xs, ys]
    jit = hash3(fx, ys, zs, 7) - 0.5

    up_air = np.ones(len(xs), bool)
    k = zs > 0
    up_air[k] = ~solid[xs[k], ys[k], zs[k] - 1]
    down_air = np.zeros(len(xs), bool)
    k = zs < 63
    down_air[k] = ~solid[xs[k], ys[k], zs[k] + 1]
    side = ~up_air
    top = np.argmax(solid, axis=2)
    gtop = np.where(top < 63, top, 63)

    # --- ground: dead grass / grey earth / dark moss, blended
    s = mat == P.SOIL
    w_e = np.clip((npch[s] - 0.45) / 0.25, 0, 1); w_e = w_e * w_e * (3 - 2 * w_e)
    col = mix((90, 84, 56), (102, 92, 78), w_e)
    w_d = np.clip((0.40 - nbig[s]) / 0.2, 0, 1)
    col = col * (1 - 0.35 * w_d[:, None]) + np.array([62, 66, 48]) * 0.35 * w_d[:, None]
    w_s = np.clip((nfin[s] - 0.62) / 0.2, 0, 1)
    col = col * (1 - 0.4 * w_s[:, None]) + np.array([120, 110, 76]) * 0.4 * w_s[:, None]
    hl = np.clip((G - zs[s]) / 26.0, 0, 1)                       # higher ground slightly paler (moonlit)
    col = col * (1 + 0.10 * hl[:, None])
    rgb[s] = col
    s = mat == P.MOSS
    rgb[s] = mix((66, 76, 48), (86, 94, 58), nfin[s])
    s = mat == P.DIRT
    rgb[s] = mix((76, 62, 48), (96, 78, 58), npch[s])
    s = mat == P.EARTH_DK
    rgb[s] = mix((62, 50, 40), (82, 66, 50), nfin[s])
    s = mat == P.MUD
    rgb[s] = mix((56, 50, 40), (74, 64, 48), nfin[s])
    s = mat == P.POOL
    scum = (nfin[s] > 0.6)
    col = mix((40, 62, 44), (54, 80, 50), npch[s])
    col[scum] = col[scum] * 0.6 + np.array([96, 118, 58]) * 0.4
    rgb[s] = col

    # --- rock strata (cliffs, deep faces)
    s = mat == P.ROCK
    band = 0.5 + 0.5 * np.sin(zs[s] * 1.1 + nbig[s] * 8 + fx[s] * 0.04)
    rgb[s] = mix((52, 48, 52), (84, 78, 78), 0.4 * band + 0.4 * npch[s] + 0.2 * nfin[s])

    # --- paths / courtyard / gravel: flagstones with dark joints and mossy cracks
    s = mat == P.PATH
    j = ((fx[s] + (ys[s] // 3) * 2) % 4 == 0) | (ys[s] % 3 == 0)
    col = mix((104, 98, 90), (128, 122, 112), npch[s])
    col[j] *= 0.80
    rgb[s] = col
    s = mat == P.COURT
    j = (fx[s] % 4 == 0) | ((ys[s] + (fx[s] // 4) * 2) % 4 == 0)
    col = mix((116, 110, 100), (140, 134, 122), 0.6 * npch[s] + 0.4 * nfin[s])
    col[j] = col[j] * 0.78 + np.array([70, 80, 56]) * 0.22 * (nfin[s][j][:, None] > 0.5)
    rgb[s] = col
    s = mat == P.GRAVEL
    rgb[s] = mix((100, 96, 90), (124, 118, 108), nfin[s]) + jit[s][:, None] * 10

    # --- cathedral stone: lighter crowns, grime streaks toward the foot, moss creeping up the base
    for k_, lo, hi in ((P.STONE, (84, 82, 88), (118, 114, 116)), (P.STONE_DK, (60, 58, 64), (82, 80, 86)),
                       (P.STONE_LT, (132, 128, 120), (160, 156, 146)), (P.TRACERY, (128, 124, 116), (150, 146, 136)),
                       (P.RUBBLE, (80, 78, 78), (110, 106, 102))):
        s = mat == k_
        hgt = np.clip((gtop[xs[s], ys[s]] * 0 + G - zs[s]) / 34.0, 0, 1)
        streak = hash3((fx[s] + ys[s]) // 1, 0, 0, 23) * 0.5 + 0.5 * nfin[s]
        t = 0.45 * hgt + 0.35 * npch[s] + 0.2 * streak
        col = mix(lo, hi, t)
        course = (zs[s] % 3 == 0)
        col[course & side[s]] *= 0.93                       # masonry courses on walls
        base = np.clip((zs[s] - (G - 4)) / 4.0, 0, 1)       # bottom 4 voxels: moss/grime
        col = col * (1 - 0.3 * base[:, None]) + np.array([66, 76, 52]) * 0.3 * base[:, None]
        rgb[s] = col
    s = mat == P.ROOF_SLATE
    rgb[s] = mix((54, 54, 64), (76, 74, 86), nfin[s]) * np.where(zs[s] % 2 == 0, 1.0, 0.88)[:, None]
    for k_, a, b in ((P.TILE_A, (128, 120, 106), (150, 142, 126)), (P.TILE_B, (62, 60, 66), (82, 80, 86))):
        s = mat == k_
        col = mix(a, b, npch[s])
        crack = nfin[s] > 0.7
        col[crack] *= 0.82
        rgb[s] = col

    # --- bone: ivory on top, greyer and cooler lower down and underneath, darker joints already a material
    for k_ in (P.BONE, P.SKULLROCK):
        s = mat == k_
        hz = np.clip((G - zs[s]) / 40.0, 0, 1)
        base = np.array(C[k_], float)
        low = base * np.array([0.72, 0.70, 0.68])
        col = mix(low, base, 0.35 + 0.65 * hz)
        col = col * (0.94 + 0.10 * nfin[s][:, None])
        col[down_air[s]] *= 0.80
        if k_ == P.SKULLROCK:
            band = (0.5 + 0.5 * np.sin(zs[s] * 1.4 + fx[s] * 0.2)) > 0.8
            col[band] *= 0.9
        rgb[s] = col
    s = mat == P.BONE_DK
    rgb[s] = rgb[s] * (0.9 + 0.15 * nfin[s][:, None])

    # --- graves: per-stone tone, lichen at the foot
    for k_ in (P.GRAVE, P.GRAVE_DK):
        s = mat == k_
        tone = hash3(fx[s] // 3, ys[s] // 3, 0, 31)
        col = np.array(C[k_], float)[None, :] * (0.86 + 0.24 * tone[:, None])
        lichen = (nfin[s] > 0.62) & (zs[s] >= gtop[xs[s], ys[s]] - 1)
        col[lichen] = col[lichen] * 0.7 + np.array([122, 128, 70]) * 0.3
        rgb[s] = col

    # --- wood, iron, cloth, reeds: gentle variation
    for k_, amp in ((P.DEADWOOD, 0.22), (P.WOOD, 0.18), (P.WOOD_DK, 0.15), (P.IRON, 0.10), (P.REED, 0.2),
                    (P.CLOTH_TEAM, 0.12), (P.CLOTH_RAG, 0.15), (P.BELL, 0.2), (P.BLOOD, 0.12), (P.GLASS_P, 0.12),
                    (P.GLASS_R, 0.12)):
        s = mat == k_
        rgb[s] = rgb[s] * (1 - amp / 2 + amp * (0.6 * nfin[s] + 0.4 * (jit[s] + 0.5)))[:, None]
    s = mat == P.BELL                                               # verdigris on the bell
    vg = nfin[s] > 0.55
    tmp = rgb[s]; tmp[vg] = tmp[vg] * 0.78 + np.array([70, 118, 98]) * 0.22; rgb[s] = tmp

    # --- ground-level ambient occlusion next to tall neighbours (structure bases, grave plinths)
    t2 = np.where(top < 63, top, 63).astype(float)
    mn = ndi.minimum_filter(t2, size=3)
    occ = np.clip((t2 - mn - 1) / 6.0, 0, 1)            # neighbour at least 2 higher -> darker
    o = occ[xs, ys] * (zs == top[xs, ys]) * up_air
    rgb *= (1 - 0.18 * o)[:, None]

    # --- ghost-light pools on the ground around lamps (colour device; no renderer lighting assumed)
    gl = np.zeros((512, 512), bool)
    lampz = np.full((512, 512), 99.0)
    gxs, gys, gzs = np.nonzero(m == P.GHOST)
    gl[gxs, gys] = True
    np.minimum.at(lampz, (gxs, gys), gzs.astype(float))
    lampz = -ndi.grey_dilation(-lampz, size=(9, 9))          # nearest-lamp height spread around it
    glow = ndi.gaussian_filter(gl.astype(float), 2.2)
    glow = np.clip(glow / (glow.max() + 1e-9) * 2.2, 0, 1)
    lz = lampz[xs, ys]
    near_h = (zs >= lz) & (zs <= lz + 7)                        # only surfaces at/below the lamp (no roofs)
    gv = glow[xs, ys] * up_air * near_h
    rgb = rgb * (1 - 0.35 * gv[:, None]) + np.array([120, 200, 140]) * 0.35 * gv[:, None]

    # --- side shading + small jitter (not emissive)
    emissive = np.isin(mat, EMISSIVE)
    s = side & ~emissive
    rgb[s] *= 0.80
    rgb += jit[:, None] * 4 * (~emissive)[:, None]

    out = np.zeros(m.shape, np.uint32)
    out[xs, ys, zs] = pack_rgb(rgb)
    return out


def team_recolor(m, out):
    """East (red team) cloth -> red."""
    xs, ys, zs = np.nonzero(m[257:] == P.CLOTH_TEAM)
    xs = xs + 257
    if len(xs):
        cur = unpack_rgb(out[xs, ys, zs]).astype(float)
        f = cur.mean(1, keepdims=True) / np.mean(C[P.CLOTH_TEAM])
        out[xs, ys, zs] = pack_rgb(np.array(TEAM_RED) * f)
    return out


def paint_tag(out, m, text, x0, y0, z, rgb=(214, 204, 180)):
    """Paint the map name on the ground strip (top voxels at z) in the SW corner. Returns the rectangle."""
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    from aosmap.pixelfont import text_mask
    tm = text_mask([text])
    xs, ys = np.nonzero(tm)
    for x, y in zip(xs + x0, ys + y0):
        assert m[x, y, z] != 0 and (z == 0 or m[x, y, z - 1] == 0), 'tag must sit on open ground'
        out[x, y, z] = pack_rgb(np.array(rgb, float))
    # a dark border line one voxel around the lettering block for contrast
    return (int(x0), int(x0 + tm.shape[0] - 1), int(y0), int(y0 + tm.shape[1] - 1))
