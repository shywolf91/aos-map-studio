"""Materials, voxel canvas and small props for Silverpine Hunt.

Everything writes material ids into V.m[x, y, z] (z down; ground top voxel at z = g, so 'k above ground' is
z = g - k). Props are built face-connected to the ground or to the host they hang from.
"""
from __future__ import annotations

import math

import numpy as np

AIR = 0
M = {}
_names = (
    # terrain
    'SNOW SNOW_TRACK DRYGRASS NEEDLE MOSS EARTH EARTH_DK PATH MUD ROCK ROCK_DK CLIFF ICE ICE_DK ICE_LT ICICLE '
    'GRAVEL CAVE_ROCK CAVE_FLOOR BLOOD_SNOW PAW '
    # wood
    'LOG LOG_DK PLANK PLANK_DK ROOF ROOF_DK BARK BARK_DK SCOTS_BARK DEADWOOD BIRCH CLAW_BARK TIMBER '
    # foliage (8 palettes) + extras
    'FOL0 FOL1 FOL2 FOL3 FOL4 FOL5 FOL6 FOL7 FROST RUST SNOWCAP WOLFSBANE LEAFY CONE '
    # stone, metal
    'STONE STONE_DK MOSS_STONE IRON IRON_DK SILVER ORE RAIL '
    # light
    'GLOW LANTERN EMBER EYE CANDLE MOONGLOW JACK '
    # cloth, hide, bone, flesh
    'PELT PELT_GREY PELT_RED CANVAS CLOTH_TEAM ROPE RAG_RED COAT BONE BONE_DK BLOOD STRAW PUMPKIN '
    # werewolf
    'FUR_DK FUR FUR_LT FUR_TIP CLAW FANG NOSE MAW EAR_IN '
    # sky
    'MOON MOON_DK MOON_RIM BAT BAT_EYE CROW CROW_BEAK').split()
for i, n in enumerate(_names, start=1):
    M[n] = i
globals().update(M)
FOLS = [FOL0, FOL1, FOL2, FOL3, FOL4, FOL5, FOL6, FOL7]
TERRAIN_MATS = {SNOW, SNOW_TRACK, DRYGRASS, NEEDLE, MOSS, EARTH, EARTH_DK, PATH, MUD, ROCK, ROCK_DK, CLIFF, ICE,
                ICE_DK, GRAVEL, CAVE_ROCK, CAVE_FLOOR, BLOOD_SNOW, PAW}


