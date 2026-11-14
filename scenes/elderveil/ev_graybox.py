"""Elderveil graybox v1: gameplay geometry only (flat function colours per material, no art pass).

Order: terrain heights (relief, flats, outpost, plaza / amphitheatre bowls, aqueduct corridor, stream + pool,
cliff ring with spurs and coves) -> fill_terrain -> structures (west half + axis objects written symmetric about
x = 256) -> props, pinned cover trees -> seeded vegetation stand-ins -> nook fill, trap clearing, flat breaking ->
[ev_main: orphan report -> mirror x512]. Every number comes from ev_spec.SPEC; every random choice comes from
aosmap.kit.noise (crc32 seeds). The layout seed is fixed; the veg seed (OS seed per build, saved) only places
vegetation stand-ins. Every room, floor, deck and landing is recorded in cv.interiors.
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..'))
from aosmap.kit import Canvas, noise, structures  # noqa: E402
from aosmap.kit.canvas import poly_mask  # noqa: E402
from aosmap.kit.structures import straight_stair  # noqa: E402

from ev_spec import SPEC  # noqa: E402

# flat graybox colours per material (floors luma >= 40, max channel <= 212)
C = {
    'ground': (92, 118, 78), 'paving': (150, 146, 136), 'rock': (104, 102, 110), 'shelf': (128, 122, 108),
    'water': (60, 96, 120), 'dirt': (120, 104, 82), 'mosaic': (166, 150, 120),
    'ruin': (186, 180, 168), 'stone': (160, 156, 148), 'building': (176, 168, 150), 'roof': (110, 84, 70),
    'floor': (124, 98, 72), 'stair': (198, 170, 120), 'root': (112, 86, 62), 'prop': (178, 126, 66),
    'veg': (54, 104, 64), 'trunk': (98, 74, 54), 'furn': (102, 80, 58), 'tent': (150, 130, 96),
    'fern': (70, 130, 70), 'mushroom': (170, 120, 150), 'stem': (190, 184, 160), 'rune': (90, 170, 180),
    'spire': (196, 192, 180), 'pad': (204, 206, 196),
}
GROUND_KEYS = ['ground', 'paving', 'rock', 'shelf', 'water', 'dirt', 'mosaic']   # region codes 0..6
X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
XW = np.minimum(X, 512 - X)

KEEP_SPAWN, KEEP_ANCHOR, KEEP_FRONT, KEEP_UNDER, KEEP_LANE, KEEP_STRUCT, KEEP_MISC = 1, 2, 4, 8, 16, 32, 64


def _box(xr, yr):
    m = np.zeros((512, 512), bool)
    m[max(0, xr[0]):min(511, xr[1]) + 1, max(0, yr[0]):min(511, yr[1]) + 1] = True
    return m


def _wbox(xr, yr):
    """A west box and its mirror."""
    return _box(xr, yr) | _box((512 - xr[1], 512 - xr[0]), yr)


def _row(tag, seed, cell, octaves=2):
    return noise.fbm2((512, 8), cell, octaves, tag, seed)[:, 0]


def ellipse_val(c, r, tag, seed, edge_noise):
    """Normalised elliptic distance (symmetric about x = 256) with smooth noise on the outline."""
    cx, cy = c
    v = np.sqrt(((XW - cx) / r[0]) ** 2 + ((Y - cy) / r[1]) ** 2)
    return v + edge_noise * (_sym(noise.fbm2((512, 512), 14, 2, tag, seed)) - 0.5) * 2


def _sym(a):
    """West half copied onto the east half (x512), so noise-driven outlines come out mirror-exact."""
    a = a.copy()
    a[257:] = a[255:0:-1]
    a[256] = a[255]
    return a


# =============================================================================================== masks

def outpost_mask(S=SPEC):
    return _sym(poly_mask(S['outpost']['poly']))


def _mirror_mask(m):
    out = np.zeros_like(m)
    out[257:] = m[255:0:-1]
    out[256] = m[255]
    return out


def plaza_val(S=SPEC):
    p = S['plaza']
    return ellipse_val(p['c'], p['r'], 'plaza_edge', S['layout_seed'], p['edge_noise'])


def amphi_val(S=SPEC):
    a = S['amphi']
    return ellipse_val(a['c'], a['r'], 'amphi_edge', S['layout_seed'], a['edge_noise'])


def stream_line(S=SPEC):
    """Stream centre y_c(x) and water half width wh(x) (symmetric about x = 256, a pool on the axis)."""
    st = S['stream']
    xs = np.arange(512)
    u = 256 - np.minimum(xs, 512 - xs)
    yc = st['y_c'] + st['amp'] * np.sin(math.pi * u / st['period']) * (1 - np.exp(-(u / st['axis_flat']) ** 2))
    w0, a1, a2 = st['wh']
    wh = np.clip(w0 + a1 * np.sin(u / 13.0) + a2 * np.sin(u / 7.0 + 1.0), *st['wh_clamp'])
    pl = st['pool']
    g = np.exp(-(u / pl['L']) ** 2)
    yc = yc * (1 - g) + pl['c'][1] * g
    wh = wh * (1 - g) + pl['wh'] * g
    return yc, wh


# =============================================================================================== terrain

def _ring_profile(d, W, pk, rug, ter, R, Z, tj=0.0):
    u = d / W
    ft = R['face_top']
    face = pk + (ft - pk) * (u - R['peak_u']) / (R['face_u'] - R['peak_u'])
    face = face + rug * np.clip((u - R['peak_u']) * 4, 0, 1)
    step = R['terrace_step']
    face = np.where(ter, np.floor((face + tj) / step) * step + 2, face)          # jittered: not a stair
    foot = ft + (Z['ring_foot'] - ft) * (u - R['face_u']) / (1 - R['face_u'])
    h = np.where(u <= R['peak_u'], pk, np.where(u <= R['face_u'], face, foot))
    return np.where(u <= 1.0, h, 99.0), u


def fill_basins(H, region):
    """Priority-flood depression fill inside `region` (the cliff ring): every cell gets a path to the outside of
    the region that never climbs (terrace pockets you can drop into but not climb out of are filled to their
    spill level). Heights are floor z (smaller = higher)."""
    import heapq
    elev = (63 - H).astype(int)
    done = ~region.copy()
    heap = []
    edge = region & (ndi.binary_dilation(~region) )
    for x, y in zip(*np.nonzero(edge)):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < 512 and 0 <= ny < 512 and not region[nx, ny]:
                heapq.heappush(heap, (int(elev[nx, ny]), int(nx), int(ny)))
    while heap:
        e, x, y = heapq.heappop(heap)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < 512 and 0 <= ny < 512 and not done[nx, ny]:
                done[nx, ny] = True
                if elev[nx, ny] < e:
                    elev[nx, ny] = e
                heapq.heappush(heap, (int(elev[nx, ny]), nx, ny))
    return (63 - elev).astype(int)


def terrain(S=SPEC):
    """Height map H[x, y] (floor z), top-surface region codes and derived masks."""
    seed = S['layout_seed']
    Z = S['z']
    geo = {}
    rl = S['relief']
    r1 = noise.fbm2((512, 512), rl['cells'][0], 3, 'relief', seed)
    r2 = noise.fbm2((512, 512), rl['cells'][1], 2, 'relief2', seed)
    rel = (r1 - 0.5) * rl['amp'][0] + (r2 - 0.5) * rl['amp'][1]
    rel[257:] = rel[255:0:-1]
    rel[256] = rel[255]

    # ---------------------------------------------------------------- gameplay flats
    outp = outpost_mask(S)
    pv = plaza_val(S)
    plaza = pv < 1.0
    av = amphi_val(S)
    amphi = av < 1.0
    aq = S['aqueduct']
    aqm = (np.abs(Y - aqueduct_line(S)[X]) <= aq['half_w'] + 6) & (XW >= aq['x0'] - 4)
    f = S['front']
    front = _wbox(f['x'], f['y'])
    strip = _box((S['anchor']['x'][0], 312), S['anchor']['y'])
    lib = S['library']['box']
    libm = _box((lib[0] - 3, 512 - lib[0] + 3), (lib[2] - 3, lib[3] + 3)) | _wbox(
        (S['library']['wing'][0] - 3, 255), (S['library']['wing'][2] - 3, S['library']['wing'][3] + 3))
    sp = S['spire']
    spm = (np.hypot(XW + 0.5 - sp['c'][0], Y + 0.5 - sp['c'][1]) <= sp['r_stair'] + 4)
    qu = S['queen']
    queenm = _box((qu['ramp_x'][0] - 2, 512 - qu['ramp_x'][0] + 2), (qu['torso_y'][0], qu['legs_y'][1] + 2))
    rc = S['rune_circle']
    runem = np.hypot(XW - 256, Y - rc['c'][1]) <= rc['r'] + 4
    flats = outp | plaza | amphi | aqm | front | strip | libm | spm | queenm | runem
    dist = ndi.distance_transform_edt(~flats)
    rel_eff = np.clip(rel, *rl['clip']) * np.clip(dist / rl['fade'], 0, 1)
    H = (Z['valley'] - np.rint(rel_eff)).astype(int)
    region = np.zeros((512, 512), np.int8)

    # outpost courtyard 49 with gentle 48 mounds
    mound = noise.fbm2((512, 512), 11, 2, 'mounds', seed)
    mound[257:] = mound[255:0:-1]
    mound[256] = mound[255]
    thr = np.quantile(mound[outp], 1 - S['outpost']['mound_share'])
    # mounds stay >= 3 inside the outline and off the front band, so every breach and the spawn-front edge is a
    # 1-voxel step both ways (a 2-step at a breach made it one-way)
    inner = ndi.distance_transform_edt(outp & ~front) >= 3
    H[outp] = np.where((mound[outp] > thr) & inner[outp], Z['outpost_mound'], Z['outpost'])
    region[outp] = 5
    # front: +-1 drifts away from its edges, flat next to the anchors and the shrine
    H[front] = Z['valley']
    fin = _wbox((f['x'][0] + 8, f['x'][1] - 6), (f['y'][0] + 2, f['y'][1] - 2))
    fc = rl['front_clip']
    H[fin] = Z['valley'] - np.rint(np.clip(rel[fin] * 0.6, -fc, fc)).astype(int)
    for (kind, x, y, prm) in S['front_pieces']:
        if kind == 'shrine':
            H[_wbox((x - 1, x + 10), (y - 1, y + 9))] = Z['valley']
    H[strip] = Z['valley']                              # anchors + under-platform strip: flat 50
    region[strip & ~_wbox((200, 211), (0, 511))] = 6
    H[aqm] = Z['aqueduct_ground']
    H[libm | spm | queenm | runem] = Z['valley']
    region[libm] = 1
    # sunken plaza: wide steps (51, 52) round a floor at 53, following the noisy outline
    pdist = ndi.distance_transform_edt(plaza)
    s1, s2 = S['plaza']['steps']
    H[plaza] = np.where(pdist[plaza] <= s1, 51, np.where(pdist[plaza] <= s2, 52, Z['plaza']))
    region[plaza] = 1
    # amphitheatre: terraces 51 / 52 / 53 by normalised distance
    a = S['amphi']
    H[amphi] = Z['valley']
    for (lv, z) in sorted(a['levels'], key=lambda t: -t[0]):
        H[amphi & (av < lv)] = z
    region[amphi] = 1
    geo['plaza'], geo['amphi'], geo['outpost'] = plaza, amphi, outp

    # ---------------------------------------------------------------- stream + pool (south flank)
    st = S['stream']
    yc, wh = stream_line(S)
    YC, WH = yc[X], wh[X]
    ady = np.abs(Y - YC)
    shn = noise.fbm2((512, 512), 6, 2, 'shelf', seed)
    shn[257:] = shn[255:0:-1]
    shn[256] = shn[255]
    shelf = np.maximum(WH + st['shelf'] + (shn - 0.5) * 2 * st['shelf_noise'], WH + 0.6)
    bank = np.rint(Z['bank_low'] - (ady - shelf - 1) * (Z['bank_low'] - Z['valley']) / st['bank_w'])
    cz = np.where(ady <= WH, Z['water'], np.where(ady <= shelf, Z['shelf'],
                                                   np.where(ady <= shelf + 1, Z['bank_low'], bank))).astype(int)
    cm = ady <= shelf + 1 + st['bank_w'] + 6
    H[cm] = np.maximum(H[cm], cz[cm])
    region[cm & (cz >= 62)] = 3
    region[cm & (cz == 63)] = 4
    valley = cm & (cz > Z['valley'])
    geo['stream_yc'], geo['stream_wh'], geo['stream'] = yc, wh, valley
    # rune circle ground stays flat 50 even on the bank top
    H[runem] = np.minimum(H[runem], Z['valley'])

    # ---------------------------------------------------------------- cliff ring (spurs, coves, terraces)
    R = S['ring']
    wn = noise.fbm2((512, 512), R['w_cell'], 2, 'ringw', seed)
    Wbase = R['w'][0] + (R['w'][1] - R['w'][0]) * np.clip((wn - 0.3) / 0.4, 0, 1)
    pk = Z['ring_peak'][0] + (Z['ring_peak'][1] - Z['ring_peak'][0]) * noise.fbm2((512, 512), 16, 2, 'peaks', seed)
    rug = (noise.fbm2((512, 512), 6, 2, 'rugged', seed) - 0.5) * 2 * R['rugged']
    ter = noise.fbm2((512, 512), 20, 2, 'terrace', seed) > 0.52
    tj = (noise.fbm2((512, 512), 9, 2, 'terrace_jitter', seed) - 0.5) * R.get('terrace_jitter', 0.0)
    ringH = np.full((512, 512), 99.0)
    ring_u = np.full((512, 512), 9.0)
    for edge, d, along in (('N', Y.astype(float), XW), ('S', (511 - Y).astype(float), XW), ('W', XW.astype(float), Y)):
        W = Wbase.copy()
        for (e, c0, hw, ex) in R['bumps']:
            if e == edge:
                W = W + ex * np.exp(-((along - c0) / hw) ** 2)
        if S.get('v11'):                                     # buttress ribs and re-entrant gullies along the face
            rib = _row('ribs_' + edge, seed, R['v11']['rib_cell'], 2)
            W = W + (rib[np.clip(along, 0, 511).astype(int)] - 0.5) * 2 * R['v11']['rib_amp']
        h, u = _ring_profile(d, W, pk, rug, ter, R, Z, tj)
        ringH = np.minimum(ringH, h)
        ring_u = np.minimum(ring_u, u)
    for arr in (ringH, ring_u):
        arr[257:] = arr[255:0:-1]
        arr[256] = arr[255]
    protect = (flats & ~outp) | (outp & (XW >= 58)) | (valley & (XW >= 56))
    P = ndi.distance_transform_edt(~protect)
    ringH = np.maximum(ringH, Z['ring_foot'] - R['approach_slope'] * P)
    ringH = np.rint(ringH).astype(int)
    rm = ring_u <= 1.0
    H[rm] = np.minimum(H[rm], ringH[rm])
    geo['ring_u'] = ring_u

    # ---------------------------------------------------------------- safety: ring basins, ceiling, pits
    cr = S['sites']['crag']                                  # crag in the west foothills (the nest cave is dug in)
    v = np.sqrt(((XW - cr['c'][0]) / cr['r'][0]) ** 2 + ((Y - cr['c'][1]) / cr['r'][1]) ** 2)
    zc = np.rint(cr['top'] + (Z['valley'] - cr['top']) * v ** 4).astype(int)
    m = v <= 1.2
    H[m] = np.minimum(H[m], zc[m])
    if S.get('v11'):
        for (px, py, r, ztop) in R['v11']['pinnacles']:     # overhang-free pinnacles on the foothills
            dd = np.hypot(XW + 0.5 - px, Y + 0.5 - py)
            zp = np.rint(ztop + (dd / r) ** 2 * 6).astype(int)
            m = dd <= r * 2.2
            H[m] = np.minimum(H[m], zp[m])
        for (fx, fy, r, hgt) in R['v11']['fans']:             # rock-fall fans at the cliff foot (1-step slopes)
            dd = np.hypot(XW + 0.5 - fx, Y + 0.5 - fy)
            zf = np.rint(H + 0 * dd).astype(int)
            m = dd <= r
            cap = np.rint(Z['ring_foot'] - hgt * (1 - dd / r)).astype(int)
            H[m] = np.minimum(H[m], np.maximum(cap[m], H[m] - hgt))
            del zf
    if S.get('v11'):                                         # ribs can enclose valley pockets: fill under the ring
        H = fill_basins(H, (ring_u <= 1.15) & (H <= 62))
    H = fill_basins(H, (ring_u <= 1.0) & (H <= 47))
    if S.get('v11'):                                         # ledge pits: every way out is a climb >= 2 or a fall > 9
        for _ in range(20):
            nbs = np.stack([np.roll(H, 1, 0), np.roll(H, -1, 0), np.roll(H, 1, 1), np.roll(H, -1, 1)])
            ok = (np.abs(nbs - H[None]) <= 1) | ((nbs > H[None]) & (nbs - H[None] <= 9))
            hi = np.where(nbs < H[None] - 1, nbs, 99).min(0)
            pit = ~ok.any(0) & (hi < 99) & (H < 62)
            pit[:1] = pit[-1:] = False
            pit[:, :1] = pit[:, -1:] = False
            if not pit.any():
                break
            H[pit] = hi[pit] + 1
    H = np.maximum(H, Z['min_solid_z'] + 1)
    for _ in range(40):              # a column > 1 below all 4 neighbours is raised to the lowest one + 1
        nb = np.stack([np.roll(H, 1, 0), np.roll(H, -1, 0), np.roll(H, 1, 1), np.roll(H, -1, 1)]).max(0)
        pit = (H > nb + 1) & (H < 62)
        if not pit.any():
            break
        H[pit] = nb[pit] + 1
    region[(H < 61) & np.isin(region, [3, 4])] = 0          # stream ends buried under the ring
    geo['cascade'] = cut_cascade(H, region, S)
    region[(H <= 45) & (region == 0)] = 2
    region[(H <= 45) & (region == 5)] = 2
    geo['flats'] = flats
    return H.astype(int), region, geo


def paint_terrain(cv, H, region):
    def colour(xs, ys, zs):
        top = zs == H[xs, ys]
        out = np.empty((len(xs), 3), np.uint8)
        out[:] = C['dirt']
        out[(zs > H[xs, ys] + 3) | (H[xs, ys] <= 45)] = C['rock']
        for k, key in enumerate(GROUND_KEYS):
            out[top & (region[xs, ys] == k)] = C[key]
        return out
    cv.fill_terrain(H, colour, 'ground')
    xs, ys = np.nonzero(np.ones((512, 512), bool))
    zs = H[xs, ys]
    mats = np.array([cv.material(k) for k in GROUND_KEYS], np.uint16)
    cv.mat[xs, ys, zs] = mats[region[xs, ys]]


# =============================================================================================== helpers

C['timber'] = (132, 98, 66)


def gbox(cv, x0, x1, y0, y1, h, c, mat='prop'):
    """Box standing on the terrain column by column: h voxels tall from each column's surface (z H-h..H-1)."""
    for x in range(max(0, x0), min(511, x1) + 1):
        for y in range(max(0, y0), min(511, y1) + 1):
            g = int(cv.H[x, y])
            cv.box(x, x, y, y, g - h, g - 1, c, mat)


