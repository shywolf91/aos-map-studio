"""Witchwood Isles — graybox generator (Babel, stock piqueserver 1.4.2 babel_script).

Authored on the west half (x <= 256) and mirrored x' = 512 - x, like the stock bases and build-ban zones.
Heights are z (0 = sky top, 63 = seabed). H = 63 - z is height above the seabed (0 = open water).
"""
import numpy as np
from scipy import ndimage

from ww_core import W, D, new_volume, fbm, seed_of

SEED = 3131

# ---------------------------------------------------------------- spec (single source of truth)
SPEC = {
    'babel': {  # stock babel_script 1.4.2 (read in source)
        'platform': {'x': (206, 305), 'y': (240, 271), 'z': 1},
        'bases': {'blue': (118, 256), 'red': (394, 256)},
        'spawn_half': 20,
        'protected': {'blue': (128, 211, 240, 272), 'red': (301, 384, 240, 272)},
    },
    'island': {  # blue island (west), mirrored for red
        'ellipse': {'cx': 100, 'cy': 256, 'rx': 70, 'ry': 136},
        'east_shore_x': 168,          # forced shoreline in the crossing rows
        'crossing_rows': (224, 288),
        'base_H': 9,                  # z 54
        'shore_noise': 7,
    },
    'spawn_plateau': {'x': (92, 144), 'y': (230, 282), 'H': 15},   # z 48; stock spawn box x 98-138, y 236-276
    'hills': [
        {'name': 'cottage_hill', 'cx': 120, 'cy': 162, 'r_top': 13, 'H': 22},   # z 41
        {'name': 'pumpkin_hill', 'cx': 120, 'cy': 350, 'r_top': 12, 'H': 19},   # z 44
        {'name': 'tree_knoll', 'cx': 62, 'cy': 256, 'r_top': 10, 'H': 18},      # z 45
    ],
    'cover_walls': [  # staggered screen between spawn and platform (overlapping y spans)
        {'x': (142, 146), 'y': (226, 257), 'top_z': 34},
        {'x': (151, 155), 'y': (255, 286), 'top_z': 34},
    ],
    'central': {'x0': 186, 'y': (228, 284), 'corner_r': 10, 'H': 7},       # z 56 floor; west half to x 256
    'mound': {'x': (196, 211), 'y': (240, 271), 'top_z': 40,
              'north_stair_y': (236, 239), 'south_stair_y': (272, 275)},
    'boardwalk': {'x': (160, 200), 'y': (252, 259), 'deck_z': 61, 'post_every': 4},
    'footbridge': {'x': (160, 200), 'y': (229, 231), 'deck_z': 61, 'post_every': 4},
    'pilings': {'size': 3, 'top_z': 57,
                'centres': [(172, 242), (177, 246), (182, 242), (172, 269), (177, 265), (182, 269)]},
    'standing_stones': [(222, 232), (238, 230), (222, 280), (238, 282), (250, 233), (250, 279)],
    'screen_trees': [  # tall witch trees east of the spawn; canopies catch platform sightlines over the walls
        {'x': 162, 'y': 239, 'trunk': 4, 'top_z': 18, 'canopy_r': 15, 'canopy_rx': 11, 'canopy_h': 5},
        {'x': 162, 'y': 273, 'trunk': 4, 'top_z': 18, 'canopy_r': 15, 'canopy_rx': 11, 'canopy_h': 5},
    ],
    'giant_tree': {'x': 62, 'y': 256, 'trunk': 5, 'top_z': 18, 'canopy_r': 13, 'canopy_h': 6},
    'cottage': {'x': (114, 127), 'y': (156, 166), 'wall_h': 5, 'door_x': (119, 121)},
    'islets': [{'cx': 256, 'cy': 138, 'r': 13, 'H': 5}, {'cx': 256, 'cy': 374, 'r': 13, 'H': 5}],
    'lagoon': {'cx': 256, 'cy': 256, 'rx': 112, 'ry': 96},
    'groves': [  # (cx, cy, radius, count)
        (70, 170, 26, 9), (64, 330, 26, 9), (150, 330, 16, 4), (82, 120, 18, 5), (160, 175, 14, 3),
        (60, 210, 12, 3), (98, 380, 12, 3),
        (100, 300, 16, 6), (40, 300, 12, 4), (150, 140, 14, 4), (46, 140, 12, 4), (150, 372, 12, 3),
        (130, 200, 10, 3), (36, 236, 8, 2), (36, 278, 8, 2),
    ],
    'pumpkins': {'cx': 120, 'cy': 350, 'r': 9, 'count': 10},
    'fog': (182, 168, 150),
    'water_damage': 5,
}

