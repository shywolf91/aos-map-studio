"""Yulehaven Isles art pass (separate from the graybox; it must not change gameplay geometry).

    art_west(cv, rep, S, rng)   BEFORE the mirror: decoration geometry on the west half + axis halves - string lights
                                under the eaves, candles in every window, door wreaths, chimneys, ship and trawler
                                lanterns and mast lights, bonfire embers, spruce/pine/juniper groves (OS seed)
    paint(cv, S, seed)          AFTER the mirror and the one-offs: every voxel coloured from its material with
                                coherent noise; patchy snow (dusted roofs, drifts against walls, never large flat
                                snowfields); the painted sea (deep -> shallows -> wading lanes)
    finish(cv)                  baked light + AO, cool twilight grade, glow bake, brightness rules, palette nudge

Geometry the art adds: lights/candles/wreaths on walls and eaves, chimneys on roofs, trees in the groves (kept off the
spawn squares, the front band, the anchors, doors and walkways), lanterns. Everything else is a recolour.
Palette rules [USER]: dark granite, weathered timber, falu red / ochre paint and evergreens do the work; snow capped
at max channel 212, never a large flat snowfield; floors luma >= 40.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage as ndi

from aosmap.kit import color, noise, veg
from aosmap.kit.color import clamp8, mix, shade

from yh_build import GC, box, col_down, put, top

WARM, YELLOW, WHITE, CYAN, GREEN, RED = (255, 175, 95), (255, 255, 95), (255, 255, 255), (95, 255, 255), \
    (95, 255, 95), (255, 95, 95)
GLOW_PALETTE = {WARM, YELLOW, WHITE, CYAN, GREEN, RED}
STRING = [WARM, YELLOW, GREEN, WARM, CYAN, YELLOW, RED, WARM]

SNOW = [(206, 210, 214), (196, 202, 210), (186, 194, 206), (200, 204, 212)]
WINTER_DETAILS = ('moss', 'deadbranch', 'roots', 'nest', 'lantern', 'ribbon', 'mushrooms')


def _glow(cv, x, y, z, c):
    """Glow source on an empty voxel that touches a solid face (never floats)."""
    if not cv.inside(x, y, z) or cv.solid[x, y, z]:
        return False
    if not any(cv.get(x + a, y + b, z + d) for a, b, d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1),
                                                           (0, 0, -1))):
        return False
    cv.add_glow(x, y, z, c)
    cv.mat[x, y, z] = cv.material('lamp')
    return True


# =============================================================================================== decoration (west)

def string_lights(cv, rep):
    """Bulbs hung under every eave line (2 apart, colours cycling), on the cord voxel under the overhang."""
    n = 0
    for (x0, x1, y0, y1, zt, ridge) in rep.get('eaves', []):
        if x0 > 255:
            continue
        z = zt                                        # first roof layer is zt-1; the bulb hangs at zt under it
        if ridge == 'x':
            lines = [((x, y0 - 1) for x in range(x0 - 1, min(x1 + 1, 255) + 1)),
                     ((x, y1 + 1) for x in range(x0 - 1, min(x1 + 1, 255) + 1))]
        else:
            lines = [((x0 - 1, y) for y in range(y0 - 1, y1 + 2)), ((x1 + 1, y) for y in range(y0 - 1, y1 + 2))]
        for li, line in enumerate(lines):
            for i, (x, y) in enumerate(line):
                if x > 255:
                    continue
                if i % 3 == 0 and cv.solid[x, y, z - 1] and not cv.solid[x, y, z]:
                    if _glow(cv, x, y, z, STRING[(i // 2 + li * 3 + x) % len(STRING)]):
                        n += 1
    return n


def window_candles(cv, rep):
    n = 0
    for ((wx, wy), zb, ax) in rep.get('window_lights', []):
        if wx > 255:
            continue
        # the opening's lower cells: one candle per window, alternating sides
        if (wx + wy + zb) % 3:                         # a candle in every third window keeps the paint readable
            continue
        c = WARM if (wx + wy) % 3 else YELLOW
        if _glow(cv, wx, wy, zb, c):
            n += 1
    return n


def wreaths(cv, rep):
    """Evergreen ring (3 x 3 with a hole) + red bow on the wall beside each door, 1 voxel proud of the wall."""
    n = 0
    for (name, side, (x0, x1, y0, y1), fz) in rep.get('doors', []):
        if x0 > 255:
            continue
        zc = fz - 3                                     # beside the door, on the wall face
        if side in 'NS':
            yy = y0 - 1 if side == 'N' else y1 + 1
            cx = x0 - 3
            ring = [(cx + a, yy, zc + b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0)]
        else:
            xx = x0 - 1 if side == 'W' else x1 + 1
            cy = y0 - 3
            ring = [(xx, cy + a, zc + b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0)]
        if any(cv.solid[p] for p in ring):
            continue
        for (x, y, z) in ring:
            put(cv, x, y, z, 'leaf', (40, 86, 52))
        x, y, z = ring[-2]
        cv.mat[x, y, z] = cv.material('ribbon')
        cv.rgb[x, y, z] = (178, 34, 40)
        # attach: the ring touches the wall voxel behind it? if not, a hook voxel
        n += 1
    return n


def chimneys(cv, rep, rng):
    n = 0
    for b in rep.get('buildings', []):
        x0, x1, y0, y1, rz, fz = b['box']
        if x0 > 255 or b['name'].startswith(('trawler', 'boathouse', 'fish shed')):
            continue
        cx = x0 + 2 + int(rng.integers(0, max(1, x1 - x0 - 4)))
        cy = y0 + 2 + int(rng.integers(0, max(1, y1 - y0 - 4)))
        t = top(cv, cx, cy)
        if t >= fz - 3:
            continue
        box(cv, cx, cx + 1, cy, cy + 1, t - 3, t - 1, 'stone')
        n += 1
    return n


def lanterns(cv, rep):
    n = 0
    for (x, y, z) in rep.get('lanterns', []):
        if x > 255:
            continue
        for (a, b, c) in ((x, y, z), (x - 1, y, z), (x, y - 1, z), (x, y + 1, z), (x, y, z + 1)):
            if _glow(cv, a, b, c, WARM):
                n += 1
                break
    return n


def mast_lights(cv, rep):
    """Trawler mast dressed with lights: stays from the masthead to bow and stern with bulbs every 2."""
    from aosmap.kit.canvas import line_points
    n = 0
    m = rep.get('trawler_mast')
    if m:
        mx, my, mz, yb, ys, zd = m
        for (ty, tz) in ((yb, zd), (ys, zd - 6)):
            pts = line_points(mx, my, mz, mx, ty, tz)
            for i, (a, b, c) in enumerate(pts):
                if not cv.solid[a, b, c]:
                    if i % 3 == 1:
                        cv.add_glow(a, b, c, STRING[i % len(STRING)])
                        cv.mat[a, b, c] = cv.material('lamp')
                        n += 1
                    else:
                        put(cv, a, b, c, 'rope')
    for (mx, my) in rep.get('ship_masts', []):
        for k, z in enumerate(range(30, 48, 3)):
            _glow(cv, mx - 1, my, z, STRING[k % len(STRING)])
    return n


def embers(cv, rep, S):
    b = rep.get('bonfire')
    if not b:
        return 0
    cx, cy, r = S['bonfire']
    g = b['g']
    n = 0
    for x in range(cx - 3, 256):
        for y in range(cy - 3, cy + 4):
            if math.hypot(x - cx + 0.5, y - cy) < 2.6 and (x * 7 + y * 3) % 4 != 0:
                cv.add_glow(x, y, g, WARM if (x + y) % 3 else RED)
                n += 1
    return n


def groves(cv, rep, S, rng):
    """Spruce / pine / juniper groves on the west half: kit conifers and bushes with three random winter details,
    two-palette blends. Never on the spawn squares, the front band, the anchors, the strip, doors or walkways."""
    spruce = veg.palette_family([(30, 64, 48), (40, 78, 56), (52, 90, 60), (38, 72, 66), (58, 84, 52)], n=10)
    juniper = veg.palette_family([(54, 80, 62), (70, 92, 64), (86, 96, 70)], n=6)
    allowed = {cv.materials[m] for m in ('rock', 'turf', 'beach') if m in cv.materials}
    T = cv.tops()
    placed = []
    doors = [(d[2][0], d[2][2]) for d in rep.get('doors', [])]
    counts = {'conifer': 0, 'bush': 0}
    dets = {}

    def ok(x, y, r=3):
        if not (r + 2 <= x <= 250 - r and r + 2 <= y <= 509 - r):
            return False
        if 139 <= x <= 214 and 230 <= y <= 282:                         # front band + anchors stay open
            return False
        if cv.keep[x - r:x + r + 1, y - r:y + r + 1].any():
            return False
        t = T[x - 1:x + 2, y - 1:y + 2]
        if t.max() - t.min() > 2 or t.max() >= 61:
            return False
        if cv.mat[x, y, int(T[x, y])] not in allowed:
            return False
        if cv.solid[x - r:x + r + 1, y - r:y + r + 1, max(0, int(T[x, y]) - 24):int(T[x, y]) - 1].any():
            return False                                               # nothing built above / beside
        for (dx_, dy_) in doors:
            if abs(dx_ - x) < 7 and abs(dy_ - y) < 7:
                return False
        for (px, py) in placed:
            if (px - x) ** 2 + (py - y) ** 2 < 36:
                return False
        return True
    for (gx, gy, R) in S['groves']:
        want = int(R * 1.3)
        tries = 0
        while want > 0 and tries < 900:
            tries += 1
            a, rr = rng.random() * 6.283, R * math.sqrt(rng.random())
            x, y = int(gx + rr * math.cos(a)), int(gy + rr * math.sin(a))
            if not ok(x, y):
                continue
            g = int(T[x, y])
            if rng.random() < 0.78:
                info = veg.conifer(cv, rng, x, y, g, spruce, h=int(rng.integers(12, 24)),
                                   details=veg.pick_details(rng, allow=WINTER_DETAILS), clear=int(rng.integers(4, 6)))
            else:
                info = veg.bush(cv, rng, x, y, g, juniper, details=veg.pick_details(
                    rng, allow=('moss', 'roots', 'mushrooms', 'fruit')))
            counts[info['species']] = counts.get(info['species'], 0) + 1
            for d in info['details']:
                dets[d] = dets.get(d, 0) + 1
            placed.append((x, y))
            want -= 1
    rep['trees'] = placed
    return {'trees': len(placed), 'by_species': counts, 'details': dets}


def art_west(cv, rep, S, rng):
    out = {}
    out['string_lights'] = string_lights(cv, rep)
    out['window_candles'] = window_candles(cv, rep)
    out['wreaths'] = wreaths(cv, rep)
    out['chimneys'] = chimneys(cv, rep, rng)
    out['lanterns'] = lanterns(cv, rep)
    out['mast_lights'] = mast_lights(cv, rep)
    out['embers'] = embers(cv, rep, S)
    out['groves'] = groves(cv, rep, S, rng)
    return out


# =============================================================================================== one-off glow

def oneoff_glow(cv, rep):
    """Glow for the post-mirror landmarks: lighthouse lamp + helix of lights, spruce star + baubles, chapel candles
    and windows, ice-camp fire, snowman lanterns."""
    n = 0
    L = rep.get('lighthouse')
    if L:
        for (x, y, z) in L['lamp']:
            cv.add_glow(x, y, z, YELLOW if z % 2 else WHITE)
            n += 1
        cx, cy = L['c']
        R = L['R'] + 0.6
        for k in range(0, 260):                                     # helix of lights round the tower
            a = k * 0.32
            z = L['g'] - 2 - k // 10
            if z <= L['zlamp'] + 1:
                break
            x, y = int(round(cx + 0.5 + R * math.cos(a))), int(round(cy + 0.5 + R * math.sin(a)))
            if k % 4 == 0 and _glow(cv, x, y, z, STRING[(k // 4) % len(STRING)]):
                n += 1
    S_ = rep.get('spruce')
    if S_:
        sx, sy = 256, 192
        tip = S_['tip']
        for (a, b, c) in ((0, 0, -1), (0, 0, -2), (1, 0, -1), (-1, 0, -1), (0, 1, -1), (0, -1, -1)):
            x, y, z = sx + a, sy + b, tip + c
            if not cv.solid[x, y, z]:
                cv.set(x, y, z, YELLOW, 'lamp')
                cv.add_glow(x, y, z, YELLOW)
                n += 1
        lm = cv.materials.get('leaf')
        cols = [RED, YELLOW, CYAN, WARM, GREEN]
        k = 0
        for x in range(sx - 10, sx + 11):
            for y in range(sy - 10, sy + 11):
                for z in range(tip, S_['g']):
                    if cv.mat[x, y, z] == lm and not cv.solid[x, y, z + 1] and ((x * 13 + y * 7 + z * 5) % 17 == 0):
                        if _glow(cv, x, y, z + 1, cols[k % 5]):
                            k += 1
        n += k
    for (x, y, z) in rep.get('chapel_candles', []):
        if _glow(cv, x, y, z, WARM):
            n += 1
    for (x, y, z) in rep.get('chapel_windows', []):
        for dz in range(0, 4):
            if _glow(cv, x, y, z - dz, WARM if dz % 2 else YELLOW):
                n += 1
                break
    ic = rep.get('ice_camp')
    if ic:
        x, y, z = ic['fire']
        for (a, b) in ((0, 0), (1, 0), (0, 1)):
            if _glow(cv, x + a, y + b, z - 1, WARM):
                n += 1
    for (x, y, z) in rep.get('snowman_lanterns', []):
        if _glow(cv, x, y, z - 1, WARM):
            n += 1
    return n


# =============================================================================================== paint

def _N(tag, cell, seed, octaves=2):
    return noise.fbm2((512, 512), cell, octaves, tag, seed)


def paint(cv, S, seed):
    """Material -> colour for every solid voxel (glow sources untouched)."""
    m = cv.mat
    solid = cv.solid & ~cv.nolight
    X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    T = cv.tops()
    nA = _N('pA', 9, seed, 3)
    nB = _N('pB', 23, seed, 3)
    nS = _N('snow', 14, seed, 3)
    names = {v: k for k, v in cv.materials.items()}
    xs, ys, zs = np.nonzero(solid)
    mats = m[xs, ys, zs]
    h = noise.hash3(xs, ys, zs, 11)
    a = nA[xs, ys]
    b = nB[xs, ys]
    out = np.zeros((len(xs), 3))
    is_top = zs == T[xs, ys]
    sky_open = is_top
    # land/sea distance for the painted sea and beach banding
    land = T < 63
    to_sea = ndi.distance_transform_edt(land)          # land cells: distance to the nearest water column
    to_land = ndi.distance_transform_edt(~land)        # water cells: distance to the nearest land column

    def sel(*ns):
        ids = [cv.materials[n] for n in ns if n in cv.materials]
        return np.isin(mats, ids)

    def ramp(stops, t):
        return color.ramp(stops, np.clip(t, 0, 1))

    # ---------------------------------------------------------------- terrain
    k = sel('rock', 'hop', 'arch', 'boulder', 'footing')
    granite = ramp([(0.0, (70, 72, 80)), (0.35, (88, 88, 96)), (0.6, (104, 98, 102)), (0.8, (118, 108, 106)),
                    (1.0, (96, 100, 110))], a[k] * 0.7 + h[k] * 0.3)
    lich = (b[k] > 0.58) & (h[k] > 0.4)
    granite[lich] = granite[lich] * 0.55 + np.array([96, 104, 72]) * 0.45
    out[k] = granite
    k = sel('turf')
    out[k] = ramp([(0.0, (70, 78, 58)), (0.4, (84, 88, 62)), (0.7, (98, 86, 70)), (1.0, (78, 70, 66))],
                  a[k] * 0.6 + h[k] * 0.4)
    k = sel('spawn', 'front', 'anchor')
    mix_t = a[k] * 0.6 + h[k] * 0.4
    out[k] = ramp([(0.0, (82, 86, 66)), (0.35, (96, 94, 74)), (0.6, (110, 104, 90)), (1.0, (92, 92, 96))], mix_t)
    an = sel('anchor')
    out[an] = ramp([(0.0, (104, 100, 98)), (0.5, (118, 112, 106)), (1.0, (96, 96, 104))], h[an] * 0.7 + a[an] * 0.3)
    k = sel('beach')
    d = to_sea[xs[k], ys[k]]
    sand = ramp([(0.0, (110, 102, 92)), (0.5, (128, 120, 106)), (1.0, (98, 94, 92))], h[k] * 0.6 + a[k] * 0.4)
    weed = d <= 2.5
    sand[weed] = sand[weed] * 0.5 + np.array([70, 76, 54]) * 0.5
    out[k] = sand
    k = sel('ice')
    out[k] = ramp([(0.0, (132, 170, 184)), (0.5, (150, 184, 196)), (1.0, (122, 158, 178))], h[k] * 0.5 + b[k] * 0.5)
    k = sel('iceberg')
    zz = zs[k]
    out[k] = ramp([(0.0, (198, 210, 212)), (0.5, (160, 196, 206)), (1.0, (110, 160, 180))], (zz - 10) / 52.0 +
                  (h[k] - 0.5) * 0.15)
    k = sel('sea')
    ds = to_land[xs[k], ys[k]]
    t = np.clip(ds / 40.0, 0, 1)
    sea = ramp([(0.0, (66, 112, 114)), (0.15, (50, 90, 100)), (0.45, (36, 66, 82)), (1.0, (28, 50, 70))], t)
    sea += ((b[k] - 0.5) * 12)[:, None]
    lane = np.zeros(len(xs), bool)
    for ((ax0, ay0), (ax1, ay1)) in S['shallows']:
        for xm in (False, True):
            X0, X1 = (512 - ax1, 512 - ax0) if xm else (ax0, ax1)
            lane |= (xs >= X0) & (xs <= X1) & (np.abs(ys - (ay0 + ay1) / 2) <= 3)
    lk = lane[k]
    sea[lk] = sea[lk] * 0.45 + np.array([84, 128, 122]) * 0.55
    out[k] = sea
    # ---------------------------------------------------------------- buildings and timber
    k = sel('wall_red')
    board = (noise.hash3(xs[k] // 1, ys[k] // 1, zs[k] // 4, 3) - 0.5) * 0.08
    out[k] = np.array([142, 46, 40]) * (1 + board)[:, None] + ((h[k] - 0.5) * 10)[:, None]
    k = sel('wall_ochre')
    out[k] = np.array([184, 132, 58]) * (1 + (noise.hash3(xs[k], ys[k], zs[k] // 4, 5) - 0.5) * 0.08)[:, None]
    k = sel('trim')
    out[k] = (194, 190, 178)
    k = sel('roof')
    out[k] = ramp([(0.0, (56, 54, 60)), (0.5, (66, 62, 64)), (1.0, (50, 56, 58))], h[k] * 0.5 + a[k] * 0.5)
    k = sel('timber', 'post', 'mast')
    out[k] = ramp([(0.0, (88, 72, 60)), (0.5, (108, 90, 72)), (1.0, (96, 86, 80))], h[k])
    k = sel('plank', 'deck', 'stair', 'floor')
    out[k] = ramp([(0.0, (112, 92, 70)), (0.5, (132, 108, 80)), (1.0, (120, 104, 88))], h[k] * 0.7 + a[k] * 0.3)
    k = sel('furniture', 'log')
    out[k] = ramp([(0.0, (86, 64, 48)), (1.0, (110, 82, 58))], h[k])
    k = sel('hull_red')
    out[k] = np.array([126, 38, 34]) + ((h[k] - 0.5) * 12)[:, None]
    k = sel('hull_dark')
    out[k] = np.array([54, 58, 66]) + ((h[k] - 0.5) * 10)[:, None]
    k = sel('crate', 'pot')
    out[k] = ramp([(0.0, (130, 100, 66)), (0.5, (150, 118, 76)), (1.0, (116, 92, 70))], h[k])
    pk = sel('pot')
    out[pk] = out[pk] * 0.7 + np.array([150, 140, 110]) * 0.3
    k = sel('present')
    pal = np.array([(170, 40, 44), (44, 112, 70), (196, 160, 60), (60, 92, 160), (150, 60, 140), (196, 120, 50)])
    pid = (noise.hash3(xs[k] // 3, ys[k] // 3, 0, 9) * len(pal)).astype(int) % len(pal)
    out[k] = pal[pid]
    k = sel('ribbon', 'mail', 'buoy')
    out[k] = (178, 36, 40)
    by = sel('buoy')
    stripe = (zs[by] % 2 == 0)
    o = out[by]
    o[stripe] = (196, 194, 186)
    out[by] = o
    k = sel('stone', 'stone_dk')
    out[k] = ramp([(0.0, (106, 104, 104)), (0.5, (128, 124, 120)), (1.0, (114, 112, 116))], h[k] * 0.6 + a[k] * 0.4)
    sd = sel('stone_dk')
    out[sd] = out[sd] * 0.78
    k = sel('straw')
    out[k] = ramp([(0.0, (176, 138, 66)), (0.5, (198, 162, 84)), (1.0, (186, 150, 74))], h[k])
    k = sel('canvas', 'tent')
    out[k] = ramp([(0.0, (168, 104, 60)), (1.0, (186, 132, 76))], h[k])
    k = sel('fish')
    out[k] = (172, 160, 132)
    k = sel('rope')
    out[k] = (150, 128, 90)
    k = sel('letter')
    out[k] = (204, 198, 180)
    k = sel('snowman')
    out[k] = ramp([(0.0, (200, 204, 210)), (1.0, (182, 190, 204))], h[k])
    k = sel('bell')
    out[k] = (176, 142, 64)
    k = sel('tag')
    out[k] = (178, 34, 40)
    k = sel('glass')
    out[k] = (120, 150, 160)
    k = sel('ember')
    out[k] = (150, 66, 40)
    k = sel('team')
    out[k] = (200, 200, 200)
    # leaves / bark keep the vegetation colours (set by kit veg); just carry them over
    keepc = sel('leaf', 'bark', 'sky')
    out[keepc] = cv.rgb[xs[keepc], ys[keepc], zs[keepc]]
    # ---------------------------------------------------------------- patchy snow
    terrain_ids = sel('rock', 'turf', 'beach', 'spawn', 'front', 'anchor', 'hop', 'arch', 'boulder', 'footing',
                      'stone', 'stone_dk')
    roofs = sel('roof')
    slope = np.zeros((512, 512))
    slope = np.maximum(np.abs(np.roll(T, 1, 0) - T), np.abs(np.roll(T, 1, 1) - T))
    sl = slope[xs, ys]
    sn = nS[xs, ys]
    # drifts: tops next to a higher neighbour (wall bases, rock steps, sheltered corners)
    shelter = (np.roll(T, 1, 0) < T - 2) | (np.roll(T, -1, 0) < T - 2) | (np.roll(T, 1, 1) < T - 2) | \
              (np.roll(T, -1, 1) < T - 2)
    sh = shelter[xs, ys]
    snow_t = is_top & terrain_ids & (sl <= 1) & ((sn > 0.62) | (sh & (sn > 0.5)))
    snow_t &= ~((xs >= 98) & (xs <= 138) & (ys >= 236) & (ys <= 276) & (sn < 0.68))   # lighter on the spawn squares
    edge = is_top & terrain_ids & (sl <= 1) & (sn > 0.59) & ~snow_t & (h > 0.5)       # soft dithered rim, 1 band
    snow_t &= to_sea[xs, ys] > 2
    snow_r = is_top & roofs & (sn > 0.5)
    snow_l = is_top & sel('leaf') & (h > 0.6)
    pick = (noise.hash3(xs, ys, zs, 4) * len(SNOW)).astype(int) % len(SNOW)
    sc = np.array(SNOW)[pick]
    for msk, f in ((snow_t, 0.86), (edge, 0.45), (snow_r, 0.82), (snow_l, 0.38)):
        out[msk] = out[msk] * (1 - f) + sc[msk] * f
    # thin dusting on top of beams, rails, boulders and hulls (not timber walls)
    dust = is_top & sel('plank', 'deck', 'hull_red', 'hull_dark', 'boulder', 'crate', 'pot', 'stone') & (h > 0.6)
    out[dust] = out[dust] * 0.4 + sc[dust] * 0.6
    cv.rgb[xs, ys, zs] = np.clip(np.rint(out), 0, 255).astype(np.uint8)
    return {'snow_terrain_tops': int(snow_t.sum()), 'terrain_tops': int((is_top & terrain_ids).sum()),
            'snow_roofs': int(snow_r.sum())}


# =============================================================================================== finish

def finish(cv, target_median=96.0, tint=(0.97, 0.99, 1.05)):
    """Baked light + AO, cool twilight grade (glow stays full), brightness rules, glow bake, palette nudge."""
    surf = color.lighting(cv)
    T = cv.tops()
    X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    L = color.luma(cv.rgb[X, Y, T].astype(float) * np.array(tint))
    k = float(np.clip(target_median / max(np.median(L), 1.0), 0.6, 1.05))
    grade = tuple(k * t for t in tint)
    m = cv.solid & ~cv.nolight
    c = cv.rgb[m].astype(np.float32) * np.array(grade, np.float32)
    cv.rgb[m] = np.clip(c, 0, 255).astype(np.uint8)
    bright = color.enforce_brightness(cv, floor_min=41)
    stored, n_src = bake_glow_fast(cv, surf)
    srcs = {(x, y, z) for (x, y, z, _) in cv.glow}
    nudged = 0
    for key in list(stored):
        if key in srcs:
            continue
        cc = tuple(int(v) for v in cv.rgb[key])
        if cc in GLOW_PALETTE:
            cv.rgb[key] = (max(0, cc[0] - 1), cc[1], cc[2])
            nudged += 1
    return stored, {'grade': [round(g, 3) for g in grade], 'brightness': bright, 'glow_sources': n_src,
                    'glow_lit_voxels': len(stored) - n_src, 'palette_nudged': nudged}


def bake_glow_fast(cv, surf, radius=6.5, strength=0.32):
    """Same model as aosmap.kit.color.bake_glow (knowledge base §11.4), vectorised per source
    (copied from scenes/frostbell_hollow/fh_art.py)."""
    srcs, seen = [], set()
    for (x, y, z, c) in cv.glow:
        if (x, y, z) in seen or not cv.inside(x, y, z) or not cv.solid[x, y, z]:
            continue
        seen.add((x, y, z))
        srcs.append((x, y, z, c))
    R = int(math.ceil(radius))
    o = np.arange(-R, R + 1)
    DX, DY, DZ = np.meshgrid(o, o, o, indexing='ij')
    D = np.sqrt(DX ** 2 + DY ** 2 + DZ ** 2)
    W = np.where((D < radius) & (D > 0), (1 - D / radius) * strength, 0.0)
    acc = {}
    for (x, y, z, c) in srcs:
        xs, ys, zs = x + DX, y + DY, z + DZ
        ok = (W > 0) & (xs >= 0) & (xs < 512) & (ys >= 0) & (ys < 512) & (zs >= 0) & (zs < 64)
        xs, ys, zs, w = xs[ok], ys[ok], zs[ok], W[ok]
        s = surf[xs, ys, zs]
        for (a, b, cc, ww) in zip(xs[s], ys[s], zs[s], w[s]):
            k = (int(a), int(b), int(cc))
            v = acc.get(k)
            if v is None:
                acc[k] = [c[0] * ww, c[1] * ww, c[2] * ww]
            else:
                v[0] += c[0] * ww
                v[1] += c[1] * ww
                v[2] += c[2] * ww
    stored = {}
    for k, a in acc.items():
        if k in seen:
            continue
        orig = tuple(int(v) for v in cv.rgb[k])
        stored[k] = orig
        cv.rgb[k] = (min(255, int(orig[0] + a[0])), min(255, int(orig[1] + a[1])), min(255, int(orig[2] + a[2])))
    for (x, y, z, c) in srcs:
        cv.rgb[x, y, z] = c
        stored[(x, y, z)] = tuple(c)
    return stored, len(srcs)
