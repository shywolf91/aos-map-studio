"""Colour pass for Silverpine Hunt: material ids -> 0xAARRGGBB for every surface voxel.

Anti-white palette: snow is shaded blue-grey / lilac (never pure white, max ~210), covers only part of the ground;
forest floors are rust needles and moss, open ground mixes winter grass, earth and trampled slush. Variation is
structured (coherent noise, strata, height ramps); noise is sampled on x folded about 256 so the mirror matches.
"""
from __future__ import annotations

import numpy as np

from sph_core import fbm2, fold_x, hash3, pack_rgb, surface_mask, unpack_rgb
import sph_props as P
from sph_terrain import SEED

C = {
    P.SNOW: (172, 180, 202), P.SNOW_TRACK: (146, 144, 156), P.DRYGRASS: (122, 108, 74), P.NEEDLE: (94, 66, 46),
    P.MOSS: (66, 84, 56), P.EARTH: (98, 78, 60), P.EARTH_DK: (70, 56, 46), P.PATH: (118, 104, 94),
    P.MUD: (84, 68, 56), P.ROCK: (92, 94, 108), P.ROCK_DK: (62, 60, 70), P.CLIFF: (92, 94, 108),
    P.ICE: (92, 146, 176), P.ICE_DK: (52, 90, 124), P.ICE_LT: (150, 194, 214), P.ICICLE: (168, 206, 224),
    P.GRAVEL: (108, 104, 104), P.CAVE_ROCK: (72, 66, 72), P.CAVE_FLOOR: (86, 74, 66), P.BLOOD_SNOW: (146, 48, 56),
    P.PAW: (124, 126, 148),
    P.LOG: (106, 72, 48), P.LOG_DK: (80, 54, 38), P.PLANK: (132, 98, 66), P.PLANK_DK: (94, 68, 48),
    P.ROOF: (64, 58, 68), P.ROOF_DK: (48, 44, 54), P.BARK: (80, 60, 48), P.BARK_DK: (58, 44, 38),
    P.SCOTS_BARK: (160, 94, 58), P.DEADWOOD: (114, 106, 100), P.BIRCH: (184, 178, 166), P.CLAW_BARK: (150, 100, 76),
    P.TIMBER: (98, 74, 52),
    P.FROST: (150, 168, 178), P.RUST: (152, 84, 42), P.SNOWCAP: (164, 172, 194), P.WOLFSBANE: (116, 66, 156),
    P.LEAFY: (62, 88, 52), P.CONE: (98, 64, 42),
    P.STONE: (122, 118, 122), P.STONE_DK: (88, 86, 92), P.MOSS_STONE: (86, 98, 72), P.IRON: (72, 72, 78),
    P.IRON_DK: (46, 46, 52), P.SILVER: (198, 206, 222), P.ORE: (150, 160, 180), P.RAIL: (82, 76, 74),
    P.GLOW: (255, 196, 104), P.LANTERN: (255, 172, 66), P.EMBER: (242, 112, 42), P.EYE: (255, 72, 30),
    P.CANDLE: (252, 226, 160), P.MOONGLOW: (150, 220, 255), P.JACK: (255, 164, 42),
    P.PELT: (112, 84, 62), P.PELT_GREY: (106, 102, 100), P.PELT_RED: (130, 54, 48), P.CANVAS: (166, 152, 124),
    P.CLOTH_TEAM: (54, 74, 164), P.ROPE: (142, 120, 86), P.RAG_RED: (158, 32, 36), P.COAT: (72, 58, 54),
    P.BONE: (186, 174, 148), P.BONE_DK: (140, 128, 106), P.BLOOD: (132, 22, 28), P.STRAW: (176, 148, 90),
    P.PUMPKIN: (214, 110, 32),
    P.FUR_DK: (60, 52, 52), P.FUR: (84, 74, 70), P.FUR_LT: (130, 118, 106), P.FUR_TIP: (104, 96, 94),
    P.CLAW: (32, 30, 34), P.FANG: (222, 216, 192), P.NOSE: (26, 24, 28), P.MAW: (56, 20, 24), P.EAR_IN: (122, 72, 72),
    P.MOON: (226, 224, 206), P.MOON_DK: (186, 184, 170), P.MOON_RIM: (240, 238, 222), P.BAT: (42, 36, 50),
    P.BAT_EYE: (240, 92, 40), P.CROW: (28, 26, 34), P.CROW_BEAK: (122, 102, 62),
}
FOL = {  # (inner/dark, outer/light) - v2: a calm, close family of dark conifer greens (neighbours similar)
    P.FOL0: ((26, 46, 36), (50, 78, 58)), P.FOL1: ((24, 46, 40), (46, 76, 64)),
    P.FOL2: ((24, 46, 46), (44, 76, 72)), P.FOL3: ((26, 46, 52), (48, 78, 82)),
    P.FOL4: ((30, 48, 56), (56, 80, 90)), P.FOL5: ((30, 50, 40), (58, 82, 60)),
    P.FOL6: ((32, 50, 34), (60, 84, 52)), P.FOL7: ((28, 48, 38), (54, 80, 56)),
}
TEAM_RED = (164, 40, 40)


