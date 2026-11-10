"""The Hollow Crown — Halloween ground Babel (AoS 0.75 / piqueserver 1.4.2 babel + babel_script).

A cursed medieval kingdom around the ruined Blackthorn Citadel. The citadel's courtyard is the tower zone; teams
spawn in war camps west / east, walk an open causeway and pass under the Crown Gate into the courtyard. North:
the Weeping Graveyard and its hill chapel; south: Hollowshade Village; behind each camp the Whispering Woods.

The owner's mock-up has the teams north/south; stock babel_script fixes the bases at (118, 256) / (394, 256), so
the layout is rotated 90 degrees: the approaches run west/east, graveyard north, village south.

Everything is authored on the west half (x <= 256) and mirrored x' = 512 - x.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage as ndi

from hc_core import fbm2, fold_x, hash3
from hc_props import *            # noqa: F401,F403
import hc_props as P

NAME = 'The Hollow Crown'
FILE = 'the_hollow_crown'
VERSION = '1.1'
SEED = 1347

SPEC = {
    'g0': G0,
    'bases': ((118, 256), (394, 256)),
    'spawn_half': 20,
    'platform': {'x': (206, 305), 'y': (240, 271), 'z': 1},
    # citadel (west half; mirrored)
    'curtain': {'x_out': 166, 'thick': 6, 'y_n': 150, 'y_s': 362, 'top': 22},
    'gate': {'y': (240, 272), 'x': (164, 173), 'spring': 36, 'R': 18.0, 'top': 12},
    'drums': {'c': ((168, 230), (168, 282)), 'r': 8, 'top': 8},
    'corner': {'c': ((172, 156), (172, 356)), 'r': 14, 'top_n': 10},
    'moat': {'bed': 49, 'flat': 8, 'width': 15},
    'causeway_y': (226, 286),
    'courtyard': (172, 340, 201, 311),
    'hall': {'x': (204, 308), 'y': (156, 200), 'top': 12},
    'apart': {'x': (204, 308), 'y': (312, 356), 'top': 12},
    'breach_y': ((188, 202), (310, 324)),
    'camp_ring': (94, 142, 232, 280),
    'fields': ((88, 150, 158, 222), (88, 150, 290, 354)),
    'chapel': {'c': (256, 40), 'z': 34},
    'sunken': {'c': (196, 86), 'r': 22, 'depth': 5},
    'village': {'high_y': (418, 426), 'main_x': (250, 262), 'square': (228, 284, 436, 468), 'lane_x': (168, 174)},
    'stone_circle': {'c': (46, 256), 'r': 15},
    'tag': {'text': 'THE HOLLOW CROWN', 'x': 14, 'y': 494},
}


def fx_of(x):
    return np.where(x <= 256, x, 512 - x)


# ============================================================================== terrain

def terrain():
    x = np.arange(512)[:, None].astype(float); y = np.arange(512)[None, :].astype(float)
    fx = fx_of(np.broadcast_to(x, (512, 512))).astype(float)
    Y = np.broadcast_to(y, (512, 512))
    H = np.full((512, 512), float(G0))
    n_roll = fold_x(fbm2((512, 512), 46, 3, 'roll', SEED))
    core = np.zeros((512, 512), bool)
    for (x0, x1, y0, y1) in ((140, 256, 122, 390), (84, 160, 150, 362), (120, 256, 376, 472), (126, 256, 128, 140)):
        sel = (fx >= x0) & (fx <= x1) & (Y >= y0) & (Y <= y1)
        core |= sel
    dcore = ndi.distance_transform_edt(~core)
    w = np.clip(dcore / 22, 0, 1); w = w * w * (3 - 2 * w)
    H += w * (n_roll - 0.5) * 9
    d_edge = np.minimum(np.minimum(fx, 511 - fx), np.minimum(Y, 511 - Y))
    rim = np.clip((50 - d_edge) / 50, 0, 1) ** 1.5
    H -= rim * 14
    # chapel hill (north, on the axis)
    cx, cy = SPEC['chapel']['c']
    r = np.hypot(fx - cx, Y - cy)
    hill = np.clip(1 - (r / 62) ** 2, 0, 1)
    H -= hill ** 1.2 * 9
    # graveyard: gentle swells
    gy = (Y < 132) & (fx > 110)
    H += np.where(gy, (fold_x(fbm2((512, 512), 20, 2, 'gy', SEED)) - 0.5) * 2.5 * w, 0)
    H = np.rint(H)
    # chapel plateau
    pl = (np.abs(fx - cx) <= 22) & (Y >= 12) & (Y <= 72)
    H[pl] = SPEC['chapel']['z']
    # sunken burial ground: terraced bowl (1 per 3 cells)
    sx, sy = SPEC['sunken']['c']; sr = SPEC['sunken']['r']
    rs = np.hypot(fx - sx, (Y - sy) * 1.15)
    sunk = np.clip(np.floor((sr - rs) / 3) + 1, 0, SPEC['sunken']['depth'])
    H = np.where(rs < sr, np.maximum(H, G0 + sunk), H)
    H = slope_limit(H)
    # hard-flat play zones
    flat = np.zeros((512, 512), bool)
    for (x0, x1, y0, y1) in ((84, 256, 150, 362), (120, 256, 380, 470)):
        flat |= (fx >= x0) & (fx <= x1) & (Y >= y0) & (Y <= y1)
    H[flat] = G0
    H = slope_limit(H, keep=flat | pl)
    return H.astype(int)


def slope_limit(H, keep=None, iters=40):
    """Limit 4-neighbour height steps to 1 so the natural terrain is walkable (1-voxel auto-step)."""
    H = H.copy()
    for _ in range(iters):
        n = np.minimum.reduce([np.roll(H, 1, 0), np.roll(H, -1, 0), np.roll(H, 1, 1), np.roll(H, -1, 1)])
        # z points down: a cell more than 1 below its highest neighbour is raised to within 1 of it
        hi = H > n + 1
        new = np.where(hi, n + 1, H)
        if keep is not None:
            new = np.where(keep, H, new)
        if (new == H).all():
            break
        H = new
    return H


def castle_footprint():
    c = SPEC['curtain']
    fp = np.zeros((512, 512), bool)
    fp[c['x_out']:512 - c['x_out'] + 1, c['y_n']:c['y_s'] + 1] = True
    xs, ys = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    for (tx, ty) in SPEC['corner']['c']:
        for X in (tx, 512 - tx):
            fp |= np.hypot(xs + 0.5 - (X + 0.5), ys + 0.5 - (ty + 0.5)) <= SPEC['corner']['r'] + 1
    for (tx, ty) in SPEC['drums']['c']:
        for X in (tx, 512 - tx):
            fp |= np.hypot(xs + 0.5 - (X + 0.5), ys + 0.5 - (ty + 0.5)) <= SPEC['drums']['r'] + 1
    return fp


def moat(H, F):
    fp = castle_footprint()
    d = ndi.distance_transform_edt(~fp)
    mo = SPEC['moat']
    z = np.clip(np.rint(mo['bed'] - np.maximum(0, d - mo['flat'])), G0, mo['bed'])
    ring = (d > 0) & (d <= mo['width'])
    xs = np.arange(512)[:, None]; ys = np.arange(512)[None, :]
    cw = ((ys >= SPEC['causeway_y'][0]) & (ys <= SPEC['causeway_y'][1])) & ((xs < 172) | (xs > 340))
    ring &= ~cw
    H = np.where(ring, np.maximum(H, z), H).astype(int)
    F['moat'] = ring
    F['footprint'] = fp
    return H


def voxelize(V, H, F):
    zz = np.arange(64)[None, None, :]
    solid = zz >= H[:, :, None]
    depth = zz - H[:, :, None]
    mat = np.where(depth >= 6, ROCK, EARTH)
    mat = np.where(depth == 0, GRASS, mat)
    V.m[:] = np.where(solid, mat, AIR).astype(np.uint8)
    V.m[:, :, 63] = ROCK
    F['H'] = H


def paint_top(V, mask, mat, H=None):
    xs, ys = np.nonzero(mask)
    for x, y in zip(xs, ys):
        g = V.ground(x, y)
        if V.m[x, y, g] in (GRASS, MUD, DIRT_GREY, PATH, MOSS_GROUND, LEAFLITTER, EARTH, COBBLE, FLAG, FURROW):
            V.m[x, y, g] = mat


def poly_mask(polys):
    m = np.zeros((512, 512), bool)
    for pts, w in polys:
        for (p, q) in zip(pts[:-1], pts[1:]):
            n = int(max(abs(q[0] - p[0]), abs(q[1] - p[1])) * 2) + 1
            for k in range(n + 1):
                x = p[0] + (q[0] - p[0]) * k / n
                y = p[1] + (q[1] - p[1]) * k / n
                r = w / 2
                for xx in range(max(int(math.floor(x - r)), 0), min(int(math.ceil(x + r)), 511) + 1):
                    for yy in range(max(int(math.floor(y - r)), 0), min(int(math.ceil(y + r)), 511) + 1):
                        if (xx + 0.5 - x) ** 2 + (yy + 0.5 - y) ** 2 <= r * r:
                            m[xx, yy] = True
    return m


def ground_paint(V, F):
    """Dead grass / muddy brown / grey dirt variation, paths and cobbles (west half; mirrored later)."""
    H = F['H']
    n1 = fold_x(fbm2((512, 512), 16, 3, 'gp1', SEED)); n2 = fold_x(fbm2((512, 512), 7, 2, 'gp2', SEED))
    xs, ys = np.nonzero(np.ones((512, 512), bool))
    top = V.m[xs, ys, H[xs, ys]]
    g = top == GRASS
    mud = g & (n1[xs, ys] < 0.36)
    grey = g & (n2[xs, ys] > 0.68) & ~mud
    V.m[xs[mud], ys[mud], H[xs[mud], ys[mud]]] = MUD
    V.m[xs[grey], ys[grey], H[xs[grey], ys[grey]]] = DIRT_GREY
    # moat bed: mud and grey silt
    mo = F['moat']
    sel = mo & (H >= SPEC['moat']['bed'] - 1)
    a, b = np.nonzero(sel)
    V.m[a, b, H[a, b]] = np.where(n2[a, b] > 0.55, DIRT_GREY, MUD).astype(np.uint8)
    # paths (west half)
    paths = [
        ([(98, 256), (140, 256), (164, 256)], 13),                              # front to the Crown Gate
        ([(118, 234), (118, 222), (122, 206), (136, 196), (150, 195)], 5),       # camp -> NW breach bridge
        ([(118, 278), (118, 290), (122, 306), (136, 316), (150, 317)], 5),       # camp -> SW breach bridge
        ([(96, 256), (70, 256), (62, 256)], 4),                                  # camp -> stone circle
        ([(118, 232), (114, 200), (112, 160), (120, 132), (140, 110), (180, 104), (256, 104)], 4),   # to graveyard
        ([(256, 104), (256, 72)], 5),                                            # graveyard -> chapel
        ([(256, 104), (256, 132)], 6),                                           # graveyard -> north bridge
        ([(118, 280), (114, 320), (114, 360), (126, 400), (140, 420)], 4),      # camp -> village
        ([(46, 241), (40, 200), (36, 156)], 3), ([(46, 271), (40, 312), (36, 356)], 3),   # woods -> shrines
    ]
    pm = poly_mask(paths)
    pm &= fx_of(np.arange(512))[:, None] <= 256
    F['path_mask'] = pm
    paint_top(V, pm, PATH)


# ============================================================================== castle

INTERIORS = []          # (name, x, y, floor_top_z) sample points for the accessibility check (west half)


def interior(name, x, y, z):
    INTERIORS.append((name, int(x), int(y), int(z)))


def stair_run(V, cells, base_top, mat=PLANK, clear_above=None):
    """Straight 1-wide stair: cells[i] gets a solid step whose top is base_top - (i + 1), filled down to the
    floor below. clear_above: z of the floor slab above, opened over the steps that need head room."""
    for i, (x, y) in enumerate(cells):
        top = base_top - (i + 1)
        V.box(x, x, y, y, top, base_top - 1, mat)
        if clear_above is not None and top - 4 <= clear_above:      # head room to step up onto the next
            V.clear(x, x, y, y, clear_above - 1, clear_above)
            V.clear(x, x, y, y, top - 3, top - 1)


def arch_top(dy, w, R, spring):
    """Underside z of a pointed (two-centred) arch at offset dy from its centre; w = half span."""
    t = abs(dy) + (R - w)
    if t > R:
        return spring
    return spring - math.sqrt(R * R - t * t)


def ruin_noise(n, tag, amp=8, base=0.55):
    v = fbm2((max(n, 4), 4), 9, 2, tag, SEED)[:, 0]
    return np.maximum(0, np.rint((v - base) * amp * 3)).astype(int)


def curtain_run(V, axis, fixed0, fixed1, a0, a1, top, outer_side, rng, tag, ruin=0.55, ruin_amp=6,
                merlons=True, buttress=True):
    """A straight curtain wall. axis='y' runs along y (fixed x range fixed0..fixed1); outer_side = -1/+1 on the
    fixed axis. Body from the ground up to `top`, ruined top, merlons, buttresses, string course, slits."""
    n = a1 - a0 + 1
    rn = ruin_noise(n, tag, ruin_amp, ruin)
    outer = fixed0 if outer_side < 0 else fixed1
    inner = fixed1 if outer_side < 0 else fixed0
    for i in range(n):
        a = a0 + i
        t = top + int(rn[i])
        for f in range(fixed0, fixed1 + 1):
            x, y = (f, a) if axis == 'y' else (a, f)
            V.column_to_ground(x, y, t, STONE)
        # merlons (3 on / 2 off) on the outer two voxels, parapet lip on the inner voxel
        if merlons and rn[i] == 0:
            for f in (outer, outer - outer_side * -1 if False else outer + (1 if outer_side < 0 else -1)):
                x, y = (f, a) if axis == 'y' else (a, f)
                if (a % 5) < 3:
                    V.box(x, x, y, y, t - 3, t - 1, STONE)
                else:
                    V.put(x, y, t - 1, STONE)
            x, y = (inner, a) if axis == 'y' else (a, inner)
            V.put(x, y, t - 1, STONE_DK)
        elif rn[i] > 0:
            # jagged top: knock out a few top voxels
            for f in range(fixed0, fixed1 + 1):
                if hash3(f, a, t, 11) < 0.35:
                    x, y = (f, a) if axis == 'y' else (a, f)
                    V.put(x, y, t, AIR)
        # string course (outward ledge) and arrow slit marks
        so = outer + outer_side
        x, y = (so, a) if axis == 'y' else (a, so)
        if t <= 31:
            V.put(x, y, 32, STONE_TRIM)
        if a % 13 == 6 and t <= 27:
            for z in range(26, 31):
                x2, y2 = (outer, a) if axis == 'y' else (a, outer)
                V.put(x2, y2, z, WINDOW)
    if buttress:
        for a in range(a0 + 8, a1 - 4, 22):
            if axis == 'y' and (218 <= a <= 294 or any(b0 - 10 <= a <= b1 + 8 for b0, b1 in SPEC['breach_y'])):
                continue
            for k in range(1, 4):
                f = outer + outer_side * k
                ztop = 26 + (k - 1) * 2
                for aa in range(a, a + 3):
                    x, y = (f, aa) if axis == 'y' else (aa, f)
                    V.column_to_ground(x, y, ztop, STONE_DK)


def round_tower(V, cx, cy, r, top, rng, roof=False, ruined=False, tag='t', wall=3, windows=True,
                roof_mat=SLATE_P, base_out=1, door=None, name='tower'):
    """Round tower centred on cell (cx, cy): wall ring `wall` thick, battered foot, corbel ring, crenellated
    parapet, optional conical slate roof, optional ruined crown. The interior is a real room: cleared, paved,
    lit by arrow-slit openings at head height, entered by a doorway cut through the ring toward `door`."""
    R = int(r) + 3
    ang_n = fbm2((64, 4), 6, 2, tag, SEED)[:, 0]
    rin = r - wall + 0.5
    for dx in range(-R, R + 1):
        for dy in range(-R, R + 1):
            d = math.hypot(dx, dy)
            x, y = cx + dx, cy + dy
            a = (math.atan2(dy, dx) + math.pi) / (2 * math.pi)
            t = top
            if ruined:
                t = top + int(max(0, (ang_n[int(a * 63)] - 0.35) * 40))
            if rin < d <= r + 0.5:
                V.column_to_ground(x, y, t, STONE)
            elif d <= rin:
                V.clear(x, x, y, y, 0, G0 - 1)                     # hollow room (removes wall runs crossing it)
                V.m[x, y, G0] = FLAG_DK
            if r + 0.5 < d <= r + base_out + 0.5:
                V.column_to_ground(x, y, 45, STONE_DK)            # battered foot
            if not ruined:
                if r + 0.5 < d <= r + 1.5:
                    V.box(x, x, y, y, top + 1, top + 2, STONE_TRIM)    # corbel ring (machicolation)
                    V.put(x, y, top + 3, STONE_TRIM)
                if r - 1.5 < d <= r + 1.5:
                    k = int(a * (2 * math.pi * r) / 2.5)
                    if k % 2 == 0:
                        V.box(x, x, y, y, top - 3, top, STONE)
                    else:
                        V.put(x, y, top, STONE)
    if windows:
        nwin = max(4, int(2 * math.pi * r / 9))
        for i in range(nwin):
            a = 2 * math.pi * (i + 0.5) / nwin
            # high slits: glazed / glowing; low slits at head height: real openings through the ring
            wx = cx + int(round(math.cos(a) * r)); wy = cy + int(round(math.sin(a) * r))
            zt = top + 12 if not ruined else 32
            for z in range(zt, zt + 5):
                if V.get(wx, wy, z) == STONE:
                    V.put(wx, wy, z, WINDOW if (i % 3) else GLOW_GREEN)
            if i % 2 == 0:
                for rr in np.arange(rin - 0.5, r + 1.0, 0.5):
                    px = cx + int(round(math.cos(a) * rr)); py = cy + int(round(math.sin(a) * rr))
                    if V.get(px, py, 38) in (STONE, STONE_DK, WINDOW):
                        V.clear(px, px, py, py, 37, 39)
    if door is not None:
        ddx, ddy = door
        n = math.hypot(ddx, ddy); ux, uy = ddx / n, ddy / n
        for rr in np.arange(rin - 1.0, r + 2.0, 0.5):
            for w in (-1, 0, 1):
                px = cx + int(round(ux * rr - uy * w)); py = cy + int(round(uy * rr + ux * w))
                V.clear(px, px, py, py, G0 - 4, G0 - 1)
                V.m[px, py, G0] = FLAG_DK
        interior(name, cx - int(round(ux * 3)), cy - int(round(uy * 3)), G0)
    if roof:
        rr = r - 0.5
        z = top - 1
        k = 0
        while rr > 0.3 and z >= 0:
            for dx in range(-int(rr) - 1, int(rr) + 2):
                for dy in range(-int(rr) - 1, int(rr) + 2):
                    d = math.hypot(dx, dy)
                    if d <= rr and d > rr - 2.2:
                        V.put(cx + dx, cy + dy, z, roof_mat if (k % 3) else SLATE)
            rr -= 1.45; z -= 1; k += 1
        V.box(cx, cx, cy, cy, max(z - 2, 0), z, IRON)
        hx, hy = cx + int(r * 0.35), cy - int(r * 0.25)
        for dz in range(top - 9, top - 3):
            for dx in range(-2, 3):
                for dy in range(-2, 2):
                    if V.get(hx + dx, hy + dy, dz) in (roof_mat, SLATE) and hash3(hx + dx, hy + dy, dz, 5) < 0.7:
                        V.put(hx + dx, hy + dy, dz, AIR)
    if door is not None and not ruined:
        # inside: a brazier and a weapon rack against the far wall
        brazier(V, cx - int(round(ux * (rin - 3))), cy - int(round(uy * (rin - 3))), G0, glow=EMBER)


def build_castle(V, F, rng):
    c = SPEC['curtain']
    xo, th, yn, ys_ = c['x_out'], c['thick'], c['y_n'], c['y_s']
    xi = xo + th - 1                                                       # 171
    top = c['top']
    # ---- interior floor: flagstones over the whole ward
    for x in range(xi + 1, 257):
        for y in range(yn + th, ys_ - th + 1):
            V.m[x, y, G0] = FLAG
    # ---- curtain walls
    curtain_run(V, 'y', xo, xi, yn + th, ys_ - th, top, -1, rng, 'cw_w', ruin=0.6, ruin_amp=5)
    curtain_run(V, 'x', yn, yn + th - 1, xi + 1, 256, top, -1, rng, 'cw_n', ruin=0.5, ruin_amp=7)
    curtain_run(V, 'x', ys_ - th + 1, ys_, xi + 1, 256, top, +1, rng, 'cw_s', ruin=0.45, ruin_amp=8)
    # ---- corner towers (north pair roofed, south pair shattered)
    (tnx, tny), (tsx, tsy) = SPEC['corner']['c']
    round_tower(V, tnx, tny, SPEC['corner']['r'], SPEC['corner']['top_n'], rng, roof=True, tag='tn',
                door=(0.15, 1), name='NW tower room')
    round_tower(V, tsx, tsy, SPEC['corner']['r'], 16, rng, roof=False, ruined=True, tag='ts',
                door=(0.15, -1), name='SW tower room')
    # ---- Crown Gate: gatehouse block + drum towers + pointed arch + raised portcullis
    gt = SPEC['gate']
    gy0, gy1 = gt['y']; gx0, gx1 = gt['x']
    for (dx_, dy_) in SPEC['drums']['c']:
        round_tower(V, dx_, dy_, SPEC['drums']['r'], SPEC['drums']['top'], rng, roof=False, tag=f'd{dy_}',
                    wall=3, windows=True, door=(1, 0), name='gate drum room')
    for x in range(gx0, gx1 + 1):
        for y in range(gy0 - 3, gy1 + 4):
            V.column_to_ground(x, y, gt['top'], STONE)
    cy = (gy0 + gy1) / 2
    w = (gy1 - gy0 + 1) / 2
    for y in range(gy0, gy1 + 1):
        zt = arch_top(y + 0.5 - (cy + 0.5), w, gt['R'], gt['spring'])
        zt_i = int(math.ceil(zt))
        for x in range(gx0, gx1 + 1):
            V.clear(x, x, y, y, zt_i, G0 - 1)
        # voussoirs on both faces (trim ring 2 deep into the soffit)
        for x in (gx0, gx0 + 1, gx1 - 1, gx1):
            for z in (zt_i - 1, zt_i - 2):
                if V.get(x, y, z) == STONE:
                    V.put(x, y, z, STONE_TRIM)
        # raised portcullis hanging in the arch (grid, x = middle)
        px = (gx0 + gx1) // 2
        if zt_i <= 26:
            for z in range(zt_i, 27):
                if y % 2 == 0 or z % 3 == 0:
                    V.put(px, y, z, IRON)
            if y % 2 == 0:
                V.put(px, y, 27, IRON)
    # crenellations + machicolation on the gatehouse
    for y in range(gy0 - 3, gy1 + 4):
        V.put(gx0 - 1, y, gt['top'] + 2, STONE_TRIM)
        V.put(gx0 - 1, y, gt['top'] + 1, STONE_TRIM)
        if y % 4 < 2:
            V.box(gx0, gx0, y, y, gt['top'] - 3, gt['top'] - 1, STONE)
            V.box(gx0 - 1, gx0 - 1, y, y, gt['top'] - 3, gt['top'], STONE)
        V.put(gx1, y, gt['top'] - 1, STONE_DK)
    # carved crown emblem above the arch (outer face), gold inlay
    crown_relief(V, gx0 - 1, int(cy), 18)
    # ---- breaches in the west wall with collapsed bridges and rubble ramps
    for (b0, b1) in SPEC['breach_y']:
        breach(V, F, xo, xi, b0, b1, rng)
    # ---- north range: Great Hall (throne room); south range: Royal Apartments
    great_hall(V, rng)
    apartments(V, rng)
    barracks(V, rng)
    V.clear(182, 188, 156, 158, G0 - 4, G0 - 1)          # alley behind the barracks opens into the NW tower room
    V.clear(182, 188, 354, 356, G0 - 4, G0 - 1)          # same behind the castle chapel (SW tower)
    castle_chapel(V, rng)
    # ---- north / south collapsed bridges over the moat (on the axis)
    collapsed_bridge(V, 248, 264, yn - 16, yn - 1, 'y', rng)
    collapsed_bridge(V, 248, 264, ys_ + 1, ys_ + 16, 'y', rng, south=True)
    courtyard_dressing(V, F, rng)


def crown_relief(V, x, yc, zc):
    """Crown emblem in relief on a wall face at x (one voxel proud), centred on (yc, zc)."""
    pts = []
    for dy in range(-6, 7):
        pts += [(dy, 0), (dy, 1)]
    for dy in (-6, -3, 0, 3, 6):
        h = 4 if dy in (-6, 0, 6) else 3
        for k in range(2, 2 + h):
            pts.append((dy, k))
    for dy, k in pts:
        V.put(x, yc + dy, zc - k, GOLD)
    V.put(x, yc, zc - 1, GEM_RED); V.put(x, yc - 3, zc - 1, GEM_CYAN); V.put(x, yc + 3, zc - 1, GEM_CYAN)


def breach(V, F, xo, xi, b0, b1, rng):
    mid = (b0 + b1) / 2; half = (b1 - b0) / 2
    for y in range(b0 - 6, b1 + 7):
        e = abs(y + 0.5 - (mid + 0.5))
        for x in range(xo - 1, xi + 1):                                   # xo - 1: the string course too
            if e <= half:
                cut_to = G0 - 1
            else:
                cut_to = G0 - 1 - int((e - half) * 3.2 + hash3(x, y, 0, 3) * 3)
            col = V.m[x, y]
            for z in range(0, max(cut_to, 0) + 1):
                if z < G0:
                    col[z] = AIR
            if e <= half:
                col[G0] = RUBBLE
    # rubble ramp in the moat (1 step per cell) from the moat bed up to the breach floor
    bed = SPEC['moat']['bed']
    for y in range(b0, b1 + 1):
        for x in range(xo - (bed - G0) - 1, xo):
            z = min(G0 + (xo - 1 - x), bed)
            V.column_to_ground(x, y, z, RUBBLE)
    # rubble heaps either side of the breach (inside and outside), off the walking line
    for (yy, side) in ((b0 - 4, -1), (b1 + 4, 1)):
        rubble(V, xi + 4, yy + side * 2, G0, 4, rng, h=3)
        rubble(V, xo - 10, yy + side * 3, G0, 3, rng, h=2)
    # collapsed bridge: two stub spans with a gap over the moat
    for y in range(b0 - 2, b1 + 3):
        edge = y in (b0 - 2, b1 + 2)
        for x in range(xo - 16, xo - 10):
            V.column_to_ground(x, y, G0 - 1 if not edge else G0 - 2, STONE if not edge else STONE_TRIM)
        V.put(xo - 10, y, G0 - 1, STONE_DK)                           # broken lip
    for y in range(b0 - 2, b1 + 3):
        for x in range(xo - 16, xo - 10):
            if y in (b0 - 2, b1 + 2):
                V.put(x, y, G0 - 2, STONE_TRIM)
    # fallen span pieces on the moat bed beside the ramp
    rubble(V, xo - 8, b0 - 3, bed, 2, rng, h=2, mats=[STONE, STONE_TRIM])
    rubble(V, xo - 7, b1 + 3, bed, 2, rng, h=2, mats=[STONE, STONE_TRIM])


def collapsed_bridge(V, x0, x1, y0, y1, axis, rng, south=False):
    """Stone bridge across the moat on piers; the middle span has fallen (no crossing)."""
    L = y1 - y0 + 1
    gap = (y0 + L // 2 - 3, y0 + L // 2 + 2)
    for y in range(y0, y1 + 1):
        if gap[0] <= y <= gap[1]:
            continue
        for x in range(x0, x1 + 1):
            V.box(x, x, y, y, G0 - 2, G0 - 1, STONE)                    # 2-thick deck
            if x in (x0, x1):
                V.put(x, y, G0 - 3, STONE_TRIM)
                if y % 3 == 0:
                    V.put(x, y, G0 - 4, STONE_TRIM)
        # pier under deck at a quarter span
    for yy in (y0 + 2, y1 - 2):
        for x in range(x0 + 2, x1 - 1):
            V.column_to_ground(x, yy, G0, STONE_DK)
            V.column_to_ground(x, yy + (1 if yy < gap[0] else -1), G0, STONE_DK)
    # jagged broken ends
    for y in (gap[0] - 1, gap[1] + 1):
        for x in range(x0, x1 + 1):
            if hash3(x, y, 1, 9) < 0.5:
                V.put(x, y, G0 - 2, AIR)
    # fallen blocks in the moat
    bed = SPEC['moat']['bed']
    for k in range(5):
        rx = int(rng.integers(x0, x1 + 1)); ry = int(rng.integers(gap[0], gap[1] + 1))
        rubble(V, rx, ry, bed, 2, rng, h=2, mats=[STONE, STONE_TRIM, RUBBLE])
    # bricked-up postern where the bridge meets the wall
    wy = y1 + 1 if not south else y0 - 1
    for x in range(x0 + 3, x1 - 2):
        for z in range(G0 - 9, G0):
            if V.get(x, wy, z) == STONE:
                V.put(x, wy, z, BRICK)


def great_hall(V, rng):
    hx0, hx1 = SPEC['hall']['x']; hy0, hy1 = SPEC['hall']['y']
    top = SPEC['hall']['top']
    yn_in = SPEC['curtain']['y_n'] + SPEC['curtain']['thick']          # 156
    # raise the curtain behind the hall into the hall's north wall
    for x in range(hx0, 257):
        for y in range(SPEC['curtain']['y_n'], yn_in):
            V.column_to_ground(x, y, top, STONE)
    # west gable wall (x 204..207) with a stepped gable and a stained rose window
    for x in range(hx0, hx0 + 4):
        for y in range(yn_in, hy1 + 1):
            dyc = abs(y - (yn_in + hy1) / 2)
            gz = top - int(max(0, (22 - dyc)) * 0.45)
            V.column_to_ground(x, y, gz, STONE)
    rose(V, hx0 + 3, (yn_in + hy1) // 2, 22, 7, face=+1)
    # buttresses outside the gable
    for y in (yn_in + 6, hy1 - 6):
        for x in range(hx0 - 3, hx0):
            V.column_to_ground(x, y, top + 8 + (hx0 - x), STONE_DK)
            V.column_to_ground(x, y + 1, top + 8 + (hx0 - x), STONE_DK)
    # north wall lancets (stained glass in the wall face) between interior shafts
    for x in range(hx0 + 10, 252, 12):
        lancet(V, x, yn_in - 1, 34, 13, axis='x', face=+1)
        V.box(x + 5, x + 6, yn_in, yn_in, top + 2, G0 - 1, STONE_TRIM)          # wall shaft
    # south arcade facing the courtyard
    ay0, ay1 = hy1 - 4, hy1
    piers = [(208, 212), (227, 231), (246, 250)]
    for x in range(hx0 + 4, 257):
        for y in range(ay0, ay1 + 1):
            V.column_to_ground(x, y, top, STONE)
    bays = [(213, 226), (232, 245), (251, 261)]
    for i, (b0, b1) in enumerate(bays):
        w = (b1 - b0 + 1) / 2; cxb = (b0 + b1) / 2
        spring = 31 if i < 2 else 33
        R = w + 2.0
        for x in range(b0, b1 + 1):
            zt = int(math.ceil(arch_top(x - cxb, w, R, spring)))
            V.clear(x, x, ay0, ay1, zt, G0 - 1)
            for y in (ay0, ay1):
                for z in (zt - 1, zt - 2):
                    if V.get(x, y, z) == STONE:
                        V.put(x, y, z, STONE_TRIM)
    for (p0, p1) in piers:                                                # clustered pier shafts
        for y in (ay1 + 1,):
            V.box(p0 + 1, p1 - 1, y, y, top + 4, G0 - 1, STONE_TRIM)
    # collapse over the west bay: the wall above the arch has fallen in a V
    for x in range(213, 228):
        e = abs(x - 220)
        cut = 24 - e
        for y in range(ay0, ay1 + 1):
            V.clear(x, x, y, y, 0, max(cut, top))
    rubble(V, 220, hy1 + 4, G0, 4, rng, h=3)
    rubble(V, 219, hy1 - 8, G0, 4, rng, h=3)
    # parapet merlons on the arcade top
    for x in range(232, 257):
        if x % 5 < 3:
            V.box(x, x, ay1, ay1, top - 3, top - 1, STONE)
    # floor: marble checker; dais; throne; banner; columns; the fallen Hollow Crown
    for x in range(hx0 + 4, 257):
        for y in range(yn_in, ay0):
            V.m[x, y, G0] = MARBLE_W if ((x // 3 + y // 3) % 2 == 0) else MARBLE_B
    for (k, (x0, y1)) in enumerate(((234, 172), (239, 168), (244, 164))):
        V.box(x0, 256, yn_in, y1, G0 - 1 - k, G0 - 1 - k, STONE_TRIM if k == 0 else MARBLE_B)
        for x in range(x0, 257):
            V.put(x, y1, G0 - 1 - k, STONE_TRIM)
    throne(V, 256, yn_in, G0 - 3)
    # huge torn banner behind the throne (on the north wall face)
    for x in range(236, 248):                                            # banners flanking the throne
        for z in range(12, 33):
            if z < 31 or (x % 3 != 0):
                V.put(x, yn_in, z, CLOTH_PURPLE)
    for x in range(238, 246):
        for z in (17, 18):
            V.put(x, yn_in, z, GOLD)
    for x in (238, 241, 244):
        V.box(x, x, yn_in, yn_in, 14, 16, GOLD)
    # interior column rows (some snapped, one fallen across the floor)
    for (x, y, h) in ((218, 170, 28), (232, 170, 12), (218, 186, 6), (232, 186, 28), (246, 186, 20)):
        V.box(x, x + 2, y, y + 2, G0 - h, G0 - 1, STONE_TRIM)
        V.box(x - 1, x + 3, y - 1, y + 3, G0 - 1, G0 - 1, STONE_DK)
        if h >= 20:
            V.box(x - 1, x + 3, y - 1, y + 3, G0 - h - 1, G0 - h, STONE_DK)
    for k in range(18):                                                     # fallen drum column
        V.box(222 + k, 222 + k, 177, 179, G0 - 3, G0 - 1, STONE_TRIM if k % 4 else STONE_DK)
    # charred roof beams fallen into the hall
    V.line4((236, 160, G0 - 1), (226, 190, G0 - 1), TIMBER_CHAR, thick=0)
    V.line4((237, 160, G0 - 1), (227, 190, G0 - 1), TIMBER_CHAR)
    V.line4((210, 176, G0 - 1), (240, 182, G0 - 1), TIMBER_CHAR)
    # long banquet table, broken
    V.box(214, 244, 191, 193, G0 - 3, G0 - 3, PLANK)
    for x in (214, 222, 230, 238, 244):
        V.box(x, x, 191, 193, G0 - 2, G0 - 1, TIMBER)
    V.clear(228, 233, 191, 193, G0 - 3, G0 - 3)
    V.line4((228, 192, G0 - 3), (233, 192, G0 - 1), PLANK)
    # ghost candelabra
    for (x, y) in ((212, 162), (240, 176), (212, 190)):
        V.box(x, x, y, y, G0 - 5, G0 - 1, IRON)
        for (a, b) in ((-1, 0), (1, 0), (0, 0)):
            V.put(x + a, y + b, G0 - 5 if a else G0 - 6, IRON if a else GLOW_GREEN)
            if a:
                V.put(x + a, y + b, G0 - 6, GLOW_GREEN)
    hollow_crown(V, 256, 182, G0)
    interior('great hall', 214, 184, G0)


def rose(V, x, yc, zc, r, face=1):
    """Stained-glass rose window flush in a wall plane at x (tracery spokes and ring in stone trim)."""
    glass = [CLOTH_PURPLE, GLOW_GREEN, CLOTH_BLOOD, GEM_CYAN]
    for dy in range(-r - 1, r + 2):
        for dz in range(-r - 1, r + 2):
            d = math.hypot(dy, dz)
            if d <= r + 1:
                y, z = yc + dy, zc + dz
                a = math.atan2(dz, dy)
                spoke = abs(((a / (2 * math.pi)) * 12) % 1 - 0.5) > 0.42
                if d > r - 0.6 or d < 1.6 or spoke or abs(d - r * 0.55) < 0.5:
                    mat = STONE_TRIM
                else:
                    mat = glass[int(((a / (2 * math.pi)) * 12) % 12 + (d > r * 0.55) * 2) % 4]
                for xx in (x, x - face * 1 if False else x):
                    if V.get(xx, y, z) != AIR:
                        V.put(xx, y, z, mat)


def lancet(V, a, b, z_bot, h, axis='x', face=1, w=3):
    """Tall pointed window of stained glass painted into a wall at fixed coord b (axis x: wall along x)."""
    main = (CLOTH_PURPLE, CLOTH_BLOOD)[int(hash3(a, b, 0, 77) * 2)]
    for k in range(h):
        z = z_bot - k
        ww = w if k < h - 2 else (w - 2 if k == h - 1 else w - 1)
        for u in range(-(ww // 2), ww // 2 + 1):
            x, y = (a + u, b) if axis == 'x' else (b, a + u)
            if V.get(x, y, z) != AIR:
                if k == h // 2 or (u == 0 and ww == 3 and k < h - 2):
                    mat = STONE_TRIM                                      # mullion + transom
                elif k == h - 2 or k == 1:
                    mat = GLOW_GREEN                                      # pale-green border panes
                else:
                    mat = main
                V.put(x, y, z, mat)


def throne(V, cx, y0, zseat_base):
    """The black throne: stepped seat, tall spiked back against the north wall, gold trims, blood velvet."""
    z0 = zseat_base                     # top step surface z (the throne stands on it)
    V.box(cx - 6, cx, y0, y0 + 6, z0 - 3, z0, OBSIDIAN)                  # seat block
    V.box(cx - 4, cx, y0 + 2, y0 + 6, z0 - 3, z0 - 3, VELVET)
    V.box(cx - 7, cx - 6, y0, y0 + 7, z0 - 6, z0, OBSIDIAN)              # arm
    V.box(cx - 7, cx - 6, y0 + 7, y0 + 7, z0 - 7, z0 - 6, GOLD)
    V.box(cx - 6, cx, y0, y0 + 1, z0 - 20, z0 - 4, OBSIDIAN)             # back
    V.box(cx - 4, cx, y0 + 1, y0 + 1, z0 - 16, z0 - 6, VELVET)
    for (dx, h) in ((-6, 24), (-4, 22), (-2, 26), (0, 29)):
        V.box(cx + dx, cx + dx, y0, y0, z0 - h, z0 - 20, OBSIDIAN)
        V.put(cx + dx, y0, z0 - h - 1, GOLD)
    V.box(cx - 6, cx, y0 + 1, y0 + 1, z0 - 18, z0 - 18, GOLD)


def hollow_crown(V, cx, cy, g):
    """The fallen Hollow Crown: a giant tarnished-gold crown band (jewelled) with eight tall points capped by
    trefoil tips, lying tipped toward the throne; one point has snapped off and lies on the floor."""
    ro, ri = 7.5, 5.8
    for dx in range(-9, 10):
        for dy in range(-9, 10):
            d = math.hypot(dx, dy)
            if ri < d <= ro:
                a = math.atan2(dy, dx)
                tilt = int(round((-dy / ro) * 2.0))               # raised on the courtyard side
                hb = 4
                base = g - 1 - max(tilt, 0)
                if tilt > 0:
                    for k in range(tilt):                         # rests on its low edge: fill to the floor
                        V.put(cx + dx, cy + dy, g - 1 - k, CROWN_DK)
                for k in range(hb):
                    V.put(cx + dx, cy + dy, base - k, CROWN_DK if k == 0 else GOLD)
                seg = (a / (2 * math.pi)) * 8
                si = int(round(seg)) % 8
                if abs(seg - round(seg)) < 0.16 and d > ro - 1.3:
                    ph = 6 if si % 2 == 0 else 4
                    if si == 3:
                        ph = 1                                    # the snapped point
                    for k in range(ph):
                        V.put(cx + dx, cy + dy, base - hb - k, GOLD)
                    if ph > 1:
                        V.put(cx + dx, cy + dy, base - hb - ph, GEM_RED if si % 2 else GOLD)
                if abs(seg - round(seg) - 0.5) < 0.08 and d > ro - 1.2:
                    V.put(cx + dx, cy + dy, base - 2, GEM_CYAN if si % 2 else GEM_RED)
    V.box(cx - 14, cx - 10, cy + 8, cy + 8, g - 1, g - 1, GOLD)        # the snapped point on the floor
    V.put(cx - 9, cy + 8, g - 1, GEM_RED)


def apartments(V, rng):
    ax0, ax1 = SPEC['apart']['x']; ay0, ay1 = SPEC['apart']['y']
    top = SPEC['apart']['top']
    ys_in = SPEC['curtain']['y_s'] - SPEC['curtain']['thick']           # 356
    for x in range(ax0, 257):                                           # back wall = raised curtain
        for y in range(ys_in + 1, SPEC['curtain']['y_s'] + 1):
            V.column_to_ground(x, y, top, STONE)
    for x in range(ax0, ax0 + 4):                                       # west gable wall
        for y in range(ay0, ys_in + 1):
            V.column_to_ground(x, y, top, STONE)
    # gable over the roofed back half
    ry0 = 334
    for x in range(ax0, ax0 + 4):
        for y in range(ry0, ys_in + 1):
            k = min(y - ry0, ys_in - y)
            V.column_to_ground(x, y, top - k, STONE)
    # front wall (courtyard side) collapsed to an uneven sill, piers between rooms remain
    rn = ruin_noise(257 - ax0, 'apfront', 8, 0.4)
    for i, x in enumerate(range(ax0 + 4, 257)):
        tz = 36 - int(rn[i])
        pier = x in range(228, 232) or x >= 254
        for y in range(ay0, ay0 + 3):
            V.column_to_ground(x, y, top if pier else tz, STONE)
    # floors (timber) at z 32 and z 22 with a ragged front edge, partition walls
    for fz in (32, 22):
        edge = ruin_noise(257 - ax0, f'fl{fz}', 10, 0.35)
        for i, x in enumerate(range(ax0 + 4, 257)):
            y_start = ay0 + 3 + int(edge[i])
            V.box(x, x, y_start, ys_in, fz, fz, PLANK)
            V.box(x, x, ys_in, ys_in, fz - 1, fz - 1, TIMBER)
            if hash3(x, fz, 1, 4) < 0.15:
                V.put(x, y_start, fz + 1, PLANK)                      # hanging board
    for px in (228, 254):
        for x in range(px, px + 3 if px == 228 else 257):
            for y in range(ay0, ys_in + 1):
                V.column_to_ground(x, y, top, STONE)
        for z in (G0 - 1, 31, 21):                                    # doorways
            V.clear(px, px + 2 if px == 228 else 256, 338, 342, z - 4, z)
    # roof: steep slate over the back half; part collapsed with bare rafters
    for x in range(ax0 + 1, 257):
        for y in range(ry0 - 1, ys_in + 2):
            k = min(y - (ry0 - 1), ys_in + 1 - y)
            z = top - 1 - k
            if z >= 0:
                mat = SLATE_P if (k % 2 == 0) else SLATE
                V.put(x, y, z, mat)
                V.put(x, y, z + 1, mat)
    for x in range(232, 248):
        for y in range(ry0, ys_in):
            k = min(y - (ry0 - 1), ys_in + 1 - y)
            z = top - 1 - k
            V.clear(x, x, y, y, z, z + 1)
    for x in (234, 238, 242, 246):
        for y in range(ry0, ys_in):
            k = min(y - (ry0 - 1), ys_in + 1 - y)
            V.put(x, y, top - 1 - k, ROOF_BEAM)
    # chimneys
    for (x, y) in ((214, 352), (224, 352)):
        V.box(x, x + 2, y, y + 2, 1, 21, BRICK)
    # rooms: furniture per floor (bed, fireplace, wardrobe, table, paintings)
    for fz in (G0, 32, 22):
        for (rx0, rx1) in ((ax0 + 5, 227), (232, 253)):
            room(V, rx0, rx1, ay0 + 6, ys_in, fz, rng)
    # two places where the courtyard wall has fallen to the floor: walk into the ground-floor chambers
    for (g0_, g1_) in ((213, 220), (238, 244)):
        for x in range(g0_, g1_ + 1):
            V.clear(x, x, ay0, ay0 + 2, 0, G0 - 1)
            V.m[x, ay0:ay0 + 3, G0] = RUBBLE
    rubble(V, 210, ay0 - 3, G0, 3, rng, h=2)
    # stairs to the upper floors (west room): ground -> z 32 along x 208, z 32 -> z 22 along x 210
    stair_run(V, [(208, y) for y in range(340, 350)], G0, PLANK, clear_above=32)
    stair_run(V, [(210, y) for y in range(349, 339, -1)], 32, PLANK, clear_above=22)
    # window openings through the back wall (curtain) and the west gable on every floor
    for x in (212, 224, 235, 247):
        for (z0, z1) in ((38, 39), (28, 29), (18, 19)):
            V.clear(x, x + 1, ys_in + 1, SPEC['curtain']['y_s'], z0, z1)
    for (z0, z1) in ((38, 39), (28, 29), (18, 19)):
        V.clear(ax0, ax0 + 3, 324, 325, z0, z1)
    interior('apartments ground floor', 215, 335, G0)
    interior('apartments first floor', 215, 335, 32)
    interior('apartments second floor', 215, 335, 22)
    rubble(V, 244, ay0 - 2, G0, 3, rng, h=2)


def room(V, x0, x1, y0, y1, fz, rng):
    """Furnish one exposed chamber whose floor surface is z = fz (objects stand at fz - 1 ...)."""
    g = fz
    # fireplace in the back wall
    fx = (x0 + x1) // 2
    V.box(fx - 3, fx + 3, y1 - 1, y1, g - 6, g - 1, STONE_TRIM)
    V.box(fx - 1, fx + 1, y1 - 1, y1 - 1, g - 3, g - 1, AIR)
    V.put(fx, y1 - 1, g - 1, EMBER); V.put(fx - 1, y1 - 1, g - 1, ASH)
    # canopy bed
    bx = x0 + 2
    V.box(bx, bx + 5, y1 - 9, y1 - 2, g - 2, g - 1, VELVET)
    V.box(bx, bx + 5, y1 - 9, y1 - 9, g - 2, g - 1, TIMBER)
    for (a, b) in ((bx, y1 - 9), (bx + 5, y1 - 9), (bx, y1 - 2), (bx + 5, y1 - 2)):
        V.box(a, a, b, b, g - 6, g - 1, TIMBER)
    V.box(bx, bx + 5, y1 - 9, y1 - 2, g - 7, g - 7, CLOTH_PURPLE)
    V.box(bx, bx + 5, y1 - 9, y1 - 9, g - 6, g - 5, CLOTH_PURPLE)
    # wardrobe + table + painting
    V.box(x1 - 3, x1, y1 - 2, y1, g - 6, g - 1, PLANK)
    tx = x1 - 6
    V.box(tx - 2, tx + 1, y1 - 12, y1 - 10, g - 2, g - 2, PLANK)
    V.put(tx - 2, y1 - 12, g - 1, TIMBER); V.put(tx + 1, y1 - 10, g - 1, TIMBER)
    V.put(tx, y1 - 11, g - 3, CANDLE)
    V.box(x0 + 9, x0 + 12, y1, y1, g - 7, g - 5, GOLD)
    V.box(x0 + 10, x0 + 11, y1, y1, g - 7, g - 6, CLOTH_BLOOD)


def barracks(V, rng):
    """NW ward building: two-storey barracks, upper floor half fallen in, a stair up to what is left of it,
    window openings on both floors."""
    x0, x1, y0, y1 = 175, 200, 159, 184
    top = 24
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            if x in (x0, x0 + 1, x1 - 1, x1) or y in (y0, y0 + 1, y1 - 1, y1):
                t = top + int(max(0, (hash3(x // 3, y // 3, 0, 2) - 0.45) * 14)) if y >= y1 - 1 or x >= x1 - 1 \
                    else top
                V.column_to_ground(x, y, t, STONE if (x + y) % 9 else BRICK)
    for x in range(x0 + 2, x1 - 1):
        for y in range(y0 + 2, y1 - 1):
            V.clear(x, x, y, y, top, G0 - 1)
            V.m[x, y, G0] = FLAG_DK
            if not (x > 186 and y > 170) and not (math.hypot(x - 192, y - 174) < 7):
                V.put(x, y, 33, PLANK)
    # door (south, to the lane) + side door (east, to the ward)
    V.clear(186, 190, y1 - 1, y1, G0 - 5, G0 - 1)
    V.clear(x1 - 1, x1, 168, 172, G0 - 4, G0 - 1)
    # window openings: ground floor (z 37-39) and upper floor (z 29-31), west and north walls
    for y in (164, 176):
        V.clear(x0, x0 + 1, y, y + 1, 37, 39); V.clear(x0, x0 + 1, y, y + 1, 29, 31)
    for x in (182, 194):
        V.clear(x, x + 1, y0, y0 + 1, 37, 39); V.clear(x, x + 1, y0, y0 + 1, 29, 31)
    # fireplace, bunks, barrels
    V.box(x0 + 2, x0 + 3, 168, 174, G0 - 6, G0 - 1, STONE_TRIM)
    V.box(x0 + 3, x0 + 3, 170, 172, G0 - 3, G0 - 1, AIR)                 # hearth opens into the room
    V.put(x0 + 3, 171, G0 - 1, EMBER)
    for y in (163, 167):
        V.box(186, 192, y, y + 2, G0 - 2, G0 - 2, PLANK); V.box(186, 192, y, y + 2, G0 - 5, G0 - 5, PLANK)
        V.box(186, 186, y, y, G0 - 5, G0 - 1, TIMBER); V.box(192, 192, y + 2, y + 2, G0 - 5, G0 - 1, TIMBER)
    for (x, y) in ((196, 164), (196, 167), (178, 180)):
        barrel(V, x, y, G0)
    # stair along the north wall up to the upper floor (floor top z 33): 8 steps x 177..184, landing x 185
    stair_run(V, [(x, 161) for x in range(177, 185)], G0, PLANK, clear_above=33)
    V.box(177, 185, 162, 162, G0 - 1, G0 - 1, AIR)        # keep the walkway beside the stair open
    # upper floor furniture
    V.box(178, 183, 165, 167, 32, 32, PLANK); V.put(178, 165, 31, CANDLE)
    barrel(V, 182, 178, 33)
    rubble(V, 193, 176, G0, 3, rng, h=2, mats=[PLANK, TIMBER_CHAR, RUBBLE])
    interior('barracks ground floor', 182, 172, G0)
    interior('barracks upper floor', 180, 170, 33)


def castle_chapel(V, rng):
    """SW ward: the castle chapel, roofless, stained lancets, altar, doors on both long sides."""
    x0, x1, y0, y1 = 175, 200, 329, 354
    top = 22
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            if x in (x0, x0 + 1, x1 - 1, x1) or y in (y0, y0 + 1, y1 - 1, y1):
                V.column_to_ground(x, y, top, STONE)
    for x in range(x0 + 2, x1 - 1):
        for y in range(y0 + 2, y1 - 1):
            V.clear(x, x, y, y, 0, G0 - 1)
            V.m[x, y, G0] = MARBLE_B if (x + y) % 2 else FLAG_DK
    for y in range(y0, y1 + 1):
        k = min(y - y0, y1 - y)
        V.column_to_ground(x0, y, top - k // 2, STONE); V.column_to_ground(x0 + 1, y, top - k // 2, STONE)
    rose(V, x0 + 1, (y0 + y1) // 2, 28, 5)
    for x in range(x0 + 5, x1 - 3, 6):
        lancet(V, x, y0, 34, 9, axis='x')
        lancet(V, x, y1, 34, 9, axis='x')
    V.clear(x1 - 1, x1, 338, 344, G0 - 6, G0 - 1)                      # east door
    V.clear(186, 189, y0, y0 + 1, G0 - 5, G0 - 1)                      # north door to the lane
    V.box(x0 + 3, x0 + 5, 337, 346, G0 - 2, G0 - 1, STONE_TRIM)
    V.box(x0 + 3, x0 + 5, 337, 346, G0 - 2, G0 - 2, CLOTH_BLOOD)
    for y in (337, 341, 346):
        V.put(x0 + 4, y, G0 - 3, CANDLE)
    for x in range(x0 + 9, x1 - 3, 4):
        V.box(x, x, 333, 339, G0 - 1, G0 - 1, PLANK); V.box(x, x, 344, 350, G0 - 1, G0 - 1, PLANK)
    rubble(V, 192, 336, G0, 3, rng, h=2)
    interior('castle chapel', 190, 342, G0)


def courtyard_dressing(V, F, rng):
    cx0, cx1, cy0, cy1 = SPEC['courtyard']
    # inlaid crown mosaic under the platform, read from the sky
    for x in range(200, 257):
        for y in range(226, 287):
            dx, dy = x + 0.5 - 256.5, y + 0.5 - 256.5
            d = math.hypot(dx, dy)
            if 22 < d <= 25:
                V.m[x, y, G0] = CROWN_DK
            a = math.atan2(dy, dx)
            seg = (a / (2 * math.pi)) * 8
            if 25 < d <= 25 + 6 * (1 - abs(seg - round(seg)) * 4) and abs(seg - round(seg)) < 0.25:
                V.m[x, y, G0] = CROWN_DK
            if 10 < d <= 11.5:
                V.m[x, y, G0] = FLAG_DK
    # worn cobble path from the gate to the tower zone
    for x in range(174, 206):
        for y in range(247, 266):
            if hash3(x, y, 0, 13) < 0.65:
                V.m[x, y, G0] = COBBLE
    # cracks in the paving
    for k in range(10):
        x = int(rng.integers(176, 250)); y = int(rng.integers(205, 308))
        for s in range(int(rng.integers(6, 14))):
            V.m[x, y, G0] = CRACK
            x += int(rng.integers(-1, 2)); y += int(rng.integers(0, 2)) * (1 if k % 2 else -1)
            x = min(max(x, 174), 256); y = min(max(y, 203), 310)
    # weeds/moss in the joints near the walls
    for x in range(174, 257):
        for y in list(range(201, 207)) + list(range(306, 312)):
            if hash3(x, y, 1, 21) < 0.3 and V.m[x, y, G0] == FLAG:
                V.m[x, y, G0] = MOSS_GROUND
    # fallen masonry in the courtyard corners (well away from the anchor ground)
    for (x, y) in ((181, 208), (182, 304), (198, 207)):
        rubble(V, x, y, G0, 3, rng, h=2, mats=[STONE, STONE_TRIM, RUBBLE])
    # braziers along the ward edge
    for (x, y) in ((184, 210), (184, 302), (228, 206), (228, 306)):
        brazier(V, x, y, G0, glow=GLOW_GREEN)


# ============================================================================== outside the walls

def war_camp(V, F, rng):
    rx0, rx1, ry0, ry1 = SPEC['camp_ring']
    gaps = {'E': (240, 272), 'W': (250, 262), 'N': (110, 126), 'S': (110, 126)}
    def low_wall(x, y, h):
        V.column_to_ground(x, y, G0 - h, STONE if hash3(x, y, 0, 8) > 0.2 else MENHIR)
    for y in range(ry0, ry1 + 1):
        for x in (rx0, rx0 + 1):
            if not (gaps['W'][0] <= y <= gaps['W'][1]):
                low_wall(x, y, 2 + int(hash3(x, y // 4, 0, 3) > 0.6))
        for x in (rx1 - 1, rx1):
            if not (gaps['E'][0] - 2 <= y <= gaps['E'][1] + 2):
                low_wall(x, y, 2 + int(hash3(x, y // 4, 0, 3) > 0.6))
    for x in range(rx0, rx1 + 1):
        for y in (ry0, ry0 + 1, ry1 - 1, ry1):
            if not (gaps['N'][0] <= x <= gaps['N'][1]):
                low_wall(x, y, 2 + int(hash3(x // 4, y, 0, 3) > 0.6))
    # corner braziers and front banners (team cloth)
    for (x, y) in ((rx0 - 2, ry0 - 2), (rx0 - 2, ry1 + 2), (rx1 + 2, ry0 - 2), (rx1 + 2, ry1 + 2)):
        brazier(V, x, y, G0)
    banner_pole(V, rx1 + 2, gaps['E'][0] - 4, G0, 12, CLOTH_TEAM, (0, -1), 3, 7)
    banner_pole(V, rx1 + 2, gaps['E'][1] + 4, G0, 12, CLOTH_TEAM, (0, 1), 3, 7)
    for (x, y) in ((rx0 - 2, gaps['W'][0] - 3), (rx0 - 2, gaps['W'][1] + 3)):
        banner_pole(V, x, y, G0, 9, CLOTH_TEAM, (-1, 0), 2, 5)
    # pavilion tents west of the ring
    for (tx, ty) in ((78, 238), (78, 274)):
        tent(V, tx, ty, G0, 6, rng)
    # supply carts and crates by the north/south gaps (outside the ring)
    cart(V, 128, 222, G0, True, load=PUMPKIN)
    cart(V, 128, 286, G0, True, load=HAY)
    for (x, y) in ((100, 226), (103, 226), (100, 288), (104, 289)):
        crate(V, x, y, G0)
    # weapon racks
    for (x, y) in ((90, 240), (90, 270)):
        V.box(x, x, y, y + 4, G0 - 4, G0 - 4, TIMBER)
        V.box(x, x, y, y, G0 - 4, G0 - 1, TIMBER); V.box(x, x, y + 4, y + 4, G0 - 4, G0 - 1, TIMBER)
        for k in (1, 2, 3):
            V.put(x + 1, y + k, G0 - 3, IRON)


def tent(V, cx, cy, g, r, rng):
    h = 9
    for k in range(h):
        z = g - 1 - k
        rr = r if k < 3 else r * (1 - (k - 3) / (h - 3)) + 0.4
        for dx in range(-r - 1, r + 2):
            for dy in range(-r - 1, r + 2):
                d = math.hypot(dx, dy)
                if d <= rr and (d > rr - 1.3 or k >= 3):
                    a = math.atan2(dy, dx)
                    stripe = int(((a / (2 * math.pi)) * 12) % 2)
                    if k < 3 and dx > r - 2 and abs(dy) <= 1:
                        continue                                      # door flap opening (east)
                    V.put(cx + dx, cy + dy, z, CLOTH_TEAM if stripe else PLASTER)
    V.box(cx, cx, cy, cy, g - h - 3, g - h, TIMBER)
    V.put(cx, cy - 1, g - h - 3, CLOTH_TEAM); V.put(cx, cy - 2, g - h - 3, CLOTH_TEAM)


def pumpkin_fields(V, F, rng):
    for (x0, x1, y0, y1) in SPEC['fields']:
        pm = F['path_mask']
        for y in range(y0, y1 + 1):
            row = (y - y0) % 5
            for x in range(x0, x1 + 1):
                if F['moat'][x, y] or pm[x, y]:
                    continue
                g = V.ground(x, y)
                if g != G0:
                    continue
                if row in (0, 1):
                    V.m[x, y, g] = FURROW
                elif row == 2:
                    V.m[x, y, g] = VINE if hash3(x, y, 0, 5) < 0.55 else SOIL_DARK
                else:
                    V.m[x, y, g] = SOIL_DARK
        # pumpkins on the vine rows
        for y in range(y0 + 2, y1, 5):
            x = x0 + 2
            while x < x1 - 2:
                if not pm[x - 2:x + 3, y - 2:y + 3].any() and not F['moat'][x - 3:x + 4, y - 3:y + 4].any():
                    r = rng.random()
                    if r < 0.5:
                        pumpkin(V, x, y, G0, 1, mat=PUMPKIN if rng.random() < 0.8 else PUMPKIN_YEL)
                    elif r < 0.68:
                        pumpkin(V, x, y, G0, 0)
                    elif r < 0.74:
                        pumpkin(V, x, y, G0, 2, carved=rng.random() < 0.4, face=(0, 1))
                x += int(rng.integers(4, 8))
        # a giant carved pumpkin and two scarecrows per field
        gy = (y0 + y1) // 2
        pumpkin(V, x0 + 10, gy + 3, G0, 4, carved=True, face=(1, 0))
        scarecrow(V, x0 + 34, gy - 8, G0, rng, face=(1, 0))
        scarecrow(V, x0 + 50, gy + 12, G0, rng, face=(1, 0))
        # broken split-rail fence along the outer edge
        yf = y0 - 2 if y0 < 256 else y1 + 2
        for x in range(x0, x1 - 4):
            if pm[x, yf] or F['moat'][x, yf] or hash3(x // 6, yf, 0, 4) < 0.2:
                continue
            if x % 4 == 0:
                V.box(x, x, yf, yf, G0 - 3, G0 - 1, TIMBER)
            V.put(x, yf, G0 - 2, TIMBER)


def stone_circle(V, rng):
    cx, cy = SPEC['stone_circle']['c']; r = SPEC['stone_circle']['r']
    for dx in range(-r - 3, r + 4):
        for dy in range(-r - 3, r + 4):
            d = math.hypot(dx, dy)
            g = V.ground(cx + dx, cy + dy)
            if d <= r + 3:
                V.m[cx + dx, cy + dy, g] = MOSS_GROUND if d > 4 or (dx + dy) % 3 else DIRT_GREY
    n = 11
    for i in range(n):
        a = 2 * math.pi * i / n + 0.15
        x = cx + int(round(math.cos(a) * r)); y = cy + int(round(math.sin(a) * r))
        if i == 7:                                                        # one fallen stone
            g = V.ground(x, y)
            V.box(x - 1, x + 5, y, y + 1, g - 2, g - 1, MENHIR)
            continue
        g = V.ground(x, y)
        menhir(V, x, y, g, 7 + int(rng.integers(0, 4)), w=2, lean=1 if i % 4 == 2 else 0)
    # lintel trilithon on the east side (toward the camp)
    g = V.ground(cx + r, cy)
    V.box(cx + r, cx + r + 1, cy - 4, cy - 3, g - 9, g - 1, MENHIR)
    V.box(cx + r, cx + r + 1, cy + 3, cy + 4, g - 9, g - 1, MENHIR)
    V.box(cx + r, cx + r + 1, cy - 4, cy + 4, g - 11, g - 10, MENHIR)
    # altar slab with ghost candles
    g = V.ground(cx, cy)
    V.box(cx - 1, cx + 1, cy - 1, cy + 1, g - 2, g - 1, MENHIR)
    V.box(cx - 3, cx + 3, cy - 2, cy + 2, g - 3, g - 3, MENHIR)
    for (a, b) in ((-3, -2), (3, 2), (-3, 2), (3, -2)):
        V.put(cx + a, cy + b, g - 4, CANDLE)
    V.put(cx, cy, g - 4, GLOW_GREEN)


def shrine(V, x, y, rng):
    g = V.ground(x, y)
    V.box(x - 3, x + 3, y - 3, y + 3, g, g, STONE_DK)
    for (a, b) in ((-3, -3), (3, -3), (-3, 3), (3, 3)):
        V.column_to_ground(x + a, y + b, g - 6, STONE)
    for k in range(4):
        V.box(x - 4 + k, x + 4 - k, y - 4 + k, y + 4 - k, g - 7 - k, g - 7 - k, SLATE_P if k % 2 else SLATE)
    V.box(x - 1, x + 1, y - 1, y + 1, g - 2, g - 1, STONE_TRIM)
    pumpkin(V, x, y, g - 2, 1)
    V.put(x + 1, y + 1, g - 3, CANDLE); V.put(x - 1, y + 1, g - 3, CANDLE)


def woods(V, F, rng, keepout):
    """Whispering Woods: twisted dead trees (some with carved faces), exposed roots, boulders.
    Placed on the west half only (x <= 246) and mirrored."""
    pts = []
    H = F['H']
    tries = 0
    zone = np.zeros((512, 512), bool)
    zone[:90, :] = True                    # behind the camps
    zone[:140, :140] = True                # NW
    zone[:150, 372:] = True                # SW
    zone[:247, 470:] = True                # south rim behind the village
    zone[:120, :] |= False
    zone[100:247, :18] = True              # north rim behind the graveyard
    dens = fold_x(fbm2((512, 512), 30, 2, 'woods', SEED))
    while len(pts) < 430 and tries < 40000:
        tries += 1
        x = int(rng.integers(3, 247)); y = int(rng.integers(3, 509))
        if not zone[x, y] or keepout[x, y]:
            continue
        if dens[x, y] < 0.33 and rng.random() < 0.7:
            continue
        sp = 12 if dens[x, y] > 0.5 else 15
        if any((x - a) ** 2 + (y - b) ** 2 < sp * sp for a, b in pts[-400:]):
            continue
        pts.append((x, y))
    placed = 0
    for (x, y) in pts:
        g = int(H[x, y])
        if V.m[x, y, g - 1] != AIR or V.m[x + 1, y + 1, g - 1] != AIR:
            continue
        h = min(int(rng.integers(10, 19)), g - 8)
        placed += 1
        face = None
        if rng.random() < 0.09:
            face = [(1, 0), (0, 1), (0, -1)][int(rng.integers(0, 3))]
        dead_tree(V, x, y, g, h, rng, girth=2 if rng.random() < 0.7 else 3, face=face)
        if rng.random() < 0.3:
            r = 5
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    if dx * dx + dy * dy <= r * r and rng.random() < 0.4:
                        gg = V.ground(x + dx, y + dy)
                        if V.get(x + dx, y + dy, gg) in (GRASS, MUD, DIRT_GREY):
                            V.put(x + dx, y + dy, gg, LEAFLITTER)
    for k in range(40):
        x = int(rng.integers(5, 240)); y = int(rng.integers(5, 507))
        if zone[x, y] and not keepout[x - 3:x + 4, y - 3:y + 4].any():
            g = int(H[x, y])
            if V.m[x - 4:x + 5, y - 4:y + 5, max(g - 6, 0):g].any():
                continue
            boulder(V, x, y, g, int(rng.integers(2, 5)), rng)
    return placed


def skeletal_hand(V, bx, by, g):
    """A giant skeletal hand clawing up out of the sunken burial ground (west hand; the mirror is the other)."""
    B, D = BONE, BONE_DK
    # radius + ulna rising from the earth (slight lean toward the castle, +y)
    V.line4((bx - 2, by, g + 1), (bx - 1, by + 3, g - 14), B, thick=1)
    V.line4((bx + 2, by, g + 1), (bx + 2, by + 3, g - 14), B, thick=1)
    # earth heaved up around the wrist base
    for dx in range(-5, 6):
        for dy in range(-5, 6):
            d = math.hypot(dx, dy)
            if d <= 5:
                gg = V.ground(bx + dx, by + dy)
                for k in range(int(2 - d * 0.4)):
                    V.put(bx + dx, by + dy, gg - 1 - k, SOIL_DARK)
    # wrist (carpals)
    wz = g - 15
    V.box(bx - 4, bx + 4, by + 1, by + 5, wz - 1, wz + 1, D)
    V.box(bx - 3, bx + 3, by + 2, by + 4, wz - 3, wz - 2, B)
    # metacarpals fanning out to the knuckles, fingers curling back toward the palm (claw)
    def bone2(p, q, mat=B):
        # 2x2-section bone (face connected), reads at gameplay distance
        for (a, b) in ((0, 0), (1, 0), (0, 1), (1, 1)):
            V.line4((p[0] + a, p[1] + b, p[2]), (q[0] + a, q[1] + b, q[2]), mat)
    def joint(p):
        V.box(int(p[0]) - 1, int(p[0]) + 2, int(p[1]) - 1, int(p[1]) + 2, int(p[2]) - 1, int(p[2]) + 1, D)
    fingers = [(-6, 11), (-2, 14), (2, 13), (6, 10)]
    for (kx, L) in fingers:
        k0 = (bx + kx * 0.4, by + 3, wz - 2)
        k1 = (bx + kx, by + 4, wz - 9)
        bone2(k0, k1)
        joint(k1)
        p1 = (k1[0], k1[1] + 1, k1[2] - L * 0.5)
        bone2(k1, p1); joint(p1)
        p2 = (p1[0], p1[1] + 3, p1[2] - L * 0.25)
        bone2(p1, p2); joint(p2)
        p3 = (p2[0], p2[1] + 4, p2[2] + 2)
        bone2(p2, p3)
        V.put(p3[0], p3[1] + 1, p3[2] + 1, B)
    # thumb, out to the side and up
    bone2((bx - 3, by + 3, wz - 1), (bx - 10, by + 5, wz - 6)); joint((bx - 10, by + 5, wz - 6))
    bone2((bx - 10, by + 5, wz - 6), (bx - 12, by + 8, wz - 11)); joint((bx - 12, by + 8, wz - 11))
    bone2((bx - 12, by + 8, wz - 11), (bx - 11, by + 11, wz - 10))


def chapel(V, rng):
    cx, cy = SPEC['chapel']['c']; g = SPEC['chapel']['z']
    x0, y0, y1 = cx - 10, 26, 62
    top = g - 14
    for x in range(x0, cx + 1):
        for y in range(y0, y1 + 1):
            if x in (x0, x0 + 1) or y in (y0, y0 + 1, y1 - 1, y1):
                t = top + (int(max(0, (hash3(x // 2, y // 3, 0, 7) - 0.55) * 18)) if y > 44 else 0)
                V.column_to_ground(x, y, t, STONE)
    for x in range(x0 + 2, cx + 1):
        for y in range(y0 + 2, y1 - 1):
            V.m[x, y, g] = FLAG_DK if (x + y) % 3 else FLAG
    # buttresses
    for y in range(y0 + 4, y1 - 2, 7):
        for k in range(1, 4):
            V.column_to_ground(x0 - k, y, top + 2 + k * 2, STONE_DK)
    # lancets
    for y in range(y0 + 7, y1 - 4, 7):
        lancet(V, y, x0, g - 4, 8, axis='y')
    # south façade: pointed door + rose window, gable
    for x in range(x0, cx + 1):
        k = x - x0
        V.column_to_ground(x, y1, top - k // 2, STONE); V.column_to_ground(x, y1 - 1, top - k // 2, STONE)
    for x in range(cx - 3, cx + 1):
        zt = int(math.ceil(arch_top(x + 0.5 - (cx + 0.5), 3.5, 4.5, g - 4)))
        V.clear(x, x, y1 - 1, y1, zt, g - 1)
    rose(V, cx, y1, g - 12, 4) if False else None
    for dz in range(-4, 5):
        for dx in range(-4, 1):
            if math.hypot(dx, dz) <= 4.2:
                V.put(cx + dx, y1, g - 13 + dz, (STONE_TRIM if math.hypot(dx, dz) > 3.2 or dx == 0 or dz == 0
                                                  else (GLOW_GREEN if (dx + dz) % 2 else CLOTH_PURPLE)))
    # roof: steep slate over the north half (south half collapsed)
    for x in range(x0 - 1, cx + 1):
        k = x - (x0 - 1)
        for y in range(y0, 46):
            z = top - 1 - k
            if z >= 0:
                V.put(x, y, z, SLATE if (k % 2) else SLATE_P)
                V.put(x, y, z + 1, SLATE)
    for x in range(x0 + 2, cx + 1, 3):                                 # bare rafters over the fallen half
        k = x - (x0 - 1)
        for y in range(46, 58, 4):
            V.put(x, y, top - 1 - k, ROOF_BEAM)
            V.line4((x, 46, top - 1 - k), (x, 58, top - 1 - k), ROOF_BEAM)
    # bell tower at the north end with a broken spire
    tx0, ty0 = cx - 5, 15
    for x in range(tx0, cx + 1):
        for y in range(ty0, 27):
            if x in (tx0, tx0 + 1) or y in (ty0, ty0 + 1, 25, 26):
                V.column_to_ground(x, y, g - 26, STONE)
    for y in range(ty0 + 3, 24, 4):
        V.box(tx0, tx0, y, y + 1, g - 24, g - 20, WINDOW)
    for k in range(7):
        rr = 5 - k * 0.7
        for x in range(tx0, cx + 1):
            for y in range(ty0, 27):
                if abs(x - cx) <= rr and abs(y - 20.5) <= rr and not (k >= 4 and x < cx - 1):
                    if abs(x - cx) > rr - 1.2 or abs(y - 20.5) > rr - 1.2:
                        V.put(x, y, g - 27 - k, SLATE_P)
    V.box(cx - 1, cx, 20, 21, g - 25, g - 24, IRON)                    # bell
    V.clear(cx - 1, cx, 24, 28, g - 4, g - 1)                          # nave -> bell tower doorway
    for x in range(tx0 + 2, cx + 1):
        for y in range(ty0 + 2, 25):
            V.m[x, y, g] = FLAG_DK
    V.clear(tx0, tx0 + 1, 19, 20, g - 3, g - 2)                        # low tower window openings
    V.box(cx, cx, 20, 20, g - 23, g - 3, STRAW)                    # bell rope
    # interior: altar, broken pews
    V.box(cx - 3, cx, 30, 31, g - 2, g - 1, STONE_TRIM)
    V.put(cx - 2, 30, g - 3, CANDLE); V.put(cx, 31, g - 3, GLOW_GREEN)
    for y in range(36, 58, 3):
        if hash3(y, 0, 0, 2) < 0.75:
            V.box(cx - 8, cx - 3, y, y, g - 1, g - 1, PLANK)
    rubble(V, cx - 4, 52, g, 3, rng, h=2)
    interior('hill chapel nave', cx - 1, 47, g)
    interior('bell tower', cx - 2, 20, g)


def mausoleum(V, x, y, g, rng, face=(0, 1), w=9, d=11):
    """Gothic tomb house you can walk into: stepped plinth, 1-thick walls with corner shafts, open pointed
    doorway between two columns, slit windows on the sides, a sarcophagus and candles inside, cornice and
    steep gable slate roof (ridge toward the door) with a cross on the front gable."""
    fx, fy = face
    if fx != 0:
        w, d = d, w
    x0, x1 = x - w // 2, x + w // 2
    y0, y1 = y - d // 2, y + d // 2
    for xx in range(x0 - 1, x1 + 2):
        for yy in range(y0 - 1, y1 + 2):
            V.column_to_ground(xx, yy, g - 1, STONE_DK)
    for xx in range(x0, x1 + 1):
        for yy in range(y0, y1 + 1):
            edge = xx in (x0, x1) or yy in (y0, y1)
            if edge:
                V.box(xx, xx, yy, yy, g - 7, g - 2, GRAVE)
            else:
                V.clear(xx, xx, yy, yy, g - 7, g - 2)
                V.m[xx, yy, g - 1] = MARBLE_B if (xx + yy) % 2 else STONE_DK
    for (a, b) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        V.box(a, a, b, b, g - 8, g - 2, STONE_TRIM)
        V.put(a, b, g - 9, STONE_TRIM)
    V.box(x0, x1, y0, y1, g - 8, g - 8, STONE_TRIM)                     # cornice / ceiling
    ridge_y = fy != 0
    k = 0
    while True:
        z = g - 9 - k
        if ridge_y:
            a0, a1 = x0 - 1 + k, x1 + 1 - k
            if a0 > a1:
                break
            for yy in range(y0 - 1, y1 + 2):
                V.put(a0, yy, z, SLATE if k % 2 else SLATE_P); V.put(a1, yy, z, SLATE if k % 2 else SLATE_P)
            for yy in (y0, y1):
                for xx in range(a0 + 1, a1):
                    V.put(xx, yy, z, STONE_TRIM)
        else:
            a0, a1 = y0 - 1 + k, y1 + 1 - k
            if a0 > a1:
                break
            for xx in range(x0 - 1, x1 + 2):
                V.put(xx, a0, z, SLATE if k % 2 else SLATE_P); V.put(xx, a1, z, SLATE if k % 2 else SLATE_P)
            for xx in (x0, x1):
                for yy in range(a0 + 1, a1):
                    V.put(xx, yy, z, STONE_TRIM)
        k += 1
    zr = g - 9 - k
    if ridge_y:
        dy_ = y1 if fy > 0 else y0
        back = y0 if fy > 0 else y1
        V.box(x, x, dy_, dy_, zr - 2, zr, STONE_TRIM); V.put(x - 1, dy_, zr - 1, STONE_TRIM)
        V.put(x + 1, dy_, zr - 1, STONE_TRIM)
        V.clear(x - 1, x + 1, dy_, dy_, g - 5, g - 2)                      # doorway
        V.clear(x, x, dy_, dy_, g - 6, g - 6)
        for cx_ in (x - 3, x + 3):
            V.box(cx_, cx_, dy_ + fy, dy_ + fy, g - 7, g - 2, STONE_TRIM)
        V.put(x, dy_ + fy, g - 7, GLOW_CYAN)
        for sx_ in (x0, x1):                                                # side slit windows
            V.clear(sx_, sx_, y, y, g - 5, g - 4)
        V.box(x - 1, x + 1, back + fy * 2, back + fy * 4, g - 2, g - 2, STONE_TRIM)   # sarcophagus
        V.put(x, back + fy * 3, g - 3, BONE_DK)
        V.put(x - 3, back + fy, g - 2, CANDLE); V.put(x + 3, back + fy, g - 2, CANDLE)
        interior('mausoleum', x, (dy_ + back) // 2, g - 1)
    else:
        dx_ = x1 if fx > 0 else x0
        back = x0 if fx > 0 else x1
        V.box(dx_, dx_, y, y, zr - 2, zr, STONE_TRIM); V.put(dx_, y - 1, zr - 1, STONE_TRIM)
        V.put(dx_, y + 1, zr - 1, STONE_TRIM)
        V.clear(dx_, dx_, y - 1, y + 1, g - 5, g - 2)
        V.clear(dx_, dx_, y, y, g - 6, g - 6)
        for cy_ in (y - 3, y + 3):
            V.box(dx_ + fx, dx_ + fx, cy_, cy_, g - 7, g - 2, STONE_TRIM)
        V.put(dx_ + fx, y, g - 7, GLOW_CYAN)
        for sy_ in (y0, y1):
            V.clear(x, x, sy_, sy_, g - 5, g - 4)
        V.box(back + fx * 2, back + fx * 4, y - 1, y + 1, g - 2, g - 2, STONE_TRIM)
        V.put(back + fx * 3, y, g - 3, BONE_DK)
        V.put(back + fx, y - 3, g - 2, CANDLE); V.put(back + fx, y + 3, g - 2, CANDLE)
        interior('mausoleum', (dx_ + back) // 2, y, g - 1)


def burial_pit(V, x, y, g, rng):
    # 2 deep with a 1-voxel step at the south end so nobody is trapped
    V.clear(x, x + 2, y, y + 4, g - 4, g + 1)
    for xx in range(x, x + 3):
        for yy in range(y, y + 5):
            V.m[xx, yy, g + 2] = SOIL_DARK
        V.m[xx, y + 4, g + 1] = SOIL_DARK
    V.box(x + 1, x + 1, y, y + 2, g + 1, g + 1, COFFIN)
    V.put(x + 1, y + 1, g + 1, BONE)
    # spoil heap beside it
    for dx in range(-1, 2):
        for dy in range(0, 5):
            hh = 2 if dx == 0 and 1 <= dy <= 3 else 1
            for k in range(hh):
                V.put(x + 4 + dx, y + dy, g - 1 - k, SOIL_DARK)
    V.box(x + 6, x + 6, y + 2, y + 2, g - 4, g - 1, TIMBER)          # shovel
    V.put(x + 6, y + 2, g - 4, IRON)


def crypt_entrance(V, x, y, g):
    """Open crypt: stairs under a stone hood go down to an arched opening into a vault (7 x 7, 4 high) with
    coffin niches, an open sarcophagus and ghost candles; walk in and back out."""
    for k in range(5):
        V.clear(x, x + 2, y + k, y + k, g - 4, g + k)
        V.box(x, x + 2, y + k, y + k, g + k + 1, g + k + 1, STONE_DK)
    for k in range(5):
        for xx in (x - 1, x + 3):
            V.column_to_ground(xx, y + k, g - 2, STONE)
    V.box(x - 1, x + 3, y + 4, y + 6, g - 6, g + 1, STONE)
    V.clear(x, x + 2, y + 4, y + 4, g + 1, g + 4)
    V.box(x - 1, x + 3, y + 3, y + 6, g - 7, g - 7, SLATE)
    V.put(x + 1, y + 3, g - 6, BONE)
    # vault: walls 1 thick of dark stone carved out of the ground, floor one step below the landing
    vx0, vx1, vy0, vy1 = x - 2, x + 4, y + 6, y + 12
    V.box(vx0 - 1, vx1 + 1, vy0 - 1, vy1 + 1, g + 1, g + 7, STONE_DK)
    V.clear(vx0, vx1, vy0, vy1, g + 2, g + 5)
    V.box(vx0, vx1, vy0, vy1, g + 6, g + 6, FLAG_DK)
    V.clear(x, x + 2, y + 5, y + 5, g + 2, g + 4)                       # arched opening from the landing
    V.box(x, x + 2, y + 5, y + 5, g + 5, g + 5, STONE_DK)
    V.box(x - 1, x - 1, y + 5, y + 5, g + 2, g + 4, IRON); V.box(x + 3, x + 3, y + 5, y + 5, g + 2, g + 4, IRON)
    for (cx_, cy_) in ((vx0, vy0 + 1), (vx0, vy0 + 4), (vx1, vy0 + 1), (vx1, vy0 + 4)):     # wall niches
        V.clear(cx_ - (1 if cx_ == vx0 else -1), cx_ - (1 if cx_ == vx0 else -1), cy_, cy_ + 1, g + 4, g + 5)
        V.put(cx_ - (1 if cx_ == vx0 else -1), cy_, g + 5, COFFIN)
    V.box(x, x + 2, vy1 - 3, vy1 - 1, g + 5, g + 5, STONE_TRIM)       # sarcophagus, lid pushed aside
    V.put(x + 1, vy1 - 2, g + 4, BONE)
    V.put(x + 3, vy1 - 1, g + 5, STONE_TRIM)
    for (cx_, cy_) in ((vx0, vy1), (vx1, vy1)):
        V.put(cx_, cy_, g + 5, GLOW_CYAN)
    interior('crypt vault', x + 1, vy0 + 2, g + 6)


def graveyard(V, F, rng, keepout):
    pm = F['path_mask']
    taken = np.zeros((512, 512), bool)
    taken |= pm
    taken |= keepout
    # low boundary wall along the moat side with a gate at the axis path
    mo = F['moat']
    for x in range(122, 249):
        if mo[x - 1:x + 2, 124:129].any():
            continue
        g = V.ground(x, 126)
        V.column_to_ground(x, 126, g - 2 - int(hash3(x // 3, 0, 0, 6) > 0.6), STONE)
        V.column_to_ground(x, 127, g - 2, STONE)
    gx = 247
    g = V.ground(gx, 128)
    V.column_to_ground(gx, 126, g - 6, STONE_TRIM); V.column_to_ground(gx, 127, g - 6, STONE_TRIM)
    V.put(gx, 125, g - 6, GLOW_CYAN)
    taken[226:257, 8:76] = True                                          # chapel and its plateau
    taken[:, 122:] = True
    # mausoleums
    for (x, y, f) in ((150, 76, (0, 1)), (212, 66, (0, 1)), (146, 118, (0, -1)), (226, 118, (0, -1)),
                      (178, 52, (0, 1)), (232, 90, (1, 0))):
        g = V.ground(x, y)
        mausoleum(V, x, y, g, rng, face=f)
        taken[x - 7:x + 8, y - 8:y + 9] = True
    # crypt entrances
    for (x, y) in ((168, 96), (238, 108)):
        g = V.ground(x, y)
        crypt_entrance(V, x, y, g)
        taken[x - 3:x + 6, y - 2:y + 9] = True
    # skeletal hand rising from the sunken burial ground
    sx, sy = SPEC['sunken']['c']
    skeletal_hand(V, sx, sy, V.ground(sx, sy))
    taken[sx - 16:sx + 14, sy - 8:sy + 20] = True
    # burial pits
    for (x, y) in ((136, 92), (160, 64), (204, 104), (222, 76), (190, 120), (140, 106), (214, 52)):
        if taken[x - 1:x + 8, y - 1:y + 6].any():
            continue
        burial_pit(V, x, y, V.ground(x, y), rng)
        taken[x - 2:x + 9, y - 2:y + 7] = True
    # rows of gravestones (hundreds), facing south toward the castle, some leaning, some mossy
    n = 0
    for y in range(52, 121, 5):
        x = 126 + int(rng.integers(0, 3))
        while x < 247:
            jx = x + int(rng.integers(-1, 2)); jy = y + int(rng.integers(-1, 2))
            if not taken[jx - 2:jx + 3, jy - 1:jy + 4].any() and V.ground(jx, jy) < 52:
                g = V.ground(jx, jy)
                r = rng.random()
                kind = 0 if r < 0.34 else 1 if r < 0.56 else 5 if r < 0.7 else 2 if r < 0.82 else 4 if r < 0.92 else 3
                mat = GRAVE_MOSS if rng.random() < 0.35 else GRAVE
                gravestone(V, jx, jy, g, kind, face=(0, 1), lean=1 if rng.random() < 0.3 else 0, mat=mat)
                # grave mound in front
                for k in range(1, 4):
                    gg = V.ground(jx, jy + k)
                    if V.get(jx, jy + k, gg) in (GRASS, MUD, DIRT_GREY):
                        V.put(jx, jy + k, gg, SOIL_DARK)
                n += 1
                taken[jx - 1:jx + 2, jy:jy + 4] = True
            x += int(rng.integers(4, 7))
    # graves in the sunken ground follow its rings
    for k in range(26):
        a = 2 * math.pi * k / 26
        for rr in (9, 15):
            x = int(round(sx + math.cos(a) * rr)); y = int(round(sy + math.sin(a) * rr / 1.15))
            if x > 246 or taken[x, y] and rr < 9:
                continue
            g = V.ground(x, y)
            gravestone(V, x, y, g, 0 if k % 3 else 1, face=(0, 1), mat=GRAVE_MOSS if k % 2 else GRAVE)
            n += 1
    # iron railings around two family plots
    for (x0, x1, y0, y1) in ((128, 144, 56, 70), (186, 206, 56, 70)):
        for x in range(x0, x1 + 1):
            for y in (y0, y1):
                if x % 2 == 0 and not (y == y1 and (x0 + x1) // 2 - 2 <= x <= (x0 + x1) // 2 + 2):
                    g = V.ground(x, y)
                    V.box(x, x, y, y, g - 2, g - 1, IRON)
        for y in range(y0, y1 + 1):
            for x in (x0, x1):
                if y % 2 == 0:
                    g = V.ground(x, y)
                    V.box(x, x, y, y, g - 2, g - 1, IRON)
    # ghost lanterns along the paths
    for (x, y) in ((252, 80), (252, 96), (252, 116), (230, 101), (200, 101), (170, 101), (142, 108)):
        g = V.ground(x, y)
        lantern_post(V, x, y, g, h=5, arm=(1, 0), glow=GLOW_CYAN)
    # a few dead trees among the graves
    for (x, y) in ((134, 80), (158, 100), (200, 62), (240, 74), (184, 112), (222, 128)):
        if not taken[x - 1:x + 3, y - 1:y + 3].any():
            dead_tree(V, x, y, V.ground(x, y), int(rng.integers(12, 17)), rng, girth=2,
                      face=(0, 1) if (x + y) % 5 == 0 else None)
    return n


# ---------------------------------------------------------------- village

def house(V, x0, y0, w, d, g, rng, street_dir, storeys=2, collapsed=False, roof_mat=SLATE):
    """Half-timbered house you can walk through: open front door, stone ground floor split into a front room
    (hearth, table) and a back room by a partition with a doorway, a stair up through a hole in the floor,
    jettied upper storey(s) with a bedroom, window openings (some lit amber glass) on every storey, gable
    roof facing the street with an attic window, exterior stone chimney. x0..x0+w-1, y0..y0+d-1 footprint."""
    sx, sy = street_dir
    W, D = (w, d) if sy != 0 else (d, w)

    def P(u, v):
        if sy > 0:
            return (x0 + u, y0 + d - 1 - v)
        if sy < 0:
            return (x0 + u, y0 + v)
        if sx > 0:
            return (x0 + w - 1 - v, y0 + u)
        return (x0 + v, y0 + u)

    def put(u, v, z, mat, only_air=False):
        x, y = P(u, v); V.put(x, y, z, mat, only_air)

    def clr(u, v, z0, z1):
        x, y = P(u, v); V.clear(x, x, y, y, z0, z1)

    def win(u, v, z0, z1, lit_p=0.35):
        lit = hash3(*P(u, v), z0, 19) < lit_p
        for zz in range(z0, z1 + 1):
            if lit:
                put(u, v, zz, GLOW_AMBER)
            else:
                clr(u, v, zz, zz)

    # ---- ground floor shell (stone, 4 high) and plank floor
    for u in range(W):
        for v in range(D):
            x, y = P(u, v)
            if u in (0, W - 1) or v in (0, D - 1):
                V.column_to_ground(x, y, g - 4, STONE if hash3(x, y, 0, 9) > 0.15 else BRICK)
            else:
                V.clear(x, x, y, y, g - 4, g - 1)
            V.m[x, y, g] = PLANK
    du = W // 2 - 1
    for u in (du, du + 1):                                            # open front door
        clr(u, 0, g - 3, g - 1)
    for k in range(3):
        put(du + 2, 1, g - 1 - k, TIMBER_CHAR)                        # door leaf swung inward (right)
    win(1, 0, g - 3, g - 2, 0.0); win(W - 2, 0, g - 3, g - 2, 0.0)   # front windows
    vp = D // 2
    win(W - 1, vp - 1, g - 3, g - 2, 0.0); win(W - 1, D - 2, g - 3, g - 2, 0.0)
    # partition between front and back rooms, doorway in line with the front door
    for u in range(1, W - 1):
        if u in (du, du + 1):
            continue
        for zz in range(g - 4, g):
            put(u, vp, zz, TIMBER if u % 3 == 0 or zz == g - 4 else PLASTER)
    # hearth against the west side wall (chimney outside), table, barrels
    put(1, vp - 1, g - 1, EMBER); put(1, vp - 1, g - 3, STONE_TRIM)
    put(1, vp - 2, g - 1, STONE_TRIM); put(1, vp - 2, g - 2, STONE_TRIM)
    # table against the partition (keeps a clear walkway round the front room), barrels in the back room
    put(W - 3, vp - 1, g - 2, PLANK); put(W - 2, vp - 1, g - 2, PLANK); put(W - 3, vp - 1, g - 1, TIMBER)
    put(W - 2, vp + 1, g - 1, BARREL); put(W - 2, vp + 1, g - 2, BARREL)
    # ---- upper storeys
    zb = g - 5
    beams = []
    for s in range(1, storeys):
        zb = g - 5 * s
        beams.append(zb)
        for u in range(W):
            for v in range(-1, D):
                put(u, v, zb, TIMBER)                                 # floor / jetty beam
        for k in range(1, 5):
            zz = zb - k
            for u in range(W):
                for v in range(-1, D):
                    if u in (0, W - 1) or v in (-1, D - 1):
                        post = ((u % 3 == 0) and v in (-1, D - 1)) or ((v % 3 == 0) and u in (0, W - 1)) or k == 4
                        brace = k == 2 and hash3(*P(u, v), s, 2) < 0.3
                        put(u, v, zz, TIMBER if (post or brace) else PLASTER)
                    else:
                        clr(u, v, zz, zz)
        for (u0, u1) in ((2, 3), (W - 4, W - 3)):                      # street windows 2 x 2
            for u in (u0, u1):
                win(u, -1, zb - 3, zb - 2)
        win(W // 2, D - 1, zb - 3, zb - 2); win(W - 1, vp, zb - 3, zb - 2); win(W - 1, vp + 1, zb - 3, zb - 2)
        if s == 1:                                                     # bedroom
            for u in (W - 3, W - 2):
                for v in (D - 4, D - 3, D - 2):
                    put(u, v, zb - 1, VELVET if v < D - 2 else TIMBER)
            put(W - 2, D - 2, zb - 2, TIMBER); put(W - 3, D - 2, zb - 2, TIMBER)
            put(1, 0, zb - 1, PLANK); put(2, 0, zb - 1, PLANK)        # chest
            put(W - 3, 0, zb - 2, CANDLE) if W > 9 else None
        else:
            put(1, 1, zb - 1, BARREL); put(2, 1, zb - 1, PLANK)
    # ---- stairs: ground -> storey 2 along the back row; storey 2 -> 3 along the front row
    if storeys >= 2:
        stair_run(V, [P(u, D - 2) for u in range(1, 5)], g, PLANK, clear_above=g - 5)
    if storeys >= 3:
        stair_run(V, [P(u, 0) for u in range(W - 2, W - 6, -1)], g - 5, PLANK, clear_above=g - 10)
    # ---- steep gable roof facing the street (ridge runs front-to-back), attic window in the street gable
    z_r = zb - 5
    k = 0
    while True:
        zz = z_r - k
        a0, a1 = -1 + k, W - k
        if a0 > a1 or zz < 1:
            break
        for v in range(-2, D + 1):
            for u in (a0, a1):
                put(u, v, zz, roof_mat if (k % 2 == 0) else SLATE)
                if k > 0:
                    put(u, v, zz + 1, roof_mat, only_air=True)
        for v in (-1, D - 1):
            for u in range(a0 + 1, a1):
                put(u, v, zz, PLASTER if (u + zz) % 4 else TIMBER)
        k += 1
    kmax = k
    for u in (W // 2 - 1, W // 2):
        if z_r - 2 > 0:
            clr(u, -1, z_r - 2, z_r - 1)
    # ---- exterior chimney on the west side wall (u = -2..-1), from the ground to above the ridge
    for u in (-2, -1):
        for v in (vp - 2, vp - 1):
            x, y = P(u, v)
            V.column_to_ground(x, y, max(z_r - kmax - 1, 1), BRICK)
    if collapsed:
        hx, hy = P(W // 2, D // 2)
        for zz in range(max(z_r - kmax, 0), z_r + 1):
            for x in range(hx - 3, hx + 3):
                for y in range(hy - 3, hy + 3):
                    if V.get(x, y, zz) in (roof_mat, SLATE) and hash3(x, y, zz, 6) < 0.8:
                        V.put(x, y, zz, AIR)
        put(W // 2, D // 2, zb - 1, SLATE); put(W // 2 + 1, D // 2, zb - 1, ROOF_BEAM)
    interior('house ground floor', *P(W // 2, 1), g)
    if storeys >= 2:
        interior('house upper floor', *P(W // 2, 1), g - 5)
    if storeys >= 3:
        interior('house top floor', *P(W // 2, D - 3), g - 10)
    xs = [P(u, v)[0] for u in (-3, W) for v in (-2, D)]
    ys = [P(u, v)[1] for u in (-3, W) for v in (-2, D)]
    door = [P(u, v) for u in (du - 1, du, du + 1, du + 2) for v in (-1, -2, -3, -4)]
    return (min(xs), max(xs), min(ys), max(ys)), door


def market_stall(V, x, y, g, rng, along_x=True):
    w, d = (6, 4) if along_x else (4, 6)
    for (a, b) in ((x, y), (x + w - 1, y), (x, y + d - 1), (x + w - 1, y + d - 1)):
        V.box(a, a, b, b, g - 5, g - 1, TIMBER)
    V.box(x, x + w - 1, y, y + d - 1, g - 2, g - 2, PLANK)
    for xx in range(x - 1, x + w + 1):
        for yy in range(y - 1, y + d + 1):
            stripe = ((xx if along_x else yy) % 2 == 0)
            V.put(xx, yy, g - 6, AWNING_O if stripe else AWNING_P)
    for k in range(int(rng.integers(2, 4))):
        a = x + 1 + int(rng.integers(0, w - 2)); b = y + 1 + int(rng.integers(0, d - 2))
        V.put(a, b, g - 3, PUMPKIN if rng.random() < 0.6 else PUMPKIN_YEL)


def well(V, x, y, g):
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            if abs(dx) == 2 or abs(dy) == 2:
                V.box(x + dx, x + dx, y + dy, y + dy, g - 2, g - 1, STONE)
            else:
                V.m[x + dx, y + dy, g] = WATER_DK
    V.box(x - 2, x - 2, y, y, g - 6, g - 3, TIMBER); V.box(x + 2, x + 2, y, y, g - 6, g - 3, TIMBER)
    V.box(x - 2, x + 2, y, y, g - 7, g - 7, SLATE)
    V.box(x - 3, x + 3, y - 1, y + 1, g - 8, g - 8, SLATE)
    V.put(x, y, g - 6, ROOF_BEAM); V.put(x, y, g - 5, IRON)


def gallows(V, x, y, g):
    V.box(x - 2, x + 2, y - 2, y + 2, g - 2, g - 1, PLANK)
    V.box(x - 2, x - 2, y, y, g - 10, g - 3, TIMBER)
    V.box(x - 2, x + 2, y, y, g - 10, g - 10, TIMBER)
    V.box(x + 1, x + 1, y, y, g - 9, g - 7, STRAW)
    V.line4((x - 2, y, g - 7), (x, y, g - 10), TIMBER)


def village(V, F, rng):
    vs = SPEC['village']
    (hy0, hy1) = vs['high_y']; (mx0, mx1) = vs['main_x']; (sq0, sq1, sqy0, sqy1) = vs['square']
    lx0, lx1 = vs['lane_x']
    road = np.zeros((512, 512), bool)
    road[120:257, hy0:hy1 + 1] = True
    road[mx0:257, 377:472] = True
    road[sq0:257, sqy0:sqy1 + 1] = True
    road[lx0:lx1 + 1, 384:472] = True
    for x, y in zip(*np.nonzero(road)):
        g = V.ground(x, y)
        V.m[x, y, g] = COBBLE if hash3(x, y, 0, 3) > 0.22 else COBBLE_DK
        if hash3(x // 2, y // 2, 0, 17) < 0.04:
            V.m[x, y, g] = CRACK
    F['road'] = road
    occ = road.copy()
    occ[:, :382] |= True
    houses = 0
    keep = np.zeros((512, 512), bool)          # houses + their door approaches: no props here
    lots = []
    # north side of the high street: houses face south
    for x0 in range(124, 246, 14):
        if lx0 - 2 <= x0 + 11 and x0 <= lx1 + 2:
            continue
        if x0 + 11 >= mx0 - 1:
            continue
        lots.append((x0, hy0 - 12, (0, 1)))
    # south side of the high street: face north
    for x0 in range(124, 228, 14):
        if lx0 - 2 <= x0 + 11 and x0 <= lx1 + 2:
            continue
        if x0 + 11 >= sq0 - 1:
            continue
        lots.append((x0, hy1 + 3, (0, -1)))
    # along the main street (west side) facing east, north of the high street
    for y0 in (386, 400):
        lots.append((mx0 - 13, y0, (1, 0)))
    # around the square (west side) facing east, and a row south of the high street
    for y0 in (438, 452):
        lots.append((sq0 - 13, y0, (1, 0)))
    for x0 in (178, 196):
        lots.append((x0, 450, (0, -1)))
    for (x0, y0, sd) in lots:
        w = int(rng.integers(9, 12)); d = int(rng.integers(8, 11))
        if sd[0] != 0:
            w, d = d, w
        if sd == (0, 1):
            y0 = hy0 - 2 - d - 1
        g = V.ground(x0 + w // 2, y0 + d // 2)
        if occ[x0 - 1:x0 + w + 1, y0 - 1:y0 + d + 1].any():
            continue
        storeys = 3 if rng.random() < 0.3 else 2
        collapsed = rng.random() < 0.3
        bb, door = house(V, x0, y0, w, d, g, rng, sd, storeys, collapsed,
                         roof_mat=SLATE_P if rng.random() < 0.45 else SLATE)
        occ[x0 - 2:x0 + w + 2, y0 - 2:y0 + d + 2] = True
        keep[bb[0]:bb[1] + 1, bb[2]:bb[3] + 1] = True
        for (dx_, dy_) in door:
            keep[dx_, dy_] = True
        houses += 1
    # market: stalls, giant carved pumpkin on the axis, wells, carts, gallows, lanterns
    for (x, y, ax) in ((232, 440, True), (232, 461, True), (242, 440, True), (242, 461, True)):
        market_stall(V, x, y, G0, rng, ax)
    giant_pumpkin(V, 256, 452, G0)
    well(V, 238, 452, G0)
    def free(x0_, x1_, y0_, y1_):
        return not keep[max(x0_ - 1, 0):x1_ + 2, max(y0_ - 1, 0):y1_ + 2].any()
    placed = 0
    if free(136, 144, 442, 450):
        gallows(V, 140, 446, V.ground(140, 446))
    for (x, y) in ((196, 421), (150, 421)):
        if free(x - 4, x + 7, y - 1, y + 4):
            cart(V, x, y, G0, True, load=PUMPKIN if x > 160 else HAY); placed += 1
    for (x, y) in ((248, 416), (210, 416), (176, 428), (140, 416), (248, 432), (226, 468), (166, 420),
                   (206, 424), (236, 424), (122, 424)):
        if free(x, x, y, y + 1):
            lantern_post(V, x, y, V.ground(x, y), h=5, arm=(0, 1), glow=GLOW_AMBER); placed += 1
    for (x, y) in ((226, 430), (182, 416), (150, 428), (236, 470), (178, 424), (230, 420)):
        if free(x - 2, x + 2, y - 2, y + 2):
            pumpkin(V, x, y, V.ground(x, y), 2, carved=True, face=(0, 1)); placed += 1
    for (x, y) in ((230, 474), (214, 432), (160, 432), (244, 420), (200, 425), (130, 425)):
        if free(x, x + 1, y, y + 1):
            barrel(V, x, y, V.ground(x, y)); placed += 1
    F['village_keep'] = keep
    return houses


def giant_pumpkin(V, cx, cy, g):
    """Village-square jack-o'-lantern (r 8, 12 tall), carved face toward the castle (north), symmetric on x."""
    r, h = 8.5, 12
    for k in range(h):
        z = g - 1 - k
        frac = (k + 0.5) / h
        rr = r * math.sqrt(max(0.0, 1 - ((frac - 0.45) / 0.58) ** 2))
        for dx in range(-9, 10):
            for dy in range(-9, 10):
                d = math.hypot(dx, dy)
                if d <= rr:
                    a = math.atan2(dy, abs(dx))
                    rib = int(math.floor((a / math.pi) * 7 + 0.5)) % 2 == 0
                    shell = d > rr - 1.5
                    V.put(cx + dx, cy + dy, z, (PUMPKIN_DK if rib else PUMPKIN) if shell else JACK)
    for k in range(4):
        V.box(cx - 1 + (k > 1), cx + 1 - (k > 1), cy - 1, cy, g - 1 - h - k, g - 1 - h - k, STEM)
    # face (north side = -y): eyes, nose, grin; carved through the shell to the lit interior
    face = []
    for dx in (-5, -4, -3, 3, 4, 5):
        for zz in (7, 8):
            face.append((dx, zz))
    face += [(-4, 9), (4, 9), (0, 6), (-1, 5), (1, 5)]
    for dx in range(-6, 7):
        face.append((dx, 3 if abs(dx) < 6 else 4))
        if abs(dx) in (1, 2, 4, 5):
            face.append((dx, 2))
    for (dx, k) in face:
        z = g - 1 - k
        for dy in range(-9, 1):
            if V.get(cx + dx, cy + dy, z) in (PUMPKIN, PUMPKIN_DK):
                V.put(cx + dx, cy + dy, z, AIR)
                break


