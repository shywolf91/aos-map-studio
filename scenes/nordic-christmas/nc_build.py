"""Hrafnfjord Yule: building blocks (graybox geometry). Real rooms, doors, windows, stairs to every floor/perch.

z conventions (kit): z grows downward; a floor z is the solid voxel a player stands on, air at z-1..z-3.
Roofs: wall top row is `ze`; the roof voxel over overhang distance t is at z = ze - t (pitch 1), 2 thick so every
step has face contact. Stairs come from aosmap.kit.structures (straight / switchback), drawn after the slabs.
"""
from __future__ import annotations

import math

import numpy as np

from aosmap.kit import structures
from nc_world import FC, boxm, put, reg, ground_med

STAIR = FC['stair']


# ------------------------------------------------------------------ ground preparation
def pad(cv, x0, x1, y0, y1, z, name='track', ring=6, clear_up=30):
    """Flat floor z over the box, then blend a ring so every step to the old ground is <= 1."""
    X0, X1, Y0, Y1 = max(0, x0 - ring), min(511, x1 + ring), max(0, y0 - ring), min(511, y1 + ring)
    for x in range(X0, X1 + 1):
        for y in range(Y0, Y1 + 1):
            d = max(x0 - x, x - x1, y0 - y, y - y1, 0)
            old = int(cv.H[x, y])
            if cv.mat[x, y, old] == cv.materials.get('ice', -1) and d > 0:
                continue                                   # never raise ice beside a footprint
            new = z if d == 0 else int(np.clip(old, z - d, z + d))
            if new == old and d > 0:
                continue
            cv.box(x, x, y, y, max(0, new - clear_up), new - 1, air=True)
            if new < old:
                boxm(cv, x, x, y, y, new, old, name if d == 0 else 'ground', 'ground')
            elif d == 0:
                boxm(cv, x, x, y, y, new, new, name, 'ground')
            cv.H[x, y] = new


# ------------------------------------------------------------------ roofs
def gable_roof(cv, x0, x1, y0, y1, ze, along='x', ov=1, pitch=1, gable_ends=True, wall='wall', roof='roof',
               ztop_min=1):
    """Gable roof over walls x0..x1, y0..y1 whose top wall row is ze. along = ridge direction. Returns ridge z."""
    rx0, rx1, ry0, ry1 = x0 - ov, x1 + ov, y0 - ov, y1 + ov
    lo, hi = (ry0, ry1) if along == 'x' else (rx0, rx1)
    tmax = (hi - lo) // 2
    zr = ze
    for x in range(rx0, rx1 + 1):
        for y in range(ry0, ry1 + 1):
            u = y if along == 'x' else x
            t = min(u - lo, hi - u)
            z = max(ztop_min, ze - t * pitch)
            zr = min(zr, z)
            nm = 'ridge' if t >= tmax else roof
            for k in range(0, (pitch + 1) if t > 0 else 1):
                put(cv, x, y, z + k, nm, 'roof')
    if gable_ends:
        ends = (x0, x1) if along == 'x' else (y0, y1)
        a, b = (y0, y1) if along == 'x' else (x0, x1)
        for e in ends:
            for u in range(a, b + 1):
                t = min(u - lo, hi - u)
                z = max(ztop_min, ze - t * pitch)
                for zz in range(z + pitch + 1, ze):
                    if along == 'x':
                        put(cv, e, u, zz, wall, 'building')
                    else:
                        put(cv, u, e, zz, wall, 'building')
    return zr


def pyramid_roof(cv, x0, x1, y0, y1, ze, ov=1, pitch=1, roof='roof', ztop_min=1):
    rx0, rx1, ry0, ry1 = x0 - ov, x1 + ov, y0 - ov, y1 + ov
    zr = ze
    for x in range(rx0, rx1 + 1):
        for y in range(ry0, ry1 + 1):
            t = min(x - rx0, rx1 - x, y - ry0, ry1 - y)
            z = max(ztop_min, ze - t * pitch)
            zr = min(zr, z)
            for k in range(0, (pitch + 1) if t > 0 else 1):
                put(cv, x, y, z + k, roof, 'roof')
    return zr


