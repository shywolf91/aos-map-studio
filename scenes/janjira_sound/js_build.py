"""Janjira Sound gameplay geometry (stage 1 graybox): terrain, fort, towers, islet buildings, props, vegetation.

terrain(cv, S, seed)       land mask + height field for the whole map, made point-symmetric (point512) before
                           it is filled, so the rotation never cuts a coast.
build_west(S, seed, veg_seed)  terrain + every structure on the source half (x < 256; the baoli is authored whole)
                           + vegetation; the caller removes orphans and rotates with symmetry.mirror_canvas.
dhow(cv, S)                the asymmetric one-off, after the rotation (returns its cosmetic box).

Every structure is real (owner rule 2026-10-20): doorways >= 2 wide x 3 high, rooms, slits, stairs to every level.
Each room / floor / terrace is recorded in cv.interiors. Graybox colours are flat per material (no art pass).
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage as ndi

from aosmap.kit import noise, symmetry
from aosmap.kit.canvas import Canvas, line_points
from aosmap.kit.structures import straight_stair

# flat graybox colours, one per material (stage 2 replaces them)
GC = {
    'sea': (40, 92, 112), 'sand': (206, 184, 136), 'grass': (104, 138, 70), 'laterite': (172, 104, 70),
    'paving': (150, 128, 110), 'basalt': (84, 84, 92), 'basalt_dk': (66, 66, 74), 'plaster': (204, 196, 180),
    'timber': (128, 92, 60), 'floor': (138, 108, 80), 'stair': (150, 120, 90), 'leaf': (58, 112, 58),
    'frond': (96, 146, 62), 'bark': (98, 76, 58), 'palm_trunk': (140, 116, 84), 'iron': (70, 70, 76),
    'cloth': (226, 150, 48), 'crate': (160, 124, 80), 'keg': (120, 84, 56), 'rope': (176, 156, 110),
    'net': (120, 140, 130), 'hull': (110, 80, 54), 'deck': (156, 124, 86), 'mast': (120, 90, 62),
    'thatch': (186, 160, 96), 'kerb': (160, 96, 64), 'shrub': (70, 118, 62), 'furniture': (110, 82, 58),
    'pool': (60, 120, 130), 'rock': (96, 98, 104), 'flag_teal': (72, 138, 128),
    'finial': (176, 140, 66), 'fig': (128, 82, 72), 'ribbon': (224, 150, 50), 'nest': (118, 94, 66),
    'deadwood': (124, 110, 94), 'coconut': (104, 96, 48), 'sail': (204, 194, 168), 'moss': (88, 112, 62),
    'root': (118, 104, 90), 'dryfrond': (150, 126, 74), 'palm_ring': (122, 100, 74), 'frond_young': (150, 172, 84),
}


def put(cv, x, y, z, mat, c=None):
    cv.set(int(x), int(y), int(z), c or GC[mat], mat)


def box(cv, x0, x1, y0, y1, z0, z1, mat, c=None):
    cv.box(min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), min(z0, z1), max(z0, z1), c or GC[mat], mat)


def ground(cv, x, y):
    return cv.column_top(int(x), int(y))


def smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def rounded_rect(X, Y, x0, x1, y0, y1, r):
    dx = np.maximum(np.maximum(x0 + r - X, X - (x1 - r)), 0)
    dy = np.maximum(np.maximum(y0 + r - Y, Y - (y1 - r)), 0)
    return dx * dx + dy * dy <= r * r


def symmetrize(a, axis='point512'):
    a = a.copy()
    symmetry.mirror_west_to_east(a, axis=axis)
    return a


# =============================================================================================== terrain

def causeway_shores(S, seed):
    """Per-x shorelines (west half) of the causeway and the island edges across the channels.
    Returns y arrays [512]: north shore, south shore, NW island south edge, SW island north edge, and the shore
    including the sand spits (spits stick out into the channels; the island edges ignore them).
    u >= 0 is how far a shore lies outside the lane edge (236 / 276): coves 0, lobes up to ~9."""
    cw = S['causeway']
    xs = np.arange(512, dtype=float)
    rows = noise.fbm2((512, 64), 18, 3, 'cwshore', seed)
    def norm(r):                                     # zero mean, unit spread over the causeway, then [-1, 1]
        v = r[cw['x'][0]:cw['x'][1] + 1]
        return np.clip((r - v.mean()) / (v.std() + 1e-6), -1.6, 1.6) / 1.6
    un = np.clip(cw['shore_mean'] + cw['shore_amp'] * norm(rows[:, 10]), 0, cw['shore_max'])
    us = np.clip(cw['shore_mean'] + cw['shore_amp'] * norm(rows[:, 50]), 0, cw['shore_max'])
    an = S['anchor']
    # straight (u = 1) beside the anchors and at the plaza; equal at the rotation seam (x 256)
    t = np.ones(512)
    t = np.minimum(t, smooth(np.maximum(np.maximum(an['x'][0] - 4 - xs, xs - an['x'][1] - 4), 0) / 6))
    t = np.minimum(t, smooth((xs - 150) / 6))
    un = 1 + (un - 1) * t
    us = 1 + (us - 1) * t
    seam = smooth((xs - 238) / 18)
    m = (un + us) / 2
    un = un + (m - un) * seam
    us = us + (m - us) * seam
    spn, sps = np.zeros(512), np.zeros(512)
    for (x0, side, length) in cw['spits']:
        bump = length * np.exp(-((xs - x0) / 2.6) ** 2)
        if side == 'N':
            spn = np.maximum(spn, bump)
        else:
            sps = np.maximum(sps, bump)
    sh_n, sh_s = np.round(236 - un), np.round(276 + us)
    ch = S['channels']
    isl_n = np.where((xs >= ch['x'][0]) & (xs <= ch['x'][1]), sh_n - ch['width'] - 1, 227)
    isl_s = np.where((xs >= ch['x'][0]) & (xs <= ch['x'][1]), sh_s + ch['width'] + 1, 285)
    isl_n = np.minimum(isl_n, 227)
    isl_s = np.maximum(isl_s, 285)
    return sh_n, sh_s, isl_n, isl_s, np.round(sh_n - spn), np.round(sh_s + sps)


def terrain(S, seed):
    """-> (H [x, y] int, zone dict of [x, y] masks). Point-symmetric."""
    X, Y = np.meshgrid(np.arange(512, dtype=float), np.arange(512, dtype=float), indexing='ij')
    N = noise.fbm2((512, 512), 24, 3, 'coast', seed) - 0.5
    N2 = noise.fbm2((512, 512), 12, 2, 'edge', seed) - 0.5
    M = noise.fbm2((512, 512), S['plaza']['mound_cell'], 2, 'mounds', seed)
    D = noise.fbm2((512, 512), 14, 2, 'dunes', seed)
    west = X <= 256

    # ------------------------------------------------------------------ shapes
    fg, pl = S['fort_ground'], S['plaza']
    ap = S['fort_apron']
    Ax = X + (noise.fbm2((512, 512), 16, 3, 'apronx', seed) - 0.5) * 2 * ap['warp']
    Ay = Y + (noise.fbm2((512, 512), 16, 3, 'aprony', seed) - 0.5) * 2 * ap['warp']
    apron = rounded_rect(Ax, Ay, *ap['x'], *ap['y'], ap['corner_r'])
    court = rounded_rect(X, Y, *fg['x'], *fg['y'], 3)
    for (cx, cy) in S['corner_bastions']:
        court |= (X - cx) ** 2 + (Y - cy) ** 2 <= 11.5 ** 2
        apron |= np.hypot(Ax - cx, Ay - cy) <= 15
    fort = court | apron
    plaza = rounded_rect(X, Y, *pl['x'], *pl['y'], pl['corner_r'])
    for (cx, cy) in S['gate_bastions']:
        plaza |= (X - cx) ** 2 + (Y - cy) ** 2 <= 9 ** 2
    cw = S['causeway']
    sh_n, sh_s, isl_n, isl_s, spit_n, spit_s = causeway_shores(S, seed)
    # the causeway is land between its two shorelines (natural coves and lobes, sand spits into the channels);
    # straight beside the anchor blocks, the lane y 236-276 always land
    causeway = (X >= cw['x'][0]) & (X <= cw['x'][1]) & (Y >= sh_n[:, None]) & (Y <= sh_s[:, None])
    causeway |= (X >= cw['x'][0]) & (X <= cw['x'][1]) & (Y >= spit_n[:, None]) & (Y <= spit_s[:, None])
    # domain-warped coasts: natural, blobby outlines (classic island style), never terraces
    Wx = (noise.fbm2((512, 512), 32, 3, 'warpx', seed) - 0.5) * 2 * S['warp']
    Wy = (noise.fbm2((512, 512), 32, 3, 'warpy', seed) - 0.5) * 2 * S['warp'] * 0.6
    Xw, Yw = X + Wx, Y + Wy
    islands = np.zeros((512, 512), bool)
    for name, (cx, cy, rx, ry, (ylo, yhi), knolls) in S['islands'].items():
        f = 1 - ((Xw - cx) / rx) ** 2 - ((Yw - cy) / ry) ** 2
        for (lx, ly, lrx, lry) in S['island_lobes'][name]:
            f = np.maximum(f, 1 - ((Xw - lx) / lrx) ** 2 - ((Yw - ly) / lry) ** 2)
        f += S['edge_noise'] * 2 * N
        clip = (Y <= isl_n[:, None]) if name == 'NW' else (Y >= isl_s[:, None])
        islands |= (f > 0) & clip & (X <= S['island_x_max'])
    islets = np.zeros((512, 512), bool)
    for (cx, cy, r, kz) in S['islets']:
        islets |= np.hypot(Xw - cx, Yw - cy) <= r * (1 + 0.3 * 2 * N)
    bars = np.zeros((512, 512), bool)
    for (a, b, w) in S['bars']:
        ax_, ay_ = a
        bx_, by_ = b
        L = max(math.hypot(bx_ - ax_, by_ - ay_), 1)
        t = np.clip(((X - ax_) * (bx_ - ax_) + (Y - ay_) * (by_ - ay_)) / (L * L), 0, 1)
        dd = np.hypot(X - (ax_ + t * (bx_ - ax_)), Y - (ay_ + t * (by_ - ay_)))
        bars |= dd <= w + 1.6 * N
    rs = S['rear_spit']
    spit = rounded_rect(Xw, Y, *rs['x'], *rs['y'], 5) | ((X > rs['x'][1] - 4) & (X <= rs['x'][1] + 2) &
                                                         (Y >= rs['y'][0]) & (Y <= rs['y'][1]))
    mids = np.zeros((512, 512), bool)
    for (cx, cy, r) in S['mid_islets']:
        mids |= np.hypot(X - cx, Y - cy) <= r + 1.5 * N
    land = (fort | plaza | causeway | islands | islets | bars | spit | mids) & west
    mids &= ~(fort | plaza | causeway | islands | islets | bars | spit)
    ch = S['channels']
    cx_ = (X >= ch['x'][0]) & (X <= ch['x'][1])
    land &= ~(cx_ & (Y > isl_n[:, None]) & (Y < np.minimum(sh_n, spit_n)[:, None]))
    land &= ~(cx_ & (Y < isl_s[:, None]) & (Y > np.maximum(sh_s, spit_s)[:, None]))
    land = symmetrize(land)
    d = ndi.distance_transform_edt(land)

    # ------------------------------------------------------------------ heights
    zs = S['z']
    base = np.where(d <= 2, 62, np.where(d <= 4, 61, np.where(d <= 7, 60, 60 - (D > 0.55).astype(int))))
    H = base.astype(float)
    # island knolls (smooth, slope well under 1 per column)
    for name, (cx, cy, rx, ry, _, knolls) in S['islands'].items():
        for (kx, ky, R, kz) in knolls:
            k = kz + (60 - kz) * smooth(np.hypot(X - kx, Y - ky) / R)
            H = np.where(islands & ~causeway & ~plaza & ~fort, np.minimum(H, np.round(k)), H)
    for (cx, cy, r, kz) in S['islets']:
        k = kz + (61 - kz) * smooth(np.hypot(X - cx, Y - cy) / (r * 1.0))
        H = np.where(islets, np.minimum(H, np.round(k)), H)
    # fort courtyard flat; the apron outside it is a natural rocky shore (beach profile)
    H = np.where(court, zs['fort'], H)
    H = np.where(apron & ~court, np.maximum(H, 59), H)
    mound = np.where(M > 0.52, 59, 60)
    H = np.where(plaza, mound, H)
    # causeway: 59 at the plaza edge rising to 57 by the anchor, flat 57 to the axis
    (sx0, sx1) = cw['slope_x']
    prof = np.round(59 - 2 * np.clip((X - sx0) / (sx1 - sx0), 0, 1))
    cmask = causeway & ~plaza & ~fort
    an = S['anchor']
    da = np.maximum(np.maximum(an['x'][0] - 4 - X, X - an['x'][1] - 4), 0)
    k = 1.0 - (1.0 - cw['beach_slope']) * smooth(da / 6)           # 1 beside the anchors, gentler elsewhere
    H = np.where(cmask, np.maximum(prof, np.round(63 - k * d)), H)
    # rear spit: z 60 at the gate, 61 further out (one step at a time back to the gate floor z 59)
    sp = spit & ~fort
    dx_, dy_, dr, dz_ = rs['dune']
    dune = np.round(dz_ + (61 - dz_) * smooth(np.hypot(X - dx_, Y - dy_) / dr))
    H = np.where(sp, np.where(X >= 78, 60, np.minimum(61, dune)), H)
    # mid-channel islets are flat sandbars (z 62)
    H = np.where(mids, 62, H)
    # anchor ground exactly flat
    an = S['anchor']
    anchor = (X >= an['x'][0]) & (X <= an['x'][1]) & (Y >= an['y'][0]) & (Y <= an['y'][1])
    H = np.where(anchor, an['z'], H)
    # coast slope limit: never more than 1 above the water per column inland
    H = np.maximum(H, 63 - d)
    # basalt outcrops (1-2 high) along the fort apron's waterline, outside the gate path and play lanes
    O = noise.fbm2((512, 512), 6, 2, 'outcrop', seed)
    gp = S['gate_path']
    path = (X >= gp['x'][0]) & (X <= gp['x'][1]) & (Y >= gp['y'][0]) & (Y <= gp['y'][1])
    rocky = apron & ~court & ~plaza & ~path & (d >= 2) & (d <= 6) & ((X < ap['outcrop_x_max']) |
                                                                    (Y < 196) | (Y > 316))
    H = np.where(rocky & (O > ap['outcrop'][0]), H - 1, H)
    H = np.where(rocky & (O > ap['outcrop'][1]), H - 1, H)
    H = np.where(path, np.minimum(H, 60), H)
    H = np.where(land, H, 63).astype(int)
    H = symmetrize(H)
    zones = {'land': land, 'fort': symmetrize(court & west), 'apron': symmetrize(apron & ~court & west),
             'outcrop': symmetrize(rocky & (O > ap['outcrop'][0]) & west), 'plaza': symmetrize(plaza & west),
             'causeway': symmetrize(cmask & west), 'islands': symmetrize(islands & west & land),
             'islets': symmetrize((islets | bars | spit | mids) & west & land), 'anchor': symmetrize(anchor & west),
             'd': d}
    return H, zones


def paint_terrain(cv, H, Z):
    """Fill the terrain solid to z 63 and tag materials per zone (flat graybox colours)."""
    cls = np.full((512, 512), 'sea', object)
    cls[Z['land']] = 'grass'
    cls[Z['land'] & (H >= 61)] = 'sand'
    cls[Z['islets'] & (H >= 60)] = 'sand'
    cls[Z['causeway'] | Z['plaza']] = 'laterite'
    cls[Z['causeway'] & (H >= 61)] = 'sand'
    cls[Z['fort']] = 'paving'
    cls[Z['apron'] & (Z['d'] <= 4) & (H <= 61)] = 'rock'
    cls[Z['outcrop']] = 'rock'
    cls[Z['plaza']] = 'laterite'
    cv.fill_terrain(H, GC['sea'], 'sea')
    zz = np.arange(64)[None, None, :]
    below = zz >= H[:, :, None]
    for name in ('grass', 'sand', 'laterite', 'paving', 'rock'):
        m = (cls == name)[:, :, None] & below
        cv.rgb[m] = GC[name]
        cv.mat[m] = cv.material(name)
    cv.material('sea')
    return cls


# =============================================================================================== towers

def _ring_cells(cx, cy, r0, r1):
    out = []
    for x in range(int(cx - r1 - 2), int(cx + r1 + 3)):
        for y in range(int(cy - r1 - 2), int(cy + r1 + 3)):
            dd = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if r0 <= dd <= r1:
                out.append((x, y, math.atan2(y + 0.5 - cy, x + 0.5 - cx)))
    return out


def _radial_carve(cv, cx, cy, ang, r0, r1, z0, z1, width=2):
    """Carve a doorway / slit through a round wall along angle ang (width cells across, z0..z1 inclusive)."""
    ux, uy = math.cos(ang), math.sin(ang)
    px, py = -uy, ux
    cells = set()
    t = r0
    while t <= r1:
        for k in range(width):
            o = k - (width - 1) / 2
            cells.add((int(math.floor(cx + ux * t + px * o)), int(math.floor(cy + uy * t + py * o))))
        t += 0.25
    cells = {(x, y) for (x, y) in cells if math.hypot(x + 0.5 - cx, y + 0.5 - cy) >= r0 - 0.25}
    for (x, y) in cells:
        cv.carve(x, x, y, y, z0, z1)
    return cells


def round_tower(cv, name, cx, cy, G, r, wall, floors, terrace, steps_per_turn, door_angle, upper_doors=(),
                pavilion='large', mast_top=None, sense=1, windows=True, flag='cloth'):
    """Round bastion/tower on ground floor z G: solid wall `wall` thick, a helical stair (2 wide, steps 2 voxels
    thick, hugging the inside of the wall) from G up to the roof terrace at z `terrace`, floor discs at `floors`,
    a crenellated parapet, an optional domed pavilion and flag mast.
    door_angle: ground door (radians, math angle in x/y). upper_doors: [(floor_z, 'name')] doors cut at the angle
    where the stair reaches floor_z. The stair starts beside the ground door and turns `sense` (+1/-1).
    Returns {'doors': {...}, 'top_z': ...}."""
    ri = r - wall
    rin = ri - 2
    T = terrace
    cx_, cy_ = cx + 0.5, cy + 0.5                     # centre of cell (cx, cy)
    cv.cylinder(cx_, cy_, r, T, 62, GC['basalt'], 'basalt')
    inner = _ring_cells(cx_, cy_, 0, ri)
    for (x, y, _) in inner:
        cv.carve(x, x, y, y, T + 1, G - 1)
    # floor discs
    for L in floors:
        for (x, y, _) in _ring_cells(cx_, cy_, 0, rin - 0.01):
            put(cv, x, y, L, 'floor')
    # helical stair: sector s spans [a0 + s*D, a0 + (s+1)*D) in the turning sense
    n = G - T                                         # step tops G-1 ... T
    Nt = steps_per_turn
    D = 2 * math.pi / Nt
    a0 = door_angle - 0.5 * D * sense
    band = _ring_cells(cx_, cy_, rin, ri + 0.3)
    step_tops = {}
    for (x, y, a) in band:
        s = int(((a - a0) * sense) % (2 * math.pi) // D)
        tops = [G - 1 - i for i in range(s, n, Nt)]
        step_tops[(x, y)] = tops
        for k, t in enumerate(tops):
            # first turn: a solid helical ramp down to the floor (no pockets under it); later turns: 2-thick
            # steps hanging off the wall, >= steps_per_turn - 2 voxels above the turn below
            for z in range(t, G if k == 0 else min(t + 2, G)):
                put(cv, x, y, z, 'stair')
    # terrace slab (z T) stays over the disc; open it above steps that still need climb room
    for (x, y), tops in step_tops.items():
        if any(T + 1 <= t <= T + 4 for t in tops):
            cv.clear(x, y, T)
    # parapet ring: 2 high (a player cannot step onto it from the terrace) with loopholes in the lower course
    for (x, y, a) in _ring_cells(cx_, cy_, r - 1.0, r):
        put(cv, x, y, T - 2, 'basalt_dk')
        if int((a + math.pi) / (2 * math.pi) * (r * 4)) % 3 != 0:
            put(cv, x, y, T - 1, 'basalt_dk')
    doors = {}
    # ground door (2 wide x 4 high) through the wall at the stair foot
    _radial_carve(cv, cx_, cy_, door_angle, ri - 0.5, r + 0.6, G - 4, G - 1)
    doors['ground'] = (round(math.degrees(door_angle)), G)
    for (L, dn) in upper_doors:
        i = G - 1 - L
        s = i % Nt
        ang = a0 + (s + 0.5) * D * sense
        _radial_carve(cv, cx_, cy_, ang, ri - 0.5, r + 0.6, L - 3, L - 1)
        doors[dn] = (round(math.degrees(ang)), L)
    # window slits (1 wide x 2 high) on every level, away from the doors
    if windows:
        levels = list(floors)                       # the ground level sits behind the solid first-turn ramp
        for k, L in enumerate(levels, start=1):
            for j in range(4):
                ang = door_angle + math.pi / 4 + j * math.pi / 2 + k * 0.4
                _radial_carve(cv, cx_, cy_, ang, ri + 0.45, r + 0.6, L - 3, L - 2, width=1)
    # domed pavilion on the terrace. 'large'/'small': a chhatri on the core disc (it must stay inside the stair
    # band, which needs 4 voxels of climb room); 'ring': four pillars on the wall ring carrying a lintel disc and a
    # dome over the whole terrace (lintel at T - 4, so the band still has its climb room)
    top_z = T - 2
    if pavilion in ('large', 'small'):
        big = pavilion == 'large'
        h = 4 if big else 3                    # pillar height (air under the lintel slab)
        e = 3 if big else 2
        assert math.hypot(e + 0.5, e + 0.5) < rin, f'{name}: pavilion overlaps the stair band'
        zl = T - 1 - h                         # lintel slab z
        for (sx, sy) in ((-e - 1, -e - 1), (e - 1, -e - 1), (-e - 1, e - 1), (e - 1, e - 1)):
            box(cv, cx + sx, cx + sx + 1, cy + sy, cy + sy + 1, zl + 1, T - 1, 'plaster')
        box(cv, cx - e - 1, cx + e, cy - e - 1, cy + e, zl, zl, 'plaster')
        rd, rz = e + 0.6, (3 if big else 2)
        for x in range(cx - e - 1, cx + e + 1):
            for y in range(cy - e - 1, cy + e + 1):
                for z in range(zl - rz, zl):
                    q = ((x + 0.5 - cx_) / rd) ** 2 + ((y + 0.5 - cy_) / rd) ** 2 + ((z + 1 - zl) / rz) ** 2
                    if q <= 1.0:
                        put(cv, x, y, z, 'plaster')
        crown = zl - rz
    elif pavilion == 'ring':
        zl = T - 4
        for (x, y, a) in _ring_cells(cx_, cy_, ri + 0.5, r - 0.2):
            if min(abs(((a - math.pi / 4) % (math.pi / 2)) - 0), abs(((a - math.pi / 4) % (math.pi / 2)) -
                                                                       math.pi / 2)) < 0.22:
                box(cv, x, x, y, y, zl + 1, T - 1, 'plaster')
        for (x, y, _) in _ring_cells(cx_, cy_, 0, r - 0.6):
            put(cv, x, y, zl, 'plaster')
        rd, rz = r - 1.2, 3
        for (x, y, _) in _ring_cells(cx_, cy_, 0, rd):
            for z in range(zl - rz, zl):
                q = ((x + 0.5 - cx_) / rd) ** 2 + ((y + 0.5 - cy_) / rd) ** 2 + ((z + 1 - zl) / rz) ** 2
                if q <= 1.0:
                    put(cv, x, y, z, 'plaster')
        crown = zl - rz
    if pavilion:
        put(cv, cx, cy, crown, 'plaster')
        top_z = crown
        if mast_top is None:                                    # brass finial on the dome crown
            put(cv, cx, cy, crown - 1, 'finial')
            put(cv, cx, cy, crown - 2, 'finial')
            top_z = crown - 2
        if mast_top is not None:
            for z in range(mast_top, crown):
                put(cv, cx, cy, z, 'mast')
            for z in range(mast_top, mast_top + 3):              # flag, face-joined to the mast
                for k in (1, 2, 3):
                    put(cv, cx + k, cy, z, flag)
            top_z = mast_top
    # interiors: ground core, each floor, terrace
    cv.interiors.append([f'{name} ground', cx, cy, G])
    for L in floors:
        cv.interiors.append([f'{name} floor z{L}', cx, cy, L])
    cv.interiors.append([f'{name} terrace', cx, cy, T])
    return {'name': name, 'doors': doors, 'top_z': top_z, 'centre': (cx, cy), 'r': r, 'G': G, 'T': T}


# =============================================================================================== fort

def fort(cv, S):
    W = S['wall']
    (x0, x1), (y0, y1) = W['x'], W['y']
    G = S['z']['fort']
    wz = W['walk_z']
    rep = {}
    # curtain wall, solid masonry from the wall-walk (z 47) down to the bottom
    box(cv, x0, x1, y0, y1, wz, 62, 'basalt')
    # parapet on the seaward (west) edge: +1 continuous, merlons +2 on alternate pairs
    box(cv, x0, x0, y0, y1, wz - 1, wz - 1, 'basalt_dk')
    for y in range(y0, y1 + 1):
        if (y // 2) % 2 == 0:
            put(cv, x0, y, wz - 2, 'basalt_dk')
    # low kerb on the courtyard edge (1 high, gaps every 6) so the walk reads as a walk
    for y in range(y0, y1 + 1):
        if y % 6 not in (0, 1):
            put(cv, x1, y, wz - 1, 'basalt_dk')
    # casemates: vaulted rooms in the wall, doors to the courtyard, slits to the sea
    for k, (ya, yb) in enumerate(W['casemates']):
        cv.carve(x0 + 1, x1 - 1, ya, yb, G - 5, G - 1)
        box(cv, x0 + 1, x1 - 1, ya, yb, G, G, 'floor')
        ym = (ya + yb) // 2
        cv.carve(x1, x1, ym - 1, ym, G - 3, G - 1)                 # door 2 wide x 3 high
        for ys in range(ya + 1, yb, 4):
            cv.carve(x0, x0, ys, ys, G - 4, G - 3)                 # sea slits
        box(cv, x0 + 1, x0 + 1, yb - 1, yb, G - 1, G - 1, 'furniture')   # bench
        cv.interiors.append([f'casemate {k + 1}', x0 + 2, ym, G])
    # rear gate (4 high) through the full wall
    ga, gb = W['gate_y']
    cv.carve(x0, x1, ga, gb, G - W['gate_h'], G - 1)
    box(cv, x0, x1, ga, gb, G, G, 'paving')
    # stair flights up to the wall-walk on the courtyard side (outside the spawn square)
    for (ys, dy) in W['stairs']:
        box(cv, x1 + 1, x1 + 3, min(ys, ys + dy * (G - wz)), max(ys, ys + dy * (G - wz)), G, G, 'paving')
        straight_stair(cv, ys, x1 + 1, x1 + 3, G, G - wz, dy, GC['stair'], 'stair', along='y')
    rep['wall'] = {'x': [x0, x1], 'y': [y0, y1], 'walk_z': wz}
    cv.interiors.append(['wall-walk north', x0 + 3, y0 + 12, wz])
    cv.interiors.append(['wall-walk south', x0 + 3, y1 - 12, wz])
    # corner bastions: door to the wall-walk at z 47 aimed along the wall
    CB = S['corner_bastion']
    rep['corner_bastions'] = []
    for (cx, cy) in S['corner_bastions']:
        toward = 1 if cy < 256 else -1                              # the wall runs from the bastion toward y 256
        walk_ang = math.atan2(toward * 7.5, (x0 + x1) / 2 - cx)
        # ground door into the courtyard (east); the stair turns so it reaches z 47 at walk_ang
        n_to = G - 1 - S['wall']['walk_z']
        D = 2 * math.pi / CB['steps_per_turn']
        best = None
        for sense in (1, -1):
            ang = walk_ang - (n_to % CB['steps_per_turn']) * D * sense      # step n_to sits at walk_ang
            score = math.cos(ang)                                          # prefer the door facing the courtyard
            if best is None or score > best[0]:
                best = (score, sense, ang)
        _, sense, door_ang = best
        rep['corner_bastions'].append(round_tower(
            cv, f'corner bastion ({cx},{cy})', cx, cy, G, CB['r'], CB['wall'], CB['floors'], CB['terrace'],
            CB['steps_per_turn'], door_ang, upper_doors=[(S['wall']['walk_z'], 'wall-walk')], sense=sense,
            pavilion='large'))
    GB = S['gate_bastion']
    rep['gate_bastions'] = []
    for (cx, cy) in S['gate_bastions']:
        g = G
        door_ang = math.atan2(0, -1)                               # door faces the plaza (west)
        rep['gate_bastions'].append(round_tower(
            cv, f'gate bastion ({cx},{cy})', cx, cy, g, GB['r'], GB['wall'], GB['floors'], GB['terrace'],
            GB['steps_per_turn'], door_ang, pavilion='ring'))
    return rep


def level_disc(cv, cx, cy, r_flat, r_blend, G):
    """Flatten the ground to z G inside r_flat and blend outward so neighbouring columns differ by <= 1
    (fills or carves terrain; keeps cv.H in step)."""
    for x in range(int(cx - r_blend - 1), int(cx + r_blend + 2)):
        for y in range(int(cy - r_blend - 1), int(cy + r_blend + 2)):
            dd = math.hypot(x - cx, y - cy)
            if dd > r_blend:
                continue
            t = ground(cv, x, y)
            if t >= 62:
                continue
            k = 0 if dd <= r_flat else int(math.ceil(dd - r_flat))
            want = int(np.clip(t, G - k, G + k))
            if want < t:
                m = int(cv.mat[x, y, t])
                box(cv, x, x, y, y, want, t - 1, 'paving' if dd <= r_flat else
                    {v: k_ for k_, v in cv.materials.items()}.get(m, 'grass'))
            elif want > t:
                cv.carve(x, x, y, y, t, want - 1)
            cv.H[x, y] = want


def watch_towers(cv, S):
    WT = S['watch_tower']
    out = []
    for (cx, cy) in S['watch_towers']:
        G = int(np.median([ground(cv, cx + dx, cy + dy) for dx in range(-9, 10, 3) for dy in range(-9, 10, 3)]))
        level_disc(cv, cx, cy, 10.5, 16, G)
        door_ang = math.atan2(1 if cy < 256 else -1, -1)                    # toward the channel, spawn side
        out.append(round_tower(cv, f'watch tower ({cx},{cy})', cx, cy, G, WT['r'], WT['wall'], WT['floors'],
                               WT['terrace'], WT['steps_per_turn'], door_ang, pavilion='small',
                               mast_top=WT['mast_top'], flag='cloth' if cy < 256 else 'flag_teal'))
        r0, r1, wh, gap = WT['yard_wall']
        for x in range(int(cx - r1 - 1), int(cx + r1 + 2)):
            for y in range(int(cy - r1 - 1), int(cy + r1 + 2)):
                dd = math.hypot(x + 0.5 - cx - 0.5, y + 0.5 - cy - 0.5)
                a = math.atan2(y - cy, x - cx)
                da = abs((a - door_ang + math.pi) % (2 * math.pi) - math.pi)
                if r0 <= dd < r1 and da > gap:
                    t = ground(cv, x, y)
                    if t < 62:
                        box(cv, x, x, y, y, t - wh, t - 1, 'kerb')
    return out


# =============================================================================================== small buildings

def room(cv, name, x0, x1, y0, y1, G, h=4, door='E', wall='basalt', roof='flat', windows=True):
    """One-room building: walls 1 thick, air h high, door 2 wide x 3 high, slits, roof (flat slab or dome)."""
    tops = {(x, y): ground(cv, x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}
    box(cv, x0, x1, y0, y1, G - h - 1, G - 1, wall)
    cv.carve(x0 + 1, x1 - 1, y0 + 1, y1 - 1, G - h, G - 1)
    box(cv, x0 + 1, x1 - 1, y0 + 1, y1 - 1, G, G, 'floor')
    for x in range(x0, x1 + 1):                         # foundation down to the ground
        for y in range(y0, y1 + 1):
            t = tops[(x, y)]
            if t > G:
                box(cv, x, x, y, y, G, t - 1, wall)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    if door == 'E':
        cv.carve(x1, x1, cy - 1, cy, G - 3, G - 1)
    elif door == 'W':
        cv.carve(x0, x0, cy - 1, cy, G - 3, G - 1)
    elif door == 'N':
        cv.carve(cx - 1, cx, y0, y0, G - 3, G - 1)
    else:
        cv.carve(cx - 1, cx, y1, y1, G - 3, G - 1)
    if windows:
        for (wx, wy) in ((cx, y0), (cx, y1), (x0, cy), (x1, cy)):
            if (door == 'E' and wx == x1) or (door == 'W' and wx == x0) or (door == 'N' and wy == y0) or \
                    (door == 'S' and wy == y1):
                continue
            cv.carve(wx, wx, wy, wy, G - 3, G - 2)
    top = G - h - 1
    if roof == 'dome':
        rx, ry = (x1 - x0 + 1) / 2 - 0.5, (y1 - y0 + 1) / 2 - 0.5
        ccx, ccy = (x0 + x1 + 1) / 2, (y0 + y1 + 1) / 2
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(top - 4, top):
                    q = ((x + 0.5 - ccx) / rx) ** 2 + ((y + 0.5 - ccy) / ry) ** 2 + ((z + 1 - top) / 4) ** 2
                    if q <= 1.0:
                        put(cv, x, y, z, 'plaster')
        top -= 4
        fx, fy = int(ccx), int(ccy)
        put(cv, fx, fy, top - 1, 'finial')
        top -= 1
    cv.interiors.append([name, cx, cy, G])
    return {'name': name, 'box': [x0, x1, y0, y1], 'G': G, 'top_z': top}


def door_ground(cv, r):
    """Ground z just outside a room's door (the room floor is set to it so the doorway is level)."""
    (x0, x1), (y0, y1) = r['x'], r['y']
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    p = {'E': (x1 + 1, cy), 'W': (x0 - 1, cy), 'N': (cx, y0 - 1), 'S': (cx, y1 + 1)}[r['door']]
    return ground(cv, *p)


