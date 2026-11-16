"""Cursed Skull Reef extra checks (island Babel with damaging water, assist structures), on top of
aosmap.kit.babel_checks.

water_routes   fewest water (wading) cells on the best route from each spawn to: the enemy spawn, the fort rampart,
               the skull sea cave and eye rooms, the north / south chain middles, the own and enemy crow's nests.
               Graph model (aosmap.kit Nav: 3 air to stand, step 1, drops <= 9); a water cell is a z 63 node.
flank_dry      fewest water cells spawn -> enemy spawn with the centre band removed (the kit flank definition):
               the flank must be dry (owner: no walkable-sea flank).
assist         per crow's nest: top z, blocks to build to platform level, horizontal gap to the platform footprint,
               steps (graph cost) from each spawn, and whether it is inside the platform's z <= 2 keep-out (must not).
"""
from __future__ import annotations

import math

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

from aosmap.kit import codec
from aosmap.kit.babel_checks import Nav
from aosmap.kit.params import BABEL_DEFAULT as P


def run(out, data, info, S):
    solid = codec.decode(data)[0]
    nav = Nav(solid)
    p = nav.xyz
    water = p[:, 2] == 63
    Gw = nav.G.tocsr().copy()
    Gw.sum_duplicates()
    Gw.data = (1.0 + 1000.0 * water[Gw.indices]).astype(float)   # hop count; a water node costs 1000
    half = P['spawn_half']
    tg = dict(info.get('check_targets') or {})
    R = {}
    dists = {}
    for k, (name, b) in enumerate(zip(P['team_names'], P['bases'])):
        other = P['bases'][1 - k]
        src = nav.nodes_in(b[0] - half, b[0] + half, b[1] - half, b[1] + half, 0, 62)
        d = dijkstra(Gw, directed=True, indices=src, min_only=True)
        dists[name] = d
        r = {}
        boxes = dict(tg)
        boxes['enemy_spawn'] = (other[0] - half, other[0] + half, other[1] - half, other[1] + half, 0, 62)
        for tn, bx in boxes.items():
            nodes = nav.nodes_in(*bx[:6])
            if len(nodes) and np.isfinite(d[nodes]).any():
                c = float(np.min(d[nodes]))
                r[tn] = {'water_cells': int(c // 1000), 'steps': int(c % 1000)}
            else:
                r[tn] = None
        R[name] = r
    res = {'water_routes': R}
    # dry flank (kit definition of the flank band)
    cx0, cx1 = 256 - 80, 256 + 80
    fl = {}
    for side, sgn in (('north', -1), ('south', 1)):
        dy = (p[:, 1] - 256) * sgn
        band = (p[:, 0] >= cx0) & (p[:, 0] <= cx1)
        keep = ~band | ((dy >= 130) & (dy <= 210))
        Gc = Gw.tocsr()
        mask = np.zeros(len(p), bool)
        mask[np.nonzero(keep)[0]] = True
        coo = Gc.tocoo()
        ok = mask[coo.row] & mask[coo.col]
        Gk = csr_matrix((coo.data[ok], (coo.row[ok], coo.col[ok])), shape=Gc.shape)
        b, o = P['bases']
        src = nav.nodes_in(b[0] - half, b[0] + half, b[1] - half, b[1] + half, 0, 62)
        d = dijkstra(Gk, directed=True, indices=src, min_only=True)
        tgt = nav.nodes_in(o[0] - half, o[0] + half, o[1] - half, o[1] + half, 0, 62)
        c = float(np.min(d[tgt])) if np.isfinite(d[tgt]).any() else None
        fl[side] = None if c is None else {'water_cells': int(c // 1000), 'steps': int(c % 1000)}
    res['flank_dry'] = fl
    # assist structures: crow's nest geometry
    (px0, px1), (py0, py1), pz = P['platform_x'], P['platform_y'], P['platform_z']
    A = {}
    for name in ('blue_crow_nest', 'red_crow_nest'):
        bx = tg.get(name)
        if not bx:
            continue
        nodes = nav.nodes_in(*bx[:6])
        if not len(nodes):
            A[name] = None
            continue
        zmin = int(p[nodes, 2].min())
        topn = nodes[p[nodes, 2] == zmin]
        hd = []
        for i in topn:
            x, y = p[i, 0], p[i, 1]
            dx = max(px0 - x, x - px1, 0)
            dy = max(py0 - y, y - py1, 0)
            hd.append(math.hypot(dx, dy))
        A[name] = {'top_z': zmin, 'blocks_to_platform_level': zmin - (pz + 1),
                   'horizontal_gap_to_platform': round(min(hd), 1),
                   'steps_from': {t: (int(np.min(dists[t][nodes])) % 1000 if np.isfinite(dists[t][nodes]).any()
                                      else None) for t in dists},
                   'water_cells_from': {t: (int(np.min(dists[t][nodes])) // 1000
                                            if np.isfinite(dists[t][nodes]).any() else None) for t in dists}}
    res['assist'] = A
    # keep-out over the platform footprint (z 0..3) must stay empty
    res['platform_keepout_voxels'] = int(solid[px0:px1 + 1, py0:py1 + 1, 0:4].sum())
    return res
