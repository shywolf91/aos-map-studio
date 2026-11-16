"""Northgale Freighter geometry (graybox + every voxel; the art pass only recolours).

build_west(S, veg_seed) -> cv, rep     sea, islets, hull core, decks, holds, access, props, vegetation (west half)
ends(cv, S, rep)                       after the mirror: raked bow + forecastle + foremast (west), bridge, funnel,
                                       smoke, lifeboats, poop deck (east) - one-offs in the cosmetic boxes
sky(cv, S)                             opt-in floating gulls and clouds (owner asked for sky decor)
"""
from __future__ import annotations

import math

import numpy as np

from aosmap.kit import Canvas, noise, structures, veg
from aosmap.kit.color import shade

# ---------------------------------------------------------------------- base palette (night grade in nf_art)
SEA = (60, 88, 108)
HULL = (124, 38, 40)
HULLFILL = (96, 92, 92)
BULWARK = (196, 192, 184)
DECK = (72, 118, 86)
GANGWAY = (96, 112, 104)
HATCH = (84, 130, 96)
SUPER = (200, 200, 194)
STEEL = (118, 122, 128)
DARK_STEEL = (74, 78, 86)
STAIR = (150, 154, 150)
TARP = (64, 84, 116)
CRATE = (150, 116, 76)
YELLOW = (204, 168, 52)
ORANGE = (212, 112, 40)
FLOOR_HOLD = (110, 112, 104)
ROCK = (110, 112, 118)
MOSS = (84, 102, 70)
SAND = (148, 138, 114)
PLANK = (122, 96, 70)
CONTAINER = {'rust': (150, 70, 48), 'teal': (52, 112, 116), 'steel': (78, 98, 136), 'mustard': (176, 140, 56),
             'grey': (120, 124, 128)}
LAMP = (255, 175, 95)
LAMP_W = (255, 255, 255)
LAMP_Y = (255, 255, 95)
LAMP_G = (95, 255, 95)
LAMP_R = (255, 95, 95)


def vcol(base, amt=0.08, salt=0):
    b = np.array(base, float)

    def f(xs, ys, zs):
        n = noise.hash3(xs, ys, zs, salt)
        return np.clip(b[None, :] * (1 - amt / 2 + amt * np.asarray(n))[:, None], 0, 255).astype(np.uint8)
    return f


def ym(y0, y1):
    return 512 - y1, 512 - y0


def surf_top(cv, x0, x1, y0, y1):
    """Highest surface (smallest z) over a footprint: an object placed there sits on it."""
    t = np.argmax(cv.solid[x0:x1 + 1, y0:y1 + 1], axis=2)
    return int(t.min())


# ---------------------------------------------------------------------- props
def container(cv, x0, y0, g, along, L, levels, colour, open_end=None, mat='container'):
    """ISO container(s) 5 wide x 5 tall, stacked `levels` high, bottom on surface z g (the voxel below them).
    open_end 'W'/'E'/'N'/'S': a hollow box with the doors open (a real hiding place)."""
    base = np.array(CONTAINER[colour], float)
    x1, y1 = (x0 + L - 1, y0 + 4) if along == 'x' else (x0 + 4, y0 + L - 1)
    for k in range(levels):
        zb = g - 1 - 5 * k
        zt = zb - 4
        b = base * (0.92 + 0.12 * ((x0 * 7 + y0 * 3 + k * 5) % 5) / 4)

        def c(xs, ys, zs, b=b):
            pos = xs if along == 'x' else ys
            f = np.where(pos % 2 == 0, 1.0, 0.94)
            end = (xs == x0) | (xs == x1) if along == 'x' else (ys == y0) | (ys == y1)
            f = np.where(end, 0.80, f)
            f = np.where(zs == zt, f * 1.06, f)
            f = np.where(zs == zb, f * 0.86, f)
            return np.clip(b[None, :] * f[:, None], 0, 255).astype(np.uint8)
        cv.box(x0, x1, y0, y1, zt, zb, c, mat)
        if open_end and k == 0:
            cv.carve(x0 + 1, x1 - 1, y0 + 1, y1 - 1, zt + 1, zb - 1)
            if open_end == 'W':
                cv.carve(x0, x0, y0 + 1, y1 - 1, zt + 1, zb - 1)
            elif open_end == 'E':
                cv.carve(x1, x1, y0 + 1, y1 - 1, zt + 1, zb - 1)
            elif open_end == 'N':
                cv.carve(x0 + 1, x1 - 1, y0, y0, zt + 1, zb - 1)
            else:
                cv.carve(x0 + 1, x1 - 1, y1, y1, zt + 1, zb - 1)
    return (x0, x1, y0, y1, g - 5 * levels, g - 1)


