"""Frozen Icebreaker places (west half authored, mirrored; pieces on x = 256 are symmetric by construction).

spawn_camp      expedition camp around the blue spawn square: lodge behind, tents, windbreaks, sleds, drums
front_dressing  low objects on the spawn -> tower-zone strip (zone rules: 4-15 objects, <= 10 tall, lanes free)
under_platform  cargo that fell off the ship under the platform (tops >= 25 below it), anchor ends left bare
station         drift research station south of the platform: core-lab hall, enclosed drill tower, labs, sheds
schooner        old expedition schooner frozen in on the north flank (ruin, keel on x = 256)
plane           crashed ski-plane on the south flank (fuselage on x = 256, enterable cabin)
ridges, bergs   pressure ridges in the skirts and grounded icebergs in the sea ring
tunnels         blue-ice tunnel from the north-west flank to the ship's hold (mirrored: north-east)
"""
from __future__ import annotations

import math

import numpy as np

from aosmap.kit import structures
from fi_spec import SPEC
from fi_struct import (house, heap, woodpile, drum_stack, crate_stack, sled_rack, snowmobile, cargo_sled, tent, ice_block,
                       rubble, flagpole, antenna, lamp_post, snow_wall, ski_rack, generator, core_boxes, seal, cairn,
                       g_at)
from fi_world import boxm, put, lamp, pad, reg, tone, P

ICE = SPEC['ice_z']


def _in_square(x, y, m=0):
    bx, by = SPEC['spawn']['base']
    h = SPEC['spawn']['half']
    return bx - h - m <= x <= bx + h + m and by - h - m <= y <= by + h + m


# ------------------------------------------------------------------------------------------------ spawn camp
def spawn_camp(cv, rng):
    bx, by = SPEC['spawn']['base']
    h = SPEC['spawn']['half']
    cv.no_prop(bx - h, bx + h, by - h, by + h)
    # expedition lodge behind the spawn: log hall (2 floors) + teal radio wing, porch toward the spawn
    lx, ly = SPEC['lodge']['x'], SPEC['lodge']['y']
    zf = pad(cv, lx - 4, lx + 28, ly - 16, ly + 28)
    house(cv, lx, ly, 13, 24, floors=2, storey=5, fam='log', ridge='long', doors=(('E', ly + 14), ('W', None)),
          chimney='W', porch=True, snow=0.6, name='expedition lodge hall', zf=zf, register=False, roofmat='roof_wood')
    house(cv, lx + 13, ly, 12, 11, floors=1, storey=6, fam='teal', ridge='short',
          doors=(('E', None), ('N', lx + 17)), chimney=None, snow=0.5, name='expedition lodge radio room', zf=zf,
          register=False)
    cv.carve(lx + 12, lx + 13, ly + 4, ly + 5, zf - 3, zf - 1)                # inner door hall <-> radio room
    reg('expedition lodge', (lx - 2, lx + 26, ly - 2, ly + 25), 'main')
    # lodge yard: woodpile, sled rack, drums, crates, ski rack, antenna, generator, lamp, dog kennels
    woodpile(cv, lx - 4, ly + 2, 7, 'y')
    sled_rack(cv, lx + 16, ly + 26, 'x')
    drum_stack(cv, lx + 27, ly + 1)
    crate_stack(cv, lx + 2, ly + 26, 5)
    ski_rack(cv, lx + 9, ly + 28)
    antenna(cv, lx + 28, ly - 8, 20)
    generator(cv, lx - 3, ly - 8)
    lamp_post(cv, lx + 26, ly + 22)
    for k in range(3):                                                        # dog kennels with a stake line
        x = lx + 1 + 4 * k
        y = ly - 15
        boxm(cv, x, x + 2, y, y + 2, zf - 2, zf - 1, 'dwood', mode='course')
        boxm(cv, x, x + 2, y, y + 2, zf - 3, zf - 3, 'roof_wood')
        cv.carve(x + 1, x + 1, y + 2, y + 2, zf - 1, zf - 1)
    # tents and gear north and south of the square (outside it, within 8 = cover for the spawn spots)
    for (tx, ty, fam) in ((100, 226, 'canvas_o'), (122, 226, 'canvas_g'), (100, 280, 'canvas_g'),
                          (122, 280, 'canvas_o')):
        tent(cv, tx, ty, fam, 7)
    sled_rack(cv, 110, 230)
    ski_rack(cv, 111, 283)
    woodpile(cv, 131, 229, 5)
    crate_stack(cv, 131, 281, 4)
    # west side (lodge side) gear, with the lodge track left open at y 250-258
    drum_stack(cv, 91, 240)
    generator(cv, 91, 263)
    crate_stack(cv, 92, 270, 4)
    # windbreak walls on the enemy-facing corners (spawn cover wedge) - lanes kept between pieces
    snow_wall(cv, 139, 232, 150, 232, 4, 3)
    snow_wall(cv, 140, 279, 151, 279, 4, 3)
    snow_wall(cv, 146, 222, 157, 217, 4, 3)
    snow_wall(cv, 146, 290, 157, 295, 4, 3)
    snow_wall(cv, 136, 218, 141, 210, 3)
    snow_wall(cv, 136, 294, 141, 302, 3)
    for (cx, cy) in ((151, 225), (151, 285), (142, 212), (142, 298), (131, 205), (131, 305)):
        heap(cv, rng, cx, cy, n=5, hmin=3, hmax=5)
    # flag mast (team colour) and camp lamps
    flagpole(cv, 96, 232, 15)
    lamp_post(cv, 97, 278)
    lamp_post(cv, 139, 238, 5)
    lamp_post(cv, 139, 274, 5)
    # backdrop pressure ridge behind the lodge's flanks (rear wedge cover) with walk-through gaps
    for (cx, cy) in ((64, 214), (74, 206), (84, 212), (64, 298), (74, 306), (84, 300), (52, 228), (52, 284)):
        rubble(cv, rng, cx, cy, n=7, spread=5, hmin=3, hmax=7)
    for (tx, ty) in ((74, 220), (74, 286)):
        tent(cv, tx, ty, 'canvas_k', 7)


