"""Frozen Icebreaker: the beset icebreaker (one-off landmark, drawn after the mirror, cosmetic-asymmetric box).

Hull x 184-328 along x (stern west, bow east), centre line y 176, beam 23 (kept under the 25-column window that
craft_checks uses to find ground, so the vessel is graded as an object). Everything is enterable:

  hold        floor z 61 (below the ice; the blue-ice tunnels from both north flanks come in here)
  tween deck  floor z 53 (one step up from the ice through the crushed-hull breaches)
  main deck   floor z 44 (four accommodation ladders from the ice), forecastle deck z 39 with a store below
  superstructure A / B / C decks z 44 / 39 / 34, boat deck z 29 (funnel, lifeboats), bridge z 29, roof z 24
  helideck    z 39 aft, with a parked helicopter
"""
from __future__ import annotations

import math

from aosmap.kit import structures
from fi_struct import ice_block
from fi_world import boxm, put, lamp, reg, tone

CY = 176
X0, X1 = 184, 328
DECK = 44
TWEEN = 53
HOLD = 61
FC = 39            # forecastle deck
FC_X = 296


def halfbeam(x):
    if x < X0 or x > X1:
        return 0.0
    if x < 196:
        t = (196 - x) / 12.5
        return 11.0 * math.sqrt(max(0.0, 1 - t * t))
    if x <= 292:
        return 11.0
    t = (x - 292) / 36.0
    return 11.0 * (1 - t ** 1.6) if t < 1 else 0.0


def yspan(x):
    b = halfbeam(x)
    if b < 1.5:
        return None
    return int(math.ceil(CY - b)), int(math.floor(CY + b))


def _hull_colour(z, deck_z):
    if z <= deck_z - 2:
        return 'sheer' if z == deck_z - 2 else 'hull'
    if z <= 50:
        return 'hull'
    if z <= 53:
        return 'hull_band'
    return 'rust'