# ------------------------------------------------------------------ openings
def door(cv, side, box, zf, pos, w=3, h=4):
    x0, x1, y0, y1 = box
    if side in 'NS':
        yy = y0 if side == 'N' else y1
        cv.carve(pos, pos + w - 1, yy, yy, zf - h, zf - 1)
        boxm(cv, pos - 1, pos - 1, yy, yy, zf - h - 1, zf - 1, 'door_trim', 'building')
        boxm(cv, pos + w, pos + w, yy, yy, zf - h - 1, zf - 1, 'door_trim', 'building')
        boxm(cv, pos, pos + w - 1, yy, yy, zf - h - 1, zf - h - 1, 'door_trim', 'building')
    else:
        xx = x0 if side == 'W' else x1
        cv.carve(xx, xx, pos, pos + w - 1, zf - h, zf - 1)
        boxm(cv, xx, xx, pos - 1, pos - 1, zf - h - 1, zf - 1, 'door_trim', 'building')
        boxm(cv, xx, xx, pos + w, pos + w, zf - h - 1, zf - 1, 'door_trim', 'building')
        boxm(cv, xx, xx, pos, pos + w - 1, zf - h - 1, zf - h - 1, 'door_trim', 'building')


def windows(cv, box, zf, avoid=(), every=5, sill=2, h=2):
    x0, x1, y0, y1 = box
    for x in range(x0 + 2, x1 - 2, every):
        for yy in (y0, y1):
            if any(abs(x - a) <= 3 and abs(yy - b) <= 1 for a, b in avoid):
                continue
            cv.carve(x, x + 1, yy, yy, zf - sill - h + 1, zf - sill)
    for y in range(y0 + 2, y1 - 2, every):
        for xx in (x0, x1):
            if any(abs(y - b) <= 3 and abs(xx - a) <= 1 for a, b in avoid):
                continue
            cv.carve(xx, xx, y, y + 1, zf - sill - h + 1, zf - sill)


# ------------------------------------------------------------------ generic Nordic house
def house(cv, name, role, box, zf, wall_h, along='x', doors=(), lofts=(), ov=1, open_end=None, register=True,
          window_every=5, pitch=1, ring=6):
    """Timber house: walls, floor, gable roof (open to the rafters), doors, windows, optional lofts.
    doors: [(side, pos, w)]; lofts: [(lx0, lx1, ly0, ly1, z_loft, stair)] with stair = (x0, y0, y1, dx, along)
    rising from zf to z_loft. open_end: 'E'/'W'/'N'/'S' gable end left open (boat sheds).
    Records every floor in cv.interiors (free spots) and registers the structure."""
    x0, x1, y0, y1 = box
    pad(cv, x0 - 1, x1 + 1, y0 - 1, y1 + 1, zf, ring=ring)
    ze = zf - wall_h
    boxm(cv, x0, x1, y0, y1, ze, zf - 1, 'wall', 'building')
    cv.carve(x0 + 1, x1 - 1, y0 + 1, y1 - 1, ze, zf - 1)
    boxm(cv, x0 + 1, x1 - 1, y0 + 1, y1 - 1, zf, zf, 'floor', 'building')
    for (cx, cy) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        boxm(cv, cx, cx, cy, cy, ze, zf - 1, 'post', 'building')
    zr = gable_roof(cv, x0, x1, y0, y1, ze, along, ov=ov, pitch=pitch)
    avoid = []
    for (side, pos, w) in doors:
        door(cv, side, box, zf, pos, w)
        avoid.append({'N': (pos, y0), 'S': (pos, y1), 'W': (x0, pos), 'E': (x1, pos)}[side])
    if open_end:
        if open_end in 'EW':
            xx = x1 if open_end == 'E' else x0
            cv.carve(xx, xx, y0 + 1, y1 - 1, ze - 1, zf - 1)
        else:
            yy = y1 if open_end == 'S' else y0
            cv.carve(x0 + 1, x1 - 1, yy, yy, ze - 1, zf - 1)
    if window_every:
        windows(cv, box, zf, avoid, window_every)
    for (lx0, lx1, ly0, ly1, zl, st) in lofts:
        boxm(cv, lx0, lx1, ly0, ly1, zl, zl, 'floor', 'building')
        windows(cv, box, zl, avoid=(), every=window_every or 5)
    for (lx0, lx1, ly0, ly1, zl, st) in lofts:           # stairs after slabs (cut-outs open the slab)
        sx, sy0, sy1, dx, al = st
        structures.straight_stair(cv, sx, sy0, sy1, zf, zf - zl, dx, STAIR, 'stair', along=al)
    if register:
        reg(name, (x0 - ov, x1 + ov, y0 - ov, y1 + ov), role)
    cv.no_prop(x0 - 4, x1 + 4, y0 - 4, y1 + 4)
    return {'ze': ze, 'ridge': zr, 'zf': zf}