# ---------------------------------------------------------------- materials (graybox function colours)
MATS = {
    0: ('air', (0, 0, 0)),
    1: ('seabed', (38, 66, 78)),
    2: ('lagoon_bed', (40, 108, 92)),
    3: ('sand', (176, 162, 116)),
    4: ('grass', (78, 120, 62)),
    5: ('spawn_floor', (150, 140, 96)),
    6: ('earth', (104, 84, 60)),
    7: ('stone_floor', (120, 116, 132)),
    8: ('mound', (152, 146, 172)),
    9: ('stair', (196, 184, 122)),
    10: ('boardwalk', (132, 98, 62)),
    11: ('piling', (90, 66, 46)),
    12: ('cover_wall', (96, 92, 112)),
    13: ('trunk', (70, 52, 38)),
    14: ('foliage_purple', (98, 72, 140)),
    15: ('foliage_green', (60, 108, 60)),
    16: ('cottage_wall', (122, 96, 72)),
    17: ('roof', (66, 52, 92)),
    18: ('pumpkin', (226, 122, 34)),
    19: ('standing_stone', (62, 58, 78)),
    20: ('path', (150, 120, 84)),
}
M = {v[0]: k for k, v in MATS.items()}


def _box(solid, mat, x0, x1, y0, y1, z0, z1, m):
    """Inclusive box fill (z0 <= z1)."""
    solid[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1] = True
    mat[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1] = m


def _column(solid, mat, x, y, ztop, m, mfill=None):
    solid[x, y, ztop:] = True
    mat[x, y, ztop:] = mfill if mfill is not None else m
    mat[x, y, ztop] = m


def raise_relax(H, land):
    """Raise cells so no land cell is more than 1 below a land neighbour (keeps plateaus flat)."""
    H = H.copy()
    fp = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool)
    for _ in range(64):
        nb = ndimage.maximum_filter(np.where(land, H, -999), footprint=fp, mode='constant', cval=-999)
        newH = np.where(land, np.maximum(H, nb - 1), 0)
        if np.array_equal(newH, H):
            break
        H = newH
    return H


