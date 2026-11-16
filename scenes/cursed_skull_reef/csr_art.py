"""Cursed Skull Reef art pass (separate from the graybox; it must not change gameplay geometry).

    art_west(cv, rep, S, rng)   BEFORE the mirror: decoration on the west half + axis halves - window candles, dock
                                lamps, ship and fort lanterns, cursed green lights, torn sails and flags, and the
                                vegetation groves (palms, dead trees, mangroves; OS seed, three random details each)
    oneoff_glow(cv, rep)        AFTER the one-offs: tavern lamps, lighthouse brazier, rum-dock lamps, gallows lamp,
                                heeled-brig lanterns
    paint(cv, S, seed)          every voxel coloured from its material with coherent noise (x folded so both teams
                                see the same patterns); the painted sea: deep -> shallows, storm foam streaks and the
                                maelstrom spiral in the south lagoon
    finish(cv)                  baked light + AO, cool moonlit grade, brightness rules, glow bake, palette nudge

Geometry the art adds: lanterns on walls, posts and masts, torn sails under yards, flags, plants in the groves
(kept off the spawn squares, the front band, the anchors, the neck, doors and walkways). Everything else is a
recolour. Palette rules [USER]: bright moonlit night, floors luma >= 40, whites capped at 212.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage as ndi

from aosmap.kit import color, noise, veg
from aosmap.kit.canvas import line_points
from aosmap.kit.color import clamp8, mix, shade

from csr_build import box, put, top

WARM, YELLOW, WHITE, CYAN, GREEN, RED = (255, 175, 95), (255, 255, 95), (255, 255, 255), (95, 255, 255), \
    (95, 255, 95), (255, 95, 95)
GLOW_PALETTE = {WARM, YELLOW, WHITE, CYAN, GREEN, RED}

PLANT_DETAILS = {
    'palm': ('coconuts', 'deadfronds', 'vines', 'roots', 'lantern', 'nest', 'moss', 'rope'),
    'dead': ('moss', 'rope', 'lantern', 'nest', 'roots', 'mushrooms', 'deadbranch', 'cage'),
    'mangrove': ('roots', 'vines', 'moss', 'fruit', 'mushrooms', 'nest', 'lantern'),
}


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


def _glow_near(cv, x, y, z, c):
    for (a, b, d) in ((0, 0, 0), (-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, 1), (0, 0, -1)):
        if _glow(cv, x + a, y + b, z + d, c):
            return 1
    return 0


# =============================================================================================== plants

def _crown_blend(pal, rng):
    i = int(rng.integers(0, len(pal)))
    return pal[i], pal[(i + 1 + int(rng.integers(0, 2))) % len(pal)]


def _extras(cv, rng, x, y, g, h, details, crown, bark, leaf, tipz):
    """Custom details (the kit's _decorate covers moss/roots/deadbranch/fruit/vines/nest/lantern/mushrooms)."""
    if 'coconuts' in details and tipz is not None:
        for (a, b) in ((1, 0), (-1, 0), (0, 1), (0, -1))[:int(rng.integers(2, 5))]:
            if not cv.get(x + a, y + b, tipz + 1):
                cv.set(x + a, y + b, tipz + 1, (110, 82, 50), 'coconut')
    if 'deadfronds' in details and tipz is not None:
        for k in range(1, 4):
            if not cv.get(x + 1, y, tipz + k):
                cv.set(x + 1, y, tipz + k, (150, 128, 80), 'frond')
            else:
                break
    if 'rope' in details:
        z = g - 2 - int(h * 0.3)
        if cv.get(x, y, z):
            for (a, b) in ((1, 0), (0, 1)):
                if not cv.get(x + a, y + b, z):
                    cv.set(x + a, y + b, z, (150, 130, 92), 'rope')
                    break
    if 'cage' in details and crown:
        px, py, pz = sorted(crown, key=lambda p: -p[2])[0]
        for k in range(1, 3):
            if not cv.get(px, py, pz + k):
                cv.set(px, py, pz + k, (64, 62, 66), 'iron' if k == 1 else 'cage')
            else:
                break


@veg._connected
def palm(cv, rng, x, y, g, pal, details=None, h=None):
    """Leaning coconut palm: banded trunk curving to a crown of 6-8 drooping fronds (gradient base -> tip)."""
    details = details or veg.pick_details(rng, PLANT_DETAILS['palm'])
    h = h or int(rng.integers(10, 18))
    lean = rng.random() * 6.283
    lx, ly = math.cos(lean), math.sin(lean)
    bark = clamp8(mix((112, 92, 70), (138, 116, 86), rng.random()))
    px, py = float(x), float(y)
    cx, cy, cz = x, y, g - 1
    prev = (x, y, g - 1)
    for k in range(h):
        t = k / h
        px, py = x + lx * 4.5 * t * t, y + ly * 4.5 * t * t
        q = (int(round(px)), int(round(py)), g - 1 - k)
        for (a, b, c) in line_points(*prev, *q):
            cv.set(a, b, c, shade(bark, 0.86 + 0.14 * ((c // 2) % 2)), 'bark')
        prev = q
    cx, cy, cz = prev
    fa, fb = _crown_blend(pal, rng)
    crown = []
    n = int(rng.integers(6, 9))
    for i in range(n):
        a = i * 6.283 / n + rng.uniform(-0.25, 0.25)
        L = rng.uniform(4.5, 7.5)
        last = (cx, cy, cz)
        for s in range(1, int(L) + 1):
            f = s / L
            q = (int(round(cx + math.cos(a) * s)), int(round(cy + math.sin(a) * s)),
                 int(round(cz - 1.2 + 3.2 * f * f)))
            for (u, v, w) in line_points(*last, *q):
                if not cv.get(u, v, w):
                    cv.set(u, v, w, veg._blend(fa, fb, f), 'frond')
                    crown.append((u, v, w))
            last = q
    for (u, v, w) in ((cx, cy, cz - 1), (cx + 1, cy, cz), (cx - 1, cy, cz), (cx, cy + 1, cz), (cx, cy - 1, cz)):
        if not cv.get(u, v, w):
            cv.set(u, v, w, fa, 'frond')
            crown.append((u, v, w))
    kit = tuple(d for d in details if d in veg.DETAILS)
    veg._decorate(cv, rng, x, y, g, h, kit, crown, bark, fa)
    _extras(cv, rng, cx, cy, g, h, details, crown, bark, fa, cz)
    return {'species': 'palm', 'h': h, 'details': details}


@veg._connected
def dead_tree(cv, rng, x, y, g, pal, details=None, h=None):
    """Gnarled dead tree: twisting trunk, 4-6 jagged bare branches reaching up and out, sparse grey moss tufts."""
    details = details or veg.pick_details(rng, PLANT_DETAILS['dead'])
    h = h or int(rng.integers(8, 15))
    bark = clamp8(mix((96, 90, 86), (124, 110, 98), rng.random()))
    prev = (x, y, g - 1)
    pts = []
    for k in range(h):
        q = (x + int(round(math.sin(k * 0.5 + rng.random()) * 0.8)), y + int(round(math.cos(k * 0.4) * 0.6)),
             g - 1 - k)
        for p in line_points(*prev, *q):
            cv.set(*p, shade(bark, 0.9 + 0.1 * (p[2] % 2)), 'bark')
            pts.append(p)
        prev = q
    crown = []
    for i in range(int(rng.integers(4, 7))):
        base = pts[int(len(pts) * rng.uniform(0.45, 0.95))]
        a = rng.random() * 6.283
        L = rng.uniform(3, 7)
        last = base
        for s in range(1, int(L) + 1):
            a += rng.uniform(-0.5, 0.5)
            q = (int(round(base[0] + math.cos(a) * s)), int(round(base[1] + math.sin(a) * s)),
                 int(round(base[2] - s * rng.uniform(0.4, 1.0))))
            for p in line_points(*last, *q):
                if not cv.get(*p):
                    cv.set(*p, shade(bark, 0.96), 'deadwood')
                    crown.append(p)
            last = q
    moss = pal[int(rng.integers(0, len(pal)))]
    for p in crown[::5]:
        if not cv.get(p[0], p[1], p[2] + 1):
            cv.set(p[0], p[1], p[2] + 1, moss, 'leaf')
    kit = tuple(d for d in details if d in veg.DETAILS)
    veg._decorate(cv, rng, x, y, g, h, kit, crown, bark, moss)
    _extras(cv, rng, x, y, g, h, details, crown, bark, moss, None)
    return {'species': 'dead', 'h': h, 'details': details}


@veg._connected
def mangrove(cv, rng, x, y, g, pal, details=None, h=None):
    """Mangrove: short trunk on arching stilt roots, a broad jagged crown (gradient top -> underside)."""
    details = details or veg.pick_details(rng, PLANT_DETAILS['mangrove'])
    h = h or int(rng.integers(6, 10))
    bark = clamp8(mix((92, 74, 58), (114, 92, 70), rng.random()))
    base = g - 3
    for k in range(3, h):
        cv.set(x, y, g - 1 - k, bark, 'bark')
    for i in range(5):
        a = i * 1.257 + rng.uniform(-0.2, 0.2)
        r = rng.uniform(2.5, 4.0)
        q = (int(round(x + math.cos(a) * r)), int(round(y + math.sin(a) * r)), g - 1)
        for p in line_points(x, y, base - 1, *q):
            if not cv.get(*p) or p[2] == g:
                cv.set(*p, shade(bark, 0.85), 'root')
    for z in range(base - 1, g):
        cv.set(x, y, z, bark, 'bark')
    fa, fb = _crown_blend(pal, rng)
    jag = veg._jag(rng)
    R = rng.uniform(3.5, 5.5)
    cz = g - h - 1
    crown = []
    for X in range(int(x - R - 2), int(x + R + 3)):
        for Y in range(int(y - R - 2), int(y + R + 3)):
            th = math.atan2(Y - y, X - x)
            for Z in range(int(cz - R * 0.6 - 1), int(cz + R * 0.5 + 1)):
                d = math.sqrt((X - x) ** 2 + (Y - y) ** 2 + ((Z - cz) * 1.7) ** 2)
                if d <= R * jag(th) and not cv.get(X, Y, Z):
                    cv.set(X, Y, Z, veg._blend(fb, fa, (Z - (cz - R * 0.6)) / (R * 1.1)), 'leaf')
                    crown.append((X, Y, Z))
    for z in range(cz, g - h + 1):
        cv.set(x, y, z, bark, 'bark')
    kit = tuple(d for d in details if d in veg.DETAILS)
    veg._decorate(cv, rng, x, y, g, h, kit, crown, bark, fa)
    _extras(cv, rng, x, y, g, h, details, crown, bark, fa, None)
    return {'species': 'mangrove', 'h': h, 'details': details}


SPECIES = {'palm': palm, 'dead': dead_tree, 'mangrove': mangrove}


def groves(cv, rep, S, rng):
    """Groves on the west half (mirrored): palms on the beaches and town, dead trees on the outer rocks, mangroves on
    the inner shores. Never on the spawn squares, the front band, the anchors, the neck, doors or walkways."""
    pal = {
        'palm': veg.palette_family([(62, 98, 44), (88, 118, 46), (112, 128, 52), (74, 110, 64), (128, 120, 58)], 10),
        'dead': veg.palette_family([(96, 110, 84), (120, 124, 96), (88, 100, 90)], 6),
        'mangrove': veg.palette_family([(48, 86, 52), (66, 102, 58), (84, 112, 60), (58, 94, 74)], 8),
    }
    allowed = {cv.materials[m] for m in ('rock', 'turf', 'sand') if m in cv.materials}
    T = cv.tops()
    placed = []
    doors = [(d[2][0], d[2][2]) for d in rep.get('doors', [])]
    counts, dets = {}, {}

    def ok(x, y, r=3):
        if not (r + 2 <= x <= 250 - r and r + 2 <= y <= 509 - r):
            return False
        if 136 <= x <= 216 and 230 <= y <= 282:
            return False
        if x >= 200 and 196 <= y <= 316:                                  # inner shores by the wrecks and neck
            return False
        if cv.keep[x - r:x + r + 1, y - r:y + r + 1].any():
            return False
        t = T[x - 1:x + 2, y - 1:y + 2]
        if t.max() - t.min() > 2 or t.max() >= 62:
            return False
        if cv.mat[x, y, int(T[x, y])] not in allowed:
            return False
        if cv.solid[x - r:x + r + 1, y - r:y + r + 1, max(0, int(T[x, y]) - 20):int(T[x, y]) - 1].any():
            return False
        for (dx_, dy_) in doors:
            if abs(dx_ - x) < 7 and abs(dy_ - y) < 7:
                return False
        for (px, py) in placed:
            if (px - x) ** 2 + (py - y) ** 2 < 30:
                return False
        return True
    for (gx, gy, R, kind) in S['groves']:
        want = int(R * 1.2)
        tries = 0
        while want > 0 and tries < 700:
            tries += 1
            a, rr = rng.random() * 6.283, R * math.sqrt(rng.random())
            x, y = int(gx + rr * math.cos(a)), int(gy + rr * math.sin(a))
            if not ok(x, y):
                continue
            k = kind if kind != 'mix' else ('palm', 'dead', 'mangrove')[int(rng.choice(3, p=[0.5, 0.3, 0.2]))]
            g = int(T[x, y])
            info = SPECIES[k](cv, rng, x, y, g, pal[k])
            counts[k] = counts.get(k, 0) + 1
            for d in info['details']:
                dets[d] = dets.get(d, 0) + 1
            placed.append((x, y))
            want -= 1
    return {'plants': len(placed), 'by_species': counts, 'details': dets}


# =============================================================================================== decoration (west)

def window_candles(cv, rep):
    n = 0
    for ((wx, wy), zb, ax) in rep.get('window_lights', []):
        if wx > 255 or (wx + wy + zb) % 3:
            continue
        if _glow(cv, wx, wy, zb, WARM if (wx + wy) % 3 else YELLOW):
            n += 1
    return n


def lanterns(cv, rep):
    n = 0
    for key, c in (('dock_lamps', WARM), ('galleon_lanterns', YELLOW), ('fort_torches', WARM),
                   ('bridge_ruin_lamps', GREEN), ('chest_glow', YELLOW)):
        for (x, y, z) in rep.get(key, []):
            if x <= 255:
                n += _glow_near(cv, x, y, z, c)
    A = rep.get('assist')
    if A:
        n += _glow_near(cv, *A['lantern'], GREEN)                         # cursed light on the crow's nest
        n += _glow_near(cv, *A['stern_lantern'], WARM)
    B = rep.get('brig')
    if B:
        n += _glow_near(cv, *B['stern_lantern'], YELLOW) + _glow_near(cv, *B['bow_lantern'], WARM)
    for (x, y, z) in rep.get('eye_glow', []):
        n += _glow_near(cv, x, y, z, GREEN)
    ch = rep.get('skull_chest')
    if ch:
        for (a, b) in ((0, 0), (-2, 0), (-2, 2)):
            n += _glow_near(cv, ch[0] + a, ch[1] + b, ch[2], YELLOW)
    return n


def sails_and_flags(cv, rep, rng):
    """Torn sails hanging under the galleon yards and furled on the brig yards, a tattered black flag on the fort."""
    n = 0
    for (my, ztop) in ((176, 32), (196, 22)):
        yz = ztop + 6
        for x in range(249, 256):
            for z in range(yz + 1, yz + 7):
                h = noise.hash3(np.array([x]), np.array([my]), np.array([z]), 21)[0]
                if (z - yz) > 2 + 4 * abs(math.sin(x * 1.3)) or h < 0.12:
                    break
                if not cv.solid[x, my, z]:
                    put(cv, x, my, z, 'sail')
                    n += 1
    for (mx, yc, mt) in rep.get('brig_masts', []):
        for zy in (mt + 4, mt + 12):
            for y in range(yc - 5, yc + 6):
                if not cv.solid[mx, y, zy + 1]:
                    put(cv, mx, y, zy + 1, 'sail')
                    n += 1
    f = rep.get('fort_flag')
    if f:
        x, y, z = f
        zt = z - 13
        for k in range(1, 6):
            for dz in range(0, 3 - (k // 3)):
                if not cv.solid[x, y - k, zt + dz]:
                    put(cv, x, y - k, zt + dz, 'flag')
                    n += 1
    return n


def art_west(cv, rep, S, rng):
    out = {}
    out['window_candles'] = window_candles(cv, rep)
    out['lanterns'] = lanterns(cv, rep)
    out['sails_flags'] = sails_and_flags(cv, rep, rng)
    out['groves'] = groves(cv, rep, S, rng)
    # nothing of a plant may hang over a spawn square (players spawn on the topmost voxel)
    b = S['spawn']['base']
    hs = S['spawn']['half']
    ids = [cv.materials[m] for m in ('leaf', 'bark', 'frond', 'root', 'deadwood', 'coconut', 'moss', 'vine', 'fruit',
                                     'mushroom', 'nest', 'ribbon', 'rope', 'iron', 'cage', 'blossom', 'lamp')
           if m in cv.materials]
    sl = (slice(b[0] - hs, b[0] + hs + 1), slice(b[1] - hs, b[1] + hs + 1), slice(0, 64))
    over = np.isin(cv.mat[sl], ids) & cv.solid[sl]
    cv.solid[sl][over] = False
    cv.mat[sl][over] = 0
    out['cleared_over_spawn'] = int(over.sum())
    return out


# =============================================================================================== one-off glow

def oneoff_glow(cv, rep):
    n = 0
    for (x, y, z) in rep.get('tavern_lamps', []):
        n += _glow_near(cv, x, y, z, WARM)
    L = rep.get('lighthouse')
    if L:
        for i, (x, y, z) in enumerate(L['brazier']):
            n += _glow_near(cv, x, y, z, WHITE if i % 2 else YELLOW)
    for (x, y, z) in rep.get('oneoff_lamps', []):
        n += _glow_near(cv, x, y, z, WARM)
    G = rep.get('gallows')
    if G:
        for (x, y, z) in G['lamps']:
            n += _glow_near(cv, x, y, z + 1, GREEN)
    hb = rep.get('heeled_brig')
    if hb:
        for (x, y, z) in hb['lamps']:
            n += _glow_near(cv, x, y, z, YELLOW)
    return n


# =============================================================================================== paint

def _N(tag, cell, seed, octaves=2):
    n = noise.fbm2((512, 512), cell, octaves, tag, seed)
    n[256:] = n[:256][::-1]                                               # fold x: both halves see the same field
    return n


def paint(cv, S, seed):
    """Material -> colour for every solid voxel (glow sources and plants keep theirs)."""
    m = cv.mat
    solid = cv.solid & ~cv.nolight
    T = cv.tops()
    nA = _N('pA', 9, seed, 3)
    nB = _N('pB', 23, seed, 3)
    xs, ys, zs = np.nonzero(solid)
    xf = np.where(xs > 255, 511 - xs, xs)
    mats = m[xs, ys, zs]
    h = noise.hash3(xf, ys, zs, 11)
    a = nA[xs, ys]
    b = nB[xs, ys]
    out = np.zeros((len(xs), 3))
    is_top = zs == T[xs, ys]
    land = T < 63
    to_sea = ndi.distance_transform_edt(land)
    to_land = ndi.distance_transform_edt(~land)

    def sel(*ns):
        ids = [cv.materials[n] for n in ns if n in cv.materials]
        return np.isin(mats, ids)

    def ramp(stops, t):
        return color.ramp(stops, np.clip(t, 0, 1))
    # ---------------------------------------------------------------- terrain
    k = sel('rock', 'boulder', 'footing', 'stone_dk')
    rock = ramp([(0.0, (70, 70, 78)), (0.35, (86, 84, 90)), (0.6, (100, 94, 92)), (0.85, (112, 104, 98)),
                 (1.0, (90, 92, 100))], a[k] * 0.7 + h[k] * 0.3)
    lich = (b[k] > 0.6) & (h[k] > 0.45)
    rock[lich] = rock[lich] * 0.55 + np.array([84, 104, 70]) * 0.45
    out[k] = rock
    k = sel('turf')
    out[k] = ramp([(0.0, (60, 84, 50)), (0.35, (74, 98, 54)), (0.7, (92, 104, 58)), (1.0, (82, 88, 62))],
                  a[k] * 0.6 + h[k] * 0.4)
    k = sel('sand', 'neck', 'front', 'spawn')
    d = to_sea[xs[k], ys[k]]
    sand = ramp([(0.0, (150, 134, 104)), (0.5, (170, 152, 116)), (1.0, (158, 142, 112))], h[k] * 0.5 + a[k] * 0.5)
    wet = d <= 2.5
    sand[wet] = sand[wet] * 0.72 + np.array([96, 98, 92]) * 0.28
    weed = (d > 2.5) & (d <= 4) & (h[k] > 0.55)
    sand[weed] = sand[weed] * 0.6 + np.array([78, 92, 56]) * 0.4
    out[k] = sand
    # driftwood boardwalk patches on the spawn squares (harbour spawns): plank strips along y
    sp = sel('spawn') & is_top
    bw = (noise.hash3(xf[sp] // 3, ys[sp] // 9, 0, 5) > 0.45)
    o = out[sp]
    plank = np.array([132, 108, 80]) * (0.9 + 0.12 * (((xf[sp] + ys[sp] // 9) % 3) == 0))[:, None]
    o[bw] = plank[bw] + ((h[sp][bw] - 0.5) * 14)[:, None]
    out[sp] = o
    k = sel('anchor')
    out[k] = ramp([(0.0, (96, 92, 92)), (0.5, (112, 106, 100)), (1.0, (92, 94, 102))], h[k] * 0.7 + a[k] * 0.3)
    k = sel('reef', 'coral')
    out[k] = ramp([(0.0, (124, 96, 100)), (0.4, (150, 108, 104)), (0.7, (118, 112, 120)), (1.0, (166, 128, 110))],
                  h[k] * 0.6 + b[k] * 0.4)
    # ---------------------------------------------------------------- sea (bottom layer, painted)
    k = sel('sea')
    ds = to_land[xs[k], ys[k]]
    t = np.clip(ds / 36.0, 0, 1)
    sea = ramp([(0.0, (60, 116, 130)), (0.12, (46, 94, 118)), (0.45, (34, 70, 104)), (1.0, (30, 56, 92))], t)
    # storm foam streaks: long wind-driven bands (folded noise, sheared)
    sx = xf[k].astype(float)
    sy = ys[k].astype(float)
    streak = np.sin(sx * 0.11 + sy * 0.045 + 3.0 * nB[xs[k], ys[k]]) * 0.5 + 0.5
    foam = (streak > 0.955) & (h[k] > 0.4) & (ds > 6)
    sea[foam] = sea[foam] * 0.68 + np.array([120, 148, 162]) * 0.32
    sea += ((b[k] - 0.5) * 14)[:, None]
    # shoreline surf ring
    surf = (ds >= 1) & (ds <= 2.2) & (h[k] > 0.4)
    sea[surf] = sea[surf] * 0.5 + np.array([150, 172, 176]) * 0.5
    # maelstrom spiral (south lagoon), symmetric about the axis
    mx, my = S['maelstrom']['c']
    R = S['maelstrom']['r']
    rr = np.hypot(xs[k] - mx + 0.5, ys[k] - my)
    ang = np.arctan2(ys[k] - my, np.abs(xs[k] - mx + 0.5))
    inm = rr <= R + 3
    arm = np.sin(2 * ang + rr * 0.42) * 0.5 + 0.5
    fall = np.clip(1 - rr / (R + 3), 0, 1)
    core = np.array([34, 54, 88])
    swirl = np.where((arm > 0.62)[:, None], np.array([140, 168, 176]), np.array([40, 74, 104]))
    mixf = (fall * 0.9)[:, None]
    blend = sea * (1 - mixf) + (swirl * (1 - fall[:, None] ** 3) + core * fall[:, None] ** 3) * mixf
    sea[inm] = blend[inm]
    out[k] = sea
    # ---------------------------------------------------------------- buildings, timber, ships
    k = sel('wall')
    plaster = ramp([(0.0, (166, 150, 122)), (0.5, (178, 160, 128)), (1.0, (156, 146, 130))], h[k] * 0.4 + a[k] * 0.6)
    stain = (noise.hash3(xf[k] // 2, ys[k] // 2, zs[k] // 3, 9) > 0.78)
    plaster[stain] = plaster[stain] * 0.8 + np.array([110, 110, 90]) * 0.2
    out[k] = plaster
    k = sel('wall_dk', 'brick')
    out[k] = ramp([(0.0, (128, 90, 74)), (0.5, (142, 100, 80)), (1.0, (118, 92, 82))], h[k])
    k = sel('trim', 'timber', 'post', 'mast')
    out[k] = ramp([(0.0, (78, 62, 50)), (0.5, (96, 78, 60)), (1.0, (86, 74, 66))], h[k])
    k = sel('roof')
    out[k] = ramp([(0.0, (104, 60, 48)), (0.4, (122, 70, 54)), (0.7, (94, 72, 60)), (1.0, (112, 84, 60))],
                  h[k] * 0.5 + a[k] * 0.5)
    k = sel('plank', 'deck', 'stair', 'floor')
    out[k] = ramp([(0.0, (110, 88, 66)), (0.5, (130, 106, 78)), (1.0, (118, 100, 84))], h[k] * 0.7 + a[k] * 0.3)
    k = sel('furniture', 'chest', 'barrel')
    out[k] = ramp([(0.0, (92, 62, 42)), (1.0, (118, 82, 52))], h[k])
    bk = sel('barrel')
    hoop = (zs[bk] % 3 == 1)
    o = out[bk]
    o[hoop] = (70, 66, 64)
    out[bk] = o
    k = sel('hull')
    out[k] = ramp([(0.0, (58, 48, 44)), (0.5, (70, 56, 46)), (1.0, (62, 58, 56))], h[k] * 0.6 + a[k] * 0.4)
    k = sel('hull_trim')
    out[k] = (150, 118, 56)
    k = sel('crate', 'pot', 'net')
    out[k] = ramp([(0.0, (128, 100, 66)), (0.5, (146, 116, 76)), (1.0, (114, 92, 70))], h[k])
    k = sel('iron', 'cage')
    out[k] = ramp([(0.0, (58, 60, 66)), (1.0, (76, 74, 78))], h[k])
    k = sel('stone')
    out[k] = ramp([(0.0, (112, 108, 104)), (0.5, (128, 124, 116)), (1.0, (106, 108, 114))], h[k] * 0.6 + a[k] * 0.4)
    k = sel('skull_rock', 'bone')
    bone = ramp([(0.0, (164, 154, 128)), (0.4, (186, 176, 146)), (0.8, (200, 190, 160)), (1.0, (176, 168, 150))],
                h[k] * 0.4 + a[k] * 0.6)
    crack = noise.hash3(xf[k] // 2, ys[k] // 2, zs[k] // 2, 33) > 0.84
    bone[crack] = bone[crack] * 0.7
    mossy = is_top[k] & (b[k] > 0.5)
    bone[mossy] = bone[mossy] * 0.5 + np.array([92, 112, 76]) * 0.5
    out[k] = bone
    k = sel('gold')
    out[k] = (206, 168, 62)
    k = sel('sail')
    out[k] = ramp([(0.0, (150, 144, 124)), (1.0, (172, 162, 136))], h[k])
    k = sel('rope')
    out[k] = (146, 126, 90)
    k = sel('flag')
    out[k] = (58, 52, 56)
    k = sel('tag')
    out[k] = (214, 184, 96)
    k = sel('glass')
    out[k] = (120, 150, 150)
    k = sel('cloth')
    out[k] = (140, 60, 50)
    keepc = sel('leaf', 'bark', 'frond', 'root', 'deadwood', 'coconut', 'moss', 'vine', 'fruit', 'mushroom', 'nest',
                'ribbon', 'sky', 'blossom')
    out[keepc] = cv.rgb[xs[keepc], ys[keepc], zs[keepc]]
    cv.rgb[xs, ys, zs] = np.clip(np.rint(out), 0, 255).astype(np.uint8)
    return {'terrain_tops': int((is_top & sel('rock', 'turf', 'sand')).sum())}


# =============================================================================================== finish

def finish(cv, target_median=92.0, tint=(0.9, 0.98, 1.08)):
    """Baked light + AO, cool moonlit grade (glow stays full), brightness rules, glow bake, palette nudge."""
    surf = color.lighting(cv)
    T = cv.tops()
    X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    L = color.luma(cv.rgb[X, Y, T].astype(float) * np.array(tint))
    k = float(np.clip(target_median / max(np.median(L), 1.0), 0.6, 1.08))
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
    """Same model as aosmap.kit.color.bake_glow (knowledge base §11.4), vectorised per source."""
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
    acc = np.zeros(cv.solid.shape + (3,), np.float32)
    hit = np.zeros(cv.solid.shape, bool)
    for (x, y, z, c) in srcs:
        xs, ys, zs = x + DX, y + DY, z + DZ
        ok = (W > 0) & (xs >= 0) & (xs < 512) & (ys >= 0) & (ys < 512) & (zs >= 0) & (zs < 64)
        xs, ys, zs, w = xs[ok], ys[ok], zs[ok], W[ok]
        s = surf[xs, ys, zs]
        xs, ys, zs, w = xs[s], ys[s], zs[s], w[s]
        np.add.at(acc, (xs, ys, zs), (w[:, None] * np.array(c, np.float32)[None, :]))
        hit[xs, ys, zs] = True
    for (x, y, z, _) in srcs:
        hit[x, y, z] = False
    stored = {}
    hx, hy, hz = np.nonzero(hit)
    orig = cv.rgb[hx, hy, hz].copy()
    new = np.clip(orig.astype(np.float32) + acc[hx, hy, hz], 0, 255).astype(np.uint8)
    cv.rgb[hx, hy, hz] = new
    for i in range(len(hx)):
        stored[(int(hx[i]), int(hy[i]), int(hz[i]))] = tuple(int(v) for v in orig[i])
    for (x, y, z, c) in srcs:
        cv.rgb[x, y, z] = c
        stored[(x, y, z)] = tuple(c)
    return stored, len(srcs)