def stairwell(cv, X, Y, z_deck, flight=5, width=2):
    """Open the top deck over a kit switchback's whole footprint (call BEFORE the stair, which then adds its top
    landing): without it the deck sits < 3 above the lower flights near the top and blocks them."""
    cv.carve(X, X + flight + 1, Y, Y + 2 * width, z_deck, z_deck)


def interior(cv, name, x, y, z):
    cv.interiors.append([name, int(x), int(y), int(z)])


# ------------------------------------------------------------------ furniture and small props
def table(cv, x0, x1, y0, y1, zf):
    boxm(cv, x0, x1, y0, y1, zf - 1, zf - 1, 'furniture', 'furniture')


def bench(cv, x0, x1, y0, y1, zf):
    boxm(cv, x0, x1, y0, y1, zf - 1, zf - 1, 'furniture', 'furniture')


def hearth(cv, x0, x1, y0, y1, zf):
    boxm(cv, x0, x1, y0, y1, zf - 1, zf - 1, 'stone', 'furniture')


def yard_props(cv, rng, box, zf, n, keepout=(), name='prop', h=1, margin=(3, 9)):
    """n low props (sleds, logs, troughs, benches) around a building, on its yard ground, outside door aprons.
    h = 1 by default so they count as yard dressing but not as zone-rule objects (centre median rule)."""
    x0, x1, y0, y1 = box
    placed, tries = 0, 0
    pts = []
    while placed < n and tries < n * 60:
        tries += 1
        side = rng.integers(4)
        off = int(rng.integers(margin[0], margin[1] + 1))
        if side == 0:
            x, y = int(rng.integers(x0, x1 + 1)), y0 - off
        elif side == 1:
            x, y = int(rng.integers(x0, x1 + 1)), y1 + off
        elif side == 2:
            x, y = x0 - off, int(rng.integers(y0, y1 + 1))
        else:
            x, y = x1 + off, int(rng.integers(y0, y1 + 1))
        L = int(rng.integers(2, 5))
        ax = rng.integers(2)
        xa, xb, ya, yb = (x, x + L - 1, y, y + 1) if ax == 0 else (x, x + 1, y, y + L - 1)
        if xa < 1 or ya < 1 or xb > 510 or yb > 510:
            continue
        if any(not (xb < k[0] - 1 or xa > k[1] + 1 or yb < k[2] - 1 or ya > k[3] + 1) for k in keepout):
            continue
        if any(abs(xa - a) < 4 and abs(ya - b) < 4 for a, b in pts):
            continue
        sub = cv.H[xa:xb + 1, ya:yb + 1]
        if sub.max() != sub.min() or abs(int(sub.min()) - zf) > 1:
            continue
        if cv.mat[xa, ya, int(sub.min())] != cv.materials.get('ground'):
            continue
        g = int(sub.min())
        boxm(cv, xa, xb, ya, yb, g - h, g - 1, name, 'prop')
        pts.append((xa, ya))
        placed += 1
    return placed


def haystack(cv, cx, cy, h=4, r=2.5, name='hay'):
    g = int(cv.H[int(cx), int(cy)])
    cv.cone(cx + 0.5, cy + 0.5, r, g - 1, g - h, FC[name], name)


def fence(cv, x0, x1, y0, y1, h=2, name='post'):
    g = ground_med(cv, x0, x1, y0, y1)
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            gg = int(cv.H[x, y])
            boxm(cv, x, x, y, y, gg - h, gg - 1, name, 'prop')
    return g


