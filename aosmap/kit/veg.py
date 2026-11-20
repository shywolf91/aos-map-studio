"""Vegetation with the owner's rules (2026-10 feedback): non-deterministic (OS seed saved in build.json), varied
colours with smooth gradients, three random details per plant, groves rather than even scatter, every part
face-connected to the trunk (diagonal-only contact floats and collapses).

Merged from sph_trees (pick_details, jagged tiers, two-palette blend, _decorate), Bloomhop veg.py
(can_place, bloom_tree, bush, plant_all) and wkh_props.big_tree / ww_gen.big_tree.

Usage:
    seed = noise.os_seed()                 # record in build.json
    rng = np.random.default_rng(seed)
    pal = palette_family([(52, 98, 46), (74, 120, 52), (96, 132, 60)], n=8)
    report = plant_groves(cv, rng, centres, pal, species=('broadleaf', 'conifer', 'bush'))
"""
from __future__ import annotations

import math

import functools

import numpy as np
from scipy import ndimage as ndi

from .color import clamp8, mix, shade

DETAILS = ('moss', 'vines', 'fruit', 'blossom', 'deadbranch', 'roots', 'nest', 'mushrooms', 'lantern', 'ribbon')


def pick_details(rng, allow=DETAILS, n=3):
    idx = rng.choice(len(allow), size=min(n, len(allow)), replace=False)
    return tuple(sorted(allow[i] for i in idx))


def palette_family(anchors, n=8):
    """n colours interpolated smoothly through the anchor colours; neighbours in the list are similar hues."""
    out = []
    for i in range(n):
        t = i / max(n - 1, 1) * (len(anchors) - 1)
        k = min(int(t), len(anchors) - 2)
        out.append(clamp8(mix(anchors[k], anchors[k + 1], t - k)))
    return out


def _jag(rng):
    ph = rng.random(2) * 6.283
    k1, k2 = int(rng.integers(4, 7)), int(rng.integers(8, 12))
    a1, a2 = 0.12 + 0.1 * rng.random(), 0.06 + 0.08 * rng.random()
    return lambda th: 1 + a1 * math.sin(k1 * th + ph[0]) + a2 * math.sin(k2 * th + ph[1])


def _blend(fa, fb, t):
    return clamp8(mix(fa, fb, max(0.0, min(1.0, t))))


