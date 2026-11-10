"""Frostbell Hollow checks the kit lacks (docs/frostbell_hollow_spec.md "Checks to pass before the art pass").

    python scenes/frostbell_hollow/fh_checks.py out/frostbell_hollow

1. front openness per north-south section (x 152-199 and mirror, y 232-280, walking height) + prop heights
2. gatehouse open share across y 232-280 and widest pier
3. tunnel exclusion: no air below the surface in x 150-215, y 232-280 (and mirror)
4. flank routes restricted to the north / south flank bands, both teams, lengths within 10 %
5. nothing solid at z <= 6; nothing at z <= 2 over the platform footprint + margin
6. underground: every entrance connected to the network; network reachable from both spawns and walk-out
7. (extra) spawn no-prop margin and anchors free of anything above the terrain

Graph model = aosmap.kit.babel_checks.Nav (3 air to stand, 1-voxel step with 4 climb room, drops <= 9).
"""
from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from aosmap.kit import codec  # noqa: E402
from aosmap.kit.babel_checks import Nav, _dmin  # noqa: E402
from aosmap.kit.symmetry import mirror_index  # noqa: E402

from fh_spec import SPEC  # noqa: E402


def _walk_blocked(solid, H, x, y):
    h = int(H[x, y])
    return bool(solid[x, y, max(0, h - 3):h].any())


def front_openness(solid, H, S=SPEC):
    fc = S['front_check']
    y0, y1 = fc['y']
    out = {}
    for side, xs in (('west', range(fc['x'][0], fc['x'][1] + 1)),
                     ('east', [mirror_index(x) for x in range(fc['x'][0], fc['x'][1] + 1)])):
        shares = {}
        for x in xs:
            free = sum(1 for y in range(y0, y1 + 1) if not _walk_blocked(solid, H, x, y))
            shares[x] = free / float(y1 - y0 + 1)
        xm = min(shares, key=shares.get)
        out[side] = {'min_free_share': round(shares[xm], 3), 'worst_x': int(xm),
                     'mean_free_share': round(float(np.mean(list(shares.values()))), 3)}
    # prop heights over the band (both sides)
    top = np.argmax(solid, axis=2)
    hts = []
    for x in list(range(fc['x'][0], fc['x'][1] + 1)) + [mirror_index(x) for x in range(fc['x'][0], fc['x'][1] + 1)]:
        for y in range(y0, y1 + 1):
            hts.append(int(H[x, y]) - int(top[x, y]))
    hts = np.array(hts)
    out['max_prop_height'] = int(hts.max())
    out['columns_over_5'] = int((hts > S['front']['max_prop_h']).sum())          # lantern posts only (6 tall)
    out['columns_over_6'] = int((hts > S['front']['lantern_h']).sum())
    out['ok'] = (min(out['west']['min_free_share'], out['east']['min_free_share']) >= S['front']['min_free'] and
                 out['columns_over_6'] == 0 and out['columns_over_5'] <= 4)
    return out


def gatehouse_open(solid, H, S=SPEC):
    gh, gc = S['gatehouse'], S['gatehouse_check']
    y0, y1 = gc['y']
    out = {}
    for side, xs in (('west', range(gh['x'][0], gh['x'][1] + 1)),
                     ('east', [mirror_index(x) for x in range(gh['x'][0], gh['x'][1] + 1)])):
        open_rows = [all(not _walk_blocked(solid, H, x, y) for x in xs) for y in range(y0, y1 + 1)]
        run = best = 0
        for o in open_rows:
            run = 0 if o else run + 1
            best = max(best, run)
        out[side] = {'open_share': round(sum(open_rows) / float(len(open_rows)), 3), 'widest_pier': best}
    out['ok'] = all(out[s]['open_share'] >= gc['min_open'] and out[s]['widest_pier'] <= gc['max_pier']
                    for s in ('west', 'east'))
    return out


def tunnel_exclusion(solid, H, S=SPEC):
    te = S['tunnel_exclusion']
    out = {}
    for side, (xa, xb) in (('west', te['x']), ('east', tuple(sorted(mirror_index(x) for x in te['x'])))):
        n = 0
        for x in range(xa, xb + 1):
            for y in range(te['y'][0], te['y'][1] + 1):
                h = int(H[x, y])
                n += int((~solid[x, y, h:64]).sum())
        out[side] = {'box': [xa, xb] + list(te['y']), 'air_below_surface': n}
    out['ok'] = all(out[s]['air_below_surface'] == 0 for s in ('west', 'east'))
    return out