# ------------------------------------------------------------------------------------------------ front
def ice_fishing_hut(cv, x0, y0):
    g = house(cv, x0, y0, 9, 7, floors=1, storey=5, fam='teal', ridge='long', doors=(('E', None), ('W', None)),
              chimney=None, snow=0.5, name='ice-fishing hut', role='small', zf=pad(cv, x0 - 2, x0 + 10, y0 - 2, y0 + 8))
    zf = g['zf']
    boxm(cv, x0 + 6, x0 + 6, y0 + 1, y0 + 1, g['top_z'] + 1, g['top_z'] + 2, 'dsteel', 'building')   # stovepipe
    for dx in (0, 1):                                                          # fishing hole inside
        for dy in (0, 1):
            put(cv, x0 + 3 + dx, y0 + 3 + dy, zf, 'lead', 'building')
    drum_stack(cv, x0 + 11, y0 + 1, ('drum_y',))
    boxm(cv, x0 - 3, x0 - 3, y0 + 8, y0 + 8, zf - 3, zf - 1, 'dsteel')                 # ice auger standing
    put(cv, x0 - 3, y0 + 8, zf - 4, 'yellow')
    for k in range(3):                                                         # fish drying rack (under the eave)
        boxm(cv, x0 + 1 + 3 * k, x0 + 1 + 3 * k, y0 - 2, y0 - 2, zf - 3, zf - 1, 'beam')
    boxm(cv, x0 + 1, x0 + 7, y0 - 2, y0 - 2, zf - 3, zf - 3, 'beam')
    for k in range(3):
        put(cv, x0 + 2 + 2 * k, y0 - 2, zf - 2, 'seal')


def front_dressing(cv, rng):
    """Low objects (<= 10 tall), lanes kept (every 8-column section >= 50 % free). A staggered two-row supply dump
    at the spawn edge (containers, snowcat, ice windbreak, drum pallet) gives the spawn its enemy-side cover and
    hides the nearest spawn spots from the platform; the rest of the strip carries smaller stories."""
    # row A (x 139-146): container with a crate stack on one end; snowcat parked along y
    boxm(cv, 140, 144, 238, 247, ICE - 5, ICE - 1, 'container_s', 'prop', 'course')
    for y in range(239, 247, 2):
        put(cv, 139, y, ICE - 3, 'dsteel')
        put(cv, 145, y, ICE - 3, 'dsteel')
    boxm(cv, 140, 144, 239, 247, ICE - 9, ICE - 6, 'container_y', 'prop', 'course')    # second box on top (10 tall)
    crate_stack(cv, 141, 236, 3)
    _snowcat(cv, 139, 262, 'y')
    boxm(cv, 140, 145, 264, 270, ICE - 9, ICE - 9, 'canvas_k', 'prop')                  # roof-rack cargo
    # row B (x 147-154): walk-through survey hut (doors E and W on the spawn-to-tower line), staggered behind
    # the gap in row A so the spawn edge is screened from the platform without blocking movement
    g = house(cv, 147, 247, 8, 16, floors=1, storey=5, fam='moss', ridge='long', doors=(('E', 253), ('W', 253)),
              chimney=None, snow=0.5, name='survey hut', role='small', zf=pad(cv, 145, 156, 245, 264),
              lantern=False)
    lamp_post(cv, 157, 246, 5)
    lamp_post(cv, 157, 264, 5)
    drum_stack(cv, 147, 264, ('drum_y',))
    # smaller stories further out
    snowmobile(cv, 163, 240, 'x', 'canvas_o')
    snowmobile(cv, 163, 243, 'x', 'yellow')
    cargo_sled(cv, 163, 260, 'x')
    ice_fishing_hut(cv, 179, 245)
    for k in range(3):
        ice_block(cv, 190 + 3 * k, 265 + k, 3, 3, int(rng.integers(3, 6)), int(rng.integers(-1, 2)))
    g = g_at(cv, 166, 254)                                                      # survey tripod + pennant
    for (a, b) in ((165, 253), (167, 253), (166, 255)):
        boxm(cv, a, a, b, b, g - 3, g - 1, 'beam')
    boxm(cv, 166, 166, 254, 254, g - 5, g - 4, 'beam')
    put(cv, 167, 254, g - 5, 'canvas_o')
    put(cv, 168, 254, g - 5, 'canvas_o')


