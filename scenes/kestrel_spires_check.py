"""Validation for Kestrel Spires: structure, babel rules, routes and team parity (preliminary nav).

Run: python scenes/kestrel_spires_check.py out/kestrel_spires
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aosmap.vxl import load                                # noqa: E402
from aosmap.validate import floating_components, check_babel, push_team_colour_collisions  # noqa: E402
from aosmap import nav                                     # noqa: E402
from scenes.kestrel_spires import SPEC                     # noqa: E402


def mirror_pt(p):
    return (512 - p[0],) + tuple(p[1:])


def snap(g, x, y, z, r=4, dz=3):
    """Nearest node to (x, y, z) within r columns and +-dz levels (art props may sit on the exact voxel)."""
    best, bd = -1, 1e9
    for xx in range(x - r, x + r + 1):
        for yy in range(y - r, y + r + 1):
            for zz in range(max(z - dz, 0), min(z + dz, 63) + 1):
                n = int(g.index[xx, yy, zz])
                d = (xx - x) ** 2 + (yy - y) ** 2 + (zz - z) ** 2
                if n >= 0 and d < bd:
                    best, bd = n, d
    return best


def main(out):
    vm, rep = load(os.path.join(out, 'kestrel_spires.vxl'))
    R = {'reader_ok': rep.ok}
    fl = floating_components(vm.solid)
    R['floating_components'] = len(fl)
    R['babel_static'] = [f'{f.level}: {f.detail}' for f in check_babel(vm).findings]
    R['team_colour_clashes'] = [str(c) for c in push_team_colour_collisions(vm, ((0, 0, 255), (255, 0, 0)))]

    # nav graph with the script platform simulated; water allowed (water_damage 0 on this map)
    sc = SPEC['script_constants']
    s = vm.solid.copy()
    s[sc['platform_x'][0]:sc['platform_x'][1] + 1, sc['platform_y'][0]:sc['platform_y'][1] + 1, 1] = True
    g = nav.build(s, water_damage=False)
    xyz = g.node_xyz
    plat = (xyz[:, 2] == 1) & (xyz[:, 0] >= 206) & (xyz[:, 0] <= 305) & (xyz[:, 1] >= 240) & (xyz[:, 1] <= 271)

    def spawn_nodes(bx, by):
        return nav.zone_nodes(g, bx, by, sc['spawn_half'])

    targets = {   # team1 (west) coordinates; team2 uses the mirror
        'spire_top': (178, 256, 13),
        'finger_north_top': (168, 226, 17),
        'finger_south_top': (168, 286, 17),
        'slot_stair_bottom_floor': (88, 200, 56),
        'own_canyon_floor_mid': (150, 200, 56),
        'enemy_canyon_floor_near_spire': (512 - 150, 200, 56),
        'river_bank_top': (214, 300, 56),
    }
    T = {}
    for team, base in (('team1', sc['bases'][0]), ('team2', sc['bases'][1])):
        d = nav.distances(g, spawn_nodes(*base))
        T[team] = {'platform_reachable_without_building': bool(np.isfinite(d[plat]).any())}
        for name, p in targets.items():
            n = snap(g, *p)                       # snap on the west side, then use the exact mirror node
            if team == 'team2' and n >= 0:
                x1, y1, z1 = (int(v) for v in xyz[n])
                n = int(g.index[512 - x1, y1, z1])
            T[team][name] = round(float(d[n]), 1) if n >= 0 and np.isfinite(d[n]) else None
    R['routes_from_spawn'] = T
    R['route_parity_max_diff'] = max(abs((T['team1'][k] or 0) - (T['team2'][k] or 0)) for k in targets)

    # climb back: canyon floor -> own spawn plaza (directed graph: must exist for both teams)
    back = {}
    n1 = snap(g, 150, 200, 56)
    x1, y1, z1 = (int(v) for v in xyz[n1])
    for team, base, n in (('team1', sc['bases'][0], n1), ('team2', sc['bases'][1], int(g.index[512 - x1, y1, z1]))):
        d = nav.distances(g, [n])
        ids = spawn_nodes(*base)
        back[team] = round(float(np.min(d[ids])), 1) if np.isfinite(d[ids]).any() else None
    R['canyon_to_own_spawn'] = back

    # river exit: from water under the platform to the bank top
    d = nav.distances(g, [g.node(256, 300)])
    bank = snap(g, 214, 300, 56)
    R['river_exit_cost'] = round(float(d[bank]), 1) if np.isfinite(d[bank]) else None

    # canyon perches: highest standable point reachable on foot in the canyon (away from the mesa stair)
    P = {}
    for team, base, flip in (('team1', sc['bases'][0], False), ('team2', sc['bases'][1], True)):
        d = nav.distances(g, spawn_nodes(*base))
        ok = np.isfinite(d) & (xyz[:, 2] >= 36)                 # below mesa-top heights
        x = np.where(xyz[:, 0] > 256, 512 - xyz[:, 0], xyz[:, 0])        # both teams' slot stairs
        stair = (x >= 84) & (x <= 134) & (xyz[:, 1] >= 186) & (xyz[:, 1] <= 219)
        ok &= ~stair
        zmin = int(xyz[ok, 2].min()) if ok.any() else None
        P[team] = {'highest_z': zmin, 'height_above_floor': None if zmin is None else SPEC['canyon_floor_z'] - zmin,
                   'nodes_above_3': int((ok & (xyz[:, 2] < SPEC['canyon_floor_z'] - 3)).sum())}
    R['canyon_perches'] = P

    # build gap per bridgehead (straight-line from its walkable top to the platform's standing surface)
    def gap(top_cells):
        best = None
        for (x, y, z) in top_cells:
            dx = max(0, 206 - x, x - 305); dy = max(0, 240 - y, y - 271); dz = max(0, z - 1)
            v = (round(float(np.sqrt(dx * dx + dy * dy + dz * dz)), 1), dx, dy, dz)
            best = v if best is None or v < best else best
        return {'gap': best[0], 'out_x': best[1], 'out_y': best[2], 'up': best[3]}
    G = {}
    for name, (c, r, tz) in {'spire': (SPEC['spire']['center'], SPEC['spire']['r'], SPEC['spire']['top_z']),
                            'finger_north': (SPEC['fingers'][0]['center'], 4.5, 17),
                            'finger_south': (SPEC['fingers'][1]['center'], 4.5, 17)}.items():
        for team in ('team1', 'team2'):
            cc = c if team == 'team1' else (512 - c[0], c[1])
            cells = [(x, y, tz) for x in range(cc[0] - 7, cc[0] + 8) for y in range(cc[1] - 7, cc[1] + 8)
                     if (x - cc[0]) ** 2 + (y - cc[1]) ** 2 < r * r and g.node(x, y, tz) >= 0]
            G[f'{name}_{team}'] = gap(cells)
    R['build_gaps'] = G
    # spawn exposure to platform snipers (see docs/babel_rotation_guide_notes.md); targets: <= ~10 viewers/spot
    from aosmap.sightline import babel_spawn_report
    R['spawn_exposure'] = {k: {kk: (float(vv) if hasattr(vv, 'item') else vv) for kk, vv in v.items()}
                           for k, v in babel_spawn_report(vm.solid).items()}
    json.dump(R, open(os.path.join(out, 'validation.json'), 'w'), indent=1, default=str)
    print(json.dumps(R, indent=1, default=str))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'out/kestrel_spires')
