"""Sprinkler Field gameplay geometry (graybox): terrain, hose, edging, ant nest, lawn props (west half).

build_west(S, seed) -> (canvas, report)
    terrain for the whole map (east half comes from symmetry.mirror_canvas) + every mirrored feature on the west
    half: the garden hose (rests, ruts, arches, split), brick edging + mud trail, the ant nest (tunnels, chambers,
    crater entrances with walkable ramps), grass tussocks, clover, dandelions, pebbles, mushrooms, acorns, twigs,
    leaves, bottle caps, pinecones, front dressing, spawn cover, under-platform props, puddles.
    Axis objects (sprinkler, feeder hose, trowel, queen chamber, under-platform cap) are in sf_axis (after the mirror);
    one-off landmarks in sf_oneoffs.

Every number comes from SPEC (sf_spec.py). Graybox colours are function colours keyed by material; the art pass
(sf_art, not written yet) recolours by material. Layout randomness uses aosmap.kit.noise (crc32 seeds) only.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage as ndi

from aosmap.kit import noise
from aosmap.kit.canvas import Canvas, line_points

# graybox function colours by material (sf_art replaces them)
GC = {
    'soil': (112, 88, 64), 'lawn': (88, 112, 62), 'spawn': (104, 124, 78), 'front': (116, 118, 80),
    'anchor': (128, 112, 90), 'bank': (100, 96, 66), 'trail': (96, 78, 60), 'puddle': (96, 132, 150),
    'hose': (60, 132, 70), 'hose_stripe': (206, 196, 70), 'brick': (164, 92, 66), 'crater': (132, 104, 74),
    'tunnel': (84, 70, 56), 'crown': (70, 96, 52), 'blade': (78, 150, 64), 'clover': (66, 140, 84),
    'stalk': (110, 150, 80), 'seedhead': (214, 210, 196), 'dandelion_stalk': (120, 160, 90), 'pebble': (138, 134, 128),
    'mushroom_cap': (176, 120, 86), 'mushroom_stem': (210, 196, 170), 'acorn': (150, 104, 56),
    'acorn_cap': (110, 86, 58), 'twig': (104, 80, 60), 'leaf': (170, 120, 50), 'cap': (180, 60, 60),
    'cap_inner': (200, 196, 190), 'pinecone': (120, 84, 54), 'pinecone_dk': (92, 64, 44), 'daisy': (226, 220, 210),
    'daisy_eye': (220, 180, 60), 'seed': (90, 86, 70), 'dew': (170, 200, 214), 'sprout': (130, 190, 90),
    # axis objects and one-offs (sf_axis / sf_oneoffs)
    'pad': (150, 150, 156), 'leg': (150, 154, 160), 'rivet': (110, 112, 118), 'collar': (210, 120, 50),
    'riser': (140, 142, 150), 'step': (196, 160, 70), 'brass': (190, 160, 70), 'arm': (170, 150, 80),
    'tbar': (196, 168, 80), 'spring': (100, 100, 108), 'coupling': (190, 160, 70), 'heap': (124, 96, 68),
    'blade_steel': (176, 180, 186), 'rib': (150, 154, 160), 'handle': (176, 136, 70), 'ferrule': (160, 160, 168),
    'concrete': (160, 158, 150), 'tap': (186, 150, 64), 'reel': (60, 120, 66), 'cart': (90, 92, 100),
    'wheel': (50, 52, 58), 'pot': (190, 110, 70), 'potsoil': (100, 76, 56), 'glove': (120, 150, 170),
    'glove_cuff': (200, 180, 90), 'shell': (176, 150, 110), 'shell_dk': (130, 104, 80), 'label': (220, 218, 200),
    'print': (96, 76, 58), 'key': (130, 130, 136), 'stair': (150, 120, 90), 'floor': (128, 100, 72),
}

KEEP = {'spawn': 1, 'front': 2, 'anchor': 4, 'hose': 8, 'nest': 16, 'axis': 32, 'edge': 64}


def put(cv, x, y, z, mat, c=None):
    cv.set(int(x), int(y), int(z), c or GC.get(mat, (200, 0, 200)), mat)


def box(cv, x0, x1, y0, y1, z0, z1, mat, c=None):
    cv.box(min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), min(z0, z1), max(z0, z1), c or GC.get(mat), mat)


def top(cv, x, y):
    return cv.column_top(int(x), int(y))


def col_down(cv, x, y, z, mat):
    """Fill from z down to the first solid voxel (face contact with whatever is below)."""
    if not (0 <= x < 512 and 0 <= y < 512):
        return
    zz = int(z)
    while zz < 64 and not cv.solid[x, y, zz]:
        put(cv, x, y, zz, mat)
        zz += 1


def smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def feature(rep, name, kind, x, y, r_walk, r_top=None, **extra):
    """Record a feature for the gap report; `extra` (geometry numbers) is read by the art pass only."""
    f = {'name': name, 'kind': kind, 'x': float(x), 'y': float(y), 'r_walk': float(r_walk),
         'r_top': float(r_top or r_walk)}
    f.update(extra)
    rep.setdefault('features', []).append(f)


# =============================================================================================== hose field

def polyline_field(pts, X, Y):
    """Distance to a polyline and the x / y of the closest point, per column."""
    best = np.full(X.shape, np.inf)
    bx = np.zeros(X.shape)
    by = np.zeros(X.shape)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        dx, dy = x1 - x0, y1 - y0
        L2 = float(dx * dx + dy * dy)
        t = np.clip(((X - x0) * dx + (Y - y0) * dy) / L2, 0, 1)
        px, py = x0 + t * dx, y0 + t * dy
        d = np.hypot(X - px, Y - py)
        m = d < best
        best = np.where(m, d, best)
        bx = np.where(m, px, bx)
        by = np.where(m, py, by)
    return best, bx, by


def hose_lift(S, xs):
    """Lift of the hose centre line (voxels up, + = higher) as a function of x along the path: arches rise to
    their lift over the span with 1-per-column ramps; ruts sink the hose until its top is flush with the ground."""
    Hs = S['hose']
    xs = np.asarray(xs, float)
    L = np.zeros_like(xs)
    for (a, b), lift in Hs['arches']:
        dist = np.maximum(np.maximum(a - xs, xs - b), 0)
        L += np.clip(lift - dist * Hs['ramp'], 0, None)
    top_h = 2 * Hs['r_out']
    for (a, b) in Hs['ruts']:
        dist = np.maximum(np.maximum(a - xs, xs - b), 0)
        L -= np.clip(top_h - dist * Hs['ramp'], 0, None)
    return L


def hose_y(S, x):
    pts = S['hose']['path']
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / max(x1 - x0, 1)
    return pts[-1][1]


# =============================================================================================== terrain

def terrain(cv, rep, S, seed):
    X, Y = np.meshgrid(np.arange(512, dtype=float), np.arange(512, dtype=float), indexing='ij')
    Z = S['z']
    lawn = Z['lawn']
    rl = S['relief']
    f1 = noise.fbm2((512, 512), rl['cell'], 3, 'relief', seed)
    f2 = noise.fbm2((512, 512), rl['mound_cell'], 2, 'mounds', seed)
    Hf = lawn + rl['amp'] * (f1 - 0.5) * 4 + rl['mound_amp'] * (f2 - 0.5) * 4
    Hf = np.clip(Hf, lawn - 2, lawn + 2)
    # ---------------------------------------------------------------- flat bands (hose, trail, axis pads, puddles)
    W = np.zeros((512, 512))
    T = np.full((512, 512), float(lawn))
    dh, _, _ = polyline_field(S['hose']['path'], X, Y)
    W = np.maximum(W, smooth((S['hose']['flat'] + 6 - dh) / 6))
    fd = S['hose']['feeder']
    W = np.maximum(W, smooth((12 - np.abs(X - 256)) / 5) * (Y >= fd['path'][0][1] - 6) * (Y <= fd['path'][-1][1] + 6))
    tr = S['south_trail']
    dtr = np.maximum(np.maximum(tr['y'][0] - Y, Y - tr['y'][1]), 0)
    W = np.maximum(W, smooth((10 - dtr) / 6) * (X >= tr['x'][0] - 8))
    ed = S['edging']
    ded = np.maximum(np.maximum(ed['y'][0] - Y, Y - ed['y'][1]), 0)
    W = np.maximum(W, smooth((6 - ded) / 4))
    sp = S['sprinkler']
    for (fx, fy) in sp['feet'].values():
        for xx in (fx, 512 - fx):
            W = np.maximum(W, smooth((S['sprinkler']['pad'] + 6 - np.hypot(X - xx, Y - fy)) / 5))
    hx, hy, hrx, hry, _ = S['trowel']['heap']
    W = np.maximum(W, smooth((1.0 - np.hypot((X - hx) / (hrx + 8), (Y - hy) / (hry + 8))) * 4))
    for (px, py, pr) in S['puddles']:
        W = np.maximum(W, smooth((pr + 6 - np.hypot(X - px, Y - py)) / 4))
    for (kind, px, py, pr) in S['under_platform']:
        if kind == 'puddle':
            W = np.maximum(W, smooth((pr + 6 - np.hypot(X - px, Y - py)) / 4))
    Hf = Hf * (1 - W) + T * W
    # trail: worn 1 below the flattened lawn
    trail = (Y >= tr['y'][0]) & (Y <= tr['y'][1]) & (X >= tr['x'][0])
    trail_edge = trail & ~((Y >= tr['y'][0] + 1) & (Y <= tr['y'][1] - 1))
    Hf = np.where(trail & ~trail_edge, lawn + 1, Hf)
    # ---------------------------------------------------------------- gameplay zones: spawn, front, anchor (blended)
    Zm = np.zeros((512, 512), bool)
    Tz = np.zeros((512, 512))
    b = S['spawn']['base']
    h = S['spawn']['half'] + S['spawn']['margin']
    sq = (np.abs(X - b[0]) <= h) & (np.abs(Y - b[1]) <= h)
    mn = noise.fbm2((512, 512), S['spawn']['mound_cell'], 2, 'spawn_mounds', seed)
    mounds = np.where(mn > S['spawn']['mound_thresh'], -1, 0)
    Zm |= sq
    Tz = np.where(sq, Z['spawn'] + mounds, Tz)
    ax, ay = S['anchor']['x'], S['anchor']['y']
    fy = S['front']['y']
    fr = (X > b[0] + h) & (X < ax[0]) & (Y >= fy[0] - 4) & (Y <= fy[1] + 4)
    FC = S['front_crest']
    zs, za, zc = Z['spawn'], S['anchor']['z'], FC['z']
    c0, c1 = FC['crest']
    prof = np.where(X < c0, zs - (zs - zc) * np.clip((X - FC['x0']) / max(c0 - FC['x0'], 1), 0, 1),
                    np.where(X <= c1, zc, zc + (za - zc) * np.clip((X - c1) / (ax[0] - c1), 0, 1)))
    Zm |= fr
    Tz = np.where(fr, np.round(prof), Tz)
    an = (X >= ax[0]) & (X <= ax[1]) & (Y >= ay[0]) & (Y <= ay[1])
    Zm |= an
    Tz = np.where(an, S['anchor']['z'], Tz)
    dz, (ix, iy) = ndi.distance_transform_edt(~Zm, return_indices=True)
    w = np.clip(1 - dz / S['zone_blend'], 0, 1)
    Hn = Hf * (1 - w) + Tz[ix, iy] * w
    Hn = np.where(Zm, Tz, Hn)
    # ---------------------------------------------------------------- rear bank (spawn backdrop): a worm-cast ridge
    rb = S['rear_bank']
    (bcx, bcy), (brx, bry), bh = rb['c'], rb['r'], rb['h']
    inside = ((X - bcx) / brx) ** 2 + ((Y - bcy) / bry) ** 2 <= 1
    din = ndi.distance_transform_edt(inside)
    bank_h = np.minimum(bh, din * rb['slope'])
    Hn = np.minimum(Hn, np.where(inside, lawn - bank_h, 99))
    H = np.round(Hn)
    # ---------------------------------------------------------------- puddles: shallow dips (painted water)
    pud = np.zeros((512, 512), bool)
    plist = [(px, py, pr) for (px, py, pr) in S['puddles']] + \
            [(px, py, pr) for (k, px, py, pr) in S['under_platform'] if k == 'puddle']
    for (px, py, pr) in plist:
        d = np.hypot(X - px, Y - py)
        H = np.where(d <= pr, np.maximum(H, lawn + 1), H)
        H = np.where(d <= pr - 3, np.maximum(H, Z['puddle']), H)
        pud |= d <= pr
    H = np.clip(H, 0, 61).astype(int)
    H[257:] = 63                                         # east half comes from the mirror
    # materials (top voxel); everything below is soil
    mat = np.full((512, 512), 'lawn', object)
    mat[(f1 > 0.56) & ~Zm] = 'soil'
    mat[inside & (bank_h >= 2)] = 'bank'
    mat[trail & ~trail_edge] = 'trail'
    mat[pud] = 'puddle'
    mat[Zm & sq] = 'spawn'
    mat[Zm & fr] = 'front'
    mat[Zm & an] = 'anchor'
    cv.H = H.astype(np.int16)
    zz = np.arange(64)[None, None, :]
    cv.fill_mask(zz >= H[:, :, None], GC['soil'], 'soil')
    xi, yi = np.nonzero(H < 63)
    for m in ('lawn', 'bank', 'trail', 'puddle', 'spawn', 'front', 'anchor'):
        k = mat[xi, yi] == m
        cv.rgb[xi[k], yi[k], H[xi[k], yi[k]]] = GC[m]
        cv.mat[xi[k], yi[k], H[xi[k], yi[k]]] = cv.material(m)
    # no-prop flags
    cv.no_prop(b[0] - h, b[0] + h, b[1] - h, b[1] + h, KEEP['spawn'])
    cv.no_prop(b[0] + h + 1, ax[0] - 1, fy[0], fy[1], KEEP['front'])
    cv.no_prop(ax[0], 255, ay[0], ay[1], KEEP['anchor'])
    cv.no_prop(0, 511, 0, 3, KEEP['edge'])
    cv.no_prop(0, 511, 508, 511, KEEP['edge'])
    cv.no_prop(0, 3, 0, 511, KEEP['edge'])
    rep['terrain'] = {'H_min': int(H[:256].min()), 'H_max': int(H[:256][H[:256] < 63].max()),
                      'spawn_cols_raised': int((sq & (mounds < 0)).sum()), 'bank_cells': int(inside.sum())}
    return {'zones': Zm, 'puddles': pud}


# =============================================================================================== garden hose

def garden_hose(cv, rep, S):
    """Main hose, west half (x 0-256 on the path; mirrored). A pipe on the ground (outer r_out), solid except the
    split section; arches lift it (walk under), ruts sink it flush with the soil (walk over / climb on), the split is
    torn open (walk through, hoops intact)."""
    Hs = S['hose']
    r = Hs['r_out'] + 0.4
    x0, x1 = 0, 259
    ys = [p[1] for p in Hs['path']]
    y0, y1 = min(ys) - 12, max(ys) + 12
    X, Y = np.meshgrid(np.arange(x0, x1 + 1, dtype=float), np.arange(y0, y1 + 1, dtype=float), indexing='ij')
    d, xc, _ = polyline_field(Hs['path'], X, Y)
    cz = np.round(Hs['cz'] - hose_lift(S, xc))
    zs = np.arange(64, dtype=float)[None, None, :]
    dz = zs - cz[:, :, None]
    rr = d[:, :, None] ** 2 + dz ** 2
    tube = rr <= r * r
    sx0, sx1 = Hs['split']
    split = ((xc >= sx0) & (xc <= sx1))[:, :, None]
    hoop = np.zeros(xc.shape, bool)
    for hx in Hs['hoops']:
        hoop |= (xc >= hx) & (xc <= hx + 1)
    hoop = hoop[:, :, None]
    r_in = Hs['r_in'] + 0.4
    keep_low = dz >= Hs['split_floor']                  # the bottom skin that stays on the ground
    tube_split = tube & split & ((hoop & (rr > r_in * r_in)) | (~hoop & keep_low))
    tube = np.where(split, tube_split, tube)
    sub_solid = cv.solid[x0:x1 + 1, y0:y1 + 1]
    stripe = tube & (d[:, :, None] < 0.8) & (dz <= -Hs['r_out'] + 0.5)
    m_h = cv.material('hose')
    m_s = cv.material('hose_stripe')
    sub_solid[tube] = True
    cv.rgb[x0:x1 + 1, y0:y1 + 1][tube] = GC['hose']
    cv.mat[x0:x1 + 1, y0:y1 + 1][tube] = m_h
    cv.rgb[x0:x1 + 1, y0:y1 + 1][stripe & tube] = GC['hose_stripe']
    cv.mat[x0:x1 + 1, y0:y1 + 1][stripe & tube] = m_s
    # torn flaps at the split ends: a step block inside the trough (top -> flap 6 -> trough 5)
    for (fa, fb) in ((sx0, sx0 + 2), (sx1 - 2, sx1)):
        for x in range(fa, fb + 1):
            yc = hose_y(S, x)
            czx = int(round(Hs['cz'] - hose_lift(S, [x])[0]))
            for y in range(int(round(yc)) - 2, int(round(yc)) + 3):
                box(cv, x, x, y, y, czx, czx + Hs['split_floor'], 'hose')
    # Y-coupling collar on the axis (thicker ring; walk on it with a 1-voxel step)
    cpx, cpy = Hs['coupling']
    for x in range(cpx - 6, 256):
        for y in range(cpy - 9, cpy + 10):
            dd = abs(y - cpy)
            czx = Hs['cz']
            for z in range(czx - 7, czx + 8):
                if dd * dd + (z - czx) ** 2 <= (Hs['r_out'] + 1.4) ** 2 and not cv.solid[x, y, z]:
                    put(cv, x, y, z, 'coupling')
    band = d <= Hs['r_out'] + 2
    cv.keep[x0:x1 + 1, y0:y1 + 1][band] |= KEEP['hose']
    # crossings (walk under arches, walk over ruts, walk through the split) for sf_checks
    cr = []
    for (a, b), lift in Hs['arches']:
        cr.append({'kind': 'arch (walk under)', 'x': [a, b]})
    for (a, b) in Hs['ruts']:
        cr.append({'kind': 'rut (walk over)', 'x': [a, b]})
    cr.append({'kind': 'split (walk through)', 'x': [sx0 + 3, sx1 - 3]})
    rep['hose'] = {'crossings': cr, 'top_rest_z': int(Hs['cz'] - Hs['r_out']),
                   'arch_top_z': [int(Hs['cz'] - Hs['r_out'] - lift) for _, lift in Hs['arches']],
                   'voxels': int(tube.sum())}


def edging(cv, rep, S):
    E = S['edging']
    x = E['x'][0]
    n = 0
    while x <= E['x'][1] - 1:
        xb = min(x + E['brick_len'] - 1, 255)
        box(cv, x, xb, E['y'][0], E['y'][1], E['top_z'], 57, 'brick')
        # frog (shallow recess) on top, as on a real brick
        if xb - x > 12:
            cv.carve(x + 4, xb - 4, E['y'][0] + 3, E['y'][1] - 3, E['top_z'], E['top_z'])
        n += 1
        x += E['brick_len'] + E['gap']
    cv.no_prop(E['x'][0], 255, E['y'][0] - 2, E['y'][1] + 2, KEEP['hose'])
    rep['edging'] = {'bricks_west': n}


# =============================================================================================== ant nest

def carve_tube(cv, pts, half, floor, air, skip=None):
    """Tunnel along a polyline: 2*half+1 wide, `air` voxels of air over floor `floor` (floor made solid)."""
    cells = set()
    for (a, b) in zip(pts, pts[1:]):
        for (x, y, _) in line_points(a[0], a[1], 0, b[0], b[1], 0):
            for dx in range(-half, half + 1):
                for dy in range(-half, half + 1):
                    cells.add((x + dx, y + dy))
    for (x, y) in sorted(cells):
        if skip is not None and skip(x, y):
            continue
        cv.carve(x, x, y, y, floor - air, floor - 1)
        if not cv.solid[x, y, floor]:
            box(cv, x, x, y, y, floor, 63, 'tunnel')
        cv.rgb[x, y, floor] = GC['tunnel']
        cv.mat[x, y, floor] = cv.material('tunnel')
    return cells


def chamber(cv, cx, cy, rx, ry, floor, air_lo, air_hi, x_max=511):
    for x in range(cx - rx, min(cx + rx, x_max) + 1):
        for y in range(cy - ry, cy + ry + 1):
            r2 = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            if r2 <= 1:
                ztop = air_hi + int(round((air_lo - air_hi) * r2))
                cv.carve(x, x, y, y, ztop, floor - 1)
                cv.rgb[x, y, floor] = GC['tunnel']
                cv.mat[x, y, floor] = cv.material('tunnel')


def nest(cv, rep, S):
    N = S['nest']
    Z = S['z']
    fl = Z['tunnel_floor']
    air = fl - Z['tunnel_air'][0]
    half = N['w'] // 2
    out = {'entrances': {}, 'chambers': {}, 'tunnel_cells': 0}
    for name, (cx, cy, rx, ry) in N['chambers'].items():
        chamber(cv, cx, cy, rx, ry, fl, Z['tunnel_air'][0], N['chamber_air_top'])
        out['chambers'][name] = [cx, cy, fl]
        cv.interiors.append([f'ant nest {name} chamber', cx, cy, fl])
    for pts in N['tunnels']:
        cells = carve_tube(cv, pts, half, fl, air)
        out['tunnel_cells'] += len(cells)
    # crater entrances: a ring mound (rim 3, 1-per-column slopes) round the crater floor, and a straight ramp
    # (1 down per column, `ramp` columns) from the crater floor to the tunnel junction
    R = N['crater']
    for name, (jx, jy) in N['entrances'].items():
        dx, dy = N['ramp_dir'][name]
        L = fl - S['z']['lawn']
        px, py = jx + dx * (L + 1), jy + dy * (L + 1)
        g = S['z']['lawn']
        # level the crater floor
        for x in range(px - R['r_out'] - 1, px + R['r_out'] + 2):
            for y in range(py - R['r_out'] - 1, py + R['r_out'] + 2):
                rr = math.hypot(x - px, y - py)
                if rr <= R['r_out'] + 0.5:
                    t = top(cv, x, y)
                    if t < g:
                        cv.carve(x, x, y, y, t, g - 1)
                    elif t > g:
                        box(cv, x, x, y, y, g, t - 1, 'crater')
                    hh = int(max(0, R['rim'] - abs(rr - R['r_peak'])))
                    if hh > 0:
                        box(cv, x, x, y, y, g - hh, g - 1, 'crater')
                    else:
                        cv.rgb[x, y, g] = GC['crater']
                        cv.mat[x, y, g] = cv.material('crater')
        # ramp: from (px, py) at floor g to the junction at floor fl, `half` wide on each side
        for i in range(L + 2):
            cxr, cyr = px - dx * i, py - dy * i
            f = min(g + i, fl)
            for k in range(-half, half + 1):
                x, y = (cxr + k, cyr) if dx == 0 else (cxr, cyr + k)
                cv.carve(x, x, y, y, f - air, f - 1)
                if not cv.solid[x, y, f]:
                    box(cv, x, x, y, y, f, 63, 'tunnel')
                cv.rgb[x, y, f] = GC['tunnel']
                cv.mat[x, y, f] = cv.material('tunnel')
        cv.no_prop(px - R['r_out'] - 2, px + R['r_out'] + 2, py - R['r_out'] - 2, py + R['r_out'] + 2, KEEP['nest'])
        out['entrances'][name] = {'crater': [px, py, g], 'junction': [jx, jy, fl]}
        feature(rep, f'nest entrance {name}', 'crater', px, py, R['r_out'])
    rep['nest'] = out


# =============================================================================================== lawn props

def _blade(cv, rng, bx, by, bz, ang, Hb, lean, rep, stats):
    """One grass blade: a face-connected spine curving outward (offset = lean * (h/Hb)^2); a cross-section stamp
    3x2 at the base, 2x2, 2x1, then 1x1 at the tip (<= 10 % of the height). Stops at no-prop zones and z 4."""
    ox, oy = math.cos(ang), math.sin(ang)
    along_x = abs(ox) >= abs(oy)
    prev = None
    nvox = 0
    vox = []                                  # (x, y, z, f, a, b, w) per placed voxel: read by the art pass only
    keep_stop = KEEP['spawn'] | KEEP['front'] | KEEP['anchor'] | KEEP['hose'] | KEEP['axis']
    for hh in range(0, Hb + 1):
        off = lean * (hh / Hb) ** 2
        p = (int(round(bx + ox * off)), int(round(by + oy * off)), int(bz - hh))
        if not (4 <= p[0] < 508 and 4 <= p[1] < 508) or p[2] < 4 or (cv.keep[p[0], p[1]] & keep_stop):
            stats['truncated'] += 1
            break
        pts = [p] if prev is None else line_points(*prev, *p)[1:]
        prev = p
        f = hh / Hb
        w, t = (3, 2) if f < 0.4 else (2, 2) if f < 0.7 else (2, 1) if f < 0.9 else (1, 1)
        for (x, y, z) in pts:
            ws = range(-(w // 2), w - w // 2)
            ts = range(0, t)
            for a in ws:
                for b in ts:
                    xx, yy = (x + b, y + a) if along_x else (x + a, y + b)
                    if 0 <= xx < 512 and 0 <= yy < 512 and not (cv.keep[xx, yy] & keep_stop):
                        if not cv.solid[xx, yy, z] or cv.mat[xx, yy, z] in stats['own']:
                            put(cv, xx, yy, z, 'blade')
                            nvox += 1
                            vox.append((int(xx), int(yy), int(z), round(f, 3), a, b, w))
    stats['blades'] += 1
    stats['base_w'] = min(stats['base_w'], 3)
    rep.setdefault('blade_records', []).append({'tussock': stats.get('cur'), 'base': (float(bx), float(by), int(bz)),
                                                'Hb': int(Hb), 'ang': float(ang), 'vox': vox})
    return nvox


def tussock(cv, rep, name, cx, cy, R, rng, stats):
    """Clump of 5-9 tapered, curved blades (2-3 thick at the base, 25-40 tall) out of a thatch crown mound."""
    g = top(cv, cx, cy)
    rc = max(3, int(round(0.38 * R)))
    hc = 4 + (1 if R >= 12 else 0)
    crown_top = {}
    for x in range(cx - rc - 1, cx + rc + 2):
        for y in range(cy - rc - 1, cy + rc + 2):
            rr = math.hypot(x - cx, y - cy) / (rc + 0.3)
            if rr <= 1:
                zt = g - int(round(hc * math.sqrt(max(0.0, 1 - rr * rr))))
                if zt < g:
                    gl = top(cv, x, y)
                    box(cv, x, x, y, y, zt, max(zt, gl - 1), 'crown')
                    crown_top[(x, y)] = zt
    stats['own'] = {cv.material('crown'), cv.material('blade')}
    stats['cur'] = name
    n = int(rng.integers(5, 10))
    hmax = int(min(40, 22 + R * 1.3))
    for k in range(n):
        a = 2 * math.pi * k / n + rng.normal(0, 0.3)
        br = 0.45 * rc
        bx, by = cx + br * math.cos(a), cy + br * math.sin(a)
        bz = crown_top.get((int(round(bx)), int(round(by))), g - 1) + 1
        Hb = int(rng.integers(25, max(26, hmax + 1)))
        lean = R * rng.uniform(0.55, 0.95)
        _blade(cv, rng, bx, by, bz, a + rng.normal(0, 0.25), Hb, lean, rep, stats)
    feature(rep, name, 'tussock', cx, cy, rc + 1, R, g=g, rc=rc, hc=hc)


def clover(cv, rep, name, cx, cy, R, low=False, rot=0.0):
    """Stalked trefoil: a 2x2 stalk and three cupped leaflets (12-18 tall: walk under; low: 6-8)."""
    g = top(cv, cx, cy)
    hgt = 7 if low else int(round(10 + R * 0.75))
    for z in range(g - hgt, g):
        box(cv, cx, cx + 1, cy, cy + 1, z, z, 'stalk')
    zc = g - hgt
    rl = 0.55 * R
    for k in range(3):
        a = rot + k * 2 * math.pi / 3
        lx, ly = cx + 0.5 + 0.5 * R * math.cos(a), cy + 0.5 + 0.5 * R * math.sin(a)
        for x in range(int(lx - rl - 1), int(lx + rl + 2)):
            for y in range(int(ly - rl - 1), int(ly + rl + 2)):
                rr = math.hypot(x + 0.5 - lx, y + 0.5 - ly) / rl
                # heart notch at the outer tip
                tip = math.hypot(x + 0.5 - (lx + 0.8 * rl * math.cos(a)), y + 0.5 - (ly + 0.8 * rl * math.sin(a)))
                if rr <= 1 and tip > 0.35 * rl:
                    put(cv, x, y, zc, 'clover')
                    if rr > 0.7:
                        put(cv, x, y, zc - 1, 'clover')
    # connect leaflets to the stalk top (the stalk top voxel is inside the leaflet union)
    box(cv, cx - 1, cx + 2, cy - 1, cy + 2, zc, zc, 'clover')
    feature(rep, name, 'clover_low' if low else 'clover', cx, cy, 1.5, R, g=g, zc=zc, rot=rot, R=R, hgt=hgt)
    return hgt + 1


def dandelion(cv, rep, name, cx, cy, R, rng):
    g = top(cv, cx, cy)
    hgt = 30 + int(rng.integers(0, 5))
    for z in range(g - hgt, g):
        for a in range(3):
            for b in range(3):
                if not (a == 1 and b == 1):
                    put(cv, cx + a, cy + b, z, 'dandelion_stalk')
    Rg = R + 1
    gx, gy, gz = cx + 1.0, cy + 1.0, g - hgt - Rg + 1
    for x in range(int(gx - Rg - 1), int(gx + Rg + 2)):
        for y in range(int(gy - Rg - 1), int(gy + Rg + 2)):
            for z in range(int(gz - Rg - 1), int(gz + Rg + 2)):
                dd = math.sqrt((x - gx) ** 2 + (y - gy) ** 2 + (z - gz) ** 2)
                if Rg - 1.3 < dd <= Rg:
                    put(cv, x, y, z, 'seedhead')
    # receptacle where the stalk enters the globe
    box(cv, cx, cx + 2, cy, cy + 2, int(gz + Rg - 2), g - hgt, 'dandelion_stalk')
    feature(rep, name, 'dandelion', cx + 1, cy + 1, 2, Rg, g=g, hgt=hgt, gz=gz, Rg=Rg)


def pebble(cv, rep, name, cx, cy, R, h=None, mat='pebble', salt=0):
    """Stepped boulder: one layer per voxel of height, radius shrinking ~1 per layer (climbable terraces)."""
    g = top(cv, cx, cy)
    h = h or max(3, int(round(R * 0.85)))
    phi = noise.hash3(cx, cy, salt) * 2 * math.pi
    for k in range(h):
        rk = R - k * (R - 1.5) / max(h - 1, 1)
        z = g - 1 - k
        for x in range(int(cx - R - 2), int(cx + R + 3)):
            for y in range(int(cy - R - 2), int(cy + R + 3)):
                th = math.atan2(y - cy, x - cx)
                rr = math.hypot(x - cx, y - cy) / (rk * (1 + 0.12 * math.cos(2 * th + phi)))
                if rr <= 1:
                    if k == 0:
                        col_down(cv, x, y, z, mat)
                    else:
                        put(cv, x, y, z, mat)
    feature(rep, name, 'pebble', cx, cy, R, R, g=g, h=h)
    return h


def mushroom(cv, rep, name, cx, cy, R):
    g = top(cv, cx, cy)
    hgt = 8 + R // 3
    for x in range(cx - 2, cx + 3):
        for y in range(cy - 2, cy + 3):
            if math.hypot(x - cx, y - cy) <= 2.3:
                for z in range(g - hgt, g):
                    put(cv, x, y, z, 'mushroom_stem')
    for x in range(cx - R - 1, cx + R + 2):
        for y in range(cy - R - 1, cy + R + 2):
            rr = math.hypot(x - cx, y - cy) / R
            if rr <= 1:
                zt = g - hgt - int(round(3 * (1 - rr * rr)))
                zb = g - hgt + (1 if rr > 0.78 else 0)
                box(cv, x, x, y, y, zt, zb, 'mushroom_cap')
    feature(rep, name, 'mushroom', cx, cy, 3, R, g=g, hgt=hgt, R=R)


def acorn(cv, rep, name, cx, cy, R):
    g = top(cv, cx, cy)
    rz = R * 1.0
    zc = g - rz + 0.6
    cv.ellipsoid(cx, cy, zc, R * 0.78, R * 0.78, rz, GC['acorn'], 'acorn')
    cv.ellipsoid(cx, cy, zc - rz * 0.62, R * 0.9, R * 0.9, R * 0.45, GC['acorn_cap'], 'acorn_cap')
    zt = int(math.floor(zc - rz * 0.62 - R * 0.45))
    box(cv, cx, cx + 1, cy, cy, zt - 2, zt + 1, 'twig')
    for x in range(cx - R, cx + R + 1):
        for y in range(cy - R, cy + R + 1):
            zs = np.nonzero(cv.solid[x, y, :g])[0]
            if len(zs) and cv.mat[x, y, zs[-1]] == cv.material('acorn'):
                col_down(cv, x, y, zs[-1] + 1, 'acorn')
    feature(rep, name, 'acorn', cx, cy, R * 0.8, R, g=g, zc=zc, R=R)


def twig(cv, rep, name, cx, cy, L, ang, stubs=2, r=2.8, hmax=3):
    """Lying twig, half sunk: a walk-over log (profile 1-2-3-2-1 high), with short side stubs."""
    ux, uy = math.cos(ang), math.sin(ang)
    ax0, ay0 = cx - ux * L, cy - uy * L
    for x in range(int(cx - L - 4), int(cx + L + 5)):
        for y in range(int(cy - L - 4), int(cy + L + 5)):
            t = ((x - ax0) * ux + (y - ay0) * uy) / (2 * L)
            if not 0 <= t <= 1:
                continue
            d = abs(-(x - ax0) * uy + (y - ay0) * ux)
            if d <= r:
                hh = int(round(hmax * math.sqrt(max(0.0, 1 - (d / r) ** 2))))
                if hh >= 1:
                    g = top(cv, x, y)
                    box(cv, x, x, y, y, g - hh, g - 1, 'twig')
    for k in range(stubs):
        t = 0.3 + 0.4 * k
        sx, sy = ax0 + ux * 2 * L * t, ay0 + uy * 2 * L * t
        side = 1 if k % 2 == 0 else -1
        ex, ey = sx + (-uy * side + ux * 0.6) * 6, sy + (ux * side + uy * 0.6) * 6
        g = int(cv.H[int(sx), int(sy)])
        for (x, y, z) in line_points(sx, sy, g - 2, ex, ey, g - 2):
            for xx, yy in ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)):
                col_down(cv, xx, yy, z, 'twig')
    feature(rep, name, 'twig', cx, cy, 0, L, ang=ang, L=L, r=r)


def leaf(cv, rep, name, cx, cy, R, ang):
    """Curled fallen leaf: one edge on the soil, the sheet rising to a curled edge R*0.8 high (lean-to shelter)."""
    ux, uy = math.cos(ang), math.sin(ang)
    Wh = 0.6 * R
    hmax = 0.8 * R
    hs = {}
    for x in range(int(cx - R - 2), int(cx + R + 3)):
        for y in range(int(cy - R - 2), int(cy + R + 3)):
            u = (x - cx) * ux + (y - cy) * uy
            v = -(x - cx) * uy + (y - cy) * ux
            if abs(u) > R:
                continue
            wv = Wh * math.sqrt(max(0.0, 1 - (u / R) ** 2))
            if wv < 1 or abs(v) > wv:
                continue
            s = (v / wv + 1) / 2
            hs[(x, y)] = int(round(hmax * s ** 1.7 * (0.6 + 0.4 * math.sqrt(max(0.0, 1 - (u / R) ** 2)))))
    dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))
    zs = {}
    for (x, y), hh in hs.items():
        g = int(cv.H[x, y])                                    # terrain top (not raised by earlier leaf voxels)
        zs[(x, y)] = g - max(hh, 1)
    for (x, y), zt in zs.items():
        # face contact only with in-leaf neighbours: each column reaches down to its lowest neighbour's sheet
        # voxel (same z, face to face); the curled edge stays up, so the shelter is open on that side
        nbz = [(zs[(x + a, y + b)], a, b) for a, b in dirs if (x + a, y + b) in zs]
        zb = max([zt] + [v[0] for v in nbz])
        box(cv, x, x, y, y, zt, zb, 'leaf')
        if zb - zt >= 3:                                       # tall curl strip: 2 thick (no 1x1 vertical runs)
            _, a, b = max(nbz)
            box(cv, x + a, x + a, y + b, y + b, zt + 1, zb, 'leaf')
    feature(rep, name, 'leaf', cx, cy, R * 0.6, R, ang=ang, R=R)


def bottle_cap(cv, rep, name, cx, cy, R, open_axis='x', x_max=511):
    """Bottle cap bunker, open side up: floor 1 above the soil, rim 3 tall (crimped), two 3-wide gaps."""
    g = top(cv, cx, cy)
    for x in range(cx - R - 2, min(cx + R + 2, x_max) + 1):
        for y in range(cy - R - 2, cy + R + 3):
            rr = math.hypot(x - cx, y - cy)
            th = math.atan2(y - cy, x - cx)
            crimp = 0.8 if (int((th + math.pi) / (2 * math.pi) * 24) % 2 == 0) else 0.0
            if rr <= R + crimp:
                gl = top(cv, x, y)
                box(cv, x, x, y, y, g - 1, max(g - 1, gl - 1), 'cap_inner' if rr < R - 1.6 else 'cap')
                if rr >= R - 1.6:
                    box(cv, x, x, y, y, g - 3, g - 2, 'cap')
    for s in (-1, 1):
        if open_axis == 'x':
            xa, xb = (cx - R - 2, cx - R + 2) if s < 0 else (cx + R - 2, min(cx + R + 2, x_max))
            if xa <= xb:
                cv.carve(xa, xb, cy - 1, cy + 1, g - 3, g - 2)
        else:
            ya, yb = (cy - R - 2, cy - R + 2) if s < 0 else (cy + R - 2, cy + R + 2)
            cv.carve(cx - 1, min(cx + 1, x_max), ya, yb, g - 3, g - 2)
    feature(rep, name, 'cap', cx, cy, R, R, g=g, R=R)


def pinecone(cv, rep, name, cx, cy, R):
    """Upright pinecone: scale whorls 1 voxel per layer (radius shrinking 1 per layer: climbable), 2x2 tip."""
    g = top(cv, cx, cy)
    for k in range(R):
        rk = R - k
        z = g - 1 - k
        for x in range(cx - R - 2, cx + R + 3):
            for y in range(cy - R - 2, cy + R + 3):
                th = math.atan2(y - cy, x - cx)
                rr = math.hypot(x - cx, y - cy) / (rk * (1 + 0.1 * math.cos(6 * th + 0.9 * k)))
                if rr <= 1:
                    if k == 0:
                        col_down(cv, x, y, z, 'pinecone')
                    else:
                        put(cv, x, y, z, 'pinecone_dk' if (k % 2 and rr > 0.6) else 'pinecone')
    zt = g - 1 - R
    box(cv, cx, cx + 1, cy, cy + 1, zt - 1, zt, 'pinecone')
    put(cv, cx, cy, zt - 2, 'pinecone')
    feature(rep, name, 'pinecone', cx, cy, R, R, g=g, R=R)


# ---------------------------------------------------------------- front dressing (<= 10 tall, ~25-40 cells each)

def front_prop(cv, rep, kind, x, y, i):
    g = top(cv, x, y)
    if kind == 'pebble_low':
        pebble(cv, rep, f'front {kind} {i}', x, y, 4, 3, salt=i)
        return
    if kind == 'daisy':
        for z in range(g - 7, g):
            box(cv, x, x + 1, y, y + 1, z, z, 'stalk')
        for xx in range(x - 3, x + 5):
            for yy in range(y - 3, y + 5):
                rr = math.hypot(xx - x - 0.5, yy - y - 0.5)
                if rr <= 3.6:
                    put(cv, xx, yy, g - 7, 'daisy_eye' if rr <= 1.2 else 'daisy')
        box(cv, x, x + 1, y, y + 1, g - 8, g - 8, 'daisy_eye')
    elif kind == 'twiglet':
        twig(cv, rep, f'front twiglet {i}', x, y, 7, 0.35, stubs=1, r=1.8, hmax=2)
    elif kind == 'seed':
        cv.ellipsoid(x, y, g - 1.2, 4.5, 2.4, 1.8, GC['seed'], 'seed')
    elif kind == 'clover_low':
        clover(cv, rep, f'front clover {i}', x, y, 4, low=True, rot=0.4 * i)
        return
    elif kind == 'dewdrop':
        cv.ellipsoid(x, y, g, 3.4, 3.4, 3.2, GC['dew'], 'dew')
    elif kind == 'sprout':
        for z in range(g - 6, g):
            box(cv, x, x + 1, y, y + 1, z, z, 'sprout')
        for s in (-1, 1):
            cv.ellipsoid(x + 0.5 + s * 3.0, y + 0.5, g - 6.5, 3.0, 1.8, 1.0, GC['sprout'], 'sprout')
    feature(rep, f'front {kind} {i}', 'front', x, y, 3, sub=kind, g=g)


# =============================================================================================== west-half build

def build_west(S, seed):
    cv = Canvas(S['name'])
    for k in GC:
        cv.material(k)
    rep = {'west_seed': seed}
    terrain(cv, rep, S, seed)
    # axis reserve (sprinkler legs and collar, feeder, trowel) so west props keep clear of the axis objects
    sp = S['sprinkler']
    hx, hy = sp['hub']
    X, Y = np.meshgrid(np.arange(512, dtype=float), np.arange(512, dtype=float), indexing='ij')
    res = np.hypot(X - hx, Y - hy) <= sp['collar_r'] + 4
    for (fx, fy) in sp['feet'].values():
        d, _, _ = polyline_field([(fx, fy), (hx, hy)], X, Y)
        res |= d <= sp['leg_w'] / 2 + 4
    fd = S['hose']['feeder']
    res |= (np.abs(X - 256) <= 10) & (Y >= fd['path'][0][1] - 8) & (Y <= fd['path'][-1][1] + 4)
    tw = S['trowel']
    res |= (np.abs(X - 256) <= tw['heap'][2] + 3) & (Y >= tw['cap']['c'][1] - 6) & \
        (Y <= tw['heap'][1] + tw['heap'][3] + 4)
    res |= (np.abs(X - 256) <= 8) & (Y >= tw['cap']['c'][1] - 6)
    cv.keep[res] |= KEEP['axis']
    for (x0, x1, y0, y1) in S['oneoff_sites'].values():         # one-off sites and their mirrors stay prop-free
        for (a, b) in ((x0, x1), (512 - x1, 512 - x0)):
            cv.no_prop(max(0, a - 1), min(511, b + 1), y0 - 1, y1 + 1, KEEP['axis'])
    nest(cv, rep, S)
    garden_hose(cv, rep, S)
    edging(cv, rep, S)
    rng = noise.rng('props', seed)
    stats = {'blades': 0, 'truncated': 0, 'base_w': 9, 'own': set()}
    bad = []
    for i, (x, y, R) in enumerate(S['tussocks']):
        if cv.keep[x, y] & (KEEP['spawn'] | KEEP['front'] | KEEP['anchor'] | KEEP['hose'] | KEEP['axis']):
            bad.append(('tussock', x, y, int(cv.keep[x, y])))
        tussock(cv, rep, f'tussock {i}', x, y, R, noise.rng(f'tussock{i}', seed), stats)
    stats.pop('own', None)
    stats.pop('cur', None)
    rep['blades'] = stats
    for i, (kind, x, y, R) in enumerate(S['centre_props']):
        if cv.keep[x, y] & (KEEP['spawn'] | KEEP['front'] | KEEP['anchor'] | KEEP['hose'] | KEEP['axis']):
            bad.append((kind, x, y, int(cv.keep[x, y])))
        nm = f'{kind} {i}'
        r_ = noise.rng(f'prop{i}', seed)
        if kind == 'pebble':
            pebble(cv, rep, nm, x, y, R, salt=i)
        elif kind == 'clover':
            clover(cv, rep, nm, x, y, R, rot=float(r_.uniform(0, 2 * math.pi)))
        elif kind == 'mushroom':
            mushroom(cv, rep, nm, x, y, R)
        elif kind == 'dandelion':
            dandelion(cv, rep, nm, x, y, R, r_)
        elif kind == 'acorn':
            acorn(cv, rep, nm, x, y, R)
        elif kind == 'twig':
            twig(cv, rep, nm, x, y, R, S['twig_angle'].get(f'{x},{y}', 0.0))
        elif kind == 'leaf':
            leaf(cv, rep, nm, x, y, R, float(r_.uniform(0, 2 * math.pi)))
        elif kind == 'cap':
            bottle_cap(cv, rep, nm, x, y, R)
        elif kind == 'pinecone':
            pinecone(cv, rep, nm, x, y, R)
    for i, (kind, x, y) in enumerate(S['front_props']):
        front_prop(cv, rep, kind, x, y, i)
    for i, (x, y, R) in enumerate(S['spawn_cover']):
        pebble(cv, rep, f'spawn cover {i}', x, y, R, salt=100 + i)
    for i, (kind, x, y, R) in enumerate(S['under_platform']):
        if x >= 256 or kind == 'puddle':
            continue                                      # axis pieces in sf_axis; puddles are terrain
        nm = f'under-platform {kind} {i}'
        if kind == 'pebble':
            pebble(cv, rep, nm, x, y, R, salt=200 + i)
        elif kind == 'clover_low':
            clover(cv, rep, nm, x, y, R, low=True, rot=0.9)
    rep['keep_violations'] = bad
    rep['tight_pairs'] = tight_pairs(rep.get('features', []), S['min_gap'])
    return cv, rep


def tight_pairs(feats, min_gap):
    """Walking-footprint gaps between centre/periphery features below min_gap (reported, never silently fixed)."""
    out = []
    F = [f for f in feats if f['r_walk'] > 0]
    for i in range(len(F)):
        for j in range(i + 1, len(F)):
            a, b = F[i], F[j]
            gap = math.hypot(a['x'] - b['x'], a['y'] - b['y']) - a['r_walk'] - b['r_walk']
            if gap < min_gap:
                out.append({'a': a['name'], 'b': b['name'], 'gap': round(gap, 1)})
    return out
