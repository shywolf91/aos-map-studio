"""Validation for Silverpine Hunt (Babel, piqueserver 1.4.2 stock babel_script constants).

python sph_check.py OUTDIR [--pyspades] [--exposure]
Writes OUTDIR/validation.json. Route checks are a preliminary graph model (3-air standing, 1-voxel step up,
drops <= 9 counted safe), not a collision simulation.
"""
from __future__ import annotations

import io
import json
import sys
import time

import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra as shortest_path

from sph_core import read_vxl, write_vxl, surface_mask

PLAT = {'x': (206, 305), 'y': (240, 271), 'z': 1}
BASES = ((118, 256), (394, 256))
HALF = 20


def floating(solid, mat=None):
    lab, n = ndi.label(solid, structure=ndi.generate_binary_structure(3, 1))
    grounded = set(np.unique(lab[:, :, 62:][solid[:, :, 62:]]).tolist())
    sizes = ndi.sum(solid, lab, index=np.arange(1, n + 1))
    out = []
    for i in range(1, n + 1):
        if i not in grounded:
            xs, ys, zs = np.nonzero(lab == i)
            mm = None
            if mat is not None:
                import sph_props as P_
                names = {v: k for k, v in P_.M.items()}
                vals, cnt = np.unique(mat[xs, ys, zs], return_counts=True)
                mm = names.get(int(vals[np.argmax(cnt)]), str(vals[np.argmax(cnt)]))
            out.append({'mat': mm, 'voxels': int(sizes[i - 1]), 'x': [int(xs.min()), int(xs.max())],
                        'y': [int(ys.min()), int(ys.max())], 'z': [int(zs.min()), int(zs.max())]})
    return out


class Nav:
    """Standable cells + 4-neighbour moves: step up <= 1, drop <= max_drop."""

    def __init__(self, solid, max_drop=9):
        air = ~solid
        st = solid.copy()
        st[:, :, :3] = False
        st[:, :, 3:] &= air[:, :, 2:-1] & air[:, :, 1:-2] & air[:, :, 0:-3]
        self.stand = st
        xs, ys, zs = np.nonzero(st)
        self.xyz = np.stack([xs, ys, zs], 1)
        idx = -np.ones(solid.shape, np.int32)
        idx[xs, ys, zs] = np.arange(len(xs))
        self.idx = idx
        rows, cols = [], []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = xs + dx, ys + dy
            ok = (nx >= 0) & (nx < 512) & (ny >= 0) & (ny < 512)
            for dz in range(-1, max_drop + 1):        # dz > 0 = going down (drop), -1 = step up
                nz = zs + dz
                ok2 = ok & (nz >= 3) & (nz < 64)
                j = np.full(len(xs), -1)
                j[ok2] = idx[nx[ok2], ny[ok2], nz[ok2]]
                if dz == -1:
                    # stepping up needs head room above the source: z-4 air
                    hr = np.zeros(len(xs), bool)
                    k = zs >= 4
                    hr[k] = ~solid[xs[k], ys[k], zs[k] - 4]
                    j[~hr] = -1
                m = j >= 0
                rows.append(np.nonzero(m)[0]); cols.append(j[m])
        r = np.concatenate(rows); c = np.concatenate(cols)
        self.G = csr_matrix((np.ones(len(r), np.int8), (r, c)), shape=(len(xs), len(xs)))

    def nodes_in(self, x0, x1, y0, y1, z0=0, z1=63):
        p = self.xyz
        return np.nonzero((p[:, 0] >= x0) & (p[:, 0] <= x1) & (p[:, 1] >= y0) & (p[:, 1] <= y1) &
                          (p[:, 2] >= z0) & (p[:, 2] <= z1))[0]

    def dist_from(self, srcs):
        d = shortest_path(self.G, directed=True, unweighted=True, indices=srcs, min_only=True)
        return d


def spawn_tops(solid, b):
    bx, by = b
    sq = solid[bx - HALF:bx + HALF + 1, by - HALF:by + HALF + 1]
    return np.argmax(sq, axis=2)


