"""Assemble Floebreaker geometry. build(decor_seed) -> World.

Everything except the centre-line pieces (ship, whale), sky decor, penguins and the tag is built on the LEFT half
(x <= 256) and mirrored by array copy (x <-> 512 - x), so the gameplay geometry is exactly symmetric.
"""
from __future__ import annotations

import numpy as np

import fb_props as P
import fb_spawn as SP
from fb_paths import paint_paths
import fb_struct as S
from fb_core import MAT, World, XX, YY, fbm, sym
from fb_detail import detail_blocked, detail_pass, front_dress, penguin_pass
from fb_ship import build_ship
from fb_terrain import BASE, SPEC, berg, fill, icebergs, terrain


def mirror_world(W, H):
    for x in range(257, 512):
        W.m[x] = W.m[512 - x]
        H[x] = H[512 - x]
        W.keep[x] = W.keep[512 - x]
    for s in list(W.structures):
        x0, x1, y0, y1 = s['box']
        W.structures.append({'name': s['name'] + '_r', 'box': [512 - x1, 512 - x0, y0, y1], 'role': s['role']})
    W.interiors += [(n + '_r', 512 - x, y, z) for (n, x, y, z) in list(W.interiors)]


def build(decor_seed=1, layout_seed=7311, graybox=False):
    W = World(layout_seed, decor_seed)
    H, land, d, calm, e = terrain(W)
    rock = (fbm(layout_seed + 5, (14, 7), (1, .6)) > 0.42) & (e > 7)
    fill(W, H, rock)
    W.stats['land_pct'] = round(100 * float(land.mean()), 1)
    # ---- research stations (north: red main hall + grey lab; south: green hall + grey lab) with tents nearby
    S.station(W, H, 126, 178, family='red', name='station_n')
    S.station(W, H, 126, 318, family='green', name='station_s')
    P.tent(W, H, 104, 160, 8, 3, 'S', 'canvas_o')
    P.tent(W, H, 104, 344, 8, 3, 'S', 'canvas_g')
    # ---- observation towers and small cabins by the corridor
    S.observation_tower(W, H, 184, 206, name='tower_n')
    S.observation_tower(W, H, 184, 298, name='tower_s')
    S.cabin(W, H, 214, 214, 'wood', 'S', name='cabin_n')
    S.cabin(W, H, 214, 292, 'wood', 'N', name='cabin_s')
    # ---- crevasses and ice arches
    for pts in ([(96, 150), (120, 142), (150, 148), (176, 138)], [(96, 362), (124, 372), (152, 366), (176, 376)],
                [(196, 222), (210, 212), (232, 204)], [(196, 292), (212, 304), (232, 312)]):
        P.crevasse(W, H, pts)
    for ax, ay in ((200, 158), (200, 354)):
        P.ice_arch(W, H, ax, ay, 9, 10, 4, 'x')
    # ---- ice-spire groves (fixed layout seed)
    rng = W.lrng
    occupied = [(144, 186), (144, 326), (162, 186), (162, 326), (190, 210), (190, 302), (220, 218), (220, 296)]
    placed = []
    tries = 0
    while len(placed) < 22 and tries < 3000:
        tries += 1
        x = int(rng.integers(64, 246)); y = int(rng.integers(70, 450))
        if calm[x, y] > 0.05 or d[x, y] < 12 or H[x, y] > 60 or detail_blocked(x, y) or W.keep[max(x - 8, 0):x + 9, max(y - 8, 0):y + 9].any():
            continue
        if abs(y - 256) < 52 and x > 100:
            continue
        if any(np.hypot(x - ox, y - oy) < 24 for ox, oy in occupied + placed):
            continue
        placed.append((x, y))
    for i, (x, y) in enumerate(placed):
        P.serac_cluster(W, H, x, y, 4, seed=i)
    # ---- spawn compound: windbreaks and gear around the square, expedition lodge behind, glacier arch gate in front
    W.marks['arch_box'] = SP.spawn_compound(W, H)
    # ---- spawn-front dressing, rear backdrop, strip under the platform
    front_dress(W, H)
    detail_pass(W, H, calm, d)
    from fb_detail import keep_out
    from fb_trees import GROVES, groves
    W.stats['trees'] = groves(W, H, keep_out, d, GROVES)
    icebergs(W, H, land)
    paint_paths(W, H)
    # ---- mirror the whole left half, then the centre-line pieces
    mirror_world(W, H)
    P.whale(W, H, 255.5, 318, 416)
    build_ship(W, H)
    W.structures.append({'name': 'ship_superstructure', 'box': [243, 268, 124, 160], 'role': 'vessel'})
    W.marks['penguin_boxes'] = penguin_pass(W, H)
    # orphan cleanup: small authored fragments not grounded (diagonal-only contacts) are removed
    from scipy import ndimage as ndi
    s = W.m > 0
    s[:, :, 63] = True
    lab, n = ndi.label(s, structure=ndi.generate_binary_structure(3, 1))
    grounded = set(np.unique(lab[:, :, 62:][s[:, :, 62:]]).tolist())
    sizes = ndi.sum(s, lab, range(1, n + 1))
    bad = [i + 1 for i in range(n) if (i + 1) not in grounded]
    if bad:
        W.m[np.isin(lab, bad) & (W.m > 0)] = 0
    W.stats['orphans_removed'] = {'components': len(bad), 'voxels': int(sum(sizes[i - 1] for i in bad))}
    W.H = H
    W.land = land
    return W
