"""Elderveil art pass (separate from the graybox; must not change gameplay geometry - ev_checks.collision_diff:
the set of standable cells reachable on foot from a spawn is compared between the graybox reference and the art
build; differences are allowed only in plant columns, feature pads, sky boxes and the tag box).

    art_west(cv, rep, S, rng, seed)   west half + axis halves BEFORE the mirror: terrain shaders, worn paths, elder
                                      masonry (bond, weathering, moss, ivy, cracks, carved bands, gold inlay),
                                      mosaics, water, wood/canvas, real vegetation (ev_veg), one-offs (ev_props),
                                      glow sources (mirrored with the map)
    art_post(cv, rep, S, rng, info)   AFTER the mirror: sky islets and crows, the sky-level corner tag (ev_sky)
    finish(cv)                        baked light + AO, misty-morning grade, glow bake, brightness rules

Geometry the art adds: trees and ground plants (on open ground or the stand-in columns), crown tiers / hanging moss
>= 4 above the ground, small details on unreachable tops (>= 2 above the floor or above a structure), sky decor and
the tag. Everything else is a recolour.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage as ndi

from aosmap.kit import color, noise
from aosmap.kit.color import clamp8, mix, shade

import ev_props
import ev_sky
import ev_veg

WARM, CYAN, GREEN, WHITE = (255, 175, 95), (95, 255, 255), (95, 255, 95), (255, 255, 255)
GLOW_PALETTE = {WARM, CYAN, GREEN, WHITE}

ELDER = [(198, 192, 178), (186, 182, 172), (206, 198, 184), (178, 176, 168), (192, 186, 172), (200, 196, 186)]
MOSS = [(86, 116, 62), (102, 132, 70), (76, 106, 58)]
IVY = [(52, 96, 48), (66, 112, 54), (84, 128, 60), (58, 88, 46)]
GOLD = (198, 164, 76)
STONE_MATS = ('ruin', 'building', 'spire', 'statue', 'aqueduct', 'bridge', 'crest_wall', 'rune', 'stair', 'rubble')
WOOD_MATS = ('timber', 'furniture', 'prop', 'fire')


def ids(cv, *names):
    return [cv.materials[n] for n in names if n in cv.materials]


def isin(cv, arr, *names):
    i = ids(cv, *names)
    return np.isin(arr, i) if i else np.zeros(arr.shape, bool)


# =============================================================================================== terrain

def path_mask(S, seed):
    """Worn dirt paths between landmarks (west half + axis), noisy width 2-3."""
    pts = S['art']['paths']
    X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    n = noise.fbm2((512, 512), 9, 2, 'path_w', seed)
    wob = (noise.fbm2((512, 512), 23, 2, 'path_wob', seed) - 0.5) * 6
    m = np.zeros((512, 512), bool)
    for line in pts:
        for (ax, ay), (bx, by) in zip(line, line[1:]):
            dx, dy = bx - ax, by - ay
            L2 = float(dx * dx + dy * dy) or 1.0
            x0, x1 = max(0, min(ax, bx) - 12), min(511, max(ax, bx) + 12)
            y0, y1 = max(0, min(ay, by) - 12), min(511, max(ay, by) + 12)
            sx, sy = X[x0:x1 + 1, y0:y1 + 1], Y[x0:x1 + 1, y0:y1 + 1] + wob[x0:x1 + 1, y0:y1 + 1]
            t = np.clip(((sx - ax) * dx + (sy - ay) * dy) / L2, 0, 1)
            d = np.hypot(sx - (ax + t * dx), sy - (ay + t * dy))
            m[x0:x1 + 1, y0:y1 + 1] |= d <= 1.0 + 1.2 * n[x0:x1 + 1, y0:y1 + 1]
    m[257:] = m[255:0:-1]
    m[256] = m[255]
    return m


def terrain_art(cv, S, seed):
    H = cv.H.astype(int)
    X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    n1 = noise.fbm2((512, 512), 16, 3, 'art_floor', seed)
    n2 = noise.fbm2((512, 512), 5, 2, 'art_fine', seed)
    n3 = noise.fbm2((512, 512), 40, 2, 'art_broad', seed)
    gx = np.abs(np.roll(H, 1, 0) - np.roll(H, -1, 0))
    gy = np.abs(np.roll(H, 1, 1) - np.roll(H, -1, 1))
    slope = np.maximum(gx, gy) / 2.0
    topmat = cv.mat[X, Y, H]
    is_ = {k: topmat == cv.materials[k] if k in cv.materials else np.zeros((512, 512), bool)
           for k in ('ground', 'paving', 'rock', 'shelf', 'water', 'dirt', 'mosaic', 'waterfall', 'cave', 'pad')}
    shade_col = (np.argmax(cv.solid, axis=2) < H - 4)                       # something tall over the column
    under = ndi.uniform_filter(shade_col.astype(float), 7) > 0.3
    paths = path_mask(S, seed) & (is_['ground'] | is_['dirt'])
    tops = np.zeros((512, 512, 3))
    # forest floor: moss greens, leaf litter where shaded, sunlit clearings warmer
    grass_lo, grass_hi = np.array((70, 104, 56)), np.array((128, 146, 70))
    t = np.clip(0.45 + (n1 - 0.5) * 1.4 + (n3 - 0.5) * 0.6, 0, 1)
    gr = grass_lo * (1 - t[..., None]) + grass_hi * t[..., None]
    litter = np.array((112, 92, 62)) * (0.9 + 0.2 * n2[..., None])
    lt = np.clip((n2 - 0.45) * 2.5, 0, 1) * under
    gr = gr * (1 - lt[..., None]) + litter * lt[..., None]
    moss = (n2 > 0.68) & ~under
    gr[moss] = np.array((96, 132, 66)) * (0.95 + 0.1 * n1[moss, None])
    tops[:] = gr
    # worn paths: packed earth with a lighter centre and leaf edges
    pd = ndi.distance_transform_edt(paths)
    pc = np.array((124, 104, 78)) * (0.94 + 0.12 * n2[..., None])
    pc = np.where((pd >= 2)[..., None], pc * 1.06, pc)
    tops[paths] = pc[paths]
    # outpost courtyard: trodden dirt, straw, darker round the fires
    dc = np.array((128, 108, 82)) * (0.92 + 0.14 * n2[..., None])
    straw = (n2 > 0.74) & (noise.hash3(X, Y, 3, 8) < 0.6)
    dc[straw] = np.array((152, 136, 96))
    tops[is_['dirt']] = dc[is_['dirt']]
    # paving: ashlar slabs (3 x 2) with soft tone variation, moss in some joints
    sx, sy = (X + (Y // 2 % 2) * 1) // 3, Y // 2
    hs = noise.hash3(sx, sy, 0, 13)
    slab = np.array(ELDER)[(hs * len(ELDER)).astype(int) % len(ELDER)] * 0.92
    joint = ((X + (Y // 2 % 2)) % 3 == 0) & (Y % 2 == 0)
    slab = np.where(joint[..., None], slab * 0.9, slab)
    mj = joint & (n2 > 0.6)
    slab[mj] = np.array(MOSS[0])
    tops[is_['paving']] = slab[is_['paving']]
    # mosaics: plaza rings round the moonwell + star rays; under-platform rings + border; missing tiles
    mos = mosaic_colours(S, X, Y, n2)
    pm = is_['paving'] & S['_plaza_mask'] & (np.hypot(X - 256.5, Y - 170.5) <= 22)
    tops[pm] = mos[pm]
    tops[is_['mosaic']] = mos[is_['mosaic']]
    gone = (is_['mosaic'] | pm) & (n1 < 0.3) & (noise.hash3(X, Y, 1, 4) < 0.5)
    tops[gone] = np.array((110, 100, 80)) * (0.9 + 0.2 * n2[gone, None])
    # rock: warped strata, moss on gentle tops, scree tones at the foot
    warp = (noise.fbm2((512, 512), 24, 2, 'strata', seed) - 0.5) * 8
    STR = np.array([(116, 112, 108), (128, 122, 114), (106, 104, 104), (138, 132, 122), (120, 114, 110)])
    rk = STR[((H + warp).astype(int) // 3) % len(STR)].astype(float)
    rtop = is_['rock']
    gentle = rtop & (slope <= 1.0) & (n1 > 0.42)
    tops[rtop] = rk[rtop]
    tops[gentle] = (np.array((92, 120, 64)) * (0.9 + 0.2 * n2[..., None]))[gentle]
    # water: depth gradient, foam at the falls; gravel bars on shelves
    wat = is_['water'] | is_['waterfall']
    deep = np.clip(ndi.distance_transform_edt(is_['water']) / 6.0, 0, 1)
    wc = np.array((86, 132, 138))[None, None] * (1 - deep[..., None]) + np.array((40, 78, 96))[None, None] * \
        deep[..., None]
    tops[is_['water']] = wc[is_['water']]
    tops[is_['waterfall']] = np.array((176, 196, 200))
    grav = np.array((140, 132, 116)) * (0.88 + 0.2 * noise.hash3(X, Y, 2, 6)[..., None])
    tops[is_['shelf']] = grav[is_['shelf']]
    tops[is_['cave']] = np.array((96, 82, 66))
    tops[is_['pad']] = (np.array((96, 128, 66)) * (0.9 + 0.15 * n2[..., None]))[is_['pad']]
    # apply: top voxel, then earth / strata below
    zz = np.arange(64)[None, None, :]
    ter = (zz >= H[:, :, None]) & cv.solid & isin(cv, cv.mat, 'ground', 'paving', 'rock', 'shelf', 'water', 'dirt',
                                                    'mosaic', 'waterfall', 'cave', 'pad')
    xs, ys, zs = np.nonzero(ter)
    d = zs - H[xs, ys]
    out = cv.rgb[xs, ys, zs].astype(float)
    top0 = d == 0
    out[top0] = tops[xs[top0], ys[top0]]
    sub = ~top0
    strata = STR[((zs + warp[xs, ys]).astype(int) // 3) % len(STR)].astype(float)
    earth = np.array((110, 90, 70)) * (0.9 + 0.12 * n2[xs, ys])[:, None]
    deepc = (d > 2) | (H[xs, ys] <= 46)
    out[sub] = np.where(deepc[sub][:, None], strata[sub], earth[sub])
    cv.rgb[xs, ys, zs] = np.clip(out, 0, 255).astype(np.uint8)
    # wet rock round the falls: darken and cool the rock near the cascade
    wf = S['waterfall']
    for x in range(wf['x'][0] - 4, wf['x'][1] + 5):
        for y in range(440, 511):
            for z in range(max(0, H[x, y] - 1), min(63, H[x, y] + 4)):
                if cv.solid[x, y, z] and not wat[x, y]:
                    cv.rgb[x, y, z] = clamp8(np.array(cv.rgb[x, y, z], float) * np.array((0.8, 0.86, 0.94)))
    return {'path_cols': int(paths[:256].sum())}


def mosaic_colours(S, X, Y, n2):
    TILE = np.array([(172, 156, 120), (146, 150, 150), (186, 178, 158), (158, 136, 110), (152, 158, 132)], float)
    out = np.zeros((512, 512, 3))
    for (cx, cy, kind) in ((256.5, 170.5, 'plaza'), (256.5, 256.5, 'under')):
        r = np.hypot(X - cx, Y - cy)
        a = np.arctan2(Y - cy, X - cx)
        ring = (r // 3).astype(int)
        ray = (np.cos(a * 8) > 0.7) & (r > 6) & (r % 6 < 4)
        if kind == 'under':                                              # soft concentric rings, no rays
            ring = (r // 4).astype(int)
        idx = np.where(ray, 0, ring % 4 + 1) if kind == 'plaza' else (ring % 3) + 1
        c = TILE[idx % len(TILE)] * (0.94 + 0.1 * n2[..., None])
        m = (np.abs(X - cx) < 60) & (np.abs(Y - cy) < 40)
        out[m] = c[m]
    border = ((np.abs(Y - 240) <= 1) | (np.abs(Y - 271) <= 1)) & (X >= 218)
    out[border] = TILE[0]
    return out


# =============================================================================================== masonry

def stone_art(cv, S, seed):
    """Elder masonry on every stone voxel: running bond blocks (4 long, 2 high, alternate courses offset), a pale
    warm-grey palette (<= 212) with block-to-block tone, soft mortar, weathering darker towards the ground, moss
    from the base and on north faces and open tops, ivy sheets on wall faces, scattered cracks; statues smooth."""
    H = cv.H.astype(int)
    sm = isin(cv, cv.mat, *STONE_MATS)
    sm[256:] = False
    xs, ys, zs = np.nonzero(sm)
    mats = cv.mat[xs, ys, zs]
    course = zs // 2
    off = (course % 2) * 2
    bx, by = (xs + off) // 4, (ys + off) // 4
    h = noise.hash3(bx, by, course, 7)
    base = np.array(ELDER, float)[(h * len(ELDER)).astype(int) % len(ELDER)]
    mortar = (((xs + off) % 4 == 0) & ((ys + off) % 4 == 0)) | (zs % 2 == 0) & (noise.hash3(xs, ys, zs, 2) < 0.25)
    base[mortar] *= 0.93
    statue = np.isin(mats, ids(cv, 'statue'))
    base[statue] = np.array((204, 198, 186)) * (0.96 + 0.06 * noise.hash3(xs[statue] // 2, ys[statue] // 2,
                                                                              zs[statue] // 2, 3))[:, None]
    ag = H[xs, ys] - zs                                                           # height above the ground
    wear = np.clip(1.0 - ag / 18.0, 0, 1)
    base *= (1.0 - 0.12 * wear)[:, None]
    nfield = noise.fbm2((512, 512), 6, 2, 'moss_field', seed)
    nf = nfield[xs, ys]
    air = lambda dx, dy, dz: ~cv.solid[np.clip(xs + dx, 0, 511), np.clip(ys + dy, 0, 511), np.clip(zs + dz, 0, 63)]
    north = air(0, -1, 0)
    upf = air(0, 0, -1)
    side = air(1, 0, 0) | air(-1, 0, 0) | north | air(0, 1, 0)
    mossp = np.clip(1.0 - ag / 4.0, 0, 1) * 0.8 + north * 0.25 + upf * 0.3 + (nf - 0.5) * 0.9
    mossp -= 0.3 * np.isin(mats, ids(cv, 'spire', 'stair'))              # the spire stays pale: moss only low
    mossy = mossp > 0.62
    mc = np.array(MOSS, float)[(noise.hash3(xs, ys, zs, 9) * 3).astype(int) % 3]
    base[mossy] = mc[mossy]
    # ivy sheets on wall faces (2D noise across the face), 1-14 above the ground
    ivn = noise.fbm2((512, 64), 5, 2, 'ivy', seed)
    u = np.where(north | air(0, 1, 0), xs, ys)
    ivy = side & (ag >= 1) & (ag <= 14) & (ivn[u % 512, zs] > 0.64) & ~statue
    ic = np.array(IVY, float)[(noise.hash3(xs, ys, zs, 11) * 4).astype(int) % 4]
    base[ivy] = ic[ivy]
    crack = (noise.hash3(xs, ys, zs, 17) < 0.025) & ~mossy & ~ivy
    base[crack] *= 0.78
    streak = noise.fbm2((512, 512), 3, 1, 'grime', seed)[xs, ys] > 0.7
    base[streak & side & ~ivy & ~mossy] *= 0.92
    cv.rgb[xs, ys, zs] = np.clip(base, 0, 212).astype(np.uint8)
    return {'stone_voxels': int(len(xs)), 'moss_voxels': int(mossy.sum()), 'ivy_voxels': int(ivy.sum())}


def carved_bands(cv, S, glow):
    """Carved courses with gold inlay on the key pieces: the spire (bands every 6 with a few cyan rune lights),
    the library facade (between the floors), the obelisk, the gate-tower crown course."""
    sp = S['spire']
    cx, cy = sp['c']
    sid = cv.materials['spire']
    n = 0
    for z in range(sp['top'] + 3, sp['ground'] - 2, 6):
        for x in range(int(cx) - 8, int(cx) + 9):
            for y in range(int(cy) - 8, int(cy) + 9):
                if cv.solid[x, y, z] and cv.mat[x, y, z] == sid:
                    d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
                    if d > sp['r_wall'][1] - 1.0:
                        a = int(math.degrees(math.atan2(y + 0.5 - cy, x + 0.5 - cx)) % 360)
                        cv.rgb[x, y, z] = GOLD if a % 24 < 6 else (170, 160, 142)
                        n += 1
        # one rune light per band, on the open face
        a = math.radians((z * 47) % 360)
        x, y = int(math.floor(cx + 6.2 * math.cos(a))), int(math.floor(cy + 6.2 * math.sin(a)))
        if cv.solid[x, y, z] and cv.mat[x, y, z] == sid and z % 24 == (sp['top'] + 3) % 24:
            cv.rgb[x, y, z] = CYAN
            glow.append((x, y, z, CYAN))
    lb = S['library']['box']
    bid = cv.materials['building']
    z = 50 - S['library']['storey_h']
    for x in range(lb[0], 256):
        for y in (lb[2], lb[3]):
            if cv.solid[x, y, z] and cv.mat[x, y, z] == bid:
                cv.rgb[x, y, z] = GOLD if x % 4 == 0 else (172, 162, 144)
                n += 1
    return n


def wood_art(cv, S, seed):
    """Timber grain, canvas per tent, shingles, furniture."""
    out = 0
    for name, cols in (('timber', [(112, 82, 56), (100, 72, 50), (122, 90, 60)]),
                       ('roof', [(96, 70, 56), (84, 74, 70), (106, 78, 60)]),
                       ('furniture', [(110, 80, 56), (96, 70, 50)]),
                       ('prop', [(120, 90, 60), (138, 104, 66), (104, 80, 58)]),
                       ('fire', [(70, 50, 40)])):
        if name not in cv.materials:
            continue
        m = cv.mat == cv.materials[name]
        m[256:] = False
        xs, ys, zs = np.nonzero(m)
        k = (noise.hash3(xs // 1, ys // 3, zs, 23) * len(cols)).astype(int) % len(cols)
        cv.rgb[xs, ys, zs] = np.array(cols)[k]
        out += len(xs)
    # tents: one canvas colour per tent (muted ochre, sage, rust, faded blue, oat, moss)
    CAN = [(176, 150, 96), (140, 150, 116), (150, 104, 76), (110, 128, 150), (188, 172, 136), (112, 128, 88)]
    tid = cv.materials.get('tent')
    for i, (x0, x1, y0, y1, o) in enumerate(S['tents']):
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(40, 50):
                    if cv.mat[x, y, z] == tid:
                        stripe = 0.92 if (x + y) % 4 == 0 else 1.0
                        cv.rgb[x, y, z] = shade(CAN[i % len(CAN)], stripe)
    return out


# =============================================================================================== top level

def tree_traps(cv, art_trees, rounds=3):
    """Real trees can close a pocket the stand-ins did not: delete plant voxels round any tree within reach of a
    trap cell (kit trap model on a mirrored copy), repeat."""
    import ev_graybox
    pids = ids(cv, *ev_veg.PLANT_MATS)
    removed = 0
    for _ in range(rounds):
        tp = ev_graybox.trap_cells(cv)
        if not len(tp):
            break
        tx = np.minimum(tp[:, 0], 512 - tp[:, 0])
        ty = tp[:, 1]
        hit = False
        for (x, y) in set(zip(tx.tolist(), ty.tolist())):
            sl = (slice(max(0, x - 6), min(256, x + 7)), slice(max(0, y - 6), y + 7))
            m = np.isin(cv.mat[sl], pids)
            if m.any():
                cv.solid[sl][m] = False
                cv.mat[sl][m] = 0
                removed += int(m.sum())
                hit = True
        if not hit:
            break
    return removed


def reach_fix(cv, solid_gray, rounds=3):
    """Real trees must not change where players can walk: compare the cells reachable on foot (both spawns, safe
    graph) with the graybox reference; any difference outside plant columns means a tree closed or opened a path
    (usually a narrow terrace ledge on the cliff ring). Delete the plants round those cells and repeat."""
    import ev_checks
    import ev_graybox
    pids = ids(cv, *ev_veg.PLANT_MATS)
    Rg = ev_checks._reach(solid_gray)
    removed = 0
    for _ in range(rounds):
        Ra = ev_checks._reach(ev_graybox._mirrored(cv.solid))
        plant = np.isin(ev_graybox._mirrored(cv.mat), pids).any(2)
        diff = (Rg ^ Ra) & ~ndi.binary_dilation(plant, iterations=1)[:, :, None]
        pts = np.argwhere(diff)
        if not len(pts):
            break
        for (x, y) in {(int(min(p[0], 512 - p[0])), int(p[1])) for p in pts}:
            sl = (slice(max(0, x - 8), min(256, x + 9)), slice(max(0, y - 8), y + 9))
            m = np.isin(cv.mat[sl], pids)
            if m.any():
                cv.solid[sl][m] = False
                cv.mat[sl][m] = 0
                removed += int(m.sum())
    return removed


def art_west(cv, rep, S, rng, seed, solid_gray=None):
    glow = []
    out = {}
    import ev_graybox
    S['_plaza_mask'] = ev_graybox.plaza_val(S) < 1.0
    out['stand_ins_cleared'] = ev_veg.clear_stand_ins(cv)
    out['terrain'] = terrain_art(cv, S, seed)
    out['stone'] = stone_art(cv, S, seed)
    out['bands'] = carved_bands(cv, S, glow)
    out['wood'] = wood_art(cv, S, seed)
    out['props'] = ev_props.props_art(cv, S, rng, glow)
    out['heart_tree'] = ev_veg.heart_tree(cv, rng, S, glow)
    out['mushrooms'] = ev_veg.giant_mushrooms(cv, rng, S, glow)
    trees = ev_veg.plant_trees(cv, rep['scatter']['tree_list'], rng, seed, glow)
    out['trees'] = {k: v for k, v in trees.items() if k != 'list'}
    out['understory'] = ev_veg.understory(cv, rng, seed, plaza_mask=S['_plaza_mask'])
    out['water_plants'] = ev_veg.reeds_and_lilies(cv, rng, seed)
    out['tree_trap_voxels_removed'] = tree_traps(cv, trees['list'])
    if solid_gray is not None:
        out['reach_fix_voxels_removed'] = reach_fix(cv, solid_gray)
    skipped = 0
    for (x, y, z, c) in glow:
        if x <= 255 and cv.inside(x, y, z) and cv.solid[x, y, z]:
            cv.add_glow(x, y, z, c)
        else:
            skipped += 1
    out['glow_sources_west'] = len(glow) - skipped
    out['glow_skipped'] = skipped
    S.pop('_plaza_mask', None)
    return out


def art_post(cv, rep, S, rng, info):
    """After the mirror: sky islets, crows and the sky-level tag. Returns cosmetic boxes for the mirror check."""
    recs, glow = ev_sky.place_sky(cv, S, rng)
    tag = ev_sky.sky_tag(cv, S)
    for (x, y, z, c) in glow:
        if cv.inside(x, y, z) and cv.solid[x, y, z]:
            cv.add_glow(x, y, z, c)
    info.update({'sky': recs, 'tag': tag})
    boxes = [[r['x'][0], r['x'][1], r['y'][0], r['y'][1]] for r in recs]
    boxes.append(tag['box'][:4])
    return boxes


def finish(cv, target_median=98.0, tint=(1.03, 1.01, 0.95)):
    """Baked light + AO, misty-morning grade (pale gold), brightness rules, glow bake, palette nudge."""
    surf = color.lighting(cv)
    top = np.argmax(cv.solid, axis=2)
    X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    L = color.luma(cv.rgb[X, Y, top].astype(float) * np.array(tint))
    k = float(np.clip(target_median / max(np.median(L), 1.0), 0.7, 1.25))
    grade = tuple(k * t for t in tint)
    m = cv.solid & ~cv.nolight
    c = cv.rgb[m].astype(np.float32) * np.array(grade, np.float32)
    cv.rgb[m] = np.clip(c, 0, 255).astype(np.uint8)
    bright = color.enforce_brightness(cv, floor_min=41)
    stored, n_src = bake_glow_fast(cv, surf)
    srcs = {(x, y, z) for (x, y, z, _) in cv.glow}
    nudged = 0
    for kk in list(stored):
        if kk in srcs:
            continue
        cc = tuple(int(v) for v in cv.rgb[kk])
        if cc in GLOW_PALETTE:
            cv.rgb[kk] = (max(0, cc[0] - 1), cc[1], cc[2])
            nudged += 1
    return stored, {'grade': [round(g, 3) for g in grade], 'brightness': bright, 'glow_sources': n_src,
                    'glow_lit_voxels': len(stored) - n_src, 'palette_nudged': nudged}


def bake_glow_fast(cv, surf, radius=6.5, strength=0.24):
    """aosmap.kit.color.bake_glow's model (additive, linear falloff; sources keep their exact colour; originals
    stored for the glow-aware server), vectorised per source (as in Frostbell)."""
    srcs, seen = [], set()
    for (x, y, z, c) in cv.glow:
        if (x, y, z) in seen or not cv.inside(x, y, z) or not cv.solid[x, y, z]:
            continue
        seen.add((x, y, z))
        srcs.append((x, y, z, c))
    R = int(math.ceil(radius))
    o = np.arange(-R, R + 1)
    DX, DY, DZ = np.meshgrid(o, o, o, indexing='ij')
    D = np.sqrt(DX ** 2 + DY ** 2 + DZ ** 2)
    W = np.where((D < radius) & (D > 0), (1 - D / radius) * strength, 0.0)
    acc = {}
    for (x, y, z, c) in srcs:
        xs, ys, zs = x + DX, y + DY, z + DZ
        ok = (W > 0) & (xs >= 0) & (xs < 512) & (ys >= 0) & (ys < 512) & (zs >= 0) & (zs < 64)
        xs, ys, zs, w = xs[ok], ys[ok], zs[ok], W[ok]
        s = surf[xs, ys, zs]
        for (a, b, cc, ww) in zip(xs[s], ys[s], zs[s], w[s]):
            kk = (int(a), int(b), int(cc))
            v = acc.get(kk)
            if v is None:
                acc[kk] = [c[0] * ww, c[1] * ww, c[2] * ww]
            else:
                v[0] += c[0] * ww
                v[1] += c[1] * ww
                v[2] += c[2] * ww
    stored = {}
    for kk, a in acc.items():
        if kk in seen:
            continue
        orig = tuple(int(v) for v in cv.rgb[kk])
        stored[kk] = orig
        cv.rgb[kk] = (min(255, int(orig[0] + a[0])), min(255, int(orig[1] + a[1])), min(255, int(orig[2] + a[2])))
    for (x, y, z, c) in srcs:
        cv.rgb[x, y, z] = c
        stored[(x, y, z)] = tuple(c)
    return stored, len(srcs)