# ------------------------------------------------------------------------------------------------ under the platform
def under_platform(cv, rng):
    """Cargo lost from the ship: containers, a capsized lifeboat, crates, drums, ice. Tops z >= 27."""
    g = ICE
    boxm(cv, 216, 229, 244, 248, g - 5, g - 1, 'container_y', 'prop', 'course')
    for x in range(217, 229, 2):
        put(cv, x, 243, g - 3, 'dsteel')
    cv.carve(229, 229, 245, 247, g - 4, g - 1)                                  # doors hang open
    boxm(cv, 238, 242, 252, 265, g - 5, g - 1, 'container_g', 'prop', 'course')
    boxm(cv, 238, 242, 258, 265, g - 9, g - 6, 'container_s', 'prop', 'course')   # one stacked half on top
    # capsized lifeboat (keel up), half a hull shape
    for x in range(221, 234):
        w = 2 if x in (221, 233) else 3
        for j in range(-w // 2 - 1, w // 2 + 2):
            y = 264 + j
            hh = 3 - abs(j) // 2
            for z in range(g - hh, g):
                put(cv, x, y, z, 'lifeboat')
        put(cv, x, 264, g - 4, 'black')
    crate_stack(cv, 245, 248, 5)
    crate_stack(cv, 216, 262, 4)
    drum_stack(cv, 234, 254)
    for k in range(4):                                                          # one heap of floes
        ice_block(cv, 248 + (k % 2), 250 + 3 * k, 3, 3, int(rng.integers(2, 5)), int(rng.integers(-1, 2)))
    cv.no_prop(196, 211, 236, 276)


# ------------------------------------------------------------------------------------------------ station
def station(cv, rng):
    """Drift research station south of the platform. Symmetric pieces straddle x = 256; the west lab mirrors."""
    sy = SPEC['station']['lab_y']
    zf = pad(cv, 236, 255, sy - 4, sy + 34)
    # core-lab hall (2 floors) on x 245-267 (centre 256): doors north and south, framed windows, lamps
    house(cv, 245, sy, 23, 13, floors=2, storey=5, fam='ochre', ridge='long', doors=(('N', 255), ('S', 251)),
          chimney=None, snow=0.5, name='core lab hall', zf=zf, register=False)
    # enclosed drill tower south of the hall (x 252-260), 3 storeys + hip roof, joined by a covered passage
    t = house(cv, 252, sy + 16, 9, 13, floors=2, storey=6, fam='grey', roof='hip', pitch=2,
              doors=(('N', 255),), chimney=None, snow=0.3, name='drill tower', zf=zf, register=False)
    boxm(cv, 253, 259, sy + 13, sy + 15, zf - 5, zf - 1, 'clad_grey', 'building', 'course')
    cv.carve(254, 258, sy + 12, sy + 16, zf - 4, zf - 1)
    boxm(cv, 252, 260, sy + 12, sy + 16, zf - 6, zf - 6, 'roof', 'roof')
    top = t['top_z']
    boxm(cv, 256, 256, sy + 22, sy + 22, top - 7, top - 1, 'steel', 'building')
    boxm(cv, 254, 258, sy + 22, sy + 22, top - 5, top - 5, 'steel', 'building')
    lamp(cv, 256, sy + 22, top - 8, 'flood')
    reg('core lab + drill tower', (243, 269, sy - 2, sy + 30), 'main')
    # west lab: teal two-volume lab with a mustard workshop wing (mirrored to the east)
    lab_x = SPEC['station']['lab_x']
    zf2 = pad(cv, lab_x - 4, lab_x + 30, sy + 14, sy + 40)
    house(cv, lab_x, sy + 18, 22, 12, floors=1, storey=6, fam='teal', ridge='long',
          doors=(('N', lab_x + 6), ('E', None)), chimney='W', porch=True, snow=0.55, name='glaciology lab',
          zf=zf2, register=False)
    house(cv, lab_x + 4, sy + 30, 11, 9, floors=1, storey=5, fam='ochre', ridge='short',
          doors=(('E', None), ('S', None)), chimney=None, snow=0.5, name='lab workshop', zf=zf2, register=False)
    cv.carve(lab_x + 8, lab_x + 9, sy + 29, sy + 30, zf2 - 3, zf2 - 1)
    reg('glaciology lab', (lab_x - 3, lab_x + 23, sy + 17, sy + 39), 'main')
    # small generator shed between them (small building) with its generator against the wall
    house(cv, 222, sy + 2, 11, 8, floors=1, storey=5, fam='moss', ridge='long', doors=(('S', None), ('N', None)),
          chimney='E', snow=0.5, name='generator shed', role='small', zf=zf)
    generator(cv, 222, sy + 10)
    # yard vignettes (each >= 25 cells: props touch and read as one story) + lamp posts / marker posts
    core_boxes(cv, 236, sy + 2)                                                 # hall: core boxes waiting
    _fuel_bladder(cv, 232, sy - 12)                                             # hall: fuel bladder + pump
    supply_pile(cv, 236, sy + 17)                                               # tower: drum pallet + crates
    _snowcat(cv, 233, sy + 24, 'x')                                             # tower: snowcat
    sled_rack(cv, lab_x - 8, sy + 18, 'y')                                      # lab: sled rack + woodpile
    woodpile(cv, lab_x - 6, sy + 18, 6, 'y')
    crate_stack(cv, lab_x - 8, sy + 25, 4)
    supply_pile(cv, lab_x + 24, sy + 34)                                        # lab: drums + crates
    snowmobile(cv, lab_x + 2, sy + 42, 'x', 'canvas_o')                         # lab: two snowmobiles
    snowmobile(cv, lab_x + 2, sy + 45, 'x', 'yellow')
    core_boxes(cv, lab_x + 10, sy + 42)                                         # lab: core boxes
    sled_rack(cv, lab_x + 14, sy + 14)                                          # lab: sled + ski racks
    ski_rack(cv, lab_x + 21, sy + 14)
    woodpile(cv, lab_x + 21, sy + 12, 6, 'x')
    cargo_sled(cv, lab_x + 25, sy + 21, 'y')                                    # lab: loaded cargo sled
    _weather_mast(cv, 218, sy - 4)
    for (x, y) in ((240, sy - 3), (214, sy + 16), (246, sy + 34), (lab_x - 3, sy + 34), (lab_x + 25, sy + 16),
                   (lab_x + 8, sy + 40), (230, sy + 16)):
        lamp_post(cv, x, y)


def supply_pile(cv, x, y):
    """Drum pallet + crate stack + a lashed tarp bundle, touching: one 9 x 5 story."""
    drum_stack(cv, x, y)
    crate_stack(cv, x + 4, y, 4)
    boxm(cv, x, x + 8, y + 4, y + 4, g_at(cv, x, y + 4) - 2, g_at(cv, x, y + 4) - 1, 'canvas_k')


def _fuel_bladder(cv, x, y):
    g = g_at(cv, x, y)
    for i in range(10):
        for j in range(6):
            hh = 2 if 1 <= i <= 8 and 1 <= j <= 4 else 1
            for z in range(g - hh, g):
                put(cv, x + i, y + j, z, 'black' if hh == 1 else 'dsteel')
    boxm(cv, x + 10, x + 12, y + 3, y + 3, g - 1, g - 1, 'dsteel')


def _snowcat(cv, x, y, axis='x'):
    """Tracked snowcat (12 x 8, 8 tall): two dark track units, orange cab with windows, roof rack, flood lamp."""
    g = g_at(cv, x + 4, y + 4)

    def B(i0, i1, j0, j1, z0, z1, nm, mode='hash'):
        if axis == 'x':
            boxm(cv, x + i0, x + i1, y + j0, y + j1, z0, z1, nm, 'prop', mode)
        else:
            boxm(cv, x + j0, x + j1, y + i0, y + i1, z0, z1, nm, 'prop', mode)

    def C(i0, i1, j0, j1, z0, z1):
        if axis == 'x':
            cv.carve(x + i0, x + i1, y + j0, y + j1, z0, z1)
        else:
            cv.carve(x + j0, x + j1, y + i0, y + i1, z0, z1)
    for j in (0, 6):
        B(0, 11, j, j + 1, g - 2, g - 1, 'black', 'course')
        for i in range(0, 12, 3):
            B(i, i, j, j, g - 2, g - 2, 'dsteel')
    B(1, 10, 2, 5, g - 3, g - 1, 'dsteel')
    B(1, 10, 0, 7, g - 3, g - 3, 'canvas_o')
    B(2, 8, 1, 6, g - 7, g - 4, 'canvas_o', 'course')
    C(3, 7, 2, 5, g - 6, g - 4)
    B(8, 8, 2, 5, g - 6, g - 5, 'glass')
    C(4, 6, 1, 1, g - 6, g - 5)
    C(4, 6, 6, 6, g - 6, g - 5)
    B(2, 7, 1, 6, g - 8, g - 8, 'dsteel')
    if axis == 'x':
        lamp(cv, x + 9, y + 1, g - 4, 'flood')
    else:
        lamp(cv, x + 1, y + 9, g - 4, 'flood')


def _weather_mast(cv, x, y):
    g = g_at(cv, x, y)
    boxm(cv, x, x, y, y, g - 20, g - 1, 'steel', 'prop')
    for z in (g - 7, g - 13, g - 19):
        boxm(cv, x - 2, x + 2, y, y, z, z, 'steel', 'prop')
    put(cv, x - 2, y, g - 20, 'canvas_o'); put(cv, x + 2, y, g - 20, 'canvas_o')
    lamp(cv, x, y, g - 21, 'amber')
    boxm(cv, x - 2, x + 2, y - 2, y + 2, g - 2, g - 1, 'plank', 'prop', 'course')   # instrument hut (screen)
    boxm(cv, x - 2, x + 2, y - 2, y + 2, g - 3, g - 3, 'roof')
    for k in (-2, 0, 2):
        put(cv, x + k, y + 3, g - 1, 'dsteel')


# ------------------------------------------------------------------------------------------------ flank wrecks
def schooner(cv, rng):
    """Old wooden expedition schooner frozen in, keel along x = 256, bow north. Hull planking in courses,
    broken midships (ribs exposed, deck gone), stern cabin with windows, stump foremast, bowsprit, ice heaped
    round. Hold reachable through the broken midships and two breaches at ice level."""
    ya, yb = SPEC['schooner']['y']
    deck = ICE - 7
    zf = pad(cv, 238, 255, ya - 6, yb + 6)
    for y in range(ya, yb + 1):
        t = (y - ya) / (yb - ya)
        hb = 9.0 * math.sin(math.pi * min(1.0, 0.12 + t * 0.95)) ** 0.6
        if y > yb - 4:
            hb = 8.0
        for x in range(238, 257):
            d = abs(x - 255.5) + 0.5
            if d > hb:
                continue
            wall = d > hb - 2 or y <= ya + 1 or y >= yb - 1
            for z in range(deck - 1, ICE + 1):
                if wall:
                    nm = 'log' if (z // 1) % 2 else 'dwood'
                    if z == deck - 1:
                        nm = 'beam'
                    put(cv, x, y, z, nm, 'ruin', salt=y // 5)
                else:
                    cv.clear(x, y, z)
            if not wall:
                put(cv, x, y, deck, 'plank', 'ruin')
                put(cv, x, y, ICE, 'plank', 'ruin')
    # broken midships: deck and upper planking gone, ribs left standing
    m0, m1 = ya + 22, ya + 32
    for y in range(m0, m1 + 1):
        for x in range(238, 257):
            for z in range(deck - 1, deck + 3):
                cv.clear(x, y, z)
        if (y - m0) % 3 == 0:
            for x in range(240, 256):
                d = abs(x - 255.5) + 0.5
                if d > 7.5:
                    for z in range(deck - 2, deck + 3):
                        put(cv, x, y, z, 'beam', 'ruin')
    for y in range(m0 - 1, m1 + 2):                                          # torn plank ends
        put(cv, 247, y, deck + 3, 'dwood', 'ruin')
    # ladder of planks down into the hold through the break
    structures.straight_stair(cv, m0 + 2, 252, 253, ICE, ICE - deck, -1, tone('plank', 0, 0, 0), 'ruin', along='y')
    # breaches at ice level on both sides
    yy = ya + 36
    cv.carve(238, 251, yy, yy + 2, ICE - 4, ICE - 1)
    structures.straight_stair(cv, m1 + 3, 252, 253, ICE, ICE - deck, 1, tone('plank', 0, 0, 0), 'ruin', along='y')
    # stern cabin (deckhouse) with windows and a door
    cy0, cy1 = yb - 12, yb - 3
    boxm(cv, 250, 255, cy0, cy1, deck - 5, deck - 1, 'log', 'ruin', 'course')
    cv.carve(251, 255, cy0 + 1, cy1 - 1, deck - 4, deck - 1)
    boxm(cv, 249, 255, cy0 - 1, cy1 + 1, deck - 6, deck - 6, 'roof_wood', 'ruin')
    for y in range(cy0 + 2, cy1 - 1, 3):
        cv.carve(250, 250, y, y, deck - 3, deck - 2)
    cv.carve(254, 255, cy0, cy0, deck - 3, deck - 1)
    lamp(cv, 255, (cy0 + cy1) // 2, deck - 5 + 1, 'amber')
    # foremast stump with a broken yard, mainmast fallen along the keel on the deck
    boxm(cv, 255, 255, ya + 12, ya + 12, deck - 16, deck - 1, 'beam', 'ruin')
    boxm(cv, 250, 255, ya + 12, ya + 12, deck - 12, deck - 12, 'beam', 'ruin')
    boxm(cv, 255, 255, ya + 34, yb - 14, deck - 1, deck - 1, 'beam', 'ruin')
    # bowsprit
    for k in range(8):
        put(cv, 255, ya - k, deck - 1 - k // 3, 'beam', 'ruin')
    # interiors
    cv.interiors.append(['schooner hold', 251, ya + 12, ICE])
    cv.interiors.append(['schooner cabin', 253, (cy0 + cy1) // 2, deck])
    # ice heaped against the hull and a few relics around (yard props of a ruin)
    for k in range(7):
        ice_block(cv, int(234 + rng.integers(-2, 2)), int(ya + 6 + 7 * k), 3, 3, int(rng.integers(3, 6)),
                  int(rng.integers(-1, 2)))
    crate_stack(cv, 228, ya + 30, 4)
    cairn(cv, 226, yb + 4)
    drum_stack(cv, 230, ya + 46, ('drum_s',))
    for (x, y) in ((232, ya + 16), (231, ya + 52)):
        boxm(cv, x, x + 4, y, y, ICE - 2, ICE - 1, 'dwood')                   # broken spars on the ice
    reg('expedition schooner', (236, 276, ya - 8, yb + 1), 'ruin')


def plane(cv, rng):
    """Crashed ski-plane, fuselage on x = 256 (nose north into a pressure ridge), wings span x, tail south."""
    ya, yb = SPEC['plane']['y']
    zf = pad(cv, 226, 255, ya - 4, yb + 4)
    fz = zf - 2                                                                # cabin floor on the skis
    # skis and struts
    for x in (250, 251):
        boxm(cv, x, x, ya + 8, ya + 20, zf - 1, zf - 1, 'dsteel')
        boxm(cv, x, x, ya + 12, ya + 12, fz, zf - 2, 'dsteel')
    # fuselage: hollow, 7 wide x 6 tall, door both sides, windows
    boxm(cv, 253, 255, ya + 2, yb - 10, fz - 6, fz, 'heli', 'building', 'course')
    cv.carve(254, 255, ya + 4, yb - 12, fz - 5, fz - 1)
    boxm(cv, 253, 253, ya + 2, yb - 10, fz - 2, fz - 2, 'super', 'building')     # cheat line (before openings)
    boxm(cv, 254, 255, ya + 4, yb - 12, fz, fz, 'floor', 'building')
    for y in range(ya + 6, yb - 12, 3):
        cv.carve(253, 253, y, y + 1, fz - 4, fz - 3)
    cv.carve(253, 253, ya + 20, ya + 21, fz - 3, fz - 1)                    # cargo door
    boxm(cv, 252, 252, ya + 20, ya + 21, zf - 1, zf - 1, 'plank', 'building')   # step up to the door
    put(cv, 255, ya + 1, fz - 3, 'glass'); put(cv, 254, ya + 1, fz - 3, 'glass')
    boxm(cv, 253, 255, ya, ya + 1, fz - 4, fz - 1, 'super', 'building')     # crumpled nose
    # wings: high wing on top of the fuselage, one tip broken down onto the ice
    for x in range(232, 256):
        w0, w1 = ya + 12, ya + 17
        zz = fz - 7 + (1 if x < 238 else 0)
        boxm(cv, x, x, w0, w1, zz, zz, 'heli' if x % 6 else 'super', 'building')
    for x in range(228, 232):
        boxm(cv, x, x, ya + 12, ya + 17, fz - 5 + (232 - x), fz - 5 + (232 - x), 'heli', 'building')
    for k in range(4):
        boxm(cv, 238 + 4 * k // 2, 238 + 4 * k // 2, ya + 14, ya + 14, fz - 6, zf - 1, 'dsteel', 'building')
    # engine nacelles + propellers (one prop bent)
    boxm(cv, 244, 246, ya + 8, ya + 13, fz - 7, fz - 5, 'dsteel', 'building')
    boxm(cv, 245, 245, ya + 7, ya + 7, fz - 9, fz - 3, 'black', 'building')
    # tail: tailplane + fin on the centreline
    boxm(cv, 246, 255, yb - 8, yb - 5, fz - 6, fz - 6, 'heli', 'building')
    boxm(cv, 254, 255, yb - 10, yb - 1, fz - 6, fz - 1, 'heli', 'building', 'course')
    boxm(cv, 255, 255, yb - 8, yb - 1, fz - 14, fz - 7, 'heli', 'building')
    boxm(cv, 255, 255, yb - 6, yb - 3, fz - 12, fz - 11, 'super', 'building')
    lamp(cv, 255, (ya + yb) // 2 - 4, fz - 5, 'warm')
    cv.interiors.append(['plane cabin', 254, ya + 10, fz])
    # wreck yard: scattered cargo, a fuel drum, a sledge, and the ridge the nose ploughed into
    rubble(cv, rng, 248, ya - 6, n=10, spread=6, hmin=3, hmax=7)
    crate_stack(cv, 236, ya + 24, 4)
    drum_stack(cv, 232, yb - 2, ('drum_s', 'drum_y'))
    cargo_sled(cv, 238, yb + 1, 'x')
    reg('crashed ski-plane', (226, 286, ya - 2, yb + 2), 'vessel')


# ------------------------------------------------------------------------------------------------ skirts
RIDGES = [
    [(34, 300), (52, 330), (80, 350), (112, 372)],
    [(150, 380), (176, 392), (204, 388)],
    [(40, 150), (62, 126), (92, 108)],
    [(134, 92), (162, 120), (176, 140)],
    [(30, 400), (60, 418), (96, 440)],
    [(186, 470), (214, 462)],
    [(122, 168), (138, 186)],
]


def ridges(cv, rng):
    """Pressure ridges: chains of tilted ice blocks 3-8 tall with a walk-through gap every ~14 voxels."""
    n = 0
    for pl in RIDGES:
        for (x0, y0), (x1, y1) in zip(pl, pl[1:]):
            L = math.hypot(x1 - x0, y1 - y0)
            for s in range(0, int(L), 3):
                if (s // 3) % 5 == 4:
                    continue                                                   # gap
                t = s / L
                x = int(x0 + (x1 - x0) * t + rng.integers(-1, 2))
                y = int(y0 + (y1 - y0) * t + rng.integers(-1, 2))
                if cv.H[x, y] >= 62 or _in_square(x, y, 6) or cv.keep[x, y] or (150 <= x and 130 <= y <= 382):
                    continue
                ice_block(cv, x, y, int(rng.integers(2, 5)), int(rng.integers(2, 5)), int(rng.integers(3, 8)),
                          int(rng.integers(-2, 3)))
                n += 1
    return n


BERGS = [(18, 60, 20, 34), (70, 22, 16, 26), (150, 10, 18, 30), (8, 160, 12, 22), (6, 330, 16, 30),
         (40, 470, 22, 36), (120, 500, 16, 26), (210, 498, 12, 20), (226, 8, 10, 18)]


def bergs(cv, rng):
    """Grounded icebergs in the sea ring: faceted (stepped) bodies, snow caps, deep-ice bases; solid to the seabed."""
    placed = 0
    for (cx, cy, r, hgt) in BERGS:
        if cv.H[cx, cy] < 62:
            continue
        ph = rng.uniform(0, math.tau)
        facets = int(rng.integers(5, 8))
        for x in range(cx - r - 3, cx + r + 4):
            for y in range(cy - r - 3, cy + r + 4):
                if not (0 <= x < 256 and 0 <= y < 512) or cv.H[x, y] < 62:
                    continue
                a = math.atan2(y - cy, x - cx)
                k = math.cos(math.pi / facets) / math.cos(((a + ph) % (math.tau / facets)) - math.pi / facets)
                rr = math.hypot(x - cx, y - cy) / (r * k)
                if rr > 1:
                    continue
                h = int(hgt * (1 - rr ** 1.6) // 2 * 2) + 2                       # stepped faces read as facets
                zt = 62 - h
                for z in range(zt, 64):
                    nm = 'ice_cap' if z <= zt + 1 and rr < 0.8 else ('ice_deep' if z > 58 else 'ice')
                    put(cv, x, y, z, nm, 'ice', salt=int(rr * 6))
        placed += 1
    return placed


def skirts(cv, rng):
    """Small stories in the skirts: depot cache, cairns, seal holes, flag lines along the flank tracks."""
    # supply depot on the north-west flank
    crate_stack(cv, 64, 166, 5)
    drum_stack(cv, 70, 170, ('drum_y', 'drum_s'))
    flagpole(cv, 62, 172, 9, flag='canvas_o', mat='prop')
    cargo_sled(cv, 74, 162, 'y')
    cairn(cv, 44, 426)
    cairn(cv, 196, 52, cross=False)
    for (x, y) in ((96, 400), (150, 330), (40, 260), (176, 450)):
        seal(cv, x, y, 'x' if (x + y) % 2 else 'y')
    # trail marker flags along the flank tracks (thin poles, orange pennants)
    for (x, y) in ((64, 150), (110, 96), (150, 82), (70, 370), (120, 420), (160, 436)):
        g = g_at(cv, x, y)
        boxm(cv, x, x, y, y, g - 5, g - 1, 'beam')
        put(cv, x + 1, y, g - 5, 'canvas_o')
    lamp_post(cv, 196, 112, 6)
    lamp_post(cv, 196, 400, 6)


# ------------------------------------------------------------------------------------------------ tunnels
def tunnel_path():
    T = SPEC['tunnel']
    mx, my = T['mouth']
    pts = [(mx, my), (150, my + 4), (200, T['run_y']), (T['end_x'], T['run_y']), (T['end_x'], 158)]
    return pts


def tunnels(cv, rng):
    """Blue-ice tunnel: cave mouth in an ice hummock, a ramp down 7 steps, a 5-wide gallery (air z 56-60,
    floor z 61, ice roof z 54-55), a crystal chamber, and the run into the ship's hold (opened after the ship)."""
    T = SPEC['tunnel']
    F = T['floor_z']
    a0, a1 = T['air']
    mx, my = T['mouth']
    air = np.zeros((512, 512, 64), bool)
    pts = tunnel_path()
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = int(max(abs(x1 - x0), abs(y1 - y0)))
        for s in range(L + 1):
            x = round(x0 + (x1 - x0) * s / max(L, 1))
            y = round(y0 + (y1 - y0) * s / max(L, 1))
            air[x - 2:x + 3, y - 2:y + 3, a0:a1 + 1] = True
    # crystal chamber
    cx, cy = 150, my + 4
    air[cx - 8:cx + 9, cy - 6:cy + 7, a0 - 0:a1 + 1] = True
    # hummock over the mouth (ice body + snow-capped top), then the ramp down and an open approach cut
    cv.ellipsoid(mx - 2, my, ICE, 15, 11, 9, P('ice', 'block'), 'ice')
    for x in range(mx - 18, mx + 14):
        for y in range(my - 12, my + 13):
            z = top_z = int(np.argmax(cv.solid[x, y]))
            if top_z < ICE - 2:
                put(cv, x, y, top_z, 'ice_cap', 'ice')
    for k in range(8):
        x = mx - 8 + k
        floor = ICE + k
        air[x, my - 2:my + 3, :] = False
        air[x, my - 2:my + 3, floor - 5:floor] = True
    air[mx - 22:mx - 8, my - 2:my + 3, ICE - 6:ICE] = True
    cv.solid[air] = False
    cv.mat[air] = 0
    for k in range(8):                                                      # ramp floors (packed snow treads)
        x = mx - 8 + k
        boxm(cv, x, x, my - 2, my + 2, ICE + k, 63, 'ice_deep', 'ground')
        boxm(cv, x, x, my - 2, my + 2, ICE + k, ICE + k, 'track', 'ground')
    for x in range(mx - 22, mx - 8):
        boxm(cv, x, x, my - 2, my + 2, ICE, ICE, 'track', 'ground')
    from scipy import ndimage as ndi
    shell = ndi.binary_dilation(air, iterations=1) & cv.solid
    xs, ys, zs = np.nonzero(shell)
    cv.rgb[xs, ys, zs] = P('cave', 'block')(xs, ys, zs)
    fl = shell & np.roll(air, 1, axis=2)                                     # floor voxels (air above)
    xs, ys, zs = np.nonzero(fl)
    cv.rgb[xs, ys, zs] = P('ice_deep', 'hash')(xs, ys, zs)
    # glow crystals on the walls every ~14 along the path, clusters of 2-3
    n = 0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = int(max(abs(x1 - x0), abs(y1 - y0)))
        for s in range(6, L, 14):
            x = round(x0 + (x1 - x0) * s / max(L, 1))
            y = round(y0 + (y1 - y0) * s / max(L, 1))
            horiz = abs(x1 - x0) >= abs(y1 - y0)
            wx, wy = (x, y - 3) if horiz else (x - 3, y)
            for dz in (0, 1):
                if cv.solid[wx, wy, a0 + 1 + dz]:
                    lamp(cv, wx, wy, a0 + 1 + dz, 'aurora' if n % 2 else 'aurora_b')
            n += 1
    for (dx, dy) in ((-6, -4), (6, 4), (-5, 5), (5, -5)):                  # chamber ice pillars with crystals
        boxm(cv, cx + dx, cx + dx + 1, cy + dy, cy + dy + 1, a0, F - 1, 'ice', 'ice')
        lamp(cv, cx + dx, cy + dy - 1 if dy > 0 else cy + dy + 2, a0 + 2, 'aurora')
    cv.interiors.extend([['tunnel mouth', mx + 2, my, F], ['crystal chamber', cx, cy, F],
                         ['tunnel run', 200, T['run_y'], F], ['tunnel end', T['end_x'], 152, F]])
    return {'path': pts, 'glow': n}


def open_tunnel_into_hold(cv):
    """After the ship is drawn: cut the doorway through the hull's north wall at both tunnel ends."""
    from fi_ship import yspan
    from aosmap.kit.symmetry import mirror_index
    T = SPEC['tunnel']
    a0, a1 = T['air']
    for x in (T['end_x'], mirror_index(T['end_x'])):
        ya, _ = yspan(x)
        cv.carve(x - 2, x + 2, 150, ya + 2, a0, a1)
        boxm(cv, x - 2, x + 2, 150, ya + 2, T['floor_z'], T['floor_z'], 'steel', 'ship')
        boxm(cv, x - 3, x - 3, ya, ya + 1, a0 - 1, a1, 'hull_band', 'ship')
        boxm(cv, x + 3, x + 3, ya, ya + 1, a0 - 1, a1, 'hull_band', 'ship')
        lamp(cv, x, ya - 1, a0, 'amber')