def guard_hut(cv, x, y):
    G = ground(cv, x + 4, y + 4)
    r = room(cv, 'front guard hut', x, x + 8, y, y + 8, G, h=4, door='N', wall='laterite')
    return r


# =============================================================================================== props

def pad(cv, x0, x1, y0, y1):
    """Level a footprint to its highest ground (fills lower columns with their own top material, <= 2 voxels on
    this map's gentle ground). Returns the floor z. Keeps cv.H in step so the zone rules see it as terrain."""
    tops = [(x, y, ground(cv, x, y)) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]
    land = [t for t in tops if t[2] < 62] or tops
    G = min(t[2] for t in land)
    for (x, y, t) in tops:
        if t > G:
            m = int(cv.mat[x, y, min(t, 63)])
            cv.box(x, x, y, y, G, t - 1, tuple(int(v) for v in cv.rgb[x, y, min(t, 63)]), m)
            cv.H[x, y] = G
    return G


FOOT = {'cannonEW': (0, 7, 0, 4), 'cannonNS': (0, 4, -1, 6), 'crates': (0, 5, 0, 5), 'kegs': (0, 8, 0, 3),
        'cart': (0, 12, -1, 5), 'rack_shelter': (0, 11, 0, 15), 'net_rack': (0, 2, 0, 10), 'boat': (0, 16, -3, 3),
        'boat_shed': (0, 10, 0, 16), 'drying_rack': (0, 2, 0, 13)}