# ============================================================================== assembly

def keepout_mask():
    k = np.zeros((512, 512), bool)
    b = SPEC['bases'][0]; h = SPEC['spawn_half']
    k[b[0] - h - 8:b[0] + h + 9, b[1] - h - 8:b[1] + h + 9] = True          # spawn + ring
    k[60:100, 228:286] = True                                                   # tents/racks
    rx0 = SPEC['stone_circle']['c'][0]; ry0 = SPEC['stone_circle']['c'][1]; r = SPEC['stone_circle']['r']
    k[rx0 - r - 5:rx0 + r + 8, ry0 - r - 5:ry0 + r + 6] = True
    for (x0, x1, y0, y1) in SPEC['fields']:
        k[x0 - 2:x1 + 1, y0 - 4:y1 + 5] = True
    k[140:, 120:392] = True                                                     # castle + moat
    k[28:42, 142:160] = True; k[28:42, 354:372] = True                          # shrines
    t = SPEC['tag']
    k[t['x'] - 3:t['x'] + 6 * len(t['text']) + 4, t['y'] - 6:512] = True
    return k


def build(graybox=False):
    rng = np.random.default_rng(SEED)
    INTERIORS.clear()
    V = Vox()
    F = {}
    H = terrain()
    H = moat(H, F)
    voxelize(V, H, F)
    ground_paint(V, F)
    build_castle(V, F, rng)
    stats = {}
    if not graybox:
        ko = keepout_mask()
        war_camp(V, F, rng)
        pumpkin_fields(V, F, rng)
        stone_circle(V, rng)
        for (x, y) in ((34, 150), (34, 362)):
            shrine(V, x, y, rng)
        chapel(V, rng)
        ko_g = ko.copy(); ko_g[226:, :80] = True
        stats['graves'] = graveyard(V, F, rng, np.zeros((512, 512), bool))
        stats['houses'] = village(V, F, rng)
        ko2 = ko.copy()
        ko2 |= F.get('road', np.zeros((512, 512), bool))
        ko2[100:257, 20:140] = True                                             # graveyard proper
        ko2[118:257, 380:472] = True                                            # village core
        stats['trees'] = woods(V, F, rng, ko2)
    else:
        war_camp(V, F, rng)
    # keep-clear volumes: spawn squares, platform volume, courtyard sky
    b = SPEC['bases'][0]; h = SPEC['spawn_half']
    V.clear(b[0] - h, b[0] + h, b[1] - h, b[1] + h, 0, G0 - 1)
    pl = SPEC['platform']
    V.clear(pl['x'][0] - 2, 256, pl['y'][0] - 2, pl['y'][1] + 2, 0, 4)
    cx0, cx1, cy0, cy1 = SPEC['courtyard']
    # tower zone: nothing above the flagstones between the gate passage and the axis, y 206..306
    V.clear(178, 256, 214, 298, 0, G0 - 1)
    # column x = 0 has no mirror partner: keep only terrain there so the cleanup treats both edges alike
    zz = np.arange(64)[None, :]
    V.m[0][zz < F['H'][0][:, None]] = AIR
    # mirror
    V.m[257:] = V.m[255:0:-1]
    F['H_terrain'] = F['H'].copy()
    ints = []
    for (nm, x, y, z) in INTERIORS:
        if x <= 256:
            ints.append([nm + ' (W)', x, y, z])
            if x < 256:
                ints.append([nm + ' (E)', 512 - x, y, z])
    stats['interiors'] = ints
    F['H'] = np.argmax(V.m > 0, axis=2)
    stats['cleanup'] = remove_floating(V)
    return V, F, stats


