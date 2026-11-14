"""Elderveil vegetation (art pass): old-growth groves on the graybox stand-in positions (the veg seed placed them;
the same seed drives every look here), understory, reeds and lily pads, the heart-tree showpiece and the giant
mushrooms.

Species: elder oak (buttress roots, limbs ending in lumpy crown masses, hanging moss), grey beech (tall smooth
trunk, dense oval crown), dark fir (drooping tiers, 4+ clear underneath), silver birch (thin pale trunk with dark
marks, airy crown), dead silver snag (broken limbs). Every plant gets THREE random details from a species list,
two-colour smooth gradients with per-tree hue variation, and is pruned to voxels face-connected to its trunk.
Rules kept: crowns never reach a keep zone (spawn squares + margin, anchors, front band, under-platform strip),
crown undersides stay >= 4 above the ground, nothing overwrites existing voxels.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage as ndi

from aosmap.kit import noise
from aosmap.kit.color import clamp8, mix, shade

PLANT_MATS = ('leaf', 'bark', 'moss', 'twig', 'fungus', 'flower', 'fern', 'bramble', 'reed', 'deadwood', 'lichen',
              'nest', 'berry', 'shroom')
KEEP_BLOCK = 1 | 2 | 4 | 8                       # spawn, anchor, front, under-platform
V11 = False                                      # set by ev_art for release 1.1 (richer crowns)

SPECIES_PAL = {
    'oak': [((46, 60, 40), (112, 116, 68)), ((44, 60, 44), (102, 110, 66)), ((50, 64, 40), (120, 120, 72))],
    'beech': [((44, 66, 52), (108, 122, 80)), ((50, 72, 50), (116, 126, 82))],
    'fir': [((24, 44, 46), (50, 78, 74)), ((26, 48, 52), (56, 84, 80)), ((22, 42, 40), (46, 72, 62))],
    'birch': [((76, 92, 62), (136, 140, 96)), ((82, 96, 66), (142, 142, 100))],
}
BARK = {'oak': (88, 70, 54), 'beech': (132, 128, 120), 'fir': (78, 60, 48), 'birch': (196, 190, 176),
        'snag': (150, 146, 140)}
DETAILS = {
    'oak': ('hanging_moss', 'ivy', 'shelf_fungus', 'nest', 'golden_leaves', 'hollow', 'mushrooms', 'flowers',
            'lichen', 'deadbranch'),
    'beech': ('ivy', 'shelf_fungus', 'golden_leaves', 'lichen', 'carved_rune', 'mushrooms', 'nest', 'flowers'),
    'fir': ('hanging_moss', 'cones', 'lichen', 'deadbranch', 'mushrooms', 'resin'),
    'birch': ('catkins', 'golden_leaves', 'lichen', 'flowers', 'mushrooms', 'shelf_fungus'),
    'snag': ('shelf_fungus', 'lichen', 'nest', 'ivy', 'hollow', 'mushrooms'),
}


class Plant:
    """Collects one plant's voxels, then commits only the part face-connected to its trunk base."""

    def __init__(self, cv, x, y, g):
        self.cv, self.x, self.y, self.g = cv, x, y, g
        self.v = {}

    def put(self, x, y, z, c, mat, force=False):
        cv = self.cv
        if not (0 <= x < 256 and 0 <= y < 512 and 7 <= z < 63):
            return
        if cv.solid[x, y, z] and not force:
            return
        if cv.keep[x, y] & KEEP_BLOCK and z < cv.H[x, y]:
            return
        self.v[(x, y, z)] = (clamp8(c), mat)

    def commit(self, ground_seed):
        cv = self.cv
        self.v = {k: v for k, v in self.v.items()
                  if 0 <= k[0] < 256 and 0 <= k[1] < 512 and 7 <= k[2] < 63 and
                  not (cv.keep[k[0], k[1]] & KEEP_BLOCK and k[2] < cv.H[k[0], k[1]]) and
                  not cv.solid[k]}                                   # never overwrite an existing voxel
        if not self.v:
            return 0
        keys = list(self.v)
        a = np.array(keys)
        lo = a.min(0) - 1
        hi = a.max(0) + 1
        sub = np.zeros(tuple(hi - lo + 1), bool)
        sub[tuple((a - lo).T)] = True
        lab, n = ndi.label(sub, structure=ndi.generate_binary_structure(3, 1))
        good = set()
        for (sx, sy, sz) in ground_seed:
            p = (sx - lo[0], sy - lo[1], sz - lo[2])
            if all(0 <= p[i] < sub.shape[i] for i in range(3)) and lab[p]:
                good.add(int(lab[p]))
        k = 0
        for key in keys:
            if lab[tuple(np.array(key) - lo)] in good:
                c, m = self.v[key]
                self.cv.set(*key, c, m)
                k += 1
        return k


def _grad(fa, fb, t):
    return mix(fa, fb, max(0.0, min(1.0, t)))