def prop(cv, kind, x, y, arg=None):
    """Low dressing props (graybox). Every piece is face-connected to the ground. Returns a record."""
    key = kind + ('EW' if arg in ('E', 'W') else 'NS') if kind == 'cannon' else kind
    if key in FOOT:
        a, b, c, d = FOOT[key]
        if kind == 'crates' and arg:
            b = d = arg - 1
        G = pad(cv, x + a, x + b, y + c, y + d)
    else:
        G = ground(cv, x, y)
    rec = {'kind': kind, 'x': x, 'y': y}
    if kind == 'garden_wall':                # 2 thick, 4 high laterite wall along x, a 3-wide notch (2 deep) mid-way
        L = arg
        for i in range(L):
            notch = L // 2 - 1 <= i <= L // 2 + 1
            for j in (0, 1):
                g = ground(cv, x + i, y + (j if y < 256 else -j))
                box(cv, x + i, x + i, y + (j if y < 256 else -j), y + (j if y < 256 else -j),
                    g - (2 if notch else 4), g - 1, 'kerb')
        rec['box'] = [x, x + L - 1, min(y, y + (1 if y < 256 else -1)), max(y, y + (1 if y < 256 else -1))]
    elif kind == 'cannon':                   # cannon on a timber carriage: 5 x 8 footprint, 4 tall
        along = arg in ('E', 'W')
        sx = 1 if arg in ('E', 'S') else -1
        if along:
            box(cv, x, x + 6, y, y + 4, G - 2, G - 1, 'timber')          # carriage bed
            box(cv, x + 1, x + 2, y - 0, y + 4, G - 3, G - 1, 'timber')  # axle block
            for wy in (y, y + 4):                                         # wheels (discs 3 high)
                box(cv, x + 1, x + 3, wy, wy, G - 3, G - 1, 'timber')
            bx0 = x + (5 if sx > 0 else -2)
            box(cv, x, x + 7 if sx > 0 else x + 6, y + 2, y + 2, G - 4, G - 4, 'iron')   # barrel
            box(cv, x + 1, x + 4, y + 1, y + 3, G - 3, G - 3, 'iron')
            rec['box'] = [x, x + 7, y, y + 4]
        else:
            box(cv, x, x + 4, y, y + 6, G - 2, G - 1, 'timber')
            for wx in (x, x + 4):
                box(cv, wx, wx, y + 1, y + 3, G - 3, G - 1, 'timber')
            box(cv, x + 2, x + 2, y - 1, y + 6, G - 4, G - 4, 'iron')
            box(cv, x + 1, x + 3, y + 1, y + 4, G - 3, G - 3, 'iron')
            rec['box'] = [x, x + 4, y - 1, y + 6]
    elif kind == 'crates':                   # stacked crates n x n (default 6), 2 tiers (3 + 2 high)
        n = arg or 6
        box(cv, x, x + n - 1, y, y + n - 1, G - 3, G - 1, 'crate')
        box(cv, x + 1, x + n // 2 + 1, y + 1, y + n - 2, G - 5, G - 4, 'crate')
        rec['box'] = [x, x + n - 1, y, y + n - 1]
    elif kind == 'kegs':                     # powder kegs: a 3 x 2 block of upright kegs (each 2 x 2 x 3) + a crate
        for i in range(3):
            for j in range(2):
                box(cv, x + 2 * i, x + 2 * i + 1, y + 2 * j, y + 2 * j + 1, G - 3, G - 1, 'keg')
        box(cv, x + 6, x + 8, y, y + 3, G - 2, G - 1, 'crate')
        rec['box'] = [x, x + 8, y, y + 3]
    elif kind == 'cart':                     # bullock cart: bed 5 x 9 on two wheels, shafts forward, sacks
        box(cv, x, x + 8, y, y + 4, G - 3, G - 3, 'timber')
        for wy in (y - 1, y + 5):
            box(cv, x + 2, x + 4, wy, wy, G - 3, G - 1, 'timber')
        box(cv, x + 3, x + 3, y, y + 4, G - 2, G - 1, 'timber')             # axle + prop under the bed
        for yy in (y + 1, y + 3):
            box(cv, x + 9, x + 10, yy, yy, G - 3, G - 3, 'timber')
            box(cv, x + 10, x + 12, yy, yy, G - 2, G - 2, 'timber')
            put(cv, x + 12, yy, G - 1, 'timber')
        box(cv, x + 1, x + 6, y + 1, y + 3, G - 5, G - 4, 'cloth', (196, 184, 150))
        rec['box'] = [x, x + 12, y - 1, y + 5]
    elif kind == 'shrub':                    # low clipped bush, radius arg
        r = arg
        for X in range(x - r - 1, x + r + 2):
            for Y in range(y - r - 1, y + r + 2):
                for Z in range(G - r - 1, G):
                    if (X - x) ** 2 + (Y - y) ** 2 + ((Z - G + 1) * 1.6) ** 2 <= r * r + 0.5 and \
                            not cv.solid[X, Y, Z]:
                        put(cv, X, Y, Z, 'shrub')
        rec['box'] = [x - r, x + r, y - r, y + r]
    elif kind == 'rack_shelter':             # open-sided fish-drying shelter: 4 posts 2 x 2, roof 12 x 16 at +6
        x1, y1 = x + 11, y + 15
        for (px, py) in ((x, y), (x1 - 1, y), (x, y1 - 1), (x1 - 1, y1 - 1)):
            box(cv, px, px + 1, py, py + 1, G - 5, G - 1, 'timber')
        box(cv, x, x1, y, y1, G - 6, G - 6, 'thatch')
        box(cv, x + 2, x1 - 2, y + 2, y1 - 2, G - 7, G - 7, 'thatch')
        for yy in range(y + 3, y1 - 2, 3):              # hanging racks (low rails, walk-under 3 air)
            box(cv, x + 2, x1 - 2, yy, yy, G - 5, G - 5, 'rope')
        rec['box'] = [x, x1, y, y1]
        cv.interiors.append(['rack shelter', x + 4, y + 6, G])
    elif kind == 'net_rack':                 # two A-frames with a hanging net, 3 x 11
        for py in (y, y + 10):
            box(cv, x, x + 2, py, py, G - 4, G - 1, 'timber')
            cv.carve(x + 1, x + 1, py, py, G - 2, G - 1)
        box(cv, x + 1, x + 1, y, y + 10, G - 5, G - 5, 'timber')
        box(cv, x + 1, x + 1, y + 1, y + 9, G - 4, G - 2, 'net')
        rec['box'] = [x, x + 2, y, y + 10]
    elif kind == 'boat':                     # fishing boat drawn up on the sand, 7 x 17, open hull
        for i in range(17):
            w = 3 if 3 <= i <= 13 else (2 if 1 <= i <= 15 else 1)
            for j in range(-w, w + 1):
                put(cv, x + i, y + j, G - 1, 'hull')
                if abs(j) == w:
                    put(cv, x + i, y + j, G - 2, 'hull')
                    put(cv, x + i, y + j, G - 3, 'hull') if 3 <= i <= 13 else None
        for tx in (x + 5, x + 11):                                       # thwarts
            box(cv, tx, tx, y - 2, y + 2, G - 2, G - 2, 'timber')
        rec['box'] = [x, x + 16, y - 3, y + 3]
    elif kind == 'boat_shed':                # open-ended timber shed with a pitched roof, 9 x 15, sea end open
        x1, y1 = x + 10, y + 16
        box(cv, x, x, y, y1, G - 5, G - 1, 'timber')
        box(cv, x1, x1, y, y1, G - 5, G - 1, 'timber')
        box(cv, x, x1, y1, y1, G - 5, G - 1, 'timber')
        cv.carve(x + 4, x + 6, y1, y1, G - 3, G - 1)                     # back door
        for k in range(6):
            box(cv, x + k, x1 - k, y, y1, G - 6 - k, G - 6 - k, 'thatch')
        cv.carve(x + 1, x1 - 1, y, y1 - 1, G - 5, G - 1)
        rec['box'] = [x, x1, y, y1]
        cv.interiors.append(['boat shed', x + 5, y + 8, G])
    elif kind == 'field_wall':               # laterite field boundary wall, 3 thick x 3 high, open ends
        x1, y1 = arg
        for (px, py, _) in line_points(x, y, 0, x1, y1, 0):
            for (qx, qy) in ((px, py), (px, py + 1), (px, py + 2)):
                g = ground(cv, qx, qy)
                if g < 62:
                    box(cv, qx, qx, qy, qy, g - 3, g - 1, 'kerb')
        rec['box'] = [min(x, x1), max(x, x1), min(y, y1), max(y, y1) + 2]
    elif kind == 'drying_rack':              # long low drying rack (posts + rails), 3 x 14
        for py in range(y, y + 14, 4):
            box(cv, x, x + 2, py, py + 1, G - 3, G - 1, 'timber')
        box(cv, x, x + 2, y, y + 13, G - 4, G - 4, 'rope')
        rec['box'] = [x, x + 2, y, y + 13]
    else:
        raise ValueError(kind)
    rec['G'] = G
    return rec


def baoli(cv, S):
    """Stepped well at the centre (self-symmetric): kerb ring 1 high with gaps on the 4 axes, rings stepping down
    one voxel each from the causeway (z 57) to a water pool (z 63) in the middle."""
    B = S['baoli']
    (cx, cy), h, top, ph = B['c'], B['half'], B['top'], B['pool_half']
    for x in range(cx - h, cx + h + 1):
        for y in range(cy - h, cy + h + 1):
            r = max(abs(x - cx), abs(y - cy))
            cv.carve(x, x, y, y, 0, 62)
            z = min(top + (h - r), 62)                       # r = h: 57, then 58 ... 62 for r <= 3 (pool floor)
            mat = 'kerb' if r == h else ('pool' if r <= ph else 'paving')
            box(cv, x, x, y, y, z, 63, mat)
            if r == h and not (abs(x - cx) <= 1 or abs(y - cy) <= 1):
                put(cv, x, y, z - 1, 'kerb')                  # 1-high kerb, gaps on the axes
    cv.interiors.append(['baoli pool', cx - ph, cy, 62])
    return {'c': [cx, cy], 'half': h, 'pool_floor_z': 62}


# =============================================================================================== vegetation

def can_plant(cv, x, y, R, ok_mats):
    """Trunk lands on real ground (tests the surface), canopy keeps off no-canopy cells, gentle slope."""
    if not (R + 2 <= x < 511 - R - 2 and R + 2 <= y < 511 - R - 2):
        return False
    if x > 254:
        return False
    if (cv.keep[x - 2:x + 3, y - 2:y + 3] & 1).any():
        return False
    if (cv.keep[x - R - 1:x + R + 2, y - R - 1:y + R + 2] & 2).any():
        return False
    t = np.argmax(cv.solid[x - 1:x + 3, y - 1:y + 3], axis=2)
    if t.max() - t.min() > 1 or t.min() >= 62:
        return False
    return cv.mat[x, y, int(t[1, 1])] in [cv.materials.get(m, -1) for m in ok_mats]


BANYAN_DETAILS = ('figs', 'ribbons', 'nest', 'dead_limb', 'trunk_moss', 'root_tint')
PALM_DETAILS = ('coconuts', 'dry_frond', 'trunk_rings', 'shoot', 'fallen_nut')


def banyan(cv, rng, x, y, R):
    """Broad flat canopy (r R), 3 x 3 trunk, 2-4 thick (2 x 2) aerial-root pillars inside the canopy edge.
    Layers are concentric discs stacked face to face; roots run from the canopy floor to the ground."""
    g = ground(cv, x, y)
    hb = int(rng.integers(8, 11))                      # canopy floor height above the ground
    zb = g - hb
    ph = rng.random(2) * 6.283
    k1 = int(rng.integers(3, 6))
    jag = lambda a: 1 + 0.12 * math.sin(k1 * a + ph[0]) + 0.06 * math.sin(2 * k1 * a + ph[1])  # noqa: E731
    layers = [(0, 0.8), (1, 1.0), (2, 1.0), (3, 0.82), (4, 0.5)]
    for (k, f) in layers:
        z = zb - k
        for X in range(int(x - R - 2), int(x + R + 3)):
            for Y in range(int(y - R - 2), int(y + R + 3)):
                a = math.atan2(Y - y, X - x)
                if math.hypot(X - x, Y - y) <= R * f * jag(a) and not cv.solid[X, Y, z]:
                    put(cv, X, Y, z, 'leaf')
    for z in range(zb + 1, g):                         # trunk 3 x 3 into the canopy floor
        box(cv, x - 1, x + 1, y - 1, y + 1, z, z, 'bark')
    roots = []
    nr = int(rng.integers(2, 5))
    a0 = rng.random() * 6.283
    for i in range(nr):
        a = a0 + i * 2 * math.pi / nr + rng.uniform(-0.3, 0.3)
        rr = R * rng.uniform(0.5, 0.65)
        px, py = int(round(x + rr * math.cos(a))), int(round(y + rr * math.sin(a)))
        if (cv.keep[px - 1:px + 3, py - 1:py + 3] & 1).any():
            continue
        gz = min(ground(cv, px + i_, py + j_) for i_ in (0, 1) for j_ in (0, 1))
        if gz >= 62:
            continue
        for z in range(zb + 1, 64):
            if all(cv.solid[px + i_, py + j_, z] for i_ in (0, 1) for j_ in (0, 1)):
                break
            for i_ in (0, 1):
                for j_ in (0, 1):
                    if not cv.solid[px + i_, py + j_, z]:
                        put(cv, px + i_, py + j_, z, 'bark')
        roots.append((px, py))
    details = [BANYAN_DETAILS[i] for i in sorted(rng.choice(len(BANYAN_DETAILS), 3, replace=False))]
    under = [(X, Y) for X in range(int(x - R), int(x + R) + 1) for Y in range(int(y - R), int(y + R) + 1)
             if cv.mat[X, Y, zb] == cv.materials['leaf'] and not cv.solid[X, Y, zb + 1]
             and math.hypot(X - x, Y - y) > 2.5]
    if 'figs' in details and under:                      # fig clusters hanging from the canopy floor
        for i in rng.choice(len(under), min(10, len(under)), replace=False):
            put(cv, *under[i], zb + 1, 'fig')
    if 'ribbons' in details and under:                   # prayer ribbons: 3 strands of 2-3 voxels
        for i in rng.choice(len(under), min(3, len(under)), replace=False):
            for k in range(1, int(rng.integers(3, 5))):
                if cv.solid[under[i][0], under[i][1], zb + k]:
                    break
                put(cv, under[i][0], under[i][1], zb + k, 'ribbon')
    if 'nest' in details:                                # a nest on the crown
        topz = zb - 4
        cand = [(X, Y) for X in range(x - 3, x + 3) for Y in range(y - 3, y + 3)
                if cv.solid[X, Y, topz] and not cv.solid[X, Y, topz - 1]]
        if cand:
            X, Y = cand[int(rng.integers(len(cand)))]
            put(cv, X, Y, topz - 1, 'nest')
    if 'dead_limb' in details:                           # a dead limb from the trunk, face-connected
        a = rng.random() * 6.283
        dx, dy = (1, 0) if abs(math.cos(a)) > abs(math.sin(a)) else (0, 1)
        sgn = 1 if rng.random() < 0.5 else -1
        zl = g - hb // 2 - 1
        for k in range(2, 6):
            X, Y = x + sgn * dx * k, y + sgn * dy * k
            if cv.solid[X, Y, zl]:
                break
            put(cv, X, Y, zl, 'deadwood')
    if 'trunk_moss' in details:                          # paint-type: mark the trunk's lower west face as moss
        for z in range(g - hb // 2, g):
            if cv.mat[x - 1, y, z] == cv.materials['bark']:
                cv.mat[x - 1, y, z] = cv.material('moss')
    if 'root_tint' in details:                           # paint-type: aerial roots in a paler grey bark
        for (px, py) in roots:
            for z in range(zb + 1, g):
                for i_ in (0, 1):
                    for j_ in (0, 1):
                        if cv.mat[px + i_, py + j_, z] == cv.materials['bark']:
                            cv.mat[px + i_, py + j_, z] = cv.material('root')
    return {'species': 'banyan', 'x': x, 'y': y, 'R': R, 'h': g - (zb - 4), 'roots': len(roots), 'zb': zb,
            'g': g, 'details': details}


def palm(cv, rng, x, y):
    """Coconut palm: 1-wide curved trunk (face-connected), a 2 x 2 crown head and 6 drooping fronds."""
    g = ground(cv, x, y)
    h = int(rng.integers(9, 14))
    a = rng.random() * 6.283
    lean = rng.uniform(1.5, 3.5)
    tx, ty = x + lean * math.cos(a), y + lean * math.sin(a)
    pts = []
    for k in range(h + 1):
        f = (k / h) ** 1.8
        pts.append((x + (tx - x) * f, y + (ty - y) * f, g - 1 - k))
    last = None
    for p in pts:
        q = (int(round(p[0])), int(round(p[1])), int(p[2]))
        if last is not None:
            for v in line_points(*last, *q):
                put(cv, *v, 'palm_trunk')
        else:
            put(cv, *q, 'palm_trunk')
        last = q
    hx, hy, hz = last
    box(cv, hx, hx + 1, hy, hy + 1, hz - 1, hz, 'frond')
    nf = int(rng.integers(5, 8))
    b = rng.random() * 6.283
    for i in range(nf):
        ang = b + i * 2 * math.pi / nf
        L = rng.uniform(4, 6.5)
        mid = (hx + 0.5 + 0.6 * L * math.cos(ang), hy + 0.5 + 0.6 * L * math.sin(ang), hz - 2)
        end = (hx + 0.5 + L * math.cos(ang), hy + 0.5 + L * math.sin(ang), hz + 1)
        q0 = (hx, hy, hz - 1)
        q1 = tuple(int(math.floor(v)) for v in mid)
        q2 = tuple(int(math.floor(v)) for v in end)
        for v in line_points(*q0, *q1) + line_points(*q1, *q2):
            if 0 <= v[2] < 62 and not cv.solid[v]:
                put(cv, *v, 'frond')
    details = [PALM_DETAILS[i] for i in sorted(rng.choice(len(PALM_DETAILS), 3, replace=False))]
    if 'coconuts' in details:                            # nuts face-joined under the crown head
        for (X, Y) in ((hx - 1, hy), (hx + 2, hy + 1), (hx, hy - 1), (hx + 1, hy + 2)):
            if rng.random() < 0.8 and not cv.solid[X, Y, hz]:
                put(cv, X, Y, hz, 'coconut')
    if 'dry_frond' in details:                           # paint-type: one frond withered
        for z in range(hz - 3, hz + 3):
            for X in range(hx - 7, hx + 8):
                for Y in range(hy - 7, hy + 8):
                    if cv.mat[X, Y, z] == cv.materials['frond'] and (X - hx) * math.cos(b) + (Y - hy) * \
                            math.sin(b) > 1.5 and abs(-(X - hx) * math.sin(b) + (Y - hy) * math.cos(b)) < 1.2:
                        cv.mat[X, Y, z] = cv.material('dryfrond')
    if 'trunk_rings' in details:                         # paint-type: ringed trunk
        for k, p in enumerate(pts):
            if k % 2 == 0:
                q = (int(round(p[0])), int(round(p[1])), int(p[2]))
                if cv.mat[q] == cv.materials['palm_trunk']:
                    cv.mat[q] = cv.material('palm_ring')
    if 'shoot' in details:                               # a young shoot on top of the head
        put(cv, hx, hy, hz - 2, 'frond_young')
        put(cv, hx + 1, hy, hz - 2, 'frond_young')
    if 'fallen_nut' in details:                          # a fallen coconut at the foot (1 high)
        X, Y = x + (1 if rng.random() < 0.5 else -1), y
        gz = ground(cv, X, Y)
        if gz < 62 and gz == g:
            put(cv, X, Y, gz - 1, 'coconut')
    return {'species': 'palm', 'x': x, 'y': y, 'h': h + 2, 'g': g, 'details': details}


def plant(cv, S, rng):
    rep = {'banyan': [], 'palm': []}
    placed = []
    for (c, count, R) in S['banyan_groves']:
        n = count
        for k in range(600):
            if n <= 0:
                break
            spread = (R + 2) * (0.9 + 1.2 * k / 600)          # widen the search if the grove centre is crowded
            a, rr = rng.random() * 6.283, spread * math.sqrt(rng.random())
            x, y = int(c[0] + rr * math.cos(a)), int(c[1] + rr * math.sin(a))
            Rr = float(R * rng.uniform(0.85, 1.1))
            if any(math.hypot(x - px, y - py) < Rr + pr - 2 for px, py, pr in placed):
                continue
            if not can_plant(cv, x, y, int(math.ceil(Rr)), ('grass', 'sand', 'laterite')):
                continue
            rep['banyan'].append(banyan(cv, rng, x, y, Rr))
            placed.append((x, y, Rr))
            n -= 1
    for (c, count) in S['palm_groves']:
        n = count
        for _ in range(200):
            if n <= 0:
                break
            a, rr = rng.random() * 6.283, 10 * math.sqrt(rng.random())
            x, y = int(c[0] + rr * math.cos(a)), int(c[1] + rr * math.sin(a))
            if any(math.hypot(x - px, y - py) < 5 + pr * 0.6 for px, py, pr in placed):
                continue
            if not can_plant(cv, x, y, 4, ('sand', 'grass')):
                continue
            rep['palm'].append(palm(cv, rng, x, y))
            placed.append((x, y, 3))
            n -= 1
    rep['counts'] = {k: len(v) for k, v in rep.items() if isinstance(v, list)}
    return rep


# =============================================================================================== assembly

def keep_masks(cv, S):
    """No-prop (bit 1) and no-canopy (bit 2) zones."""
    b = S['spawn']['base']
    h = S['spawn']['half']
    m = S['spawn']['keep_margin']
    cv.no_prop(b[0] - h - m, b[0] + h + m, b[1] - h - m, b[1] + h + m, 3)          # spawn square: nothing over it
    fx, fy = S['front']['x'], S['front']['y']
    cv.no_prop(fx[0] - 2, 216 + 2, fy[0] - 1, fy[1] + 1, 3)                        # lane + anchor: no trees
    sx, sy = S['strip']['x'], S['strip']['y']
    cv.no_prop(sx[0] - 6, 256, sy[0] - 4, sy[1] + 4, 3)                           # under the platform
    W = S['wall']
    cv.no_prop(W['x'][0] - 2, W['x'][1] + 4, W['y'][0] - 2, W['y'][1] + 2, 3)
    for (cx, cy) in S['corner_bastions']:
        cv.no_prop(cx - 12, cx + 12, cy - 12, cy + 12, 3)
    for (cx, cy) in S['gate_bastions']:
        cv.no_prop(cx - 8, cx + 8, cy - 8, cy + 8, 3)
    for (cx, cy) in S['watch_towers']:
        cv.no_prop(cx - 12, cx + 12, cy - 12, cy + 12, 3)
    for k in ('shrine', 'hut'):
        r = S[k]
        cv.no_prop(r['x'][0] - 3, r['x'][1] + 6, r['y'][0] - 3, r['y'][1] + 3, 3)
    cv.no_prop(S['rear_spit']['x'][0], 96, 248, 264, 1)                            # gate path
    for (kind, x, y, arg) in S['island_props']:
        if kind == 'field_wall':
            cv.no_prop(min(x, arg[0]) - 2, max(x, arg[0]) + 2, min(y, arg[1]) - 2, max(y, arg[1]) + 3, 1)
        else:
            cv.no_prop(x - 3, x + 14, y - 3, y + 19, 3)
    # the mid-channel: keep the axis column clear of plants (rotation seam)
    cv.no_prop(250, 262, 0, 511, 3)


def build_west(S, seed, veg_seed):
    cv = Canvas(S['name'])
    H, Z = terrain(S, seed)
    paint_terrain(cv, H, Z)
    keep_masks(cv, S)
    rep = {'land_cols': int(Z['land'].sum()), 'water_pct': round(100 * float(1 - Z['land'].mean()), 2)}
    rep['fort'] = fort(cv, S)
    rep['watch_towers'] = watch_towers(cv, S)
    sh, hu = S['shrine'], S['hut']
    G = door_ground(cv, sh)
    rep['shrine'] = room(cv, 'islet shrine', *sh['x'], *sh['y'], G, h=4, door=sh['door'], wall='basalt',
                         roof='dome')
    G = door_ground(cv, hu)
    rep['hut'] = room(cv, 'fisher hut', *hu['x'], *hu['y'], G, h=4, door=hu['door'], wall='timber')
    # porch: thatch roof on two 2 x 2 posts in front of the door
    px0 = hu['x'][1] + 1
    px1 = px0 + hu['porch'] - 1
    for py in (hu['y'][0], hu['y'][1] - 1):
        gz = ground(cv, px1 - 1, py)
        box(cv, px1 - 1, px1, py, py + 1, G - 4, gz - 1, 'timber')
    box(cv, hu['x'][1], px1, hu['y'][0], hu['y'][1], G - 5, G - 5, 'thatch')
    rep['props'] = {'front': [], 'strip': [], 'island': []}
    for (kind, x, y, arg) in S['front_props']:
        if kind == 'guard_hut':
            rep['props']['front'].append(guard_hut(cv, x, y))
        else:
            rep['props']['front'].append(prop(cv, kind, x, y, arg))
    for (kind, x, y, arg) in S['strip_props']:
        rep['props']['strip'].append(prop(cv, kind, x, y, arg))
    for (kind, x, y, arg) in S['island_props'] + S['cover_props']:
        rep['props']['island'].append(prop(cv, kind, x, y, arg))
    rep['baoli'] = baoli(cv, S)
    rng = np.random.default_rng(veg_seed)
    rep['vegetation'] = plant(cv, S, rng)
    return cv, rep, H, Z


# =============================================================================================== one-off

def dhow(cv, S):
    """Beached dhow on its own sandbar (after the rotation; asymmetric). Enterable hold through a breach in the
    hull, a stair up through a hatch to the deck, a raked mast with a lateen yard. Every voxel face-connected."""
    Dh = S['dhow']
    bx0, bx1, by0, by1 = Dh['bar']
    X, Y = np.meshgrid(np.arange(bx0 - 4, bx1 + 5), np.arange(by0 - 4, by1 + 5), indexing='ij')
    cxb, cyb = (bx0 + bx1) / 2, (by0 + by1) / 2
    n = noise.fbm2((512, 512), 10, 2, 'dhowbar', S['layout_seed'])
    f = ((X - cxb) / ((bx1 - bx0) / 2)) ** 2 + ((Y - cyb) / ((by1 - by0) / 2)) ** 2 - 0.3 * (n[X, Y] - 0.5)
    for (x, y, v) in zip(X.ravel(), Y.ravel(), f.ravel()):
        if v <= 1.0 and cv.column_top(x, y) >= 62:
            z = 62 if v > 0.55 else 61
            box(cv, x, x, y, y, z, 62, 'sand')
            cv.H[x, y] = z
    (x0, x1), yc, hb = Dh['x'], Dh['y_c'], Dh['beam_half']
    keel, deck = Dh['keel_z'], Dh['deck_z']
    L = x1 - x0
    hull_cells = []
    for x in range(x0, x1 + 1):
        t = (x - x0) / L
        w = hb * math.sin(math.pi * min(1.0, 0.15 + 0.85 * t)) ** 0.6 if t < 0.95 else 1
        w = max(1, int(round(w)))
        prev = None
        for z in range(deck, keel + 1):
            wz = max(1, int(round(w * (1 - 0.55 * ((z - deck) / (keel - deck)) ** 2))))
            lo, hi = (wz, wz) if prev is None else (min(wz, prev), max(wz, prev))
            for k in range(lo, hi + 1):                    # side cells joined face to face down the hull
                put(cv, x, yc - k, z, 'hull')
                put(cv, x, yc + k, z, 'hull')
            prev = wz
            if z == keel:
                box(cv, x, x, yc - wz, yc + wz, z, z, 'hull')
        hull_cells.append((x, w))
    # end posts
    box(cv, x0, x0, yc - 1, yc + 1, deck - 2, keel, 'hull')
    box(cv, x1, x1, yc - 1, yc + 1, deck - 4, keel, 'hull')
    # hold floor (z 61) and deck (z 56) with a hatch
    for (x, w) in hull_cells[1:-1]:
        wz_floor = max(1, int(round(w * 0.6)))
        box(cv, x, x, yc - wz_floor + 1, yc + wz_floor - 1, 61, 61, 'deck')
        box(cv, x, x, yc - w + 1, yc + w - 1, deck, deck, 'deck')
    hx = x0 + L // 2 + 4
    cv.carve(hx, hx + 6, yc - 1, yc + 1, deck, deck)            # hatch
    straight_stair(cv, hx + 1, yc - 1, yc + 1, 61, 61 - deck, 1, (150, 120, 90), 'stair')
    # breach in the hull (south side) at sand level, 3 wide x 4 high
    cv.carve(x0 + 8, x0 + 10, yc + 2, yc + hb + 1, 57, 60)
    # raked mast and lateen yard
    (mx, my), mtop = Dh['mast']
    for v in line_points(mx, my, deck - 1, mx - 4, my, mtop):
        put(cv, *v, 'mast')
    for v in line_points(mx - 4, my, mtop + 1, mx + 10, my, mtop + 12):
        put(cv, *v, 'mast')
    for v in line_points(mx - 3, my, mtop + 2, mx + 9, my, mtop + 13):     # furled lateen sail under the yard
        if not cv.solid[v]:
            put(cv, *v, 'sail')
        if not cv.solid[v[0], v[1] + 1, v[2]]:
            put(cv, v[0], v[1] + 1, v[2], 'sail')
    cv.interiors.append(['dhow hold', x0 + 12, yc, 61])
    cv.interiors.append(['dhow deck', x0 + 8, yc, deck])
    wb = dict(hull_cells).get(x1 - 4, 2)
    return {'box': [bx0 - 4, bx1 + 4, by0 - 4, by1 + 4], 'mast_top_z': mtop, 'deck_z': deck,
            'geom': {'x1': x1, 'yc': yc, 'w_bow': int(wb), 'eye_z': deck + 2, 'stern_z': deck - 4}}
