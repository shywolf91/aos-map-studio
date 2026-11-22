"""Prop models for Royal Parade Snow Night (geometry + material names; the art pass colours them).

Every model is built through Placer, which refuses voxels inside the protected column boxes (spawn squares, the
under-platform strip) and records what it added, so the build can prove: nothing new in the squares, every new voxel
face-connected to the street (checked afterwards on the whole map), and the voxel diff against the original.
Graybox colours are function colours; rpsn_art recolours by material.
"""
from __future__ import annotations

import math

import numpy as np

FUNC = {'cover': (210, 60, 210), 'festive': (60, 200, 200), 'snow': (230, 230, 90), 'lamp': (255, 140, 0)}


class Placer:
    def __init__(self, cv, forbid_boxes):
        self.cv = cv
        self.forbid = np.zeros((512, 512), bool)
        for (x0, x1, y0, y1) in forbid_boxes:
            self.forbid[x0:x1 + 1, y0:y1 + 1] = True
        self.added = np.zeros(cv.solid.shape, bool)
        self.refused = 0
        self.pieces = []            # dicts: name, kind, box, z, voxels

    def put(self, x, y, z, c, mat, over=False):
        cv = self.cv
        if not (0 <= x < 512 and 0 <= y < 512 and 0 <= z < 63):
            return False
        if self.forbid[x, y]:
            self.refused += 1
            return False
        if cv.solid[x, y, z] and not over:
            return False
        if not cv.solid[x, y, z]:
            self.added[x, y, z] = True
        cv.set(x, y, z, c, mat)
        return True

    def begin(self):
        self._mark = self.added.copy()

    def end(self, name, kind, **extra):
        new = self.added & ~self._mark
        xs, ys, zs = np.nonzero(new)
        rec = {'name': name, 'kind': kind, 'voxels': int(len(xs))}
        if len(xs):
            rec['box'] = [int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())]
            rec['z'] = [int(zs.min()), int(zs.max())]
        rec.update(extra)
        self.pieces.append(rec)
        return rec


def ground_z(cv, x, y, zmin=0):
    col = cv.solid[x, y, zmin:]
    return zmin + int(np.argmax(col)) if col.any() else 63


# ----------------------------------------------------------------------------------------------- trees
def fir(P, cx, cy, r, h, mat='xtree', tub=True, base_z=None, name='fir'):
    """Deterministic tiered Christmas fir: tub (optional), 2-wide trunk, 4 tiers with drooping skirts, top spike.
    Column ground is read per column (the tree can straddle the median kerb). Returns the canopy surface points."""
    P.begin()
    cv = P.cv
    ix, iy = int(math.floor(cx)), int(math.floor(cy))
    g = base_z if base_z is not None else min(ground_z(cv, ix + dx, iy + dy) for dx in (0, 1) for dy in (0, 1))
    if tub:
        for x in range(ix - 2, ix + 4):
            for y in range(iy - 2, iy + 4):
                if math.hypot(x + 0.5 - cx - 0.5, y + 0.5 - cy - 0.5) <= 2.6:
                    gz = ground_z(cv, x, y)
                    for z in range(g - 1, gz):           # fill down to the column's own ground: no gaps
                        P.put(x, y, z, FUNC['cover'], mat + '_tub')
                    P.put(x, y, g - 1, FUNC['cover'], mat + '_tub')
    trunk_top = g - 4
    for x in (ix, ix + 1):
        for y in (iy, iy + 1):
            gz = ground_z(cv, x, y)
            for z in range(trunk_top, gz):
                P.put(x, y, z, FUNC['cover'], mat + '_trunk')
    tiers = 4
    k0 = 2                                               # lowest canopy level above the ground
    pts = []
    for k in range(k0, h):
        f = (k - k0) / max(h - k0 - 1, 1)
        tier_pos = (f * tiers) % 1.0                     # 0 at the bottom of a tier (wide skirt) -> 1 at its top
        rr = r * (1 - f) ** 0.92 * (1 - 0.30 * tier_pos) + 0.55
        z = g - 1 - k
        R = int(math.ceil(rr + 1))
        for x in range(ix - R, ix + R + 2):
            for y in range(iy - R, iy + R + 2):
                if math.hypot(x + 0.5 - (cx + 0.5), y + 0.5 - (cy + 0.5)) <= rr:
                    if P.put(x, y, z, FUNC['cover'], mat):
                        pts.append((x, y, z))
    for k in range(h, h + 2):                            # spike for the star
        P.put(ix, iy, g - 1 - k, FUNC['cover'], mat)
    star = (ix, iy, g - 1 - (h + 2))
    P.put(*star, FUNC['lamp'], mat + '_star')
    for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):  # star points, face-connected to the centre
        P.put(ix + dx, iy + dy, star[2], FUNC['lamp'], mat + '_star')
    rec = P.end(name, 'tree', c=[cx, cy], r=r, h=h, ground=int(g), star=list(star))
    return rec, pts


