"""Elderveil checks the kit lacks (docs/elderveil_spec.md).

    python scenes/elderveil/ev_checks.py out/elderveil

1. front openness per north-south section (x 139-211 and mirror, y 236-276, walking height) >= 70 % free;
   front pieces <= 5 tall (x 139-199)
2. nothing solid at z <= 6; nothing at z <= 3 over the platform footprint + margin (x 200-311, y 234-277)
3. spawn no-prop margins and the anchors free of anything above the terrain; anchors flat
4. flank routes restricted to the north / south flank bands, both teams, lengths within 10 %
5. largest featureless flat patch (same metric as Frostbell): <= 24 outside the exempt zones
6. central gaps: smallest gap (Chebyshev) between room-sized structures (>= 25 cells, no vegetation) in the
   central zone x 150-362, y 130-382; target >= 7
7. assist spires: highest reachable point, build gap, closest horizontal / vertical distance to the platform,
   route length from each spawn, safe way back down; spires outside the front band, the strip and the corridor
8. normal tower build gap: highest reachable point near the platform with the assist spires left out
9. spire-top perch (report only): how many spawn spots a player standing on each spire top can see
10. safe descent from every recorded high floor (z <= 45): a safe-graph path back to the anchor set

Graph model = aosmap.kit.babel_checks.Nav (3 air to stand, 1-voxel step with 4 climb room, drops <= 9).
"""
from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from aosmap.kit import codec  # noqa: E402
from aosmap.kit.babel_checks import Nav, _dmin  # noqa: E402
from aosmap.kit.params import BABEL_DEFAULT as P  # noqa: E402
from aosmap.kit.symmetry import mirror_index  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ev_spec import SPEC  # noqa: E402


def _walk_blocked(solid, H, x, y):
    h = int(H[x, y])
    return bool(solid[x, y, max(0, h - 3):h].any())


def front_openness(solid, H, S=SPEC):
    f = S['front']
    y0, y1 = f['y']
    xa, xb = 139, 211
    out = {}
    for side, xs in (('west', range(xa, xb + 1)), ('east', [mirror_index(x) for x in range(xa, xb + 1)])):
        shares = {}
        for x in xs:
            free = sum(1 for y in range(y0, y1 + 1) if not _walk_blocked(solid, H, x, y))
            shares[x] = free / float(y1 - y0 + 1)
        xm = min(shares, key=shares.get)
        out[side] = {'min_free_share': round(shares[xm], 3), 'worst_x': int(xm),
                     'mean_free_share': round(float(np.mean(list(shares.values()))), 3)}
    top = np.argmax(solid, axis=2)
    hts = []
    for x in list(range(f['x'][0], f['x'][1] + 1)) + [mirror_index(x) for x in range(f['x'][0], f['x'][1] + 1)]:
        for y in range(y0, y1 + 1):
            hts.append(int(H[x, y]) - int(top[x, y]))
    hts = np.array(hts)
    out['max_piece_height'] = int(hts.max())
    out['ok'] = (min(out['west']['min_free_share'], out['east']['min_free_share']) >= f['min_free'] and
                 out['max_piece_height'] <= f['max_prop_h'])
    return out


def sky_ceiling(solid, S=SPEC):
    pc = S['platform_clear']
    n6 = int(solid[:, :, :S['z']['min_solid_z']].sum())
    n3 = int(solid[pc['x'][0]:pc['x'][1] + 1, pc['y'][0]:pc['y'][1] + 1, :pc['z_max'] + 1].sum())
    return {'solid_z_le_6': n6, 'solid_z_le_3_over_platform_margin': n3,
            'top_solid_z': int(np.argmax(solid.reshape(-1, 64).any(0))), 'ok': n6 == 0 and n3 == 0}


def prop_free(solid, H, S=SPEC):
    sp = S['spawn']
    h, m = sp['half'], sp['margin']
    out = {}
    boxes = {}
    for k, (bx, by) in enumerate([sp['base'], (mirror_index(sp['base'][0]), sp['base'][1])]):
        boxes[f'spawn margin {k}'] = (bx - h - m, bx + h + m, by - h - m, by + h + m)
    a = S['anchor']
    boxes['anchor W'] = a['x'] + a['y']
    boxes['anchor E'] = tuple(sorted(mirror_index(x) for x in a['x'])) + a['y']
    for nm, (x0, x1, y0, y1) in boxes.items():
        n = 0
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                n += int(solid[x, y, :int(H[x, y])].sum())
        out[nm] = n
    out['anchor_flat'] = all(len(np.unique(H[bx0:bx1 + 1, a['y'][0]:a['y'][1] + 1])) == 1
                             for (bx0, bx1) in (a['x'], tuple(sorted(mirror_index(x) for x in a['x']))))
    out['ok'] = all(v == 0 for k, v in out.items() if k != 'anchor_flat') and out['anchor_flat']
    return out