def heightfield():
    """Return (H, landmask) for the authored west half (full-size arrays, x > 256 ignored)."""
    S = SPEC
    xs = np.arange(W)[:, None]
    ys = np.arange(W)[None, :]
    isl = S['island']
    e = isl['ellipse']
    n = fbm(seed_of('shore', SEED), (W, W), 32, 3)
    r = ((xs - e['cx']) / e['rx']) ** 2 + ((ys - e['cy']) / e['ry']) ** 2
    land = r + (n - 0.5) * 2 * isl['shore_noise'] / e['rx'] < 1.0
    # forced straight east shore in the crossing rows (boardwalk, footbridge, pilings)
    cr0, cr1 = isl['crossing_rows']
    rows = (ys >= cr0) & (ys <= cr1)
    land &= ~(rows & (xs > isl['east_shore_x']))
    land |= rows & (xs <= isl['east_shore_x']) & (xs >= 120)
    # central island (west half): rounded rectangle x0..256
    c = S['central']
    cy0, cy1 = c['y']
    cr = c['corner_r']
    inner = (xs >= c['x0'] + cr) & (ys >= cy0) & (ys <= cy1) | \
            (xs >= c['x0']) & (ys >= cy0 + cr) & (ys <= cy1 - cr)
    corners = np.zeros((W, W), bool)
    for (ccx, ccy) in ((c['x0'] + cr, cy0 + cr), (c['x0'] + cr, cy1 - cr)):
        corners |= (xs - ccx) ** 2 + (ys - ccy) ** 2 <= cr * cr
    central = (inner | corners) & (xs <= 256)
    # islets
    islets = np.zeros((W, W), bool)
    for it in S['islets']:
        islets |= (xs - it['cx']) ** 2 + (ys - it['cy']) ** 2 <= it['r'] ** 2
    land = (land | central | islets) & (xs <= 256)
    land[0:4, :] = False
    land[:, 0:4] = False
    land[:, -4:] = False

    # design heights
    design = np.zeros((W, W))
    design[land] = isl['base_H']
    design[central] = c['H']
    design[islets] = 0
    for it in S['islets']:
        dd = np.sqrt((xs - it['cx']) ** 2 + (ys - it['cy']) ** 2)
        design = np.where(islets & (dd <= it['r'] - 7), it['H'], design)
    sp = S['spawn_plateau']
    plateau = (xs >= sp['x'][0]) & (xs <= sp['x'][1]) & (ys >= sp['y'][0]) & (ys <= sp['y'][1])
    design = np.where(plateau & land, sp['H'], design)
    for h in S['hills']:
        dd = np.sqrt((xs - h['cx']) ** 2 + (ys - h['cy']) ** 2)
        design = np.where((dd <= h['r_top']) & land, np.maximum(design, h['H']), design)
    # gentle undulation of the base woods (+0..2), never on the plateau or central island
    und = np.round(fbm(seed_of('und', SEED), (W, W), 24, 2) * 3).astype(int)
    island_only = land & ~central & ~islets & ~plateau
    design = np.where(island_only, design + und, design)
    design = design.astype(int)

    # mirror the masks/design before relax + coast distance so the x 256 axis is not seen as shore
    def mir(a):
        a = a.copy()
        a[257:512] = a[255:0:-1]
        return a
    land, central, islets, plateau, design = mir(land), mir(central), mir(islets), mir(plateau), mir(design)
    H = raise_relax(design, land)
    water = ~land
    coast = ndimage.distance_transform_cdt(~water, metric='taxicab')
    H = np.where(land, np.minimum(H, coast), 0)
    return H.astype(int), land, central, islets, plateau


def big_tree(solid, mat, H, tr):
    zg = int(np.max(63 - H[tr['x'] - 2:tr['x'] + 3, tr['y'] - 2:tr['y'] + 3]))   # lowest ground under trunk
    t = tr['trunk']
    tx0 = tr['x'] - t // 2
    ty0 = tr['y'] - t // 2
    _box(solid, mat, tx0, tx0 + t - 1, ty0, ty0 + t - 1, tr['top_z'], zg, M['trunk'])
    cz = tr['top_z'] + 2
    R = tr['canopy_r']
    RX = tr.get('canopy_rx', R)
    hh = tr['canopy_h']
    for x in range(tr['x'] - RX, tr['x'] + RX + 1):
        for y in range(tr['y'] - R, tr['y'] + R + 1):
            for z in range(cz - hh, cz + hh + 1):
                d = ((x - tr['x']) / RX) ** 2 + ((y - tr['y']) / R) ** 2 + ((z - cz) / hh) ** 2
                if d <= 1.0 and not solid[x, y, z]:
                    solid[x, y, z] = True
                    mat[x, y, z] = M['foliage_purple']