# ----------------------------------------------------------------------------------------------- snow
def drift(P, x0, x1, y0, y1, h, rng, mat='drift', name='drift', zmin=0):
    """Noise-warped snow mound filling the box; peak h above each column's ground, softly rounded edges."""
    P.begin()
    cv = P.cv
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = (x1 - x0) / 2 + 0.9, (y1 - y0) / 2 + 0.9
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            hh = int(round(h * max(0.0, 1 - d) ** 0.35 + rng.uniform(-0.4, 0.4)))
            hh = max(1, min(h, hh))
            gz = ground_z(cv, x, y, zmin)
            for z in range(gz - hh, gz):
                P.put(x, y, z, FUNC['snow'], mat)
    return P.end(name, 'drift', h=h)


def sleigh(P, x0, x1, y0, y1, h, facing, mat='sleigh', name='sleigh', zmin=0):
    """Parked sleigh in the box: runners curled at the front, a hollow seat tub, a high backrest at the rear.
    facing: +1 = front toward +y, -1 = toward -y (along y), or 'x+'/'x-' along x."""
    P.begin()
    cv = P.cv
    along_y = facing in (1, -1)
    L = (y1 - y0 + 1) if along_y else (x1 - x0 + 1)
    W = (x1 - x0 + 1) if along_y else (y1 - y0 + 1)
    sgn = facing if along_y else (1 if facing == 'x+' else -1)

    def cell(a, b):        # a along the length from the rear (0) to the front (L-1), b across (0..W-1)
        if along_y:
            y = y0 + a if sgn > 0 else y1 - a
            return x0 + b, y
        x = x0 + a if sgn > 0 else x1 - a
        return x, y0 + b
    for a in range(L):
        for b in range(W):
            x, y = cell(a, b)
            g = ground_z(cv, x, y, zmin)
            edge = b in (0, W - 1)
            if edge:                                     # runner
                P.put(x, y, g - 1, FUNC['festive'], mat + '_runner')
            if a == L - 1:                               # curled runner tip / dash
                if edge:
                    P.put(x, y, g - 2, FUNC['festive'], mat + '_runner')
                    P.put(x, y, g - 3, FUNC['festive'], mat + '_runner')
                continue
            top = g - 1 - (h if a <= 1 else max(3, h - 3 if a < L - 2 else h - 2))
            for z in range(top, g - 1):
                inner = 0 < b < W - 1 and 1 < a < L - 2 and z >= g - 3
                if inner and W >= 3:
                    continue                             # seat well
                P.put(x, y, z, FUNC['festive'], mat + ('_back' if a <= 1 else '_body'))
            if not edge and a > 0:
                P.put(x, y, g - 1, FUNC['festive'], mat + '_body')
    return P.end(name, 'sleigh', h=h)


