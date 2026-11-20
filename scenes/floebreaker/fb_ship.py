"""The icebreaker: N-S axis, bow north (y 58), stern south (y 170), centre line x = 255.5.

Hull sides stand 10 above the ice plain (ground surface z 59). Hold = air z 50..58 on the ice floor; main deck slab z 49.
Stern superstructure: three levels (floors z 49 / 43 / 37, roof z 31) with corridors, cabins, doors, windows, stairs.
Every room is entered through real openings; stairs rise 1 per voxel.
"""
from __future__ import annotations

import numpy as np

from fb_core import MAT

CX = 255.5
Y_BOW, Y_STERN = 58, 170
G = 59            # ice-plain surface
DECK = 49


def hb(y):
    """Half-beam of the hull at row y (bow taper, full beam from y >= 100)."""
    if y >= 100:
        return 12.0
    t = min(max((100 - y) / 42.0, 0.0), 1.0)
    return max(1.0, 12.0 * (1 - t ** 1.7) ** 0.5)


def inside(x, y):
    return abs(x - CX) <= hb(y) + 0.5 and Y_BOW <= y <= Y_STERN


def build_ship(W, H):
    m = W.m
    glow = W.glow
    # ---- flatten the ship pad (ground exactly G within the footprint + 10 apron)
    for y in range(Y_BOW - 6, Y_STERN + 8):
        for x in range(228, 284):
            d = max(0, abs(x - CX) - hb(min(max(y, Y_BOW), Y_STERN)))
            if d < 12:
                h0 = int(H[x, y])
                if h0 < G:
                    m[x, y, h0:G] = 0
                elif h0 > G and h0 < 62:
                    m[x, y, G:h0] = MAT['pack']
                m[x, y, G] = MAT['pack'] if d < 11 else m[x, y, G]
                H[x, y] = min(h0, G) if h0 <= G else G
    # ---- hull shell
    for y in range(Y_BOW, Y_STERN + 1):
        for x in range(240, 272):
            if not inside(x, y):
                continue
            edge = (not inside(x - 1, y)) or (not inside(x + 1, y)) or (not inside(x, y - 1)) or (not inside(x, y + 1))
            edge2 = edge or (not inside(x - 2, y)) or (not inside(x + 2, y)) or (not inside(x, y - 2)) \
                or (not inside(x, y + 2)) or y >= Y_STERN - 1
            m[x, y, DECK] = MAT['deck']
            if edge2:                                  # 2-thick plating
                m[x, y, 50:55] = MAT['hull_red']
                m[x, y, 55:59] = MAT['hull_black']
                m[x, y, 59] = MAT['hull_black']
            else:                                      # hold interior
                m[x, y, 50:59] = 0
                if m[x, y, 59] == 0:
                    m[x, y, 59] = MAT['pack']
            if edge:                                   # bulwark (rail) with gaps every 6 voxels for scuppers
                if (x + y) % 6 != 0:
                    m[x, y, 48] = MAT['hull_grey']
                else:
                    m[x, y, 48] = 0
    # ---- hull doors into the hold (4 wide x 4 high, floor = ice plain) both sides
    for y0 in (96, 126):
        for x in (243, 244, 245, 246, 265, 266, 267, 268):
            m[x, y0:y0 + 4, 55:59] = 0
    # ---- gangways (wooden stairs up the hull side to the deck), notch in the bulwark
    for side in (-1, +1):
        ya, yb = 112, 115
        W.stairs(ya, yb, 233 if side < 0 else 278, G, DECK, '+x' if side < 0 else '-x', 'plank')
        for x in (243, 244, 245, 266, 267, 268):
            m[x, ya:yb + 1, 46:49] = 0
        for k in range(1, 10):
            xx = (233 + k - 1) if side < 0 else (278 - (k - 1))
            for yy in (ya - 1, yb + 1):
                m[xx, yy, G - k - 1:G + 1] = MAT['steel']
    # ---- hatches from the deck to the hold (10-tread stairs along +y, 4 wide)
    # hold hatch 1 (foredeck) and hatch 2 (midship); 10-tread stair, 4 wide
    W.stairs(253, 256, 84, G, DECK, '+y', 'dsteel')
    W.stairs(253, 256, 114, G, DECK, '+y', 'dsteel')
    # coaming around hatch heads
    for y0 in (84, 114):
        m[252, y0:y0 + 10, 48] = MAT['yellow']; m[257, y0:y0 + 10, 48] = MAT['yellow']
    # ---- hold furnishing: pillars, lamps, crates, engine block
    for y in range(92, 164, 14):
        for x in (248, 262):
            if inside(x, y) and inside(x - 2, y):
                m[x:x + 2, y:y + 2, 50:59] = MAT['dsteel']
                m[x:x + 2, y:y + 2, 58] = MAT['dsteel']
    for y in range(90, 166, 8):
        for x in (254, 257):
            if m[x, y, 50] == 0 and m[x, y, DECK] != 0:
                m[x, y, 50] = MAT['lamp']; glow.append((x, y, 50))
    # engine block with orange pipes (stern part of the hold), leaving aisles
    W.box(248, 251, 144, 156, 55, 58, 'dsteel'); W.box(260, 263, 144, 156, 55, 58, 'dsteel')
    for y in range(145, 156, 3):
        W.box(248, 263, y, y, 54, 54, 'orange')
    for (x, y) in ((250, 100), (261, 104), (251, 124), (260, 120), (252, 160), (259, 160)):
        W.box(x, x + 2, y, y + 2, 57, 58, 'plank'); W.box(x, x + 1, y, y + 1, 56, 56, 'plank')
    # ---- stern superstructure
    SX0, SX1, SY0, SY1 = 247, 264, 128, 156
    floors = [49, 43, 37]
    for i, zf in enumerate(floors):
        zc = zf - 6
        W.room(SX0, SX1, SY0, SY1, zf, zc, 'white')
        # interior layout: corridor x 254..257; partitions at x 253/258
        for x in (253, 258):
            W.box(x, x, SY0 + 1, SY1 - 1, zc + 1, zf - 1, 'white')
        # doors from corridor into rooms (2 wide, 3 high) every 7 along y
        yy = SY0 + 3
        while yy < SY1 - 2:
            for x in (253, 258):
                W.carve(x, x, yy, yy + 1, zf - 3, zf - 1)
            # room dividers
            for x0, x1 in ((SX0 + 1, 252), (259, SX1 - 1)):
                W.box(x0, x1, yy + 3, yy + 3, zc + 1, zf - 1, 'white')
                W.carve(x0 + 1, x0 + 2, yy + 3, yy + 3, zf - 3, zf - 1)     # door between neighbouring cabins
            yy += 7
        # windows: 2 wide x 2 high openings along both long walls and the ends
        for y in range(SY0 + 2, SY1 - 1, 4):
            for x in (SX0, SX1):
                W.carve(x, x, y, y + 1, zf - 3, zf - 2)
        for x in range(SX0 + 3, SX1 - 2, 4):
            for y in (SY0, SY1):
                W.carve(x, x + 1, y, y, zf - 3, zf - 2)
        # cabin furniture: bunk + table + warm lamp, per room (keeps every room occupied)
        yy = SY0 + 2
        while yy + 5 < SY1:
            for x in (248, 260):
                if zf == 49 or zf == 43 or zf == 37:
                    W.box(x, x + 1, yy, yy + 2, zf - 1, zf - 1, 'plank')           # bunk
                    W.box(x + 2, x + 2, yy + 1, yy + 1, zf - 2, zf - 1, 'dwood')   # table leg
                    pt = (x + (3 if x == 248 else -1), yy, zc + 1)
                    W.pt(pt[0], pt[1], pt[2], 'lamp')
            yy += 7
    # exterior doors on level A (both long walls near the stern end) + stern door
    for x in (SX0, SX1):
        W.carve(x, x, 144, 145, 46, 48)
    W.carve(255, 256, SY1, SY1, 46, 48)
    # stairs: F1 A->B and F3 C->roof along +y at the north end, F2 B->C along -y at the south end (4 wide)
    W.stairs(254, 257, 138, 49, 43, '-y', 'steel')
    W.stairs(254, 257, 146, 43, 37, '+y', 'steel')
    W.stairs(254, 257, 138, 37, 31, '-y', 'steel')
    # bridge wings: wider glazed bridge on level C, projecting 2 voxels each side
    for x0, x1 in ((SX0 - 3, SX0), (SX1, SX1 + 3)):
        W.room(x0, x1, SY0 + 1, SY0 + 10, 37, 31, 'white')
        W.carve(x0 + 1, x1 - 1, SY0 + 2, SY0 + 9, 32, 36)
        for y in range(SY0 + 3, SY0 + 9, 3):
            W.carve(x0, x0, y, y + 1, 33, 35) if x0 < SX0 else W.carve(x1, x1, y, y + 1, 33, 35)
        # wall between wing and bridge deck opened (3 wide)
        xx = SX0 if x0 < SX0 else SX1
        W.carve(xx, xx, SY0 + 4, SY0 + 6, 34, 36)
    # roof deck rails, funnel, mast, radar
    for x in range(SX0, SX1 + 1):
        for y in (SY0, SY1):
            if (x + y) % 3: m[x, y, 30] = MAT['steel']
    for y in range(SY0, SY1 + 1):
        for x in (SX0, SX1):
            if (x + y) % 3: m[x, y, 30] = MAT['steel']
    W.room(251, 260, 140, 149, 31, 18, 'hull_red')                    # funnel stack (hollow)
    W.box(251, 260, 140, 149, 18, 20, 'hull_black'); W.carve(252, 259, 141, 148, 19, 20)
    W.carve(251, 251, 144, 145, 28, 30)                                # service door in the stack
    W.pt(255, 145, 19, 'lamp')
    W.box(255, 256, 133, 134, 9, 30, 'steel')                         # mast
    W.box(251, 260, 133, 133, 14, 14, 'steel'); W.box(253, 258, 133, 133, 20, 20, 'steel')
    W.box(254, 257, 131, 132, 8, 9, 'orange')                         # radar bar
    W.pt(255, 133, 8, 'lamp'); glow.append((255, 133, 8))
    # ---- deck gear: gantry crane, containers, windlass, bow mast, life rings
    for x in (246, 265):                                              # crane posts + beam
        W.box(x, x, 100, 100, 38, 48, 'yellow')
    W.box(246, 265, 100, 100, 37, 38, 'yellow')
    W.box(255, 256, 101, 101, 38, 45, 'dsteel')
    for i, (x0, y0) in enumerate(((247, 104), (260, 104), (247, 115), (260, 115))):
        zt = 44
        mid = ['cont_r', 'cont_g', 'cont_b', 'cont_y'][i]
        W.room(x0, x0 + 4, y0, y0 + 8, 48, zt, mid)
        W.carve(x0 + 1, x0 + 3, y0 + 8, y0 + 8, 45, 48)               # open door end faces the stern
        W.pt(x0 + 2, y0 + 4, zt + 1, 'lamp'); glow.append((x0 + 2, y0 + 4, zt + 1))
    W.box(254, 257, 72, 74, 44, 48, 'dsteel')                         # windlass
    W.box(255, 256, 64, 65, 34, 48, 'steel')                          # bow mast
    W.box(253, 258, 65, 65, 40, 40, 'steel')
    W.pt(255, 64, 34, 'lamp'); glow.append((255, 64, 34))
    for (x, y) in ((246, 140), (265, 140), (246, 110), (265, 110)):    # life rings
        W.pt(x, y, 47, 'orange')
    W.marks['ship'] = {'x': (244, 267), 'y': (Y_BOW, Y_STERN), 'deck_z': DECK, 'roof_z': 31, 'mast_top_z': 8}
    # helipad on the aft deck (painted by material)
    for y in range(158, 169):
        for x in range(248, 264):
            r = np.hypot(x - CX, y - 163.5)
            if 4.5 <= r <= 6.2:
                m[x, y, DECK] = MAT['orange']
    for y in range(160, 168):
        for x in (251, 252, 259, 260):
            m[x, y, DECK] = MAT['orange']
    for x in range(251, 261):
        m[x, 163, DECK] = MAT['orange']
    return m
