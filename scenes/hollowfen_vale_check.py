"""Validation for Hollowfen Vale (Babel + CTF): structure, tower-zone clearance, free scaffolding near the platform,
both modes' rules, routes and team parity (preliminary nav).

Run: python scenes/hollowfen_vale_check.py out/hollowfen_vale
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aosmap.vxl import load                                                    # noqa: E402
from aosmap.validate import floating_components, check_babel, settle_entity_z, spawn_check  # noqa: E402
from aosmap import nav                                                         # noqa: E402
from scenes.hollowfen_vale import SPEC, G, Layout, terrain                     # noqa: E402
from scenes.hollowfen_check import snap, mirror_node                           # noqa: E402


def main(out, name='hollowfen_vale'):
    vm, rep = load(os.path.join(out, name + '.vxl'))
    R = {'reader_ok': rep.ok}
    L = Layout()
    H = terrain(L)
    Hfull = H.copy(); Hfull[257:] = H[1:256][::-1]; Hfull[256] = H[255]
    top = np.argmax(vm.solid, axis=2)
    witches = SPEC['witches']

    fl = floating_components(vm.solid)
    def is_witch(c):
        (x0, x1), (y0, y1), (z0, z1) = c['bbox']
        return any(x0 - 2 <= wx <= x1 + 2 and y0 - 2 <= wy <= y1 + 2 for (wx, wy, wz) in witches)
    R['floating_components'] = len(fl)
    R['floating_witch_components'] = sum(1 for c in fl if is_witch(c))
    R['floating_unexpected'] = [c for c in fl if not is_witch(c)]

    # ---- tower zones: nothing but terrain (no voxel above the terrain surface)
    zone = L.zone_both
    above = zone & (top < Hfull)
    R['tower_zone_columns'] = int(zone.sum())
    R['tower_zone_columns_with_structures'] = int(above.sum())
    R['tower_zone_examples'] = [[int(x), int(y), int(top[x, y])] for x, y in np.argwhere(above)[:5]]

    # ---- free scaffolding: nearest authored (non-terrain) voxel to the platform's standing surface
    sc = SPEC['script_constants']
    struct = (top < Hfull) & ~zone
    for (wx, wy, wz) in witches:
        struct[max(wx - 12, 0):wx + 13, max(wy - 12, 0):wy + 13] &= ~(top[max(wx - 12, 0):wx + 13, max(wy - 12, 0):wy + 13] < 30)
    xs, ys = np.nonzero(struct)
    zs = top[xs, ys]
    ddx = np.maximum(0, np.maximum(sc['platform_x'][0] - xs, xs - sc['platform_x'][1]))
    ddy = np.maximum(0, np.maximum(sc['platform_y'][0] - ys, ys - sc['platform_y'][1]))
    dd = np.sqrt(ddx ** 2 + ddy ** 2 + (zs - 1.0) ** 2)
    k = int(np.argmin(dd))
    R['nearest_structure_to_platform'] = {'distance': round(float(dd[k]), 1), 'at': [int(xs[k]), int(ys[k]), int(zs[k])]}
    zx, zy = SPEC['tower_zone']['x'], SPEC['tower_zone']['y']
    gz = Hfull[zx[1], (zy[0] + zy[1]) // 2]
    R['ground_gap_from_zone_edge'] = round(float(np.hypot(max(0, sc['platform_x'][0] - zx[1]), gz - 1)), 1)

    R['babel_static'] = [f'{f.level}: {f.detail}' for f in check_babel(vm).findings]
    s = vm.solid.copy()
    s[sc['platform_x'][0]:sc['platform_x'][1] + 1, sc['platform_y'][0]:sc['platform_y'][1] + 1, 1] = True
    g = nav.build(s, water_damage=False)
    xyz = g.node_xyz
    plat = (xyz[:, 2] == 1) & (xyz[:, 0] >= 206) & (xyz[:, 0] <= 305) & (xyz[:, 1] >= 240) & (xyz[:, 1] <= 271)
    B = {}
    D = {}
    for team, base in (('team1', sc['bases'][0]), ('team2', sc['bases'][1])):
        d = nav.distances(g, nav.zone_nodes(g, *base, sc['spawn_half']))
        D[team] = d
        reach = np.isfinite(d) & ~plat
        p = xyz[reach].astype(float)
        ddx = np.maximum(0, np.maximum(206 - p[:, 0], p[:, 0] - 305))
        ddy = np.maximum(0, np.maximum(240 - p[:, 1], p[:, 1] - 271))
        gap = np.sqrt(ddx ** 2 + ddy ** 2 + np.maximum(0, p[:, 2] - 1) ** 2)
        kk = int(np.argmin(gap))
        B[team] = {'platform_reachable_without_building': bool(np.isfinite(d[plat]).any()),
                   'walkable_build_gap': round(float(gap[kk]), 1), 'gap_from': [int(v) for v in p[kk]]}
    R['babel'] = B

    targets = {'green_centre': (240, 256, G), 'church_door': (256, 146, G), 'belfry': (256, 186, 32),
               'cemetery_gate': (220, 330, G), 'mausoleum': (240, 350, G - 1),
               'own_intel': (SPEC['ctf']['blue_flag'][0], 256, int(Hfull[SPEC['ctf']['blue_flag']])),
               'enemy_intel': (512 - SPEC['ctf']['blue_flag'][0], 256, int(Hfull[SPEC['ctf']['blue_flag']])),
               'enemy_spawn': (394, 256, int(Hfull[394, 256]))}
    T = {'team1': {}, 'team2': {}}
    for nm, (x, y, z) in targets.items():
        n1 = snap(g, x, y, z)
        n2 = mirror_node(g, n1) if n1 >= 0 else -1
        if nm in ('church_door', 'belfry') and n1 >= 0:
            n2 = n1                                   # central, shared: same node for both teams
        T['team1'][nm] = round(float(D['team1'][n1]), 1) if n1 >= 0 and np.isfinite(D['team1'][n1]) else None
        T['team2'][nm] = round(float(D['team2'][n2]), 1) if n2 >= 0 and np.isfinite(D['team2'][n2]) else None
    R['routes_from_spawn'] = T
    R['route_parity_max_diff'] = max(abs((T['team1'][k] or 0) - (T['team2'][k] or 0)) for k in targets)

    fx, fy = SPEC['ctf']['blue_flag']; bx, by = SPEC['ctf']['blue_base']
    C = {'blue_flag_z': settle_entity_z(vm, fx, fy, int(Hfull[fx, fy])), 'blue_flag_ground': int(Hfull[fx, fy]),
         'green_flag_z': settle_entity_z(vm, 512 - fx, fy, int(Hfull[fx, fy])),
         'blue_base_z': settle_entity_z(vm, bx, by, int(Hfull[bx, by])), 'base_ground': int(Hfull[bx, by]),
         'green_base_z': settle_entity_z(vm, 512 - bx, by, int(Hfull[bx, by]))}
    sq = SPEC['spawn_square']
    pts = [(x, y) for x in range(sq['x'][0] + 4, sq['x'][1] - 3, 8) for y in range(sq['y'][0] + 4, sq['y'][1] - 3, 8)]
    bad = []
    for (x, y) in pts + [(512 - x, y) for (x, y) in pts]:
        r = spawn_check(vm, x, y, int(Hfull[x, y]))
        if not (r['floor_solid'] and r['headroom_ok'] and not r['in_water']):
            bad.append((x, y))
    C['ctf_spawn_points'] = 2 * len(pts); C['ctf_spawn_points_bad'] = bad
    ne = snap(g, 512 - fx, fy, int(Hfull[fx, fy])); ot = snap(g, bx, by, int(Hfull[bx, by]))
    dc = nav.distances(g, [ne])
    C['carry_enemy_intel_to_own_tent'] = round(float(dc[ot]), 1) if np.isfinite(dc[ot]) else None
    R['ctf'] = C
    # spawn square must be clear: no structure above the terrain inside either square
    sqm = (L.X >= sq['x'][0]) & (L.X <= sq['x'][1]) & (L.Y >= sq['y'][0]) & (L.Y <= sq['y'][1])
    sqm = sqm | ((512 - L.X >= sq['x'][0]) & (512 - L.X <= sq['x'][1]) & (L.Y >= sq['y'][0]) & (L.Y <= sq['y'][1]))
    R['spawn_square_columns_with_structures'] = int((sqm & (top < Hfull)).sum())
    json.dump(R, open(os.path.join(out, 'validation.json'), 'w'), indent=1, default=str)
    print(json.dumps(R, indent=1, default=str))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'out/hollowfen_vale')
