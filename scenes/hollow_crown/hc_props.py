"""Materials, voxel canvas and original prop library for The Hollow Crown.

Arrays are m[x, y, z] with z = 0 the sky top and z = 63 the bottom; a ground top at z = g means "k above the
ground" is z = g - k. Every prop is built face-connected to the ground or to the host it rests on; the build
removes any orphan fragments at the end and reports them.
"""
from __future__ import annotations

import math

import numpy as np

AIR = 0
M = {}
_names = '''
ROCK EARTH GRASS MUD DIRT_GREY PATH COBBLE COBBLE_DK FLAG FLAG_DK MOSS_GROUND LEAFLITTER
STONE STONE_DK STONE_TRIM BRICK RUBBLE MARBLE_W MARBLE_B SLATE SLATE_P IRON TIMBER TIMBER_CHAR PLASTER
WINDOW GLOW_AMBER GLOW_GREEN GLOW_CYAN CANDLE CLOTH_TEAM CLOTH_PURPLE CLOTH_BLOOD GOLD GEM_RED GEM_CYAN
OBSIDIAN VELVET GRAVE GRAVE_MOSS BONE BONE_DK COFFIN PLANK AWNING_O AWNING_P TRUNK BRANCH ROOT
PUMPKIN PUMPKIN_DK PUMPKIN_YEL STEM VINE JACK STRAW BOULDER MENHIR SOIL_DARK FURROW EMBER ASH WATER_DK
CRACK ROOF_BEAM HAY BARREL CROWN_DK
'''.split()
for _i, _n in enumerate(_names, start=1):
    M[_n] = _i
globals().update(M)

G0 = 42                       # base ground level of the play area (top voxel z)


class Vox:
    def __init__(self):
        self.m = np.zeros((512, 512, 64), np.uint8)

    def box(self, x0, x1, y0, y1, z0, z1, mat, only_air=False):
        x0, x1 = sorted((int(x0), int(x1))); y0, y1 = sorted((int(y0), int(y1))); z0, z1 = sorted((int(z0), int(z1)))
        x0 = max(x0, 0); y0 = max(y0, 0); z0 = max(z0, 0)
        x1 = min(x1, 511); y1 = min(y1, 511); z1 = min(z1, 63)
        if x0 > x1 or y0 > y1 or z0 > z1:
            return
        if only_air:
            sl = self.m[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1]
            sl[sl == AIR] = mat
        else:
            self.m[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1] = mat

    def clear(self, x0, x1, y0, y1, z0, z1):
        self.box(x0, x1, y0, y1, z0, z1, AIR)

    def put(self, x, y, z, mat, only_air=False):
        x, y, z = int(x), int(y), int(z)
        if 0 <= x < 512 and 0 <= y < 512 and 0 <= z < 64:
            if not only_air or self.m[x, y, z] == AIR:
                self.m[x, y, z] = mat

    def get(self, x, y, z):
        x, y, z = int(x), int(y), int(z)
        if 0 <= x < 512 and 0 <= y < 512 and 0 <= z < 64:
            return self.m[x, y, z]
        return 255

    def ground(self, x, y):
        col = self.m[min(max(int(x), 0), 511), min(max(int(y), 0), 511)]
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

    def touches(self, x, y, z):
        return any(self.get(x + a, y + b, z + c) not in (AIR, 255) for a, b, c in
                   ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)))

    def line4(self, p0, p1, mat, only_air=False, thick=0):
        """Face-connected voxel line from p0 to p1 (x, y, z); thick>0 adds a cross of that radius."""
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
            if thick:
                for d in range(1, thick + 1):
                    for (u, v, w) in ((d, 0, 0), (-d, 0, 0), (0, d, 0), (0, -d, 0), (0, 0, d), (0, 0, -d)):
                        self.put(a + u, b + v, c + w, mat, True)
        return pts

    def disc(self, cx, cy, r, z, mat, ring=None, only_air=False):
        """Filled disc (or annulus with inner radius ring) at height z, centred on (cx, cy) (may be .5)."""
        R = int(math.ceil(r)) + 1
        for dx in range(-R, R + 1):
            for dy in range(-R, R + 1):
                x = int(math.floor(cx)) + dx; y = int(math.floor(cy)) + dy
                d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
                if d <= r and (ring is None or d > ring):
                    self.put(x, y, z, mat, only_air)