def exposure(solid, base, step_v=4, step_s=2):
    opaque = solid.copy()
    (x0, x1), (y0, y1) = PLAT['x'], PLAT['y']
    opaque[x0:x1 + 1, y0:y1 + 1, PLAT['z']] = True
    v = []
    for x in range(x0, x1 + 1, step_v):
        v += [(x + 0.5, y0 + 0.5), (x + 0.5, y1 + 0.5)]
    for y in range(y0, y1 + 1, step_v):
        v += [(x0 + 0.5, y + 0.5), (x1 + 0.5, y + 0.5)]
    V = np.unique(np.array(v), axis=0)
    V = np.column_stack([V, np.full(len(V), PLAT['z'] - 2.4)])
    T = []
    for x in range(base[0] - HALF, base[0] + HALF + 1, step_s):
        for y in range(base[1] - HALF, base[1] + HALF + 1, step_s):
            col = solid[x, y]
            z = int(np.argmax(col))
            T.append((x + 0.5, y + 0.5, z - 2.2))
    T = np.array(T)
    A = np.repeat(V, len(T), 0); B = np.tile(T, (len(V), 1))
    d = B - A; L = np.linalg.norm(d, axis=1)
    vis = np.ones(len(A), bool)
    n = int(np.ceil(L.max() / 0.25)) + 1
    for k in range(1, n):
        t = k * 0.25 / L
        act = vis & (t < 0.995)
        if not act.any():
            break
        p = A[act] + d[act] * t[act, None]
        xi = np.floor(p[:, 0]).astype(int); yi = np.floor(p[:, 1]).astype(int); zi = np.floor(p[:, 2]).astype(int)
        ins = (zi >= 0) & (zi < 64) & (xi >= 0) & (xi < 512) & (yi >= 0) & (yi < 512)
        hit = np.zeros(len(xi), bool)
        hit[ins] = opaque[xi[ins], yi[ins], zi[ins]]
        idx = np.nonzero(act)[0]
        vis[idx[hit]] = False
    viewers = vis.reshape(len(V), len(T)).sum(0)
    return {'viewers_per_spot_mean': round(float(viewers.mean()), 2), 'viewers_max': int(viewers.max()),
            'hidden_pct': round(100 * float((viewers == 0).mean()), 1), 'n_viewers': len(V), 'n_spots': len(T)}


def sky_rules(solid, sky, expected):
    """Placement rules for intentional floating pieces."""
    (x0, x1), (y0, y1) = PLAT['x'], PLAT['y']
    rows = []
    for o in sky:
        dx = max(x0 - o['x'][1], o['x'][0] - x1, 0); dy = max(y0 - o['y'][1], o['y'][0] - y1, 0)
        over_spawn = any(not (o['x'][1] < bx - HALF or o['x'][0] > bx + HALF or o['y'][1] < by - HALF or
                              o['y'][0] > by + HALF) for bx, by in BASES)
        # air between the object's underside and the next solid below it (excluding the object itself)
        gap = 64
        for x in range(o['x'][0], o['x'][1] + 1):
            for y in range(o['y'][0], o['y'][1] + 1):
                col = solid[x, y]
                zs = np.nonzero(col[o['z'][0]:o['z'][1] + 1])[0]
                if len(zs):
                    zb = o['z'][0] + zs.max()
                    below = np.nonzero(col[zb + 1:])[0]
                    if len(below):
                        gap = min(gap, int(below[0]))
        rows.append({'name': o['name'], 'voxels': o['voxels'], 'platform_dist': round(float(np.hypot(dx, dy)), 1),
                     'over_spawn_square': over_spawn, 'air_below_min': gap, 'z': o['z']})
    return {'objects': len(sky), 'voxels': sum(o['voxels'] for o in sky),
            'floating_components_found': len(expected),
            'min_platform_dist': min(r['platform_dist'] for r in rows),
            'any_over_spawn': any(r['over_spawn_square'] for r in rows),
            'min_air_below': min(r['air_below_min'] for r in rows), 'rows': rows}