def sky_ceiling(solid, S=SPEC):
    pc = S['platform_clear']
    n6 = int(solid[:, :, :S['z']['min_solid_z']].sum())
    n2 = int(solid[pc['x'][0]:pc['x'][1] + 1, pc['y'][0]:pc['y'][1] + 1, :pc['z_max'] + 1].sum())
    return {'solid_z_le_6': n6, 'solid_z_le_2_over_platform_margin': n2, 'top_solid_z': int(np.argmax(
        solid.reshape(-1, 64).any(0))), 'ok': n6 == 0 and n2 == 0}


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
    out['ok'] = all(v == 0 for k, v in out.items() if k not in ('anchor_flat',)) and out['anchor_flat']
    return out


def flank_routes(nav, S=SPEC):
    fb = S['flank_bands']
    sp = S['spawn']
    h = sp['half']
    bases = [sp['base'], (mirror_index(sp['base'][0]), sp['base'][1])]
    p = nav.xyz
    rx0, rx1 = fb['restrict_x']
    res = {}
    for k, name in enumerate(('blue', 'red')):
        b, o = bases[k], bases[1 - k]
        src = nav.nodes_in(b[0] - h, b[0] + h, b[1] - h, b[1] + h, 0, 62)
        dst = nav.nodes_in(o[0] - h, o[0] + h, o[1] - h, o[1] + h, 0, 62)
        row = {}
        for side in ('north', 'south'):
            ya, yb = fb[side]
            inside = (p[:, 0] >= rx0) & (p[:, 0] <= rx1)
            allowed = np.nonzero(~inside | ((p[:, 1] >= ya) & (p[:, 1] <= yb)))[0]
            d = nav.dist_from(src, allowed=allowed)
            row[side] = _dmin(d, dst)
        n, s_ = row['north'], row['south']
        row['diff_share'] = round(abs(n - s_) / max(n, s_), 3) if n and s_ else None
        res[name] = row
    res['ok'] = all(res[t]['north'] is not None and res[t]['south'] is not None and
                    res[t]['diff_share'] <= fb['max_diff'] for t in ('blue', 'red'))
    return res


def underground(nav, solid, H, S=SPEC):
    fz = S['z']['underground_floor']
    sp = S['spawn']
    h = sp['half']
    bases = [sp['base'], (mirror_index(sp['base'][0]), sp['base'][1])]
    p = nav.xyz
    covered = solid[p[:, 0], p[:, 1], 40:fz - 4].any(axis=1) if len(p) else np.zeros(0, bool)
    U = np.nonzero((p[:, 2] == fz) & covered & (H[p[:, 0], p[:, 1]] < fz - 4))[0]
    srcs = [nav.nodes_in(b[0] - h, b[0] + h, b[1] - h, b[1] + h, 0, 62) for b in bases]
    d_b = nav.dist_from(srcs[0])
    d_r = nav.dist_from(srcs[1])
    back = nav.dist_from(np.concatenate(srcs), reverse=True)
    out = {'network_cells': int(len(U)),
           'reachable_from_blue_pct': round(100 * float(np.isfinite(d_b[U]).mean()), 1) if len(U) else None,
           'reachable_from_red_pct': round(100 * float(np.isfinite(d_r[U]).mean()), 1) if len(U) else None,
           'walk_out_to_a_spawn_pct': round(100 * float(np.isfinite(back[U]).mean()), 1) if len(U) else None}
    # entrances: (name, stair box x0, x1, y0, y1, top box z range); west boxes, east = mirror
    ent = [('mine adit', (51, 62, 207, 211), (60, 62, 46, 50)),
           ('cellar house stair', (65, 77, 296, 297), (74, 77, 46, 50)),
           ('hatch N', (188, 190, 168, 178), (176, 178, 49, 51)),
           ('hatch S', (188, 190, 332, 342), (332, 334, 49, 51)),
           ('tavern cellar stair', (248, 250, 145, 155), (145, 147, 49, 51))]
    rows = []
    Uset = U
    for name, (x0, x1, y0, y1), (ta, tb, za, zb) in ent:
        for side in ('W', 'E'):
            if side == 'W':
                xa, xb = x0, x1
            else:
                xa, xb = sorted((mirror_index(x0), mirror_index(x1)))
            stair = nav.nodes_in(xa, xb, y0, y1, 40, 62)
            if name in ('mine adit', 'cellar house stair'):
                if side == 'W':
                    top = nav.nodes_in(ta, tb, y0, y1, za, zb)
                else:
                    a_, b_ = sorted((mirror_index(ta), mirror_index(tb)))
                    top = nav.nodes_in(a_, b_, y0, y1, za, zb)
            else:
                top = nav.nodes_in(xa, xb, ta, tb, za, zb)
            allowed = np.unique(np.concatenate([Uset, stair, top]))
            dn = nav.dist_from(top, allowed=allowed)
            up = nav.dist_from(top, reverse=True, allowed=allowed)
            rows.append({'entrance': f'{name} ({side})', 'top_cells': int(len(top)),
                         'down_to_network': bool(len(Uset) and np.isfinite(dn[Uset]).any()),
                         'up_from_network': bool(len(Uset) and np.isfinite(up[Uset]).any()),
                         'top_reachable_both_spawns': bool(len(top) and np.isfinite(d_b[top]).any() and
                                                           np.isfinite(d_r[top]).any())})
    out['entrances'] = rows
    out['ok'] = (len(U) > 0 and out['reachable_from_blue_pct'] == 100.0 and out['reachable_from_red_pct'] == 100.0
                 and out['walk_out_to_a_spawn_pct'] == 100.0 and
                 all(r['down_to_network'] and r['up_from_network'] and r['top_reachable_both_spawns'] for r in rows))
    return out