def _spawn_nodes(nav, b, h=None):
    h = P['spawn_half'] if h is None else h
    return nav.nodes_in(b[0] - h, b[0] + h, b[1] - h, b[1] + h, 0, 62)


def flank_routes(nav, S=SPEC):
    fb = S['flank_bands']
    p = nav.xyz
    rx0, rx1 = fb['restrict_x']
    res = {}
    for k, name in enumerate(P['team_names']):
        b, o = P['bases'][k], P['bases'][1 - k]
        src, dst = _spawn_nodes(nav, b), _spawn_nodes(nav, o)
        row = {}
        for side in ('north', 'south'):
            ya, yb = fb[side]
            inside = (p[:, 0] >= rx0) & (p[:, 0] <= rx1)
            allowed = np.nonzero(~inside | ((p[:, 1] >= ya) & (p[:, 1] <= yb)))[0]
            row[side] = _dmin(nav.dist_from(src, allowed=allowed), dst)
        n, s_ = row['north'], row['south']
        row['diff_share'] = round(abs(n - s_) / max(n, s_), 3) if n and s_ else None
        res[name] = row
    res['ok'] = all(res[t]['north'] is not None and res[t]['south'] is not None and
                    res[t]['diff_share'] <= fb['max_diff'] for t in P['team_names'])
    return res


def largest_flat_squares(H, ok, min_report=16, n_report=6, sep=24):
    """Largest squares of same-height columns where ok is True (DP over the grid). Returns (best, corner, tops)."""
    Hl = H.tolist()
    okl = ok.tolist()
    prev = [0] * 512
    best, where = 0, None
    cand = []
    for x in range(512):
        cur = [0] * 512
        hx, hp, ox = Hl[x], Hl[x - 1] if x else None, okl[x]
        for y in range(512):
            if not ox[y]:
                continue
            v = 1
            if x and y and hx[y - 1] == hx[y] and hp[y] == hx[y] and hp[y - 1] == hx[y]:
                v = 1 + min(prev[y], cur[y - 1], prev[y - 1])
            cur[y] = v
            if v >= min_report:
                cand.append((v, x, y))
            if v > best:
                best, where = v, (x - v + 1, y - v + 1)
        prev = cur
    cand.sort(reverse=True)
    tops = []
    for v, x, y in cand:
        if all(max(abs(x - a), abs(y - b)) > sep for (_, a, b) in tops):
            tops.append((v, x, y))
        if len(tops) >= n_report:
            break
    return best, where, tops


def featureless_ok_mask(solid, H, S=SPEC):
    top = np.argmax(solid, axis=2)
    ok = (top >= H) & (H < 62)
    for (x0, x1, y0, y1) in S['featureless']['exempt']:
        ok[x0:x1 + 1, y0:y1 + 1] = False
    return ok


def featureless(solid, H, S=SPEC):
    fe = S['featureless']
    best, where, tops = largest_flat_squares(H, featureless_ok_mask(solid, H, S))
    return {'largest_side': best, 'at_xy_min_corner': where, 'z': int(H[where]) if where else None,
            'largest_patches': [{'side': v, 'x': [x - v + 1, x], 'y': [y - v + 1, y]} for v, x, y in tops],
            'max_allowed': fe['max_side'], 'ok': best <= fe['max_side']}


VEG = {'veg', 'canopy', 'trunk', 'fern'}
NATURAL = VEG | {'mound', 'rock', 'pad', 'rubble', 'mushroom'}


