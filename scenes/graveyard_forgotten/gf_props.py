"""Original prop library for Graveyard of the Forgotten (The Bone Cathedral).

Everything writes material ids into V.m[x, y, z] (z down; the ground's top voxel is z = g, so 'k above ground'
is z = g - k). Props are built face-connected to the ground or to the host they rest on; a cleanup pass in
gf_build removes any tiny orphan the jitter might leave and reports anything larger.
"""
from __future__ import annotations

import math
import zlib

import numpy as np

# ------------------------------------------------------------------ materials
AIR = 0
M = {}
_names = ('ROCK DIRT SOIL MOSS PATH COURT COURT_EDGE GRAVEL MUD POOL REED EARTH_DK '
          'STONE STONE_DK STONE_LT TRACERY ROOF_SLATE RUBBLE TILE_A TILE_B STAIR '
          'BONE BONE_DK SOCKET SKULLROCK '
          'GLASS_P GLASS_R GLASS_G GHOST CANDLE IRON WOOD WOOD_DK DEADWOOD BELL '
          'GRAVE GRAVE_DK CLOTH_TEAM CLOTH_RAG CRACK_GLOW TAG BLOOD').split()
for i, n in enumerate(_names, start=1):
    M[n] = i
globals().update(M)

EMISSIVE = ('GHOST', 'CANDLE', 'CRACK_GLOW', 'GLASS_G')


def rng_for(*key):
    return np.random.default_rng(zlib.crc32(repr(key).encode()))


class Vox:
    def __init__(self):
        self.m = np.zeros((512, 512, 64), np.uint8)

    # --- basic ops (inclusive ranges)
    def box(self, x0, x1, y0, y1, z0, z1, mat, only_air=False):
        x0, x1 = sorted((int(x0), int(x1))); y0, y1 = sorted((int(y0), int(y1))); z0, z1 = sorted((int(z0), int(z1)))
        x0 = max(x0, 0); y0 = max(y0, 0); z0 = max(z0, 0)
        x1 = min(x1, 511); y1 = min(y1, 511); z1 = min(z1, 63)
        if x0 > x1 or y0 > y1 or z0 > z1:
            return
        if only_air:
            sl = self.m[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1]
            sl[sl == 0] = mat
        else:
            self.m[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1] = mat

    def put(self, x, y, z, mat, only_air=False):
        x, y, z = int(x), int(y), int(z)
        if 0 <= x < 512 and 0 <= y < 512 and 0 <= z < 64:
            if not only_air or self.m[x, y, z] == 0:
                self.m[x, y, z] = mat

    def get(self, x, y, z):
        x, y, z = int(x), int(y), int(z)
        if 0 <= x < 512 and 0 <= y < 512 and 0 <= z < 64:
            return int(self.m[x, y, z])
        return 255

    def ground(self, x, y):
        col = self.m[int(x), int(y)]
        nz = np.nonzero(col)[0]
        return int(nz[0]) if len(nz) else 63

    def column_to_ground(self, x, y, z_top, mat):
        x, y = int(x), int(y)
        if not (0 <= x < 512 and 0 <= y < 512):
            return
        z = max(int(z_top), 0)
        while z < 64 and self.m[x, y, z] == AIR:
            self.m[x, y, z] = mat
            z += 1

    def line4(self, p0, p1, mat, only_air=False):
        """Face-connected voxel line from p0 to p1 (x, y, z)."""
        x0, y0, z0 = [int(round(v)) for v in p0]
        x1, y1, z1 = [int(round(v)) for v in p1]
        x, y, z = x0, y0, z0
        n = abs(x1 - x0) + abs(y1 - y0) + abs(z1 - z0)
        pts = [(x, y, z)]
        for i in range(n):
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
            self.put(a, b, c, mat, only_air)
        return pts

    def sweep(self, pts, radii, mat, only_air=False, squash=1.0):
        """Capsule chain through pts [(x, y, z)...] with per-point radius (linearly interpolated).
        Radius >= 0.87 everywhere keeps it face-connected. squash < 1 flattens it vertically."""
        pts = np.asarray(pts, float)
        radii = np.broadcast_to(np.asarray(radii, float), (len(pts),))
        for a, b, ra, rb in zip(pts[:-1], pts[1:], radii[:-1], radii[1:]):
            r = max(ra, rb)
            lo = np.floor(np.minimum(a, b) - r - 1).astype(int)
            hi = np.ceil(np.maximum(a, b) + r + 1).astype(int)
            lo = np.maximum(lo, 0); hi = np.minimum(hi, [511, 511, 63])
            if (lo > hi).any():
                continue
            gx, gy, gz = np.meshgrid(np.arange(lo[0], hi[0] + 1), np.arange(lo[1], hi[1] + 1),
                                     np.arange(lo[2], hi[2] + 1), indexing='ij')
            P = np.stack([gx, gy, gz], -1).astype(float)
            ab = b - a
            L2 = float(ab @ ab) or 1e-9
            t = np.clip(((P - a) @ ab) / L2, 0, 1)
            C = a + t[..., None] * ab
            D = P - C
            D[..., 2] /= squash
            d = np.linalg.norm(D, axis=-1)
            rr = ra + (rb - ra) * t
            sel = d <= rr
            xs, ys, zs = gx[sel], gy[sel], gz[sel]
            if only_air:
                k = self.m[xs, ys, zs] == 0
                xs, ys, zs = xs[k], ys[k], zs[k]
            self.m[xs, ys, zs] = mat

    def ball(self, c, r, mat, only_air=False, squash=1.0):
        self.sweep([c, c], [r, r], mat, only_air, squash)


