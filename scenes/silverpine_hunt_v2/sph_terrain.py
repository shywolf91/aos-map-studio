"""Terrain fields for Silverpine Hunt (moonlit werewolf snow basin, Tower of Babel).

All fields are [x, y] arrays, mirror-symmetric about x = 256 (x' = 512 - x).
H = top solid z of each column (z down: smaller z = higher ground). PZ = basin floor.
"""
from __future__ import annotations

import numpy as np

from sph_core import fbm2, fold_x

SEED = 1030
PZ = 46

SPEC = {
    'pz': PZ,
    'platform': {'x': (206, 305), 'y': (240, 271), 'z': 1},
    'bases': ((118, 256), (394, 256)),
    'spawn_half': 20,
    # flat tower corridor (spawn edge -> platform anchor), per half
    'corridor': {'x': (138, 212), 'y': (234, 278)},
    'lake': {'c': (256, 94), 'r': (68, 40), 'ice_z': PZ + 4},
    'waterfall': {'x': (236, 276), 'cliff_y': 52, 'top_z': 13},
    'massif': {'x': (168, 344), 'y': (398, 474), 'top_z': (34, 26)},
    'tunnel': {'x': (150, 362), 'y': (412, 420), 'z_air': (41, 45)},
    'mine_yard': {'x': (234, 278), 'y': (394, 412)},
    'crag': {'c': (256, 200), 'r': (30, 16), 'h': 6},
    'den': {'c': (256, 256), 'pit_r': 7, 'floor_z': PZ + 10},
    'skull': {'c': (256, 322)},
    'trophy_knoll': {'c': (256, 370), 'r': (22, 16), 'h': 5},
    # west-half knolls (cx, cy, rx, ry, height)
    'knolls': [(120, 114, 26, 20, 3), (176, 164, 22, 18, 4), (100, 372, 30, 24, 5), (168, 342, 20, 16, 2),
               (70, 140, 18, 16, 3), (64, 392, 16, 14, 3), (204, 448, 16, 12, 2)],
    # frozen creek, west half: lake outlet -> pond -> west mountains
    'creek': [(194, 116), (172, 128), (150, 136), (126, 152), (104, 164), (92, 170), (74, 182), (58, 190), (40, 198)],
    'pond': {'c': (92, 170), 'r': (13, 9)},
    'compound': {'x': (60, 154), 'y': (184, 322)},
}


def smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def seg_dist(X, Y, pts):
    d = np.full(X.shape, 1e9)
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        vx, vy = x1 - x0, y1 - y0
        L2 = vx * vx + vy * vy
        t = np.clip(((X - x0) * vx + (Y - y0) * vy) / L2, 0, 1)
        d = np.minimum(d, np.hypot(X - (x0 + t * vx), Y - (y0 + t * vy)))
    return d


def ell(X, Y, c, r):
    return np.hypot((X - c[0]) / r[0], (Y - c[1]) / r[1])


