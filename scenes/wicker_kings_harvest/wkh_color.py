"""Colour pass: material ids -> 0xAARRGGBB for every surface voxel, plus the painted sea (z = 63).

Variation is structured (coherent noise, strata, boards, rows, height ramps); per-voxel jitter is kept small.
Noise is sampled on x folded about 256 so the mirrored half gets the same pattern.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from wkh_core import fbm2, fold_x, hash3, pack_rgb, surface_mask
import wkh_props as P
from wkh_terrain import SEED, SPEC

C = {
    P.ROCK: (72, 66, 68), P.SHORE_ROCK: (86, 82, 80), P.SKIN: (196, 102, 34), P.SOIL: (126, 106, 58),
    P.DIRT: (100, 76, 50), P.PATH: (162, 130, 86), P.FIELD: (90, 64, 40), P.FURROW: (70, 50, 32),
    P.PIT_ROCK: (54, 48, 52), P.EMBER: (238, 138, 40), P.ASH: (46, 42, 44), P.CLEARING: (128, 98, 64),
    P.STONE: (152, 144, 128), P.STONE_DARK: (112, 106, 98), P.TIMBER: (100, 76, 52), P.PLANK: (134, 102, 66),
    P.BARN: (132, 56, 42), P.BARN_TRIM: (196, 186, 166), P.ROOF: (64, 54, 58), P.STRAW: (194, 164, 92),
    P.PUMPKIN: (228, 122, 34), P.PUMPKIN_DK: (184, 86, 24), P.STEM_GREEN: (86, 98, 44), P.VINE: (60, 82, 40),
    P.DEADWOOD: (80, 68, 60), P.WICKER: (184, 150, 96), P.WICKER_DK: (118, 90, 58), P.GLOW: (255, 198, 98),
    P.IRON: (46, 44, 48), P.CLOTH_TEAM: (60, 84, 150), P.CLOTH_RAG: (124, 106, 84), P.STALK: (128, 122, 76),
    P.FLESH: (230, 160, 70), P.FENCE: (88, 72, 58), P.MOSS: (84, 92, 50), P.JACK: (255, 176, 52),
    P.GRASS: (100, 102, 52), P.SEA: (30, 46, 60), P.STAIR: (128, 98, 64), P.GRAVE: (120, 118, 112),
    P.SHINGLE_GREY: (76, 74, 82), P.WALL_GREY: (138, 126, 110), P.WINDOW: (34, 32, 40), P.CANDLE: (250, 230, 170),
    P.EARTH_DK: (70, 56, 40), P.ROPE: (150, 128, 90), P.HULL: (90, 62, 42), P.LEAF_DK: (48, 64, 36),
    P.LEAF_RUST: (150, 58, 30), P.LEAF_ORANGE: (196, 104, 34), P.LEAF_BROWN: (112, 74, 40),
    P.SILO: (128, 112, 92), P.SILO_BAND: (62, 58, 60), P.HAY_LITTER: (150, 128, 76), P.STALK_DK: (78, 80, 46),
    P.MOON: (222, 216, 190), P.MOON_DK: (184, 178, 160), P.MOON_RIM: (234, 228, 204),
    P.CROW: (28, 26, 32), P.CROW_BEAK: (128, 104, 58), P.BAT: (48, 38, 54), P.BAT_EYE: (230, 96, 40),
}
TEAM_RED = (160, 50, 44)
BARN_GREY = (118, 106, 94)


def colorize(m, F):
    solid = m > 0
    surf = surface_mask(solid)
    surf[:, :, 63] = True                     # always paint the bottom layer (sea + under-island)
    xs, ys, zs = np.nonzero(surf & solid)
    mat = m[xs, ys, zs]
    fx = np.minimum(xs, 512 - xs)            # folded x for symmetric patterns
    rgb = np.zeros((len(xs), 3))
    for k, v in C.items():
        sel = mat == k
        rgb[sel] = v

    # coherent fields
    n_patch = fold_x(fbm2((512, 512), 18, 3, 'patch', SEED))
    n_fine = fold_x(fbm2((512, 512), 5, 2, 'fine', SEED))
    n_big = fold_x(fbm2((512, 512), 64, 2, 'big', SEED))
    npch = n_patch[xs, ys]; nfin = n_fine[xs, ys]; nbig = n_big[xs, ys]
    jit = (hash3(fx, ys, zs, 7) - 0.5)

    up_air = np.ones(len(xs), bool)
    k = zs > 0
    up_air[k] = ~solid[xs[k], ys[k], zs[k] - 1]
    side = ~up_air

    # --- soil: olive grass / ochre earth / straw, blended (no hard thresholds)
    s = mat == P.SOIL
    t1 = npch[s]; t2 = nfin[s]; t3 = nbig[s]
    w_e = np.clip((t1 - 0.42) / 0.22, 0, 1); w_e = w_e * w_e * (3 - 2 * w_e)
    grass = np.array([104, 100, 52]); earth = np.array([146, 112, 62])
    col = grass * (1 - w_e[:, None]) + earth * w_e[:, None]
    w_s = np.clip((t2 - 0.6) / 0.2, 0, 1)
    col = col * (1 - 0.6 * w_s[:, None]) + np.array([168, 144, 86]) * 0.6 * w_s[:, None]
    w_d = np.clip((0.42 - t3) / 0.2, 0, 1)
    col = col * (1 - 0.3 * w_d[:, None]) + np.array([80, 78, 44]) * 0.3 * w_d[:, None]
    rgb[s] = col
    s = mat == P.GRASS
    rgb[s] = np.array([92, 98, 48]) * (0.9 + 0.2 * nfin[s][:, None])

    # --- pumpkin skin: crown light, grooves deep, vertical streaks, cliff darkening
    s = mat == P.SKIN
    th = F['th'][xs[s], ys[s]]
    groove = F['groove'][xs[s], ys[s]]
    streak = 0.5 + 0.5 * np.cos(th * SPEC['lobes'] * 3)
    hgt = np.clip((52 - zs[s]) / 18, 0, 1)
    col = np.array([150, 66, 26]) * (1 - hgt[:, None]) + np.array([214, 116, 38]) * hgt[:, None]
    col = col * (1 - 0.32 * groove[:, None]) + np.array([96, 44, 22]) * 0.32 * groove[:, None]
    col = col * (0.95 + 0.07 * streak[:, None])
    col = col * (0.94 + 0.12 * nfin[s][:, None])
    rgb[s] = col

    # --- rocks: strata bands
    for k_, lo, hi in ((P.ROCK, (58, 54, 58), (84, 78, 78)), (P.PIT_ROCK, (40, 36, 40), (66, 58, 60)),
                       (P.SHORE_ROCK, (66, 64, 66), (108, 102, 96))):
        s = mat == k_
        band = 0.5 + 0.5 * np.sin(zs[s] * 1.3 + nbig[s] * 9 + fx[s] * 0.05)
        t = 0.35 * band + 0.45 * npch[s] + 0.2 * nfin[s]
        rgb[s] = np.array(lo) * (1 - t[:, None]) + np.array(hi) * t[:, None]
    s = (mat == P.SHORE_ROCK) & (zs >= 60)
    rgb[s] *= 0.72                                          # wet rock at the waterline
    s = (mat == P.SHORE_ROCK) & up_air & (zs < 60)
    rgb[s] = rgb[s] * 0.85 + np.array([120, 116, 100]) * 0.15

    # --- ash floor with ember speckle, embers
    s = mat == P.ASH
    rgb[s] = np.array([40, 36, 38]) + (nfin[s][:, None] - 0.5) * 30 + np.array([20, 8, 0]) * (npch[s][:, None] > 0.62)
    s = mat == P.EMBER
    t = hash3(fx[s], ys[s], zs[s], 3)
    rgb[s] = np.array([214, 104, 30]) * (1 - t[:, None]) + np.array([255, 178, 70]) * t[:, None]

    # --- path: lighter centre, dusty edges
    s = mat == P.PATH
    pm = F.get('path_mask')
    if pm is not None:
        d = ndi.distance_transform_edt(pm)
        dd = np.clip(d[xs[s], ys[s]] / 2.5, 0, 1)
        rgb[s] = np.array([132, 108, 70]) * (1 - dd[:, None]) + np.array([170, 138, 92]) * dd[:, None]
        rgb[s] += (nfin[s][:, None] - 0.5) * 14

    # --- clearing: packed earth with faint concentric rings
    s = mat == P.CLEARING
    (ccx, ccy), cr = SPEC['clearing']
    rr = np.hypot(fx[s] + 0.5 - ccx, ys[s] + 0.5 - ccy)
    ring = (np.floor(rr) % 9 < 1) & (rr < cr)
    rgb[s] = np.array([124, 96, 62]) + (npch[s][:, None] - 0.5) * 26
    tmp = rgb[s]; tmp[ring] = tmp[ring] * 0.86; rgb[s] = tmp

    # --- planks/timber/barn: board pattern
    for k_ in (P.PLANK, P.STAIR, P.BARN, P.WALL_GREY, P.TIMBER, P.FENCE, P.HULL):
        s = mat == k_
        board = (((fx[s] + ys[s]) // 1) % 2 == 0)
        f = np.where(board, 1.0, 0.9) * (0.93 + 0.14 * nfin[s])
        rgb[s] = rgb[s] * f[:, None]
    s = mat == P.STAIR
    tread = zs[s] % 2 == 0
    tmp = rgb[s]; tmp[tread] *= 1.08; rgb[s] = tmp

    # --- stone tops: flagstone joints; silo staves
    s = (mat == P.STONE) & up_air
    joint = ((fx % 5) == 0) | ((ys % 4) == 0)
    tmp = rgb[s]; tmp[joint[s]] *= 0.82; rgb[s] = tmp
    s = mat == P.SILO
    stv = ((fx + ys) % 3) == 0
    tmp = rgb[s]; tmp[stv[s]] *= 0.85; rgb[s] = tmp

    # --- roof shingles: alternating courses
    for k_ in (P.ROOF, P.SHINGLE_GREY):
        s = mat == k_
        course = (zs[s] % 2 == 0)
        rgb[s] = rgb[s] * np.where(course, 1.0, 0.86)[:, None] * (0.92 + 0.16 * nfin[s])[:, None]

    # --- straw, wicker, pumpkins, dead wood, vines: gentle variation
    for k_, amp in ((P.STRAW, 0.18), (P.WICKER, 0.18), (P.WICKER_DK, 0.15), (P.PUMPKIN, 0.10),
                    (P.PUMPKIN_DK, 0.10), (P.DEADWOOD, 0.20), (P.VINE, 0.25), (P.LEAF_DK, 0.25),
                    (P.STALK, 0.06), (P.STALK_DK, 0.06), (P.STONE, 0.12), (P.STONE_DARK, 0.15),
                    (P.FIELD, 0.12), (P.FURROW, 0.12), (P.CLOTH_RAG, 0.15), (P.LEAF_RUST, 0.2), (P.LEAF_ORANGE, 0.2), (P.LEAF_BROWN, 0.2),
                    (P.SILO, 0.1)):
        s = mat == k_
        rgb[s] = rgb[s] * (1 - amp / 2 + amp * (0.6 * nfin[s] + 0.4 * (jit[s] + 0.5)))[:, None]

    # --- side-face hand shading + gentle height lift (not for emissive materials)
    emissive = np.isin(mat, [P.GLOW, P.JACK, P.EMBER, P.CANDLE, P.MOON, P.MOON_DK, P.MOON_RIM, P.BAT_EYE])
    s = side & ~emissive
    rgb[s] *= 0.86
    lift = np.clip((52 - zs) / 40, 0, 1) * 0.06
    rgb[~emissive] *= (1 + lift[~emissive])[:, None]
    rgb += jit[:, None] * 4 * (~emissive)[:, None]

    # --- sea floor painting (z = 63 under water columns)
    s = mat == P.SEA
    sea_z = s & (zs == 63)
    land2d = m[:, :, 62] > 0
    dist = ndi.distance_transform_edt(~land2d)
    d = dist[xs[sea_z], ys[sea_z]]
    deep = np.array([14, 20, 34]); mid = np.array([22, 38, 54]); shallow = np.array([40, 70, 80])
    t_sh = np.clip(1 - d / 12, 0, 1); t_mid = np.clip(1 - d / 46, 0, 1)
    col = deep * (1 - t_mid[:, None]) + mid * t_mid[:, None]
    col = col * (1 - t_sh[:, None]) + shallow * t_sh[:, None]
    foam = np.clip(1 - (d - 1) / 2.0, 0, 1)
    col = col * (1 - 0.55 * foam[:, None]) + np.array([120, 132, 136]) * 0.55 * foam[:, None]
    wv = value_wave(xs[sea_z], ys[sea_z])
    col = col * (0.94 + 0.10 * wv[:, None])
    # moonlight glint path (north-east sea), soft and broken
    gx, gy = xs[sea_z].astype(float), ys[sea_z].astype(float)
    band = np.exp(-(((gx - 430) * 0.8 + (gy - 60) * 0.6) / 22.0) ** 2) * np.exp(-((gx - 430) ** 2 + (gy - 60) ** 2) / (2 * 80 ** 2))
    streak = (np.sin(gy * 1.7 + np.sin(gx * 0.31) * 2.0) > 0.86) & (np.sin(gx * 0.45 + gy * 0.05) > -0.2)
    glint = band * streak
    col = col + np.array([60, 66, 78]) * glint[:, None] * 0.55
    rgb[sea_z] = col
    s = (mat == P.SEA) & (zs < 63)
    rgb[s] = np.array([36, 58, 70])                           # trough water

    out = np.zeros(m.shape, np.uint32)
    out[xs, ys, zs] = pack_rgb(rgb)
    return out


def value_wave(x, y):
    a = np.sin(x * 0.21 + y * 0.07) + np.sin(x * 0.05 - y * 0.23 + 1.3) + 0.6 * np.sin((x + y) * 0.41)
    return (a + 2.6) / 5.2


def team_recolor(m, rgb_out, x_split=256):
    """Post-mirror cosmetic difference: east team cloth red, east barn weathered grey."""
    from wkh_core import unpack_rgb
    xs, ys, zs = np.nonzero(m[x_split + 1:] == P.CLOTH_TEAM)
    xs = xs + x_split + 1
    if len(xs):
        cur = unpack_rgb(rgb_out[xs, ys, zs]).astype(float)
        f = cur.mean(1, keepdims=True) / np.mean(C[P.CLOTH_TEAM])
        rgb_out[xs, ys, zs] = pack_rgb(np.array(TEAM_RED) * f)
    xs, ys, zs = np.nonzero(m[x_split + 1:] == P.BARN)
    xs = xs + x_split + 1
    if len(xs):
        cur = unpack_rgb(rgb_out[xs, ys, zs]).astype(float)
        f = cur.mean(1, keepdims=True) / np.mean(C[P.BARN])
        rgb_out[xs, ys, zs] = pack_rgb(np.array(BARN_GREY) * f)
    return rgb_out