# ------------------------------------------------------------------ tower with switchback stair
def tower(cv, name, box, zf, rise, roof='pyramid', parapet=True, doors=(), canopy=4, register=True, role='tower'):
    """Square tower box (>= 9 x 9): walls zf-1 .. zf-rise, deck floor at zf-rise, switchback stair inside (rise a
    multiple of 5: a short last flight puts the kit's top landing < 3 above the flight below),
    parapet, then (optional) canopy posts + pyramid roof. Returns deck z."""
    x0, x1, y0, y1 = box
    pad(cv, x0 - 1, x1 + 1, y0 - 1, y1 + 1, zf)
    zt = zf - rise
    boxm(cv, x0, x1, y0, y1, zt, zf - 1, 'stone', 'building')
    cv.carve(x0 + 1, x1 - 1, y0 + 1, y1 - 1, zt + 1, zf - 1)
    boxm(cv, x0 + 1, x1 - 1, y0 + 1, y1 - 1, zf, zf, 'floor', 'building')
    for (side, pos, w) in doors:
        door(cv, side, box, zf, pos, w)
    # slit windows every 4 rows
    for z in range(zf - 6, zt + 2, -5):
        for x in range(x0 + 3, x1 - 2, 4):
            cv.carve(x, x, y0, y0, z - 1, z)
            cv.carve(x, x, y1, y1, z - 1, z)
        for y in range(y0 + 3, y1 - 2, 4):
            cv.carve(x0, x0, y, y, z - 1, z)
            cv.carve(x1, x1, y, y, z - 1, z)
    if parapet:
        for x in range(x0, x1 + 1):
            for y in (y0, y1):
                put(cv, x, y, zt - 1, 'stone', 'building')
                if (x - x0) % 2 == 0:
                    put(cv, x, y, zt - 2, 'stone', 'building')
        for y in range(y0, y1 + 1):
            for x in (x0, x1):
                put(cv, x, y, zt - 1, 'stone', 'building')
                if (y - y0) % 2 == 0:
                    put(cv, x, y, zt - 2, 'stone', 'building')
    top = zt - 2
    if roof == 'pyramid' and canopy:
        for (cx, cy) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
            boxm(cv, cx, cx, cy, cy, zt - canopy, zt - 1, 'post', 'building')
        top = pyramid_roof(cv, x0, x1, y0, y1, zt - canopy - 1, ov=1)
    # stair last: its cut-outs open the deck
    stairwell(cv, x0 + 1, y0 + 1, zt)
    structures.switchback_stair(cv, x0 + 1, y0 + 1, zf, rise, flight=5, width=2, c=STAIR, mat='stair')
    if register:
        reg(name, (x0 - 1, x1 + 1, y0 - 1, y1 + 1), role)
    cv.no_prop(x0 - 4, x1 + 4, y0 - 4, y1 + 4)
    return zt, top


# ------------------------------------------------------------------ longship (centred on x 256, authored x <= 255)
def longship(cv, name, cy, tilt=0, mast_top=20, keel=44, gz0=37, prow=28, awn=(240, 255)):
    xs = range(232, 256)
    hwmax = 5

    def hw(x):
        u = (256 - x) / 24.0
        return max(1, int(round(hwmax * math.sqrt(max(0.0, 1 - u ** 2.4)))))

    def gz(x):
        u = (256 - x) / 24.0
        return gz0 - int(round(3 * u ** 3))

    def wz(x, z):
        g = gz(x)
        f = (z - g) / max(keel - g, 1)
        return max(0, int(round(hw(x) * (1 - 0.6 * f * f))))

    def zz(y, z):
        return z + (tilt if y > cy else 0)

    for x in xs:
        g = gz(x)
        for z in range(g, keel + 1):
            a, b = wz(x, z), wz(x, min(z + 1, keel))
            for w in range(min(a, b), max(a, b) + 1):
                for y in (cy - w, cy + w):
                    put(cv, x, y, zz(y, z), 'hull', 'hull')
            if z >= 41:                                         # deck at 41, solid below (frozen in)
                for y in range(cy - a, cy + a + 1):
                    put(cv, x, y, zz(y, z), 'deck' if z == 41 else 'hull', 'hull')
        for z in range(g, 41):                                  # air above the deck inside the hull
            a = wz(x, z)
            for y in range(cy - a + 1, cy + a):
                cv.clear(x, y, zz(y, z))
        if x % 3 == 0 and x > 236:                              # oar ports
            for y in (cy - wz(x, g + 1), cy + wz(x, g + 1)):
                cv.clear(x, y, zz(y, g + 1))
    # benches (thwarts) 1 tall across the deck
    for x in range(238, 254, 4):
        for y in range(cy - wz(x, 40) + 1, cy + wz(x, 40)):
            put(cv, x, y, zz(y, 40), 'furniture', 'hull')
    # stem post + dragon head at x 232..233
    for z in range(prow, gz(232) + 1):
        put(cv, 232, cy, z, 'hull', 'hull')
        put(cv, 233, cy, z, 'hull', 'hull')
    boxm(cv, 230, 233, cy - 1, cy + 1, prow - 2, prow, 'hull', 'hull')
    boxm(cv, 229, 229, cy, cy, prow - 1, prow, 'hull', 'hull')
    # boarding gap amidships (x 249..255 both sides) with outside steps 42 -> deck 41
    for x in range(249, 256):
        for side in (-1, 1):
            a = hw(x)
            for w in range(wz(x, 41), a + 1):
                y = cy + side * w
                for z in range(gz(x), 41):
                    cv.clear(x, y, zz(y, z))
                put(cv, x, y, zz(y, 41), 'deck', 'hull')
            y = cy + side * (a + 1)
            boxm(cv, x, x, y, y, zz(y, 42), 43, 'deck', 'hull')
            for z in range(zz(y, 42) - 4, zz(y, 42)):
                cv.clear(x, y, z)
    # mast + yard
    if mast_top:
        for z in range(mast_top, 41):
            put(cv, 255, cy, zz(cy, z), 'mast', 'hull')
        if mast_top <= 24:
            for y in range(cy - 6, cy + 7):
                put(cv, 255, y, mast_top + 2, 'mast', 'hull')
    # awning: ridge tent over the deck, poles at its ends
    a0, a1 = awn
    for x in range(a0, a1 + 1):
        for d in range(0, 4):
            z = gz0 - 4 + d
            for y in {cy - d, cy + d}:
                put(cv, x, y, zz(y, z), 'canvas', 'hull')
                put(cv, x, y, zz(y, z) + 1, 'canvas', 'hull') if d < 3 else None
    for x in (a0,):
        for z in range(gz0 - 4, 41):
            put(cv, x, cy, z, 'mast', 'hull')
    reg(name, (229, 512 - 229, cy - hwmax - 2, cy + hwmax + 2), 'vessel')
    cv.interiors.append([name + ' deck', 244, cy + 2, 41 + tilt])