# ================================================================== small props

def pumpkin(V, x, y, g, size=1, carved=False, face=(0, 1), mat=None):
    """size 0: 2x2x1, 1: 3x3x2, 2: 5x5x3 ribbed, 3: 7x7x5, 4: 11x11x8 (giant)."""
    base = mat or PUMPKIN
    if size == 0:
        V.box(x, x + 1, y, y + 1, g - 1, g - 1, base)
        V.put(x, y, g - 2, STEM)
        return
    r = {1: 1, 2: 2, 3: 3, 4: 5}[size]
    h = {1: 2, 2: 3, 3: 5, 4: 8}[size]
    for k in range(h):
        z = g - 1 - k
        frac = (k + 0.5) / h
        rr = r + 0.5 - (abs(frac - 0.45) * 1.7) ** 2 * (r + 0.5)
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if dx * dx + dy * dy <= rr * rr + 0.6:
                    a = math.atan2(dy, dx)
                    rib = size >= 2 and (int(math.floor((a / (2 * math.pi)) * (8 if size < 4 else 12) + 0.5)) % 2 == 0)
                    V.put(x + dx, y + dy, z, PUMPKIN_DK if rib else base)
    V.put(x, y, g - 1 - h, STEM)
    if size >= 2:
        V.put(x, y, g - 2 - h, STEM)
    if size >= 3:
        V.put(x + 1, y, g - 2 - h, STEM)
        V.put(x + 1, y, g - 3 - h, STEM)
    if carved and size >= 2:
        fx, fy = face
        if size == 2:
            pts = [(-1, 2), (1, 2), (-1, 1), (0, 1), (1, 1)]
        elif size == 3:
            pts = [(-2, 3), (-1, 3), (1, 3), (2, 3), (-2, 1), (-1, 1), (0, 1), (1, 1), (2, 1), (0, 2)]
        else:
            pts = ([(-3, 5), (-2, 5), (-3, 6), (2, 5), (3, 5), (3, 6), (0, 4)] +
                   [(u, 2) for u in range(-3, 4)] + [(-3, 3), (3, 3), (-1, 1), (1, 1)])
        for (u, v) in pts:
            # carve inward from the face until the shell is passed
            for depth in range(0, r + 1):
                px = x + fx * (r - depth) + (fy != 0) * u
                py = y + fy * (r - depth) + (fx != 0) * u
                if V.get(px, py, g - 1 - v) in (PUMPKIN, PUMPKIN_DK, base):
                    V.put(px, py, g - 1 - v, JACK)
                    break


def gravestone(V, x, y, g, kind, face=(0, 1), lean=0, mat=GRAVE):
    """kinds: 0 round, 1 cross, 2 slab (lying), 3 obelisk, 4 broken stump, 5 tall tablet. face = text side."""
    fx, fy = face
    along_x = fy != 0               # stone plane runs along x when it faces +-y
    def P(u, h, d=0):               # u across, h up, d depth
        if along_x:
            return (x + u, y + d, g - h)
        return (x + d, y + u, g - h)
    if kind == 0:
        for u in (-1, 0, 1):
            for h in (1, 2, 3):
                if not (abs(u) == 1 and h == 3):
                    V.put(*P(u, h), mat)
        V.put(*P(0, 4), mat)
    elif kind == 1:
        for h in (1, 2, 3, 4, 5):
            V.put(*P(0, h), mat)
        V.put(*P(-1, 4), mat); V.put(*P(1, 4), mat)
    elif kind == 2:
        for u in (-1, 0, 1):
            for d in range(0, 4):
                V.put(*P(u, 1, d), mat)
        V.put(*P(0, 2, 0), mat)
    elif kind == 3:
        for h in range(1, 7):
            for u in (0, 1):
                for d in (0, 1):
                    if h < 6 or (u == 0 and d == 0):
                        V.put(*P(u, h, d), mat)
        V.put(*P(0, 7), mat)
    elif kind == 4:
        V.put(*P(0, 1), mat); V.put(*P(1, 1), mat); V.put(*P(0, 2), mat)
    elif kind == 5:
        for u in (-1, 0, 1):
            for h in range(1, 6):
                if not (abs(u) == 1 and h == 5):
                    V.put(*P(u, h), mat)
    if lean and kind in (0, 1, 5):
        # tip the top two voxels one step forward (still face connected through the stone)
        top = {0: 4, 1: 5, 5: 5}[kind]
        for u in (-1, 0, 1):
            src = P(u, top)
            if V.get(*src) == mat:
                V.put(*src, AIR)
                V.put(*P(u, top - 1, lean), mat)      # leaned top rests on the voxel below it


