"""Cursed Skull Reef one-offs, placed AFTER the mirror (each one is a cosmetic asymmetric box):

  ruined tavern     Blue NW shore, on stilts over the water    two storeys, broken corner, sign, boardwalk
  lighthouse stump  Red NE shore                              round stone tower, spiral stair to a broken lamp deck
  rum-barrel dock   Blue south chain (S1)                     dock warehouse, barrel pyramids, a jib crane, lamps
  gallows           Red south chain (S1)                      scaffold with a stair, crossbeam, nooses, crow cage
  heeled-over brig  north chain middle islet (M), off the axis brig lying on its side, enterable, broken mast

Pairs are balanced by role: each team has one tall landmark on its outer shore (tavern / lighthouse) and one on the
first south-chain islet (rum dock / gallows). Colours are graybox material colours; csr_art paints them.
"""
from __future__ import annotations

import math

import numpy as np

from aosmap.kit.structures import spiral_stair, straight_stair

from csr_build import GC, barrels, box, col_down, house, put, top, windows_on


def tavern(cv, rep, S):
    cx, cy = S['tavern']
    x0, x1, y0, y1 = cx - 12, cx + 5, cy - 7, cy + 6
    house(cv, rep, 'ruined tavern', x0, x1, y0, y1, 2, 'x', 'E', 'corner', stilt_floor=56)
    # wrap-around boardwalk (deck z 56) on the south side, posts to the seabed, with a stair to the shore
    for x in range(x0 - 1, x1 + 2):
        for y in (y1 + 1, y1 + 2):
            if top(cv, x, y) > 56:
                put(cv, x, y, 56, 'plank')
                if x % 3 == 0:
                    col_down(cv, x, y, 57, 'post')
    # hanging sign on a bracket by the door, barrels on the boardwalk
    box(cv, x1 + 1, x1 + 3, cy + 3, cy + 3, 46, 46, "timber")            # bracket out of the wall
    box(cv, x1 + 3, x1 + 3, cy + 3, cy + 3, 47, 47, "rope")
    box(cv, x1 + 3, x1 + 3, cy + 2, cy + 4, 48, 50, "plank")
    rep['tavern_lamps'] = [(x1 + 1, cy + 1, 51), (x0 - 1, y1 + 1, 55), (x1 + 1, y1 + 2, 55)]
    return [x0 - 3, x1 + 9, y0 - 3, y1 + 4]


def lighthouse(cv, rep, S):
    cx, cy = S['lighthouse']
    g = min(top(cv, cx + a, cy + b) for a in (-7, 0, 7) for b in (-7, 0, 7))
    g = min(g, 60)
    R = 6.5
    # plinth: level a disc at g, solid down
    for x in range(cx - 9, cx + 10):
        for y in range(cy - 9, cy + 10):
            if math.hypot(x - cx, y - cy) <= 8.5:
                cv.carve(x, x, y, y, 0, g - 1)
                box(cv, x, x, y, y, g, 63, 'stone_dk')
    ztop = 24
    cv.cylinder(cx, cy, R, ztop, g - 1, GC['stone'], 'stone', hollow=R - 1.6)
    # jagged broken crown
    for x in range(cx - 8, cx + 9):
        for y in range(cy - 8, cy + 9):
            a = math.atan2(y - cy, x - cx)
            drop = int(3 + 3 * math.sin(3 * a) + 2 * math.sin(7 * a + 1))
            if drop > 0:
                cv.carve(x, x, y, y, ztop, ztop + drop - 1)
    spiral_stair(cv, cx, cy, 30, g, r=4, c=GC['stair'], core=GC['stone_dk'], mat='stair')
    # lamp deck (ring at z 30) and the brazier on the core
    for x in range(cx - 6, cx + 7):
        for y in range(cy - 6, cy + 7):
            d = math.hypot(x - cx, y - cy)
            if 4.3 < d <= 5.2:
                put(cv, x, y, 30, 'plank')
    box(cv, cx - 1, cx, cy - 1, cy, 29, 29, 'iron')
    # door (west, facing the shore path) and slit windows
    cv.carve(cx - 7, cx - 5, cy - 1, cy + 1, g - 4, g - 1)
    for z in (g - 10, g - 18, g - 26):
        for (dx, dy) in ((6, 0), (0, 6), (0, -6)):
            cv.carve(cx + dx, cx + dx, cy + dy, cy + dy, z - 1, z)
    cv.interiors.append(['lighthouse stump base', cx - 3, cy, g])
    cv.interiors.append(['lighthouse lamp deck', cx + 5, cy, 30])
    rep['lighthouse'] = {'brazier': [(cx - 1, cy - 1, 28), (cx, cy, 28), (cx - 1, cy, 28), (cx, cy - 1, 28)],
                         'g': g}
    return [cx - 10, cx + 10, cy - 10, cy + 10]