# ------------------------------------------------------------------ Raven Gate (centred on x 256)
def raven_gate(cv, spec):
    rg = spec
    (lx0, lx1, ly0, ly1) = rg['legs'][0]
    zf = 40
    zc = rg['crown_floor_z']
    zi = zc + 20                       # leg floor 2 above the ground: switchback rise 20 = 4 full flights
    pad(cv, lx0, lx1, ly0, ly1, zf, ring=0)
    boxm(cv, lx0, lx1, ly0, ly1, zc, zf - 1, 'stone', 'building')
    cv.carve(lx0 + 1, lx1 - 1, ly0 + 1, ly1 - 1, zc + 1, zi - 1)
    boxm(cv, lx0 + 1, lx1 - 1, ly0 + 1, ly1 - 1, zi, zf, 'floor', 'building')
    for side, yo in (('N', ly0 - 1), ('S', ly1 + 1)):
        door(cv, side, (lx0, lx1, ly0, ly1), zi, lx0 + 4, 3)
        boxm(cv, lx0 + 4, lx0 + 6, yo, yo, zi + 1, zf, 'stone', 'building')     # outside step 39
        cv.carve(lx0 + 4, lx0 + 6, yo, yo, zi - 3, zi)
    for z in range(zf - 7, zc + 3, -6):                          # slit windows
        for y in range(ly0 + 3, ly1 - 2, 4):
            cv.carve(lx0, lx0, y, y, z - 1, z)
    # arch body + crown deck, x lx1+1 .. 255, y 98..106
    ya, yb = 98, 106
    for x in range(lx1 + 1, 256):
        u = (256 - x) / 23.0
        soff = int(round(41 - 11 * math.sqrt(max(0.0, 1 - u * u))))
        boxm(cv, x, x, ya, yb, zc, soff, 'stone', 'building')
    # crown deck over the leg too + merlons on the long sides (not on the leg's inner face)
    boxm(cv, lx0, 255, ya, yb, zc, zc, 'stone', 'building')
    for x in range(lx0, 256):
        for y in (ya, yb):
            put(cv, x, y, zc - 1, 'stone', 'building')
            if (x - lx0) % 3 != 2:
                put(cv, x, y, zc - 2, 'stone', 'building')
                put(cv, x, y, zc - 3, 'stone', 'building')
    for y in range(ly0, ly1 + 1):                                 # leg outer parapet
        put(cv, lx0, y, zc - 1, 'stone', 'building')
        if (y - ly0) % 3 != 2:
            put(cv, lx0, y, zc - 2, 'stone', 'building')
            put(cv, lx0, y, zc - 3, 'stone', 'building')
    for x in range(lx0, lx1 + 1):
        for y in (ly0, ly1):
            put(cv, x, y, zc - 1, 'stone', 'building')
    # leg turret cap (massing): small pyramid over the outer half of the leg
    pyramid_roof(cv, lx0, lx0 + 4, ly1 - 4, ly1, zc - 4, ov=0)
    for (cx, cy) in ((lx0, ly1 - 4), (lx0 + 4, ly1 - 4), (lx0, ly1), (lx0 + 4, ly1)):
        boxm(cv, cx, cx, cy, cy, zc - 3, zc - 1, 'stone', 'building')
    stairwell(cv, lx0 + 2, ly0 + 3, zc)
    structures.switchback_stair(cv, lx0 + 2, ly0 + 3, zi, zi - zc, flight=5, width=2, c=STAIR, mat='stair')
    reg('Raven Gate', (lx0, 512 - lx0, ly0, ly1), 'tower')
    interior(cv, 'Raven Gate leg', lx0 + 5, ly1 - 2, zi)
    interior(cv, 'Raven Gate crown', 245, 102, zc)
    cv.no_prop(lx0 - 4, 255, ly0 - 4, ly1 + 4)


