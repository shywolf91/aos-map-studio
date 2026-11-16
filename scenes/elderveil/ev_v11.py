"""Elderveil v1.1 art round (only runs for release 1.1; v1.0 stays byte-identical).

queen_art / head_art      weathering on the sculpted figures: darker creases with moss in the valleys, lichen on
                          upper faces, gold inlay on crown points, belt and staff, ivy creeping up the west sides,
                          dark eye hollows
cliff_art                 strata of varying thickness and colour bands (ochre and cool grey), ferns on ledges,
                          hanging vines on the wet faces near the falls (face-connected plants)
forest_floor              fallen logs, stumps and saplings at grove edges (plants: seed-driven, face-connected)
small_things              foam and mist at the plunge pools, stones painted along the stream banks, leaf-drift
                          patches, lantern glow on the graybox posts, crows perched on two ruins (tethered)
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage as ndi

from aosmap.kit import noise
from aosmap.kit.color import clamp8, mix, shade

WARM, CYAN = (255, 175, 95), (95, 255, 255)
GOLD = (196, 162, 78)
MARBLE = (188, 186, 180)
MOSS = (80, 96, 70)
LICHEN = (170, 176, 150)
IVY = (48, 74, 48)


def _sculpt_shade(cv, box, glow, gold_fn=None, seed=0):
    """Shade every statue voxel in box: creases (lower than the 8-neighbour tops) darker with moss, crests lichen,
    west-facing faces ivy (noise), optional gold mask."""
    x0, x1, y0, y1 = box
    sid = cv.materials['statue']
    sub = cv.mat[x0:x1 + 1, y0:y1 + 1] == sid
    xs, ys, zs = np.nonzero(sub & cv.solid[x0:x1 + 1, y0:y1 + 1])
    xs, ys = xs + x0, ys + y0
    top = np.argmax(cv.solid, axis=2)
    nb = ndi.uniform_filter(top.astype(float), 3)
    exposed = ~cv.solid[xs, ys, np.maximum(zs - 1, 0)]
    crease = exposed & (top[xs, ys] > nb[xs, ys] + 0.7)
    crest = exposed & (top[xs, ys] < nb[xs, ys] - 0.7)
    west = ~cv.solid[np.maximum(xs - 1, 0), ys, zs]
    n = noise.fbm2((512, 64), 3, 2, 'statue_ivy', seed)
    c = np.array([MARBLE] * len(xs), float) * (0.94 + 0.08 * noise.hash3(xs // 2, ys // 2, zs // 2, 5))[:, None]
    low = (cv.H[xs, ys] - zs) <= 2
    c[low] *= 0.88
    c[crease] = c[crease] * 0.72 + np.array(MOSS) * 0.28
    lich = crest & (noise.hash3(xs, ys, zs, 6) < 0.25)
    c[lich] = c[lich] * 0.6 + np.array(LICHEN) * 0.4
    ivy = west & (n[ys % 512, zs] > 0.66) & ((cv.H[xs, ys] - zs) <= 5)
    c[ivy] = np.array(IVY) * (0.9 + 0.2 * noise.hash3(xs[ivy], ys[ivy], zs[ivy], 7))[:, None]
    if gold_fn is not None:
        gm = gold_fn(xs, ys, zs, exposed)
        c[gm] = GOLD
    cv.rgb[xs, ys, zs] = np.clip(c, 0, 212).astype(np.uint8)
    return int(len(xs))


def queen_art(cv, S, glow):
    q = S['queen11']
    hy = q['head_y']
    def gold(xs, ys, zs, exposed):
        crown = (ys <= hy - 4) & (ys >= hy - 6) & (zs < cv.H[xs, ys] - 6)
        belt = exposed & (ys >= 209) & (ys <= 211) & (xs >= 251)
        staff = (np.abs(ys - q['staff_y']) <= 2) & (xs <= q['staff_x'][1] - 1) & (xs >= q['staff_x'][0] - 3)
        return crown | belt | (staff & exposed & (noise.hash3(xs, ys, zs, 9) < 0.5))
    n = _sculpt_shade(cv, (232, 255, 176, 242), glow, gold, seed=11)
    for x in (252, 253):                                                # dark eye hollows
        t = int(np.argmax(cv.solid[x, hy - 1]))
        cv.rgb[x, hy - 1, t] = (52, 50, 54)
    return n


def head_art(cv, S, glow):
    hd = S['under']['head']
    cy = hd['c'][1]
    n = _sculpt_shade(cv, (240, 255, 240, 272), glow, None, seed=12)
    for x in (251, 252):
        for y in (cy - 4, cy - 3):
            t = int(np.argmax(cv.solid[x, y]))
            if cv.mat[x, y, t] == cv.materials['statue']:
                cv.rgb[x, y, t] = (50, 48, 52)
    return n


def cliff_art(cv, S, seed, plant_put):
    """Strata of varying thickness and colour bands on the ring rock below the surface; ferns on gentle ledges; vines
    hanging from the wet faces beside the falls."""
    H = cv.H.astype(int)
    rid = [cv.materials[k] for k in ('rock', 'ground') if k in cv.materials]
    X, Y = np.meshgrid(np.arange(256), np.arange(512), indexing='ij')
    thick = 2 + (noise.fbm2((512, 512), 40, 2, 'strata_t', seed)[:256] * 4).astype(int)
    warp = (noise.fbm2((512, 512), 24, 2, 'strata', seed)[:256] - 0.5) * 8
    BANDS = np.array([(106, 102, 98), (118, 112, 102), (98, 96, 94), (128, 114, 90), (110, 106, 100),
                      (94, 92, 90)], float)
    zz = np.arange(64)[None, None, :]
    face = cv.solid[:256] & (zz > H[:256, :, None]) & (H[:256, :, None] <= 46) & np.isin(cv.mat[:256], rid)
    xs, ys, zs = np.nonzero(face)
    b = ((zs + warp[xs, ys]) / thick[xs, ys]).astype(int) % len(BANDS)
    c = BANDS[b] * (0.92 + 0.12 * noise.hash3(xs // 2, ys, zs, 3))[:, None]
    crack = noise.hash3(xs, ys, 0, 55) < 0.035
    c[crack] *= 0.74
    cv.rgb[xs, ys, zs] = np.clip(c, 0, 212).astype(np.uint8)
    # ferns on gentle ring ledges (1 tall)
    gx = np.abs(np.roll(H, 1, 0) - np.roll(H, -1, 0))
    gy = np.abs(np.roll(H, 1, 1) - np.roll(H, -1, 1))
    gentle = (np.maximum(gx, gy) <= 2)[:256] & (H[:256] <= 44) & (H[:256] >= 12) & (cv.keep[:256] == 0)
    top = np.argmax(cv.solid[:256], axis=2)
    led = gentle & (top == H[:256]) & (noise.hash3(X, Y, 1, 66) < 0.06)
    nf = 0
    for x, y in zip(*np.nonzero(led)):
        cv.set(int(x), int(y), int(H[x, y]) - 1, (58, 86, 58) if (x + y) % 2 else (72, 98, 62), 'fern')
        nf += 1
    # vines on the wet faces beside the falls (hang into air next to a face, stop 4 above the floor below)
    wf = S['waterfall']
    nv = 0
    for x in range(wf['x'][0] - 8, min(256, wf['x'][1] + 9)):
        for y in range(445, 505):
            if noise.hash3(x, y, 2, 67) > 0.22:
                continue
            for z in range(10, 60):
                if cv.solid[x, y, z] and not cv.solid[x, y - 1, z] and not cv.solid[x, y - 1, z - 1]:
                    gb = int(np.argmax(cv.solid[x, y - 1, z:])) + z
                    L = 2 + int(noise.hash3(x, y, z, 68) * 5)
                    for k in range(L):
                        if z + k >= gb - 4:
                            break
                        cv.set(x, y - 1, z + k, (52, 82, 50) if k % 2 else (64, 94, 56), 'moss')
                        nv += 1
                    break
    return {'ledge_ferns': nf, 'vine_voxels': nv}


def forest_floor(cv, rng, seed):
    """Fallen logs (2 tall), stumps (2-3 tall, pale cut tops, moss) and saplings at grove edges. Plants: placed only
    on open flat ground without keep flags, each face-connected to the ground."""
    import ev_veg
    H = cv.H.astype(int)
    dens = noise.fbm2((512, 512), 30, 2, 'forest_density', seed)
    gid = cv.materials.get('ground')
    top = np.argmax(cv.solid, axis=2)
    out = {'logs': 0, 'stumps': 0, 'saplings': 0}

    def clear(x0, x1, y0, y1):
        if x0 < 2 or x1 > 250 or y0 < 2 or y1 > 509:
            return False
        if cv.keep[x0 - 1:x1 + 2, y0 - 1:y1 + 2].any():
            return False
        hh = H[x0:x1 + 1, y0:y1 + 1]
        if hh.max() - hh.min() > 1 or hh.max() > 57 or hh.min() < 44:
            return False
        if (top[x0 - 1:x1 + 2, y0 - 1:y1 + 2] < H[x0 - 1:x1 + 2, y0 - 1:y1 + 2] - 0).any():
            return False
        return bool((cv.mat[x0:x1 + 1, y0:y1 + 1][np.arange(x1 - x0 + 1)[:, None],
                                                    np.arange(y1 - y0 + 1)[None, :], hh] == gid).all())
    r = noise.rng('forest_floor', seed)
    for gx in range(8, 250, 9):
        for gy in range(8, 504, 9):
            x, y = gx + int(r.integers(-3, 4)), gy + int(r.integers(-3, 4))
            if not (0 <= x < 250 and 0 <= y < 510):
                continue
            d = dens[x, y]
            u = r.random()
            if d > 0.56 and u < 0.10:                                   # fallen log
                along = r.random() < 0.5
                L = int(r.integers(6, 11))
                box = (x, x + L - 1, y, y + 1) if along else (x, x + 1, y, y + L - 1)
                if not clear(*box):
                    continue
                P = ev_veg.Plant(cv, x, y, H[x, y])
                bark = (78 + int(r.integers(0, 12)), 62, 50)
                for i in range(L):
                    for j in (0, 1):
                        px, py = (x + i, y + j) if along else (x + j, y + i)
                        g = H[px, py]
                        P.put(px, py, g - 1, shade(bark, 0.9), 'deadwood')
                        P.put(px, py, g - 2, MOSS if (i + j) % 3 == 0 else bark, 'deadwood')
                    if i in (0, L - 1):
                        P.v[((x + i, y, H[x + i, y] - 2) if along else (x, y + i, H[x, y + i] - 2))] = \
                            ((150, 126, 96), 'deadwood')                      # pale broken ends
                P.commit([(px, py, H[px, py] - 1) for px in range(box[0], box[1] + 1)
                          for py in range(box[2], box[3] + 1)])
                out['logs'] += 1
            elif d > 0.52 and u < 0.20:                                 # stump
                if not clear(x - 1, x + 1, y - 1, y + 1):
                    continue
                P = ev_veg.Plant(cv, x, y, H[x, y])
                hh = int(r.integers(2, 4))
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if abs(dx) + abs(dy) == 2 and r.random() < 0.6:
                            continue
                        g = H[x + dx, y + dy]
                        for k in range(hh):
                            P.put(x + dx, y + dy, g - 1 - k, (176, 150, 112) if k == hh - 1 else (84, 66, 52),
                                  'deadwood')
                P.v = {k: v for k, v in P.v.items()}
                P.commit([(x, y, H[x, y] - 1)])
                out['stumps'] += 1
            elif 0.47 < d < 0.54 and u < 0.35:                          # sapling at a grove edge
                if not clear(x - 1, x + 1, y - 1, y + 1):
                    continue
                P = ev_veg.Plant(cv, x, y, H[x, y])
                h = int(r.integers(4, 8))
                g = H[x, y]
                for k in range(h):
                    P.put(x, y, g - 1 - k, (84, 66, 52), 'bark')
                fa, fb = ((32, 54, 50), (58, 86, 72)) if r.random() < 0.5 else ((52, 70, 46), (110, 118, 72))
                for k in range(2, h + 1):
                    rr = (h - k) * 0.5 + 0.6
                    for dx in range(-2, 3):
                        for dy in range(-2, 3):
                            if dx * dx + dy * dy <= rr * rr and (dx or dy):
                                P.put(x + dx, y + dy, g - 1 - k, mix(fa, fb, k / h), 'leaf')
                P.put(x, y, g - 1 - h, fb, 'leaf')
                P.commit([(x, y, g - 1)])
                out['saplings'] += 1
    return out


def small_things(cv, S, seed, glow, info):
    H = cv.H.astype(int)
    wid = cv.materials.get('water')
    wf = S['waterfall']
    # foam and mist at the plunge pools and on the falls
    n = 0
    for x in range(wf['x'][0] - 4, min(256, wf['x'][1] + 5)):
        for y in range(430, 470):
            z = H[x, y]
            if z >= 62 and cv.mat[x, y, z] == wid and noise.hash3(x, y, 0, 71) < 0.45:
                cv.rgb[x, y, z] = (188, 196, 198) if noise.hash3(x, y, 1, 71) < 0.5 else (166, 180, 186)
                n += 1
    # stones painted along the stream banks, leaf-drift patches on the forest floor
    gid = cv.materials.get('ground')
    st = lf = 0
    dr = noise.fbm2((512, 512), 6, 2, 'leaf_drift', seed)
    for x in range(20, 256):
        for y in range(20, 492):
            z = H[x, y]
            top = cv.solid[x, y, z] and not cv.solid[x, y, z - 1]
            if not top:
                continue
            if z in (60, 61, 62) and noise.hash3(x, y, 3, 72) < 0.18:
                cv.rgb[x, y, z] = (124, 122, 118) if noise.hash3(x, y, 4, 72) < 0.5 else (104, 104, 104)
                st += 1
            elif cv.mat[x, y, z] == gid and dr[x, y] > 0.74 and noise.hash3(x, y, 5, 72) < 0.6:
                cv.rgb[x, y, z] = (132, 104, 64) if noise.hash3(x, y, 6, 72) < 0.5 else (112, 86, 56)
                lf += 1
    # lantern glow on the graybox lantern posts
    lid = cv.materials.get('lantern')
    lt = 0
    for (x, y, z) in info.get('lanterns') or []:
        if cv.solid[x, y, z]:
            cv.rgb[x, y, z] = WARM
            glow.append((x, y, z, WARM))
            lt += 1
        for k in range(1, 5):
            if cv.solid[x, y, z + k] and cv.mat[x, y, z + k] == lid:
                cv.rgb[x, y, z + k] = (92, 70, 52)
    # crows perched on two ruins (tiny, face-connected to the ruin top: tethered, not floating)
    crows = 0
    aq = S['aqueduct']
    import ev_graybox
    yc = ev_graybox.aqueduct_line(S)
    ta, tb = aq['collapses'][aq['tall_pier_in']]
    tm = (ta + tb) // 2
    sites = [(tm, int(yc[tm]), aq['tall_pier_top'])]
    gt = S['gate_tower']['box']
    sites.append((gt[0] + 4, gt[2], int(np.argmax(cv.solid[gt[0] + 4, gt[2]]))))
    for (x, y, zt) in sites:
        if not cv.solid[x, y, zt] or cv.solid[x, y, zt - 1]:
            continue
        body = [(x, y, zt - 1), (x, y, zt - 2), (x + 1, y, zt - 2), (x - 1, y, zt - 2)]
        for (bx, by, bz) in body:
            if not cv.solid[bx, by, bz]:
                cv.set(bx, by, bz, (42, 40, 46), 'crow')
        cv.set(x, y, zt - 3, (48, 46, 52), 'crow')
        crows += 1
    return {'foam': n, 'bank_stones': st, 'leaf_drift': lf, 'lanterns_lit': lt, 'perched_crows': crows}