def lantern_post(V, x, y, g, h=5, arm=(1, 0), glow=GLOW_AMBER, post=IRON):
    V.box(x, x, y, y, g - h, g - 1, post)
    ax, ay = arm
    V.put(x + ax, y + ay, g - h, post)
    V.put(x + ax, y + ay, g - h + 1, glow)


def brazier(V, x, y, g, glow=EMBER):
    V.box(x, x, y, y, g - 2, g - 1, IRON)
    V.box(x - 1, x + 1, y - 1, y + 1, g - 3, g - 3, IRON)
    V.put(x, y, g - 4, glow); V.put(x - 1, y, g - 4, glow); V.put(x, y + 1, g - 4, glow)


def banner_pole(V, x, y, g, h, cloth, dirn=(0, 1), length=4, drop=6):
    V.box(x, x, y, y, g - h, g - 1, TIMBER)
    V.put(x, y, g - h - 1, GOLD)
    dx, dy = dirn
    for k in range(1, length + 1):
        for j in range(drop - (k == length) * 2):
            V.put(x + dx * k, y + dy * k, g - h + 1 + j, cloth)


def rubble(V, x, y, g, r, rng, mat=RUBBLE, h=3, mats=None):
    """Mound of fallen blocks; every voxel stacks on something (column fill from the ground)."""
    mats = mats or [mat, STONE, STONE_DK]
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            d = math.hypot(dx, dy) / max(r, 1)
            if d <= 1.0:
                hh = int(round(h * (1 - d * d) + rng.random() * 1.2 - 0.4))
                if hh <= 0:
                    continue
                gx = V.ground(x + dx, y + dy)
                for k in range(hh):
                    V.put(x + dx, y + dy, gx - 1 - k, mats[int(rng.integers(0, len(mats)))])


def boulder(V, x, y, g, r, rng, mat=BOULDER):
    for dx in range(-r - 1, r + 2):
        for dy in range(-r - 1, r + 2):
            for k in range(int(r * 1.4) + 1):
                rr = r * (1 - (k / (r * 1.5 + 0.01)) ** 2)
                if math.hypot(dx * (1 + 0.15 * math.sin(k)), dy) <= rr + 0.3 * rng.random():
                    V.put(x + dx, y + dy, g - k, mat)
    for dx in range(-r - 1, r + 2):
        for dy in range(-r - 1, r + 2):
            if V.get(x + dx, y + dy, g) == mat:
                V.column_to_ground(x + dx, y + dy, g, mat)