def run(solid, H, S=SPEC, nav=None):
    nav = nav or Nav(solid)
    R = {'front': front_openness(solid, H, S), 'gatehouse': gatehouse_open(solid, H, S),
         'tunnel_exclusion': tunnel_exclusion(solid, H, S), 'flank_bands': flank_routes(nav, S),
         'sky_ceiling': sky_ceiling(solid, S), 'prop_free_zones': prop_free(solid, H, S),
         'underground': underground(nav, solid, H, S)}
    return R


def summary(R):
    f, g = R['front'], R['gatehouse']
    fl = R['flank_bands']
    u = R['underground']
    return [
        {'rule': 'front open (every N-S section >= 70 % free, props <= 5, lanterns <= 6)', 'ok': f['ok'],
         'detail': {'min_free': min(f['west']['min_free_share'], f['east']['min_free_share']),
                    'max_prop_height': f['max_prop_height'], 'columns_over_5': f['columns_over_5']}},
        {'rule': 'gatehouse >= 60 % open, piers <= 5', 'ok': g['ok'], 'detail': {k: g[k] for k in ('west', 'east')}},
        {'rule': 'no tunnel under the tower corridor', 'ok': R['tunnel_exclusion']['ok'],
         'detail': {k: R['tunnel_exclusion'][k]['air_below_surface'] for k in ('west', 'east')}},
        {'rule': 'flank routes N and S both teams, within 10 %', 'ok': fl['ok'],
         'detail': {t: fl[t] for t in ('blue', 'red')}},
        {'rule': 'nothing at z <= 6; platform volume + margin clear', 'ok': R['sky_ceiling']['ok'],
         'detail': R['sky_ceiling']},
        {'rule': 'spawn margins + anchors prop-free, anchors flat', 'ok': R['prop_free_zones']['ok'],
         'detail': R['prop_free_zones']},
        {'rule': 'underground connected, reachable from both spawns, walk-out', 'ok': u['ok'],
         'detail': {k: u[k] for k in ('network_cells', 'reachable_from_blue_pct', 'reachable_from_red_pct',
                                      'walk_out_to_a_spawn_pct')}},
    ]


if __name__ == '__main__':
    d = sys.argv[1]
    data = open(glob.glob(os.path.join(d, '*.vxl'))[0], 'rb').read()
    solid, _, _ = codec.decode(data)
    H = np.load(os.path.join(d, 'terrain_H.npy')).astype(int)
    R = run(solid, H)
    R['summary'] = summary(R)
    print(json.dumps(R, indent=1, default=str))