def central_gaps(solid, H, mat, names, S=SPEC):
    """Room-sized structures (>= 25 columns, >= 2 above the terrain; plants, moss mounds, rocks, rubble and
    feature pads left out) whose footprint centre lies in the central zone; smallest Chebyshev gap (free columns
    between the two footprints) between any two of them."""
    from aosmap.kit.params import ZONE_RULES
    cx0, cx1, cy0, cy1 = ZONE_RULES['centre']['box']
    zz = np.arange(64)[None, None, :]
    above = solid & (zz <= H[:, :, None] - 2)
    if mat is not None and names:
        vid = [v for k, v in names.items() if k in NATURAL]
        above &= ~np.isin(mat, vid)
    col = above.any(2)
    lab0 = col.copy()
    for (a0, a1, b0, b1) in S['central_gap'].get('composites', []):        # one structure each
        sub = col[a0:a1 + 1, b0:b1 + 1]
        if sub.any():
            xs, ys = np.nonzero(sub)
            lab0[a0 + xs.min():a0 + xs.max() + 1, b0 + ys.min():b0 + ys.max() + 1] = True
    lab, n = ndi.label(lab0, structure=np.ones((3, 3)))
    lab[~col] = 0
    sizes = np.bincount(lab.ravel(), minlength=n + 1)
    cen = ndi.center_of_mass(col, lab, np.arange(1, n + 1)) if n else []
    ids = [i for i in range(1, n + 1) if sizes[i] >= 25 and cx0 <= cen[i - 1][0] <= cx1 and
           cy0 <= cen[i - 1][1] <= cy1]
    rows = []
    for i in ids:
        m = lab == i
        d = ndi.distance_transform_cdt(~m, metric='chessboard')
        xs, ys = np.nonzero(m)
        bb = [int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())]
        for j in ids:
            if j <= i:
                continue
            g = int(d[lab == j].min()) - 1
            xj, yj = np.nonzero(lab == j)
            rows.append((g, bb, [int(xj.min()), int(xj.max()), int(yj.min()), int(yj.max())]))
    rows.sort(key=lambda r: r[0])
    under7 = [r for r in rows if r[0] < S['central_gap']['min']]
    return {'structures': len(ids), 'min_gap': rows[0][0] if rows else None,
            'pairs_under_7': len(under7), 'closest': [list(r) for r in rows[:6]],
            'ok': not under7}


def spires(nav, solid, S=SPEC, d_spawn=None, d_back=None):
    sp = S['spire']
    bx = sp['box']
    (px0, px1), (py0, py1), pz = P['platform_x'], P['platform_y'], P['platform_z']
    boxes = {'west spire': bx, 'east spire': (mirror_index(bx[1]), mirror_index(bx[0]), bx[2], bx[3])}
    p = nav.xyz
    out = {}
    for nm, (x0, x1, y0, y1) in boxes.items():
        nodes = nav.nodes_in(x0, x1, y0, y1, 0, 62)
        row = {'box': [x0, x1, y0, y1]}
        for t in P['team_names']:
            rch = nodes[np.isfinite(d_spawn[t][nodes])]
            if not len(rch):
                row[t] = None
                continue
            zt = int(p[rch][:, 2].min())
            topn = rch[p[rch][:, 2] == zt]
            row[t] = {'top_z': zt, 'route_len_from_spawn': float(d_spawn[t][topn].min()),
                      'top_cells': int(len(topn))}
        top = nodes[np.isfinite(d_spawn['blue'][nodes]) | np.isfinite(d_spawn['red'][nodes])]
        zt = int(p[top][:, 2].min())
        topn = top[p[top][:, 2] == zt]
        tx, ty = p[topn][:, 0], p[topn][:, 1]
        dx = np.maximum(np.maximum(px0 - tx, tx - px1), 0)
        dy = np.maximum(np.maximum(py0 - ty, ty - py1), 0)
        row['build_gap'] = zt - (pz + 1)
        row['closest_horizontal_to_platform'] = round(float(np.hypot(dx, dy).min()), 1)
        row['closest_dx_dy'] = [int(dx[np.argmin(np.hypot(dx, dy))]), int(dy[np.argmin(np.hypot(dx, dy))])]
        row['vertical_top_to_platform_floor'] = zt - pz
        row['safe_way_down'] = bool(np.isfinite(d_back[topn]).all())
        fb = (139, 211, 236, 276) if nm.startswith('west') else (300, 373, 236, 276)
        strip = (212, 300, 240, 271)
        corr = (128, 211, 240, 272) if nm.startswith('west') else (301, 384, 240, 272)

        def overlap(a, b):
            return not (a[1] < b[0] or a[0] > b[1] or a[3] < b[2] or a[2] > b[3])
        sol = solid[x0:x1 + 1, y0:y1 + 1]
        row['outside_front_band'] = not overlap((x0, x1, y0, y1), fb)
        row['outside_strip'] = not overlap((x0, x1, y0, y1), strip)
        row['outside_tower_corridor'] = not overlap((x0, x1, y0, y1), corr)
        row['solid_z_le_6_in_box'] = int(sol[:, :, :7].sum())
        row['ok'] = (8 <= row['build_gap'] <= 12 and row['blue'] is not None and row['red'] is not None and
                     row['safe_way_down'] and row['outside_front_band'] and row['outside_strip'] and
                     row['outside_tower_corridor'] and row['solid_z_le_6_in_box'] == 0)
        out[nm] = row
    out['ok'] = all(out[k]['ok'] for k in boxes)
    return out


