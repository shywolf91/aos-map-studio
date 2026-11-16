"""Yulehaven Isles extra checks (island Babel with damaging water), on top of aosmap.kit.babel_checks.

water_routes   fewest water (wading) cells on the best route from each spawn to: the islet, the enemy spawn, the
               enemy spawn by the north / south flank chains, the islet sea cave through the passage. Graph model
               (aosmap.kit Nav, 3 air to stand, step 1, drops <= 9); a water cell is a z 63 node.
dry_shortcut   is any dry (0 water cells) route from a spawn island to the islet or to the enemy island? (should be
               false: the crossings are the rock hops, the wading lane, the chains and the roofed passage)
passage_roof   can a player walk along the passage roof across the channel (dry)? (should be false)
"""
from __future__ import annotations

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

from aosmap.kit import codec
from aosmap.kit.babel_checks import Nav
from aosmap.kit.params import BABEL_DEFAULT


def run(out, data, info, S):
    solid = codec.decode(data)[0]
    nav = Nav(solid)
    p = nav.xyz
    water = p[:, 2] == 63
    G = nav.G.tocoo()
    w = 1.0 + 1000.0 * water[G.col]
    Gw = csr_matrix((w, (G.row, G.col)), shape=nav.G.shape)
    half = BABEL_DEFAULT['spawn_half']
    R = {}
    boxes = {
        'islet': (232, 280, 190, 330, 40, 62),
        'enemy_spawn': None,
        'north_chain_mid': (242, 270, 72, 100, 40, 62),
        'south_chain_mid': (242, 270, 411, 439, 40, 62),
        'islet_sea_cave': (240, 272, 312, 324, 58, 62),
        'cargo_hold': (249, 263, 234, 288, 59, 61),
    }
    for k, (name, b) in enumerate(zip(('blue', 'red'), BABEL_DEFAULT['bases'])):
        other = BABEL_DEFAULT['bases'][1 - k]
        src = nav.nodes_in(b[0] - half, b[0] + half, b[1] - half, b[1] + half, 0, 62)
        d = dijkstra(Gw, directed=True, indices=src, min_only=True)
        r = {}
        for tn, bx in boxes.items():
            if bx is None:
                bx = (other[0] - half, other[0] + half, other[1] - half, other[1] + half, 0, 62)
            nodes = nav.nodes_in(*bx)
            if len(nodes) and np.isfinite(d[nodes]).any():
                c = float(np.min(d[nodes]))
                r[tn] = {'water_cells': int(c // 1000), 'steps': int(c % 1000)}
            else:
                r[tn] = None
        R[name] = r
    out_ = {'water_routes': R}
    out_['dry_shortcut'] = {t: any(R[t][k] is not None and R[t][k]['water_cells'] == 0 for k in ('islet', 'enemy_spawn'))
                            for t in R}
    # passage roof: standable dry nodes on the roof over the water columns, can they connect across?
    pz = info.get('passage') or {}
    if pz:
        x0, x1 = pz['x']
        yc = pz['y']
        roof = nav.nodes_in(x0, x1, yc - 3, yc + 3, 40, 58)
        xs = p[roof, 0]
        west = roof[xs <= x0 + 26]
        east = roof[xs >= x1 - 6]
        if len(west) and len(east):
            d = dijkstra(Gw, directed=True, indices=west, min_only=True)
            c = float(np.min(d[east])) if np.isfinite(d[east]).any() else None
            out_['passage_roof'] = {'dry_crossing': bool(c is not None and c < 1000), 'cost': c}
        else:
            out_['passage_roof'] = {'dry_crossing': False, 'roof_nodes': int(len(roof))}
    return out_
