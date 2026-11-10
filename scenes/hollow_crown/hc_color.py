"""Colour pass: material ids -> 0xAARRGGBB for every surface voxel.

Restrained palette from the brief: charcoal/weathered stone, black slate + dark purple roofs, dead grass, muddy
brown, grey dirt, charcoal trunks, muted orange/amber pumpkins, pale grave stone and moss, with small accents of
blood red, ghostly cyan and sickly green. Variation is structured (coherent noise, masonry courses, slabs,
shingle rows, height ramps); per-voxel jitter is small. Noise is sampled on folded x so both halves match.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from hc_core import fbm2, fold_x, hash3, pack_rgb, surface_mask, unpack_rgb
import hc_props as P
from hc_build import SEED

C = {
    P.ROCK: (70, 66, 64), P.EARTH: (92, 76, 58), P.GRASS: (108, 102, 64), P.MUD: (92, 74, 54),
    P.DIRT_GREY: (104, 100, 94), P.PATH: (122, 106, 84), P.COBBLE: (96, 94, 96), P.COBBLE_DK: (74, 72, 76),
    P.FLAG: (112, 108, 106), P.FLAG_DK: (82, 78, 80), P.MOSS_GROUND: (76, 88, 58), P.LEAFLITTER: (112, 78, 46),
    P.STONE: (88, 86, 92), P.STONE_DK: (70, 68, 74), P.STONE_TRIM: (126, 122, 118), P.BRICK: (104, 78, 70),
    P.RUBBLE: (84, 82, 86), P.MARBLE_W: (150, 146, 140), P.MARBLE_B: (58, 56, 62), P.SLATE: (48, 46, 54),
    P.SLATE_P: (70, 52, 86), P.IRON: (44, 44, 50), P.TIMBER: (72, 54, 42), P.TIMBER_CHAR: (46, 40, 38),
    P.PLASTER: (150, 138, 116), P.WINDOW: (30, 28, 36), P.GLOW_AMBER: (250, 186, 84),
    P.GLOW_GREEN: (164, 214, 84), P.GLOW_CYAN: (130, 230, 220), P.CANDLE: (250, 236, 186),
    P.CLOTH_TEAM: (52, 74, 150), P.CLOTH_PURPLE: (76, 46, 96), P.CLOTH_BLOOD: (128, 26, 32),
    P.GOLD: (176, 142, 64), P.GEM_RED: (190, 34, 40), P.GEM_CYAN: (92, 200, 200), P.OBSIDIAN: (36, 32, 42),
    P.VELVET: (112, 22, 34), P.GRAVE: (148, 148, 144), P.GRAVE_MOSS: (112, 124, 98), P.BONE: (214, 206, 182),
    P.BONE_DK: (168, 158, 132), P.COFFIN: (70, 50, 40), P.PLANK: (110, 82, 58), P.AWNING_O: (196, 108, 40),
    P.AWNING_P: (84, 54, 100), P.TRUNK: (54, 50, 52), P.BRANCH: (70, 56, 46), P.ROOT: (62, 52, 46),
    P.PUMPKIN: (212, 112, 32), P.PUMPKIN_DK: (170, 80, 24), P.PUMPKIN_YEL: (204, 168, 74), P.STEM: (82, 92, 46),
    P.VINE: (74, 94, 48), P.JACK: (255, 178, 54), P.STRAW: (178, 152, 92), P.BOULDER: (98, 96, 96),
    P.MENHIR: (110, 108, 104), P.SOIL_DARK: (76, 60, 46), P.FURROW: (66, 52, 40), P.EMBER: (240, 128, 40),
    P.ASH: (52, 50, 52), P.WATER_DK: (34, 52, 58), P.CRACK: (60, 58, 62), P.ROOF_BEAM: (58, 44, 36),
    P.HAY: (176, 150, 84), P.BARREL: (96, 70, 48), P.CROWN_DK: (92, 60, 70),
}
TEAM_RED = (150, 40, 40)
EMISSIVE = (P.GLOW_AMBER, P.GLOW_GREEN, P.GLOW_CYAN, P.CANDLE, P.JACK, P.EMBER, P.GEM_RED, P.GEM_CYAN)


def colorize(m, F, graybox=False):
    solid = m > 0
    surf = surface_mask(solid)
    surf[:, :, 63] = True
    xs, ys, zs = np.nonzero(surf & solid)
    mat = m[xs, ys, zs]
    fx = np.minimum(xs, 512 - xs)
    rgb = np.zeros((len(xs), 3))
    for k, v in C.items():
        rgb[mat == k] = v
    if graybox:
        out = np.zeros(m.shape, np.uint32)
        out[xs, ys, zs] = pack_rgb(rgb)
        return out
    n_patch = fold_x(fbm2((512, 512), 18, 3, 'patch', SEED))
    n_fine = fold_x(fbm2((512, 512), 5, 2, 'fine', SEED))
    n_big = fold_x(fbm2((512, 512), 60, 2, 'big', SEED))
    npch = n_patch[xs, ys]; nfin = n_fine[xs, ys]; nbig = n_big[xs, ys]
    jit = hash3(fx, ys, zs, 7) - 0.5
    up_air = np.ones(len(xs), bool)
    k = zs > 0
    up_air[k] = ~solid[xs[k], ys[k], zs[k] - 1]
    side = ~up_air
    is_ = lambda *ms: np.isin(mat, ms)

    # ---------------- ground: dead grass blended with dry tan and dark olive; mud; grey dirt
    s = mat == P.GRASS
    t = np.clip((npch[s] - 0.35) / 0.35, 0, 1)
    col = np.array([96, 94, 58]) * (1 - t[:, None]) + np.array([128, 114, 72]) * t[:, None]
    w = np.clip((nfin[s] - 0.62) / 0.2, 0, 1)
    col = col * (1 - 0.45 * w[:, None]) + np.array([142, 128, 86]) * 0.45 * w[:, None]
    w = np.clip((0.4 - nbig[s]) / 0.2, 0, 1)
    col = col * (1 - 0.35 * w[:, None]) + np.array([76, 84, 52]) * 0.35 * w[:, None]
    rgb[s] = col
    for k_, amp in ((P.MUD, 0.16), (P.DIRT_GREY, 0.14), (P.PATH, 0.14), (P.MOSS_GROUND, 0.2),
                    (P.LEAFLITTER, 0.25), (P.SOIL_DARK, 0.16), (P.FURROW, 0.12), (P.EARTH, 0.14), (P.ROCK, 0.14)):
        s = mat == k_
        rgb[s] = rgb[s] * (1 - amp / 2 + amp * (0.6 * nfin[s] + 0.4 * (jit[s] + 0.5)))[:, None]
    s = mat == P.LEAFLITTER
    tmp = rgb[s]; alt = hash3(fx[s], ys[s], 0, 31) < 0.4
    tmp[alt] = tmp[alt] * 0.6 + np.array([150, 70, 32]) * 0.4; rgb[s] = tmp
    # path: lighter centre, dusty edges
    pm = F.get('path_mask')
    if pm is not None:
        pmf = pm.copy(); pmf[257:] = pm[255:0:-1]
        d = ndi.distance_transform_edt(pmf)
        s = mat == P.PATH
        dd = np.clip(d[xs[s], ys[s]] / 2.5, 0, 1)
        rgb[s] = rgb[s] * (0.88 + 0.16 * dd[:, None])
    # rock / earth strata on cut faces
    s = is_(P.ROCK, P.EARTH) & side
    band = 0.5 + 0.5 * np.sin(zs[s] * 1.1 + nbig[s] * 8)
    rgb[s] = rgb[s] * (0.86 + 0.18 * band[:, None])

    # ---------------- paving
    s = mat == P.FLAG                           # big slabs 6x6 (offset rows), slab-to-slab tone, soft joints
    gx = fx[s]; gy = ys[s] + (gx // 6 % 2) * 3
    joint = (gx % 6 == 0) | (gy % 6 == 0)
    slab = hash3(gx // 6, gy // 6, 0, 41)
    col = rgb[s] * (0.9 + 0.16 * slab[:, None])
    col[joint] *= 0.92
    col = col * (1 - 0.18 * np.clip((nbig[s] - 0.55) / 0.2, 0, 1))[:, None] + \
        np.array([84, 92, 66]) * 0.18 * np.clip((nbig[s] - 0.55) / 0.2, 0, 1)[:, None]
    rgb[s] = col
    s = is_(P.COBBLE, P.COBBLE_DK)
    c = (hash3(fx[s] // 2, (ys[s] + (fx[s] // 2) % 2) // 2, 0, 43) - 0.5)
    rgb[s] = rgb[s] * (1 + 0.22 * c[:, None])
    e = ((fx[s] % 2 == 0) & (ys[s] % 2 == 0))
    tmp = rgb[s]; tmp[e] *= 0.93; rgb[s] = tmp
    s = is_(P.MARBLE_W, P.MARBLE_B)
    rgb[s] = rgb[s] * (0.94 + 0.12 * nfin[s][:, None]) + jit[s][:, None] * 6

    # ---------------- masonry: soft block mottling by course (3 high) and block (5 long), soot high, moss low
    s = is_(P.STONE, P.STONE_DK, P.RUBBLE)
    zz = zs[s]
    course = zz // 3
    along = fx[s] + ys[s] + (course % 2) * 2
    blk = hash3(along // 5, course, 0, 51)
    col = rgb[s] * (0.93 + 0.13 * blk[:, None]) * (0.95 + 0.08 * nfin[s][:, None])
    moss = np.clip((zz - 34) / 10, 0, 1) * np.clip((npch[s] - 0.35) / 0.3, 0, 1)
    col = col * (1 - 0.5 * moss[:, None]) + np.array([66, 82, 52]) * 0.5 * moss[:, None]
    soot = np.clip((28 - zz) / 20, 0, 1) * 0.10
    col = col * (1 - soot[:, None])
    streak = (hash3(fx[s], ys[s], 0, 61) < 0.06) & side[s]
    col[streak] *= 0.9
    rgb[s] = col
    s = mat == P.BRICK
    zz = zs[s]
    col = rgb[s] * (0.88 + 0.2 * hash3((fx[s] + ys[s] + (zz % 2) * 2) // 3, zz, 0, 53)[:, None])
    rgb[s] = col
    s = mat == P.STONE_TRIM
    rgb[s] = rgb[s] * (0.94 + 0.1 * nfin[s][:, None])
    s = mat == P.RUBBLE
    rgb[s] = rgb[s] * (0.85 + 0.3 * (hash3(fx[s], ys[s], zs[s], 3)[:, None]))

    # ---------------- roofs: shingle rows (alternate courses), purple banding fades with height
    s = is_(P.SLATE, P.SLATE_P)
    row = zs[s] % 2 == 0
    tab = ((fx[s] + ys[s] + zs[s]) % 3 == 0)
    col = rgb[s] * np.where(row, 1.0, 0.86)[:, None] * (0.94 + 0.1 * nfin[s])[:, None]
    col[tab] *= 0.92
    rgb[s] = col

    # ---------------- wood, cloth, organic
    for k_ in (P.TIMBER, P.PLANK, P.COFFIN, P.BARREL, P.ROOF_BEAM, P.TIMBER_CHAR):
        s = mat == k_
        board = ((fx[s] + ys[s]) % 2 == 0)
        rgb[s] = rgb[s] * (np.where(board, 1.0, 0.9) * (0.93 + 0.12 * nfin[s]))[:, None]
    s = mat == P.BARREL
    hoop = (zs[s] % 2 == 0)
    tmp = rgb[s]; tmp[hoop] = tmp[hoop] * 0.55 + np.array([40, 40, 44]) * 0.45; rgb[s] = tmp
    s = mat == P.PLASTER
    rgb[s] = rgb[s] * (0.9 + 0.14 * npch[s][:, None]) + np.array([0, 4, 0]) * (npch[s][:, None] < 0.4)
    for k_, amp in ((P.TRUNK, 0.16), (P.BRANCH, 0.18), (P.ROOT, 0.2), (P.PUMPKIN, 0.1), (P.PUMPKIN_DK, 0.1),
                    (P.PUMPKIN_YEL, 0.1), (P.VINE, 0.25), (P.STRAW, 0.18), (P.HAY, 0.16), (P.CLOTH_PURPLE, 0.14),
                    (P.CLOTH_TEAM, 0.12), (P.CLOTH_BLOOD, 0.14), (P.GRAVE, 0.12), (P.GRAVE_MOSS, 0.18),
                    (P.BONE, 0.08), (P.BONE_DK, 0.1), (P.MENHIR, 0.14), (P.BOULDER, 0.16), (P.GOLD, 0.14),
                    (P.AWNING_O, 0.08), (P.AWNING_P, 0.08), (P.OBSIDIAN, 0.12), (P.VELVET, 0.12)):
        s = mat == k_
        rgb[s] = rgb[s] * (1 - amp / 2 + amp * (0.6 * nfin[s] + 0.4 * (jit[s] + 0.5)))[:, None]
    # moss caps on graves, menhirs and boulders (tops greener)
    s = is_(P.GRAVE, P.GRAVE_MOSS, P.MENHIR, P.BOULDER) & up_air
    rgb[s] = rgb[s] * 0.7 + np.array([80, 100, 62]) * 0.3
    # bone: darker in the crevices (sides lower down)
    s = is_(P.BONE, P.BONE_DK) & side
    rgb[s] *= 0.92
    # trunk bark: vertical fissures
    s = mat == P.TRUNK
    fis = ((fx[s] * 7 + ys[s] * 3) % 5 == 0)
    tmp = rgb[s]; tmp[fis] *= 0.8; rgb[s] = tmp
    # gold: tarnish toward the base
    s = mat == P.GOLD
    tz = np.clip((zs[s] - 34) / 8, 0, 1)
    rgb[s] = rgb[s] * (1 - 0.25 * tz[:, None]) + np.array([90, 84, 50]) * 0.25 * tz[:, None]
    # jack-o'-lantern glow: hot core, slight flicker variation
    s = mat == P.JACK
    t = hash3(fx[s], ys[s], zs[s], 9)
    rgb[s] = np.array([255, 158, 40]) * (1 - t[:, None]) + np.array([255, 206, 90]) * t[:, None]
    s = mat == P.EMBER
    t = hash3(fx[s], ys[s], zs[s], 3)
    rgb[s] = np.array([214, 96, 30]) * (1 - t[:, None]) + np.array([255, 170, 60]) * t[:, None]

    # ---------------- ghost-light pools painted on the ground around cyan/green lamps (colour device only)
    glow2d = np.zeros((512, 512), bool)
    gl = np.isin(m, [P.GLOW_CYAN, P.GLOW_GREEN]).any(axis=2)
    if gl.any():
        dist = ndi.distance_transform_edt(~gl)
        s = up_air & is_(P.GRASS, P.MUD, P.DIRT_GREY, P.PATH, P.FLAG, P.COBBLE, P.SOIL_DARK, P.MOSS_GROUND,
                         P.MARBLE_W, P.MARBLE_B, P.FLAG_DK)
        d = dist[xs[s], ys[s]]
        w = np.clip(1 - d / 4.5, 0, 1) * 0.28
        rgb[s] = rgb[s] * (1 - w[:, None]) + np.array([120, 190, 170]) * w[:, None]
    amb = np.isin(m, [P.GLOW_AMBER, P.JACK, P.EMBER]).any(axis=2)
    if amb.any():
        dist = ndi.distance_transform_edt(~amb)
        s = up_air & is_(P.GRASS, P.MUD, P.DIRT_GREY, P.PATH, P.FLAG, P.COBBLE, P.COBBLE_DK, P.SOIL_DARK,
                         P.FURROW, P.VINE)
        d = dist[xs[s], ys[s]]
        w = np.clip(1 - d / 5.0, 0, 1) * 0.22
        rgb[s] = rgb[s] * (1 - w[:, None]) + np.array([210, 140, 70]) * w[:, None]

    # ---------------- face shading + height lift (not for emissive materials)
    emissive = np.isin(mat, EMISSIVE)
    s = side & ~emissive
    rgb[s] *= 0.86
    lift = np.clip((48 - zs) / 40, 0, 1) * 0.07
    rgb[~emissive] *= (1 + lift[~emissive])[:, None]
    rgb += jit[:, None] * 4 * (~emissive)[:, None]
    # floor luma guard (>= ~40)
    luma = rgb @ np.array([0.299, 0.587, 0.114])
    low = (luma < 40) & up_air & ~emissive
    rgb[low] *= (40 / np.maximum(luma[low], 1))[:, None]
    out = np.zeros(m.shape, np.uint32)
    out[xs, ys, zs] = pack_rgb(rgb)
    return out


def team_recolor(m, rgb_out, x_split=256):
    xs, ys, zs = np.nonzero(m[x_split + 1:] == P.CLOTH_TEAM)
    xs = xs + x_split + 1
    if len(xs):
        cur = unpack_rgb(rgb_out[xs, ys, zs]).astype(float)
        f = cur.mean(1, keepdims=True) / np.mean(C[P.CLOTH_TEAM])
        rgb_out[xs, ys, zs] = pack_rgb(np.clip(np.array(TEAM_RED) * f, 0, 255))
    return rgb_out


FONT = {
    'T': ['#####', '..#..', '..#..', '..#..', '..#..', '..#..', '..#..'],
    'H': ['#...#', '#...#', '#...#', '#####', '#...#', '#...#', '#...#'],
    'E': ['#####', '#....', '#....', '####.', '#....', '#....', '#####'],
    'O': ['.###.', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'],
    'L': ['#....', '#....', '#....', '#....', '#....', '#....', '#####'],
    'W': ['#...#', '#...#', '#...#', '#.#.#', '#.#.#', '##.##', '#...#'],
    'C': ['.####', '#....', '#....', '#....', '#....', '#....', '.####'],
    'R': ['####.', '#...#', '#...#', '####.', '#.#..', '#..#.', '#...#'],
    'N': ['#...#', '##..#', '#.#.#', '#..##', '#...#', '#...#', '#...#'],
    ' ': ['.....'] * 7,
}


def paint_tag(m, color, text, x0, y0, scale=1, rgb=(214, 204, 176)):
    """Paint the map name onto the ground tops in the SW corner (colour only). Returns the tag rectangle."""
    solid = m > 0
    top = np.argmax(solid, axis=2)
    x = x0
    for ch in text:
        g = FONT[ch]
        for r, row in enumerate(g):
            for c, v in enumerate(row):
                if v == '#':
                    for dx in range(scale):
                        for dy in range(scale):
                            cx, cy = x + c * scale + dx, y0 + r * scale + dy
                            z = top[cx, cy]
                            color[cx, cy, z] = pack_rgb(np.array(rgb, float))
        x += 6 * scale
    return (x0, x, y0, y0 + 7 * scale)
