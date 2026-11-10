"""Build, colour, export and check Death Swamp (Push).

python ds_main.py OUTDIR [--graybox]
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..')))

import ds_build as B                      # noqa: E402
from ds_color import colorize             # noqa: E402
from ds_layout import SPEC                # noqa: E402
from aosmap.vxl import VoxelMap, write_vxl, read_vxl, surface_mask   # noqa: E402
from aosmap.validate import (Report, floating_components, check_push, push_extensions,  # noqa: E402
                             push_team_colour_collisions)
from aosmap import nav                    # noqa: E402
from aosmap.render import top_down, isometric   # noqa: E402

NAME = 'Death Swamp'
FILE = 'death_swamp'
VERSION = '1.0'
TEAMS = ((0, 0, 255), (255, 0, 0))        # owner's server: team1 Blue, team2 Red
FOG = (178, 172, 192)                     # pale lilac-grey: absent from the palette, neutral blue/red


def mirror_pt(p):
    return (511 - p[0],) + tuple(p[1:])


def extensions(w):
    sx, sy = SPEC['spawn']; cx, cy = SPEC['cp']
    bz, cz = w.markers['spawn_z'], w.markers['cp_z']
    bb = SPEC['build_area_blue']
    rb = (511 - bb[2] + 1, bb[1], 511 - bb[0] + 1, bb[3])
    return push_extensions(blue_spawn=(sx, sy, bz), blue_cp=(cx, cy, cz),
                           green_spawn=mirror_pt((sx, sy, bz)), green_cp=mirror_pt((cx, cy, cz)),
                           spawn_range=SPEC['spawn_range'], water_damage=100,
                           blue_build_area=bb, green_build_area=rb)


def map_txt(ext):
    lines = [
        f"name = '{NAME}'",
        f"version = '{VERSION}'",
        "author = 'shywolf91'",
        "description = 'Push: carry the intel north through the drowned swamp. The water kills - bridge every gap.'",
        f"fog = {FOG}",
        "extensions = {",
    ]
    for k, v in ext.items():
        lines.append(f"    {k!r}: {v!r},")
    lines.append("}")
    lines.append("# Push spawns/CPs are required by piqueserver game_modes/push.py (it raises without them);")
    lines.append("# the spawn/entity hooks are supplied by push.py itself, so none are defined here.")
    return '\n'.join(lines) + '\n'


def checks(vm, w, ext):
    rep = Report()
    out = {}
    fl = floating_components(vm.solid)
    out['floating_components'] = len(fl)
    if fl:
        rep.add('error', 'floating', f'{len(fl)} floating components, e.g. {fl[:3]}')
    check_push(vm, ext, rep, team_colors=TEAMS)
    out['team_colour_hits'] = len(push_team_colour_collisions(vm, TEAMS))
    # mirror parity
    s = vm.solid
    out['mirror_mismatch_voxels'] = int((s[:256] != s[:255:-1]).sum()) if False else int((s[:256] != s[256:][::-1]).sum())
    # routes without building: spawn -> own CP must be impossible; each island internally connected
    g = nav.build(vm.solid, water_damage=True)
    res = {}
    for team, sp, cp in (('blue', ext['push_blue_spawn'], ext['push_blue_cp']),
                         ('red', ext['push_green_spawn'], ext['push_green_cp'])):
        src = g.node(sp[0], sp[1])
        dist = nav.distances(g, [src])
        cpn = g.node(cp[0], cp[1])
        reach = nav.reach_map(g, dist)
        res[team] = {'spawn_node': src, 'cp_reachable_without_building': bool(np.isfinite(dist[cpn])) if cpn >= 0 else None,
                     'walkable_columns_from_spawn': int(np.isfinite(reach).sum())}
        if cpn >= 0 and np.isfinite(dist[cpn]):
            rep.add('error', 'push_free_route', f'{team}: CP reachable from spawn without building')
    # per-island walk reachability from each landing (blue side; red is the mirror)
    isl = {}
    land = w.markers['landings']
    for name, pts in land.items():
        ids = [g.node(p[0], p[1]) for p in pts]
        if any(i < 0 for i in ids):
            isl[name] = f'landing without node: {pts}'
            rep.add('error', 'landing_node', f'{name} landing not standable {pts}')
            continue
        d = nav.distances(g, [ids[0]])
        ok = all(np.isfinite(d[i]) for i in ids)
        isl[name] = {'landings': pts, 'connected': ok,
                     'walk_cost': [round(float(d[i]), 1) for i in ids]}
        if not ok:
            rep.add('error', 'island_route', f'{name}: landings not connected on foot {pts}')
    res['islands'] = isl
    # lane islands reachable from each other only by building: count distinct walk components on land
    out['routes'] = res
    out['gaps'] = {k: v for k, v in w.markers['gaps'].items()}
    # spawn exposure to the enemy lane: is the red spawn pad visible from the blue pad? (eye heights)
    out['findings'] = [f.__dict__ for f in rep.findings]
    return rep, out


def renders(vm, outdir):
    top_down(vm, scale=2).save(os.path.join(outdir, 'top_down.png'))
    for v in (0, 2):
        isometric(vm, view=v, s=2).save(os.path.join(outdir, f'iso_view{v}.png'))
    # close-ups
    isometric(vm, crop=(150, 10, 362, 170), view=0, s=4).save(os.path.join(outdir, 'iso_north_isle.png'))
    isometric(vm, crop=(110, 400, 260, 511), view=0, s=4).save(os.path.join(outdir, 'iso_blue_spawn.png'))
    isometric(vm, crop=(120, 160, 392, 330), view=2, s=3).save(os.path.join(outdir, 'iso_mid_lanes.png'))


def main(outdir, graybox=False):
    os.makedirs(outdir, exist_ok=True)
    w = B.build(graybox=graybox)
    M = w.M
    if graybox:
        from ds_color import B_surface
        col = np.zeros(M.shape, np.uint32)
        pal = {B.PEAT: (110, 120, 80), B.SOIL: (90, 80, 60), B.BANK: (120, 110, 80), B.PATH: (170, 150, 100),
               B.FLAG: (150, 150, 150), B.RUNE: (90, 160, 150), B.STONE: (130, 130, 130), B.BONE: (210, 200, 170),
               B.SOCKET: (60, 60, 60)}
        for k, v in pal.items():
            col[M == k] = (0x80 << 24) | (v[0] << 16) | (v[1] << 8) | v[2]
        col[:, :, 63] = (0x80 << 24) | (50 << 16) | (110 << 8) | 115
    else:
        col = colorize(M)
    solid = M > 0
    solid[:, :, 63] = True
    vm = VoxelMap(solid=solid, color=col, colored=surface_mask(solid))
    data = write_vxl(vm)
    path = os.path.join(outdir, f'{FILE}.vxl')
    open(path, 'wb').write(data)
    vm2, rr = read_vxl(data)
    same = bool((vm2.solid == vm.solid).all())
    ext = extensions(w)
    open(os.path.join(outdir, f'{FILE}.txt'), 'w').write(map_txt(ext))
    rep, out = checks(vm, w, ext)
    out['export'] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'reread_solid_identical': same}
    surf = surface_mask(vm.solid)
    out['distinct_colours'] = int(len(np.unique(vm.color[surf] & 0xFFFFFF)))
    out['extensions'] = {k: list(v) if isinstance(v, tuple) else v for k, v in ext.items()}
    json.dump(out, open(os.path.join(outdir, 'validation.json'), 'w'), indent=1, default=str)
    print(rep.text())
    print(json.dumps({k: out[k] for k in ('floating_components', 'team_colour_hits', 'mirror_mismatch_voxels',
                                          'export', 'distinct_colours')}, indent=1))
    print(json.dumps(out['routes'], indent=1, default=str))
    renders(vm, outdir)
    return vm, w, out


if __name__ == '__main__':
    main(sys.argv[1], graybox='--graybox' in sys.argv)