def build_fields(seed=SEED):
    X, Y = np.meshgrid(np.arange(512, dtype=float), np.arange(512, dtype=float), indexing='ij')
    sh = (512, 512)
    n_roll = fold_x(fbm2(sh, 96, 3, 'roll', seed))
    n_mt = fold_x(fbm2(sh, 48, 3, 'mt', seed))
    n_pk = fold_x(fbm2(sh, 22, 3, 'peak', seed))
    n_ter = fold_x(fbm2(sh, 30, 2, 'terr', seed))
    n_edge = fold_x(fbm2(sh, 14, 2, 'edge', seed))
    F = {'X': X, 'Y': Y}
    H = PZ + (n_roll - 0.5) * 3.2                       # gentle +-1.6 rolling
    kind = np.zeros(sh, np.uint8)                       # 0 basin

    # ---------------------------------------------------------------- mountain ring
    n_mt2 = fold_x(fbm2(sh, 90, 2, 'mt2', seed))
    calm = 0.45 + 0.55 * smooth((np.abs(Y - 256) - 60) / 60)       # quieter edge behind the spawns
    pert = ((n_mt - 0.5) * 30 + (n_mt2 - 0.5) * 44) * calm
    dx = np.minimum(X, 511 - X) + pert
    dy = np.minimum(Y, 511 - Y) + (n_mt - 0.5) * 30 + (n_mt2 - 0.5) * 40
    north = Y < 256
    # mountain start distance per edge: tight behind the spawns, deeper at the corners/north
    sx = 50 + 16 * smooth(np.abs(Y - 256) / 140)        # west/east
    sy = np.where(north, 68 - 10 * smooth(1 - np.abs(X - 256) / 90), 54)
    sx, sy = fold_x(sx), fold_x(sy)
    s = np.maximum(np.clip((sx - dx) / sx, 0, 1), np.clip((sy - dy) / sy, 0, 1))
    corner = smooth(1 - np.hypot(np.minimum(X, 511 - X), np.minimum(Y, 511 - Y)) / 120)
    s = np.clip(s + 0.25 * corner * (s > 0), 0, 1)
    # v2: sculpted slopes instead of strata: gentle walkable foothills, then a steep ridged wall
    n_rib = fold_x(fbm2(sh, 9, 2, 'rib', seed))
    n_rdg = fold_x(fbm2(sh, 30, 3, 'ridge', seed))
    ridged = 1 - np.abs(2 * n_rdg - 1)                    # 1 on ridge lines, 0 in gullies
    foot = 12 * smooth(s / 0.45)
    wall = 30 * smooth((s - 0.36) / 0.64) ** 1.15 * (0.7 + 0.6 * ridged)
    hm = foot + wall + 3.0 * (n_rib - 0.5) * s + 4 * (n_pk - 0.5) * smooth((s - 0.5) / 0.5)
    hm = np.clip(hm, 0, 41)
    mt = hm > 1.0
    H = np.where(mt, PZ - hm, H)
    kind[mt] = 1
    F['mt_s'] = s

    # ---------------------------------------------------------------- frozen lake + waterfall cliff
    L = SPEC['lake']
    lake_n = fold_x(fbm2(sh, 20, 2, 'lake', seed))
    dl = ell(X, Y, L['c'], L['r']) + (lake_n - 0.5) * 0.16
    in_lake = dl < 1.0
    bank = (dl >= 1.0) & (dl < 1.2)
    # the lake cuts into the mountains; north of it (around the falls) the mountain becomes a sheer cliff
    wf = SPEC['waterfall']
    cliff_zone = (np.abs(X - 256) < 52) & (Y < L['c'][1])
    H = np.where(bank & ~mt, np.maximum(H, PZ + np.floor((1.2 - dl) / 0.2 * 4.0)), H)
    H = np.where(in_lake, L['ice_z'], H)
    kind[in_lake] = 2
    kind[bank & (kind == 0)] = 6
    # sheer cliff behind the falls: everything north of the cliff line at the falls is high rock
    dfm = ell(X, Y, (256, 14), (78, 42)) + (n_edge - 0.5) * 0.12
    cl = (dfm < 1.0) & ~in_lake
    fz = wf['top_z'] + np.clip((dfm - 0.55) / 0.45, 0, 1) * 10 + 3 * n_pk
    H = np.where(cl, np.minimum(H, fz), H)
    kind[cl] = 1

    # ---------------------------------------------------------------- knolls (stepped 1-voxel terraces)
    for (cx, cy, rx, ry, h) in SPEC['knolls'] + [(*SPEC['trophy_knoll']['c'], *SPEC['trophy_knoll']['r'],
                                                  SPEC['trophy_knoll']['h'])]:
        for (ccx) in {cx, 512 - cx}:
            d = ell(X, Y, (ccx, cy), (rx, ry)) + (n_edge - 0.5) * 0.18
            k = (d < 1) & (kind == 0)
            hh = np.floor(h * smooth(1 - d) + 0.5)
            H = np.where(k, np.minimum(H, PZ - hh), H)
            kind[k & (hh > 0)] = 6

    # ---------------------------------------------------------------- den crag (rocky, 2-3 high steps)
    C = SPEC['crag']
    d = ell(X, Y, C['c'], C['r']) + (n_edge - 0.5) * 0.22
    k = d < 1
    hh = np.floor(C['h'] * smooth((1 - d) * 1.6) / 2.5) * 2.5
    H = np.where(k & (hh > 0), np.minimum(H, PZ - np.ceil(hh)), H)
    kind[k & (hh > 0)] = 5

    # ---------------------------------------------------------------- silver-mine massif (south)
    n_ms = fold_x(fbm2(sh, 34, 2, 'massif', seed))
    # superellipse spur of the south range, terraced in 4-high strata; rim step 7 high
    dm = (np.abs((X - 256) / 92.0) ** 2.6 + np.abs((Y - 452) / 56.0) ** 2.6) ** (1 / 2.6) + (n_ms - 0.5) * 0.22
    km = dm < 1.0
    hdome = 12 + 16 * smooth((1 - dm) / 0.7) + 3 * (ridged - 0.5)     # 12..28 above PZ, ridged
    rim = smooth((1.0 - dm) / 0.1)                                    # 7-high rim wall, then a smooth dome
    lvl = PZ - np.maximum(7, 7 + (hdome - 7) * smooth((0.9 - dm) / 0.25)) * (rim > 0)
    H = np.where(km, np.minimum(H, lvl), H)
    kind[km] = 4
    # ridge 'fingers' running in from the ring (west half; mirrored): ridged crest, falling toward the basin
    for (p0, p1, w, hh) in (((0, 150), (54, 144), 15, 30), ((0, 352), (56, 360), 15, 28), ((124, 0), (132, 50), 17, 30),
                            ((108, 511), (118, 474), 17, 26), ((0, 30), (74, 74), 18, 32)):
        for flip in (False, True):
            q0 = (512 - p0[0], p0[1]) if flip else p0
            q1 = (512 - p1[0], p1[1]) if flip else p1
            d = seg_dist(X, Y, [q0, q1]) + (n_ms - 0.5) * 8
            vx, vy = q1[0] - q0[0], q1[1] - q0[1]
            t = np.clip(((X - q0[0]) * vx + (Y - q0[1]) * vy) / (vx * vx + vy * vy), 0, 1)
            prof = smooth(1 - d / w) * (1 - 0.55 * t) * (0.8 + 0.4 * ridged)
            k = (prof > 0.02) & (kind != 2)
            H = np.where(k, np.minimum(H, PZ - hh * prof), H)
            kind[k & (prof * hh > 1)] = 1
    yard = SPEC['mine_yard']
    ky = (X >= yard['x'][0]) & (X <= yard['x'][1]) & (Y >= yard['y'][0] - 6) & (Y <= yard['y'][1])
    H = np.where(ky, PZ, H)
    kind[ky] = 0

    # ---------------------------------------------------------------- creek + pond (2 deep, ice)
    cr = SPEC['creek']
    dc = np.minimum(seg_dist(X, Y, cr), seg_dist(X, Y, [(512 - a, b) for a, b in cr]))
    pond = SPEC['pond']
    dp = np.minimum(ell(X, Y, pond['c'], pond['r']), ell(X, Y, (512 - pond['c'][0], pond['c'][1]), pond['r']))
    bed = ((dc < 2.6) | (dp < 1.0)) & (kind != 1) & (kind != 2)
    bnk = ((dc < 4.6) | (dp < 1.3)) & ~bed & (kind != 1) & (kind != 2)
    H = np.where(bed, np.maximum(H, PZ + 2), H)
    H = np.where(bnk, np.maximum(H, PZ + 1), H)
    kind[bed] = 3
    F['creek_d'] = dc

    # ---------------------------------------------------------------- flat pads (spawn compound, corridor, centre)
    cmp_ = SPEC['compound']
    def rect(x0, x1, y0, y1, feather=6):
        a = np.minimum.reduce([X - x0, x1 - X, Y - y0, y1 - Y])
        b = np.minimum.reduce([(512 - X) - x0, x1 - (512 - X), Y - y0, y1 - Y])
        return smooth(np.maximum(a, b) / feather)
    w = rect(cmp_['x'][0], cmp_['x'][1], cmp_['y'][0], cmp_['y'][1], 10)
    mound = PZ + np.clip(np.round((fold_x(fbm2(sh, 14, 2, 'spawnmound', seed)) - 0.5) * 3.4), -1, 1)
    H = np.where((kind == 0) | (kind == 6), H * (1 - w) + mound * w, H)
    co = SPEC['corridor']
    w2 = rect(co['x'][0], co['x'][1], co['y'][0], co['y'][1], 4)
    H = H * (1 - w2) + PZ * w2
    w3 = rect(212, 300, 222, 292, 4)                    # under-platform den floor
    H = H * (1 - w3) + PZ * w3
    w4 = rect(236, 276, 296, 346, 3)                    # skull-gate apron
    H = np.where(kind != 5, H * (1 - w4) + PZ * w4, H)
    F['H'] = np.clip(np.rint(H), 6, 61).astype(np.int16)
    F['kind'] = kind
    F['n_roll'] = n_roll
    return F