def tarp(cv, x0, y0, g, L, W, H, colour=TARP):
    """Tarp-covered machinery: a lumpy rounded mound with rope lines (the screenshot's blue tarps)."""
    cx, cy = x0 + (L - 1) / 2, y0 + (W - 1) / 2
    b = np.array(colour, float)
    for x in range(x0, x0 + L):
        for y in range(y0, y0 + W):
            u, v = (x - cx) / (L / 2 + 0.3), (y - cy) / (W / 2 + 0.3)
            r = max(abs(u) ** 3, abs(v) ** 3) ** (1 / 3) * 0.6 + math.hypot(u, v) * 0.4
            if r > 1:
                continue
            lump = 0.85 + 0.3 * noise.hash3(np.array([x // 3]), np.array([y // 3]), np.array([7]), 41)[0]
            h = max(1, int(round(H * min(1.0, (1 - r ** 2.2) * 1.3) * lump)))
            for z in range(g - h, g):
                rope = (x - x0) % 4 == 1 and z > g - h
                f = 0.72 if rope else 0.9 + 0.15 * ((g - z) / H)
                cv.set(x, y, z, tuple(int(v) for v in np.clip(b * f, 0, 255)), 'tarp')
    return (x0, x0 + L - 1, y0, y0 + W - 1)


def crates(cv, x, y, g, levels):
    """A pile of 3x3x3 wooden crates: 2x2 at the bottom, one per level above."""
    c = vcol(CRATE, 0.14, 3)
    for i in range(2):
        for j in range(2):
            cv.box(x + 3 * i, x + 3 * i + 2, y + 3 * j, y + 3 * j + 2, g - 3, g - 1, c, 'crate')
    for k in range(1, levels):
        cv.box(x + 1 + (k % 2), x + 3 + (k % 2), y + 1, y + 3, g - 3 - 3 * k, g - 1 - 3 * k, c, 'crate')
    return (x, x + 5, y, y + 5)


def drums(cv, x, y, g):
    """Cable drums: two standing, one lying."""
    for (dx, dy) in ((1, 1), (4, 2)):
        cv.cylinder(x + dx + 0.5, y + dy + 0.5, 1.6, g - 3, g - 1, (150, 104, 70), 'crate')
        cv.set(x + dx, y + dy, g - 4, (90, 90, 96), 'steel')
    cv.box(x, x + 5, y + 5, y + 7, g - 2, g - 1, (160, 112, 74), 'crate')
    return (x, x + 6, y, y + 7)


def pallets(cv, x, y, g):
    cv.box(x, x + 5, y, y + 3, g - 1, g - 1, (126, 98, 66), 'crate')
    cv.box(x + 1, x + 4, y, y + 3, g - 3, g - 2, (180, 172, 156), 'crate')      # shrink-wrapped sacks
    cv.box(x + 1, x + 2, y + 1, y + 2, g - 4, g - 4, (180, 172, 156), 'crate')
    return (x, x + 5, y, y + 3)


def vents(cv, x, y, g):
    """Two mushroom vents."""
    for dx in (0, 4):
        cv.box(x + dx, x + dx + 1, y, y + 1, g - 3, g - 1, STEEL, 'steel')
        cv.box(x + dx - 1, x + dx + 2, y - 1, y + 2, g - 4, g - 4, SUPER, 'steel')
    return (x - 1, x + 6, y - 1, y + 2)


def forklift(cv, x, y, g):
    cv.box(x, x + 5, y, y + 3, g - 2, g - 1, YELLOW, 'vehicle')
    cv.box(x + 3, x + 5, y, y + 3, g - 4, g - 3, YELLOW, 'vehicle')            # cab
    cv.carve(x + 4, x + 4, y + 1, y + 2, g - 4, g - 3)
    cv.box(x - 1, x - 1, y, y, g - 5, g - 1, DARK_STEEL, 'vehicle')            # mast
    cv.box(x - 1, x - 1, y + 3, y + 3, g - 5, g - 1, DARK_STEEL, 'vehicle')
    cv.box(x - 1, x - 1, y + 1, y + 2, g - 5, g - 5, DARK_STEEL, 'vehicle')
    cv.box(x - 3, x - 2, y, y + 3, g - 1, g - 1, DARK_STEEL, 'vehicle')        # forks
    for (dx, dy) in ((0, -1), (4, -1), (0, 4), (4, 4)):
        cv.set(x + dx, y + dy, g - 1, (40, 40, 44), 'vehicle')
    return (x - 3, x + 5, y - 1, y + 4)


def place_prop(cv, kind, x, y, arg, south=False):
    """Place a prop by its (west, north-side) footprint; south=True places the y-mirrored twin instead."""
    if kind == 'container':
        along, L, lv, col = arg[:4]
        op = arg[4] if len(arg) > 4 else None
        w, h = (L, 5) if along == 'x' else (5, L)
        if south:
            y = 512 - (y + h - 1)
            op = {'N': 'S', 'S': 'N'}.get(op, op)
        g = surf_top(cv, x, x + w - 1, y, y + h - 1)
        return container(cv, x, y, g, along, L, lv, col, op)
    if kind == 'tarp':
        L, W, H = arg
        if south:
            y = 512 - (y + W - 1)
        return tarp(cv, x, y, surf_top(cv, x, x + L - 1, y, y + W - 1), L, W, H)
    sizes = {'crates': (6, 6), 'drums': (7, 8), 'pallets': (6, 4), 'vents': (7, 2), 'forklift': (6, 4)}
    w, h = sizes[kind]
    if south:
        y = 512 - (y + h - 1)
    g = surf_top(cv, x, x + w - 1, y, y + h - 1)
    if kind == 'crates':
        return crates(cv, x, y, g, arg)
    if kind == 'drums':
        return drums(cv, x, y, g)
    if kind == 'pallets':
        return pallets(cv, x, y, g)
    if kind == 'vents':
        return vents(cv, x, y, g)
    return forklift(cv, x, y, g)


# ---------------------------------------------------------------------- sea and islets
def islets(cv, S, rep):
    F = noise.fbm2((512, 512), 9, 3, 'islet_r', S['layout_seed'])
    F2 = noise.fbm2((512, 512), 5, 2, 'islet_lump', S['layout_seed'])
    X, Y = np.indices((512, 512))
    h = np.zeros((512, 512), float)
    for (cx, cy, r, peak, hut) in S['islets']:
        d = np.hypot(X - cx, Y - cy)
        er = r * (0.80 + 0.40 * F)
        t = np.clip(1 - (d / er) ** 1.6, 0, 1)
        hh = peak * np.minimum(1.0, t * 1.5) + (F2 - 0.5) * 3 * (t > 0.3)
        hh = np.where(d <= er + 2.5, np.maximum(hh, 1), hh)
        h = np.maximum(h, hh)
    for (cx, cy, r, peak) in S['rocks']:
        d = np.hypot(X - cx, Y - cy)
        er = r * (0.8 + 0.4 * F)
        t = np.clip(1 - (d / er) ** 1.4, 0, 1)
        hh = peak * np.minimum(1.0, t * 1.8) + (F2 - 0.5) * 2 * (t > 0.3)
        hh = np.where(d <= er + 1.5, np.maximum(hh, 1), hh)
        h = np.maximum(h, hh)
    h = np.rint(h).astype(int)
    for (cx, cy, r, peak, hut) in S['islets']:
        if hut:
            lvl = peak - 2
            h[cx - 7:cx + 7, cy - 6:cy + 7] = np.maximum(np.minimum(h[cx - 7:cx + 7, cy - 6:cy + 7], lvl), 1)
            h[cx - 6:cx + 6, cy - 5:cy + 6] = lvl
    h[256:] = 0                                      # west half only (mirror)
    top = 63 - h
    zz = np.arange(64)[None, None, :]
    land = (zz >= top[:, :, None]) & (zz <= 62) & (h[:, :, None] > 0)
    sand = land & (h[:, :, None] <= 1)
    rock = land & ~sand & ((zz > top[:, :, None]) | (h[:, :, None] >= 2))
    cv.fill_mask(rock, vcol(ROCK, 0.18, 11), 'rock')
    cv.fill_mask(sand, vcol(SAND, 0.10, 12), 'sand')
    topm = (zz == top[:, :, None]) & (h[:, :, None] >= 2)
    cv.fill_mask(topm, vcol(MOSS, 0.16, 13), 'ground')
    cv.H = np.where(h > 0, top, cv.H).astype(np.int16)
    rep['islet_columns_west'] = int((h > 0).sum())
    # piers (z 62 plank walks from the beach out over the sea), huts, beacons
    for (x, ya, yb, d) in S['piers']:
        y0, y1 = min(ya, yb), max(ya, yb)
        for y in range(y0, y1 + 1):
            for xx in range(x - 2, x + 2):
                if xx > 255:
                    continue
                if cv.solid[xx, y, 62] and cv.mat[xx, y, 62] != cv.materials.get('pier'):
                    continue
                cv.set(xx, y, 62, shade(PLANK, 0.9 + 0.12 * ((y + xx) % 3) / 2), 'pier')
            if (y - y0) % 6 == 0:
                for xx in (x - 3, x + 2):
                    if xx <= 255:
                        cv.box(xx, xx, y, y, 60, 62, (84, 70, 58), 'pier')
        ye = yb
        for xx in range(x - 5, x + 5):
            if xx <= 255:
                cv.set(xx, ye, 62, PLANK, 'pier')
                cv.set(xx, ye + (1 if d == 'S' else -1), 62, PLANK, 'pier')
    rep['huts'] = []
    for (cx, cy, r, peak, hut) in S['islets']:
        if not hut:
            continue
        g = 63 - (peak - 2)
        door = 'S' if cy < 256 else 'N'
        b = structures.building(cv, cx - 5, cx + 5, cy - 4, cy + 4, g, storeys=1, storey_h=5, wall=(118, 92, 72),
                                floor=(130, 104, 78), roof=(70, 74, 80), doors=(door, 'W'), name='fisher hut',
                                mat='hut')
        # pitched roof ridge
        for k in range(1, 3):
            cv.box(cx - 5, cx + 5, cy - 4 + k, cy + 4 - k, g - 5 - k, g - 5 - k, (66, 70, 78), 'hut')
        cv.no_prop(cx - 7, cx + 7, cy - 6, cy + 6)
        rep['huts'].append(b)
        lx = cx
        ly = cy + 5 if door == 'S' else cy - 5
        cv.set(lx + 2, ly, g - 4, LAMP, 'lamp')
        cv.glow.append((lx + 2, ly, g - 4, LAMP))
        cv.nolight[lx + 2, ly, g - 4] = True
    for (bx, by) in S['beacons']:
        g = int(np.argmax(cv.solid[bx - 1, by]))
        for z in range(g - 14, g):
            band = ((g - z) // 3) % 2
            cv.cylinder(256.5, by + 0.5, 2.3, z, z, (196, 192, 184) if band else (150, 52, 48), 'beacon')
        cv.cylinder(256.5, by + 0.5, 3.4, g - 15, g - 15, DARK_STEEL, 'beacon')       # gallery
        cv.box(255, 257, by - 1, by + 1, g - 17, g - 16, DARK_STEEL, 'beacon')
        cv.set(255, by, g - 18, LAMP_W, 'lamp')
        cv.glow.append((255, by, g - 18, LAMP_W))
        cv.nolight[255, by, g - 18] = True
        cv.no_prop(250, 262, by - 6, by + 6)
    for (bx, by) in S['buoys']:
        col = (70, 120, 70) if by < 256 else (170, 120, 50)
        cv.cylinder(bx + 0.5, by + 0.5, 1.8, 61, 62, col, 'buoy')
        cv.box(bx, bx, by, by, 57, 60, DARK_STEEL, 'buoy')
        cv.box(bx - 1, bx + 1, by, by, 59, 59, col, 'buoy')
        cv.set(bx, by, 56, LAMP_G if by < 256 else LAMP, 'lamp')
        cv.glow.append((bx, by, 56, LAMP_G if by < 256 else LAMP))
        cv.nolight[bx, by, 56] = True


# ---------------------------------------------------------------------- hull core (west half, x 70-256)
def hull_core(cv, S, rep):
    Z = S['z']
    ya, yb = S['hull']['y']
    x0 = S['hull']['mid_x'][0]
    deck, tween, hold = Z['deck'], Z['tween'], Z['hold']
    cv.box(x0, 256, ya, yb, deck, 62, vcol(HULLFILL, 0.06, 21), 'hullfill')
    cv.box(x0, 256, ya, ya, deck, 62, HULL, 'hull')
    cv.box(x0, 256, yb, yb, deck, 62, HULL, 'hull')
    cv.box(x0, 256, ya + 1, yb - 1, deck, deck, vcol(DECK, 0.06, 22), 'deck')
    cv.box(x0, 256, ya + 1, yb - 1, deck + 1, deck + 1, vcol((132, 134, 130), 0.06, 29), 'deckhead')   # underside
    cv.box(x0, 256, ya + 1, ya + 10, deck, deck, vcol(GANGWAY, 0.06, 23), 'deck')          # side gangways
    cv.box(x0, 256, yb - 10, yb - 1, deck, deck, vcol(GANGWAY, 0.06, 23), 'deck')
    cv.box(x0, 256, ya, ya, Z['bulwark_top'], deck - 1, BULWARK, 'bulwark')
    cv.box(x0, 256, yb, yb, Z['bulwark_top'], deck - 1, BULWARK, 'bulwark')
    cv.H[x0:257, ya:yb + 1] = deck
    # tween deck
    T = S['tween']
    cv.carve(T['x'][0], 256, T['y'][0], T['y'][1], T['air'][0], T['air'][1])
    cv.box(T['x'][0], 256, T['y'][0], T['y'][1], tween, tween, vcol(FLOOR_HOLD, 0.08, 24), 'holdfloor')
    for bx in T['bulkheads']:
        cv.box(bx, bx + 1, T['y'][0], T['y'][1], T['air'][0], T['air'][1], vcol(STEEL, 0.05, 25), 'bulkhead')
        for (da, db) in T['doors_y']:
            cv.carve(bx, bx + 1, da, db, T['air'][1] - 4, T['air'][1])
    for px in T['pillar_x']:
        for (pa, pb) in T['pillar_y']:
            for (qa, qb) in ((pa, pb), ym(pa, pb)):
                cv.box(px, px + 1, qa, qb, T['air'][0], T['air'][1], DARK_STEEL, 'steel')
    # lower hold
    L = S['lower_hold']
    cv.carve(L['x'][0], 256, L['y'][0], L['y'][1], L['air'][0], L['air'][1])
    cv.box(L['x'][0], 256, L['y'][0], L['y'][1], hold, hold, vcol(FLOOR_HOLD, 0.08, 26), 'holdfloor')
    for px in (200, 228):
        for (pa, pb) in ((231, 232), (280, 281)):
            cv.box(px, px + 1, pa, pb, L['air'][0], L['air'][1], DARK_STEEL, 'steel')
    for (sx0, sx1, sy0, sy1) in S['solid_below']:          # roof-free ground under spawn squares and anchors
        for (qa, qb) in ((sy0, sy1),):
            cv.box(sx0, sx1, qa, qb, T['air'][0], L['air'][1], vcol(HULLFILL, 0.06, 28), 'hullfill')
    for (wx0, wx1, wy0, wy1) in T['wells']:
        cv.carve(wx0, wx1, wy0, wy1, tween, tween + 1)
        for x in range(wx0 - 1, wx1 + 2):                      # 1-high rail round the well
            for y in (wy0 - 1, wy1 + 1):
                cv.set(x, y, tween - 1, (170, 150, 60), 'rail')
        for y in range(wy0 - 1, wy1 + 2):
            for x in (wx0 - 1, wx1 + 1):
                cv.set(x, y, tween - 1, (170, 150, 60), 'rail')
    for (sx, sy0, sy1) in L['stairs']:
        ys = (sy0 + 4, sy1 + 4) if sy0 < 256 else (sy0 - 4, sy1 - 4)
        structures.straight_stair(cv, sx, ys[0], ys[1], hold, hold - tween, 1, STAIR, 'stair')
    cv.interiors += [['tween deck fore', 88, 256, tween], ['tween deck mid', 150, 256, tween],
                     ['tween deck aft', 222, 240, tween], ['lower hold', 190, 256, hold]]
    # hatch panels (raised 1) in the bays
    hz = Z['hatch']
    hy0, hy1 = S['hatch_y']
    for (bx0, bx1) in S['hatch_bays']:
        x = bx0
        while x <= bx1:
            xe = min(x + 11, bx1)
            for (pa, pb) in ((hy0, 255), (257, hy1)):
                cv.box(x, xe, pa, pb, hz, hz, vcol(HATCH, 0.07, 27), 'hatch')
            x = xe + 2
    # side ports into the lower hold (both sides) with steps up from the sea
    P = S['side_port']
    za, zb = P['z_air']
    cv.carve(P['x'][0], 256, ya, L['y'][0] - 1, za, zb)
    cv.carve(P['x'][0], 256, L['y'][1] + 1, yb, za, zb)
    for i, y in enumerate(range(ya - 4, ya)):
        cv.box(P['x'][0], 256, y, y, 62 - i, 62, STAIR, 'stair')
        cv.box(P['x'][0], 256, 512 - y, 512 - y, 62 - i, 62, STAIR, 'stair')
    cv.interiors += [['side port N', 252, ya + 2, hold], ['side port S', 252, yb - 2, hold]]
    # open deck hatch under the platform centre (1-high coaming)
    D = S['deck_hatch']
    cv.carve(D['x'][0], 256, D['y'][0], D['y'][1], hz, deck + 1)
    for x in range(D['x'][0] - 1, 257):
        cv.set(x, D['y'][0] - 1, hz, SUPER, 'coaming')
        cv.set(x, D['y'][1] + 1, hz, SUPER, 'coaming')
    for y in range(D['y'][0] - 1, D['y'][1] + 2):
        cv.set(D['x'][0] - 1, y, hz, SUPER, 'coaming')
    rep['hull_core'] = {'deck_z': deck, 'tween_floor': tween, 'hold_floor': hold}


def companionway(cv, x0, yc, deck, tween):
    """Deck <-> tween deck: a straight stair rising +x under a small white deckhouse with a door at the top end."""
    structures.straight_stair(cv, x0, yc - 1, yc + 1, tween, tween - deck, 1, STAIR, 'stair')
    hx0, hx1 = x0 + 4, x0 + 11
    cv.box(hx0, hx1, yc - 2, yc + 2, deck - 5, deck - 1, vcol(SUPER, 0.05, 31), 'deckhouse')
    cv.carve(hx0 + 1, hx1 - 1, yc - 1, yc + 1, deck - 4, deck - 1)
    cv.carve(hx1, hx1, yc - 1, yc + 1, deck - 4, deck - 1)
    cv.box(hx0, hx1, yc - 2, yc + 2, deck - 5, deck - 5, (150, 60, 56), 'deckhouse')       # roof
    cv.carve(hx0 + 3, hx0 + 4, yc - 2, yc - 2, deck - 3, deck - 2)                          # portholes
    cv.carve(hx0 + 3, hx0 + 4, yc + 2, yc + 2, deck - 3, deck - 2)
    cv.interiors.append(['companionway', hx1 - 1, yc, deck])
    return (hx0, hx1, yc - 2, yc + 2)


def crane(cv, cx, cy, deck, rest_x, south=False):
    """Deck crane: hollow pedestal with a spiral stair to the cab, jib stowed west on a rest post."""
    x0, x1, y0, y1 = cx - 5, cx + 4, cy - 5, cy + 4
    top = deck - 12                                      # cab floor z 28
    cv.box(x0, x1, y0, y1, top, deck - 1, vcol(SUPER, 0.05, 32), 'crane')
    cv.carve(x0 + 1, x1 - 1, y0 + 1, y1 - 1, top + 1, deck - 1)
    structures.spiral_stair(cv, cx, cy, top, deck, r=3, c=STAIR, core=DARK_STEEL)
    dy = y1 if south else y0                             # door on the gangway side
    cv.carve(cx - 1, cx + 1, dy, dy, deck - 4, deck - 1)
    # cab
    cx0, cx1, cy0, cy1 = x0 - 1, x1 + 1, y0, y1
    cv.box(cx0, cx1, cy0, cy1, top - 6, top - 1, vcol((206, 160, 60), 0.05, 33), 'crane')
    cv.carve(cx0 + 1, cx1 - 1, cy0 + 1, cy1 - 1, top - 5, top - 1)
    cv.box(cx0 + 1, cx1 - 1, cy0 + 1, cy1 - 1, top, top, STAIR, 'crane')
    structures.spiral_stair(cv, cx, cy, top, deck, r=3, c=STAIR, core=DARK_STEEL)  # re-open the shaft
    for wx in range(cx0 + 2, cx1 - 1, 3):
        cv.carve(wx, wx + 1, cy0, cy0, top - 4, top - 3)
        cv.carve(wx, wx + 1, cy1, cy1, top - 4, top - 3)
    cv.carve(cx0, cx0, cy0 + 2, cy1 - 2, top - 4, top - 3)
    cv.interiors.append(['crane cab', cx + 3, cy + (2 if not south else -2), top])
    # jib (2x2 lattice beam) stowed west, resting on a post
    jz = top - 2                                         # below the cab's west window (z top-4..top-3)
    jy = cy - 1
    g = surf_top(cv, rest_x - 1, rest_x, jy, jy + 1)
    cv.box(rest_x, cx0 - 1, jy, jy + 1, jz, jz + 1, (196, 156, 58), 'jib')
    for x in range(rest_x + 1, cx0 - 1, 2):
        cv.set(x, jy, jz + 1, (120, 96, 40), 'jib')
    cv.box(rest_x - 1, rest_x, jy, jy + 1, jz, g - 1, DARK_STEEL, 'jib')
    cv.add_glow(cx0, cy0 + 2, top - 6, LAMP)
    cv.add_glow(cx1, cy0 + 2, top - 6, LAMP)
    return (rest_x - 1, cx1, cy0, cy1)


def gangway(cv, x0, y0, y1, deck):
    """Accommodation ladder: from the sea (floor z 63) up the hull side to the deck, with a bulwark gap."""
    rise = 63 - deck
    structures.straight_stair(cv, x0, y0, y1, 63, rise, 1, STAIR, 'stair')
    lx0, lx1 = x0 + rise, x0 + rise + 3
    cv.box(lx0, lx1, y0, y1, deck, 62, vcol(DARK_STEEL, 0.05, 34), 'stair')
    cv.carve(lx0, lx1, y0, y1, deck - 3, deck - 1)
    if y0 < 256:
        cv.carve(lx0, lx1, y1 + 1, y1 + 1, deck - 2, deck - 1)      # bulwark gap
    else:
        cv.carve(lx0, lx1, y0 - 1, y0 - 1, deck - 2, deck - 1)
    # handrail posts on the sea side
    ry = y0 if y0 < 256 else y1
    for i in range(0, rise, 4):
        cv.set(x0 + i, ry, 63 - i - 2, (190, 186, 176), 'rail')
    return (x0, lx1, y0, y1)


def build_west(S, veg_seed):
    cv = Canvas(S['name'])
    rep = {}
    cv.box(0, 511, 0, 511, 63, 63, SEA, 'sea')
    islets(cv, S, rep)
    hull_core(cv, S, rep)
    Z = S['z']
    deck, tween = Z['deck'], Z['tween']
    sp = S['spawn']
    bx, by, h = sp['base'][0], sp['base'][1], sp['half']
    cv.no_prop(bx - h - 2, bx + h + 2, by - h - 2, by + h + 2)
    cv.no_prop(S['anchor']['x'][0], S['anchor']['x'][1], 236, 276)
    rep['companionways'], rep['cranes'], rep['gangways'] = [], [], []
    for (x0, yc, dx) in S['companionways']:
        rep['companionways'].append(companionway(cv, x0, yc, deck, tween))
        rep['companionways'].append(companionway(cv, x0, 512 - yc, deck, tween))
    for (cx, cy) in S['cranes']:
        rep['cranes'].append(crane(cv, cx, cy, deck, S['jib_rest_x']))
        rep['cranes'].append(crane(cv, cx, 512 - cy, deck, S['jib_rest_x'], south=True))
    for (x0, y0, y1) in S['gangways']:
        rep['gangways'].append(gangway(cv, x0, y0, y1, deck))
        a, b = ym(y0, y1)
        rep['gangways'].append(gangway(cv, x0, a, b, deck))
    props = []
    for (k, x, y, a) in S['front_props']:
        props.append(('front', k, place_prop(cv, k, x, y, a)))
    for (k, x, y, a) in S['cover_props'] + S['cover_props_s']:
        props.append(('cover', k, place_prop(cv, k, x, y, a)))
    for (k, x, y, a) in S['strip_props']:
        props.append(('strip', k, place_prop(cv, k, x, y, a)))
    for (k, x, y, a) in S['centre_props']:
        props.append(('centre', k, place_prop(cv, k, x, y, a)))
        props.append(('centre', k, place_prop(cv, k, x, y, a, south=True)))
    for (k, x, y, a) in S['tween_props']:
        g = tween
        if k == 'container':
            along, L, lv, col = a[:4]
            op = a[4] if len(a) > 4 else None
            props.append(('tween', k, container(cv, x, y, g, along, L, lv, col, op)))
        else:
            props.append(('tween', k, crates(cv, x, y, g, a)))
    # locomotive cargo in the lower hold (twin-cab, so it is symmetric end to end)
    hz = Z['hold']
    loco = (70, 84, 92)
    cv.box(228, 256, 253, 259, hz - 1, hz - 1, DARK_STEEL, 'loco')                 # bogies / frame
    cv.box(230, 256, 252, 260, hz - 5, hz - 2, vcol(loco, 0.05, 41), 'loco')
    cv.box(228, 233, 252, 260, hz - 6, hz - 2, vcol((176, 140, 56), 0.05, 42), 'loco')   # cab
    cv.carve(229, 229, 253, 259, hz - 5, hz - 4)
    for x in range(236, 256, 6):
        cv.box(x, x + 2, 252, 252, hz - 4, hz - 3, (40, 44, 50), 'loco')             # grilles
        cv.box(x, x + 2, 260, 260, hz - 4, hz - 3, (40, 44, 50), 'loco')
    for x in (230, 236, 246, 252):
        cv.box(x, x + 1, 251, 261, hz - 1, hz - 1, (40, 40, 44), 'loco')
    cv.add_glow(228, 256, hz - 4, LAMP_Y)
    # hold lamps (bulkheads, pillars) and deck lamps on the companionways
    for bxk in S['tween']['bulkheads']:
        for y in (240, 272):
            cv.add_glow(bxk - 1 if bxk > 0 else bxk, y, 44, LAMP_Y)
    for px in (104, 158, 238):
        cv.add_glow(px, 231, 44, LAMP_Y)
        cv.add_glow(px, 281, 44, LAMP_Y)
    for px in (200, 228):
        cv.add_glow(px, 233, 54, LAMP_Y)
        cv.add_glow(px, 279, 54, LAMP_Y)
    rep['props'] = [(z, k, list(map(int, b[:4]))) for (z, k, b) in props]
    # vegetation on the islets (west; OS seed by owner rule), then the mirror happens in main
    rng = np.random.default_rng(veg_seed)
    pal = veg.palette_family([(46, 74, 54), (58, 88, 60), (70, 98, 66), (52, 80, 72), (84, 104, 70)], n=8)
    rep['vegetation'] = veg.plant_groves(cv, rng, S['groves'], pal, species=('conifer', 'bush'), weights=(3, 1),
                                         per_grove=(4, 9), radius=(5, 14), spacing=5,
                                         region_ok=lambda x, y: x <= 250 and not (186 <= y <= 326))
    return cv, rep


# ---------------------------------------------------------------------- ends (after the mirror)
def _hw_bow(S, x, z):
    B = S['hull']['bow']
    xe = x - B['rake'] * (z - S['z']['forecastle'])
    t = (S['hull']['mid_x'][0] - xe) / (S['hull']['mid_x'][0] - B['tip_x'])
    if t <= 0:
        return 52.0
    if t >= 1:
        return -1.0
    return 52.0 * (1 - t ** B['power'])


def _hw_stern(S, x, z):
    St = S['hull']['stern']
    xm = S['hull']['mid_x'][1]
    if x <= xm:
        return 52.0
    xend = St['end_x'] - St['rake'] * (z - S['z']['deck'])
    if x > xend:
        return -1.0
    return 52.0 * math.sqrt(max(0.0, 1 - ((x - xm) / 58.0) ** 2))


def ends(cv, S, rep):
    Z = S['z']
    deck, fc = Z['deck'], Z['forecastle']
    out = {}
    # ---------------- bow (west, x <= 72)
    xb = 72
    ys = np.arange(186, 327)
    foot_top = np.zeros((512, 512), bool)
    for x in range(4, xb + 1):
        top = fc if x <= S['forecastle']['x_break'] else deck
        for z in range(top, 63):
            hw = _hw_bow(S, x, z)
            if hw < 0:
                continue
            sel = ys[np.abs(ys - 256) <= hw]
            if len(sel) == 0:
                continue
            cv.box(x, x, sel[0], sel[-1], z, z, None, 'hullfill')
            cv.rgb[x, sel[0]:sel[-1] + 1, z] = HULLFILL
            if z == top:
                foot_top[x, sel[0]:sel[-1] + 1] = True
                cv.H[x, sel[0]:sel[-1] + 1] = top
    # outer skin = hull material (columns on the footprint edge), deck on top
    from scipy import ndimage as ndi
    foot_top[xb + 1:xb + 5, 204:309] = True               # the core deck continues east: no edge at x 72
    edge = foot_top & ~ndi.binary_erosion(foot_top, structure=np.ones((3, 3), bool))
    foot_top[xb + 1:xb + 5] = False
    for x in range(4, xb + 1):
        top = fc if x <= S['forecastle']['x_break'] else deck
        col_sel = foot_top[x]
        if not col_sel.any():
            continue
        yy = np.nonzero(col_sel)[0]
        cv.rgb[x, yy, top] = DECK
        cv.mat[x, yy, top] = cv.material('deck')
        for y in np.nonzero(edge[x])[0]:
            zs = np.nonzero(cv.solid[x, y, :63])[0]
            cv.rgb[x, y, zs] = HULL
            cv.mat[x, y, zs] = cv.material('hull')
            if x <= S['forecastle']['x_break'] or y in (204, 308) or x < 70:
                cv.box(x, x, y, y, top - 2, top - 1, BULWARK, 'bulwark')
    # skin on the raked stem: any hullfill voxel with air beside it becomes hull
    sub = cv.solid[:xb + 1, 180:333, :63]
    mat = cv.mat[:xb + 1, 180:333, :63]
    air = ~sub
    nb = np.zeros_like(sub)
    nb[1:] |= air[:-1]
    nb[:-1] |= air[1:]
    nb[:, 1:] |= air[:, :-1]
    nb[:, :-1] |= air[:, 1:]
    nb[:, :, 1:] |= air[:, :, :-1] & (np.arange(63)[None, None, 1:] > deck)
    skin = sub & nb & (mat == cv.material('hullfill'))
    xs, ys2, zs = np.nonzero(skin)
    cv.rgb[xs, ys2 + 180, zs] = HULL
    cv.mat[xs, ys2 + 180, zs] = cv.material('hull')
    # break wall rail at x_break, forecastle store with a door, stairs up on both sides
    F = S['forecastle']
    xbk = F['x_break']
    cv.box(xbk, xbk, 206, 306, fc - 2, fc - 1, BULWARK, 'bulwark')
    sx0, sx1 = F['store']
    for x in range(sx0, sx1 + 1):
        hw = _hw_bow(S, x, fc + 1) - 3
        if hw <= 3:
            continue
        cv.carve(x, x, int(256 - hw), int(256 + hw), fc + 1, deck - 1)
        cv.box(x, x, int(256 - hw), int(256 + hw), deck, deck, vcol(FLOOR_HOLD, 0.08, 51), 'holdfloor')
    cv.carve(sx1 + 1, xbk, F['door_y'][0], F['door_y'][1], fc + 1, deck - 1)
    for (a, b) in F['stairs_y']:
        cv.carve(xbk, xbk, a, b, fc - 2, fc - 1)                    # rail gap
        structures.straight_stair(cv, xbk + 5, a, b, deck, deck - fc, -1, STAIR, 'stair')
    for x in range(30, 62, 6):                                       # store: shelves, rope coils, lamps
        cv.box(x, x + 2, 236, 237, deck - 2, deck - 1, CRATE, 'crate')
        cv.box(x, x + 2, 275, 276, deck - 2, deck - 1, CRATE, 'crate')
    cv.add_glow(sx1 - 2, 244, fc + 1, LAMP_Y)
    cv.add_glow(sx1 - 2, 268, fc + 1, LAMP_Y)
    cv.add_glow(xbk, 250, fc - 1, LAMP)
    cv.add_glow(xbk, 262, fc - 1, LAMP)
    cv.interiors.append(['forecastle store', 50, 256, deck])
    cv.interiors.append(['forecastle deck', 50, 256, fc])
    # foremast with two lookout rings, a yard and a masthead light
    M = S['foremast']
    mx, my = M['x'], M['y']
    cv.cylinder(mx + 0.5, my + 0.5, 1.7, M['top'], fc - 1, vcol((200, 196, 186), 0.05, 52), 'mast')
    for rz in M['rings']:
        cv.cylinder(mx + 0.5, my + 0.5, 4.2, rz, rz, DARK_STEEL, 'mast')
        cv.cylinder(mx + 0.5, my + 0.5, 4.2, rz - 1, rz - 1, (190, 186, 176), 'mast', hollow=3.4)
    cv.box(mx, mx, my - 7, my + 7, M['top'] + 5, M['top'] + 5, DARK_STEEL, 'mast')
    cv.box(mx, mx + 1, my, my, M['top'] - 1, M['top'] - 1, DARK_STEEL, 'mast')
    cv.add_glow(mx, my, M['top'] - 2, LAMP_W)
    # windlasses, chain to the hawse pipes, bollards
    for (wy0, wy1) in ((243, 249), (263, 269)):
        cv.box(40, 47, wy0, wy1, fc - 3, fc - 1, vcol(DARK_STEEL, 0.06, 53), 'machinery')
        cv.cylinder(43.5, (wy0 + wy1) / 2 + 0.5, 2.0, fc - 5, fc - 4, (150, 154, 150), 'machinery')
        yy = wy0 + 3
        for x in range(26, 40):
            cv.set(x, yy, fc - 1, (60, 60, 64), 'chain')
    for (bxx, byy) in ((28, 236), (28, 275), (58, 214), (58, 297)):
        cv.box(bxx, bxx + 1, byy, byy + 1, fc - 2, fc - 1, DARK_STEEL, 'machinery')
    cv.add_glow(16, 256, fc - 1, LAMP_W)                             # stem light
    out['bow'] = {'x': [4, xb], 'forecastle_z': fc}

    # ---------------- stern (east, x >= 440)
    xs0 = 440
    foot = np.zeros((512, 512), bool)
    foot[xs0 - 4:xs0, 204:309] = True                     # the core deck continues west: no edge at x 440
    for x in range(xs0, 500):
        for z in range(deck, 63):
            hw = _hw_stern(S, x, z)
            if hw < 0:
                continue
            sel = ys[np.abs(ys - 256) <= hw]
            if len(sel) == 0:
                continue
            cv.box(x, x, sel[0], sel[-1], z, z, HULLFILL, 'hullfill')
            if z == deck:
                foot[x, sel[0]:sel[-1] + 1] = True
                cv.H[x, sel[0]:sel[-1] + 1] = deck
    edge = foot & ~ndi.binary_erosion(foot, structure=np.ones((3, 3), bool))
    for x in range(xs0, 500):
        yy = np.nonzero(foot[x])[0]
        if len(yy) == 0:
            continue
        cv.rgb[x, yy, deck] = DECK
        cv.mat[x, yy, deck] = cv.material('deck')
        for y in np.nonzero(edge[x])[0]:
            zs = np.nonzero(cv.solid[x, y, :63])[0]
            cv.rgb[x, y, zs] = HULL
            cv.mat[x, y, zs] = cv.material('hull')
            cv.box(x, x, y, y, deck - 2, deck - 1, BULWARK, 'bulwark')
    sub = cv.solid[xs0 - 1:, 180:333, :63]
    mat = cv.mat[xs0 - 1:, 180:333, :63]
    air = ~sub
    nb = np.zeros_like(sub)
    nb[1:] |= air[:-1]
    nb[:-1] |= air[1:]
    nb[:, :, 1:] |= air[:, :, :-1] & (np.arange(63)[None, None, 1:] > deck)
    skin = sub & nb & (mat == cv.material('hullfill'))
    xs, ys2, zs = np.nonzero(skin)
    cv.rgb[xs + xs0 - 1, ys2 + 180, zs] = HULL
    cv.mat[xs + xs0 - 1, ys2 + 180, zs] = cv.material('hull')
    # bridge superstructure: 5 storeys, real rooms, stairs to every floor, doors to the deck
    Bd = S['bridge']
    bx0, bx1 = Bd['x']
    by0, by1 = Bd['y']
    b = structures.building(cv, bx0, bx1, by0, by1, deck, storeys=Bd['storeys'], storey_h=Bd['storey_h'],
                            wall=SUPER, floor=(118, 120, 114), roof=(96, 100, 104), stair=STAIR,
                            doors=('W', 'N', 'S'), name='bridge', mat='superstructure')
    sh = Bd['storey_h']
    top_floor = deck - (Bd['storeys'] - 1) * sh
    roof = deck - Bd['storeys'] * sh
    # bridge wings at the wheelhouse floor
    for (wy0, wy1, wall_y) in ((Bd['wing_y'][0], by0 - 1, by0), (by1 + 1, Bd['wing_y'][1], by1)):
        cv.box(bx0, bx0 + 11, wy0, wy1, top_floor, top_floor, (118, 120, 114), 'superstructure')
        cv.box(bx0, bx0 + 11, wy0, wy1, top_floor + 1, top_floor + 1, SUPER, 'superstructure')
        rail_y = wy0 if wall_y == by0 else wy1
        cv.box(bx0, bx0 + 11, rail_y, rail_y, top_floor - 1, top_floor - 1, SUPER, 'superstructure')
        cv.box(bx0, bx0, wy0, wy1, top_floor - 1, top_floor - 1, SUPER, 'superstructure')
        # door clear of the stairwells (x bx0+2..bx0+7 along both long walls)
        cv.carve(bx0 + 8, bx0 + 10, wall_y, wall_y, top_floor - 4, top_floor - 1)
        cv.add_glow(bx0, rail_y, top_floor - 2, LAMP_G if wall_y == by0 else LAMP_R)
        cv.interiors.append(['bridge wing', bx0 + 6, (wy0 + wy1) // 2, top_floor])
    # wheelhouse windows: a wide band of glass on the wheelhouse front
    cv.carve(bx0, bx0, by0 + 3, by1 - 3, top_floor - 3, top_floor - 2)
    # lifeboat balconies at the second storey
    lbz = deck - 2 * sh
    for (lx, ly) in S['lifeboats']:
        north = ly < 256
        ya_, yb_ = (Bd['wing_y'][0] + 1, by0 - 1) if north else (by1 + 1, Bd['wing_y'][1] - 1)
        cv.box(lx, lx + 18, ya_, yb_, lbz, lbz, (118, 120, 114), 'superstructure')
        ry = ya_ if north else yb_
        cv.box(lx, lx + 18, ry, ry, lbz - 1, lbz - 1, SUPER, 'superstructure')
        cv.carve(lx + 8, lx + 10, by0 if north else by1, by0 if north else by1, lbz - 4, lbz - 1)
        boy = (ya_ + 1) if north else (yb_ - 7)
        for x in range(lx + 1, lx + 18):
            t = abs(x - (lx + 9)) / 9.0
            w = 3 if t < 0.7 else 2
            for y in range(boy + 3 - w, boy + 4 + w):
                hh = 4 if t < 0.8 else 3
                for z in range(lbz - hh, lbz):
                    cv.set(x, y, z, ORANGE if z < lbz - 2 else (190, 186, 176), 'lifeboat')
        cv.interiors.append(['lifeboat balcony', lx + 9, (yb_ if north else ya_), lbz])
    # floodlights on the bridge front, porthole lights
    for y in (232, 256, 280):
        cv.add_glow(bx0, y, deck - sh - 2, LAMP)
    for k in range(1, Bd['storeys']):
        for y in (226, 286):
            cv.add_glow(bx0, y, deck - k * sh - 3, LAMP_Y)
    # radar mast on the roof
    mx, my = 466, 256
    cv.box(mx, mx + 1, my - 1, my, 2, roof - 1, (190, 186, 176), 'mast')
    cv.box(mx, mx, my - 8, my + 7, 6, 6, DARK_STEEL, 'mast')
    cv.box(mx - 3, mx + 4, my, my, 9, 9, DARK_STEEL, 'mast')
    cv.add_glow(mx, my, 1, LAMP_W)
    # funnel (white, orange band, black top) with an attached smoke plume
    Fn = S['funnel']
    fx0, fx1 = Fn['x']
    fy0, fy1 = Fn['y']
    fcx, fcy = (fx0 + fx1 + 1) / 2, (fy0 + fy1 + 1) / 2
    rx, ry = (fx1 - fx0 + 1) / 2, (fy1 - fy0 + 1) / 2
    for z in range(Fn['top'], deck):
        col = (40, 40, 44) if z <= Fn['top'] + 1 else ORANGE if z <= Fn['top'] + 7 else SUPER
        for x in range(fx0, fx1 + 1):
            for y in range(fy0, fy1 + 1):
                if ((x + 0.5 - fcx) / rx) ** 2 + ((y + 0.5 - fcy) / ry) ** 2 <= 1:
                    cv.set(x, y, z, col, 'funnel')
    prev = None
    puffs = [(486, 256, Fn['top'] - 1, 3.0), (489, 255, Fn['top'] - 3, 3.6), (493, 254, Fn['top'] - 4, 4.2),
             (498, 252, Fn['top'] - 5, 4.6), (503, 250, Fn['top'] - 5, 4.4), (507, 248, Fn['top'] - 6, 3.6)]
    for i, (px, py, pz, pr) in enumerate(puffs):
        g = int(110 - 6 * i)
        cv.ellipsoid(px, py, max(pr * 0.7, pz), pr, pr * 0.9, pr * 0.7, (g, g, g + 8), 'smoke')
    # poop deck: mooring winches, bollards, a flagstaff
    for (wy0, wy1) in ((232, 240), (272, 280)):
        cv.box(484, 490, wy0, wy1, deck - 3, deck - 1, vcol(DARK_STEEL, 0.06, 54), 'machinery')
        cv.cylinder(487.5, (wy0 + wy1) / 2 + 0.5, 2.2, deck - 5, deck - 4, (150, 154, 150), 'machinery')
    cv.box(493, 493, 256, 256, 22, deck - 1, (190, 186, 176), 'mast')
    cv.box(494, 501, 256, 256, 22, 26, (56, 92, 70), 'flag')
    cv.box(494, 501, 256, 256, 24, 24, (196, 192, 184), 'flag')
    cv.add_glow(495, 256, deck - 2, LAMP_W)
    out['stern'] = {'x': [xs0, 499], 'bridge': b, 'roof_z': roof}
    rep['ends'] = out
    return out


def sky(cv, S):
    from aosmap.kit import sky as skym
    recs = []
    for i, (x, y, z, hd) in enumerate(S['sky']['gulls']):
        recs.append(skym.place(cv, f'gull {i + 1}', skym.bird, x, y, z, hd, colour=(196, 196, 204),
                               beak=(220, 170, 60)))
    for i, (x, y, z, L) in enumerate(S['sky']['clouds']):
        recs.append(skym.place(cv, f'cloud {i + 1}', skym.cloud, x, y, z, L, seed=i,
                               top=(176, 176, 196), bottom=(140, 144, 170)))
    return recs