def snowman(P, x, y, rng, mat='snowman', name='snowman'):
    """Three balls, coal eyes and buttons, carrot nose, top hat, scarf, stick arms (all face-connected)."""
    P.begin()
    cv = P.cv
    g = ground_z(cv, x, y)
    radii = [2.3, 1.7, 1.25]
    face = str(rng.choice(['x+', 'x-', 'y+', 'y-']))
    fdx, fdy = {'x+': (1, 0), 'x-': (-1, 0), 'y+': (0, 1), 'y-': (0, -1)}[face]
    c0 = g - 0.5 - radii[0]
    c1 = c0 - 0.85 * (radii[0] + radii[1])
    c2 = c1 - 0.85 * (radii[1] + radii[2])
    centres = [c0, c1, c2]
    for r, zc in zip(radii, centres):
        R = int(math.ceil(r))
        for dx in range(-R, R + 1):
            for dy in range(-R, R + 1):
                for z in range(int(math.floor(zc - r)) - 1, int(math.ceil(zc + r)) + 2):
                    if dx * dx + dy * dy + (z + 0.5 - zc - 0.5) ** 2 <= r * r + 0.3 and z < g:
                        P.put(x + dx, y + dy, z, FUNC['snow'], mat)
    for z in range(int(round(c2)), g):                   # core column: the stack is one piece
        P.put(x, y, z, FUNC['snow'], mat)
    hz = int(round(c2))
    for k in (2, 3):
        P.put(x + fdx * k, y + fdy * k, hz, (240, 120, 30), mat + '_nose')
    for s in (1, -1):                                    # coal eyes (recolour only)
        ex, ey = x + fdx + s * fdy, y + fdy + s * fdx
        if cv.solid[ex, ey, hz - 1]:
            P.put(ex, ey, hz - 1, (30, 30, 30), mat + '_coal', over=True)
    for k in (0, 1, 2):                                  # coal buttons down the front of the middle/base ball
        z = int(round(c1)) + k * 2 - 1
        for d in (2, 1):
            if cv.solid[x + fdx * d, y + fdy * d, z]:
                P.put(x + fdx * d, y + fdy * d, z, (30, 30, 30), mat + '_coal', over=True)
                break
    hat_z = int(round(c2 - radii[2])) - 1
    for z in range(hat_z - 2, hat_z + 1):
        P.put(x, y, z, (30, 30, 30), mat + '_hat')
    for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        P.put(x + dx, y + dy, hat_z, (30, 30, 30), mat + '_hat')
    nz = int(round(c1 - radii[1] * 0.85))                # scarf: recolour the neck ring, one tail hanging down
    for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        if cv.solid[x + dx, y + dy, nz]:
            P.put(x + dx, y + dy, nz, (200, 40, 40), mat + '_scarf', over=True)
    if cv.solid[x - fdx, y - fdy, nz] and cv.solid[x - fdx, y - fdy, nz + 1]:
        P.put(x - fdx, y - fdy, nz + 1, (200, 40, 40), mat + '_scarf', over=True)   # tail on the back
    ax, ay = (fdy, -fdx)
    az = int(round(c1))
    for s in (1, -1):
        for k in range(2, 4):
            P.put(x + ax * s * k, y + ay * s * k, az, (90, 60, 40), mat + '_arm')
        P.put(x + ax * s * 3, y + ay * s * 3, az - 1, (90, 60, 40), mat + '_arm')
    return P.end(name, 'snowman', face=face)


# ----------------------------------------------------------------------------------------------- lamps
def lamp(P, x, y, post_h=7, mat='lamp', name='lamp'):
    """Victorian street lamp: 1x1 post (footprint 1: no step, no centre clutter), lantern (glow source), cap, snow."""
    P.begin()
    cv = P.cv
    g = ground_z(cv, x, y)
    for z in range(g - post_h + 2, g):
        P.put(x, y, z, FUNC['lamp'], mat + '_post')
    P.put(x, y, g - post_h + 1, FUNC['lamp'], mat + '_collar')   # collar under the lantern
    lz = g - post_h - 1                                       # two-voxel lantern (both glow sources)
    lights = [(x, y, lz), (x, y, lz + 1)]
    P.put(x, y, lz + 1, FUNC['lamp'], mat + '_light')
    P.put(x, y, lz, FUNC['lamp'], mat + '_light')
    P.put(x, y, lz - 1, FUNC['lamp'], mat + '_cap')
    P.put(x, y, lz - 2, FUNC['snow'], 'snowcap')
    rec = P.end(name, 'lamp', light=[x, y, lz], lights=[list(p) for p in lights])
    return rec