def remove_floating(V):
    solid = V.m > 0
    lab, n = ndi.label(solid, structure=ndi.generate_binary_structure(3, 1))
    grounded = np.unique(lab[:, :, 62:][solid[:, :, 62:]])
    sizes = ndi.sum(solid, lab, index=np.arange(1, n + 1))
    keep = np.zeros(n + 1, bool); keep[grounded] = True
    rm = ~keep[lab] & solid
    big = []
    names = {v: k for k, v in P.M.items()}
    objs = ndi.find_objects(lab)
    for i, s_ in enumerate(sizes, 1):
        if not keep[i] and s_ > 40:
            sl = objs[i - 1]
            sub = V.m[sl][lab[sl] == i]
            vals, cnt = np.unique(sub, return_counts=True)
            big.append({'voxels': int(s_), 'mat': names.get(int(vals[np.argmax(cnt)])),
                        'x': [sl[0].start, sl[0].stop - 1], 'y': [sl[1].start, sl[1].stop - 1],
                        'z': [sl[2].start, sl[2].stop - 1]})
    big.sort(key=lambda d: -d['voxels'])
    V.m[rm] = AIR
    return {'removed_components': int(n - len(grounded)), 'removed_voxels': int(rm.sum()),
            'components_over_40': big[:30]}
