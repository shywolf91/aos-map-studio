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

SPECIES_PAL = {
    'oak': [((58, 92, 44), (128, 150, 66)), ((52, 86, 48), (112, 142, 70)), ((64, 98, 42), (146, 156, 74))],
    'beech': [((60, 104, 52), (150, 168, 84)), ((70, 110, 50), (164, 170, 90))],
    'fir': [((30, 62, 50), (62, 102, 72)), ((34, 66, 58), (70, 108, 84)), ((28, 58, 46), (56, 92, 62))],
    'birch': [((96, 132, 60), (176, 182, 98)), ((110, 140, 64), (188, 186, 104))],
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
                    c = _grad(fa, fb, t + (rng.random() - 0.5) * 0.18)
                    P.put(X, Y, Z, shade(c, 0.92 + 0.12 * t), mat)


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
                P.v[(px, py, pz)] = ((206, 178, 82) if rng.random() < 0.6 else (190, 150, 70), 'leaf')
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
    for i in range(n):
        a = rng.random() * 6.283
        L = 3 + rng.random() * (2 + h * 0.15)
        ex, ey = top[0] + L * math.cos(a), top[1] + L * math.sin(a)
        ez = top[2] - 2 - rng.random() * h * 0.25
        _limb(P, top, (int(ex), int(ey), int(ez)), shade(bark, 0.95))
        r = 3.0 + rng.random() * 2.2 + h * 0.06
        before = set(P.v)
        _blob(P, rng, ex + 0.5, ey + 0.5, ez - r * 0.3, r, r * 0.62, fa, fb, g - 5)
        crown += [k for k in P.v if k not in before]
    r = 3.5 + h * 0.08
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
    clear = 4
    R0 = 0.24 * h + 1.6
    period = int(rng.integers(3, 5))
    ph = rng.random() * 6.283
    crown = []
    cx, cy = x + (w - 1) / 2 + 0.5, y + (w - 1) / 2 + 0.5
    for k in range(clear, h + 1):
        f = (k - clear) / max(h - clear, 1)
        phase = ((k - clear) % period) / period
        r = R0 * (1 - f) ** 1.1 * (1 - 0.35 * phase) + 0.5
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
        _limb(P, (x, y, z), (int(x + L * math.cos(a)), int(y + L * math.sin(a)), int(z - L * 0.6)),
              shade(bark, 0.9), 'deadwood')
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
    flow = ok & (dens < 0.45) & (n2 > 0.66) & (h < 0.2)
    for m, mat, cols in ((fern, 'fern', [(58, 108, 54), (76, 128, 62), (96, 140, 70)]),
                         (bram, 'bramble', [(62, 76, 46), (74, 84, 50), (70, 52, 70)]),
                         (flow, 'flower', [(136, 104, 150), (196, 192, 174), (184, 170, 96), (120, 116, 158)])):
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
    """The amphitheatre's ancient heart-tree: bark with deep vertical fluting, a dark hollow high on the trunk,
    roots recoloured as old bark with moss on top, a layered crown (gold-green on top, deep green underneath)
    with extra tiers and hanging roots/moss, three rune-lit knots."""
    a = S['amphi']
    cx, cy = a['c'][0] + 0.5, a['c'][1] + 0.5
    tid, cid, rid = cv.materials.get('trunk'), cv.materials.get('canopy'), cv.materials.get('root')
    for m_id, kind in ((tid, 'trunk'), (rid, 'root')):
        xs, ys, zs = np.nonzero(cv.mat == m_id)
        sel = xs <= 255
        xs, ys, zs = xs[sel], ys[sel], zs[sel]
        ang = np.arctan2(ys + 0.5 - cy, xs + 0.5 - cx)
        flute = (np.sin(ang * 14) > 0.3)
        base = np.array((86, 66, 50), float) if kind == 'trunk' else np.array((96, 74, 54), float)
        c = base * np.where(flute, 0.86, 1.04)[:, None]
        mossy = ~cv.solid[xs, ys, np.maximum(zs - 1, 0)] & (noise.hash3(xs, ys, zs, 21) < 0.6)
        c[mossy] = np.array((92, 122, 62)) * (0.9 + 0.2 * noise.hash3(xs[mossy], ys[mossy], zs[mossy], 3))[:, None]
        cv.rgb[xs, ys, zs] = np.clip(c, 0, 255).astype(np.uint8)          # materials kept (trunk / root)
    xs, ys, zs = np.nonzero(cv.mat == cid)
    sel = xs <= 255
    xs, ys, zs = xs[sel], ys[sel], zs[sel]
    zt, zb = zs.min(), zs.max()
    t = (zb - zs) / max(zb - zt, 1)
    n = noise.fbm2((512, 512), 5, 2, 'heart_crown', 1)[xs, ys]
    lo, hi = np.array((40, 82, 44), float), np.array((176, 170, 78), float)
    c = lo[None] * (1 - t[:, None]) + hi[None] * t[:, None]
    c *= (0.9 + 0.2 * n)[:, None]
    cv.rgb[xs, ys, zs] = np.clip(c, 0, 212).astype(np.uint8)
    # crown tiers on top (unreachable, >= 30 above the arena)
    P = Plant(cv, int(cx), int(cy), int(cv.H[255, a['c'][1]]))
    for (ox, oy, r) in ((-6, -4, 6.0), (-9, 5, 5.0), (-3, 8, 5.5), (-12, -1, 4.5)):
        _blob(P, rng, cx + ox, cy + oy, zt + 1, r, r * 0.5, (70, 110, 52), (190, 178, 84), zt + 4)
    seed = [k for k in P.v if cv.solid[k[0], k[1], k[2] + 1] or cv.solid[k[0], k[1], k[2] + 2]]
    P.commit(seed[:200] or [(int(cx), int(cy), zt)])
    # hanging roots and moss from the crown underside (stop >= 6 above the ground)
    hung = 0
    for x in range(int(cx) - 17, 256):
        for y in range(int(cy) - 15, int(cy) + 16):
            col = cv.solid[x, y, :]
            if not col[zb] or noise.hash3(x, y, 0, 31) > 0.12:
                continue
            g = int(cv.H[x, y])
            for k in range(1, int(noise.hash3(x, y, 1, 31) * 7) + 2):
                z = zb + k
                if z >= g - 6 or cv.solid[x, y, z]:
                    break
                cv.set(x, y, z, (112, 136, 84) if k % 2 else (98, 84, 64), 'moss')
                hung += 1
    # hollow: a dark knot-hole high on the trunk (unreachable), rune-lit knots
    ga = int(cv.H[255, a['c'][1]])
    for (ang, z, gl) in ((200, ga - 12, False), (160, ga - 22, True), (230, ga - 28, True), (185, ga - 16, True)):
        px = int(math.floor(cx + 4.6 * math.cos(math.radians(ang))))
        py = int(math.floor(cy + 4.6 * math.sin(math.radians(ang))))
        if gl:
            if cv.solid[px, py, z]:
                cv.rgb[px, py, z] = (95, 255, 255)
                glow.append((px, py, z, (95, 255, 255)))
        else:
            for dz in range(0, 4):
                for d in (0, 1):
                    if cv.solid[px, py + d, z - dz]:
                        cv.rgb[px, py + d, z - dz] = (34, 28, 24)
    return {'hanging_voxels': hung}


SHROOM_SPECIES = [('amber cap', (196, 132, 70), (212, 196, 160)), ('violet bell', (128, 88, 150), (180, 150, 196)),
                  ('teal shelf', (60, 132, 128), (120, 190, 170)), ('ivory parasol', (206, 196, 176), (150, 120, 100))]


def giant_mushrooms(cv, rng, S, glow):
    """Recolour the graybox giant mushrooms per species: stem gradient, cap gradient with spots, radial gills on
    the underside; two get a few soft green glow points under the cap."""
    mid = cv.materials.get('mushroom')
    out = []
    for i, (x, y, r, h) in enumerate(S['mushrooms']):
        name, cap, rim = SHROOM_SPECIES[i % len(SHROOM_SPECIES)]
        g = int(cv.H[x, y])
        ztop = g - h
        cx, cy = x + 0.5, y + 0.5
        for X in range(x - r - 2, x + r + 3):
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
        if i in (2, 4):
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