def main(out, use_pyspades=False, do_exposure=False):
    t0 = time.time()
    data = open(f'{out}/silverpine_hunt.vxl', 'rb').read()
    solid, color, colored = read_vxl(data)
    R = {}
    surf = surface_mask(solid)
    R['reader'] = {'bytes': len(data), 'reencode_identical': write_vxl(solid, np.where(colored, color, 0)) == data,
                   'surface_all_coloured': bool((colored >= surf).all()), 'z63_solid': bool(solid[:, :, 63].all())}
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
                mine = ((cc >> 16) & 255, (cc >> 8) & 255, cc & 255)
                if tuple(c[:3]) != mine:
                    cm += 1
        R['pyspades'] = {'generate_identical': g == data, 'solid_mismatch_20k': sm, 'colour_mismatch_20k': cm,
                         'get_z_bases': [int(vm.get_z(*b)) for b in BASES]}
    fl = floating(solid, np.load(f'{out}/mat.npy'))
    binfo = json.load(open(f'{out}/build.json'))
    sky = binfo.get('sky_objects') or []

    def in_sky(f):
        return any(o['x'][0] <= f['x'][0] and f['x'][1] <= o['x'][1] and o['y'][0] <= f['y'][0] and
                   f['y'][1] <= o['y'][1] and o['z'][0] <= f['z'][0] and f['z'][1] <= o['z'][1] for o in sky)
    expected = [f for f in fl if in_sky(f)]
    fl = [f for f in fl if not in_sky(f)]
    R['floating_components'] = {'count': len(fl), 'voxels': sum(f['voxels'] for f in fl), 'list': fl[:20]}
    if sky:
        R['sky_layer'] = sky_rules(solid, sky, expected)
    cb = binfo.get('cosmetic_asymmetric_bbox')
    excl = np.zeros((512, 512), bool)
    if cb:
        excl[cb[0]:cb[1] + 1, cb[2]:cb[3] + 1] = True
        excl[512 - cb[1]:512 - cb[0] + 1, cb[2]:cb[3] + 1] = True
    for o in (binfo.get('sky_objects') or []):          # intentional cosmetic floating pieces
        excl[o['x'][0]:o['x'][1] + 1, o['y'][0]:o['y'][1] + 1] = True
        excl[512 - o['x'][1]:512 - o['x'][0] + 1, o['y'][0]:o['y'][1] + 1] = True
    keepm = ~excl[1:256, :, None]
    mir = (solid[1:256] != solid[511:256:-1]) & keepm
    R['mirror_solid_mismatch'] = int(mir.sum())
    mat = np.load(f'{out}/mat.npy')
    R['mirror_material_mismatch'] = int(((mat[1:256] != mat[511:256:-1]) & keepm).sum())
    R['mirror_excluded_cosmetic_bbox'] = cb
    (x0, x1), (y0, y1) = PLAT['x'], PLAT['y']
    R['platform_volume_voxels'] = int(solid[x0:x1 + 1, y0:y1 + 1, 0:3].sum())
    R['platform_margin_voxels'] = int(solid[x0 - 1:x1 + 2, y0 - 1:y1 + 2, 0:3].sum()) - R['platform_volume_voxels']
    top = np.argmax(solid, axis=2)
    ends = {'blue_end_x206_211': top[206:212, 240:272], 'red_end_x300_305': top[300:306, 240:272]}
    R['ground_under_platform_ends'] = {k: {'top_z_min': int(v.min()), 'top_z_max': int(v.max()),
                                           'water_cols': int((v >= 62).sum())} for k, v in ends.items()}
    sp = {}
    for name, b in zip(('blue', 'red'), BASES):
        t = spawn_tops(solid, b)
        sp[name] = {'top_z_values': {str(int(k)): int(v) for k, v in zip(*np.unique(t, return_counts=True))},
                    'water_cols': int((t >= 62).sum())}
    R['spawn_squares'] = sp
    R['spawn_heights_mirror_equal'] = bool((spawn_tops(solid, BASES[0]) == spawn_tops(solid, BASES[1])[::-1]).all())

    # routes
    nav = Nav(solid)
    res = {}
    for name, b in zip(('blue', 'red'), BASES):
        src = nav.nodes_in(b[0] - HALF, b[0] + HALF, b[1] - HALF, b[1] + HALF, 0, 62)
        d = nav.dist_from(src)
        own_end = (206, 211) if name == 'blue' else (300, 305)
        tgt = nav.nodes_in(own_end[0], own_end[1], 240, 271, 30, 62)
        other = BASES[1] if name == 'blue' else BASES[0]
        tgt2 = nav.nodes_in(other[0] - HALF, other[0] + HALF, other[1] - HALF, other[1] + HALF, 0, 62)
        king = nav.nodes_in(236, 276, 120, 160, 0, 62)       # kill site / lake shore
        mine = nav.nodes_in(150, 362, 412, 420, 44, 47)       # silver-mine tunnel
        nest = nav.nodes_in(230, 282, 236, 276, 55, 57)       # nest hall floor
        res[name] = {'to_own_platform_end': float(np.min(d[tgt])) if len(tgt) else None,
                     'to_enemy_spawn': float(np.min(d[tgt2])) if len(tgt2) else None,
                     'to_kill_site': float(np.min(d[king])) if len(king) else None,
                     'to_mine_tunnel': float(np.min(d[mine])) if len(mine) else None,
                     'to_nest_hall': float(np.min(d[nest])) if len(nest) else None,
                     'reachable_nodes_pct': round(100 * float(np.isfinite(d).mean()), 1)}
        if name == 'blue':
            d_blue = d
    R['routes'] = res
    # trap cells: standable land/pit cells (not water, not roofs) that cannot reach the plateau safely
    G_rev = nav.G.T.tocsr()
    plat_nodes = nav.nodes_in(0, 511, 0, 511, 45, 47)
    dback = shortest_path(G_rev, directed=True, unweighted=True, indices=plat_nodes[::7], min_only=True)
    p = nav.xyz
    landish = (p[:, 2] < 62) & (p[:, 2] >= 45)
    trap = landish & ~np.isfinite(dback)
    tp = p[trap]
    R['trap_cells_z45_61'] = {'count': int(trap.sum()),
                              'sample': tp[:: max(1, len(tp) // 15)][:15].tolist()}
    # lake / creek / cave floors can walk back to the basin
    for nm, (z0, z1) in (('lake_ice_z50', (50, 50)), ('cave_floor_z56', (56, 56)), ('creek_z47_48', (47, 48))):
        q = nav.nodes_in(0, 511, 0, 511, z0, z1)
        R.setdefault('exits', {})[nm] = {'cells': int(len(q)),
                                         'can_reach_basin_pct': round(100 * float(np.isfinite(dback[q]).mean()), 1)
                                         if len(q) else None}
    # highest walkable point near the platform (build gap)
    near = nav.nodes_in(x0 - 24, x1 + 24, y0 - 24, y1 + 24, 0, 62)
    reach = near[np.isfinite(d_blue[near])]
    zmin = int(p[reach][:, 2].min()) if len(reach) else None
    R['build_gap'] = {'highest_reachable_near_platform_z': zmin,
                      'blocks_to_build_up_to_platform_level': (zmin - 2) if zmin is not None else None,
                      'platform_reachable_on_foot': bool(zmin is not None and zmin <= 3)}
    if do_exposure:
        R['spawn_exposure'] = {name: exposure(solid, b) for name, b in zip(('blue', 'red'), BASES)}
    R['check_seconds'] = round(time.time() - t0, 1)
    with open(f'{out}/validation.json', 'w') as f:
        json.dump(R, f, indent=1)
    print(json.dumps({k: v for k, v in R.items() if k != 'floating_components'}, indent=1))
    print('floating:', R['floating_components']['count'], R['floating_components']['voxels'])
    for f_ in R['floating_components']['list'][:20]:
        print('  ', f_)
    return R


if __name__ == '__main__':
    main(sys.argv[1], '--pyspades' in sys.argv, '--exposure' in sys.argv)