class Local:
    """Local frame for oriented props: u across, v depth (v < 0 toward the front), k up.
    front = unit vector (fx, fy) the prop faces."""

    def __init__(self, cx, cy, front):
        self.cx, self.cy = int(cx), int(cy)
        self.fx, self.fy = front
        self.rx, self.ry = -self.fy, self.fx

    def xy(self, u, v):
        return (self.cx + u * self.rx - v * self.fx, self.cy + u * self.ry - v * self.fy)

    def put(self, V, u, v, z, mat, only_air=False):
        x, y = self.xy(u, v)
        V.put(x, y, z, mat, only_air)

    def box(self, V, u0, u1, v0, v1, z0, z1, mat, only_air=False):
        xa, ya = self.xy(u0, v0); xb, yb = self.xy(u1, v1)
        V.box(xa, xb, ya, yb, z0, z1, mat, only_air)


DIRS = {'N': (0, -1), 'S': (0, 1), 'W': (-1, 0), 'E': (1, 0)}


# ------------------------------------------------------------------ grave markers

def headstone(V, x, y, g, front, kind, rng, lean=0):
    """A single grave marker on ground top z = g, facing `front`. kinds:
    0 round-top, 1 latin cross, 2 square slab, 3 obelisk, 4 ringed cross, 5 fallen slab, 6 broken stump.
    lean: 0 none, +-1 tilts the top one voxel toward/away from the front (face-connected)."""
    L = Local(x, y, front)
    gm = GRAVE if rng.random() < 0.8 else GRAVE_DK
    # kerbed plot in front of some stones
    if kind in (0, 2, 4) and rng.random() < 0.12:
        for v in range(-6, 0):
            for u in (-1, 1):
                L.put(V, u, v, g - 1, STONE_DK, True)
        for u in (-1, 0, 1):
            L.put(V, u, -6, g - 1, STONE_DK, True)
        for v in range(-5, 0):
            L.put(V, 0, v, g, GRAVEL)
    if kind == 5:                                    # fallen slab lying in front
        L.box(V, -1, 1, -4, -1, g - 1, g - 1, gm, True)
        L.put(V, 0, 0, g - 1, STONE_DK, True)
        return
    if kind == 6:                                    # broken stump with a chipped fragment
        L.box(V, -1, 1, 0, 0, g - 1, g - 1, gm, True)
        L.put(V, -1, 0, g - 2, gm, True)
        L.put(V, 2, -2, g - 1, gm, True)
        return
    rows = {0: ['###', '###', '###', '.#.'],
            1: ['.#.', '.#.', '.#.', '###', '.#.'],
            2: ['###', '###', '###'],
            3: ['##', '##', '#', '#', '#', '#'],
            4: ['.#.', '.#.', '.#.', '#.#', '###', '#.#', '.#.']}[kind]
    if kind == 3:
        L.box(V, 0, 1, 0, 1, g - 2, g - 1, STONE_DK, True)
        for k in range(3, 7):
            sh = 1 if (lean and k >= 5) else 0
            L.put(V, 0, sh * lean, g - k, gm)
            if sh and k == 5:
                L.put(V, 0, 0, g - k, gm)
        return
    w = len(rows[0])
    off = -(w // 2)
    for k, row in enumerate(rows):
        z = g - 1 - k
        sh = lean if (lean and k >= len(rows) // 2 + 1) else 0
        for i, ch in enumerate(row):
            if ch == '#':
                L.put(V, off + i, sh, z, gm)
                if sh and k == len(rows) // 2 + 1:
                    L.put(V, off + i, 0, z, gm)          # overlap row keeps the lean face-connected
    # plinth
    L.box(V, off, off + w - 1, 0, 1, g - 1, g - 1, STONE_DK, True) if kind != 1 else None


def coffin(V, x, y, z, front, mat_lid_open=True):
    """3 x 6 coffin, top at z (1 high), lid slid aside."""
    L = Local(x, y, front)
    L.box(V, -1, 1, -5, 0, z, z, WOOD)
    L.box(V, 0, 0, -4, -1, z, z, WOOD_DK)           # dark interior strip
    L.put(V, 0, -3, z, BONE)                         # remains
    if mat_lid_open:
        L.box(V, 2, 3, -5, -1, z, z, WOOD, True)     # lid lying beside


def open_grave(V, x, y, g, front, rng):
    """Dug grave: 3 x 6 pit two deep with the coffin filling the bottom (standing depth 1), spoil mound."""
    L = Local(x, y, front)
    L.box(V, -1, 1, -6, -1, g, g, AIR)
    L.box(V, -1, 1, -6, -1, g + 1, g + 1, EARTH_DK)
    coffin(V, *L.xy(0, 0), g + 1, front, mat_lid_open=False)
    L.box(V, 0, 0, -6, -2, g + 1, g + 1, WOOD)
    L.put(V, 0, -4, g + 1, BONE)
    # spoil heap (1-2 high) beside
    for v in range(-6, 0):
        L.put(V, 3, v, g - 1, EARTH_DK, True)
        if -5 <= v <= -2:
            L.put(V, 4, v, g - 1, EARTH_DK, True)
            if v in (-4, -3):
                L.put(V, 3, v, g - 2, EARTH_DK, True)
    # shovel stuck in the spoil
    sx, sy = L.xy(3, -3)
    V.put(sx, sy, g - 3, WOOD); V.put(sx, sy, g - 4, WOOD); V.put(sx, sy, g - 5, IRON)
    headstone(V, *L.xy(0, 1), g, front, 0, rng)


# ------------------------------------------------------------------ bones and skulls

def femur(V, x, y, g, along_x, length=5):
    z = g - 1
    for i in range(length):
        if along_x:
            V.put(x + i, y, z, BONE, True)
        else:
            V.put(x, y + i, z, BONE, True)
    for end in (0, length - 1):
        if along_x:
            V.put(x + end, y + 1, z, BONE, True)
        else:
            V.put(x + 1, y + end, z, BONE, True)


def small_skull(V, x, y, g, front):
    """3 x 3 x 3 skull, sockets facing `front`."""
    L = Local(x, y, front)
    L.box(V, -1, 1, -1, 1, g - 3, g - 1, BONE)
    L.put(V, -1, -1, g - 2, SOCKET); L.put(V, 1, -1, g - 2, SOCKET)
    L.put(V, 0, -1, g - 1, BONE_DK)
    V.put(*L.xy(-1, 1), g - 3, BONE_DK); V.put(*L.xy(1, 1), g - 3, BONE_DK)


def bone_pile(V, x, y, g, rng, n=6):
    for i in range(n):
        dx, dy = rng.integers(-4, 5, 2)
        if rng.random() < 0.35:
            small_skull(V, x + dx, y + dy, g if V.ground(x + dx, y + dy) >= g else V.ground(x + dx, y + dy),
                        DIRS['NSEW'[int(rng.integers(4))]])
        else:
            gg = V.ground(x + dx, y + dy)
            femur(V, x + dx, y + dy, gg, bool(rng.integers(2)), int(rng.integers(3, 6)))


def skull_rock(V, cx, cy, g, front, s=1.0):
    """Skull-shaped rock formation: weathered cranium, deep sockets, nasal cavity, broken teeth.
    Base sits 2 below ground so it reads as half-buried."""
    L = Local(cx, cy, front)
    R = 7.5 * s
    # cranium: squashed sphere centred above ground; build in world coords via local mapping
    for u in range(-int(R) - 1, int(R) + 2):
        for v in range(-int(R) - 1, int(R) + 3):
            for k in range(-2, int(2 * R) + 1):
                du, dv, dk = u / R, (v - 1) / (R * 1.1), (k - R * 0.95) / (R * 0.95)
                if du * du + dv * dv + dk * dk <= 1.0:
                    L.put(V, u, v, g - k, SKULLROCK)
    # jaw / cheekbones toward the front, lower
    for u in range(-int(R * 0.7), int(R * 0.7) + 1):
        for v in range(-int(R * 1.15), -int(R * 0.4)):
            for k in range(-1, int(R * 0.55)):
                if (u / (R * 0.72)) ** 2 + ((k - R * 0.2) / (R * 0.5)) ** 2 <= 1.0:
                    L.put(V, u, v, g - k, SKULLROCK)
    # eye sockets: two deep ellipsoids carved into the face
    ez = int(round(R * 1.05))
    for side in (-1, 1):
        ux = int(round(side * R * 0.42))
        for u in range(ux - 3, ux + 4):
            for v in range(-int(R * 1.3), -int(R * 0.35)):
                for k in range(ez - 3, ez + 3):
                    if ((u - ux) / 2.4) ** 2 + ((k - ez) / 2.1) ** 2 <= 1.0:
                        L.put(V, u, v, g - k, AIR)
                        if v == -int(R * 0.35) - 1:
                            L.put(V, u, v, g - k, SOCKET)
    # nasal cavity (inverted heart)
    nz = int(round(R * 0.62))
    for k in range(nz - 2, nz + 1):
        w = 1 if k < nz else 0
        for u in range(-w, w + 1):
            for v in range(-int(R * 1.3), -int(R * 0.6)):
                L.put(V, u, v, g - k, AIR)
    # tooth row: alternate notches along the upper jaw line
    tz = int(round(R * 0.3))
    vfront = None
    for v in range(-int(R * 1.4), 0):
        if V.get(*L.xy(0, v), g - tz) not in (0, 255):
            vfront = v
            break
    if vfront is not None:
        for u in range(-int(R * 0.55), int(R * 0.55) + 1):
            if u % 2 == 0:
                L.put(V, u, vfront, g - tz, AIR)
                L.put(V, u, vfront + 1, g - tz, SOCKET)
            else:
                L.put(V, u, vfront, g - tz, BONE)


# ------------------------------------------------------------------ dead trees

def dead_tree(V, x, y, g, rng, h=16, trunk_r=1.6, twist=1.0):
    """Twisted leafless tree: tapering crooked trunk, flared roots, 3-6 gnarled limbs with face-connected
    twigs. Top of the canopy roughly g - h."""
    ang = rng.random() * 2 * math.pi
    lean = rng.normal(0, 0.12, 2)
    pts = []; rad = []
    n = 6
    px, py = x + 0.5, y + 0.5
    for i in range(n + 1):
        t = i / n
        wob = math.sin(t * 3.1 * twist + ang) * 1.2 * t
        pts.append((px + lean[0] * h * t + wob * math.cos(ang), py + lean[1] * h * t + wob * math.sin(ang),
                    g + 1 - h * 0.78 * t))
        rad.append(trunk_r * (1 - 0.55 * t) + 0.35)
    V.sweep(pts, rad, DEADWOOD)
    # roots
    for k in range(int(rng.integers(3, 6))):
        a = ang + k * 2 * math.pi / 5 + rng.normal(0, 0.3)
        L = trunk_r + 2 + rng.random() * 3
        V.sweep([(px, py, g - 1.5), (px + math.cos(a) * L, py + math.sin(a) * L, g - 0.2)],
                [trunk_r * 0.7 + 0.3, 0.9], DEADWOOD)
    # limbs
    nl = int(rng.integers(3, 7))
    tips = []
    for k in range(nl):
        t0 = 0.45 + 0.5 * k / max(1, nl - 1) + rng.normal(0, 0.04)
        i = min(n - 1, int(t0 * n))
        s = np.array(pts[i]) + (np.array(pts[i + 1]) - np.array(pts[i])) * (t0 * n - i)
        a = ang + k * 2.4 + rng.normal(0, 0.4)
        length = h * (0.32 + 0.25 * rng.random()) * (1.1 - 0.4 * t0)
        up = 0.35 + 0.55 * rng.random()
        seg = [s]
        cur = s.copy()
        for j in range(3):
            a += rng.normal(0, 0.45)
            step = length / 3
            cur = cur + np.array([math.cos(a) * step, math.sin(a) * step, -up * step * (1.1 - 0.3 * j)])
            seg.append(cur.copy())
        V.sweep(seg[:2], [1.0, 0.9], DEADWOOD)                 # thick base of the limb
        V.line4(seg[1], seg[2], DEADWOOD)                        # then thin, face-connected wood
        V.line4(seg[2], seg[3], DEADWOOD)
        tips.append((seg[-1], a))
        # twigs off the limb
        for j in (1, 2, 3):
            if rng.random() < 0.8:
                b = seg[j]
                a2 = a + rng.choice([-1, 1]) * (0.7 + rng.random() * 0.8)
                l2 = 2 + rng.random() * 4
                e = b + np.array([math.cos(a2) * l2, math.sin(a2) * l2, -l2 * (0.4 + rng.random() * 0.6)])
                V.line4(b, e, DEADWOOD)
                if rng.random() < 0.5:
                    a3 = a2 + rng.normal(0, 0.8)
                    e2 = e + np.array([math.cos(a3) * 2, math.sin(a3) * 2, -1 - rng.random() * 2])
                    V.line4(e, e2, DEADWOOD)
    # crown spikes from the trunk top
    top = np.array(pts[-1])
    for k in range(int(rng.integers(2, 4))):
        a = ang + rng.normal(0, 1.5)
        e = top + np.array([math.cos(a) * 3, math.sin(a) * 3, -3 - rng.random() * 4])
        V.line4(top, e, DEADWOOD)
    return tips


def hanging_cage(V, x, y, z_top, length=3):
    """Gibbet cage hung from a branch tip at (x, y, z_top): chain then a 3x3x4 iron cage with a skull."""
    for k in range(1, length + 1):
        V.put(x, y, z_top + k, IRON)
    zt = z_top + length + 1
    for k in range(4):
        z = zt + k
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                edge = abs(dx) == 1 or abs(dy) == 1
                if k in (0, 3) or (edge and (dx + dy) % 2 != 0) or (abs(dx) == 1 and abs(dy) == 1):
                    V.put(x + dx, y + dy, z, IRON)
    V.put(x, y, zt + 2, BONE)


# ------------------------------------------------------------------ structures

def iron_fence(V, pts, g_of, h=3):
    """Iron railing along a polyline: posts every 2 with spear tips, two rails."""
    seen = set()
    for (p, q) in zip(pts[:-1], pts[1:]):
        n = int(max(abs(q[0] - p[0]), abs(q[1] - p[1])))
        for i in range(n + 1):
            x = int(round(p[0] + (q[0] - p[0]) * i / max(n, 1)))
            y = int(round(p[1] + (q[1] - p[1]) * i / max(n, 1)))
            if (x, y) in seen:
                continue
            seen.add((x, y))
            g = g_of(x, y)
            V.put(x, y, g - 1, STONE_DK, True)            # low stone footing everywhere
            if (x + y) % 2 == 0:
                for k in range(2, h + 1):
                    V.put(x, y, g - k, IRON)
                V.put(x, y, g - h - 1, IRON)                # spear tip
            else:
                V.put(x, y, g - 2, IRON)
                V.put(x, y, g - h, IRON)


def stone_wall(V, pts, g_of, rng, h=3, thick=2, gaps=0.08):
    """Crumbling cemetery wall along a polyline with coping and the odd breach."""
    cells = []
    for (p, q) in zip(pts[:-1], pts[1:]):
        n = int(max(abs(q[0] - p[0]), abs(q[1] - p[1])) * 2)
        for i in range(n + 1):
            cells.append((p[0] + (q[0] - p[0]) * i / max(n, 1), p[1] + (q[1] - p[1]) * i / max(n, 1)))
    hh = h
    breach = 0
    done = set()
    for idx, (fx, fy) in enumerate(cells):
        if idx % 6 == 0:
            if breach <= 0 and rng.random() < gaps:
                breach = int(rng.integers(3, 7))
            hh = h if rng.random() > 0.3 else h - 1
        for dx in range(thick):
            for dy in range(thick):
                x, y = int(fx) + dx, int(fy) + dy
                if (x, y) in done:
                    continue
                done.add((x, y))
                g = g_of(x, y)
                top = 1 if breach > 0 else hh
                for k in range(1, top + 1):
                    V.put(x, y, g - k, STONE if k < top else STONE_DK)
        breach -= 0.5


def gate_pillars(V, x, y, g, front, gap, rng, banner=False, skull=True):
    """Two 3x3 stone pillars `gap` apart (across `front`), urn/skull finials, an iron arch, one gate leaf
    swung open, optional team banners."""
    L = Local(x, y, front)
    half = gap // 2 + 2
    for side in (-1, 1):
        u0 = side * half
        L.box(V, u0 - 1, u0 + 1, -1, 1, g - 6, g - 1, STONE)
        L.box(V, u0 - 1, u0 + 1, -1, 1, g - 1, g - 1, STONE_DK)
        L.box(V, u0 - 1, u0 + 1, -1, 1, g - 6, g - 6, STONE_DK)
        if skull:
            small_skull(V, *L.xy(u0, 0), g - 6, front)
        else:
            L.put(V, u0, 0, g - 7, STONE_LT); L.put(V, u0, 0, g - 8, STONE_LT)
        if banner:
            for k in range(2, 6):
                L.put(V, u0, -2, g - k - 1, CLOTH_TEAM)
            L.put(V, u0, -2, g - 2, CLOTH_RAG)
    # iron arch across the top (curved, face-connected)
    prev = None
    for u in range(-half + 2, half - 1):
        t = u / (half - 1)
        k = 7 + int(round(3 * (1 - t * t)))
        p = (*L.xy(u, 0), g - k)
        if prev is not None:
            V.line4(prev, p, IRON)
        prev = p
    L.put(V, -half + 2, 0, g - 7, IRON); L.put(V, half - 2, 0, g - 7, IRON)
    V.line4((*L.xy(-half + 1, 0), g - 7), (*L.xy(-half + 2, 0), g - 7), IRON)
    V.line4((*L.xy(half - 1, 0), g - 7), (*L.xy(half - 2, 0), g - 7), IRON)
    # one leaf swung open against its pillar (outside the passage)
    for v in range(-4, -1):
        for k in range(2, 6):
            if (v + k) % 2 == 0 or k in (2, 5):
                L.put(V, -half + 1, v, g - k, IRON)
    for k in range(2, 6):
        L.put(V, -half + 1, -1, g - k, IRON)


def lantern_post(V, x, y, g, h=5):
    for k in range(1, h + 1):
        V.put(x, y, g - k, IRON)
    V.put(x + 1, y, g - h, IRON)
    V.put(x + 1, y, g - h + 1, GHOST)
    V.put(x + 1, y, g - h + 2, IRON)


def mausoleum(V, cx, cy, g, front, rng, hw=4, hd=6, wall_h=7, spire=True, door=True, cracked=0.06,
              banner=False):
    """Gothic family tomb: plinth, buttressed walls, pointed door with iron grille, ghost lamp inside,
    steep slate gable roof with cracks, corner pinnacles, skull keystone, cross or spirelet on the ridge.
    Footprint (2hw+1) x (2hd+1) centred on (cx, cy)."""
    L = Local(cx, cy, front)
    # plinth (1 wider) and steps at the door
    L.box(V, -hw - 1, hw + 1, -hd - 1, hd + 1, g - 1, g - 1, STONE_DK)
    L.box(V, -2, 2, -hd - 2, -hd - 2, g - 1, g - 1, STONE_DK, True)
    zb = g - 2
    zt = g - 1 - wall_h
    L.box(V, -hw, hw, -hd, hd, zt, zb, STONE)
    # hollow interior 3 high (walkable through the door)
    if door:
        L.box(V, -hw + 1, hw - 1, -hd + 1, hd - 1, g - 4, zb, AIR)
        L.box(V, -1, 1, -hd, -hd, g - 5, zb, AIR)
        L.put(V, 0, -hd, g - 6, AIR)
        L.box(V, -hw + 1, hw - 1, -hd + 1, hd - 1, g - 1, g - 1, TILE_A)
        # sarcophagus and ghost lamp
        L.box(V, -1, 1, hd - 4, hd - 1, g - 2, g - 2, STONE_LT)
        L.put(V, 0, hd - 1, g - 4, GHOST)
        # grille: iron bars across the lower door half
        for k in (2, 3):
            for u in (-1, 1):
                L.put(V, u, -hd, g - k, IRON)
    else:
        L.box(V, -1, 1, -hd, -hd, g - 5, zb, STONE_DK)
    # keystone skull above the door
    L.put(V, 0, -hd - 1, g - 7, BONE); L.put(V, -1, -hd - 1, g - 7, BONE); L.put(V, 1, -hd - 1, g - 7, BONE)
    L.put(V, 0, -hd - 1, g - 8, BONE)
    L.put(V, -1, -hd - 1, g - 7, SOCKET) if wall_h >= 8 else None
    # buttresses on the long sides
    for v in (-hd + 2, 0, hd - 2):
        for side in (-1, 1):
            u = side * (hw + 1)
            L.box(V, u, u, v, v, zt + 2, zb, STONE_DK)
            L.put(V, u, v, zt + 1, STONE_LT)
    # lancet windows (dark recess) on the sides
    for v in (-hd + 3, hd - 3):
        for side in (-1, 1):
            u = side * hw
            L.box(V, u, u, v, v, zt + 2, zt + 4, SOCKET)
    # gable roof: ridge runs along v (front to back)
    for j in range(hw + 2):
        z = zt - j
        uu = hw + 1 - j
        for v in range(-hd - 1, hd + 2):
            for u in (-uu, uu):
                if rng.random() > cracked:
                    L.put(V, u, v, z, ROOF_SLATE)
            if uu > 0:
                L.box(V, -uu + 1, uu - 1, v, v, z, z, STONE, True)     # solid core under the slates
        if uu <= 0:
            break
    # front pediment (stone) and ridge cross / spirelet
    rz = zt - (hw + 1)
    if spire:
        for k in range(1, 6):
            L.put(V, 0, -hd - 1, rz - k, STONE_LT if k < 5 else STONE_DK)
        L.put(V, -1, -hd - 1, rz - 3, STONE_LT); L.put(V, 1, -hd - 1, rz - 3, STONE_LT)
    # corner pinnacles
    for su in (-1, 1):
        for sv in (-1, 1):
            u, v = su * hw, sv * hd
            for k in range(1, 3):
                L.put(V, u, v, zt - k, STONE_DK)
            L.put(V, u, v, zt - 3, STONE_LT)
    if banner:
        for k in range(3, 7):
            L.put(V, -2, -hd - 1, g - k, CLOTH_TEAM); L.put(V, 2, -hd - 1, g - k, CLOTH_TEAM)
    return (rz - 6)


def crypt_entrance(V, cx, cy, g, front, rng, depth=6):
    """Sunken burial chamber: a small roofed porch, 1-voxel stair down `depth`, an 11 x 9 vault below with
    coffin niches, bones and ghost candles. Stairs give the way back up (no traps)."""
    L = Local(cx, cy, front)
    # porch walls + roof (3 wide passage)
    L.box(V, -3, 3, -1, 2, g - 6, g - 1, STONE)
    L.box(V, -1, 1, -1, 2, g - 4, g - 1, AIR)
    L.box(V, -3, 3, -1, 2, g - 6, g - 6, ROOF_SLATE)
    L.box(V, -2, 2, -1, 2, g - 7, g - 7, ROOF_SLATE)
    L.box(V, -1, 1, -1, 2, g - 8, g - 8, STONE_DK)
    L.put(V, 0, -2, g - 6, BONE); L.put(V, 0, -2, g - 5, SOCKET)
    # stair down: v from 0 .. depth-1, step floor z = g + 1 + i
    for i in range(depth):
        v = i
        zf = g + 1 + i
        L.box(V, -1, 1, v, v, zf - 4, zf - 1, AIR)
        L.box(V, -1, 1, v, v, zf, zf, STAIR)
        L.box(V, -2, -2, v, v, zf - 5, zf, STONE_DK)
        L.box(V, 2, 2, v, v, zf - 5, zf, STONE_DK)
        L.box(V, -2, 2, v, v, zf - 5, zf - 5, STONE_DK)     # tunnel ceiling (4 air above each tread)
    zf = g + depth
    # chamber: v depth .. depth+8, u -5..5
    v0 = depth
    L.box(V, -6, 6, v0, v0 + 10, zf - 6, zf + 1, STONE_DK)
    L.box(V, -5, 5, v0, v0 + 9, zf - 4, zf - 1, AIR)
    L.box(V, -5, 5, v0, v0 + 9, zf, zf, TILE_B)
    L.box(V, -4, 4, v0 + 1, v0 + 8, zf - 5, zf - 5, AIR)       # vaulted middle
    # coffin niches along both side walls
    for v in (v0 + 1, v0 + 4, v0 + 7):
        for side in (-1, 1):
            u = side * 5
            L.box(V, u, u, v, v + 1, zf - 2, zf - 1, WOOD)
    small_skull(V, *L.xy(0, v0 + 8), zf, front)
    L.put(V, -3, v0 + 9, zf - 2, CANDLE); L.put(V, 3, v0 + 9, zf - 2, CANDLE)
    L.put(V, -3, v0 + 9, zf - 1, STONE_LT); L.put(V, 3, v0 + 9, zf - 1, STONE_LT)
    L.put(V, 0, v0 + 9, zf - 3, GHOST)
    coffin(V, *L.xy(0, v0 + 6), zf - 1, (front[0], front[1]), True)


def pool(V, cx, cy, rx, ry, g_of, rng):
    """Murky swamp pool: the top voxel is replaced by painted pool surface one below the rim (no AoS water;
    purely visual), muddy rim, sparse reeds and a sunken headstone."""
    for x in range(int(cx - rx - 3), int(cx + rx + 4)):
        for y in range(int(cy - ry - 3), int(cy + ry + 4)):
            d = ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2
            g = g_of(x, y)
            if d <= 1.0:
                V.put(x, y, g, AIR)
                V.put(x, y, g + 1, POOL)
            elif d <= 1.6:
                V.put(x, y, g, MUD)
                if rng.random() < 0.10:
                    for k in range(1, int(rng.integers(2, 4))):
                        V.put(x, y, g - k, REED)


def crack_glow(V, pts, g_of):
    """Ghostly cracks in the ground (top voxel recoloured)."""
    for (p, q) in zip(pts[:-1], pts[1:]):
        n = int(max(abs(q[0] - p[0]), abs(q[1] - p[1]))) + 1
        for i in range(n + 1):
            x = int(round(p[0] + (q[0] - p[0]) * i / n)); y = int(round(p[1] + (q[1] - p[1]) * i / n))
            g = g_of(x, y)
            if V.get(x, y, g) in (SOIL, EARTH_DK, MUD, DIRT):
                V.put(x, y, g, CRACK_GLOW)


def bone_gate(V, x, y, g, gap, rng):
    """The spawn churchyard's front gate: two gothic pylons outside a `gap`-wide opening and a high pointed arch
    of vertebrae (bone) spanning it, skull keystone and a hanging ghost lantern. The arch's underside is >= 11
    above the path, so the front stays open at ground level while the arch breaks sightlines from the platform
    to the back of the spawn square. Front faces +x (west team)."""
    half = gap // 2
    for side in (-1, 1):
        y0 = y + side * (half + 1)
        y1 = y + side * (half + 7)
        ya, yb = sorted((y0, y1))
        V.box(x - 2, x + 3, ya, yb, g - 1, g - 1, STONE_DK)
        V.box(x - 1, x + 2, ya + 1, yb - 1, g - 22, g - 2, STONE)
        V.box(x - 2, x + 3, ya, yb, g - 9, g - 9, STONE_DK)
        V.box(x - 2, x + 3, ya, yb, g - 17, g - 17, STONE_DK)
        V.box(x, x + 1, ya + 2, yb - 2, g - 25, g - 23, STONE_DK)
        V.put(x, (ya + yb) // 2, g - 26, STONE_LT); V.put(x + 1, (ya + yb) // 2, g - 26, STONE_LT)
        for k in range(4, 15):                               # team banners on the courtyard face
            V.put(x + 3, ya + 2, g - k, CLOTH_TEAM); V.put(x + 3, yb - 2, g - k, CLOTH_TEAM)
        V.put(x + 3, ya + 2, g - 3, CLOTH_RAG); V.put(x + 3, yb - 2, g - 3, CLOTH_RAG)
        small_skull(V, x + 4, (ya + yb) // 2, g - 10, (1, 0))
    for yy in range(y - half - 1, y + half + 2):
        t = abs(yy - y) / (half + 1.0)
        ku = 11 + int(round(9 * (1 - t ** 1.35)))           # underside (k above the path)
        mat = BONE if (yy // 3) % 2 == 0 else BONE_DK
        V.box(x - 1, x + 2, yy, yy, g - ku - 5, g - ku, mat)
    small_skull(V, x + 3, y, g - 22, (1, 0))
    small_skull(V, x - 2, y, g - 22, (-1, 0))
    for k in range(20, 15, -1):
        V.put(x, y, g - k, IRON)
    V.put(x, y, g - 15, GHOST)
    V.put(x, y, g - 14, IRON)
