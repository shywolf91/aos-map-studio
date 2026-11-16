"""Assemble Silverpine Hunt: terrain -> caves/tunnel -> landmarks -> camps -> forest -> scatter -> ground paint
-> mirror (x' = 512 - x) -> cleanup.  The west half (x < 256) and the axis are authored; the east half is the mirror.
"""
from __future__ import annotations

import math
import sys

import numpy as np
from scipy import ndimage as ndi

from sph_core import fbm2, fold_x
from sph_props import *            # noqa: F401,F403
from sph_props import AIR, M, TERRAIN_MATS, Vox, hsh
import sph_structs as S
import sph_landmarks as LM
import sph_trees as T
from sph_terrain import PZ, SEED, SPEC, seg_dist, terrain

NAME = 'Silverpine Hunt'
FILE = 'silverpine_hunt'
VERSION = '2.2'

SQ = [(98, 138, 236, 276), (374, 414, 236, 276)]
LODGE = (92, 130, 196, 224)
PATHS = [   # west half (mirrored); trampled trails
    [(118, 232), (122, 226)],
    [(112, 196), (124, 172), (150, 160), (196, 150), (236, 146), (256, 146)],
    [(100, 196), (112, 160), (118, 138)],
    [(150, 160), (168, 136), (196, 128)],
    [(118, 280), (124, 300), (150, 326), (170, 346), (172, 380), (170, 404)],
    [(104, 300), (100, 330), (112, 356)],
    [(150, 326), (190, 320), (226, 330), (246, 340)],
    [(256, 336), (256, 352)], [(256, 386), (256, 396)],
    [(170, 404), (186, 420)],
    [(140, 256), (212, 256)],
    [(196, 150), (214, 172), (236, 182)],
]
PAWS = [[(256, 178), (256, 160), (240, 150), (218, 140), (204, 124)],
        [(250, 338), (230, 332), (196, 338), (176, 344)],
        [(226, 296), (204, 300), (180, 290)]]


# ------------------------------------------------------------------ terrain voxelisation

def pads(F):
    H = F['H']
    for (x0, x1, y0, y1) in [LODGE, (70, 80, 251, 261), (94, 108, 286, 299), (110, 136, 286, 300),
                             (84, 120, 356, 384), (120, 150, 358, 392)]:
        for (a, b) in ((x0, x1), (512 - x1, 512 - x0)):
            sub = H[a - 2:b + 3, y0 - 2:y1 + 3]
            H[a - 2:b + 3, y0 - 2:y1 + 3] = int(np.median(sub))
    F['H'] = fold_x(H)


def voxelize(V, F):
    H = F['H']; kind = F['kind']
    zz = np.arange(64)[None, None, :]
    solid = zz >= H[:, :, None]
    V.m[solid] = ROCK
    depth = zz - H[:, :, None]
    soft = (kind == 0) | (kind == 6)
    V.m[solid & (depth >= 1) & (depth <= 3) & soft[:, :, None]] = EARTH
    xs, ys = np.nonzero(np.ones((512, 512), bool))
    top = H[xs, ys]
    k = kind[xs, ys]
    mat = np.full(len(xs), SNOW, np.uint8)
    mat[k == 1] = ROCK; mat[k == 4] = ROCK; mat[k == 5] = ROCK
    mat[k == 2] = ICE; mat[k == 3] = ICE
    V.m[xs, ys, top] = mat
    # 2-deep creek beds: the ice is the top voxel; under it dark water-ice
    V.m[:, :, 62:] = ROCK