def hull(cv):
    for x in range(X0, X1 + 1):
        sp = yspan(x)
        if sp is None:
            continue
        ya, yb = sp
        dz = FC if x >= FC_X else DECK
        for y in range(ya, yb + 1):
            wall = y <= ya + 1 or y >= yb - 1 or x <= X0 + 1 or yspan(x - 2) is None or yspan(x + 2) is None
            if wall:
                for z in range(dz - 2, HOLD + 1):
                    put(cv, x, y, z, _hull_colour(z, dz), 'ship', salt=x // 4)
            else:
                cv.carve(x, x, y, y, 0, HOLD - 1)
                put(cv, x, y, dz, 'deck', 'ship')
                if dz == FC:
                    put(cv, x, y, DECK, 'deck', 'ship')
                put(cv, x, y, TWEEN, 'plank', 'ship')
                put(cv, x, y, HOLD, 'steel', 'ship')
    # freeing ports in the bulwark (2 wide, every 12)
    for x in range(200, 292, 12):
        for y in (yspan(x)[0], yspan(x)[1]):
            cv.carve(x, x + 1, min(y, y + 1), max(y, y + 1), DECK - 1, DECK - 1)
    # portholes along the tween deck (1 x 1 through both wall columns), every 4
    for x in range(198, 294, 4):
        ya, yb = yspan(x)
        cv.carve(x, x, ya, ya + 1, 48, 48)
        cv.carve(x, x, yb - 1, yb, 48, 48)
    # forecastle front bulkhead with a doorway, and the store room below the forecastle deck
    sp = yspan(FC_X)
    boxm(cv, FC_X, FC_X, sp[0] + 2, sp[1] - 2, FC + 1, DECK - 1, 'super', 'ship', 'course')
    cv.carve(FC_X, FC_X, CY - 1, CY + 1, DECK - 3, DECK - 1)
    boxm(cv, FC_X, FC_X, CY - 2, CY - 2, DECK - 4, DECK - 1, 'trim', 'ship')
    boxm(cv, FC_X, FC_X, CY + 2, CY + 2, DECK - 4, DECK - 1, 'trim', 'ship')


def bulkheads(cv):
    """Tween-deck bulkheads with doorways (rooms), hold cargo, engines, lamps, stairs between the decks."""
    for bx in (230, 266):
        ya, yb = yspan(bx)
        boxm(cv, bx, bx, ya + 2, yb - 2, DECK + 1, TWEEN - 1, 'steel', 'ship', 'course')
        cv.carve(bx, bx, CY - 2, CY + 1, TWEEN - 4, TWEEN - 1)
        boxm(cv, bx, bx, ya + 2, yb - 2, TWEEN + 1, HOLD - 1, 'steel', 'ship', 'course')
        cv.carve(bx, bx, CY - 2, CY + 1, HOLD - 4, HOLD - 1)
    # engines in the aft hold: two long diesel blocks with cylinder heads and a walkway between them
    for yy in (169, 180):
        boxm(cv, 198, 226, yy, yy + 2, HOLD - 3, HOLD - 1, 'dsteel', 'ship')
        for x in range(200, 225, 4):
            boxm(cv, x, x + 1, yy, yy + 2, HOLD - 4, HOLD - 4, 'hull_band', 'ship')
    # hold cargo: crate stacks and drums (fore hold), clear lanes
    for (x, y) in ((242, 181), (248, 181), (272, 181), (280, 181), (288, 168)):
        boxm(cv, x, x + 3, y, y + 3, HOLD - 3, HOLD - 1, 'plank', 'ship', 'course')
        boxm(cv, x, x + 3, y, y + 3, HOLD - 3, HOLD - 3, 'beam', 'ship')
    for (x, y) in ((256, 169), (258, 169), (256, 181), (300, 175)):
        boxm(cv, x, x, y, y + 1, HOLD - 3, HOLD - 1, 'drum_y', 'ship')
    # tween-deck furniture: mess tables, bunks, lockers
    for x in (236, 244, 252):
        boxm(cv, x, x + 3, CY - 4, CY - 3, TWEEN - 2, TWEEN - 2, 'furn', 'ship')
        boxm(cv, x, x, CY - 4, CY - 4, TWEEN - 1, TWEEN - 1, 'furn', 'ship')
    for x in range(272, 292, 5):
        boxm(cv, x, x + 2, yspan(x)[1] - 3, yspan(x)[1] - 2, TWEEN - 1, TWEEN - 1, 'canvas_k', 'ship')
        boxm(cv, x, x + 2, yspan(x)[1] - 3, yspan(x)[1] - 2, TWEEN - 4, TWEEN - 4, 'canvas_k', 'ship')
    for x in range(200, 228, 5):
        boxm(cv, x, x + 1, yspan(x)[0] + 2, yspan(x)[0] + 2, TWEEN - 3, TWEEN - 1, 'container_s', 'ship')
    # ceiling lamps
    for x in range(200, 296, 10):
        lamp(cv, x, CY, TWEEN + 1, 'warm')
        lamp(cv, x, CY, DECK + 1, 'warm')
    # stairs: hold -> tween (2), tween -> main deck (2: one aft companionway, one in the open fore hatch)
    st = tone('steel', 0, 0, 0)
    structures.straight_stair(cv, 214, CY + 1, CY + 2, HOLD, HOLD - TWEEN, 1, st, 'ship')
    structures.straight_stair(cv, 290, CY - 2, CY - 1, HOLD, HOLD - TWEEN, -1, st, 'ship')
    structures.straight_stair(cv, 236, CY + 4, CY + 5, TWEEN, TWEEN - DECK, 1, st, 'ship')
    structures.straight_stair(cv, 287, CY - 1, CY, TWEEN, TWEEN - DECK, -1, st, 'ship')


def breaches(cv):
    """Crushed-hull breaches at ice level into the tween deck (one step up), with torn plate edges."""
    out = []
    for bx in (222, 290):
        for side in (0, 1):
            ya, yb = yspan(bx)
            ys = (ya, ya + 1) if side == 0 else (yb - 1, yb)
            cv.carve(bx, bx + 3, ys[0], ys[1], TWEEN - 4, TWEEN - 1)
            cv.carve(bx + 1, bx + 2, ys[0], ys[1], TWEEN - 5, TWEEN - 5)          # torn top edge
            for x in (bx - 1, bx + 4):
                put(cv, x, ys[0], TWEEN - 2, 'rust', 'ship')
            out.append((bx, ys))
    return out


def gangways(cv):
    """Accommodation ladders from the ice to the main deck, both sides, west and east halves (rise 10)."""
    st = tone('plank', 0, 0, 0)
    for (x0, dx) in ((204, 1), (290, -1)):
        for side in (0, 1):
            land_x = x0 + 10 * dx
            ya, yb = yspan(land_x)
            if side == 0:
                yy = (ya - 2, ya - 1)
                wall = (ya, ya + 1)
            else:
                yy = (yb + 1, yb + 2)
                wall = (yb - 1, yb)
            structures.straight_stair(cv, x0, yy[0], yy[1], 54, 10, dx, st, 'ship')
            for lx in (land_x, land_x + dx):
                boxm(cv, lx, lx, yy[0], yy[1], DECK, DECK, 'plank', 'ship')
                boxm(cv, lx, lx, yy[0], yy[1], DECK + 1, 53, 'beam', 'ship')
                cv.carve(lx, lx, wall[0], wall[1], DECK - 4, DECK - 1)
                boxm(cv, lx, lx, wall[0], wall[1], DECK, DECK, 'deck', 'ship')
            # hand rail posts along the outer edge of the ladder
            oy = yy[0] - 1 if side == 0 else yy[1] + 1
            for k in range(0, 10, 3):
                xx = x0 + k * dx
                zt = 54 - (k + 1)
                put(cv, xx, oy, zt - 1, 'dsteel', 'ship')
                put(cv, xx, oy, zt, 'dsteel', 'ship')
            lamp(cv, land_x + dx, oy, DECK - 2, 'amber')


def deckhouse(cv, x0, x1, y0, y1, zf, storeys, name, doors):
    """Flat-roofed ship superstructure: cream walls with trim string courses, framed window rows on every deck,
    doors, rooms with lamps; floors zf, zf - 5, ... Returns the roof z."""
    n = storeys
    roof = zf - 5 * n
    boxm(cv, x0, x1, y0, y1, roof, zf - 1, 'super', 'ship', 'course', salt=7)
    for k in range(n):
        f = zf - 5 * k
        cv.carve(x0 + 1, x1 - 1, y0 + 1, y1 - 1, f - 4, f - 1)
        if k:
            boxm(cv, x0, x1, y0, y1, f, f, 'trim', 'ship')
            boxm(cv, x0 + 1, x1 - 1, y0 + 1, y1 - 1, f, f, 'floor', 'ship', 'col')
        for x in range(x0 + 3, x1 - 2, 4):
            for yy in (y0, y1):
                cv.carve(x, x + 1, yy, yy, f - 3, f - 2)
                boxm(cv, x, x + 1, yy, yy, f - 4, f - 4, 'dsteel', 'ship')
        for y in range(y0 + 3, y1 - 2, 4):
            for xx in (x0, x1):
                cv.carve(xx, xx, y, y + 1, f - 3, f - 2)
                boxm(cv, xx, xx, y, y + 1, f - 4, f - 4, 'dsteel', 'ship')
        lamp(cv, (x0 + x1) // 2, (y0 + y1) // 2, f - 4, 'warm')
        lamp(cv, x0 + 4, (y0 + y1) // 2, f - 4, 'warm')
        cv.interiors.append([f'{name} deck {k}', (x0 + x1) // 2, (y0 + y1) // 2 + 2, f])
    boxm(cv, x0, x1, y0, y1, roof, roof, 'dsteel', 'ship')
    # roof rail
    for x in range(x0, x1 + 1, 2):
        put(cv, x, y0, roof - 1, 'steel', 'ship')
        put(cv, x, y1, roof - 1, 'steel', 'ship')
    for (side, pos, k) in doors:
        f = zf - 5 * k
        if side in ('N', 'S'):
            yy = y0 if side == 'N' else y1
            cv.carve(pos, pos + 1, yy, yy, f - 3, f - 1)
            boxm(cv, pos - 1, pos - 1, yy, yy, f - 4, f - 1, 'hull', 'ship')
            boxm(cv, pos + 2, pos + 2, yy, yy, f - 4, f - 1, 'hull', 'ship')
        else:
            xx = x0 if side == 'W' else x1
            cv.carve(xx, xx, pos, pos + 1, f - 3, f - 1)
            boxm(cv, xx, xx, pos - 1, pos - 1, f - 4, f - 1, 'hull', 'ship')
            boxm(cv, xx, xx, pos + 2, pos + 2, f - 4, f - 1, 'hull', 'ship')
    return roof


def superstructure(cv):
    st = tone('steel', 0, 0, 0)
    # A/B/C decks: x 200-246, y 170-182
    roof = deckhouse(cv, 200, 246, 170, 182, DECK, 3, 'superstructure',
                     doors=[('N', 220, 0), ('S', 220, 0), ('E', 175, 0), ('W', 175, 1), ('N', 236, 2), ('S', 236, 2)])
    # inner stairs A->B, B->C, C->boat deck (29)
    structures.straight_stair(cv, 203, 171, 172, DECK, 5, 1, st, 'ship')
    structures.straight_stair(cv, 243, 180, 181, DECK - 5, 5, -1, st, 'ship')
    structures.straight_stair(cv, 203, 171, 172, DECK - 10, 5, 1, st, 'ship')
    # external stairs from the main deck up the sides to the C deck doors (alleys y 167-169 / 183-185)
    structures.straight_stair(cv, 226, 167, 168, DECK, 5, 1, st, 'ship')
    boxm(cv, 231, 240, 167, 169, DECK - 5, DECK - 5, 'deck', 'ship')
    structures.straight_stair(cv, 226, 184, 185, DECK, 5, 1, st, 'ship')
    boxm(cv, 231, 240, 183, 185, DECK - 5, DECK - 5, 'deck', 'ship')
    structures.straight_stair(cv, 232, 167, 168, DECK - 5, 5, 1, st, 'ship')
    structures.straight_stair(cv, 232, 184, 185, DECK - 5, 5, 1, st, 'ship')
    boxm(cv, 237, 240, 167, 169, DECK - 10, DECK - 10, 'deck', 'ship')       # C-deck door landings
    boxm(cv, 237, 240, 183, 185, DECK - 10, DECK - 10, 'deck', 'ship')
    # bridge house on the C roof: x 222-244, y 170-182, floor 29, roof 24, wings to the ship sides
    bz = roof
    boxm(cv, 222, 244, 170, 182, bz - 5, bz - 1, 'super', 'ship', 'course', salt=9)
    cv.carve(223, 243, 171, 181, bz - 4, bz - 1)
    boxm(cv, 222, 244, 170, 182, bz - 5, bz - 5, 'dsteel', 'ship')
    cv.carve(244, 244, 171, 181, bz - 3, bz - 2)                        # wide bridge window band (fore)
    for x in range(224, 243, 3):
        cv.carve(x, x + 1, 170, 170, bz - 3, bz - 2)
        cv.carve(x, x + 1, 182, 182, bz - 3, bz - 2)
    cv.carve(222, 222, 175, 176, bz - 3, bz - 1)                        # aft door to the boat deck
    for y in (166, 167, 168, 169, 183, 184, 185, 186):                  # bridge wings
        boxm(cv, 236, 244, y, y, bz, bz, 'deck', 'ship')
    for x in range(236, 245):
        put(cv, x, 166, bz - 1, 'steel', 'ship')
        put(cv, x, 186, bz - 1, 'steel', 'ship')
    boxm(cv, 236, 244, 170, 170, bz - 3, bz - 1, 'super', 'ship')       # keep the wing doors framed
    cv.carve(238, 239, 170, 170, bz - 3, bz - 1)
    cv.carve(238, 239, 182, 182, bz - 3, bz - 1)
    boxm(cv, 230, 236, 172, 173, bz - 1, bz - 1, 'dsteel', 'ship')     # chart table / console
    boxm(cv, 241, 242, 174, 178, bz - 1, bz - 1, 'dsteel', 'ship')
    put(cv, 240, 176, bz - 1, 'black', 'ship')                          # wheel
    lamp(cv, 233, 176, bz - 4, 'warm')
    lamp(cv, 241, 176, bz - 4, 'warm')
    cv.interiors.append(['bridge', 232, 178, bz])
    cv.interiors.append(['boat deck', 204, 176, bz])
    # radar mast on the bridge roof
    rz = bz - 5
    boxm(cv, 234, 235, 176, 176, rz - 11, rz - 1, 'steel', 'ship')
    boxm(cv, 234, 235, 171, 181, rz - 6, rz - 6, 'steel', 'ship')
    boxm(cv, 230, 239, 176, 176, rz - 9, rz - 9, 'dsteel', 'ship')
    lamp(cv, 234, 176, rz - 12, 'nav_w')
    lamp(cv, 236, 171, rz - 6, 'flood')
    lamp(cv, 236, 181, rz - 6, 'flood')
    lamp(cv, 245, 176, bz - 6, 'flood')
    # funnel on the boat deck
    for z in range(bz - 16, bz):
        for x in range(209, 220):
            for y in range(171, 182):
                if ((x - 214) / 5.6) ** 2 + ((y - 176) / 5.0) ** 2 <= 1:
                    nm = 'funnel_top' if z <= bz - 14 else ('sheer' if z in (bz - 10, bz - 9) else 'funnel')
                    put(cv, x, y, z, nm, 'ship')
    cv.carve(212, 216, 174, 178, bz - 16, bz - 15)
    # lifeboats in davits on both sides of the C deck, hanging over the alleys
    for (y0, y1) in ((167, 169), (183, 185)):
        boxm(cv, 204, 216, y0, y1, DECK - 14, DECK - 12, 'lifeboat', 'ship', 'course')
        boxm(cv, 205, 215, y0, y1, DECK - 15, DECK - 15, 'lifeboat', 'ship')
        boxm(cv, 206, 214, y0 + 1, y0 + 1, DECK - 15, DECK - 15, 'sheer', 'ship')
        for x in (205, 215):
            boxm(cv, x, x, min(y0, y1), max(y0, y1), DECK - 16, DECK - 16, 'dsteel', 'ship')
    return bz


def helideck(cv):
    z = DECK - 5
    for x in range(183, 200):
        for y in range(165, 188):
            if (x - 192) ** 2 + (y - 176) ** 2 <= 11.5 ** 2:
                put(cv, x, y, z, 'deck', 'ship')
                r = math.hypot(x - 192, y - 176)
                if 7.0 <= r <= 8.2:
                    put(cv, x, y, z, 'yellow', 'ship')
                if r > 10.6 and (x + y) % 2 == 0:
                    put(cv, x, y, z - 1, 'steel', 'ship')
    for (x, y) in ((188, 172), (188, 180), (196, 172), (196, 180)):
        boxm(cv, x, x, y, y, z + 1, DECK - 1, 'dsteel', 'ship')
    # "H" marking
    for y in range(173, 180):
        put(cv, 189, y, z, 'sheer', 'ship')
        put(cv, 194, y, z, 'sheer', 'ship')
    for x in range(190, 194):
        put(cv, x, 176, z, 'sheer', 'ship')
    cv.interiors.append(['helideck', 192, 182, z])
    # helicopter: fuselage along x, nose east, skids, rotor mast + blades, tail boom and rotor
    hz = z - 1
    fy = (182, 185)
    boxm(cv, 184, 191, fy[0], fy[1], hz - 1, hz, 'dsteel', 'ship')                 # skids/frame
    cv.carve(185, 190, fy[0] + 1, fy[1] - 1, hz, hz)
    boxm(cv, 184, 191, fy[0], fy[1], hz - 4, hz - 1, 'heli', 'ship', 'course')
    boxm(cv, 191, 191, fy[0] + 1, fy[1] - 1, hz - 3, hz - 2, 'glass', 'ship')
    boxm(cv, 185, 189, fy[0], fy[0], hz - 3, hz - 3, 'glass', 'ship')
    boxm(cv, 185, 189, fy[1], fy[1], hz - 3, hz - 3, 'glass', 'ship')
    boxm(cv, 176, 183, 183, 184, hz - 3, hz - 3, 'heli', 'ship')                   # tail boom
    boxm(cv, 176, 176, 183, 184, hz - 6, hz - 4, 'heli', 'ship')
    put(cv, 176, 185, hz - 5, 'dsteel', 'ship')
    boxm(cv, 187, 188, 183, 184, hz - 6, hz - 5, 'dsteel', 'ship')                 # rotor mast
    boxm(cv, 180, 195, 183, 183, hz - 7, hz - 7, 'black', 'ship')
    boxm(cv, 187, 187, 177, 190, hz - 7, hz - 7, 'black', 'ship')


def foredeck(cv):
    # cargo hatch 1 with two containers side by side and one stacked
    boxm(cv, 252, 268, 170, 182, DECK - 2, DECK - 1, 'container_s', 'ship')
    boxm(cv, 253, 266, 170, 174, DECK - 7, DECK - 3, 'container_y', 'ship', 'course')
    boxm(cv, 253, 266, 177, 181, DECK - 7, DECK - 3, 'container_g', 'ship', 'course')
    boxm(cv, 255, 264, 170, 174, DECK - 12, DECK - 8, 'container_g', 'ship', 'course')
    for x in range(254, 266, 2):
        put(cv, x, 169, DECK - 5, 'dsteel', 'ship')
        put(cv, x, 182, DECK - 5, 'dsteel', 'ship')
    # open hatch 2 over the companionway stair
    for x in range(277, 291):
        for y in (172, 179):
            boxm(cv, x, x, y, y, DECK - 2, DECK - 1, 'yellow' if x % 4 < 2 else 'black', 'ship')
    # crane: pedestal, cab, slewing jib and hook
    boxm(cv, 272, 274, 166, 168, DECK - 8, DECK - 1, 'yellow', 'ship')
    boxm(cv, 271, 275, 165, 169, DECK - 12, DECK - 9, 'yellow', 'ship', 'course')
    boxm(cv, 275, 275, 166, 167, DECK - 11, DECK - 10, 'glass', 'ship')
    for i in range(0, 27):
        x = 274 + i
        z = DECK - 13 - int(i * 0.45)
        boxm(cv, x, x, 167, 168, z, z, 'yellow', 'ship')
        if i < 26:
            put(cv, x, 167, z - 1, 'yellow', 'ship')
    boxm(cv, 300, 300, 167, 167, DECK - 24, DECK - 16, 'dsteel', 'ship')
    boxm(cv, 299, 301, 167, 167, DECK - 16, DECK - 16, 'black', 'ship')
    lamp(cv, 286, 168, DECK - 20, 'flood')
    # bollards
    for x in range(204, 292, 22):
        ya, yb = yspan(x)
        boxm(cv, x, x + 1, ya + 2, ya + 2, DECK - 2, DECK - 1, 'dsteel', 'ship')
        boxm(cv, x, x + 1, yb - 2, yb - 2, DECK - 2, DECK - 1, 'dsteel', 'ship')
    # forecastle: stairs up from the main deck, windlass, chain, bow mast with light
    st = tone('steel', 0, 0, 0)
    structures.straight_stair(cv, 291, 169, 170, DECK, 5, 1, st, 'ship')
    structures.straight_stair(cv, 291, 182, 183, DECK, 5, 1, st, 'ship')
    boxm(cv, 304, 308, 172, 180, FC - 2, FC - 1, 'dsteel', 'ship')
    boxm(cv, 305, 307, 175, 177, FC - 3, FC - 3, 'hull_band', 'ship')
    for i in range(10):
        put(cv, 309 + i, 173, FC - 1, 'dsteel', 'ship')
        put(cv, 309 + i, 179, FC - 1, 'dsteel', 'ship')
    boxm(cv, 316, 317, 176, 176, FC - 19, FC - 1, 'steel', 'ship')
    boxm(cv, 314, 319, 176, 176, FC - 14, FC - 14, 'steel', 'ship')
    lamp(cv, 316, 176, FC - 20, 'nav_w')
    lamp(cv, 318, 176, FC - 14, 'flood')
    lamp(cv, 314, 176, FC - 14, 'nav_g')
    for x in range(FC_X, 326):
        sp = yspan(x)
        if sp is None:
            continue
        put(cv, x, sp[0], FC - 3, 'steel', 'ship')
        put(cv, x, sp[1], FC - 3, 'steel', 'ship')
    cv.interiors.append(['forecastle', 310, 176, FC])
    cv.interiors.append(['forecastle store', 300, 176, DECK])
    cv.interiors.append(['main deck', 270, 176, DECK])
    cv.interiors.append(['tween deck', 250, 176, TWEEN])
    cv.interiors.append(['hold fore', 262, 176, HOLD])
    cv.interiors.append(['hold aft (engines)', 212, 176, HOLD])


def ice_collar(cv, rng):
    """Crushed ice piled against the hull and ahead of the bow; gaps keep every breach and ladder open."""
    keep = [(220, 228), (288, 296), (200, 218), (276, 294)]
    def blocked(x):
        return any(a - 2 <= x <= b + 2 for a, b in keep)
    for x in range(186, 330, 3):
        if blocked(x):
            continue
        sp = yspan(x)
        if sp is None:
            continue
        for side, y in ((0, sp[0] - 2), (1, sp[1] + 1)):          # touching the hull
            if rng.random() < 0.6:
                ice_block(cv, x, y, int(rng.integers(2, 4)), 2, int(rng.integers(2, 5)), int(rng.integers(-1, 2)))
    for i in range(14):                                                 # bow wave: heaped floes ahead
        x = int(325 + rng.integers(0, 10))
        y = int(CY + rng.integers(-9, 9))
        ice_block(cv, x, y, int(rng.integers(3, 6)), int(rng.integers(3, 6)), int(rng.integers(3, 8)),
                  int(rng.integers(-2, 3)))


def build_ship(cv, rng):
    hull(cv)
    bulkheads(cv)
    breaches(cv)
    superstructure(cv)
    helideck(cv)
    foredeck(cv)
    gangways(cv)
    ice_collar(cv, rng)
    reg('icebreaker', (178, 330, 164, 188), 'vessel')
