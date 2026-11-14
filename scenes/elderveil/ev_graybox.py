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

def _ring_profile(d, W, pk, rug, ter, R, Z):
    u = d / W
    ft = R['face_top']
    face = pk + (ft - pk) * (u - R['peak_u']) / (R['face_u'] - R['peak_u'])
    face = face + rug * np.clip((u - R['peak_u']) * 4, 0, 1)
    step = R['terrace_step']
    face = np.where(ter, np.floor(face / step) * step + 2, face)
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
    aqm = _box((aq['x0'] - 4, 255), (aq['y'][0] - 5, aq['y'][1] + 5))
    aqm |= _mirror_mask(aqm)
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
    ringH = np.full((512, 512), 99.0)
    ring_u = np.full((512, 512), 9.0)
    for edge, d, along in (('N', Y.astype(float), XW), ('S', (511 - Y).astype(float), XW), ('W', XW.astype(float), Y)):
        W = Wbase.copy()
        for (e, c0, hw, ex) in R['bumps']:
            if e == edge:
                W = W + ex * np.exp(-((along - c0) / hw) ** 2)
        h, u = _ring_profile(d, W, pk, rug, ter, R, Z)
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
    H = fill_basins(H, (ring_u <= 1.0) & (H <= 47))
    H = np.maximum(H, Z['min_solid_z'] + 1)
    for _ in range(40):              # a column > 1 below all 4 neighbours is raised to the lowest one + 1
        nb = np.stack([np.roll(H, 1, 0), np.roll(H, -1, 0), np.roll(H, 1, 1), np.roll(H, -1, 1)]).max(0)
        pit = (H > nb + 1) & (H < 62)
        if not pit.any():
            break
        H[pit] = nb[pit] + 1
    region[(H < 61) & np.isin(region, [3, 4])] = 0          # stream ends buried under the ring
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


def build_gate_tower(cv, S=SPEC):
    gt = S['gate_tower']
    x0, x1, y0, y1 = gt['box']
    g = 50
    structures.building(cv, x0, x1, y0, y1, g, storeys=gt['storeys'], storey_h=gt['storey_h'], doors=('S', 'W'),
                        wall=C['building'], floor=C['floor'], roof=C['roof'], stair=C['stair'], name='gate tower',
                        furnish=False)
    roof = g - gt['storeys'] * gt['storey_h']
    for x in range(x0, x1 + 1):                    # merlons (2 tall; the roof has no access)
        for y in (y0, y1):
            if (x - x0) % 4 < 2:
                cv.box(x, x, y, y, roof - 2, roof - 1, C['building'], 'building')
    for y in range(y0, y1 + 1):
        for x in (x0, x1):
            if (y - y0) % 4 < 2:
                cv.box(x, x, y, y, roof - 2, roof - 1, C['building'], 'building')
    cv.carve(x1 - 4, x1 - 1, y0 + 1, y0 + 4, roof, roof)          # collapsed roof corner over the top room
    cv.carve(x1, x1, y0 + 1, y0 + 3, roof - 2, roof + 3)
    for (cx, cy) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):      # chamfered corners
        cv.carve(cx, cx, cy, cy, roof - 2, roof + 1)


def build_bastion(cv, S=SPEC):
    """Stump of a collapsed round bastion at the south end of the front breach: a broken 3-thick ring wall (6-9
    tall) filled with fallen masonry (rubble 4-6 tall, never a 1-voxel step from the ground). A ruin mound, not a
    building: no room, no interior record."""
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
                h = b['h'][0] + int(round((b['h'][1] - b['h'][0]) * hn[x, y]))
                cv.box(x, x, y, y, g - h, g - 1, C['ruin'], 'ruin')
            elif d <= R - 3.0:
                h = b['fill_h'][0] + int(round((b['fill_h'][1] - b['fill_h'][0]) * hn[x, y]))
                cv.box(x, x, y, y, g - h, g - 1, C['rock'], 'rubble')


