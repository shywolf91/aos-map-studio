"""Validation for Drowned Cathedral v2 (rotated layout): everything the v1 check does (structure, zone/spawn flatness,
platform clearance, build gaps, routes + parity, spawn exposure) on v2 targets, plus a SAFE-DESCENT check: the same
nav graph with every damaging drop (fall >= 10 voxels) removed, so a route that still exists is one a player can take
from spawn down to the tower zone, the fen and the cathedral without taking fall damage. Preliminary nav model
(3-voxel standing clearance, 1-voxel auto-step, 2-voxel jump edges), not an in-game test.

Run: python scenes/drowned_cathedral_v2_check.py maps/drowned_cathedral_v2
"""
import os
import sys

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scenes.drowned_cathedral_v2 as V                                      # noqa: E402  (configures SPEC)
from scenes import drowned_cathedral_check as C                             # noqa: E402
from scenes.drowned_cathedral import SPEC, BANK                              # noqa: E402
from aosmap import nav                                                       # noqa: E402

TX0 = SPEC['cathedral']['transept']['x'][0]
TARGETS = {
    'esplanade_edge': (204, 256, BANK),
    'gallery': (222, 256, BANK),
    'ghat_foot': (161, 191, 59),
    'precinct_ghat_foot': (129, 170, 59),
    'fen_water_north': (200, 165, 63),
    'nave_floor': (238, 252, 59),
    'crossing_floor': (254, 250, 59),
    'transept_north_door': (255, TX0 + 3, 59),
    'belfry_floor': (250, 252, 32),
    'enemy_esplanade': (308, 256, BANK),
    'enemy_spawn': (394, 256, BANK),
}


def safe_descent(R, vm, g, D, L, plat):
    src, dst, cost, kind = g.edges
    n = len(g.node_xyz)
    keep = kind != 4
    Ms = coo_matrix((cost[keep], (src[keep], dst[keep])), shape=(n, n)).tocsr()
    sc = SPEC['script_constants']
    xyz = g.node_xyz
    fen = L.inside[xyz[:, 0], xyz[:, 1]] & (xyz[:, 2] >= 59)
    out = {}
    for ti, (team, base) in enumerate((('team1', sc['bases'][0]), ('team2', sc['bases'][1]))):
        srcs = nav.zone_nodes(g, *base, sc['spawn_half'])
        ds = dijkstra(Ms, directed=True, indices=srcs, min_only=True)
        da = D[team]
        side = (xyz[:, 0] < 256) if ti == 0 else (xyz[:, 0] > 256)
        tg = {}
        for nm, (x, y, z) in TARGETS.items():
            xx = x if ti == 0 else 512 - x
            k = C.snap(g, xx, y, z)
            tg[nm] = {'any': round(float(da[k]), 1) if k >= 0 and np.isfinite(da[k]) else None,
                      'no_fall_damage': round(float(ds[k]), 1) if k >= 0 and np.isfinite(ds[k]) else None}
        own_fen = fen & side
        reach_any = np.isfinite(da) & own_fen
        reach_safe = np.isfinite(ds) & own_fen
        # way back up: from any own-side fen node to the spawn without fall damage (reverse graph)
        back = dijkstra(Ms.T.tocsr(), directed=True, indices=srcs, min_only=True)
        out[team] = {'targets': tg,
                     'fen_nodes_own_half': int(own_fen.sum()),
                     'fen_nodes_reachable_any': int(reach_any.sum()),
                     'fen_nodes_reachable_without_fall_damage': int(reach_safe.sum()),
                     'fen_nodes_that_can_walk_back_to_spawn_safely': int((np.isfinite(back) & own_fen).sum()),
                     # reachable without fall damage but no way back without a damaging drop or placing a block
                     'one_way_nodes': int((np.isfinite(ds) & ~np.isfinite(back) & ~plat).sum())}
    R['safe_descent'] = out
    R['unguarded_edges_on_descent_routes'] = unguarded_edges(vm, g, L, np.isfinite(D['team1']) | np.isfinite(D['team2']))


def unguarded_edges(vm, g, L, reach):
    """Edges of the stair routes (ghats, parvis, gallery, gallery flights) where a player walking (auto-step over
    a 1-high lip included) would fall 10+ voxels: a 4-neighbour column with no 2-high barrier above the standing
    level and its first floor 10+ below. 0 = every damaging edge is guarded."""
    G = V.V2['gallery']
    route = np.zeros((512, 512), bool)
    for gh in V.V2['ghats']:                                       # walking lanes only (not the cheek-wall tops)
        (gx0, gx1), ey = gh['x'], gh['edge_y']
        route[gx0:gx1 + 1, ey - 21:ey] = True
        route[gx0:gx1 + 1, 512 - ey + 1:512 - ey + 22] = True
    pv = V.V2['parvis']
    route[pv['x'][0]:pv['x'][1] + 1, pv['y'][0]:pv['y'][1] + 1] = True
    route[G['x'][0]:G['x'][1], G['y'][0]:G['y'][1] + 1] = True     # gallery inside its parapet
    for (ly0, ly1) in G['stair_lanes_y']:
        route[G['stair_x'][0]:G['stair_x'][1] + 1, ly0:ly1 + 1] = True
    route[257:] |= route[1:256][::-1]                                # x mirror (x' = 512 - x)
    solid = vm.solid.copy(); solid[:, :, 63] = True
    bad = []
    for (x, y, z) in g.node_xyz[reach]:
        if not route[x, y] or z >= 59:
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            xx, yy = x + dx, y + dy
            if solid[xx, yy, z - 1] and solid[xx, yy, z - 2]:
                continue                                          # 2-high wall / riser: no walking over
            zs = z - 1 if solid[xx, yy, z - 1] else z           # 1-high lip: stepped onto, then falls from there
            col = solid[xx, yy, zs:]
            f = zs + int(np.argmax(col))
            if f - zs >= 10:
                bad.append([int(x), int(y), int(z), int(xx), int(yy), int(f - zs)])
    return {'route_nodes': int(sum(1 for (x, y, z) in g.node_xyz[reach] if route[x, y] and z < 59)), 'count': len(bad),
            'examples': bad[:12]}


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'maps/drowned_cathedral_v2'
    C.main(out, name=V.NAME, layout=V.Layout2(), targets=TARGETS, extend=safe_descent)