def carve_tunnel(V, rng):
    t = SPEC['tunnel']
    (x0, x1), (y0, y1) = t['x'], t['y']
    za, zb = t['z_air']
    for x in range(x0, 257):
        for y in range(y0, y1 + 1):
            if V.H[x, y] < PZ - 1:                         # only through rock
                V.box(x, x, y, y, za, zb, AIR)
                V.put(x, y, PZ, CAVE_FLOOR if y not in (y0 + 3, y1 - 3) else RAIL)
    # walls / ceiling dressing
    for x in range(x0, 257):
        for y in range(y0 - 1, y1 + 2):
            for z in range(za - 1, zb + 1):
                if V.get(x, y, z) == ROCK and (V.get(x, y + 1, z) == AIR or V.get(x, y - 1, z) == AIR or
                                               V.get(x, y, z + 1) == AIR):
                    V.put(x, y, z, CAVE_ROCK)
    # shoring frames + lanterns
    frames = []
    for x in range(x0 + 4, 257, 6):
        if V.get(x, y0 + 4, zb) == AIR and V.get(x, y0 - 1, za) != AIR:
            S.mine_frame(V, x, y0, y1, PZ, h=zb - za + 1)
            frames.append(x)
    for x in frames[::2]:
        S.hanging_lantern(V, x, (y0 + y1) // 2, za, drop=1) if False else V.put(x, (y0 + y1) // 2, za + 1, LANTERN)
    # ore chamber off the tunnel (south side)
    cx0, cx1 = 198, 212
    for x in range(cx0, cx1 + 1):
        for y in range(y1 + 1, y1 + 9):
            if V.H[x, y] < PZ - 2:
                V.box(x, x, y, y, za + 1, zb, AIR)
                V.put(x, y, PZ, CAVE_FLOOR)
    S.ore_cart(V, cx0 + 2, y1 + 3, PZ, along_x=True)
    for (ox, oy) in ((cx1 - 3, y1 + 6), (cx1 - 1, y1 + 5), (cx0 + 8, y1 + 7)):
        V.put(ox, oy, PZ - 1, ORE); V.put(ox + 1, oy, PZ - 1, GRAVEL)
    crate(V, cx1 - 2, y1 + 2, PZ)
    V.put(cx0 + 6, y1 + 7, PZ - 1, LANTERN)
    S.ore_cart(V, 228, y0 + 2, PZ, along_x=True)
    return frames


# ------------------------------------------------------------------ paint ground

def paint_ground(V, F, rng):
    """v2: continuous ground cover. Computes a smooth snow-cover weight and a ground colour per column (stored in
    V.cover for the colour pass) and sets the top materials accordingly (snow where w > 0.5)."""
    H = F['H']; kind = F['kind']
    X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    n_big = fold_x(fbm2((512, 512), 90, 3, 'gc_big', SEED))
    n_mid = fold_x(fbm2((512, 512), 34, 3, 'gc_mid', SEED))
    n_fin = fold_x(fbm2((512, 512), 9, 2, 'gc_fin', SEED))
    top = H
    cur = V.m[X, Y, top]
    fol = np.isin(V.m, list(FOLS) + [SNOWCAP])
    zz = np.arange(64)[None, None, :]
    win = (zz < top[:, :, None]) & (zz >= top[:, :, None] - 18)
    canopy = ndi.gaussian_filter((fol & win).any(axis=2).astype(float), 2.5)
    canopy = np.clip(canopy * 1.6, 0, 1)
    pd = np.full((512, 512), 1e9)
    for p in PATHS:
        pd = np.minimum(pd, seg_dist(X, Y, p))
        pd = np.minimum(pd, seg_dist(X, Y, [(512 - a, b) for a, b in p]))
    path = np.clip(1 - (pd - 1.0) / 2.5, 0, 1)
    def soft_rect(x0, x1, y0, y1, sig):
        r = np.zeros((512, 512)); r[x0:x1 + 1, y0:y1 + 1] = 1; r[512 - x1:512 - x0 + 1, y0:y1 + 1] = 1
        return ndi.gaussian_filter(r, sig)
    yard = np.clip(soft_rect(70, 146, 192, 312, 7) * 1.2, 0, 1) * (0.55 + 0.45 * n_mid)
    den = np.clip(ndi.gaussian_filter(((np.hypot((X - 256) / 48.0, (Y - 256) / 36.0)) < 1).astype(float), 8) * 1.3, 0, 1)
    lane = np.clip(1 - (np.abs(Y - 256) - 3) / 3.0, 0, 1) * soft_rect(140, 211, 240, 272, 1.5)
    trample = np.clip(np.maximum.reduce([path, yard * 0.85, den * 0.9, lane * 0.8]), 0, 1)
    # snow weight: open ground white-ish, forest floors and trampled ground bare, a few big soft bare patches
    w = 0.92 - 1.15 * canopy - 1.0 * trample - 0.55 * np.clip((0.38 - n_big) / 0.18, 0, 1) + 0.12 * (n_mid - 0.5)
    w = ndi.gaussian_filter(np.clip(w, 0, 1), 1.2)
    # ground colour where the snow is thin: needles under trees, slush on paths, winter grass / earth elsewhere
    grass = np.array([116, 104, 72.]); earth = np.array([92, 76, 60.]); needle = np.array([88, 62, 44.])
    moss = np.array([62, 76, 54.]); slush = np.array([116, 108, 104.]); mud = np.array([82, 68, 58.])
    t = np.clip((n_mid - 0.35) / 0.3, 0, 1)[..., None]
    open_g = grass * (1 - t) + earth * t
    t2 = np.clip((n_fin - 0.4) / 0.3, 0, 1)[..., None]
    forest_g = needle * (1 - t2 * 0.5) + moss * t2 * 0.5
    t3 = np.clip(n_fin, 0, 1)[..., None]
    tramp_g = slush * (1 - t3 * 0.5) + mud * t3 * 0.5
    c = canopy[..., None]; tr = trample[..., None]
    gcol = open_g * (1 - c) + forest_g * c
    gcol = gcol * (1 - tr) + tramp_g * tr
    den_g = np.array([76, 60, 50.])
    gcol = gcol * (1 - den[..., None] * 0.7) + den_g * den[..., None] * 0.7
    # mountains / massif / crag: snow on gentle slopes and high ground, rock on steep faces
    Hf = ndi.gaussian_filter(H.astype(float), 1.0)
    gyx = np.hypot(*np.gradient(Hf))
    rocky = np.isin(kind, [1, 4, 5])
    alt = np.clip((PZ - H) / 40.0, 0, 1)
    wm = np.clip(1.25 - 0.85 * gyx + 0.35 * alt + 0.3 * (n_mid - 0.5), 0, 1) * np.where(kind == 5, 0.4, 1.0)
    wm = ndi.gaussian_filter(wm, 0.8)
    w = np.where(rocky, wm * (1 - 0.8 * canopy), w)
    rockc = np.array([90, 92, 106.]) * (0.9 + 0.2 * n_mid)[..., None]
    gcol = np.where(rocky[..., None], rockc, gcol)
    # lake + creek: shallow edge lighter, deep centre darker, wind-swept snow dusting
    lake = kind == 2
    dl = ndi.distance_transform_edt(lake)
    icec = np.array([70, 112, 146.]) + np.clip(1 - dl / 18, 0, 1)[..., None] * np.array([36, 40, 34.])
    gcol = np.where(np.isin(kind, [2, 3])[..., None], icec, gcol)
    w = np.where(lake, np.clip((n_mid - 0.62) / 0.2, 0, 0.7) + 0.25 * np.clip(1 - dl / 6, 0, 1), w)
    w = np.where(kind == 3, 0.15 * n_fin, w)
    w = fold_x(w); gcol = fold_x(gcol)                     # the east half mirrors the authored west half
    V.cover = {'w': w.astype(np.float32), 'gcol': gcol.astype(np.float32), 'top': top.copy()}
    # materials (stats / check): snow where the weight dominates
    basin = np.isin(cur, [SNOW, ROCK, ICE])
    newm = np.where(w > 0.5, SNOW, np.where(rocky, ROCK, np.where(canopy > 0.4, NEEDLE,
                    np.where(trample > 0.4, PATH, DRYGRASS))))
    newm = np.where(np.isin(kind, [2, 3]), np.where(w > 0.5, SNOW, ICE), newm)
    xs, ys = np.nonzero(basin)
    V.m[xs, ys, top[xs, ys]] = newm[xs, ys]
    # lake cracks: a few long meandering pressure cracks (not a noise web)
    crng = np.random.default_rng(SEED + 77)
    for _ in range(5):
        x, y = 200 + crng.random() * 50, 64 + crng.random() * 60
        ang = crng.random() * 6.283
        for k in range(70):
            ang += (crng.random() - 0.5) * 0.5
            x += math.cos(ang); y += math.sin(ang)
            xi, yi = int(round(x)), int(round(y))
            if 0 <= xi < 256 and kind[xi, yi] == 2 and V.m[xi, yi, top[xi, yi]] in (ICE, SNOW):
                V.m[xi, yi, top[xi, yi]] = ICE_DK
                if k % 9 == 0:                                     # side branch
                    a2 = ang + (1 if crng.random() < 0.5 else -1) * 0.9
                    for j in range(1, 6):
                        bx, by = int(round(x + j * math.cos(a2))), int(round(y + j * math.sin(a2)))
                        if 0 <= bx < 256 and kind[bx, by] == 2:
                            V.m[bx, by, top[bx, by]] = ICE_DK
    # blood trails / splashes stay as accents (few), paw tracks across the snow
    for trail in PAWS:
        for tr_ in (trail, [(512 - a, b) for a, b in trail]):
            for (xa, ya), (xb, yb) in zip(tr_[:-1], tr_[1:]):
                L = math.hypot(xb - xa, yb - ya)
                ux, uy = (xb - xa) / L, (yb - ya) / L
                for i in range(0, int(L), 7):
                    sd = 1 if (i // 7) % 2 else -1
                    px, py = xa + ux * i - uy * 2 * sd, ya + uy * i + ux * 2 * sd
                    for (dx, dy) in ((0, 0), (1, 0), (0, 1), (1, 1), (int(round(ux * 2)), int(round(uy * 2)))):
                        qx, qy = int(px) + dx, int(py) + dy
                        if 0 <= qx < 512 and V.m[qx, qy, top[qx, qy]] in (SNOW, DRYGRASS, NEEDLE, PATH):
                            V.m[qx, qy, top[qx, qy]] = PAW


# ------------------------------------------------------------------ forest

def place_forest(V, F, rng, n_try=14000):
    H = F['H']; kind = F['kind']
    X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    n_d = fold_x(fbm2((512, 512), 40, 2, 'forest', SEED))
    mt = ndi.distance_transform_edt(~np.isin(kind, [1, 4]))
    block = V.res.copy() | np.isin(kind, [2, 3]) | (np.abs(X - 256) < 9)
    for (x0, x1, y0, y1) in SQ:
        block[x0 - 4:x1 + 5, y0 - 4:y1 + 5] = True
    block[136:216, 232:281] = True
    block[200:257, 176:346] = True                     # den, crag, skull
    block[230:257, 346:420] = True                     # trophy knoll, mine yard
    block[60:154, 186:320] = True                      # spawn compound (authored trees only)
    pd = np.full((512, 512), 1e9)
    for p in PATHS:
        pd = np.minimum(pd, seg_dist(X, Y, p))
    block |= pd < 3.0
    bank = (kind == 6) & (ndi.distance_transform_edt(kind != 2) < 12)
    block |= bank
    # v2: groves and clearings. A low-frequency grove field decides where forest stands (dense, canopies may touch)
    # and where clearings are; a second field gives each grove its own (smoothly varying) palette.
    n_g = fold_x(fbm2((512, 512), 46, 3, 'grove', SEED))
    n_pal = fold_x(fbm2((512, 512), 120, 2, 'grovepal', SEED))
    trees = []
    grid = {}
    def ok(x, y, r, gap):
        gx, gy = x // 16, y // 16
        for i in range(gx - 2, gx + 3):
            for j in range(gy - 2, gy + 3):
                for (ox, oy, orr) in grid.get((i, j), ()):
                    dd = math.hypot(ox - x, oy - y)
                    if dd < r + orr + gap or dd < 6:
                        return False
        return True
    for _ in range(n_try * 2):
        x = int(rng.integers(6, 248)); y = int(rng.integers(6, 506))
        if block[x, y]:
            continue
        kd = kind[x, y]
        centre = abs(x - 256) < 150 and abs(y - 256) < 125
        thr = 0.47 if centre else (0.40 if mt[x, y] > 40 else 0.33)
        if kd == 1 and F['H'][x, y] < PZ - 26:
            continue                                         # bare upper rock
        g_ = n_g[x, y]
        in_grove = g_ > thr
        if not in_grove and rng.random() > 0.04:
            continue                                         # clearings: only the odd lone tree
        sub = H[x - 1:x + 3, y - 1:y + 3]
        slope_ok = 3 if kd in (1, 4, 6) else 1                # trees climb the foothills (trunk set on the low side)
        if sub.max() - sub.min() > slope_ok or H[x, y] < 8:
            continue
        edge = in_grove and g_ < thr + 0.04
        r_kind = rng.random()
        if centre:
            typ = 'scots' if r_kind < 0.45 else ('spruce' if r_kind < 0.9 else ('snag' if r_kind < 0.95 else 'sapling'))
        elif edge:
            typ = 'sapling' if r_kind < 0.4 else ('spruce' if r_kind < 0.92 else 'snag')
        else:
            typ = 'spruce' if r_kind < 0.88 else ('scots' if r_kind < 0.95 else ('snag' if r_kind < 0.98 else 'sapling'))
        h = {'spruce': int(rng.integers(16, 31)), 'scots': int(rng.integers(22, 33)), 'snag': int(rng.integers(10, 20)),
             'sapling': int(rng.integers(4, 9))}[typ]
        if kd in (1, 4):
            h = int(h * 0.85)
        r = {'spruce': 0.2 * h + 2.6, 'scots': 6.0, 'snag': 2.5, 'sapling': 2.0}[typ]
        ri = int(math.ceil(r))
        x0, x1, y0, y1 = max(0, x - ri), min(511, x + ri + 1), max(0, y - ri), min(511, y + ri + 1)
        if V.res[x0:x1, y0:y1].any() or x + ri >= 252:
            continue
        if any(not (x + ri < a - 2 or x - ri > b + 2 or y + ri < c - 2 or y - ri > d + 2) for (a, b, c, d) in SQ):
            continue
        gap = -1.5 if (in_grove and not centre) else 2.5
        if not ok(x, y, r, gap):
            continue
        grid.setdefault((x // 16, y // 16), []).append((x, y, r))
        pal = int(np.clip(n_pal[x, y], 0, 0.999) * 8)
        trees.append((x, y, typ, h, pal))
    for (x, y, typ, h, pal) in trees:
        tr = np.random.default_rng(SEED * 7 + x * 1009 + y)
        g = int(H[x - 1:x + 3, y - 1:y + 3].max())             # lowest ground under the trunk footprint
        for dx in range(2):
            for dy in range(2):
                V.column_to_ground(x + dx, y + dy, g, BARK_DK)      # root plinth down to the slope
        pal = (pal + (1 if tr.random() < 0.25 else 0)) % 8
        if typ == 'spruce':
            T.spruce(V, x, y, g, tr, h=h, pal=pal, clear=int(tr.choice([4, 4, 5])))
            if kind[x, y] in (1, 4) and tr.random() < 0.5:
                boulder(V, x + 4, y + 3, int(H[min(x + 4, 511), min(y + 3, 511)]), 2, tr)
        elif typ == 'scots':
            T.scots_pine(V, x, y, g, tr, h=h, pal=pal)
        elif typ == 'snag':
            T.snag(V, x, y, g, tr, h=h)
        else:
            T.sapling(V, x, y, g, tr, h=h, pal=pal)
    return trees


# ------------------------------------------------------------------ scatter

def scatter(V, F, rng, n=650):
    H = F['H']; kind = F['kind']
    gz = lambda a, b: int(H[a, b])
    out = {'boulder': 0, 'log': 0, 'stump': 0, 'trap': 0, 'bones': 0, 'wolfsbane': 0, 'sapling': 0, 'lantern': 0}
    for _ in range(n):
        x = int(rng.integers(8, 244)); y = int(rng.integers(8, 504))
        if V.res[max(0, x - 3):x + 4, max(0, y - 3):y + 4].any():
            continue
        if any(a - 6 <= x <= b + 6 and c - 6 <= y <= d + 6 for (a, b, c, d) in SQ) or (136 <= x <= 216 and 230 <= y <= 282):
            continue
        g = int(H[x, y])
        if V.ground(x, y) != g or V.get(x, y, g - 1) != AIR or kind[x, y] in (2, 3):
            continue
        sub = H[x - 2:x + 3, y - 2:y + 3]
        if sub.max() - sub.min() > 1:
            if kind[x, y] == 1 and rng.random() < 0.3:
                boulder(V, x, y, g, int(rng.integers(2, 4)), rng); out['boulder'] += 1
            continue
        r = rng.random()
        if r < 0.24:
            boulder(V, x, y, g, int(rng.integers(2, 5)), rng); out['boulder'] += 1
            V.reserve(x - 4, x + 4, y - 4, y + 4)
        elif r < 0.40:
            along = rng.random() < 0.5
            L = int(rng.integers(7, 15))
            if (x + L if along else y + L) < (250 if along else 506) and all(V.get(x + (i if along else 0), y + (0 if along else i), int(H[x + (i if along else 0), y + (0 if along else i)]) - 1) == AIR
                   for i in range(L)):
                fallen_log(V, x, y, gz, L, along, rng); out['log'] += 1
                V.reserve(x - 2, x + (L if along else 3), y - 2, y + (3 if along else L))
        elif r < 0.50:
            stump(V, x, y, g, rng, axe=rng.random() < 0.2); out['stump'] += 1
        elif r < 0.58:
            bear_trap(V, x, y, g, rng, sprung=rng.random() < 0.4, blood=rng.random() < 0.6,
                      chain_dir=[(1, 0), (-1, 0), (0, 1), (0, -1)][int(rng.integers(0, 4))]); out['trap'] += 1
            V.reserve(x - 3, x + 3, y - 3, y + 3)
        elif r < 0.64:
            bones(V, x, y, gz, rng, n=int(rng.integers(3, 8)), r=3); out['bones'] += 1
            if rng.random() < 0.3:
                animal_skull(V, x + 2, y, g, face=(0, 1), antler=rng.random() < 0.5)
        elif r < 0.69:
            wolfsbane(V, x, y, gz, rng, r=3, n=int(rng.integers(6, 14))); out['wolfsbane'] += 1
        elif r < 0.71:
            T.sapling(V, x, y, g, rng); out['sapling'] += 1
            V.reserve(x - 2, x + 2, y - 2, y + 2)
        elif r < 0.74:
            lantern_post(V, x, y, g, h=4, arm=(1, 0)); out['lantern'] += 1
    return out


# ------------------------------------------------------------------ compound + camps (west half)

def spawn_compound(V, F, rng):
    g = PZ
    gz = lambda a, b: V.ground(a, b)
    # v2 lodge: main hall (steep roof) + a gabled front wing facing the yard, stone base, outside chimney,
    # balcony on the wing gable
    x0, x1, y0, y1 = LODGE[0], LODGE[1], LODGE[2], LODGE[2] + 20
    S.cabin(V, x0, x1, y0, y1, g, rng, floors=2, roof_axis='x', roof_pitch=1,
            doors=(('S', x0 + 5), ('S', x1 - 5), ('W', None), ('E', None)), chimney=None,
            stairs=(x1 - 10, y0 + 2, 1, 0), partition=('x', x0 + 9))
    wx0, wx1, wy0, wy1 = 103, 119, y1, y1 + 12
    S.cabin(V, wx0, wx1, wy0, wy1, g, rng, floors=2, roof_axis='y', roof_pitch=1, doors=(('S', None),),
            porch='S', furnish=True)
    mid = (wx0 + wx1) // 2
    for f in range(2):                                           # open the shared wall between hall and wing
        V.box(mid - 2, mid + 2, y1, y1, g - 4 - 5 * f, g - 1 - 5 * f, AIR)
    # stone base: the two lowest courses of every outer wall
    for (a0, a1, b0, b1) in ((x0, x1, y0, y1), (wx0, wx1, wy0, wy1)):
        for x in range(a0 - 1, a1 + 2):
            for y in range(b0 - 1, b1 + 2):
                for z in (g - 1, g - 2):
                    if V.get(x, y, z) in (LOG, LOG_DK):
                        V.put(x, y, z, STONE if (x + y + z) % 3 else STONE_DK)
    # outside chimney on the west gable: hearth carved through the wall
    cy = (y0 + y1) // 2
    V.box(x0 - 3, x0 - 1, cy - 1, cy + 1, g - 26, g - 1, STONE)
    V.box(x0 - 3, x0 - 1, cy - 1, cy + 1, g - 27, g - 27, STONE_DK)
    V.box(x0 - 4, x0, cy - 2, cy + 2, g - 3, g - 1, STONE_DK)
    V.box(x0, x0, cy - 1, cy + 1, g - 3, g - 1, AIR)
    V.box(x0 - 1, x0 - 1, cy - 1, cy + 1, g - 2, g - 1, EMBER)
    V.reserve(x0 - 5, x0, cy - 3, cy + 3)
    # balcony on the wing gable (upper floor door onto a railed deck)
    V.box(mid - 1, mid + 1, wy1, wy1, g - 9, g - 6, AIR)
    V.box(wx0 + 2, wx1 - 2, wy1 + 1, wy1 + 2, g - 5, g - 5, PLANK)
    for x in range(wx0 + 2, wx1 - 1):
        if x % 2 == 0:
            V.put(x, wy1 + 2, g - 6, TIMBER)
    V.box(wx0 + 2, wx1 - 2, wy1 + 2, wy1 + 2, g - 7, g - 7, TIMBER)
    for x in (wx0 + 2, wx1 - 2):
        V.box(x, x, wy1 + 2, wy1 + 2, g - 4, g - 6, TIMBER)
    antlers(V, mid, wy1 + 1, g - 16, along_x=True, size=5)
    V.box(mid - 1, mid + 1, wy1 + 1, wy1 + 1, g - 17, g - 16, BONE)
    V.put(mid - 1, wy1 + 1, g - 16, MAW); V.put(mid + 1, wy1 + 1, g - 16, MAW)
    for (lx, ly) in ((wx0 - 1, wy1 + 1), (wx1 + 1, wy1 + 1)):
        hanging_lantern(V, lx, ly, g - 7, drop=1) if V.get(lx, ly, g - 7) == AIR else None
    S.watchtower(V, 72, 253, g, rng, h=16, door='E')
    S.cabin(V, 96, 106, 288, 297, g, rng, floors=1, roof_axis='y', doors=(('N', None),), windows=False,
            furnish=False, wall=LOG_DK, wall2=LOG)
    for (hx, hy) in ((99, 291), (101, 293), (103, 291), (99, 294), (103, 295)):         # hanging meat + pelts
        V.put(hx, hy, g - 4, ROPE); V.box(hx, hx, hy, hy, g - 3, g - 2, PELT_RED)
    V.put(101, 292, g, EMBER)
    S.shed(V, 112, 124, 290, 298, g, rng, open_side='N')
    for kx in (114, 118, 122):                                                             # kennel stalls
        V.box(kx + 1, kx + 1, 292, 297, g - 3, g - 1, PLANK_DK)
        V.box(kx - 1, kx, 293, 296, g, g, STRAW)
        V.put(kx, 291, g - 1, IRON_DK)
    S.shed(V, 128, 135, 289, 297, g, rng, open_side='N', h=4)
    firewood(V, 129, 295, g, 6, along_x=True, h=3)
    drying_rack(V, 97, 304, g, True, rng)
    drying_rack(V, 110, 306, g, True, rng)
    S.log_gate(V, 142, 236, 276, g, rng, h=12)
    for (lx, ly) in ((95, 233), (141, 231), (95, 279), (141, 281)):
        lantern_post(V, lx, ly, g, h=5, arm=(0, 1 if ly < 256 else -1))
    snowman_jack(V, 136, 230, g)
    # spawn yard: low (<= 2) props only, nothing tall inside the square
    for a in range(16):
        t = a * math.pi / 8
        V.put(int(round(112 + 3 * math.cos(t))), int(round(262 + 3 * math.sin(t))), g - 1, STONE_DK)
    V.box(111, 113, 261, 263, g, g, EMBER)
    V.put(112, 262, g - 1, DEADWOOD)
    sled(V, 124, 242, g, along_x=True, low=True)
    firewood(V, 102, 268, g, 4, along_x=False, h=1)
    crate(V, 130, 270, g)
    jack_o_lantern(V, 106, 247, g, face=(1, 0), size=0)
    jack_o_lantern(V, 130, 252, g, face=(-1, 0), size=0)
    # yard edges: fences with wide gaps, sledge + traps for sale, a cart of pumpkins
    for (a, b) in (((66, 186), (90, 186)), ((132, 186), (150, 186)), ((66, 318), (92, 318)), ((136, 318), (150, 318))):
        for x in range(a[0], b[0] + 1):
            if (x - a[0]) % 4 == 0:
                V.box(x, x, a[1], a[1], g - 3, g - 1, TIMBER)
            V.put(x, a[1], g - 2, TIMBER)
    for (bx, by) in ((140, 300), (146, 306)):
        bear_trap(V, bx, by, g, rng, sprung=False, blood=False, chain_dir=(0, -1))
    sled(V, 84, 230, g, along_x=False, load=CANVAS)
    for (px, py) in ((88, 300), (90, 303), (86, 304)):
        jack_o_lantern(V, px, py, g, face=(1, 0), size=int(hsh(px, py) * 2))
    # cover pines on the gate flanks (crowns high: walk underneath, they screen the spawn from the platform)
    for (tx, ty, h) in ((150, 226, 30), (149, 284, 30), (164, 218, 27), (163, 294, 27), (180, 226, 25),
                        (179, 287, 25)):
        T.scots_pine(V, tx, ty, g, np.random.default_rng(SEED + tx * 3 + ty), h=h)
    for (tx, ty) in ((70, 206), (64, 226), (66, 290), (74, 312), (140, 196), (84, 196)):
        T.spruce(V, tx, ty, int(V.H[tx, ty]), np.random.default_rng(SEED + tx + ty * 7), h=int(18 + hsh(tx, ty) * 8),
                 clear=4)


def trapper_camp(V, F, rng):
    gz = lambda a, b: V.ground(a, b)
    cx, cy = 118, 112
    g = gz(cx, cy)
    S.tent(V, 106, 106, gz(106, 106), rng, along_x=True, L=9)
    campfire(V, 124, 120, gz(124, 120))
    V.reserve(119, 129, 115, 125)
    drying_rack(V, 104, 124, gz(104, 124), True, rng)
    S.shed(V, 128, 135, 102, 108, gz(130, 105), rng, open_side='S', h=4)
    firewood(V, 129, 104, gz(130, 105), 5, True, 2)
    cage(V, 136, 114, gz(136, 114), rng)
    sled(V, 112, 128, gz(112, 128), along_x=True, load=PELT_GREY)
    for (tx, ty) in ((98, 118), (102, 114), (134, 126)):
        crate(V, tx, ty, gz(tx, ty)) if hsh(tx, ty) < 0.7 else barrel(V, tx, ty, gz(tx, ty))
    for (bx, by) in ((96, 106), (99, 102), (93, 110)):
        V.box(bx, bx + 4, by, by + 1, gz(bx, by) - 1, gz(bx, by) - 1, IRON)          # stacked traps
    S.hunters_blind(V, 86, 128, gz(86, 128), rng, h=6, stair_dir=(1, 0))
    stump(V, 120, 132, gz(120, 132), rng, axe=True)
    for (lx, ly) in ((116, 136), (140, 112)):
        lantern_post(V, lx, ly, gz(lx, ly), h=4)


def rune_circle(V, F, rng):
    cx, cy = 176, 164
    gz = lambda a, b: V.ground(a, b)
    V.reserve(cx - 13, cx + 13, cy - 13, cy + 13)
    for i in range(7):
        t = i / 7 * 2 * math.pi + 0.3
        x, y = int(round(cx + 10 * math.cos(t))), int(round(cy + 10 * math.sin(t)))
        rune_stone(V, x, y, gz(x, y), int(rng.integers(4, 8)), rng, face=(0, 1 if y < cy else -1))
    g = gz(cx, cy)
    V.box(cx - 2, cx + 2, cy - 1, cy + 1, g - 2, g - 1, STONE_DK)
    V.box(cx - 1, cx + 1, cy, cy, g - 2, g - 2, BLOOD)
    V.put(cx - 2, cy - 1, g - 3, CANDLE); V.put(cx + 2, cy + 1, g - 3, CANDLE)
    animal_skull(V, cx, cy - 4, g, face=(0, -1), antler=True)
    for a in range(0, 360, 30):
        t = math.radians(a)
        x, y = int(round(cx + 6 * math.cos(t))), int(round(cy + 6 * math.sin(t)))
        V.put_air(x, y, gz(x, y) - 1, CANDLE if a % 60 == 0 else BONE)


def trap_line(V, F, rng):
    gz = lambda a, b: V.ground(a, b)
    cx, cy = 168, 342
    for (dx, dy) in ((-10, -6), (-2, -10), (6, -4), (12, 4), (-8, 6), (2, 8), (14, -10), (-14, 0)):
        x, y = cx + dx, cy + dy
        bear_trap(V, x, y, gz(x, y), rng, sprung=hsh(x, y) < 0.4, blood=True,
                  chain_dir=[(1, 0), (0, 1), (-1, 0), (0, -1)][int(hsh(x, y, 2) * 4)])
    for (dx, dy) in ((-4, -2), (8, 2), (0, 12), (-12, 10)):
        snare_post(V, cx + dx, cy + dy, gz(cx + dx, cy + dy), rng)
    S.wagon_overturned(V, 148, 330, gz(150, 331), rng, along_x=True)
    V.reserve(146, 160, 326, 336)
    S.hunters_blind(V, 188, 354, gz(188, 354), rng, h=6, stair_dir=(-1, 0))
    for (wx, wy) in ((160, 352), (178, 334), (172, 358), (156, 342)):
        wolfsbane(V, wx, wy, gz, rng, r=4, n=16)
    elk_carcass(V, 182, 360, gz(182, 360), rng, along_x=True)
    V.reserve(cx - 18, cx + 18, cy - 14, cy + 14)


def chapel_yard(V, F, rng):
    gz = lambda a, b: V.ground(a, b)
    g = int(V.H[100, 370])
    S.chapel(V, 90, 116, 362, 378, g, rng)
    # graveyard east of the chapel: headstones + crosses in loose rows, low wall, lantern posts, open grave
    for row, y in enumerate(range(362, 392, 6)):
        for i, x in enumerate(range(124, 150, 5)):
            if hsh(x, y, 4) < 0.15:
                continue
            xx, yy = x + int(hsh(x, y) * 2), y + int(hsh(y, x) * 2)
            if hsh(x, y, 5) < 0.5:
                headstone(V, xx, yy, gz(xx, yy), rng)
            else:
                grave_cross(V, xx, yy, gz(xx, yy), rng)
    V.box(146, 148, 384, 389, gz(147, 386), gz(147, 386), AIR)          # open (dug-out) grave
    V.box(146, 148, 384, 389, gz(147, 386) + 1, gz(147, 386) + 1, EARTH_DK)
    V.put(149, 383, gz(149, 383) - 1, EARTH_DK); V.put(149, 384, gz(149, 384) - 1, EARTH_DK)
    V.box(150, 150, 386, 386, gz(150, 386) - 3, gz(150, 386) - 1, TIMBER); V.put(150, 386, gz(150, 386) - 4, IRON)
    for x in range(120, 154):
        for y in (358, 394):
            if hsh(x, y, 7) > 0.18 and not (134 <= x <= 138):
                V.put(x, y, gz(x, y) - 1, STONE_DK)
    for (lx, ly) in ((121, 360), (152, 392)):
        lantern_post(V, lx, ly, gz(lx, ly), h=5)
    for (bx, by) in ((122, 386), (152, 366), (82, 386)):
        T.birch(V, bx, by, gz(bx, by), np.random.default_rng(bx * 31 + by))
    V.reserve(118, 156, 356, 396)


def lake_props(V, F, rng):
    ice = SPEC['lake']['ice_z']
    S.ice_shack(V, 206, 100, ice, rng, door='S')
    V.reserve(204, 216, 96, 112)
    for (hx, hy) in ((224, 112), (232, 104), (240, 118)):
        V.box(hx, hx + 1, hy, hy + 1, ice, ice, ICE_DK)
    sled(V, 226, 116, ice, along_x=True, load=None, broken=True)
    V.put(233, 106, ice - 1, PLANK_DK); V.box(235, 235, 104, 104, ice - 3, ice - 1, IRON)
    jack_o_lantern(V, 213, 110, ice, face=(0, 1))


def mine_west(V, F, rng):
    t = SPEC['tunnel']
    (y0, y1) = t['y']
    # portal at the first rock column along the tunnel
    px = None
    for x in range(150, 256):
        if V.H[x, (y0 + y1) // 2] < PZ - 2:
            px = x
            break
    if px is None:
        return None
    S.portal(V, px, y0, y1, PZ, rng, h=5, sign_dir=-1)
    for x in range(px - 14, px):                                     # rails out of the portal
        for y in (y0 + 3, y1 - 3):
            if V.get(x, y, PZ) in TERRAIN_MATS:
                V.put(x, y, PZ, RAIL)
    S.ore_cart(V, px - 10, y0 + 2, PZ, along_x=True)
    V.ellipsoid((px - 14, y1 + 9, PZ + 0.5), (6, 4, 2.6), GRAVEL)  # spoil heap
    for (cx_, cy_) in ((px - 6, y0 - 4), (px - 8, y0 - 6)):
        crate(V, cx_, cy_, V.ground(cx_, cy_))
    barrel(V, px - 4, y1 + 4, V.ground(px - 4, y1 + 4))
    lantern_post(V, px - 3, y0 - 2, V.ground(px - 3, y0 - 2), h=5, arm=(0, 1))
    V.reserve(px - 20, px + 2, y0 - 8, y1 + 14)
    return px


# ------------------------------------------------------------------ axis set pieces

def axis_pieces(V, F, rng):
    gz = lambda a, b: V.ground(a, b)
    tz = lambda a, b: int(V.H[a, b])
    info = {}
    # kill site
    elk_carcass(V, 256, 140, gz(256, 140), rng)
    V.reserve(244, 268, 132, 160)
    for sx in (-1,):
        sled(V, 256 + 14 * sx - 3, 150, gz(256 + 14 * sx, 150), along_x=False, load=CANVAS, broken=True)
        lantern_post(V, 256 + 9 * sx, 132, gz(256 + 9 * sx, 132), h=3, arm=(0, 1))
        bones(V, 256 + 7 * sx, 152, gz, rng, n=8, r=4)
    # crag + werewolf
    cx, cy = SPEC['crag']['c']
    g = int(np.min(F['H'][cx - 3:cx + 4, cy - 3:cy + 4]))
    LM.werewolf(V, cx, cy, g, s=0.8)
    info['werewolf_ground_z'] = g
    V.reserve(cx - 30, cx + 30, cy - 18, cy + 18)
    # claw-raked rock around the werewolf's feet
    for x in range(cx - 14, cx + 1):
        for y in range(cy - 8, cy + 10):
            z = V.ground(x, y)
            if V.get(x, y, z) == ROCK and (x + 2 * y) % 5 == 0 and hsh(x, y, 2) < 0.5:
                V.put(x, y, z, ROCK_DK)
    # skull gate (cranium centre y 304; mouth/door opens south at y ~334)
    LM.wolf_skull(V, 256, 304, PZ)
    # ruined hunting-keep corners flanking the den (axis-aligned walls read cleanly in voxels)
    for (pts, hfn) in (([(236, 212), (214, 212), (214, 230)], lambda t: int(round(9 - 4 * t))),
                       ([(214, 282), (214, 300), (238, 300)], lambda t: int(round(5 + 4 * t)))):
        S.ruin_wall(V, pts, tz, rng, h=9, thick=2, arch_every=8, gap_every=13, h_fn=hfn)
    # skull stakes on the den floor (v2.2: the barricades were replaced by sph_centre.dress_centre)
    for (sx_, sy_) in ((222, 238), (222, 274), (246, 222), (246, 290)):
        V.box(sx_, sx_, sy_, sy_, PZ - 4, PZ - 1, TIMBER)
        V.put(sx_, sy_, PZ - 5, BONE); V.put(sx_, sy_ + 1, PZ - 5, BONE)
    # pit rim: low broken stones + bones (1 high, gaps)
    for a in range(0, 360, 12):
        t = math.radians(a)
        if 80 < a < 100:                                  # leave the south landing side open on the rim? (north is stair)
            pass
        x, y = int(round(256 + 8.6 * math.cos(t))), int(round(256 + 8.6 * math.sin(t)))
        if hsh(x, y, 3) < 0.6 and not (250 <= x <= 262 and y < 250):
            V.put(x, y, PZ - 1, STONE_DK if hsh(x, y) < 0.7 else BONE)
    # trophy tree on its knoll
    kx, ky = SPEC['trophy_knoll']['c']
    LM.trophy_tree(V, kx, ky, gz(kx, ky), rng)
    # mine yard + headframe
    yd = SPEC['mine_yard']
    S.headframe(V, 256, 400, PZ, rng, h=22)
    for sx in (-1,):
        S.cabin(V, 256 + sx * 19 - 3, 256 + sx * 19 + 3, 391, 398, PZ, rng, floors=1, roof_axis='y',
                doors=(('S', None),), wall=PLANK, wall2=PLANK_DK, furnish=False, corner_logs=False)
        S.ore_cart(V, 256 + sx * 12 - 2, 406, PZ, along_x=False)
        V.ellipsoid((256 + sx * 17, 408, PZ + 0.5), (3.5, 3, 2.2), ORE)
        crate(V, 256 + sx * 9, 392, PZ)
        lantern_post(V, 256 + sx * 8, 410, PZ, h=5, arm=(1, 0))
    return info


# ------------------------------------------------------------------ main build

def build(graybox=False, sky=False):
    rng = np.random.default_rng(SEED)
    F = terrain()
    pads(F)
    V = Vox(F['H'])
    voxelize(V, F)
    if graybox:
        V.m[257:] = V.m[255:0:-1]
        return V, F
    # reservations that props/forest must avoid
    for (x0, x1, y0, y1) in SQ:
        V.reserve(x0, x1, y0, y1, pad=1)
    V.res[138:213, 234:279] = True
    carve_tunnel(V, rng)
    den = LM.carve_den(V, F)
    falls = LM.frozen_falls(V, SPEC['waterfall']['x'][0], SPEC['waterfall']['x'][1], SPEC['lake']['ice_z'], rng)
    V.reserve(200, 312, 0, 70)
    spawn_compound(V, F, rng)
    trapper_camp(V, F, rng)
    rune_circle(V, F, rng)
    trap_line(V, F, rng)
    chapel_yard(V, F, rng)
    lake_props(V, F, rng)
    px = mine_west(V, F, rng)
    info = axis_pieces(V, F, rng)
    import sph_centre
    info.update(sph_centre.dress_centre(V, F, np.random.default_rng(SEED + 22)))
    trees = place_forest(V, F, np.random.default_rng(SEED + 11))
    sc = scatter(V, F, np.random.default_rng(SEED + 12))
    paint_ground(V, F, rng)
    # creek footbridges where trails cross
    X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    # mirror
    V.m[257:] = V.m[255:0:-1]
    F['cleanup'] = cleanup(V)
    F['counts'] = {'trees': len(trees), 'scatter': sc, 'portal_x': px, **info, **den, 'falls': falls}
    F['tree_types'] = {t: sum(1 for tr in trees if tr[2] == t) * 2 for t in ('spruce', 'scots', 'snag', 'sapling')}
    if sky:
        from sph_sky import add_sky
        add_sky(V, F)
    return V, F


def cleanup(V, max_small=10, iters=5):
    """Drop tiny floating decoration and raise terrain cells that would trap a player."""
    from sph_check import Nav
    from scipy.sparse.csgraph import dijkstra
    st = ndi.generate_binary_structure(3, 1)
    solid = V.m > 0
    solid[:, :, 63] = True
    lab, n = ndi.label(solid, structure=st)
    grounded = set(np.unique(lab[:, :, 62:][solid[:, :, 62:]]).tolist())
    sizes = ndi.sum(solid, lab, index=np.arange(1, n + 1))
    removed = 0
    big = []
    for i in range(1, n + 1):
        if i not in grounded:
            if sizes[i - 1] <= max_small:
                V.m[lab == i] = 0
                removed += int(sizes[i - 1])
            else:
                big.append(int(sizes[i - 1]))
    raised = 0
    for it in range(iters):
        solid = V.m > 0
        solid[:, :, 63] = True
        nav = Nav(solid)
        pl = nav.nodes_in(0, 511, 0, 511, PZ - 1, PZ + 1)
        db = dijkstra(nav.G.T.tocsr(), directed=True, unweighted=True, indices=pl[::9], min_only=True)
        p = nav.xyz
        trap = (p[:, 2] < 62) & (p[:, 2] >= PZ - 1) & ~np.isfinite(db)
        fixed = 0
        for x, y, z in p[trap]:
            if V.m[x, y, z] in TERRAIN_MATS and V.m[x, y, z - 1] == 0 and V.m[512 - x if x > 0 else 0, y, z] == V.m[x, y, z]:
                V.m[x, y, z - 1] = V.m[x, y, z]
                fixed += 1
        raised += fixed
        if not fixed:
            break
    return {'tiny_floating_removed_voxels': removed, 'large_floating_left': big, 'trap_cells_raised': raised}


if __name__ == '__main__':
    import time
    t = time.time()
    V, F = build(graybox='--graybox' in sys.argv)
    print('built', round(time.time() - t, 1), F.get('counts'), F.get('cleanup'))