def rum_dock(cv, rep, S):
    cx, cy = S['rum_dock']
    # dock warehouse (one room, door north) on the east side of the islet
    x0, x1, y0, y1 = cx + 4, cx + 17, cy - 4, cy + 6
    house(cv, rep, 'rum warehouse', x0, x1, y0, y1, 1, 'y', 'W')
    # jetty south-east into the sea with lamps, barrel pyramids along it
    lamps = rep.setdefault('oneoff_lamps', [])
    jy = cy + 9
    for x in range(cx - 6, cx + 26):
        for y in (jy, jy + 1, jy + 2):
            if top(cv, x, y) > 60:
                put(cv, x, y, 60, 'plank')
                col_down(cv, x, y, 61, 'post' if (x % 4 == 0 and y != jy + 1) else 'plank')
    for x in (cx + 2, cx + 14):
        yy = jy - 1
        col_down(cv, x, yy, 53, 'post')
        lamps.append((x, yy, 52))
    for (bx, by) in ((cx + 18, jy), (cx - 4, jy)):
        g = top(cv, bx, by)
        for lvl, n in enumerate((4, 3, 2)):
            for k in range(n):
                box(cv, bx + 2 * k + lvl, bx + 2 * k + lvl + 1, by, by + 1, g - 3 - 3 * lvl, g - 1 - 3 * lvl,
                    'barrel')
    # jib crane at the jetty end with a barrel net
    px, py = cx + 24, jy + 1
    for z in range(48, 60):
        put(cv, px, py, z, 'timber')
    for i in range(0, 7):
        put(cv, px - i, py, 48, 'timber')
    for z in range(49, 53):
        put(cv, px - 6, py, z, 'rope')
    box(cv, px - 7, px - 5, py - 1, py + 1, 53, 55, 'net')
    rep['rum_dock'] = {'jetty_y': jy}
    return [cx - 8, cx + 27, cy - 6, jy + 4]


def gallows(cv, rep, S):
    cx, cy = S['gallows']
    g = int(np.median([top(cv, cx + a, cy + b) for a in range(-6, 7, 3) for b in range(-4, 5, 2)]))
    x0, x1, y0, y1 = cx - 6, cx + 6, cy - 4, cy + 4
    fz = g - 5
    # level the site, scaffold floor on posts with a skirt of planks (an under-croft you can walk into)
    for x in range(x0 - 3, x1 + 8):
        for y in range(y0 - 3, y1 + 4):
            t = top(cv, x, y)
            if t < g:
                cv.carve(x, x, y, y, 0, g - 1)
            elif t > g:
                box(cv, x, x, y, y, g, t - 1, 'rock')
    box(cv, x0, x1, y0, y1, fz, fz, 'plank')
    for x in (x0, cx, x1):
        for y in (y0, y1):
            box(cv, x, x, y, y, fz + 1, g - 1, 'post')
    for x in range(x0, x1 + 1):                                            # skirt on the north side only
        if x % 2:
            box(cv, x, x, y0, y0, fz + 1, g - 2, 'plank')
    # stair up the east side (rising west), rail posts
    straight_stair(cv, x1 + 5, y0 + 1, y0 + 3, g, 5, -1, GC['stair'], 'stair')
    for i in range(1, 6):
        for y in range(y0 + 1, y0 + 4):
            col_down(cv, x1 + 5 - (i - 1), y, g - i + 1, 'stair')
    # trap door, uprights, crossbeam, nooses, crow cage
    cv.carve(cx - 2, cx + 1, cy, cy + 1, fz, fz)
    for x in (x0 + 1, x1 - 1):
        for z in range(fz - 9, fz):
            put(cv, x, cy + 3, z, 'timber')
    box(cv, x0 + 1, x1 - 1, cy + 3, cy + 3, fz - 9, fz - 9, 'timber')
    for x in (cx - 2, cx + 1):
        for z in range(fz - 8, fz - 5):
            put(cv, x, cy + 3, z, 'rope')
    for z in range(fz - 8, fz - 4):
        for (a, b) in ((0, 0), (2, 0), (0, 2), (2, 2)):
            put(cv, x1 - 3 + a, cy + 1 + b, z, 'cage') if (a, b) != (0, 0) or z > fz - 7 else None
    box(cv, x1 - 3, x1 - 1, cy + 1, cy + 3, fz - 9, fz - 9, 'cage')
    box(cv, x1 - 3, x1 - 1, cy + 1, cy + 3, fz - 4, fz - 4, 'cage')
    cv.interiors.append(['gallows scaffold', cx - 3, cy - 2, fz])
    rep['gallows'] = {'lamps': [(x0 + 1, cy + 2, fz - 9)], 'fz': fz}
    return [x0 - 4, x1 + 7, y0 - 4, y1 + 4]