# ------------------------------------------------------------------ Thing-Rock isle with barrow room
def thing_rock(cv, spec):
    c = spec
    cx, cy, R = c['cx'], c['cy'], c['r']
    ztop = c['top_z']
    for x in range(cx - R, 256):
        for y in range(cy - R, cy + R + 1):
            r = math.hypot(x - cx, y - cy)
            if r > R:
                continue
            t = ztop + int(10 * (r / R) ** 1.6)
            if t < 43:
                boxm(cv, x, x, y, y, t, 42, 'rock', 'rock')
    b = c['barrow_room']
    (bx0, bx1, by0, by1) = b['box']
    za, zb = b['air']
    cv.carve(bx0 + 1, 255, by0 + 1, by1 - 1, za, zb)
    for (x0, x1, y0, y1) in ((254, 255, cy - R - 1, by0), (254, 255, by1, cy + R + 1), (cx - R - 1, bx0, 254, 258)):
        cv.carve(x0, x1, y0, y1, za, zb)
    # stone posts + lintels at the four doorways
    for y in (by0, by1):
        boxm(cv, 253, 253, y, y, za - 1, zb, 'stone', 'building')
    boxm(cv, bx0, bx0, 253, 253, za - 1, zb, 'stone', 'building')
    boxm(cv, bx0, bx0, 259, 259, za - 1, zb, 'stone', 'building')
    # barrow furniture: stone benches and a grave-goods chest (1 tall)
    bench(cv, bx0 + 2, bx0 + 2, by0 + 3, by0 + 5, 43)
    bench(cv, bx0 + 2, bx0 + 2, by1 - 5, by1 - 3, 43)
    table(cv, 252, 255, 255, 257, 43)
    # dolmen portals: lintels over the four doorway mouths and two diagonal niches (west half)
    for (y0, y1) in ((cy - R - 2, cy - R + 1), (cy + R - 1, cy + R + 2)):          # N and S mouths
        boxm(cv, 253, 255, y0, y1, za - 1, za - 1, 'stone', 'building')
        boxm(cv, 253, 253, y0, y1, za, zb, 'stone', 'building')
        cv.carve(254, 255, y0, y1, za, zb)
    x0, x1 = cx - R - 2, cx - R + 1                                                # W mouth
    boxm(cv, x0, x1, 253, 259, za - 1, za - 1, 'stone', 'building')
    boxm(cv, x0, x1, 253, 253, za, zb, 'stone', 'building')
    boxm(cv, x0, x1, 259, 259, za, zb, 'stone', 'building')
    cv.carve(x0, x1, 254, 258, za, zb)
    for (x0, y0) in ((241, 241), (241, 267)):
        boxm(cv, x0, x0 + 4, y0, y0 + 4, za, za, 'stone', 'building')
        for (px, py) in ((x0, y0), (x0 + 4, y0), (x0, y0 + 4), (x0 + 4, y0 + 4)):
            boxm(cv, px, px, py, py, za + 1, zb, 'stone', 'building')
        cv.carve(x0 + 1, x0 + 3, y0 + 1, y0 + 3, za + 1, zb)
    # offering stones on the ice around the isle (1-2 tall)
    for k, ang in enumerate((100, 125, 150, 175, 200, 225, 250)):
        a = math.radians(ang)
        sx, sy = int(round(cx + 21 * math.cos(a))), int(round(cy + 21 * math.sin(a)))
        if sx <= 254:
            boxm(cv, sx, sx + 1, sy, sy + 1, 42 - (k % 2), 42, 'rune', 'stone')
    ls = c['lawspeaker_rock']
    lx0, lx1, ly0, ly1 = ls['box']
    boxm(cv, lx0, 255, ly0, ly1, ls['top_z'], ztop, 'rune', 'rock')
    reg('Thing-Rock barrow', (cx - R, 512 - (cx - R), cy - R, cy + R), 'ruin')
    interior(cv, 'Thing-Rock barrow room', bx0 + 4, cy, 43)


