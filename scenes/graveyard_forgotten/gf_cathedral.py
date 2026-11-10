"""The Bone Cathedral: a roofless gothic ruin on the map axis (x = 256) whose missing vault has been replaced by the
rib cage and spine of a colossus. Authored for x <= 256 and mirrored by the caller (symmetric about x = 256).

Layout (north to south): parvis, twin-towered west front (here facing north) with portal + rose window, rib-vaulted
nave with bone flying buttresses, the collapsed bell-tower stump on the crossing (directly under the Babel
platform, kept low), short transepts opening onto the tower courtyards, ruined choir and apse with a bone reredos.
Everything is grounded through walls; nothing over the platform reaches above z = 16.
"""
from __future__ import annotations

import math

import numpy as np

from gf_core import hash3
from gf_props import *          # noqa: F401,F403
from gf_props import Local, DIRS, small_skull
from gf_terrain import G, SPEC


def kz(k):
    """k voxels above the basin floor -> z."""
    return G - k


def carve_pointed(V, wall_axis, t0, t1, c, half, k_lo, k_hi, k_spring, mat=AIR):
    """Pointed-arch opening through a wall. wall_axis 'y': the wall runs along y and is thick in x over
    t0..t1, the opening is centred at y = c. wall_axis 'x': runs along x, thick in y. Returns opening cells
    [(c', k)] in the wall plane."""
    cells = []
    for k in range(k_lo, k_hi + 1):
        if k <= k_spring:
            hw = half
        else:
            f = (k - k_spring) / (k_hi - k_spring + 1)
            hw = int(round(half * (1 - f ** 1.25)))
            if half - f * (half + 0.6) < -0.3:
                continue
        for o in range(c - hw, c + hw + 1):
            cells.append((o, k))
            for t in range(t0, t1 + 1):
                if wall_axis == 'y':
                    V.put(t, o, kz(k), mat)
                else:
                    V.put(o, t, kz(k), mat)
    return cells