def _hue(rng, c, amt=10):
    d = rng.integers(-amt, amt + 1, 3)
    return clamp8(tuple(int(c[i] + d[i]) for i in range(3)))


def _blob(P, rng, cx, cy, cz, rx, rz, fa, fb, zmin_floor, mat='leaf', fill=1.0):
    """Lumpy crown mass; colour gradient from the dark underside to a light (sunlit) top."""
    ph = rng.random(3) * 6.283
    R = int(rx) + 2
    for X in range(int(cx) - R, int(cx) + R + 1):
        for Y in range(int(cy) - R, int(cy) + R + 1):
            for Z in range(int(cz - rz) - 1, int(cz + rz) + 2):
                dx, dy, dz = X + 0.5 - cx, Y + 0.5 - cy, (Z + 0.5 - cz) * rx / max(rz, 0.5)
                th = math.atan2(dy, dx)
                j = 1 + 0.16 * math.sin(5 * th + ph[0]) + 0.08 * math.sin(9 * th + ph[1]) + \
                    0.08 * math.sin(0.9 * Z + ph[2])
                if dx * dx + dy * dy + dz * dz <= (rx * j) ** 2 and Z <= zmin_floor:
                    if fill < 1.0 and rng.random() > fill:
                        continue
                    t = (cz + rz - Z) / (2 * rz)                     # 0 bottom .. 1 top
                    c = _grad(fa, fb, max(t, 0.0) ** 1.3 + (rng.random() - 0.5) * 0.14)
                    if V11:
                        dn = math.sqrt(dx * dx + dy * dy + dz * dz) / max(rx * j, 0.5)
                        if dn > 0.84 and rng.random() < 0.2:
                            continue                                    # holes in the outer shell
                        sun = (dx * 0.7 + dy * 0.5) / max(rx, 1)        # sun side lighter, shade side darker
                        c = shade(c, 1.0 + 0.12 * sun)
                        if dn > 0.8 and t > 0.7:
                            c = mix(c, (150, 148, 92), 0.3)             # new growth at the lit tips
                    P.put(X, Y, Z, shade(c, 0.78 + 0.28 * t), mat)        # shadowed underside, lit top


def _limb(P, a, b, c, mat='bark'):
    from aosmap.kit.canvas import line_points
    for (x, y, z) in line_points(*a, *b):
        P.put(x, y, z, c, mat)


def _trunk(P, x, y, g, h, w, bark, rng, flute=True):
    for k in range(h):
        for dx in range(w):
            for dy in range(w):
                c = shade(bark, 0.88 + 0.1 * ((k + dx * 2 + dy) % 3 == 0) if flute else 1.0)
                P.put(x + dx, y + dy, g - 1 - k, c, 'bark', force=False)