def normal_build_gap(nav, d_spawn, S=SPEC, margin=24):
    """Highest reachable point within `margin` of the platform with the assist spire boxes left out."""
    (x0, x1), (y0, y1), pz = P['platform_x'], P['platform_y'], P['platform_z']
    bx = S['spire']['box']
    near = nav.nodes_in(x0 - margin, x1 + margin, y0 - margin, y1 + margin, 0, 62)
    p = nav.xyz
    ex = np.zeros(len(near), bool)
    for (a, b, c, d) in (bx, (mirror_index(bx[1]), mirror_index(bx[0]), bx[2], bx[3])):
        q = p[near]
        ex |= (q[:, 0] >= a) & (q[:, 0] <= b) & (q[:, 1] >= c) & (q[:, 1] <= d)
    near = near[~ex]
    out = {}
    for t in P['team_names']:
        r = near[np.isfinite(d_spawn[t][near])]
        zmin = int(p[r][:, 2].min())
        w = p[r][p[r][:, 2] == zmin][0].tolist()
        out[t] = {'highest_z': zmin, 'gap': zmin - (pz + 1), 'where': w}
    # the same restricted to the anchor ground + strip (where towers are usually built)
    an = nav.nodes_in(x0 - 6, x1 + 6, y0, y1, 0, 62)
    r = an[np.isfinite(d_spawn['blue'][an]) | np.isfinite(d_spawn['red'][an])]
    out['anchor_strip_highest_z'] = int(p[r][:, 2].min())
    out['anchor_strip_gap'] = out['anchor_strip_highest_z'] - (pz + 1)
    return out


def spire_perch(solid, nav, d_spawn, S=SPEC):
    """Report only: line of sight from eyes on each spire top (top cells, z - 2.4, every 2nd cell) to the spawn
    heads (2-voxel grid of each square, topmost voxel - 2.2)."""
    from aosmap.kit.zones import los_pairs
    bx = S['spire']['box']
    p = nav.xyz
    top = np.argmax(solid, axis=2)
    out = {}
    for nm, (x0, x1, y0, y1) in (('west spire', bx), ('east spire', (mirror_index(bx[1]), mirror_index(bx[0]),
                                                                   bx[2], bx[3]))):
        nodes = nav.nodes_in(x0, x1, y0, y1, 0, 62)
        rch = nodes[np.isfinite(d_spawn['blue'][nodes])]
        zt = p[rch][:, 2].min()
        tc = p[rch][p[rch][:, 2] == zt][::2]
        eyes = np.column_stack([tc[:, 0] + 0.5, tc[:, 1] + 0.5, tc[:, 2] - 2.4])
        row = {'eyes': int(len(eyes))}
        for t, b in zip(P['team_names'], P['bases']):
            h = P['spawn_half']
            heads = np.array([(x + 0.5, y + 0.5, top[x, y] - 2.2) for x in range(b[0] - h, b[0] + h + 1, 2)
                              for y in range(b[1] - h, b[1] + h + 1, 2)])
            A = np.repeat(eyes, len(heads), 0)
            B = np.tile(heads, (len(eyes), 1))
            vis = los_pairs(solid, A, B).reshape(len(eyes), len(heads))
            seen = vis.any(0)
            row[t] = {'spots_seen_pct': round(100 * float(seen.mean()), 1),
                      'mean_eyes_per_spot': round(float(vis.sum(0).mean()), 2)}
        out[nm] = row
    return out


def high_descent(nav, d_back, build, d_spawn):
    rows = []
    for (nm, x, y, z) in build.get('interiors') or []:
        if z > 45:
            continue
        cand = nav.nodes_in(x - 2, x + 2, y - 2, y + 2, z - 1, z + 1)
        reach = cand[np.isfinite(d_spawn['blue'][cand]) | np.isfinite(d_spawn['red'][cand])] if len(cand) else cand
        rows.append({'name': nm, 'z': z, 'reachable': bool(len(reach)),
                     'safe_back_down': bool(len(reach) and np.isfinite(d_back[reach]).any())})
    return {'high_floors': len(rows), 'failures': [r for r in rows if not (r['reachable'] and r['safe_back_down'])],
            'ok': all(r['reachable'] and r['safe_back_down'] for r in rows)}


