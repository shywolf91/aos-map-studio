"""Terrain layer: pumpkin island heightfield, carved face (eyes, nose, grin), clearing, paths, zones.

All layout numbers live in SPEC. z grows downward (z = 0 sky top, 63 = water plane).
Terrain is authored for the whole map but every field is folded to be mirror-symmetric about x = 256
(x' = 512 - x), and the final voxel array is mirrored again after props, so gameplay geometry is exact.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from wkh_core import fbm2, fold_x

SEED = 1031

SPEC = {
    'center': (256.0, 262.0),          # island centre (pumpkin body)
    'radii': (214.0, 200.0),           # outline ellipse half-axes (x, y)
    'lobes': 14,                       # rim segments (grooves at north stem + south)
    'groove_cut': 0.07,                # coastline notch depth at grooves (fraction of radius)
    'plateau_z': 44,                   # main play level (face)
    'rim_start': {'side': 0.80, 'north': 0.84, 'south': 0.83},
    'lobe_h': {'side': 12, 'north': 9, 'south': 13},
    'clearing': ((256, 256), 48),       # ritual clearing centre, radius
    'stone_ring_r': 34,
    'bases': ((118, 256), (394, 256)),
    'spawn_half': 20,
    'platform': {'x': (206, 305), 'y': (240, 271), 'z': 1},
    # left eye (apex up); right eye is its mirror
    'eye': ((138, 207), (224, 207), (183, 116)),
    'eye_depth': 9,
    'nose': ((237, 318), (275, 318), (256, 283)),
    'nose_depth': 6,
    # grin: corners at 256 +- half_w, y = corner_y; upper/lower lip sag at centre
    'grin': {'half_w': 124, 'corner_y': 294, 'upper_sag': 46, 'lower_sag': 100, 'depth': 9},
    # teeth (x offset from centre, width, length into trench); upper hang down, lower point up
    'upper_teeth': ((-104, 13, 10), (-70, 20, 16), (-26, 20, 19)),
    'lower_teeth': ((-48, 20, 17), (0, 22, 18)),
    'grin_bridges': ((-70, 'upper'), (0, 'lower')),   # bridge on a tooth line (mirrored)
    'stem': (230, 88),
    'king': (256, 122),
}

PZ = SPEC['plateau_z']


def _tri_sdf(px, py, tri):
    """Signed distance to a triangle (negative inside). px, py arrays."""
    (ax, ay), (bx, by), (cx, cy) = tri
    P = np.stack([px, py], -1).astype(float)
    V = np.array([[ax, ay], [bx, by], [cx, cy]], float)
    d = np.full(px.shape, np.inf)
    inside = np.ones(px.shape, bool)
    area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    for i in range(3):
        a, b = V[i], V[(i + 1) % 3]
        e = b - a
        w = P - a
        t = np.clip((w @ e) / (e @ e), 0, 1)
        q = w - t[..., None] * e
        d = np.minimum(d, np.hypot(q[..., 0], q[..., 1]))
        cross = e[0] * w[..., 1] - e[1] * w[..., 0]
        inside &= (cross * np.sign(area)) >= 0
    return np.where(inside, -d, d)


def build_fields(seed=SEED):
    X, Y = np.meshgrid(np.arange(512) + 0.5, np.arange(512) + 0.5, indexing='ij')
    cx, cy = SPEC['center']
    A, B = SPEC['radii']
    dx, dy = X - cx, Y - cy
    th = np.arctan2(dy, dx)                         # 0 = east, -pi/2 = north
    E = 1.0 / np.sqrt((np.cos(th) / A) ** 2 + (np.sin(th) / B) ** 2)
    r = np.hypot(dx, dy)

    K = SPEC['lobes']
    step = 2 * np.pi / K
    rel = (th + np.pi / 2) % step                   # 0 at a groove (north groove at -pi/2)
    gd = np.minimum(rel, step - rel)                # angular distance to nearest groove
    groove = np.exp(-(gd / np.radians(4.2)) ** 2)
    lobe_idx = np.floor(((th + np.pi / 2) % (2 * np.pi)) / step).astype(int)   # 0..K-1, clockwise from north
    # deterministic per-lobe swell (symmetric pairs i <-> K-1-i)
    swell = np.array([1.00, 1.04, 0.97, 1.03, 1.00, 0.96, 1.02, 1.02, 0.96, 1.00, 1.03, 0.97, 1.04, 1.00])
    lobe_sw = swell[lobe_idx]

    n_coast = fold_x(fbm2((512, 512), 32, 3, 'coast', seed))
    stem_notch = np.exp(-(((th + np.pi / 2) / np.radians(7.0)) ** 2))
    R = E * (1 - SPEC['groove_cut'] * groove - 0.035 * stem_notch) * (0.985 + 0.03 * lobe_sw) \
        + (n_coast - 0.5) * 6.0
    rho = r / R

    # where are we around the rim: north / side / south weights
    s_n = np.clip(-np.sin(th), 0, 1) ** 2
    s_s = np.clip(np.sin(th), 0, 1) ** 2
    s_e = 1 - s_n - s_s
    rs = SPEC['rim_start']
    rim0 = rs['north'] * s_n + rs['south'] * s_s + rs['side'] * s_e
    lh = SPEC['lobe_h']
    LH = (lh['north'] * s_n + lh['south'] * s_s + lh['side'] * s_e) * lobe_sw

    land = rho < 1.0
    s = np.clip((rho - rim0) / (1 - rim0), 0, 1)
    w = (1 - groove) ** 1.6
    dome = np.sin(np.pi * 0.92 * s) ** 0.85 * (s > 0)
    zf = PZ - LH * w * dome                          # float top height (z, smaller = higher)

    # gentle plateau relief away from gameplay areas (ribs + swells)
    lon = np.arcsin(np.clip(dx / (A * np.sqrt(np.clip(1 - (dy / B) ** 2, 0.05, 1))), -1, 1))
    rib = 0.5 + 0.5 * np.cos(lon * K)                # ribs along meridians
    n_relief = fold_x(fbm2((512, 512), 48, 2, 'relief', seed))
    relief = (rib - 0.5) * 1.6 + (n_relief - 0.5) * 3.0

    # gameplay-flat mask: spawn zones, fronts, clearing, under the platform, pits' surroundings
    flat = np.zeros((512, 512))
    for (bx, by) in SPEC['bases']:
        flat = np.maximum(flat, _soft_box(X, Y, bx - 26, bx + 26, by - 26, by + 26, 10))
    flat = np.maximum(flat, _soft_box(X, Y, 130, 382, 228, 284, 12))       # fronts + platform corridor
    (ccx, ccy), cr = SPEC['clearing']
    flat = np.maximum(flat, np.clip((cr + 14 - np.hypot(X - ccx, Y - ccy)) / 14, 0, 1))
    zf = zf - (1 - flat) * np.clip(relief, -1.2, 2.4) * (rho < rim0 + 0.02)

    # forehead rise toward the Wicker King (north) and a soft southern orchard knoll
    kx, ky = SPEC['king']
    zf -= 3.0 * np.clip(1 - np.hypot((X - kx) / 70, (Y - ky - 10) / 42), 0, 1) ** 1.3 * (1 - flat)
    zf -= 2.0 * np.clip(1 - np.hypot((X - 256) / 60, (Y - 436) / 22), 0, 1) * (1 - flat)

    H = np.rint(zf).astype(int)
    H = np.where(land, H, 63)
    return dict(X=X, Y=Y, th=th, rho=rho, rim0=rim0, groove=groove, land=land, H=H, lobe_idx=lobe_idx,
                lon=lon, flat=flat, R=R)


def _soft_box(X, Y, x0, x1, y0, y1, feather):
    ddx = np.maximum(np.maximum(x0 - X, X - x1), 0)
    ddy = np.maximum(np.maximum(y0 - Y, Y - y1), 0)
    return np.clip(1 - np.hypot(ddx, ddy) / feather, 0, 1)


# ---------------------------------------------------------------------------------------- face

def grin_mask(X, Y):
    g = SPEC['grin']
    t = (X - 256) / g['half_w']
    inside_t = np.abs(t) < 1
    q = np.clip(1 - t * t, 0, 1)
    yu = g['corner_y'] + g['upper_sag'] * q
    yl = g['corner_y'] + g['lower_sag'] * q ** 0.85
    m = inside_t & (Y > yu) & (Y < yl)
    teeth = np.zeros_like(m)
    for off, wdt, ln in SPEC['upper_teeth']:
        for sx in (off, -off):
            tx = sx / g['half_w']
            yu_t = g['corner_y'] + g['upper_sag'] * (1 - tx * tx)
            # slightly tapered tooth
            taper = np.clip((Y - yu_t) / ln, 0, 1) * 2.0
            teeth |= (np.abs(X - 256 - sx) < wdt / 2 - taper) & (Y > yu_t - 2) & (Y < yu_t + ln)
    for off, wdt, ln in SPEC['lower_teeth']:
        for sx in (off, -off):
            tx = sx / g['half_w']
            yl_t = g['corner_y'] + g['lower_sag'] * (1 - tx * tx) ** 0.85
            taper = np.clip((yl_t - Y) / ln, 0, 1) * 2.0
            teeth |= (np.abs(X - 256 - sx) < wdt / 2 - taper) & (Y < yl_t + 2) & (Y > yl_t - ln)
    return m & ~teeth, teeth & inside_t, t


def carve_face(F):
    X, Y, H = F['X'], F['Y'], F['H'].copy()
    labels = np.zeros(H.shape, np.int8)           # 1 eye, 2 nose, 3 grin

    def terrace(mask, depth, steps):
        d = ndi.distance_transform_edt(mask)
        z = np.zeros(mask.shape)
        for (dist, dep) in steps:
            z = np.where(d >= dist, dep, z)
        return np.where(mask, np.minimum(z, depth), 0), d

    # eyes
    tri = SPEC['eye']
    m1 = _tri_sdf(X, Y, tri) < 0
    m2 = _tri_sdf(512 - X, Y, tri) < 0
    eyes = m1 | m2
    ze, de = terrace(eyes, SPEC['eye_depth'], [(0.5, 2), (3, 5), (6, 7), (9, 9)])
    # nose
    mn = _tri_sdf(X, Y, SPEC['nose']) < 0
    zn, dn = terrace(mn, SPEC['nose_depth'], [(0.5, 1), (1.5, 2), (2.5, 3), (3.5, 4), (4.5, 5), (5.5, 6)])
    # grin
    mg, teeth, t = grin_mask(X, Y)
    zg, dg = terrace(mg, SPEC['grin']['depth'], [(0.5, 4), (4, 9)])
    corner = np.clip((np.abs(t) - 0.66) / 0.30, 0, 1)
    corner = corner * corner * (3 - 2 * corner)
    zg = np.where(mg, np.minimum(zg, np.round(SPEC['grin']['depth'] * (1 - corner))), 0)

    dep = np.maximum(np.maximum(ze, zn), zg)
    pit = (eyes | mn | mg)
    labels[eyes] = 1; labels[mn] = 2; labels[mg] = 3
    H = np.where(pit, PZ + dep, H)
    F.update(H=H.astype(int), pit=pit, pit_label=labels, teeth=teeth, eye_mask=eyes, nose_mask=mn,
             grin_mask=mg, grin_t=t)
    return F


def add_ramps(F):
    """Stair ramps (1-voxel risers) from the plateau into each pit. Left side authored; fold mirrors."""
    H = F['H'].copy()
    ramps = np.zeros(H.shape, bool)

    def ramp(points, width, z_from, z_to):
        pts = np.array(points, float)
        seg = np.diff(pts, axis=0)
        L = np.hypot(seg[:, 0], seg[:, 1])
        total = L.sum()
        cum = 0.0
        for (p, s, l) in zip(pts[:-1], seg, L):
            n = int(np.ceil(l * 2))
            for k in range(n + 1):
                q = p + s * k / n
                frac = (cum + l * k / n) / total
                z = int(round(z_from + (z_to - z_from) * frac))
                x0, y0 = int(round(q[0] - width / 2)), int(round(q[1] - width / 2))
                sl = (slice(x0, x0 + width), slice(y0, y0 + width))
                H[sl] = np.minimum(H[sl], z)
                ramps[sl] = True
            cum += l

    d = SPEC['eye_depth']
    # eye: descend along the bottom edge from the west corner, and down the inner (east) side
    ramp([(150, 203), (176, 203), (196, 196)], 4, PZ, PZ + d)
    ramp([(212, 196), (202, 172), (196, 156)], 4, PZ, PZ + d)
    # grin: stairs from the upper lip at the outer teeth, and from the lower lip
    g = SPEC['grin']
    ramp([(207, 329), (207, 352)], 4, PZ, PZ + g['depth'])
    ramp([(231, 394), (231, 371)], 4, PZ, PZ + g['depth'])
    F['H'] = H
    F['ramps'] = ramps
    return F


def fix_pockets(F, max_iter=12):
    """Raise pit cells that cannot be left on foot (heightfield model: step up 1, drop <= 9)."""
    H = F['H']
    pit = F['pit']
    for it in range(max_iter):
        ok = (~pit) & (H == PZ)
        reach = ok.copy()
        while True:
            new = reach.copy()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nb = np.roll(reach, (dx, dy), axis=(0, 1))
                Hn = np.roll(H, (dx, dy), axis=(0, 1))
                # from this cell we can move to the reached neighbour if it is at most 1 higher (z smaller by <= 1)
                new |= nb & (Hn >= H - 1) & (Hn - H <= 9) & (H < 63)
            if (new == reach).all():
                break
            reach = new
        bad = pit & ~reach
        if not bad.any():
            break
        Hmin = H.copy()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            Hmin = np.minimum(Hmin, np.roll(H, (dx, dy), axis=(0, 1)))
        H = np.where(bad, np.maximum(Hmin + 1, H - 1), H)
    F['H'] = H
    F['pocket_cells_fixed_iters'] = it
    return F


def fold_fields(F):
    for k in ('H', 'pit', 'pit_label', 'teeth', 'ramps', 'eye_mask', 'nose_mask', 'grin_mask'):
        if k in F:
            F[k] = fold_x(F[k])
    return F


def terrain(seed=SEED):
    F = build_fields(seed)
    F = carve_face(F)
    F = add_ramps(F)
    F = fold_fields(F)
    F = fix_pockets(F)
    return F