def glaze(V, wall_axis, t, cells, rng, palette, broken=0.3, mullion=None):
    """Stained glass in one wall plane: panes coloured in vertical bands, some missing (broken)."""
    for (o, k) in cells:
        if mullion is not None and o == mullion:
            m = TRACERY
        elif rng.random() < broken:
            continue
        else:
            m = palette[(o // 1 + k // 3) % len(palette)]
        if wall_axis == 'y':
            V.put(t, o, kz(k), m)
        else:
            V.put(o, t, kz(k), m)


def jag(n, y, salt, lo, hi):
    """Coherent-ish jagged height in [lo, hi] along a wall (per 3-voxel block)."""
    b = y // 3
    v = 0.55 * hash3(b, salt, 1) + 0.45 * hash3(b // 2, salt, 2)
    return int(lo + (hi - lo) * v)


# ----------------------------------------------------------------------------- west front

def facade(V, rng):
    x0, x1, y0, y1 = SPEC['facade_tower']
    # tower plinth and core
    V.box(x0, x1, y0, y1, kz(2), kz(1), STONE_DK)
    V.box(x0 + 1, x1 - 1, y0 + 1, y1 - 1, kz(36), kz(3), STONE)
    # clasping corner buttresses with set-offs
    for (cx, cy) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        sx = -1 if cx == x0 else 1
        sy = -1 if cy == y0 else 1
        for (k_lo, k_hi, out) in ((1, 14, 2), (15, 25, 1), (26, 34, 0)):
            V.box(cx - sx * 1, cx + sx * out, cy - sy * 1, cy + sy * out, kz(k_hi), kz(k_lo), STONE_DK)
        V.box(cx, cx, cy, cy, kz(38), kz(35), STONE_DK)
        V.put(cx, cy, kz(39), STONE_LT)
    # string courses
    for k in (12, 24, 35):
        V.box(x0, x1, y0, y1, kz(k), kz(k), STONE_DK, only_air=True)
    # hollow belfry stage with open lancets on all four faces
    V.box(x0 + 3, x1 - 3, y0 + 3, y1 - 3, kz(34), kz(25), AIR)
    tcx, tcy = (x0 + x1) // 2, (y0 + y1) // 2
    for (axis, t0, t1, c) in (('y', x0 + 1, x0 + 2, tcy), ('y', x1 - 2, x1 - 1, tcy),
                              ('x', y0 + 1, y0 + 2, tcx), ('x', y1 - 2, y1 - 1, tcx)):
        for off in (-4, 4):
            carve_pointed(V, axis, t0, t1, c + off, 1, 25, 33, 30)
    # lower blind lancets (dark recesses) on the outer faces
    for k_lo, k_hi in ((5, 10), (14, 19)):
        for off in (-4, 0, 4):
            cells = carve_pointed(V, 'y', x0 + 1, x0 + 1, tcy + off, 1, k_lo, k_hi, k_hi - 2, SOCKET)
            cells = carve_pointed(V, 'x', y0 + 1, y0 + 1, tcx + off, 1, k_lo, k_hi, k_hi - 2, SOCKET)
    # parapet with crenels
    for x in range(x0 + 1, x1):
        for y in (y0 + 1, y1 - 1):
            if (x + y) % 3 != 0:
                V.put(x, y, kz(37), STONE)
    for y in range(y0 + 1, y1):
        for x in (x0 + 1, x1 - 1):
            if (x + y) % 3 != 0:
                V.put(x, y, kz(37), STONE)
    # broken octagonal spire: solid pyramid from k 33, upper third sheared off at an angle
    for k in range(37, 44):
        r = 7.5 * (1 - (k - 37) / 9.0)
        for x in range(tcx - 8, tcx + 9):
            for y in range(tcy - 8, tcy + 9):
                dx, dy = abs(x - tcx), abs(y - tcy)
                if max(dx, dy) <= r and dx + dy <= r * 1.42:
                    shear = (x - tcx) * 0.55 + (y - tcy) * 0.35 + 41.5
                    if k <= shear + hash3(x, y, k, 9) * 1.5:
                        V.put(x, y, kz(k), ROOF_SLATE if (k + (x + y) // 2) % 4 else STONE_DK)
    # skull gargoyles at the belfry corners
    for (cx, cy) in ((x0, y0), (x1, y0), (x0, y1)):
        V.put(cx, cy, kz(24), BONE)
        V.put(cx + (-1 if cx == x0 else 1), cy, kz(24), BONE)

    # ---- central screen between the towers (x 236..256), y 136..141
    fy0, fy1 = SPEC['facade_wall_y']
    for x in range(x1, 257):
        k_top = int(26 + (x - x1) * 10 / (256 - x1))
        V.box(x, x, fy0, fy1, kz(k_top), kz(1), STONE)
        V.put(x, fy0, kz(k_top + 1), STONE_DK)             # gable coping
    V.box(256, 256, fy0, fy1, kz(38), kz(37), STONE_LT)     # gable cross
    V.box(255, 256, fy0 + 2, fy0 + 3, kz(37), kz(37), STONE_LT)
    # portal with stepped archivolts (recesses widen toward the front)
    for (y, half, h, spr) in ((fy0, 7, 16, 10), (fy0 + 1, 6, 15, 10)):
        carve_pointed(V, 'x', y, y, 256, half, 1, h, spr)
    carve_pointed(V, 'x', fy0 + 2, fy1, 256, 5, 1, 14, 9)
    for y in (fy0, fy0 + 1):                                 # jamb shafts
        half = 7 if y == fy0 else 6
        V.box(256 - half - 1, 256 - half - 1, y, y, kz(10), kz(1), STONE_LT)
    # fallen door leaves in front of the portal
    V.box(250, 255, fy0 - 7, fy0 - 2, kz(1), kz(1), WOOD_DK)
    V.box(251, 251, fy0 - 7, fy0 - 2, kz(1), kz(1), IRON)
    # skull frieze above the portal (protrudes one voxel)
    for xs in (241, 245, 249):
        V.box(xs - 1, xs + 1, fy0 - 1, fy0 - 1, kz(19), kz(19), BONE)
        V.put(xs - 1, fy0 - 1, kz(18), SOCKET); V.put(xs, fy0 - 1, kz(18), BONE); V.put(xs + 1, fy0 - 1, kz(18), SOCKET)
        V.put(xs, fy0 - 1, kz(17), BONE_DK)
    V.box(238, 256, fy0 - 1, fy0 - 1, kz(16), kz(16), STONE_DK)
    V.box(238, 256, fy0 - 1, fy0 - 1, kz(20), kz(20), STONE_DK)
    # rose window: frame recess, glass plane, tracery spokes, a third of the panes gone
    rc, rk, R = 256, 26, 6.6
    for x in range(249, 257):
        for k in range(rk - 8, rk + 9):
            d = math.hypot(x - rc, k - rk)
            if d <= R + 1.2:
                V.put(x, fy0, kz(k), AIR)
            if d <= R:
                for y in range(fy0 + 1, fy1 + 1):
                    V.put(x, y, kz(k), AIR)
                ang = (math.degrees(math.atan2(k - rk, x - rc)) + 360) % 360
                spoke = min(ang % 30, 30 - ang % 30) < 4.5 / max(d, 1) * 9
                if d <= 1.5 or abs(d - 3.6) < 0.5 or abs(d - R) < 0.6 or (spoke and d > 1.5):
                    V.put(x, fy0 + 2, kz(k), TRACERY)
                elif hash3(x, k, 3, 17) > 0.33:
                    sector = int(ang // 30)
                    V.put(x, fy0 + 2, kz(k), (GLASS_P, BLOOD, GLASS_P, GLASS_G)[sector % 4] if d > 3.6
                          else GLASS_R)
    # front buttresses between portal and towers
    for xb in (241, 242):
        V.box(xb, xb, fy0 - 3, fy0 - 1, kz(14), kz(1), STONE_DK)
        V.box(xb, xb, fy0 - 2, fy0 - 1, kz(22), kz(15), STONE_DK)
    V.put(241, fy0 - 1, kz(23), STONE_LT); V.put(242, fy0 - 1, kz(23), STONE_LT)


# ----------------------------------------------------------------------------- nave

def nave_top_k(y):
    """Top of the west nave wall (k above floor) at y: ~24 with crumbled merlons, lower where the bell tower
    fell (y >= 222)."""
    y0, y1 = SPEC['nave_y']
    if y >= 224:
        return jag(0, y, 31, 12, 17)
    base = jag(0, y, 37, 21, 25)
    return base


def nave(V, rng):
    wx0, wx1 = SPEC['nave_wall_x']
    y0, y1 = SPEC['nave_y']
    tops = {}
    for y in range(y0, y1 + 1):
        kt = nave_top_k(y)
        tops[y] = kt
        V.box(wx0, wx1, y, y, kz(kt), kz(1), STONE)
        V.put(wx0 - 1, y, kz(1), STONE_DK); V.put(wx0 - 1, y, kz(2), STONE_DK)     # plinth
        if kt > 8:
            V.put(wx0 - 1, y, kz(8), STONE_DK)                                     # string course
        if (y % 4) in (0, 1) and kt >= 22:
            V.put(wx0, y, kz(kt + 1), STONE)                                      # merlons
    # clerestory lancets every 10 voxels with stained glass (outer plane) and a mullion
    pal = (GLASS_P, GLASS_G, BLOOD, GLASS_P)
    for i, yc in enumerate(range(147, 228, 10)):
        top = min(19, tops[yc] - 3)
        if top < 10:
            continue
        cells = carve_pointed(V, 'y', wx0, wx1, yc, 1, 8, top, top - 2)
        glaze(V, 'y', wx0 + 1, cells, rng, pal, broken=0.35, mullion=yc)
        for k in (7,):
            V.box(wx0 - 1, wx0 - 1, yc - 2, yc + 2, kz(k), kz(k), STONE_DK)     # sill
    # side door to the courtyard lane
    carve_pointed(V, 'y', wx0 - 1, wx1, 192, 1, 1, 6, 4)
    V.box(wx0 - 2, wx0 - 2, 190, 194, kz(1), kz(1), STONE_DK)
    return tops


def buttresses(V, tops):
    bx0, bx1 = SPEC['buttress_x']
    wx0, _ = SPEC['nave_wall_x']
    for yb in range(152, 223, 10):
        V.box(bx0, bx1, yb - 1, yb + 1, kz(12), kz(1), STONE)
        V.box(bx0 + 1, bx1, yb - 1, yb + 1, kz(21), kz(13), STONE)
        V.box(bx0, bx1, yb - 1, yb + 1, kz(1), kz(1), STONE_DK)
        V.box(bx0 + 1, bx1, yb, yb, kz(23), kz(22), STONE_DK)
        V.put(bx1, yb, kz(24), STONE_LT); V.put(bx1, yb, kz(25), STONE_LT)
        # stone arm low (walk under it) and a bone flying buttress high
        V.box(bx1 + 1, wx0 - 1, yb, yb, kz(10), kz(9), STONE_DK)
        kt = tops[yb]
        a = (bx1 + 0.5, yb + 0.5, kz(20) + 0.5)
        b = (bx1 + 3.5, yb + 0.5, kz(min(kt + 2, 25)) + 0.5)
        c = (wx0 + 0.5, yb + 0.5, kz(min(kt, 23)) + 0.5)
        V.sweep([a, b, c], [1.25, 1.05, 1.2], BONE)
        V.ball((bx1 + 1.5, yb + 0.5, kz(20) + 0.5), 1.6, BONE_DK)          # knuckle where bone meets stone


def ribs_and_spine(V, tops, rng):
    """Colossal rib cage over the nave: rib pairs every 9 voxels spring from the wall tops, bulge outward and
    arch in to a vertebral spine on the axis. Two ribs are snapped (cantilevered stubs)."""
    wx0, wx1 = SPEC['nave_wall_x']
    ry0, ry1 = SPEC['rib_y']
    sz = SPEC['spine_z']
    broken = {3, 6}
    for i, yr in enumerate(range(ry0, ry1 + 1, 9)):
        kt = tops[min(yr + 3, SPEC['nave_y'][1])]
        p0 = np.array([wx1 + 0.5, yr + 3.5, kz(kt) + 0.5])
        p1 = np.array([wx0 - 6.0, yr + 3.0, kz(kt + 9) + 0.5])
        p2 = np.array([wx1 + 4.0, yr + 1.5, sz - 1.0])
        p3 = np.array([255.5, yr + 0.5, sz + 1.5])
        n = 26
        ts = np.linspace(0, 1, n)
        pts = [((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + (t ** 3) * p3 for t in ts]
        rad = [1.55 - 0.55 * t for t in ts]
        if i in broken:
            cut = int(n * 0.55)
            pts, rad = pts[:cut], rad[:cut]
            # the snapped piece lies on the nave floor below
            fx = int(pts[-1][0]) + 4
            V.sweep([(fx, yr - 2, kz(1) + 0.5), (fx + 6, yr + 3, kz(1) + 0.5)], [1.1, 0.95], BONE)
        V.sweep(pts, rad, BONE)
        V.ball(p0, 2.0, BONE_DK)                                   # rib head seated on the wall
    # spine: vertebral bodies with discs, spinous and transverse processes
    for yv in range(SPEC['facade_wall_y'][1] + 1, ry1 + 4, 5):
        V.box(254, 256, yv, yv + 3, sz, sz + 2, BONE)
        V.box(255, 256, yv + 4, yv + 4, sz + 1, sz + 1, BONE_DK)        # disc
        V.box(256, 256, yv + 1, yv + 2, sz - 3, sz - 1, BONE)           # spinous process
        V.put(256, yv + 3, sz - 3, BONE)
        V.box(250, 253, yv + 1, yv + 2, sz + 1, sz + 1, BONE)           # transverse process
        V.put(250, yv + 1, sz, BONE_DK)


def femur_column(V, x, y, h):
    """Free-standing bone column: knobbed base, shaft, double-knob capital."""
    V.ball((x + 0.5, y + 0.5, kz(1) + 0.5), 1.9, BONE_DK)
    V.sweep([(x + 0.5, y + 0.5, kz(1)), (x + 0.5, y + 0.5, kz(h - 1))], [1.15, 1.0], BONE)
    V.ball((x - 0.5, y + 0.5, kz(h) + 0.5), 1.6, BONE)
    V.ball((x + 1.5, y + 0.5, kz(h) + 0.5), 1.6, BONE)


def nave_interior(V, rng):
    y0, y1 = SPEC['nave_y']
    for yc in range(152, 213, 10):
        femur_column(V, 245, yc, 15)
    # broken pews (centre aisle x 252..256 kept clear)
    for y in range(158, 214, 4):
        if hash3(y, 1, 1, 5) < 0.2:
            continue
        xa = 241 + int(hash3(y, 2, 1, 5) * 2)
        xb = 250 - int(hash3(y, 3, 1, 5) * 3)
        V.box(xa, xb, y, y, kz(1), kz(1), WOOD)
        V.box(xa, xb, y + 1, y + 1, kz(2), kz(1), WOOD_DK)
    # ledger slabs in the aisle floor
    for y in (166, 182, 198):
        V.box(253, 256, y, y + 2, G, G, GRAVE_DK)
    # candelabra with ghost flames
    for y in (150, 170, 190, 210):
        V.box(241, 241, y, y, kz(4), kz(1), IRON)
        V.put(241, y, kz(5), GHOST)
    # the fallen spire of the bell tower, lying along the axis, broken in three
    for (ya, yb) in ((224, 236), (210, 222), (196, 207)):
        for y in range(ya, yb + 1):
            t = (236 - y) / 40.0
            r = 4.6 - 3.4 * t
            for x in range(int(256 - r) - 1, 257):
                for k in range(0, 11):
                    dx, dk = abs(x - 256), abs(k - r)
                    if max(dx, dk) <= r and dx + dk <= r * 1.42:
                        z = kz(k) + 1                        # sunk one voxel into the floor
                        V.put(x, y, z, STONE_DK if (y // 3) % 2 else ROOF_SLATE)
    # rubble where the tower fell through the nave
    for (x, y, h) in ((242, 230, 3), (246, 226, 2), (241, 220, 2), (249, 233, 2)):
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                hh = h - (abs(dx) + abs(dy)) // 2
                for k in range(1, hh + 1):
                    V.put(x + dx, y + dy, kz(k), RUBBLE, True)


# ----------------------------------------------------------------------------- crossing (bell tower stump)

def crossing(V, rng):
    x0, x1, y0, y1 = SPEC['crossing']          # 238..274 (mirrored), 238..274
    th = 5
    for y in range(y0, y1 + 1):
        for x in range(x0, 257):
            wall = (x - x0 < th) or (y - y0 < th) or (y1 - y < th)
            if not wall:
                continue
            key = (x if (y - y0 < th or y1 - y < th) else y)
            kt = jag(0, key, 41 + (x - x0 < th) * 3, 12, 19)
            V.box(x, x, y, y, kz(kt), kz(1), STONE)
            if hash3(x, y, kt, 4) < 0.35:
                V.put(x, y, kz(kt + 1), STONE)
    # massive corner piers (fractured tops)
    for (cy0, cy1) in ((y0 - 5, y0 + 6), (y1 - 6, y1 + 5)):
        for x in range(x0 - 5, x0 + 7):
            for y in range(cy0, cy1 + 1):
                kt = 20 + int(4 * hash3(x // 2, y // 2, 7, 3)) - (1 if (x in (x0 - 5, x0 + 6) or y in (cy0, cy1)) else 0)
                V.box(x, x, y, y, kz(kt), kz(1), STONE)
                if x in (x0 - 5,) or y in (cy0, cy1):
                    V.put(x, y, kz(9), STONE_DK)
                    V.put(x, y, kz(17), STONE_DK)
    # breaches north (to the nave) and south (to the choir): the fall tore the walls open
    for (ya, yb) in ((y0, y0 + th - 1), (y1 - th + 1, y1)):
        for x in range(245, 257):
            for y in range(ya, yb + 1):
                edge = 245 + int(2 * hash3(y, 1, 1, 8))
                if x >= edge:
                    V.box(x, x, y, y, kz(30), kz(1), AIR)
                    if hash3(x, y, 2, 9) < 0.45:
                        V.put(x, y, kz(1), RUBBLE)
    # arch to the transept
    carve_pointed(V, 'y', x0, x0 + th - 1, 256, 7, 1, 13, 8)
    # tall lancets left in the high walls (dark, glassless)
    for yc in (248, 264):
        carve_pointed(V, 'y', x0, x0 + th - 1, yc, 1, 15, 18, 17, SOCKET)
    # floor + the cracked great bell lying on its side across the axis, half sunk
    V.box(x0 + th, 256, y0 + th, y1 - th, G, G, TILE_A)
    bc_y = 254
    for y in range(bc_y - 6, bc_y + 7):
        t = (y - (bc_y - 6)) / 12.0
        r_out = 2.8 + 3.6 * t ** 1.6
        for x in range(int(256 - r_out) - 1, 257):
            for k in range(-2, 9):
                d = math.hypot(x - 256, k - 3.0)
                if d <= r_out and (d >= r_out - 1.3 or y <= bc_y - 5):
                    if k <= 0:
                        V.put(x, y, kz(k) , BELL)
                    else:
                        V.put(x, y, kz(k), BELL)
    V.box(255, 256, bc_y + 1, bc_y + 6, kz(4), kz(4), AIR)       # the crack along the top
    V.box(256, 256, bc_y - 8, bc_y - 7, kz(6), kz(2), BELL)      # crown stub
    V.box(254, 256, bc_y + 8, bc_y + 10, kz(2), kz(1), IRON)     # clapper
    # charred bell-frame beams leaning on the inner walls
    for (ya, ka, yb, kb) in ((246, 1, 243, 9), (266, 1, 269, 8)):
        V.line4((246, ya, kz(ka)), (243, yb, kz(kb)), WOOD_DK)
        V.line4((247, ya, kz(ka)), (244, yb, kz(kb)), WOOD_DK)
    # rubble skirts along the inner walls (<= 3 high, steep: no ramps onto the walls)
    for (x, y) in ((244, 245), (244, 268), (250, 244), (250, 268)):
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                h = 2 - (abs(dx) + abs(dy)) // 2
                for k in range(1, h + 1):
                    V.put(x + dx, y + dy, kz(k), RUBBLE, True)


def transept(V, rng):
    x0, x1, y0, y1 = SPEC['transept']
    for x in range(x0, x1 + 1):
        for y in list(range(y0, y0 + 4)) + list(range(y1 - 3, y1 + 1)):
            kt = jag(0, x, 53 + (y < 256), 8, 14)
            V.box(x, x, y, y, kz(kt), kz(1), STONE)
            V.put(x, y, kz(1), STONE_DK)
    # end wall with gable, doorway and a broken oculus
    for y in range(y0, y1 + 1):
        kt = 15 + (12 - abs(y - 256))
        V.box(x0, x0 + 3, y, y, kz(kt), kz(1), STONE)
        V.put(x0, y, kz(kt + 1), STONE_DK)
    carve_pointed(V, 'y', x0, x0 + 3, 256, 5, 1, 10, 6)
    V.box(x0 - 1, x0 - 1, 249, 249, kz(8), kz(1), STONE_LT)
    V.box(x0 - 1, x0 - 1, 263, 263, kz(8), kz(1), STONE_LT)
    for y in range(251, 262):
        for k in range(14, 23):
            d = math.hypot(y - 256, k - 18)
            if d <= 3.6:
                for x in range(x0, x0 + 4):
                    V.put(x, y, kz(k), AIR)
                if d > 2.6 or hash3(y, k, 1, 3) > 0.45:
                    V.put(x0 + 1, y, kz(k), TRACERY if d > 2.6 else GLASS_G)
    V.box(x0 + 4, x1, y0 + 4, y1 - 4, G, G, TILE_B)


def choir(V, rng):
    wx0, wx1 = SPEC['nave_wall_x']
    cy0, cy1 = SPEC['choir_y']
    (ax, ay), R = SPEC['apse']
    for y in range(cy0, cy1 + 1):
        kt = jag(0, y, 61, 10, 20)
        V.box(wx0, wx1, y, y, kz(kt), kz(1), STONE)
        V.put(wx0 - 1, y, kz(1), STONE_DK); V.put(wx0 - 1, y, kz(2), STONE_DK)
    pal = (BLOOD, GLASS_P, BLOOD, GLASS_R)
    for yc in (284, 296, 308, 320):
        cells = carve_pointed(V, 'y', wx0, wx1, yc, 1, 7, 15, 13)
        glaze(V, 'y', wx0 + 1, cells, rng, pal, broken=0.4, mullion=yc)
    carve_pointed(V, 'y', wx0 - 1, wx1, 302, 1, 1, 6, 4)            # side door
    # apse ring (outer R, 4 thick) with radial lancets and buttresses
    for x in range(ax - R - 1, 257):
        for y in range(ay, ay + R + 2):
            d = math.hypot(x + 0.5 - ax - 0.5, y + 0.5 - ay)
            ang = math.degrees(math.atan2(y - ay, x - ax))
            if R - 4 <= d <= R:
                kt = jag(0, int(ang * 0.6) + 200, 67, 14, 24)
                V.box(x, x, y, y, kz(kt), kz(1), STONE)
                V.put(x, y, kz(1), STONE_DK)
            elif d < R - 4:
                V.put(x, y, G, TILE_A)
    for ang in (100, 130, 160):
        a = math.radians(ang)
        for k in range(7, 17):
            hw = 1 if k < 15 else 0
            for o in range(-hw, hw + 1):
                for rr in range(R - 4, R + 1):
                    x = int(round(ax + math.cos(a) * rr - math.sin(a) * o))
                    y = int(round(ay + math.sin(a) * rr + math.cos(a) * o))
                    if x <= 256:
                        V.put(x, y, kz(k), AIR)
                rr = R - 2
                x = int(round(ax + math.cos(a) * rr - math.sin(a) * o))
                y = int(round(ay + math.sin(a) * rr + math.cos(a) * o))
                if x <= 256 and hash3(x, y, k, 11) > 0.35:
                    V.put(x, y, kz(k), BLOOD if (k // 3) % 2 else GLASS_P)
    for ang in (115, 145):
        a = math.radians(ang)
        for rr in range(R + 1, R + 6):
            x = int(round(ax + math.cos(a) * rr)); y = int(round(ay + math.sin(a) * rr))
            kt = 18 - (rr - R) * 2
            V.box(x - 1, x + 1, y - 1, y + 1, kz(kt), kz(1), STONE)
            V.put(x, y, kz(kt + 1), STONE_LT)
    # choir buttresses
    bx0, bx1 = SPEC['buttress_x']
    for yb in (290, 314):
        V.box(bx0 + 1, bx1, yb - 1, yb + 1, kz(16), kz(1), STONE)
        V.put(bx1, yb, kz(17), STONE_LT)
        V.box(bx1 + 1, wx0 - 1, yb, yb, kz(9), kz(8), STONE_DK)
    # floor, dais (one step), altar with blood cloth and ghost candles, bone reredos
    V.box(wx1 + 1, 256, cy0, cy1, G, G, TILE_B)
    V.box(wx1 + 1, 256, 300, ay + R - 5, kz(1), kz(1), TILE_A, only_air=True)
    V.box(252, 256, 318, 321, kz(3), kz(2), STONE_LT)
    V.box(252, 256, 318, 321, kz(3), kz(3), BLOOD)
    V.box(254, 256, 317, 317, kz(3), kz(2), BLOOD)
    for x in (252, 256):
        V.put(x, 318, kz(4), CANDLE); V.put(x, 318, kz(5), GHOST)
    small_skull(V, 254, 320, kz(3), (0, -1))
    for x in range(244, 257):
        for k in range(2, 14):
            if k > 13 - abs(x - 256) // 3:
                continue
            V.put(x, 327, kz(k), BONE if (x + k) % 3 else BONE_DK)
            if (x % 3 == 1) and (k % 4 == 2):
                V.put(x, 326, kz(k), SOCKET)
                V.put(x, 326, kz(k + 1), BONE)
    # broken rib stubs over the choir (cantilevered from the wall tops)
    for yr in (286, 306):
        kt = jag(0, yr, 61, 10, 20)
        p0 = (wx1 + 0.5, yr + 0.5, kz(kt) + 0.5)
        V.sweep([p0, (wx0 - 4.0, yr + 0.5, kz(kt + 6)), (wx1 + 3.0, yr - 0.5, kz(kt + 9))], [1.5, 1.25, 1.0], BONE)
        V.ball(p0, 2.0, BONE_DK)


def cathedral(V, rng):
    facade(V, rng)
    tops = nave(V, rng)
    buttresses(V, tops)
    nave_interior(V, rng)
    crossing(V, rng)
    transept(V, rng)
    choir(V, rng)
    ribs_and_spine(V, tops, rng)
    # floors (checker) in the nave
    wx0, wx1 = SPEC['nave_wall_x']
    y0, y1 = SPEC['nave_y']
    for x in range(wx1 + 1, 257):
        for y in range(y0, y1 + 1):
            if V.m[x, y, G] in (SOIL, DIRT, PATH, COURT, GRAVEL, MOSS):
                V.m[x, y, G] = TILE_A if ((x // 2 + y // 2) % 2) else TILE_B
    return tops