# ------------------------------------------------------------------ landmarks
def yule_pyre(cv, holm, pyre):
    cx, cy = 256, (holm['box'][2] + holm['box'][3]) // 2
    zb = holm['top_z']
    for L in range(0, 16):
        s = 8 - L // 2
        z = zb - 1 - L
        if L % 2 == 0:
            for x in range(cx - s - 1, 256):                 # ends overhang 1: face contact with the layer below
                if L < 4 and x >= 254:
                    continue                                 # walk-in gap (5 wide with the mirror), 4 tall
                put(cv, x, cy - s, z, 'log', 'pyre')
                put(cv, x, cy + s, z, 'log', 'pyre')
        else:
            for y in range(cy - s - 1, cy + s + 2):
                if L < 4 and abs(y - cy) <= 2:
                    continue
                put(cv, cx - s, y, z, 'log', 'pyre')
    boxm(cv, 254, 255, cy - 1, cy + 1, zb - 1, zb - 1, 'fire', 'pyre')
    # log-bench ring r 13 with four gaps
    for x in range(cx - 14, 256):
        for y in range(cy - 14, cy + 15):
            r = math.hypot(x - cx, y - cy)
            if 12.5 <= r <= 13.5 and abs(y - cy) > 3 and abs(x - cx) > 3:
                put(cv, x, y, zb - 1, 'log', 'pyre')


def rune_ring(cv, holm, ring):
    cx, cy, R = ring['cx'], ring['cy'], ring['r']
    zb = holm['top_z']
    for x in range(cx - R - 2, 256):
        for y in range(cy - R - 2, cy + R + 3):
            r = math.hypot(x - cx, y - cy)
            if R - 1 <= r <= R + 1 and abs(x - cx) > 3 and abs(y - cy) > 3:
                boxm(cv, x, x, y, y, zb - 2, 42, 'stone', 'kerb')
    hs = [6, 8, 9, 7, 9, 6]
    for k, ang in enumerate((15, 45, 75, 105, 135, 165, 195, 225, 255, 285, 315, 345)):
        a = math.radians(ang)
        sx, sy = cx + R * math.cos(a), cy + R * math.sin(a)
        if sx >= 255.5:
            continue
        h = hs[k % 6]
        x0, y0 = int(round(sx)) - 1, int(round(sy)) - 1
        boxm(cv, x0, min(x0 + 1, 255), y0, y0 + 1, zb - h, 42, 'rune', 'stone')
    boxm(cv, 253, 255, cy - 1, cy + 1, zb - 1, zb - 1, 'stone', 'altar')


def sleipnir(cv, s):
    cy = 450
    cv.ellipsoid(256, cy, 34, 4.4, 8, 3, FC['straw'], 'sleipnir')
    for x in range(257, 262):                                  # keep authored half only (mirror rebuilds east)
        cv.box(x, x, cy - 9, cy + 9, 30, 38, air=True)
    boxm(cv, 254, 255, 439, 443, 29, 33, 'straw', 'sleipnir')  # neck
    boxm(cv, 254, 255, 435, 440, 29, 31, 'log', 'sleipnir')    # head
    for y in (443, 446, 453, 456):                             # four west legs (eight with the mirror)
        boxm(cv, 253, 254, y, y, 37, 42, 'log', 'sleipnir')
    boxm(cv, 255, 255, 459, 461, 33, 36, 'straw', 'sleipnir')   # tail
