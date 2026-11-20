"""Assemble Floebreaker geometry (graybox + props). build(decor_seed) -> World."""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

import fb_props as P
from fb_detail import detail_blocked, detail_pass
from fb_core import MAT, World, XX, YY, fbm, sym
from fb_ship import build_ship
from fb_terrain import BASE, SPEC, berg, fill, icebergs, terrain

FLIP = {'E': 'W', 'W': 'E', 'S': 'S', 'N': 'N'}


def mirror_hut(W, H, x0, y0, w, d, door, **kw):
    """Place a hut and its x-mirror."""
    P.hut(W, H, x0, y0, w, d, door, **kw)
    P.hut(W, H, 513 - x0 - w, y0, w, d, FLIP[door], **kw)


def mirror_tent(W, H, x0, y0, length, half, door, mat):
    P.tent(W, H, x0, y0, length, half, door, mat)
    P.tent(W, H, 512 - (x0 + 2 * half), y0, length, half, door, mat)


def build(decor_seed=1, layout_seed=7311, graybox=False):
    W = World(layout_seed, decor_seed)
    H, land, d, calm, e = terrain(W)
    rock = (fbm(layout_seed + 5, (14, 7), (1, .6)) > 0.42) & (e > 7)
    fill(W, H, rock)
    W.stats['land_pct'] = round(100 * float(land.mean()), 1)
    # ---- spawn cover: staggered fins east of the blue square (mirrored for red)
    blue_rows = [(142, 206, 262, 5, 29, 8), (152, 250, 308, 5, 29, -8)]
    for i, (cx, y0, y1, th, zt, ln) in enumerate(blue_rows):
        P.fin_wall(W, H, cx, y0, y1, th, zt, ln, seed=100 + i)
        P.fin_wall(W, H, 512 - cx - th + 1, y0, y1, th, zt, -ln, seed=100 + i)
    P.whale(W, H, 255.5, 318, 416)
    build_ship(W, H)
    # ---- research camps (4, mirrored) in the centre zone
    camps = [(146, 186, 'S'), (146, 322, 'N')]
    for hx, hy, door in camps:
        mirror_hut(W, H, hx, hy, 9, 7, door, mat='dwood', roof='plank')
        mirror_tent(W, H, hx - 14, hy + (6 if door == 'S' else -4), 8, 3, 'S', 'canvas_o')
        mirror_tent(W, H, hx + 18, hy + (10 if door == 'S' else -8), 8, 3, 'S', 'canvas_g')
        for k, (ox, oy) in enumerate(((-2, -3 if door == 'S' else 9), (12, -3 if door == 'S' else 9))):
            for xx in (hx + ox, 512 - (hx + ox)):
                P.lamp_post(W, H, xx, hy + oy)
        for xx in (hx + 12, 513 - hx - 12 - 2):
            P.drum_group(W, H, xx, hy + (8 if door == 'S' else -3), 3, seed=hx + hy)
        for xx in (hx - 6, 513 - hx + 6 - 5):
            P.crates(W, H, xx, hy + (11 if door == 'S' else -6), seed=hx)
        for xx in (hx + 20, 512 - hx - 20 - 2):
            P.sled(W, H, xx, hy + (1 if door == 'S' else 0))
    # ---- weather towers
    for tx, ty in ((184, 204), (184, 300)):
        P.weather_tower(W, H, tx, ty)
        P.weather_tower(W, H, 513 - tx - 9, ty)
    # ---- crevasses (V notches with blue ice walls)
    for pts in ([(96, 150), (120, 142), (150, 148), (176, 138)], [(96, 362), (124, 372), (152, 366), (176, 376)],
                [(196, 222), (210, 212), (232, 204)], [(196, 292), (212, 304), (232, 312)]):
        P.crevasse(W, H, pts)
        P.crevasse(W, H, [(512 - px, py) for px, py in pts])
    # ---- ice arches (walk-through gates)
    for ax, ay in ((200, 158), (200, 354), (130, 96), (130, 416)):
        P.ice_arch(W, H, ax, ay, 9, 10, 4, 'x')
        P.ice_arch(W, H, 512 - ax - 4, ay, 9, 10, 4, 'x')
    # ---- serac clusters scattered in groves (fixed layout seed), kept off the calm zones
    rng = W.lrng
    occupied = [(150, 190), (150, 326), (362, 190), (362, 326), (190, 208), (190, 304), (322, 208), (322, 304)]
    placed = []
    tries = 0
    while len(placed) < 22 and tries < 3000:
        tries += 1
        x = int(rng.integers(64, 256)); y = int(rng.integers(70, 450))
        if calm[x, y] > 0.05 or d[x, y] < 12 or H[x, y] > 60 or detail_blocked(x, y):
            continue
        if abs(y - 256) < 52 and x > 100:
            continue
        if any(np.hypot(x - ox, y - oy) < 24 for ox, oy in occupied + placed):
            continue
        placed.append((x, y))
    for i, (x, y) in enumerate(placed):
        P.serac_cluster(W, H, x, y, 4, seed=i)
        P.serac_cluster(W, H, 512 - x, y, 4, seed=i + 500)
    # ---- base camps behind each spawn (outside the +-20 square)
    for bx, by in SPEC['bases']:
        s = -1 if bx < 256 else 1
        for dy, door in ((-26, 'S'), (+26, 'N')):
            hx = bx + s * 34 - (4 if s < 0 else 4)
            P.hut(W, H, hx, by + dy - 3, 9, 7, 'E' if s < 0 else 'W')
        P.tent(W, H, bx + s * 34 - 3, by - 3, 8, 3, 'S', 'canvas_o' if s < 0 else 'canvas_g')
    # ice-fishing huts on the pond shelves by the corridor (real rooms)
    for hx, hy, dr in ((214, 216, 'S'), (214, 292, 'N')):
        mirror_hut(W, H, hx, hy, 7, 6, dr, mat='dwood', roof='orange')
    detail_pass(W, H, calm, d)
    # ---- icebergs
    W.marks['bergs'] = icebergs(W, H, land)
    # ---- whale + ship (centre-line pieces, built after mirroring)
    W.H = H
    W.land = land
    return W