def _trunk(cv, x, y, g, h, w, bark, mat='bark'):
    for k in range(h):
        for dx in range(w):
            for dy in range(w):
                cv.set(x + dx, y + dy, g - 1 - k, shade(bark, 0.92 + 0.08 * ((k // 3) % 2)), mat)


def _decorate(cv, rng, x, y, g, h, details, crown_pts, bark, leaf):
    """Three details, each attached by a face to the trunk or crown."""
    if 'moss' in details:
        for k in range(0, max(2, h // 3)):
            cv.set(x - 1, y, g - 1 - k, (86, 120, 58), 'moss')          # moss strip on the west face
    if 'roots' in details:
        for (dx, dy) in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            if rng.random() < 0.8:
                cv.set(x + dx, y + dy, g - 1, shade(bark, 0.8), 'bark')
                cv.set(x + 2 * dx, y + 2 * dy, g - 1, shade(bark, 0.72), 'bark') if rng.random() < 0.5 else None
    if 'deadbranch' in details:
        z = g - 1 - int(h * 0.45)
        d = (1, 0) if rng.random() < 0.5 else (0, 1)
        for i in range(1, 4):
            cv.set(x + d[0] * i, y + d[1] * i, z - (i // 2), (120, 104, 88), 'deadwood')
            if i // 2:
                cv.set(x + d[0] * i, y + d[1] * i, z, (120, 104, 88), 'deadwood')      # face contact on the rise
    if crown_pts:
        sel = [crown_pts[int(i)] for i in rng.choice(len(crown_pts), size=min(10, len(crown_pts)), replace=False)]
        lowest = sorted(crown_pts, key=lambda p: -p[2])[:20]
        if 'fruit' in details:
            for (px, py, pz) in sel[:6]:
                cv.set(px, py, pz, (196, 60, 48), 'fruit')
        if 'blossom' in details:
            for (px, py, pz) in sel:
                cv.set(px, py, pz, (232, 170, 190), 'blossom')
        if 'vines' in details:
            for (px, py, pz) in lowest[:6]:
                for k in range(1, int(rng.integers(2, 5))):
                    if not cv.get(px, py, pz + k):
                        cv.set(px, py, pz + k, shade(leaf, 0.75), 'vine')
                    else:
                        break
        if 'nest' in details:
            px, py, pz = crown_pts[len(crown_pts) // 2]
            cv.set(px, py, pz, (124, 96, 66), 'nest')
        if 'ribbon' in details:
            px, py, pz = lowest[0]
            for k in range(1, 4):
                if not cv.get(px, py, pz + k):
                    cv.set(px, py, pz + k, (176, 48, 52), 'ribbon')
        if 'lantern' in details:
            px, py, pz = lowest[-1]
            if not cv.get(px, py, pz + 1):
                cv.set(px, py, pz + 1, (60, 52, 44), 'iron')
                if not cv.get(px, py, pz + 2):
                    cv.add_glow(px, py, pz + 2, (255, 196, 110))
    if 'mushrooms' in details:
        for (dx, dy) in ((2, 0), (0, 2), (-2, 1)):
            if rng.random() < 0.7 and cv.get(x + dx, y + dy, g) and not cv.get(x + dx, y + dy, g - 1):
                cv.set(x + dx, y + dy, g - 1, (214, 196, 170), 'mushroom')


def _connected(fn):
    """Run a plant builder, then drop any voxel it placed that is not face-connected to the ground inside its
    bounding box (jagged tiers can leave diagonal-only cells; those float and collapse). Never touches voxels
    that existed before."""
    @functools.wraps(fn)
    def wrap(cv, rng, x, y, g, *a, **kw):
        R = 24
        x0, x1, y0, y1 = max(0, x - R), min(511, x + R), max(0, y - R), min(511, y + R)
        sl = (slice(x0, x1 + 1), slice(y0, y1 + 1), slice(0, min(63, g) + 1))
        before = cv.solid[sl].copy()
        info = fn(cv, rng, x, y, g, *a, **kw)
        sub = cv.solid[sl]
        lab, n = ndi.label(sub, structure=ndi.generate_binary_structure(3, 1))
        ok = np.zeros(n + 1, bool)
        ok[np.unique(lab[:, :, -1][sub[:, :, -1]])] = True       # touches the ground layer under the plant
        ok[0] = True
        drop = ~ok[lab] & ~before
        if drop.any():
            sub[drop] = False
            cv.mat[sl][drop] = 0
        info['pruned_voxels'] = int(drop.sum())
        return info
    return wrap


@_connected
def broadleaf(cv, rng, x, y, g, pal, h=None, bark=(96, 74, 56), details=None):
    """Round-crowned tree: trunk + lumpy ellipsoid crown, two-palette blend top to bottom."""
    h = h or int(rng.integers(10, 22))
    i = int(rng.integers(0, len(pal)))
    fa, fb = pal[i], pal[(i + (1 if rng.random() < 0.5 else -1)) % len(pal)]
    details = details or pick_details(rng)
    w = 2 if h >= 16 else 1
    _trunk(cv, x, y, g, h, w, bark)
    cx, cy, cz = x + (w - 1) / 2, y + (w - 1) / 2, g - h
    rx = 2.5 + h * 0.28 * (0.85 + 0.3 * rng.random())
    rz = rx * (0.7 + 0.2 * rng.random())
    jag = _jag(rng)
    pts = []
    for X in range(int(cx - rx - 2), int(cx + rx + 3)):
        for Y in range(int(cy - rx - 2), int(cy + rx + 3)):
            for Z in range(int(cz - rz - 1), int(cz + rz + 2)):
                dx, dy, dz = X - cx, Y - cy, (Z - cz) / max(rz / rx, 0.3)
                d = math.sqrt(dx * dx + dy * dy + dz * dz)
                if d <= rx * jag(math.atan2(dy, dx)) and not cv.get(X, Y, Z):
                    t = (Z - (cz - rz)) / (2 * rz)
                    c = _blend(fa, fb, t + (rng.random() - 0.5) * 0.25)
                    cv.set(X, Y, Z, shade(c, 1.05 - 0.15 * t), 'leaf')
                    pts.append((X, Y, Z))
    for k in range(int(rz) + 1):                      # trunk runs up into the crown: face contact guaranteed
        cv.set(x, y, int(cz) + k, bark, 'bark')
    _decorate(cv, rng, x, y, g, h, details, pts, bark, fa)
    return {'species': 'broadleaf', 'h': h, 'details': details}


@_connected
def conifer(cv, rng, x, y, g, pal, h=None, bark=(84, 62, 48), details=None, clear=None):
    """Layered cone (sph_trees.spruce simplified): jagged tiers, two-palette blend, walk-under clearance."""
    h = h or int(rng.integers(13, 28))
    i = int(rng.integers(0, len(pal)))
    fa, fb = pal[i], pal[(i + 1) % len(pal)]
    details = details or pick_details(rng)
    clear = clear if clear is not None else int(rng.choice([2, 3, 4, 4, 5]))
    w = 2 if h >= 20 else 1
    _trunk(cv, x, y, g, h, w, bark)
    R0 = 0.2 * h + 1.4 + rng.random()
    period = int(rng.integers(2, 4))
    jag = _jag(rng)
    cx, cy = x + (w - 1) / 2, y + (w - 1) / 2
    pts = []
    for k in range(clear, h + 1):
        f = (k - clear) / max(h - clear, 1)
        phase = ((k - clear) % period) / period
        r = R0 * (1 - f) ** 1.05 * (1 - 0.32 * phase) + 0.45
        z = g - 1 - k
        ri = int(math.ceil(r + 1))
        for dx in range(-ri, ri + w):
            for dy in range(-ri, ri + w):
                px, py = x + dx, y + dy
                d = math.hypot(px - cx, py - cy)
                if d <= r * jag(math.atan2(py - cy, px - cx)) and not cv.get(px, py, z):
                    cv.set(px, py, z, _blend(fa, fb, f + (rng.random() - 0.5) * 0.2), 'leaf')
                    pts.append((px, py, z))
    cv.set(x, y, g - 1 - h, fb, 'leaf')            # the trunk column runs up to the tip (2-wide trunks too)
    cv.set(x, y, g - 2 - h, fb, 'leaf')
    _decorate(cv, rng, x, y, g, h, details, pts, bark, fa)
    return {'species': 'conifer', 'h': h, 'details': details}


@_connected
def bush(cv, rng, x, y, g, pal, details=None):
    r = 1.5 + rng.random() * 2.0
    i = int(rng.integers(0, len(pal)))
    fa, fb = pal[i], pal[(i + 1) % len(pal)]
    details = details or pick_details(rng, allow=('fruit', 'blossom', 'mushrooms', 'vines', 'moss', 'roots'))
    pts = []
    for X in range(int(x - r - 1), int(x + r + 2)):
        for Y in range(int(y - r - 1), int(y + r + 2)):
            for Z in range(int(g - r - 1), g):
                d = math.sqrt((X - x) ** 2 + (Y - y) ** 2 + ((Z - (g - 1)) * 1.4) ** 2)
                if d <= r and not cv.get(X, Y, Z):
                    cv.set(X, Y, Z, _blend(fa, fb, (g - Z) / (r + 1)), 'leaf')
                    pts.append((X, Y, Z))
    _decorate(cv, rng, int(x), int(y), g, 2, details, pts, (90, 70, 52), fa)
    return {'species': 'bush', 'h': int(r), 'details': details}


SPECIES = {'broadleaf': broadleaf, 'conifer': conifer, 'bush': bush}


def can_place(cv, x, y, footprint=3, max_slope=2, flag_mask=0xFF):
    """Lands on real ground (tests the surface it lands on), away from no-prop zones, on a gentle spot."""
    if not (footprint <= x < 512 - footprint and footprint <= y < 512 - footprint):
        return False
    if cv.keep[x - footprint:x + footprint + 1, y - footprint:y + footprint + 1].any():
        return False
    t = np.argmax(cv.solid[x - 1:x + 2, y - 1:y + 2], axis=2)
    if t.max() - t.min() > max_slope or t.min() >= 62:
        return False
    return cv.mat[x, y, int(t[1, 1])] in (cv.materials.get('ground', -1), cv.materials.get('grass', -1))


def plant_groves(cv, rng, centres, pal, species=('broadleaf', 'conifer', 'bush'), weights=None, per_grove=(5, 12),
                 radius=(8, 22), spacing=5, region_ok=None):
    """Groves around the given centres (not an even scatter). region_ok(x, y) -> bool can restrict halves.
    Returns {'trees': n, 'by_species': {...}, 'details': {...}} for build.json."""
    weights = weights or [1] * len(species)
    wsum = float(sum(weights))
    placed = []
    counts, dcount = {}, {}
    for (gx, gy) in centres:
        n = int(rng.integers(*per_grove))
        R = float(rng.uniform(*radius))
        for _ in range(n * 4):
            if n <= 0:
                break
            a, rr = rng.random() * 6.283, R * math.sqrt(rng.random())
            x, y = int(gx + rr * math.cos(a)), int(gy + rr * math.sin(a))
            if region_ok and not region_ok(x, y):
                continue
            if any((x - px) ** 2 + (y - py) ** 2 < spacing * spacing for px, py in placed):
                continue
            if not can_place(cv, x, y):
                continue
            sp = species[int(rng.choice(len(species), p=[w / wsum for w in weights]))]
            g = int(np.argmax(cv.solid[x, y]))
            info = SPECIES[sp](cv, rng, x, y, g, pal)
            placed.append((x, y))
            counts[sp] = counts.get(sp, 0) + 1
            for d in info['details']:
                dcount[d] = dcount.get(d, 0) + 1
            n -= 1
    return {'trees': len(placed), 'by_species': counts, 'details': dcount}