def build(props=True):
    """props=False: terrain + gameplay structures only (mound, stairs, pilings); the art pass adds the rest."""
    S = SPEC
    solid, mat = new_volume()
    mat[:, :, 63] = M['seabed']
    xs = np.arange(W)[:, None]
    ys = np.arange(W)[None, :]
    lg = S['lagoon']
    lagoon = ((xs - lg['cx']) / lg['rx']) ** 2 + ((ys - lg['cy']) / lg['ry']) ** 2 <= 1.0
    mat[:, :, 63][lagoon] = M['lagoon_bed']

    H, land, central, islets, plateau = heightfield()
    ztop = 63 - H
    for x in range(0, 257):
        for y in range(W):
            if not land[x, y]:
                continue
            z = ztop[x, y]
            solid[x, y, z:] = True
            mat[x, y, z:] = M['earth']
            if central[x, y]:
                top = M['stone_floor'] if H[x, y] >= S['central']['H'] else M['sand']
            elif plateau[x, y] and H[x, y] == S['spawn_plateau']['H']:
                top = M['spawn_floor']
            elif H[x, y] <= 2:
                top = M['sand']
            else:
                top = M['grass']
            mat[x, y, z] = top

    # --- mound (tower anchor) + stairs
    mo = S['mound']
    x0, x1 = mo['x']
    y0, y1 = mo['y']
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            _column(solid, mat, x, y, mo['top_z'], M['mound'], M['mound'])
    # north stair rises eastward from the west apron: x0 -> z 55 ... x1 -> top_z
    # outer row is a 1-high cheek rail so nobody walks off the open side
    floor_z = 63 - S['central']['H']
    ny0, ny1 = mo['north_stair_y']
    for i, x in enumerate(range(x0, x1 + 1)):
        zt = floor_z - 1 - i
        for y in range(ny0, ny1 + 1):
            if y == ny0:
                _column(solid, mat, x, y, zt - 1, M['cover_wall'], M['mound'])
            else:
                _column(solid, mat, x, y, zt, M['stair'], M['mound'])
    # south stair also rises eastward from the team's own west apron (no stair foot on the enemy-facing side)
    sy0, sy1 = mo['south_stair_y']
    for i, x in enumerate(range(x0, x1 + 1)):
        zt = floor_z - 1 - i
        for y in range(sy0, sy1 + 1):
            if y == sy1:
                _column(solid, mat, x, y, zt - 1, M['cover_wall'], M['mound'])
            else:
                _column(solid, mat, x, y, zt, M['stair'], M['mound'])

    if not props:
        pl = S['pilings']
        h = pl['size'] // 2
        for (px, py) in pl['centres']:
            _box(solid, mat, px - h, px + h, py - h, py + h, pl['top_z'], 62, M['piling'])
        return solid, mat, H, {'land': land, 'central': central, 'islets': islets, 'plateau': plateau}

    # --- standing stones (2x2, 6 high on the floor)
    for (sx, sy) in S['standing_stones']:
        zf = 63 - H[sx, sy]
        _box(solid, mat, sx, sx + 1, sy, sy + 1, zf - 6, zf - 1, M['standing_stone'])

    # --- cover walls (solid to the seabed)
    for cw in S['cover_walls']:
        for x in range(cw['x'][0], cw['x'][1] + 1):
            for y in range(cw['y'][0], cw['y'][1] + 1):
                _column(solid, mat, x, y, cw['top_z'], M['cover_wall'], M['cover_wall'])

    # --- boardwalk + footbridge: deck on posts
    for key in ('boardwalk', 'footbridge'):
        b = S[key]
        z = b['deck_z']
        for x in range(b['x'][0], b['x'][1] + 1):
            for y in range(b['y'][0], b['y'][1] + 1):
                if land[x, y] and 63 - H[x, y] <= z:
                    continue
                solid[x, y, z] = True
                mat[x, y, z] = M['boardwalk']
            if (x - b['x'][0]) % b['post_every'] == 0 or x == b['x'][1]:
                for y in (b['y'][0], b['y'][1]):
                    if not land[x, y]:
                        solid[x, y, z:63] = True
                        mat[x, y, z + 1:63] = M['piling']

    # --- pilings (3x3 tower anchors in the water gap, inside the own build-ban corridor)
    pl = S['pilings']
    h = pl['size'] // 2
    for (px, py) in pl['centres']:
        _box(solid, mat, px - h, px + h, py - h, py + h, pl['top_z'], 62, M['piling'])

    # --- giant crooked tree + screen trees (graybox: trunk + canopy ellipsoid)
    gt = S['giant_tree']
    R = gt['canopy_r']
    for tr in [gt] + S['screen_trees']:
        big_tree(solid, mat, H, tr)

    # --- cottage on the hill
    co = S['cottage']
    cx0, cx1 = co['x']
    cy0, cy1 = co['y']
    zf = int(np.min(63 - H[cx0:cx1 + 1, cy0:cy1 + 1]))  # highest ground under the footprint
    for x in range(cx0, cx1 + 1):
        for y in range(cy0, cy1 + 1):
            _column(solid, mat, x, y, zf, M['path'], M['earth'])
    zw0 = zf - co['wall_h']
    _box(solid, mat, cx0, cx1, cy0, cy1, zw0, zf - 1, M['cottage_wall'])
    solid[cx0 + 1:cx1, cy0 + 1:cy1, zw0:zf] = False
    mat[cx0 + 1:cx1, cy0 + 1:cy1, zw0:zf] = 0
    dx0, dx1 = co['door_x']
    solid[dx0:dx1 + 1, cy1, zf - 3:zf] = False   # door on the south wall (faces the spawn)
    mat[dx0:dx1 + 1, cy1, zf - 3:zf] = 0
    # gabled roof along x, stepping in over y
    k = 0
    while cy0 - 1 + k <= cy1 + 1 - k:
        _box(solid, mat, cx0 - 1, cx1 + 1, cy0 - 1 + k, cy1 + 1 - k, zw0 - 1 - k, zw0 - 1 - k, M['roof'])
        k += 1
    # gable end walls under the roof
    for kk in range(1, k):
        for x in (cx0, cx1):
            solid[x, cy0 + kk:cy1 - kk + 1, zw0 - kk] = True
            mat[x, cy0 + kk:cy1 - kk + 1, zw0 - kk] = M['cottage_wall']

    # --- groves (graybox trees: 2x2 trunk + chopped 7x7x4 canopy)
    rng = np.random.RandomState(SEED)
    keep_out = np.zeros((W, W), bool)
    sp = SPEC['spawn_plateau']
    keep_out[sp['x'][0] - 4:sp['x'][1] + 5, sp['y'][0] - 4:sp['y'][1] + 5] = True
    keep_out[cx0 - 5:cx1 + 6, cy0 - 5:cy1 + 6] = True
    keep_out[gt['x'] - R - 3:gt['x'] + R + 4, gt['y'] - R - 3:gt['y'] + R + 4] = True
    for tr in S['screen_trees']:
        keep_out[tr['x'] - 18:tr['x'] + 19, tr['y'] - 18:tr['y'] + 19] = True
    for cw in S['cover_walls']:
        keep_out[cw['x'][0] - 4:cw['x'][1] + 5, cw['y'][0] - 4:cw['y'][1] + 5] = True
    keep_out[:, 236:277] |= (xs[:, 0] >= 140)[:, None]   # open approach to the crossings
    keep_out[:, 220:292] |= (xs[:, 0] >= 150)[:, None]
    placed = []
    for gi, (gx, gy, gr, cnt) in enumerate(S['groves']):
        tries = 0
        made = 0
        while made < cnt and tries < 200:
            tries += 1
            a = rng.rand() * 2 * np.pi
            rr = gr * np.sqrt(rng.rand())
            tx, ty = int(gx + rr * np.cos(a)), int(gy + rr * np.sin(a))
            if not (8 <= tx <= 248 and 8 <= ty <= 503):
                continue
            if keep_out[tx - 4:tx + 5, ty - 4:ty + 5].any():
                continue
            if not land[tx - 3:tx + 4, ty - 3:ty + 4].all() or H[tx, ty] < 4:
                continue
            if any((tx - px) ** 2 + (ty - py) ** 2 < 64 for px, py in placed):
                continue
            th = 8 + rng.randint(0, 4)
            zg = int(np.min(63 - H[tx:tx + 2, ty:ty + 2]))
            ztt = zg - th
            _box(solid, mat, tx, tx + 1, ty, ty + 1, ztt, zg, M['trunk'])
            fol = M['foliage_purple'] if rng.rand() < 0.55 else M['foliage_green']
            for z in range(ztt - 3, ztt + 1):
                for x in range(tx - 3, tx + 5):
                    for y in range(ty - 3, ty + 5):
                        cxn = abs(x - tx - 0.5) >= 3.5 - 0.01
                        cyn = abs(y - ty - 0.5) >= 3.5 - 0.01
                        if cxn and cyn:
                            continue  # chop corners
                        if (z == ztt - 3) and (abs(x - tx - 0.5) > 2.5 or abs(y - ty - 0.5) > 2.5):
                            continue
                        if not solid[x, y, z]:
                            solid[x, y, z] = True
                            mat[x, y, z] = fol
            placed.append((tx, ty))
            made += 1

    # --- pumpkins (2x2x1 on the pumpkin hill)
    pk = S['pumpkins']
    made = 0
    tries = 0
    while made < pk['count'] and tries < 300:
        tries += 1
        a = rng.rand() * 2 * np.pi
        rr = pk['r'] * np.sqrt(rng.rand())
        px, py = int(pk['cx'] + rr * np.cos(a)), int(pk['cy'] + rr * np.sin(a))
        zt = 63 - H[px:px + 2, py:py + 2]
        if zt.min() != zt.max():
            continue
        z = int(zt.min()) - 1
        if solid[px:px + 2, py:py + 2, z].any() or solid[px - 1:px + 3, py - 1:py + 3, z].any():
            continue
        _box(solid, mat, px, px + 1, py, py + 1, z, z, M['pumpkin'])
        made += 1

    # --- islet dead trees
    for it in S['islets']:
        zg = 63 - H[it['cx'] - 3, it['cy']]
        _box(solid, mat, it['cx'] - 4, it['cx'] - 3, it['cy'], it['cy'] + 1, zg - 9, zg, M['trunk'])
        _box(solid, mat, it['cx'] - 7, it['cx'] - 3, it['cy'], it['cy'], zg - 7, zg - 7, M['trunk'])

    # --- path painting: spawn exits to the crossings (surface paint only)
    for (ax, ay, bx, by) in ((139, 220, 166, 220), (139, 292, 148, 292), (148, 292, 166, 262),
                             (166, 262, 168, 256), (166, 220, 168, 230)):
        n = max(abs(bx - ax), abs(by - ay)) + 1
        for i in range(n):
            x = int(round(ax + (bx - ax) * i / max(n - 1, 1)))
            y = int(round(ay + (by - ay) * i / max(n - 1, 1)))
            for ddx in (-1, 0, 1):
                for ddy in (-1, 0, 1):
                    xx, yy = x + ddx, y + ddy
                    if land[xx, yy] and mat[xx, yy, 63 - H[xx, yy]] in (M['grass'], M['sand']):
                        if not solid[xx, yy, :63 - H[xx, yy]].any():
                            mat[xx, yy, 63 - H[xx, yy]] = M['path']

    # --- mirror x' = 512 - x
    solid[257:512] = solid[255:0:-1]
    mat[257:512] = mat[255:0:-1]
    solid[:, :, 63] = True
    return solid, mat, H