class Vox:
    def __init__(self, H):
        self.m = np.zeros((512, 512, 64), np.uint8)
        self.H = H                                   # terrain top z per column
        self.res = np.zeros((512, 512), bool)       # footprint reservations (no trees / scatter)

    def box(self, x0, x1, y0, y1, z0, z1, mat):
        x0, x1 = sorted((int(x0), int(x1))); y0, y1 = sorted((int(y0), int(y1))); z0, z1 = sorted((int(z0), int(z1)))
        x0 = max(x0, 0); y0 = max(y0, 0); z0 = max(z0, 0)
        x1 = min(x1, 511); y1 = min(y1, 511); z1 = min(z1, 63)
        if x0 > x1 or y0 > y1 or z0 > z1:
            return
        self.m[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1] = mat

    def reserve(self, x0, x1, y0, y1, pad=0):
        self.res[max(0, int(x0) - pad):min(512, int(x1) + pad + 1), max(0, int(y0) - pad):min(512, int(y1) + pad + 1)] = True

    def put(self, x, y, z, mat):
        x, y, z = int(x), int(y), int(z)
        if 0 <= x < 512 and 0 <= y < 512 and 0 <= z < 64:
            self.m[x, y, z] = mat

    def put_air(self, x, y, z, mat):
        x, y, z = int(x), int(y), int(z)
        if 0 <= x < 512 and 0 <= y < 512 and 0 <= z < 64 and self.m[x, y, z] == AIR:
            self.m[x, y, z] = mat

    def get(self, x, y, z):
        x, y, z = int(x), int(y), int(z)
        if 0 <= x < 512 and 0 <= y < 512 and 0 <= z < 64:
            return self.m[x, y, z]
        return 255

    def ground(self, x, y):
        col = self.m[int(x), int(y)]
        nz = np.nonzero(col)[0]
        return int(nz[0]) if len(nz) else 63

    def column_to_ground(self, x, y, z_top, mat):
        x, y = int(x), int(y)
        z = int(z_top)
        while 0 <= z < 64 and self.m[x, y, z] == AIR:
            self.m[x, y, z] = mat
            z += 1

    def line4(self, p0, p1, mat, only_air=False, thick=0):
        """Face-connected voxel line from p0 to p1 (x, y, z). thick=1 adds a plus-shaped cross-section."""
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
        f = self.put_air if only_air else self.put
        for (a, b, c) in pts:
            f(a, b, c, mat)
            if thick:
                for (da, db, dc) in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                    f(a + da, b + db, c + dc, mat)
        return pts

    def capsule(self, p0, p1, r0, r1, mat, only_air=False, squash=(1, 1, 1)):
        """Filled tapered capsule between p0 and p1 (x, y, z). squash scales the radius per axis."""
        p0 = np.array(p0, float); p1 = np.array(p1, float)
        rmax = max(r0, r1) + 1
        lo = np.floor(np.minimum(p0, p1) - rmax * np.array(squash)).astype(int)
        hi = np.ceil(np.maximum(p0, p1) + rmax * np.array(squash)).astype(int)
        lo = np.maximum(lo, 0); hi = np.minimum(hi, [511, 511, 63])
        if (hi < lo).any():
            return
        gx, gy, gz = np.meshgrid(np.arange(lo[0], hi[0] + 1), np.arange(lo[1], hi[1] + 1),
                                 np.arange(lo[2], hi[2] + 1), indexing='ij')
        P = np.stack([gx, gy, gz], -1).astype(float)
        d = p1 - p0
        L2 = max(d @ d, 1e-9)
        t = np.clip(((P - p0) @ d) / L2, 0, 1)
        Q = p0 + t[..., None] * d
        D = (P - Q) / np.array(squash)
        dist = np.sqrt((D ** 2).sum(-1))
        r = r0 + (r1 - r0) * t
        k = dist <= r + 0.15
        xs, ys, zs = gx[k], gy[k], gz[k]
        if only_air:
            a = self.m[xs, ys, zs] == AIR
            xs, ys, zs = xs[a], ys[a], zs[a]
        self.m[xs, ys, zs] = mat

    def ellipsoid(self, c, r, mat, only_air=False, shell=None, noise=None):
        cx, cy, cz = c; rx, ry, rz = r
        x0, x1 = int(math.floor(cx - rx)), int(math.ceil(cx + rx))
        y0, y1 = int(math.floor(cy - ry)), int(math.ceil(cy + ry))
        z0, z1 = int(math.floor(cz - rz)), int(math.ceil(cz + rz))
        x0, y0, z0 = max(x0, 0), max(y0, 0), max(z0, 0)
        x1, y1, z1 = min(x1, 511), min(y1, 511), min(z1, 63)
        if x0 > x1 or y0 > y1 or z0 > z1:
            return
        gx, gy, gz = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1), np.arange(z0, z1 + 1), indexing='ij')
        d = np.sqrt(((gx - cx) / max(rx, 0.5)) ** 2 + ((gy - cy) / max(ry, 0.5)) ** 2 + ((gz - cz) / max(rz, 0.5)) ** 2)
        if noise is not None:
            d = d + noise(gx, gy, gz)
        k = d <= 1.0
        if shell is not None:
            k &= d >= 1.0 - shell
        xs, ys, zs = gx[k], gy[k], gz[k]
        if only_air:
            a = self.m[xs, ys, zs] == AIR
            xs, ys, zs = xs[a], ys[a], zs[a]
        self.m[xs, ys, zs] = mat


