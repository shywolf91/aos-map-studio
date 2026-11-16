"""v2.2 centre dressing: fills the top-ground centre (den floor, crag flanks, skull flanks) with themed set pieces.

Rules kept: tower corridor (x 138-212 / 300-374, y 234-278) and the anchors stay open; everything within 24 of the
platform is <= 6 high; gaps between pieces are >= 7; every piece is face-connected to the ground.
West half + axis are authored; the build mirrors x' = 512 - x afterwards.
"""
from __future__ import annotations

import math

import numpy as np

from sph_props import *            # noqa: F401,F403
from sph_props import AIR, hsh
import sph_structs as S
from sph_terrain import PZ


def _tz(V):
    return lambda a, b: int(V.H[int(a), int(b)])


# ------------------------------------------------------------------ pieces

def palisade(V, pts, rng, h=4):
    """Sharpened log stakes standing shoulder to shoulder (a wall, not a pillar field), lashed with rope."""
    cells = []
    for (xa, ya), (xb, yb) in zip(pts[:-1], pts[1:]):
        n = max(abs(xb - xa), abs(yb - ya))
        for i in range(n + 1):
            c = (int(round(xa + (xb - xa) * i / max(n, 1))), int(round(ya + (yb - ya) * i / max(n, 1))))
            if not cells or cells[-1] != c:
                cells.append(c)
    tz = _tz(V)
    for i, (x, y) in enumerate(cells):
        if i and abs(x - cells[i - 1][0]) + abs(y - cells[i - 1][1]) == 2:      # fill diagonal steps
            V.box(x, x, cells[i - 1][1], cells[i - 1][1], tz(x, cells[i - 1][1]) - h + 1, tz(x, cells[i - 1][1]) - 1, LOG)
        g = tz(x, y)
        hh = h - (1 if i % 2 else 0) - (1 if hsh(x, y, 3) < 0.15 else 0)
        V.box(x, x, y, y, g - hh, g - 1, LOG if i % 3 else LOG_DK)
        V.put(x, y, g - hh - 1, DEADWOOD)                                          # sharpened tip
        V.put(x, y, g - 2, ROPE if i % 4 else LOG_DK)
        if hsh(x, y, 4) < 0.1:
            V.put(x, y, g - 3, CLAW_BARK)
    V.reserve(min(c[0] for c in cells) - 2, max(c[0] for c in cells) + 2,
              min(c[1] for c in cells) - 2, max(c[1] for c in cells) + 2)
    return cells


def giant_ribcage(V, cx, y0, y1, rng, w=7, h=6):
    """Ribcage of something huge lying along y on the axis: spine on the ground, rib arches you walk through."""
    tz = _tz(V)
    for y in range(y0, y1 + 1):
        g = tz(cx, y)
        V.box(cx - 1, cx + 1, y, y, g - 1, g - 1, BONE_DK if y % 3 else BONE)
    for k, y in enumerate(range(y0 + 2, y1 - 1, 3)):
        g = tz(cx, y)
        f = 1 - abs((y - (y0 + y1) / 2) / ((y1 - y0) / 2)) ** 2
        hh = max(3, int(round(h * (0.55 + 0.45 * f))))
        ww = max(4, int(round(w * (0.6 + 0.4 * f))))
        for sd in (-1, 1):
            # arch: up from the spine, out, and back down to the ground at x = cx +- ww
            pts = [(cx + sd * 1, y, g - 2)]
            for a in range(1, 13):
                t = a / 12 * math.pi
                pts.append((cx + sd * (1 + (ww - 1) * (1 - math.cos(t)) / 2), y, g - 1 - hh * math.sin(t) ** 0.8))
            for p0, p1 in zip(pts[:-1], pts[1:]):
                V.line4(p0, p1, BONE if (k + sd) % 2 else BONE_DK)
            V.column_to_ground(cx + sd * ww, y, g - 1, BONE_DK)
    # broken rib stubs + a few vertebra spikes
    for y in range(y0, y1, 4):
        g = tz(cx, y)
        V.put(cx, y, g - 2, BONE)
    V.reserve(cx - w - 2, cx + w + 2, y0 - 2, y1 + 2)