def shade(solid, mat):
    """Graybox colouring: material base, darker sides, slightly darker with depth."""
    pal = np.array([MATS[i][1] if i in MATS else (255, 0, 255) for i in range(256)], dtype=np.float32)
    col = pal[mat]
    above_solid = np.zeros_like(solid)
    above_solid[:, :, 1:] = solid[:, :, :-1]
    side = solid & above_solid
    col[side] *= 0.80
    # height tint: higher tops a touch lighter
    zz = np.arange(D, dtype=np.float32)[None, None, :, None]
    col *= (1.0 + (40 - zz) * 0.004).clip(0.9, 1.12)
    return col.clip(0, 255).astype(np.uint8)


def map_txt(path, version='0.1-graybox'):
    S = SPEC
    txt = f"""name = 'Witchwood Isles'
version = '{version}'
author = 'shywolf91 and AI'
description = ('Babel, Halloween island map: twin witchwood isles, a standing-stone isle under the platform '
               'with an anchor mound under each end, mooring pilings in the water gaps.')
fog = {S['fog']}
extensions = {{
    'water_damage': {S['water_damage']},
}}
# No spawn/entity hooks on purpose: stock babel_script uses fixed bases (118,256)/(394,256) and +-20 spawns.
# water_damage needs piqueserver.scripts.map_extensions in the server's script list.
"""
    with open(path, 'w') as f:
        f.write(txt)
    return txt
