"""Original prop / structure library for The Wicker King's Harvest.

Everything writes material ids into V.m[x, y, z] (z down; ground top voxel at z = g, so 'k above ground' is
z = g - k). Every prop is built face-connected to the ground or to a host it rests on.
"""
from __future__ import annotations

import math

import numpy as np

# ------------------------------------------------------------------ materials
AIR = 0
M = {}
_names = ('ROCK SHORE_ROCK SKIN SOIL DIRT PATH FIELD FURROW PIT_ROCK EMBER ASH CLEARING STONE STONE_DARK '
          'TIMBER PLANK BARN BARN_TRIM ROOF STRAW PUMPKIN PUMPKIN_DK STEM_GREEN VINE DEADWOOD WICKER '
          'WICKER_DK GLOW IRON CLOTH_TEAM CLOTH_RAG STALK FLESH FENCE MOSS JACK GRASS SEA STAIR GRAVE '
          'SHINGLE_GREY WALL_GREY WINDOW CANDLE EARTH_DK ROPE HULL LEAF_DK LEAF_RUST LEAF_ORANGE LEAF_BROWN SILO SILO_BAND HAY_LITTER STALK_DK '
          'MOON MOON_DK MOON_RIM CROW CROW_BEAK BAT BAT_EYE').split()
for i, n in enumerate(_names, start=1):
    M[n] = i
globals().update(M)


class Vox:
    def __init__(self, H):
        self.m = np.zeros((512, 512, 64), np.uint8)
        self.H = H                       # terrain top z per column (int)

    # --- basic ops (inclusive ranges)
    def box(self, x0, x1, y0, y1, z0, z1, mat):
        x0, x1 = sorted((int(x0), int(x1))); y0, y1 = sorted((int(y0), int(y1))); z0, z1 = sorted((int(z0), int(z1)))
        x0 = max(x0, 0); y0 = max(y0, 0); z0 = max(z0, 0)
        x1 = min(x1, 511); y1 = min(y1, 511); z1 = min(z1, 63)
        if x0 > x1 or y0 > y1 or z0 > z1:
            return
        self.m[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1] = mat

    def put(self, x, y, z, mat):
        x, y, z = int(x), int(y), int(z)
        if 0 <= x < 512 and 0 <= y < 512 and 0 <= z < 64:
            self.m[x, y, z] = mat

    def get(self, x, y, z):
        x, y, z = int(x), int(y), int(z)
        if 0 <= x < 512 and 0 <= y < 512 and 0 <= z < 64:
            return self.m[x, y, z]
        return 255

    def ground(self, x, y):
        """Top solid z of the current voxel column."""
        col = self.m[int(x), int(y)]
        nz = np.nonzero(col)[0]
        return int(nz[0]) if len(nz) else 63

    def column_to_ground(self, x, y, z_top, mat):
        """Fill from z_top down to the first solid voxel (foundations / posts)."""
        x, y = int(x), int(y)
        z = int(z_top)
        while z < 64 and self.m[x, y, z] == AIR:
            self.m[x, y, z] = mat
            z += 1

    def line4(self, p0, p1, mat, only_air=False):
        """4/6-connected voxel line (face connected) from p0 to p1 (x, y, z)."""
        x0, y0, z0 = [int(round(v)) for v in p0]
        x1, y1, z1 = [int(round(v)) for v in p1]
        x, y, z = x0, y0, z0
        n = abs(x1 - x0) + abs(y1 - y0) + abs(z1 - z0)
        pts = [(x, y, z)]
        for i in range(n):
            # step along the axis that is furthest behind its proportional target
            t = (i + 1) / n
            tx, ty, tz = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, z0 + (z1 - z0) * t
            ex, ey, ez = abs(tx - x), abs(ty - y), abs(tz - z)
            if ex >= ey and ex >= ez and x != x1:
                x += 1 if x1 > x else -1
            elif ey >= ez and y != y1:
                y += 1 if y1 > y else -1
            elif z != z1:
                z += 1 if z1 > z else -1
            elif x != x1:
                x += 1 if x1 > x else -1
            elif y != y1:
                y += 1 if y1 > y else -1
            pts.append((x, y, z))
        for (a, b, c) in pts:
            if not only_air or self.get(a, b, c) == AIR:
                self.put(a, b, c, mat)
        return pts


# ------------------------------------------------------------------ small props

