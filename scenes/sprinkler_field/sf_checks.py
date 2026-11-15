"""Sprinkler Field extra checks, on top of aosmap.kit.babel_checks (same graph model: kit Nav, 'hc' rules —
3 air to stand, 1-voxel step with 4 air of climb room, drops <= 9 safe). A graph model, not a collision simulation.

assist_landings  sprinkler T-bar and trowel cap: reachable on foot from BOTH spawns, path length (graph steps) per
                 team, |blue - red| / max <= 5 %, build gap per team (top reachable z in the landing box - (pz + 1))
hose             per half: each declared crossing (arch = walk under, rut = walk over, split = walk through) is a
                 north -> south path inside its x window (>= crossings_min per half); hose-top cells reachable on foot
                 from a spawn, including the arch tops
nest             every entrance junction reachable; every underground tunnel / chamber floor cell reachable AND able to
                 walk back to a spawn; air under the ground inside the no-tunnel boxes = 0
interiors        every recorded room (one-offs included) reachable with a way back (same as the kit, listed by name)
platform_clear   solid voxels at z <= 3 over the platform footprint +-1 (must be 0)
pillars          vertical runs >= 5 of voxels with no solid in-plane neighbour (1x1 pillars); 'fields' = 16x16 tiles
                 holding >= 3 of them; plus the blade cross-section at the base (by construction)
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from aosmap.kit import codec
from aosmap.kit.babel_checks import Nav
from aosmap.kit.params import BABEL_DEFAULT as P


def _dmin(d, nodes):
    if len(nodes) == 0:
        return None
    v = d[nodes]
    return float(v.min()) if np.isfinite(v).any() else None


def run(out, data, info, S, mat=None, terrain_H=None):
    solid = codec.decode(data)[0]
    nav = Nav(solid)
    p = nav.xyz
    half = P['spawn_half']
    names = P['team_names']
    src = {n: nav.nodes_in(b[0] - half, b[0] + half, b[1] - half, b[1] + half, 0, 62)
           for n, b in zip(names, P['bases'])}
    d = {n: nav.dist_from(src[n]) for n in names}
    back = {n: nav.dist_from(src[n], reverse=True) for n in names}
    fwd_any = np.isfinite(d[names[0]]) | np.isfinite(d[names[1]])
    back_any = np.isfinite(back[names[0]]) | np.isfinite(back[names[1]])
    R = {}
    pz = P['platform_z']

    # ------------------------------------------------------------------ assist landings
    al = {}
    for lname, bx in (info.get('landings') or {}).items():
        nodes = nav.nodes_in(*bx)
        row = {}
        for n in names:
            dd = _dmin(d[n], nodes)
            rch = nodes[np.isfinite(d[n][nodes])] if len(nodes) else nodes
            zt = int(p[rch][:, 2].min()) if len(rch) else None
            row[n] = {'path_steps': dd, 'top_reachable_z': zt, 'build_gap': (zt - (pz + 1)) if zt is not None else None,
                      'can_walk_back': bool(len(rch) and np.isfinite(back[n][rch]).any())}
        a, b = row[names[0]]['path_steps'], row[names[1]]['path_steps']
        row['reachable_both'] = a is not None and b is not None
        row['path_diff_pct'] = round(100 * abs(a - b) / max(a, b), 2) if row['reachable_both'] else None
        row['equal_within_5pct'] = bool(row['reachable_both'] and row['path_diff_pct'] <= 5.0)
        row['gaps_equal'] = row[names[0]]['build_gap'] == row[names[1]]['build_gap']
        al[lname] = row
    R['assist_landings'] = al

    # ------------------------------------------------------------------ hose crossings and hose top
    Hs = S['hose']
    pts = Hs['path']

    def hy(x):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if x0 <= x <= x1:
                return y0 + (y1 - y0) * (x - x0) / max(x1 - x0, 1)
        return pts[-1][1]
    cross = {'west': [], 'east': []}
    for c in (info.get('hose') or {}).get('crossings', []):
        a, b = c['x']
        for side in ('west', 'east'):
            xa, xb = (a, b) if side == 'west' else (512 - b, 512 - a)
            yc = hy((a + b) / 2)
            allowed = nav.nodes_in(xa - 1, xb + 1, int(yc) - 22, int(yc) + 22, 20, 62)
            north = allowed[p[allowed, 1] <= yc - Hs['r_out'] - 3]
            south = allowed[p[allowed, 1] >= yc + Hs['r_out'] + 3]
            dd = nav.dist_from(north, allowed=allowed)
            ok_ns = _dmin(dd, south) is not None
            dd2 = nav.dist_from(south, allowed=allowed)
            ok_sn = _dmin(dd2, north) is not None
            cross[side].append({'kind': c['kind'], 'x': [xa, xb], 'north_to_south': ok_ns, 'south_to_north': ok_sn})
    hose_ids = []
    if mat is not None:
        names_m = info.get('materials', {})
        hose_ids = [names_m[k] for k in ('hose', 'hose_stripe', 'coupling') if k in names_m]
    on_hose = np.isin(mat[p[:, 0], p[:, 1], p[:, 2]], hose_ids) if hose_ids else np.zeros(len(p), bool)
    top_nodes = np.nonzero(on_hose & (p[:, 2] <= Hs['cz'] - Hs['r_out'] + 1))[0]
    arch_nodes = top_nodes[p[top_nodes, 2] <= Hs['cz'] - Hs['r_out'] - min(l for _, l in Hs['arches']) + 1]
    R['hose'] = {
        'crossings': cross,
        'crossings_ok_per_half': {s: sum(1 for c in v if c['north_to_south'] and c['south_to_north'])
                                  for s, v in cross.items()},
        'crossings_min': Hs['crossings_min'],
        'top_cells': int(len(top_nodes)),
        'top_cells_reachable_pct': round(100 * float(fwd_any[top_nodes].mean()), 1) if len(top_nodes) else None,
        'arch_top_cells': int(len(arch_nodes)),
        'arch_top_reachable': bool(len(arch_nodes) and fwd_any[arch_nodes].any()),
        'arch_top_walk_back': bool(len(arch_nodes) and (fwd_any & back_any)[arch_nodes].any()),
    }

    # ------------------------------------------------------------------ ant nest
    top = np.argmax(solid, axis=2)
    fl = S['z']['tunnel_floor']
    under = (p[:, 2] == fl) & (top[p[:, 0], p[:, 1]] < fl - 3)
    nest_nodes = np.nonzero(under)[0]
    ok = fwd_any[nest_nodes] & back_any[nest_nodes]
    lab_mask = np.zeros(solid.shape[:2], bool)
    lab_mask[p[nest_nodes, 0], p[nest_nodes, 1]] = True
    lab, ncomp = ndi.label(lab_mask)
    ent = {}
    for name, e in ((info.get('nest') or {}).get('entrances') or {}).items():
        jx, jy, jz = e['junction']
        for side, xx in (('W', jx), ('E', 512 - jx)):
            nn = nav.nodes_in(xx - 2, xx + 2, jy - 2, jy + 2, jz - 1, jz + 1)
            ent[f'{name}{side}'] = {'reachable': bool(len(nn) and fwd_any[nn].any()),
                                    'way_out': bool(len(nn) and back_any[nn].any())}
    no_tun = []
    for (x0, x1, y0, y1) in S['no_tunnel_boxes']:
        for (a, b) in ((x0, x1), (512 - x1, 512 - x0)):
            sub = solid[a:b + 1, y0:y1 + 1, :62]
            tz = terrain_H[a:b + 1, y0:y1 + 1] if terrain_H is not None else np.argmax(sub, axis=2)
            zz = np.arange(62)[None, None, :]
            cav = (~sub) & (zz > tz[:, :, None])                # air below the terrain surface (a cave)
            no_tun.append({'box': [a, b, y0, y1], 'air_under_ground': int(cav.sum())})
    R['nest'] = {'underground_floor_cells': int(len(nest_nodes)),
                 'reachable_and_walk_back_pct': round(100 * float(ok.mean()), 1) if len(ok) else None,
                 'cells_failing': int((~ok).sum()), 'failing_sample': p[nest_nodes[~ok]][:10].tolist(),
                 'components': int(ncomp), 'entrances': ent,
                 'all_entrances_ok': all(v['reachable'] and v['way_out'] for v in ent.values()),
                 'no_tunnel_boxes': no_tun,
                 'no_tunnel_ok': all(v['air_under_ground'] == 0 for v in no_tun)}

    # ------------------------------------------------------------------ interiors (one-offs included)
    rows = []
    for (nm, x, y, z) in info.get('interiors') or []:
        cand = nav.nodes_in(x - 2, x + 2, y - 2, y + 2, z - 1, z + 1)
        rch = bool(len(cand) and fwd_any[cand].any())
        out_ = bool(len(cand) and (fwd_any & back_any)[cand].any())
        rows.append({'name': nm, 'xyz': [x, y, z], 'reachable': rch, 'way_out': out_})
    R['interiors'] = {'checked': len(rows), 'ok': sum(1 for r in rows if r['reachable'] and r['way_out']),
                      'failures': [r for r in rows if not (r['reachable'] and r['way_out'])]}

    # ------------------------------------------------------------------ platform clearance
    (x0, x1), (y0, y1) = P['platform_x'], P['platform_y']
    R['platform_clear'] = {'box': [x0 - 1, x1 + 1, y0 - 1, y1 + 1, 0, 3],
                           'solid_voxels': int(solid[x0 - 1:x1 + 2, y0 - 1:y1 + 2, 0:4].sum())}

    # ------------------------------------------------------------------ 1x1 pillars
    s = solid
    nb = np.zeros_like(s)
    nb[1:] |= s[:-1]
    nb[:-1] |= s[1:]
    nb[:, 1:] |= s[:, :-1]
    nb[:, :-1] |= s[:, 1:]
    iso = s & ~nb
    iso[:, :, 62:] = False
    runs = []
    xs, ys = np.nonzero(iso.any(axis=2))
    for x, y in zip(xs, ys):
        col = iso[x, y]
        lab1, n1 = ndi.label(col)
        for k in range(1, n1 + 1):
            ln = int((lab1 == k).sum())
            if ln >= 5:
                runs.append((int(x), int(y), ln))
    tiles = {}
    for (x, y, ln) in runs:
        tiles[(x // 16, y // 16)] = tiles.get((x // 16, y // 16), 0) + 1
    R['pillars'] = {'runs_ge5': len(runs), 'sample': runs[:12],
                    'fields_16x16_ge3': sum(1 for v in tiles.values() if v >= 3),
                    'blade_base_section': '3 x 2 (2 x 2 from 40 %, 2 x 1 from 70 %, 1 x 1 only in the top 10 %)',
                    'blade_stats': info.get('blades')}

    R['summary'] = {
        'sprinkler_reachable_both': al.get('sprinkler_tbar', {}).get('reachable_both'),
        'sprinkler_paths_equal_5pct': al.get('sprinkler_tbar', {}).get('equal_within_5pct'),
        'trowel_reachable_both': al.get('trowel_cap', {}).get('reachable_both'),
        'trowel_paths_equal_5pct': al.get('trowel_cap', {}).get('equal_within_5pct'),
        'hose_crossings_ok': all(v >= Hs['crossings_min'] for v in R['hose']['crossings_ok_per_half'].values()),
        'hose_top_walkable': R['hose']['arch_top_reachable'] and R['hose']['arch_top_walk_back'],
        'nest_ok': R['nest']['all_entrances_ok'] and R['nest']['cells_failing'] == 0,
        'no_tunnel_ok': R['nest']['no_tunnel_ok'],
        'interiors_ok': not R['interiors']['failures'],
        'platform_clear': R['platform_clear']['solid_voxels'] == 0,
        'no_pillar_fields': R['pillars']['fields_16x16_ge3'] == 0,
    }
    return R
