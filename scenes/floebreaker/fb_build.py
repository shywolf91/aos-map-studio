"""Assemble Floebreaker geometry. build(decor_seed) -> World.

Everything except the centre-line pieces (ship, whale), sky decor, penguins and the tag is built on the LEFT half
(x <= 256) and mirrored by array copy (x <-> 512 - x), so the gameplay geometry is exactly symmetric.
"""
from __future__ import annotations

import numpy as np

import fb_props as P
from fb_core import MAT, World, XX, YY, fbm, sym
from fb_detail import detail_blocked, detail_pass, front_dress, penguin_pass
from fb_ship import build_ship
from fb_terrain import BASE, SPEC, berg, fill, icebergs, terrain


def mirror_world(W, H):
    for x in range(257, 512):
        W.m[x] = W.m[512 - x]
        H[x] = H[512 - x]


def build(decor_seed=1, layout_seed=7311, graybox=False):
    W = World(layout_seed, decor_seed)
    H, land, d, calm, e = terrain(W)
    rock = (fbm(layout_seed + 5, (14, 7), (1, .6)) > 0.42) & (e > 7)
    fill(W, H, rock)
    W.stats['land_pct'] = round(100 * float(land.mean()), 1)
    # ---- research camps (left half; mirrored later)
    for hx, hy, door in ((146, 186, 'S'), (146, 322, 'N')):
        P.hut(W, H, hx, hy, 9, 7, door, mat='dwood', roof='plank')
        P.tent(W, H, hx - 14, hy + (6 if door == 'S' else -4), 8, 3, 'S', 'canvas_o')
        P.tent(W, H, hx + 18, hy + (10 if door == 'S' else -8), 8, 3, 'S', 'canvas_g')
        for ox in (-2, 12):
            P.lamp_post(W, H, hx + ox, hy + (-3 if door == 'S' else 9))
        P.drum_group(W, H, hx + 12, hy + (8 if door == 'S' else -3), 3, seed=hx + hy)
        P.crates(W, H, hx - 6, hy + (11 if door == 'S' else -6), seed=hx)
        P.sled(W, H, hx + 20, hy + (1 if door == 'S' else 0))
    # ---- weather towers, ice-fishing huts
    for tx, ty in ((184, 204), (184, 300)):
        P.weather_tower(W, H, tx, ty)
    for hx, hy, dr in ((214, 216, 'S'), (214, 292, 'N')):
        P.hut(W, H, hx, hy, 7, 6, dr, mat='dwood', roof='orange')
    # ---- crevasses and ice arches
    for pts in ([(96, 150), (120, 142), (150, 148), (176, 138)], [(96, 362), (124, 372), (152, 366), (176, 376)],
                [(196, 222), (210, 212), (232, 204)], [(196, 292), (212, 304), (232, 312)]):
        P.crevasse(W, H, pts)
    for ax, ay in ((200, 158), (200, 354), (130, 96), (130, 416)):
        P.ice_arch(W, H, ax, ay, 9, 10, 4, 'x')
    # ---- ice-spire groves (fixed layout seed)
    rng = W.lrng
    occupied = [(150, 190), (150, 326), (190, 208), (190, 304), (222, 220), (222, 296)]
    placed = []
    tries = 0
    while len(placed) < 22 and tries < 3000:
        tries += 1
        x = int(rng.integers(64, 246)); y = int(rng.integers(70, 450))
        if calm[x, y] > 0.05 or d[x, y] < 12 or H[x, y] > 60 or detail_blocked(x, y):
            continue
        if abs(y - 256) < 52 and x > 100:
            continue
        if any(np.hypot(x - ox, y - oy) < 24 for ox, oy in occupied + placed):
            continue
        placed.append((x, y))
    for i, (x, y) in enumerate(placed):
        P.serac_cluster(W, H, x, y, 4, seed=i)
    # ---- base camp behind the blue spawn (outside the +-20 square)
    bx, by = SPEC['bases'][0]
    for dy in (-26, +26):
        P.hut(W, H, bx - 38, by + dy - 3, 9, 7, 'E')
    P.tent(W, H, bx - 37, by - 3, 8, 3, 'S', 'canvas_o')
    # ---- spawn-front dressing, rear backdrop, strip under the platform
    front_dress(W, H)
    detail_pass(W, H, calm, d)
    icebergs(W, H, land)
    # ---- mirror the whole left half, then the centre-line pieces
    mirror_world(W, H)
    P.whale(W, H, 255.5, 318, 416)
    build_ship(W, H)
    W.marks['penguin_boxes'] = penguin_pass(W, H)
    W.H = H
    W.land = land
    return W
