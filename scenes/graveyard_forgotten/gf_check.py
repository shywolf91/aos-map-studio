"""Validation for Graveyard of the Forgotten (Babel, stock piqueserver 1.4.2 babel_script constants).

python gf_check.py OUTDIR [--pyspades] [--exposure]
Writes OUTDIR/validation.json. Route checks are a preliminary graph model (3 air to stand, 1-voxel step up,
drops <= 9 safe), not a collision simulation.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

import numpy as np
from scipy import ndimage as ndi
from scipy.sparse.csgraph import dijkstra as shortest_path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'wicker_kings_harvest'))
from wkh_check import Nav, exposure                      # noqa: E402

from gf_core import read_vxl, write_vxl, surface_mask      # noqa: E402
import gf_props as P                                       # noqa: E402
from gf_terrain import G, SPEC                             # noqa: E402

PLAT = SPEC['platform']
BASES = SPEC['bases']
HALF = SPEC['spawn_half']
FILE = 'graveyard_of_the_forgotten'


def floating(solid, mat):
    lab, n = ndi.label(solid, structure=ndi.generate_binary_structure(3, 1))
    grounded = set(np.unique(lab[:, :, 62:][solid[:, :, 62:]]).tolist())
    names = {v: k for k, v in P.M.items()}
    out = []
    for i in range(1, n + 1):
        if i in grounded:
            continue
        xs, ys, zs = np.nonzero(lab == i)
        vals, cnt = np.unique(mat[xs, ys, zs], return_counts=True)
        out.append({'mat': names.get(int(vals[np.argmax(cnt)])), 'voxels': int(len(xs)),
                    'x': [int(xs.min()), int(xs.max())], 'y': [int(ys.min()), int(ys.max())],
                    'z': [int(zs.min()), int(zs.max())]})
    return out


def main(out, use_pyspades=False, do_exposure=False):
    t0 = time.time()
    data = open(f'{out}/{FILE}.vxl', 'rb').read()
    solid, color, colored = read_vxl(data)
    mat = np.load(f'{out}/mat.npy')
    binfo = json.load(open(f'{out}/build.json'))
    R = {'sha256': binfo['sha256']}
    surf = surface_mask(solid)
    R['reader'] = {'bytes': len(data), 'reencode_identical': write_vxl(solid, np.where(colored, color, 0)) == data,
                   'surface_all_coloured': bool((colored >= surf).all()), 'z63_solid': bool(solid[:, :, 63].all()),
                   'water_columns': int((~solid[:, :, 62]).sum())}
    if use_pyspades:
        from pyspades.vxl import VXLData
        vm = VXLData(fp=io.BytesIO(data))
        g = bytes(vm.generate())
        rng = np.random.default_rng(1)
        pts = rng.integers(0, [512, 512, 64], size=(20000, 3))
        sm = cm = 0
        for x, y, z in pts:
            s = vm.get_solid(int(x), int(y), int(z))
            if bool(s) != bool(solid[x, y, z]):
                sm += 1
            if s and surf[x, y, z]:
                c = vm.get_color(int(x), int(y), int(z))
                cc = int(color[x, y, z])
                if tuple(c[:3]) != ((cc >> 16) & 255, (cc >> 8) & 255, cc & 255):
                    cm += 1
        R['pyspades'] = {'generate_identical': g == data, 'solid_mismatch_20k': sm, 'colour_mismatch_20k': cm,
                         'get_z_bases': [int(vm.get_z(*b)) for b in BASES]}
    fl = floating(solid, mat)
    R['floating_components'] = {'count': len(fl), 'voxels': sum(f['voxels'] for f in fl), 'list': fl[:20]}

    # mirror (x' = 512 - x), excluding the hands' cosmetic boxes and the corner tag (colour only)
    excl = np.zeros((512, 512), bool)
    for b in binfo['cosmetic_bboxes']:
        excl[b[0]:b[1] + 1, b[2]:b[3] + 1] = True
        excl[512 - b[1]:512 - b[0] + 1, b[2]:b[3] + 1] = True
    keep = ~excl[1:256, :, None]
    R['mirror_solid_mismatch'] = int(((solid[1:256] != solid[511:256:-1]) & keep).sum())
    R['mirror_material_mismatch'] = int(((mat[1:256] != mat[511:256:-1]) & keep).sum())
    R['mirror_excluded_boxes'] = binfo['cosmetic_bboxes']

    (x0, x1), (y0, y1) = PLAT['x'], PLAT['y']
    R['platform_volume_voxels_z0_2'] = int(solid[x0:x1 + 1, y0:y1 + 1, 0:3].sum())
    R['platform_margin_voxels_z0_2'] = int(solid[x0 - 1:x1 + 2, y0 - 1:y1 + 2, 0:3].sum()) - R['platform_volume_voxels_z0_2']
    # nearest authored (non-terrain-floor) voxel to the platform slab
    above = solid.copy(); above[:, :, G:] = False
    xs, ys, zs = np.nonzero(above)
    dx = np.maximum(np.maximum(x0 - xs, xs - x1), 0); dy = np.maximum(np.maximum(y0 - ys, ys - y1), 0)
    dz = np.maximum(zs - PLAT['z'], 0)
    d = np.sqrt(dx ** 2 + dy ** 2 + dz ** 2)
    i = int(np.argmin(d))
    R['nearest_authored_voxel_to_platform'] = {'dist': round(float(d[i]), 1), 'xyz': [int(xs[i]), int(ys[i]), int(zs[i])],
                                               'mat': {v: k for k, v in P.M.items()}.get(int(mat[xs[i], ys[i], zs[i]]))}
    under = solid[x0:x1 + 1, y0:y1 + 1, :G]
    R['highest_voxel_under_platform_z'] = int(np.argmax(under.any(axis=(0, 1))))
    top = np.argmax(solid, axis=2)
    ends = {'blue_end_x206_211': top[206:212, 240:272], 'red_end_x300_305': top[300:306, 240:272]}
    R['ground_under_platform_ends'] = {k: {'top_z_values': sorted(set(int(t) for t in v.ravel())),
                                           'water_cols': int((v >= 62).sum())} for k, v in ends.items()}
    sp = {}
    for name, b in zip(('blue', 'red'), BASES):
        t = top[b[0] - HALF:b[0] + HALF + 1, b[1] - HALF:b[1] + HALF + 1]
        sp[name] = {'top_z_values': {str(int(k)): int(v) for k, v in zip(*np.unique(t, return_counts=True))}}
    R['spawn_squares'] = sp
    cx0, cx1, cy0, cy1 = SPEC['court']
    ct = top[cx0:cx1 + 1, cy0:cy1 + 1]
    R['courtyard_blue'] = {'cells': int(ct.size), 'all_at_G': bool((ct == G).all()),
                           'anything_above': int(solid[cx0:cx1 + 1, cy0:cy1 + 1, :G].sum())}

    # routes
    nav = Nav(solid)
    p = nav.xyz
    res = {}
    dists = {}
    for name, b in zip(('blue', 'red'), BASES):
        src = nav.nodes_in(b[0] - HALF, b[0] + HALF, b[1] - HALF, b[1] + HALF, 0, 62)
        d = nav.dist_from(src)
        dists[name] = d
        own_end = (206, 211) if name == 'blue' else (300, 305)
        tgt = nav.nodes_in(own_end[0], own_end[1], 240, 271, 30, 62)
        other = BASES[1] if name == 'blue' else BASES[0]
        tgt2 = nav.nodes_in(other[0] - HALF, other[0] + HALF, other[1] - HALF, other[1] + HALF, 0, 62)
        targets = {'own_platform_end': tgt, 'enemy_spawn': tgt2,
                   'crossing_bell': nav.nodes_in(246, 266, 246, 266, G - 1, G),
                   'facade_portal': nav.nodes_in(250, 262, 134, 136, G, G),
                   'hand_reaching_base': nav.nodes_in(240, 272, 72, 84, 0, 62),
                   'hand_clawing_under_fingers': nav.nodes_in(244, 268, 405, 425, 30, 62),
                   'apse_altar': nav.nodes_in(250, 262, 312, 316, 0, 62)}
        res[name] = {k: (float(np.min(d[v])) if len(v) and np.isfinite(d[v]).any() else None)
                     for k, v in targets.items()}
        res[name]['reachable_nodes_pct'] = round(100 * float(np.isfinite(d).mean()), 1)
    R['routes'] = res
    R['route_parity_max_diff'] = max(abs((res['blue'][k] or 0) - (res['red'][k] or 0))
                                     for k in res['blue'] if k != 'reachable_nodes_pct')
    # traps: standable ground-level cells that cannot walk back to the basin floor
    G_rev = nav.G.T.tocsr()
    floor = nav.nodes_in(0, 511, 0, 511, G, G)
    dback = shortest_path(G_rev, directed=True, unweighted=True, indices=floor[::9], min_only=True)
    reach = np.isfinite(dists['blue']) | np.isfinite(dists['red'])
    trap = reach & ~np.isfinite(dback)
    tp = p[trap]
    R['trap_cells'] = {'count': int(trap.sum()), 'sample': tp[:: max(1, len(tp) // 15)][:15].tolist()}
    # build gap: highest point reachable on foot within 24 of the platform
    near = nav.nodes_in(x0 - 24, x1 + 24, y0 - 24, y1 + 24, 0, 62)
    rn = near[np.isfinite(dists['blue'][near]) | np.isfinite(dists['red'][near])]
    zmin = int(p[rn][:, 2].min()) if len(rn) else None
    R['build_gap'] = {'highest_reachable_near_platform_z': zmin,
                      'blocks_to_platform_level': (zmin - 2) if zmin is not None else None,
                      'platform_reachable_on_foot': bool(zmin is not None and zmin <= 3)}
    # highest reachable anywhere (perches)
    allr = np.nonzero(np.isfinite(dists['blue']))[0]
    hz = p[allr][np.argsort(p[allr][:, 2])[:5]]
    R['highest_reachable_spots'] = hz.tolist()
    if do_exposure:
        R['spawn_exposure'] = {name: exposure(solid, b) for name, b in zip(('blue', 'red'), BASES)}
    R['check_seconds'] = round(time.time() - t0, 1)
    with open(f'{out}/validation.json', 'w') as f:
        json.dump(R, f, indent=1)
    print(json.dumps({k: v for k, v in R.items() if k != 'floating_components'}, indent=1))
    print('floating:', R['floating_components']['count'], R['floating_components']['voxels'])
    for f_ in R['floating_components']['list'][:10]:
        print('  ', f_)
    return R


if __name__ == '__main__':
    main(sys.argv[1], '--pyspades' in sys.argv, '--exposure' in sys.argv)
