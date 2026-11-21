"""Hrafnfjord Yule: placement of every piece from the SPEC (graybox, west half x <= 255; mirrored afterwards)."""
from __future__ import annotations

import math

import numpy as np

from aosmap.kit import veg
import nc_build as B
from nc_world import FC, boxm, put, ground_med, landmark, reg
from nordic_christmas_spec import SPEC

S = SPEC


def keep_zones(cv):
    """No-prop / no-tree flags (west; mirrored with the canvas)."""
    sp = S['spawn_no_prop']
    cv.no_prop(*sp)
    f = S['front']
    cv.no_prop(f[0], f[1], f[2], f[3])
    t = S['tower_zone']['blue']
    a = S['anchor']['blue']
    cv.no_prop(min(t[0], a[0]), max(t[1], a[1]) + 2, a[2] - 4, a[3] + 4)
    s = S['ctf_strip']['blue']
    cv.no_prop(*s)
    for w in S['village_wings'].values():
        cv.no_prop(*w)
    cv.no_prop(60, 230, 96, 112)                      # north flank corridor
    cv.no_prop(60, 230, 399, 415)                     # south flank corridor
    cv.no_prop(8, 64, 466, 504)                       # corner tag (art pass)


# ------------------------------------------------------------------ spawn yard + CTF strip farmland
def spawn_yard(cv, vrng):
    for y in (229, 283):                                       # wattle, top ramped 1-2-3-3-2-1 (no stranded tops)
        for (x0, x1) in ((98, 105), (113, 120)):
            for x in range(x0, x1 + 1):
                hi = max(1, min(x - x0 + 1, x1 - x + 1, 3))
                g = int(cv.H[x, y])
                boxm(cv, x, x, y, y, g - hi, g - 1, 'post', 'prop')
    lm = S['spawn_yard']['landmark']                          # julenek (CTF strip: no standable treetops)
    julenek(cv, (lm['box'][0] + lm['box'][1]) // 2, (lm['box'][2] + lm['box'][3]) // 2)


def hesje(cv, x0, y0, L, along='x', h=4):
    """Hay-drying rack (hesje) heaped with hay: the top ramps 1, 2, 3, 4 ... 3, 2, 1 along its length, so every top
    voxel steps down <= 1 to the field (no stranded tops in the CTF strip); posts every 3 inside the heap."""
    for i in range(L):
        x, y = (x0 + i, y0) if along == 'x' else (x0, y0 + i)
        g = int(cv.H[x, y])
        hi = max(1, min(i + 1, L - i, h))
        boxm(cv, x, x, y, y, g - hi, g - 1, 'post' if i % 3 == 0 else 'hay', 'prop')


def stook(cv, cx, cy, h=4):
    """Corn stook / haystack for the CTF strip: stepped cone, height h - floor(distance), so it steps down <= 1."""
    g = int(cv.H[cx, cy])
    for x in range(cx - h, cx + h + 1):
        for y in range(cy - h, cy + h + 1):
            hi = h - int(math.floor(math.hypot(x - cx, y - cy)))
            if hi > 0:
                gg = int(cv.H[x, y])
                boxm(cv, x, x, y, y, gg - hi, gg - 1, 'hay', 'prop')


def julenek(cv, x, y):
    """Christmas oat sheaf on a short pole (spawn landmark in the strip): 4 tall, 1-voxel top, nothing to stand on."""
    g = int(cv.H[x, y])
    boxm(cv, x, x, y, y, g - 3, g - 1, 'post', 'prop')
    put(cv, x, y, g - 4, 'straw', 'prop')
    for (dx, dy) in ((-1, 0), (1, 0), (0, -1), (0, 1)):          # sheaf ears: 1-tall bundle ring at the foot
        gg = int(cv.H[x + dx, y + dy])
        put(cv, x + dx, y + dy, gg - 1, 'straw', 'prop')


def _free(cv, x0, x1, y0, y1, avoid):
    if x0 < 2 or y0 < 2 or x1 > 125:
        return False
    for (a, b, c, d) in avoid:
        if not (x1 < a or x0 > b or y1 < c or y0 > d):
            return False
    sub = cv.H[x0:x1 + 1, y0:y1 + 1]
    return int(sub.max()) - int(sub.min()) <= 1 and not cv.solid[x0:x1 + 1, y0:y1 + 1, :int(sub.min())].any()


def strip_hesjer(cv):
    """Spread hesjer over the CTF strip on a jittered grid (layout seed): low cover within 8 of >= 35 % of the strip
    while object tops stay <= 3 %. Plus lines just outside the Babel spawn square (N, S, rear)."""
    from aosmap.kit import noise
    rng = noise.rng('hesjer', S['layout_seed'])
    g = S['ctf_strip_rules']['hesje_grid']
    rh = S['rear_hills']['box']
    p = S['farm_pond']
    avoid = [(rh[0] - 2, rh[1], rh[2] - 2, rh[3] + 2), (p['cx'] - p['rx'] - 2, p['cx'] + p['rx'] + 2,
             p['cy'] - p['ry'] - 2, p['cy'] + p['ry'] + 2), tuple(S['spawn_no_prop'])]
    n = 0
    for y in range(132, 382, g['step'][1]):
        for x in range(6, 124, g['step'][0]):
            L = int(rng.integers(*g['len']))
            along = 'x' if rng.random() < 0.6 else 'y'
            xx, yy = x + int(rng.integers(-4, 5)), y + int(rng.integers(-4, 5))
            box = (xx, xx + L - 1, yy, yy) if along == 'x' else (xx, xx, yy, yy + L - 1)
            if _free(cv, box[0] - 1, box[1] + 1, box[2] - 1, box[3] + 1, avoid):
                hesje(cv, xx, yy, L, along, g['h'])
                n += 1
    for (x0, L) in ((98, 11), (116, 12)):                     # spawn-side lines, just outside the +-4 margin
        hesje(cv, x0, 231, L, 'x')
        hesje(cv, x0, 281, L, 'x')
    for y0 in (236, 251, 266):                                  # rear line, off the hill (gaps 7)
        hesje(cv, 93, y0, 8, 'y')
    return n


def strip_dressing(cv):
    for (x0, x1, y) in ((10, 38, 150), (48, 76, 150), (86, 112, 150), (20, 50, 176), (62, 100, 176),
                        (10, 40, 376), (52, 84, 376), (96, 120, 376), (86, 112, 336)):
        B.fence(cv, x0, x1, y, y, h=1, name='stone')          # snowed-under drystone dyke: step-over (CTF walk-out)
    for (x, y) in ((30, 162), (70, 164), (108, 162), (18, 214), (26, 300), (110, 348), (96, 368), (14, 330)):
        stook(cv, x, y, h=4)
    for (x, y) in ((60, 188), (100, 322), (40, 140), (116, 196)):
        g = int(cv.H[x, y])
        boxm(cv, x, x + 3, y, y + 1, g - 1, g - 1, 'prop', 'prop')


# ------------------------------------------------------------------ front dressing (Babel front, low objects)
def front_dressing(cv):
    for it in S['front_dressing']['items']:
        x0, x1, y0, y1 = it['box']
        n, h = it['name'], it['h']
        g = ground_med(cv, x0, x1, y0, y1)
        if n.startswith('haystack'):
            B.haystack(cv, (x0 + x1) / 2 - 0.5, (y0 + y1) / 2 - 0.5, h=h, r=2.6)
        elif n.startswith('hay rick'):
            for (cx, cy) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
                boxm(cv, cx, cx, cy, cy, g - h + 1, g - 1, 'post', 'prop')
            boxm(cv, x0, x1, y0, y1, g - h, g - h, 'roof', 'prop')
            boxm(cv, x0 + 1, x1 - 1, y0 + 1, y1 - 1, g - 2, g - 1, 'hay', 'prop')
        elif n.startswith('woodpile'):
            boxm(cv, x0, x1, y0, y1, g - h, g - 1, 'log', 'prop')
        elif n.startswith('stockfish'):
            for (cx, cy) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
                boxm(cv, cx, cx, cy, cy, g - h, g - 1, 'post', 'prop')
            for y in (y0, y1):
                boxm(cv, x0, x1, y, y, g - h, g - h, 'post', 'prop')
            for x in range(x0 + 1, x1, 2):
                for y in (y0, y1):
                    put(cv, x, y, g - h + 1, 'prop', 'prop')
        elif n.startswith('sled'):
            boxm(cv, x0, x1, y0, y1, g - 1, g - 1, 'log', 'prop')
            boxm(cv, x0 + 1, x1 - 1, y0, y1 - 1, g - 2, g - 2, 'prop', 'prop')
        elif n.startswith('rune cairn'):
            boxm(cv, x0, x1, y0, y1, g - 2, g - 1, 'stone', 'prop')
            put(cv, x0 + 1, y0 + 1, g - 3, 'rune', 'prop')
        elif n.startswith('split-rail'):
            B.fence(cv, x0, x1, y0, y1, h=h)


# ------------------------------------------------------------------ village wings
def mead_hall(cv, rng):
    st = S['structures'][0]
    x0, x1, y0, y1 = st['box']
    zf = 40
    r = B.house(cv, st['name'], 'main', (x0, x1, y0, y1), zf, 7, 'x',
                doors=[('S', 154, 3), ('E', 159, 3), ('W', 159, 3)],
                lofts=[(x0 + 1, 145, y0 + 1, y1 - 1, 35, (150, 150, 151, -1, 'x'))])
    B.hearth(cv, 149, 165, 159, 161, zf)
    B.bench(cv, 153, 175, 150, 150, zf)
    B.bench(cv, 147, 175, 170, 170, zf)
    B.table(cv, 174, 176, 156, 157, zf)                  # high seat
    B.interior(cv, 'mead hall floor', 160, 155, zf)
    B.interior(cv, 'mead hall loft', 138, 164, 35)
    # porch on the south door
    for (cx, cy) in ((150, 177), (160, 177)):
        boxm(cv, cx, cx, cy, cy, 35, zf - 1, 'post', 'building')
    B.gable_roof(cv, 150, 160, 173, 177, 35, 'y', ov=1, gable_ends=False)
    # antler gables at both ends of the ridge (x 131 and x 179)
    rz = r['ridge']
    for ex in (x0 - 1, x1 + 1):
        for s in (-1, 1):
            cv.line((ex, 160, rz), (ex, 160 + 6 * s, rz - 6), FC['antler'], 'roof')
            cv.line((ex, 160 + 3 * s, rz - 3), (ex, 160 + 2 * s, rz - 7), FC['antler'], 'roof')
    B.yard_props(cv, rng, (x0, x1, y0, y1), zf, 11, keepout=[(149, 161, 173, 183), (179, 186, 156, 164),
                                                             (124, 131, 156, 164)])


def smithy(cv, rng):
    st = S['structures'][1]
    x0, x1, y0, y1 = st['box']
    zf = 40
    r = B.house(cv, st['name'], 'small', (x0, x1, y0, y1), zf, 5, 'x', doors=[('S', 150, 9), ('E', 193, 3)])
    boxm(cv, 146, 148, 188, 190, zf - 2, zf - 1, 'stone', 'furniture')            # forge
    boxm(cv, 146, 147, 187, 188, r['ridge'] - 2, zf - 3, 'stone', 'building')     # chimney through the roof
    B.table(cv, 153, 153, 190, 191, zf)                                           # anvil
    B.bench(cv, 160, 162, 188, 188, zf)
    B.interior(cv, 'smithy', 156, 196, zf)
    B.yard_props(cv, rng, (x0, x1, y0, y1), zf, 6, keepout=[(148, 160, 202, 212), (164, 172, 191, 197)])


def boat_shed(cv, rng, st):
    x0, x1, y0, y1 = st['box']
    zf = 40
    yc = (y0 + y1) // 2
    B.house(cv, st['name'], 'small', (x0, x1, y0, y1), zf, 5, 'x', doors=[('W', yc - 1, 3)], open_end='E')
    boxm(cv, x0 + 4, x1 - 3, yc - 1, yc + 1, zf - 1, zf - 1, 'hull', 'furniture')    # faering on trestles
    boxm(cv, x0 + 6, x1 - 5, yc, yc, zf - 2, zf - 2, 'hull', 'furniture')
    B.interior(cv, st['name'], x0 + 3, y0 + 2, zf)
    B.yard_props(cv, rng, (x0, x1, y0, y1), zf, 4, keepout=[(x0 - 8, x0, yc - 3, yc + 3), (x1, x1 + 12, y0, y1),
                                                            (176, 214, 230, 282)])


def longhouse(cv, rng):
    st = S['structures'][4]
    x0, x1, y0, y1 = st['box']
    zf = 40
    B.pad(cv, 129, 139, 311, 327, zf, ring=4)                  # byre ground first
    B.house(cv, st['name'], 'main', (x0, x1, y0, y1), zf, 6, 'x',
            doors=[('N', 158, 3), ('E', 318, 3), ('W', 318, 3)],
            lofts=[(160, x1 - 1, y0 + 1, y1 - 1, 35, (155, 310, 311, 1, 'x'))])
    B.hearth(cv, 143, 152, 318, 320, zf)
    B.bench(cv, 143, 152, 328, 328, zf)
    B.bench(cv, 162, 176, 310, 310, zf)
    B.table(cv, 164, 167, 318, 320, zf)
    B.interior(cv, 'longhouse floor', 150, 313, zf)
    B.interior(cv, 'longhouse loft', 170, 326, 35)
    # byre lean-to (second volume) against the west wall
    bx0, bx1, by0, by1 = 130, 139, 312, 326
    boxm(cv, bx0, bx0, by0, by1, zf - 4, zf - 1, 'wall', 'building')
    boxm(cv, bx0, bx1, by0, by0, zf - 4, zf - 1, 'wall', 'building')
    boxm(cv, bx0, bx1, by1, by1, zf - 4, zf - 1, 'wall', 'building')
    for x in range(bx0 - 1, bx1 + 1):
        z = zf - 5 - (x - bx0 + 1) // 4
        boxm(cv, x, x, by0 - 1, by1 + 1, z, z + 1, 'roof', 'roof')
    boxm(cv, bx0 + 1, bx1, by0 + 1, by1 - 1, zf, zf, 'floor', 'building')
    B.door(cv, 'S', (bx0, bx1, by0, by1), zf, 133, 3)
    B.interior(cv, 'longhouse byre', 135, 316, zf)
    reg('longhouse byre', (bx0 - 1, bx1, by0 - 1, by1 + 1), 'small')
    # porch on the north door
    for (cx, cy) in ((155, 303), (163, 303)):
        boxm(cv, cx, cx, cy, cy, 35, zf - 1, 'post', 'building')
    B.gable_roof(cv, 155, 163, 303, 307, 34, 'y', ov=1, gable_ends=False)
    B.yard_props(cv, rng, (x0, x1, y0, y1), zf, 11, keepout=[(152, 166, 296, 308), (178, 186, 314, 324),
                                                             (128, 140, 326, 334)])


def bathhouse(cv, rng):
    st = S['structures'][5]
    x0, x1, y0, y1 = st['box']
    zf = 40
    B.house(cv, st['name'], 'small', (x0, x1, y0, y1), zf, 5, 'y', doors=[('N', 153, 3)])
    boxm(cv, x0 + 1, x0 + 3, y0 + 2, y1 - 2, zf - 1, zf - 1, 'furniture', 'furniture')
    boxm(cv, x0 + 1, x0 + 2, y0 + 2, y1 - 2, zf - 2, zf - 2, 'furniture', 'furniture')
    boxm(cv, x0 + 1, x0 + 1, y0 + 2, y1 - 2, zf - 3, zf - 3, 'furniture', 'furniture')
    boxm(cv, x1 - 3, x1 - 2, y1 - 3, y1 - 2, zf - 2, zf - 1, 'stone', 'furniture')
    B.interior(cv, 'bathhouse', 155, 347, zf)
    B.yard_props(cv, rng, (x0, x1, y0, y1), zf, 5, keepout=[(150, 158, 334, 342)])


def boat_sheds(cv, rng):
    for st in S['structures']:
        if st['name'].startswith('boat shed'):
            boat_shed(cv, rng, st)


# ------------------------------------------------------------------ fells
def stave_church(cv, rng):
    st = [s for s in S['structures'] if s['name'] == 'stave church'][0]
    X0, X1, Y0, Y1 = st['box']                         # 138..162 x 72..96
    zf = ground_med(cv, X0, X1, Y0, Y1)
    B.pad(cv, X0 - 2, X1 + 2, Y0 - 2, Y1 + 2, zf, ring=8)
    # ambulatory (svalgang): posts on the outer line, lean-to roof rising to the nave walls
    nx0, nx1, ny0, ny1 = 146, 158, 77, 91
    for x in range(X0, X1 + 1):
        for y in range(Y0, Y1 + 1):
            if nx0 <= x <= nx1 and ny0 <= y <= ny1:
                continue
            d = min(x - X0, X1 - x, y - Y0, Y1 - y)
            z = zf - 4 - min(d, 1)                       # low skirt roof (svalgang): nave eaves read above it
            boxm(cv, x, x, y, y, z, z + 1, 'roof', 'roof')
    # nave
    zen = zf - 10
    boxm(cv, nx0, nx1, ny0, ny1, zen, zf - 1, 'wall', 'building')
    cv.carve(nx0 + 1, nx1 - 1, ny0 + 1, ny1 - 1, zen, zf - 1)
    boxm(cv, nx0 + 1, nx1 - 1, ny0 + 1, ny1 - 1, zf, zf, 'floor', 'building')
    cv.carve(X0, X1, Y0, Y1, zf - 3, zf - 1)                            # ambulatory walkway air (eaves too)
    boxm(cv, nx0, nx1, ny0, ny1, zen, zf - 4, 'wall', 'building')         # (restore nave walls above it)
    cv.carve(nx0 + 1, nx1 - 1, ny0 + 1, ny1 - 1, zen, zf - 1)
    for (x0, x1, y0, y1) in ((nx0, nx0, ny0, ny1), (nx1, nx1, ny0, ny1), (nx0, nx1, ny0, ny0), (nx0, nx1, ny1, ny1)):
        boxm(cv, x0, x1, y0, y1, zf - 3, zf - 1, 'wall', 'building')
    for x in range(X0, X1 + 1, 3):
        for y in (Y0, Y1):
            boxm(cv, x, x, y, y, zf - 3, zf - 1, 'post', 'building')
    for y in range(Y0, Y1 + 1, 3):
        for x in (X0, X1):
            boxm(cv, x, x, y, y, zf - 3, zf - 1, 'post', 'building')
    B.gable_roof(cv, nx0, nx1, ny0, ny1, zen, 'x', ov=1)
    B.door(cv, 'S', (nx0, nx1, ny0, ny1), zf, 151, 3)
    B.windows(cv, (nx0, nx1, ny0, ny1), zf - 5, avoid=[(151, ny1)], every=2)   # clerestory arcade
    for y in range(ny0 + 2, ny1 - 1, 3):
        B.bench(cv, 150, 155, y, y, zf)
    # chancel (third volume) on the east end
    cx0, cx1, cy0, cy1 = 158, 162, 81, 87
    boxm(cv, cx0, cx1, cy0, cy1, zf - 6, zf - 1, 'wall', 'building')
    cv.carve(cx0 - 1, cx1 - 1, cy0 + 1, cy1 - 1, zf - 5, zf - 1)
    B.gable_roof(cv, cx0, cx1, cy0, cy1, zf - 6, 'x', ov=0)
    B.table(cv, 160, 160, 83, 85, zf)
    # west tower with switchback stair to the bell loft
    tx0, tx1, ty0, ty1 = X0, nx0, 80, 88
    rise = 10
    zl = zf - rise
    boxm(cv, tx0, tx1, ty0, ty1, zl - 4, zf - 1, 'wall', 'building')
    cv.carve(tx0 + 1, tx1 - 1, ty0 + 1, ty1 - 1, zl - 3, zf - 1)
    boxm(cv, tx0 + 1, tx1 - 1, ty0 + 1, ty1 - 1, zf, zf, 'floor', 'building')
    boxm(cv, tx0 + 1, tx1 - 1, ty0 + 1, ty1 - 1, zl, zl, 'floor', 'building')
    for k in range(ty0 + 2, ty1 - 1, 2):                                   # bell-loft louvres
        cv.carve(tx0, tx0, k, k, zl - 3, zl - 1)
        cv.carve(tx1, tx1, k, k, zl - 3, zl - 1)
    for k in range(tx0 + 2, tx1 - 1, 2):
        cv.carve(k, k, ty0, ty0, zl - 3, zl - 1)
        cv.carve(k, k, ty1, ty1, zl - 3, zl - 1)
    B.pyramid_roof(cv, tx0, tx1, ty0, ty1, zl - 4, ov=1, pitch=2)
    B.door(cv, 'W', (tx0, tx1, ty0, ty1), zf, 85, 3)
    cv.carve(tx1, tx1, 85, 87, zf - 4, zf - 1)                            # tower base -> nave
    cv.carve(tx0 + 1, tx1 - 1, 86, 87, zf - 3, zf - 1)
    from aosmap.kit import structures
    B.stairwell(cv, tx0 + 1, ty0 + 1, zl)
    structures.switchback_stair(cv, tx0 + 1, ty0 + 1, zf, rise, flight=5, width=2, c=FC['stair'], mat='stair')
    B.interior(cv, 'stave church nave', 152, 80, zf)
    B.interior(cv, 'stave church bell loft', tx0 + 4, ty1 - 1, zl)
    reg(st['name'], (X0 - 1, X1 + 1, Y0 - 1, Y1 + 1), 'main')
    cv.no_prop(X0 - 4, X1 + 4, Y0 - 4, Y1 + 4)
    B.yard_props(cv, rng, (X0, X1, Y0, Y1), zf, 10, keepout=[(148, 156, 96, 104), (128, 138, 82, 90)])


def beacons(cv, rng):
    for st in S['structures']:
        if not st['name'].startswith('beacon'):
            continue
        x0, x1, y0, y1 = st['box']
        zf = ground_med(cv, x0, x1, y0, y1)
        north = y0 < 256
        doors = [('S', 179, 3)] if north else [('W', y1 - 2, 2)]
        zt, top = B.tower(cv, st['name'], (x0, x1, y0, y1), zf, 10, doors=doors)
        boxm(cv, x1 - 3, x1 - 1, y1 - 2, y1 - 1, zt - 2, zt - 1, 'fire', 'furniture')
        B.interior(cv, st['name'] + ' base', x0 + 4, y1 - 1, zf)
        B.interior(cv, st['name'] + ' top', x0 + 2, y1 - 1, zt)
        B.yard_props(cv, rng, (x0, x1, y0, y1), zf, 5, keepout=[(x0 - 2, x1 + 2, y1, y1 + 6), (x0 - 6, x0, y1 - 4, y1)])


def lodges(cv, rng):
    for st in S['structures']:
        if not st['name'].startswith('hunting lodge'):
            continue
        x0, x1, y0, y1 = st['box']
        zf = ground_med(cv, x0, x1, y0, y1)
        side = 'S' if y0 < 256 else 'N'
        B.house(cv, st['name'], 'small', (x0, x1, y0, y1), zf, 5, 'x', doors=[(side, 47, 3)])
        B.bench(cv, x0 + 2, x0 + 5, y0 + 2, y0 + 2, zf)
        B.table(cv, x1 - 4, x1 - 2, y0 + 5, y0 + 6, zf)
        B.interior(cv, st['name'], x0 + 4, (y0 + y1) // 2 + 1, zf)
        B.yard_props(cv, rng, (x0, x1, y0, y1), zf, 5, keepout=[(44, 52, y1, y1 + 6) if side == 'S' else (44, 52, y0 - 6, y0)])


# ------------------------------------------------------------------ bay and fjord
def bay(cv, rng):
    for c in S['bay_contents']:
        n = c['name']
        b = c['box']
        if n.startswith('ice-fishing hut'):
            x0, x1, y0, y1 = b
            zf = ground_med(cv, x0, x1, y0, y1)              # NW / SW huts stand on the shore, mid huts on ice
            B.house(cv, n, 'small', (x0, x1, y0, y1), zf, 4, 'y', doors=[('E', y0 + 2, 3)], window_every=4,
                    ring=0 if zf == 43 else 4)
            B.bench(cv, x0 + 1, x0 + 2, y0 + 1, y0 + 1, zf)
            boxm(cv, x0 + 2, x0 + 2, y1 - 2, y1 - 2, zf - 1, zf - 1, 'furniture', 'furniture')
            B.interior(cv, n, x0 + 3, y0 + 4, zf)
            for (px, py) in ((x0 - 3, y0 + 1), (x0 - 3, y1 - 1), (x0 + 1, y0 - 3), (x0 + 2, y1 + 3),
                             (x0 + 5, y0 - 4), (x0 + 5, y1 + 4), (x0 - 5, y0 + 4)):
                g = int(cv.H[px, py])
                boxm(cv, px, px + 1, py, py, g - 1, g - 1, 'prop', 'prop')
        elif n.startswith('pressure ridge'):
            x0, x1, y0, y1 = b
            for x in range(x0, x1 + 1):
                h = 3 + int((math.sin(x * 1.7) + 1) * 1.0)
                for y in range(y0, y1 + 1):
                    hh = h - abs(y - (y0 + y1) // 2)
                    if hh > 0:
                        boxm(cv, x, x, y, y, 43 - hh, 42, 'ice', 'icerubble')
        elif n.startswith('ice-hole camp'):
            x0, x1, y0, y1 = b
            boxm(cv, x0, x0 + 3, y0, y0 + 1, 42, 42, 'log', 'prop')
            for (px, py) in ((x0 + 6, y0), (x0 + 9, y0)):
                boxm(cv, px, px, py, py, 40, 42, 'post', 'prop')
            boxm(cv, x0 + 6, x0 + 9, y0, y0, 40, 40, 'post', 'prop')
            boxm(cv, x0 + 3, x0 + 4, y1 - 1, y1, 42, 42, 'prop', 'prop')
    B.longship(cv, 'longship north', 209)
    B.longship(cv, 'longship south', 303, tilt=1, mast_top=30)
    B.thing_rock(cv, S['bay_contents'][0])


def fjord_landmarks(cv):
    pyre_holm, rune_holm = S['holms']
    B.yule_pyre(cv, pyre_holm, pyre_holm['pyre'])
    landmark('Yule pyre', pyre_holm['box'])
    B.rune_ring(cv, rune_holm, rune_holm['ring'])
    landmark('rune-stone ring', rune_holm['box'])
    B.sleipnir(cv, S['sleipnir'])
    landmark('Sleipnir', S['sleipnir']['box'])
    B.raven_gate(cv, S['raven_gate'])


# ------------------------------------------------------------------ forest belts (west; OS-seeded)
def forest(cv, vrng):
    spruce = [(40, 66, 52), (50, 80, 58), (62, 92, 68)]
    birch = [(118, 128, 84), (140, 146, 96)]
    centres = [(16, 22), (52, 16), (96, 26), (196, 18), (218, 62), (104, 66), (78, 88), (18, 98),
               (196, 84), (122, 42), (24, 60), (166, 22)]
    centres += [(x, 511 - y) for (x, y) in centres]
    placed = []
    rep = {'trees': 0, 'by_species': {}, 'details': {}}
    for (gx, gy) in centres:
        n = int(vrng.integers(6, 13))
        R = float(vrng.uniform(10, 20))
        for _ in range(n * 5):
            if n <= 0:
                break
            a, rr = vrng.random() * 6.283, R * math.sqrt(vrng.random())
            x, y = int(gx + rr * math.cos(a)), int(gy + rr * math.sin(a))
            if not (4 <= x <= 226 and (y <= 116 or y >= 395)):
                continue
            if any((x - px) ** 2 + (y - py) ** 2 < 36 for px, py in placed):
                continue
            if not veg.can_place(cv, x, y):
                continue
            g = int(np.argmax(cv.solid[x, y]))
            band = (y < 28 or y > 483) and x >= 116
            hmax = 20 if band else 22
            if vrng.random() < 0.8:
                info = veg.conifer(cv, vrng, x, y, g, spruce, h=int(vrng.integers(12, hmax + 1)),
                                   clear=int(vrng.choice([4, 5])))      # walk-under: no pockets
            else:
                info = veg.broadleaf(cv, vrng, x, y, g, birch, h=int(vrng.integers(10, min(hmax, 16) + 1)))
            placed.append((x, y))
            n -= 1
            rep['trees'] += 1
            rep['by_species'][info['species']] = rep['by_species'].get(info['species'], 0) + 1
            for d in info['details']:
                rep['details'][d] = rep['details'].get(d, 0) + 1
    return rep