def _details(P, rng, kind, x, y, g, h, w, crown, bark, fa, fb, glow):
    det = tuple(sorted(rng.choice(DETAILS[kind], size=3, replace=False)))
    low = sorted(crown, key=lambda p: -p[2])[:40] if crown else []
    for d in det:
        if d == 'hanging_moss' and low:
            for (px, py, pz) in low[::3][:10]:
                for k in range(1, int(rng.integers(2, 5))):
                    if pz + k <= g - 5:
                        P.put(px, py, pz + k, (120, 142, 92) if k % 2 else (104, 128, 84), 'moss')
        elif d == 'ivy':
            for k in range(1, max(3, int(h * 0.6))):
                if rng.random() < 0.75:
                    P.put(x - 1, y + int(rng.integers(0, w)), g - 1 - k, (62, 104, 52) if k % 3 else (84, 126, 60),
                          'leaf', force=False)
        elif d == 'shelf_fungus':
            for (dx, dy, k) in ((w, 0, 3), (-1, w - 1, 5), (0, w, 7)):
                if k < h:
                    P.put(x + dx, y + dy, g - 1 - k, (196, 176, 136), 'fungus')
        elif d == 'nest' and crown:
            px, py, pz = crown[len(crown) // 3]
            P.put(px, py, pz, (118, 92, 64), 'nest', force=True)
        elif d == 'golden_leaves' and crown:
            for i in rng.choice(len(crown), size=min(14, len(crown)), replace=False):
                px, py, pz = crown[int(i)]
                P.v[(px, py, pz)] = ((168, 150, 84) if rng.random() < 0.6 else (150, 124, 70), 'leaf')
        elif d == 'hollow':
            k = min(h - 2, 4)
            for dz, c in ((0, (44, 36, 30)), (1, (52, 42, 34))):
                if (x, y, g - 1 - k - dz) in P.v:
                    P.v[(x, y, g - 1 - k - dz)] = (c, 'bark')
        elif d == 'mushrooms':
            for (dx, dy) in ((w + 1, 0), (-2, 1), (1, w + 1)):
                if rng.random() < 0.8:
                    P.put(x + dx, y + dy, int(P.cv.H[x + dx, y + dy]) - 1, (206, 186, 160) if rng.random() < 0.5
                          else (176, 120, 80), 'shroom')
        elif d == 'flowers':
            col = [(150, 96, 160), (206, 196, 170), (206, 184, 84)][int(rng.integers(3))]
            for a in range(0, 360, 45):
                if rng.random() < 0.6:
                    fx = x + int(round(3.2 * math.cos(math.radians(a))))
                    fy = y + int(round(3.2 * math.sin(math.radians(a))))
                    P.put(fx, fy, int(P.cv.H[fx, fy]) - 1, col, 'flower')
        elif d == 'lichen':
            for k in range(1, h, 2):
                if rng.random() < 0.5:
                    key = (x + w - 1, y, g - 1 - k)
                    if key in P.v:
                        P.v[key] = ((168, 176, 140), 'lichen')
        elif d == 'deadbranch':
            z = g - 1 - int(h * 0.5)
            dx, dy = ((1, 0), (0, 1), (-1, 0))[int(rng.integers(3))]
            for i in range(1, 4):
                P.put(x + dx * (i + w - 1), y + dy * (i + w - 1), z - i // 2, (128, 116, 100), 'deadwood')
                P.put(x + dx * (i + w - 1), y + dy * (i + w - 1), z, (128, 116, 100), 'deadwood')
        elif d == 'cones' and crown:
            for i in rng.choice(len(crown), size=min(8, len(crown)), replace=False):
                P.v[crown[int(i)]] = ((112, 82, 52), 'leaf')
        elif d == 'resin':
            k = min(h - 1, 4)
            P.v[(x, y, g - 1 - k)] = ((176, 132, 60), 'bark')
        elif d == 'catkins' and low:
            for (px, py, pz) in low[::4][:8]:
                if pz + 1 <= g - 5:
                    P.put(px, py, pz + 1, (176, 168, 96), 'leaf')
        elif d == 'carved_rune':
            k = min(h - 2, 5)
            P.v[(x, y, g - 1 - k)] = ((90, 200, 196), 'bark')
            glow.append((x, y, g - 1 - k, (95, 255, 255)))
    return det


def oak(cv, rng, x, y, g, h, glow):
    h = max(14, h + int(rng.integers(0, 6)))
    P = Plant(cv, x, y, g)
    w = 3 if h >= 18 else 2
    bark = _hue(rng, BARK['oak'], 6)
    fa, fb = SPECIES_PAL['oak'][int(rng.integers(len(SPECIES_PAL['oak'])))]
    fa, fb = _hue(rng, fa), _hue(rng, fb)
    th = int(h * 0.45)
    _trunk(P, x, y, g, th + 2, w, bark, rng)
    for (dx, dy) in ((-1, 0), (w, 0), (0, -1), (0, w), (-1, w - 1), (w, w - 1)):        # buttress roots
        if rng.random() < 0.75:
            P.put(x + dx, y + dy, g - 1, shade(bark, 0.82), 'bark')
            P.put(x + dx, y + dy, g - 2, shade(bark, 0.86), 'bark')
            ex, ey = x + dx + (dx > 0) - (dx < 0), y + dy + (dy >= w) - (dy < 0)
            P.put(ex, ey, int(cv.H[ex, ey]) - 1, shade(bark, 0.78), 'bark')
    crown = []
    top = (x + w // 2, y + w // 2, g - 1 - th)
    n = int(rng.integers(3, 6))
    a0 = rng.random() * 6.283
    for i in range(n):                                   # limbs, each forking into two lobes at different heights
        a = a0 + i * 6.283 / n + rng.uniform(-0.4, 0.4)
        L = 3 + rng.random() * (2 + h * 0.15)
        ex, ey = top[0] + L * math.cos(a), top[1] + L * math.sin(a)
        ez = top[2] - 2 - rng.random() * h * 0.25
        _limb(P, top, (int(ex), int(ey), int(ez)), shade(bark, 0.95))
        for da in (-0.5, 0.5):
            L2 = 2 + rng.random() * 3
            fx, fy = ex + L2 * math.cos(a + da), ey + L2 * math.sin(a + da)
            fz = ez - 1 - rng.random() * 3
            _limb(P, (int(ex), int(ey), int(ez)), (int(fx), int(fy), int(fz)), shade(bark, 0.92))
            r = 2.2 + rng.random() * 1.6 + h * 0.04
            before = set(P.v)
            _blob(P, rng, fx + 0.5, fy + 0.5, fz - r * 0.3, r, r * 0.6, fa, fb, g - 5)
            crown += [k for k in P.v if k not in before]
            if V11:                                       # twigs showing under the lobe
                for (tx, ty) in ((2, 1), (-1, 2), (1, -2)):
                    tz = min(int(fz) + 2, g - 5)
                    _limb(P, (int(fx), int(fy), int(fz)), (int(fx) + tx, int(fy) + ty, tz), shade(bark, 0.88))
    r = 2.8 + h * 0.06
    before = set(P.v)
    _blob(P, rng, top[0] + 0.5, top[1] + 0.5, top[2] - h * 0.3, r, r * 0.7, fa, fb, g - 5)
    crown += [k for k in P.v if k not in before]
    for k in range(int(h * 0.3) + 1):
        P.put(top[0], top[1], top[2] - k, bark, 'bark')
    det = _details(P, rng, 'oak', x, y, g, th, w, crown, bark, fa, fb, glow)
    return P, det


def beech(cv, rng, x, y, g, h, glow):
    h = max(15, h + int(rng.integers(2, 8)))
    P = Plant(cv, x, y, g)
    w = 2
    bark = _hue(rng, BARK['beech'], 6)
    fa, fb = SPECIES_PAL['beech'][int(rng.integers(2))]
    fa, fb = _hue(rng, fa), _hue(rng, fb)
    th = int(h * 0.55)
    _trunk(P, x, y, g, h - 2, w, bark, rng, flute=False)
    for (dx, dy) in ((-1, 0), (w, 1), (1, -1), (0, w)):
        P.put(x + dx, y + dy, g - 1, shade(bark, 0.8), 'bark')
    crown = []
    for (oz, rr) in ((0.0, 1.0), (0.35, 0.8), (0.65, 0.55)):
        r = (3.0 + h * 0.16) * rr
        before = set(P.v)
        _blob(P, rng, x + 1.0, y + 1.0, g - th - (h - th) * oz - 2, r, r * 0.75, fa, fb, g - 5)
        crown += [k for k in P.v if k not in before]
    det = _details(P, rng, 'beech', x, y, g, th, w, crown, bark, fa, fb, glow)
    return P, det


def fir(cv, rng, x, y, g, h, glow):
    h = max(12, h + int(rng.integers(2, 9)))
    P = Plant(cv, x, y, g)
    w = 2 if h >= 18 else 1
    bark = _hue(rng, BARK['fir'], 6)
    fa, fb = SPECIES_PAL['fir'][int(rng.integers(3))]
    fa, fb = _hue(rng, fa, 6), _hue(rng, fb, 6)
    _trunk(P, x, y, g, h, w, bark, rng)
    if V11:                                               # root flare
        for (dx, dy) in ((-1, 0), (w, 0), (0, -1), (0, w)):
            if rng.random() < 0.7:
                P.put(x + dx, y + dy, g - 1, shade(bark, 0.8), 'bark')
    clear = 4
    tier = 1.0
    R0 = 0.24 * h + 1.6
    period = int(rng.integers(3, 5))
    ph = rng.random() * 6.283
    crown = []
    cx, cy = x + (w - 1) / 2 + 0.5, y + (w - 1) / 2 + 0.5
    for k in range(clear, h + 1):
        f = (k - clear) / max(h - clear, 1)
        phase = ((k - clear) % period) / period
        r = R0 * (1 - f) ** 1.1 * (1 - 0.35 * phase) + 0.5
        if phase == 0:
            tier = rng.uniform(0.75, 1.15) if rng.random() > 0.18 else 0.45     # irregular tiers, some gaps
        r *= tier if k > clear else 1.0
        z = g - 1 - k
        ri = int(r) + 2
        for X in range(x - ri, x + ri + w):
            for Y in range(y - ri, y + ri + w):
                d = math.hypot(X + 0.5 - cx, Y + 0.5 - cy)
                j = 1 + 0.18 * math.sin(7 * math.atan2(Y - cy, X - cx) + ph + k)
                if d <= r * j:
                    droop = 1 if (d > r * 0.75 and phase < 0.34) else 0           # drooping tier edges
                    if z + droop <= g - 5:
                        c = _grad(fa, fb, f + 0.15 * (1 - d / max(r, 1)) + (rng.random() - 0.5) * 0.12)
                        P.put(X, Y, z + droop, c, 'leaf')
                        if (X, Y, z + droop) in P.v:
                            crown.append((X, Y, z + droop))
    P.put(x, y, g - 2 - h, fb, 'leaf')
    det = _details(P, rng, 'fir', x, y, g, h, w, crown, bark, fa, fb, glow)
    return P, det


def birch(cv, rng, x, y, g, h, glow):
    h = max(11, h + int(rng.integers(0, 5)))
    P = Plant(cv, x, y, g)
    bark = _hue(rng, BARK['birch'], 5)
    fa, fb = SPECIES_PAL['birch'][int(rng.integers(2))]
    fa, fb = _hue(rng, fa), _hue(rng, fb)
    lean = (int(rng.integers(-1, 2)), int(rng.integers(-1, 2)))
    for k in range(h):
        dx, dy = (lean[0] * (k // 6), lean[1] * (k // 6))
        c = (60, 56, 52) if (k * 7 + x) % 5 == 0 else bark                      # dark bark marks
        P.put(x + dx, y + dy, g - 1 - k, c, 'bark')
        if k and (k % 6 == 0):
            P.put(x + lean[0] * ((k - 1) // 6), y + dy, g - 1 - k, bark, 'bark')
    tx, ty = x + lean[0] * ((h - 1) // 6), y + lean[1] * ((h - 1) // 6)
    crown = []
    for i in range(3):
        r = 2.4 + rng.random() * 1.6
        before = set(P.v)
        _blob(P, rng, tx + 0.5 + rng.uniform(-1.5, 1.5), ty + 0.5 + rng.uniform(-1.5, 1.5),
              g - h + 2 - i * 2.5, r, r * 0.8, fa, fb, g - 5, fill=0.72)
        crown += [k for k in P.v if k not in before]
    for k in range(h - 6, h + 4):
        P.put(tx, ty, g - 1 - k, bark, 'bark')
    det = _details(P, rng, 'birch', x, y, g, h, 1, crown, bark, fa, fb, glow)
    return P, det


def snag(cv, rng, x, y, g, h, glow):
    h = max(9, h - int(rng.integers(0, 4)))
    P = Plant(cv, x, y, g)
    bark = _hue(rng, BARK['snag'], 6)
    w = 2
    _trunk(P, x, y, g, h, w, bark, rng)
    for i in range(int(rng.integers(2, 5))):
        z = g - 1 - int(h * (0.45 + 0.5 * rng.random()))
        a = rng.random() * 6.283
        L = 2 + rng.random() * 4
        e = (int(x + L * math.cos(a)), int(y + L * math.sin(a)), int(z - L * 0.6))
        _limb(P, (x, y, z), e, shade(bark, 0.9), 'deadwood')
        for da in (-0.6, 0.6):                                                  # forked bare tips
            _limb(P, e, (int(e[0] + 2 * math.cos(a + da)), int(e[1] + 2 * math.sin(a + da)), e[2] - 2),
                  shade(bark, 0.85), 'deadwood')
    P.put(x + 1, y, g - h, shade(bark, 0.7), 'deadwood')                        # splintered top
    det = _details(P, rng, 'snag', x, y, g, h, w, [], bark, bark, bark, glow)
    return P, det


SPECIES = {'oak': oak, 'beech': beech, 'fir': fir, 'birch': birch, 'snag': snag}


def clear_stand_ins(cv):
    vid = cv.materials.get('veg')
    m = cv.mat == vid
    m[256:] = False
    cv.solid[m] = False
    cv.mat[m] = 0
    return int(m.sum())


def plant_trees(cv, trees, rng, seed, glow):
    """Replace every stand-in (graybox tree_list: x, y, r, h, kind) with a real tree. The species follows a smooth
    stand field from the veg seed (birch stands, oak and beech woods), firs stay firs (a few become dead snags)."""
    stand = noise.fbm2((512, 512), 46, 2, 'stand_species', seed)
    out = []
    counts, dcount = {}, {}
    for (x, y, r, h, kind) in trees:
        if x > 255:
            continue
        g = int(cv.H[x, y])
        if kind == 'fir':
            sp = 'snag' if rng.random() < 0.12 else 'fir'
        else:
            s = stand[x, y]
            sp = 'birch' if s < 0.38 else ('beech' if s > 0.6 else 'oak')
            if rng.random() < 0.06:
                sp = 'snag'
        P, det = SPECIES[sp](cv, rng, x, y, g, h, glow)
        base = [(x + dx, y + dy, g - 1) for dx in range(3) for dy in range(3)]
        n = P.commit(base)
        out.append((x, y, sp, n))
        counts[sp] = counts.get(sp, 0) + 1
        for d in det:
            dcount[d] = dcount.get(d, 0) + 1
    return {'trees': len(out), 'by_species': counts, 'details': dcount, 'list': out}


def understory(cv, rng, seed, plaza_mask=None):
    """1-tall ground plants (never a trap): fern beds and bramble in the woods, wildflower patches (foxglove,
    white umbels, yellow) in clearings, fairy-ring mushrooms. Only on open ground columns without keep flags."""
    H = cv.H.astype(int)
    dens = noise.fbm2((512, 512), 30, 2, 'forest_density', seed)
    n2 = noise.fbm2((512, 512), 7, 2, 'under_fine', seed)
    gid = cv.materials.get('ground')
    X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    top = np.argmax(cv.solid, axis=2)
    ok = (top == H) & (cv.mat[X, Y, H] == gid) & (cv.keep == 0) & (H >= 44) & (H <= 57) & (X <= 255)
    ok &= ~ndi.binary_dilation(top < H, iterations=1)                        # not hugging props or trunks
    if plaza_mask is not None:
        ok &= ~plaza_mask
    counts = {'fern': 0, 'bramble': 0, 'flower': 0, 'shroom': 0}
    h = noise.hash3(X, Y, 0, 77)
    fern = ok & (dens > 0.5) & (n2 > 0.55) & (h < 0.55)
    bram = ok & (dens > 0.56) & (n2 < 0.3) & (h < 0.5)
    flow = ok & (dens < 0.42) & (n2 > 0.7) & (h < 0.07)
    for m, mat, cols in ((fern, 'fern', [(46, 76, 52), (58, 90, 58), (72, 100, 64)]),
                         (bram, 'bramble', [(52, 62, 42), (62, 68, 46), (64, 50, 62)]),
                         (flow, 'flower', [(128, 104, 136), (176, 172, 160), (162, 150, 92), (112, 112, 140)])):
        xs, ys = np.nonzero(m)
        for x, y in zip(xs, ys):
            c = cols[int(noise.hash3(x // 3, y // 3, 1, 5) * len(cols)) % len(cols)] if mat == 'flower' else \
                cols[int(h[x, y] * 97) % len(cols)]
            cv.set(int(x), int(y), int(H[x, y]) - 1, c, mat)
            counts[mat] += 1
    # fairy rings in clearings
    for _ in range(18):
        x, y = int(rng.integers(20, 250)), int(rng.integers(20, 490))
        if not ok[x, y] or dens[x, y] > 0.5:
            continue
        for a in range(0, 360, 30):
            fx, fy = x + int(round(3 * math.cos(math.radians(a)))), y + int(round(3 * math.sin(math.radians(a))))
            if ok[fx, fy] and not cv.solid[fx, fy, H[fx, fy] - 1]:
                cv.set(fx, fy, int(H[fx, fy]) - 1, (214, 200, 176), 'shroom')
                counts['shroom'] += 1
    return counts


def reeds_and_lilies(cv, rng, seed):
    """Reeds (1-2 tall single stalks, sparse) on the wading shelves and low banks; lily pads painted on calm water
    near the banks (recolour only)."""
    H = cv.H.astype(int)
    wid = cv.materials.get('water')
    n = 0
    lil = 0
    for x in range(30, 256):
        for y in range(380, 480):
            z = H[x, y]
            if z in (61, 62) and (int(cv.keep[x, y]) & 0xDF) == 0 and noise.hash3(x, y, 2, 9) < 0.16 and \
                    not cv.solid[x, y, z - 1]:                                  # 32 = stream keep flag
                hh = 2 if noise.hash3(x, y, 3, 9) < 0.4 else 1
                for k in range(hh):
                    cv.set(x, y, z - 1 - k, (112, 132, 64) if k else (92, 112, 58), 'reed')
                if hh == 2:
                    cv.set(x, y, z - 2, (132, 98, 60), 'reed')                       # seed head
                n += 1
            elif z == 63 and cv.mat[x, y, z] == wid and noise.hash3(x // 2, y // 2, 4, 9) < 0.07:
                near_bank = H[x, y - 2] < 63 or H[x, y + 2] < 63
                if near_bank:
                    cv.rgb[x, y, z] = (74, 120, 66) if noise.hash3(x, y, 5, 9) < 0.8 else (206, 196, 200)
                    lil += 1
    return {'reeds': n, 'lily_cells': lil}


def heart_tree(cv, rng, S, glow):
    """Art for the heart-tree (graybox geometry: trunk, hollow, roots, forked limbs, separate crown masses).
    Bark: deep fluting, damp-dark at the foot, lichen-grey higher up, grey-green moss on tops and north faces.
    Crowns: each mass shaded from a blue-green underside to a muted olive-gold top. Added (all >= 4 above the
    ground or inside the hollow, plant materials): moss curtains under the crowns, vines from the limbs, three dead
    silver branches, bracket fungi, a nest at a fork, a hanging lantern (warm), rune-lit knots (cyan)."""
    a = S['amphi']
    cx, cy = a['c'][0] + 0.5, a['c'][1] + 0.5
    ga = int(cv.H[255, a['c'][1]])
    tid, cid, rid = cv.materials.get('trunk'), cv.materials.get('canopy'), cv.materials.get('root')
    box = (slice(int(cx) - 40, 256), slice(int(cy) - 40, int(cy) + 41))
    ox, oy = box[0].start, box[1].start
    out = {}
    for m_id, kind in ((tid, 'trunk'), (rid, 'root')):
        xs, ys, zs = np.nonzero(cv.mat[box] == m_id)
        xs, ys = xs + ox, ys + oy
        ang = np.arctan2(ys + 0.5 - cy, xs + 0.5 - cx)
        flute = np.sin(ang * 16 + zs * 0.15) > 0.25
        hgt = np.clip((ga - zs) / 26.0, 0, 1)
        dark, lit = np.array((58, 46, 38), float), np.array((112, 102, 88), float)
        c = dark[None] * (1 - hgt[:, None]) + lit[None] * hgt[:, None]
        c *= np.where(flute, 0.82, 1.0)[:, None]
        lich = noise.hash3(xs, ys, zs, 61) < 0.06
        c[lich] = (150, 152, 140)
        up = ~cv.solid[xs, ys, np.maximum(zs - 1, 0)]
        north = ~cv.solid[xs, np.maximum(ys - 1, 0), zs]
        mossy = (up | (north & (noise.hash3(xs // 2, ys // 2, zs // 2, 3) < 0.5))) & \
            (noise.fbm2((512, 512), 4, 2, 'heart_moss', 7)[xs, ys] > 0.42)
        c[mossy] = np.array((82, 98, 68)) * (0.85 + 0.25 * noise.hash3(xs[mossy], ys[mossy], zs[mossy], 4))[:, None]
        cv.rgb[xs, ys, zs] = np.clip(c, 0, 212).astype(np.uint8)
    # crown masses: underside blue-green, sides deep green, sunlit tops muted olive-gold
    xs, ys, zs = np.nonzero(cv.mat[box] == cid)
    xs, ys = xs + ox, ys + oy
    below = ~cv.solid[xs, ys, np.minimum(zs + 1, 63)]
    above = ~cv.solid[xs, ys, np.maximum(zs - 1, 0)]
    n = noise.fbm2((512, 512), 4, 2, 'heart_crown', 3)[xs, ys]
    c = np.array((50, 76, 56), float)[None] * (0.85 + 0.3 * n[:, None])
    c[below] = np.array((32, 54, 52)) * (0.9 + 0.2 * n[below, None])
    c[above] = np.array((118, 122, 72)) * (0.88 + 0.24 * n[above, None])
    gold = above & (noise.hash3(xs, ys, zs, 71) < 0.07)
    c[gold] = (168, 150, 84)
    cv.rgb[xs, ys, zs] = np.clip(c, 0, 212).astype(np.uint8)
    # moss curtains under the crowns (clustered), >= 4 above the ground
    cur = noise.fbm2((512, 512), 3, 2, 'heart_curtain', 5)
    hung = 0
    for (x, y, z) in zip(xs[below], ys[below], zs[below]):
        if cur[x, y] < 0.52 or noise.hash3(x, y, z, 81) > 0.55:
            continue
        g = int(cv.H[x, y])
        L = 2 + int(noise.hash3(x, y, 0, 82) * 8)
        for k in range(1, L + 1):
            zz = z + k
            if zz >= g - 4 or cv.solid[x, y, zz]:
                break
            cv.set(x, y, zz, (112, 124, 98) if (k + x) % 3 else (90, 104, 82), 'moss')
            hung += 1
    out['moss_curtain_voxels'] = hung
    # vines from the limbs (limb voxels above the trunk top, open underneath)
    T = a['tree']
    vines = 0
    xs, ys, zs = np.nonzero(cv.mat[box] == tid)
    xs, ys = xs + ox, ys + oy
    sel = (zs < T['trunk_top']) & ~cv.solid[xs, ys, np.minimum(zs + 1, 63)]
    for (x, y, z) in zip(xs[sel], ys[sel], zs[sel]):
        if noise.hash3(x, y, z, 91) < 0.18:
            g = int(cv.H[x, y])
            for k in range(1, 2 + int(noise.hash3(x, y, z, 92) * 5)):
                if z + k >= g - 4 or cv.solid[x, y, z + k]:
                    break
                cv.set(x, y, z + k, (54, 80, 50), 'moss')
                vines += 1
    out['vine_voxels'] = vines
    # dead silver branches high on the trunk
    for (deg, z, L) in ((150, T['trunk_top'] + 6, 6), (205, T['trunk_top'] + 11, 5), (120, T['trunk_top'] + 2, 5)):
        ca, sa = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        x0, y0 = cx + 5.4 * ca, cy + 5.4 * sa
        prev = None
        for i in range(L + 1):
            p = (int(math.floor(x0 + i * ca)), int(math.floor(y0 + i * sa)), z - i // 2)
            if p[0] <= 255 and not cv.solid[p]:
                cv.set(*p, (172, 170, 164), 'deadwood')
            if prev and prev[2] != p[2] and prev[0] <= 255 and not cv.solid[prev[0], prev[1], p[2]]:
                cv.set(prev[0], prev[1], p[2], (172, 170, 164), 'deadwood')
            prev = p
    # bracket fungi on the trunk (4-14 above the floor), rune knots, the hollow
    fun = rk = 0
    for z in range(ga - 15, ga - 4):
        for k in range(36):
            th = k * math.pi / 18
            x, y = int(math.floor(cx + 8.0 * math.cos(th))), int(math.floor(cy + 8.0 * math.sin(th)))
            if x > 255:
                continue
            for r in range(8, 3, -1):
                px, py = int(math.floor(cx + r * math.cos(th))), int(math.floor(cy + r * math.sin(th)))
                if cv.solid[px, py, z] and cv.mat[px, py, z] == tid:
                    qx, qy = int(math.floor(cx + (r + 1) * math.cos(th))), int(math.floor(cy + (r + 1) * math.sin(th)))
                    h = noise.hash3(qx, qy, z, 101)
                    if h < 0.035 and qx <= 255 and not cv.solid[qx, qy, z]:
                        cv.set(qx, qy, z, (192, 168, 120), 'fungus')
                        fun += 1
                    elif (k, z) in ((17, ga - 9), (22, ga - 13), (27, ga - 11)):          # rune-lit knots
                        cv.rgb[px, py, z] = (95, 255, 255)
                        glow.append((px, py, z, (95, 255, 255)))
                        rk += 1
                    break
    out['bracket_fungi'], out['rune_knots'] = fun, rk
    hy = int(cy - 2.0)
    for x in range(int(cx) - 5, 256):
        for y in range(hy - 5, hy + 5):
            for z in range(ga - 6, ga + 1):
                if cv.solid[x, y, z] and cv.mat[x, y, z] == tid and math.hypot(x + 0.5 - cx, y + 0.5 - hy + 0.0) < 5:
                    cv.rgb[x, y, z] = (40, 32, 28)
    if cv.solid[251, hy, ga - 3]:
        cv.rgb[251, hy, ga - 3] = (95, 255, 255)
        glow.append((251, hy, ga - 3, (95, 255, 255)))
    # a nest at the highest fork and a hanging lantern under a limb (warm)
    xs, ys, zs = np.nonzero(cv.mat[box] == tid)
    xs, ys = xs + ox, ys + oy
    sel = zs < T['trunk_top'] - 2
    if sel.any():
        i = int(np.argmin(zs[sel]))
        x, y, z = int(xs[sel][i]), int(ys[sel][i]), int(zs[sel][i])
        if z - 1 >= 9 and not cv.solid[x, y, z - 1]:
            cv.set(x, y, z - 1, (118, 92, 64), 'twig')
        under = sel & ~cv.solid[xs, ys, np.minimum(zs + 1, 63)] & (xs < cx - 8)
        if under.any():
            j = int(np.argmax(zs[under]))
            x, y, z = int(xs[under][j]), int(ys[under][j]), int(zs[under][j])
            g = int(cv.H[x, y])
            if z + 4 < g - 5:
                for k in (1, 2):
                    cv.set(x, y, z + k, (60, 56, 52), 'deadwood')
                cv.set(x, y, z + 3, (255, 175, 95), 'deadwood')
                glow.append((x, y, z + 3, (255, 175, 95)))
                out['lantern'] = [x, y, z + 3]
    return out


SHROOM_SPECIES = [('amber cap', (196, 132, 70), (212, 196, 160)), ('violet bell', (128, 88, 150), (180, 150, 196)),
                  ('teal shelf', (60, 132, 128), (120, 190, 170)), ('ivory parasol', (206, 196, 176), (150, 120, 100))]


def giant_mushrooms(cv, rng, S, glow):
    """Recolour the graybox giant mushrooms per species: stem gradient, cap gradient with spots, radial gills on
    the underside; two get a few soft green glow points under the cap."""
    mid = cv.materials.get('mushroom')
    out = []
    for i, (x, y, r, h, tx, ty) in enumerate(S['mushrooms']):
        name, cap, rim = SHROOM_SPECIES[i % len(SHROOM_SPECIES)]
        g = int(cv.H[x, y])
        ztop = g - h
        cx, cy = x + 0.5 + tx, y + 0.5 + ty
        for X in range(x - r - 3, x + r + 4):
            for Y in range(y - r - 2, y + r + 3):
                for Z in range(ztop - 4, g):
                    if not (0 <= X < 256) or not cv.solid[X, Y, Z] or cv.mat[X, Y, Z] != mid:
                        continue
                    d = math.hypot(X + 0.5 - cx, Y + 0.5 - cy)
                    if Z > ztop + 2:                                               # stem
                        t = (g - Z) / max(h, 1)
                        cv.rgb[X, Y, Z] = clamp8(mix((176, 168, 146), (208, 200, 180), t))
                    else:
                        under = not cv.solid[X, Y, Z + 1]
                        if under:
                            gill = int(math.degrees(math.atan2(Y - cy, X - cx)) // 15) % 2
                            cv.rgb[X, Y, Z] = shade(rim, 0.82 if gill else 0.95)
                        else:
                            t = d / max(r, 1)
                            c = mix(cap, rim, t ** 2)
                            if noise.hash3(X, Y, Z, 41 + i) < 0.08:
                                c = (210, 204, 186)                                   # cap spots
                            cv.rgb[X, Y, Z] = clamp8(c)
        if i in (3,):
            k = 0
            for X in range(x - r, x + r + 1):
                for Y in range(y - r, y + r + 1):
                    Z = ztop + 2
                    if 0 <= X < 256 and cv.solid[X, Y, Z] and not cv.solid[X, Y, Z + 1] and \
                            noise.hash3(X, Y, Z, 5) < 0.06 and k < 3:
                        cv.rgb[X, Y, Z] = (95, 255, 95)
                        glow.append((X, Y, Z, (95, 255, 95)))
                        k += 1
        out.append(name)
    return out