def build_hall(cv, S=SPEC):
    hl = S['hall']
    g = 49
    x0, x1, y0, y1 = hl['main']
    structures.building(cv, x0, x1, y0, y1, g, storeys=hl['storeys'], storey_h=hl['storey_h'],
                        doors=('E', 'S', 'W'), wall=C['building'], floor=C['floor'], roof=C['roof'],
                        stair=C['stair'], name='hunters hall', furnish=True)
    roof = g - hl['storeys'] * hl['storey_h']
    wx0, wx1, wy0, wy1 = hl['wing']
    structures.building(cv, wx0, wx1, wy0, wy1, g, storeys=1, storey_h=hl['storey_h'], doors=('N',),
                        wall=C['building'], floor=C['floor'], roof=C['roof'], name='hall armoury', furnish=True)
    cx = (wx0 + wx1) // 2
    structures.door(cv, cx - 1, cx + 1, y0, y0, g)                     # armoury -> hall
    cv.carve(x0 + 1, x0 + 7, y0 + 1, y0 + 9, roof, roof)              # ruined NW corner: roof fallen in
    cv.carve(x0, x0, y0 + 2, y0 + 7, roof - 1, roof + 3)
    cv.carve(x0 + 2, x0 + 6, y0, y0, roof - 1, roof + 2)
    for ty in (y0 + 10, y0 + 22):                                      # long tables
        cv.box(x0 + 9, x0 + 16, ty, ty + 1, g - 1, g - 1, C['furn'], 'furniture')
    cv.box(x1 - 2, x1 - 1, y0 + 5, y0 + 12, g - hl['storey_h'] - 2, g - hl['storey_h'] - 1, C['furn'],
           'furniture')                                                # trophy shelf upstairs


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
    """Low ruins in the strip: a fallen elder head on the axis (3-tall steep base: not climbable), column stubs on
    2-tall plinths, two root humps (2 tall). The broken mosaic floor is region 6 (paint only)."""
    U = S['under']
    g = 50
    hd = U['head']
    cx, cy = hd['c']
    h = hd['h']
    cv.cylinder(cx + 0.5, cy + 0.5, hd['r'], g - h, g - 1, C['ruin'], 'statue')
    cv.box(253, 255, cy - 3, cy + 3, g - h - 1, g - h - 1, C['ruin'], 'statue')          # nose ridge
    cv.box(250, 252, cy - 4, cy - 3, g - h - 1, g - h - 1, C['ruin'], 'statue')          # brows
    cv.box(250, 252, cy + 3, cy + 4, g - h - 1, g - h - 1, C['ruin'], 'statue')
    for (x, y) in U['stubs']:
        cv.box(x - 3, x + 3, y - 3, y + 3, g - 2, g - 1, C['stone'], 'ruin')
        cv.carve(x - 3, x - 3, y - 3, y - 3, g - 2, g - 1)                                 # chipped corners
        cv.carve(x + 3, x + 3, y + 3, y + 3, g - 2, g - 1)
        cv.cylinder(x + 0.5, y + 0.5, 2.1, g - 5, g - 3, C['ruin'], 'ruin')


