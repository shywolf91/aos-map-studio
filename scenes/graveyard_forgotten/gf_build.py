"""Graveyard of the Forgotten — The Bone Cathedral. Halloween Tower of Babel, AoS 0.75 / piqueserver 1.4.2.

Build order: terrain (+pads) -> surface materials -> spawn churchyard -> cathedral -> cemetery plots, crypts,
skull rocks, pools -> dead forest -> keep-clear masks -> mirror (x' = 512 - x) -> hands -> cleanup.
Everything gameplay-relevant is authored on the west half (x <= 256).
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage as ndi

from gf_core import fold_x, fbm2, hash3
from gf_props import *          # noqa: F401,F403
import gf_props as P
from gf_props import Local, DIRS, rng_for
from gf_terrain import G, SEED, SPEC, terrain, pad, core_mask
from gf_cathedral import cathedral
from gf_hands import hands

NAME = 'Graveyard of the Forgotten'
FILE = 'graveyard_of_the_forgotten'
VERSION = '1.0'

# ------------------------------------------------------------------------------------------- layout data
PATHS = [   # west half polylines (x, y), width
    ([(118, 231), (118, 210), (126, 188), (146, 162), (172, 140), (198, 124), (214, 114), (232, 112)], 4),
    ([(118, 281), (118, 302), (126, 324), (146, 350), (172, 372), (200, 388), (226, 392), (240, 388)], 4),
    ([(94, 256), (76, 256)], 5),                                      # west gate -> chapel
    ([(143, 256), (156, 256)], 26),                                   # spawn front (flagstones)
    ([(200, 222), (214, 206), (224, 196), (233, 192)], 3),            # court NE -> nave side door
    ([(200, 290), (214, 298), (226, 302), (233, 302)], 3),            # court SE -> choir side door
    ([(212, 222), (214, 256), (212, 290)], 5),                        # lane between court and transept
    ([(256, 100), (256, 92)], 5),                                     # parvis -> north mound (axis)
    ([(256, 352), (256, 408)], 5),                                    # apse -> south crater (axis)
    ([(146, 162), (120, 150), (84, 150), (60, 170), (48, 200)], 3),   # NW cemetery loop
    ([(146, 350), (120, 362), (84, 362), (60, 342), (48, 312)], 3),   # SW cemetery loop
    ([(172, 140), (190, 104), (214, 84), (238, 76)], 3),              # to the mound
    ([(172, 372), (190, 408), (214, 428), (232, 432)], 3),            # to the crater
    ([(84, 150), (84, 112), (110, 84), (150, 70)], 3),
    ([(84, 362), (84, 400), (110, 428), (150, 442)], 3),
]

MAUSOLEA = [   # (cx, cy, front, hw, hd, wall_h)
    (60, 182, 'E', 4, 6, 7), (96, 122, 'S', 5, 7, 8), (152, 114, 'S', 4, 6, 7), (186, 166, 'W', 3, 5, 6),
    (58, 330, 'E', 4, 6, 7), (96, 392, 'N', 5, 7, 8), (152, 398, 'N', 4, 6, 7), (186, 346, 'W', 3, 5, 6),
    (122, 64, 'S', 4, 6, 8), (124, 448, 'N', 4, 6, 8), (196, 74, 'S', 3, 5, 6), (198, 438, 'N', 3, 5, 6),
]
CRYPTS = [(140, 190, 'E'), (140, 322, 'E')]
SKULL_ROCKS = [(56, 112, 'E', 1.15), (60, 402, 'E', 1.0), (176, 56, 'S', 0.9)]
POOLS = [(160, 186, 9, 6), (106, 344, 10, 7), (200, 452, 8, 6), (176, 92, 7, 5), (70, 238, 6, 9)]
YARD_TREES = [(103, 220, 19), (129, 219, 17), (103, 293, 19), (129, 294, 17), (84, 236, 20), (84, 278, 20)]


# ------------------------------------------------------------------------------------------- helpers

def poly_mask(polys):
    m = np.zeros((512, 512), bool)
    for pts, w in polys:
        for (p, q) in zip(pts[:-1], pts[1:]):
            n = int(max(abs(q[0] - p[0]), abs(q[1] - p[1])) * 2) + 1
            for k in range(n + 1):
                x = p[0] + (q[0] - p[0]) * k / n
                y = p[1] + (q[1] - p[1]) * k / n
                r = w / 2
                x0, x1 = int(math.floor(x - r)), int(math.ceil(x + r))
                y0, y1 = int(math.floor(y - r)), int(math.ceil(y + r))
                xs, ys = np.meshgrid(np.arange(max(x0, 0), min(x1, 511) + 1),
                                     np.arange(max(y0, 0), min(y1, 511) + 1), indexing='ij')
                sel = (xs + 0.5 - x) ** 2 + (ys + 0.5 - y) ** 2 <= r * r
                m[xs[sel], ys[sel]] = True
    return m


def footprint(cx, cy, front, hw, hd, extra=1):
    fx, fy = DIRS[front]
    if fx == 0:
        return (cx - hw - extra, cx + hw + extra, cy - hd - extra - 1, cy + hd + extra + 1)
    return (cx - hd - extra - 1, cx + hd + extra + 1, cy - hw - extra, cy + hw + extra)


def mirror_west_to_east(a):
    a[257:] = a[255:0:-1]


# ------------------------------------------------------------------------------------------- build

def build(graybox=False):
    F = {}
    H, T = terrain()
    busy = np.zeros((512, 512), bool)       # nothing scattered here (structures, paths, keep-clear zones)
    sx0, sx1, sy0, sy1 = SPEC['spawn_sq']
    cx0, cx1, cy0, cy1 = SPEC['court']

    # ---------------- pads for structures on the hills (west half), then mirror the height field
    for (mx, my, fr, hw, hd, wh) in MAUSOLEA:
        a, b, c, d = footprint(mx, my, fr, hw, hd, 2)
        pad(H, a, b, c, d, margin=1, feather=7)
    for (mx, my, fr) in CRYPTS:
        pad(H, mx - 9, mx + 18, my - 8, my + 8, margin=1, feather=7)
    for (mx, my, fr, s) in SKULL_ROCKS:
        r = int(9 * s)
        pad(H, mx - r, mx + r, my - r, my + r, margin=0, feather=6)
    for (px, py, rx, ry) in POOLS:
        pad(H, int(px - rx - 2), int(px + rx + 2), int(py - ry - 2), int(py + ry + 2), margin=0, feather=6)
    tx0, tx1, ty0, ty1 = SPEC['tag_rect']
    pad(H, tx0, tx1, ty0, ty1, margin=0, feather=6)
    tag_z = int(H[tx0:tx1 + 1, ty0:ty1 + 1].max())
    H[tx0:tx1 + 1, ty0:ty1 + 1] = tag_z
    tag_save = H[:257, :].copy()
    mirror_west_to_east(H)
    F['H0'] = H.copy()

    # ---------------- surface material map
    top = np.full((512, 512), SOIL, np.uint8)
    paths = poly_mask(PATHS)
    paths[257:] = paths[255:0:-1]
    top[paths] = PATH
    xs, ys = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    fx = np.minimum(xs, 512 - xs)
    court = (fx >= cx0) & (fx <= cx1) & (ys >= cy0) & (ys <= cy1)
    court_edge = court & ~ndi.binary_erosion(court)
    top[court] = COURT
    top[court_edge] = COURT_EDGE
    yr0, yr1, yy0, yy1 = SPEC['yard_ring']
    yard = (fx >= yr0) & (fx <= yr1) & (ys >= yy0) & (ys <= yy1)
    top[yard] = GRAVEL
    px0, px1, py0, py1 = SPEC['parvis']
    top[(fx >= px0) & (ys >= py0) & (ys <= py1)] = PATH
    n_moss = fold_x(fbm2((512, 512), 14, 2, 'moss', SEED))
    top[(top == SOIL) & (n_moss > 0.66)] = MOSS
    F['paths'] = paths

    # ---------------- voxelize
    V = Vox()
    zz = np.arange(64)[None, None, :]
    solid = zz >= H[:, :, None]
    m = np.where(solid, ROCK, 0).astype(np.uint8)
    for d, mat in ((1, DIRT), (2, DIRT)):
        z = np.clip(H + d, 0, 63)
        m[xs, ys, z] = np.where(m[xs, ys, z] > 0, mat, 0)
    m[xs, ys, H] = top
    m[:, :, 63] = ROCK
    V.m = m
    F['V0'] = None
    if graybox:
        F['busy'] = busy
        return V, F

    def g_of(x, y):
        return V.ground(x, y)

    # ---------------- keep-clear masks (west half, folded coords)
    def mark(x0, x1, y0, y1):
        busy[max(x0, 0):min(x1, 511) + 1, max(y0, 0):min(y1, 511) + 1] = True
    mark(84, 160, 206, 306)                         # churchyard, front, gate tombs
    mark(cx0 - 2, 256, cy0 - 4, cy1 + 4)            # courtyard + lane + transept/crossing
    mark(206, 256, 94, 378)                         # cathedral precinct
    busy |= paths
    mark(tx0, tx1, ty0, ty1)
    (hx, hy) = SPEC['hand_up']; mark(hx - 30, 256, hy - 30, hy + 30)
    (hx, hy) = SPEC['hand_claw']; mark(hx - 34, 256, hy - 34, hy + 36)

    # ---------------- spawn churchyard (west team)
    rng = rng_for('yard', SEED)
    gates = SPEC['yard_gates']

    def ring_runs():
        """Polylines of the railing with the four gates left open."""
        e0, e1 = gates['E']; w0, w1 = gates['W']; n0, n1 = gates['N']
        return [
            [(yr0, yy0), (n0 - 1, yy0)], [(n1 + 1, yy0), (yr1, yy0), (yr1, e0 - 1)],
            [(yr1, e1 + 1), (yr1, yy1), (n1 + 1, yy1)], [(n0 - 1, yy1), (yr0, yy1), (yr0, w1 + 1)],
            [(yr0, w0 - 1), (yr0, yy0)],
        ]
    for run in ring_runs():
        iron_fence(V, run, g_of, h=3)
    # gate piers: tall banner piers at the front (no arch over the spawn front), arched side gates
    if SPEC.get('bone_gate', True):
        bone_gate(V, yr1, 256, G, gates['E'][1] - gates['E'][0] + 1, rng)
    else:
        gate_pillars(V, yr1, 256, G, (1, 0), gates['E'][1] - gates['E'][0] + 1 - 4, rng, banner=True)
    for (x, y, fr, gap) in ((118, yy0, (0, -1), 11), (118, yy1, (0, 1), 11), (yr0, 256, (-1, 0), 9)):
        gate_pillars(V, x, y, G, fr, gap, rng, banner=False, skull=(fr[0] == 0))
    # gate tombs flanking the front
    for (tx, ty, fr) in SPEC['gate_tombs']:
        mausoleum(V, tx, ty, G, fr, rng, hw=4, hd=6, wall_h=9, spire=True, banner=True)
    # ossuary chapel behind the spawn
    chx, chy = SPEC['chapel']
    mausoleum(V, chx, chy, G, (1, 0), rng_for('chapel', SEED), hw=7, hd=10, wall_h=11, spire=True, cracked=0.03)
    bone_pile(V, 80, 246, G, rng_for('bp1', SEED), 7)
    bone_pile(V, 80, 266, G, rng_for('bp2', SEED), 7)
    for (lx, ly) in ((140, 240), (140, 272), (97, 228), (97, 284)):
        lantern_post(V, lx, ly, G, 5)
    # yard trees (cover for the spawn), one with a gibbet cage
    for i, (x, y, h) in enumerate(YARD_TREES):
        tips = dead_tree(V, x, y, G, rng_for('ytree', i, SEED), h=h, trunk_r=2.0)
        if i in (0, 4):
            tip = max(tips, key=lambda t: t[0][2])
            p = tip[0]
            if 0 < p[2] < G - 10:
                hanging_cage(V, int(p[0]), int(p[1]), int(p[2]), 3)

    # ---------------- cathedral
    tops = cathedral(V, rng_for('cathedral', SEED))
    # lawn graves and lanterns on the precinct sides (outside the court + lane)
    rngp = rng_for('precinct', SEED)
    for y in range(150, 214, 9):
        headstone(V, 218, y, G, (-1, 0), int(rngp.integers(0, 5)), rngp, lean=int(rngp.integers(-1, 2)) * (rngp.random() < 0.3))
    for y in range(306, 372, 9):
        headstone(V, 218, y, G, (-1, 0), int(rngp.integers(0, 5)), rngp, lean=int(rngp.integers(-1, 2)) * (rngp.random() < 0.3))
    for (lx, ly) in ((214, 212), (214, 300), (232, 108), (238, 384)):
        lantern_post(V, lx, ly, G, 6)

    # ---------------- cemetery: mausolea, crypts, skull rocks, pools
    for i, (mx, my, fr, hw, hd, wh) in enumerate(MAUSOLEA):
        g = g_of(mx, my)
        mausoleum(V, mx, my, g, DIRS[fr], rng_for('maus', i, SEED), hw=hw, hd=hd, wall_h=wh,
                  spire=(i % 3 != 2), door=(i % 4 != 3))
        a, b, c, d = footprint(mx, my, fr, hw, hd, 3)
        mark(a, b, c, d)
    for i, (mx, my, fr) in enumerate(CRYPTS):
        g = g_of(mx, my)
        crypt_entrance(V, mx, my, g, DIRS[fr], rng_for('crypt', i, SEED), depth=6)
        mark(mx - 9, mx + 20, my - 9, my + 9)
    for i, (mx, my, fr, s) in enumerate(SKULL_ROCKS):
        g = g_of(mx, my)
        skull_rock(V, mx, my, g, DIRS[fr], s)
        r = int(10 * s)
        mark(mx - r - 2, mx + r + 2, my - r - 2, my + r + 2)
    for i, (px_, py_, rx, ry) in enumerate(POOLS):
        pool(V, px_, py_, rx, ry, g_of, rng_for('pool', i, SEED))
        mark(int(px_ - rx - 3), int(px_ + rx + 3), int(py_ - ry - 3), int(py_ + ry + 3))

    # ---------------- cemetery plots with rows of graves (and enclosure walls/fences)
    rng = rng_for('plots', SEED)
    n_graves = 0
    rim = T['rim']
    plot_cells = []
    for gx in range(14, 236, 30):
        for gy in range(10, 502, 26):
            px_ = gx + int(rng.integers(-5, 6)); py_ = gy + int(rng.integers(-4, 5))
            plot_cells.append((px_, py_))
    for (px_, py_) in plot_cells:
        w = int(rng.integers(20, 30)); h = int(rng.integers(14, 22))
        x0, x1, y0, y1 = px_ - w // 2, px_ + w // 2, py_ - h // 2, py_ + h // 2
        if x0 < 6 or x1 > 250 or y0 < 6 or y1 > 505:
            continue
        sub = busy[x0:x1 + 1, y0:y1 + 1]
        if sub.mean() > 0.15:
            continue
        r_here = rim[px_, py_]
        kind = 'rows' if r_here < 0.25 else 'forgotten'
        if rng.random() < 0.18:
            kind = 'forgotten'
        front = DIRS['S' if rng.random() < 0.5 else 'N'] if rng.random() < 0.7 else DIRS['E' if rng.random() < 0.5 else 'W']
        dens = 1.0 if kind == 'rows' else 0.35
        if front[0] == 0:
            rows = range(y0 + 7, y1 + 1, int(rng.integers(7, 9)))
            for yy in rows:
                for xx in range(x0 + 2, x1 - 1, int(rng.integers(4, 6))):
                    xj = xx + int(rng.integers(-1, 2)) * (kind == 'forgotten')
                    if rng.random() > dens * 0.92 or busy[xj - 1:xj + 2, yy - 7:yy + 2].any():
                        continue
                    n_graves += _grave(V, xj, yy, front, rng, kind, g_of)
        else:
            cols = range(x0 + 7, x1 + 1, int(rng.integers(7, 9)))
            for xx in cols:
                for yy in range(y0 + 2, y1 - 1, int(rng.integers(4, 6))):
                    if rng.random() > dens * 0.92 or busy[xx - 7:xx + 2, yy - 1:yy + 2].any():
                        continue
                    n_graves += _grave(V, xx, yy, front, rng, kind, g_of)
        # enclosure
        if kind == 'rows' and rng.random() < 0.55:
            e = 2
            ring = [(x0 - e, y0 - e), (x1 + e, y0 - e), (x1 + e, y1 + e), (x0 - e, y1 + e), (x0 - e, y0 - e)]
            gate_side = int(rng.integers(4))
            a, b = ring[gate_side], ring[gate_side + 1]
            mx_, my_ = (a[0] + b[0]) // 2, (a[1] + b[1]) // 2
            segs = []
            for i in range(4):
                p, q = ring[i], ring[i + 1]
                if i == gate_side:
                    if p[0] == q[0]:
                        sgn = 1 if q[1] > p[1] else -1
                        segs.append([p, (p[0], my_ - 3 * sgn)]); segs.append([(p[0], my_ + 3 * sgn), q])
                    else:
                        sgn = 1 if q[0] > p[0] else -1
                        segs.append([p, (mx_ - 3 * sgn, p[1])]); segs.append([(mx_ + 3 * sgn, p[1]), q])
                else:
                    segs.append([p, q])
            use_wall = rng.random() < 0.5
            for s_ in segs:
                ok = all(not busy[min(max(int(t[0]), 0), 511), min(max(int(t[1]), 0), 511)] for t in s_)
                if not ok:
                    continue
                if use_wall:
                    stone_wall(V, s_, g_of, rng, h=3, thick=1, gaps=0.12)
                else:
                    iron_fence(V, s_, g_of, h=3)
        if kind == 'rows' and rng.random() < 0.4:
            # open grave and a bone scatter in the plot
            ox, oy = int(rng.integers(x0 + 3, x1 - 3)), int(rng.integers(y0 + 3, y1 - 3))
            if not busy[ox - 5:ox + 6, oy - 8:oy + 3].any():
                open_grave(V, ox, oy, g_of(ox, oy), front, rng)
                busy[ox - 5:ox + 6, oy - 8:oy + 3] = True
        if rng.random() < 0.3:
            bx, by = int(rng.integers(x0, x1)), int(rng.integers(y0, y1))
            if not busy[bx - 4:bx + 5, by - 4:by + 5].any():
                bone_pile(V, bx, by, g_of(bx, by), rng, int(rng.integers(3, 7)))
        busy[x0 - 2:x1 + 3, y0 - 2:y1 + 3] = True
    F['graves_west'] = n_graves

    # lanterns along the main cemetery paths
    for (pts, w) in PATHS[:2] + PATHS[9:]:
        for (p, q) in zip(pts[:-1], pts[1:]):
            L = math.hypot(q[0] - p[0], q[1] - p[1])
            if L < 20:
                continue
            t = 0.5
            x = int(p[0] + (q[0] - p[0]) * t + 4); y = int(p[1] + (q[1] - p[1]) * t)
            if not busy[x, y] or paths[x, y]:
                lantern_post(V, x, y, g_of(x, y), 5)

    # ---------------- dead trees: sparse in the cemetery, a dense forest on the rim
    rngt = rng_for('trees', SEED)
    trees = []
    for gx in range(4, 252, 10):
        for gy in range(4, 508, 10):
            x = gx + int(rngt.integers(-3, 4)); y = gy + int(rngt.integers(-3, 4))
            if not (2 <= x <= 248 and 2 <= y <= 509):
                continue
            r_here = rim[x, y]
            p_tree = 0.72 if r_here > 0.35 else (0.42 if r_here > 0.12 else 0.07)
            if rngt.random() > p_tree:
                continue
            core_near = busy[max(x - 3, 0):x + 4, max(y - 3, 0):y + 4].any()
            if core_near and r_here < 0.35:
                continue
            if paths[max(x - 2, 0):x + 3, max(y - 2, 0):y + 3].any():
                continue
            if tx0 - 4 <= x <= tx1 + 4 and ty0 - 8 <= y <= ty1 + 4:
                continue
            g = g_of(x, y)
            h = int(rngt.integers(14, 23)) if r_here > 0.35 else int(rngt.integers(12, 19))
            h = min(h, g - 3)
            trees.append((x, y, g, h))
    for i, (x, y, g, h) in enumerate(trees):
        tips = dead_tree(V, x, y, g, rng_for('tree', i, SEED), h=h, trunk_r=1.3 + 0.6 * rngt.random())
        if rngt.random() < 0.05:
            tip = max(tips, key=lambda t: t[0][2])
            p = tip[0]
            if 6 < p[2] < g - 9:
                hanging_cage(V, int(p[0]), int(p[1]), int(p[2]), 2)
    F['trees_west'] = len(trees)

    # ---------------- keep-clear volumes (spawn square, courtyard, anchors, front, platform volume)
    V.m[sx0:sx1 + 1, sy0:sy1 + 1, :G] = 0
    V.m[cx0:cx1 + 1, cy0:cy1 + 1, :G] = 0
    V.m[143:156, 243:270, :G] = 0
    V.m[tx0:tx1 + 1, ty0:ty1 + 1, :tag_z] = 0
    p = SPEC['platform']
    V.m[p['x'][0] - 1:p['x'][1] + 2, p['y'][0] - 1:p['y'][1] + 2, 0:3] = 0

    # x = 0 has no mirror column: strip props there so nothing on the west edge leans on it
    col0 = np.arange(64)[None, :] < F['H0'][0][:, None]
    V.m[0][col0] = 0
    # ---------------- mirror, then the hands (axis pieces, cosmetic asymmetry)
    V.m[257:] = V.m[255:0:-1]
    F['hands'] = hands(V)

    # ---------------- cleanup: drop tiny orphans; report anything bigger
    solid = V.m > 0
    solid[:, :, 63] = True
    lab, n = ndi.label(solid, structure=ndi.generate_binary_structure(3, 1))
    sizes = np.bincount(lab.ravel())
    grounded = np.unique(lab[:, :, 62:][solid[:, :, 62:]])
    floating = np.setdiff1d(np.arange(1, n + 1), grounded)
    small = floating[sizes[floating] <= 60]
    big = floating[sizes[floating] > 60]
    if len(small):
        V.m[np.isin(lab, small)] = 0
    F['cleanup'] = {'removed_components': int(len(small)), 'removed_voxels': int(sizes[small].sum()),
                    'big_floating_left': [int(sizes[b]) for b in big]}
    # cosmetic asymmetric boxes (hands) for the mirror check
    F['cosmetic_bboxes'] = [h['bbox'] for h in F['hands']]
    F['tag_z'] = tag_z
    return V, F


def _grave(V, x, y, front, rng, kind, g_of):
    g = g_of(x, y)
    # skip uneven ground (keeps stones seated)
    L = Local(x, y, front)
    gs = [g_of(*L.xy(u, v)) for u in (-1, 0, 1) for v in (0, -3)]
    if max(gs) - min(gs) > 1:
        return 0
    if kind == 'forgotten':
        k = int(rng.choice([0, 2, 5, 6, 6, 1]))
    else:
        k = int(rng.choice([0, 0, 0, 1, 1, 2, 2, 3, 4, 4, 5, 6]))
    lean = int(rng.choice([-1, 0, 0, 0, 1])) if k not in (5, 6) else 0
    headstone(V, x, y, g, front, k, rng, lean)
    return 1