def pumpkin(V, x, y, g, size=1, carved=False, face_dir=(0, 1), rng=None):
    """size 0: 2x2x1, 1: 3x3x2, 2: 5x5x3 ribbed, 3: 7x7x5 giant."""
    if size == 0:
        V.box(x, x + 1, y, y + 1, g - 1, g - 1, PUMPKIN)
        V.put(x, y, g - 2, STEM_GREEN)
        return
    r = {1: 1, 2: 2, 3: 3}[size]
    h = {1: 2, 2: 3, 3: 5}[size]
    for k in range(h):
        z = g - 1 - k
        # squashed sphere cross-section
        frac = (k + 0.5) / h
        rr = r + 0.5 - (abs(frac - 0.45) * 1.6) ** 2 * (r + 0.5)
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if dx * dx + dy * dy <= rr * rr + 0.6:
                    mat = PUMPKIN if ((dx + dy) % 2 == 0 or size == 1) else PUMPKIN_DK
                    if size >= 2 and (dx == 0 or dy == 0) and abs(dx) + abs(dy) == r:
                        mat = PUMPKIN_DK
                    V.put(x + dx, y + dy, z, mat)
    V.put(x, y, g - 1 - h, STEM_GREEN)
    if size >= 2:
        V.put(x, y, g - 2 - h, STEM_GREEN)
        if size == 3:
            V.put(x + 1, y, g - 2 - h, STEM_GREEN)
    if carved:
        fx, fy = face_dir
        # carve eyes + grin on the face side (glowing)
        for (u, v) in ([(-1, h - 2), (1, h - 2), (-1, 1), (0, 1), (1, 1)] if size == 2 else
                       [(-2, h - 2), (-1, h - 2), (1, h - 2), (2, h - 2), (-2, 1), (-1, 1), (0, 0), (1, 1), (2, 1)]
                       if size == 3 else [(0, 1)]):
            px = x + fx * r + (fy != 0) * u
            py = y + fy * r + (fx != 0) * u
            V.put(px, py, g - 1 - v, JACK)


def hay_bale(V, x, y, g, along_x=True):
    if along_x:
        V.box(x, x + 2, y, y + 1, g - 2, g - 1, STRAW)
    else:
        V.box(x, x + 1, y, y + 2, g - 2, g - 1, STRAW)


def hay_stack(V, x, y, g, rng):
    """A small pile of bales (max 3 tall)."""
    hay_bale(V, x, y, g, True); hay_bale(V, x, y + 2, g, True); hay_bale(V, x + 3, y, g, False)
    if rng.random() < 0.7:
        hay_bale(V, x, y + 1, g - 2, True)


def lantern_post(V, x, y, g, h=4, arm=(1, 0)):
    V.box(x, x, y, y, g - h, g - 1, TIMBER)
    ax, ay = arm
    V.put(x + ax, y + ay, g - h, TIMBER)
    V.put(x + ax, y + ay, g - h + 1, IRON)
    V.put(x + ax, y + ay, g - h + 2, GLOW)