def ruined_watchhouse(V, x0, x1, y0, y1, rng):
    """Two-room roofless stone watch-house with a broken upper floor, a stair and a corner stump of a tower."""
    tz = _tz(V)
    g = max(tz(x, y) for x in (x0, x1) for y in (y0, y1))
    for x in range(x0 - 1, x1 + 2):
        for y in range(y0 - 1, y1 + 2):
            V.column_to_ground(x, y, g, STONE_DK)
    V.box(x0, x1, y0, y1, g, g, STONE_DK)
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            if (x + y) % 4 == 0:
                V.put(x, y, g, STONE)
    wh = 9
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            if x in (x0, x1) or y in (y0, y1):
                loss = int(5 * hsh(x // 3, y // 3, 17) ** 1.6)
                for k in range(wh - loss):
                    z = g - 1 - k
                    m = STONE if hsh(x, y, z) < 0.8 else STONE_DK
                    if k < 2 and hsh(x, y, k, 5) < 0.35:
                        m = MOSS_STONE
                    V.put(x, y, z, m)
    mid = (y0 + y1) // 2
    xm = (x0 + x1) // 2
    V.box(xm, xm, y0 + 1, y1 - 1, g - 4, g - 1, STONE)                         # partition
    V.box(xm, xm, mid - 1, mid + 1, g - 4, g - 1, AIR)
    for (side, pos) in (('S', x0 + 4), ('S', x1 - 4), ('N', xm - 4), ('W', mid), ('E', mid + 3)):
        if side in 'NS':
            yy = y1 if side == 'S' else y0
            V.box(pos - 1, pos + 1, yy, yy, g - 4, g - 1, AIR)
        else:
            xx = x0 if side == 'W' else x1
            V.box(xx, xx, pos - 1, pos + 1, g - 4, g - 1, AIR)
    for x in range(x0 + 3, x1 - 2, 5):                                          # windows
        for yy in (y0, y1):
            V.box(x, x + 1, yy, yy, g - 7, g - 6, AIR)
    # broken upper floor over the west room + stair
    V.box(x0 + 1, xm - 1, y0 + 1, y1 - 1, g - 5, g - 5, PLANK_DK)
    for x in range(x0 + 1, xm):
        for y in range(y0 + 1, y1):
            if hsh(x // 2, y // 2, 9) < 0.35:
                V.put(x, y, g - 5, AIR)
    for k in range(1, 6):
        x = xm - 1 - (5 - k)
        V.box(x, x, y1 - 2, y1 - 1, g - k, g - 1, STONE_DK)       # solid stair, no pocket under it
    for x in range(xm - 6, xm):
        V.put(x, y1 - 1, g - 5, PLANK_DK); V.put(x, y1 - 2, g - 5, PLANK_DK)
        V.put(x, y1 - 1, g - 6, AIR); V.put(x, y1 - 2, g - 6, AIR)
    # rubble, fallen beams, a hearth with embers, a lantern on the sill
    for _ in range(14):
        x = int(rng.integers(x0 + 1, x1)); y = int(rng.integers(y0 + 1, y1))
        if V.get(x, y, g - 1) == AIR and V.get(x, y, g - 2) == AIR:
            V.put(x, y, g - 1, STONE_DK if rng.random() < 0.7 else PLANK_DK)
    V.line4((xm + 2, y0 + 2, g - 1), (x1 - 2, y1 - 3, g - 3), TIMBER)
    V.box(x1 - 2, x1 - 1, mid - 1, mid, g - 1, g - 1, EMBER)
    V.put(x1 - 1, y0 + 2, g - 2, LANTERN)
    for x in range(x0 - 2, x1 + 3):                                             # rubble skirt outside
        for y in (y0 - 2, y1 + 2):
            if hsh(x, y, 21) < 0.2:
                V.put_air(x, y, tz(x, y) - 1, STONE_DK)
    V.reserve(x0 - 3, x1 + 3, y0 - 3, y1 + 3)
    return g


def silver_forge(V, x, y, g):
    """Stone forge with a glowing mouth, bellows, anvil, quench barrel and a crate of silver shot."""
    V.box(x, x + 3, y, y + 2, g - 3, g - 1, STONE)
    V.box(x + 1, x + 2, y + 2, y + 2, g - 2, g - 1, EMBER)
    V.put(x + 1, y + 1, g - 3, GLOW); V.put(x + 2, y + 1, g - 3, EMBER)
    V.box(x + 1, x + 2, y, y + 1, g - 6, g - 4, STONE_DK)                        # chimney
    V.box(x - 2, x - 1, y + 1, y + 2, g - 1, g - 1, PELT)                          # bellows
    V.put(x - 2, y + 1, g - 2, PLANK_DK)
    V.box(x + 5, x + 6, y + 3, y + 3, g - 1, g - 1, IRON_DK)                       # anvil
    V.box(x + 5, x + 7, y + 3, y + 3, g - 2, g - 2, IRON)
    V.put(x + 6, y + 3, g - 3, SILVER)
    barrel(V, x + 4, y - 2, g)
    V.box(x + 8, x + 9, y, y + 1, g - 2, g - 1, PLANK)                             # crate of silver
    V.box(x + 8, x + 9, y, y + 1, g - 2, g - 2, SILVER)


def weapon_rack(V, x, y, g, along_x=True):
    L = 6
    for e in (0, L - 1):
        px, py = (x + e, y) if along_x else (x, y + e)
        V.box(px, px, py, py, g - 4, g - 1, TIMBER)
    for i in range(L):
        px, py = (x + i, y) if along_x else (x, y + i)
        V.put(px, py, g - 4, TIMBER)
        if 0 < i < L - 1:
            V.line4((px, py, g - 3), (px, py, g - 1), IRON_DK if i % 2 else TIMBER)  # rifles / spears
            V.put(px, py, g - 4, SILVER if i % 2 else TIMBER)


def torn_tent(V, x, y, g, rng, along_x=True):
    S.tent(V, x, y, g, rng, along_x=along_x, L=7)
    for i in range(1, 6):                                                          # rips in the canvas
        for off in (-2, 2):
            px, py = (x + i, y + off) if along_x else (x + off, y + i)
            if hsh(px, py, 31) < 0.35 and V.get(px, py, g - 2) == CANVAS:
                V.put(px, py, g - 2, AIR)
            if hsh(px, py, 32) < 0.2 and V.get(px, py, g - 3) == CANVAS:
                V.put(px, py, g - 3, PELT_GREY)          # patched with hide


def gibbet(V, x, y, g, arm=(1, 0)):
    """Gallows post with an arm and a hanging iron cage holding bones (cage bottom 4 above the ground)."""
    V.box(x, x, y, y, g - 10, g - 1, LOG_DK)
    V.put(x - 1, y, g - 1, STONE_DK); V.put(x + 1, y, g - 1, STONE_DK); V.put(x, y - 1, g - 1, STONE_DK)
    ax, ay = arm
    for k in range(1, 5):
        V.put(x + ax * k, y + ay * k, g - 10, LOG_DK)
    V.line4((x, y, g - 8), (x + ax * 2, y + ay * 2, g - 10), TIMBER)
    cx, cy = x + ax * 4, y + ay * 4
    V.put(cx, cy, g - 9, IRON_DK)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx or dy:
                if (dx + dy) % 2 or (dx and dy):
                    V.box(cx + dx, cx + dx, cy + dy, cy + dy, g - 8, g - 5, IRON_DK)
    V.box(cx - 1, cx + 1, cy - 1, cy + 1, g - 8, g - 8, IRON_DK)
    V.box(cx - 1, cx + 1, cy - 1, cy + 1, g - 5, g - 5, IRON_DK)
    V.put(cx, cy, g - 6, BONE); V.put(cx, cy, g - 7, BONE_DK)
    V.put(cx, cy, g - 4, LANTERN) if False else None


def claw_boulder(V, x, y, g, rng, r=3):
    boulder(V, x, y, g, r, rng, snow=True)
    for dz in range(1, r + 1):
        for k in range(3):
            px = x - r + k * 2
            if V.get(px, y + r - 1, g - dz) == ROCK:
                V.put(px, y + r - 1, g - dz, ROCK_DK)
            if V.get(px, y - r + 1, g - dz) == ROCK:
                V.put(px, y - r + 1, g - dz, ROCK_DK)


def skull_totem(V, x, y, g, rng):
    V.box(x, x, y, y, g - 6, g - 1, TIMBER)
    V.box(x - 1, x + 1, y, y, g - 7, g - 6, BONE)
    V.put(x - 1, y + 1, g - 6, MAW) if False else None
    V.put(x, y + 1, g - 7, BONE)
    antlers(V, x, y, g - 8, along_x=True, size=2)
    V.put(x + 1, y, g - 4, IRON_DK); V.put(x + 1, y, g - 3, LANTERN)
    V.put(x - 1, y, g - 3, RAG_RED); V.put(x - 1, y, g - 2, RAG_RED)


def drag_trail(V, pts, rng):
    """Blood drag marks across the snow, ending at the pit rim."""
    tz = _tz(V)
    for (xa, ya), (xb, yb) in zip(pts[:-1], pts[1:]):
        n = int(max(abs(xb - xa), abs(yb - ya)))
        for i in range(n):
            x = xa + (xb - xa) * i / n; y = ya + (yb - ya) * i / n
            for o in (-1, 0, 1):
                px, py = int(round(x + o * 0.0)), int(round(y + o))
                if hsh(px, py, 41) < 0.55 - 0.15 * abs(o):
                    g = V.ground(px, py)
                    if V.get(px, py, g) in TERRAIN_MATS:
                        V.put(px, py, g, BLOOD_SNOW)


# ------------------------------------------------------------------ placement

def dress_centre(V, F, rng):
    tz = _tz(V)
    out = {}
    # den floor: broken palisade around the pit (r 24-27), wide gaps on the E-W lane and toward the passages
    for (a0, a1) in ((112, 140), (220, 248)):
        pts = []
        for a in range(a0, a1 + 1, 4):
            t = math.radians(a)
            pts.append((256 + 26 * math.cos(t), 256 + 24 * math.sin(t)))
        palisade(V, [(int(round(p[0])), int(round(p[1]))) for p in pts], rng, h=4)
    for (a0, a1) in ((162, 170), (190, 198)):                                   # short stubs near the lane
        pts = [(int(round(256 + 27 * math.cos(math.radians(a)))), int(round(256 + 25 * math.sin(math.radians(a)))))
               for a in range(a0, a1 + 1, 4)]
        palisade(V, pts, rng, h=3)
    # giant beast ribcage on the axis between the pit and the skull (<= 6 high, under the platform)
    giant_ribcage(V, 256, 270, 290, rng, w=7, h=6)
    # overturned hunters' wagons + scattered crates on the den floor (west half)
    S.wagon_overturned(V, 222, 228, tz(222, 228), rng, along_x=True)
    V.reserve(220, 234, 224, 232)
    S.wagon_overturned(V, 222, 288, tz(222, 288), rng, along_x=True)
    V.reserve(220, 234, 284, 292)
    for (cx, cy) in ((236, 226), (238, 290), (218, 238)):
        crate(V, cx, cy, tz(cx, cy))
    barrel(V, 240, 228, tz(240, 228))
    for (bx, by) in ((228, 246), (230, 268), (244, 236), (244, 278)):
        bones(V, bx, by, tz, rng, n=6, r=3)
    drag_trail(V, [(214, 300), (232, 284), (246, 266), (249, 260)], rng)
    drag_trail(V, [(236, 214), (244, 238), (249, 250)], rng)
    # claw-raked boulders + skull totems around the crag and skull flanks
    for (bx, by, r) in ((214, 196, 4), (226, 176, 3), (232, 330, 3), (214, 346, 4), (196, 226, 3)):
        claw_boulder(V, bx, by, tz(bx, by), rng, r=r)
        V.reserve(bx - r - 1, bx + r + 1, by - r - 1, by + r + 1)
    for (sx, sy) in ((236, 198), (236, 316), (210, 220), (210, 300)):
        skull_totem(V, sx, sy, tz(sx, sy), rng)
        V.reserve(sx - 2, sx + 2, sy - 2, sy + 2)
    # ruined stone watch-house on the crag's west flank (>= 32 from the platform)
    out['watchhouse_g'] = ruined_watchhouse(V, 176, 200, 184, 202, rng)
    # hunters' war camp on the skull's west flank: torn tents, weapon rack, silver forge, campfire
    torn_tent(V, 186, 292, tz(186, 292), rng, along_x=True)
    torn_tent(V, 200, 304, tz(200, 304), rng, along_x=False)
    silver_forge(V, 182, 304, tz(182, 304))
    weapon_rack(V, 214, 296, tz(214, 296), along_x=False)
    campfire(V, 196, 296, tz(196, 296))
    sled(V, 176, 314, tz(176, 314), along_x=True, load=PELT)
    V.reserve(174, 222, 288, 318)
    # gibbets by the kill site and the trophy knoll
    gibbet(V, 230, 166, tz(230, 166), arm=(1, 0))
    gibbet(V, 230, 352, tz(230, 352), arm=(1, 0))
    V.reserve(228, 236, 162, 170); V.reserve(228, 236, 348, 356)
    # lantern posts lighting the lanes into the den
    for (lx, ly) in ((216, 232), (216, 280), (240, 214), (240, 300)):
        lantern_post(V, lx, ly, tz(lx, ly), h=5, arm=(1, 0))
    return out