def dead_tree(V, x, y, g, h, rng, girth=2, claw=True, face=None):
    """Twisted dead tree: tapering, kinking trunk; 3-6 limbs ending in finger-like forks (face connected);
    exposed root arches at the base; optional carved glowing face on the trunk (face = (dx, dy))."""
    trunk = {}
    cx, cy = x, y
    for k in range(h):
        z = g - 1 - k
        gw = girth if k < h * 0.5 else max(1, girth - 1)
        if k > 2 and k % 4 == 0 and rng.random() < 0.55:
            nx, ny = cx + int(rng.integers(-1, 2)), cy + int(rng.integers(-1, 2))
            V.box(min(cx, nx), max(cx, nx) + gw - 1, min(cy, ny), max(cy, ny) + gw - 1, z, z, TRUNK)
            cx, cy = nx, ny
        V.box(cx, cx + gw - 1, cy, cy + gw - 1, z, z, TRUNK)
        trunk[z] = (cx, cy, gw)
    V.put(cx, cy, g - h, TRUNK)
    trunk[g - h] = (cx, cy, 1)
    # roots: flared foot plus arching roots that dip into the ground
    for (rx, ry) in ((-1, 0), (girth, 0), (0, -1), (0, girth), (-1, girth - 1), (girth, girth - 1)):
        if rng.random() < 0.8:
            V.put(x + rx, y + ry, g - 1, ROOT)
            if rng.random() < 0.5:
                V.put(x + rx, y + ry, g - 2, ROOT)
    nroot = int(rng.integers(2, 5))
    for i in range(nroot):
        a = rng.random() * 2 * math.pi
        L = 3 + int(rng.integers(0, 4))
        px, py = x + girth / 2, y + girth / 2
        prev = (int(px), int(py), g - 2)
        for s in range(1, L + 1):
            qx = int(round(px + math.cos(a) * s)); qy = int(round(py + math.sin(a) * s))
            arch = 1 if 0 < s < L else 0
            zq = V.ground(qx, qy) - 1 - arch
            V.line4(prev, (qx, qy, zq), ROOT, only_air=True)
            prev = (qx, qy, zq)
    nlimb = int(rng.integers(3, 6))
    for i in range(nlimb):
        a = 2 * math.pi * (i + rng.random() * 0.6) / nlimb
        z0 = g - int(h * (0.5 + 0.45 * rng.random()))
        z0 = min(max(z0, g - h), g - 3)
        tx, ty, gw = trunk[z0]
        L = int(h * (0.25 + 0.3 * rng.random()))
        sx = tx + (gw - 1) * (math.cos(a) > 0); sy = ty + (gw - 1) * (math.sin(a) > 0)
        ex, ey = sx + math.cos(a) * L, sy + math.sin(a) * L
        ez = max(z0 - L * (0.4 + 0.5 * rng.random()), 5)
        pts = V.line4((sx, sy, z0), (ex, ey, ez), BRANCH)
        px, py, pz = pts[-1]
        nf = 3 if claw else 2
        for j in range(nf):
            b = a + (j - (nf - 1) / 2) * 0.7 + (rng.random() - 0.5) * 0.3
            fl = 3 + int(rng.integers(0, 2))
            q = V.line4((px, py, pz), (px + math.cos(b) * fl, py + math.sin(b) * fl, pz - 1 - (j % 2)), BRANCH)
            # curled fingertip
            tx2, ty2, tz2 = q[-1]
            V.put(tx2, ty2, tz2 + 1, BRANCH, only_air=True)
    if face is not None:
        fx, fy = face
        zf = g - max(3, int(h * 0.35))
        bx, by, gw = trunk.get(zf, (x, y, girth))
        # pick the trunk surface on the face side
        sx = bx + (gw - 1 if fx > 0 else 0); sy = by + (gw - 1 if fy > 0 else 0)
        V.put(sx + fx, sy + fy, zf, TRUNK); V.put(sx + fx, sy + fy, zf + 1, TRUNK)
        V.put(sx + fx, sy + fy, zf + 2, TRUNK)
        if fx == 0:
            V.box(sx - 1, sx + 1, sy + fy, sy + fy, zf - 1, zf + 3, TRUNK, only_air=True)
            V.put(sx - 1, sy + fy, zf, GLOW_GREEN); V.put(sx + 1, sy + fy, zf, GLOW_GREEN)
            V.put(sx, sy + fy, zf + 2, GLOW_GREEN)
        else:
            V.box(sx + fx, sx + fx, sy - 1, sy + 1, zf - 1, zf + 3, TRUNK, only_air=True)
            V.put(sx + fx, sy - 1, zf, GLOW_GREEN); V.put(sx + fx, sy + 1, zf, GLOW_GREEN)
            V.put(sx + fx, sy, zf + 2, GLOW_GREEN)
    return trunk