def standing_stone(V, x, y, g, h, w=2, rng=None, lean=0):
    for k in range(h):
        sh = 1 if (lean and k >= h // 2) else 0
        ww = w if k < h - 1 else max(1, w - 1)
        V.box(x + sh * lean, x + sh * lean + ww - 1, y, y + w - 1, g - 1 - k, g - 1 - k, STONE)
    V.box(x - 1, x + w, y - 1, y + w, g, g, STONE_DARK)   # sunk footing ring (stays flush with ground)


def dead_tree(V, x, y, g, h, rng, girth=2, leaves=None):
    """Gnarled tree: tapering trunk (kinks keep face contact), 3-6 limbs rooted on the trunk, twigs.
    leaves: None (dead) or a list of leaf materials for sparse autumn clumps at limb ends."""
    trunk = {}
    cx, cy = x, y
    for k in range(h):
        z = g - 1 - k
        gw = girth if k < h * 0.45 else max(1, girth - 1)
        if k > 2 and k % 4 == 0 and rng.random() < 0.5:
            nx, ny = cx + int(rng.integers(-1, 2)), cy + int(rng.integers(-1, 2))
            V.box(min(cx, nx), max(cx, nx) + gw - 1, min(cy, ny), max(cy, ny) + gw - 1, z, z, DEADWOOD)
            cx, cy = nx, ny
        V.box(cx, cx + gw - 1, cy, cy + gw - 1, z, z, DEADWOOD)
        trunk[z] = (cx, cy, gw)
    V.put(cx, cy, g - h, DEADWOOD)
    trunk[g - h] = (cx, cy, 1)
    for (rx, ry) in ((-1, 0), (girth, 0), (0, -1), (0, girth)):
        if rng.random() < 0.7:
            V.put(x + rx, y + ry, g - 1, DEADWOOD)
    ends = []
    nlimb = int(rng.integers(3, 7))
    for i in range(nlimb):
        a = rng.random() * 2 * math.pi
        z0 = g - int(h * (0.45 + 0.5 * rng.random()))
        z0 = min(max(z0, g - h), g - 2)
        tx, ty, gw = trunk[z0]
        L = int(h * (0.35 + 0.35 * rng.random()))
        sx = tx + (gw - 1) * (math.cos(a) > 0); sy = ty + (gw - 1) * (math.sin(a) > 0)
        ex, ey = sx + math.cos(a) * L, sy + math.sin(a) * L
        ez = max(z0 - L * (0.3 + 0.5 * rng.random()), 2)
        pts = V.line4((sx, sy, z0), (ex, ey, ez), DEADWOOD)
        px, py, pz = pts[-1]
        for j in range(2):
            b = a + (rng.random() - 0.5) * 1.6
            V.line4((px, py, pz), (px + math.cos(b) * 3, py + math.sin(b) * 3, pz - 2 - j), DEADWOOD)
        ends.append(pts[-1])
        if leaves:
            mid = pts[len(pts) // 2]
            ends.append(mid)
    if leaves:
        for (ex, ey, ez) in ends:
            r = 2.2 + rng.random() * 1.3
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    for dz in range(-2, 2):
                        d = math.sqrt(dx * dx + dy * dy + (dz * 1.6) ** 2)
                        if d <= r and rng.random() < 0.72:
                            px, py, pz = ex + dx, ey + dy, ez + dz
                            if V.get(px, py, pz) == AIR:
                                # only keep leaves that touch something already placed (face contact)
                                if (V.get(px + 1, py, pz) or V.get(px - 1, py, pz) or V.get(px, py + 1, pz) or
                                        V.get(px, py - 1, pz) or V.get(px, py, pz + 1) or V.get(px, py, pz - 1)):
                                    V.put(px, py, pz, leaves[int(rng.integers(0, len(leaves)))])
    return ends


def leaf_litter(V, x, y, gfun, rng, r=6, mats=None):
    """Fallen leaves recolour the ground top (no geometry)."""
    mats = mats or [LEAF_RUST, LEAF_BROWN, LEAF_ORANGE]
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r and rng.random() < 0.45 * (1 - (dx * dx + dy * dy) / (r * r + 1)) + 0.1:
                g = gfun(x + dx, y + dy)
                if V.get(x + dx, y + dy, g) in (SOIL, SKIN, PATH, CLEARING):
                    V.put(x + dx, y + dy, g, mats[int(rng.integers(0, len(mats)))])


def big_tree(V, x, y, g, rng, trunk_h=9, cr=8, ch=5, leaves=None, lean=(0, 0)):
    """Broad autumn shade tree: 3x3 trunk, forked limbs, dense ellipsoid canopy (face connected to limbs)."""
    leaves = leaves or [LEAF_RUST, LEAF_ORANGE, LEAF_BROWN, LEAF_RUST, LEAF_ORANGE]
    V.box(x - 1, x + 1, y - 1, y + 1, g - trunk_h, g - 1, DEADWOOD)
    for (rx, ry) in ((-2, 0), (2, 0), (0, -2), (0, 2)):
        V.box(x + rx, x + rx, y + ry, y + ry, g - 2, g - 1, DEADWOOD)
    zc = g - trunk_h - ch // 2 - 1
    for k in range(5):
        a = k * 2 * math.pi / 5 + rng.random() * 0.6
        V.line4((x, y, g - trunk_h + 1), (x + math.cos(a) * cr * 0.6 + lean[0], y + math.sin(a) * cr * 0.6 + lean[1],
                                           zc), DEADWOOD)
    V.box(x, x, y, y, zc - 1, g - trunk_h, DEADWOOD)
    for dx in range(-cr - 1, cr + 2):
        for dy in range(-cr - 1, cr + 2):
            for dz in range(-ch, ch + 1):
                d = math.sqrt((dx - lean[0]) ** 2 + (dy - lean[1]) ** 2) / cr
                dv = dz / ch
                if d * d + dv * dv <= 1.0:
                    edge = d * d + dv * dv > 0.62
                    if edge and rng.random() < 0.28:
                        continue
                    px, py, pz = x + dx, y + dy, zc + dz
                    if V.get(px, py, pz) == AIR:
                        V.put(px, py, pz, leaves[int(rng.integers(0, len(leaves)))])


def hedge(V, pts, gfun, rng, h=2, gap_p=0.08):
    """Low hedgerow (2 wide, 2-3 high) of dark leaves and vines, broken by gaps."""
    for (p, q) in zip(pts[:-1], pts[1:]):
        n = int(max(abs(q[0] - p[0]), abs(q[1] - p[1])))
        gap = 0
        for k in range(n + 1):
            x = int(round(p[0] + (q[0] - p[0]) * k / max(n, 1)))
            y = int(round(p[1] + (q[1] - p[1]) * k / max(n, 1)))
            if gap > 0:
                gap -= 1
                continue
            if rng.random() < gap_p:
                gap = int(rng.integers(2, 4))
                continue
            for (dx, dy) in ((0, 0), (1, 0), (0, 1), (1, 1)):
                g = gfun(x + dx, y + dy)
                hh = h + (1 if rng.random() < 0.3 else 0)
                for kk in range(1, hh + 1):
                    V.put(x + dx, y + dy, g - kk, LEAF_DK if rng.random() < 0.6 else VINE)
            if rng.random() < 0.06:
                V.put(x, y, gfun(x, y) - h - 1, LEAF_RUST)


def silo(V, x, y, g, r=4, h=15, roof=ROOF):
    """Round wooden grain silo with iron bands, conical roof and a hatch; solid core (sightline cover)."""
    for k in range(h):
        z = g - 1 - k
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r + 1:
                    V.put(x + dx, y + dy, z, SILO_BAND if k % 5 == 2 else SILO)
    for k in range(r + 3):
        rr = r + 1 - k
        z = g - h - 1 - k
        for dx in range(-r - 1, r + 2):
            for dy in range(-r - 1, r + 2):
                if dx * dx + dy * dy <= rr * rr + 0.5:
                    V.put(x + dx, y + dy, z, roof)
        if rr <= 0:
            break
    V.put(x, y, g - h - r - 3, IRON)
    V.box(x - r - 1, x + r + 1, y - r - 1, y + r + 1, g, g, STONE)


def scarecrow(V, x, y, g, rng, facing=(0, 1)):
    V.box(x, x, y, y, g - 7, g - 1, TIMBER)
    fx, fy = facing
    ax, ay = (1, 0) if fy != 0 else (0, 1)
    for s in range(-3, 4):
        V.put(x + ax * s, y + ay * s, g - 5, TIMBER)
    # ragged coat
    for s in range(-1, 2):
        for k in range(3, 6):
            V.put(x + ax * s, y + ay * s, g - k, CLOTH_RAG)
    V.put(x + ax * -2, y + ay * -2, g - 4, CLOTH_RAG)
    V.put(x + ax * 2, y + ay * 2, g - 4, CLOTH_RAG)
    # straw hands
    V.put(x + ax * 4, y + ay * 4, g - 5, STRAW); V.put(x - ax * 4, y - ay * 4, g - 5, STRAW)
    # pumpkin head
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for k in (8, 9):
                V.put(x + dx, y + dy, g - k, PUMPKIN if (dx == 0 or dy == 0 or k == 8) else PUMPKIN_DK)
    V.put(x, y, g - 10, STEM_GREEN)
    V.put(x + fx, y + fy, g - 9, JACK)
    V.put(x + fx + ax, y + fy + ay, g - 9, JACK)
    V.put(x + fx - ax, y + fy - ay, g - 9, JACK)
    # hat brim
    V.box(x - 1, x + 1, y - 1, y + 1, g - 10, g - 10, CLOTH_RAG)
    V.put(x, y, g - 11, CLOTH_RAG)


def cart(V, x, y, g, along_x=True, load=STRAW):
    if along_x:
        V.box(x, x + 5, y, y + 3, g - 2, g - 2, PLANK)
        for xx in (x, x + 5):
            V.box(xx, xx, y, y + 3, g - 3, g - 3, TIMBER)
        V.box(x, x + 5, y, y, g - 3, g - 3, TIMBER); V.box(x, x + 5, y + 3, y + 3, g - 3, g - 3, TIMBER)
        for yy in (y - 1, y + 4):
            V.box(x + 1, x + 3, yy, yy, g - 2, g - 2, IRON)
            V.box(x + 2, x + 2, yy, yy, g - 3, g - 1, IRON)
            V.box(x + 1, x + 3, yy, yy, g - 1, g - 1, IRON)
        V.box(x - 3, x - 1, y + 1, y + 1, g - 2, g - 2, TIMBER)
        V.box(x - 3, x - 1, y + 2, y + 2, g - 2, g - 2, TIMBER)
        if load:
            V.box(x + 1, x + 4, y + 1, y + 2, g - 3, g - 3, load)
            V.box(x + 2, x + 3, y + 1, y + 2, g - 4, g - 4, load)
    else:
        V.box(x, x + 3, y, y + 5, g - 2, g - 2, PLANK)
        for yy in (y, y + 5):
            V.box(x, x + 3, yy, yy, g - 3, g - 3, TIMBER)
        V.box(x, x, y, y + 5, g - 3, g - 3, TIMBER); V.box(x + 3, x + 3, y, y + 5, g - 3, g - 3, TIMBER)
        for xx in (x - 1, x + 4):
            V.box(xx, xx, y + 1, y + 3, g - 2, g - 2, IRON)
            V.box(xx, xx, y + 2, y + 2, g - 3, g - 1, IRON)
            V.box(xx, xx, y + 1, y + 3, g - 1, g - 1, IRON)
        V.box(x + 1, x + 1, y - 3, y - 1, g - 2, g - 2, TIMBER)
        V.box(x + 2, x + 2, y - 3, y - 1, g - 2, g - 2, TIMBER)
        if load:
            V.box(x + 1, x + 2, y + 1, y + 4, g - 3, g - 3, load)
            V.box(x + 1, x + 2, y + 2, y + 3, g - 4, g - 4, load)


def banner(V, x, y, g, h=9, dirx=1):
    """Pole with a hanging team cloth (CLOTH_TEAM recoloured per side after mirroring)."""
    V.box(x, x, y, y, g - h - 1, g - 1, TIMBER)
    V.put(x, y, g - h - 2, IRON)
    for s in range(1, 4):
        V.put(x + dirx * s, y, g - h, TIMBER)
    for s in range(1, 4):
        drop = 5 if s != 2 else 6
        for k in range(1, drop + 1):
            V.put(x + dirx * s, y, g - h + k, CLOTH_TEAM)
    V.put(x + dirx * 2, y, g - h + 3, STRAW)   # pale sigil


def fence(V, pts, gfun, rng, rail_h=2, gap_p=0.06, post_every=3, mat=FENCE):
    """Crooked post-and-rail fence along a 2D polyline; rails follow the ground face-connected."""
    last = None
    i = 0
    for (p, q) in zip(pts[:-1], pts[1:]):
        n = int(max(abs(q[0] - p[0]), abs(q[1] - p[1])))
        for k in range(n + (1 if q == pts[-1] else 0)):
            x = int(round(p[0] + (q[0] - p[0]) * k / max(n, 1)))
            y = int(round(p[1] + (q[1] - p[1]) * k / max(n, 1)))
            if last is not None and (x, y) == last[:2]:
                continue
            g = gfun(x, y)
            post = (i % post_every == 0)
            broken = rng.random() < gap_p and not post
            if post:
                V.box(x, x, y, y, g - rail_h - (1 if rng.random() < 0.3 else 0), g - 1, mat)
            elif not broken:
                V.put(x, y, g - rail_h, mat)
                if last is not None and last[2] is not None and last[2] != g - rail_h:
                    lz = last[2]
                    V.box(x, x, y, y, min(lz, g - rail_h), max(lz, g - rail_h), mat)
                if last is not None and abs(x - last[0]) + abs(y - last[1]) == 2:
                    V.put(last[0], y, g - rail_h, mat)   # keep diagonal runs face connected
            last = (x, y, None if broken else g - rail_h)
            i += 1


def drystone_wall(V, pts, gfun, rng, h=2, gap_p=0.05):
    last = None
    for (p, q) in zip(pts[:-1], pts[1:]):
        n = int(max(abs(q[0] - p[0]), abs(q[1] - p[1])))
        for k in range(n + 1):
            x = int(round(p[0] + (q[0] - p[0]) * k / max(n, 1)))
            y = int(round(p[1] + (q[1] - p[1]) * k / max(n, 1)))
            if rng.random() < gap_p:
                last = None
                continue
            g = gfun(x, y)
            hh = h if rng.random() > 0.25 else h - 1
            V.box(x, x, y, y, g - hh, g - 1, STONE_DARK)
            if last is not None and abs(x - last[0]) + abs(y - last[1]) == 2:
                V.box(last[0], last[0], y, y, g - hh, g - 1, STONE_DARK)
            last = (x, y)


def vine_run(V, x, y, gfun, rng, length=24, pumpkins=True):
    """Ground-hugging vine wandering on the surface with leaves and small pumpkins."""
    a = rng.random() * 2 * math.pi
    px, py = float(x), float(y)
    for k in range(length):
        a += (rng.random() - 0.5) * 0.9
        nx, ny = px + math.cos(a), py + math.sin(a)
        ix, iy = int(round(nx)), int(round(ny))
        jx, jy = int(round(px)), int(round(py))
        if not (2 < ix < 509 and 2 < iy < 509):
            break
        g = gfun(ix, iy)
        g0 = gfun(jx, iy)
        V.put(jx, iy, g0 - 1, VINE)          # elbow keeps face contact
        V.put(ix, iy, g - 1, VINE)
        if rng.random() < 0.25:
            V.put(ix + int(rng.integers(-1, 2)), iy, g - 1, LEAF_DK)
        if pumpkins and rng.random() < 0.07:
            pumpkin(V, ix + 1, iy + 1, gfun(ix + 1, iy + 1), size=int(rng.integers(0, 2)))
        px, py = nx, ny


# ------------------------------------------------------------------ buildings

def barn(V, x0, x1, y0, y1, g, door_side='S', wall_h=8, mat_wall=BARN, mat_roof=ROOF):
    """Gambrel-roofed barn, ridge along x. Hollow, open doors, cupola, hayloft door."""
    # foundation (2 courses of pale stone), flush pad
    V.box(x0, x1, y0, y1, g - 2, g, STONE)
    for z in range(g + 1, 64):
        if V.m[x0, y0, z] == AIR:
            V.box(x0, x1, y0, y1, z, z, STONE)
    V.box(x0 + 1, x1 - 1, y0 + 1, y1 - 1, g - 2, g - 2, PLANK)        # floor
    zt = g - 2 - wall_h                                                 # top of walls (eave) z
    # walls
    V.box(x0, x1, y0, y0, zt, g - 3, mat_wall); V.box(x0, x1, y1, y1, zt, g - 3, mat_wall)
    V.box(x0, x0, y0, y1, zt, g - 3, mat_wall); V.box(x1, x1, y0, y1, zt, g - 3, mat_wall)
    for (cx, cy) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        V.box(cx, cx, cy, cy, zt, g - 3, BARN_TRIM)
    # gambrel profile across y
    prof = []
    for j in range(y0 - 1, y1 + 2):
        i = min(j - (y0 - 1), (y1 + 1) - j)                             # inset from eave line
        if i <= 2:
            hr = 2 * i
        else:
            hr = 4 + (i - 2) * 0.8
        prof.append((j, int(round(hr))))
    pd = dict(prof)
    for j, hr in prof:
        thick = max(1, hr - min(pd.get(j - 1, hr), pd.get(j + 1, hr)))
        ztop = zt - hr
        V.box(x0 - 1, x1 + 1, j, j, ztop, min(ztop + thick, zt), mat_roof)
    # gable ends filled under the roof
    for j, hr in prof:
        if y0 <= j <= y1:
            V.box(x0, x0, j, j, zt - hr + 1, zt, mat_wall)
            V.box(x1, x1, j, j, zt - hr + 1, zt, mat_wall)
    # ridge cap + cupola
    ymid = (y0 + y1) // 2
    hr_max = max(h for _, h in prof)
    V.box(x0 - 1, x1 + 1, ymid, ymid + ((y1 - y0) % 2), zt - hr_max - 1, zt - hr_max - 1, BARN_TRIM)
    xm = (x0 + x1) // 2
    zc = zt - hr_max - 1
    V.box(xm - 1, xm + 1, ymid - 1, ymid + 1, zc - 3, zc - 1, BARN_TRIM)
    V.box(xm - 2, xm + 2, ymid - 2, ymid + 2, zc - 4, zc - 4, mat_roof)
    V.box(xm - 1, xm + 1, ymid - 1, ymid + 1, zc - 5, zc - 5, mat_roof)
    V.put(xm, ymid, zc - 6, IRON); V.put(xm, ymid, zc - 7, IRON); V.put(xm + 1, ymid, zc - 7, IRON)
    # big doors (open) on the door side, with white X-bracing on the leaves
    xd0, xd1 = xm - 3, xm + 3
    yw = y1 if door_side == 'S' else y0
    out = 1 if door_side == 'S' else -1
    V.box(xd0, xd1, yw, yw, g - 8, g - 3, AIR)
    V.box(xd0 - 1, xd1 + 1, yw, yw, g - 9, g - 9, BARN_TRIM)
    for side, xs in ((-1, xd0 - 1), (1, xd1 + 1)):
        # swung-open leaf, standing out from the wall
        for k in range(1, 4):
            V.box(xs, xs, yw + out * k, yw + out * k, g - 8, g - 3, mat_wall)
        V.box(xs, xs, yw + out * 1, yw + out * 3, g - 8, g - 8, BARN_TRIM)
        V.box(xs, xs, yw + out * 1, yw + out * 3, g - 3, g - 3, BARN_TRIM)
    # hay loft floor over the west third
    V.box(x0 + 1, x0 + (x1 - x0) // 3, y0 + 1, y1 - 1, zt, zt, PLANK)
    # hayloft door on the west gable with hay poking out
    V.box(x0, x0, ymid - 1, ymid + 1, zt - 3, zt - 1, AIR)
    V.box(x0 + 1, x0 + 2, ymid - 1, ymid + 1, zt - 1, zt - 1, STRAW)
    V.box(x0 - 1, x0 - 1, ymid, ymid, zt - 5, zt - 4, TIMBER)         # hay hoist beam
    V.put(x0 - 2, ymid, zt - 5, TIMBER); V.put(x0 - 2, ymid, zt - 4, ROPE); V.put(x0 - 2, ymid, zt - 3, ROPE)
    # side windows (dark) on the long walls
    for xx in range(x0 + 3, x1 - 2, 6):
        if xd0 - 1 <= xx <= xd1 + 1:
            continue
        for yy in (y0, y1):
            V.box(xx, xx + 1, yy, yy, g - 7, g - 6, WINDOW)
    # interior: stalls and hay
    for xx in range(x0 + 2, x1 - 1, 5):
        V.box(xx, xx, y0 + 1, y0 + 5, g - 4, g - 3, PLANK)
    V.box(x0 + 2, x0 + 6, y1 - 4, y1 - 2, g - 4, g - 3, STRAW)


def farmhouse(V, x0, x1, y0, y1, g, wall=WALL_GREY, roof=SHINGLE_GREY, porch='E'):
    V.box(x0, x1, y0, y1, g - 1, g, STONE)
    for z in range(g + 1, 64):
        if V.m[x0, y0, z] == AIR:
            V.box(x0, x1, y0, y1, z, z, STONE)
    zt = g - 11
    V.box(x0, x1, y0, y1, zt, g - 2, wall)
    V.box(x0 + 1, x1 - 1, y0 + 1, y1 - 1, zt + 1, g - 2, AIR)
    V.box(x0 + 1, x1 - 1, y0 + 1, y1 - 1, g - 6, g - 6, PLANK)       # upper floor
    for (cx, cy) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        V.box(cx, cx, cy, cy, zt, g - 2, TIMBER)
    V.box(x0, x1, y0, y0, g - 6, g - 6, TIMBER); V.box(x0, x1, y1, y1, g - 6, g - 6, TIMBER)
    V.box(x0, x0, y0, y1, g - 6, g - 6, TIMBER); V.box(x1, x1, y0, y1, g - 6, g - 6, TIMBER)
    # gable roof, ridge along y (steep 1:1), overhang 1
    half = (x1 - x0) // 2 + 1
    for i in range(half + 1):
        for xx in (x0 - 1 + i, x1 + 1 - i):
            V.box(xx, xx, y0 - 1, y1 + 1, zt - i, zt - i + 1, roof)
    for i in range(half):
        V.box(x0 + i, x1 - i, y0, y0, zt - i, zt, wall)
        V.box(x0 + i, x1 - i, y1, y1, zt - i, zt, wall)
    # windows: lit and dark, both storeys
    for yy in range(y0 + 2, y1 - 1, 4):
        for (zz, lit) in ((g - 4, True), (g - 9, yy % 8 == (y0 + 2) % 8)):
            V.box(x0, x0, yy, yy + 1, zz - 1, zz, GLOW if lit else WINDOW)
            V.box(x1, x1, yy, yy + 1, zz - 1, zz, WINDOW if lit else GLOW)
    # chimney on the north gable
    cx = (x0 + x1) // 2 + 2
    V.box(cx, cx + 1, y0 - 1, y0, zt - half - 2, g - 2, STONE_DARK)
    V.put(cx, y0 - 1, zt - half - 3, STONE_DARK)
    # porch + door on the east (or west) side
    px = x1 + 1 if porch == 'E' else x0 - 3
    V.box(px, px + 2, y0 + 2, y1 - 2, g - 1, g - 1, PLANK)
    for yy in (y0 + 2, y1 - 2):
        V.box(px + (2 if porch == 'E' else 0), px + (2 if porch == 'E' else 0), yy, yy, g - 6, g - 2, TIMBER)
    V.box(px, px + 2, y0 + 1, y1 - 1, g - 7, g - 7, roof)
    dx = x1 if porch == 'E' else x0
    ym = (y0 + y1) // 2
    V.box(dx, dx, ym - 1, ym, g - 5, g - 2, AIR)
    V.put(px + 1, ym + 2, g - 6, GLOW)                                 # porch lamp under the roof


def shed(V, x0, x1, y0, y1, g, wall=WALL_GREY, roof=SHINGLE_GREY, door=(0, 1)):
    V.box(x0, x1, y0, y1, g, g, STONE)
    for z in range(g + 1, 64):
        if V.m[x0, y0, z] == AIR:
            V.box(x0, x1, y0, y1, z, z, STONE)
    V.box(x0, x1, y0, y1, g - 5, g - 1, wall)
    V.box(x0 + 1, x1 - 1, y0 + 1, y1 - 1, g - 5, g - 1, AIR)
    # monopitch roof falling to +y
    n = y1 - y0 + 2
    for j in range(n + 1):
        yy = y0 - 1 + j
        zz = g - 7 + j // 3
        V.box(x0 - 1, x1 + 1, yy, yy, zz, zz, roof)
        if y0 <= yy <= y1:
            V.box(x0, x0, yy, yy, zz + 1, g - 5, wall); V.box(x1, x1, yy, yy, zz + 1, g - 5, wall)
    dx, dy = door
    xm, ym = (x0 + x1) // 2, (y0 + y1) // 2
    if dy:
        yy = y1 if dy > 0 else y0
        V.box(xm, xm + 1, yy, yy, g - 4, g - 1, AIR)
    else:
        xx = x1 if dx > 0 else x0
        V.box(xx, xx, ym, ym + 1, g - 4, g - 1, AIR)
    V.box(x0 + 1, x0 + 2, y0 + 1, y0 + 1, g - 2, g - 1, PLANK)     # crates inside


def windpump(V, x, y, g, h=16):
    """Farm wind pump: 4 legs (5x5) tapering, braced rings, rotor of 8 blades facing south, tail vane."""
    for k in range(h):
        inset = k * 2 // h
        z = g - 1 - k
        for (cx, cy) in ((x + inset, y + inset), (x + 4 - inset, y + inset), (x + inset, y + 4 - inset),
                         (x + 4 - inset, y + 4 - inset)):
            V.put(cx, cy, z, TIMBER)
            V.put(cx, cy, z + 1, TIMBER)
        if k % 5 == 4:
            V.box(x + inset, x + 4 - inset, y + inset, y + inset, z, z, TIMBER)
            V.box(x + inset, x + 4 - inset, y + 4 - inset, y + 4 - inset, z, z, TIMBER)
            V.box(x + inset, x + inset, y + inset, y + 4 - inset, z, z, TIMBER)
            V.box(x + 4 - inset, x + 4 - inset, y + inset, y + 4 - inset, z, z, TIMBER)
    zt = g - h
    V.box(x + 1, x + 3, y + 1, y + 3, zt, zt, PLANK)
    V.box(x + 2, x + 2, y + 2, y + 2, zt - 3, zt - 1, IRON)
    hub = (x + 2, y + 5, zt - 3)
    V.box(x + 2, x + 2, y + 3, y + 5, zt - 3, zt - 3, IRON)
    for i in range(8):
        a = i * math.pi / 4 + 0.2
        V.line4(hub, (hub[0] + math.cos(a) * 5, hub[1], hub[2] + math.sin(a) * 5), PLANK)
    V.box(x + 2, x + 2, y - 4, y + 1, zt - 3, zt - 3, IRON)              # tail boom
    V.box(x + 2, x + 2, y - 6, y - 4, zt - 6, zt - 2, PLANK)              # vane
    V.box(x + 2, x + 2, y + 2, y + 2, zt + 1, g - 1, IRON)                # pump rod
    V.box(x + 1, x + 3, y + 1, y + 3, g - 2, g - 1, STONE)                # well head


def standing_ring(V, cx, cy, r, n, gfun, rng, skip=()):
    for i in range(n):
        a = 2 * math.pi * (i + 0.5) / n
        if any(abs(((a - s + math.pi) % (2 * math.pi)) - math.pi) < 0.25 for s in skip):
            continue
        x = int(round(cx + r * math.cos(a))); y = int(round(cy + r * math.sin(a)))
        h = 3 + (i % 2) * 2
        standing_stone(V, x, y, gfun(x, y), h + 1, 3)