# =============================================================================================== assist spire

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
    """Fallen elder-queen statue lying N-S across the plaza's south edge: head on the plaza floor, torso slab over
    the steps (walk under it: >= 3 air), hips on the valley floor, legs broken off at the knees. A rubble stair on
    each side (the east one by mirror) climbs onto the hips: walk over hips, torso and up onto the head."""
    q = S['queen']
    hx, hy = q['head_c']
    gh = int(cv.H[255, hy])
    cv.ellipsoid(256.5, hy + 0.5, gh - q['head_r'], q['head_r'], q['head_r'], q['head_r'], C['ruin'], 'statue')
    t0, t1 = q['torso_y']
    za, zb = q['torso_z']
    cv.box(q['x'][0], 255, t0, t1, za, zb, C['ruin'], 'statue')
    cv.box(q['x'][0] + 1, 255, t0 + 2, t0 + 6, za - 1, za - 1, C['ruin'], 'statue')          # folded arms
    h0, h1 = q['hips_y']
    cv.box(q['x'][0] + 1, 255, h0, h1, za, 49, C['ruin'], 'statue')
    cv.carve(q['x'][0] + 1, q['x'][0] + 1, h1, h1, za, za + 1)                               # rounded corner
    l0, l1 = q['legs_y']
    cv.box(q['x'][0] + 2, 255, l0, l1, za + 2, 49, C['ruin'], 'statue')
    rx0, rx1 = q['ramp_x']
    ry0, ry1 = q['ramp_y']
    straight_stair(cv, rx0 + 3, ry0, ry1, 50, 50 - za, 1, C['stair'], mat='stair')     # top step meets the hips
    cv.interiors += [['queen walk-under', 252, (t0 + t1) // 2, int(cv.H[252, (t0 + t1) // 2])],
                     ['queen back', 252, (t0 + t1) // 2, za], ['queen hips', 252, (h0 + h1) // 2, za]]


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


def build_amphi(cv, S=SPEC):
    """Heart-tree stand-in (trunk + canopy, well clear of the platform) over the root amphitheatre (terraces are
    terrain). Four roots per side arch from the trunk over the seats (walk under) and plunge into the ground as a
    steep knee (top >= 6 above the ground: not walkable onto)."""
    a = S['amphi']
    cx, cy = a['c']
    fx, fy = cx + 0.5, cy + 0.5
    t = a['tree']
    ga = int(cv.H[255, cy])
    cv.cylinder(fx, fy, t['trunk_r'], t['trunk_top'], ga - 1, C['trunk'], 'trunk')
    rx, ry, rz = t['canopy']
    cv.ellipsoid(fx, fy, t['canopy_z'], rx, ry, rz, C['veg'], 'canopy')
    for (deg, reach) in a['roots']:
        ca, sa = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        rp = reach * 0.8
        px, py = fx + rp * ca, fy + rp * sa
        gp = int(cv.H[int(px), int(py)])
        z0, z1 = a['root_z0'], gp - 6.5
        n = int(rp * 3)
        for i in range(n + 1):
            u = i / n
            rho = 4.0 + (rp - 4.0) * u
            z = z0 + (z1 - z0) * u * u
            cv.ellipsoid(fx + rho * ca, fy + rho * sa, z, 1.7, 1.7, 1.7, C['root'], 'root')
        ix, iy = int(math.floor(px)), int(math.floor(py))
        cv.box(ix - 1, ix + 1, iy - 1, iy + 1, int(z1) - 1, gp - 1, C['root'], 'root')       # knee into the ground
    cv.interiors.append(['amphitheatre arena', 246, cy, int(cv.H[246, cy])])


# =============================================================================================== flanks

def build_aqueduct(cv, S=SPEC):
    """Broken elder aqueduct along the north flank: piers every 16, arch spandrels (7 air under the crown), a deck
    (floor z 39, 5 wide between 2-tall parapets) on intact spans; collapsed sections with rubble stairs up to both
    deck ends (way up and down at every collapse)."""
    aq = S['aqueduct']
    y0, y1 = aq['y']
    dz, sf = aq['deck_z'], aq['soffit']
    g = S['z']['aqueduct_ground']
    coll = aq['collapses']

    def in_coll(x):
        return any(a <= x <= b for (a, b) in coll)
    piers = [p for p in range(aq['pier_x0'], 256, aq['pier_dx']) if not any(a - 3 <= p <= b for (a, b) in coll)]
    for p in piers:
        cv.box(p, p + aq['pier_w'] - 1, y0, y1, sf, g - 1, C['ruin'], 'aqueduct')
    allp = piers + [512 - p - aq['pier_w'] + 1 for p in piers]
    allp.sort()
    for x in range(aq['x0'], 256):
        if in_coll(x):
            continue
        cv.box(x, x, y0, y1, dz, dz + aq['deck_t'] - 1, C['ruin'], 'aqueduct')
        if any(p <= x < p + aq['pier_w'] for p in piers):
            continue
        left = [p + aq['pier_w'] - 1 for p in allp if p + aq['pier_w'] - 1 < x]
        right = [p for p in allp if p > x]
        if left and right:
            a, b = left[-1], right[0]
            mid, half = (a + b) / 2.0, max((b - a) / 2.0, 1.0)
            zs = sf + int(round(4 * ((x - mid) / half) ** 2))
            cv.box(x, x, y0, y1, sf, min(zs, g - 1), C['ruin'], 'aqueduct')
        if x % 11 not in (0, 1):
            cv.box(x, x, y0, y0, dz - aq['parapet_h'], dz - 1, C['ruin'], 'aqueduct')
            cv.box(x, x, y1, y1, dz - aq['parapet_h'], dz - 1, C['ruin'], 'aqueduct')
    rise = g - dz
    for (a, b) in coll:
        straight_stair(cv, a + rise - 1, y0 + 1, y1 - 1, g, rise, -1, C['stair'], mat='stair')
        straight_stair(cv, b - rise + 1, y0 + 1, y1 - 1, g, rise, 1, C['stair'], mat='stair')
        m = (a + b) // 2
        cv.box(m - 2, m + 2, y0, y1 - 2, g - 1, g - 1, C['ruin'], 'rubble')
        cv.interiors.append([f'aqueduct gap {a}', m, y1 + 1, g])
    secs = [aq['x0']] + [v for ab in coll for v in ab] + [255]
    for i in range(0, len(secs), 2):
        xa, xb = secs[i], secs[i + 1]
        xm = (xa + xb) // 2
        if cv.H[xm, (y0 + y1) // 2] > dz:
            cv.interiors.append([f'aqueduct deck {xa}-{xb}', xm, (y0 + y1) // 2, dz])
    return {'piers': len(piers), 'deck_sections': [[secs[i], secs[i + 1]] for i in range(0, len(secs), 2)]}


def build_bridge(cv, S=SPEC):
    """Stone footbridge on the axis over the pool: deck z 50 (2 thick), 2-tall parapets, 5 wide; arch fill down to
    the banks at the ends, open above the water in the middle (walk under along the shelves)."""
    bd = S['bridge']
    xa = bd['x'][0]
    col = cv.H[255]
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


def paint_waterfall(cv, S=SPEC):
    """Graybox marker for the waterfall: top voxels of the cliff face and the bank behind the pool painted as
    water (no geometry change; the art pass builds the cascade)."""
    x0, x1 = S['waterfall']['x']
    n = 0
    for x in range(x0, 256):
        for y in range(440, 512):
            z = int(cv.H[x, y])
            if z >= 62:
                continue
            cv.set(x, y, z, C['water'], 'waterfall')
            n += 1
            if z < 20:
                break
    return n


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
    out = []
    for (x, y, r, h) in S['mushrooms']:
        g = int(cv.H[x, y])
        if g > 52:
            continue
        sr = 1.4 + 0.12 * r
        cv.cylinder(x + 0.5, y + 0.5, sr, g - h, g - 1, C['stem'], 'mushroom')
        cv.ellipsoid(x + 0.5, y + 0.5, g - h, r, r * 0.9, 2.6, C['mushroom'], 'mushroom')
        out.append((x, y, r, h))
    return out


def build_crest_walls(cv, geo, S=SPEC):
    """Broken elder walls on the cliff crests: short runs 2-4 tall in a band just behind the crest line (z >= 7)."""
    cw = S['ring']['crest_wall']
    u = geo['ring_u']
    n = noise.fbm2((512, 512), cw['cell'], 2, 'crest_wall', S['layout_seed'])
    hn = noise.fbm2((512, 512), 3, 1, 'crest_h', S['layout_seed'])
    m = (u >= cw['band_u'][0]) & (u <= cw['band_u'][1]) & (n > cw['keep']) & (X <= 255)
    k = 0
    for x, y in zip(*np.nonzero(m)):
        g = int(cv.H[x, y])
        h = min(cw['h'][0] + int(round((cw['h'][1] - cw['h'][0]) * hn[x, y])), g - S['z']['min_solid_z'])
        if h >= 2:
            cv.box(x, x, y, y, g - h, g - 1, C['ruin'], 'crest_wall')
            k += 1
    return k


# =============================================================================================== masks + vegetation

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
                             (238, 255, 180, 240), (238, 255, 380, 470), (40, 255, 78, 98),
                             (S['gate_tower']['box'][0] - 2, S['gate_tower']['box'][1] + 2,
                              S['gate_tower']['box'][2] - 2, S['gate_tower']['box'][3] + 2),
                             (S['bastion']['box'][0] - 2, S['bastion']['box'][1] + 2, S['bastion']['box'][2] - 2,
                              S['bastion']['box'][3] + 2)):
        cv.no_prop(x0 - 3, x1 + 3, y0 - 3, y1 + 3, KEEP_MISC)
    for (x, y, r, hh) in S['mushrooms']:
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
    build_front(cv, S)
    build_under(cv, S)
    rep['spire'] = build_spire(cv, S)
    build_plaza(cv, S)
    build_queen(cv, S)
    build_library(cv, S)
    build_amphi(cv, S)
    rep['aqueduct'] = build_aqueduct(cv, S)
    rep['bridge_y'] = build_bridge(cv, S)
    rep['waterfall_cells'] = paint_waterfall(cv, S)
    build_rune_circle(cv, S)
    rep['mushrooms'] = build_mushrooms(cv, S)
    pinned = plant_pinned(cv, S)
    sc = scatter(cv, geo, S, veg_seed)
    sc['nooks_filled'] = fill_nooks(cv)
    sc['trap_trees_removed'], sc['trap_crest_wall_columns_removed'] = clear_tree_traps(cv, sc['tree_list'])
    bf = break_flats(cv, S)
    sc['feature_pads'] = bf['feature_pads']
    sc['largest_flat_after_west'] = bf['largest_side_after_west']
    sc['pinned_trees'] = len(pinned)
    sc['tree_list'] = sc['tree_list'] + pinned
    rep['scatter'] = sc
    return cv, rep
