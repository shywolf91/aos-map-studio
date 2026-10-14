"""Validation for Drowned Cathedral (Babel, stock piqueserver 1.4.2): structure, tower-zone + spawn clearance,
platform clearance and free scaffolding, walkable build gaps per team, routes and parity (preliminary nav model:
3-voxel standing clearance, 1-voxel auto-step, 2-voxel jump edges), spawn exposure from the platform.

Run: python scenes/drowned_cathedral_check.py out/drowned_cathedral
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aosmap.vxl import load                                                    # noqa: E402
from aosmap.validate import floating_components, check_babel                   # noqa: E402
from aosmap import nav                                                         # noqa: E402
from scenes.drowned_cathedral import SPEC, BANK, Layout                         # noqa: E402


def snap(g, x, y, z, r=4, dz=4):
    best, bd = -1, 1e9
    for xx in range(x - r, x + r + 1):
        for yy in range(y - r, y + r + 1):
            for zz in range(max(z - dz, 0), min(z + dz, 63) + 1):
                n = int(g.index[xx, yy, zz])
                d = (xx - x) ** 2 + (yy - y) ** 2 + (zz - z) ** 2
                if n >= 0 and d < bd:
                    best, bd = n, d
    return best


def mirror_node(g, n):
    x, y, z = (int(v) for v in g.node_xyz[n])
    return int(g.index[512 - x, y, z])


def main(out, name='drowned_cathedral', layout=None, targets=None, extend=None):
    vm, rep = load(os.path.join(out, name + '.vxl'))
    R = {'reader_ok': rep.ok, 'colours_missing_on_surface': int((vm.solid & ~vm.colored).sum()) if hasattr(vm, 'colored') else None}
    L = layout or Layout()
    top = np.argmax(vm.solid, axis=2)
    fl = floating_components(vm.solid)
    R['floating_components'] = len(fl)

    # mirror symmetry of the occupancy (x' = 512 - x)
    a = vm.solid[1:256]; b = vm.solid[257:512][::-1]
    R['mirror_occupancy_match'] = round(float((a == b).mean()), 6)

    zone = L.zone_both
    R['tower_zone_columns'] = int(zone.sum())
    R['tower_zone_columns_not_flat_z40'] = int((zone & (top != BANK)).sum())
    sq = SPEC['spawn_square']
    sqm = (L.X >= sq['x'][0]) & (L.X <= sq['x'][1]) & (L.Y >= sq['y'][0]) & (L.Y <= sq['y'][1])
    sqm |= (512 - L.X >= sq['x'][0]) & (512 - L.X <= sq['x'][1]) & (L.Y >= sq['y'][0]) & (L.Y <= sq['y'][1])
    R['spawn_square_columns_not_flat_z40'] = int((sqm & (top != BANK)).sum())

    sc = SPEC['script_constants']
    R['babel_static'] = [f'{f.level}: {f.detail}' for f in check_babel(vm).findings]
    # nearest authored voxel above the general surface near the platform (free scaffolding), both halves
    px0, px1 = sc['platform_x']; py0, py1 = sc['platform_y']
    xs, ys, zs = np.nonzero(vm.solid[:, :, :62])
    ddx = np.maximum(0, np.maximum(px0 - xs, xs - px1)); ddy = np.maximum(0, np.maximum(py0 - ys, ys - py1))
    dd = np.sqrt(ddx ** 2 + ddy ** 2 + (zs - 1.0) ** 2)
    k = int(np.argmin(dd))
    R['nearest_voxel_to_platform'] = {'distance': round(float(dd[k]), 1), 'at': [int(xs[k]), int(ys[k]), int(zs[k])]}

    s = vm.solid.copy()
    s[px0:px1 + 1, py0:py1 + 1, 1] = True
    g = nav.build(s, water_damage=False)
    xyz = g.node_xyz
    plat = (xyz[:, 2] == 1) & (xyz[:, 0] >= px0) & (xyz[:, 0] <= px1) & (xyz[:, 1] >= py0) & (xyz[:, 1] <= py1)
    B, D = {}, {}
    for team, base in (('team1', sc['bases'][0]), ('team2', sc['bases'][1])):
        d = nav.distances(g, nav.zone_nodes(g, *base, sc['spawn_half']))
        D[team] = d
        reach = np.isfinite(d) & ~plat
        p = xyz[reach].astype(float)
        ddx = np.maximum(0, np.maximum(px0 - p[:, 0], p[:, 0] - px1))
        ddy = np.maximum(0, np.maximum(py0 - p[:, 1], p[:, 1] - py1))
        gap = np.sqrt(ddx ** 2 + ddy ** 2 + np.maximum(0, p[:, 2] - 1) ** 2)
        kk = int(np.argmin(gap))
        pi = p.astype(int)
        own = L.zone_both[pi[:, 0], pi[:, 1]] & ((p[:, 0] < 256) if team == 'team1' else (p[:, 0] > 256)) & (p[:, 2] == BANK)
        ko = int(np.argmin(np.where(own, gap, 1e9)))
        B[team] = {'platform_reachable_without_building': bool(np.isfinite(d[plat]).any()),
                   'walkable_build_gap_any': round(float(gap[kk]), 1), 'from': [int(v) for v in p[kk]],
                   'build_gap_from_own_esplanade': round(float(gap[ko]), 1), 'esplanade_from': [int(v) for v in p[ko]]}
    R['babel'] = B
    targets = targets or {'esplanade_edge': (204, 256, BANK), 'stair_landing': (183, 214, 59), 'transept_door': (217, 256, 59),
               'portal': (253, 140, 59), 'crossing_floor': (250, 254, 59), 'belfry_floor': (252, 250, 32),
               'enemy_esplanade': (308, 256, BANK), 'enemy_spawn': (394, 256, BANK)}
    T = {'team1': {}, 'team2': {}}
    for nm, (x, y, z) in targets.items():
        n1 = snap(g, x, y, z)
        n2 = mirror_node(g, n1) if n1 >= 0 else -1
        if nm in ('enemy_esplanade', 'enemy_spawn') and n1 >= 0:
            n2 = snap(g, 512 - x, y, z)
            n1 = snap(g, x, y, z)
        T['team1'][nm] = round(float(D['team1'][n1]), 1) if n1 >= 0 and np.isfinite(D['team1'][n1]) else None
        T['team2'][nm] = round(float(D['team2'][n2]), 1) if n2 >= 0 and np.isfinite(D['team2'][n2]) else None
        T.setdefault('nodes', {})[nm] = [[int(v) for v in g.node_xyz[n1]] if n1 >= 0 else None,
                                         [int(v) for v in g.node_xyz[n2]] if n2 >= 0 else None]
    R['routes_from_spawn'] = T
    diffs = [abs(T['team1'][k] - T['team2'][k]) for k in targets if T['team1'][k] is not None and T['team2'][k] is not None]
    R['route_parity_max_diff'] = round(max(diffs), 1) if diffs else None
    R['routes_unreachable'] = [k for k in targets if T['team1'][k] is None or T['team2'][k] is None]
    from aosmap.sightline import babel_spawn_report
    R['spawn_exposure'] = {k: {kk: (float(vv) if hasattr(vv, 'item') else vv) for kk, vv in v.items()}
                           for k, v in babel_spawn_report(vm.solid).items()}
    if extend:
        extend(R, vm=vm, g=g, D=D, L=L, plat=plat)
    json.dump(R, open(os.path.join(out, 'validation.json'), 'w'), indent=1, default=str)
    print(json.dumps(R, indent=1, default=str))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'out/drowned_cathedral')