def hsh(*a):
    h = 2166136261
    for v in a:
        h = ((h ^ (int(v) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    return h / 4294967296.0


# ================================================================== small props

def lantern_post(V, x, y, g, h=5, arm=(1, 0)):
    V.box(x, x, y, y, g - h, g - 1, TIMBER)
    ax, ay = x + arm[0], y + arm[1]
    V.put(ax, ay, g - h, TIMBER)
    V.put(ax, ay, g - h + 1, IRON)
    V.put(ax, ay, g - h + 2, LANTERN)
    V.put(x, y, g - h - 1, IRON)


def hanging_lantern(V, x, y, z, drop=1):
    for k in range(drop):
        V.put_air(x, y, z + 1 + k, IRON_DK)
    V.put_air(x, y, z + 1 + drop, LANTERN)


def campfire(V, x, y, g, r=3):
    for a in range(16):
        t = a * math.pi / 8
        V.put(int(round(x + r * math.cos(t))), int(round(y + r * math.sin(t))), g - 1, STONE_DK)
    V.box(x - 1, x + 1, y - 1, y + 1, g, g, EMBER)
    V.put(x, y, g - 1, EMBER)
    V.line4((x - 2, y, g - 1), (x + 2, y, g - 1), DEADWOOD, only_air=True)
    V.line4((x, y - 2, g - 1), (x, y + 2, g - 1), DEADWOOD, only_air=True)
    V.put(x, y, g - 2, EMBER)


def boulder(V, x, y, g, r, rng, snow=True, mat=ROCK):
    ph = rng.random(4) * 6.28
    def nz(gx, gy, gz):
        a = np.arctan2(gy - y, gx - x)
        return 0.12 * np.sin(3 * a + ph[0]) + 0.08 * np.sin(5 * a + ph[1]) + 0.06 * np.sin(gz * 0.9 + ph[2])
    rz = r * (0.55 + 0.3 * rng.random())
    V.ellipsoid((x, y, g + 0.5 - rz * 0.6), (r, r * (0.75 + 0.4 * rng.random()), rz), mat, noise=nz)
    if snow:
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                gg = V.ground(x + dx, y + dy)
                if V.get(x + dx, y + dy, gg) == mat and hsh((x + dx) // 2, (y + dy) // 2, 5) < 0.5 and dx * dx + dy * dy < r * r * 0.6:
                    V.put(x + dx, y + dy, gg, SNOW)


def stump(V, x, y, g, rng, axe=False, h=None):
    h = h or int(rng.integers(2, 4))
    V.box(x, x + 1, y, y + 1, g - h, g - 1, BARK)
    V.box(x, x + 1, y, y + 1, g - h, g - h, PLANK)
    for (dx, dy) in ((-1, 0), (2, 1), (0, 2), (1, -1)):
        if rng.random() < 0.7:
            V.put(x + dx, y + dy, g - 1, BARK_DK)
    if axe:
        V.put(x, y, g - h - 1, TIMBER); V.put(x, y, g - h - 2, TIMBER); V.put(x + 1, y, g - h - 2, IRON)


def fallen_log(V, x, y, gfun, length, along_x, rng, girth=2):
    pts = []
    for i in range(length):
        cx, cy = (x + i, y) if along_x else (x, y + i)
        g = gfun(cx, cy)
        for a in range(girth):
            for b in range(girth):
                ox, oy = (cx, cy + a) if along_x else (cx + a, cy)
                V.put(ox, oy, g - 1 - b, BARK if (i + a + b) % 5 else BARK_DK)
        pts.append((cx, cy, g))
    # cut end + snow along the top + moss
    cx, cy, g = pts[0]
    for a in range(girth):
        for b in range(girth):
            V.put(cx + (0 if along_x else a), cy + (a if along_x else 0), g - 1 - b, PLANK)
    for (cx, cy, g) in pts:
        if rng.random() < 0.55:
            V.put_air(cx, cy, g - 1 - girth, SNOWCAP)
        if rng.random() < 0.12:
            V.put(cx, cy, g - 1, MOSS)
    if rng.random() < 0.5:                                  # a broken branch stub
        cx, cy, g = pts[length // 2]
        V.line4((cx, cy, g - girth), (cx + (0 if along_x else -3), cy + (-3 if along_x else 0), g - girth - 2), DEADWOOD)


def firewood(V, x, y, g, length, along_x=True, h=2):
    for i in range(length):
        for k in range(h):
            for d in range(2):
                ox, oy = (x + i, y + d) if along_x else (x + d, y + i)
                V.put(ox, oy, g - 1 - k, LOG if (i + k + d) % 3 else PLANK)
    # snow on top
    for i in range(length):
        if hsh(x, y, i) < 0.6:
            ox, oy = (x + i, y) if along_x else (x, y + i)
            V.put_air(ox, oy, g - 1 - h, SNOWCAP)


def crate(V, x, y, g, s=2):
    V.box(x, x + s - 1, y, y + s - 1, g - s, g - 1, PLANK)
    V.box(x, x + s - 1, y, y, g - s, g - s, PLANK_DK)


def barrel(V, x, y, g):
    V.box(x, x + 1, y, y + 1, g - 3, g - 1, PLANK_DK)
    V.box(x, x + 1, y, y + 1, g - 2, g - 2, IRON_DK)


def bear_trap(V, x, y, g, rng, sprung=False, blood=True, chain_dir=(1, 0)):
    """5x5 iron jaw ring with teeth, chain and stake. 1 voxel high (2 if sprung)."""
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            edge = max(abs(dx), abs(dy)) == 2
            if edge and not (abs(dx) == 2 and abs(dy) == 2):
                V.put(x + dx, y + dy, g - 1, IRON)
    V.put(x, y, g - 1, IRON_DK)                         # pressure plate
    if sprung:
        for dy in range(-1, 2):
            V.put(x, y + dy, g - 2, IRON)
        V.put(x - 1, y, g - 2, IRON); V.put(x + 1, y, g - 2, IRON)
    else:
        for (dx, dy) in ((-1, -2), (1, -2), (-1, 2), (1, 2), (-2, -1), (-2, 1), (2, -1), (2, 1)):
            V.put(x + dx, y + dy, g - 2, IRON_DK)        # teeth
    cx, cy = chain_dir
    n = int(rng.integers(3, 6))
    for k in range(3, 3 + n):
        V.put(x + cx * k, y + cy * k, g - 1, IRON_DK)
    sx, sy = x + cx * (3 + n), y + cy * (3 + n)
    V.box(sx, sx, sy, sy, g - 2, g - 1, TIMBER)
    if blood:
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                if dx * dx + dy * dy <= 8 and rng.random() < 0.5:
                    gg = V.ground(x + dx, y + dy)
                    if V.get(x + dx, y + dy, gg) in TERRAIN_MATS:
                        V.put(x + dx, y + dy, gg, BLOOD_SNOW)


def bones(V, x, y, gfun, rng, n=6, r=4):
    for _ in range(n):
        bx, by = x + int(rng.integers(-r, r + 1)), y + int(rng.integers(-r, r + 1))
        g = gfun(bx, by)
        if rng.random() < 0.5:
            V.put(bx, by, g - 1, BONE); V.put(bx + 1, by, g - 1, BONE)
        else:
            V.put(bx, by, g - 1, BONE); V.put(bx, by + 1, g - 1, BONE_DK)


def animal_skull(V, x, y, g, face=(0, 1), antler=False):
    fx, fy = face
    for k in range(3):
        for s in (-1, 0, 1):
            px, py = (x + s, y + fy * k) if fy else (x + fx * k, y + s)
            V.put(px, py, g - 1, BONE)
            if k < 2:
                V.put(px, py, g - 2, BONE)
    # eye sockets
    if fy:
        V.put(x - 1, y + fy, g - 2, MAW); V.put(x + 1, y + fy, g - 2, MAW)
    else:
        V.put(x + fx, y - 1, g - 2, MAW); V.put(x + fx, y + 1, g - 2, MAW)
    if antler:
        for s in (-1, 1):
            bx, by = (x + s, y) if fy else (x, y + s)
            p = V.line4((bx, by, g - 3), (bx + 2 * s * (1 if fy else 0), by + 2 * s * (0 if fy else 1), g - 6), BONE_DK)
            ex, ey, ez = p[-1]
            V.line4((ex, ey, ez), (ex + (s if fy else 0), ey + (0 if fy else s), ez - 2), BONE_DK)
            mx, my, mz = p[len(p) // 2]
            V.line4((mx, my, mz), (mx - fx, my - fy, mz - 2), BONE_DK)


def antlers(V, x, y, z, along_x=True, size=3):
    """Antler rack mounted on a wall/beam at (x, y, z); spreads along the given axis, rising upward (-z)."""
    for s in (-1, 1):
        ox, oy = (s, 0) if along_x else (0, s)
        p = V.line4((x, y, z), (x + ox * size, y + oy * size, z - size), BONE_DK)
        for i in (len(p) // 3, 2 * len(p) // 3, len(p) - 1):
            ax, ay, az = p[i]
            V.line4((ax, ay, az), (ax + ox, ay + oy, az - 2), BONE_DK)


def elk_carcass(V, x, y, g, rng, along_x=False):
    """Ribcage arches along a spine, skull with antlers, blood pool, fur scraps. Spine runs along y."""
    L = 12
    for i in range(L):
        sx, sy = (x + i, y) if along_x else (x, y + i)
        V.put(sx, sy, g - 1, BONE_DK if i % 2 else BONE)
        if 2 <= i <= 8 and i % 2 == 0:                   # rib arch
            for s in (-1, 1):
                for k, (o, h) in enumerate(((1, 1), (2, 2), (3, 3), (3, 4), (2, 5), (1, 5))):
                    ox, oy = (0, s * o) if along_x else (s * o, 0)
                    if k < 5 or i % 4 == 0:
                        V.put(sx + ox, sy + oy, g - h, BONE)
                for o in range(1, 4):
                    ox, oy = (0, s * o) if along_x else (s * o, 0)
                    V.put(sx + ox, sy + oy, g - 1, BONE_DK) if o == 1 else None
    sx_, sy_ = (x, y - 3) if not along_x else (x - 3, y)
    animal_skull(V, sx_, sy_, V.ground(sx_, sy_), face=(0, -1) if not along_x else (-1, 0), antler=True)
    for dx in range(-6, 7):
        for dy in range(-5, L + 5):
            d = (dx / 6.0) ** 2 + ((dy - L / 2) / (L / 2 + 4)) ** 2
            if d < 1 and rng.random() < 0.75 - 0.6 * d:
                px, py = (x + dy, y + dx) if along_x else (x + dx, y + dy)
                gg = V.ground(px, py)
                if V.get(px, py, gg) in TERRAIN_MATS:
                    V.put(px, py, gg, BLOOD_SNOW)
    for _ in range(5):
        px, py = x + int(rng.integers(-4, 5)), y + int(rng.integers(0, L))
        V.put_air(px, py, V.ground(px, py) - 1, PELT)


def rune_stone(V, x, y, g, h, rng, face=(0, 1), w=2):
    lean = rng.integers(-1, 2)
    for k in range(h):
        ox = int(round(lean * k / max(h, 1)))
        ww = w if k < h - 1 else max(1, w - 1)
        V.box(x + ox, x + ox + ww - 1, y, y + 1, g - 1 - k, g - 1 - k, STONE_DK if k < 2 else STONE)
    # carved silver crescent on the face
    fy = 2 if face[1] > 0 else -1
    zc = g - 1 - h // 2
    for (dx, dz) in ((0, -1), (0, 0), (0, 1)) + (((1, -2), (1, 2)) if w > 1 else ()):
        V.put(x + dx, y + fy if face[1] > 0 else y - 1, zc + dz, SILVER)
    V.put(x, y + (2 if face[1] > 0 else -1), g - 1, CANDLE) if rng.random() < 0.7 else None
    if rng.random() < 0.6:
        V.put_air(x, y, g - 1 - h, SNOWCAP)
    for k in range(min(2, h)):
        if rng.random() < 0.5:
            V.put(x + w - 1, y + 1, g - 1 - k, MOSS_STONE)


def grave_cross(V, x, y, g, rng, face_y=1):
    h = int(rng.integers(4, 6))
    V.box(x, x, y, y, g - h, g - 1, TIMBER)
    V.box(x - 1, x + 1, y, y, g - h + 1, g - h + 1, TIMBER)
    V.box(x - 1, x + 1, y + face_y, y + face_y * 3, g, g, EARTH_DK)   # grave mound paint
    V.put_air(x, y + face_y * 2, g - 1, EARTH_DK)
    if rng.random() < 0.35:
        V.put(x, y + face_y, g - 1, CANDLE)


def headstone(V, x, y, g, rng):
    h = int(rng.integers(3, 5))
    V.box(x - 1, x + 1, y, y, g - h + 1, g - 1, STONE)
    V.put(x, y, g - h, STONE)
    if rng.random() < 0.5:
        V.put(x + 1, y, g - h + 1, AIR) if h > 3 else None
    V.box(x - 1, x + 1, y + 1, y + 3, g, g, EARTH_DK)
    if rng.random() < 0.4:
        V.put_air(x, y - 1, g - 1, CANDLE)
    if rng.random() < 0.5:
        V.put_air(x, y, g - h - (0 if V.get(x, y, g - h) == STONE else -1), SNOWCAP)


def wolfsbane(V, x, y, gfun, rng, r=4, n=14):
    for _ in range(n):
        px, py = x + int(rng.integers(-r, r + 1)), y + int(rng.integers(-r, r + 1))
        g = gfun(px, py)
        if V.get(px, py, g - 1) != AIR:
            continue
        h = int(rng.integers(1, 4))
        V.put(px, py, g - 1, LEAFY)
        for k in range(1, h):
            V.put(px, py, g - 1 - k, WOLFSBANE)


def snare_post(V, x, y, g, rng):
    V.box(x, x, y, y, g - 4, g - 1, TIMBER)
    V.line4((x, y, g - 4), (x + 3, y, g - 2), ROPE, only_air=True)
    V.put_air(x + 3, y, g - 1, ROPE)


def sled(V, x, y, g, along_x=True, load=None, broken=False, low=False):
    L = 7
    for i in range(L):
        for s in (0, 3):
            ox, oy = (x + i, y + s) if along_x else (x + s, y + i)
            V.put(ox, oy, g - 1, IRON_DK if i in (0, L - 1) else TIMBER)
    for i in range(1, L - 1):
        for s in range(4):
            ox, oy = (x + i, y + s) if along_x else (x + s, y + i)
            if not (broken and i > L - 3 and s > 1):
                V.put(ox, oy, g - 2, PLANK)
    ox, oy = (x, y) if along_x else (x, y)
    for s in range(4):                                   # curled front
        px, py = (x, y + s) if along_x else (x + s, y)
        V.put(px, py, g - 2, TIMBER)
        if not low:
            V.put(px, py, g - 3, TIMBER)
    if load and not low:
        for i in range(2, L - 2):
            for s in range(1, 3):
                px, py = (x + i, y + s) if along_x else (x + s, y + i)
                V.put(px, py, g - 3, load)


def snowman_jack(V, x, y, g):
    """Creepy snowman with a jack-o'-lantern head and stick arms."""
    V.ellipsoid((x, y, g - 2), (2.6, 2.6, 2.2), SNOW)
    V.ellipsoid((x, y, g - 5.5), (1.9, 1.9, 1.6), SNOW)
    V.box(x - 1, x + 1, y - 1, y + 1, g - 9, g - 7, PUMPKIN)
    V.put(x, y - 1, g - 10, LEAFY)
    V.put(x - 1, y + 1, g - 8, JACK); V.put(x + 1, y + 1, g - 8, JACK); V.put(x, y + 1, g - 7, JACK)
    V.line4((x - 2, y, g - 6), (x - 4, y, g - 8), DEADWOOD)
    V.line4((x + 2, y, g - 6), (x + 4, y, g - 7), DEADWOOD)
    V.put(x, y + 2, g - 5, STONE_DK); V.put(x, y + 2, g - 3, STONE_DK)
    V.put(x - 1, y + 1, g - 6, RAG_RED); V.put(x, y + 1, g - 6, RAG_RED); V.put(x + 1, y + 1, g - 6, RAG_RED)


def jack_o_lantern(V, x, y, g, face=(0, 1), size=1):
    if size == 1:
        V.box(x - 1, x + 1, y - 1, y + 1, g - 2, g - 1, PUMPKIN)
        V.put(x, y, g - 3, LEAFY)
        fx, fy = face
        V.put(x + fx - (1 if fy else 0), y + fy - (1 if fx else 0), g - 2, JACK)
        V.put(x + fx + (1 if fy else 0), y + fy + (1 if fx else 0), g - 2, JACK)
        V.put(x + fx, y + fy, g - 1, JACK)
    else:
        V.box(x, x + 1, y, y + 1, g - 1, g - 1, PUMPKIN)
        V.put(x, y, g - 2, LEAFY)


def pelt_patch(V, x, y, z, w, h, along_x, mat=PELT):
    for a in range(w):
        for b in range(h):
            V.put(x + (a if along_x else 0), y + (0 if along_x else a), z + b, mat)


def drying_rack(V, x, y, g, along_x, rng):
    L = 8
    for e in (0, L - 1):
        px, py = (x + e, y) if along_x else (x, y + e)
        V.box(px, px, py, py, g - 5, g - 1, TIMBER)
    for i in range(L):
        px, py = (x + i, y) if along_x else (x, y + i)
        V.put(px, py, g - 5, TIMBER)
    i = 1
    while i < L - 2:
        w = int(rng.integers(2, 4))
        mat = [PELT, PELT_GREY, PELT_RED, PELT][int(rng.integers(0, 4))]
        h = int(rng.integers(2, 4))
        for a in range(min(w, L - 1 - i)):
            px, py = (x + i + a, y) if along_x else (x, y + i + a)
            for b in range(h):
                V.put(px, py, g - 4 + b, mat)
        i += w + 1


def cage(V, x, y, g, rng, s=5, h=5):
    for dx in range(s):
        for dy in range(s):
            edge = dx in (0, s - 1) or dy in (0, s - 1)
            if edge and ((dx + dy) % 2 == 0 or (dx in (0, s - 1) and dy in (0, s - 1))):
                V.box(x + dx, x + dx, y + dy, y + dy, g - h, g - 1, IRON_DK)
    V.box(x, x + s - 1, y, y + s - 1, g - h - 1, g - h - 1, IRON_DK)
    V.box(x + 1, x + s - 2, y + 1, y + s - 2, g - h - 1, g - h - 1, AIR)
    for (dx, dy) in ((0, 0), (s - 1, 0), (0, s - 1), (s - 1, s - 1)):
        pass
    V.box(x, x + s - 1, y, y + s - 1, g - h - 1, g - h - 1, IRON_DK)
    V.put(x + s // 2, y + s // 2, g - 1, BONE); V.put(x + s // 2 + 1, y + s // 2, g - 1, BONE_DK)


def wagon_overturned(V, x, y, g, rng, along_x=True):
    L, W = 10, 6
    # bed on its side: a wall of planks 5 high along one long edge, wheels sticking out
    for i in range(L):
        for k in range(W - 1):
            px, py = (x + i, y) if along_x else (x, y + i)
            if not (i in (3, 4) and k == 2):
                V.put(px, py, g - 1 - k, PLANK if (i + k) % 4 else PLANK_DK)
    for i in range(L):                                   # floor boards lying out
        if rng.random() < 0.5:
            px, py = (x + i, y + 1) if along_x else (x + 1, y + i)
            V.put(px, py, g - 1, PLANK_DK)
    for wi in (1, L - 2):                                # wheels (rings) on the up side
        cx, cy = (x + wi, y - 1) if along_x else (x - 1, y + wi)
        for a in range(12):
            t = a * math.pi / 6
            dx, dz = int(round(2 * math.cos(t))), int(round(2 * math.sin(t)))
            px, py = (cx + dx, cy) if along_x else (cx, cy + dx)
            V.put(px, py, g - 3 + dz, TIMBER)
        V.put(cx, cy, g - 3, IRON)
        for z in range(g - 3, g):
            V.put(cx, cy, z, TIMBER)