def _blend(a, b, t):
    t = np.clip(t, 0, 1)[:, None]
    return np.array(a, float) * (1 - t) + np.array(b, float) * t


def colorize_base(m):
    solid = m > 0
    surf = surface_mask(solid)
    xs, ys, zs = np.nonzero(surf)
    mat = m[xs, ys, zs]
    fx = np.minimum(xs, 512 - xs)
    rgb = np.zeros((len(xs), 3))
    for k, v in C.items():
        rgb[mat == k] = v
    n_patch = fold_x(fbm2((512, 512), 18, 3, 'cpatch', SEED))[xs, ys]
    n_fine = fold_x(fbm2((512, 512), 5, 2, 'cfine', SEED))[xs, ys]
    n_big = fold_x(fbm2((512, 512), 70, 2, 'cbig', SEED))[xs, ys]
    jit = hash3(fx, ys, zs, 7) - 0.5
    up = np.ones(len(xs), bool)
    k = zs > 0
    up[k] = ~solid[xs[k], ys[k], zs[k] - 1]
    side = ~up

    # ---- snow: lilac shadow -> blue-grey -> cool lit crest; hollows bluer, side faces darker
    s = mat == P.SNOW
    t = n_patch[s] * 0.7 + n_big[s] * 0.3
    col = _blend((150, 156, 186), (186, 194, 212), (t - 0.3) / 0.45)
    col = col * (0.95 + 0.07 * n_fine[s][:, None])
    col[side[s]] *= 0.84
    rgb[s] = col
    s = mat == P.SNOWCAP
    rgb[s] = _blend((150, 158, 184), (170, 178, 200), n_fine[s]) * np.where(side[s], 0.88, 1.0)[:, None]
    s = mat == P.SNOW_TRACK
    rgb[s] = _blend((132, 128, 140), (158, 156, 168), n_fine[s])
    s = mat == P.PAW
    rgb[s] = _blend((112, 112, 136), (130, 130, 152), n_fine[s])
    # ---- winter grass / earth / needles / moss: warm counterweights to the snow
    s = mat == P.DRYGRASS
    rgb[s] = _blend((104, 98, 62), (144, 122, 82), n_patch[s] * 0.6 + n_fine[s] * 0.4)
    s = mat == P.NEEDLE
    rgb[s] = _blend((76, 54, 40), (118, 76, 48), n_fine[s] * 0.6 + n_patch[s] * 0.4)
    s = mat == P.MOSS
    rgb[s] = _blend((54, 72, 48), (82, 98, 62), n_fine[s])
    s = np.isin(mat, [P.EARTH, P.EARTH_DK, P.MUD, P.PATH, P.CAVE_FLOOR])
    rgb[s] *= (0.9 + 0.2 * n_fine[s])[:, None]
    s = mat == P.BLOOD_SNOW
    rgb[s] = _blend((104, 28, 36), (156, 60, 66), n_fine[s])
    # ---- rock: strata bands by depth + coherent tone; snow-dusted ledge lips
    s = np.isin(mat, [P.ROCK, P.CLIFF])
    band = ((zs[s] + (n_big[s] * 6).astype(int)) // 3) % 3
    base = np.array([(84, 86, 100), (104, 104, 116), (74, 76, 92)], float)[band]
    base *= (0.9 + 0.18 * n_patch[s])[:, None]
    warm = np.clip((n_fine[s] - 0.62) / 0.2, 0, 1)[:, None]          # lichen / iron stain
    base = base * (1 - 0.35 * warm) + np.array([104, 88, 74]) * 0.35 * warm
    base[side[s]] *= 0.88
    rgb[s] = base
    s = mat == P.GRAVEL
    rgb[s] *= (0.88 + 0.24 * n_fine[s])[:, None]
    s = mat == P.CAVE_ROCK
    rgb[s] = _blend((60, 54, 62), (84, 78, 84), n_fine[s])
    # ---- ice: teal with paler streaks, deep blue in grooves
    s = np.isin(mat, [P.ICE])
    rgb[s] = _blend((78, 132, 166), (118, 170, 194), n_fine[s] * 0.6 + n_patch[s] * 0.4)
    s = mat == P.ICE_DK
    rgb[s] = _blend((40, 74, 108), (62, 102, 136), n_fine[s])
    s = mat == P.ORE
    spark = hash3(xs[s], ys[s], zs[s], 21) > 0.82
    rgb[s] = np.where(spark[:, None], np.array([214, 222, 236], float), rgb[s])
    # ---- foliage: inner dark -> outer light, sky-facing tops lighter, plus coherent per-area hue drift
    for kmat, (dk, lt) in FOL.items():
        s = mat == kmat
        if not s.any():
            continue
        t = 0.25 + 0.42 * up[s] + 0.25 * (n_fine[s] - 0.5) + 0.07 * (hash3(xs[s], ys[s], zs[s], 3) - 0.5)
        col = _blend(dk, lt, t)
        col *= (0.94 + 0.12 * n_patch[s])[:, None]
        rgb[s] = col
    # ---- wood: log courses / plank grain / roofs with snow
    s = np.isin(mat, [P.LOG, P.LOG_DK, P.PLANK, P.PLANK_DK, P.TIMBER])
    grain = (hash3(fx[s] // 2, ys[s] // 2, zs[s], 5) - 0.5) * 0.14
    rgb[s] *= (1 + grain)[:, None]
    s = np.isin(mat, [P.ROOF, P.ROOF_DK])
    snowroof = up[s] & ((0.7 * n_big[s] + 0.3 * n_patch[s]) > 0.5)
    col = rgb[s] * (0.9 + 0.12 * (hash3(fx[s], ys[s] // 2, zs[s], 6))[:, None])
    col[snowroof] = _blend((160, 168, 192), (186, 194, 212), n_fine[s][snowroof])
    rgb[s] = col
    s = np.isin(mat, [P.BARK, P.BARK_DK, P.SCOTS_BARK, P.DEADWOOD])
    rgb[s] *= (0.86 + 0.2 * hash3(fx[s], ys[s], zs[s] // 2, 8))[:, None]
    s = mat == P.SCOTS_BARK
    rgb[s] = _blend((140, 80, 50), (176, 108, 64), hash3(fx[s], ys[s], zs[s] // 3, 10))
    # ---- fur: strand streaks, darker toward the back, tips lighter
    s = np.isin(mat, [P.FUR_DK, P.FUR, P.FUR_TIP])
    strand = hash3(fx[s] // 1, ys[s], zs[s] // 2, 31)
    rgb[s] *= (0.82 + 0.3 * strand)[:, None]
    s = np.isin(mat, [P.BONE, P.BONE_DK, P.FANG])
    rgb[s] *= (0.9 + 0.14 * n_fine[s] + 0.06 * jit[s])[:, None]
    s = np.isin(mat, [P.STONE, P.STONE_DK])
    rgb[s] *= (0.88 + 0.2 * hash3(fx[s] // 2, ys[s] // 2, zs[s], 12))[:, None]
    # general small jitter for everything not emissive
    emissive = np.isin(mat, [P.GLOW, P.LANTERN, P.EMBER, P.EYE, P.CANDLE, P.MOONGLOW, P.JACK, P.SILVER])
    rgb[~emissive] *= (1 + 0.015 * jit[~emissive])[:, None]
    # team cloth: east = red
    s = (mat == P.CLOTH_TEAM) & (xs > 256)
    rgb[s] = TEAM_RED
    return xs, ys, zs, mat, rgb, up, n_patch, n_fine


EMISSIVE = None


def colorize(m, cover=None):
    """v2: base colours -> continuous ground cover on terrain tops -> baked moonlight + ambient occlusion."""
    from scipy import ndimage as ndi
    xs, ys, zs, mat, rgb, up, n_patch, n_fine = colorize_base(m)
    solid = m > 0
    terr = np.isin(mat, list(P.TERRAIN_MATS)) & ~np.isin(mat, [P.PAW, P.CAVE_FLOOR, P.CAVE_ROCK, P.BLOOD_SNOW])
    if cover is not None:
        w = cover['w'][xs, ys]; gcol = cover['gcol'][xs, ys]; top = cover['top'][xs, ys]
        near_top = terr & (zs >= top) & (zs <= top + 2)
        snow = np.array([172, 180, 202.]) * (0.96 + 0.08 * n_patch)[:, None]
        # top voxel: blend by the snow weight; side voxels just under a snowy lip keep a snow drape
        drape = np.where(up, 1.0, np.where(zs == top, 0.8, 0.45))
        ww = np.clip(w * drape, 0, 1)[:, None]
        rgb[near_top] = (gcol * (1 - ww) + snow * ww)[near_top]
        # rock faces below the top on mountains: slate with soft strata, no hard bands
        deep = terr & (zs > top + 2) & np.isin(mat, [P.ROCK])
        band = 0.92 + 0.1 * np.sin(zs[deep] * 0.9 + n_patch[deep] * 6)
        rgb[deep] = np.array([88, 90, 104.]) * band[:, None]
    # ---- baked lighting: moon from the north-west, high; plus ambient occlusion
    S = solid.astype(np.float32)
    G = ndi.gaussian_filter(S, 1.5)
    gx = np.zeros(len(xs), np.float32); gy = np.zeros_like(gx); gz = np.zeros_like(gx)
    def samp(a, dx, dy, dz):
        x2 = np.clip(xs + dx, 0, 511); y2 = np.clip(ys + dy, 0, 511); z2 = np.clip(zs + dz, 0, 63)
        return a[x2, y2, z2]
    gx = samp(G, 1, 0, 0) - samp(G, -1, 0, 0)
    gy = samp(G, 0, 1, 0) - samp(G, 0, -1, 0)
    gz = samp(G, 0, 0, 1) - samp(G, 0, 0, -1)
    n = -np.stack([gx, gy, gz], 1)
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-6
    L = np.array([-0.45, -0.5, -0.74]); L /= np.linalg.norm(L)
    diff = np.clip(n @ L, -0.25, 1.0)
    shade = 0.62 + 0.46 * diff
    G2 = ndi.gaussian_filter(S, 2.6)
    occ = samp(G2, 0, 0, 0)
    ao = np.clip(1.0 - 1.05 * (occ - 0.5), 0.7, 1.12)
    emissive = np.isin(mat, [P.GLOW, P.LANTERN, P.EMBER, P.EYE, P.CANDLE, P.MOONGLOW, P.JACK, P.SILVER,
                             P.MOON, P.MOON_DK, P.MOON_RIM])
    f = np.where(emissive, 1.0, shade * ao)
    rgb = rgb * f[:, None]
    # keep snow off pure white
    snowy = (rgb.min(1) > 150)
    peak = rgb.max(1)
    sc = np.where(snowy & (peak > 212), 212 / np.maximum(peak, 1), 1.0)
    rgb = rgb * sc[:, None]
    # floors never pitch black (owner rule: luma >= ~40) except emissive/eyes
    luma = rgb @ np.array([0.299, 0.587, 0.114])
    lift = np.where(~emissive & (luma < 40), 40 / np.maximum(luma, 1), 1.0)
    rgb = np.clip(rgb * np.minimum(lift, 2.0)[:, None], 0, 255)
    out = np.zeros(m.shape, np.uint32)
    out[xs, ys, zs] = pack_rgb(rgb)
    return out, {'surface_voxels': int(len(xs))}


def ground_stats(m, color):
    """Share of the top-down view by material family + mean luma of the top-down colour."""
    solid = m > 0
    top = np.argmax(solid, axis=2)
    X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    tm = m[X, Y, top]
    rgb = unpack_rgb(color[X, Y, top]).astype(float)
    luma = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    fam = {
        'snow_white': [P.SNOW, P.SNOWCAP],
        'trampled_snow': [P.SNOW_TRACK, P.PAW],
        'foliage': list(FOL.keys()) + [P.FROST, P.RUST],
        'rock': [P.ROCK, P.ROCK_DK, P.CLIFF, P.GRAVEL, P.STONE, P.STONE_DK],
        'ice': [P.ICE, P.ICE_DK, P.ICE_LT, P.ICICLE],
        'earth_grass_needles': [P.DRYGRASS, P.NEEDLE, P.MOSS, P.EARTH, P.EARTH_DK, P.PATH, P.MUD, P.BLOOD_SNOW,
                                P.CAVE_FLOOR, P.STRAW],
        'roofs': [P.ROOF, P.ROOF_DK],
    }
    out = {k: round(100 * float(np.isin(tm, v).mean()), 1) for k, v in fam.items()}
    out['other'] = round(100 - sum(out.values()), 1)
    bright = (luma > 175).mean()
    out['topdown_mean_luma'] = round(float(luma.mean()), 1)
    out['topdown_pct_luma_over_175'] = round(100 * float(bright), 1)
    return out