def gcells(cv, cells, h, c, mat='prop'):
    """Columns (x, y) h tall above their terrain surface."""
    for (x, y) in cells:
        if 0 <= x < 512 and 0 <= y < 512:
            g = int(cv.H[x, y])
            cv.box(x, x, y, y, g - h, g - 1, c, mat)


def ell_cells(cx, cy, rx, ry, ang=0.0):
    """Cells of a (rotated) ellipse footprint (centre in cell-centre coordinates)."""
    out = []
    R = int(math.ceil(max(rx, ry))) + 1
    ca, sa = math.cos(ang), math.sin(ang)
    for x in range(int(cx) - R, int(cx) + R + 2):
        for y in range(int(cy) - R, int(cy) + R + 2):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            u, v = dx * ca + dy * sa, -dx * sa + dy * ca
            if rx > 0 and ry > 0 and (u / rx) ** 2 + (v / ry) ** 2 <= 1.0:
                out.append((x, y))
    return out


def seg_cells(a, b, w):
    """Cells within w/2 of the segment a-b (cell centres)."""
    (ax, ay), (bx, by) = a, b
    x0, x1 = int(min(ax, bx) - w), int(max(ax, bx) + w) + 1
    y0, y1 = int(min(ay, by) - w), int(max(ay, by) + w) + 1
    dx, dy = bx - ax, by - ay
    L2 = float(dx * dx + dy * dy) or 1.0
    out = []
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            px, py = x + 0.5, y + 0.5
            t = min(1.0, max(0.0, ((px - ax) * dx + (py - ay) * dy) / L2))
            if math.hypot(px - (ax + t * dx), py - (ay + t * dy)) <= w / 2.0:
                out.append((x, y))
    return out


def ang_deg(x, y, cx, cy):
    """Angle of a cell centre round (cx, cy) in degrees; 0 = +x (east), 90 = +y (south)."""
    return math.degrees(math.atan2(y + 0.5 - cy, x + 0.5 - cx)) % 360.0


def in_arc(a, lo, hi):
    a, lo, hi = a % 360, lo % 360, hi % 360
    return lo <= a <= hi if lo <= hi else (a >= lo or a <= hi)


def adiff(a, b):
    return abs(((a - b + 180.0) % 360.0) - 180.0)


def broadleaf(cv, x, y, r, h, mat='veg'):
    """Stand-in broadleaf: 2x2 trunk and an ellipsoid canopy whose underside stays >= 5 above the ground
    (walk under). Material veg (replaced in the art pass)."""
    g = int(cv.H[x, y])
    th = max(6, h - r)
    cv.box(x, x + 1, y, y + 1, g - th, g - 1, C['trunk'], mat)
    cz = g - th - r * 0.55
    cv.ellipsoid(x + 1.0, y + 1.0, cz, r, r * 0.9, r * 0.7, C['veg'], mat)
    vid = cv.material(mat)
    x0, y0 = max(0, x - r - 2), max(0, y - r - 2)
    sl = (slice(x0, x + r + 4), slice(y0, y + r + 4))
    sub_s, sub_m = cv.solid[sl], cv.mat[sl]
    Hs = cv.H[sl].astype(int)
    zz = np.arange(64)[None, None, :]
    low = (sub_m == vid) & sub_s & (zz >= Hs[:, :, None] - 5) & (zz < Hs[:, :, None])
    tr = np.zeros(low.shape[:2], bool)
    tr[x - x0:x - x0 + 2, y - y0:y - y0 + 2] = True
    low &= ~tr[:, :, None]
    sub_s[low] = False
    sub_m[low] = 0


def fir(cv, x, y, r, h, mat='veg'):
    """Stand-in fir: a cone standing on the ground, footprint filled down to the terrain."""
    g = int(cv.H[x, y])
    zb = g - 1
    cv.cone(x + 0.5, y + 0.5, r, zb, zb - h + 1, C['veg'], mat)
    for xx in range(x - r - 1, x + r + 2):
        for yy in range(y - r - 1, y + r + 2):
            if 0 <= xx < 512 and 0 <= yy < 512 and cv.solid[xx, yy, zb] and cv.H[xx, yy] > zb + 1:
                cv.box(xx, xx, yy, yy, zb + 1, int(cv.H[xx, yy]) - 1, C['veg'], mat)


def building_pads(H, S=SPEC):
    """Flat pads under every building (applied to H before fill_terrain)."""
    def pad(x0, x1, y0, y1, z):
        H[max(0, x0):x1 + 1, max(0, y0):y1 + 1] = z
    gt = S['gate_tower']['box']
    pad(gt[0] - 1, gt[1] + 1, gt[2] - 1, gt[3] + 1, 50)
    b = S['bastion']['box']
    pad(b[0] - 1, b[1] + 1, b[2] - 1, b[3] + 1, 50)
    for k in ('main', 'wing'):
        x0, x1, y0, y1 = S['hall'][k]
        pad(x0 - 1, x1 + 1, y0 - 1, y1 + 1, 49)
    for (x0, x1, y0, y1) in (S['sites']['chapel']['nave'],):
        pad(x0 - 1, x1 + 8, y0 - 1, y1 + 1, 50)
    ax, ay, ar = S['hall']['apse']
    pad(int(ax - ar) - 1, int(ax + ar) + 1, int(ay) - 1, int(ay + ar) + 2, 49)
    for (x0, x1, y0, y1, _o) in S['tents']:
        pad(x0 - 1, x1 + 1, y0 - 1, y1 + 1, 49)


# =============================================================================================== outpost