# ----------------------------------------------------------------------------------------------- vehicles
def gift_stack(P, lab_mask, x0, x1, y0, y1, top_z, rng, mat='gift', name='gifts'):
    """Gift boxes stacked on a vehicle roof inside its own footprint: two wide boxes, one inset box, a bow."""
    P.begin()
    cv = P.cv
    roof = {}
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            col = lab_mask[x, y]
            if col.any():
                roof[(x, y)] = int(np.argmax(col))
    if not roof:
        return P.end(name, 'gifts', boxes=[])
    rz = min(roof.values())
    xm = (x0 + x1) // 2 + int(rng.integers(-1, 2))
    boxes = []
    del rz
    layers = [((x0, xm, y0, y1), 62, top_z + 2), ((xm + 1, x1, y0 + 1, y1), 62, top_z + 3),
              ((x0 + 1, x1 - 1, y0 + 1, y1 - 1), top_z + 2, top_z)]
    for gi, ((a0, a1, b0, b1), zlo, zhi) in enumerate(layers):
        for x in range(a0, a1 + 1):
            for y in range(b0, b1 + 1):
                if (x, y) not in roof:
                    continue
                for z in range(zhi, roof[(x, y)]):
                    if z <= zlo:
                        P.put(x, y, z, FUNC['festive'], f'{mat}{gi}')
        boxes.append({'box': [a0, a1, b0, b1], 'z': [zhi, zlo], 'mat': f'{mat}{gi}'})
    bx, by = (x0 + x1) // 2, (y0 + y1) // 2
    P.put(bx, by, top_z - 1, FUNC['festive'], mat + '_bow')
    P.put(bx - 1, by, top_z - 1, FUNC['festive'], mat + '_bow')
    P.put(bx + 1, by, top_z - 1, FUNC['festive'], mat + '_bow')
    return P.end(name, 'gifts', boxes=boxes)


def reindeer(P, x, y, g, facing, mat='reindeer'):
    """Small reindeer along x: 4 legs, 3-long body, neck, head, antlers, red nose (glow added by the art pass)."""
    s = 1 if facing == 'x+' else -1
    for dx in (0, 2):
        for z in range(g - 3, g):
            P.put(x + s * dx, y, z, FUNC['festive'], mat)
    for dx in range(0, 3):
        P.put(x + s * dx, y, g - 4, FUNC['festive'], mat)
    P.put(x + s * 3, y, g - 4, FUNC['festive'], mat)
    P.put(x + s * 3, y, g - 5, FUNC['festive'], mat)
    P.put(x + s * 3, y, g - 6, FUNC['festive'], mat)
    P.put(x + s * 4, y, g - 6, FUNC['festive'], mat + '_nose')
    P.put(x + s * 3, y, g - 7, FUNC['festive'], mat + '_antler')
    P.put(x + s * 2, y, g - 7, FUNC['festive'], mat + '_antler')
    P.put(x + s * 2, y, g - 8, FUNC['festive'], mat + '_antler')
    P.put(x + s * 3, y, g - 8, FUNC['festive'], mat + '_antler')
    return (x + s * 4, y, g - 6)


def sleigh_float(P, cv, comp_mask, box, facing, h_max, name, street_z=56):
    """Rebuild a vehicle as Santa's sleigh float inside its own footprint and no taller than before."""
    x0, x1, y0, y1 = box
    old = comp_mask.copy()
    n_removed = int(old.sum())
    cv.solid[old] = False
    cv.mat[old] = 0
    P.begin()
    L = x1 - x0 + 1
    deer_len = 5 if L >= 11 else 0
    sx0, sx1 = (x0, x1 - deer_len) if facing == 'x+' else (x0 + deer_len, x1)
    rec_s = sleigh(P, sx0, sx1, y0, y1, min(h_max, 6), facing, mat='santa_sleigh', name=name + ' body')
    P.pieces.pop()
    noses = []
    street = int(street_z)
    if deer_len:
        yy = [y0, y1] if (y1 - y0) >= 2 else [y0]
        gx = x1 - deer_len + 1 if facing == 'x+' else x0 + deer_len - 1
        for y in yy:
            noses.append(list(reindeer(P, gx, y, street, facing)))
        # harness: a strap from the sleigh front to the first reindeer on each side (z of the reindeer back)
        fx = sx1 if facing == 'x+' else sx0
        for y in yy:
            for x in range(min(fx, gx), max(fx, gx) + 1):
                P.put(x, y, street - 4, FUNC['festive'], 'harness')
    # gift sack standing on the seat floor (street - 1) in the seat well
    cxm = (sx0 + sx1) // 2
    cym = (y0 + y1) // 2
    for z in range(street - 4, street - 1):
        P.put(cxm, cym, z, FUNC['festive'], 'sack')
    rec = P.end(name, 'sleigh_float', removed=n_removed, noses=noses, facing=facing)
    return rec