def heeled_brig(cv, rep, S):
    """A brig lying on its side beside the north chain's middle islet: keel along x on the sea floor, deck turned
    toward the islet (heel 68 degrees), a flat plank floor inside, two hatches in the deck as doors with rubble steps
    from the beach, the mainmast lying out over the islet."""
    cx, cy = S['heeled_brig']
    L, hb, D = 46, 6, 10
    xa = cx - L // 2
    th = math.radians(-68)
    ct, st = math.cos(th), math.sin(th)
    yk = cy - 4

    def half(u):
        nb = 0.3 * L
        if u < nb:
            return hb * (0.3 + 0.7 * math.sqrt(u / nb))
        return hb * (0.9 if u > L - 3 else 1.0)
    floor_cells = []
    for u in range(L):
        h = half(u)
        x = xa + u
        for y in range(yk - 14, yk + 16):
            for up in range(0, 16):
                z = 62 - up
                dy = y - yk
                v = dy * ct + up * st
                w = -dy * st + up * ct
                if not (0 <= w <= D and abs(v) <= h + 0.3):
                    continue
                shell = abs(v) > h - 1.1 or w < 1.1 or w > D - 1.1 or u == 0 or u == L - 1
                if shell:
                    put(cv, x, y, z, 'deck' if w > D - 1.1 else 'hull')
                elif up < 2:
                    put(cv, x, y, z, 'plank')                     # ballast under the floor: no bilge pockets
                else:
                    cv.clear(x, y, z)
                    if up == 2:
                        floor_cells.append((x, y))
    for (x, y) in floor_cells:
        put(cv, x, y, 60, 'plank')
    fy = [y for (_, y) in floor_cells]
    ymin, ymax = (min(fy), max(fy)) if fy else (yk, yk)
    # hatches (doors) through the deck side facing the islet, with rubble steps from the beach
    for ux in (14, 31):
        x = xa + ux
        for y in range(ymax - 2, ymax + 8):
            for z in range(56, 60):
                if cv.solid[x, y, z] or cv.solid[x + 1, y, z] or cv.solid[x + 2, y, z]:
                    cv.carve(x, x + 2, y, y, 56, 59)
        for y in range(ymax + 1, ymax + 9):
            for xx in (x, x + 1, x + 2):
                t = top(cv, xx, y)
                if t > 60:
                    zr = 62 if y > ymax + 5 else (61 if y > ymax + 3 else 60)
                    if t > zr:
                        box(cv, xx, xx, y, y, zr, 63, 'plank')
    # sand bar along the deck side so no water pocket sits under the leaning deck (swimmers could not climb out)
    for x in range(xa - 1, xa + L + 1):
        for y in range(ymin - 2, ymax + 10):
            if top(cv, x, y) >= 63:
                box(cv, x, x, y, y, 62, 63, 'sand')
    # mainmast lying out across the islet (from the deck side), cut where it meets the ground
    mx = xa + 22
    for k in range(0, 26):
        y = ymax + 2 + k
        z = 57 - k // 4
        if z >= top(cv, mx, y):
            break
        box(cv, mx, mx + 1, y, y, z, z, 'mast')
        if k % 7 == 3:
            box(cv, mx - 3, mx + 4, y, y, z, z, 'mast')
    cv.interiors.append(['heeled brig hold', xa + L // 2, (ymin + ymax) // 2, 60])
    rep['heeled_brig'] = {'lamps': [(xa + 2, ymax + 1, 57), (xa + L - 3, ymax + 1, 57)], 'floor_y': (ymin, ymax)}
    return [xa - 2, xa + L + 2, yk - 15, ymax + 30]


def build(cv, rep, S, rng, art=True):
    boxes = []
    out = {}
    for name, fn in (('tavern', tavern), ('lighthouse', lighthouse), ('rum_dock', rum_dock), ('gallows', gallows),
                     ('heeled_brig', heeled_brig)):
        b = fn(cv, rep, S)
        boxes.append(b)
        out[name] = b
    out['boxes'] = boxes
    return out
