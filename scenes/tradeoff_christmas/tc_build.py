"""Tradeoff Christmas: Christmas retheme of aloha.pk's Tradeoff (geometry of the towers is NOT changed).

python tc_build.py SRC.vxl OUTDIR [--seed N]

Pipeline: read original -> recolour (snow floor, candy-striped towers, pine/cream interiors) -> add props on the open
floor (trees, snowmen, gifts, candy-cane lamps, igloos, gingerbread houses, nutcrackers, sleighs, giant tree) ->
roof-edge fairy lights -> floating sky decor -> bake glow -> corner tag -> export vxl + txt + build.json.

Vegetation/decoration placement is non-deterministic by owner rule: an OS seed is drawn per build and saved in
build.json (re-run with --seed to rebuild the identical map). Recolour and one-off positions are fixed.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from aosmap.art import fbm, value_noise                      # noqa: E402
from aosmap.pixelfont import text_mask                       # noqa: E402
from aosmap.vxl import VoxelMap, read_vxl, surface_mask, write_vxl  # noqa: E402

NAME = 'Tradeoff Christmas'
FLOOR = 62            # z of the lowest air voxel above the ground
FOG = (182, 166, 208)
HEAVENS = (34, 36, 96, 255)
GLOW_PAL = [(255, 255, 255), (255, 95, 95), (255, 255, 95), (95, 255, 255), (255, 175, 95), (95, 255, 95)]
SHADE = 0x80


def pk(c):
    r, g, b = (int(max(0, min(255, round(float(v))))) for v in c)
    return (SHADE << 24) | (r << 16) | (g << 8) | b


def lerp(a, b, t):
    a = np.asarray(a, np.float32); b = np.asarray(b, np.float32)
    t = np.asarray(t, np.float32)[..., None] if np.ndim(t) else t
    return a + (b - a) * t


# ===================================================================== canvas
class Cv:
    """Voxel canvas with an expected-floating-free guarantee left to the caller (props must touch something)."""

    def __init__(self, vm):
        self.vm = vm
        self.S, self.C = vm.solid, vm.color
        self.glow = {}            # (x,y,z) -> palette index
        self.log = {}

    def put(self, x, y, z, col, over=True):
        x, y, z = int(x), int(y), int(z)
        if not (0 <= x < 512 and 0 <= y < 512 and 0 <= z <= 62):
            return False
        if self.S[x, y, z] and not over:
            return False
        self.S[x, y, z] = True
        self.C[x, y, z] = pk(col)
        self.vm.colored[x, y, z] = True
        return True

    def lit(self, x, y, z, pal):
        if self.put(x, y, z, GLOW_PAL[pal]):
            self.glow[(int(x), int(y), int(z))] = pal

    def clear(self, x, y, z):
        if 0 <= x < 512 and 0 <= y < 512 and 0 <= z <= 62:
            self.S[x, y, z] = False
            self.vm.colored[x, y, z] = False

    def box(self, x0, x1, y0, y1, z0, z1, col):
        """Inclusive box; z0 is the HIGHER voxel (smaller z)."""
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    self.put(x, y, z, col(x, y, z) if callable(col) else col)

    def ball(self, cx, cy, cz, rx, ry, rz, col, hollow=0.0):
        for x in range(int(cx - rx - 1), int(cx + rx + 2)):
            for y in range(int(cy - ry - 1), int(cy + ry + 2)):
                for z in range(int(cz - rz - 1), int(cz + rz + 2)):
                    d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 + ((z - cz) / rz) ** 2
                    if d <= 1.0 and d >= hollow:
                        self.put(x, y, z, col(x, y, z) if callable(col) else col)


# ===================================================================== palette helpers
SNOW_L, SNOW_D = (200, 207, 214), (148, 166, 200)
WHITE = (206, 210, 214)
TEAM = {1: dict(mid=(68, 104, 224), lite=(112, 150, 240), floor=(70, 104, 214), stone=((104, 136, 204), (170, 196, 234)),
                roof=(150, 178, 218), navy=(44, 60, 108)),
        2: dict(mid=(204, 42, 56), lite=(234, 100, 108), floor=(196, 44, 58), stone=((178, 72, 88), (234, 170, 178)),
                roof=(214, 170, 178), navy=(100, 36, 48))}
PINE = ((28, 84, 60), (50, 128, 84))
CREAM = (214, 204, 182)


# ===================================================================== 1. recolour
def recolour(vm, seed=7):
    S = vm.solid
    C = vm.color
    xs, ys, zs = np.nonzero(S)
    n = len(xs)
    cc = C[xs, ys, zs].astype(np.int64)
    r = ((cc >> 16) & 255).astype(np.int16); g = ((cc >> 8) & 255).astype(np.int16); b = (cc & 255).astype(np.int16)
    lum = 0.3 * r + 0.59 * g + 0.11 * b

    top2d = np.where(S.any(2), S.argmax(2), 64)
    slab = top2d < 60
    lab, _ = ndimage.label(ndimage.binary_dilation(slab, iterations=2))
    blue_lab = lab[256, 185]
    T2 = np.zeros((512, 512), np.int8)
    T2[(lab == blue_lab)] = 1
    T2[(lab != blue_lab) & (lab > 0)] = 2
    tower = T2[xs, ys]
    hue_blue = b > r
    team = np.where(tower > 0, tower, np.where(hue_blue, 1, 2)).astype(np.int8)

    up_open = np.zeros_like(S)
    up_open[:, :, 1:] = ~S[:, :, :-1]
    up_open[:, :, 0] = True
    topf = up_open[xs, ys, zs]
    surf = surface_mask(S)[xs, ys, zs]

    is_floor = (zs == 63) | ((r > 190) & (g > 70) & (g < 170) & (b < 80))
    trim = ~is_floor & (((b > 170) & (r < 110) & (g < 110)) | ((r > 170) & (g < 110) & (b < 110)))
    dark = ~is_floor & ~trim & (lum < 28)
    dteam = ~is_floor & ~trim & ~dark & ((r + g + b) < 330)
    light = ~is_floor & ~trim & ~dark & ~dteam

    nA = value_noise(xs, ys, zs, 2.6, seed)
    nB = value_noise(xs, ys, zs, 9.0, seed + 1)
    nC = value_noise(xs, ys, zs, 1.4, seed + 2)
    out = np.zeros((n, 3), np.float32)

    # --- floor: moonlit snow, capped so it never reads white
    big = fbm(xs, ys, None, 70.0, 3, seed + 3)
    t = np.clip(0.25 + 0.45 * nB + 0.25 * nA + 0.25 * (big - 0.5), 0, 1)
    snow = lerp(SNOW_D, SNOW_L, t)
    snow = np.where((nC > 0.93)[:, None], np.array([212, 216, 214], np.float32), snow)
    # ice patches (flat glassy pads) and cracks
    ice_f = fbm(xs, ys, None, 46.0, 3, seed + 4)
    ice = (ice_f > 0.665) & is_floor
    crack = np.abs(value_noise(xs, ys, None, 7.0, seed + 5) - 0.5) < 0.025
    icol = lerp((132, 184, 222), (170, 212, 236), nA)
    icol = np.where((crack & ice)[:, None], np.array([206, 228, 240], np.float32), icol)
    snow = np.where(ice[:, None], icol, snow)
    out = np.where(is_floor[:, None], snow, out)

    for tm in (1, 2):
        P = TEAM[tm]
        m_t = team == tm
        # outer trim: wide diagonal candy bands + white snow ledges every 8 rows; roof ring = 2-voxel candy stripe
        side_trim = trim & ~topf
        diag = (((xs + ys + zs) // 4) & 1).astype(bool)
        ledge = ((zs % 8) >= 2) & ((zs % 8) <= 4)
        wall = np.where(diag[:, None], np.array(P['mid'], np.float32), np.array(P['lite'], np.float32))
        wall = wall + (nA[:, None] - 0.5) * 14
        wall = np.where(ledge[:, None], lerp(SNOW_D, SNOW_L, 0.35 + 0.5 * nA), wall)
        out = np.where((side_trim & m_t)[:, None], wall, out)
        ring = (((xs + ys) // 2) & 1).astype(bool)
        rc = np.where(ring[:, None], np.array(P['mid'], np.float32), np.array(WHITE, np.float32))
        out = np.where((trim & topf & m_t)[:, None], rc, out)
        # light stone: roofs = snow, interior floors = team/cream checker, walls = ice stone / peppermint
        roof = (light | dteam) & topf & (zs <= 3) & m_t
        roofc = lerp(P['roof'], SNOW_L, 0.05 + 0.45 * nB) * (0.92 + 0.1 * nA)[:, None]
        roofc = np.where((nC > 0.94)[:, None], np.array([214, 218, 218], np.float32), roofc)
        out = np.where(roof[:, None], roofc, out)
        flo = light & topf & (zs > 3) & m_t
        chk = ((((xs // 4) + (ys // 4)) & 1) == 0)
        floc = np.where(chk[:, None], np.array(P['floor'], np.float32), np.array(CREAM, np.float32))
        floc = floc + (nA[:, None] - 0.5) * 16
        out = np.where(flo[:, None], floc, out)
        wl = light & ~topf & m_t
        wlc = lerp(P['stone'][0], P['stone'][1], np.clip(0.2 + 0.6 * nB + 0.3 * nA, 0, 1))
        wlc = wlc + (nC[:, None] - 0.5) * 12
        out = np.where(wl[:, None], wlc, out)
        dt = dteam & ~roof & m_t
        dtc = lerp(PINE[0], PINE[1], np.clip(0.2 + 0.7 * nB, 0, 1)) + (nC[:, None] - 0.5) * 12
        out = np.where(dt[:, None], dtc, out)
        dk = dark & m_t
        out = np.where(dk[:, None], np.array(P['navy'], np.float32) * (0.9 + 0.2 * nA)[:, None], out)
    out = np.where(surf[:, None] | True, out, out)
    vm.color[xs, ys, zs] = ((SHADE << 24) | (np.clip(out[:, 0], 0, 255).astype(np.int64) << 16)
                           | (np.clip(out[:, 1], 0, 255).astype(np.int64) << 8)
                           | np.clip(out[:, 2], 0, 255).astype(np.int64)).astype(np.uint32)
    vm.colored[:] = S
    return T2, slab


# ===================================================================== 2. props
def rgbv(c, j=0.0, rng=None):
    if rng is not None and j:
        c = tuple(v + rng.uniform(-j, j) for v in c)
    return c


BAUBLES = [(214, 40, 52), (236, 196, 70), (72, 112, 232), (196, 206, 220), (206, 84, 196), (240, 130, 50)]
RIBBON = [(214, 40, 52), (236, 196, 70), (60, 160, 90), (240, 240, 240), (72, 112, 232)]
WRAP = [(66, 120, 220), (200, 44, 56), (46, 140, 84), (176, 90, 210), (228, 150, 52), (80, 180, 190), (236, 120, 160)]
TREE_GREENS = [((22, 78, 56), (52, 128, 86)), ((28, 92, 52), (74, 140, 70)), ((20, 70, 74), (54, 124, 112)),
               ((36, 86, 44), (96, 150, 66)), ((26, 74, 84), (60, 120, 130)), ((44, 90, 58), (84, 146, 90))]


def pine(cv, x, y, h, rng, base=FLOOR, details=None, star=True):
    h = int(h)
    Rm = max(3.0, h * 0.33)
    lo, hi = TREE_GREENS[rng.integers(len(TREE_GREENS))]
    trunk_w = 2 if h >= 15 else 1
    for t in range(0, 4):
        for dx in range(trunk_w):
            for dy in range(trunk_w):
                cv.put(x + dx, y + dy, base - t, (104 + rng.integers(-8, 8), 72, 48))
    start = 3
    ntiers = max(2, int(round(h / 5)))
    pts = []
    for t in range(start, h + 1):
        u = (t - start) / max(1, (h - start))
        tier = min(int(u * ntiers), ntiers - 1)
        v = u * ntiers - tier
        r = Rm * (1 - 0.88 * tier / ntiers) * (1 - 0.62 * min(v, 1)) + 0.8
        R = int(np.ceil(r))
        for dx in range(-R, R + 1):
            for dy in range(-R, R + 1):
                d = (dx * dx + dy * dy) ** 0.5
                if d <= r:
                    e = d / max(r, 0.5)
                    col = lerp(lo, hi, np.clip(0.15 + 0.7 * e + rng.uniform(-0.12, 0.12), 0, 1))
                    cv.put(x + dx, y + dy, base - t, col)
                    pts.append((dx, dy, t, e))
    S = {(a, b, c) for a, b, c, _ in pts}
    cx = x + (0.5 if trunk_w == 2 else 0)
    cy = y + (0.5 if trunk_w == 2 else 0)
    pool = ['ornaments', 'snow', 'tinsel', 'lights', 'canes', 'berries']
    if details is None:
        details = list(rng.choice(pool, 3, replace=False))
    rim = [p for p in pts if p[3] > 0.78]
    for dtl in details:
        if dtl == 'snow':
            for dx, dy, t, e in pts:
                if (dx, dy, t + 1) not in S and rng.random() < 0.85 and e > 0.25:
                    cv.put(x + dx, y + dy, base - t, lerp(SNOW_D, SNOW_L, rng.uniform(0.4, 1.0)))
        elif dtl == 'ornaments':
            for dx, dy, t, e in rim:
                if rng.random() < 0.07:
                    cv.put(x + dx, y + dy, base - t, BAUBLES[rng.integers(len(BAUBLES))])
        elif dtl == 'tinsel':
            col = [(236, 198, 84), (200, 208, 220)][rng.integers(2)]
            k = rng.integers(3, 6)
            for dx, dy, t, e in rim:
                ang = np.arctan2(dy, dx) / (2 * np.pi)
                if ((ang * k + t * 0.33) % 1.0) < 0.17:
                    cv.put(x + dx, y + dy, base - t, col)
        elif dtl == 'lights':
            nl = max(5, h // 2)
            for dx, dy, t, e in rim:
                if rng.random() < nl / max(20, len(rim)):
                    cv.lit(x + dx, y + dy, base - t, int(rng.integers(len(GLOW_PAL))) if False else [2, 3, 4, 5][rng.integers(4)])
        elif dtl == 'canes':
            for dx, dy, t, e in rim:
                if rng.random() < 0.025 and (dx, dy, t - 1) in S:
                    cv.put(x + dx, y + dy, base - t, (214, 40, 52)); cv.put(x + dx, y + dy, base - t + 1, (236, 236, 236))
        elif dtl == 'berries':
            for dx, dy, t, e in rim:
                if rng.random() < 0.05:
                    cv.put(x + dx, y + dy, base - t, (196, 30, 44))
                    if rng.random() < 0.5:
                        cv.put(x + dx + 1, y + dy, base - t, (196, 30, 44))
    top = base - h
    if star:
        sc = (240, 206, 90)
        cv.put(int(x), int(y), top - 1, sc)
        cv.lit(int(x), int(y), top - 2, 2) if h >= 11 else cv.put(int(x), int(y), top - 2, sc)
    return h


def gift(cv, x, y, w, d, hh, rng, base=FLOOR):
    wrap = WRAP[rng.integers(len(WRAP))]
    rib = RIBBON[rng.integers(len(RIBBON))]
    if np.allclose(wrap, rib):
        rib = (236, 236, 236)
    for dx in range(w):
        for dy in range(d):
            for t in range(hh):
                c = wrap
                if dx == w // 2 or dy == d // 2:
                    c = rib
                cv.put(x + dx, y + dy, base - t, tuple(v + rng.integers(-5, 6) for v in c))
    cx, cy = x + w // 2, y + d // 2
    cv.put(cx, cy, base - hh, rib)
    cv.put(cx - 1, cy, base - hh, rib); cv.put(cx + 1, cy, base - hh, rib)
    return w, d


def _out(cv, cx, cy, z, fx, fy, start=0.0):
    """First air cell walking from (cx,cy) along (fx,fy) at height z (starts inside the solid)."""
    k = int(start)
    while k < 12 and cv.S[int(cx + fx * k), int(cy + fy * k), z]:
        k += 1
    return int(cx + fx * k), int(cy + fy * k)


def snowman(cv, x, y, rng, scale=1.0, base=FLOOR):
    r1, r2, r3 = 3.2 * scale, 2.4 * scale, 1.8 * scale
    z1, z2, z3 = r1 - 0.6, 2 * r1 + r2 - 1.4, 2 * r1 + 2 * r2 + r3 - 2.2
    sn = lambda x_, y_, z_: lerp(SNOW_D, SNOW_L, 0.5 + 0.5 * rng.random())
    cv.ball(x, y, base - z1, r1, r1, r1 * 0.9, sn)
    cv.ball(x, y, base - z2, r2, r2, r2 * 0.9, sn)
    cv.ball(x, y, base - z3, r3, r3, r3 * 0.9, sn)
    zh, zb = int(round(base - z3)), int(round(base - z2))
    fx, fy = [(0, 1), (0, -1), (1, 0), (-1, 0)][int(rng.integers(4))]
    px, py = -fy, fx
    coal, orange = (30, 32, 38), (240, 130, 40)
    scarf = (206, 40, 52) if rng.random() < .5 else (46, 140, 84)
    for sgn in (-1, 1):                                   # eyes
        ex, ey = _out(cv, x + px * sgn, y + py * sgn, zh - 1, fx, fy, 0)
        cv.put(ex - fx, ey - fy, zh - 1, coal) if False else cv.put(ex, ey, zh - 1, coal)
    nx, ny = _out(cv, x, y, zh, fx, fy, 0)
    cv.put(nx, ny, zh, orange); cv.put(nx + fx, ny + fy, zh, orange)
    for t in (-1, 0, 1):                                  # buttons
        bx, by = _out(cv, x, y, zb + t, fx, fy, 0)
        cv.put(bx, by, zb + t, coal)
    zn = int(round(base - (z3 - r3 * 0.9)))               # scarf: recolour/extend the neck ring
    for a in range(-4, 5):
        for bb in range(-4, 5):
            if cv.S[x + a, y + bb, zn] and 1.2 <= (a * a + bb * bb) ** 0.5 and (a * a + bb * bb) ** 0.5 <= r3 + 0.9:
                cv.put(x + a, y + bb, zn, scarf)
    for sgn in (-1, 1):                                   # stick arms
        ax, ay = _out(cv, x, y, zb - 1, px * sgn, py * sgn, 0)
        for k in range(0, 4):
            cv.put(ax + px * sgn * k, ay + py * sgn * k, zb - 1, (100, 70, 44))
        cv.put(ax + px * sgn * 3, ay + py * sgn * 3, zb - 2, (100, 70, 44))
    ztop = zh
    while cv.S[x, y, ztop - 1]:
        ztop -= 1
    hat = (34, 34, 44)
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            if abs(dx) + abs(dy) <= 3:
                cv.put(x + dx, y + dy, ztop - 1, hat)
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            for t in (2, 3, 4):
                cv.put(x + dx, y + dy, ztop - t, hat if t > 2 else scarf)


def cane_lamp(cv, x, y, rng, hh=10, pal=None, base=FLOOR):
    for t in range(hh):
        cv.put(x, y, base - t, (214, 40, 52) if (t // 2) % 2 == 0 else (232, 232, 232))
    cv.put(x, y, base - hh, (214, 40, 52)); cv.put(x + 1, y, base - hh, (232, 232, 232))
    cv.put(x + 2, y, base - hh, (214, 40, 52)); cv.put(x + 2, y, base - hh + 1, (232, 232, 232))
    cv.lit(x + 2, y, base - hh + 2, pal if pal is not None else [2, 4][rng.integers(2)])


def boulder(cv, x, y, rng, r=3.0, base=FLOOR):
    cv.ball(x, y, base - 0.6, r, r * rng.uniform(.8, 1.1), r * .6,
            lambda a, b, c: lerp(SNOW_D, SNOW_L, np.clip(0.2 + (base - c) / (r * .7) * 0.6 + rng.uniform(-.1, .1), 0, 1)))


def igloo(cv, x, y, R=6, face=0, base=FLOOR):
    fx, fy = [(0, 1), (0, -1), (1, 0), (-1, 0)][face]
    for dx in range(-R - 1, R + 2):
        for dy in range(-R - 1, R + 2):
            for t in range(0, R + 1):
                d2 = dx * dx + dy * dy + t * t
                if (R - 1) ** 2 <= d2 <= R * R + 1:
                    lin = (t % 2 == 0) or ((dx + dy + t) % 3 == 0)
                    cv.put(x + dx, y + dy, base - t, (178, 196, 214) if lin and (t % 2 == 0) else lerp(SNOW_D, SNOW_L, 0.75))
    # door tunnel (3 wide, 3 tall) + porch
    for k in range(R - 3, R + 4):
        for s in (-1, 0, 1):
            for t in range(0, 3):
                px, py = (x + fx * k + (s if fx == 0 else 0), y + fy * k + (s if fy == 0 else 0))
                cv.clear(px, py, base - t)
    for k in range(R - 1, R + 4):                 # arch above tunnel
        for s in (-2, -1, 0, 1, 2):
            px, py = (x + fx * k + (s if fx == 0 else 0), y + fy * k + (s if fy == 0 else 0))
            if abs(s) == 2:
                for t in range(0, 4):
                    cv.put(px, py, base - t, lerp(SNOW_D, SNOW_L, 0.6))
            else:
                cv.put(px, py, base - 3, lerp(SNOW_D, SNOW_L, 0.6))
    cv.lit(x, y, base - 0, 4)                       # warm lamp inside (on the floor)
    cv.put(x + 1, y, base - 0, (150, 100, 60))


def gingerbread(cv, x, y, rng, w=15, d=11, wh=5, face=1, base=FLOOR):
    """Real house: doorway, 2 windows, gable roof, chimney, candy trim. (x,y)=min corner. door on +y side if face==1."""
    brown = lambda a, b, c: lerp((132, 86, 50), (160, 108, 62), rng.random())
    icing = (232, 232, 232)
    cy = y + d / 2.0
    for xx in range(x, x + w):
        for yy in range(y, y + d):
            edge = xx in (x, x + w - 1) or yy in (y, y + d - 1)
            edge2 = xx in (x + 1, x + w - 2) or yy in (y + 1, y + d - 2)
            if edge or edge2:
                for t in range(0, wh):
                    c = icing if (t == wh - 1 or (edge and (xx in (x, x + w - 1)) and (yy in (y, y + d - 1)))) else brown(0, 0, 0)
                    cv.put(xx, yy, base - t, c)
            else:
                cv.put(xx, yy, base - 0, (176, 132, 86)) if False else None
    # door (3 wide x 4 tall) centred on +y wall; windows (2x2) in the x-end walls and back
    dcx = x + w // 2
    for xx in range(dcx - 1, dcx + 2):
        for yy in (y + d - 1, y + d - 2):
            for t in range(0, 4):
                cv.clear(xx, yy, base - t)
    for t in range(0, 5):                           # candy door frame
        cv.put(dcx - 2, y + d - 1, base - t, (214, 40, 52) if t % 2 == 0 else icing)
        cv.put(dcx + 2, y + d - 1, base - t, (214, 40, 52) if t % 2 == 0 else icing)
    for xx in range(dcx - 2, dcx + 3):
        cv.put(xx, y + d - 1, base - 4, (214, 40, 52) if xx % 2 == 0 else icing)
    for (wx, wy) in [(x, y + d // 2 - 1), (x + w - 1, y + d // 2 - 1)]:
        for dy in range(2):
            for t in (1, 2):
                for k in (0, 1) if False else (0,):
                    cv.clear(wx, wy + dy, base - t - 1)
                    cv.clear(wx + (1 if wx == x else -1), wy + dy, base - t - 1)
    for xx in (x + 3, x + w - 5):
        for t in (1, 2):
            for k in (0, 1):
                cv.clear(xx + k, y, base - t - 1); cv.clear(xx + k, y + 1, base - t - 1)
    # gable roof along x: ridge at y centre
    half = d // 2 + 1
    for xx in range(x - 1, x + w + 1):
        for yy in range(y - 1, y + d + 1):
            dy = abs(yy - cy + 0.5)
            hh = wh + int(round(half - dy))
            if dy <= half:
                for t in (hh, hh - 1):
                    pat = ((xx + yy) % 4 < 2)
                    cv.put(xx, yy, base - t, icing if (t == hh and dy < 1.2) else (200, 70, 84) if pat else (60, 150, 98))
    for yy in range(y, y + d):                      # gable fill
        dy = abs(yy - cy + 0.5)
        hh = wh + int(round(half - dy))
        for t in range(wh, hh - 1):
            cv.put(x, yy, base - t, brown(0, 0, 0)); cv.put(x + w - 1, yy, base - t, brown(0, 0, 0))
    # interior: lamp + table
    cv.lit(x + w // 2, y + 3, base - 3, 4)
    cv.put(x + w // 2, y + 3, base - 2, (150, 100, 60)); cv.put(x + w // 2, y + 3, base - 1, (150, 100, 60))
    cv.put(x + w // 2, y + 3, base - 0, (150, 100, 60))
    # chimney + candy posts + gumdrops
    for t in range(wh + half - 1, wh + half + 3):
        for a in range(2):
            for bb in range(2):
                cv.put(x + 3 + a, y + 2 + bb, base - t, (150, 70, 60) if t % 2 else (190, 98, 80))
    for (px, py) in [(x - 1, y - 1), (x + w, y - 1), (x - 1, y + d), (x + w, y + d)]:
        for t in range(0, wh + 2):
            cv.put(px, py, base - t, (214, 40, 52) if (t // 2) % 2 == 0 else (232, 232, 232))
    for k in range(10):
        gx = x + int(rng.integers(0, w)); gy = y + d - 1
        cv.put(gx, gy, base - 0, BAUBLES[k % len(BAUBLES)]) if not cv.S[gx, gy, base - 0] else None


def nutcracker(cv, x, y, rng, base=FLOOR, face=2):
    red, gold, blk, skin, wht = (190, 34, 46), (232, 190, 70), (36, 36, 46), (226, 178, 140), (230, 230, 232)
    cv.box(x, x + 1, y, y + 3, base - 4, base, blk)                 # legs
    cv.box(x + 2, x + 3, y, y + 3, base - 4, base, blk)
    cv.box(x - 1, x + 4, y - 1, y + 4, base - 5, base - 5, gold)   # belt/base
    cv.box(x, x + 3, y, y + 3, base - 10, base - 6, red)
    for t in range(6, 11):
        cv.put(x + 1, y, base - t, gold) if t % 2 else None
    cv.box(x - 1, x - 1, y + 1, y + 2, base - 10, base - 7, red)   # arms
    cv.box(x + 4, x + 4, y + 1, y + 2, base - 10, base - 7, red)
    cv.box(x - 1, x - 1, y + 1, y + 2, base - 6, base - 6, wht)
    cv.box(x + 4, x + 4, y + 1, y + 2, base - 6, base - 6, wht)
    cv.box(x, x + 3, y, y + 3, base - 11, base - 11, gold)           # shoulders
    cv.box(x, x + 3, y, y + 3, base - 14, base - 12, skin)           # head
    cv.box(x, x + 3, y, y, base - 12, base - 12, wht)                # moustache (front -y)
    cv.put(x + 1, y, base - 13, blk); cv.put(x + 2, y, base - 13, blk)
    cv.box(x, x + 3, y, y + 3, base - 21, base - 15, blk)            # tall hat
    cv.box(x, x + 3, y, y + 3, base - 15, base - 15, gold)
    cv.box(x + 1, x + 2, y, y + 3, base - 22, base - 22, red)
    cv.put(x + 1, y + 1, base - 23, (240, 206, 90))
    cv.box(x + 5, x + 5, y + 1, y + 1, base - 14, base - 4, (160, 120, 70))  # staff
    cv.put(x + 5, y + 1, base - 15, gold)


def reindeer(cv, x, y, rng, face=0, base=FLOOR, nose=False, legs=3):
    br = (132, 88, 54)
    dk = (100, 66, 42)
    cv.box(x, x + 5, y, y + 2, base - legs - 2, base - legs, br)      # body
    for lx in (x, x + 5):
        for ly in (y, y + 2):
            cv.box(lx, lx, ly, ly, base - legs + 1, base, dk)
    cv.box(x + 6, x + 6, y + 1, y + 1, base - legs - 3, base - legs - 1, br)  # neck
    cv.box(x + 6, x + 8, y, y + 2, base - legs - 5, base - legs - 4, br)      # head
    cv.put(x + 9, y + 1, base - legs - 4, (214, 40, 52) if nose else dk)
    if nose:
        cv.lit(x + 9, y + 1, base - legs - 4, 1)
    for s in (0, 2):
        for t in range(3):
            cv.put(x + 6, y + s, base - legs - 6 - t, (196, 168, 118))
        sg = -1 if s == 0 else 1
        cv.put(x + 6, y + s + sg, base - legs - 8, (196, 168, 118))
        cv.put(x + 6, y + s + 2 * sg, base - legs - 8, (196, 168, 118))
        cv.put(x + 6, y + s + sg, base - legs - 9, (196, 168, 118))
    cv.put(x - 1, y + 1, base - legs - 2, (240, 240, 240))           # tail


def sleigh(cv, x, y, rng, base=FLOOR, scale=1, flying=False, deer=0):
    red, gold, dk = (190, 34, 46), (232, 190, 70), (110, 24, 34)
    base += 1
    L, W = 14 * scale, 6 * scale
    for t in range(1, 4):                                     # hull
        for dx in range(L):
            for dy in range(W):
                edge = dx in (0, L - 1) or dy in (0, W - 1)
                if edge or t == 1:
                    cv.put(x + dx, y + dy, base - 2 - t, red if t < 3 else dk)
    for dx in range(L - 1):                                   # runners
        for sy in (0, W - 1):
            cv.put(x + dx, y + sy, base - 2, gold); cv.put(x + dx, y + sy, base - 1, gold)
    for dy in range(W):                                       # curl front + back
        cv.put(x + L - 1, y + dy, base - 6, red)
    for sy in (0, W - 1):
        for t in range(2, 6):
            cv.put(x + L, y + sy, base - t, gold) if t < 5 else cv.put(x + L + 1, y + sy, base - 5, gold)
    for dx in range(1, 5):                                    # seat back
        for dy in range(1, W - 1):
            cv.put(x + dx, y + dy, base - 4, (140, 28, 40))
    for k in range(10):                                       # gift sack pile
        gx, gy = x + 6 + int(rng.integers(0, 6)), y + 1 + int(rng.integers(0, W - 3))
        gift(cv, gx, gy, 2, 2, 2, rng, base=base - 4)
    if deer:
        for i in range(deer):
            reindeer(cv, x + L + 6 + i * 11, y + (W // 2) - 1, rng, base=base - 1, nose=(i == deer - 1), legs=3)
        for dx in range(L - 1, L + 6 + deer * 11):
            cv.put(x + dx, y + W // 2, base - 3, gold if dx % 3 else (214, 40, 52))


# ===================================================================== giant tree and sky decor
def giant_tree(cv, x, y, rng, h=40):
    glows = 0
    pine(cv, x, y, h, rng, details=['tinsel', 'ornaments', 'berries'], star=False)
    # wide trunk
    for t in range(0, 8):
        for dx in range(-1, 3):
            for dy in range(-1, 3):
                cv.put(x + dx, y + dy, FLOOR - t, (112 + rng.integers(-8, 8), 78, 50))
    def snap(ang, z, rmax):
        for r_ in np.arange(rmax, 0.4, -0.5):
            px_, py_ = int(round(x + 0.5 + r_ * np.cos(ang))), int(round(y + 0.5 + r_ * np.sin(ang)))
            if cv.S[px_, py_, z]:
                return px_, py_, r_
        return None
    for k in range(80):
        t = 5 + (h - 8) * k / 80.0
        z = int(FLOOR - t)
        hit = snap(k * 0.62, z, 0.33 * h + 2)
        if hit:
            cv.lit(hit[0], hit[1], z, [2, 3, 4, 5][k % 4])
    for k in range(20):
        t = rng.uniform(6, h - 8)
        z = int(FLOOR - t)
        hit = snap(rng.uniform(0, 6.28), z, 0.33 * h + 2)
        if hit:
            cv.ball(hit[0], hit[1], z, 1.5, 1.5, 1.5, BAUBLES[k % len(BAUBLES)])
    top = FLOOR - h
    sc = (244, 208, 96)
    for dz in range(-4, 1):
        for dx in range(-2, 3):
            for dy in (0,):
                if abs(dx) + abs(dz) * 0.7 <= 2.6:
                    cv.put(x + dx, y, top + dz - 2, sc); cv.put(x, y + dx, top + dz - 2, sc)
    cv.lit(x, y, top - 3, 2)
    for dx in (-1, 1):
        cv.lit(x + dx, y, top - 3, 2); cv.lit(x, y + dx, top - 3, 2)


def cloud(cv, cx, cy, cz, R, rng, deck_trees=3, baubles=2):
    """Floating snow-cloud island: puffy underside with icicles, trees + gifts on top, hanging baubles."""
    bumps = [(rng.uniform(-R * .6, R * .6), rng.uniform(-R * .6, R * .6), rng.uniform(R * .35, R * .6)) for _ in range(5)]
    cv.ball(cx, cy, cz, R, R * 0.9, R * 0.32, lambda a, b, c: lerp((176, 192, 214), SNOW_L, np.clip(0.5 + (cz - c) / (R * .5) * .5 + rng.uniform(-.08, .08), 0, 1)))
    for bx, by, br in bumps:
        cv.ball(cx + bx, cy + by, cz + 1, br, br, br * 0.4, lambda a, b, c: lerp((186, 200, 220), SNOW_L, rng.uniform(.4, 1)))
    for _ in range(int(R * 1.2)):                                  # icicles
        a = rng.uniform(0, 6.28); r = rng.uniform(.3, .85) * R
        ix, iy = int(cx + r * np.cos(a)), int(cy + r * np.sin(a))
        for t in range(int(rng.integers(2, 6))):
            cv.put(ix, iy, int(cz + R * .1 + t), (170, 208, 232))
    deck = int(cz - R * 0.3)
    for k in range(deck_trees):
        a = 6.28 * k / max(1, deck_trees) + rng.uniform(-.4, .4); r = R * rng.uniform(.25, .55)
        pine(cv, int(cx + r * np.cos(a)), int(cy + r * np.sin(a)), int(rng.integers(7, 12)), rng, base=deck + 3)
    for k in range(2):
        gift(cv, int(cx + rng.uniform(-R * .5, R * .5)), int(cy + rng.uniform(-R * .5, R * .5)), 3, 3, 3, rng, base=deck + 2)
    for k in range(baubles):
        a = rng.uniform(0, 6.28); r = R * rng.uniform(.2, .55)
        bx, by = int(cx + r * np.cos(a)), int(cy + r * np.sin(a))
        s0 = int(cz)
        L = int(rng.integers(5, 9))
        for t in range(L):
            cv.put(bx, by, s0 + t, (232, 196, 84))
        cv.ball(bx, by, s0 + L + 2.5, 2.7, 2.7, 2.7, BAUBLES[(k + int(R)) % len(BAUBLES)])
        cv.lit(bx, by, s0 + L + 5, 2)


def snowflake(cv, cx, cy, cz, R, axis, col):
    """Vertical snowflake plate (thickness 2) in the x-z (axis 0) or y-z (axis 1) plane. Face-connected."""
    def pt(u, v, off):
        px, py = (cx + u, cy + off) if axis == 0 else (cx + off, cy + u)
        cv.put(px, py, cz + v, col)
    cells = set()
    for k in range(6):
        a = k * np.pi / 3 + np.pi / 6
        pu, pv = 0, 0
        for sv in np.arange(0, R + 0.01, 0.5):
            u, v = int(round(sv * np.cos(a))), int(round(sv * np.sin(a)))
            if (u, v) == (pu, pv):
                continue
            if u != pu and v != pv:
                cells.add((u, pv))
            cells.add((u, v))
            pu, pv = u, v
            if abs(sv - R // 2) < 0.26 or abs(sv - R * 3 // 4) < 0.26:
                for q in (1, 2):
                    for dq in ((q, 0), (-q, 0), (0, q), (0, -q)):
                        cells.add((u + dq[0], v + dq[1]))
    for dx in range(-1, 2):
        for dz in range(-1, 2):
            cells.add((dx, dz))
    for (u, v) in cells:
        for off in range(2):
            pt(u, v, off)


# ===================================================================== glow bake
def bake_glow(vm, glow):
    S = vm.solid
    surf = surface_mask(S)
    src = np.array(list(glow.keys()), np.int32)
    spal = np.array([glow[tuple(k)] for k in src], np.int32)
    srcset = {tuple(k) for k in src}
    acc = {}
    R = 6
    for (sx, sy, sz), pi in zip(src, spal):
        sc = np.array(GLOW_PAL[pi], np.float32)
        x0, x1 = max(0, sx - R), min(512, sx + R + 1)
        y0, y1 = max(0, sy - R), min(512, sy + R + 1)
        z0, z1 = max(0, sz - R), min(64, sz + R + 1)
        sub = surf[x0:x1, y0:y1, z0:z1]
        ix, iy, iz = np.nonzero(sub)
        if len(ix) == 0:
            continue
        gx, gy, gz = ix + x0, iy + y0, iz + z0
        d = np.sqrt((gx - sx) ** 2 + (gy - sy) ** 2 + (gz - sz) ** 2)
        ok = (d < 6.5) & (d > 0)
        w = 0.32 * (1 - d[ok] / 6.5)
        for a, b, c, ww in zip(gx[ok], gy[ok], gz[ok], w):
            if (a, b, c) in srcset:
                continue
            k = (int(a), int(b), int(c))
            acc[k] = acc.get(k, 0) + sc * ww
    stored = {k: tuple(int(v) for v in unpack(vm.color[k])) for k in acc}
    for k, add in acc.items():
        r, g, b = unpack(vm.color[k])
        new = np.clip(np.array([r, g, b], np.float32) + add, 0, 255).round().astype(int)
        if tuple(new) in [tuple(p) for p in GLOW_PAL]:
            new = np.maximum(new - 1, 0) if tuple(new) != (255, 255, 255) else np.array([254, 254, 254])
        vm.color[k] = pk(new)
    for k, pi in glow.items():
        stored[k] = GLOW_PAL[pi]
    return stored, len(acc)


def unpack(c):
    c = int(c)
    return (c >> 16) & 255, (c >> 8) & 255, c & 255


# ===================================================================== build
def build(src, seed):
    t0 = time.time()
    vm, rep = read_vxl(open(src, 'rb').read())
    assert rep.ok if hasattr(rep, 'ok') else True
    T2, slab = recolour(vm)
    cv = Cv(vm)
    rng = np.random.default_rng(seed)
    log = {}

    # ---- fixed layout masks
    near = ndimage.binary_dilation(slab, iterations=9)
    yy, xx = np.meshgrid(np.arange(512), np.arange(512))
    near |= (xx < 8) | (xx > 503) | (yy < 8) | (yy > 503)
    tag_rect = (438, 476, 502, 505)
    near[tag_rect[0] - 6:tag_rect[2] + 6, tag_rect[1] - 4:tag_rect[3] + 2] = True
    placed = []          # (x, y, r)

    def free(x, y, r):
        x0, x1, y0, y1 = max(0, x - r), min(512, x + r + 1), max(0, y - r), min(512, y + r + 1)
        if near[x0:x1, y0:y1].any():
            return False
        for (px, py, pr) in placed:
            if (px - x) ** 2 + (py - y) ** 2 < (pr + r) ** 2:
                return False
        return True

    def claim(x, y, r):
        placed.append((x, y, r))

    # ---- unique one-offs (fixed positions) -----------------------------------------------------------
    one = {}
    gx, gy = 256, 256
    assert not near[gx - 20:gx + 21, gy - 20:gy + 21].any(), 'giant tree spot not free'
    giant_tree(cv, gx, gy, rng, h=40); claim(gx, gy, 14); one['giant_tree'] = (gx, gy)
    near5 = ndimage.binary_dilation(slab, iterations=5)
    near5[:8] = True; near5[-8:] = True; near5[:, :8] = True; near5[:, -8:] = True

    def find_spot(tx, ty, w, d, pad=2):
        for rad in range(0, 90, 3):
            for ang in np.linspace(0, 6.283, max(1, rad // 2), endpoint=False) if rad else [0]:
                x, y = int(tx + rad * np.cos(ang)), int(ty + rad * np.sin(ang))
                if x < 10 or y < 10 or x + w > 500 or y + d > 500:
                    continue
                if near5[x - pad:x + w + pad, y - pad:y + d + pad].any():
                    continue
                cxm, cym, rr = x + w / 2, y + d / 2, max(w, d) / 2 + 3
                if any((px - cxm) ** 2 + (py - cym) ** 2 < (pr + rr) ** 2 for px, py, pr in placed):
                    continue
                return x, y
        return None

    one_off = [('gingerbread', 190, 232, dict(w=15, d=11), (15, 11)), ('gingerbread', 322, 280, dict(w=15, d=11), (15, 11)),
               ('sleigh', 270, 300, dict(deer=2), (46, 8)), ('nutcracker', 214, 262, {}, (6, 6)),
               ('nutcracker', 300, 250, {}, (6, 6)), ('igloo', 150, 236, dict(face=0), (14, 14)),
               ('igloo', 360, 270, dict(face=1), (14, 14)), ('nutcracker', 40, 256, {}, (6, 6))]
    for kind, tx, ty, kw, (fw, fd) in one_off:
        spot = find_spot(tx - (7 if kind == 'igloo' else 0), ty - (7 if kind == 'igloo' else 0), fw, fd)
        if spot is None:
            log.setdefault('skipped_oneoffs', []).append((kind, tx, ty)); continue
        x, y = spot
        if kind == 'gingerbread':
            gingerbread(cv, x, y, rng, **kw); claim(x + 7, y + 5, 10)
        elif kind == 'sleigh':
            sleigh(cv, x, y, rng, **kw); claim(x + 20, y + 3, 26)
        elif kind == 'nutcracker':
            nutcracker(cv, x, y, rng); claim(x + 2, y + 2, 6)
        elif kind == 'igloo':
            igloo(cv, x + 7, y + 7, 6, **kw); claim(x + 7, y + 7, 11)
        one.setdefault(kind, []).append((int(x), int(y)))
    # ---- grove field -----------------------------------------------------------------------------------
    G = fbm(xx, yy, None, 80.0, 3, int(seed % 9973) + 17)
    cnt = dict(tree=0, snowman=0, gift=0, lamp=0, boulder=0)
    tries = 0
    while cnt['tree'] < 210 and tries < 20000:
        tries += 1
        x, y = int(rng.integers(10, 502)), int(rng.integers(10, 502))
        g = G[x, y]
        if g < 0.50 and rng.random() > 0.12:
            continue
        h = int(rng.choice([8, 9, 10, 11, 12, 14, 16, 18, 21, 24], p=[.1, .1, .12, .13, .12, .13, .1, .08, .07, .05]))
        r = int(h * 0.32) + 5
        if not free(x, y, r):
            continue
        pine(cv, x, y, h, rng); claim(x, y, r); cnt['tree'] += 1
        if rng.random() < 0.35:
            for _ in range(int(rng.integers(1, 4))):
                gx_, gy_ = x + int(rng.integers(-r, r)), y + int(rng.integers(-r, r))
                if not near[gx_ - 2:gx_ + 6, gy_ - 2:gy_ + 6].any() and not cv.S[gx_:gx_ + 4, gy_:gy_ + 4, FLOOR].any():
                    gift(cv, gx_, gy_, int(rng.integers(3, 6)), int(rng.integers(3, 6)), int(rng.integers(2, 5)), rng); cnt['gift'] += 1
    tries = 0
    plan = [('snowman', 26, 7), ('gift', 22, 6), ('lamp', 40, 5), ('boulder', 28, 5)]
    for kind, want, r in plan:
        tries = 0
        while cnt[kind] < want + (cnt['gift'] if kind == 'gift' and False else 0) and tries < 8000:
            tries += 1
            x, y = int(rng.integers(10, 502)), int(rng.integers(10, 502))
            rr = r if kind != 'snowman' else 6
            if not free(x, y, rr):
                continue
            if kind == 'snowman':
                snowman(cv, x, y, rng, scale=float(rng.uniform(.9, 1.35)))
            elif kind == 'gift':
                for _ in range(int(rng.integers(2, 5))):
                    gift(cv, x + int(rng.integers(-3, 4)), y + int(rng.integers(-3, 4)), int(rng.integers(3, 6)), int(rng.integers(3, 6)), int(rng.integers(2, 5)), rng)
            elif kind == 'lamp':
                cane_lamp(cv, x, y, rng, hh=int(rng.integers(9, 13)))
            elif kind == 'boulder':
                boulder(cv, x, y, rng, r=float(rng.uniform(2.4, 4.2)))
            claim(x, y, rr); cnt[kind] += 1
    log['counts'] = cnt
    log['oneoffs'] = one

    # ---- roof-edge fairy lights on top of the candy ring (z=2 ring -> bulbs at z=1) ----------------------
    ring_top = np.zeros_like(S_ := vm.solid)
    sf = surface_mask(vm.solid)
    cand = np.argwhere(sf[:, :, 2] & slab[:, :])
    nb = 0
    pal = [2, 3, 4, 5, 3]
    edge = ndimage.binary_erosion(slab, iterations=1)
    for x, y in cand:
        if slab[x, y] and not edge[x, y] and (x * 7 + y * 3) % 6 == 0 and not vm.solid[x, y, 1]:
            cv.lit(x, y, 1, pal[(x // 6 + y // 6) % 5]); nb += 1
    log['roof_bulbs'] = nb

    # ---- floating sky decor (opt-in; list as expected floating) -----------------------------------------
    floaters = []

    def mark(name, bbox):
        floaters.append({'name': name, 'bbox': [int(v) for v in bbox]})

    sleigh_x, sleigh_y, sleigh_z = 120, 62, 24
    sleigh(cv, sleigh_x, sleigh_y, rng, base=sleigh_z, scale=1, deer=4, flying=True)
    mark('flying sleigh + 4 reindeer', (sleigh_x - 2, sleigh_y - 12, 8, sleigh_x + 70, sleigh_y + 14, sleigh_z + 2))
    clouds = [(400, 70, 26, 13), (60, 120, 30, 11), (84, 430, 28, 14), (430, 400, 24, 12), (250, 450, 32, 12), (270, 50, 34, 10)]
    for (cx, cy, cz, R) in clouds:
        cloud(cv, cx, cy, cz, R, rng, deck_trees=3 if R > 10 else 2, baubles=2)
        mark('snow-cloud island', (cx - R, cy - R, cz - R, cx + R, cy + R, cz + R))
    flakes = [(30, 60, 20, 8, 1), (470, 150, 22, 9, 1), (30, 330, 24, 8, 1), (480, 300, 18, 8, 1),
              (160, 470, 22, 9, 0), (360, 40, 14, 8, 0), (140, 28, 14, 7, 0), (390, 475, 20, 8, 0)]
    for (cx, cy, cz, R, ax) in flakes:
        snowflake(cv, cx, cy, cz, R, ax, (208, 224, 240))
        mark('snowflake', (cx - R - 2, cy - R - 2, cz - R, cx + R + 2, cy + R + 2, cz + R))
    log['floaters'] = floaters

    # ---- remove tiny accidental floating bits left by decoration (not the listed sky pieces) --------------
    from aosmap.validate import floating_components
    removed = 0
    for c in floating_components(vm.solid):
        (x0, x1), (y0, y1), (z0, z1) = c['bbox']
        in_sky = any(f['bbox'][0] - 6 <= x0 and x1 <= f['bbox'][3] + 6 and f['bbox'][1] - 6 <= y0 and y1 <= f['bbox'][4] + 6
                     and f['bbox'][2] - 16 <= z0 and z1 <= f['bbox'][5] + 16 for f in floaters)
        if not in_sky and c['voxels'] <= 40:
            lab_sub = None
            vm.solid[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1] &= ~ndimage.label(vm.solid[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1])[0].astype(bool) | True if False else vm.solid[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1]
            sub = vm.solid[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1]
            lbl, nl = ndimage.label(sub, structure=ndimage.generate_binary_structure(3, 1))
            # drop only voxels of this floating component (component has no ground contact)
            for i in range(1, nl + 1):
                m_ = lbl == i
                if m_.sum() == c['voxels']:
                    sub[m_] = False; vm.colored[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1][m_] = False
                    removed += c['voxels']; break
    cv.glow = {k: v for k, v in cv.glow.items() if vm.solid[k]}
    log['removed_floating_voxels'] = removed

    # ---- corner tag (map name only), painted on the ground ----------------------------------------------
    lines = ['Tradeoff', 'Christmas']
    tm = text_mask(lines, spacing=1, line_gap=3)
    ox, oy = tag_rect[0], tag_rect[1]
    for i in range(tm.shape[0]):
        for j in range(tm.shape[1]):
            if tm[i, j] and ox + i < 512 and oy + j < 512:
                vm.color[ox + i, oy + j, 63] = pk((176, 30, 46))
    hal = ndimage.binary_dilation(tm, iterations=1) & ~tm
    for i, j in np.argwhere(hal):
        if ox + i < 512 and oy + j < 512:
            vm.color[ox + i, oy + j, 63] = pk((236, 236, 236))
    log['tag'] = dict(x=ox, y=oy, w=int(tm.shape[0]), h=int(tm.shape[1]))

    vm.colored[:] = vm.solid
    stored, nlit = bake_glow(vm, cv.glow)
    log['glow_sources'] = len(cv.glow)
    log['glow_lit_voxels'] = nlit
    log['build_s'] = round(time.time() - t0, 1)
    return vm, stored, log, slab


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('out'); ap.add_argument('--seed', type=int, default=None)
    a = ap.parse_args()
    seed = a.seed if a.seed is not None else int.from_bytes(os.urandom(4), 'little')
    os.makedirs(a.out, exist_ok=True)
    vm, stored, log, slab = build(a.src, seed)
    data = write_vxl(vm)
    with open(os.path.join(a.out, 'tradeoff_christmas.vxl'), 'wb') as f:
        f.write(data)
    txt = ["# Generated by scenes/tradeoff_christmas/tc_build.py", "",
           f"name = {NAME!r}", "version = '1.0'", "author = 'shywolf91 + AI'",
           "description = ('Christmas retheme of Tradeoff by aloha.pk (tower geometry unchanged): candy-striped towers, "
           "snowy field, pine groves, gingerbread houses, igloos, giant tree and a floating sky layer with fairy lights.')",
           f"fog = {FOG!r}", "", "extensions = {", f"    'heavens_color': {HEAVENS!r},", "    'glow_enabled': True,",
           "    'glow_stored_colors': {"]
    for k in sorted(stored):
        txt.append(f"        {k!r}: {tuple(int(v) for v in stored[k])!r},")
    txt += ["    },", "}", ""]
    open(os.path.join(a.out, 'tradeoff_christmas.txt'), 'w', newline='\n').write('\n'.join(txt))
    info = dict(seed=seed, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), **log)
    json.dump(info, open(os.path.join(a.out, 'build.json'), 'w'), indent=1, default=int)
    print(json.dumps({k: v for k, v in info.items() if k not in ('floaters',)}, indent=1, default=int))


if __name__ == '__main__':
    main()
