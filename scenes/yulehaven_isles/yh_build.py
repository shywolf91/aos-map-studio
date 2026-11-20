"""Yulehaven Isles gameplay geometry (graybox): terrain, islands, skerries, caves, every structure shell.

build_west(S, seed)  terrain for the whole map + every mirrored structure on the west half and the axis halves
                     (cargo ship, islet chamber, bonfire stones are symmetric about x = 256 and built as their
                     west half); then symmetry.mirror_canvas() gives the east side.
build_oneoffs(cv, S, rng)  after the mirror: the unique landmarks (lighthouse, Yule goat, chapel, ice-fishing camp,
                     spruce, sauna jump tower / giant mailbox, iceberg + sky-level tag) - recorded as cosmetic boxes.

Every structure is real (owner rule 2026-10-20): open doorways, rooms, window openings, stairs to every upper floor;
each storey is recorded in cv.interiors for the interiors check. Colours here are graybox function colours keyed by
material; yh_art recolours by material afterwards.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage as ndi

from aosmap.kit import noise
from aosmap.kit.canvas import Canvas, line_points
from aosmap.kit.structures import straight_stair, spiral_stair

# graybox colours by material (yh_art replaces them)
GC = {
    'sea': (34, 62, 78), 'beach': (128, 120, 104), 'rock': (96, 98, 106), 'turf': (82, 92, 70), 'ice': (150, 184, 198),
    'anchor': (120, 110, 96), 'spawn': (110, 120, 90), 'front': (116, 112, 96), 'hop': (90, 92, 100),
    'arch': (84, 86, 96), 'footing': (110, 108, 104), 'floor': (128, 100, 72), 'wall_red': (150, 48, 42),
    'wall_ochre': (186, 136, 62), 'roof': (62, 60, 66), 'trim': (196, 192, 182), 'timber': (104, 84, 66),
    'plank': (130, 104, 76), 'post': (86, 72, 60), 'stair': (150, 120, 90), 'furniture': (96, 74, 56),
    'hull_red': (128, 40, 36), 'hull_dark': (58, 60, 66), 'deck': (140, 116, 84), 'mast': (110, 88, 66),
    'crate': (150, 118, 76), 'present': (170, 50, 50), 'rope': (150, 130, 92), 'stone': (132, 128, 122),
    'stone_dk': (100, 98, 96), 'straw': (196, 160, 82), 'ribbon': (176, 36, 40), 'canvas': (176, 160, 130),
    'pot': (120, 96, 70), 'fish': (176, 164, 140), 'log': (96, 74, 56), 'ember': (180, 80, 40),
    'boulder': (104, 104, 110), 'leaf': (44, 74, 54), 'bark': (84, 62, 48), 'team': (200, 200, 200),
    'lamp': (255, 255, 95), 'glass': (120, 150, 160), 'snowman': (196, 200, 206), 'buoy': (196, 70, 50),
    'iceberg': (170, 200, 212), 'tag': (222, 206, 160), 'sky': (200, 200, 210), 'mail': (176, 40, 36),
    'letter': (204, 196, 176), 'tent': (176, 120, 70), 'bell': (170, 140, 60),
}


def put(cv, x, y, z, mat, c=None):
    cv.set(int(x), int(y), int(z), c or GC.get(mat, (200, 0, 200)), mat)


def box(cv, x0, x1, y0, y1, z0, z1, mat, c=None):
    cv.box(min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), min(z0, z1), max(z0, z1), c or GC.get(mat), mat)


def col_down(cv, x, y, z, mat):
    """Post from z down to the first solid voxel (face-connected to the ground)."""
    zz = int(z)
    while zz < 64 and not cv.solid[x, y, zz]:
        put(cv, x, y, zz, mat)
        zz += 1


def top(cv, x, y):
    return cv.column_top(int(x), int(y))


def smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


# =============================================================================================== terrain

def _ellipse_f(X, Y, cx, cy, rx, ry):
    return 1 - ((X - cx) / rx) ** 2 - ((Y - cy) / ry) ** 2


def terrain(cv, S, seed):
    X, Y = np.meshgrid(np.arange(512, dtype=float), np.arange(512, dtype=float), indexing='ij')
    N1 = noise.fbm2((512, 512), 40, 3, 'coast', seed) - 0.5
    N2 = noise.fbm2((512, 512), 16, 2, 'skerry', seed) - 0.5
    R = noise.fbm2((512, 512), S['island']['relief_cell'], 3, 'relief', seed)
    I = S['island']
    # ---------------------------------------------------------------- spawn island (west)
    f = np.full((512, 512), -9.0)
    for (cx, cy, rx, ry) in I['ellipses']:
        f = np.maximum(f, _ellipse_f(X, Y, cx, cy, rx, ry))
    f += I['edge_noise'] * 2 * N1
    land = f > 0
    xmax = np.full(512, I['x_max'])
    ax, ay = S['anchor']['x'], S['anchor']['y']
    xmax[ay[0]:ay[1] + 1] = ax[1]
    xmax[162:205] = 192                                   # trawler dock basin
    xmax[300:337] = 211                                   # inner south shore reaches the channel (sea passage)
    land &= X <= xmax[None, :]
    land &= X <= 255
    land[ax[0]:ax[1] + 1, ay[0]:ay[1] + 1] = True
    hx, hy, hr = I['cliff_headland']
    head = (X - hx) ** 2 + (Y - hy) ** 2 <= hr * hr
    land |= head & (X <= 255)
    lab, n = ndi.label(land)
    if n > 1:
        sizes = ndi.sum(land, lab, range(1, n + 1))
        land = lab == (1 + int(np.argmax(sizes)))
    d = ndi.distance_transform_edt(land)
    bw, rw = I['beach_w'], I['rise_w']
    # beaches end in a z 62 lip (land, flush with the water) so wading players step straight out
    H_I = np.where(d < bw + 1, 62 - np.floor((d - 1) / 2), 60 - 12 * smooth((d - bw - 1) / rw))
    rel = I['relief_amp'] * np.clip((R - 0.45) / 0.3, 0, 1) ** 1.5 * smooth((d - 8) / 10)
    H_I = H_I - rel
    # granite headland with a sheer seaward face (sea-cave mouth)
    H_I = np.where(head, np.minimum(H_I, 50 - 2 * smooth(1 - np.hypot(X - hx, Y - hy) / hr)), H_I)
    # gameplay zones: spawn square (gentle mounds), front ramp, flat anchor - blended into the terrain
    Z = np.zeros((512, 512), bool)
    T = np.zeros((512, 512))
    b = S['spawn']['base']; h = S['spawn']['half'] + S['spawn']['margin']
    sq = (np.abs(X - b[0]) <= h) & (np.abs(Y - b[1]) <= h)
    mounds = np.round(1.2 * (noise.fbm2((512, 512), 10, 2, 'mounds', seed) - 0.5) * 2).clip(-1, 0)
    Z |= sq
    T = np.where(sq, S['z']['spawn'] + mounds, T)
    fx, fy = S['front']['x'], S['front']['y']
    fr = (X >= b[0] + h) & (X < ax[0]) & (Y >= fy[0] - 4) & (Y <= fy[1] + 4)
    FC = S['front_crest']
    zs, za, zc = S['z']['spawn'], S['anchor']['z'], FC['z']
    c0, c1 = FC['crest']
    prof = np.where(X < c0, zs - (zs - zc) * np.clip((X - FC['x0']) / (c0 - FC['x0']), 0, 1),
                    np.where(X <= c1, zc, zc + (za - zc) * np.clip((X - c1) / (ax[0] - c1), 0, 1)))
    Z |= fr
    T = np.where(fr, np.round(prof), T)
    an = (X >= ax[0]) & (X <= ax[1]) & (Y >= ay[0]) & (Y <= ay[1])
    Z |= an
    T = np.where(an, S['anchor']['z'], T)
    dz, (ix, iy) = ndi.distance_transform_edt(~Z, return_indices=True)
    w = np.clip(1 - dz / S['zone_blend'], 0, 1)
    Tn = T[ix, iy]
    H_I = np.where(land, np.round(H_I * (1 - w) + Tn * w), 63)
    H_I = np.where(Z & land, T, H_I)
    # granite spine over the smugglers' tunnel where it runs under the inner south shore
    (sx0, sx1), sy, sz = S['cave']['spine']
    spine = (X >= sx0) & (X <= sx1) & (np.abs(Y - sy) <= 12) & land
    H_I = np.where(spine, np.minimum(H_I, np.round(sz + 8 * smooth(np.abs(Y - sy) / 12))), H_I)
    # ---------------------------------------------------------------- central islet (symmetric after the mirror)
    C = S['islet']
    fc = np.maximum(_ellipse_f(X, Y, C['c'][0], C['c'][1], C['rx'], C['ry']),
                    _ellipse_f(X, Y, *C['south_lobe'])) + C['edge_noise'] * 2 * N1
    land_c = (fc > 0) & (X >= C['x'][0]) & (X <= C['x'][1])
    dc = ndi.distance_transform_edt(land_c)
    H_C = 62 - np.minimum(dc - 1, 8) / 2
    ox, oy, orr, oz = C['outcrop']
    rho = np.hypot(X - ox, Y - oy) / orr
    H_C = np.where(rho < 1, np.minimum(H_C, oz + (61 - oz) * rho ** 1.6), H_C)
    px, py, pr, pz = C['plateau']
    rho = np.hypot(X - px, Y - py) / pr
    H_C = np.where(rho < 1, np.minimum(H_C, pz + np.round(4 * smooth((rho - 0.75) / 0.25))), H_C)
    lx, ly, lrx, lry = C['lagoon']
    lag = _ellipse_f(X, Y, lx, ly, lrx, lry) > 0
    H_C = np.where(lag, S['z']['ice'], np.round(H_C))
    H_C = np.where(land_c, H_C, 63)
    # ---------------------------------------------------------------- skerries (north + y-mirror south)
    H_S = np.full((512, 512), 63.0)
    sk_land = np.zeros((512, 512), bool)
    for name, (cx, cy, r, pz) in S['skerries'].items():
        for yy in (cy, 511 - cy):
            rho = np.hypot(X - cx, Y - yy) / r
            fs = 1 - rho ** 2 + 0.5 * N2
            m = fs > 0
            hh = 62 - (62 - pz) * np.clip(fs, 0, 1) ** 0.7
            H_S = np.where(m, np.minimum(H_S, np.round(hh)), H_S)
            sk_land |= m
    # ---------------------------------------------------------------- rock hops (north channel) and ice patches
    H = np.minimum(np.minimum(H_I, H_C), H_S)
    hop = np.zeros((512, 512), bool)
    for (hx_, hy_, hs) in S['hops']:
        hop[hx_ - hs:hx_ + hs + 1, hy_ - 1:hy_ + 2] = True
    # 3x3 rocks: centre 61, rim 62 (flush with the water), so a wader steps up 1 then 1 (game and graph model)
    hopc = np.zeros((512, 512), bool)
    for (hx_, hy_, hs) in S['hops']:
        hopc[hx_, hy_] = True
    H = np.where(hop & (H >= 63), np.where(hopc, 61, 62), H)
    ice = np.zeros((512, 512), bool)
    td = S['trawler_dock']
    ice[td['pier_x'][0]:td['boat_x'][1] + 5, td['pier_y'][0] - 4:td['pier_y'][1] + 1] = True
    ice &= (H >= 63) & (X <= 214)
    H = np.where(ice, S['z']['ice'], H)
    H = np.clip(H, 0, 63).astype(int)
    H[256:] = 63          # east half comes from the mirror
    # materials
    mat = np.full((512, 512), 'sea', object)
    rockish = (H < 59)
    mat[(H < 63)] = 'beach'
    # the islet spine: the sea passage enters the plateau through rock
    
    mat[rockish] = 'rock'
    turfm = rockish & (noise.fbm2((512, 512), 12, 2, 'turf', seed) > 0.52) & land
    mat[turfm] = 'turf'
    mat[lag & land_c] = 'ice'
    mat[ice] = 'ice'
    mat[hop & (H < 62)] = 'hop'
    mat[Z & land & sq] = 'spawn'
    mat[Z & land & fr] = 'front'
    mat[Z & land & an] = 'anchor'
    cv.H = H.astype(np.int16)
    zz = np.arange(64)[None, None, :]
    for m in ('sea', 'beach', 'rock', 'turf', 'ice', 'hop', 'spawn', 'front', 'anchor'):
        mm = (mat == m)[:, :, None] & (zz >= H[:, :, None])
        cv.fill_mask(mm, GC[m], m)
    cv.no_prop(b[0] - h, b[0] + h, b[1] - h, b[1] + h, 1)
    cv.no_prop(ax[0] - 2, 255, ay[0] - 2, ay[1] + 2, 2)
    return {'land_island': land, 'land_islet': land_c, 'lagoon': lag, 'skerry': sk_land, 'zones': Z,
            'H0': H.copy()}


# =============================================================================================== small helpers

def pad(cv, x0, x1, y0, y1, z=None, mat='footing'):
    """Level a building pad: solid from z down, air above (keeps 'ground is solid all the way down')."""
    if z is None:
        z = int(np.median(cv.tops()[x0:x1 + 1, y0:y1 + 1]))
    cv.carve(x0, x1, y0, y1, 0, z - 1)
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            t = top(cv, x, y)
            if t > z:
                box(cv, x, x, y, y, z, t - 1, mat)
    return z


def gable_roof(cv, x0, x1, y0, y1, zt, ridge='x', mat='roof', over=1):
    """Stepped gable roof above wall-top z zt; every layer is 2 deep so steps share faces; gable ends walled."""
    if ridge == 'x':
        a0, a1, b0, b1 = y0, y1, x0, x1
    else:
        a0, a1, b0, b1 = x0, x1, y0, y1

    def P(a, b, z, m):
        if ridge == 'x':
            put(cv, b, a, z, m)
        else:
            put(cv, a, b, z, m)
    k = 0
    while True:
        lo, hi = a0 - over + k, a1 + over - k
        z = zt - 1 - k
        if lo >= hi - 1:
            for a in range(lo, hi + 1):
                for b in range(b0 - over, b1 + over + 1):
                    P(a, b, z, mat)
            break
        for b in range(b0 - over, b1 + over + 1):
            for a in (lo, lo + 1, hi - 1, hi):
                P(a, b, z, mat)
        if k >= over:                                       # gable end walls inside the walls' outline
            for a in range(lo + 2, hi - 1):
                for b in (b0, b1):
                    P(a, b, z, 'timber')
        k += 1
    return zt - 1 - k                                       # ridge z


def windows_on(cv, x0, x1, y0, y1, fz, lights, every=4, sill=2, hgt=2):
    """Window openings (2 wide, 2 tall) on all four walls of one storey; a candle on each sill (glow)."""
    out = []
    for wx in range(x0 + 3, x1 - 2, every):
        for wy in (y0, y1):
            out.append((wx, wy, 'x'))
    for wy in range(y0 + 3, y1 - 2, every):
        for wx in (x0, x1):
            out.append((wx, wy, 'y'))
    for (wx, wy, ax) in out:
        for k in range(2):
            xx, yy = (wx + k, wy) if ax == 'x' else (wx, wy + k)
            for z in range(fz - sill - hgt + 1, fz - sill + 1):
                cv.clear(xx, yy, z)
        lights.append(((wx, wy) if ax == 'x' else (wx, wy), fz - sill, ax))
    return len(out)


# =============================================================================================== buildings

def cabin(cv, rep, name, x0, x1, y0, y1, storeys=1, ridge='x', door='S', wall='red', stilt_floor=None, sh=5):
    """Fishing cabin: footing or stilts, floor slab, timber walls, real door, windows with candles, inner stair to the
    upper floor, stepped gable roof. Records every storey."""
    wm = 'wall_red' if wall == 'red' else 'wall_ochre'
    if stilt_floor is None:
        g = pad(cv, x0 - 1, x1 + 1, y0 - 1, y1 + 1)
        fz = g - 1                                       # floor one step above the ground on a stone footing
        box(cv, x0, x1, y0, y1, fz, fz, 'footing')
    else:
        fz = stilt_floor
        cv.carve(x0, x1, y0, y1, 0, fz - 1)
        box(cv, x0, x1, y0, y1, fz, fz, 'floor')
        for x in sorted({x0, (x0 + x1) // 2, x1}):
            for y in sorted({y0, (y0 + y1) // 2, y1}):
                col_down(cv, x, y, fz + 1, 'post')
        g = None
    zt = fz - sh * storeys
    box(cv, x0, x1, y0, y1, zt, fz - 1, wm)
    cv.carve(x0 + 1, x1 - 1, y0 + 1, y1 - 1, zt, fz - 1)
    for k in range(1, storeys):
        box(cv, x0 + 1, x1 - 1, y0 + 1, y1 - 1, fz - sh * k, fz - sh * k, 'floor')
    for (cx_, cy_) in ((x0, y0), (x0, y1), (x1, y0), (x1, y1)):          # white corner boards
        box(cv, cx_, cx_, cy_, cy_, zt, fz - 1, 'trim')
    lights = rep.setdefault('window_lights', [])
    for k in range(storeys):
        windows_on(cv, x0, x1, y0, y1, fz - sh * k, lights)
    ridge_z = gable_roof(cv, x0, x1, y0, y1, zt, ridge)
    rep.setdefault('eaves', []).append((x0, x1, y0, y1, zt, ridge))
    for k in range(storeys - 1):
        f = fz - sh * k
        if (x1 - x0) >= (y1 - y0):
            straight_stair(cv, x0 + 2, y0 + 1 if k % 2 == 0 else y1 - 2, y0 + 2 if k % 2 == 0 else y1 - 1, f, sh,
                           1, GC['stair'], 'stair')
        else:
            straight_stair(cv, y0 + 2, x0 + 1, x0 + 2, f, sh, 1, GC['stair'], 'stair', along='y')
    # door (3 wide, 4 tall) + outside stair to a raised floor
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    dsp = {'S': (cx - 1, cx + 1, y1, y1), 'N': (cx - 1, cx + 1, y0, y0), 'E': (x1, x1, cy - 1, cy + 1),
           'W': (x0, x0, cy - 1, cy + 1)}[door]
    cv.carve(dsp[0], dsp[1], dsp[2], dsp[3], fz - 4, fz - 1)
    rep.setdefault('doors', []).append((name, door, dsp, fz))
    if stilt_floor is not None:
        g2 = int(np.median([top(cv, *p) for p in ((cx, y1 + 3), (cx, y0 - 3), (x1 + 3, cy), (x0 - 3, cy))]))
        rise = max(0, _ground_out(cv, door, dsp, fz) - fz)
        if rise > 0:
            _outside_stair(cv, door, dsp, fz, rise)
    # furniture: table + bench + bunk on the ground floor, kept off the stair and door lines
    f = fz
    box(cv, x1 - 3, x1 - 2, y1 - 3 if door != 'S' else y0 + 3, y1 - 3 if door != 'S' else y0 + 3, f - 1, f - 1,
        'furniture')
    for k in range(storeys):
        ix = (x0 + x1) // 2 + 1
        iy = (y0 + y1) // 2
        cv.interiors.append([f'{name} floor {k}', ix, iy, fz - sh * k])
    rep.setdefault('buildings', []).append({'name': name, 'box': [x0, x1, y0, y1, ridge_z, fz], 'storeys': storeys})
    return fz, zt


def _ground_out(cv, door, dsp, fz):
    x0, x1, y0, y1 = dsp
    if door == 'S':
        return top(cv, (x0 + x1) // 2, y1 + 1)
    if door == 'N':
        return top(cv, (x0 + x1) // 2, y0 - 1)
    if door == 'E':
        return top(cv, x1 + 1, (y0 + y1) // 2)
    return top(cv, x0 - 1, (y0 + y1) // 2)


def _outside_stair(cv, door, dsp, fz, rise, mat='stair'):
    """Straight stair from the ground outside a door up to floor fz (steps run away from the wall)."""
    x0, x1, y0, y1 = dsp
    g = fz + rise
    if door == 'S':
        straight_stair(cv, y1 + rise, x0, x1, g, rise, -1, GC['stair'], mat, along='y')
    elif door == 'N':
        straight_stair(cv, y0 - rise, x0, x1, g, rise, 1, GC['stair'], mat, along='y')
    elif door == 'E':
        straight_stair(cv, x1 + rise, y0, y1, g, rise, -1, GC['stair'], mat)
    else:
        straight_stair(cv, x0 - rise, y0, y1, g, rise, 1, GC['stair'], mat)
    # support every step down to the ground
    for i in range(1, rise + 1):
        for a in range(x0, x1 + 1) if door in 'NS' else range(y0, y1 + 1):
            if door == 'S':
                col_down(cv, a, y1 + rise - (i - 1), g - i + 1, 'stair')
            elif door == 'N':
                col_down(cv, a, y0 - rise + (i - 1), g - i + 1, 'stair')
            elif door == 'E':
                col_down(cv, x1 + rise - (i - 1), a, g - i + 1, 'stair')
            else:
                col_down(cv, x0 - rise + (i - 1), a, g - i + 1, 'stair')


def boathouse(cv, rep, name, x0, x1, y0, y1, fz=57):
    """Boathouse half over the water: floor on posts, a slip of open water in the middle, sea doors open to the north,
    land door to the south, a stair out of the slip, a loft ladder-stair. Interiors recorded."""
    cv.carve(x0, x1, y0, y1, 0, fz - 1)
    box(cv, x0, x1, y0, y1, fz, fz, 'floor')
    sx0, sx1 = (x0 + x1) // 2 - 2, (x0 + x1) // 2 + 2
    cv.carve(sx0, sx1, y0, y1 - 6, fz, fz)                        # the slip
    for x in range(x0, x1 + 1, 4):
        for y in (y0, (y0 + y1) // 2, y1):
            if not (sx0 <= x <= sx1):
                col_down(cv, x, y, fz + 1, 'post')
    zt = fz - 7
    box(cv, x0, x1, y0, y1, zt, fz - 1, 'wall_red')
    cv.carve(x0 + 1, x1 - 1, y0 + 1, y1 - 1, zt, fz - 1)
    cv.carve(sx0 - 1, sx1 + 1, y0, y0, fz - 6, fz)                # sea doors (wide open)
    cx = (x0 + x1) // 2
    cv.carve(cx - 1, cx + 1, y1, y1, fz - 4, fz - 1)              # land door
    lights = rep.setdefault('window_lights', [])
    windows_on(cv, x0, x1, y0 + 2, y1, fz, lights, every=5)
    gable_roof(cv, x0, x1, y0, y1, zt, 'y')
    rep.setdefault('eaves', []).append((x0, x1, y0, y1, zt, 'y'))
    # stair out of the slip: water floor 62 -> boathouse floor fz, along -y at the slip's inner end
    rise = 63 - fz
    for i in range(1, rise + 1):                                   # steps climbing south out of the slip
        yy = y1 - 6 - rise + i
        box(cv, sx0, sx1, yy, yy, 63 - i, 63, 'stair')
    # land side: steps down to the ground if needed
    g = top(cv, cx, y1 + 1)
    if g > fz:
        _outside_stair(cv, 'S', (cx - 1, cx + 1, y1, y1), fz, g - fz)
    rep.setdefault('doors', []).append((name, 'S', (cx - 1, cx + 1, y1, y1), fz))
    cv.interiors.append([f'{name} floor', x0 + 2, y1 - 3, fz])
    # team pennant on the gable (team_recolor)
    rz = zt - 1 - ((x1 - x0) // 2 + 1)
    for z in range(rz - 6, rz):
        put(cv, cx, y0 + 1, z, 'mast')
    box(cv, cx + 1, cx + 4, y0 + 1, y0 + 1, rz - 6, rz - 4, 'team')
    rep.setdefault('buildings', []).append({'name': name, 'box': [x0, x1, y0, y1, rz, fz], 'storeys': 1})


def pier(cv, x0, x1, ya, yb, z=60, posts=4, ladders=8, mat='plank', along='y', broken=None):
    """Plank jetty (deck z) along y (or x); posts to the seabed; step blocks at z 61 every `ladders` so a swimmer can
    climb back out (water floor 62 -> 61 -> 60). broken=(a, b): that stretch sags 1 lower and loses its edge planks."""
    lo, hi = sorted((ya, yb))
    for t in range(lo, hi + 1):
        sag = False
        for s in range(x0, x1 + 1):
            X, Y = (s, t) if along == 'y' else (t, s)
            g = top(cv, X, Y)
            zz = z
            sag = bool(broken and broken[0] <= t <= broken[1])
            if sag:
                zz = z + 1
                if s in (x0, x1) and (t % 3):
                    continue
            if g <= zz:
                continue
            put(cv, X, Y, zz, mat)
            if ((t - lo) % posts == 0 and s in (x0, x1)) or sag:
                col_down(cv, X, Y, zz + 1, 'post')
        if (t - lo) % ladders == 4:
            for s, s2 in ((x0 - 1, x0 - 2), (x1 + 1, x1 + 2)):
                X, Y = (s, t) if along == 'y' else (t, s)
                X2, Y2 = (s2, t) if along == 'y' else (t, s2)
                if top(cv, X, Y) >= 63 and top(cv, X2, Y2) >= 63:
                    box(cv, X, X, Y, Y, z + 1, 63, 'stair')         # one below the deck
                    box(cv, X2, X2, Y2, Y2, z + 2, 63, 'stair')     # two below: out of the water


def rope_bridge(cv, p0, p1, z0, z1, w=3, sag=2):
    """Plank deck from p0 to p1 (any heading), deck height interpolated z0 -> z1 with a gentle sag (<= 1 per step),
    rope rails on posts every 4 planks. Ends are cut into the rock so they meet the skerry tops."""
    x0, y0 = p0
    x1, y1 = p1
    z0, z1 = top(cv, x0, y0), top(cv, x1, y1)              # the deck ends sit on the skerry tops
    L = int(max(abs(x1 - x0), abs(y1 - y0)))
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    nx, ny = -uy, ux
    prev = None
    pts = []
    for i in range(L + 1):
        t = i / L
        zz = round(z0 + (z1 - z0) * t + sag * math.sin(math.pi * t))
        if prev is not None and abs(zz - prev) > 1:
            zz = prev + (1 if zz > prev else -1)
        prev = zz
        cx, cy = x0 + ux * i, y0 + uy * i
        for k in range(-(w // 2), w // 2 + 1):
            X, Y = int(round(cx + nx * k)), int(round(cy + ny * k))
            cv.carve(X, X, Y, Y, zz - 3, zz - 1)
            put(cv, X, Y, zz, 'plank')
            # fill diagonal gaps between successive planks
            pts.append((X, Y, zz))
        if i % 4 == 0:
            for k in (-(w // 2) - 1, w // 2 + 1):
                X, Y = int(round(cx + nx * k)), int(round(cy + ny * k))
                for z in range(zz - 2, zz + 1):
                    put(cv, X, Y, z, 'post')
    have = {(p[0], p[1]): p[2] for p in pts}
    for (X, Y, zz) in pts:                                       # face-connect diagonal steps of the deck
        for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            if (X + dx, Y + dy) in have and (X + dx, Y) not in have and (X, Y + dy) not in have:
                put(cv, X + dx, Y, zz, 'plank')
                have[(X + dx, Y)] = zz
    # rope rails: a line 2 above the deck on each side, joining the posts
    for k in (-(w // 2) - 1, w // 2 + 1):
        prevp = None
        for i in range(0, L + 1, 4):
            t = i / L
            zz = round(z0 + (z1 - z0) * t + sag * math.sin(math.pi * t)) - 2
            cx, cy = x0 + ux * i, y0 + uy * i
            q = (int(round(cx + nx * k)), int(round(cy + ny * k)), zz)
            if prevp is not None:
                for (a, b, c) in line_points(*prevp, *q):
                    put(cv, a, b, c, 'rope')
            prevp = q


# =============================================================================================== props (low)

def crate_stack(cv, x, y, n=3, mat='pot', size=2):
    g = top(cv, x, y)
    z = g - 1
    for k in range(n):
        ox = (k % 2) * size
        box(cv, x + ox, x + ox + size - 1, y, y + size - 1, z - size + 1, z, mat)
        if k % 2 == 1:
            z -= size
    return g


def boat_trestle(cv, x, y, L=12, W=5):
    """Upturned rowing boat on two trestles (low front dressing, 4 tall)."""
    g = top(cv, x + L // 2, y + W // 2)
    for tx in (x + 2, x + L - 3):
        for yy in (y, y + W - 1):
            box(cv, tx, tx, yy, yy, g - 2, g - 1, 'timber')
        box(cv, tx, tx, y, y + W - 1, g - 2, g - 2, 'timber')
    for i in range(L):
        half = (W // 2) * (1.0 if 2 <= i <= L - 3 else 0.5)
        for j in range(W):
            if abs(j - W // 2) <= half:
                put(cv, x + i, y + j, g - 3, 'hull_red')
        put(cv, x + i, y + W // 2, g - 4, 'hull_red')
    for i in range(L):
        for j in range(W):
            if cv.solid[x + i, y + j, g - 3]:
                col_down(cv, x + i, y + j, g - 2, 'timber') if (i in (2, L - 3)) else None


def woodpile(cv, x, y, L=6, W=3, H=3):
    g = top(cv, x, y)
    box(cv, x, x + L - 1, y, y + W - 1, g - H, g - 1, 'log')


def net_reel(cv, x, y):
    g = top(cv, x, y)
    for z in range(g - 4, g):
        put(cv, x, y, z, 'timber')
        put(cv, x + 3, y, z, 'timber')
    box(cv, x, x + 3, y, y, g - 4, g - 4, 'timber')
    box(cv, x + 1, x + 2, y - 1, y + 1, g - 4, g - 2, 'rope')


def kicksled(cv, x, y):
    g = top(cv, x, y)
    box(cv, x, x + 5, y, y, g - 1, g - 1, 'timber')
    box(cv, x, x + 5, y + 2, y + 2, g - 1, g - 1, 'timber')
    box(cv, x + 1, x + 2, y, y + 2, g - 2, g - 2, 'plank')
    box(cv, x + 4, x + 4, y, y + 2, g - 4, g - 2, 'timber')


def boulder(cv, x, y, r=3, seed=0):
    g = top(cv, x, y)
    rng = np.random.default_rng(seed)
    cv.ellipsoid(x, y, g - r * 0.55, r * rng.uniform(0.9, 1.25), r * rng.uniform(0.9, 1.25), r * 0.95,
                 GC['boulder'], 'boulder')
    for xx in range(int(x - r - 2), int(x + r + 3)):          # sink into the ground: no gap under the boulder
        for yy in range(int(y - r - 2), int(y + r + 3)):
            col = cv.solid[xx, yy]
            zs = np.nonzero(col)[0]
            if len(zs) and cv.mat[xx, yy, zs[0]] == cv.materials.get('boulder'):
                col_down(cv, xx, yy, zs[0], 'boulder')


def drying_rack(cv, x, y, along_y=False, L=10):
    """Stockfish rack: two post frames, a ridge pole and two side poles with rows of hanging fish (9 tall)."""
    g = min(top(cv, x, y), top(cv, x + (0 if along_y else L), y + (L if along_y else 0)))

    def P(u, v, z, m):
        put(cv, x + (v if along_y else u), y + (u if along_y else v), z, m)
    for u in (0, L):
        for v in (-3, 3):
            for z in range(g - 8, g):
                P(u, v, z, 'timber')
            col_down(cv, x + (v if along_y else u), y + (u if along_y else v), g, 'timber')
        for v in range(-3, 4):
            P(u, v, g - 8, 'timber')
    for u in range(0, L + 1):
        P(u, 0, g - 9, 'timber')
        P(u, -3, g - 6, 'timber')
        P(u, 3, g - 6, 'timber')
    for u in range(1, L, 2):
        for v in (-3, 3):
            P(u, v, g - 5, 'fish')
            P(u, v, g - 4, 'fish')


def fish_shed(cv, rep, x, y, name):
    """One-room fish shed on the front (owner: one-storey one-room houses are fine): 8 x 7, open doors at both
    ends (walk-through along x), windows, a low gable roof; 9 tall."""
    x0, x1, y0, y1 = x, x + 7, y, y + 6
    g = pad(cv, x0 - 1, x1 + 1, y0 - 1, y1 + 1)
    fz = g
    zt = fz - 5
    box(cv, x0, x1, y0, y1, zt, fz - 1, 'wall_ochre' if (x + y) % 2 else 'wall_red')
    cv.carve(x0 + 1, x1 - 1, y0 + 1, y1 - 1, zt, fz - 1)
    cy = (y0 + y1) // 2
    cv.carve(x0, x0, cy - 1, cy + 1, fz - 4, fz - 1)
    cv.carve(x1, x1, cy - 1, cy + 1, fz - 4, fz - 1)
    lights = rep.setdefault('window_lights', [])
    windows_on(cv, x0, x1, y0, y1, fz, lights, every=5)
    gable_roof(cv, x0, x1, y0, y1, zt, 'x', over=0)              # no overhang: the shed stays <= 9 tall
    rep.setdefault('eaves', []).append((x0, x1, y0, y1, zt, 'x'))
    box(cv, x0 + 2, x0 + 3, y1 - 1, y1 - 1, fz - 1, fz - 1, 'crate')
    cv.interiors.append([name, x0 + 4, cy, fz])
    rep.setdefault('buildings', []).append({'name': name, 'box': [x0, x1, y0, y1, zt - 4, fz], 'storeys': 1})


# =============================================================================================== trawler and ship

def trawler(cv, rep, x0, x1, y0, y1, ice_z=62, deck=56):
    """Fishing trawler frozen at the dock, bow north. Hull in the ice, deck, a hold with a hatch stair, an enterable
    wheelhouse aft, a mast (string lights are art), a gangway stair from the ice to the deck."""
    L = y1 - y0 + 1
    cxm = (x0 + x1) / 2
    hw0 = (x1 - x0) / 2
    for i in range(L):
        y = y0 + i
        taper = min(1.0, 0.35 + i / 8) if i < 8 else (1.0 if i < L - 2 else 0.85)
        hw = hw0 * taper
        for x in range(x0, x1 + 1):
            if abs(x + 0.5 - (cxm + 0.5)) <= hw + 0.01:
                for z in range(deck - 1, ice_z + 1):
                    edge = abs(x + 0.5 - (cxm + 0.5)) > hw - 1 or i == 0 or i == L - 1
                    if edge:
                        put(cv, x, y, z, 'hull_red' if z < 59 else 'hull_dark')
                    else:
                        cv.clear(x, y, z)
                put(cv, x, y, deck, 'deck')
                put(cv, x, y, ice_z, 'hull_dark')
                if abs(x + 0.5 - (cxm + 0.5)) > hw - 1:
                    put(cv, x, y, deck - 1, 'hull_red')         # bulwark
    # hold: air 57-60 above a floor at 61, hatch stair to the deck
    box(cv, x0 + 2, x1 - 2, y0 + 6, y1 - 4, 61, 61, 'plank')
    cv.carve(x0 + 2, x1 - 2, y0 + 6, y1 - 4, 57, 60)
    straight_stair(cv, y0 + 8, x0 + 2, x0 + 3, 61, 61 - deck, 1, GC['stair'], 'stair', along='y')
    cv.interiors.append(['trawler hold', int(cxm) + 1, y1 - 6, 61])
    # wheelhouse aft
    wy0, wy1 = y1 - 9, y1 - 3
    box(cv, x0 + 1, x1 - 1, wy0, wy1, deck - 6, deck - 1, 'wall_ochre')
    cv.carve(x0 + 2, x1 - 2, wy0 + 1, wy1 - 1, deck - 5, deck - 1)
    box(cv, x0, x1, wy0 - 1, wy1 + 1, deck - 6, deck - 6, 'roof')
    cv.carve(int(cxm) - 1, int(cxm) + 1, wy0, wy0, deck - 4, deck - 1)          # door, facing the bow
    for wx in (x0 + 1, x1 - 1):
        cv.carve(wx, wx, wy0 + 2, wy0 + 3, deck - 4, deck - 3)
    cv.interiors.append(['trawler wheelhouse', int(cxm), wy0 + 3, deck])
    rep.setdefault('lanterns', []).append((x0 + 1, wy0 - 1, deck - 6))
    # mast + boom (fore, ahead of the hold hatch)
    mx = int(cxm)
    for z in range(deck - 18, deck):
        put(cv, mx, y0 + 4, z, 'mast')
    box(cv, mx - 3, mx + 3, y0 + 4, y0 + 4, deck - 14, deck - 14, 'mast')
    rep['trawler_mast'] = (mx, y0 + 4, deck - 18, y0 + 1, wy0 - 1, deck - 1)
    # gangway: ice -> deck along the east hull, rising north
    rise = ice_z - deck
    yy = y1 - 6
    straight_stair(cv, yy - rise, x1 + 1, x1 + 3, ice_z, rise, 1, GC['stair'], 'stair', along='y')
    box(cv, x1 + 1, x1 + 3, yy, yy, deck, deck, 'plank')
    cv.carve(x1, x1, yy - 1, yy + 1, deck - 3, deck - 1)            # gap in the bulwark
    rep.setdefault('buildings', []).append({'name': 'trawler', 'box': [x0, x1, y0, y1, deck - 18, ice_z]})


def cargo_ship(cv, rep, S):
    """Ice-locked cargo ship on the islet lagoon, bow north, on the axis (built as its west half + axis columns, the
    mirror completes it). Hold (breaches on both sides at ice level, two stairs to the deck), forecastle cabin,
    two-storey deckhouse (mess + wheelhouse), two masts kept >= 25 below the platform."""
    P = S['ship']
    y0, y1 = P['y']
    cxs = P['x_c']
    hw = P['beam_half']
    keel, deck, hold = P['keel_z'], P['deck_z'], P['hold_floor']
    L = y1 - y0 + 1

    def half(i):
        if i < 16:
            return hw * (0.25 + 0.75 * math.sqrt(i / 16))
        if i > L - 5:
            return hw * (0.85 + 0.15 * (L - 1 - i) / 4)
        return hw
    for i in range(L):
        y = y0 + i
        h = half(i)
        for x in range(cxs - hw - 1, 256):
            dx = abs(x - cxs)
            if dx > h + 0.01:
                continue
            for z in range(deck, keel + 1):
                # hull flare: lower strakes tuck in by 1 below the waterline band
                if z > 58 and dx > h - 1 and dx > 1 and (z - 58) > (h - dx) * 2 + 1:
                    continue
                shell = dx > h - 1 or i == 0 or i == L - 1
                if shell:
                    put(cv, x, y, z, 'hull_dark' if z <= 54 else 'hull_red')
                else:
                    cv.clear(x, y, z)
            put(cv, x, y, deck, 'deck')
            if dx > h - 1:
                put(cv, x, y, deck - 1, 'hull_dark')                 # bulwark
    # hold floor (whole hull, so the bow has no pit) + air
    for i in range(1, L - 1):
        h = half(i)
        for x in range(cxs - hw, 256):
            if abs(x - cxs) <= h - 1:
                box(cv, x, x, y0 + i, y0 + i, hold, keel, 'plank')
    cv.carve(cxs - hw + 1, 255, y0 + 14, y1 - 3, deck + 1, hold - 1)
    # forecastle side walls (hull shell carried up)
    for i in range(0, P['forecastle_y'][1] - y0 + 1):
        h = half(i)
        for x in range(cxs - hw - 1, 256):
            dx = abs(x - cxs)
            if h - 1 < dx <= h + 0.01:
                box(cv, x, x, y0 + i, y0 + i, deck - 5, deck - 1, 'hull_red')
    # breach (west; mirror makes the east one): open hull at ice level
    by0, by1 = P['breach_y']
    cv.carve(cxs - hw - 1, cxs - hw + 1, by0, by1, hold - 4, hold - 1)
    box(cv, cxs - hw - 1, cxs - hw + 1, by0, by1, hold, keel, 'plank')
    # two stairs hold -> deck (west one; mirrored), rising north->south along y at x = cx - 6..-5
    rise = hold - deck
    sx0, sx1 = cxs - 6, cxs - 5
    straight_stair(cv, y0 + 30, sx0, sx1, hold, rise, 1, GC['stair'], 'stair', along='y')
    cv.interiors.append(['cargo hold', cxs - 3, y0 + 22, hold])
    # cargo in the hold: crate stacks along the hull, presents spilling toward the breach
    for (yy, n) in ((y0 + 16, 3), (y0 + 46, 4), (y0 + 54, 3)):
        crate_stack_at(cv, cxs - hw + 2, yy, hold, n)
    # forecastle: raised deck z deck-4 over y0..fy1, a cabin under it with a door aft, stair up on the west side
    fy0, fy1 = P['forecastle_y']
    fz = deck - 5
    for i in range(0, fy1 - y0 + 1):
        y = y0 + i
        h = half(i)
        for x in range(cxs - hw, 256):
            if abs(x - cxs) <= h - 1:
                put(cv, x, y, fz, 'deck')
    cv.carve(cxs - 4, 255, fy0 + 5, fy1 - 1, fz + 1, deck - 1)
    box(cv, cxs - 4, 255, fy1, fy1, fz + 1, deck - 1, 'timber')
    cv.carve(cxs - 1, 255, fy1, fy1, deck - 4, deck - 1)                     # forecastle door (3 wide on axis)
    straight_stair(cv, fy1 + 5, cxs - hw + 1, cxs - hw + 2, deck, 5, -1, GC['stair'], 'stair', along='y')
    cv.interiors.append(['forecastle cabin', cxs - 2, fy0 + 8, deck])
    # deckhouse: two storeys aft
    dy0, dy1 = P['deckhouse_y']
    hx0 = cxs - hw + 2
    z1 = deck - 5
    z2 = deck - 10
    box(cv, hx0, 255, dy0, dy1, z2, deck - 1, 'wall_ochre')
    cv.carve(hx0 + 1, 255, dy0 + 1, dy1 - 1, z1 + 1, deck - 1)
    cv.carve(hx0 + 1, 255, dy0 + 1, dy1 - 1, z2 + 1, z1 - 1)
    box(cv, hx0 + 1, 255, dy0 + 1, dy1 - 1, z1, z1, 'floor')
    box(cv, hx0 - 1, 255, dy0 - 1, dy1 + 1, z2, z2, 'roof')
    cv.carve(cxs - 1, 255, dy0, dy0, deck - 4, deck - 1)                     # door facing the bow (axis)
    straight_stair(cv, dy0 + 3, hx0 + 1, hx0 + 2, deck, 5, 1, GC['stair'], 'stair', along='y')
    for (a, b) in ((dy0 + 3, dy0 + 4), (dy0 + 9, dy0 + 10), (dy1 - 4, dy1 - 3)):
        for zz in (deck, z1):
            cv.carve(hx0, hx0, a, b, zz - 3, zz - 2)
    cv.carve(hx0 + 2, 255, dy0, dy0, z1 - 3, z1 - 2)                         # wheelhouse front windows
    cv.interiors.append(['deckhouse mess', cxs - 2, dy1 - 4, deck])
    cv.interiors.append(['wheelhouse', cxs - 2, dy1 - 4, z1])
    # funnel (axis) and masts (axis, 3 wide after the mirror), cargo booms
    for z in range(z2 - 6, z2):
        box(cv, cxs - 2, 255, dy1 - 6, dy1 - 3, z, z, 'hull_red' if z > z2 - 3 else 'hull_dark')
    cv.carve(cxs - 1, 255, dy1 - 5, dy1 - 4, z2 - 6, z2 - 1)
    for my in (y0 + 18, y0 + 42):
        for z in range(P['mast_top'], deck):
            put(cv, 255, my, z, 'mast')
        box(cv, cxs - 7, 255, my, my, P['mast_top'] + 6, P['mast_top'] + 6, 'mast')       # yard
        for z in range(deck - 4, deck):
            put(cv, 250, my + 2, z, 'mast')                                               # boom post
    rep['ship_masts'] = [(255, y0 + 18), (255, y0 + 42)]
    rep['ship_box'] = [cxs - hw - 4, 2 * 256 - (cxs - hw - 4), y0, y1]
    rep.setdefault('lanterns', []).extend([(cxs - hw, y0 + 14, deck - 2), (cxs - hw, y0 + 40, deck - 2),
                                           (hx0 - 1, dy0 + 6, z2 - 1), (255, y0 + 1, fz - 1)])
    # gangway from the ice onto the deck (west side, near the deckhouse), rising north
    rise2 = keel - deck
    gy = dy0 - 2
    straight_stair(cv, gy - rise2 + 1, cxs - hw - 4, cxs - hw - 2, keel, rise2, 1, GC['stair'], 'stair', along='y')
    for i in range(1, rise2 + 1):
        for x in range(cxs - hw - 4, cxs - hw - 1):
            col_down(cv, x, gy - rise2 + i, keel - i + 1, 'stair')
    box(cv, cxs - hw - 4, cxs - hw - 1, gy + 1, gy + 1, deck, deck, 'plank')
    cv.carve(cxs - hw - 1, cxs - hw, gy, gy + 2, deck - 3, deck - 1)


def crate_stack_at(cv, x, y, floor, n):
    z = floor - 1
    for k in range(n):
        box(cv, x, x + 2, y + (k % 2) * 3, y + (k % 2) * 3 + 2, z - 2, z, 'crate')
        if k % 2:
            z -= 3


def presents(cv, rng, x, y, n=5, spread=4):
    """A small spill of wrapped presents (1-3 voxel boxes) on the ground around (x, y)."""
    out = 0
    for _ in range(n):
        px, py = int(x + rng.integers(-spread, spread + 1)), int(y + rng.integers(-spread, spread + 1))
        s = int(rng.integers(1, 3))
        g = top(cv, px, py)
        if g >= 62 or cv.keep[px, py]:
            continue
        ok = all(abs(top(cv, px + a, py + b) - g) <= 0 for a in range(s) for b in range(s))
        if not ok:
            continue
        box(cv, px, px + s - 1, py, py + s - 1, g - s, g - 1, 'present')
        out += 1
    return out


# =============================================================================================== caves

def carve_tube(cv, pts, half=2, floor=60, air=4):
    """Tunnel along a polyline: 2*half+1 wide, `air` voxels of air above floor `floor`, floor solidified."""
    for (a, b) in zip(pts, pts[1:]):
        for (x, y, _) in line_points(a[0], a[1], 0, b[0], b[1], 0):
            for dx in range(-half, half + 1):
                for dy in range(-half, half + 1):
                    cv.carve(x + dx, x + dx, y + dy, y + dy, floor - air, floor - 1)
                    if not cv.solid[x + dx, y + dy, floor]:
                        box(cv, x + dx, x + dx, y + dy, y + dy, floor, 63, 'rock')


def floor_profile(F):
    """Floors along a line may only change by 1 per column: raise the floor (larger z) next to deeper columns."""
    F = list(F)
    for _ in range(4):
        for i in range(len(F)):
            for j in (i - 1, i + 1):
                if 0 <= j < len(F) and F[j] - F[i] > 1:
                    F[i] = F[j] - 1
    return F


def caves(cv, rep, S):
    C = S['cave']
    cx, cy, rx, ry = C['chamber']
    for x in range(cx - rx, cx + rx + 1):
        for y in range(cy - ry, cy + ry + 1):
            r2 = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            if r2 <= 1:
                ztop = 54 + int(round(2 * r2))
                cv.carve(x, x, y, y, ztop, 59)
    # sea-cave mouth: tunnel south into the headland; the floor steps down 60 -> 63 (water) at the cliff face
    (ax_, ay_), (bx_, by_) = C['mouth']
    carve_tube(cv, [(ax_, ay_), (bx_, by_ - 10)], 2, 60, 4)
    ys = list(range(by_ - 10, by_ + 8))
    F = [63 if top(cv, bx_, y) >= 63 else 60 for y in ys]
    F = floor_profile(F)
    for y, fl in zip(ys, F):
        for dx in range(-2, 3):
            x = bx_ + dx
            cv.carve(x, x, y, y, fl - 4, fl - 1)
            if fl < 63:
                box(cv, x, x, y, y, fl, 63, 'rock')
            else:
                cv.carve(x, x, y, y, fl - 4, 62)
    rep['sea_cave_mouth'] = (bx_, ys[F.index(63)] if 63 in F else None)
    # smugglers' shed stair: connector north of the chamber, then a straight stair up into the shed
    sx0, sx1 = C['shed_stair_x']
    sy0, sy1 = C['shed_y']
    carve_tube(cv, [(cx - 2, cy - ry + 1), (cx - 2, sy0 + 1)], 2, 60, 4)
    carve_tube(cv, [(cx - 2, sy0 + 1), (sx0 - 1, sy0 + 1)], 2, 60, 4)
    rep['cave_shed_stair'] = (sx0, sy0, sy1)
    # islet chamber (west half; mirrored): floor 61, air 57-60 under the plateau (ground 53)
    ix, iy, irx, iry = C['islet_chamber']
    for x in range(ix - irx, 256):
        for y in range(iy - iry, iy + iry + 1):
            r2 = ((x - ix) / irx) ** 2 + ((y - iy) / iry) ** 2
            if r2 <= 1:
                cv.carve(x, x, y, y, 57, 60)
                box(cv, x, x, y, y, 61, 63, 'rock')
    # tunnel east under the shore spine, then the roofed wading passage into the islet chamber
    carve_tube(cv, [(cx + rx - 2, cy - 2)] + list(C['tunnel']), 2, 60, 4)
    (px0, py), (px1, _) = C['passage']
    passage(cv, rep, px0, px1, py)
    # stair from the islet chamber up to the south plateau, rising north (exit just north of the bonfire ring)
    fl, g = 61, S['islet']['plateau'][3]
    rise = fl - g
    ys0 = iy - iry + 1
    straight_stair(cv, ys0, 254, 255, fl, rise, -1, GC['stair'], 'stair', along='y')
    rep['islet_stair'] = (254, ys0, ys0 - rise, g)
    cv.interiors.append(['islet sea cave', ix - 8, iy, 61])
    cv.interiors.append(['smugglers cave', cx, cy, 60])


def passage(cv, rep, x0, x1, yc, half=1):
    """Roofed wading passage along x at y = yc: 3 wide, 4+ air over every floor (water node z 63, rock floors
    60-62 stepping by 1), rock walls and a roof where the terrain is too low to hold them, and a toothed crest
    (alternating 2-column slabs 4 apart in height) over the water so the roof is NOT a dry walkway."""
    xs = list(range(x0, x1 + 1))
    F = []
    for x in xs:
        g = top(cv, x, yc)
        F.append(63 if g >= 63 else (61 if cv.solid[x, yc, 57:61].sum() == 0 and g >= 61 else 60))
    F = floor_profile(F)
    teeth = 0
    for x, fl in zip(xs, F):
        water = top(cv, x, yc) >= 63
        for y in range(yc - half, yc + half + 1):
            cv.carve(x, x, y, y, fl - 4, fl - 1 if fl < 63 else 62)
            if fl < 63:
                box(cv, x, x, y, y, fl, 63, 'rock')
        roof_lo = fl - 5                                  # lowest roof voxel
        for y in range(yc - half - 2, yc + half + 3):
            inner = abs(y - yc) <= half
            if inner:
                for z in range(roof_lo - 2, roof_lo + 1):
                    if not cv.solid[x, y, z]:
                        put(cv, x, y, z, 'arch')
            else:
                for z in range(roof_lo - 2, 63):
                    if z >= 62 and not water:
                        break
                    if not cv.solid[x, y, z]:
                        put(cv, x, y, z, 'arch')
        if water and (x // 2) % 2 == 0:
            box(cv, x, x, yc - half - 2, yc + half + 2, roof_lo - 6, roof_lo - 3, 'arch')
            teeth += 1
    rep['passage'] = {'x': (x0, x1), 'y': yc, 'water_cols': int(sum(1 for f in F if f == 63)), 'teeth': teeth}


# =============================================================================================== bonfire ring

def bonfire(cv, rep, S):
    cx, cy, r = S['bonfire']
    g = top(cv, cx, cy)
    stones = []
    n = 10
    for k in range(n):
        a = (k + 0.5) * 2 * math.pi / n
        sx, sy = cx + r * math.cos(a), cy + r * math.sin(a)
        if sx > 256.5:
            continue
        hgt = 6 + (k * 7) % 4
        x, y = int(round(sx)), int(round(sy))
        gg = top(cv, x, y)
        box(cv, x - 1, min(x, 255), y - 1, y, gg - hgt, gg - 1, 'stone')
        for xx in range(x - 1, min(x, 255) + 1):
            for yy in (y - 1, y):
                col_down(cv, xx, yy, gg, 'stone')
        box(cv, x - 1, min(x, 255), y - 1, y, gg - hgt - 1, gg - hgt - 1, 'stone_dk')
        stones.append((x, y, hgt))
    # log ring + ember bed (painted, glow sources added by the art pass)
    for x in range(cx - 4, 256):
        for y in range(cy - 4, cy + 5):
            d = math.hypot(x - cx + 0.5, y - cy)
            if 3.0 <= d <= 4.2:
                put(cv, x, y, g - 1, 'log')
            elif d < 3.0:
                cv.rgb[x, y, g] = GC['ember']
                cv.mat[x, y, g] = cv.material('ember')
    rep['bonfire'] = {'stones': stones, 'g': g}


# =============================================================================================== west-half build

def build_west(S, seed):
    cv = Canvas(S['name'])
    for k in GC:
        cv.material(k)
    rep = {}
    T = terrain(cv, S, seed)
    rep['terrain'] = {k: int(v.sum()) for k, v in T.items() if k not in ('H0',)}
    caves(cv, rep, S)
    # cabins (+ the smugglers' shed with the cave stair)
    for (name, x0, x1, y0, y1, st, ridge, door, wall, stilt) in S['cabins']:
        fz, zt = cabin(cv, rep, name, x0, x1, y0, y1, st, ridge, door, wall, stilt)
        if name == 'smugglers shed':
            sx0, sy0, sy1 = rep['cave_shed_stair']
            rise = 60 - fz
            straight_stair(cv, sx0, sy0, sy1, 60, rise, 1, GC['stair'], 'stair')
            rep['shed_floor'] = fz
    bx0, bx1, by0, by1 = S['boathouse']
    boathouse(cv, rep, 'boathouse', bx0, bx1, by0, by1)
    # trawler dock: pier + boat in the ice
    td = S['trawler_dock']
    pier(cv, td['pier_x'][0], td['pier_x'][1], td['pier_y'][0], td['pier_y'][1], z=60)
    trawler(cv, rep, td['boat_x'][0], td['boat_x'][1], td['boat_y'][0], td['boat_y'][1])
    # post office (blue) / sauna (red): same shell; a pier south into the sea
    p = S['post_office']
    cabin(cv, rep, 'post office', p[0], p[1], p[2], p[3], 1, 'x', 'N', 'ochre')
    pp = S['post_pier']
    pier(cv, pp['x'][0], pp['x'][1], pp['y'][0], pp['y'][1], z=60)
    # stockfish racks, lobster pots
    for (x, y, ay) in S['racks']:
        drying_rack(cv, x, y, bool(ay))
    for (x, y) in S['pots']:
        crate_stack(cv, x, y, 4, 'pot', 3)
        crate_stack(cv, x, y + 3, 4, 'pot', 3)
    # front dressing (low, walk-around)
    for (kind, x, y) in S['front_props']:
        if kind == 'boat_trestle':
            boat_trestle(cv, x, y)
        elif kind == 'crates':
            crate_stack(cv, x, y, 4, 'crate', 3)
            crate_stack(cv, x, y + 3, 2, 'crate', 3)
        elif kind == 'woodpile':
            woodpile(cv, x, y, 8, 4, 3)
        elif kind == 'shed':
            fish_shed(cv, rep, x, y, f'fish shed {y}')
        elif kind == 'net_reel':
            net_reel(cv, x, y)
        elif kind == 'sled':
            kicksled(cv, x, y)
    for i, (x, y, r) in enumerate(S['spawn_cover']):
        boulder(cv, x, y, r, seed=i)
    # flank chains: north links, and the same links y-mirrored for the south chain
    for (kind, pts, w) in S['links']:
        for flip in (False, True):
            P_ = [(p[0], 511 - p[1]) if flip else p for p in pts]
            for A, B in zip(P_, P_[1:]):
                if kind == 'rope':
                    rope_bridge(cv, A, B, None, None, w)
                    continue
                along = 'y' if A[0] == B[0] else 'x'
                if along == 'y':
                    x0_ = A[0] - w // 2
                    lo = min(A[1], B[1])
                    pier(cv, x0_, x0_ + w - 1, A[1], B[1], z=60, broken=None if kind == 'pier' else (lo + 8, lo + 14))
                else:
                    y0_ = A[1] - w // 2
                    lo = min(A[0], B[0])
                    pier(cv, y0_, y0_ + w - 1, A[0], B[0], z=60, along='x',
                         broken=None if kind == 'pier' else (lo + 9, lo + 16))
    # centre (axis halves)
    cargo_ship(cv, rep, S)
    bonfire(cv, rep, S)
    rep['west_seed'] = seed
    return cv, rep