def scarecrow(V, x, y, g, rng, face=(1, 0)):
    V.box(x, x, y, y, g - 9, g - 1, TIMBER)
    along_y = face[0] != 0
    for k in range(-3, 4):
        if along_y:
            V.put(x, y + k, g - 7, TIMBER)
        else:
            V.put(x + k, y, g - 7, TIMBER)
    # ragged straw coat on the cross-bar and body
    for k in range(-3, 4):
        for j in range(1, 3 if abs(k) < 3 else 2):
            if along_y:
                V.put(x + face[0], y + k, g - 7 + j, STRAW if (k + j) % 3 else CLOTH_PURPLE)
            else:
                V.put(x + k, y + face[1], g - 7 + j, STRAW if (k + j) % 3 else CLOTH_PURPLE)
    V.box(x + face[0], x + face[0], y + face[1], y + face[1], g - 6, g - 3, CLOTH_PURPLE)
    # pumpkin head
    hx, hy = x, y
    V.box(hx - 1, hx + 1, hy - 1, hy + 1, g - 11, g - 10, PUMPKIN)
    V.put(hx + face[0] * 2, hy + face[1] * 2, g - 11, AIR)
    V.put(hx + face[0], hy + face[1], g - 11, JACK)
    V.put(hx, hy, g - 12, STEM)
    V.box(hx - 2, hx + 2, hy - 2, hy + 2, g - 12, g - 12, STRAW, only_air=True)  # hat brim
    V.box(hx, hx, hy, hy, g - 13, g - 13, STRAW)


def coffin(V, x, y, z, along_x=True, open_=False):
    if along_x:
        V.box(x, x + 4, y, y + 1, z, z, COFFIN)
        if not open_:
            V.box(x, x + 4, y, y + 1, z - 1, z - 1, COFFIN)
        else:
            V.put(x + 1, y, z - 1, COFFIN); V.put(x + 4, y + 1, z - 1, COFFIN)
            V.put(x + 2, y, z, BONE)
    else:
        V.box(x, x + 1, y, y + 4, z, z, COFFIN)
        if not open_:
            V.box(x, x + 1, y, y + 4, z - 1, z - 1, COFFIN)
        else:
            V.put(x, y + 1, z - 1, COFFIN); V.put(x + 1, y + 4, z - 1, COFFIN)
            V.put(x, y + 2, z, BONE)


def barrel(V, x, y, g, h=2):
    V.box(x, x + 1, y, y + 1, g - h, g - 1, BARREL)


def crate(V, x, y, g, s=2):
    V.box(x, x + s - 1, y, y + s - 1, g - s, g - 1, PLANK)


def cart(V, x, y, g, along_x=True, load=None):
    if along_x:
        V.box(x, x + 6, y, y + 3, g - 3, g - 3, PLANK)
        V.box(x, x + 6, y, y, g - 4, g - 4, PLANK); V.box(x, x + 6, y + 3, y + 3, g - 4, g - 4, PLANK)
        for wx in (x + 1, x + 5):
            for wy in (y - 1, y + 4):
                V.box(wx, wx, wy, wy, g - 3, g - 1, TIMBER_CHAR)
                V.put(wx - 1, wy, g - 2, TIMBER_CHAR); V.put(wx + 1, wy, g - 2, TIMBER_CHAR)
        V.line4((x - 1, y + 1, g - 3), (x - 4, y + 1, g - 1), TIMBER)
        V.line4((x - 1, y + 2, g - 3), (x - 4, y + 2, g - 1), TIMBER)
        if load:
            V.box(x + 1, x + 5, y + 1, y + 2, g - 4, g - 4, load)
    else:
        V.box(x, x + 3, y, y + 6, g - 3, g - 3, PLANK)
        V.box(x, x, y, y + 6, g - 4, g - 4, PLANK); V.box(x + 3, x + 3, y, y + 6, g - 4, g - 4, PLANK)
        for wy in (y + 1, y + 5):
            for wx in (x - 1, x + 4):
                V.box(wx, wx, wy, wy, g - 3, g - 1, TIMBER_CHAR)
                V.put(wx, wy - 1, g - 2, TIMBER_CHAR); V.put(wx, wy + 1, g - 2, TIMBER_CHAR)
        V.line4((x + 1, y - 1, g - 3), (x + 1, y - 4, g - 1), TIMBER)
        V.line4((x + 2, y - 1, g - 3), (x + 2, y - 4, g - 1), TIMBER)
        if load:
            V.box(x + 1, x + 2, y + 1, y + 5, g - 4, g - 4, load)


def menhir(V, x, y, g, h, w=2, lean=0, mat=MENHIR):
    for k in range(h):
        ww = w if k < h - 2 else max(1, w - 1)
        sh = lean if k > h * 0.6 else 0
        V.box(x + sh, x + sh + ww - 1, y, y + w - 1, g - 1 - k, g - 1 - k, mat)
    V.box(x - 1, x + w, y - 1, y + w, g, g, MOSS_GROUND)
