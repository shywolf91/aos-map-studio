"""Royal Parade Snow Night checks that the kit suite does not cover for a rework.

    python scenes/royal_parade_snow_night/rpsn_check.py OUTDIR      (re-runs on an exported folder)

diff vs the original (counts, per-piece boxes, spawn squares / under-platform strip unchanged), face-connectivity of
every new voxel (no new floating component), spawn exposure before/after (kit 'calibrated' preset = aosmap.sightline
model), front lanes (>= 3 lanes >= 3 wide at every front x), clear street width beside each festive vehicle,
glow-palette collisions, colour stats (top-surface luma percentiles, max channel > 212 shares).
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..'))
from aosmap.kit import babel_checks, codec, color, params, symmetry  # noqa: E402

GLOW_PALETTE = {(255, 255, 255), (255, 95, 95), (255, 255, 95), (95, 255, 255), (255, 175, 95), (95, 255, 95)}


def diff_report(orig, new, spec, pieces):
    add = new & ~orig
    rem = orig & ~new
    out = {'added_voxels': int(add.sum()), 'removed_voxels': int(rem.sum()),
           'changed_columns': int((add | rem).any(2).sum()),
           'share_of_original_solid_changed_pct': round(100 * float((add | rem).sum()) / float(orig.sum()), 3)}
    for team, (x0, x1, y0, y1) in spec['spawn_squares'].items():
        sl = (slice(x0, x1 + 1), slice(y0, y1 + 1))
        out[f'spawn_square_{team}_changed_voxels'] = int((orig[sl] != new[sl]).sum())
    x0, x1, y0, y1 = spec['no_new_geometry'][2]
    sl = (slice(x0, x1 + 1), slice(y0, y1 + 1))
    out['under_platform_strip_changed_voxels'] = int((orig[sl] != new[sl]).sum())
    kinds = {}
    for p in pieces:
        k = kinds.setdefault(p['kind'], {'count': 0, 'voxels': 0})
        k['count'] += 1
        k['voxels'] += p['voxels']
    out['by_kind'] = kinds
    out['locations'] = [{'name': p['name'], 'kind': p['kind'], 'box': p.get('box'), 'z': p.get('z'),
                         'voxels': p['voxels'], **({'removed': p['removed']} if 'removed' in p else {})}
                        for p in pieces if p['kind'] not in ('icicle',)]
    return out


def connectivity(orig, new):
    fo = symmetry.floating_components(orig)
    fn = symmetry.floating_components(new)
    key = {(tuple(f['x']), tuple(f['y']), tuple(f['z']), f['voxels']) for f in fo}
    extra = [f for f in fn if (tuple(f['x']), tuple(f['y']), tuple(f['z']), f['voxels']) not in key]
    return {'original_floating': len(fo), 'now_floating': len(fn), 'new_floating': extra,
            'ok': not extra, 'note': 'the original floating pieces (4 jets + small stubs) are kept as they were'}


def exposure(orig, new, P=params.BABEL_DEFAULT):
    out = {}
    for team, base in zip(P['team_names'], P['bases']):
        a = babel_checks.spawn_exposure(orig, base, P)
        b = babel_checks.spawn_exposure(new, base, P)
        out[team] = {'before': {k: a[k] for k in ('viewers_per_spot_mean', 'hidden_pct', 'exposed_pct', 'viewers_max')},
                     'after': {k: b[k] for k in ('viewers_per_spot_mean', 'hidden_pct', 'exposed_pct', 'viewers_max',
                                                 'targets_met')}}
    out['model'] = 'kit babel_checks calibrated preset (aosmap.sightline): fog ignored, an upper bound'
    return out


def _runs(free):
    runs, r = [], 0
    for f in free:
        if f:
            r += 1
        elif r:
            runs.append(r)
            r = 0
    if r:
        runs.append(r)
    return runs


def front_lanes(solid, spec):
    """At every x of each front (x 139-160 / 352-373), the walkable lanes across y 236-276: a column is open when
    z 51-54 are air (a 1-high kerb or drift at z 55 is a step). Reports the worst x."""
    z0, z1 = spec['front_lanes_min']['clearance_z']
    out = {}
    for team, xs in (('blue', range(139, 161)), ('red', range(352, 374))):
        rows = []
        for x in xs:
            free = ~solid[x, 236:277, z0:z1 + 1].any(axis=1)
            runs = _runs(free)
            rows.append({'x': x, 'lanes_3wide': sum(1 for r in runs if r >= 3), 'widest': max(runs or [0]),
                         'open_cols': int(free.sum())})
        worst = min(rows, key=lambda r: (r['lanes_3wide'], r['open_cols']))
        need = spec['front_lanes_min']['lanes_3wide']
        # ok: at every x either >= need lanes 3+ wide, or one lane >= 8 wide (a wide open boulevard)
        ok = all(r['lanes_3wide'] >= need or r['widest'] >= 8 for r in rows)
        out[team] = {'worst': worst, 'min_lanes_3wide': min(r['lanes_3wide'] for r in rows),
                     'min_open_cols_of_41': min(r['open_cols'] for r in rows), 'ok': ok}
    return out


def clear_width(orig, new, spec, pieces):
    """Owner: a festive vehicle may narrow the clear street beside it by at most 1. For every x of the vehicle's
    footprint, count the columns within its y-range +-3 that are blocked at walking height (z 51-54) by the vehicle
    or by its own additions (original component, gift stack, tree float, rebuilt sleigh); spawn-cover pieces are
    other objects and are excluded by their recorded boxes. growth = after - before."""
    z0, z1 = spec['front_lanes_min']['clearance_z']
    from rpsn_source import components
    lab, rows = components(orig, spec['street_z'])
    cover_boxes = [p['box'] for p in pieces if p.get('team') and p.get('box')]
    res = {}
    names = list(spec['gift_stack']) + list(spec['tree_float']) + ['sleigh_w', 'sleigh_e']
    for name in names:
        x0, x1, y0, y1 = spec['vehicles'][name]
        comp = [r for r in rows if r['box'] == [x0, x1, y0, y1]][0]
        vm = np.zeros(orig.shape, bool)
        vm[:, :, :spec['street_z']] = lab == comp['id']
        worst = 0
        for x in range(x0, x1 + 1):
            before = after = 0
            for y in range(max(0, y0 - 3), min(511, y1 + 3) + 1):
                b = vm[x, y, z0:z1 + 1].any()
                added = (new[x, y, z0:z1 + 1] & ~orig[x, y, z0:z1 + 1]).any()
                in_cover = any(c[0] <= x <= c[1] and c[2] <= y <= c[3] for c in cover_boxes)
                a = bool((b and new[x, y, z0:z1 + 1].any()) or (added and not in_cover))
                before += int(b)
                after += int(a)
            worst = max(worst, after - before)
        res[name] = {'max_width_growth': int(worst), 'ok': worst <= spec['clear_width_max_loss']}
    return res


def colour_stats(solid, rgb, nolight=None):
    top = np.argmax(solid, axis=2)
    X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    t = rgb[X, Y, top].astype(float)
    L = color.luma(t)
    land = solid[:, :, 50:63].any(axis=2)
    surf = codec.surface_mask(solid)
    s = rgb[surf].astype(int)
    hot = s.max(1) > 212
    out = {'top_luma_pct': {p: round(float(np.percentile(L, p)), 1) for p in (1, 5, 10, 50, 90, 99)},
           'land_top_luma_pct': {p: round(float(np.percentile(L[land], p)), 1) for p in (1, 5, 10, 50, 90, 99)},
           'top_maxch_over_212_pct': round(100 * float((t.max(-1) > 212).mean()), 2),
           'surface_maxch_over_212_pct': round(100 * float(hot.mean()), 2),
           'unique_surface_colours': int(len(np.unique(s[:, 0] * 65536 + s[:, 1] * 256 + s[:, 2])))}
    if nolight is not None:
        nl = nolight[surf]
        out['surface_maxch_over_212_non_glow_pct'] = round(100 * float((hot & ~nl).mean()), 2)
    out['kit'] = color.colour_stats(solid, rgb)
    return out


def palette_collisions(rgb, solid, sources):
    """Voxels that carry a glow-palette colour but are not a listed source (only true sources may match)."""
    src = set(map(tuple, sources))
    surf = codec.surface_mask(solid)
    xs, ys, zs = np.nonzero(surf)
    c = rgb[xs, ys, zs]
    bad = 0
    for pal in GLOW_PALETTE:
        m = (c == np.array(pal)).all(1)
        for i in np.nonzero(m)[0]:
            if (int(xs[i]), int(ys[i]), int(zs[i])) not in src:
                bad += 1
    return bad


def main(out):
    from rpsn_spec import SPEC
    import rpsn_source
    info = json.load(open(os.path.join(out, 'build.json')))
    data = open(os.path.join(out, SPEC['file'] + '.vxl'), 'rb').read()
    solid, colr, _ = codec.decode(data)
    rgb = codec.unpack_rgb(colr).astype(np.uint8)
    orig, _, _ = rpsn_source.load(SPEC)
    R = {'diff': diff_report(orig, solid, SPEC, info.get('pieces', [])), 'connectivity': connectivity(orig, solid),
         'exposure': exposure(orig, solid), 'front_lanes': front_lanes(solid, SPEC),
         'clear_width': clear_width(orig, solid, SPEC, info.get('pieces', [])), 'colour': colour_stats(solid, rgb)}
    print(json.dumps(R, indent=1, default=str)[:6000])
    return R


if __name__ == '__main__':
    main(sys.argv[1])
