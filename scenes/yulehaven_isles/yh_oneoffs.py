"""Yulehaven Isles one-off landmarks, placed AFTER the mirror (each one is a cosmetic asymmetric box):

  lighthouse      north chain, Blue end (skerry L)       spiral stair to the lamp room, gallery, string lights
  Yule goat       north chain, Red end (skerry L mirror)  giant straw goat, walk under its belly
  stone chapel    south chain, Red end                   nave with pews and candles, bell tower with a stair
  ice camp        south chain, Blue end                  ice shelf, three enterable tents, fishing holes
  spruce          islet north outcrop                    decorated spruce with a star
  giant mailbox   Blue post office (inner south shore)   overflowing with letters
  sauna jump      Red sauna pier                         jump tower + board over the sea
  iceberg + tag   SW corner                              map name on an ice plate at sky level, one ice stalk
  snowmen         beaches (each one different)           driftwood + buoy snowmen
  presents        beaches                                washed-up present crates

Pairs are balanced by role: each team has one tall landmark at its flank end (lighthouse / chapel) and one other
(goat / ice camp); the post office and sauna share one mirrored shell.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage as ndi

from aosmap.kit import veg
from aosmap.kit.canvas import line_points
from aosmap.kit.structures import spiral_stair, straight_stair
from aosmap.pixelfont import text_mask

from yh_build import GC, box, col_down, gable_roof, pad, put, top, windows_on


def _bbox(pts, m=1):
    a = np.array(pts)
    return [int(a[:, 0].min()) - m, int(a[:, 0].max()) + m, int(a[:, 1].min()) - m, int(a[:, 1].max()) + m]


class Rec:
    """Wraps the canvas and records the x/y footprint of everything a one-off writes."""

    def __init__(self, cv):
        self.cv = cv
        self.pts = []

    def mark(self, x0, x1, y0, y1):
        self.pts += [(x0, y0), (x1, y1)]


TERRAIN = ('rock', 'turf', 'beach', 'hop', 'footing')


def level_site(cv, mask, z=None, blend=10):
    """Level a building site on a skerry: tops inside `mask` set to z (default: the median top), then a skirt
    `blend` wide outside it is clamped to within d of z (d = distance from the site), so the site meets the rock in
    steps of at most 1 - no sheer mesa. Only terrain columns are touched (z >= 62 stays as it is)."""
    T = cv.tops()
    if z is None:
        landm = mask & (T < 62)
        z = int(np.median(T[landm])) if landm.any() else 60
    d = ndi.distance_transform_edt(~mask)
    ids = [cv.materials[m] for m in TERRAIN if m in cv.materials]
    xs, ys = np.nonzero(mask | (d <= blend))
    for x, y in zip(xs, ys):
        t = int(T[x, y])
        if t < 62 and cv.mat[x, y, t] not in ids:
            continue
        k = 0 if mask[x, y] else int(math.ceil(d[x, y]))
        lo, hi = z - k, z + k                                # allowed top range
        if t < lo:
            cv.carve(x, x, y, y, 0, lo - 1)
        elif t > hi:
            box(cv, x, x, y, y, hi, t - 1, 'rock')
    return z


def disc_pad(cv, cx, cy, r, z=None):
    X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    return level_site(cv, (X - cx) ** 2 + (Y - cy) ** 2 <= r * r, z)


# =============================================================================================== lighthouse

def lighthouse(cv, rep, cx, cy):
    g = disc_pad(cv, cx, cy, 8)
    R, zlamp = 5.5, 26
    cv.cylinder(cx + 0.5, cy + 0.5, R, zlamp, g - 1, GC['wall_red'], 'wall_red', hollow=R - 1.2)
    # white bands
    for zb in range(g - 6, zlamp, 8):
        cv.cylinder(cx + 0.5, cy + 0.5, R, zb, zb + 1, GC['trim'], 'trim', hollow=R - 1.2)
    spiral_stair(cv, cx + 0.5, cy + 0.5, zlamp, g, r=4, c=GC['stair'], core=GC['stone'], mat='stair')
    n = g - zlamp
    for x in range(cx - 5, cx + 7):                          # plinth under steps 1-3 (no low pocket under them)
        for y in range(cy - 5, cy + 7):
            d = math.hypot(x - cx, y - cy)                    # cell centre to shaft centre (cx + 0.5)
            if 0.8 < d <= 4.6:
                a = math.degrees(math.atan2(y - cy, x - cx)) % 360
                if 40 <= a < 185:
                    for z in ((g - 1,) if a < 130 else (g - 1, g - 2)):
                        if not cv.solid[x, y, z]:
                            put(cv, x, y, z, 'stair')
    # lamp-room floor: open over the last three steps' sectors
    last = [((n - k) % 8) * math.pi / 4 for k in range(0, 6)]       # climb room: 4 above every step
    for x in range(cx - 5, cx + 7):
        for y in range(cy - 5, cy + 7):
            d = math.hypot(x - cx - 0.5 + 0.5, y - cy - 0.5 + 0.5)
            if d <= 4.6:
                a = math.atan2(y - cy - 0.5, x - cx - 0.5) % (2 * math.pi)
                if any((a - a0) % (2 * math.pi) < math.pi / 4 + 0.1 for a0 in last[1:]):
                    continue
                if not cv.solid[x, y, zlamp]:
                    put(cv, x, y, zlamp, 'floor')
    # gallery ring + rail posts
    for x in range(cx - 8, cx + 10):
        for y in range(cy - 8, cy + 10):
            d = math.hypot(x - cx, y - cy)
            if R - 0.5 < d <= R + 2.0:
                put(cv, x, y, zlamp, 'plank')
                if d > R + 1.2 and (x + y) % 3 == 0:
                    put(cv, x, y, zlamp - 1, 'post')
    # lamp room: open glazed walls z zlamp-5 .. zlamp-1 (posts only), lamp on the core, cone roof
    cv.carve(cx - 5, cx + 6, cy - 5, cy + 6, zlamp - 5, zlamp - 1)
    for k in range(8):
        a = k * math.pi / 4
        px, py = int(round(cx + 0.5 + (R - 0.6) * math.cos(a))), int(round(cy + 0.5 + (R - 0.6) * math.sin(a)))
        for z in range(zlamp - 5, zlamp):
            put(cv, px, py, z, 'wall_red')
    cv.cylinder(cx + 0.5, cy + 0.5, R + 0.8, zlamp - 6, zlamp - 6, GC['roof'], 'roof')
    cv.cone(cx + 0.5, cy + 0.5, R + 0.3, zlamp - 7, zlamp - 13, GC['roof'], 'roof')
    lamp = []
    for z in (zlamp - 1, zlamp - 2, zlamp - 3):
        for (x, y) in ((cx, cy), (cx + 1, cy), (cx, cy + 1), (cx + 1, cy + 1)):
            lamp.append((x, y, z))
            put(cv, x, y, z, 'lamp')
    # door (east) through the wall at the base
    cv.carve(cx + 4, cx + 6, cy - 1, cy + 1, g - 4, g - 1)
    rep['lighthouse'] = {'g': g, 'lamp': lamp, 'R': R, 'zlamp': zlamp, 'c': (cx, cy)}
    cv.interiors.append(['lighthouse base', cx + 3, cy - 3, g])
    cv.interiors.append(['lighthouse lamp room', cx + 3, cy + 3, zlamp])
    return [cx - 21, cx + 22, cy - 21, cy + 22]


# =============================================================================================== Yule goat

def yule_goat(cv, rep, cx, cy, face=-1):
    """Giant straw goat facing -x (toward the chain), legs 2x2, belly 8 above the ground."""
    g = disc_pad(cv, cx, cy, 12)
    bz = g - 12
    cv.ellipsoid(cx, cy, bz, 9.5, 3.6, 3.6, GC['straw'], 'straw')
    for lx in (cx - 6, cx + 5):
        for ly in (cy - 2, cy + 1):
            box(cv, lx, lx + 1, ly, ly + 1, bz + 2, g - 1, 'straw')
            box(cv, lx, lx + 1, ly, ly + 1, g - 5, g - 4, 'ribbon')
    hx = cx + face * 9
    for k in range(6):                                     # short, thick goat neck leaning forward
        x = hx + face * (k // 2)
        z = bz - 2 - k
        box(cv, x - 1, x + 2, cy - 1, cy + 1, z, z, 'straw')
    hx2 = hx + face * 4
    cv.ellipsoid(hx2, cy, bz - 9, 3.2, 2.4, 2.4, GC['straw'], 'straw')
    cv.ellipsoid(hx2 + face * 3, cy, bz - 8, 1.8, 1.6, 1.6, GC['straw'], 'straw')       # muzzle
    for k in range(3):                                     # beard
        put(cv, hx2 + face * 4, cy, bz - 6 + k, 'straw')
    for side in (-1, 1):                                    # curled horns (face-connected lines from the head)
        prev = (hx2, cy + side, bz - 10)
        for k in range(1, 11):
            a = k * 0.55
            q = (int(round(hx2 - face * (2.2 * math.sin(a)))), cy + side * 2,
                 int(round(bz - 11 - 2.4 * (1 - math.cos(a)))))
            for (xx, yy, zz) in line_points(*prev, *q):
                put(cv, xx, yy, zz, 'straw')
            prev = q
    for (xx, yy, zz) in line_points(cx - face * 9, cy, bz - 1, cx - face * 12, cy, bz - 6):     # tail
        put(cv, xx, yy, zz, 'straw')
    for x in range(cx - 9, cx + 10, 5):                     # red ribbon bands round the body
        for y in range(cy - 4, cy + 5):
            for z in range(bz - 4, bz + 5):
                if cv.mat[x, y, z] == cv.materials['straw'] and (
                        not cv.solid[x, y - 1, z] or not cv.solid[x, y + 1, z] or not cv.solid[x, y, z - 1] or
                        not cv.solid[x, y, z + 1]):
                    cv.mat[x, y, z] = cv.materials['ribbon']
                    cv.rgb[x, y, z] = GC['ribbon']
    box(cv, hx - 1, hx + 1, cy - 2, cy + 2, bz - 4, bz - 3, 'ribbon')       # collar
    rep['goat'] = {'g': g, 'belly_z': bz + 4}
    return [cx - 25, cx + 25, cy - 25, cy + 25]


# =============================================================================================== chapel

def square_spiral(cv, x0, y0, n_in, z_bot, z_top, mat='stair', start=0):
    """Stair winding round the inside of an n_in x n_in shaft (x0, y0 = first inner cell), 1 rise per cell on the
    perimeter ring of the shaft; returns the top step position."""
    ring = []
    for i in range(n_in):
        ring.append((x0 + i, y0))
    for j in range(1, n_in):
        ring.append((x0 + n_in - 1, y0 + j))
    for i in range(n_in - 2, -1, -1):
        ring.append((x0 + i, y0 + n_in - 1))
    for j in range(n_in - 2, 0, -1):
        ring.append((x0, y0 + j))
    ring = ring[start:] + ring[:start]
    z = z_bot
    k = 0
    last = None
    while z > z_top:
        z -= 1
        x, y = ring[k % len(ring)]
        box(cv, x, x, y, y, z, min(z + 1, z_bot), mat)      # 2-tall step: face contact with the step below
        cv.carve(x, x, y, y, z - 4, z - 1)
        last = (x, y, z)
        k += 1
    return last, [ring[(k - 1 - i) % len(ring)] for i in range(len(ring))]   # ring ordered from the last step back


def chapel(cv, rep, cx, cy):
    x0, x1, y0, y1 = cx - 8, cx + 7, cy - 12, cy + 11
    msk = np.zeros((512, 512), bool)
    msk[x0 - 2:x1 + 3, y0 - 2:y1 + 3] = True
    g = level_site(cv, msk)
    fz = g - 1
    box(cv, x0, x1, y0, y1, fz, fz, 'stone_dk')
    zt = fz - 9
    box(cv, x0, x1, y0, y1, zt, fz - 1, 'stone')
    cv.carve(x0 + 1, x1 - 1, y0 + 1, y1 - 1, zt, fz - 1)
    lights = rep.setdefault('chapel_windows', [])
    for wy in range(y0 + 4, y1 - 6, 4):                    # tall lancet windows
        for wx in (x0, x1):
            cv.carve(wx, wx, wy, wy, fz - 6, fz - 2)
            lights.append((wx, wy, fz - 2))
    gable_roof(cv, x0, x1, y0, y1, zt, 'y', mat='roof')
    cv.carve(x0, x0, cy - 1, cy + 1, fz - 5, fz - 1)        # west door (arched: 5 tall)
    # pews with a centre aisle, altar, candles
    for py in range(y0 + 3, y1 - 6, 3):
        for (a, b) in ((x0 + 2, cx - 2), (cx + 1, x1 - 2)):
            box(cv, a, b, py, py, fz - 1, fz - 1, 'furniture')
    box(cv, cx - 3, cx + 2, y0 + 1, y0 + 2, fz - 2, fz - 1, 'stone')
    rep['chapel_candles'] = [(cx - 3, y0 + 1, fz - 3), (cx + 2, y0 + 1, fz - 3), (cx, y0 + 2, fz - 3)]
    # bell tower over the south end: 6x6 outside, 4x4 shaft, square spiral up to the bell loft
    tx0, ty0 = cx - 3, y1 - 5
    tz = zt - 12
    box(cv, tx0, tx0 + 5, ty0, ty0 + 5, tz, fz - 1, 'stone')
    cv.carve(tx0 + 1, tx0 + 4, ty0 + 1, ty0 + 4, tz + 1, fz - 1)
    cv.carve(tx0 + 2, tx0 + 3, ty0, ty0, fz - 4, fz - 1)     # opening from the nave
    last, ring = square_spiral(cv, tx0 + 1, ty0 + 1, 4, fz, tz + 6, start=1)   # first step inside the opening
    # loft floor (skip the cells over the last steps)
    lz = last[2]
    skip = set(ring[:5]) if last else set()                  # the last five steps keep their headroom
    for x in range(tx0 + 1, tx0 + 5):
        for y in range(ty0 + 1, ty0 + 5):
            if (x, y) not in skip and not cv.solid[x, y, lz]:
                put(cv, x, y, lz, 'floor')
    for side in range(4):                                    # belfry arches
        if side < 2:
            xa = tx0 if side == 0 else tx0 + 5
            cv.carve(xa, xa, ty0 + 2, ty0 + 3, lz - 4, lz - 1)
        else:
            ya = ty0 if side == 2 else ty0 + 5
            cv.carve(tx0 + 2, tx0 + 3, ya, ya, lz - 4, lz - 1)
    box(cv, tx0 + 2, tx0 + 3, ty0 + 2, ty0 + 3, tz + 1, tz + 2, 'bell')
    cv.cone(tx0 + 3, ty0 + 3, 4.2, tz, tz - 7, GC['roof'], 'roof')
    cv.interiors.append(['chapel nave', cx + 3, cy, fz])
    cv.interiors.append(['chapel bell loft', tx0 + 2, ty0 + 2, lz])
    rep['chapel'] = {'fz': fz, 'tower_top': tz - 7}
    return [x0 - 14, x1 + 14, y0 - 14, y1 + 14]


# =============================================================================================== ice camp

def tent(cv, x0, y0, L=7, W=5, opening='N'):
    """A-frame canvas tent, open at one end, 4 tall inside the ridge."""
    g = top(cv, x0 + W // 2, y0 + L // 2)
    for j in range(L):
        for k in range(W // 2 + 1):
            z = g - 1 - k
            for x in (x0 + k, x0 + W - 1 - k):
                put(cv, x, y0 + j, z, 'tent')
        put(cv, x0 + W // 2, y0 + j, g - 1 - W // 2 - 1, 'tent')
    back = y0 + L - 1 if opening == 'N' else y0
    for k in range(W // 2 + 1):
        for x in range(x0 + k, x0 + W - k):
            put(cv, x, back, g - 1 - k, 'tent')
    return g


def ice_camp(cv, rep, cx, cy, rng):
    # ice shelf east of the skerry (sea cells only)
    n_ice = 0
    for x in range(cx + 6, cx + 30):
        for y in range(cy - 12, cy + 14):
            if top(cv, x, y) >= 63 and math.hypot((x - cx - 16) / 15, (y - cy) / 13) <= 1:
                box(cv, x, x, y, y, 62, 63, 'ice')
                n_ice += 1
    holes = []
    for (hx, hy) in ((cx + 12, cy - 4), (cx + 20, cy + 3), (cx + 15, cy + 8)):
        if cv.mat[hx, hy, 62] == cv.materials['ice']:
            cv.carve(hx, hx + 1, hy, hy + 1, 62, 62)
            holes.append((hx, hy))
            put(cv, hx + 3, hy, 61, 'log')                  # stool
            for z in range(58, 62):
                put(cv, hx + 2, hy - 1, z, 'mast')          # rod, standing in the ice
    tents = []
    for (tx, ty) in ((cx + 9, cy - 10), (cx + 18, cy - 8), (cx + 22, cy + 5)):
        if top(cv, tx + 2, ty + 3) >= 62:
            tent(cv, tx, ty)
            tents.append((tx, ty))
            cv.interiors.append([f'ice tent {len(tents)}', tx + 2, ty + 3, 62])
    rep['ice_camp'] = {'ice': n_ice, 'holes': holes, 'tents': tents, 'fire': (cx + 14, cy + 1, 61)}
    put(cv, cx + 14, cy + 1, 61, 'log')
    return [cx + 4, cx + 32, cy - 14, cy + 16]


# =============================================================================================== mailbox / sauna

def giant_mailbox(cv, rep, rng, x, y):
    g = top(cv, x + 2, y + 1)
    box(cv, x + 2, x + 3, y + 1, y + 2, g - 6, g - 1, 'post')
    for (a, b_) in ((x + 2, y + 1), (x + 3, y + 1), (x + 2, y + 2), (x + 3, y + 2)):
        col_down(cv, a, b_, g, 'post')
    box(cv, x, x + 5, y, y + 3, g - 11, g - 7, 'mail')
    cv.carve(x + 1, x + 4, y, y, g - 10, g - 9)              # slot
    box(cv, x + 6, x + 6, y + 1, y + 1, g - 13, g - 8, 'mast')
    box(cv, x + 6, x + 6, y + 1, y + 2, g - 13, g - 12, 'mail')     # flag
    n = 0
    for _ in range(40):                                      # letters spilling out of the slot and over the ground
        lx, ly = x + int(rng.integers(-4, 10)), y + int(rng.integers(-6, 3))
        gg = top(cv, lx, ly)
        if gg < 62 and abs(gg - g) <= 1 and not cv.solid[lx, ly, gg - 1]:
            put(cv, lx, ly, gg - 1, 'letter')
            n += 1
    for k in range(4):                                       # letters jammed in the slot (on the box face)
        put(cv, x + 1 + k, y, g - 9, 'letter')
    rep['mailbox_letters'] = n
    return [x - 5, x + 11, y - 7, y + 5]


def sauna_jump(cv, rep, x0, x1, y_end):
    """Jump tower at the end of the red sauna pier: platform 5 above the deck, a stair, a board over the sea."""
    deck = 60
    pz = deck - 5
    box(cv, x0, x1, y_end - 4, y_end, pz, pz, 'plank')
    for (a, b) in ((x0, y_end - 4), (x1, y_end - 4), (x0, y_end), (x1, y_end)):
        col_down(cv, a, b, pz + 1, 'post')
    straight_stair(cv, y_end - 10, x0, x1, deck, 5, 1, GC['stair'], 'stair', along='y')
    for k in range(1, 5):
        put(cv, (x0 + x1) // 2, y_end + k, pz, 'plank')
    rep['sauna_jump'] = {'platform_z': pz}
    return [x0 - 2, x1 + 2, y_end - 12, y_end + 6]


def chimney(cv, x, y, ztop, h=4):
    for z in range(ztop - h, ztop + 1):
        box(cv, x, x + 1, y, y + 1, z, z, 'stone')


# =============================================================================================== iceberg + tag

def iceberg_tag(cv, rep, S):
    T = S['tag']
    m = text_mask([T['text']])
    W, Hh = m.shape
    x0, y0, zp = T['x0'], T['y0'], T['z']
    px0, px1, py0, py1 = x0 - 2, x0 + W + 1, y0 - 2, y0 + Hh + 1
    ix, iy = (px0 + px1) // 2, (py0 + py1) // 2 - 6
    # iceberg: jagged ice mass in the sea under the plate
    rng = np.random.default_rng(7)
    peaks = [(ix, iy, 13, 20), (ix - 18, iy + 4, 10, 34), (ix + 20, iy - 6, 9, 38), (ix + 6, iy + 10, 8, 30)]
    for x in range(max(0, px0 - 6), min(511, px1 + 8)):
        for y in range(py0 - 26, 512):
            zbest = 64
            for (cx, cy, r, pz) in peaks:
                d = math.hypot(x - cx, (y - cy) * 1.2) / (r * 2.2)
                if d < 1:
                    z = int(round(pz + (62 - pz) * d ** 0.8 + rng.integers(0, 2)))
                    zbest = min(zbest, z)
            if zbest < 63 and top(cv, x, y) >= 63:
                box(cv, x, x, y, y, zbest, 63, 'iceberg')
    peak = (ix, iy, 20)
    # stalk from the main peak up to the plate, then the plate, then the letters (painted on it)
    sx, sy = ix, iy
    while top(cv, sx, sy) > 20 and sy < py0 + 3:
        sy += 1
    gtop = top(cv, sx, sy)
    for z in range(zp + 1, gtop):
        box(cv, sx, sx + 1, sy, sy + 1, z, z, 'iceberg')
    box(cv, px0, px1, py0, py1, zp, zp, 'iceberg')
    # the stalk must meet the plate: extend the plate down to the stalk if the stalk is outside it
    if not (py0 <= sy <= py1):
        box(cv, sx, sx + 1, min(sy, py0), max(sy, py1), zp, zp, 'iceberg')
    letters = []
    for (i, j) in zip(*np.nonzero(m)):
        letters.append((x0 + i, y0 + j, zp))
        cv.mat[x0 + i, y0 + j, zp] = cv.materials['tag']
        cv.rgb[x0 + i, y0 + j, zp] = GC['tag']
    rep['tag'] = {'plate': [px0, px1, py0, py1, zp], 'stalk': [sx, sy, zp + 1, gtop], 'letters': len(letters)}
    return [max(0, px0 - 8), min(511, px1 + 10), py0 - 30, 511]


# =============================================================================================== beach props

def beach_cells(cv, H):
    t = cv.tops()
    m = (t == H) & (t >= 60) & (t <= 62) & (cv.keep == 0)
    return m


def snowman(cv, rng, x, y):
    """Driftwood-and-buoy snowman: two snow balls, a buoy head (or buoy belly), driftwood arms, a net scarf.
    Every one gets three random details from: hat, pipe, lantern, scarf, buttons, sign."""
    g = top(cv, x, y)
    r1 = rng.uniform(2.2, 3.0)
    r2 = r1 * rng.uniform(0.62, 0.78)
    z1 = g - r1 + 0.3
    z2 = z1 - r1 - r2 + 0.8
    cv.ellipsoid(x, y, z1, r1, r1, r1, GC['snowman'], 'snowman')
    buoy_head = rng.random() < 0.6
    cv.ellipsoid(x, y, z2, r2, r2, r2, GC['buoy'] if not buoy_head else GC['snowman'],
                 'buoy' if not buoy_head else 'snowman')
    zh = int(round(z2 - r2))
    rh = 1.6
    cv.ellipsoid(x, y, zh - rh + 0.4, rh, rh, rh, GC['buoy'] if buoy_head else GC['snowman'],
                 'buoy' if buoy_head else 'snowman')
    zt = int(round(zh - 2 * rh))
    # driftwood arms (face-connected lines)
    za = int(round(z2))
    a = rng.uniform(0, math.pi)
    for side in (-1, 1):                                     # driftwood arms: face-connected from inside the body
        dx, dy = math.cos(a) * side, math.sin(a) * side
        L = int(rng.integers(4, 7))
        r0 = max(0, int(r2) - 1)
        p0 = (int(round(x + dx * r0)), int(round(y + dy * r0)), za)
        p1 = (int(round(x + dx * (r0 + L))), int(round(y + dy * (r0 + L))), za - int(rng.integers(1, 3)))
        for (ax_, ay_, az_) in line_points(*p0, *p1):
            put(cv, ax_, ay_, az_, 'log')
    det = veg.pick_details(rng, allow=('hat', 'pipe', 'lantern', 'scarf', 'buttons', 'sign'), n=3)
    if 'hat' in det:
        box(cv, x - 1, x + 1, y - 1, y + 1, zt, zt, 'roof')
        box(cv, x, x, y, y, zt - 2, zt - 1, 'roof')
    if 'scarf' in det:
        for k in range(-2, 3):
            put(cv, x + k, y + int(r2), za - int(r2) + 1, 'ribbon') if not cv.solid[x + k, y + int(r2), za - int(r2) + 1] else None
    if 'buttons' in det:
        for k in range(3):
            put(cv, x, y - int(r1) - 1 + 1, int(z1) - 1 + k, 'stone_dk')
    if 'sign' in det:
        col_down(cv, x + 4, y, g - 5, 'post')
        box(cv, x + 4, x + 6, y, y, g - 7, g - 5, 'plank')
    if 'pipe' in det:
        put(cv, x, y - 2, zh - 1, 'log')
    lantern = (x - 3, y, g - 1) if 'lantern' in det else None
    if lantern:
        put(cv, x - 3, y, g - 1, 'post')
    return det, lantern


def present_crate(cv, rng, x, y):
    g = top(cv, x, y)
    s = int(rng.integers(2, 5))
    h = int(rng.integers(2, 4))
    box(cv, x, x + s - 1, y, y + s - 1, g - h, g - 1, 'present')
    for k in range(s):                                       # ribbon cross
        cv.mat[x + k, y + s // 2, g - h] = cv.materials['ribbon']
        cv.mat[x + s // 2, y + k, g - h] = cv.materials['ribbon']
    return s


def scatter_beach(cv, rep, rng, S, n_snow=8, n_pres=24):
    b = beach_cells(cv, cv.H)
    xs, ys = np.nonzero(b)
    order = rng.permutation(len(xs))
    placed_s, placed_p, boxes = [], [], []
    lights = []

    def free(x, y, r):
        if not (4 <= x < 508 and 4 <= y < 508):
            return False
        tt = cv.tops()[x - r:x + r + 1, y - r:y + r + 1]
        if tt.max() > 62 or tt.max() - tt.min() > 1:
            return False
        if cv.keep[x - r:x + r + 1, y - r:y + r + 1].any():
            return False
        for (px, py) in placed_s + placed_p:
            if abs(px - x) < 12 and abs(py - y) < 12:
                return False
        return True
    T = cv.tops()
    for i in order:
        x, y = int(xs[i]), int(ys[i])
        if len(placed_s) < n_snow and free(x, y, 2) and (x < 256) == (len(placed_s) % 2 == 0):
            det, lant = snowman(cv, rng, x, y)
            placed_s.append((x, y))
            boxes.append([x - 8, x + 8, y - 8, y + 8])
            if lant:
                lights.append(lant)
        elif len(placed_p) < n_pres and free(x, y, 3):
            present_crate(cv, rng, x, y)
            placed_p.append((x, y))
            boxes.append([x - 1, x + 5, y - 1, y + 5])
        if len(placed_s) >= n_snow and len(placed_p) >= n_pres:
            break
    rep['snowmen'] = placed_s
    rep['presents'] = placed_p
    rep['snowman_lanterns'] = lights
    return boxes


# =============================================================================================== driver

def build(cv, rep, S, rng, art=True):
    boxes = []
    lx, ly = S['lighthouse']
    boxes.append(lighthouse(cv, rep, lx, ly))
    gx, gy = S['goat']
    boxes.append(yule_goat(cv, rep, gx, gy, face=1))
    cx, cy = S['chapel']
    boxes.append(chapel(cv, rep, cx, cy))
    ix, iy = S['ice_camp']
    boxes.append(ice_camp(cv, rep, ix, iy, rng))
    # spruce on the islet outcrop (kit conifer: three random details) + star
    sx, sy, sg, sh = S['spruce']
    g = top(cv, sx, sy)
    pal = veg.palette_family([(36, 70, 52), (48, 88, 60), (60, 98, 66), (40, 78, 70)], n=8)
    info = veg.conifer(cv, rng, sx, sy, g, pal, h=sh, details=('ribbon', 'lantern', 'roots'), clear=3)
    tip = g - 2 - sh
    rep['spruce'] = {'g': g, 'tip': tip, 'info': info}
    boxes.append([sx - 12, sx + 12, sy - 12, sy + 12])
    # post office (Blue) giant mailbox, sauna (Red) jump tower + chimney
    p = S['post_office']
    boxes.append(giant_mailbox(cv, rep, rng, p[1] + 3, p[2] - 2))
    pp = S['post_pier']
    ex0, ex1 = 512 - pp['x'][1], 512 - pp['x'][0]
    boxes.append(sauna_jump(cv, rep, ex0, ex1, pp['y'][1]))
    sx0 = 512 - p[1]
    chimney(cv, sx0 + 3, p[2] + 4, top(cv, sx0 + 3, p[2] + 4) - 1)
    boxes.append([sx0 + 1, sx0 + 6, p[2] + 2, p[2] + 7])
    boxes.append(iceberg_tag(cv, rep, S))
    boxes += scatter_beach(cv, rep, rng, S)
    out = {'boxes': boxes, 'lighthouse': rep.get('lighthouse', {}).get('g'), 'chapel': rep.get('chapel'),
           'goat': rep.get('goat'), 'ice_camp': {k: v for k, v in rep.get('ice_camp', {}).items() if k != 'holes'},
           'spruce': {'tip': rep['spruce']['tip']}, 'tag': rep.get('tag'), 'snowmen': len(rep['snowmen']),
           'presents': len(rep['presents'])}
    if art:
        import yh_sky
        out['sky'] = yh_sky.place_all(cv, rep, S, rng)
    return out