def build_walls(cv, S=SPEC):
    """Curtain wall along the outpost outline: 3 thick, 6-11 tall with a broken noisy top (broken-down stretches
    3-4 tall, never a step), wide breaches. Returns the number of wall columns."""
    op = S['outpost']
    poly = op['poly']
    hn = noise.fbm2((512, 512), 5, 2, 'wall_top', S['layout_seed'])
    br = {}
    for (i, t0, t1) in op['breaches']:
        br.setdefault(i, []).append((t0, t1))
    cells = set()
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        L2 = float((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)
        for (x, y) in seg_cells(a, b, op['wall_t']):
            t = ((x + 0.5 - a[0]) * (b[0] - a[0]) + (y + 0.5 - a[1]) * (b[1] - a[1])) / L2
            if any(t0 <= t <= t1 for (t0, t1) in br.get(i, [])):
                continue
            cells.add((x, y))
    gt = S['gate_tower']['box']
    bs = S['bastion']['box']
    lo, hi = op['wall_h']
    n = 0
    for (x, y) in sorted(cells):
        if gt[0] - 1 <= x <= gt[1] + 1 and gt[2] - 1 <= y <= gt[3] + 1:
            continue
        if bs[0] - 1 <= x <= bs[1] + 1 and bs[2] - 1 <= y <= bs[3] + 1:
            continue
        v = float(hn[x, y])
        h = int(round(lo + (hi - lo) * v))
        if v < 0.30:
            h = 3 + int(v * 4)                       # broken-down stretch: 3-4 tall (not a step)
        g = int(cv.H[x, y])
        h = min(h, g - 8)
        if h < 3:
            continue
        cv.box(x, x, y, y, g - h, g - 1, C['ruin'], 'ruin')
        n += 1
    return n


def ruin_building(cv, M, origin, g, storeys, sh, name, stairs=(), doors=(), collapse=None, buttresses=(),
                  parapet=(2, 5), wall_c=None, seed=0, windows=True, interior_pts=None):
    """Enterable ruin of any footprint. M: bool [w, h] footprint at origin (x0, y0). Walls = the footprint rim
    (1 thick), a floor slab per storey over the interior, the top storey open to the sky, walls rising 2-5 above
    the top floor in stepped broken runs (never 1: not a step). stairs: (storey, x, y0, y1, dx) straight flights
    (they cut the slab above). doors: (x0, x1, y0, y1, storey, height). collapse: (x0, x1, y0, y1) corner where the
    walls and upper slabs have fallen: open to the ground with 1-tall rubble (climb through). buttresses:
    (x0, x1, y0, y1, h) masonry piers against the outside. Records one interior point per storey."""
    wall_c = wall_c or C['building']
    ox, oy = origin
    w, h = M.shape
    I = ndi.binary_erosion(M, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]]), border_value=0)
    Wl = M & ~I
    topf = g - (storeys - 1) * sh
    hn = noise.fbm2((64, 64), 3, 1, f'ruin_top_{name}', seed)
    for i in range(w):
        for j in range(h):
            x, y = ox + i, oy + j
            if Wl[i, j]:
                ph = parapet[0] + int((parapet[1] - parapet[0] + 0.999) * hn[(i // 2) % 64, (j // 2) % 64])
                cv.box(x, x, y, y, topf - ph, g - 1, wall_c, 'building')
            elif I[i, j]:
                cv.carve(x, x, y, y, topf - parapet[1] - 2, g - 1)
                for k in range(storeys):
                    cv.set(x, y, g - k * sh, C['floor'], 'building')
    for (k, x, y0, y1, dx) in stairs:
        straight_stair(cv, x, y0, y1, g - k * sh, sh, dx, C['stair'])
    for (x0, x1, y0, y1, k, hh) in doors:
        cv.carve(x0, x1, y0, y1, g - k * sh - hh, g - k * sh - 1)
    if windows:
        for i in range(w):
            for j in range(h):
                if Wl[i, j]:
                    for k in range(storeys):
                        fz = g - k * sh
                        if k < storeys - 1 and (ox + i + 2 * (oy + j) + 3 * k) % 7 == 0:   # staggered per storey
                            cv.carve(ox + i, ox + i, oy + j, oy + j, fz - 3, fz - 2)
    if collapse:
        x0, x1, y0, y1 = collapse
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                i, j = x - ox, y - oy
                if 0 <= i < w and 0 <= j < h and M[i, j]:
                    cv.carve(x, x, y, y, 0, g - 1)
                    if (x + y) % 3:
                        cv.set(x, y, g - 1, C['ruin'], 'rubble')
    for (x0, x1, y0, y1, bh) in buttresses:
        gbox(cv, x0, x1, y0, y1, bh, wall_c, 'building')
    pts = interior_pts or []
    if not pts:
        cxy = np.argwhere(I)
        c = cxy.mean(0)
        best = cxy[np.argmin(((cxy - c) ** 2).sum(1))]
        pts = [(ox + int(best[0]), oy + int(best[1]))] * storeys
    for k in range(storeys):
        px, py = pts[min(k, len(pts) - 1)]
        cv.interiors.append([f'{name} floor {k}', px, py, g - k * sh])
    return {'name': name, 'top_floor': topf}


def octagon(w, h, c):
    xs, ys = np.meshgrid(np.arange(w), np.arange(h), indexing='ij')
    d = np.minimum(xs, w - 1 - xs) + np.minimum(ys, h - 1 - ys)
    return d >= c


def build_gate_tower(cv, S=SPEC):
    """Octagonal gate tower (3 storeys) with an arched gateway straight through its base (west-east), stairs to
    every floor, an open broken top with stepped parapets, a collapsed north-east corner you can climb through,
    two buttresses on the courtyard side."""
    gt = S['gate_tower']
    x0, x1, y0, y1 = gt['box']
    M = octagon(x1 - x0 + 1, y1 - y0 + 1, 3)
    g, sh = 50, gt['storey_h']
    ruin_building(cv, M, (x0, y0), g, gt['storeys'], sh, 'gate tower',
                  stairs=[(0, x0 + 2, y0 + 2, y0 + 3, 1), (1, x1 - 2, y1 - 3, y1 - 2, -1)],
                  doors=[(x0, x0, y0 + 6, y0 + 8, 0, 5), (x1, x1, y0 + 6, y0 + 8, 0, 5)],
                  collapse=(x1 - 1, x1, y0 + 1, y0 + 3), parapet=(2, 6), seed=S['layout_seed'],
                  buttresses=[(x0 - 2, x0 - 1, y0 + 3, y0 + 4, 7), (x0 + 5, x0 + 6, y0 - 2, y0 - 1, 7)],
                  interior_pts=[(x0 + 5, y0 + 7), (x0 + 6, y0 + 7), (x0 + 6, y0 + 7)])
    # arch: round the gateway top (one voxel each side lower) - an arch, not a slot
    for xx in (x0, x1):
        cv.box(xx, xx, y0 + 6, y0 + 6, g - 5, g - 5, C['building'], 'building')
        cv.box(xx, xx, y0 + 8, y0 + 8, g - 5, g - 5, C['building'], 'building')


def build_hall(cv, S=SPEC):
    """Hunters' hall: an L-shaped two-storey ruin (main range + north armoury wing) with a rounded apse on the
    south, roofless upper floor with broken stepped walls, a collapsed south-west corner, buttresses on the
    courtyard (east) facade."""
    hl = S['hall']
    mx0, mx1, my0, my1 = hl['main']
    wx0, wx1, wy0, wy1 = hl['wing']
    ax, ay, ar = hl['apse']
    x0, x1, y0, y1 = min(mx0, wx0), max(mx1, wx1), min(my0, wy0), max(my1, int(ay + ar) + 1)
    w, h = x1 - x0 + 1, y1 - y0 + 1
    M = np.zeros((w, h), bool)
    M[mx0 - x0:mx1 - x0 + 1, my0 - y0:my1 - y0 + 1] = True
    M[wx0 - x0:wx1 - x0 + 1, wy0 - y0:wy1 - y0 + 1] = True
    xs, ys = np.meshgrid(np.arange(w) + x0 + 0.5, np.arange(h) + y0 + 0.5, indexing='ij')
    M |= (np.hypot(xs - ax, ys - ay) <= ar) & (ys >= my1 - 1)
    g, sh = 49, hl['storey_h']
    cy = (my0 + my1) // 2
    ruin_building(cv, M, (x0, y0), g, hl['storeys'], sh, 'hunters hall',
                  stairs=[(0, mx0 + 3, my0 + 2, my0 + 3, 1)],
                  doors=[(mx1, mx1, cy - 1, cy + 1, 0, 4), (mx0, mx0, cy - 2, cy, 0, 4),
                         ((wx0 + wx1) // 2 - 1, (wx0 + wx1) // 2 + 1, wy0, wy0, 0, 4)],
                  collapse=(mx0, mx0 + 3, my1 - 6, my1 - 2), parapet=(2, 5), seed=S['layout_seed'] + 1,
                  buttresses=[(mx1 + 1, mx1 + 2, my0 + 5, my0 + 6, 8), (mx1 + 1, mx1 + 2, my1 - 6, my1 - 5, 8),
                              (mx1 + 1, mx1 + 2, cy + 6, cy + 7, 6)],
                  interior_pts=[(mx0 + 10, cy), (mx0 + 12, cy)])
    for ty in (my0 + 10, my0 + 22):                                    # long tables + benches
        cv.box(mx0 + 9, mx0 + 16, ty, ty + 1, g - 1, g - 1, C['furn'], 'furniture')
    cv.box(mx1 - 2, mx1 - 1, my0 + 5, my0 + 12, g - sh - 2, g - sh - 1, C['furn'], 'furniture')
    cv.box(wx0 + 2, wx0 + 3, wy0 + 2, wy1 - 2, g - 2, g - 1, C['furn'], 'furniture')     # armoury racks


def build_bastion(cv, S=SPEC):
    """Broken round tower base at the south end of the front breach: 3-thick ring wall 6-9 tall with a vaulted
    roof slab over a real room (5 voxels of headroom), a west door and a north breach; the vault is not
    reachable (no stair, walls >= 6). Recorded as a room."""
    b = S['bastion']
    x0, x1, y0, y1 = b['box']
    cx, cy = (x0 + x1 + 1) / 2.0, (y0 + y1 + 1) / 2.0
    R = (x1 - x0 + 1) / 2.0
    hn = noise.fbm2((512, 512), 4, 2, 'bastion_top', S['layout_seed'])
    g = 50
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if R - 3.0 < d <= R:
                hh = b['h'][0] + int(round((b['h'][1] - b['h'][0]) * hn[x, y]))
                cv.box(x, x, y, y, g - hh, g - 1, C['ruin'], 'ruin')
            elif d <= R - 3.0:
                cv.set(x, y, g - 6, C['ruin'], 'ruin')                      # vault slab
                cv.set(x, y, g - 7, C['ruin'], 'ruin')
    ic, jc = int(cx), int(cy)
    cv.carve(x0, x0 + 3, jc - 1, jc + 1, g - 4, g - 1)                     # west door
    cv.carve(ic - 1, ic + 1, y0, y0 + 3, g - 4, g - 1)                     # north breach (doorway height)
    cv.carve(ic - 2, ic + 2, y0, y0 + 1, 0, g - 5)                         # broken crown over the breach
    cv.set(ic + 1, jc + 2, g - 1, C['ruin'], 'rubble')
    cv.interiors.append(['bastion room', ic, jc, g])


def tent(cv, x0, x1, y0, y1, open_side, name, g=49):
    """A-frame tent: canvas 1 thick, ridge half+1 above the floor, closed back, open front.
    'S'/'N': ridge along y (open at y1 / y0); 'W'/'E': ridge along x (open at x0 / x1)."""
    along_y = open_side in ('S', 'N')
    if along_y:
        c, half = (x0 + x1) / 2.0, (x1 - x0) // 2
    else:
        c, half = (y0 + y1) / 2.0, (y1 - y0) // 2
    ridge = g - (half + 1)
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            d = int(math.floor(abs((x if along_y else y) - c) + 0.01))
            z = ridge + d
            if z <= g - 1:
                cv.set(x, y, z, C['tent'], 'tent')
    if along_y:
        by = y0 if open_side == 'S' else y1
        for x in range(x0, x1 + 1):
            d = int(math.floor(abs(x - c) + 0.01))
            cv.box(x, x, by, by, ridge + d, g - 1, C['tent'], 'tent')
        bz = y0 + 2 if open_side == 'S' else y1 - 3
        cv.box(int(c) - 3, int(c) - 2, bz, bz + 1, g - 1, g - 1, C['furn'], 'furniture')
        cx, cy = int(round(c)), (y0 + y1) // 2
    else:
        bx = x1 if open_side == 'W' else x0
        for y in range(y0, y1 + 1):
            d = int(math.floor(abs(y - c) + 0.01))
            cv.box(bx, bx, y, y, ridge + d, g - 1, C['tent'], 'tent')
        cx, cy = (x0 + x1) // 2, int(round(c))
    cv.interiors.append([name, cx, cy, g])


def build_camp(cv, S=SPEC):
    for i, (x0, x1, y0, y1, o) in enumerate(S['tents']):
        tent(cv, x0, x1, y0, y1, o, f'tent {i}', 49)
    for (x0, x1, y0, y1) in S['racks']:                       # trophy racks: two posts, a bar, hanging trophies
        g = int(cv.H[x0, y0])
        cv.box(x0, x1, y0, y1, g - 4, g - 4, C['trunk'], 'prop')
        cv.box(x0, x0, y0, y0, g - 4, g - 1, C['trunk'], 'prop')
        cv.box(x1, x1, y1, y1, g - 4, g - 1, C['trunk'], 'prop')
        for k in range(1, max(x1 - x0, y1 - y0), 2):
            xx, yy = (x0 + k, y0) if x1 > x0 else (x0, y0 + k)
            cv.box(xx, xx, yy, yy, g - 3, g - 3, C['stem'], 'prop')
    x0, x1, y0, y1 = S['cart']                                  # hunters' cart: bed, wheels, shaft
    g = int(cv.H[x0, y0])
    cv.box(x0, x1, y0, y1, g - 3, g - 2, C['timber'], 'prop')
    for (x, y) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        cv.box(x, x, y, y, g - 1, g - 1, C['trunk'], 'prop')
    my = (y0 + y1) // 2
    cv.box(x1 + 1, x1 + 3, my, my, g - 2, g - 2, C['trunk'], 'prop')
    cv.box(x1 + 3, x1 + 3, my, my, g - 1, g - 1, C['trunk'], 'prop')
    for (x, y) in S['campfires']:                               # campfire: ring of stones round a fire log
        for (dx, dy) in ((-2, -1), (-2, 0), (-2, 1), (2, -1), (2, 0), (2, 1), (-1, -2), (0, -2), (1, -2),
                         (-1, 2), (0, 2), (1, 2)):
            cv.set(x + dx, y + dy, int(cv.H[x + dx, y + dy]) - 1, C['stone'], 'prop')
        cv.set(x, y, int(cv.H[x, y]) - 1, (200, 120, 70), 'fire')


# =============================================================================================== front (dressed)

def drum(cv, x, y, length, r, along):
    """Fallen column drum lying on the ground: a horizontal cylinder of radius r (about 2r tall)."""
    for i in range(length):
        for j in range(-int(r) - 1, int(r) + 2):
            ax, ay = (x + i, y + j) if along == 'x' else (x + j, y + i)
            g = int(cv.H[ax, ay])
            zc = g - r
            for z in range(g - int(2 * r) - 1, g):
                if j * j + (z + 0.5 - zc) ** 2 <= r * r:
                    cv.set(ax, ay, z, C['ruin'], 'ruin')
    k = (2 * length) // 3                                       # chipped notch on top
    ax, ay = (x + k, y) if along == 'x' else (x, y + k)
    g = int(cv.H[ax, ay])
    top = g - int(2 * r)
    cv.carve(ax, ax + (1 if along == 'x' else 0), ay, ay + (0 if along == 'x' else 1), top - 1, top)


def build_front(cv, S=SPEC):
    """Low ruin pieces on the front band (<= 5 tall, each >= 25 cells, scattered): drums, a toppled torso, moss
    mounds, a sled-cart, fern clumps and a roofless one-room shrine."""
    g = 50
    for (kind, x, y, p) in S['front_pieces']:
        if kind == 'drum_x':
            drum(cv, x, y, p['len'], p['r'], 'x')
        elif kind == 'drum_y':
            drum(cv, x, y, p['len'], p['r'], 'y')
        elif kind == 'lintel':                      # fallen carved lintel: a block with a chamfered top edge
            gbox(cv, x, x + p['w'] - 1, y, y + p['d'] - 1, p['h'] - 1, C['ruin'], 'ruin')
            gbox(cv, x + 1, x + p['w'] - 2, y + 1, y + p['d'] - 2, p['h'], C['ruin'], 'ruin')
        elif kind == 'torso':                       # toppled statue torso + broken arm + neck stub
            cv.ellipsoid(x + 0.5, y + 0.5, g - 0.5, 5.5, 3.6, 4.2, C['ruin'], 'statue')
            cv.box(x + 5, x + 9, y + 3, y + 4, g - 2, g - 1, C['ruin'], 'statue')
            cv.box(x - 7, x - 5, y - 1, y + 1, g - 3, g - 1, C['ruin'], 'statue')
        elif kind == 'mound':
            gcells(cv, ell_cells(x + 0.5, y + 0.5, p['rx'], p['ry']), 1, C['ground'], 'mound')
            gcells(cv, ell_cells(x + 0.5, y + 0.5, p['rx'] - 0.8, p['ry'] - 0.8), 2, C['ground'], 'mound')
            if p['h'] > 2:
                gcells(cv, ell_cells(x + 0.5, y + 0.5, p['rx'] - 2.0, p['ry'] - 2.0), p['h'], C['ground'], 'mound')
        elif kind == 'sled':                        # hunter's sled-cart: bed 2 tall, load 3 tall, a pole
            gbox(cv, x, x + 6, y, y + 3, 2, C['timber'], 'prop')
            gbox(cv, x + 1, x + 3, y + 1, y + 2, 3, C['prop'], 'prop')
            cv.box(x + 7, x + 8, y + 1, y + 2, g - 1, g - 1, C['timber'], 'prop')
        elif kind == 'ferns':
            gcells(cv, ell_cells(x + 0.5, y + 0.5, p['rx'], p['ry']), 2, C['fern'], 'fern')
        elif kind == 'shrine':                      # roofless one-room shrine: 4-tall walls, three doorways, altar
            x0, x1, y0, y1 = x, x + 9, y, y + 8
            cv.box(x0, x1, y0, y1, g - 4, g - 1, C['ruin'], 'ruin')
            cv.carve(x0 + 1, x1 - 1, y0 + 1, y1 - 1, g - 4, g - 1)
            cv.carve(x0, x0, y0 + 3, y0 + 5, g - 4, g - 1)
            cv.carve(x1, x1, y0 + 3, y0 + 5, g - 4, g - 1)
            cv.carve(x0 + 4, x0 + 6, y1, y1, g - 4, g - 1)
            cv.carve(x0, x0, y0, y0, g - 4, g - 3)                      # broken corners
            cv.carve(x1, x1, y1, y1, g - 4, g - 3)
            cv.box(x0 + 3, x0 + 6, y0 + 1, y0 + 1, g - 1, g - 1, C['stone'], 'furniture')   # altar
            cv.interiors.append(['front shrine', x0 + 4, y0 + 4, g])


# =============================================================================================== under the platform

def build_under(cv, S=SPEC):
    """Low ruins in the strip: a fallen elder head half-buried and tilted (brow, eye sockets, nose, lips, a crown
    fragment against its crown; every edge >= 2 tall: not climbable), column stubs on 2-tall plinths. The mosaic
    floor is region 6 (paint only)."""
    U = S['under']
    g = 50
    hd = U['head']
    cx, cy = hd['c'][0] + 0.5, hd['c'][1] + 0.5
    rx, ry, rz = hd['r']
    W = C['ruin']
    for x in range(int(cx - rx) - 1, 256):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            u = ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2
            if u > 1:
                continue
            tilt = hd['tilt'] * (y + 0.5 - cy) / ry                        # face tilted toward the north
            hgt = int(round(rz * math.sqrt(1 - u) - tilt))
            if hgt >= 2:
                cv.box(x, x, y, y, g - hgt, g - 1, W, 'statue')
    def top(x, y):                                  # features only on the head itself (never a 1-tall stub)
        t = int(np.argmax(cv.solid[x, y]))
        return t if t <= g - 3 else -99
    ny = int(cy) - 2                                                    # face features on the upper surface
    for y in range(ny - 1, ny + 4):
        t = top(255, y)
        if t > 0:
            cv.set(255, y, t - 1, W, 'statue')                              # nose
    for x in (251, 252):
        t = top(x, ny - 2)
        if t > 0:
            cv.carve(x, x, ny - 2, ny - 2, t, t)                             # eye sockets
    for x in range(250, 254):
        t = top(x, ny - 4)
        if t > 0:
            cv.set(x, ny - 4, t - 1, W, 'statue')                           # brow
    for x in range(253, 256):
        t = top(x, ny + 5)
        if t > 0:
            cv.carve(x, x, ny + 5, ny + 5, t, t)                             # lips (a groove)
    for x in range(int(cx) - 5, 256):                                   # crown fragment on the crown side, 2 tall
        y = int(cy - ry) - 1
        if x % 3:
            gbox(cv, x, x, y, y, 2, W, 'statue')
    for (x, y) in U['stubs']:
        cv.box(x - 3, x + 3, y - 3, y + 3, g - 2, g - 1, C['stone'], 'ruin')
        cv.carve(x - 3, x - 3, y - 3, y - 3, g - 2, g - 1)
        cv.carve(x + 3, x + 3, y + 3, y + 3, g - 2, g - 1)
        cv.cylinder(x + 0.5, y + 0.5, 2.1, g - 5, g - 3, C['ruin'], 'ruin')


def build_spire(cv, S=SPEC):
    """Ruined round elder spire (west; the east one is the mirror). Wall ring r 4.5-6.5 from the ground (z 50) up to
    the top floor (z 12). External helix stair on r 6.5-9.5 (24 rises per turn, 38 rises): rises 1-5 a solid ramp,
    higher treads 2-thick slabs keyed into the wall (walk under them from rise 6 on), 4 voxels of climb room over
    every tread, the outer tread ring crumbled in places (2 wide left). Mid landing at rise 19 (z 31): balcony and
    a doorway into the mid floor, which is half collapsed. Ground room with three doors under high treads. Broken
    parapet stubs (2-4 tall) on the top floor, open where the stair arrives. Returns a report."""
    sp = S['spire']
    cx, cy = sp['c']
    r_in, r_out = sp['r_wall']
    rs = sp['r_stair']
    g, top = sp['ground'], sp['top']
    n = g - top
    dth = 360.0 / sp['rises_per_turn']
    th0 = sp['start_deg']
    zmid = g - sp['mid_rise']
    R = int(rs) + 3
    xs = list(range(int(cx) - R, int(cx) + R + 1))
    ys = list(range(int(cy) - R, int(cy) + R + 1))
    hn = noise.fbm2((64, 64), 4, 2, 'spire_parapet', S['layout_seed'])
    arrive = (th0 + (n - 0.5) * dth) % 360
    door_mid = (th0 + (sp['mid_rise'] - 0.5) * dth) % 360
    ph = sp['parapet']['h']
    treads = 0
    for x in xs:
        for y in ys:
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            a = ang_deg(x, y, cx, cy)
            if d <= r_out:
                if d > r_in:
                    cv.box(x, x, y, y, top, g - 1, C['spire'], 'spire')
                else:
                    cv.carve(x, x, y, y, top + 1, g - 1)
                cv.set(x, y, top, C['floor'], 'spire')                             # top floor
                if d <= r_in + 0.5 and not in_arc(a, *sp['collapse_deg']):
                    cv.set(x, y, zmid, C['floor'], 'spire')                        # mid floor (half collapsed)
                if r_out - 1.0 < d:                                                # parapet stubs, 2-4 tall
                    gap = any(in_arc(a, lo, hi) for (lo, hi) in sp['parapet']['gap_deg']) or adiff(a, arrive) <= 30
                    if not gap:
                        h = ph[0] + int(round((ph[1] - ph[0]) * hn[x - xs[0], y - ys[0]]))
                        cv.box(x, x, y, y, top - h, top - 1, C['spire'], 'spire')
            elif d <= rs:
                th = (a - th0) % 360.0
                for k in (0, 1):
                    rise = int((th + 360.0 * k) // dth) + 1
                    if rise > n:
                        continue
                    zt = g - rise
                    if d > rs - 1.0 and rise > sp['fill_rises'] and \
                            any(in_arc(a, lo, hi) for (lo, hi) in sp['crumble']):
                        continue
                    if rise <= sp['fill_rises']:
                        cv.box(x, x, y, y, zt, g - 1, C['stair'], 'stair')
                    else:
                        cv.box(x, x, y, y, zt, zt + sp['tread_t'] - 1, C['stair'], 'stair')
                    cv.carve(x, x, y, y, zt - 4, zt - 1)
                    treads += 1
    for x in xs:                                # mid landing: balcony + doorway into the mid floor
        for y in ys:
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            a = ang_deg(x, y, cx, cy)
            if adiff(a, door_mid) <= 13:
                if rs < d <= rs + 1.6:
                    cv.box(x, x, y, y, zmid, zmid + 1, C['stair'], 'stair')
                    cv.carve(x, x, y, y, zmid - 4, zmid - 1)
                if r_in - 0.6 < d <= r_out + 0.2:
                    cv.carve(x, x, y, y, zmid - 4, zmid - 1)
                    cv.set(x, y, zmid, C['floor'], 'spire')
    for dd in sp['doors_deg']:                  # ground doors (under high treads)
        for x in xs:
            for y in ys:
                d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
                if r_in - 0.6 < d <= r_out + 0.2 and adiff(ang_deg(x, y, cx, cy), dd) <= 11:
                    cv.carve(x, x, y, y, g - 4, g - 1)
    for (dd, z) in ((60, 40), (250, 36), (130, 24), (330, 20), (200, 16)):     # arrow slits
        for x in xs:
            for y in ys:
                d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
                if r_in < d <= r_out and adiff(ang_deg(x, y, cx, cy), dd) <= 5:
                    cv.carve(x, x, y, y, z - 1, z)
    for x in xs:                                # fallen floor rubble (1 tall) under the collapse
        for y in ys:
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if d <= r_in - 1 and in_arc(ang_deg(x, y, cx, cy), 240, 300):
                cv.set(x, y, g - 1, C['ruin'], 'rubble')
    icx, icy = int(cx), int(cy)
    mx = int(math.floor(cx + (rs - 1.5) * math.cos(math.radians(door_mid))))
    my = int(math.floor(cy + (rs - 1.5) * math.sin(math.radians(door_mid))))
    cv.interiors += [['spire ground room', icx, icy, g], ['spire mid floor', icx + 2, icy + 1, zmid],
                     ['spire top', icx, icy, top], ['spire mid landing', mx, my, zmid]]
    return {'centre': [cx, cy], 'top_floor_z': top, 'rises': n, 'tread_cells': treads,
            'arrive_deg': round(arrive, 1), 'mid_door_deg': round(door_mid, 1), 'box': list(sp['box'])}


# =============================================================================================== centre (axis objects)

def build_plaza(cv, S=SPEC):
    """Sunken plaza pieces: dry moonwell (two rim arcs, pillar on a plinth), broken statues on plinths in a ring,
    two curved arcades (piers + roof slab, walk-through). The steps and floor are terrain."""
    p = S['plaza']
    mw = p['moonwell']
    cx, cy = mw['c']
    fx, fy = cx + 0.5, cy + 0.5
    r = mw['r']
    for x in range(int(fx - r) - 2, 256):
        for y in range(int(fy - r) - 2, int(fy + r) + 3):
            d = math.hypot(x + 0.5 - fx, y + 0.5 - fy)
            if r - 1.6 < d <= r:
                a = ang_deg(x, y, fx, fy)
                if adiff(a, 180) <= 16:                                   # entrances E and W (the E one by mirror)
                    continue
                g = int(cv.H[x, y])
                cv.box(x, x, y, y, g - mw['rim_h'], g - 1, C['ruin'], 'ruin')
    g = int(cv.H[255, cy])
    cv.box(254, 255, cy - 2, cy + 2, g - 2, g - 1, C['stone'], 'ruin')                  # plinth 5 x 5, 2 tall
    cv.cylinder(fx, fy, 1.6, g - 2 - mw['pillar_h'], g - 3, C['rune'], 'rune')          # rune pillar
    cv.interiors.append(['moonwell basin', 251, cy + 3, g])
    # statues on plinths (axis statue written as its west half)
    hrng = noise.rng('statues', S['layout_seed'])
    for a in p['statue_deg']:
        sx = int(math.floor(fx + p['statue_r'] * math.cos(math.radians(a))))
        sy = int(math.floor(fy + p['statue_r'] * math.sin(math.radians(a))))
        if a == 270:
            sx = 256
        gbox(cv, sx - 2, min(255, sx + 2), sy - 2, sy + 2, 2, C['stone'], 'ruin')
        h = int(hrng.integers(5, 10))
        g = int(cv.H[sx, sy])
        cv.box(sx - 1, min(255, sx + 1), sy - 1, sy, g - 2 - h, g - 3, C['ruin'], 'statue')
        if h >= 8:
            cv.box(sx - 1, min(255, sx), sy - 1, sy - 1, g - 4 - h, g - 3 - h, C['ruin'], 'statue')   # head
    # arcades along the plaza outline (inside the steps): piers every 6, roof slab 5 above the floor
    pc, pr = p['c'], p['r']
    for (ca, half, f) in p['arcades']:
        pts = []
        n = int(half * 4)
        for i in range(-n, n + 1):
            t = math.radians(ca + half * i / n)
            pts.append((pc[0] + pr[0] * f * math.cos(t), pc[1] + pr[1] * f * math.sin(t)))
        roof = set()
        for (a, b) in zip(pts, pts[1:]):
            roof.update(seg_cells(a, b, 3.2))
        L = 0.0
        piers = [pts[0]]
        for (a, b) in zip(pts, pts[1:]):
            L += math.hypot(b[0] - a[0], b[1] - a[1])
            if L >= 6.0:
                piers.append(b)
                L = 0.0
        if math.hypot(piers[-1][0] - pts[-1][0], piers[-1][1] - pts[-1][1]) > 2:
            piers.append(pts[-1])
        zroof = {}
        for (x, y) in roof:
            if x <= 255:
                zroof[(x, y)] = int(cv.H[x, y]) - 6
        zr = min(zroof.values())
        broken = len(piers) // 2
        for i, (px, py) in enumerate(piers):
            ix, iy = int(math.floor(px)), int(math.floor(py))
            for (x, y) in ((ix, iy), (ix + 1, iy), (ix, iy + 1), (ix + 1, iy + 1)):
                if x <= 255:
                    cv.box(x, x, y, y, zr + 1, int(cv.H[x, y]) - 1, C['ruin'], 'ruin')
        for (x, y) in roof:
            if x <= 255:
                cv.set(x, y, zr, C['ruin'], 'ruin')
        # a broken bay: the roof between the two middle piers has fallen
        if len(piers) > 3:
            (ax, ay), (bx, by) = piers[broken], piers[broken + 1]
            for (x, y) in seg_cells((ax + 1.5, ay + 1.0), (bx - 0.5, by), 3.4):
                if x <= 255 and (x, y) in roof and not cv.solid[x, y, zr + 1]:
                    cv.clear(x, y, zr)
        mx, my = pts[len(pts) // 2]
        cv.interiors.append([f'arcade {int(ca)}', int(mx), int(my), int(cv.H[int(mx), int(my)])])
    for (x, y, along, ln, r) in S['plaza_drums']:                       # fallen arcade columns on the floor
        drum(cv, x, y, ln, r, along)


def build_queen(cv, S=SPEC):
    """Fallen elder-queen: a reclining broken figure in four pieces lying N-S across the plaza's south edge.
    head (crown points, brow, eye sockets, nose, lips; face to the sky) | neck break with rubble | torso with
    shoulders resting on rubble supports, robe folds as long grooves (never ridges: the walk-over top stays z 44),
    the arms broken off and lying apart on the plaza | hips + thighs (walk-over from the rubble stair) | lower legs
    and upturned feet broken off at the knees. Walk under the torso (>= 3 air), walk over hips and torso."""
    q = S['queen']
    hx, hy = q['head_c']
    gh = int(cv.H[255, hy])
    R = q['head_r']
    W = C['ruin']
    cv.ellipsoid(256.5, hy + 0.5, gh - R + 0.5, R, R + 0.5, R, W, 'statue')
    hz = gh - int(2 * R)                                                # head top z
    for x in range(250, 256):                                           # crown points on the north rim
        if x % 2 == 0:
            t = int(np.argmax(cv.solid[x, hy - 3]))
            cv.box(x, x, hy - 3, hy - 3, hz - 2, t, W, 'statue')
    cv.box(255, 255, hy, hy + 3, hz - 1, hz - 1, W, 'statue')           # nose ridge
    cv.carve(253, 253, hy - 1, hy - 1, hz, hz)                          # eye sockets
    cv.carve(253, 253, hy, hy, hz, hz)
    cv.box(251, 254, hy - 2, hy - 2, hz - 1, hz - 1, W, 'statue')       # brow
    # neck break: rubble only (1 tall)
    n0, n1 = q['neck_y']
    for (x, y) in ((251, n0), (253, n0 + 1), (255, n1)):
        cv.set(x, y, int(cv.H[x, y]) - 1, W, 'rubble')
    # torso: shoulders on rubble supports at the north end, slab over the steps, folds as grooves
    t0, t1 = q['torso_y']
    za, zb = q['torso_z']
    cv.box(q['x'][0], 255, t0, t1, za, zb, W, 'statue')
    cv.box(q['x'][0] - 2, 255, t0, t0 + 4, za, zb, W, 'statue')        # shoulders (wider)
    for x in (q['x'][0] - 2, q['x'][0] - 1):
        for y in range(t0, t0 + 3):
            cv.box(x, x, y, y, zb + 1, int(cv.H[x, y]) - 1, C['ruin'], 'rubble')   # rubble support
    for x in range(q['x'][0] + 1, 256, 3):
        cv.carve(x, x, t0 + 6, t1, za, za)                              # robe folds (grooves)
    # arms broken off, lying apart on the plaza floor west of the torso (hand with fingers), 2 tall
    ax0, ay0 = q['arm']
    gbox(cv, ax0, ax0 + 7, ay0, ay0 + 2, 2, W, 'statue')
    for k in range(4):
        gbox(cv, ax0 - 1, ax0 - 1, ay0 - 1 + k, ay0 - 1 + k, 2, W, 'statue')     # fingers
    # hips + thighs (walk-over), lower legs and feet broken at the knees
    h0, h1 = q['hips_y']
    cv.box(q['x'][0] + 1, 255, h0, h1, za, 49, W, 'statue')
    cv.carve(q['x'][0] + 1, q['x'][0] + 1, h1, h1, za, za + 1)
    l0, l1 = q['legs_y']
    cv.box(q['x'][0] + 2, 255, l0, l1, za + 2, 49, W, 'statue')
    cv.carve(254, 255, l0, l1 - 3, za + 2, za + 2)                      # the cleft between the legs
    cv.box(q['x'][0] + 2, 254, l1 - 2, l1, za, za + 1, W, 'statue')    # upturned feet (unreachable)
    rx0, rx1 = q['ramp_x']
    ry0, ry1 = q['ramp_y']
    straight_stair(cv, rx0 + 3, ry0, ry1, 50, 50 - za, 1, C['stair'], mat='stair')
    cv.interiors += [['queen walk-under', 252, (t0 + t1) // 2 + 2, int(cv.H[252, (t0 + t1) // 2 + 2])],
                     ['queen back', 252, (t0 + t1) // 2 + 2, za], ['queen hips', 252, (h0 + h1) // 2, za]]


def build_library(cv, S=SPEC):
    """Elder library ruin on the axis: two floors with a stair (the mirror adds a second one), a west wing (east by
    mirror), fallen and upright shelves, reading alcoves upstairs, roof holes and broken wall tops."""
    lb = S['library']
    x0, x1, y0, y1 = lb['box']
    g = 50
    sh = lb['storey_h']
    wx0, wx1, wy0, wy1 = lb['wing']
    structures.building(cv, wx0, wx1, wy0, wy1, g, storeys=1, storey_h=sh, doors=('W', 'N'), wall=C['building'],
                        floor=C['floor'], roof=C['roof'], name='library wing', furnish=False)
    structures.building(cv, x0, x1, y0, y1, g, storeys=lb['storeys'], storey_h=sh, doors=('S', 'N', 'W'),
                        wall=C['building'], floor=C['floor'], roof=C['roof'], stair=C['stair'], name='elder library',
                        furnish=False)
    roof = g - lb['storeys'] * sh
    up = g - sh
    cv.carve(x0 + 4, x0 + 9, y0 + 7, y0 + 12, roof, roof)                  # roof holes (open sky upstairs)
    cv.carve(x0 + 11, x0 + 14, y1 - 6, y1 - 3, roof, roof)
    cv.carve(x0, x0, y0 + 14, y0 + 20, roof - 1, roof + 2)                 # broken wall tops
    cv.carve(x0 + 6, x0 + 12, y1, y1, roof - 1, roof + 1)
    for yy in (y0 + 9, y0 + 15, y0 + 21):                                   # fallen shelves (ground floor, 1 tall)
        cv.box(x0 + 5, x0 + 12, yy, yy, g - 1, g - 1, C['furn'], 'furniture')
    cv.box(x0 + 11, x0 + 16, y0 + 1, y0 + 1, up - 3, up - 1, C['furn'], 'furniture')   # upright shelves upstairs
    for px in (x0 + 6, x0 + 12):                                            # reading alcoves (south side, upstairs)
        cv.box(px, px, y1 - 6, y1 - 1, up - 5, up - 1, C['building'], 'building')
    cv.box(x0 + 8, x0 + 10, y1 - 3, y1 - 2, up - 1, up - 1, C['furn'], 'furniture')
    cv.interiors += [['library alcove', x0 + 9, y1 - 4, up]]


def _tube(cv, pts, r0, r1, c, mat):
    """Thick tapered tube through a list of points (spheres every half voxel; face-connected)."""
    n = len(pts)
    for i in range(n - 1):
        (ax, ay, az), (bx, by, bz) = pts[i], pts[i + 1]
        L = max(1, int(math.hypot(math.hypot(bx - ax, by - ay), bz - az) * 2))
        for k in range(L + 1):
            t = k / L
            u = (i + t) / max(n - 1, 1)
            r = r0 + (r1 - r0) * u
            cv.ellipsoid(ax + (bx - ax) * t, ay + (by - ay) * t, az + (bz - az) * t, r, r, r, c, mat)


def build_amphi(cv, S=SPEC):
    """The heart-tree: an ancient tree over the root amphitheatre (terraces are terrain).
    - trunk: three stacked girths (a 3-tall flared base, a 7-tall lower bole, the twisting upper bole), lobed and
      twisting, with a walk-in hollow at the floor opening north (recorded);
    - roots: four kinds (high arch you walk under, low arch, two ground roots) at different angles, lengths and
      thicknesses; arches end in a steep knee (top >= 5 above the ground), ground roots stay >= 2 tall (no step);
    - limbs: three main limbs + an axis leader, each forking twice, carrying separate crown masses at different
      heights with sky between them (all >= 26 above the arena, well clear of the platform)."""
    a = S['amphi']
    T = a['tree']
    cx, cy = a['c'][0] + 0.5, a['c'][1] + 0.5
    g = int(cv.H[255, a['c'][1]])
    top = T['trunk_top']
    TR, CN, RT = C['trunk'], C['veg'], C['root']
    for z in range(top, g):
        h = g - 1 - z
        r = T['base_r'] if h <= 2 else (T['mid_r'] if h <= 9 else T['upper_r'] - (h - 10) * 0.035)
        oy = T['twist'] * math.sin(h / 6.0)
        for x in range(int(cx) - 12, 256):
            for y in range(int(cy) - 12, int(cy) + 13):
                dx, dy = x + 0.5 - cx, y + 0.5 - (cy + oy)
                th = math.atan2(dy, dx)
                rr = r * (1 + 0.12 * math.sin(3 * th + h / 5.0) + 0.06 * math.sin(7 * th + 1.3))
                if dx * dx + dy * dy <= rr * rr:
                    cv.set(x, y, z, TR, 'trunk')
    # walk-in hollow at the floor: a room r 3.4 north of the centre, a 4-wide 4-tall doorway to the north
    hy = cy - 2.0
    for x in range(int(cx) - 5, 256):
        for y in range(int(hy) - 5, int(hy) + 5):
            if math.hypot(x + 0.5 - cx, y + 0.5 - hy) <= 3.4:
                cv.carve(x, x, y, y, g - 5, g - 1)
    cv.carve(254, 255, int(cy) - 12, int(hy), g - 4, g - 1)
    cv.interiors.append(['heart-tree hollow', 255, int(hy), g])
    # roots and limbs use the kit ellipsoid (integer cell coordinates): centre on 256.0 so the axis pieces survive
    # the mirror (column 255 is copied to 256)
    cx, cy = cx - 0.5, cy - 0.5
    for (deg, reach, kind, t) in a['roots']:
        ca, sa = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        ex, ey = cx + reach * ca, cy + reach * sa
        ge = int(cv.H[min(255, int(ex)), int(ey)])
        if kind in ('arch', 'arch_low'):
            z0 = g - (16 if kind == 'arch' else 10)
            zk = ge - 5
            pts = []
            for i in range(13):
                u = i / 12
                rho = 6.0 + (reach - 6.0) * u
                z = z0 + (zk - z0) * u ** 1.6 - (2.5 if kind == 'arch' else 1.0) * math.sin(math.pi * u)
                pts.append((cx + rho * ca, cy + rho * sa, z))
            _tube(cv, pts, t, t * 0.7, RT, 'root')
            ix, iy = int(math.floor(ex)), int(math.floor(ey))
            cv.box(ix - 1, min(255, ix + 1), iy - 1, iy + 1, int(zk) - 1, ge - 1, RT, 'root')    # knee
        else:
            pts = []
            for i in range(11):
                u = i / 10
                rho = 6.5 + (reach - 6.5) * u
                px, py = cx + rho * ca + 1.5 * math.sin(u * 5) * -sa, cy + rho * sa + 1.5 * math.sin(u * 5) * ca
                gz = int(cv.H[min(255, int(px)), int(py)])
                pts.append((px, py, gz - t + 0.3))
            _tube(cv, pts, t, max(1.0, t * 0.75), RT, 'root')
            for (px, py, pz) in pts:                                          # keep >= 2 tall (never a step)
                for x in range(int(px) - 2, int(px) + 3):
                    for y in range(int(py) - 2, int(py) + 3):
                        if 0 <= x <= 255:
                            gz = int(cv.H[x, y])
                            if cv.solid[x, y, gz - 1] and not cv.solid[x, y, gz - 2] and \
                                    cv.mat[x, y, gz - 1] == cv.material('root'):
                                cv.set(x, y, gz - 2, RT, 'root')
    # limbs forking twice, separate crown masses
    rng = noise.rng('heart_limbs', S['layout_seed'])
    trunk_top = (cx, cy, top + 2)
    for (deg, rise, length, mass_r) in a['limbs']:
        ca, sa = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        if deg in (90, 270):
            ca = 0.0
        f1 = (cx + length * ca, cy + length * sa, top - rise)
        _tube(cv, [trunk_top, f1], 2.2, 1.6, TR, 'trunk')
        for d2 in (-28, 28):
            a2 = math.radians(deg + d2)
            c2, s2 = math.cos(a2), math.sin(a2)
            f2 = (f1[0] + 0.6 * length * c2, f1[1] + 0.6 * length * s2, f1[2] - rise * 0.5)
            _tube(cv, [f1, f2], 1.5, 1.1, TR, 'trunk')
            for d3 in (-22, 22):
                a3 = math.radians(deg + d2 + d3)
                f3 = (f2[0] + 0.4 * length * math.cos(a3), f2[1] + 0.4 * length * math.sin(a3),
                      f2[2] - 1 - rng.random() * 3)
                _tube(cv, [f2, f3], 1.0, 0.8, TR, 'trunk')
                r = mass_r * (0.8 + 0.4 * rng.random())
                cv.ellipsoid(f3[0], f3[1], f3[2] - 1.0, r, r * 0.9, r * 0.55, CN, 'canopy')
    for (x, y, z, rr) in [(cx, cy, top - 12, 5.5)]:                         # leader crown on the axis
        _tube(cv, [trunk_top, (cx, cy, top - 8)], 2.0, 1.4, TR, 'trunk')
        cv.ellipsoid(x, y, z, rr, rr, rr * 0.6, CN, 'canopy')
    # clamp: nothing above z 9, nothing over x 256 (mirror) - the leader is written on the axis
    m = cv.mat[:, :, :9] == cv.material('canopy')
    cv.solid[:, :, :9][m] = False
    cv.mat[:, :, :9][m] = 0
    cv.interiors.append(['amphitheatre arena', 246, a['c'][1], int(cv.H[246, a['c'][1]])])


def aqueduct_line(S=SPEC):
    """Aqueduct centre y for every column (gentle double bend, symmetric about the axis)."""
    aq = S['aqueduct']
    xs = np.arange(512)
    u = 256 - np.minimum(xs, 512 - xs)
    return np.rint(aq['y_c'] + aq['bend'] * np.sin(math.pi * u / aq['bend_period'])).astype(int)


def build_aqueduct(cv, S=SPEC):
    """Broken elder aqueduct along the north flank, bending gently: piers every 16, arches of varying height
    (crown 7 air, spandrels 3-6 deep), a deck (floor z 39, 5 wide between 2-tall parapets) on the intact spans,
    three collapsed gaps per side with rubble stairs up to both deck ends, a fallen span lying on the ground and a
    surviving tall pier standing in a gap."""
    aq = S['aqueduct']
    yc = aqueduct_line(S)
    hw = aq['half_w']
    dz, sf = aq['deck_z'], aq['soffit']
    g = S['z']['aqueduct_ground']
    coll = aq['collapses']

    def in_coll(x):
        return any(a <= x <= b for (a, b) in coll)
    piers = [p for p in range(aq['pier_x0'], 256, aq['pier_dx']) if not any(a - 3 <= p <= b for (a, b) in coll)]
    for p in piers:
        for x in range(p, p + aq['pier_w']):
            cv.box(x, x, yc[x] - hw, yc[x] + hw, sf, g - 1, C['ruin'], 'aqueduct')
    allp = sorted(piers + [512 - p - aq['pier_w'] + 1 for p in piers])
    for x in range(aq['x0'], 256):
        if in_coll(x):
            continue
        y0, y1 = yc[x] - hw, yc[x] + hw
        cv.box(x, x, y0, y1, dz, dz + aq['deck_t'] - 1, C['ruin'], 'aqueduct')
        if not any(p <= x < p + aq['pier_w'] for p in piers):
            left = [p + aq['pier_w'] - 1 for p in allp if p + aq['pier_w'] - 1 < x]
            right = [p for p in allp if p > x]
            if left and right:
                a, b = left[-1], right[0]
                mid, half = (a + b) / 2.0, max((b - a) / 2.0, 1.0)
                depth = aq['arch_depth'][(a // aq['pier_dx']) % len(aq['arch_depth'])]
                zs = sf + int(round(depth * ((x - mid) / half) ** 2))
                cv.box(x, x, y0, y1, sf, min(zs, g - 1), C['ruin'], 'aqueduct')
        if x % 11 not in (0, 1):
            cv.box(x, x, y0, y0, dz - aq['parapet_h'], dz - 1, C['ruin'], 'aqueduct')
            cv.box(x, x, y1, y1, dz - aq['parapet_h'], dz - 1, C['ruin'], 'aqueduct')
    rise = g - dz
    for (a, b) in coll:
        for i in range(1, rise + 1):                       # rubble stairs: west end rises to the deck at a - 1,
            for x, top in ((a + rise - i, g - i), (b - rise + i, g - i)):     # east end to the deck at b + 1
                cv.box(x, x, yc[x] - hw + 1, yc[x] + hw - 1, top, g - 1, C['stair'], 'stair')
                cv.carve(x, x, yc[x] - hw + 1, yc[x] + hw - 1, top - 4, top - 1)
        for x in (a - 1, b + 1):                           # open the parapet ends at the landings
            cv.carve(x, x, yc[x] - hw + 1, yc[x] + hw - 1, dz - 3, dz - 1)
        m = (a + b) // 2
        cv.interiors.append([f'aqueduct gap {a}', m, yc[m] + hw + 2, g])
    # fallen span lying in the middle gap (2 tall: not a step), beside the line
    fa, fb = coll[aq['fallen_in']]
    fm = (fa + fb) // 2
    for x in range(fm - 7, fm + 8):
        y0 = yc[x] + hw + 3 + (x - fm) // 5
        gbox(cv, x, x, y0, y0 + 4, 2, C['ruin'], 'aqueduct')
    # surviving tall pier in the gap nearest the axis (stands above the deck line, not reachable)
    ta, tb = coll[aq['tall_pier_in']]
    tm = (ta + tb) // 2
    for x in range(tm - 1, tm + 2):
        cv.box(x, x, yc[x] - hw + 1, yc[x] + hw - 1, aq['tall_pier_top'], g - 1, C['ruin'], 'aqueduct')
    secs = [aq['x0']] + [v for ab in coll for v in ab] + [255]
    for i in range(0, len(secs), 2):
        xa, xb = secs[i], secs[i + 1]
        xm = (xa + xb) // 2
        if cv.H[xm, yc[xm]] > dz:
            cv.interiors.append([f'aqueduct deck {xa}-{xb}', xm, int(yc[xm]), dz])
    return {'piers': len(piers), 'deck_sections': [[secs[i], secs[i + 1]] for i in range(0, len(secs), 2)]}


def build_camp_extras(cv, S=SPEC):
    """Hunters'-camp pieces round the courtyard edges (never in the spawn square + margin): a smithing lean-to with
    forge and anvil, a notice board, a covered well, a drying rack, crates and barrels, an alchemy table, low
    breached inner wall stubs (3 tall: not a step)."""
    E = S['camp_extras']
    g = 49
    x0, x1, y0, y1 = E['lean_to']                                       # back wall north, roof sloping south
    cv.box(x0, x1, y0, y0, g - 5, g - 1, C['timber'], 'timber')
    for x in (x0, x1):
        cv.box(x, x, y1, y1, g - 4, g - 1, C['timber'], 'timber')
    cv.box(x0, x1, y0, y1, g - 6, g - 6, C['roof'], 'roof')
    cv.box(x0, x1, y1, y1, g - 5, g - 5, C['roof'], 'roof')                            # eave board
    cv.box(x0 + 1, x0 + 3, y0 + 2, y0 + 4, g - 2, g - 1, C['stone'], 'prop')              # forge
    cv.box(x0 + 6, x0 + 7, y0 + 3, y0 + 3, g - 1, g - 1, (90, 90, 98), 'prop')           # anvil
    cv.interiors.append(['smithing lean-to', x0 + 5, y0 + 2, g])
    bx, by = E['notice']                                                # notice board: two posts and a board
    cv.box(bx, bx, by, by, g - 5, g - 1, C['timber'], 'timber')
    cv.box(bx + 3, bx + 3, by, by, g - 5, g - 1, C['timber'], 'timber')
    cv.box(bx, bx + 3, by, by, g - 5, g - 3, C['furn'], 'prop')
    wx, wy = E['well']                                                  # covered well
    for x in range(wx - 2, wx + 3):
        for y in range(wy - 2, wy + 3):
            if max(abs(x - wx), abs(y - wy)) == 2 and not (abs(x - wx) == 2 and abs(y - wy) == 2):
                cv.box(x, x, y, y, g - 2, g - 1, C['stone'], 'prop')
            elif max(abs(x - wx), abs(y - wy)) <= 1:
                cv.set(x, y, g, C['water'], 'water')
    for y in (wy - 2, wy + 2):
        cv.box(wx, wx, y, y, g - 6, g - 3, C['timber'], 'timber')
    cv.box(wx, wx, wy - 2, wy + 2, g - 6, g - 6, C['timber'], 'timber')
    cv.box(wx - 2, wx + 2, wy - 1, wy + 1, g - 7, g - 7, C['roof'], 'roof')
    x0, x1, y0 = E['drying_rack']
    cv.box(x0, x0, y0, y0, g - 4, g - 1, C['timber'], 'timber')
    cv.box(x1, x1, y0, y0, g - 4, g - 1, C['timber'], 'timber')
    cv.box(x0, x1, y0, y0, g - 4, g - 4, C['timber'], 'timber')
    for x in range(x0 + 1, x1, 2):
        cv.box(x, x, y0, y0, g - 3, g - 3, C['tent'], 'prop')
    for (x, y) in E['crates']:
        gbox(cv, x, x + 2, y, y + 2, 2, C['prop'], 'prop')
        gbox(cv, x, x + 1, y, y + 1, 3, C['prop'], 'prop')
    for (x, y) in E['barrels']:
        gbox(cv, x, x + 1, y, y + 1, 2, C['trunk'], 'prop')
    x0, x1, y0 = E['alchemy']
    cv.box(x0, x1, y0, y0 + 1, g - 2, g - 2, C['furn'], 'furniture')
    for x in (x0, x1):
        cv.box(x, x, y0, y0 + 1, g - 1, g - 1, C['furn'], 'furniture')
    for (a, b) in E['wall_stubs']:
        for (x, y) in seg_cells(a, b, 1.2):
            gbox(cv, x, x, y, y, 3, C['ruin'], 'ruin')


def build_bridge(cv, S=SPEC):
    """Stone footbridge on the axis over the pool: deck z 50 (2 thick), 2-tall parapets, 5 wide; arch fill down to
    the banks at the ends, open above the water in the middle (walk under along the shelves)."""
    bd = S['bridge']
    xa = bd['x'][0]
    col = cv.H[250]
    ys = [y for y in range(395, 480) if col[y] > bd['deck_z']]
    if not ys:
        return None
    y0, y1 = min(ys) - 1, max(ys) + 1
    yc, half = (y0 + y1) / 2.0, (y1 - y0) / 2.0
    dz = bd['deck_z']
    for y in range(y0, y1 + 1):
        zb = dz + 2 + int(round(10 * ((y - yc) / half) ** 2))
        for x in range(xa, 256):
            hb = int(cv.H[x, y])
            cv.box(x, x, y, y, dz, min(max(zb, dz + 1), hb - 1), C['stone'], 'bridge')
        cv.box(xa, xa, y, y, dz - 2, dz - 1, C['stone'], 'bridge')
    cv.interiors += [['footbridge deck', xa + 2, int(yc), dz], ['under the footbridge', xa + 2, int(yc),
                                                                  int(cv.H[xa + 2, int(yc)])]]
    return [y0, y1]


def cut_cascade(H, region, S=SPEC):
    """Stepped falls: a channel cut 3-6 into the south slope (x 240-247 and its mirror), treads 4 rows long with
    4-voxel risers, from a rock lip high on the slope down to a plunge pool joining the stream pool. Treads are
    painted water (region 4). Walkable downhill only; every tread drains to the pool (no trap)."""
    wf = S['waterfall']
    xa, xb = wf['x']
    out = {'cols': [xa, xb]}
    for x in range(xa, xb + 1):
        col = H[x].copy()
        ys = [y for y in range(400, 500) if col[y] >= 62]
        y0 = max(ys) + 1 if ys else 450                      # first dry row south of the pool
        y_lip = next((y for y in range(y0, 511) if col[y] <= wf['lip_z']), 500)
        for y in range(y0, y_lip + 1):
            if y - y0 < wf['plunge']:
                z = 63 if y - y0 < wf['plunge'] - 2 else 62
            else:
                raw = col[y] + wf['depth']
                k = (y - y0 - wf['plunge']) // wf['tread']
                z = min(62, int(col[y0 + wf['plunge'] + k * wf['tread']]) + wf['depth'])
                z = min(z, int(raw) + 2)
            H[x, y] = max(int(H[x, y]), z)
            region[x, y] = 4 if z < 62 else (4 if z == 63 else 3)
        out['lip_y'] = y_lip
    H[512 - xb:512 - xa + 1] = H[xa:xb + 1][::-1]
    region[512 - xb:512 - xa + 1] = region[xa:xb + 1][::-1]
    return out


def paint_cascade(cv, S=SPEC):
    """Water on the risers (the falling sheets) and a rock lip overhanging the top tread."""
    wf = S['waterfall']
    xa, xb = wf['x']
    n = 0
    lip = 0
    for x in range(xa, xb + 1):
        for y in range(420, 510):
            t, tn = int(cv.H[x, y]), int(cv.H[x, y - 1])
            if cv.mat[x, y, t] == cv.material('water') and tn > t + 1:
                for z in range(t, tn):
                    cv.set(x, y, z, C['water'], 'waterfall')
                    n += 1
            lip = max(lip, y if cv.mat[x, y, t] == cv.material('water') else 0)
    for x in range(xa - 1, xb + 2):                           # rock lip: a ledge jutting 2 over the top tread
        t = int(cv.H[x, lip + 1])
        cv.box(x, x, lip - 1, lip + 1, t - 2, t - 1, C['rock'], 'rock')
    return {'riser_voxels': n, 'lip_y': lip}


def build_sites(cv, S=SPEC):
    """Minor ruin sites in the fields between the outposts and the flanks, each unique (west; east by mirror):
    collapsed colonnade, toppled obelisk, broken stair to nowhere (climbable, top 9 above the ground: safe drop),
    roofless chapel, hunters' lookout platform (stair up, railings), monster-nest cave dug into the west cliff."""
    T = S['sites']
    g0 = 50
    rng = noise.rng('sites', S['layout_seed'])
    # collapsed colonnade on a stylobate, one column fallen, a lintel still spanning two columns
    x0, x1, y0, y1 = T['colonnade']['box']
    gbox(cv, x0, x1, y0, y1, 1, C['stone'], 'ruin')
    cols = list(range(x0 + 2, x1 - 2, T['colonnade']['step']))
    hs = []
    for i, cx in enumerate(cols):
        h = [11, 4, 8, 12, 3, 9][i % 6]
        hs.append(h)
        gbox(cv, cx, cx + 2, y0 + 2, y0 + 4, 1 + h, C['ruin'], 'ruin')
    a = hs.index(max(hs))
    if a + 1 < len(cols) and hs[a + 1] >= 8:
        g = int(cv.H[cols[a], y0 + 2])
        cv.box(cols[a], cols[a + 1] + 2, y0 + 2, y0 + 4, g - 1 - min(hs[a], hs[a + 1]) - 1,
               g - 1 - min(hs[a], hs[a + 1]), C['ruin'], 'ruin')
    drum(cv, cols[1] - 1, y1 + 4, 10, 1.6, 'x')
    # toppled obelisk: plinth, shaft lying across the grass, broken tip
    ob = T['obelisk']
    bx, by = ob['base']
    gbox(cv, bx - 2, bx + 2, by - 2, by + 2, 3, C['stone'], 'ruin')
    gcells(cv, seg_cells(ob['shaft'][0], ob['shaft'][1], 3.2), 3, C['ruin'], 'ruin')
    tx, ty = ob['tip']
    gbox(cv, tx - 1, tx + 1, ty - 1, ty + 1, 2, C['ruin'], 'ruin')
    # broken stair to nowhere: 9 steps up to a broken landing (top 9 above the ground: safe drop), wall stub behind
    st = S['sites']['stair']
    sx, sy0, sy1 = st['x'], st['y'][0], st['y'][1]
    g0 = int(cv.H[sx - 1, sy0])
    straight_stair(cv, sx, sy0, sy1, g0, st['rise'], 1, C['ruin'], mat='ruin')
    lx = sx + st['rise']
    cv.box(lx, lx + 2, sy0, sy1, g0 - st['rise'], g0 - 1, C['ruin'], 'ruin')
    cv.carve(lx, lx + 2, sy0, sy1, g0 - st['rise'] - 3, g0 - st['rise'] - 1)
    cv.box(lx + 3, lx + 3, sy0 - 2, sy1 + 2, g0 - st['rise'] - 4, g0 - 1, C['ruin'], 'ruin')   # wall stub
    cv.carve(lx + 3, lx + 3, sy0 - 2, sy0 - 1, g0 - st['rise'] - 4, g0 - st['rise'] - 2)
    cv.interiors.append(['stair to nowhere', lx + 1, sy0 + 1, g0 - st['rise']])
    # roofless chapel: nave + apse, broken walls 5-8 tall, west door, side door, windows, benches and an altar
    ch = T['chapel']
    nx0, nx1, ny0, ny1 = ch['nave']
    ax, ay, ar = ch['apse']
    w, h = int(ax + ar) - nx0 + 2, ny1 - ny0 + 1
    M = np.zeros((w, h), bool)
    M[:nx1 - nx0 + 1, :] = True
    xs, ys = np.meshgrid(np.arange(w) + nx0 + 0.5, np.arange(h) + ny0 + 0.5, indexing='ij')
    M |= (np.hypot(xs - ax, ys - ay) <= ar) & (xs >= nx1)
    cy = (ny0 + ny1) // 2
    g0 = 50
    ruin_building(cv, M, (nx0, ny0), g0, 1, 6, 'roofless chapel',
                  doors=[(nx0, nx0, cy - 1, cy + 1, 0, 5), (nx0 + 8, nx0 + 10, ny1, ny1, 0, 4)],
                  collapse=(nx0 + 12, nx0 + 15, ny0, ny0 + 1), parapet=(5, 8), seed=S['layout_seed'] + 7,
                  interior_pts=[(nx0 + 5, cy)])
    for bxx in range(nx0 + 4, nx1 - 3, 3):
        cv.box(bxx, bxx, ny0 + 2, cy - 2, g0 - 1, g0 - 1, C['furn'], 'furniture')
        cv.box(bxx, bxx, cy + 2, ny1 - 2, g0 - 1, g0 - 1, C['furn'], 'furniture')
    cv.box(int(ax), int(ax) + 1, cy - 1, cy + 1, g0 - 2, g0 - 1, C['stone'], 'furniture')
    # hunters' lookout: timber deck 10 up on four posts, railings, a stair up from the west
    lk = T['lookout']
    dx0, dx1, dy0, dy1 = lk['deck']
    g0 = int(cv.H[dx0 - lk['h'] - 1, (dy0 + dy1) // 2])
    dz = g0 - lk['h']
    for (px, py) in ((dx0, dy0), (dx1, dy0), (dx0, dy1), (dx1, dy1)):
        cv.box(px, px, py, py, dz + 1, int(cv.H[px, py]) - 1, C['timber'], 'timber')
    cv.box(dx0, dx1, dy0, dy1, dz, dz, C['floor'], 'timber')
    for x in range(dx0, dx1 + 1):
        for y in (dy0, dy1):
            cv.box(x, x, y, y, dz - 2, dz - 1, C['timber'], 'timber')
    for y in range(dy0, dy1 + 1):
        cv.box(dx1, dx1, y, y, dz - 2, dz - 1, C['timber'], 'timber')
    sy = (dy0 + dy1) // 2
    straight_stair(cv, dx0 - lk['h'], sy - 1, sy + 1, g0, lk['h'], 1, C['stair'], mat='stair')
    cv.carve(dx0, dx0, sy - 1, sy + 1, dz - 3, dz - 1)
    cv.interiors.append(['hunters lookout', dx0 + 3, sy, dz])
    # monster-nest cave: a tunnel dug west into the cliff from the foothill line, a chamber at the end
    cvx = T['cave']
    yc = cvx['y']
    row = cv.H[:, yc].astype(int)
    mx = next(x for x in range(cvx['search_x'][1], cvx['search_x'][0], -1) if row[x - 3] <= row[x] - 6)
    fz = int(row[mx])
    for x in range(mx - cvx['len'], mx + 1):
        for y in range(yc - 2, yc + 3):
            cv.carve(x, x, y, y, fz - 4, fz - 1)
            cv.set(x, y, fz, C['dirt'], 'cave')
    chx = mx - cvx['len'] - 4
    for x in range(chx - 4, chx + 5):
        for y in range(yc - 4, yc + 5):
            if (x - chx) ** 2 + (y - yc) ** 2 <= 22:
                cv.carve(x, x, y, y, fz - 5, fz - 1)
                cv.set(x, y, fz, C['dirt'], 'cave')
    for (dx, dy) in ((-2, -1), (-2, 1), (-1, 2), (1, 2), (2, 1), (2, -1), (-1, -2), (1, -2)):
        cv.set(chx + dx, yc + dy, fz - 1, C['root'], 'nest')                # nest ring (1 tall)
    cv.interiors.append(['monster nest cave', chx, yc, fz])
    return {'cave_mouth': [mx, yc, fz], 'cave_chamber': [chx, yc]}


def site_masks(cv, S=SPEC):
    T = S['sites']
    boxes = [T['colonnade']['box'], (140, 176, 104, 130), (T['stair']['x'] - 2, T['stair']['x'] + T['stair']['rise'] + 5,
             T['stair']['y'][0] - 3, T['stair']['y'][1] + 3), T['chapel']['nave'] and
             (T['chapel']['nave'][0], int(T['chapel']['apse'][0] + T['chapel']['apse'][2]) + 1, T['chapel']['nave'][2],
              T['chapel']['nave'][3]), (T['lookout']['deck'][0] - T['lookout']['h'] - 1, T['lookout']['deck'][1],
                                        T['lookout']['deck'][2], T['lookout']['deck'][3]),
             (T['crag']['c'][0] - T['crag']['r'][0] - 4, T['crag']['c'][0] + T['crag']['r'][0] + 14,
              T['crag']['c'][1] - T['crag']['r'][1] - 2, T['crag']['c'][1] + T['crag']['r'][1] + 2),
             (S['waterfall']['x'][0] - 3, S['waterfall']['x'][1] + 3, 440, 511)]
    for (x0, x1, y0, y1) in boxes:
        cv.no_prop(x0 - 3, x1 + 3, y0 - 3, y1 + 3, KEEP_MISC)


def build_rune_circle(cv, S=SPEC):
    rc = S['rune_circle']
    cx, cy = rc['c']
    fx, fy = cx + 0.5, cy + 0.5
    rng = noise.rng('runes', S['layout_seed'])
    for a in rc['stones_deg']:
        sx = int(math.floor(fx + rc['r'] * math.cos(math.radians(a))))
        sy = int(math.floor(fy + rc['r'] * math.sin(math.radians(a))))
        h = int(rng.integers(rc['stone_h'][0], rc['stone_h'][1] + 1))
        gbox(cv, sx - 1, min(255, sx), sy - 1, sy + 1, h, C['rune'], 'rune')
    gbox(cv, 254, 255, cy - 1, cy + 1, 1, C['stone'], 'rune')                      # altar slab
    cv.interiors.append(['rune circle', 251, cy, int(cv.H[251, cy])])


def build_mushrooms(cv, S=SPEC):
    """Giant mushrooms in clusters in the hollow, varied height and tilt (stem leans by up to 2 over its height;
    cap bottom >= 5 above the ground)."""
    out = []
    for (x, y, r, h, tx, ty) in S['mushrooms']:
        g = int(cv.H[x, y])
        if g > 52:
            continue
        sr = 1.3 + 0.12 * r
        for k in range(h):
            f = k / max(h - 1, 1)
            cv.cylinder(x + 0.5 + tx * f, y + 0.5 + ty * f, sr * (1.15 - 0.2 * f), g - 1 - k, g - 1 - k, C['stem'],
                        'mushroom')
        cv.ellipsoid(x + 0.5 + tx, y + 0.5 + ty, g - h, r, r * 0.9, 2.4 + 0.15 * r, C['mushroom'], 'mushroom')
        out.append((x, y, r, h))
    return out


def build_crest_walls(cv, geo, S=SPEC):
    """Broken elder walls along the cliff crest: a continuous 2-thick wall line following the crest contour,
    3 tall with crenel stubs (+1 on alternate pairs), cut by collapsed sections (low-frequency noise)."""
    cw = S['ring']['crest_wall']
    u = geo['ring_u']
    line = (u >= cw['band_u'][0]) & (u <= cw['band_u'][1]) & (X <= 255)
    seg = noise.fbm2((512, 512), cw['cell'], 2, 'crest_wall', S['layout_seed']) > cw['keep']
    k = 0
    if S.get('v11'):                                         # collapsed sections: rubble chutes down the face
        for (a, b) in S['ring']['v11']['chutes']:
            for (x, y) in seg_cells(a, b, 3.4):
                if 0 <= x <= 255 and 0 <= y <= 511 and int(cv.H[x, y]) > S['z']['min_solid_z'] + 2:
                    if noise.hash3(x, y, 0, 33) < 0.75:
                        gbox(cv, x, x, y, y, 1, C['rock'], 'rubble')
            line &= ~(np.hypot(X + 0.5 - a[0], Y + 0.5 - a[1]) < 7)
    for x, y in zip(*np.nonzero(line & seg)):
        g = int(cv.H[x, y])
        h = cw['h'][0] + (1 if ((x + y) // 2) % 2 == 0 else 0)
        h = min(h, g - S['z']['min_solid_z'])
        if h >= 2:
            cv.box(x, x, y, y, g - h, g - 1, C['ruin'], 'crest_wall')
            k += 1
    return k


def set_masks(cv, geo, S=SPEC):
    sp = S['spawn']
    (bx, by), h, m = sp['base'], sp['half'], sp['margin']
    cv.no_prop(bx - h - m, bx + h + m, by - h - m, by + h + m, KEEP_SPAWN)
    a = S['anchor']
    cv.no_prop(a['x'][0] - 2, a['x'][1] + 2, a['y'][0] - 2, a['y'][1] + 2, KEEP_ANCHOR)
    cv.no_prop(139, 211, 236, 276, KEEP_FRONT)                          # whole zone-rule front band
    cv.no_prop(212, 255, 236, 276, KEEP_UNDER)
    cv.keep[geo['outpost']] |= KEEP_LANE
    st = np.zeros((512, 512), bool)
    st |= geo['plaza'] | geo['amphi']
    st |= ndi.binary_dilation(geo['stream'] & (cv.H >= 60), iterations=2)
    cv.keep[st] |= KEEP_STRUCT
    for (x0, x1, y0, y1) in (S['spire']['box'], (S['library']['wing'][0] - 4, 255, S['library']['box'][2] - 4,
                                                  S['library']['box'][3] + 4),
                             (238, 255, 180, 240), (238, 255, 380, 470),
                             (S['gate_tower']['box'][0] - 2, S['gate_tower']['box'][1] + 2,
                              S['gate_tower']['box'][2] - 2, S['gate_tower']['box'][3] + 2),
                             (S['bastion']['box'][0] - 2, S['bastion']['box'][1] + 2, S['bastion']['box'][2] - 2,
                              S['bastion']['box'][3] + 2)):
        cv.no_prop(x0 - 3, x1 + 3, y0 - 3, y1 + 3, KEEP_MISC)
    cv.keep[(np.abs(Y - aqueduct_line(S)[X]) <= S['aqueduct']['half_w'] + 5) & (X <= 255)] |= KEEP_MISC
    for (x, y, r, hh, _tx, _ty) in S['mushrooms']:
        cv.no_prop(x - r - 3, x + r + 3, y - r - 3, y + r + 3, KEEP_MISC)


def free_for_prop(cv, x0, x1, y0, y1, keep_mask=0xFF):
    """No keep flag and nothing above the terrain in the box."""
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(255, x1), min(511, y1)
    if x0 > x1 or (cv.keep[x0:x1 + 1, y0:y1 + 1] & keep_mask).any():
        return False
    sub = cv.solid[x0:x1 + 1, y0:y1 + 1]
    hh = cv.H[x0:x1 + 1, y0:y1 + 1]
    zz = np.arange(64)[None, None, :]
    return not (sub & (zz < hh[:, :, None])).any()


def free_low(cv, x0, x1, y0, y1, h):
    """Nothing solid within h voxels above the terrain in the box (crowns higher up may overlap)."""
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(255, x1), min(511, y1)
    sub = cv.solid[x0:x1 + 1, y0:y1 + 1]
    hh = cv.H[x0:x1 + 1, y0:y1 + 1].astype(int)
    zz = np.arange(64)[None, None, :]
    return not (sub & (zz < hh[:, :, None]) & (zz >= hh[:, :, None] - h)).any()


def plant_pinned(cv, S=SPEC):
    """Trees the zone rules depend on (spawn cover, rear backdrop): positions fixed by the layout."""
    out = []
    for (x, y, r, h) in S['rear_trees'] + S['cover_trees'] + S['plaza_trees']:
        broadleaf(cv, x, y, r, h)
        out.append((x, y, r, h, 'broadleaf'))
    return out


def _try_tree(cv, rng, x, y, margin=3, grove=False):
    """One stand-in tree. Lone trees keep `margin` clear round the whole crown; grove members only need their
    trunk area clear (crowns may touch: they stay >= 5 above the ground), but no crown may reach a keep zone."""
    kind = 'fir' if rng.random() < 0.4 else 'broadleaf'
    r = int(rng.integers(3, 6)) if kind == 'broadleaf' else int(rng.integers(2, 5))
    if 150 <= x <= 255 and 130 <= y <= 382 and r < 3:            # centre zone: room-sized pieces only
        r = 3
    h = int(rng.integers(10, 17))
    R = r + 2
    if not (R + margin <= x <= 250 - R - margin and R + margin <= y <= 511 - R - margin):
        return None
    Hs = cv.H[x - R:x + R + 1, y - R:y + R + 1]
    if Hs.max() > 58 or Hs.max() - Hs.min() > 4:
        return None
    if (cv.keep[x - R - 1:x + R + 2, y - R - 1:y + R + 2]).any():
        return None
    if grove and kind == 'broadleaf':
        if not free_low(cv, x - 3, x + 4, y - 3, y + 4, 6):
            return None
    elif not free_for_prop(cv, x - R - (0 if grove else margin), x + R + (0 if grove else margin),
                           y - R - (0 if grove else margin), y + R + (0 if grove else margin)):
        return None
    if kind == 'fir':
        fir(cv, x, y, r, h)
    else:
        broadleaf(cv, x, y, r, h)
    return (x, y, r, h, kind)


def _try_outcrop(cv, rng, x, y):
    rx, ry, rz = float(rng.uniform(2.5, 5)), float(rng.uniform(2.5, 4.5)), float(rng.uniform(1.5, 3.5))
    R = int(math.ceil(max(rx, ry)))
    if not (R + 4 <= x <= 250 - R and R + 4 <= y <= 507 - R):
        return None
    Hs = cv.H[x - R:x + R + 1, y - R:y + R + 1]
    if Hs.max() > 58 or Hs.max() - Hs.min() > 3:
        return None
    if not free_for_prop(cv, x - R - 3, x + R + 3, y - R - 3, y + R + 3):
        return None
    cv.ellipsoid(x + 0.5, y + 0.5, int(cv.H[x, y]), rx, ry, rz, C['rock'], 'rock')
    return (x, y, round(rx, 1), round(ry, 1), round(rz, 1))


def scatter(cv, geo, S=SPEC, veg_seed=None):
    """Layout seed: rock outcrops on the fields. Veg seed (OS seed per build, saved): every vegetation stand-in -
    groves of broadleaf and fir (centres, member counts, positions), lone trees, firs on the ring terraces."""
    sc = S['scatter']
    seed = S['layout_seed']
    rng = noise.rng('scatter', seed)
    vseed = seed if veg_seed is None else int(veg_seed)
    vrng = noise.rng('veg_scatter', vseed)
    trees, rocks = [], []

    def grid(spacing, jitter, tag, sd):
        r = noise.rng(tag, sd)
        for gx in range(6, 252, spacing):
            for gy in range(6, 506, spacing):
                yield (gx + int(r.integers(-jitter, jitter + 1)), gy + int(r.integers(-jitter, jitter + 1)))

    for (x, y) in grid(sc['field_spacing'], sc['field_jitter'], 'grid_rock', seed):
        if 0 <= x <= 250 and 0 <= y <= 511 and 44 <= cv.H[x, y] <= 56 and rng.random() < 0.28:
            o = _try_outcrop(cv, rng, x, y)
            if o:
                rocks.append(o)
    # groves, not an even scatter: a smooth density field from the veg seed; dense stands where it is high,
    # open clearings with a rare lone tree elsewhere
    dens = noise.fbm2((512, 512), sc['forest_cell'], 2, 'forest_density', vseed)
    lo, hi = sc['grove_density']
    for (x, y) in grid(sc['grove_spacing'], sc['grove_jitter'], 'grid_field_veg', vseed):
        if not (0 <= x <= 250 and 0 <= y <= 511) or not (44 <= cv.H[x, y] <= 57):
            continue
        d = float(dens[x, y])
        if d >= lo:
            if vrng.random() < hi:
                p = _try_tree(cv, vrng, x, y, grove=True)
                if p:
                    trees.append(p)
        elif vrng.random() < sc['lone_p']:
            p = _try_tree(cv, vrng, x, y)
            if p:
                trees.append(p)
    ring_n = 0
    for (x, y) in grid(12, 4, 'grid_ring', vseed):
        if not (3 <= x <= 248 and 3 <= y <= 508) or not (17 <= cv.H[x, y] <= 46):
            continue
        loc = cv.H[x - 1:x + 2, y - 1:y + 2]
        if loc.max() - loc.min() > 3 or vrng.random() < 0.25:
            continue
        r = int(vrng.integers(2, 4))
        h = min(int(vrng.integers(9, 15)), int(cv.H[x, y]) - 8)
        if h >= 6 and free_for_prop(cv, x - r - 2, x + r + 2, y - r - 2, y + r + 2):
            fir(cv, x, y, r, h)
            trees.append((x, y, r, h, 'fir'))
            ring_n += 1
    return {'trees': len(trees), 'ring_firs': ring_n, 'outcrops': len(rocks), 'tree_list': trees,
            'veg_seed': vseed}


# =============================================================================================== cleanup passes

def fill_nooks(cv, rounds=10):
    """Terrain-top columns more than 1 below all 4 neighbouring tops are raised with rock to the lowest neighbour
    + 1 (no drop-in pockets between a terrace step and a tree stand-in)."""
    n = 0
    for _ in range(rounds):
        top = np.argmax(cv.solid, axis=2)
        nb = np.stack([np.roll(top, 1, 0), np.roll(top, -1, 0), np.roll(top, 1, 1), np.roll(top, -1, 1)]).max(0)
        pit = (top > nb + 1) & (top == cv.H) & (cv.H < 62)
        pit[:2] = pit[-2:] = False
        pit[:, :2] = pit[:, -2:] = False
        pit[256:] = False
        if not pit.any():
            break
        for x, y in zip(*np.nonzero(pit)):
            z = int(nb[x, y]) + 1
            cv.box(x, x, y, y, z, int(cv.H[x, y]) - 1, C['rock'], 'rock')
            cv.H[x, y] = z
            n += 1
    return n


def _mirrored(a):
    b = a.copy()
    b[257:] = a[255:0:-1]
    b[256] = a[255]
    return b


def trap_cells(cv):
    """The kit's trap model (babel_checks: safe graph from both spawns, walk back to the anchor set, terrain band
    +-3) on a mirrored copy. Returns the trap cells (x, y, z)."""
    from aosmap.kit.babel_checks import Nav
    from aosmap.kit.params import BABEL_DEFAULT as P
    solid = _mirrored(cv.solid)
    Hm = _mirrored(cv.H.astype(int))
    nav = Nav(solid)
    h = P['spawn_half']
    src = np.concatenate([nav.nodes_in(b[0] - h, b[0] + h, b[1] - h, b[1] + h, 0, 62) for b in P['bases']])
    fwd = np.isfinite(nav.dist_from(src))
    (x0, x1), (y0, y1) = P['platform_x'], P['platform_y']
    anc = nav.nodes_in(min(b[0] for b in P['bases']) - h, max(b[0] for b in P['bases']) + h, y0 - 40, y1 + 40,
                       0, 62)[::5]
    back = np.isfinite(nav.dist_from(anc, reverse=True))
    p = nav.xyz
    landish = np.abs(p[:, 2] - Hm[p[:, 0], p[:, 1]]) <= 3
    return p[landish & fwd & ~back]


def clear_tree_traps(cv, trees, rounds=4):
    """Seeded trees can close a pocket against a terrace step or a wall, and crest-wall runs can close one on a
    cliff top: delete crest-wall columns within 3 of a trap cell and every seeded stand-in within reach of one,
    repeat. Pinned trees are not in `trees` and are never removed. Returns (trees removed, crest columns removed)."""
    vid = cv.material('veg')
    cid = cv.material('crest_wall')
    removed = crest = 0
    for _ in range(rounds):
        tp = trap_cells(cv)
        if not len(tp):
            break
        tx = np.minimum(tp[:, 0], 512 - tp[:, 0])
        ty = tp[:, 1]
        for (x, y) in set(zip(tx.tolist(), ty.tolist())):
            sl = (slice(max(0, x - 3), min(256, x + 4)), slice(max(0, y - 3), y + 4))
            m = cv.mat[sl] == cid
            if m.any():
                cv.solid[sl][m] = False
                cv.mat[sl][m] = 0
                crest += int(m.any(2).sum())
        drop = [q for q in trees if np.any((np.abs(tx - q[0]) <= q[2] + 5) & (np.abs(ty - q[1]) <= q[2] + 5))]
        if not drop:
            break
        for q in drop:
            x, y, r = q[0], q[1], q[2]
            sl = (slice(max(0, x - r - 3), x + r + 4), slice(max(0, y - r - 3), y + r + 4))
            m = cv.mat[sl] == vid
            cv.solid[sl][m] = False
            cv.mat[sl][m] = 0
            trees.remove(q)
            removed += 1
    return removed, crest


def break_flats(cv, S=SPEC, target=22, rounds=40):
    """While a featureless flat square larger than `target` exists (same metric as ev_checks.featureless), put a
    1-tall feature pad (reserved for an art-pass one-off: fern bed, mossy slab, hunters' gear, ...) near its centre.
    Pads are 1 tall: not objects for the zone rules, not a climbing aid."""
    import ev_checks
    rng = noise.rng('break_flats', S['layout_seed'])
    pads = []
    best = 0
    kinds = ['fern bed', 'mossy slab', 'fallen stones', 'hunters gear', 'flower patch']
    for _ in range(rounds):
        okw = ev_checks.featureless_ok_mask(cv.solid, cv.H, S)
        best, where, tops = ev_checks.largest_flat_squares(_mirrored(cv.H.astype(int)), _mirrored(okw),
                                                            min_report=target + 1, n_report=12)
        if best <= target:
            break
        done = 0
        for v, x, y in tops:
            cx, cy = x - v // 2, y - v // 2
            cand = sorted(((px, py) for px in range(x - v + 2, min(x, 249), 2) for py in range(y - v + 2, y, 2)),
                          key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)
            for (px, py) in cand:
                if px < 4 or py < 4 or py > 503:
                    continue
                if not free_for_prop(cv, px - 2, px + 6, py - 2, py + 6, keep_mask=0xFF & ~KEEP_LANE):
                    continue
                Hs = cv.H[px:px + 5, py:py + 5]
                if Hs.max() != Hs.min() or Hs.max() > 60:
                    continue
                gbox(cv, px, px + 4, py, py + 4, 1, C['pad'], 'pad')
                pads.append({'kind': kinds[int(rng.integers(len(kinds)))], 'box': [px, px + 4, py, py + 4]})
                done += 1
                break
        if not done:
            break
    return {'feature_pads': pads, 'largest_side_after_west': int(best)}


# =============================================================================================== top level

def build_west(S=SPEC, veg_seed=None):
    """Everything except the mirror. veg_seed places the vegetation stand-ins. Returns (canvas, report)."""
    cv = Canvas(S['name'])
    H, region, geo = terrain(S)
    building_pads(H, S)
    paint_terrain(cv, H, region)
    set_masks(cv, geo, S)
    rep = {}
    rep['crest_wall_columns'] = build_crest_walls(cv, geo, S)
    rep['wall_columns'] = build_walls(cv, S)
    build_gate_tower(cv, S)
    build_bastion(cv, S)
    build_hall(cv, S)
    build_camp(cv, S)
    build_camp_extras(cv, S)
    build_front(cv, S)
    if S.get('v11'):
        rep['under_v11'] = build_under_head_v11(cv, S)
    else:
        build_under(cv, S)
    rep['spire'] = build_spire(cv, S)
    build_plaza(cv, S)
    if S.get('v11'):
        rep['queen_v11'] = build_queen_v11(cv, S)
    else:
        build_queen(cv, S)
    build_library(cv, S)
    build_amphi(cv, S)
    rep['aqueduct'] = build_aqueduct(cv, S)
    rep['bridge_y'] = build_bridge(cv, S)
    rep['cascade'] = paint_cascade(cv, S)
    rep['sites'] = build_sites(cv, S)
    if S.get('v11'):
        rep['lanterns'] = build_lanterns_v11(cv, S)
    site_masks(cv, S)
    build_rune_circle(cv, S)
    rep['mushrooms'] = build_mushrooms(cv, S)
    pinned = plant_pinned(cv, S)
    sc = scatter(cv, geo, S, veg_seed)
    sc['nooks_filled'] = fill_nooks(cv)
    sc['trap_trees_removed'], sc['trap_crest_wall_columns_removed'] = clear_tree_traps(cv, sc['tree_list'])
    bf = break_flats(cv, S)
    if S.get('v11'):                                     # late passes (nook rock, pads) can sit beside a sculpture
        rep['late_seal'] = seal_entries(cv, (232, 255, 176, 242), ('statue',)) +             seal_entries(cv, (240, 255, 240, 272), ('statue',))
        rep['nav_seal'] = seal_nav(cv, (232, 255, 176, 242), ('statue',)) +             seal_nav(cv, (240, 255, 240, 272), ('statue',))
    sc['feature_pads'] = bf['feature_pads']
    sc['largest_flat_after_west'] = bf['largest_side_after_west']
    sc['pinned_trees'] = len(pinned)
    sc['tree_list'] = sc['tree_list'] + pinned
    rep['scatter'] = sc
    return cv, rep


# =============================================================================================== v1.1 sculpture

def _g(cv, x, y):
    return int(cv.H[min(255, int(x)), int(y)])


def _rest(cv, cx, cy, rx, ry, rz, c, mat, lift=0.0):
    """Ellipsoid resting on the local ground (bottom touching it): every column top is >= rz above the ground."""
    g = _g(cv, cx, cy)
    cv.ellipsoid(cx, cy, g - rz - lift, rx, ry, rz, c, mat)
    return g


def prune_steps(cv, box, mats, rounds=6):
    """Remove 1-tall columns of the given materials (a 1-voxel step onto a sculpture); repeat. Returns removed."""
    x0, x1, y0, y1 = box
    ids = [cv.materials[m] for m in mats if m in cv.materials]
    n = 0
    for _ in range(rounds):
        hit = 0
        for x in range(x0, min(255, x1) + 1):
            for y in range(y0, y1 + 1):
                t = int(np.argmax(cv.solid[x, y]))
                g = int(cv.H[x, y])
                if t == g - 1 and cv.mat[x, y, t] in ids:
                    cv.clear(x, y, t)
                    hit += 1
        n += hit
        if not hit:
            break
    return n


def unclimb(cv, box, mats, rounds=8):
    """Make a sculpture unwalkable on top: on a mirrored copy, find standable cells reachable on foot from a spawn
    (safe graph) whose floor voxel is one of `mats` inside `box` (west coordinates), clear those voxels, repeat.
    Edges that a step (or a plaza step next to them) made climbable are cut back. Returns voxels removed."""
    from aosmap.kit.babel_checks import Nav
    from aosmap.kit.params import BABEL_DEFAULT as P
    ids = [cv.materials[m] for m in mats if m in cv.materials]
    x0, x1, y0, y1 = box
    n = 0
    for _ in range(rounds):
        solid = _mirrored(cv.solid)
        nav = Nav(solid)
        h = P['spawn_half']
        src = np.concatenate([nav.nodes_in(b[0] - h, b[0] + h, b[1] - h, b[1] + h, 0, 62) for b in P['bases']])
        d = nav.dist_from(src)
        p = nav.xyz[np.isfinite(d)]
        xw = np.minimum(p[:, 0], 512 - p[:, 0])
        sel = (xw >= x0) & (xw <= x1) & (p[:, 1] >= y0) & (p[:, 1] <= y1)
        hit = 0
        for (x, y, z) in zip(xw[sel], p[sel, 1], p[sel, 2]):
            x = int(min(x, 255))
            if cv.solid[x, y, z] and cv.mat[x, y, z] in ids:
                cv.clear(x, y, z)
                hit += 1
        n += hit
        if not hit:
            break
    return n


def seal_entries(cv, box, mats, c=None, rounds=12):
    """Make a sculpture unwalkable on top without eating it: wherever a sculpture column's top is within one step
    of the floor of a neighbouring non-sculpture column (terrain, rubble, another object), raise that column to two
    above that floor (a carved lip). Repeat until stable. Returns voxels added."""
    ids = [cv.materials[m] for m in mats if m in cv.materials]
    x0, x1, y0, y1 = box
    c = c or C['ruin']
    n = 0
    for _ in range(rounds):
        top = np.argmax(cv.solid, axis=2)
        hit = 0
        for x in range(max(1, x0), min(255, x1) + 1):
            for y in range(y0, y1 + 1):
                t = int(top[x, y])
                if cv.mat[x, y, t] not in ids:
                    continue
                for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    nx_ = nx if nx <= 255 else 510 - nx
                    tn = int(top[nx_, ny])
                    if cv.mat[nx_, ny, tn] in ids:
                        continue
                    if t >= tn - 1:
                        for z in range(tn - 2, t):
                            cv.set(x, y, z, c, mats[0])
                        hit += tn - 2 - t if tn - 2 < t else 0
                        t = tn - 2
                        hit += 1
        n += hit
        if not hit:
            break
    return n


def seal_nav(cv, box, mats, c=None, rounds=8):
    """Graph-exact sealing: on a mirrored copy, find every move of the safe nav graph from a reachable non-sculpture
    floor onto a sculpture floor inside `box`; raise that sculpture column to 2 above the source floor when there is
    air for it, otherwise (an overhang, e.g. under the knee arch) clear the low sculpture voxels down to the ground.
    Repeat until no entry is left. Returns the number of entries fixed."""
    from aosmap.kit.babel_checks import Nav
    from aosmap.kit.params import BABEL_DEFAULT as P
    ids = [cv.materials[m] for m in mats if m in cv.materials]
    c = c or C['ruin']
    x0, x1, y0, y1 = box
    fixed = 0
    for _ in range(rounds):
        solid, mat = _mirrored(cv.solid), _mirrored(cv.mat)
        nav = Nav(solid)
        h = P['spawn_half']
        src = np.concatenate([nav.nodes_in(b[0] - h, b[0] + h, b[1] - h, b[1] + h, 0, 62) for b in P['bases']])
        reach = np.isfinite(nav.dist_from(src))
        p = nav.xyz
        is_s = np.isin(mat[p[:, 0], p[:, 1], p[:, 2]], ids)
        G = nav.G.tocoo()
        e = reach[G.row] & ~is_s[G.row] & is_s[G.col]
        hit = 0
        done = set()
        for r_, c_ in zip(G.row[e], G.col[e]):
            sx, sy, sz = p[r_]
            tx, ty, tz = (int(v) for v in p[c_])
            xw = int(min(tx, 512 - tx)) if tx >= 256 else tx
            xw = min(xw, 255)
            if not (x0 <= xw <= x1 and y0 <= ty <= y1) or (xw, ty) in done:
                continue
            done.add((xw, ty))
            new_top = int(sz) - 2
            if new_top < tz and not cv.solid[xw, ty, new_top:tz].any():
                for z in range(new_top, tz):
                    cv.set(xw, ty, z, c, mats[0])
            else:
                g = int(cv.H[xw, ty])
                for z in range(tz, g):
                    if cv.mat[xw, ty, z] in ids:
                        cv.clear(xw, ty, z)
            hit += 1
        fixed += hit
        if not hit:
            break
    return fixed


def build_lanterns_v11(cv, S=SPEC):
    """v1.1: a few lantern posts beside the worn paths between the camps and the plaza (1x1 post 4 tall, lantern
    block on top, 2 off the path line, never in a keep zone, never next to anything standing)."""
    out = []
    for line in S['art']['paths']:
        for (ax, ay), (bx, by) in zip(line, line[1:]):
            L = math.hypot(bx - ax, by - ay)
            if L < 24:
                continue
            t = 0.5
            px, py = ax + (bx - ax) * t, ay + (by - ay) * t
            nx, ny = -(by - ay) / L, (bx - ax) / L
            x, y = int(round(px + 3 * nx)), int(round(py + 3 * ny))
            if not (2 <= x <= 250) or cv.keep[x - 2:x + 3, y - 2:y + 3].any():
                continue
            if not free_for_prop(cv, x - 2, x + 2, y - 2, y + 2, keep_mask=0):
                continue
            g = int(cv.H[x, y])
            cv.box(x, x, y, y, g - 4, g - 1, C['timber'], 'lantern')
            cv.set(x, y, g - 5, (200, 160, 90), 'lantern')
            out.append((x, y, g - 5))
    return out


def build_queen_v11(cv, S=SPEC):
    """v1.1 fallen elder-queen: a colossal reclining figure of rounded masses on the axis (head north, feet south).
    Head 10 across (chin, brow, nose ridge, hollow eyes, mouth), a crown of separate tall points (one snapped and
    lying by the head), a neck break (4-wide rubble gap you walk through), rounded shoulders above a rising chest, a
    dipping waist, hips, both knees drawn up as arches you walk under (>= 3 air), shins, upturned feet, arms along
    the body ending in open palm-up hands with finger ridges, robe drapery as 2-3 tall ridges flowing onto the plaza,
    a broken staff lying across. Everything rests on the ground (no 1-tall edge: prune_steps), so the figure is not
    walkable on top; heights 3-10 above the plaza."""
    q = S['queen11']
    W = C['ruin']
    X0 = 256.0                                                         # axis (kit ellipsoid: integer coordinates)
    hy = q['head_y']
    gh = _rest(cv, X0, hy, 5.0, 5.5, 4.2, W, 'statue')                 # head
    _rest(cv, X0, hy + 5.0, 2.6, 2.0, 2.8, W, 'statue')                # chin
    def top(x, y):
        return int(np.argmax(cv.solid[x, y]))
    for y in range(hy - 2, hy + 3):                                    # nose ridge
        t = top(255, y)
        cv.set(255, y, t - 1, W, 'statue')
    for x in range(251, 256):                                          # brow
        t = top(x, hy - 3)
        cv.set(x, hy - 3, t - 1, W, 'statue')
    for x in (252, 253):                                               # hollow eyes
        t = top(x, hy - 1)
        cv.carve(x, x, hy - 1, hy - 1, t, t + 1)
    for x in (254, 255):                                               # mouth
        t = top(x, hy + 4)
        cv.carve(x, x, hy + 4, hy + 4, t, t)
    for (x, h) in q['crown_points']:                                   # crown points on the north rim
        t = top(x, hy - 5)
        cv.box(x, x, hy - 5, hy - 5, t - h, t, W, 'statue')
    sx, sy0 = q['snapped_point']
    gbox(cv, sx, sx, sy0, sy0 + 3, 2, W, 'statue')                     # a snapped crown point lying by the head
    # neck stub + break (rubble only in the 4-wide gap)
    _tube(cv, [(X0, hy + 5.5, gh - 2.6), (X0, hy + 6.5, gh - 2.4)], 1.9, 1.7, W, 'statue')
    n0, n1 = q['neck_gap']
    for (x, y) in ((251, n0), (253, n0 + 1)):
        cv.set(x, y, _g(cv, x, y) - 1, W, 'rubble')
    # body masses
    for (y, rx, ry, rz) in q['body']:
        _rest(cv, X0, y, rx, ry, rz, W, 'statue')
    # legs (west leg; the east one is the mirror): thigh up to a raised knee, shin down to an upturned foot
    lx = q['leg_x']
    hipy, kneey, ankley = q['leg_y']
    g1, g2, g3 = _g(cv, lx, hipy), _g(cv, lx, kneey), _g(cv, lx, ankley)
    _tube(cv, [(lx, hipy, g1 - 2.6), (lx, kneey, g2 - q['knee_h'])], 2.6, 2.3, W, 'statue')
    cv.ellipsoid(lx, kneey, g2 - q['knee_h'], 2.9, 2.6, 2.6, W, 'statue')
    _tube(cv, [(lx, kneey + 0.5, g2 - q['knee_h']), (lx, ankley, g3 - 2.0)], 2.2, 1.9, W, 'statue')
    _rest(cv, lx, ankley + 2.0, 1.9, 2.6, 2.4, W, 'statue')
    _tube(cv, [(lx, ankley + 2.5, g3 - 2.5), (lx, ankley + 3.0, g3 - 5.0)], 1.4, 1.1, W, 'statue')   # toes up
    # arms along the body, open palm-up hands with finger ridges
    for (pts, r0, r1) in q['arm']:
        _tube(cv, [(x, y, _g(cv, x, y) - zz) for (x, y, zz) in pts], r0, r1, W, 'statue')
    hx, hyh = q['hand']
    g4 = _rest(cv, hx, hyh, 2.8, 3.0, 1.9, W, 'statue')
    t = top(int(hx), int(hyh))
    cv.carve(int(hx) - 1, int(hx), int(hyh) - 1, int(hyh), t, t)      # the cupped palm
    for k in range(4):
        fx = hx - 1.5 + k
        _tube(cv, [(fx, hyh + 2.5, g4 - 1.2), (fx, hyh + 5.5, g4 - 1.1)], 0.85, 0.75, W, 'statue')
    # robe drapery: ridges flowing off the hips and shoulders onto the plaza (valleys open outward)
    _rest(cv, X0, q['skirt'][0], q['skirt'][1], q['skirt'][2], q['skirt'][3], W, 'statue')     # robe skirt
    for (a, b) in q['drape']:
        _tube(cv, [(a[0], a[1], _g(cv, *a) - 1.8), (b[0], b[1], _g(cv, *b) - 1.2)], 2.1, 1.5, W, 'statue')
    # broken staff lying across the plaza at the waist line (two halves, the head of the staff on the west end)
    (s0, s1), sy = q['staff_x'], q['staff_y']
    _tube(cv, [(s0, sy, _g(cv, s0, sy) - 1.2), (s1, sy, _g(cv, s1, sy) - 1.2)], 1.15, 1.0, W, 'statue')
    _rest(cv, s0 - 1.0, sy, 1.9, 1.9, 1.9, W, 'statue')
    pruned = prune_steps(cv, (232, 255, 176, 242), ('statue',))
    sealed = seal_entries(cv, (232, 255, 176, 242), ('statue',))
    cv.interiors += [['queen knee arch', int(lx) - 1, kneey, _g(cv, lx - 1, kneey)],
                     ['queen neck gap', 253, n0 + 1, _g(cv, 253, n0 + 1)]]
    return {'pruned_step_voxels': pruned, 'sealed_edge_voxels': sealed}


def build_under_head_v11(cv, S=SPEC):
    """v1.1 elder head under the platform: half-buried, tilted, with brow ridge, eye sockets 2 deep, nose, lips,
    cheeks, an ear, a hair/crown band, a broken crown piece north of it and a severed hand south of it. Every edge
    >= 2 tall (prune_steps), top far below the platform."""
    U = S['under']
    g = 50
    hd = U['head']
    cx, cy = hd['c'][0] + 0.5, hd['c'][1] + 0.5
    rx, ry, rz = hd['r']
    W = C['ruin']
    for x in range(int(cx - rx) - 1, 256):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            u = ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2
            if u > 1:
                continue
            tilt = hd['tilt'] * (y + 0.5 - cy) / ry
            hgt = int(round(rz * math.sqrt(1 - u) - tilt))
            if hgt >= 2:
                cv.box(x, x, y, y, g - hgt, g - 1, W, 'statue')
    def top(x, y):
        t = int(np.argmax(cv.solid[x, y]))
        return t if t <= g - 3 else -99
    ny = int(cy) - 2
    for y in range(ny - 1, ny + 4):                                    # nose (2 high near the tip)
        t = top(255, y)
        if t > 0:
            cv.box(255, 255, y, y, t - (2 if y == ny + 2 else 1), t - 1, W, 'statue')
    for x in range(249, 255):                                          # brow ridge
        t = top(x, ny - 4)
        if t > 0:
            cv.set(x, ny - 4, t - 1, W, 'statue')
    for x in (251, 252):                                               # eye sockets, 2 deep
        for y in (ny - 2, ny - 1):
            t = top(x, y)
            if t > 0:
                cv.carve(x, x, y, y, t, t + 1)
    for (x, y) in ((250, ny + 2), (251, ny + 2), (250, ny + 3)):       # cheek
        t = top(x, y)
        if t > 0:
            cv.set(x, y, t - 1, W, 'statue')
    for x in range(252, 256):                                          # lips: ridge + groove
        t = top(x, ny + 5)
        if t > 0:
            cv.set(x, ny + 5, t - 1, W, 'statue')
        t = top(x, ny + 6)
        if t > 0:
            cv.carve(x, x, ny + 6, ny + 6, t, t)
    ex = int(cx - rx) - 1                                              # ear on the west side
    gbox(cv, ex, ex + 1, int(cy) - 2, int(cy) + 1, 3, W, 'statue')
    for x in range(int(cx) - 6, 256):                                  # hair / crown band on the north rim
        y = int(cy - ry) + 1
        t = top(x, y)
        if t > 0 and x % 2 == 0:
            cv.set(x, y, t - 1, W, 'statue')
    cx0, cy0 = U['crown_piece']                                        # broken crown piece (2 tall arc)
    for (dx, dy) in ((0, 0), (1, 0), (2, 1), (3, 1), (4, 0)):
        gbox(cv, cx0 + dx, cx0 + dx, cy0 + dy, cy0 + dy, 2 + (dx % 2), W, 'statue')
    hx, hy = U['hand']                                                 # severed hand + finger ridges
    _rest(cv, hx, hy, 2.4, 2.2, 1.7, W, 'statue')
    for k in range(3):
        _tube(cv, [(hx - 1.0 + k, hy + 2.0, g - 1.1), (hx - 1.0 + k, hy + 4.0, g - 1.0)], 0.8, 0.7, W, 'statue')
    for (x, y) in U['stubs_v11']:
        cv.box(x - 3, x + 3, y - 3, y + 3, g - 2, g - 1, C['stone'], 'ruin')
        cv.carve(x - 3, x - 3, y - 3, y - 3, g - 2, g - 1)
        cv.carve(x + 3, x + 3, y + 3, y + 3, g - 2, g - 1)
        cv.cylinder(x + 0.5, y + 0.5, 2.1, g - 5, g - 3, C['ruin'], 'ruin')
    n = prune_steps(cv, (240, 255, 240, 272), ('statue',))
    return {'pruned_step_voxels': n, 'sealed_edge_voxels': seal_entries(cv, (240, 255, 240, 272), ('statue',))}
