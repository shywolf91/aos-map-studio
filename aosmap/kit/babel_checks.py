"""The full Babel check suite -> validation.json.

Merged from the identical cores of gf/hc/wkh/sph_check.py (Nav graph, exposure, floating, sky rules, mirror,
platform, spawn squares, routes, traps, interiors, build gap), Bloomhop check.py (8-neighbour BFS rules,
its exposure model, anchor front step), aosmap.validate.check_babel and aosmap.sightline. New here (no map had
them as checks): safe descent, flank routes, enemy-face access to the tower anchors, per-structure assist gaps,
periphery reachability. 'zone_profile' (report-only) adds the aosmap.kit.zones metrics (docs/babel_zone_study.md).

Route checks are a GRAPH MODEL (3 air voxels to stand, 1-voxel step up, drops <= 9 counted safe, <= 19 survivable),
not a collision simulation, and never proof of playability.

    python -m aosmap.kit.babel_checks maps/<map>_v1 [--out scratch/validation.json] [--rules hc|bloomhop]
        [--exposure calibrated|bloomhop] [--axis x512|x511|point512] [--no-pyspades] [--targets targets.json]
    (--axis defaults to build.json 'axis', else x512; 'point512' = 180 degree rotation about (256, 256))

Inputs read from the map folder when present: the .vxl, build.json (sky_objects / kept_floating, interiors,
cosmetic_asymmetric_bbox and/or cosmetic_asymmetric_boxes, tag_rect, check_targets), mat.npy, terrain_H.npy.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import time

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

from . import codec
from .params import BABEL_DEFAULT, FALL_ANY_MAX, FALL_SAFE_MAX, MX, MY, MZ
from .symmetry import AXES, floating_components, mirror_index, mirror_index_y, mirror_mismatch, split_expected, \
    standable


# =============================================================================================== navigation graph

class Nav:
    """Standable cells and moves between neighbouring columns.

    rules='hc'       (gf/hc/wkh/sph_check): 4 neighbours, step up 1 needs air at z-4 over the source,
                     drop <= max_drop, no check of the target column above the landing.
    rules='bloomhop' (Bloomhop check.bfs): 8 neighbours, same step/drop limits, plus the target column must be clear
                     from min(z, Z) - 3 down to the landing (you can actually fall down it); wade=False drops z 63.
    """

    def __init__(self, solid, max_drop=FALL_SAFE_MAX, rules='hc', wade=True):
        self.solid = solid
        st = standable(solid)
        st[:, :, :3] = False
        if not wade:
            st[:, :, 63] = False
        self.stand = st
        xs, ys, zs = np.nonzero(st)
        self.xyz = np.stack([xs, ys, zs], 1)
        idx = -np.ones(solid.shape, np.int32)
        idx[xs, ys, zs] = np.arange(len(xs))
        self.idx = idx
        dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))
        if rules == 'bloomhop':
            dirs = dirs + ((1, 1), (1, -1), (-1, 1), (-1, -1))
            cs = np.concatenate([np.zeros(solid.shape[:2] + (1,), np.int16),
                                 np.cumsum(solid, axis=2, dtype=np.int16)], axis=2)    # cs[..., k] = solids z < k
        rows, cols = [], []
        for dx, dy in dirs:
            nx, ny = xs + dx, ys + dy
            ok = (nx >= 0) & (nx < MX) & (ny >= 0) & (ny < MY)
            for dz in range(-1, max_drop + 1):
                nz = zs + dz
                ok2 = ok & (nz >= 3) & (nz < MZ)
                j = np.full(len(xs), -1)
                j[ok2] = idx[nx[ok2], ny[ok2], nz[ok2]]
                if dz == -1:
                    hr = np.zeros(len(xs), bool)
                    k = zs >= 4
                    hr[k] = ~solid[xs[k], ys[k], zs[k] - 4]
                    if rules == 'bloomhop':
                        hr[~k] = ~solid[xs[~k], ys[~k], 0]
                    j[~hr] = -1
                if rules == 'bloomhop':
                    m = j >= 0
                    lo = np.maximum(np.minimum(zs, nz) - 3, 0)
                    blocked = np.zeros(len(xs), bool)
                    blocked[m] = (cs[nx[m], ny[m], nz[m]] - cs[nx[m], ny[m], lo[m]]) > 0
                    j[blocked] = -1
                m = j >= 0
                rows.append(np.nonzero(m)[0])
                cols.append(j[m])
        r = np.concatenate(rows)
        c = np.concatenate(cols)
        self.G = csr_matrix((np.ones(len(r), np.int8), (r, c)), shape=(len(xs), len(xs)))
        self._GT = None

    @property
    def GT(self):
        if self._GT is None:
            self._GT = self.G.T.tocsr()
        return self._GT

    def nodes_in(self, x0, x1, y0, y1, z0=0, z1=63):
        p = self.xyz
        return np.nonzero((p[:, 0] >= x0) & (p[:, 0] <= x1) & (p[:, 1] >= y0) & (p[:, 1] <= y1) &
                          (p[:, 2] >= z0) & (p[:, 2] <= z1))[0]

    def dist_from(self, srcs, reverse=False, allowed=None):
        G = self.GT if reverse else self.G
        if allowed is not None:
            keep = np.zeros(G.shape[0], bool)
            keep[allowed] = True
            D = csr_matrix((keep.astype(np.int8), (np.arange(len(keep)), np.arange(len(keep)))), shape=G.shape)
            G = D @ G @ D
            srcs = np.asarray(srcs)[keep[np.asarray(srcs)]] if len(srcs) else srcs
        if len(srcs) == 0:
            return np.full(G.shape[0], np.inf)
        return dijkstra(G, directed=True, unweighted=True, indices=srcs, min_only=True)


def _dmin(d, nodes):
    if len(nodes) == 0:
        return None
    v = d[nodes]
    return float(v.min()) if np.isfinite(v).any() else None


# =============================================================================================== exposure

def _exposure_calibrated(solid, base, P):
    """platform-edge eyes (every 4, z - 2.4) -> heads (topmost voxel - 2.2, every 2); 0.25 march; platform opaque.
    Same model as aosmap.sightline and docs/spawn_exposure_calibration.json."""
    (x0, x1), (y0, y1), pz = P['platform_x'], P['platform_y'], P['platform_z']
    half = P['spawn_half']
    opaque = solid.copy()
    opaque[x0:x1 + 1, y0:y1 + 1, pz] = True
    v = []
    for x in range(x0, x1 + 1, 4):
        v += [(x + 0.5, y0 + 0.5), (x + 0.5, y1 + 0.5)]
    for y in range(y0, y1 + 1, 4):
        v += [(x0 + 0.5, y + 0.5), (x1 + 0.5, y + 0.5)]
    V = np.unique(np.array(v), axis=0)
    V = np.column_stack([V, np.full(len(V), pz - 2.4)])
    T = []
    for x in range(base[0] - half, base[0] + half + 1, 2):
        for y in range(base[1] - half, base[1] + half + 1, 2):
            T.append((x + 0.5, y + 0.5, int(np.argmax(solid[x, y])) - 2.2))
    T = np.array(T)
    A = np.repeat(V, len(T), 0)
    B = np.tile(T, (len(V), 1))
    d = B - A
    L = np.linalg.norm(d, axis=1)
    vis = np.ones(len(A), bool)
    n = int(np.ceil(L.max() / 0.25)) + 1
    for k in range(1, n):
        t = k * 0.25 / L
        act = vis & (t < 0.995)
        if not act.any():
            break
        p = A[act] + d[act] * t[act, None]
        xi, yi, zi = (np.floor(p[:, i]).astype(int) for i in range(3))
        ins = (zi >= 0) & (zi < MZ) & (xi >= 0) & (xi < MX) & (yi >= 0) & (yi < MY)
        hit = np.zeros(len(xi), bool)
        hit[ins] = opaque[xi[ins], yi[ins], zi[ins]]
        vis[np.nonzero(act)[0][hit]] = False
    viewers = vis.reshape(len(V), len(T)).sum(0)
    return viewers, len(V), len(T)


def _exposure_bloomhop(solid, base, P):
    """Bloomhop check.exposure: eyes every 3 at z -1.0, heads top - 2.4, 0.5 sampling incl. endpoints, samples within
    1.5 of the head ignored, the platform counts only beyond 1.0 from the eye."""
    (x0, x1), (y0, y1) = P['platform_x'], P['platform_y']
    half = P['spawn_half']
    top = np.argmax(solid, axis=2)
    eyes = []
    for x in range(x0, x1 + 1, 3):
        eyes += [(x + .5, y0 + .5, -1.0), (x + .5, y1 + .5, -1.0)]
    for y in range(y0, y1 + 1, 3):
        eyes += [(x0 + .5, y + .5, -1.0), (x1 + .5, y + .5, -1.0)]
    eyes = np.array(eyes)
    heads = np.array([(x + .5, y + .5, top[x, y] - 2.4)
                      for x in range(base[0] - half, base[0] + half + 1, 2)
                      for y in range(base[1] - half, base[1] + half + 1, 2)])
    viewers = np.zeros(len(heads), int)
    for e in eyes:
        d = heads - e[None, :]
        L = np.linalg.norm(d, axis=1)
        n = int(L.max() / 0.5) + 1
        ts = np.linspace(0, 1, n)[None, :]
        Pp = e[None, None, :] + d[:, None, :] * ts[..., None]
        px, py, pz = (np.floor(Pp[..., i]).astype(int) for i in range(3))
        ok = (pz >= 0) & (pz < MZ)
        near = (1 - ts) * L[:, None] < 1.5
        plat_hit = (pz == 1) & (px >= x0) & (px <= x1) & (py >= y0) & (py <= y1) & (ts * L[:, None] > 1.0)
        hit = np.zeros(px.shape, bool)
        hit[ok] = solid[np.clip(px[ok], 0, 511), np.clip(py[ok], 0, 511), pz[ok]]
        hit &= ~near
        viewers += ~(hit | plat_hit).any(axis=1)
    return viewers, len(eyes), len(heads)


EXPOSURE_PRESETS = {'calibrated': _exposure_calibrated, 'bloomhop': _exposure_bloomhop}


def spawn_exposure(solid, base, params=BABEL_DEFAULT, preset='calibrated'):
    viewers, nv, ns = EXPOSURE_PRESETS[preset](solid, base, params)
    return {'preset': preset, 'viewers_per_spot_mean': round(float(viewers.mean()), 2),
            'viewers_max': int(viewers.max()), 'hidden_pct': round(100 * float((viewers == 0).mean()), 1),
            'exposed_pct': round(100 * float((viewers > 0).mean()), 1), 'n_viewers': nv, 'n_spots': ns,
            'targets_met': bool(viewers.mean() <= 10 and (viewers == 0).mean() >= 0.15)}


# =============================================================================================== static checks

def reader_checks(data, solid, color, colored):
    surf = codec.surface_mask(solid)
    return {'bytes': len(data), 'reencode_identical': codec.encode(solid, np.where(colored, color, 0)) == data,
            'surface_all_coloured': bool((colored >= surf).all()), 'z63_solid': bool(solid[:, :, 63].all())}


def sky_rules(solid, sky, params=BABEL_DEFAULT):
    (x0, x1), (y0, y1) = params['platform_x'], params['platform_y']
    half = params['spawn_half']
    rows = []
    for o in sky:
        dx = max(x0 - o['x'][1], o['x'][0] - x1, 0)
        dy = max(y0 - o['y'][1], o['y'][0] - y1, 0)
        over = any(not (o['x'][1] < bx - half or o['x'][0] > bx + half or o['y'][1] < by - half or
                        o['y'][0] > by + half) for bx, by in params['bases'])
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
        rows.append({'name': o.get('name', '?'), 'voxels': o.get('voxels'),
                     'platform_dist': round(float(np.hypot(dx, dy)), 1), 'over_spawn_square': over,
                     'air_below_min': gap, 'z': o['z']})
    return {'objects': len(sky), 'min_platform_dist': min(r['platform_dist'] for r in rows),
            'any_over_spawn': any(r['over_spawn_square'] for r in rows),
            'min_air_below': min(r['air_below_min'] for r in rows),
            'rules_met': all(r['platform_dist'] >= 60 and not r['over_spawn_square'] and r['air_below_min'] >= 8
                             for r in rows), 'rows': rows}


def platform_checks(solid, params=BABEL_DEFAULT):
    (x0, x1), (y0, y1) = params['platform_x'], params['platform_y']
    vol = int(solid[x0:x1 + 1, y0:y1 + 1, 0:3].sum())
    margin = int(solid[x0 - 1:x1 + 2, y0 - 1:y1 + 2, 0:3].sum()) - vol
    top = np.argmax(solid, axis=2)
    ends = {'blue_end': top[x0:x0 + 6, y0:y1 + 1], 'red_end': top[x1 - 5:x1 + 1, y0:y1 + 1]}
    return {'platform_volume_voxels': vol, 'platform_margin_voxels': margin,
            'ground_under_platform_ends': {k: {'top_z_min': int(v.min()), 'top_z_max': int(v.max()),
                                               'water_cols': int((v >= 62).sum())} for k, v in ends.items()}}


def spawn_square_checks(solid, params=BABEL_DEFAULT, axis='x512'):
    half = params['spawn_half']
    top = np.argmax(solid, axis=2)
    out = {}
    tops = []
    for name, (bx, by) in zip(params['team_names'], params['bases']):
        t = top[bx - half:bx + half + 1, by - half:by + half + 1]
        tops.append(t)
        mode = np.bincount(t.ravel()).argmax()
        # roof spawn: a solid voxel in the column below an air gap under the top (spawning on a roof/canopy)
        sq = solid[bx - half:bx + half + 1, by - half:by + half + 1]
        air_below_top = np.zeros(t.shape, bool)
        for i in range(t.shape[0]):
            for j in range(t.shape[1]):
                z = t[i, j]
                air_below_top[i, j] = (~sq[i, j, z:63]).any() if z < 62 else False
        out[name] = {'top_z_values': {str(int(k)): int(v) for k, v in zip(*np.unique(t, return_counts=True))},
                     'top_z_min': int(t.min()), 'top_z_max': int(t.max()),
                     'flat_share': round(float((t == mode).mean()), 2),
                     'water_cols': int((t >= 62).sum()), 'roof_cols': int(air_below_top.sum())}
    a, b = tops
    # red square mirrored onto blue's
    bx_r = params['bases'][1][0]
    xs = [mirror_index(x, axis) for x in range(params['bases'][0][0] - half, params['bases'][0][0] + half + 1)]
    ys = [mirror_index_y(y, axis) for y in range(params['bases'][0][1] - half, params['bases'][0][1] + half + 1)]
    b_m = top[np.ix_(xs, ys)]
    out['mirror_equal_share'] = round(float((a == b_m).mean()), 3)
    out['_red_base_x'] = bx_r
    return out


def anchor_checks(solid, nav=None, params=BABEL_DEFAULT, face=None, axis='x512'):
    """Tower anchors: ground directly under each platform end, and how the enemy-facing side meets the corridor.
    face = (x_blue_face, x_red_face): the outermost anchor columns toward the enemy (default: the platform ends).
    enemy_face_step = top[face+1] - top[face] (blue) / top[face-1] - top[face] (red): > 1 means no walk-on step.
    enemy_face_walk_on_rows = rows where the graph has a move from the corridor column onto the anchor top."""
    (x0, x1), (y0, y1) = params['platform_x'], params['platform_y']
    fb, fr = face or (x0 + 5, x1 - 5)
    top = np.argmax(solid, axis=2)
    res = {}
    for name, f, out_dx in (('blue', fb, 1), ('red', fr, -1)):
        steps = [int(top[f + out_dx, y]) - int(top[f, y]) for y in range(y0, y1 + 2)]
        r = {'face_x': f, 'enemy_face_step_min': min(steps), 'raised': max(steps) >= 2}
        if nav is not None:
            walk = 0
            for y in range(y0, y1 + 1):
                a = nav.idx[f + out_dx, y][nav.idx[f + out_dx, y] >= 0]
                b = nav.idx[f, y, int(top[f, y])]
                if b >= 0 and len(a) and nav.G[a][:, [b]].nnz:
                    walk += 1
            r['enemy_face_walk_on_rows'] = walk
        res[name] = r
    return res


def cosmetic_excludes(build):
    """Mirror-check exclusion boxes (x0, x1, y0, y1) from build.json: the single legacy 'cosmetic_asymmetric_bbox'
    and/or a list 'cosmetic_asymmetric_boxes' (train, tag, snowmen, sky ...). Each box also excludes its mirror."""
    excl = []
    cb = (build or {}).get('cosmetic_asymmetric_bbox')
    if cb:
        excl.append(tuple(cb[:4]))
    for b in (build or {}).get('cosmetic_asymmetric_boxes') or []:
        t = tuple(b[:4])
        if t not in excl:
            excl.append(t)
    return excl


# =============================================================================================== routes etc.

def run_all(data: bytes, *, params=BABEL_DEFAULT, build=None, mat=None, mat_names=None, terrain_H=None,
            axis='x512', exposure_preset='calibrated', rules='hc', pyspades=True, targets=None,
            end_z=(0, 62), trap_anchor=None, trap_stride=5, ground_band=3, trap_z=None,
            tower_zone=None, assist=None, flank_min=130, flank_max=210, centre_half_x=80,
            anchor_face=None, build_gap_margin=24, build_gap_graph='safe', exits=None, timing=True,
            zone_profile=True, zone_rules=True, zone_rules_skip=None, waivers=None):
    """Run every check on one map. Returns a JSON-able dict. See the module docstring for the model."""
    t0 = time.time()
    build = build or {}
    P = params
    wv = dict(build.get('waivers') or {})
    wv.update(waivers or {})
    bad = sorted(set(wv) - set(row_keys(P)))
    if bad:
        raise ValueError(f'waiver names unknown summary rows: {bad} (known: {row_keys(P)})')
    R = {'model': {'rules': rules, 'axis': axis, 'exposure': exposure_preset, 'max_drop_safe': FALL_SAFE_MAX,
                   'note': 'graph model, not a collision simulation'}}
    if wv:
        R['waivers'] = wv
    solid, color, colored = codec.decode(data)
    R['reader'] = reader_checks(data, solid, color, colored)
    if pyspades:
        R['pyspades'] = codec.pyspades_crosscheck(data, solid, color)

    # floating
    fl = floating_components(solid, mat, mat_names)
    expected_boxes = list(build.get('sky_objects') or []) + [
        {'x': k['bbox'][0:2], 'y': k['bbox'][2:4], 'z': k['bbox'][4:6]} for k in (build.get('kept_floating') or [])]
    fl, expected = split_expected(fl, expected_boxes)
    R['floating_components'] = {'count': len(fl), 'voxels': sum(f['voxels'] for f in fl), 'list': fl[:20],
                                'expected_count': len(expected), 'expected_voxels': sum(f['voxels'] for f in expected)}
    if expected_boxes:
        R['sky_layer'] = sky_rules(solid, expected_boxes, P)

    # mirror
    excl = cosmetic_excludes(build)
    for o in expected_boxes:
        excl.append((o['x'][0], o['x'][1], o['y'][0], o['y'][1]))
    mm = mirror_mismatch(solid, mat, axis, excl)
    R['mirror'] = {'solid_mismatch': mm['solid'], 'material_mismatch': mm.get('material'),
                   'solid_mismatch_unfiltered': mirror_mismatch(solid, None, axis)['solid'],
                   'excluded_boxes': excl, 'axis': axis}

    R.update(platform_checks(solid, P))
    R['spawn_squares'] = spawn_square_checks(solid, P, axis)
    R['spawn_squares'].pop('_red_base_x', None)

    # ------------------------------------------------------------------ routes (safe graph and survivable graph)
    nav = Nav(solid, FALL_SAFE_MAX, rules)
    nav_any = Nav(solid, FALL_ANY_MAX, rules)
    (x0, x1), (y0, y1), pz = P['platform_x'], P['platform_y'], P['platform_z']
    half = P['spawn_half']
    names = P['team_names']
    if rules == 'bloomhop':
        def spawn_src(g, b):
            top = np.argmax(solid, axis=2)
            ids = [g.idx[x, y, top[x, y]] for x in range(b[0] - half, b[0] + half + 1, 4)
                   for y in range(b[1] - half, b[1] + half + 1, 4)]
            return np.array([i for i in ids if i >= 0], int)
    else:
        def spawn_src(g, b):
            return g.nodes_in(b[0] - half, b[0] + half, b[1] - half, b[1] + half, 0, 62)
    routes, dsafe, dany = {}, {}, {}
    tz_default = {'blue': (x0 - 38, x0 + 5), 'red': (x1 - 5, x1 + 38)}
    for k, (name, b) in enumerate(zip(names, P['bases'])):
        other = P['bases'][1 - k]
        d = nav.dist_from(spawn_src(nav, b))
        da = nav_any.dist_from(spawn_src(nav_any, b))
        dsafe[name], dany[name] = d, da
        own_end = (x0, x0 + 5) if k == 0 else (x1 - 5, x1)
        r = {'to_own_platform_end': _dmin(d, nav.nodes_in(own_end[0], own_end[1], y0, y1, *end_z)),
             'to_enemy_spawn': _dmin(d, nav.nodes_in(other[0] - half, other[0] + half, other[1] - half,
                                                     other[1] + half, 0, 62)),
             'to_enemy_spawn_any_drop': _dmin(da, nav_any.nodes_in(other[0] - half, other[0] + half,
                                                                   other[1] - half, other[1] + half, 0, 62)),
             'reachable_nodes_pct': round(100 * float(np.isfinite(d).mean()), 1),
             'reachable_nodes_safe': int(np.isfinite(d).sum()), 'reachable_nodes_any': int(np.isfinite(da).sum())}
        for tname, box in (targets or {}).items():      # box, or {'blue': box, 'red': box} for per-team targets
            bx = box[name] if isinstance(box, dict) else box
            r['to_' + tname] = _dmin(d, nav.nodes_in(*bx[:6]))
        # safe descent: own tower zone reached with drops <= 9 only
        tzx = tuple((tower_zone or tz_default)[name]) + (0, 62)        # (x0, x1[, z0, z1])
        tzn = nav.nodes_in(tzx[0], tzx[1], y0, y1 + 1, tzx[2], tzx[3])
        r['safe_descent_to_tower_zone'] = _dmin(d, tzn) is not None
        r['tower_zone_min_cost'] = _dmin(d, tzn)
        routes[name] = r
    R['routes'] = routes

    # safe descent to the rest of the map: of all survivable-reachable ground nodes, the share also reachable safely
    p = nav.xyz
    top = np.argmax(solid, axis=2)
    ground = p[:, 2] == top[p[:, 0], p[:, 1]]
    pa = nav_any.xyz
    ground_a = pa[:, 2] == top[pa[:, 0], pa[:, 1]]
    desc = {}
    for name in names:
        safe_xy = {tuple(v) for v in p[ground & np.isfinite(dsafe[name]), :2].tolist()}
        any_xy = pa[ground_a & np.isfinite(dany[name]), :2]
        n_any = len(any_xy)
        n_both = sum(1 for v in any_xy.tolist() if tuple(v) in safe_xy)
        desc[name] = {'ground_cols_reachable_any': n_any, 'ground_cols_reachable_safe': n_both,
                      'safe_share_pct': round(100 * n_both / max(n_any, 1), 1)}
    R['safe_descent'] = desc

    # periphery: share of ground-top columns (dry) reachable by either team without building
    gcol = ground & (p[:, 2] < 62)
    reach = np.isfinite(dsafe[names[0]]) | np.isfinite(dsafe[names[1]])
    R['periphery'] = {'ground_cols': int(gcol.sum()), 'reachable_pct': round(100 * float(reach[gcol].mean()), 1)}

    # traps: standable cells reached from a spawn that cannot walk back to the anchor set
    if trap_anchor is None:
        trap_anchor = (min(b[0] for b in P['bases']) - half, max(b[0] for b in P['bases']) + half,
                       y0 - 40, y1 + 40, 0, 62)
    anchor_nodes = nav.nodes_in(*trap_anchor)[::trap_stride]
    dback = nav.dist_from(anchor_nodes, reverse=True)
    if terrain_H is not None:
        landish = np.abs(p[:, 2] - terrain_H[p[:, 0], p[:, 1]]) <= ground_band
    elif trap_z is not None:
        landish = (p[:, 2] >= trap_z[0]) & (p[:, 2] <= trap_z[1])
    else:
        landish = ground & (p[:, 2] < 62)
    fwd = np.isfinite(dsafe[names[0]]) | np.isfinite(dsafe[names[1]])
    trap = landish & (fwd if trap_z is None else True) & ~np.isfinite(dback)
    tp = p[trap]
    R['trap_cells'] = {'count': int(trap.sum()), 'of_cells': int(landish.sum()),
                       'sample': tp[::max(1, len(tp) // 25)][:25].tolist()}
    for nm, (za, zb) in (exits or {}).items():
        q = nav.nodes_in(0, 511, 0, 511, za, zb)
        R.setdefault('exits', {})[nm] = {'cells': int(len(q)), 'can_reach_anchor_pct':
                                         round(100 * float(np.isfinite(dback[q]).mean()), 1) if len(q) else None}

    # interiors
    ints = build.get('interiors') or []
    bad = []
    for (nm, x, y, z) in ints:
        cand = nav.nodes_in(x - 2, x + 2, y - 2, y + 2, z - 1, z + 1)
        ok_in = cand[np.isfinite(dsafe[names[0]][cand]) | np.isfinite(dsafe[names[1]][cand])] if len(cand) else cand
        if not (len(ok_in) and np.isfinite(dback[ok_in]).any()):
            bad.append({'name': nm, 'xyz': [x, y, z], 'standable_nodes_near': int(len(cand))})
    R['interiors'] = {'checked': len(ints), 'reachable_and_exit': len(ints) - len(bad), 'failures': bad}

    # flank routes: spawn -> enemy spawn with the centre band (|y-256| < flank_min within centre +-centre_half_x)
    # removed, separately north and south
    cx0, cx1 = 256 - centre_half_x, 256 + centre_half_x
    fl_res = {}
    for side, sgn in (('north', -1), ('south', 1)):
        dy = (p[:, 1] - 256) * sgn
        band = (p[:, 0] >= cx0) & (p[:, 0] <= cx1)
        allowed = np.nonzero(~band | ((dy >= flank_min) & (dy <= flank_max)))[0]
        d = nav.dist_from(spawn_src(nav, P['bases'][0]), allowed=allowed)
        o = P['bases'][1]
        fl_res[side] = _dmin(d, nav.nodes_in(o[0] - half, o[0] + half, o[1] - half, o[1] + half, 0, 62))
    R['flank'] = {'band': [flank_min, flank_max], 'blue_to_red_cost': fl_res,
                  'exists': any(v is not None for v in fl_res.values())}

    # build gap (hc definition) + per-structure assist gaps
    near = nav.nodes_in(x0 - build_gap_margin, x1 + build_gap_margin, y0 - build_gap_margin,
                        y1 + build_gap_margin, 0, 62)
    gaps = {}
    for name in names:
        if build_gap_graph == 'any':
            nr = nav_any.nodes_in(x0 - build_gap_margin, x1 + build_gap_margin, y0 - build_gap_margin,
                                  y1 + build_gap_margin, 0, 62)
            rch_xyz = nav_any.xyz[nr[np.isfinite(dany[name][nr])]]
        else:
            rch_xyz = p[near[np.isfinite(dsafe[name][near])]]
        zmin = int(rch_xyz[:, 2].min()) if len(rch_xyz) else None
        gaps[name] = {'graph': build_gap_graph, 'margin': build_gap_margin, 'highest_reachable_near_platform_z': zmin,
                      'blocks_to_build_up_to_platform_level': (zmin - (pz + 1)) if zmin is not None else None,
                      'platform_reachable_on_foot': bool(zmin is not None and zmin <= pz + 2)}
    R['build_gap'] = gaps
    if assist:
        ag = {}
        for sname, box in assist.items():
            nodes = nav.nodes_in(*box[:4], 0, 62)
            row = {}
            for name in names:
                rch = nodes[np.isfinite(dsafe[name][nodes])]
                zmin = int(p[rch][:, 2].min()) if len(rch) else None
                row[name] = {'top_reachable_z': zmin, 'gap_to_platform': (zmin - (pz + 1)) if zmin is not None else None}
            ag[sname] = row
        R['assist_structures'] = ag

    R['anchors'] = anchor_checks(solid, nav, P, anchor_face, axis)
    R['spawn_exposure'] = {name: spawn_exposure(solid, b, P, exposure_preset) for name, b in zip(names, P['bases'])}
    if zone_profile:
        # report-only zone metrics (aosmap.kit.zones, docs/babel_zone_study.md); no pass/fail yet
        from . import zones
        zp = zones.zone_profile(solid, P, nav=nav if rules == 'hc' else None)
        zp['class'] = zones.classify(zp)
        R['zone_profile'] = zp
    if zone_rules:
        # adopted zone rules (AGENTS.md §4, 2026-11-13); thresholds in params.ZONE_RULES, overridable with a dict.
        # Declared exemptions: build['front_exempt_boxes']; declared skips: zone_rules_skip or build['zone_rules_skip']
        from . import zones
        R['zone_rules'] = zones.zone_rules(
            solid, P, overrides=zone_rules if isinstance(zone_rules, dict) else None, terrain_H=terrain_H,
            front_exempt_boxes=build.get('front_exempt_boxes'),
            skip=zone_rules_skip if zone_rules_skip is not None else build.get('zone_rules_skip'))
    if timing:
        R['check_seconds'] = round(time.time() - t0, 1)
    return R


FIXED_ROW_KEYS = ('parser', 'pyspades', 'floating', 'mirror', 'platform_volume', 'platform_ends', 'spawn_squares',
                  'safe_descent', 'enemy_spawn', 'traps', 'interiors', 'flank', 'platform_on_foot', 'anchor_face')


def row_keys(params=BABEL_DEFAULT):
    """Every summary row key (the names a declared waiver may use)."""
    from .zones import RULE_KEYS
    return list(FIXED_ROW_KEYS) + [f'spawn_exposure_{t}' for t in params['team_names']] + list(RULE_KEYS)


def summary(R):
    """One pass/fail line per rule (owner targets). Each row has a 'key'. A row named in R['waivers'] (declared in
    build.json 'waivers' or run_all(waivers=)) gets status 'waived', keeps its measured detail plus the reason, and
    counts as ok; only explicitly named rows are waived."""
    rows = []

    def add(key, rule, ok, detail):
        rows.append({'rule': rule, 'ok': bool(ok), 'detail': detail, 'key': key})
    add('parser', 'parser', R['reader']['reencode_identical'] and R['reader']['z63_solid'], R['reader'])
    if 'pyspades' in R:
        add('pyspades', 'pyspades', R['pyspades']['generate_identical'] or (R['pyspades']['solid_mismatch_20k'] == 0 and
                                                                R['pyspades']['colour_mismatch_20k'] == 0),
            R['pyspades'])
    add('floating', 'no unintended floating', R['floating_components']['count'] == 0, R['floating_components']['count'])
    add('mirror', 'mirror', R['mirror']['solid_mismatch'] == 0, R['mirror']['solid_mismatch'])
    add('platform_volume', 'platform volume clear', R['platform_volume_voxels'] == 0, R['platform_volume_voxels'])
    ends = R['ground_under_platform_ends']
    add('platform_ends', 'ground under both platform ends', all(v['water_cols'] == 0 for v in ends.values()), ends)
    sq = R['spawn_squares']
    add('spawn_squares', 'spawn squares: no water / roofs', all(sq[t]['water_cols'] == 0 and sq[t]['roof_cols'] == 0
                                               for t in ('blue', 'red')), {t: sq[t] for t in ('blue', 'red')})
    add('safe_descent', 'safe descent to tower zone', all(v['safe_descent_to_tower_zone'] for v in R['routes'].values()),
        {k: v['tower_zone_min_cost'] for k, v in R['routes'].items()})
    add('enemy_spawn', 'enemy spawn reachable on foot', all(v['to_enemy_spawn'] is not None for v in R['routes'].values()),
        {k: v['to_enemy_spawn'] for k, v in R['routes'].items()})
    add('traps', 'no trap cells', R['trap_cells']['count'] == 0, R['trap_cells']['count'])
    add('interiors', 'interiors reachable', not R['interiors']['failures'], R['interiors']['checked'])
    add('flank', 'flank route exists', R['flank']['exists'], R['flank']['blue_to_red_cost'])
    add('platform_on_foot', 'platform not reachable on foot', not any(v['platform_reachable_on_foot'] for v in R['build_gap'].values()),
        {k: v['blocks_to_build_up_to_platform_level'] for k, v in R['build_gap'].items()})
    add('anchor_face', 'no walk-on steps on the enemy face of the anchors',
        all(not v['raised'] or v.get('enemy_face_walk_on_rows', 0) == 0 for v in R['anchors'].values()),
        R['anchors'])
    for t, e in R['spawn_exposure'].items():
        add(f'spawn_exposure_{t}', f'spawn exposure {t} (<= 10 viewers, >= 15 % hidden)', e['targets_met'],
            {'mean': e['viewers_per_spot_mean'], 'hidden_pct': e['hidden_pct']})
    if 'zone_rules' in R:
        from .zones import RULE_KEYS, RULE_TITLES
        Z = R['zone_rules']
        for k in RULE_KEYS:
            z = Z[k]
            # 'n.a.' and 'skipped' rows are not failures (ok=True) but keep their status for printing
            rows.append({'key': k, 'rule': RULE_TITLES[k], 'ok': z['status'] != 'fail', 'status': z['status'],
                         'detail': {'why': z['why'], 'avg': z.get('avg'), 'values': z['values'],
                                    'object_ground': Z['object_ground'],
                                    **({'front_exempt': Z['front_exempt']} if k == 'front_dressing' else {})}})
    wv = R.get('waivers') or {}
    for row in rows:
        if row['key'] in wv:
            row['measured_ok'] = row['ok']
            row['measured_status'] = row.get('status')
            row['status'] = 'waived'
            row['ok'] = True
            row['waiver'] = wv[row['key']]
    return rows


def format_row(row):
    """One printable line per summary row; zone rows carry a status (PASS / FAIL / N/A / SKIP) and, unless they
    pass, the reason on a second line (which number failed and by how much)."""
    st = row.get('status')
    if st is None:
        return ('PASS ' if row['ok'] else 'FAIL ') + row['rule']
    if st == 'waived':
        return ('WAIVED ' + row['rule'] + '  measured: ' + ('pass' if row['measured_ok'] else 'fail') + ' ' +
                json.dumps(row['detail'], default=str)[:300] + '\n      waiver: ' + row['waiver'])
    tag = {'pass': 'PASS ', 'fail': 'FAIL ', 'n.a.': 'N/A  ', 'skipped': 'SKIP '}[st]
    return tag + row['rule'] + ('' if st == 'pass' else '\n      ' + row['detail']['why'])


def _load_dir(d):
    vx = sorted(glob.glob(os.path.join(d, '*.vxl')))
    if len(vx) != 1:
        raise SystemExit(f'expected exactly one .vxl in {d}, found {len(vx)}')
    data = open(vx[0], 'rb').read()
    build = json.load(open(os.path.join(d, 'build.json'))) if os.path.exists(os.path.join(d, 'build.json')) else {}
    mat = np.load(os.path.join(d, 'mat.npy')) if os.path.exists(os.path.join(d, 'mat.npy')) else None
    H = np.load(os.path.join(d, 'terrain_H.npy')) if os.path.exists(os.path.join(d, 'terrain_H.npy')) else None
    return vx[0], data, build, mat, H


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('mapdir')
    ap.add_argument('--out', help='where to write validation.json (default: print only)')
    ap.add_argument('--rules', default='hc', choices=('hc', 'bloomhop'))
    ap.add_argument('--exposure', default='calibrated', choices=tuple(EXPOSURE_PRESETS))
    ap.add_argument('--axis', default=None, choices=AXES, help="default: build.json 'axis', else x512")
    ap.add_argument('--no-pyspades', action='store_true')
    ap.add_argument('--targets', help='JSON file: {"name": [x0, x1, y0, y1, z0, z1], ...} extra route targets')
    a = ap.parse_args(argv)
    path, data, build, mat, H = _load_dir(a.mapdir)
    targets = json.load(open(a.targets)) if a.targets else build.get('check_targets')
    axis = a.axis or build.get('axis') or 'x512'
    R = run_all(data, build=build, mat=mat, terrain_H=H, axis=axis, exposure_preset=a.exposure, rules=a.rules,
                pyspades=not a.no_pyspades, targets=targets)
    R['map'] = os.path.basename(path)
    R['summary'] = summary(R)
    if a.out:
        with open(a.out, 'w') as f:
            json.dump(R, f, indent=1, default=str)
    for row in R['summary']:
        print(format_row(row))
    return R


if __name__ == '__main__':
    main()
