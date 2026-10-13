"""Validation for Hollowfen (Babel + CTF): structure, both modes' rules, routes and team parity (preliminary nav).

Run: python scenes/hollowfen_check.py out/hollowfen_graybox
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aosmap.vxl import load                                                    # noqa: E402
from aosmap.validate import floating_components, check_babel, settle_entity_z, spawn_check  # noqa: E402
from aosmap import nav                                                         # noqa: E402
from scenes.hollowfen import SPEC, G                                            # noqa: E402


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


def main(out, name='hollowfen'):
    vm, rep = load(os.path.join(out, name + '.vxl'))
    R = {'reader_ok': rep.ok}
    fl = floating_components(vm.solid)
    witches = SPEC['witches']
    def is_witch(c):
        (x0, x1), (y0, y1), (z0, z1) = c['bbox']
        return any(x0 - 2 <= wx <= x1 + 2 and y0 - 6 <= wy <= y1 + 6 and z1 <= 20 for (wx, wy, wz) in witches)
    R['floating_components'] = len(fl)
    R['floating_witch_components'] = sum(1 for c in fl if is_witch(c))
    R['floating_unexpected'] = [c for c in fl if not is_witch(c)]
    R['babel_static'] = [f'{f.level}: {f.detail}' for f in check_babel(vm).findings]

    sc = SPEC['script_constants']
    s = vm.solid.copy()
    s[sc['platform_x'][0]:sc['platform_x'][1] + 1, sc['platform_y'][0]:sc['platform_y'][1] + 1, 1] = True
    g = nav.build(s, water_damage=False)
    xyz = g.node_xyz
    plat = (xyz[:, 2] == 1) & (xyz[:, 0] >= 206) & (xyz[:, 0] <= 305) & (xyz[:, 1] >= 240) & (xyz[:, 1] <= 271)

    # ---- Babel: platform unreachable on foot; build gap from anything walkable
    B = {}
    for team, base in (('team1', sc['bases'][0]), ('team2', sc['bases'][1])):
        d = nav.distances(g, nav.zone_nodes(g, *base, sc['spawn_half']))
        reach = np.isfinite(d) & ~plat
        p = xyz[reach].astype(float)
        ddx = np.maximum(0, np.maximum(206 - p[:, 0], p[:, 0] - 305))
        ddy = np.maximum(0, np.maximum(240 - p[:, 1], p[:, 1] - 271))
        ddz = np.maximum(0, p[:, 2] - 1)
        gap = np.sqrt(ddx ** 2 + ddy ** 2 + ddz ** 2)
        k = int(np.argmin(gap))
        B[team] = {'platform_reachable_without_building': bool(np.isfinite(d[plat]).any()),
                   'build_gap': round(float(gap[k]), 1), 'gap_from': [int(v) for v in p[k]]}
    R['babel'] = B

    # ---- routes from each team's spawn square (team2 = exact mirror nodes)
    targets = {   # west-side coordinates; team2 uses mirror
        'belfry_deck': (186, 254, SPEC['church']['belfry_floor_z']),
        'cemetery_centre_gate': (210, 256, G - 1),
        'mausoleum_door': (244, 256, G - 1),
        'north_boardwalk_mid': (250, 131, G),
        'south_boardwalk_mid': (250, 380, G),
        'own_intel_farm': (56, 256, G),
        'enemy_intel_farm': (512 - 56, 256, G),
        'enemy_square': (512 - 118, 256, G),
    }
    T = {'team1': {}, 'team2': {}}
    d1 = nav.distances(g, nav.zone_nodes(g, *sc['bases'][0], sc['spawn_half']))
    d2 = nav.distances(g, nav.zone_nodes(g, *sc['bases'][1], sc['spawn_half']))
    for name_t, (x, y, z) in targets.items():
        n1 = snap(g, x, y, z)
        n2 = mirror_node(g, n1) if n1 >= 0 else -1
        T['team1'][name_t] = round(float(d1[n1]), 1) if n1 >= 0 and np.isfinite(d1[n1]) else None
        T['team2'][name_t] = round(float(d2[n2]), 1) if n2 >= 0 and np.isfinite(d2[n2]) else None
    R['routes_from_spawn'] = T
    R['route_parity_max_diff'] = max(abs((T['team1'][k] or 0) - (T['team2'][k] or 0)) for k in targets)

    # ---- CTF: entities settle where intended; spawns standable; carry route enemy intel -> own tent
    fx, fy = SPEC['ctf']['blue_flag']; bx, by = SPEC['ctf']['blue_base']
    C = {'blue_flag_z': settle_entity_z(vm, fx, fy, G), 'green_flag_z': settle_entity_z(vm, 512 - fx, fy, G),
         'blue_base_z': settle_entity_z(vm, bx, by, G), 'green_base_z': settle_entity_z(vm, 512 - bx, by, G),
         'expected_z': G}
    sq = SPEC['square']
    pts = [(x, y) for x in range(sq['x'][0] + 4, sq['x'][1] - 3, 8) for y in range(sq['y'][0] + 4, sq['y'][1] - 3, 8)]
    def bad_spawn(x, y):
        r = spawn_check(vm, x, y, G)
        return not (r['floor_solid'] and r['headroom_ok'] and not r['in_water'])
    bad = [p for p in pts if bad_spawn(*p)] + [(512 - p[0], p[1]) for p in pts if bad_spawn(512 - p[0], p[1])]
    C['ctf_spawn_points'] = 2 * len(pts)
    C['ctf_spawn_points_bad'] = bad
    ne = snap(g, 512 - fx, fy, G); ot = snap(g, bx, by, G)
    dcarry = nav.distances(g, [ne])
    C['carry_enemy_intel_to_own_tent_team1'] = round(float(dcarry[ot]), 1) if np.isfinite(dcarry[ot]) else None
    ne2 = mirror_node(g, ne); ot2 = mirror_node(g, ot)
    dcarry2 = nav.distances(g, [ne2])
    C['carry_enemy_intel_to_own_tent_team2'] = round(float(dcarry2[ot2]), 1) if np.isfinite(dcarry2[ot2]) else None
    R['ctf'] = C

    # ---- boardwalks: every deck cell over the bog has 3 air voxels above (nothing decorative on the walkway)
    from scenes.hollowfen import Layout
    L = Layout()
    bwc = []
    for (wy0, wy1) in SPEC['boardwalk_y']:
        for x in range(200, 256):
            for y in range(wy0, wy1 + 1):
                if L.bog[x, y]:
                    for xx in (x, 512 - x):
                        bwc.append(bool(vm.solid[xx, y, G]) and not vm.solid[xx, y, G - 3:G].any())
    R['boardwalk_cells'] = len(bwc)
    R['boardwalk_clear_pct'] = round(100.0 * sum(bwc) / max(len(bwc), 1), 1)

    # ---- perches: highest standable point reachable on foot outside the church tower
    P = {}
    for team, d in (('team1', d1), ('team2', d2)):
        x = np.where(xyz[:, 0] > 256, 512 - xyz[:, 0], xyz[:, 0])
        tower = (x >= 182) & (x <= 194) & (xyz[:, 1] >= 250) & (xyz[:, 1] <= 262)
        ok = np.isfinite(d) & ~tower & ~plat
        zmin = int(xyz[ok, 2].min())
        P[team] = {'highest_z_outside_tower': zmin, 'where': [int(v) for v in xyz[ok][np.argmin(xyz[ok, 2])]]}
    R['perches'] = P
    # spawn exposure to platform snipers (see docs/babel_rotation_guide_notes.md); targets: <= ~10 viewers/spot
    from aosmap.sightline import babel_spawn_report
    R['spawn_exposure'] = {k: {kk: (float(vv) if hasattr(vv, 'item') else vv) for kk, vv in v.items()}
                           for k, v in babel_spawn_report(vm.solid).items()}
    json.dump(R, open(os.path.join(out, 'validation.json'), 'w'), indent=1, default=str)
    print(json.dumps(R, indent=1, default=str))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'out/hollowfen_graybox')