def run(solid, H, S=SPEC, nav=None, build=None, mat=None, materials=None):
    nav = nav or Nav(solid)
    build = build or {}
    d_spawn = {t: nav.dist_from(_spawn_nodes(nav, b)) for t, b in zip(P['team_names'], P['bases'])}
    h = P['spawn_half']
    (x0, x1), (y0, y1) = P['platform_x'], P['platform_y']
    anc = nav.nodes_in(min(b[0] for b in P['bases']) - h, max(b[0] for b in P['bases']) + h, y0 - 40, y1 + 40,
                       0, 62)[::5]
    d_back = nav.dist_from(anc, reverse=True)
    R = {'front': front_openness(solid, H, S), 'sky_ceiling': sky_ceiling(solid, S),
         'prop_free_zones': prop_free(solid, H, S), 'flank_bands': flank_routes(nav, S),
         'featureless': featureless(solid, H, S),
         'central_gaps': central_gaps(solid, H, mat, materials, S),
         'spires': spires(nav, solid, S, d_spawn, d_back), 'normal_build_gap': normal_build_gap(nav, d_spawn, S),
         'spire_perch': spire_perch(solid, nav, d_spawn, S),
         'high_descent': high_descent(nav, d_back, build, d_spawn)}
    return R


def summary(R):
    f = R['front']
    fl = R['flank_bands']
    sp = R['spires']
    return [
        {'rule': 'front open (every N-S section x 139-211 >= 70 % free, pieces <= 5 tall)', 'ok': f['ok'],
         'detail': {'min_free': min(f['west']['min_free_share'], f['east']['min_free_share']),
                    'max_piece_height': f['max_piece_height']}},
        {'rule': 'nothing at z <= 6; platform footprint + margin clear to z 3', 'ok': R['sky_ceiling']['ok'],
         'detail': R['sky_ceiling']},
        {'rule': 'spawn margins + anchors prop-free, anchors flat', 'ok': R['prop_free_zones']['ok'],
         'detail': R['prop_free_zones']},
        {'rule': 'flank routes N and S both teams, within 10 %', 'ok': fl['ok'],
         'detail': {t: fl[t] for t in ('blue', 'red')}},
        {'rule': 'largest featureless flat patch <= 24', 'ok': R['featureless']['ok'],
         'detail': {k: R['featureless'][k] for k in ('largest_side', 'at_xy_min_corner')}},
        {'rule': 'central structures >= 7 apart', 'ok': R['central_gaps']['ok'],
         'detail': {k: R['central_gaps'][k] for k in ('structures', 'min_gap', 'pairs_under_7', 'closest')}},
        {'rule': 'assist spires: build gap 8-12, reachable by both teams, safe way down, outside band/strip/corridor',
         'ok': sp['ok'], 'detail': {k: {kk: v.get(kk) for kk in ('build_gap', 'closest_horizontal_to_platform',
                                                                'closest_dx_dy', 'vertical_top_to_platform_floor',
                                                                'blue', 'red', 'safe_way_down')}
                                    for k, v in sp.items() if k != 'ok'}},
        {'rule': 'safe way down from every high floor (z <= 45)', 'ok': R['high_descent']['ok'],
         'detail': {'high_floors': R['high_descent']['high_floors'], 'failures': R['high_descent']['failures'][:5]}},
        {'rule': 'normal tower build gap (spires left out) - report', 'ok': True, 'detail': R['normal_build_gap']},
        {'rule': 'spire-top perch view of the spawns - report', 'ok': True, 'detail': R['spire_perch']},
    ]


if __name__ == '__main__':
    d = sys.argv[1]
    data = open(glob.glob(os.path.join(d, '*.vxl'))[0], 'rb').read()
    solid, _, _ = codec.decode(data)
    H = np.load(os.path.join(d, 'terrain_H.npy')).astype(int)
    b = json.load(open(os.path.join(d, 'build.json')))
    R = run(solid, H, build=b, mat=np.load(os.path.join(d, 'mat.npy')), materials=b.get('materials'))
    R['summary'] = summary(R)
    print(json.dumps(R['summary'], indent=1, default=str))
