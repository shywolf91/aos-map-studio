"""Cursed Skull Reef gameplay geometry (graybox): terrain, islets, every structure shell.

build_west(S, seed)  terrain for the whole map + every mirrored structure on the west half and the axis halves
                     (skull crag, half-sunk galleon, cannon fort, bridge ruin, hull ribs, axis piers are symmetric
                     about x = 256 and built as their west half + axis column); symmetry.mirror_canvas() then gives
                     the east side.

Every structure is real (owner rule 2026-10-20): open doorways, rooms, window openings, stairs to every upper floor;
each storey is recorded in cv.interiors for the interiors check. Colours here are graybox colours keyed by material;
csr_art recolours by material afterwards.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage as ndi

from aosmap.kit import noise
from aosmap.kit.canvas import Canvas, line_points
from aosmap.kit.structures import spiral_stair, straight_stair

# graybox colours by material (csr_art replaces them)
GC = {
    'sea': (30, 60, 90), 'sand': (170, 150, 110), 'rock': (92, 88, 90), 'turf': (78, 96, 58), 'reef': (130, 100, 100),
    'spawn': (150, 132, 100), 'front': (160, 140, 104), 'anchor': (110, 104, 96), 'neck': (176, 156, 116),
    'footing': (110, 104, 98), 'floor': (120, 96, 70), 'wall': (150, 128, 96), 'wall_dk': (110, 96, 80),
    'plaster': (176, 160, 128), 'roof': (96, 64, 50), 'trim': (90, 70, 56), 'timber': (100, 80, 62),
    'plank': (126, 100, 74), 'post': (84, 68, 56), 'stair': (140, 112, 84), 'furniture': (96, 74, 56),
    'hull': (70, 54, 44), 'hull_trim': (120, 96, 50), 'deck': (132, 106, 78), 'mast': (104, 84, 64),
    'sail': (170, 160, 136), 'rope': (150, 130, 92), 'crate': (146, 116, 76), 'barrel': (120, 86, 56),
    'iron': (64, 64, 70), 'stone': (128, 124, 118), 'stone_dk': (96, 94, 92), 'bone': (196, 188, 160),
    'gold': (210, 170, 60), 'chest': (110, 70, 40), 'coral': (180, 110, 110), 'boulder': (100, 96, 98),
    'leaf': (70, 100, 50), 'bark': (90, 70, 52), 'lamp': (255, 175, 95), 'glass': (120, 150, 150),
    'flag': (40, 40, 44), 'net': (130, 120, 90), 'pot': (120, 96, 70), 'tag': (222, 206, 160), 'sky': (200, 200, 210),
    'brick': (150, 96, 76), 'skull_rock': (176, 168, 146), 'cloth': (140, 60, 50), 'cage': (60, 60, 64),
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


def _ell(X, Y, cx, cy, rx, ry):
    return 1 - ((X - cx) / rx) ** 2 - ((Y - cy) / ry) ** 2


# =============================================================================================== terrain

def terrain(cv, S, seed):
    X, Y = np.meshgrid(np.arange(512, dtype=float), np.arange(512, dtype=float), indexing='ij')
    N1 = noise.fbm2((512, 512), 40, 3, 'coast', seed) - 0.5
    N2 = noise.fbm2((512, 512), 14, 2, 'skerry', seed) - 0.5
    R = noise.fbm2((512, 512), S['island']['relief_cell'], 3, 'relief', seed)
    I = S['island']
    # ---------------------------------------------------------------- spawn isle (west)
    f = np.full((512, 512), -9.0)
    for (cx, cy, rx, ry) in I['ellipses']:
        f = np.maximum(f, _ell(X, Y, cx, cy, rx, ry))
    f += I['edge_noise'] * 2 * N1
    land = f > 0
    xmax = np.full(512, I['x_max'])
    for (a, b) in I['shoulder_y']:
        xmax[a:b + 1] = I['x_max_shoulder']
    ax, ay = S['anchor']['x'], S['anchor']['y']
    xmax[ay[0]:ay[1] + 1] = ax[1]
    land &= X <= xmax[None, :]
    land[ax[0]:ax[1] + 1, ay[0]:ay[1] + 1] = True
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
    # rear ridge behind the spawn square (backdrop / spawn cover): smooth hump up to h above the plateau
    rr = I['rear_ridge']
    rcx, rcy = (rr['x'][0] + rr['x'][1]) / 2, (rr['y'][0] + rr['y'][1]) / 2
    rho = np.hypot((X - rcx) / ((rr['x'][1] - rr['x'][0]) / 2), (Y - rcy) / ((rr['y'][1] - rr['y'][0]) / 2))
    ridge = rr['h'] * smooth(1.25 * (1 - rho)) * (0.75 + 0.5 * R)
    H_I = H_I - np.where(land, ridge * smooth((d - 10) / 8), 0)
    # gameplay zones: spawn square (gentle mounds), front crest, flat anchor - blended into the terrain
    Z = np.zeros((512, 512), bool)
    T = np.zeros((512, 512))
    b = S['spawn']['base']
    h = S['spawn']['half'] + S['spawn']['margin']
    sq = (np.abs(X - b[0]) <= h) & (np.abs(Y - b[1]) <= h)
    mounds = np.round(1.2 * (noise.fbm2((512, 512), 10, 2, 'mounds', seed) - 0.5) * 2).clip(-1, 0)
    Z |= sq
    T = np.where(sq, S['z']['spawn'] + mounds, T)
    fy = S['front']['y']
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
    # ---------------------------------------------------------------- neck (shoal) + shoulders, stern reef
    NK = S['neck']
    neck = (X >= NK['x'][0]) & (X <= 255) & (Y >= NK['y'][0]) & (Y <= NK['y'][1])
    for (xs_, ys_) in NK['shoulders']:
        neck |= (X >= xs_[0]) & (X <= xs_[1]) & (Y >= ys_[0]) & (Y <= ys_[1])
    dune = (noise.fbm2((512, 512), 9, 2, 'dune', seed) > 0.62) & (np.abs(Y - 256) <= 14)
    H_N = np.where(neck, NK['z'] - dune.astype(int), 63)
    # neck edges: a z 62 lip where it meets the lagoon
    ne = neck & ~ndi.binary_erosion(neck, iterations=1)
    H_N = np.where(ne & (H_N < 62), 62, H_N)
    SR = S['stern_reef']
    reef = (X >= SR['x'][0]) & (X <= SR['x'][1]) & (Y >= SR['y'][0]) & (Y <= SR['y'][1])
    H_R = np.where(reef, S['z']['reef'], 63)
    # ---------------------------------------------------------------- fort islet, skull islet (axis)
    H_C = np.full((512, 512), 63.0)
    centre_land = np.zeros((512, 512), bool)
    for key in ('fort_islet', 'skull_islet'):
        C = S[key]
        fc = _ell(X, Y, C['c'][0], C['c'][1], C['rx'], C['ry']) + C['edge_noise'] * 2 * N1
        m = fc > 0
        dc = ndi.distance_transform_edt(m)
        hh = np.where(dc < 4, 62 - np.floor((dc - 1) / 2), 61 - (61 - C['z']) * smooth((dc - 4) / 9))
        H_C = np.where(m, np.minimum(H_C, np.round(hh)), H_C)
        centre_land |= m
    # ---------------------------------------------------------------- skerries (north + y-mirror south)
    H_S = np.full((512, 512), 63.0)
    sk = np.zeros((512, 512), bool)
    for name, (cx, cy, r, pz) in S['skerries'].items():
        for yy in (cy, 511 - cy):
            rho = np.hypot(X - cx, Y - yy) / r
            fs = 1 - rho ** 2 + 0.45 * N2
            m = fs > 0
            hh = 62 - (62 - pz) * np.clip(fs, 0, 1) ** 0.7
            H_S = np.where(m, np.minimum(H_S, np.round(hh)), H_S)
            sk |= m
    # ---------------------------------------------------------------- corner sandbar for the tag (SW)
    tagbar = (X >= 4) & (X <= 116) & (Y >= 486) & (Y <= 508)
    H_T = np.where(tagbar, 62, 63)
    H = np.minimum.reduce([H_I, H_N, H_R, H_C, H_S, H_T])
    H = np.clip(H, 0, 63).astype(int)
    H[256:] = 63          # east half comes from the mirror
    # materials
    mat = np.full((512, 512), 'sea', object)
    mat[H < 63] = 'sand'
    rockish = (H < 58)
    mat[rockish] = 'rock'
    turfm = rockish & (noise.fbm2((512, 512), 12, 2, 'turf', seed) > 0.46) & (land | centre_land)
    mat[turfm] = 'turf'
    mat[(neck | reef) & (H < 63)] = 'neck'
    mat[reef & (H < 63)] = 'reef'
    mat[Z & land & sq] = 'spawn'
    mat[Z & land & fr] = 'front'
    mat[Z & land & an] = 'anchor'
    cv.H = H.astype(np.int16)
    zz = np.arange(64)[None, None, :]
    for m in ('sea', 'sand', 'rock', 'turf', 'neck', 'reef', 'spawn', 'front', 'anchor'):
        mm = (mat == m)[:, :, None] & (zz >= H[:, :, None])
        cv.fill_mask(mm, GC[m], m)
    cv.no_prop(b[0] - h, b[0] + h, b[1] - h, b[1] + h, 1)
    cv.no_prop(ax[0] - 2, ax[1] + 2, ay[0] - 2, ay[1] + 2, 2)
    return {'land_isle': land, 'centre_land': centre_land, 'neck': neck, 'skerry': sk, 'zones': Z}


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


def gable_roof(cv, x0, x1, y0, y1, zt, ridge='x', mat='roof', over=1, hole=None):
    """Stepped gable roof above wall-top z zt; layers 2 deep so steps share faces; gable ends walled.
    hole=(a0, a1) leaves those ridge-axis positions open on the upper layers (a ruined roof)."""
    if ridge == 'x':
        a0, a1, b0, b1 = y0, y1, x0, x1
    else:
        a0, a1, b0, b1 = x0, x1, y0, y1

    def P(a, b, z, m):
        if hole and hole[0] <= b <= hole[1] and z < zt - 1:
            return
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
        if k >= over:
            for a in range(lo + 2, hi - 1):
                for b in (b0, b1):
                    P(a, b, z, 'timber')
        k += 1
    return zt - 1 - k


def windows_on(cv, x0, x1, y0, y1, fz, lights, every=4, sill=2, hgt=2):
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
        lights.append(((wx, wy), fz - sill, ax))
    return len(out)


def _ground_out(cv, door, dsp, zmin=0):
    """Ground top just outside a door, ignoring anything above zmin (roof eaves over the door)."""
    x0, x1, y0, y1 = dsp
    if door == 'S':
        p = ((x0 + x1) // 2, y1 + 1)
    elif door == 'N':
        p = ((x0 + x1) // 2, y0 - 1)
    elif door == 'E':
        p = (x1 + 1, (y0 + y1) // 2)
    else:
        p = (x0 - 1, (y0 + y1) // 2)
    return cv.column_top(p[0], p[1], zmin)


def outside_stair(cv, door, dsp, fz, rise, mat='stair'):
    """Straight stair from the ground outside a door up to floor fz (steps run away from the wall), supported."""
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


# =============================================================================================== houses

def house(cv, rep, name, x0, x1, y0, y1, storeys=1, ridge='x', door='S', ruin=None, stilt_floor=None, sh=5,
          wall='wall'):
    """Pirate-town house: stone footing (or stilts), timber-framed plaster walls, a real 3-wide door, windows,
    inner stair to every upper floor, stepped gable roof. ruin='roof' opens part of the roof; ruin='corner' breaks
    the top of one wall corner (the rooms stay real). Records every storey."""
    if stilt_floor is None:
        g = pad(cv, x0 - 1, x1 + 1, y0 - 1, y1 + 1)
        fz = g - 1
        box(cv, x0, x1, y0, y1, fz, fz, 'footing')
    else:
        fz = stilt_floor
        cv.carve(x0, x1, y0, y1, 0, fz - 1)
        box(cv, x0, x1, y0, y1, fz, fz, 'floor')
        for x in sorted({x0, (x0 + x1) // 2, x1}):
            for y in sorted({y0, (y0 + y1) // 2, y1}):
                col_down(cv, x, y, fz + 1, 'post')
    zt = fz - sh * storeys
    box(cv, x0, x1, y0, y1, zt, fz - 1, wall)
    cv.carve(x0 + 1, x1 - 1, y0 + 1, y1 - 1, zt, fz - 1)
    for k in range(1, storeys):
        box(cv, x0 + 1, x1 - 1, y0 + 1, y1 - 1, fz - sh * k, fz - sh * k, 'floor')
    for (cx_, cy_) in ((x0, y0), (x0, y1), (x1, y0), (x1, y1)):          # dark timber corner posts
        box(cv, cx_, cx_, cy_, cy_, zt, fz - 1, 'trim')
    for k in range(storeys):                                               # timber band under each floor
        zb = fz - sh * k - 1
        for x in range(x0, x1 + 1):
            for y in (y0, y1):
                if cv.solid[x, y, zb]:
                    cv.mat[x, y, zb] = cv.material('trim')
        for y in range(y0, y1 + 1):
            for x in (x0, x1):
                if cv.solid[x, y, zb]:
                    cv.mat[x, y, zb] = cv.material('trim')
    lights = rep.setdefault('window_lights', [])
    for k in range(storeys):
        windows_on(cv, x0, x1, y0, y1, fz - sh * k, lights)
    hole = None
    if ruin == 'roof':
        L = (x1 - x0) if ridge == 'x' else (y1 - y0)
        base = x0 if ridge == 'x' else y0
        hole = (base + L // 3, base + L // 3 + 3)
    ridge_z = gable_roof(cv, x0, x1, y0, y1, zt, ridge, hole=hole)
    rep.setdefault('eaves', []).append((x0, x1, y0, y1, zt, ridge))
    for k in range(storeys - 1):
        f = fz - sh * k
        if (x1 - x0) >= (y1 - y0):
            straight_stair(cv, x0 + 2, y0 + 1 if k % 2 == 0 else y1 - 2, y0 + 2 if k % 2 == 0 else y1 - 1, f, sh,
                           1, GC['stair'], 'stair')
        else:
            straight_stair(cv, y0 + 2, x0 + 1, x0 + 2, f, sh, 1, GC['stair'], 'stair', along='y')
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    dsp = {'S': (cx - 1, cx + 1, y1, y1), 'N': (cx - 1, cx + 1, y0, y0), 'E': (x1, x1, cy - 1, cy + 1),
           'W': (x0, x0, cy - 1, cy + 1)}[door]
    cv.carve(dsp[0], dsp[1], dsp[2], dsp[3], fz - 4, fz - 1)
    rep.setdefault('doors', []).append((name, door, dsp, fz))
    rise = max(0, _ground_out(cv, door, dsp, fz) - fz)
    if rise > 0:
        outside_stair(cv, door, dsp, fz, rise)
    if ruin == 'corner':                                                  # broken corner: jagged top, NE/SE corner
        cxr = x1
        cyr = y0 if door != 'N' else y1
        sgn = 1 if cyr == y0 else -1
        for i in range(4):
            for j in range(4 - i):
                for z in range(zt - 6, zt + 1 + (3 - i - j)):
                    cv.clear(cxr - i, cyr + sgn * j, z)
    # furniture: table + benches + a bunk; kept off the stair and door lines
    f = fz
    tx, ty = x1 - 3, (y1 - 3 if door != 'S' else y0 + 3)
    box(cv, tx, tx + 1, ty, ty, f - 1, f - 1, 'furniture')
    if storeys > 1:
        box(cv, x1 - 2, x1 - 1, y0 + 1 if door != 'N' else y1 - 1, y0 + 1 if door != 'N' else y1 - 1, f - sh - 1,
            f - sh - 1, 'furniture')
    for k in range(storeys):
        cv.interiors.append([f'{name} floor {k}', (x0 + x1) // 2 + 1, (y0 + y1) // 2, fz - sh * k])
    rep.setdefault('buildings', []).append({'name': name, 'box': [x0, x1, y0, y1, ridge_z, fz], 'storeys': storeys})
    return fz, zt


def hut(cv, rep, x, y, name):
    """One-room fisher's hut on the front (owner: one-storey one-room houses are fine): 8 x 7, open doors at both
    ends (walk-through along x), windows, a low roof with no overhang; 9 tall."""
    x0, x1, y0, y1 = x, x + 7, y, y + 6
    g = pad(cv, x0 - 1, x1 + 1, y0 - 1, y1 + 1)
    fz = g
    zt = fz - 5
    box(cv, x0, x1, y0, y1, zt, fz - 1, 'wall')
    cv.carve(x0 + 1, x1 - 1, y0 + 1, y1 - 1, zt, fz - 1)
    for (cx_, cy_) in ((x0, y0), (x0, y1), (x1, y0), (x1, y1)):
        box(cv, cx_, cx_, cy_, cy_, zt, fz - 1, 'trim')
    cy = (y0 + y1) // 2
    cv.carve(x0, x0, cy - 1, cy + 1, fz - 4, fz - 1)
    cv.carve(x1, x1, cy - 1, cy + 1, fz - 4, fz - 1)
    lights = rep.setdefault('window_lights', [])
    windows_on(cv, x0, x1, y0, y1, fz, lights, every=5)
    gable_roof(cv, x0, x1, y0, y1, zt, 'x', over=0)
    rep.setdefault('eaves', []).append((x0, x1, y0, y1, zt, 'x'))
    box(cv, x0 + 2, x0 + 3, y1 - 1, y1 - 1, fz - 1, fz - 1, 'crate')
    cv.interiors.append([name, x0 + 4, cy, fz])
    rep.setdefault('buildings', []).append({'name': name, 'box': [x0, x1, y0, y1, zt - 4, fz], 'storeys': 1})


# =============================================================================================== piers, bridges

def pier(cv, x0, x1, ya, yb, z=60, posts=4, ladders=8, mat='plank', along='y', broken=None, lamps=None):
    """Plank jetty (deck z) along y (or x); posts to the seabed; step blocks every `ladders` so a swimmer can climb
    back out (water floor 62 -> 61 -> 60). broken=(a, b): that stretch sags 1 lower and loses its edge planks.
    lamps: list collecting (x, y, z) lamp-post tops every 10 planks."""
    lo, hi = sorted((ya, yb))
    for t in range(lo, hi + 1):
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
                    box(cv, X, X, Y, Y, z + 1, 63, 'stair')
                    box(cv, X2, X2, Y2, Y2, z + 2, 63, 'stair')
        if lamps is not None and (t - lo) % 10 == 6 and not (broken and broken[0] <= t <= broken[1]):
            X, Y = (x0 - 1, t) if along == 'y' else (t, x0 - 1)
            if top(cv, X, Y) >= 62:
                for zz in range(z - 4, 64):
                    if cv.solid[X, Y, zz]:
                        break
                    put(cv, X, Y, zz, 'post')
                lamps.append((X, Y, z - 5))


def rope_bridge(cv, p0, p1, w=3, sag=2, broken=None):
    """Plank deck from p0 to p1 (any heading), heights from the land at both ends with a gentle sag (<= 1 per step),
    rope rails on posts every 4 planks. broken=(t0, t1) fraction range: rails gone and every other edge plank
    missing there (the centre line stays walkable)."""
    x0, y0 = p0
    x1, y1 = p1
    z0, z1 = top(cv, x0, y0), top(cv, x1, y1)
    L = int(max(abs(x1 - x0), abs(y1 - y0)))
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    nx, ny = -uy, ux
    pts = []
    Z = []
    for i in range(L + 1):
        t = i / L
        zz = round(z0 + (z1 - z0) * t + sag * math.sin(math.pi * t))
        cx, cy = x0 + ux * i, y0 + uy * i
        wet = any(top(cv, int(round(cx + nx * k)), int(round(cy + ny * k))) >= 62 for k in range(-(w // 2) - 1,
                                                                                               w // 2 + 2))
        Z.append(min(zz, 58) if wet else zz)
    for _ in range(3):                                   # steps of at most 1 between planks, both directions
        for i in range(1, len(Z)):
            Z[i] = min(Z[i], Z[i - 1] + 1)
        for i in range(len(Z) - 2, -1, -1):
            Z[i] = min(Z[i], Z[i + 1] + 1)
    zmap = Z
    for i in range(L + 1):
        t = i / L
        zz = zmap[i]
        cx, cy = x0 + ux * i, y0 + uy * i
        brk = broken and broken[0] <= t <= broken[1]
        for k in range(-(w // 2), w // 2 + 1):
            if brk and k != 0 and (i + k) % 2:
                continue
            X, Y = int(round(cx + nx * k)), int(round(cy + ny * k))
            cv.carve(X, X, Y, Y, zz - 3, zz - 1)
            put(cv, X, Y, zz, 'plank')
            pts.append((X, Y, zz))
        if i % 4 == 0 and not brk:
            for k in (-(w // 2) - 1, w // 2 + 1):
                X, Y = int(round(cx + nx * k)), int(round(cy + ny * k))
                for z in range(zz - 2, zz + 1):
                    put(cv, X, Y, z, 'post')
    have = {(p[0], p[1]): p[2] for p in pts}
    for (X, Y, zz) in pts:
        for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            if (X + dx, Y + dy) in have and (X + dx, Y) not in have and (X, Y + dy) not in have:
                put(cv, X + dx, Y, zz, 'plank')
                have[(X + dx, Y)] = zz
    for k in (-(w // 2) - 1, w // 2 + 1):
        prevp = None
        for i in range(0, L + 1, 4):
            t = i / L
            if broken and broken[0] <= t <= broken[1]:
                prevp = None
                continue
            zz = zmap[i] - 2
            cx, cy = x0 + ux * i, y0 + uy * i
            q = (int(round(cx + nx * k)), int(round(cy + ny * k)), zz)
            if prevp is not None:
                for (a, b, c) in line_points(*prevp, *q):
                    put(cv, a, b, c, 'rope')
            prevp = q
    return {'from': p0, 'to': p1, 'z': (int(z0), int(z1)), 'len': L}


# =============================================================================================== ships

class Hull:
    """A wooden hull in a local frame: u along the length (0 = bow), v across (- = port side), z world.
    frame: 'y' -> x = xc + v, y = y0 + u (bow north if bow_at_start); 'x' -> x = x0 + u, y = yc + v.
    axis_half: only v < 0 is built (x <= 255; the mirror completes it and copies 255 into 256)."""

    def __init__(self, cv, frame, origin, L, hb, deck_of_u, depth, axis_half=False, bow_taper=0.32,
                 reverse=False):
        self.cv, self.frame, self.origin, self.L, self.hb = cv, frame, origin, L, hb
        self.deck_of_u, self.depth, self.axis_half, self.bt, self.rev = deck_of_u, depth, axis_half, bow_taper, reverse

    def xy(self, u, v):
        a, b = self.origin
        uu = (self.L - 1 - u) if self.rev else u
        return (a + v, b + uu) if self.frame == 'y' else (a + uu, b + v)

    def half(self, u):
        L, hb = self.L, self.hb
        nb = max(2.0, self.bt * L)
        if u < nb:
            return hb * (0.25 + 0.75 * math.sqrt(u / nb))
        if u > L - 3:
            return hb * 0.9
        return hb

    def av(self, v):
        return abs(v + 0.5) - 0.5 if self.axis_half else abs(v)

    def vs(self):
        return range(-self.hb - 1, 0 if self.axis_half else self.hb + 2)

    def deck(self, u):
        return int(self.deck_of_u(u))

    def keel(self, u):
        return min(62, self.deck(u) + self.depth)

    def build(self, shell='hull', deck='deck', trim_z=None):
        cv = self.cv
        for u in range(self.L):
            h = self.half(u)
            d, k = self.deck(u), self.keel(u)
            for v in self.vs():
                a = self.av(v)
                if a > h + 0.01:
                    continue
                x, y = self.xy(u, v)
                for z in range(d, k + 1):
                    tuck = z - (k - 3)
                    if tuck > 0 and a > h - tuck - 0.01 and a > 1:
                        continue
                    edge = a > h - 1 or u == 0 or u == self.L - 1 or z == k
                    if edge:
                        put(cv, x, y, z, shell)
                    else:
                        cv.clear(x, y, z)
                put(cv, x, y, d, deck)
                if a > h - 1:
                    put(cv, x, y, d - 1, shell)
                    if trim_z is not None and d + trim_z < k:
                        put(cv, x, y, d + trim_z, 'hull_trim')

    def inner(self, u, v, margin=1):
        return self.av(v) <= self.half(u) - margin

    def floor(self, off, u0=1, u1=None, mat='plank'):
        """Inner floor at deck(u) + off for u0..u1 (skipped where it would reach the keel)."""
        u1 = self.L - 2 if u1 is None else u1
        for u in range(u0, u1 + 1):
            z = self.deck(u) + off
            if z >= self.keel(u):
                continue
            for v in self.vs():
                if self.inner(u, v):
                    x, y = self.xy(u, v)
                    put(self.cv, x, y, z, mat)

    def carve_band(self, u0, u1, z0_off, z1_off, margin=1):
        for u in range(u0, u1 + 1):
            for v in self.vs():
                if self.inner(u, v, margin):
                    x, y = self.xy(u, v)
                    self.cv.carve(x, x, y, y, self.deck(u) + z0_off, min(self.keel(u) - 1, self.deck(u) + z1_off))


def galleon(cv, rep, S):
    """Half-sunk galleon on the axis, bow north sunk at the fort islet, stern raised on the stern reef. Sloped main
    deck (walkable 1 in ~4.5), gun deck with cannons, hold, quarterdeck over the captain's cabin, broken masts.
    Entry from the stern reef through a breach in the transom; from the fort islet onto the awash bow."""
    G = S['galleon']
    y0, y1 = G['y']
    L = y1 - y0 + 1
    ds, db = G['deck_stern'], G['deck_bow']

    def deck_of(u):
        return int(round(db + (ds - db) * u / (L - 1)))
    hl = Hull(cv, 'y', (G['x_c'], y0), L, G['beam_half'], deck_of, G['depth'], axis_half=True)
    hl.build(trim_z=3)
    # gun deck (deck + 5) and hold floor (deck + 10) where the hull is deep enough
    hl.floor(5, 1, L - 2)
    hl.floor(10, 1, L - 2)
    # quarterdeck: raised 5 over the stern (u from quarter_y) with the captain's cabin under it
    q0 = G['quarter_y'][0] - y0
    for u in range(q0, L):
        d = hl.deck(u)
        h = hl.half(u)
        for v in hl.vs():
            a = hl.av(v)
            if a > h + 0.01:
                continue
            x, y = hl.xy(u, v)
            if a > h - 1 or u == L - 1:
                box(cv, x, x, y, y, d - 6, d - 1, 'hull')
            put(cv, x, y, d - 5, 'deck')
            if a > h - 1:
                put(cv, x, y, d - 6, 'hull')
    # cabin wall (bow side) with a door on the axis, windows aft
    dq = hl.deck(q0)
    for v in hl.vs():
        if hl.inner(q0, v, 0):
            x, y = hl.xy(q0, v)
            box(cv, x, x, y, y, dq - 4, dq - 1, 'timber')
    cv.carve(254, 255, y0 + q0, y0 + q0, dq - 4, dq - 1)
    for v in (-9, -8):
        x, y = hl.xy(L - 1, v)
        cv.carve(x, x, y, y, hl.deck(L - 1) - 3, hl.deck(L - 1) - 2)
    cv.interiors.append(['galleon captain cabin', 252, y0 + q0 + 6, hl.deck(q0 + 6)])
    # stair main deck -> quarterdeck (west side, rising south along y) just ahead of the cabin wall
    for rise in range(5, 12):
        st_u = q0 - rise
        if hl.deck(st_u) - rise == hl.deck(q0) - 5:
            break
    straight_stair(cv, y0 + st_u, 247, 248, hl.deck(st_u), rise, 1, GC['stair'], 'stair', along='y')
    # stairs hold -> gun deck -> main deck across the beam (rising toward the axis) where the deck is level
    rep['galleon_stairs'] = []
    for (u, off) in ((L - 16, 10), (L - 28, 5)):
        while hl.deck(u) != hl.deck(u + 1):
            u -= 1
        fz = hl.deck(u) + off
        straight_stair(cv, 248, y0 + u, y0 + u + 1, fz, 5, 1, GC['stair'], 'stair')
        rep['galleon_stairs'].append((u, fz))
        cv.interiors.append([f'galleon deck +{off}', 251, y0 + u + 4, hl.deck(u + 4) + off])
    # stern breach into the hold from the stern reef: transom opening + steps
    zh = hl.deck(L - 1) + 10                                         # hold floor at the stern
    cv.carve(253, 255, y1 - 1, y1, zh - 4, zh - 1)
    for i, z in enumerate(range(zh + 1, 62)):
        box(cv, 253, 255, y1 + 1 + i, y1 + 1 + i, z, 62, 'reef')
    # gun deck cannons (ports on the west side) every 6 along the level stretches
    rep['galleon_lanterns'] = []
    for u in range(14, L - 4, 7):
        z = hl.deck(u) + 5
        if z >= hl.keel(u) - 1:
            continue
        h = hl.half(u)
        xo, y = hl.xy(u, -int(h))
        cv.carve(xo, xo, y, y, z - 2, z - 2)                         # gun port
        box(cv, xo + 1, xo + 3, y, y, z - 2, z - 2, 'iron')          # barrel
        box(cv, xo + 2, xo + 3, y - 1, y + 1, z - 1, z - 1, 'timber')  # carriage
    # broken masts and the stump of the bowsprit
    for my, ztop in ((G['masts_y'][0], G['mast_top'] + 10), (G['masts_y'][1], G['mast_top'])):
        u = my - y0
        for z in range(ztop, hl.deck(u)):
            box(cv, 255, 255, my, my + 1, z, z, 'mast')
        box(cv, 248, 255, my, my, ztop + 6, ztop + 6, 'mast')          # yard
        rep['galleon_lanterns'].append((249, my, ztop + 7))
    rep['galleon_lanterns'] += [(248, y1 - 1, hl.deck(L - 1) - 6), (248, y0 + q0 + 1, hl.deck(q0) - 6)]
    # reef rock under the raised stern (ground is solid all the way down)
    for u in range(L):
        for v in hl.vs():
            if hl.av(v) <= hl.half(u):
                x, y = hl.xy(u, v)
                k = hl.keel(u)
                if k < 62 and cv.solid[x, y, k]:
                    col_down(cv, x, y, k + 1, 'reef')
    rep['galleon'] = {'deck_bow': hl.deck(0), 'deck_stern': hl.deck(L - 1), 'hold_stern': zh}
    rep.setdefault('buildings', []).append({'name': 'galleon', 'box': [246, 266, y0, y1, G['mast_top'], 62]})
    return hl


def assist_wreck(cv, rep, S):
    """Assist structure (west; mirrored): the broken-off stern of a galleon beached on the neck shoulder. Hold,
    gun deck, main deck, quarterdeck over a captain's cabin, broken bow end open to the lagoon, breaches into the hold
    from the sand. The mizzen mast carries a spiral rope-and-plank stair from the quarterdeck to a crow's-nest ring
    at nest_z, just north of the platform's west end (short build to the platform)."""
    A = S['assist']
    y0, y1 = A['y']
    L = y1 - y0 + 1
    xc, hb = A['x_c'], A['beam_half']
    keel = A['keel']
    hold, gun, main = A['decks']
    hl = Hull(cv, 'y', (xc, y0), L, hb, lambda u: main, keel - main, bow_taper=0.0)
    hl.build(trim_z=4)
    hl.floor(gun - main, 1, L - 2)
    hl.floor(hold - main, 1, L - 2)
    # broken bow: ragged open end, decks end jaggedly
    rng = np.random.default_rng(S['layout_seed'] + 7)
    for v in range(-hb - 1, hb + 2):
        r = int(rng.integers(2, 6))
        for u in range(0, r):
            x, y = hl.xy(u, v)
            for z in range(main - 1, keel - 1):
                if z in (main, gun, hold) and u >= r - 2 and abs(v) < hb:
                    continue
                cv.clear(x, y, z)
    # quarterdeck at quarter_z over the stern with the cabin under it
    q0 = A['quarter_y'][0] - y0
    qz = A['quarter_z']
    for u in range(q0, L):
        for v in hl.vs():
            a = hl.av(v)
            if a > hl.half(u) + 0.01:
                continue
            x, y = hl.xy(u, v)
            if a > hl.half(u) - 1 or u == L - 1:
                box(cv, x, x, y, y, qz - 1, main - 1, 'hull')
            put(cv, x, y, qz, 'deck')
    for v in hl.vs():
        if hl.inner(q0, v, 0):
            x, y = hl.xy(q0, v)
            box(cv, x, x, y, y, qz + 1, main - 1, 'timber')
    cv.carve(xc - 1, xc + 1, y0 + q0, y0 + q0, main - 4, main - 1)          # cabin door facing the bow
    for yy in (y0 + q0 + 4, y0 + q0 + 9):                                     # side windows
        cv.carve(xc - hb, xc - hb, yy, yy + 1, main - 3, main - 2)
        cv.carve(xc + hb, xc + hb, yy, yy + 1, main - 3, main - 2)
    cv.carve(xc - 3, xc - 2, y1, y1, main - 3, main - 2)                      # stern windows
    cv.carve(xc + 2, xc + 3, y1, y1, main - 3, main - 2)
    cv.interiors.append(['assist wreck cabin', xc + 2, y0 + q0 + 4, main])
    # stairs: hold -> gun -> main across the beam; main -> quarterdeck along y (west side)
    straight_stair(cv, xc - 4, y0 + 9, y0 + 10, hold, hold - gun, 1, GC['stair'], 'stair')
    straight_stair(cv, xc - 4, y0 + 14, y0 + 15, gun, gun - main, 1, GC['stair'], 'stair')
    straight_stair(cv, y0 + q0 - 5, xc - hb + 1, xc - hb + 2, main, main - qz, 1, GC['stair'], 'stair', along='y')
    cv.interiors.append(['assist wreck hold', xc + 2, y0 + 12, hold])
    cv.interiors.append(['assist wreck gun deck', xc + 2, y0 + 17, gun])
    # breaches into the hold: stern transom (from the neck shoulder sand) and the west side (from the isle shore)
    cv.carve(xc - 1, xc + 1, y1, y1, hold - 4, hold - 1)
    g = top(cv, xc, y1 + 1)
    for i, z in enumerate(range(hold + 1, g)):
        box(cv, xc - 1, xc + 1, y1 + 1 + i, y1 + 1 + i, z, 62, 'stair')
    cv.carve(xc - hb, xc - hb, y0 + 11, y0 + 13, hold - 4, hold - 1)
    for x in range(xc - hb - 14, xc - hb):
        for y in range(y0 + 10, y0 + 15):
            if top(cv, x, y) >= 61:
                box(cv, x, x, y, y, hold if x >= xc - hb - 2 else 61, 63, 'reef')
    # collapsed patch of the main deck (a drop into the gun deck)
    cv.carve(xc + 2, xc + 4, y0 + 7, y0 + 9, main, main)
    # gun deck cannons on the east side
    for yy in (y0 + 8, y0 + 20):
        cv.carve(xc + hb, xc + hb, yy, yy, gun - 2, gun - 2)
        box(cv, xc + hb - 3, xc + hb - 1, yy, yy, gun - 2, gun - 2, 'iron')
        box(cv, xc + hb - 3, xc + hb - 2, yy - 1, yy + 1, gun - 1, gun - 1, 'timber')
    # mizzen mast with the spiral stair to the crow's-nest ring
    mx, my = A['mast']
    nz = A['nest_z']
    r = A['stair_r']
    spiral_stair(cv, mx, my, nz, qz, r=r, c=GC['plank'], core=GC['mast'], mat='stair')
    for z in range(nz - 5, nz):                                              # broken mast head above the nest
        box(cv, mx - 1, mx, my - 1, my, z, z, 'mast')
    rn = A['nest_r']
    for x in range(int(mx - rn - 1), int(mx + rn + 2)):
        for y in range(int(my - rn - 1), int(my + rn + 2)):
            dd = math.hypot(x - mx, y - my)
            if r + 0.3 < dd <= rn:
                put(cv, x, y, nz, 'plank')
                if dd > rn - 1 and (int(math.degrees(math.atan2(y - my, x - mx))) // 30) % 3 == 0:
                    put(cv, x, y, nz - 1, 'timber')                         # broken rail stubs
    # mast posts from the quarterdeck: the core already runs nz..qz-1 (spiral_stair)
    rep['assist'] = {'mast': (mx, my), 'nest_z': nz, 'quarter_z': qz, 'treads': qz - nz,
                     'lantern': (mx - 1, my - 2, nz - 3), 'stern_lantern': (xc, y1 + 1, qz)}
    cv.interiors.append(['assist crow nest', mx, my - 5, nz])
    rep.setdefault('buildings', []).append({'name': 'assist wreck', 'box': [xc - hb, xc + hb, y0, y1, nz - 7, keel]})
    return hl


def brig(cv, rep, S):
    """Moored brig at N1 (west; mirrored): along x, bow west, floating on the water (keel 62), deck, hold with a
    hatch stair, captain's cabin aft with a door forward, two masts with yards, gangway to its pier."""
    B = S['brig']
    x0, x1 = B['x']
    y0, y1 = B['y']
    L = x1 - x0 + 1
    hb = (y1 - y0) // 2
    yc = y0 + hb
    deck = B['deck']
    hl = Hull(cv, 'x', (x0, yc), L, hb, lambda u: deck, 62 - deck, bow_taper=0.3)
    hl.build(trim_z=2)
    hl.floor(5, 2, L - 2)
    # cabin aft (last 9 u): walls up 5 from the deck, roof, door forward
    cu = L - 10
    for u in range(cu, L):
        for v in hl.vs():
            a = hl.av(v)
            if a > hl.half(u) + 0.01:
                continue
            x, y = hl.xy(u, v)
            if a > hl.half(u) - 1 or u == cu or u == L - 1:
                box(cv, x, x, y, y, deck - 5, deck - 1, 'hull')
            put(cv, x, y, deck - 5, 'deck')
    cx0, _ = hl.xy(cu, 0)
    cv.carve(cx0, cx0, yc - 1, yc + 1, deck - 4, deck - 1)
    cv.carve(x1, x1, yc - 3, yc - 2, deck - 3, deck - 2)
    cv.interiors.append(['brig cabin', cx0 + 4, yc, deck])
    # hold below with a stair down (across the beam)
    straight_stair(cv, yc + 3, x0 + 14, x0 + 15, deck + 5, 5, -1, GC['stair'], 'stair', along='y')
    cv.interiors.append(['brig hold', x0 + 20, yc, deck + 5])
    # masts and yards
    rep.setdefault('brig_masts', [])
    for mu, mt in ((12, 24), (24, 22)):
        mx_, _ = hl.xy(mu, 0)
        for z in range(mt, deck):
            put(cv, mx_, yc, z, 'mast')
        for zy in (mt + 4, mt + 12):
            box(cv, mx_, mx_, yc - 6, yc + 6, zy, zy, 'mast')
        rep['brig_masts'].append((mx_, yc, mt))
    # bowsprit
    for i in range(1, 7):
        put(cv, x0 - i, yc, deck - i // 2, 'mast')
        if i // 2:
            put(cv, x0 - i + 1, yc, deck - i // 2, 'mast')
    # gangway from the pier (south side) to the deck
    (px, py0), (_, py1) = B['pier']
    pier(cv, px - 1, px + 1, py0 + 1, py1, z=60)
    # sloped gangway: plank ramp stepping 1 per column from the pier (z 60) up to the deck
    rise = 60 - deck
    for i in range(rise + 1):
        yy = y1 + rise + 1 - i
        z = 60 - i
        box(cv, px - 1, px + 1, yy, yy, z, z, 'plank')
        cv.carve(px - 1, px + 1, yy, yy, z - 4, z - 1)
        col_down(cv, px - 1, yy, z + 1, 'post')
        col_down(cv, px + 1, yy, z + 1, 'post')
    cv.carve(px - 1, px + 1, y1, y1, deck - 3, deck - 1)                     # gap in the bulwark
    rep['brig'] = {'stern_lantern': (x1 + 1, yc, deck - 6), 'bow_lantern': (x0 + 2, yc, deck - 2)}
    rep.setdefault('buildings', []).append({'name': 'brig', 'box': [x0, x1, y0, y1, 20, 62]})


# =============================================================================================== cannon fort

def fort(cv, rep, S):
    """Cannon fort on the fort islet (axis; west half built): 3-thick curtain walls with a rampart walk and
    embrasures, south gate on the axis, SW bastion tower (two storeys + gun roof), north wing (magazine + two-storey
    barracks), stairs from the courtyard to the rampart, courtyard well, flagstaff and cannons."""
    F = S['fort']
    x0, x1 = F['x'][0], 255
    y0, y1 = F['y']
    fl, wt = F['floor'], F['wall_top']
    t = 3
    pad(cv, x0 - 2, 255, y0 - 2, y1 + 2, fl, 'stone_dk')
    # curtain walls (solid), rampart walk on top (wall_top), parapet with embrasures on the outer cell
    box(cv, x0, x1, y0, y0 + t - 1, wt, fl - 1, 'stone')
    box(cv, x0, x1, y1 - t + 1, y1, wt, fl - 1, 'stone')
    box(cv, x0, x0 + t - 1, y0, y1, wt, fl - 1, 'stone')
    for x in range(x0, x1 + 1):
        for (y, out) in ((y0, True), (y1, True)):
            if (x - x0) % 4 != 2:
                box(cv, x, x, y, y, wt - 2, wt - 1, 'stone')
    for y in range(y0, y1 + 1):
        if (y - y0) % 4 != 2:
            box(cv, x0, x0, y, y, wt - 2, wt - 1, 'stone')
    # south gate on the axis (5 tall), arch keystone band
    cv.carve(252, 255, y1 - t + 1, y1, fl - 6, fl - 1)
    box(cv, 251, 255, y1 + 1, y1 + 1, fl - 8, fl - 7, 'stone_dk')
    rep['fort_gate'] = (253, y1 + 1, fl - 6)
    # SW bastion tower: x 230-241, y 145-156, two storeys inside, gun roof 1 over the rampart
    tx0, tx1, ty0, ty1 = x0, x0 + 11, y1 - 11, y1
    box(cv, tx0, tx1, ty0, ty1, wt - 1, fl - 1, 'stone')
    cv.carve(tx0 + 2, tx1 - 1, ty0 + 1, ty1 - 2, wt, fl - 1)
    box(cv, tx0 + 2, tx1 - 1, ty0 + 1, ty1 - 2, fl - 5, fl - 5, 'floor')
    box(cv, tx0, tx1, ty0, ty1, wt - 1, wt - 1, 'stone_dk')
    for x in range(tx0, tx1 + 1):
        for y in (ty0, ty1):
            if (x + y) % 3 == 0:
                put(cv, x, y, wt - 2, 'stone')
    for y in range(ty0, ty1 + 1):
        if (y + tx0) % 3 == 0:
            put(cv, tx0, y, wt - 2, 'stone')
    cv.carve(tx1, tx1, ty0 + 4, ty0 + 6, fl - 4, fl - 1)                      # door from the courtyard (east)
    straight_stair(cv, tx0 + 3, ty0 + 2, ty0 + 3, fl, 5, 1, GC['stair'], 'stair')       # ground -> upper floor
    straight_stair(cv, tx0 + 3, ty1 - 4, ty1 - 3, fl - 5, fl - 5 - (wt - 1), 1, GC['stair'], 'stair')  # -> roof
    for (x, y) in ((tx0 + 1, ty0 + 5), (tx0 + 5, ty1 - 1)):                    # slit windows
        cv.carve(x - 1 if x == tx0 + 1 else x, x, y, y + (1 if x == tx0 + 1 else 0), fl - 3, fl - 2)
        cv.carve(x - 1 if x == tx0 + 1 else x, x, y, y + (1 if x == tx0 + 1 else 0), fl - 8, fl - 7)
    cv.interiors.append(['fort tower ground', tx0 + 6, ty0 + 5, fl])
    cv.interiors.append(['fort tower upper', tx0 + 6, ty0 + 5, fl - 5])
    cv.interiors.append(['fort tower roof', tx0 + 6, ty0 + 3, wt - 1])
    # north wing: magazine (x 233-238) + barracks (x 239-255, two storeys), roof = rampart level
    wy0, wy1 = y0 + t, y0 + t + 9
    box(cv, x0 + t, x1, wy0, wy1, wt, fl - 1, 'wall_dk')
    cv.carve(x0 + t, x1, wy0, wy1 - 1, wt + 1, fl - 1)
    box(cv, x0 + t + 5, x0 + t + 5, wy0, wy1, wt + 1, fl - 1, 'wall_dk')    # magazine wall
    box(cv, x0 + t + 6, x1, wy0, wy1 - 1, fl - 5, fl - 5, 'floor')           # barracks upper floor
    cv.carve(x0 + t + 1, x0 + t + 3, wy1, wy1, fl - 4, fl - 1)               # magazine door
    cv.carve(245, 247, wy1, wy1, fl - 4, fl - 1)                               # barracks door
    for wx in (241, 249):
        cv.carve(wx, wx + 1, wy1, wy1, fl - 3, fl - 2)
        cv.carve(wx, wx + 1, wy1, wy1, fl - 8, fl - 7)
    straight_stair(cv, 241, wy0 + 1, wy0 + 2, fl, 5, 1, GC['stair'], 'stair')
    for (x, y) in ((x0 + t + 1, wy0 + 1), (x0 + t + 3, wy0 + 1), (x0 + t + 1, wy0 + 3)):     # powder kegs
        box(cv, x, x + 1, y, y + 1, fl - 2, fl - 1, 'barrel')
    for y in range(wy0 + 1, wy1 - 1, 3):                                       # bunks
        box(cv, 252, 254, y, y, fl - 6, fl - 6, 'furniture')
    cv.interiors.append(['fort magazine', x0 + t + 2, wy0 + 6, fl])
    cv.interiors.append(['fort barracks', 250, wy0 + 4, fl])
    cv.interiors.append(['fort barracks upper', 250, wy0 + 4, fl - 5])
    # stairs courtyard -> rampart along the west wall (rising north), lands on the wall walk
    straight_stair(cv, wy1 + 1 + (fl - wt), x0 + t, x0 + t + 1, fl, fl - wt, -1, GC['stair'], 'stair', along='y')
    cv.interiors.append(['fort rampart', x0 + 1, y0 + 14, wt])
    # courtyard: well on the axis, flagstaff, cannons on the rampart facing south and west
    for x in range(250, 256):
        for y in range(137, 143):
            if math.hypot(x - 255.5, y - 139.5) <= 3.2 and math.hypot(x - 255.5, y - 139.5) > 2.0:
                box(cv, x, x, y, y, fl - 2, fl - 1, 'stone')
    rep['fort_flag'] = (255, wy0 + 5, wt - 1)
    for z in range(wt - 14, wt):
        put(cv, 255, wy0 + 5, z, 'mast')
    for x in (244, 248):                                                       # through the south embrasures
        box(cv, x, x, y1 - 2, y1, wt - 1, wt - 1, 'iron')
        box(cv, x - 1, x + 1, y1 - 3, y1 - 3, wt - 1, wt - 1, 'timber')
    for y in (132, 140):                                                       # through the west embrasures
        box(cv, x0, x0 + 2, y, y, wt - 1, wt - 1, 'iron')
        box(cv, x0 + 2, x0 + 2, y - 1, y + 1, wt - 1, wt - 1, 'timber')
    rep['fort_torches'] = [(x0 - 1, y0 + 6, wt + 3), (x0 - 1, y1 - 14, wt + 3), (251, y1 + 1, fl - 9),
                           (x0 + 6, y1 + 1, fl - 4), (x0 + 3, wy1 + 1, fl - 5)]
    rep['fort_floor'] = fl
    rep.setdefault('buildings', []).append({'name': 'fort', 'box': [x0, 282, y0, y1, wt - 2, fl]})


# =============================================================================================== skull crag

def skull(cv, rep, S):
    """Skull crag on the skull islet (axis; west half + axis): cranium, maxilla, brow and cheekbones, the jaw over a
    sea cave (pool fed by the lagoon, rock ledges, treasure alcove), eye sockets with real rooms reached by a stair
    tunnel inside the skull, a nose cavity, teeth. Built as rock ('skull_rock'), painted bone by csr_art."""
    K = S['skull']
    cx, cy, cz, rx, ry, rz = K['cranium']
    W = 255

    def ell(cx_, cy_, cz_, rx_, ry_, rz_, mat='skull_rock', air=False):
        for x in range(int(cx_ - rx_ - 1), min(W, int(cx_ + rx_ + 1)) + 1):
            for y in range(int(cy_ - ry_ - 1), int(cy_ + ry_ + 2)):
                for z in range(max(0, int(cz_ - rz_ - 1)), min(63, int(cz_ + rz_ + 1)) + 1):
                    if ((x - cx_) / rx_) ** 2 + ((y - cy_) / ry_) ** 2 + ((z - cz_) / rz_) ** 2 <= 1:
                        if air:
                            cv.clear(x, y, z)
                        else:
                            put(cv, x, y, z, mat)
    ell(cx, cy, cz, rx, ry, rz)                                               # cranium
    ell(*K['maxilla'])                                                        # upper face / cheeks
    ell(cx - 16, 326, 40, 8, 9, 7)                                            # cheekbone
    ell(cx - 11, 321, 26, 10, 6, 4)                                           # brow ridge
    ell(cx, 338, 55, 24, 18, 8)                                               # jaw mass (into the islet)
    # fill down to the seabed under every skull column (ground is solid all the way down)
    for x in range(int(cx - rx - 2), W + 1):
        for y in range(int(cy - ry - 2), int(cy + ry + 3)):
            col = cv.solid[x, y]
            m = cv.mat[x, y]
            sk = np.nonzero(col & (m == cv.material('skull_rock')))[0]
            if len(sk):
                zb = int(sk.max())
                for z in range(zb + 1, 64):
                    if not cv.solid[x, y, z]:
                        put(cv, x, y, z, 'rock')
    # eye sockets (carve), eye rooms behind them (floor z ey1 + 1), a lantern slot at the back
    ex, ey, ez, erx, ery, erz = K['eye']
    ell(ex, ey - 4, ez, erx, ery, erz, air=True)
    rx0, rx1, ry0, ry1, rz0, rz1 = K['eye_room']
    cv.carve(rx0, rx1, ry0, ry1, rz0, rz1)
    box(cv, rx0, rx1, ry0, ry1, rz1 + 1, rz1 + 1, 'floor')
    # the socket floor meets the room floor: fill the socket bottom to the room floor level
    for x in range(int(ex - erx), int(ex + erx) + 1):
        for y in range(int(ey - ery - 4), ry0 + 1):
            if cv.solid[x, y, rz1 + 1] or not cv.solid[x, y, rz1 + 2]:
                continue
            put(cv, x, y, rz1 + 1, 'skull_rock')
    cv.interiors.append(['skull eye room', (rx0 + rx1) // 2, (ry0 + ry1) // 2 + 2, rz1 + 1])
    rep['eye_glow'] = [(ex, ry1, rz1 - 2), (ex - 2, ry1, rz1 - 1), (ex + 2, ry1, rz1 - 1), (ex, ey - 2, rz1)]
    # nose cavity (inverted heart): rows z 38..46 at the face, two lobes meeting on the axis
    nx, ny, nz = K['nose']
    for z in range(nz - 4, nz + 5):
        w = max(1, int((z - (nz - 5)) * 0.7))
        for x in range(W - w, W + 1):
            for y in range(ny - 10, ny + 4):
                if math.hypot(x - (W - w * 0.4), (z - nz) * 0.6) <= w + 0.5:
                    cv.clear(x, y, z)
    # mouth = sea cave: carve the jaw opening and the cave behind it (air z mz0..61), pool on the axis (water),
    # rock ledges at ledge_z on the west, teeth hanging from the upper jaw and rising from the ledge edge
    mx0, mx1, my0, my1, mz0, mz1 = K['mouth']
    lz = K['ledge_z']
    for x in range(mx0, W + 1):
        for y in range(my0, my1 + 1):
            # vaulted cave: roof rises toward the centre and the back
            roof = mz0 - int(4 * smooth((x - mx0) / 10.0)) - (3 if y > my0 + 8 else 0)
            cv.carve(x, x, y, y, roof, 62)
            if x < K['pool_x']:
                box(cv, x, x, y, y, lz, 63, 'rock')
            else:
                box(cv, x, x, y, y, 63, 63, 'sea')
    # cave mouth opens to the north lagoon: clear rock in front of the opening below the jaw line
    for x in range(mx0, W + 1):
        for y in range(my0 - 10, my0):
            cv.carve(x, x, y, y, mz0, 62)
            box(cv, x, x, y, y, 63, 63, 'sea')
    # teeth: upper teeth hang from the jaw at the front (grown up until they meet rock), lower teeth on the ledge
    for x in range(mx0 + 1, W + 1, 4):
        for xx in (x, x + 1):
            if xx > W:
                continue
            for y in range(my0, my0 + 3):
                zt = mz0 + 3
                z = zt
                while z > mz0 - 12 and not cv.solid[xx, y, z]:
                    z -= 1
                if cv.solid[xx, y, z]:
                    box(cv, xx, xx, y, y, z + 1, zt, 'bone')
        if x < K['pool_x'] - 2:
            box(cv, x, x + 1, my0, my0, lz - 2, lz - 1, 'bone')
    # ledge path out of the cave: a rock shelf west along the jaw front, then south to the islet beach
    pts = [(mx0 + 6, my0 - 3), (mx0 - 14, my0 - 3), (mx0 - 14, my0 + 16)]
    for (p0, p1) in zip(pts, pts[1:]):
        for (x, y, _) in line_points(p0[0], p0[1], 0, p1[0], p1[1], 0):
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    X, Y = x + dx, y + dy
                    if top(cv, X, Y) >= lz:
                        box(cv, X, X, Y, Y, lz, 63, 'rock')
                    cv.carve(X, X, Y, Y, lz - 4, lz - 1)
    # treasure alcove at the back of the cave (axis)
    chx, chy = K['chest']
    cv.carve(chx - 5, W, my1 + 1, my1 + 6, lz - 5, lz - 1)
    box(cv, chx - 5, W, my1 + 1, my1 + 6, lz, 63, 'rock')
    box(cv, W - 2, W, my1 + 3, my1 + 4, lz - 2, lz - 1, 'chest')
    box(cv, W - 4, W - 3, my1 + 2, my1 + 5, lz - 1, lz - 1, 'gold')
    rep['skull_chest'] = (W - 1, my1 + 3, lz - 3)
    cv.interiors.append(['skull sea cave', mx0 + 4, my0 + 12, lz])
    # walkway across the cave back from the west ledge to the alcove (over the pool edge)
    box(cv, K['pool_x'], W, my1 - 2, my1, lz, 63, 'rock')
    # stair tunnel: from the cave ledge at the back (y stair_y0) rising north to the eye room floor
    sx0, sx1 = K['stair_x']
    rise = lz - (rz1 + 1)
    ys = K['stair_y0']
    # connector from the cave back to the stair foot
    cv.carve(sx0, sx1 + 2, my1 - 3, ys + 1, lz - 4, lz - 1)
    box(cv, sx0, sx1 + 2, my1 - 3, ys + 1, lz, 63, 'rock')
    straight_stair(cv, ys, sx0, sx1, lz, rise, -1, GC['stair'], 'stair', along='y')
    top_y = ys - rise + 1
    cv.carve(sx0, sx1, top_y - 1, ry1 + 1, rz1 - 3, rz1)
    box(cv, sx0, sx1, min(top_y - 1, ry1 + 1), max(top_y - 1, ry1 + 1), rz1 + 1, rz1 + 1, 'floor')
    cv.interiors.append(['skull stair', sx0 + 1, ys - rise // 2, lz - rise // 2])
    rep['skull'] = {'stair': (sx0, ys, rise), 'eye_room_floor': rz1 + 1}
    rep.setdefault('buildings', []).append({'name': 'skull', 'box': [int(cx - rx), 256, int(cy - ry), int(cy + ry),
                                                                    int(cz - rz), 62]})


def bridge_ruin(cv, rep, S):
    """Rope-and-plank bridge ruin over the maelstrom (axis): neck south beach -> the skull's jaw ledge. 3 wide,
    posts to the seabed, rope rails; the middle stretch sags, rails gone and edge planks missing (centre stays)."""
    B = S['bridge_ruin']
    y0, y1 = B['y']
    z = B['z']
    b0, b1 = B['broken']
    for y in range(y0, y1 + 1):
        brk = b0 <= y <= b1
        zz = z + (1 if brk else 0)
        if top(cv, 255, y) <= zz:
            continue
        put(cv, 255, y, zz, 'plank')
        if not (brk and y % 2):
            put(cv, 254, y, zz, 'plank')
        if y % 4 == 0:
            col_down(cv, 254, y, zz + 1, 'post')
        if not brk and y % 4 == 0:
            for k in range(zz - 2, zz):
                put(cv, 253, y, k, 'post')
            col_down(cv, 253, y, zz, 'post')
    for y in range(y0, y1 + 1, 4):
        if b0 - 3 <= y <= b1 + 3:
            continue
        if y + 4 <= y1 and not (b0 - 3 <= y + 4 <= b1 + 3):
            for (a, b, c) in line_points(253, y, z - 2, 253, y + 4, z - 2):
                put(cv, a, b, c, 'rope')
    rep['bridge_ruin_lamps'] = [(253, y0 + 1, z - 3), (253, y1 - 2, z - 3)]


# =============================================================================================== props (low)

def crate_stack(cv, x, y, n=3, mat='crate', size=2):
    g = top(cv, x, y)
    z = g - 1
    for k in range(n):
        ox = (k % 2) * size
        box(cv, x + ox, x + ox + size - 1, y, y + size - 1, z - size + 1, z, mat)
        if k % 2 == 1:
            z -= size
    return g


def barrels(cv, x, y, n=5):
    """Cluster of barrels (2x2x3 each, hooped), a few stacked; footprint about 6 x 6."""
    g = top(cv, x + 2, y + 2)
    spots = [(0, 0), (2, 0), (4, 1), (1, 2), (3, 3), (0, 4)][:n]
    for i, (a, b) in enumerate(spots):
        gg = top(cv, x + a, y + b)
        box(cv, x + a, x + a + 1, y + b, y + b + 1, gg - 3, gg - 1, 'barrel')
        put(cv, x + a, y + b, gg - 2, 'iron')
    box(cv, x + 1, x + 2, y + 1, y + 2, g - 6, g - 4, 'barrel')        # one on top (bridging two)


def rowboat(cv, x, y, L=10, W=5, upturned=False):
    """Beached rowing boat (open hull, thwarts) or upturned on the sand; 3-4 tall."""
    g = top(cv, x + L // 2, y + W // 2)
    for i in range(L):
        half = (W / 2) * (0.55 if i in (0, L - 1) else (0.8 if i in (1, L - 2) else 1.0))
        for j in range(W):
            dj = abs(j - (W - 1) / 2)
            if dj > half:
                continue
            gg = g
            if upturned:
                box(cv, x + i, x + i, y + j, y + j, gg - 3, gg - 3, 'hull')
                if dj > half - 1:
                    box(cv, x + i, x + i, y + j, y + j, gg - 2, gg - 1, 'hull')
            else:
                put(cv, x + i, y + j, gg - 1, 'hull')
                if dj > half - 1 or i in (0, L - 1):
                    box(cv, x + i, x + i, y + j, y + j, gg - 3, gg - 2, 'hull')
        if not upturned and i in (3, 6):
            box(cv, x + i, x + i, y, y + W - 1, gg - 2, gg - 2, 'plank')


def cannon(cv, x, y, along='x', L=5):
    """Cannon on a wooden carriage (3 tall): barrel along x or y."""
    g = top(cv, x, y)
    if along == 'x':
        box(cv, x, x + L - 1, y, y + 1, g - 3, g - 3, 'iron')
        box(cv, x, x + 1, y, y + 1, g - 4, g - 4, 'iron')
        box(cv, x + 1, x + 3, y - 1, y + 2, g - 2, g - 1, 'timber')
    else:
        box(cv, x, x + 1, y, y + L - 1, g - 3, g - 3, 'iron')
        box(cv, x, x + 1, y, y + 1, g - 4, g - 4, 'iron')
        box(cv, x - 1, x + 2, y + 1, y + 3, g - 2, g - 1, 'timber')


def logs(cv, x, y, L=8, W=4):
    g = top(cv, x, y)
    box(cv, x, x + L - 1, y, y + W - 1, g - 2, g - 1, 'timber')
    box(cv, x + 1, x + L - 2, y + 1, y + W - 2, g - 3, g - 3, 'timber')


def ship_anchor(cv, x, y, big=False):
    """Ship's anchor stuck fluke-down in the sand: shank, stock, crown and flukes (iron); 8 or 11 tall."""
    g = top(cv, x, y)
    h = 11 if big else 8
    for z in range(g - h, g):
        box(cv, x, x + 1, y, y, z, z, 'iron')
    box(cv, x - 3, x + 4, y, y, g - h + 1, g - h + 1, 'timber')            # stock
    put(cv, x, y, g - h - 1, 'iron')
    box(cv, x - 1, x + 2, y, y, g - h - 2, g - h - 2, 'iron')              # ring
    for k in range(1, 4):                                                   # flukes along y
        box(cv, x, x + 1, y - k, y - k, g - 1 - (k // 2), g - 1, 'iron')
        box(cv, x, x + 1, y + k, y + k, g - 1 - (k // 2), g - 1, 'iron')
    box(cv, x - 1, x + 2, y - 3, y + 3, g - 1, g - 1, 'iron') if big else None


def pots(cv, x, y):
    crate_stack(cv, x, y, 4, 'pot', 3)
    crate_stack(cv, x, y + 3, 3, 'pot', 3)


def boulder(cv, x, y, r=3, seed=0, mat='boulder'):
    g = top(cv, x, y)
    rng = np.random.default_rng(seed)
    cv.ellipsoid(x, y, g - r * 0.55, r * rng.uniform(0.9, 1.25), r * rng.uniform(0.9, 1.25), r * 0.95, GC[mat], mat)
    for xx in range(int(x - r - 2), int(x + r + 3)):
        for yy in range(int(y - r - 2), int(y + r + 3)):
            zs = np.nonzero(cv.solid[xx, yy])[0]
            if len(zs) and cv.mat[xx, yy, zs[0]] == cv.materials.get(mat):
                col_down(cv, xx, yy, zs[0], mat)


def coral(cv, x, y, seed=0):
    """Coral head on the sand: knobbly mound with three branching fingers (6 tall)."""
    rng = np.random.default_rng(seed)
    g = top(cv, x, y)
    cv.ellipsoid(x, y, g - 1.5, 3.2, 2.8, 2.2, GC['coral'], 'coral')
    for k in range(3):
        a = k * 2.1 + rng.random()
        px, py = int(round(x + 1.6 * math.cos(a))), int(round(y + 1.6 * math.sin(a)))
        for z in range(g - 6 + k % 2, g - 2):
            put(cv, px, py, z, 'coral')
    for xx in range(x - 4, x + 5):
        for yy in range(y - 4, y + 5):
            zs = np.nonzero(cv.solid[xx, yy])[0]
            if len(zs) and cv.mat[xx, yy, zs[0]] == cv.materials.get('coral'):
                col_down(cv, xx, yy, zs[0], 'coral')


def longboat(cv, x, y):
    """Capsized longboat on the neck sand: upturned hull (12 x 5), keel ridge, a gap at the gunwale to crawl in."""
    rowboat(cv, x, y, 12, 5, upturned=True)
    g = top(cv, x + 6, y - 2)
    box(cv, x + 1, x + 10, y + 2, y + 2, g - 4, g - 4, 'hull')


def mast_log(cv, x, y, L=22):
    """A fallen mast lying along x with a broken yard across it (2 tall)."""
    g = top(cv, x + L // 2, y)
    box(cv, x, x + L - 1, y, y + 1, g - 2, g - 1, 'mast')
    box(cv, x + 6, x + 7, y - 4, y + 5, g - 1, g - 1, 'mast')
    box(cv, x + 7, x + 9, y + 2, y + 4, g - 1, g - 1, 'sail')


def sea_chests(cv, x, y):
    """Washed-up sea chests and coin spill (3 tall); the axis pile (built as its west half)."""
    g = top(cv, x, y)
    box(cv, x, x + 2, y, y + 1, g - 2, g - 1, 'chest')
    box(cv, x - 3, x - 1, y + 2, y + 4, g - 2, g - 1, 'chest')
    box(cv, x, x + 1, y + 3, y + 4, g - 1, g - 1, 'gold')
    put(cv, x + 1, y, g - 3, 'gold')


def ribs(cv, rep, S):
    """Hull ribs of an old wreck on the neck (axis, west half): a keel beam along x on the sand and inverted-U ribs
    every 3 columns spanning y (9 tall). Walk-through between and under the ribs."""
    R = S['ribs']
    x0, x1 = R['x']
    y0, y1 = R['y']
    g = top(cv, x1, (y0 + y1) // 2)
    box(cv, x0, x1, (y0 + y1) // 2, (y0 + y1) // 2, g - 1, g - 1, 'timber')
    cy = (y0 + y1) / 2
    half = (y1 - y0) / 2
    for x in range(x1, x0 - 1, -R['every']):
        for y in range(y0, y1 + 1):
            dy = abs(y - cy) / half
            zt = g - 1 - int(round(R['h'] * math.sqrt(max(0.0, 1 - dy ** 3))))
            if dy > 0.82:                                                   # the uprights reach the sand
                box(cv, x, x, y, y, zt, g - 1, 'timber')
            else:
                put(cv, x, y, zt, 'timber')
                put(cv, x, y, zt - 1, 'timber') if dy < 0.3 else None
    rep['ribs'] = {'x': (x0, x1), 'g': g}


def rope_fence(cv, x0, y0, x1, y1, gap_every=12, gap=4):
    """Low driftwood post-and-rope fence (posts 2 tall every 3, rope 1 below the post top) with walk gaps."""
    pts = line_points(x0, y0, 0, x1, y1, 0)
    for i, (x, y, _) in enumerate(pts):
        if (i % gap_every) >= gap_every - gap:
            continue
        g = top(cv, x, y)
        if i % 3 == 0:
            box(cv, x, x, y, y, g - 2, g - 1, 'post')
        elif not cv.solid[x, y, g - 2]:
            put(cv, x, y, g - 2, 'rope')


def alcove(cv, rep, x, y, face='W', seed=0):
    """Treasure-chest alcove: a rock outcrop (9 x 9, 7 tall) with a carved niche facing `face`, a chest and coins."""
    g = top(cv, x, y)
    rng = np.random.default_rng(seed)
    cv.ellipsoid(x, y, g - 2, 5.5, 5.0, 6.0, GC['rock'], 'rock')
    for xx in range(x - 7, x + 8):
        for yy in range(y - 7, y + 8):
            zs = np.nonzero(cv.solid[xx, yy])[0]
            if len(zs):
                col_down(cv, xx, yy, zs[0], 'rock')
    dx = {'W': -1, 'E': 1}[face]
    nx0 = x + dx * 6
    g = min(61, top(cv, x + dx * 8, y))                                   # niche floor = ground at its mouth
    a, b = sorted((x, nx0))
    cv.carve(a, b, y - 2, y + 2, g - 5, g - 1)
    box(cv, a, b, y - 2, y + 2, g, 63, 'rock')
    box(cv, x - 1, x, y - 1, y, g - 2, g - 1, 'chest')
    put(cv, x + dx, y + 1, g - 1, 'gold')
    put(cv, x + dx, y - 1, g - 1, 'gold')
    rep.setdefault('chest_glow', []).append((x + dx, y, g - 3))
    cv.interiors.append([f'alcove {x},{y}', x + dx * 3, y, g])


def harbour(cv, rep, S):
    """West harbour behind the spawn: two piers into the sea with lamp posts and moored rowboats."""
    Hh = S['harbour']
    lamps = rep.setdefault('dock_lamps', [])
    for y in (Hh['pier_y'][0], Hh['pier_y'][1]):
        # pier starts where the land is (search east from pier_x[0])
        xs = Hh['pier_x'][1]
        while xs < 120 and top(cv, xs, y) >= 61:
            xs += 1
        pier(cv, y - 1, y + 1, Hh['pier_x'][0], xs, z=60, along='x', lamps=lamps)
        rowboat(cv, Hh['pier_x'][0] + 3, y + 3, 9, 4)


# =============================================================================================== west-half build

def build_west(S, seed):
    cv = Canvas(S['name'])
    for k in GC:
        cv.material(k)
    rep = {}
    T = terrain(cv, S, seed)
    rep['terrain'] = {k: int(v.sum()) for k, v in T.items()}
    # spawn isle: town, harbour, alcoves, spawn fences
    for (name, x0, x1, y0, y1, st, ridge, door, ruin) in S['houses']:
        house(cv, rep, name, x0, x1, y0, y1, st, ridge, door, ruin)
    harbour(cv, rep, S)
    for i, (x, y, face) in enumerate(S['alcoves']):
        alcove(cv, rep, x, y, face, seed=i)
    b = S['spawn']['base']
    hs = S['spawn']['half']
    rope_fence(cv, b[0] - hs - 2, b[1] - hs - 2, b[0] - hs - 2, b[1] + hs + 2)
    # front dressing (low, walk-around)
    for (kind, x, y) in S['front_props']:
        if kind == 'hut':
            hut(cv, rep, x, y, f'fisher hut {y}')
        elif kind == 'rowboat':
            rowboat(cv, x, y, 11, 5, upturned=True)
        elif kind == 'crates':
            crate_stack(cv, x, y, 4, 'crate', 3)
            crate_stack(cv, x, y + 3, 2, 'crate', 3)
        elif kind == 'barrels':
            barrels(cv, x, y)
        elif kind == 'cannon':
            cannon(cv, x, y, 'x')
        elif kind == 'logs':
            logs(cv, x, y)
        elif kind == 'anchor':
            ship_anchor(cv, x, y)
        elif kind == 'pots':
            pots(cv, x, y)
    for i, (x, y, r) in enumerate(S['spawn_cover']):
        boulder(cv, x, y, r, seed=i)
    # neck strip props (under the platform; low, >= 25 air below the platform)
    for i, (kind, x, y) in enumerate(S['strip_props']):
        if kind == 'longboat':
            longboat(cv, x, y)
        elif kind == 'anchor_big':
            ship_anchor(cv, x, y, big=True)
        elif kind == 'coral':
            coral(cv, x, y, seed=i)
        elif kind == 'mast_log':
            mast_log(cv, x, y)
        elif kind == 'barrels':
            barrels(cv, x, y)
        elif kind == 'cannon':
            cannon(cv, x, y, 'y')
    ribs(cv, rep, S)
    sea_chests(cv, 253, 270)
    # flank chains: north links and the same links y-mirrored for the south chain
    rep['links'] = []
    for (kind, pts, w) in S['links']:
        for flip in (False, True):
            P_ = [(p[0], 511 - p[1]) if flip else p for p in pts]
            for A, B in zip(P_, P_[1:]):
                if kind == 'rope':
                    rep['links'].append(rope_bridge(cv, A, B, w))
                    continue
                along = 'y' if A[0] == B[0] else 'x'
                lamps = rep.setdefault('dock_lamps', [])
                if along == 'y':
                    x0_ = A[0] - w // 2
                    lo = min(A[1], B[1])
                    pier(cv, x0_, x0_ + w - 1, A[1], B[1], z=60, broken=None if kind == 'pier' else (lo + 8, lo + 14),
                         lamps=lamps)
                else:
                    y0_ = A[1] - w // 2
                    lo = min(A[0], B[0])
                    pier(cv, y0_, y0_ + w - 1, A[0], B[0], z=60, along='x',
                         broken=None if kind == 'pier' else (lo + 9, lo + 16), lamps=lamps)
    for (kind, pts, w) in S['centre_links']:
        rep['links'].append(rope_bridge(cv, pts[0], pts[1], w))
    for ((x, ya), (_, yb)) in S['axis_piers']:
        pier(cv, x - 1, x, ya, yb, z=60, lamps=rep.setdefault('dock_lamps', []))
    brig(cv, rep, S)
    # centre (axis halves) and the assist wreck
    fort(cv, rep, S)
    galleon(cv, rep, S)
    skull(cv, rep, S)
    bridge_ruin(cv, rep, S)
    assist_wreck(cv, rep, S)
    rep['west_seed'] = seed
    return cv, rep