def fix_heights(F):
    """Make the 41x41 spawn squares smooth (1-voxel steps only, no dips) and anchors exactly PZ."""
    H = F['H']
    for bx, by in SPEC['bases']:
        sq = H[bx - 22:bx + 23, by - 22:by + 23].astype(int)
        # no local minima deeper than their neighbours (no 'holes'): raise each cell to min(max neighbours)
        for _ in range(4):
            p = np.pad(sq, 1, mode='edge')
            nb = np.stack([p[:-2, 1:-1], p[2:, 1:-1], p[1:-1, :-2], p[1:-1, 2:]])
            sq = np.minimum(sq, nb.max(0))          # a cell can't sit lower (bigger z) than all its neighbours
            sq = np.clip(sq, np.min(nb, 0) - 1, np.max(nb, 0) + 1)
        H[bx - 22:bx + 23, by - 22:by + 23] = sq
    H[206:212, 240:272] = PZ
    H[300:306, 240:272] = PZ
    F['H'] = fold_x(H).astype(np.int16)
    return F


def terrain(seed=SEED):
    F = build_fields(seed)
    F = fix_heights(F)
    return F


if __name__ == '__main__':
    from PIL import Image
    F = terrain()
    H = F['H'].astype(float)
    img = np.clip((63 - H) * 4, 0, 255).astype(np.uint8).T
    Image.fromarray(img).resize((1024, 1024), Image.NEAREST).save('/tmp/sph_h.png')
    k = F['kind']
    pal = np.array([[90, 90, 90], [140, 120, 110], [80, 140, 200], [40, 90, 200], [160, 160, 60], [200, 80, 60],
                    [110, 160, 90]], np.uint8)
    Image.fromarray(pal[k].transpose(1, 0, 2)).resize((1024, 1024), Image.NEAREST).save('/tmp/sph_kind.png')
    print('H range', H.min(), H.max(), 'spawn', np.unique(F['H'][98:139, 236:277], return_counts=True))
