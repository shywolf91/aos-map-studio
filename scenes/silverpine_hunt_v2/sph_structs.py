"""Buildings and landmarks for Silverpine Hunt.

House rule: every structure is 'real' - open doorways (3 wide, 4 high), rooms, real window openings, stairs to
upper floors. Floors sit at ground level z = g (the floor voxel replaces the ground top); room air z g-1 .. g-4;
upper floors are 5 apart.
"""
from __future__ import annotations

import math

import numpy as np

from sph_props import *            # noqa: F401,F403  (materials + small props)
from sph_props import AIR, hsh


# ================================================================== log lodge / cabin

def _wall_mat(z, g, base, alt):
    c = (g - 1 - z) // 2
    return base if c % 2 == 0 else alt


def cabin(V, x0, x1, y0, y1, g, rng, floors=1, roof_axis='x', doors=(('S', None),), wall=LOG, wall2=LOG_DK,
          roof=ROOF, windows=True, chimney=None, stairs=None, partition=None, furnish=True, roof_pitch=1,
          porch=None, corner_logs=True, attic=False):
    """Log building. doors: tuple of (side, offset or None=centre). stairs: (sx, sy, dx, dy) start + direction
    for the stair to the upper floor (floors >= 2). chimney: 'W'/'E'/'N'/'S' end wall for the fireplace."""
    wh = 5 * floors
    V.reserve(x0, x1, y0, y1, pad=2)
    V.box(x0, x1, y0, y1, g, g, PLANK)                            # floor
    V.box(x0, x1, y0, y1, g + 1, g + 1, STONE_DK)                 # foundation course
    for z in range(g - wh, g):
        for x in range(x0, x1 + 1):
            for y in (y0, y1):
                V.put(x, y, z, _wall_mat(z, g, wall, wall2))
        for y in range(y0, y1 + 1):
            for x in (x0, x1):
                V.put(x, y, z, _wall_mat(z, g, wall, wall2))
        if corner_logs and ((g - 1 - z) // 2) % 2 == 0:
            for (cx, cy) in ((x0 - 1, y0), (x1 + 1, y0), (x0 - 1, y1), (x1 + 1, y1)):
                V.put(cx, cy, z, wall2)
            for (cx, cy) in ((x0, y0 - 1), (x1, y0 - 1), (x0, y1 + 1), (x1, y1 + 1)):
                V.put(cx, cy, z, wall2)
    V.box(x0, x1, y0, y1, g - wh, g - wh, wall2)                  # top plate
    V.box(x0 + 1, x1 - 1, y0 + 1, y1 - 1, g - wh, g - wh, AIR if not attic else PLANK)
    for f in range(1, floors):                                     # upper floor slabs
        V.box(x0 + 1, x1 - 1, y0 + 1, y1 - 1, g - 5 * f, g - 5 * f, PLANK)
    # doors
    door_cells = []
    for side, off in doors:
        if side in 'NS':
            yy = y0 if side == 'N' else y1
            c = (x0 + x1) // 2 if off is None else off
            V.box(c - 1, c + 1, yy, yy, g - 4, g - 1, AIR)
            V.box(c - 2, c + 2, yy, yy, g - 5, g - 5, TIMBER)      # lintel
            door_cells += [(c + d, yy) for d in (-2, -1, 0, 1, 2)]
        else:
            xx = x0 if side == 'W' else x1
            c = (y0 + y1) // 2 if off is None else off
            V.box(xx, xx, c - 1, c + 1, g - 4, g - 1, AIR)
            V.box(xx, xx, c - 2, c + 2, g - 5, g - 5, TIMBER)
            door_cells += [(xx, c + d) for d in (-2, -1, 0, 1, 2)]
    # windows (2 wide, 2 high) with sills and an inner candle
    if windows:
        for f in range(floors):
            zb = g - 2 - 5 * f
            for x in range(x0 + 3, x1 - 3, 6):
                for yy, iy in ((y0, 1), (y1, -1)):
                    if any(abs(x - dx) <= 2 and dy == yy for dx, dy in door_cells) or \
                            any(abs(x + 1 - dx) <= 2 and dy == yy for dx, dy in door_cells):
                        continue
                    V.box(x, x + 1, yy, yy, zb - 1, zb, AIR)
                    V.box(x - 1, x + 2, yy - iy, yy - iy, zb + 1, zb + 1, PLANK_DK)
                    if hsh(x, yy, f) < 0.55:
                        V.put(x, yy + iy, zb + 1, PLANK); V.put(x, yy + iy, zb, CANDLE)
            for y in range(y0 + 3, y1 - 3, 6):
                for xx, ix in ((x0, 1), (x1, -1)):
                    if any(abs(y - dy) <= 2 and dx == xx for dx, dy in door_cells) or \
                            any(abs(y + 1 - dy) <= 2 and dx == xx for dx, dy in door_cells):
                        continue
                    V.box(xx, xx, y, y + 1, zb - 1, zb, AIR)
                    V.box(xx - ix, xx - ix, y - 1, y + 2, zb + 1, zb + 1, PLANK_DK)
                    if hsh(xx, y, f) < 0.55:
                        V.put(xx + ix, y, zb + 1, PLANK); V.put(xx + ix, y, zb, CANDLE)
    # interior partition with a doorway
    if partition:
        ax, pos = partition
        if ax == 'x':                                               # wall at x = pos spanning y
            V.box(pos, pos, y0 + 1, y1 - 1, g - 4, g - 1, wall)
            mid = (y0 + y1) // 2
            V.box(pos, pos, mid - 1, mid + 1, g - 4, g - 1, AIR)
        else:
            V.box(x0 + 1, x1 - 1, pos, pos, g - 4, g - 1, wall)
            mid = (x0 + x1) // 2
            V.box(mid - 1, mid + 1, pos, pos, g - 4, g - 1, AIR)
    # stairs (2 wide, 2-voxel-tall treads so they are face connected), slab cut above
    if stairs and floors >= 2:
        sx, sy, dx, dy = stairs
        for f in range(floors - 1):
            for k in range(1, 6):
                px, py = sx + dx * (k - 1), sy + dy * (k - 1)
                ztop = g - 5 * f - k
                for w in range(2):
                    qx, qy = (px, py + w) if dx else (px + w, py)
                    V.box(qx, qx, qy, qy, ztop, g - 5 * f - 1, PLANK_DK)
                    for kk in range(0, 6):                          # head room through the slab
                        if V.get(qx, qy, ztop - 1 - kk) == PLANK and ztop - 1 - kk >= g - 5 * (f + 1):
                            V.put(qx, qy, ztop - 1 - kk, AIR)
            # open the slab over the first steps too
            for k in range(-1, 3):
                px, py = sx + dx * k, sy + dy * k
                for w in range(2):
                    qx, qy = (px, py + w) if dx else (px + w, py)
                    if x0 < qx < x1 and y0 < qy < y1:
                        V.put(qx, qy, g - 5 * (f + 1), AIR)
            # railing on the open slab edge
    # gable roof
    rx0, rx1, ry0, ry1 = x0 - 1, x1 + 1, y0 - 1, y1 + 1
    zt = g - wh
    if roof_axis == 'x':
        lo0, lo1, n_lo = ry0, ry1, None
    else:
        lo0, lo1 = rx0, rx1
    W = lo1 - lo0 + 1
    half = (W + 1) // 2
    zprev = None
    for i in range(half):
        z = zt - i // roof_pitch
        rows = (lo0 + i, lo1 - i)
        for r_ in rows:
            if roof_axis == 'x':
                for x in range(rx0, rx1 + 1):
                    V.put(x, r_, z, roof if i < half - 1 else ROOF_DK)
                    if zprev is not None and z != zprev:
                        V.put(x, r_, z + 1, roof)
            else:
                for y in range(ry0, ry1 + 1):
                    V.put(r_, y, z, roof if i < half - 1 else ROOF_DK)
                    if zprev is not None and z != zprev:
                        V.put(r_, y, z + 1, roof)
        if i > 0:                                                   # gable end walls
            for c in range(lo0 + i + 1, lo1 - i):
                for zz in range(z, (zprev if zprev is not None else z) + 1):
                    if roof_axis == 'x':
                        for xx in (x0, x1):
                            if V.get(xx, c, zz) == AIR:
                                V.put(xx, c, zz, wall2 if (i % 2) else wall)
                    else:
                        for yy in (y0, y1):
                            if V.get(c, yy, zz) == AIR:
                                V.put(c, yy, zz, wall2 if (i % 2) else wall)
        zprev = z
    ridge_z = zt - (half - 1) // roof_pitch
    if half > 4 and (zt - ridge_z) >= 4:                            # gable windows
        if roof_axis == 'x':
            mid = (y0 + y1) // 2
            for xx in (x0, x1):
                V.box(xx, xx, mid - 1, mid, zt - 3, zt - 2, AIR)
        else:
            mid = (x0 + x1) // 2
            for yy in (y0, y1):
                V.box(mid - 1, mid, yy, yy, zt - 3, zt - 2, AIR)
    # chimney + fireplace
    if chimney:
        if chimney in 'WE':
            cx = x0 + 1 if chimney == 'W' else x1 - 2
            cy = (y0 + y1) // 2 - 1
            V.box(cx, cx + 1, cy, cy + 2, ridge_z - 2, g - 1, STONE)
            V.box(cx + (1 if chimney == 'W' else 0), cx + (1 if chimney == 'W' else 0), cy, cy + 2, g - 2, g - 1,
                  EMBER)
            V.put(cx + (1 if chimney == 'W' else 0), cy + 1, g - 3, EMBER)
            V.box(cx, cx + 1, cy, cy + 2, ridge_z - 3, ridge_z - 2, STONE_DK)
        else:
            cy = y0 + 1 if chimney == 'N' else y1 - 2
            cx = (x0 + x1) // 2 - 1
            V.box(cx, cx + 2, cy, cy + 1, ridge_z - 2, g - 1, STONE)
            iy = cy + (1 if chimney == 'N' else 0)
            V.box(cx, cx + 2, iy, iy, g - 2, g - 1, EMBER)
            V.put(cx + 1, iy, g - 3, EMBER)
            V.box(cx, cx + 2, cy, cy + 1, ridge_z - 3, ridge_z - 2, STONE_DK)
    if furnish:
        _furnish(V, x0, x1, y0, y1, g, rng, floors)
    if porch:
        _porch(V, x0, x1, y0, y1, g, porch, rng, zt)
    return {'zt': zt, 'ridge_z': ridge_z}


def _free(V, x, y, z0, z1):
    return all(V.get(x, y, z) == AIR for z in range(z0, z1 + 1))


def _furnish(V, x0, x1, y0, y1, g, rng, floors):
    for f in range(floors):
        gf = g - 5 * f
        tries = 0
        placed = 0
        while placed < max(2, (x1 - x0) * (y1 - y0) // 60) and tries < 40:
            tries += 1
            x = int(rng.integers(x0 + 3, x1 - 4)); y = int(rng.integers(y0 + 3, y1 - 4))
            kind = rng.random()
            if kind < 0.35 and all(_free(V, x + a, y + b, gf - 3, gf - 1) for a in range(3) for b in range(2)):
                V.box(x, x + 2, y, y + 1, gf - 2, gf - 2, PLANK_DK)       # table
                V.put(x, y, gf - 1, TIMBER); V.put(x + 2, y + 1, gf - 1, TIMBER)
                V.put(x + 1, y, gf - 3, CANDLE if rng.random() < 0.6 else BONE)
                placed += 1
            elif kind < 0.6 and all(_free(V, x + a, y + b, gf - 3, gf - 1) for a in range(2) for b in range(4)):
                V.box(x, x + 1, y, y + 3, gf - 1, gf - 1, PLANK)          # bed with pelt
                V.box(x, x + 1, y + 1, y + 3, gf - 1, gf - 1, PELT if rng.random() < 0.5 else PELT_GREY)
                placed += 1
            elif kind < 0.75 and _free(V, x, y, gf - 3, gf - 1) and _free(V, x + 1, y, gf - 3, gf - 1):
                barrel(V, x, y, gf); placed += 1
            elif kind < 0.9:
                for a in range(-1, 3):                                   # pelt rug painted into the floor
                    for b in range(-1, 2):
                        if V.get(x + a, y + b, gf) == PLANK and _free(V, x + a, y + b, gf - 1, gf - 1):
                            V.put(x + a, y + b, gf, PELT_RED if (a + b) % 3 == 0 else PELT)
                placed += 1
    # antlers on the inside of the long walls
    for x in range(x0 + 4, x1 - 3, 9):
        for yy, iy in ((y0, 1), (y1, -1)):
            z = g - 4
            if V.get(x, yy, z) != AIR and V.get(x, yy + iy, z) == AIR:
                V.put(x, yy + iy, z, BONE_DK)
                antlers(V, x, yy + iy, z - 1, along_x=True, size=2)


def _porch(V, x0, x1, y0, y1, g, side, rng, zt):
    d = 3
    if side == 'S':
        px0, px1, py0, py1 = x0, x1, y1 + 1, y1 + d
    elif side == 'N':
        px0, px1, py0, py1 = x0, x1, y0 - d, y0 - 1
    elif side == 'E':
        px0, px1, py0, py1 = x1 + 1, x1 + d, y0, y1
    else:
        px0, px1, py0, py1 = x0 - d, x0 - 1, y0, y1
    V.reserve(px0, px1, py0, py1, pad=1)
    V.box(px0, px1, py0, py1, g, g, PLANK)
    zr = g - 5
    posts = []
    if side in 'NS':
        oy = py1 if side == 'S' else py0
        for x in list(range(px0, px1 + 1, 5)) + [px1]:
            posts.append((x, oy))
        V.box(px0, px1, py0, py1, zr, zr, ROOF)
        V.box(px0, px1, oy, oy, zr + 1, zr + 1, TIMBER)
    else:
        ox = px1 if side == 'E' else px0
        for y in list(range(py0, py1 + 1, 5)) + [py1]:
            posts.append((ox, y))
        V.box(px0, px1, py0, py1, zr, zr, ROOF)
        V.box(ox, ox, py0, py1, zr + 1, zr + 1, TIMBER)
    for (x, y) in posts:
        V.box(x, x, y, y, zr + 1, g - 1, TIMBER)
    for i, (x, y) in enumerate(posts[1:-1]):
        if i % 2 == 0:
            V.put(x, y, zr + 2, IRON_DK); V.put(x, y, zr + 3, LANTERN) if V.get(x, y, zr + 3) == AIR else None
    # jack-o'-lanterns + firewood on the porch ends
    if side in 'NS':
        jack_o_lantern(V, px0 + 1, (py0 + py1) // 2, g, face=(0, 1 if side == 'S' else -1))
        firewood(V, px1 - 5, py0, g, 4, along_x=True, h=2)
    else:
        jack_o_lantern(V, (px0 + px1) // 2, py0 + 1, g, face=(1 if side == 'E' else -1, 0))
        firewood(V, px0, py1 - 5, g, 4, along_x=False, h=2)


# ================================================================== tower, gate, sheds

def watchtower(V, x, y, g, rng, h=16, door='E'):
    """7x7 timber tower; interior square spiral stair (16 steps / loop) to a railed lookout with a roof."""
    S = 7
    V.reserve(x, x + S - 1, y, y + S - 1, pad=2)
    V.box(x, x + S - 1, y, y + S - 1, g, g, PLANK)
    for (cx, cy) in ((x, y), (x + S - 1, y), (x, y + S - 1), (x + S - 1, y + S - 1)):
        V.box(cx, cx, cy, cy, g - h - 5, g - 1, LOG_DK)
    # plank walls with horizontal slits every 4th course
    for z in range(g - h + 1, g):
        if (g - z) % 4 == 0:
            continue
        for i in range(1, S - 1):
            for (wx, wy) in ((x + i, y), (x + i, y + S - 1), (x, y + i), (x + S - 1, y + i)):
                V.put(wx, wy, z, PLANK if (i + z) % 5 else PLANK_DK)
    # door
    if door == 'E':
        V.box(x + S - 1, x + S - 1, y + 2, y + 4, g - 4, g - 1, AIR)
    elif door == 'W':
        V.box(x, x, y + 2, y + 4, g - 4, g - 1, AIR)
    elif door == 'S':
        V.box(x + 2, x + 4, y + S - 1, y + S - 1, g - 4, g - 1, AIR)
    else:
        V.box(x + 2, x + 4, y, y, g - 4, g - 1, AIR)
    # spiral ring: interior cells 1..5 border, clockwise, starting next to the door
    ring = []
    for i in range(1, 6):
        ring.append((x + i, y + 1))
    for i in range(2, 6):
        ring.append((x + 5, y + i))
    for i in range(4, 0, -1):
        ring.append((x + i, y + 5))
    for i in range(4, 1, -1):
        ring.append((x + 1, y + i))
    start = {'N': 2, 'E': 6, 'S': 10, 'W': 14}[door] if door in 'NESW' else 0
    for k in range(1, h + 1):
        px, py = ring[(start + k) % len(ring)]
        V.box(px, px, py, py, g - k, g - k + 1, PLANK_DK)
    # lookout floor (with stair hole at the arrival cell and the 2 before it)
    zf = g - h
    V.box(x, x + S - 1, y, y + S - 1, zf, zf, PLANK)
    for k in range(h - 3, h):
        px, py = ring[(start + k) % len(ring)]
        V.put(px, py, zf, AIR)
    V.box(x - 1, x + S, y - 1, y + S, zf, zf, PLANK)            # 1-voxel balcony overhang
    for i in range(-1, S + 1):                                   # railing with gaps
        for (wx, wy) in ((x + i, y - 1), (x + i, y + S), (x - 1, y + i), (x + S, y + i)):
            if (i % 2) == 0:
                V.put(wx, wy, zf - 1, TIMBER)
    # pyramid roof
    zr = zf - 5
    for i in range(0, 5):
        V.box(x - 1 + i, x + S - i, y - 1 + i, y + S - i, zr - i, zr - i, ROOF if i < 4 else ROOF_DK)
    V.put(x + 3, y + 3, zr - 5, IRON_DK)
    hanging_lantern(V, x + 3, y + 3, zr, drop=1)
    antlers(V, x + 3, y - 2, zr + 1, along_x=True, size=3)
    V.put(x + 3, y - 2, zr + 1, BONE)
    return zf


def log_gate(V, x, y0, y1, g, rng, h=12):
    """Hunters' log gateway across a front (opening y0+2 .. y1-2, beam h above ground)."""
    for py in (y0, y1 - 1):
        V.box(x, x + 1, py, py + 1, g - h - 1, g - 1, LOG)
        V.box(x, x + 1, py, py + 1, g - h - 2, g - h - 2, LOG_DK)
        V.put(x - 1, py, g - 1, STONE_DK); V.put(x + 2, py + 1, g - 1, STONE_DK)
    V.box(x, x + 1, y0, y1, g - h, g - h + 1, LOG)
    V.box(x, x + 1, y0 - 1, y1 + 1, g - h - 1, g - h - 1, LOG_DK)
    # braces
    for (a, b) in ((y0 + 1, y0 + 5), (y1 - 1, y1 - 5)):
        V.line4((x, a, g - h + 5), (x, b, g - h + 2), TIMBER)
    mid = (y0 + y1) // 2
    # wolf skull + antlers centrepiece
    V.box(x - 1, x - 1, mid - 1, mid + 1, g - h + 2, g - h + 3, BONE)
    V.put(x - 1, mid - 1, g - h + 2, MAW); V.put(x - 1, mid + 1, g - h + 2, MAW)
    V.box(x - 2, x - 2, mid, mid, g - h + 3, g - h + 4, BONE)
    antlers(V, x, mid, g - h - 2, along_x=False, size=4)
    # banners hanging off the beam (bottom 6 above the ground)
    for by in (y0 + 5, y1 - 7):
        V.box(x - 1, x - 1, by, by + 2, g - h + 2, g - 7, CLOTH_TEAM)
        V.put(x - 1, by + 1, g - 6, CLOTH_TEAM)
    for ly in (y0 + 10, y1 - 10):
        hanging_lantern(V, x, ly, g - h + 1, drop=1)


def shed(V, x0, x1, y0, y1, g, rng, open_side='S', wall=PLANK, roof=ROOF, h=5):
    """Open-fronted lean-to shed (kennel / woodshed / skinning shed)."""
    V.reserve(x0, x1, y0, y1, pad=1)
    V.box(x0, x1, y0, y1, g, g, PLANK_DK)
    for z in range(g - h, g):
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                edge_x = x in (x0, x1); edge_y = y in (y0, y1)
                if not (edge_x or edge_y):
                    continue
                if open_side == 'S' and y == y1 and not edge_x:
                    continue
                if open_side == 'N' and y == y0 and not edge_x:
                    continue
                if open_side == 'E' and x == x1 and not edge_y:
                    continue
                if open_side == 'W' and x == x0 and not edge_y:
                    continue
                V.put(x, y, z, wall if (x + y + z) % 4 else PLANK_DK)
    # lean-to roof sloping toward the open side
    if open_side in 'NS':
        n = y1 - y0 + 3
        for i in range(n):
            yy = (y0 - 1 + i) if open_side == 'S' else (y1 + 1 - i)
            z = g - h - 2 + (i * 2) // n
            V.box(x0 - 1, x1 + 1, yy, yy, z, z, roof)
            V.box(x0, x1, yy, yy, z + 1, g - h, AIR) if False else None
        V.box(x0, x1, y0, y1, g - h - 1, g - h - 1, PLANK_DK)
        V.box(x0 + 1, x1 - 1, y0 + 1, y1 - (0 if open_side == 'S' else 1), g - h - 1, g - h - 1, AIR)
    else:
        n = x1 - x0 + 3
        for i in range(n):
            xx = (x0 - 1 + i) if open_side == 'E' else (x1 + 1 - i)
            z = g - h - 2 + (i * 2) // n
            V.box(xx, xx, y0 - 1, y1 + 1, z, z, roof)
        V.box(x0, x1, y0, y1, g - h - 1, g - h - 1, PLANK_DK)
        V.box(x0 + 1, x1 - 1, y0 + 1, y1 - 1, g - h - 1, g - h - 1, AIR)
    # walls must reach the roof
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            if V.get(x, y, g - h) != AIR:
                V.column_to_ground(x, y, g - h - 1, PLANK_DK) if False else None


# ================================================================== small camp structures

def tent(V, x, y, g, rng, along_x=True, L=9):
    """A-frame canvas tent 7 wide, ridge 4 up, open at the front slice (i = 0), closed at the back."""
    prof = [(3, 1), (3, 2), (2, 2), (2, 3), (1, 3), (1, 4), (0, 4)]       # face-connected (offset, height)
    def at(i, off):
        return (x + i, y + off) if along_x else (x + off, y + i)
    for i in range(L):
        for (o, k) in prof:
            for s_ in ((-1, 1) if o else (1,)):
                px, py = at(i, s_ * o)
                V.put(px, py, g - k, TIMBER if (o == 0 and i in (0, L - 1)) else CANVAS)
    for o in range(-2, 3):                                               # back wall
        for k in range(1, 4 - abs(o) + (1 if abs(o) < 2 else 0)):
            px, py = at(L - 1, o)
            V.put(px, py, g - k, CANVAS)
    for i in (0, L - 1):                                                 # poles + guy ropes
        px, py = at(i, 0)
        V.box(px, px, py, py, g - 6, g - 5, TIMBER)
        ex, ey = at(i - 3 if i == 0 else i + 3, 0)
        V.line4((px, py, g - 6), (ex, ey, g - 1), ROPE, only_air=True)
    px, py = at(L - 3, 0)
    V.put(px, py, g, PELT)
    qx, qy = at(L - 4, 0)
    V.put(qx, qy, g, PELT)
    hx, hy = at(L - 2, 1)
    V.put(hx, hy, g - 1, LANTERN)
    xa, xb = sorted((x - 4, x + L + 3)) if along_x else (x - 4, x + 4)
    ya, yb = (y - 4, y + 4) if along_x else sorted((y - 4, y + L + 3))
    V.reserve(xa, xb, ya, yb)


def hunters_blind(V, x, y, g, rng, h=6, stair_dir=(1, 0)):
    """5x5 raised platform with a branch-screen railing, a lean-to roof and a 1-wide stair."""
    V.reserve(x - 1, x + 5, y - 1, y + 5, pad=2)
    for (cx, cy) in ((x, y), (x + 4, y), (x, y + 4), (x + 4, y + 4)):
        V.box(cx, cx, cy, cy, g - h - 4, g - 1, LOG_DK)
    V.box(x, x + 4, y, y + 4, g - h, g - h, PLANK)
    for i in range(5):
        for (wx, wy) in ((x + i, y), (x + i, y + 4), (x, y + i), (x + 4, y + i)):
            if hsh(wx, wy, 1) < 0.7:
                V.put(wx, wy, g - h - 1, FOL6 if hsh(wx, wy) < 0.6 else FOL2)
    V.box(x - 1, x + 5, y - 1, y + 5, g - h - 4, g - h - 4, ROOF)
    # opening in the screen at the stair arrival
    sx, sy = stair_dir
    ax, ay = (x + 4, y + 2) if sx > 0 else (x, y + 2)
    V.put(ax, ay, g - h - 1, AIR)
    for k in range(1, h + 1):
        px = ax + sx * (h + 1 - k)
        V.box(px, px, ay, ay, g - k, g - k + 1, PLANK_DK)


def ice_shack(V, x0, y0, g, rng, door='S'):
    cabin(V, x0, x0 + 6, y0, y0 + 5, g, rng, floors=1, roof_axis='x', doors=((door, None),), wall=PLANK,
          wall2=PLANK_DK, roof=ROOF, windows=True, furnish=False, corner_logs=False)
    V.box(x0 + 2, x0 + 3, y0 + 2, y0 + 3, g, g, ICE_DK)             # fishing hole inside
    V.box(x0 + 5, x0 + 5, y0 + 1, y0 + 1, g - 9, g - 1, IRON_DK)     # stovepipe
    V.put(x0 + 5, y0 + 1, g - 1, EMBER)
    crate(V, x0 + 1, y0 + 1, g, 1)
    oy = y0 + 7 if door == 'S' else y0 - 3
    V.box(x0 + 4, x0 + 5, oy, oy + 1, g, g, ICE_DK)                  # outside hole + stool + auger
    V.put(x0 + 2, oy, g - 1, PLANK_DK)
    V.box(x0 + 7, x0 + 7, oy, oy, g - 3, g - 1, IRON)


# ================================================================== ruins + chapel

def ruin_wall(V, pts, gfun, rng, h=7, thick=2, arch_every=9, gap_every=14, h_fn=None):
    """Broken stone wall along a polyline; pointed window arches, doorway gaps, eroded crest."""
    cells = []
    for (xa, ya), (xb, yb) in zip(pts[:-1], pts[1:]):
        n = max(abs(xb - xa), abs(yb - ya))
        for i in range(n + 1):
            cells.append((int(round(xa + (xb - xa) * i / max(n, 1))), int(round(ya + (yb - ya) * i / max(n, 1)))))
    out = []
    for i, (x, y) in enumerate(cells):
        if (i % gap_every) in range(gap_every - 4, gap_every) and i > 2:
            continue                                                   # doorway gap (4 wide)
        g = gfun(x, y)
        hh = h if h_fn is None else h_fn(i / max(len(cells) - 1, 1))
        top = hh - int(2 * hsh(x // 6, y // 6, 7)) - (1 if hsh(x // 2, y // 2, 8) < 0.25 else 0)
        for t in range(thick):
            for (ox, oy) in ((0, 0), (t, 0), (0, t)):
                for k in range(top):
                    z = g - 1 - k
                    m = STONE if hsh(x + ox, y + oy, z) < 0.8 else STONE_DK
                    if k < 2 and hsh(x, y, k, 3) < 0.4:
                        m = MOSS_STONE
                    V.put(x + ox, y + oy, z, m)
        # pointed arch window
        ph = i % arch_every
        if 3 <= ph <= 4 and top >= 6:
            for k in (2, 3, 4):
                V.put(x, y, g - 1 - k, AIR); V.put(x + 1, y, g - 1 - k, AIR) if thick > 1 else None
                V.put(x, y + 1, g - 1 - k, AIR) if thick > 1 else None
        if hsh(x, y, 9) < 0.25:
            V.put_air(x, y, g - 1 - top, SNOWCAP)
        out.append((x, y))
        V.res[max(0, x - 2):x + 3, max(0, y - 2):y + 3] = True
    # rubble at the foot
    for (x, y) in out[::5]:
        if rng.random() < 0.5:
            dx, dy = int(rng.integers(-3, 4)), int(rng.integers(-3, 4))
            V.put_air(x + dx, y + dy, gfun(x + dx, y + dy) - 1, STONE_DK)
    return out


def chapel(V, x0, x1, y0, y1, g, rng):
    """Ruined moon-chapel: nave along x, door + bell tower at the east end, apse west, partial roof."""
    V.reserve(x0 - 3, x1 + 3, y0 - 3, y1 + 3)
    wh = 10
    V.box(x0, x1, y0, y1, g, g, STONE_DK)                           # flagstone floor
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            if (x + y) % 3 == 0:
                V.put(x, y, g, STONE)
    for z in range(g - wh, g):
        for x in range(x0, x1 + 1):
            for y in (y0, y0 + 1, y1 - 1, y1):
                V.put(x, y, z, STONE if hsh(x, y, z) < 0.82 else STONE_DK)
        for y in range(y0, y1 + 1):
            for x in (x0, x0 + 1, x1 - 1, x1):
                V.put(x, y, z, STONE if hsh(x, y, z) < 0.82 else STONE_DK)
    # eroded crest
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            if x in (x0, x0 + 1, x1 - 1, x1) or y in (y0, y0 + 1, y1 - 1, y1):
                loss = int(4 * hsh(x // 2, y // 2, 5) ** 2)
                if x < x0 + (x1 - x0) * 0.4:
                    loss = 0
                for k in range(loss):
                    V.put(x, y, g - wh + k, AIR)
    # buttresses + pointed windows on the long walls
    for x in range(x0 + 3, x1 - 2, 6):
        for (yy, oy) in ((y0, -1), (y1, 1)):
            V.box(x, x, yy + oy, yy + oy, g - 6, g - 1, STONE_DK)
            V.box(x, x, yy + 2 * oy, yy + 2 * oy, g - 3, g - 1, STONE_DK)
        for (yy) in (y0, y1):
            wx = x + 3
            if wx < x1 - 2:
                for k in range(2, 8):
                    w = 1 if k == 7 else 2
                    V.box(wx, wx + w - 1, yy, yy, g - 1 - k, g - 1 - k, AIR)
                    inner = yy + (1 if yy == y0 else -1)
                    V.box(wx, wx + w - 1, inner, inner, g - 1 - k, g - 1 - k, AIR)
                V.put(wx, yy, g - 2, PLANK_DK)
    # big breach in the south wall
    bx = x0 + (x1 - x0) * 2 // 3
    for dx in range(-3, 4):
        for k in range(0, 8 - abs(dx)):
            V.put(bx + dx, y1, g - 1 - k, AIR); V.put(bx + dx, y1 - 1, g - 1 - k, AIR)
        V.put_air(bx + dx, y1 + 2, g - 1, STONE_DK)
        V.put_air(bx + dx, y1 + 3, g - 1, STONE_DK) if dx % 2 else None
    # east door
    mid = (y0 + y1) // 2
    V.box(x1 - 1, x1, mid - 1, mid + 1, g - 5, g - 1, AIR)
    V.box(x1 - 1, x1, mid, mid, g - 6, g - 6, AIR)
    # west apse (semicircle) with the altar + silver crescent
    r = (y1 - y0) // 2
    for z in range(g - wh, g):
        for a in range(-90, 91, 6):
            t = math.radians(a)
            for rr in (r, r - 1):
                ax, ay = int(round(x0 - rr * math.cos(t) + 1)), int(round(mid + rr * math.sin(t)))
                if ax < x0:
                    V.put(ax, ay, z, STONE)
    for a in range(-90, 91, 6):
        t = math.radians(a)
        for rr in range(0, r - 1):
            ax, ay = int(round(x0 - rr * math.cos(t) + 1)), int(round(mid + rr * math.sin(t)))
            if ax < x0 + 2:
                V.put(ax, ay, g, STONE_DK)
                for z in range(g - wh, g):
                    if V.get(ax, ay, z) == STONE and rr < r - 1:
                        V.put(ax, ay, z, AIR)
    V.box(x0 + 2, x0 + 3, mid - 2, mid + 2, g - 2, g - 1, STONE)       # altar
    V.box(x0 + 2, x0 + 3, mid - 2, mid + 2, g - 2, g - 2, STONE_DK)
    for (dy, dz) in ((-1, -4), (0, -5), (1, -4), (-2, -3), (2, -3)):
        V.put(x0 + 2, mid + dy, g + dz, SILVER)
    V.box(x0 + 2, x0 + 2, mid, mid, g - 4, g - 3, IRON_DK)
    for dy in (-2, 2):
        V.put(x0 + 3, mid + dy, g - 3, CANDLE)
    # broken pews
    for x in range(x0 + 6, x1 - 5, 3):
        for side in (-1, 1):
            if hsh(x, side, 2) < 0.75:
                y_a, y_b = (mid + 2, mid + 6) if side > 0 else (mid - 6, mid - 2)
                L = y_b - y_a if hsh(x, side, 3) < 0.7 else (y_b - y_a) // 2
                V.box(x, x, y_a, y_a + L, g - 1, g - 1, PLANK)
                V.box(x + 1, x + 1, y_a, y_a + L, g - 2, g - 1, PLANK_DK)
    # roof: slate over the west 40 %, bare rafters over the middle, open at the east
    zt = g - wh
    half = (y1 - y0 + 3) // 2
    xs_roof = int(x0 + (x1 - x0) * 0.42)
    xs_raft = int(x0 + (x1 - x0) * 0.78)
    for i in range(half):
        z = zt - i
        for x in range(x0 - 1, xs_raft):
            solid_part = x <= xs_roof
            for y in (y0 - 1 + i, y1 + 1 - i):
                if solid_part or (x - x0) % 3 == 0:
                    V.put(x, y, z, ROOF_DK if solid_part else TIMBER)
        if i > 0:
            for y in range(y0 - 1 + i + 1, y1 + 1 - i):
                V.put_air(x0, y, z, STONE)
    for x in range(x0 + 1, xs_raft, 3):                                   # tie beams (below any erosion)
        V.box(x, x, y0 + 1, y1 - 1, zt + 4, zt + 4, TIMBER)
    # snow drifts + rubble where the roof is open
    for x in range(xs_roof + 2, x1 - 1):
        for y in range(y0 + 2, y1 - 1):
            if hsh(x // 2, y // 2, 11) < 0.25:
                V.put_air(x, y, g - 1, SNOW)
            elif hsh(x, y, 12) < 0.05:
                V.put_air(x, y, g - 1, STONE_DK)
    # bell tower at the NE corner: 6x6, spiral stair (12 per loop), belfry with bell
    tx, ty = x1 - 5, y0 - 5
    TH = 20
    V.box(tx, tx + 5, ty, ty + 5, g, g, STONE_DK)
    for z in range(g - TH, g):
        for i in range(6):
            for (wx, wy) in ((tx + i, ty), (tx + i, ty + 5), (tx, ty + i), (tx + 5, ty + i)):
                V.put(wx, wy, z, STONE if hsh(wx, wy, z) < 0.85 else STONE_DK)
    V.box(tx + 2, tx + 3, ty + 5, ty + 5, g - 4, g - 1, AIR)                 # opening into the nave side
    V.box(tx + 2, tx + 3, ty + 6, ty + 6, g - 4, g - 1, AIR)
    V.box(tx + 5, tx + 5, ty + 2, ty + 3, g - 4, g - 1, AIR)                 # outside door (east)
    ring = [(tx + 1, ty + 1), (tx + 2, ty + 1), (tx + 3, ty + 1), (tx + 4, ty + 1), (tx + 4, ty + 2),
            (tx + 4, ty + 3), (tx + 4, ty + 4), (tx + 3, ty + 4), (tx + 2, ty + 4), (tx + 1, ty + 4),
            (tx + 1, ty + 3), (tx + 1, ty + 2)]
    zb = TH - 4
    for k in range(1, zb + 1):
        px, py = ring[(k + 7) % 12]
        V.box(px, px, py, py, g - k, g - k + 1, STONE_DK)
    V.box(tx + 1, tx + 4, ty + 1, ty + 4, g - zb, g - zb, PLANK)
    for k in range(zb - 2, zb + 1):
        px, py = ring[(k + 7) % 12]
        V.put(px, py, g - zb, AIR)
    for (wx, wy) in ((tx + 2, ty), (tx + 3, ty), (tx + 2, ty + 5), (tx + 3, ty + 5), (tx, ty + 2), (tx, ty + 3),
                     (tx + 5, ty + 2), (tx + 5, ty + 3)):
        V.box(wx, wx, wy, wy, g - TH + 1, g - zb - 1, AIR)                   # belfry arches
    V.box(tx + 2, tx + 3, ty + 2, ty + 3, g - TH + 2, g - TH + 3, IRON)     # bell
    V.box(tx + 2, tx + 3, ty + 2, ty + 3, g - TH + 4, g - TH + 4, SILVER)
    V.box(tx + 2, tx + 3, ty + 2, ty + 3, g - TH + 1, g - TH + 1, TIMBER)
    for i in range(0, 4):                                                    # spire cap
        V.box(tx - 0 + i, tx + 5 - i, ty + i, ty + 5 - i, g - TH - i, g - TH - i, ROOF_DK)
    V.put(tx + 2, ty + 2, g - TH - 4, SILVER); V.put(tx + 2, ty + 2, g - TH - 5, SILVER)
    return {'tower': (tx, ty), 'mid': mid}


# ================================================================== mine

def ore_cart(V, x, y, g, along_x=True, load=ORE):
    L, W = (4, 3) if along_x else (3, 4)
    V.box(x, x + L - 1, y, y + W - 1, g - 3, g - 2, IRON_DK)
    V.box(x + 1, x + L - 2, y + 1, y + W - 2, g - 3, g - 3, load)
    if along_x:
        for wx in (x, x + L - 1):
            V.put(wx, y - 1, g - 1, IRON); V.put(wx, y + W, g - 1, IRON)
        V.box(x, x + L - 1, y + 1, y + 1, g - 1, g - 1, IRON_DK)
    else:
        for wy in (y, y + L - 1):
            V.put(x - 1, wy, g - 1, IRON); V.put(x + W, wy, g - 1, IRON)
        V.box(x + 1, x + 1, y, y + L - 1, g - 1, g - 1, IRON_DK)
    V.put_air(x + 1, y + 1, g - 4, SILVER)


def mine_frame(V, x, y0, y1, z_floor, h=5):
    """Timber shoring frame across a tunnel running along x: posts at y0 / y1, cap beam on top."""
    V.box(x, x, y0, y0, z_floor - h, z_floor - 1, TIMBER)
    V.box(x, x, y1, y1, z_floor - h, z_floor - 1, TIMBER)
    V.box(x, x, y0, y1, z_floor - h, z_floor - h, TIMBER)


def headframe(V, x, y, g, rng, h=22):
    """Timber pithead over a capped shaft: two vertical legs, back braces, sheave wheel, cable, collar."""
    V.reserve(x - 5, x + 5, y - 9, y + 4, pad=1)
    V.box(x - 3, x + 3, y - 3, y + 3, g, g, TIMBER)                       # collar + grating
    for i in range(-2, 3):
        for j in range(-2, 3):
            V.put(x + i, y + j, g, IRON_DK if (i + j) % 2 else PLANK_DK)
    V.box(x - 3, x + 3, y - 3, y + 3, g - 1, g - 1, AIR)
    for (i, j) in ((-3, -3), (3, -3), (-3, 3), (3, 3)):
        V.put(x + i, y + j, g - 1, TIMBER)
    for sx in (-3, 3):
        V.box(x + sx, x + sx, y, y, g - h, g - 1, LOG_DK)
        V.line4((x + sx, y - 8, g - 1), (x + sx, y, g - h + 3), LOG_DK)
        for k in range(4, h - 2, 5):
            V.box(x - 3, x + 3, y, y, g - k, g - k, TIMBER)
        V.line4((x + sx, y - 8, g - 1), (x + sx, y - 8, g - 2), LOG_DK)
    V.box(x - 3, x + 3, y, y, g - h, g - h, LOG)
    # sheave wheel (ring in the y-z plane) + cable
    cz = g - h - 4
    pts = [(x, int(round(y + 3 * math.cos(a * math.pi / 8))), int(round(cz + 3 * math.sin(a * math.pi / 8))))
           for a in range(17)]
    for p0, p1 in zip(pts[:-1], pts[1:]):
        V.line4(p0, p1, IRON)
    V.box(x, x, y, y, cz, g - h - 1, IRON_DK)                               # axle post to the cap beam
    V.line4((x, y - 3, cz), (x, y + 3, cz), IRON_DK)                         # spokes
    V.line4((x, y, cz - 3), (x, y, cz + 3), IRON_DK)
    V.box(x, x, y + 3, y + 3, cz, g - 2, ROPE)
    V.box(x - 1, x + 1, y + 3, y + 3, g - 3, g - 2, IRON_DK)                # cage hanging over the shaft
    hanging_lantern(V, x - 3, y + 1, g - h + 4, drop=1)
    hanging_lantern(V, x + 3, y + 1, g - h + 4, drop=1)


def portal(V, x, y0, y1, z_floor, rng, h=5, sign_dir=1):
    """Timber mine portal at the tunnel mouth (posts y0 / y1, lintel, sign, lanterns)."""
    for px in (x, x + sign_dir):
        V.box(px, px, y0 - 1, y0 - 1, z_floor - h - 1, z_floor - 1, LOG_DK)
        V.box(px, px, y1 + 1, y1 + 1, z_floor - h - 1, z_floor - 1, LOG_DK)
        V.box(px, px, y0 - 1, y1 + 1, z_floor - h - 1, z_floor - h - 1, LOG)
    sx = x + 2 * sign_dir
    V.box(sx, sx, y0 + 1, y1 - 1, z_floor - h - 3, z_floor - h - 2, PLANK)
    V.box(sx, sx, y0 + 2, y1 - 2, z_floor - h - 3, z_floor - h - 3, SILVER)
    V.box(x, x, y0, y1, z_floor - h - 2, z_floor - h - 2, LOG_DK)
    hanging_lantern(V, x + sign_dir, y0, z_floor - h - 1, drop=1)
    hanging_lantern(V, x + sign_dir, y1, z_floor - h - 1, drop=1)
