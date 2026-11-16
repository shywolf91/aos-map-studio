"""Original-map analysis for a [recreate] job (docs/remus_recreate_report.md §1 + the 2026-11-13 Babel zone targets).

    python tools/recreate_analysis.py ORIGINAL.vxl [--txt ORIGINAL.txt] [--out out/recreate/<stem>]
            [--mode babel] [--compare NEW.vxl] [--no-render] [--fast]

Writes <out>/analysis.json (every number), <out>/analysis.md (the report) and numpy previews (top, height, contours,
side views) unless --no-render. Default out dir: <repo>/out/recreate/<stem>/ (git-ignored).

The input map is third-party and untrusted: it is opened read-only, nothing is written beside it, and its .txt is
NEVER executed or imported. It is parsed with `ast` literals only (tools/babel_zone_study.parse_txt).

This tool composes existing measurements; it does not reimplement them:
  identity      aosmap.vxl.read_vxl, kit babel_checks.reader_checks, kit codec.pyspades_crosscheck (pyspades VXLData)
  map DNA       kit zones.fields / tops / SYM_TRANSFORMS / symmetry_type / object_field, kit symmetry.floating_components,
                vxl_analyzer.basic_stats, kit babel_checks.run_all routes
  Babel         kit babel_checks.run_all (platform_checks, spawn_square_checks, anchor_checks, build gap, routes,
                spawn_exposure 'calibrated', zone_profile, zone_rules), vxl_analyzer.babel_geometry
  art           tools/art_metrics.metrics, kit color.colour_stats / luma, vxl_analyzer hue names
  island        tools/island_style_metrics.measure / classic_table (only when > 50 % of columns are water)
  orientation   vxl_analyzer.region_grid / ascii_height / top_view / height_view / contour_view / side_view
New here (no module had them): sealed air pockets, neighbour colour jump, pure team-hue share, height levels, water
bodies, the element-ledger skeleton and the problem list.

--fast skips: kit zones.zone_profile inside run_all (spawn exits / sealability, ground LOS, centre metrics, so the
"spawn spots that cannot walk to their own platform end" share is not measured), the pyspades cross-check (canonical
encoding is then reported as "not checked"), island-style metrics, and the --compare side's slow parts likewise.

Every number is a [RUN] measurement of the file given; route checks are a graph model (kit Nav 'hc': 3 air to stand,
1-voxel step, drops <= 9 safe), not a collision simulation. Deterministic: fixed sampling seeds inside the kit, no
`hash()`, no wall-clock values in the analysis dict (the CLI adds a separate 'timing' block).
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
import sys
import time

import numpy as np
from scipy import ndimage as ndi

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (ROOT, os.path.join(ROOT, 'tools'), os.path.join(ROOT, 'tools', 'share')):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from aosmap.vxl import read_vxl  # noqa: E402
from aosmap.kit import babel_checks, codec, zones  # noqa: E402
from aosmap.kit.color import LUMA_FLOOR_MIN, WHITE_CAP, colour_stats, luma  # noqa: E402
from aosmap.kit.params import BABEL_DEFAULT, ZONE_RULES  # noqa: E402
from aosmap.kit.symmetry import floating_components, standable  # noqa: E402

import vxl_analyzer as va  # noqa: E402  (tools/share)

MODES = ('babel',)
SQUARE_SPOTS = 41 * 41
EXPOSURE_TARGET = {'viewers_max_mean': 10, 'hidden_min_pct': 15}
BUILD_GAP_REF = (38, 54)          # docs/babel_zone_study.md §9 item 9 (community p25-p75) - a proposal, not a rule
FOG_MIN = 150                     # AGENTS.md §4: fog brightness ~150+ per channel
BRIGHT_LUMA = 175                 # knowledge base §10.2: top-down bright share (luma > 175)
LEDGER_OBJECTS = 12
LEDGER_MASS_CELLS = 1500          # object components this large are usually landforms/islands or big complexes
LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'


# =============================================================================================== helpers

def _err(e):
    return {'error': f'{type(e).__name__}: {e}'}


def _run(rep, key, fn, *a, **k):
    """rep[key] = fn(...); on any exception record {'error': ...} and carry on (graceful degradation)."""
    try:
        rep[key] = fn(*a, **k)
    except Exception as e:                      # noqa: BLE001 - every sub-check degrades on its own
        rep[key] = _err(e)
    return rep[key]


def jsonable(o):
    """numpy scalars/arrays and tuples -> plain JSON types (keys as str), recursively."""
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return jsonable(o.tolist())
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        v = float(o)
        return None if math.isnan(v) else v
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
        return None if math.isnan(o) else str(o)
    return o


def _r(v, n=2):
    return None if v is None else round(float(v), n)


def _ok(d):
    return isinstance(d, dict) and 'error' not in d


def colour_name(c):
    """Neutral colour words for a packed colour: '<light|dark> <hue> (#rrggbb)'."""
    rgb = va.rgb_of(np.array([int(c) & 0xFFFFFF]))
    L = float(va.lightness(rgb)[0])
    hue = va.HUE_NAMES[int(va.hue_bin(rgb)[0])].replace('grey/neutral', 'grey')
    tone = 'dark ' if L < 35 else ('light ' if L > 72 else '')
    return f'{tone}{hue} ({va.hexcol(c)})'


def zone_of(x, y, P=BABEL_DEFAULT):
    """Babel zone of a column (stock geometry from params): spawn square / spawn district / tower zone / front /
    under platform / centre / flank / periphery, with the team side (west = blue, east = red, axis)."""
    (x0, x1), (y0, y1) = P['platform_x'], P['platform_y']
    half = P['spawn_half']
    side = 'axis' if abs(x - 255.5) <= 8 else (P['team_names'][0] if x < 256 else P['team_names'][1])
    for k, (bx, by) in enumerate(P['bases']):
        d = max(abs(x - bx), abs(y - by))
        if d <= half:
            return 'spawn square', P['team_names'][k]
    if x0 + 6 <= x <= x1 - 5 and y0 <= y <= y1:
        return 'under platform', side
    for t in zones.team_geometry(P):
        fx0, fx1 = t['front']
        b0, b1 = t['band']
        tz = (x0 - 38, x0 + 5) if t['s'] > 0 else (x1 - 5, x1 + 38)
        if tz[0] <= x <= tz[1] and y0 <= y <= y1:
            return 'tower zone', t['name']
        if fx0 <= x <= fx1 and b0 <= y <= b1:
            return 'front', t['name']
    for k, (bx, by) in enumerate(P['bases']):
        if max(abs(x - bx), abs(y - by)) <= half + 40:
            return 'spawn district', P['team_names'][k]
    cx0, cx1, cy0, cy1 = ZONE_RULES['centre']['box']
    if cx0 <= x <= cx1 and cy0 <= y <= cy1:
        return 'centre', side
    if 130 <= abs(y - 256) <= 210:
        return 'flank', side
    return 'periphery', side


# =============================================================================================== .txt

def resolve_txt(vxl_path, txt_path=None):
    if txt_path:
        return txt_path
    cand = os.path.splitext(vxl_path)[0] + '.txt'
    return cand if os.path.isfile(cand) else None


def txt_section(txt_path):
    """Literal-only parse (never executed): tools/babel_zone_study.parse_txt plus `version` and the top-level keys."""
    if not txt_path:
        return {'supplied': False}
    if not os.path.isfile(txt_path):
        return {'supplied': False, 'error': f'not found: {txt_path}'}
    from babel_zone_study import parse_txt
    out = {'supplied': True, 'file': os.path.basename(txt_path)}
    out.update(parse_txt(txt_path))
    keys, version = [], None
    try:
        src = open(txt_path, 'rb').read().decode('utf-8', 'replace')
        for node in ast.parse(src).body:
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        keys.append(t.id)
                        if t.id == 'version':
                            try:
                                v = ast.literal_eval(node.value)
                                version = v if isinstance(v, (str, int, float)) else str(v)
                            except Exception:            # noqa: BLE001
                                version = '<non-literal>'
    except Exception as e:                               # noqa: BLE001 - SyntaxError, RecursionError ...
        out['ast_error'] = f'{type(e).__name__}: {e}'
    out['version'] = version
    out['top_level_keys'] = keys
    out['hooks_note'] = ('present but not evaluated (the .txt is never executed)' if out.get('spawn_hooks')
                         else 'none')
    return out


# =============================================================================================== sections

def identity_section(path, data, m, rrep, fast):
    out = {'file': os.path.basename(path), 'path': path, 'sha256': hashlib.sha256(data).hexdigest(),
           'bytes': len(data), 'reader_ok': rrep.ok, 'reader_issues': [list(map(str, i)) for i in rrep.issues[:10]],
           'void_columns': rrep.void_columns}
    s = m.solid
    out['z63_solid_every_column'] = bool(s[:, :, 63].all())
    out['z63_air_columns'] = int((~s[:, :, 63]).sum())
    _run(out, 'reencode', babel_checks.reader_checks, data, s, m.color, m.colored)
    if fast:
        out['pyspades'] = {'skipped': '--fast'}
        out['pyspades_loads'] = None
        out['canonical_encoding'] = None
    elif not rrep.ok:
        out['pyspades'] = {'skipped': 'our reader flagged issues; pyspades not fed a malformed file'}
        out['pyspades_loads'] = None
        out['canonical_encoding'] = None
    else:
        ps = _run(out, 'pyspades', codec.pyspades_crosscheck, data, s, m.color)
        out['pyspades_loads'] = _ok(ps)
        out['canonical_encoding'] = bool(ps.get('generate_identical')) if _ok(ps) else None
    return out


def _mirror_topz(top):
    """% of columns whose top z equals the transformed column's (zones.SYM_TRANSFORMS on the 2-D top field)."""
    return {k: round(100 * float((top == f(top)).mean()), 1) for k, f in zones.SYM_TRANSFORMS.items()}


def _sealed_pockets(solid):
    """Air components (6-connected) that do not reach z = 0 (the open sky): sealed rooms, voids, closed caves.
    Off-map counts as solid (pyspades is_surface rule), so a pocket against the map edge is still sealed."""
    air = ~solid
    lab, n = ndi.label(air, structure=ndi.generate_binary_structure(3, 1))
    open_ids = np.unique(lab[:, :, 0][air[:, :, 0]])
    sizes = np.bincount(lab.ravel(), minlength=n + 1)
    sealed = np.ones(n + 1, bool)
    sealed[0] = False
    sealed[open_ids] = False
    ids = np.nonzero(sealed)[0]
    out = {'count': int(len(ids)), 'voxels': int(sizes[ids].sum()),
           'count_ge_27_voxels': int((sizes[ids] >= 27).sum())}
    big = ids[np.argsort(-sizes[ids], kind='stable')][:5]
    sl = ndi.find_objects(lab)
    out['largest'] = [{'voxels': int(sizes[i]), 'x': [sl[i - 1][0].start, sl[i - 1][0].stop - 1],
                       'y': [sl[i - 1][1].start, sl[i - 1][1].stop - 1],
                       'z': [sl[i - 1][2].start, sl[i - 1][2].stop - 1]} for i in big]
    return out


def _water_bodies(top, min_cols=200):
    """Engine water (top z 63: z 62 is air), 4-connected bodies >= min_cols, with the median rim (kerb) height."""
    water = top >= 63
    lab, n = ndi.label(water)
    sizes = np.bincount(lab.ravel(), minlength=n + 1)
    sizes[0] = 0
    order = [int(i) for i in np.argsort(-sizes, kind='stable') if sizes[i] >= min_cols]
    sl = ndi.find_objects(lab)
    rows = []
    for k, i in enumerate(order[:10]):
        body = lab == i
        rim = ndi.binary_dilation(body) & ~water
        rz = top[rim]
        bx, by = np.nonzero(body)
        rows.append({'name': f'water body {LETTERS[k]}', 'cols': int(sizes[i]),
                     'centroid': [int(round(bx.mean())), int(round(by.mean()))],
                     'x': [sl[i - 1][0].start, sl[i - 1][0].stop - 1], 'y': [sl[i - 1][1].start, sl[i - 1][1].stop - 1],
                     'rim_top_z_median': _r(np.median(rz), 1) if rz.size else None,
                     'kerb_height_median': _r(63 - np.median(rz), 1) if rz.size else None,
                     'touches_map_edge': bool(body[0].any() or body[-1].any() or body[:, 0].any() or body[:, -1].any())})
    return {'bodies_ge_%d' % min_cols: len(order), 'bodies': rows, 'bodies_total': int(n)}


def dna_section(m, F, R, P):
    s = m.solid
    top = F['top'].astype(int)                       # 64 = all-air column
    out = {}
    vals, cnt = np.unique(top, return_counts=True)
    out['top_z_histogram'] = {str(int(v)): int(c) for v, c in zip(vals, cnt)}
    land = top <= 62
    lv, lc = np.unique(top[land], return_counts=True)
    order = np.argsort(-lc, kind='stable')
    out['dominant_levels'] = [{'z': int(lv[i]), 'height': int(63 - lv[i]),
                               'share_of_all_cols_pct': _r(100 * lc[i] / top.size, 1),
                               'share_of_land_pct': _r(100 * lc[i] / max(land.sum(), 1), 1)} for i in order[:6]]
    if len(lv):
        dz = int(lv[order[0]])
        p = np.pad(top, 1, mode='edge')
        flat = (top == dz) & (p[:-2, 1:-1] == dz) & (p[2:, 1:-1] == dz) & (p[1:-1, :-2] == dz) & (p[1:-1, 2:] == dz)
        st = standable(s)
        xs, ys = np.indices(top.shape)
        walk = st[xs, ys, np.clip(top, 0, 63)] & (top <= 63)
        out['dominant_level_z'] = dz
        out['flat_walkable_at_dominant_level_pct'] = _r(100 * (flat & walk).mean(), 1)
        out['flat_walkable_at_dominant_level_pct_of_land'] = _r(100 * (flat & walk).sum() / max(land.sum(), 1), 1)
    out['land_cols_pct'] = _r(100 * land.mean(), 1)
    out['water'] = {'engine_water_cols_pct': _r(100 * (top >= 63).mean(), 1),
                    'note': 'engine water = top z 63 (z 62 air); z 62 tops are land at sea level',
                    'sea_level_land_z62_cols_pct': _r(100 * (top == 62).mean(), 1),
                    'all_air_cols': int((top >= 64).sum())}
    _run(out['water'], 'bodies', _water_bodies, top)
    out['mirror_topz_match_pct'] = _mirror_topz(top)
    out['mirror_topz_note'] = ("x511: x' = 511 - x; x512: x' = 512 - x (kit default axis); y likewise; "
                               "point = 180 degree rotation")
    _run(out, 'symmetry_voxels', zones.symmetry_type, s)
    fl = floating_components(s)
    fl.sort(key=lambda f: (-f['voxels'], f['x'][0], f['y'][0], f['z'][0]))
    out['floating'] = {'count': len(fl), 'voxels': int(sum(f['voxels'] for f in fl)), 'largest': fl[:10],
                       'note': 'components (6-face) not connected to z >= 62; includes any intended sky decor'}
    _run(out, 'sealed_air_pockets', _sealed_pockets, s)
    # tallest point / tallest object
    h = np.where(top <= 63, 63 - top, 0)
    k = int(np.argmax(h))
    hx, hy = np.unravel_index(k, h.shape)
    out['highest_point'] = {'x': int(hx), 'y': int(hy), 'top_z': int(top[hx, hy]), 'height': int(h[hx, hy]),
                            'zone': zone_of(int(hx), int(hy), P)}
    bs = va.basic_stats(m)
    out['basic'] = {k: bs[k] for k in ('solid_voxels', 'surface_voxels_above_water', 'height_median_land',
                                       'height_histogram_land', 'columns_with_air_gap_pct', 'max_runs_in_a_column',
                                       'air_under_surface_mean', 'columns_with_8plus_air_under_surface_pct',
                                       'sky_level_columns(z<=3)', 'bounding_box_of_land')}
    air_below = (F['roof'] | F['deck'])
    Z = np.arange(64)[None, None, :]
    any_air = ((~s) & (Z > top[..., None])).any(axis=2)
    out['solid_down'] = {'solid_all_the_way_down_pct': _r(100 * (~any_air & (top <= 63)).mean(), 1),
                         'air_below_top_pct': _r(100 * any_air.mean(), 1),
                         'roof_room_height_gap_pct': _r(100 * F['roof'].mean(), 2),
                         'deck_or_thin_gap_pct': _r(100 * F['deck'].mean(), 2),
                         'roof_or_deck_pct': _r(100 * air_below.mean(), 2),
                         'note': 'roof = air gap >= 3 tall under the top with a dry floor <= 20 below (kit zones); '
                                 'deck = any other air below the top'}
    if _ok(R):
        rt = R['routes']
        out['spawn_to_spawn_steps'] = {t: rt[t]['to_enemy_spawn'] for t in P['team_names']}
        out['spawn_to_spawn_steps_any_drop'] = {t: rt[t]['to_enemy_spawn_any_drop'] for t in P['team_names']}
    else:
        out['spawn_to_spawn_steps'] = {'error': 'babel_checks.run_all failed'}
    return out


def _fallback_checks(m, P):
    """When run_all fails: the static kit checks one by one (no routes)."""
    s = m.solid
    R = {'fallback': True}
    _run(R, 'platform', babel_checks.platform_checks, s, P)
    if _ok(R['platform']):
        R.update(R.pop('platform'))
    _run(R, 'spawn_squares', babel_checks.spawn_square_checks, s, P)
    _run(R, 'anchors', babel_checks.anchor_checks, s, None, P)
    R['spawn_exposure'] = {}
    for t, b in zip(P['team_names'], P['bases']):
        _run(R['spawn_exposure'], t, babel_checks.spawn_exposure, s, b, P)
    _run(R, 'zone_rules', zones.zone_rules, s, P)
    return R


def babel_section(m, R, F, P):
    s = m.solid
    out = {'params': {k: v for k, v in P.items()}, 'graph_model': 'kit Nav hc: 3 air to stand, 1 step, drops <= 9'}
    (x0, x1), (y0, y1), pz = P['platform_x'], P['platform_y'], P['platform_z']
    out['platform_volume_z0_2_voxels'] = R.get('platform_volume_voxels')
    out['platform_margin_z0_2_voxels'] = R.get('platform_margin_voxels')
    out['platform_layer_voxels'] = int(s[x0:x1 + 1, y0:y1 + 1, pz].sum())
    out['platform_volume_clear'] = R.get('platform_volume_voxels') == 0
    ends = R.get('ground_under_platform_ends') or {}
    out['ground_under_ends'] = {k: dict(v, kind='water' if v['water_cols'] else 'land') for k, v in ends.items()}
    if len(ends) == 2:
        a, b = list(ends.values())
        out['anchors_equal'] = bool(a['top_z_min'] == b['top_z_min'] and a['top_z_max'] == b['top_z_max'] and
                                    a['water_cols'] == b['water_cols'])
    out['anchor_faces'] = R.get('anchors')
    if 'build_gap' in R:
        out['build_gap'] = {t: {'highest_walkable_z': v['highest_reachable_near_platform_z'],
                                'blocks_to_platform_level': v['blocks_to_build_up_to_platform_level'],
                                'platform_reachable_on_foot': v['platform_reachable_on_foot']}
                            for t, v in R['build_gap'].items()}
        out['build_gap_definition'] = ('highest cell walkable from own spawn within %d of the platform; blocks = '
                                       'z - (platform_z + 1)' % R['build_gap'][P['team_names'][0]]['margin'])
        out['platform_reachable_on_foot'] = any(v['platform_reachable_on_foot'] for v in R['build_gap'].values())
    try:
        out['nearest_map_voxel_to_platform'] = {k: v for k, v in va.babel_geometry(m).items()
                                                if k.startswith('nearest_solid')}
    except Exception as e:                       # noqa: BLE001
        out['nearest_map_voxel_to_platform'] = _err(e)
    sq = R.get('spawn_squares') or {}
    half = P['spawn_half']
    zp = (R.get('zone_profile') or {}).get('teams') or {}
    spawns = {}
    for t, (bx, by) in zip(P['team_names'], P['bases']):
        q = sq.get(t)
        if not q:
            continue
        roof = int(F['roof'][bx - half:bx + half + 1, by - half:by + half + 1].sum())
        deck = int(F['deck'][bx - half:bx + half + 1, by - half:by + half + 1].sum())
        row = {'top_z_min': q['top_z_min'], 'top_z_max': q['top_z_max'], 'flat_share': q['flat_share'],
               'water_cols': q['water_cols'], 'water_pct': _r(100 * q['water_cols'] / SQUARE_SPOTS, 1),
               'over_air_cols': q['roof_cols'], 'over_air_pct': _r(100 * q['roof_cols'] / SQUARE_SPOTS, 1),
               'roof_cols': roof, 'roof_pct': _r(100 * roof / SQUARE_SPOTS, 1),
               'deck_cols': deck, 'top_z_values': q['top_z_values']}
        sp = (zp.get(t) or {}).get('spawn') or {}
        share = sp.get('spots_reaching_own_end_share')
        row['spots_not_reaching_own_end_pct'] = _r(100 * (1 - share), 1) if share is not None else None
        row['sealable'] = sp.get('sealable')
        row['exit_min_cut'] = sp.get('exit_min_cut')
        spawns[t] = row
    out['spawn_squares'] = spawns
    out['spawn_squares_mirror_equal_share'] = sq.get('mirror_equal_share')
    out['spawn_square_notes'] = ('over_air = any air under the top voxel (kit spawn_square_checks "roof_cols"); '
                                 'roof = room-height gap with a floor (kit zones); not-reaching share needs zone_profile'
                                 ' (absent with --fast)')
    if 'routes' in R:
        out['routes'] = R['routes']
        out['safe_descent'] = R.get('safe_descent')
        out['trap_cells'] = {'count': R['trap_cells']['count'], 'of_cells': R['trap_cells']['of_cells']}
        out['flank'] = R.get('flank')
        out['periphery'] = R.get('periphery')
    if R.get('zone_profile'):
        out['zone_class'] = R['zone_profile'].get('class')
    return out


def exposure_section(R, P):
    e = R.get('spawn_exposure') or {}
    out = {'model': 'kit babel_checks.spawn_exposure preset "calibrated" (platform-edge eyes every 4, heads every 2; '
                    'fog ignored, an upper bound)', 'targets': EXPOSURE_TARGET, 'teams': e}
    for t, v in e.items():
        if _ok(v):
            v['meets_viewers'] = v['viewers_per_spot_mean'] <= EXPOSURE_TARGET['viewers_max_mean']
            v['meets_hidden'] = v['hidden_pct'] >= EXPOSURE_TARGET['hidden_min_pct']
    return out


def zone_section(R):
    Z = R.get('zone_rules')
    if not Z:
        return {'error': 'zone_rules not run'}
    if not _ok(Z):
        return Z
    T = Z['thresholds']
    rows = []
    fr = Z['front_dressing']
    for t, v in (fr.get('values') or {}).items():
        if not isinstance(v, dict) or not v.get('applicable'):
            rows.append({'rule': 'front_dressing', 'team': t, 'metric': 'applicable', 'value': False,
                         'target': 'land front', 'ok': None})
            continue
        f = T['front']
        rows += [
            {'rule': 'front_dressing', 'team': t, 'metric': 'low objects', 'value': v['objects'],
             'target': '%d-%d' % f['objects'], 'ok': f['objects'][0] <= v['objects'] <= f['objects'][1]},
            {'rule': 'front_dressing', 'team': t, 'metric': 'object coverage', 'value': v['object_share'],
             'target': '%.2f-%.2f' % f['share'], 'ok': f['share'][0] <= v['object_share'] <= f['share'][1]},
            {'rule': 'front_dressing', 'team': t, 'metric': 'objects <= %d tall' % f['low_h'],
             'value': v['low_share'], 'target': '>= %.2f' % f['low_share_min'],
             'ok': v['low_share'] >= f['low_share_min']},
            {'rule': 'front_dressing', 'team': t, 'metric': 'worst 8-col section free',
             'value': v['section_free_min'], 'target': '>= %.2f' % f['section_free_min'],
             'ok': v['section_free_min'] >= f['section_free_min']}]
    sc = Z['spawn_cover']
    c = T['spawn_cover']
    for t, v in (sc.get('values') or {}).items():
        if not isinstance(v, dict) or not v.get('applicable'):
            continue
        rows += [{'rule': 'spawn_cover', 'team': t, 'metric': 'enemy-side cover >= %d tall within %d'
                  % (c['cover_h'], c['enemy_r']), 'value': v['enemy_0_20'], 'target': '>= %.2f' % c['enemy_min'],
                  'ok': v['enemy_0_20'] >= c['enemy_min']},
                 {'rule': 'spawn_cover', 'team': t, 'metric': 'rear backdrop %d-%d' % tuple(c['rear_r']),
                  'value': v['rear_20_40'], 'target': '>= %.2f' % c['rear_min'], 'ok': v['rear_20_40'] >= c['rear_min']}]
    up = Z['under_platform']
    u = T['under_platform']
    v = up.get('values') or {}
    if 'object_share' in v:
        rows += [{'rule': 'under_platform', 'team': '-', 'metric': 'strip object coverage', 'value': v['object_share'],
                  'target': '%.2f-%.2f' % u['share'], 'ok': u['share'][0] <= v['object_share'] <= u['share'][1]},
                 {'rule': 'under_platform', 'team': '-', 'metric': 'min air strip tops -> platform',
                  'value': v['min_air_all'], 'target': '>= %d' % u['min_air'], 'ok': v['min_air_all'] >= u['min_air']}]
    for t, a in (v.get('anchors') or {}).items():
        if a.get('applicable'):
            rows += [{'rule': 'under_platform', 'team': t, 'metric': 'anchor end top-z range',
                      'value': a['top_z_range'], 'target': '<= %d' % u['anchor_flat_range'],
                      'ok': a['top_z_range'] <= u['anchor_flat_range']},
                     {'rule': 'under_platform', 'team': t, 'metric': 'anchor end prop columns',
                      'value': a['prop_cols'], 'target': '0', 'ok': a['prop_cols'] == 0}]
    cf = Z['centre_footprint']
    v = cf.get('values') or {}
    if 'footprint_p50' in v:
        rows.append({'rule': 'centre_footprint', 'team': '-', 'metric': 'median object footprint (cells)',
                     'value': v['footprint_p50'], 'target': '>= %d' % T['centre']['footprint_p50_min'],
                     'ok': v['footprint_p50'] >= T['centre']['footprint_p50_min']})
    return {'object_ground': Z.get('object_ground'),
            'status': {k: Z[k]['status'] for k in zones.RULE_KEYS},
            'why': {k: Z[k]['why'] for k in zones.RULE_KEYS}, 'rows': rows, 'raw': Z}


def art_section(path, m, F):
    import art_metrics
    out = {}
    _run(out, 'art_metrics', art_metrics.metrics, path)
    s = m.solid
    top = np.clip(F['top'].astype(int), 0, 63)
    xs, ys = np.indices(top.shape)
    tc = m.color[xs, ys, top] & 0xFFFFFF
    rgb = va.rgb_of(tc)
    _run(out, 'colour_stats', colour_stats, s, m.color)
    # neighbour colour jump (top-down): mean Euclidean RGB distance between 4-adjacent top colours, all columns.
    # The knowledge base (§10.2) quotes this metric (MountainRoad 34, Silverpine v2 29) but no code for it is in the
    # repo; this is our reconstruction, so compare it with those numbers loosely.
    dx = np.linalg.norm(rgb[1:] - rgb[:-1], axis=-1)
    dy = np.linalg.norm(rgb[:, 1:] - rgb[:, :-1], axis=-1)
    out['neighbour_jump_mean'] = _r(np.concatenate([dx.ravel(), dy.ravel()]).mean(), 1)
    Lt = luma(rgb)
    out['bright_share_top_pct'] = _r(100 * (Lt > BRIGHT_LUMA).mean(), 1)
    out['bright_definition'] = 'top-down columns with luma > %d (knowledge base §10.2)' % BRIGHT_LUMA
    # pure team hues
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    land = top <= 62
    pure_red = (r > 0) & (g == 0) & (b == 0)
    pure_blue = (b > 0) & (r == 0) & (g == 0)
    out['pure_team_hue_top_pct'] = {'red': _r(100 * pure_red.mean(), 2), 'blue': _r(100 * pure_blue.mean(), 2)}
    surf = va.surface_mask(s)
    surf[:, :, 63] = False
    sc = m.color[surf] & 0xFFFFFF
    srgb = va.rgb_of(sc)
    sr, sg, sb = srgb[:, 0], srgb[:, 1], srgb[:, 2]
    out['pure_team_hue_surface_pct'] = {'red': _r(100 * ((sr > 0) & (sg == 0) & (sb == 0)).mean(), 2),
                                        'blue': _r(100 * ((sb > 0) & (sr == 0) & (sg == 0)).mean(), 2)}
    out['exact_team_colour_surface_voxels'] = {'red_255_0_0': int((sc == 0xFF0000).sum()),
                                               'blue_0_0_255': int((sc == 0x0000FF).sum())}
    # floors and whites
    st = standable(s)
    walk = st[xs, ys, top] & land
    Lw = Lt[walk]
    out['floor_luma'] = {'walkable_land_tops': int(walk.sum()),
                         'min': _r(Lw.min(), 1) if Lw.size else None,
                         'p1': _r(np.percentile(Lw, 1), 1) if Lw.size else None,
                         'p5': _r(np.percentile(Lw, 5), 1) if Lw.size else None,
                         'near_black_lt40_pct': _r(100 * (Lw < LUMA_FLOOR_MIN).mean(), 2) if Lw.size else None}
    Ls = luma(srgb)
    mc = srgb.max(axis=1)
    out['surface'] = {'voxels': int(len(sc)), 'max_channel': int(mc.max()) if mc.size else None,
                      'max_channel_p99': _r(np.percentile(mc, 99), 1) if mc.size else None,
                      'over_white_cap_pct': _r(100 * (mc > WHITE_CAP).mean(), 2) if mc.size else None,
                      'near_black_lt40_pct': _r(100 * (Ls < LUMA_FLOOR_MIN).mean(), 2) if mc.size else None}
    out['white_cap'] = WHITE_CAP
    # hue shares (same binning as art_metrics.hue_bins)
    hb = art_metrics.hue_bins(srgb)
    hc = np.bincount(hb, minlength=13)
    out['hue_shares_pct'] = {va.HUE_NAMES[i]: _r(100 * hc[i] / max(hc.sum(), 1), 1)
                             for i in np.argsort(-hc, kind='stable') if hc[i] > 0}
    u, n = np.unique(sc, return_counts=True)
    o = np.argsort(-n, kind='stable')[:10]
    out['top_surface_colours'] = [{'colour': colour_name(u[i]), 'share_pct': _r(100 * n[i] / n.sum(), 2)} for i in o]
    return out


def island_section(path, m, nbytes):
    import island_style_metrics as ism
    r = ism.measure(m, os.path.splitext(os.path.basename(path))[0], nbytes)
    r['classic'] = [dict(metric=k, lo=lo, hi=hi, value=v, in_range=ok, separates=sep)
                    for k, lo, hi, v, ok, sep, _ in ism.classic_table(r)]
    return r


def ledger_section(m, F, P, dna):
    s = m.solid
    obj, obj_h, ground_z, method = zones.object_field(s, F)
    lab, n = ndi.label(obj, structure=np.ones((3, 3)))
    sizes = np.bincount(lab.ravel(), minlength=n + 1)
    sizes[0] = 0
    keep = [int(i) for i in np.argsort(-sizes, kind='stable') if sizes[i] >= ZONE_RULES['min_object_cells']]
    top = F['top'].astype(int)
    xs, ys = np.indices(top.shape)
    tc = m.color[xs, ys, np.clip(top, 0, 63)] & 0xFFFFFF
    sl = ndi.find_objects(lab)
    rows = []
    for k, i in enumerate(keep[:LEDGER_OBJECTS]):
        sx, sy = sl[i - 1][:2]
        comp = lab[sx, sy] == i
        u, c = np.unique(tc[sx, sy][comp], return_counts=True)
        cx, cy = np.argwhere(comp).mean(axis=0) + (sx.start, sy.start)
        z, side = zone_of(int(round(cx)), int(round(cy)), P)
        w, d = sx.stop - sx.start, sy.stop - sy.start
        hgt = int(obj_h[sx, sy][comp].max())
        kind = 'mass' if sizes[i] >= LEDGER_MASS_CELLS else 'structure'
        cname = colour_name(u[np.argmax(c)])
        rows.append({'element': f'{kind} {LETTERS[k]}', 'kind': kind, 'x': [sx.start, sx.stop - 1], 'y': [sy.start, sy.stop - 1],
                     'size': f'{w}x{d}', 'footprint_cells': int(sizes[i]), 'height_above_ground': hgt,
                     'top_z': int(top[sx, sy][comp].min()), 'colour': cname,
                     'zone': z, 'side': side,
                     'label': f'{kind} {LETTERS[k]}, {w}x{d}, {hgt} tall, {cname.split(" (")[0]}'})
    out = {'object_ground': method, 'objects_total': len(keep), 'objects': rows,
           'note': 'kit zones.object_field: features narrower than %d columns standing >= %d above the estimated '
                   'ground (broad buildings and plateaus count as ground); "mass" = a component of >= %d cells, '
                   'usually a landform, island or a joined building complex' % (
                       ZONE_RULES['baseline_window'], ZONE_RULES['object_min_h'], LEDGER_MASS_CELLS)}
    wb = ((dna.get('water') or {}).get('bodies') or {}).get('bodies') or []
    out['water_bodies'] = [dict(b, zone='map-wide' if (b['x'][1] - b['x'][0] >= 400 and b['y'][1] - b['y'][0] >= 400)
                                else '%s (%s)' % zone_of(b['centroid'][0], b['centroid'][1], P)) for b in wb[:5]]
    # major terrain levels on the estimated ground (grey opening)
    land = top <= 62
    gz = (63 - F['base']).astype(int)
    lv, lc = np.unique(gz[land], return_counts=True)
    levels = []
    for i in np.argsort(-lc, kind='stable')[:6]:
        if lc[i] < 0.03 * max(land.sum(), 1) or lv[i] >= 63:     # baseline z 63 = land narrower than the window
            continue
        mask = land & (gz == lv[i])
        L2, n2 = ndi.label(mask)
        sz = np.bincount(L2.ravel())
        sz[0] = 0
        j = int(np.argmax(sz))
        bx, by = np.nonzero(L2 == j)
        levels.append({'element': f'terrain level z {int(lv[i])} (height {63 - int(lv[i])})',
                       'cols': int(lc[i]), 'share_of_land_pct': _r(100 * lc[i] / land.sum(), 1),
                       'largest_region_x': [int(bx.min()), int(bx.max())], 'largest_region_y': [int(by.min()), int(by.max())],
                       'regions': int(n2)})
    out['terrain_levels'] = levels
    return out


def orientation_section(m):
    return {'region_grid': va.region_grid(m), 'ascii_height': va.ascii_height(m)}


# =============================================================================================== problems

def problems(rep, P=BABEL_DEFAULT):
    """Every failed target as {'key', 'text'} (key is stable, so --compare can tell which ones are fixed)."""
    out = []

    def add(key, text):
        out.append({'key': key, 'text': text})
    I = rep.get('identity') or {}
    if I.get('canonical_encoding') is False:
        add('encoding', 'the file is not in canonical pyspades encoding (generate() differs); re-export fixes it')
    if I.get('pyspades_loads') is False:
        add('pyspades', 'pyspades 1.4.2 fails to load the file: ' + str((I.get('pyspades') or {}).get('error')))
    if I.get('error'):
        add('decode', f"the file cannot be decoded: {I['error']}")
    elif I.get('reader_ok') is False:
        iss = I.get('reader_issues') or []
        add('reader', f'our reader flagged {len(iss)} issue(s): {iss[:3]}')
    if I.get('z63_solid_every_column') is False:
        add('z63', f"{I.get('z63_air_columns')} columns have air at z 63 (no bottom voxel)")
    T = rep.get('txt') or {}
    if not T.get('supplied'):
        add('txt_missing', '.txt not supplied: author, fog and extensions unknown')
    else:
        if T.get('spawn_hooks'):
            add('spawn_hooks', f"the .txt defines {', '.join(T['spawn_hooks'])} (present, not evaluated; owner rule: "
                               "no AI-authored spawn hooks in our version)")
        fog = T.get('fog')
        if isinstance(fog, list) and len(fog) >= 3 and min(fog[:3]) < FOG_MIN:
            add('fog_dark', f'fog {tuple(fog[:3])} is below the owner\'s ~{FOG_MIN} per channel')
        if T.get('supplied') and not T.get('babel'):
            add('txt_babel', "the .txt has no 'babel': True extension")
    D = rep.get('dna') or {}
    fl = D.get('floating') or {}
    if fl.get('count'):
        add('floating', f"{fl['count']} floating pieces ({fl['voxels']} voxels) not connected to the ground "
                        '(some may be intended sky decor)')
    sp = D.get('sealed_air_pockets') or {}
    if sp.get('count'):
        add('sealed', f"{sp['count']} sealed air pockets ({sp['voxels']} voxels; {sp.get('count_ge_27_voxels')} of "
                      '>= 27 voxels)')
    ss = D.get('spawn_to_spawn_steps') or {}
    vals = [v for v in ss.values() if isinstance(v, (int, float))]
    if len(vals) == 2 and max(vals) > 1.05 * min(vals):
        add('route_parity', f'spawn-to-spawn routes differ: {ss}')
    if any(v is None for k, v in ss.items() if k != 'error'):
        add('route_missing', f'a spawn cannot walk to the enemy spawn: {ss}')
    B = rep.get('babel') or {}
    if B.get('platform_volume_clear') is False:
        add('platform_volume', f"{B.get('platform_volume_z0_2_voxels')} map voxels inside the platform volume "
                               '(z 0-2 over the platform footprint)')
    for k, v in (B.get('ground_under_ends') or {}).items():
        if v.get('water_cols'):
            add(f'end_water_{k}', f"{v['water_cols']} water columns under the {k.replace('_', ' ')} of the platform")
    if B.get('anchors_equal') is False:
        e = B['ground_under_ends']
        add('anchors_unequal', 'unequal anchors: ' + '; '.join(
            f"{k.replace('_', ' ')} z {v['top_z_min']}-{v['top_z_max']}, {v['water_cols']} water columns"
            for k, v in e.items()))
    for t, v in (B.get('build_gap') or {}).items():
        g = v.get('blocks_to_platform_level')
        if v.get('platform_reachable_on_foot'):
            add(f'on_foot_{t}', f'{t} can reach the platform on foot (standard Babel needs a build)')
        elif g is not None and not (BUILD_GAP_REF[0] <= g <= BUILD_GAP_REF[1]):
            add(f'build_gap_{t}', f'{t} build gap {g} blocks is outside the community range {BUILD_GAP_REF[0]}-'
                                  f'{BUILD_GAP_REF[1]} (zone study proposal, not an owner rule)')
    gaps = [v.get('blocks_to_platform_level') for v in (B.get('build_gap') or {}).values()]
    if len(gaps) == 2 and None not in gaps and abs(gaps[0] - gaps[1]) > 2:
        add('build_gap_parity', f'build gaps differ between teams: {gaps}')
    for t, v in (B.get('spawn_squares') or {}).items():
        if v.get('over_air_cols'):
            add(f'spawn_roof_{t}', f"{v['over_air_pct']} % of {t} spawn spots land on roofs/canopies/decks "
                                   f"({v['over_air_cols']} of {SQUARE_SPOTS} columns; {v['roof_cols']} room-height roofs)")
        if v.get('water_cols'):
            add(f'spawn_water_{t}', f"{v['water_pct']} % of {t} spawn spots are water")
        if v.get('top_z_max', 0) - v.get('top_z_min', 0) > 6:
            add(f'spawn_flat_{t}', f"{t} spawn square spans z {v['top_z_min']}-{v['top_z_max']} (not easy, flat land)")
        if v.get('spots_not_reaching_own_end_pct'):
            add(f'spawn_reach_{t}', f"{v['spots_not_reaching_own_end_pct']} % of sampled {t} spawn spots cannot walk "
                                    'to their own platform end')
        if v.get('sealable'):
            add(f'spawn_seal_{t}', f"{t} spawn is sealable (exit min cut {v.get('exit_min_cut')} cells)")
    sq_eq = B.get('spawn_squares_mirror_equal_share')
    if sq_eq is not None and sq_eq < 0.9:
        add('spawn_unequal', f'spawn squares are not mirrored: {round(100 * sq_eq)} % of columns equal')
    E = (rep.get('exposure') or {}).get('teams') or {}
    for t, v in E.items():
        if _ok(v) and not (v.get('meets_viewers') and v.get('meets_hidden')):
            add(f'exposure_{t}', f"{t} spawn exposure {v['viewers_per_spot_mean']} viewers/spot, "
                                 f"{v['hidden_pct']} % hidden (targets <= 10, >= 15 %)")
    Z = rep.get('zones') or {}
    for k, st in (Z.get('status') or {}).items():
        if st == 'fail':
            add(f'zone_{k}', f"zone target {k}: {Z['why'][k]}")
    A = rep.get('art') or {}
    pt = A.get('pure_team_hue_top_pct') or {}
    for t in ('red', 'blue'):
        if (pt.get(t) or 0) >= 1:
            add(f'team_hue_{t}', f'{pt[t]} % of the top view is pure {t} (a team hue)')
    sf = A.get('surface') or {}
    if (sf.get('over_white_cap_pct') or 0) >= 1:
        top_hot = (A.get('colour_stats') or {}).get('top_bright_share_pct')
        add('too_white', f"{sf['over_white_cap_pct']} % of surface voxels exceed the white cap (max channel > "
                         f"{WHITE_CAP}; max {sf.get('max_channel')}; top view {top_hot} %); check whether they are "
                         'light/glow sources, which the kit exempts from the cap, or snow and plaster')
    fz = A.get('floor_luma') or {}
    if (fz.get('near_black_lt40_pct') or 0) >= 1:
        add('too_black', f"{fz['near_black_lt40_pct']} % of walkable tops are near black (luma < {LUMA_FLOOR_MIN}; "
                         f"darkest {fz.get('min')})")
    am = A.get('art_metrics') or {}
    if isinstance(am.get('hue_families_90'), int) and not 2 <= am['hue_families_90'] <= 4:
        add('hue_families', f"{am['hue_families_90']} hue families cover 90 % of the surface (target 2-4)")
    if isinstance(am.get('coherence_4'), (int, float)) and am['coherence_4'] < 1.5:
        add('coherence', f"colour coherence {am['coherence_4']} < 1.5 (per-voxel noise rather than gradients)")
    if (A.get('bright_share_top_pct') or 0) > 8:
        add('bright', f"bright share {A['bright_share_top_pct']} % of the top view (refs 7-8 %; keep low)")
    for key in ('identity', 'txt', 'dna', 'babel', 'exposure', 'zones', 'art', 'ledger'):
        v = rep.get(key)
        if isinstance(v, dict) and 'error' in v:
            add(f'error_{key}', f'section {key} could not be measured: {v["error"]}')
    return out


# =============================================================================================== driver

def _analyse(vxl_path, txt_path=None, fast=False, params=BABEL_DEFAULT):
    rep = {'tool': 'tools/recreate_analysis.py', 'mode': 'babel', 'fast': bool(fast),
           'status_rung': 'parser-validated read of a third-party file (numpy measurements only; no server, '
                          'no client)'}
    with open(vxl_path, 'rb') as f:              # read-only; nothing is ever written beside the input
        data = f.read()
    ctx = {'data': data}
    try:
        m, rrep = read_vxl(data)
    except Exception as e:                       # noqa: BLE001
        rep['identity'] = {'file': os.path.basename(vxl_path), 'path': vxl_path,
                           'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'reader_ok': False,
                           'error': f'{type(e).__name__}: {e}'}
        rep['txt'] = txt_section(resolve_txt(vxl_path, txt_path))
        rep['status_rung'] = 'not parseable (decode failed)'
        rep['problems'] = problems(rep, params)
        return jsonable(rep), ctx
    ctx['m'] = m
    rep['identity'] = identity_section(vxl_path, data, m, rrep, fast)
    if not rrep.ok:
        rep['status_rung'] = 'decoded with reader issues (numpy measurements only; no server, no client)'
    rep['txt'] = txt_section(resolve_txt(vxl_path, txt_path))
    F = zones.fields(m.solid)
    ctx['top'] = F['top']
    try:
        R = babel_checks.run_all(data, params=params, pyspades=False, zone_profile=not fast, zone_rules=True,
                                 timing=False)
    except Exception as e:                       # noqa: BLE001
        R = _fallback_checks(m, params)
        R['run_all_error'] = f'{type(e).__name__}: {e}'
    rep['babel_checks'] = R
    _run(rep, 'dna', dna_section, m, F, R, params)
    _run(rep, 'babel', babel_section, m, R, F, params)
    _run(rep, 'exposure', exposure_section, R, params)
    _run(rep, 'zones', zone_section, R)
    _run(rep, 'art', art_section, vxl_path, m, F)
    water = ((rep.get('dna') or {}).get('water') or {}).get('engine_water_cols_pct')
    if fast:
        rep['island'] = {'skipped': '--fast'}
    elif water is not None and water > 50:
        _run(rep, 'island', island_section, vxl_path, m, len(data))
    else:
        rep['island'] = {'skipped': f'water share {water} % <= 50 %'}
    _run(rep, 'ledger', ledger_section, m, F, params, rep.get('dna') or {})
    _run(rep, 'orientation', orientation_section, m)
    rep['problems'] = problems(rep, params)
    return jsonable(rep), ctx


def analyse(vxl_path, txt_path=None, fast=False, params=BABEL_DEFAULT) -> dict:
    """Full original-map analysis -> JSON-able dict (deterministic: same input -> same dict)."""
    return _analyse(vxl_path, txt_path, fast, params)[0]


def _key_numbers(rep):
    B, E, A, D = rep.get('babel') or {}, (rep.get('exposure') or {}).get('teams') or {}, rep.get('art') or {}, \
        rep.get('dna') or {}
    out = {'sha256': (rep.get('identity') or {}).get('sha256', '')[:12]}
    for t, v in (B.get('build_gap') or {}).items():
        out[f'build gap {t}'] = v.get('blocks_to_platform_level')
    for t, v in E.items():
        if _ok(v):
            out[f'exposure {t} (viewers / hidden %)'] = f"{v['viewers_per_spot_mean']} / {v['hidden_pct']}"
    for t, v in (B.get('spawn_squares') or {}).items():
        out[f'{t} spawn over air / water %'] = f"{v.get('over_air_pct')} / {v.get('water_pct')}"
    out['spawn to spawn steps'] = D.get('spawn_to_spawn_steps')
    out['platform volume voxels'] = B.get('platform_volume_z0_2_voxels')
    out['anchors equal'] = B.get('anchors_equal')
    out['floating pieces'] = (D.get('floating') or {}).get('count')
    out['sealed pockets'] = (D.get('sealed_air_pockets') or {}).get('count')
    for k, v in ((rep.get('zones') or {}).get('status') or {}).items():
        out[f'zone {k}'] = v
    am = A.get('art_metrics') or {}
    out['hue families'] = am.get('hue_families_90')
    out['coherence'] = am.get('coherence_4')
    out['bright share %'] = A.get('bright_share_top_pct')
    out['pure team hue top % (red / blue)'] = '%s / %s' % tuple((A.get('pure_team_hue_top_pct') or {}).get(t)
                                                              for t in ('red', 'blue'))
    out['problems'] = len(rep.get('problems') or [])
    return out


def compare(orig_rep, orig_ctx, new_path, new_txt=None, fast=False, params=BABEL_DEFAULT):
    """Fidelity section (remus report §4): heightfield correlation, mirror match, routes, key Babel numbers."""
    new_rep, new_ctx = _analyse(new_path, new_txt, fast, params)
    out = {'new_file': os.path.basename(new_path), 'new_sha256': (new_rep.get('identity') or {}).get('sha256')}
    a, b = orig_ctx.get('top'), new_ctx.get('top')
    if a is not None and b is not None:
        ha = np.where(a <= 63, 63 - a, 0).astype(float).ravel()
        hb = np.where(b <= 63, 63 - b, 0).astype(float).ravel()
        out['heightfield_correlation'] = _r(np.corrcoef(ha, hb)[0, 1], 3) if ha.std() and hb.std() else None
        out['top_z_equal_pct'] = _r(100 * (a == b).mean(), 1)
        out['mean_abs_height_diff'] = _r(np.abs(ha - hb).mean(), 2)
    for nm, r in (('original', orig_rep), ('new', new_rep)):
        mt = (r.get('dna') or {}).get('mirror_topz_match_pct') or {}
        out[f'mirror_x_{nm}_pct'] = max(mt.get('x511', 0), mt.get('x512', 0)) if mt else None
        out[f'routes_{nm}'] = (r.get('dna') or {}).get('spawn_to_spawn_steps')
    ko, kn = _key_numbers(orig_rep), _key_numbers(new_rep)
    out['side_by_side'] = [{'metric': k, 'original': ko.get(k), 'new': kn.get(k)} for k in dict.fromkeys(list(ko) + list(kn))]
    new_keys = {p['key'] for p in new_rep.get('problems') or []}
    out['problem_ledger'] = [{'problem': p['text'], 'key': p['key'],
                              'status_in_new': 'still present' if p['key'] in new_keys else 'not detected'}
                             for p in orig_rep.get('problems') or []]
    out['new_problems'] = [p for p in new_rep.get('problems') or []
                           if p['key'] not in {q['key'] for q in orig_rep.get('problems') or []}]
    return jsonable(out), new_rep


# =============================================================================================== report

def _v(x):
    if x is None:
        return 'n/a'
    if isinstance(x, bool):
        return 'yes' if x else 'no'
    return str(x)


def _err_line(sec):
    return f"_could not be measured: {sec['error']}_" if isinstance(sec, dict) and 'error' in sec else None


def render_md(rep):
    I, T, D, B = rep.get('identity') or {}, rep.get('txt') or {}, rep.get('dna') or {}, rep.get('babel') or {}
    name = I.get('file', '?')
    L = [f'# Recreate analysis: {name}', '',
         f"Generated by `tools/recreate_analysis.py`{' (--fast)' if rep.get('fast') else ''}. Every measured value is "
         '`[RUN]` on this file. Route numbers are a graph model (kit Nav), not in-game proof. Status: '
         f"{rep.get('status_rung')}. Any previews (`top.png`, `height.png`, `contours.png`, `sides.png`) are "
         '**numpy previews, not client captures**.', '']
    # 1 identity
    L += ['## 1. Identity', '', '| item | value |', '|---|---|']
    if 'error' in I and 'reencode' not in I:
        L += [f"| file | {name} |", f"| SHA-256 | `{I.get('sha256')}` |", f"| size | {I.get('bytes'):,} B |",
              f"| decode | **failed**: {I['error']} |"]
    else:
        L += [f'| file | {name} |', f"| SHA-256 | `{I['sha256']}` |", f"| size | {I['bytes']:,} B |",
              f"| our reader | {'ok' if I['reader_ok'] else 'issues: ' + str(I['reader_issues'][:3])} `[RUN]` |",
              f"| re-encode with our writer identical | {_v((I.get('reencode') or {}).get('reencode_identical'))} `[RUN]` |",
              f"| pyspades 1.4.2 loads | {_v(I.get('pyspades_loads'))} `[RUN]` |",
              f"| canonical encoding (= pyspades `generate()`) | {_v(I.get('canonical_encoding'))} `[RUN]` |",
              f"| z = 63 solid in every column | {_v(I.get('z63_solid_every_column'))} "
              f"({I.get('z63_air_columns')} columns without it) `[RUN]` |"]
    if not T.get('supplied'):
        L += ['| `.txt` | not supplied (author and settings unknown) |']
    else:
        L += [f"| `.txt` | `{T.get('file')}`, parsed with `ast` literals only, **never executed** |",
              f"| parsed | {'yes' if T.get('parsed') else 'no (not valid Python; regex fallback for name/author/description)'}"
              f"{'; ' + T['ast_error'] if T.get('ast_error') else ''} |",
              f"| name / author / version | {_v(T.get('name'))} / {_v(T.get('author'))} / {_v(T.get('version'))} |",
              f"| description | {_v(T.get('description'))} |",
              f"| fog | {_v(T.get('fog'))} |",
              f"| extensions keys | {', '.join(T.get('extension_keys') or []) or 'none'} |",
              f"| spawn hooks | {', '.join(T['spawn_hooks']) + ' (' + T['hooks_note'] + ')' if T.get('spawn_hooks') else 'none'} |",
              f"| functions defined | {', '.join(T.get('functions') or []) or 'none'} |"]
    L += ['']
    if 'dna' not in rep:
        L += ['_The file could not be decoded; nothing else was measured._']
        return '\n'.join(L) + '\n'
    # 2 DNA
    L += ['## 2. Map DNA `[RUN]`', '']
    e = _err_line(D)
    if e:
        L += [e, '']
    else:
        lv = D.get('dominant_levels') or []
        L += ['* **Height levels** (top z, share of all columns): ' + ', '.join(
            f"z {d['z']} (h {d['height']}) {d['share_of_all_cols_pct']} %" for d in lv[:5]) + '.',
              f"* **Flat walkable ground at the dominant level z {D.get('dominant_level_z')}**: "
              f"{D.get('flat_walkable_at_dominant_level_pct')} % of all columns "
              f"({D.get('flat_walkable_at_dominant_level_pct_of_land')} % of land); land {D.get('land_cols_pct')} %."]
        W = D.get('water') or {}
        bodies = (W.get('bodies') or {}).get('bodies') or []
        L += [f"* **Water**: {W.get('engine_water_cols_pct')} % of columns are engine water (top z 63); "
              f"{W.get('sea_level_land_z62_cols_pct')} % are sea-level land (z 62). "
              + (f"{len(bodies)} bodies >= 200 columns; largest: " + '; '.join(
                  f"{b['cols']} cols x {b['x']} y {b['y']}, kerb {b['kerb_height_median']}" for b in bodies[:3])
                 if bodies else 'No water body >= 200 columns.')]
        mt = D.get('mirror_topz_match_pct') or {}
        sv = D.get('symmetry_voxels') or {}
        L += [f"* **Mirror match (top z equal)**: x' = 511 - x {mt.get('x511')} %, x' = 512 - x {mt.get('x512')} %, "
              f"y511 {mt.get('y511')} %, y512 {mt.get('y512')} %, 180 deg {mt.get('point511')} / {mt.get('point512')} %. "
              f"Voxel symmetry type (kit): {sv.get('type')} (best {sv.get('best')}, mismatch {sv.get('best_mismatch')})."]
        fl, sp = D.get('floating') or {}, D.get('sealed_air_pockets') or {}
        L += [f"* **Floating components**: {fl.get('count')} ({fl.get('voxels')} voxels)"
              + (f"; largest {fl['largest'][0]['voxels']} voxels at x {fl['largest'][0]['x']} y {fl['largest'][0]['y']} "
                 f"z {fl['largest'][0]['z']}" if fl.get('largest') else '') + '.',
              f"* **Sealed air pockets**: {sp.get('count')} ({sp.get('voxels')} voxels; {sp.get('count_ge_27_voxels')} "
              'of >= 27 voxels).' if 'error' not in sp else f"* Sealed air pockets: {_err_line(sp)}"]
        hp = D.get('highest_point') or {}
        led = (rep.get('ledger') or {}).get('objects') or []
        tall = max(led, key=lambda r: r['height_above_ground']) if led else None
        L += [f"* **Highest point**: z {hp.get('top_z')} (height {hp.get('height')}) at x {hp.get('x')} y {hp.get('y')}"
              f" ({'/'.join(hp.get('zone') or [])})."
              + (f" Tallest detected object: {tall['element']} ({tall['height_above_ground']} above its ground, top z "
                 f"{tall['top_z']}, {tall['zone']}/{tall['side']})." if tall else '')]
        sd = D.get('solid_down') or {}
        L += [f"* **Solid all the way down**: {sd.get('solid_all_the_way_down_pct')} % of columns; air below the top in "
              f"{sd.get('air_below_top_pct')} % (room-height roofs {sd.get('roof_room_height_gap_pct')} %, decks/thin "
              f"gaps {sd.get('deck_or_thin_gap_pct')} %); mean air under the surface "
              f"{(D.get('basic') or {}).get('air_under_surface_mean')} voxels per land column."]
        L += [f"* **Spawn <-> spawn route** (safe drops): {D.get('spawn_to_spawn_steps')} steps; with drops <= 19: "
              f"{D.get('spawn_to_spawn_steps_any_drop')}.", '']
    # 3 Babel
    L += ['## 3. Babel fitness (stock constants, `BABEL_DEFAULT`) `[RUN]`', '']
    e = _err_line(B)
    if e:
        L += [e, '']
    else:
        P = B.get('params') or {}
        L += [f"Platform x {P.get('platform_x')}, y {P.get('platform_y')}, z {P.get('platform_z')}; bases "
              f"{P.get('bases')} +-{P.get('spawn_half')}.", '', '| check | value |', '|---|---|',
              f"| platform volume clear (z 0-2 over the footprint) | {_v(B.get('platform_volume_clear'))} "
              f"({B.get('platform_volume_z0_2_voxels')} voxels; platform layer z {P.get('platform_z')}: "
              f"{B.get('platform_layer_voxels')}; 1-column margin {B.get('platform_margin_z0_2_voxels')}) |"]
        for k, v in (B.get('ground_under_ends') or {}).items():
            L += [f"| ground under {k.replace('_', ' ')} | {v['kind']}, top z {v['top_z_min']}-{v['top_z_max']}, "
                  f"{v['water_cols']} water columns |"]
        L += [f"| anchors equal (ends' z range and water) | {_v(B.get('anchors_equal'))} |"]
        for t, v in (B.get('build_gap') or {}).items():
            L += [f"| build gap {t} | **{v['blocks_to_platform_level']}** blocks (highest walkable z "
                  f"{v['highest_walkable_z']}) |"]
        L += [f"| platform reachable on foot | {_v(B.get('platform_reachable_on_foot'))} |"]
        for k, v in (B.get('nearest_map_voxel_to_platform') or {}).items():
            if isinstance(v, dict) and 'distance' in v:
                L += [f"| {k.replace('_', ' ')} | {v['distance']} at {v['at']} |"]
        for t, v in (B.get('spawn_squares') or {}).items():
            L += [f"| {t} spawn square | z {v['top_z_min']}-{v['top_z_max']}, flat share {v['flat_share']}; over air "
                  f"{v['over_air_pct']} % (room-height roofs {v['roof_pct']} %), water {v['water_pct']} %, cannot walk "
                  f"to own end {_v(v.get('spots_not_reaching_own_end_pct'))} %, sealable {_v(v.get('sealable'))} |"]
        L += [f"| spawn squares mirror-equal | {B.get('spawn_squares_mirror_equal_share')} |"]
        if 'routes' in B:
            for t, v in B['routes'].items():
                L += [f"| {t} routes | own platform end {v['to_own_platform_end']} steps, safe descent to tower zone "
                      f"{_v(v['safe_descent_to_tower_zone'])}, reachable nodes {v['reachable_nodes_pct']} % |"]
            L += [f"| trap cells | {B['trap_cells']['count']} of {B['trap_cells']['of_cells']} |",
                  f"| flank route exists | {_v((B.get('flank') or {}).get('exists'))} "
                  f"({(B.get('flank') or {}).get('blue_to_red_cost')}) |"]
        if B.get('zone_class'):
            L += [f"| map class (kit zones.classify) | {B['zone_class']} |"]
        L += ['', f"Build gap = {B.get('build_gap_definition')}. Community range 38-54 (zone study proposal).", '']
    # 4 exposure
    X = rep.get('exposure') or {}
    L += ['## 4. Spawn exposure `[RUN]`', '', X.get('model', ''), '',
          '| team | viewers / spot (mean) | max | hidden % | targets (<= 10, >= 15 %) |', '|---|---|---|---|---|']
    for t, v in (X.get('teams') or {}).items():
        if _ok(v):
            L += [f"| {t} | {v['viewers_per_spot_mean']} | {v['viewers_max']} | {v['hidden_pct']} | "
                  f"{'met' if v['meets_viewers'] and v['meets_hidden'] else 'NOT met'} |"]
        else:
            L += [f'| {t} | {_err_line(v)} | | | |']
    L += ['']
    # 5 zones
    Z = rep.get('zones') or {}
    L += ['## 5. Zone targets (owner, 2026-11-13) `[RUN]`', '']
    e = _err_line(Z)
    if e:
        L += [e, '']
    else:
        L += [f"Object ground: {Z.get('object_ground')} (kit `zones.zone_rules`).", '',
              '| rule | status | why |', '|---|---|---|']
        for k, st in (Z.get('status') or {}).items():
            L += [f"| {k} | **{st.upper()}** | {Z['why'][k]} |"]
        L += ['', '| rule | team | metric | value | target | ok |', '|---|---|---|---|---|---|']
        for r in Z.get('rows') or []:
            L += [f"| {r['rule']} | {r['team']} | {r['metric']} | {r['value']} | {r['target']} | {_v(r['ok'])} |"]
        L += ['']
    # 6 art
    A = rep.get('art') or {}
    L += ['## 6. Art stats `[RUN]`', '']
    e = _err_line(A)
    if e:
        L += [e, '']
    else:
        am = A.get('art_metrics') or {}
        fz, sf = A.get('floor_luma') or {}, A.get('surface') or {}
        cs = A.get('colour_stats') or {}
        pt, ps = A.get('pure_team_hue_top_pct') or {}, A.get('pure_team_hue_surface_pct') or {}
        L += ['| metric | value | target / reference |', '|---|---|---|',
              f"| hue families covering 90 % | {am.get('hue_families_90')} | 2-4 |",
              f"| coherence (dL at 4 / dL at 1) | {am.get('coherence_4')} | >= 1.5 |",
              f"| side faces minus tops L* | {am.get('side_minus_top_L')} | -10 .. -20 |",
              f"| neighbour colour jump, top-down mean RGB | {A.get('neighbour_jump_mean')} | <~ 30 (reconstructed metric) |",
              f"| bright share (luma > {BRIGHT_LUMA}, top view) | {A.get('bright_share_top_pct')} % | refs 7-8 %, keep low |",
              f"| pure team hue, top view (red / blue) | {pt.get('red')} % / {pt.get('blue')} % | 0 |",
              f"| pure team hue, surface voxels (red / blue) | {ps.get('red')} % / {ps.get('blue')} % | 0 |",
              f"| darkest walkable top luma (min / p1 / p5) | {fz.get('min')} / {fz.get('p1')} / {fz.get('p5')} | >= 40 |",
              f"| near-black walkable tops (luma < 40) | {fz.get('near_black_lt40_pct')} % | 0 |",
              f"| near-black surface voxels | {sf.get('near_black_lt40_pct')} % | |",
              f"| max channel (max / p99) | {sf.get('max_channel')} / {sf.get('max_channel_p99')} | cap ~{WHITE_CAP} |",
              f"| surface voxels over the white cap (incl. light/glow sources) | {sf.get('over_white_cap_pct')} % | 0 |",
              f"| top view over the white cap (kit colour_stats) | {cs.get('top_bright_share_pct')} % | 0 |",
              f"| top luma median (kit colour_stats) | {cs.get('top_luma_median')} | |",
              f"| unique surface colours | {am.get('colours')} | |", '',
              'Hue shares: ' + ', '.join(f'{k} {v} %' for k, v in (A.get('hue_shares_pct') or {}).items()) + '.', '',
              'Most used surface colours: ' + ', '.join(f"{c['colour']} {c['share_pct']} %"
                                                       for c in A.get('top_surface_colours') or []) + '.', '']
    # 7 island
    IS = rep.get('island') or {}
    L += ['## 7. Island style', '']
    if 'skipped' in IS:
        L += [f"Not measured: {IS['skipped']}.", '']
    elif _err_line(IS):
        L += [_err_line(IS), '']
    else:
        L += [f"Water {IS.get('water_pct')} %, landmasses {IS.get('landmasses')} {IS.get('landmass_sizes')}, main "
              f"island bbox {IS.get('main_bbox')} (aspect {IS.get('main_aspect_x_over_y')}, neck "
              f"{IS.get('main_neck_min_y_width')}), beach-ring low share {IS.get('beach_ring_low_pct')} %.", '',
              '| metric | classic range | this map | in range |', '|---|---|---|---|']
        for c in IS.get('classic') or []:
            L += [f"| {c['metric']}{'' if c['separates'] else ' (info)'} | {c['lo']}-{c['hi']} | {c['value']} | "
                  f"{_v(c['in_range'])} |"]
        L += ['']
    # 8 problems
    L += ['## 8. Problems found', '']
    pr = rep.get('problems') or []
    L += [f"* {p['text']}" for p in pr] if pr else ['* none of the measured targets failed']
    L += ['']
    # 9 ledger
    LG = rep.get('ledger') or {}
    L += ['## 9. Element ledger (skeleton)', '']
    e = _err_line(LG)
    if e:
        L += [e, '']
    else:
        L += [f"Detected candidates only; name the real elements and fill **verdict** (Keep / Reimagine / Replace / "
              f"Remove / Add) and **result** yourself. {LG.get('note')}. {LG.get('objects_total')} objects in total; the "
              f"{len(LG.get('objects') or [])} largest are listed.", '',
              '| element | where | size | verdict | result |', '|---|---|---|---|---|']
        for r in LG.get('objects') or []:
            L += [f"| {r['label']} | {r['zone']} ({r['side']}), x {r['x'][0]}-{r['x'][1]} y {r['y'][0]}-{r['y'][1]} | "
                  f"{r['footprint_cells']} cells, {r['height_above_ground']} tall, top z {r['top_z']}, {r['colour']} | | |"]
        for b in LG.get('water_bodies') or []:
            L += [f"| {b['name']} | {b['zone']}, x {b['x'][0]}-{b['x'][1]} y {b['y'][0]}-{b['y'][1]} | {b['cols']} "
                  f"columns, kerb {b['kerb_height_median']}{', reaches the map edge' if b['touches_map_edge'] else ''} | | |"]
        for t in LG.get('terrain_levels') or []:
            L += [f"| {t['element']} | largest region x {t['largest_region_x'][0]}-{t['largest_region_x'][1]} y "
                  f"{t['largest_region_y'][0]}-{t['largest_region_y'][1]} ({t['regions']} regions) | "
                  f"{t['share_of_land_pct']} % of land | | |"]
        L += ['']
    # 10 orientation
    O = rep.get('orientation') or {}
    L += ['## 10. Orientation', '']
    e = _err_line(O)
    if e:
        L += [e, '']
    else:
        L += ['Region grid (64 x 64 cells; A-H = x west -> east, 1-8 = y north -> south): land % h(mean)/(max) '
              'd(surface voxels per land column) dominant top colour.', '',
              '| | ' + ' | '.join('ABCDEFGH') + ' |', '|---' * 9 + '|']
        for row in O.get('region_grid') or []:
            L.append(f"| {row[0]['cell'][1:]} | " + ' | '.join(
                f"{c['land_pct']}% h{c['h_mean']}/{c['h_max']} d{c['detail']} {c['colour']}" for c in row) + ' |')
        L += ['', '```', O.get('ascii_height', ''), '```', '']
    # fidelity
    C = rep.get('compare')
    if C:
        L += ['## Fidelity (original vs new) `[RUN]`', '']
        if _err_line(C):
            L += [_err_line(C), '']
        else:
            L += [f"New: `{C.get('new_file')}` (`{(C.get('new_sha256') or '')[:16]}...`).", '',
                  f"* Heightfield (top-z height) correlation: **{C.get('heightfield_correlation')}**; equal top z in "
                  f"{C.get('top_z_equal_pct')} % of columns; mean |height difference| {C.get('mean_abs_height_diff')}.",
                  f"* Mirror match (best x axis, top z): original {C.get('mirror_x_original_pct')} %, new "
                  f"{C.get('mirror_x_new_pct')} %.",
                  f"* Spawn <-> spawn steps: original {C.get('routes_original')}, new {C.get('routes_new')}.", '',
                  '| metric | original | new |', '|---|---|---|']
            for r in C.get('side_by_side') or []:
                L += [f"| {r['metric']} | {_v(r['original'])} | {_v(r['new'])} |"]
            L += ['', '| original problem | in the new map |', '|---|---|']
            L += [f"| {p['problem']} | {p['status_in_new']} |" for p in C.get('problem_ledger') or []]
            if C.get('new_problems'):
                L += ['', 'New problems (not in the original): ' + '; '.join(p['text'] for p in C['new_problems'])]
            L += ['']
    tm = rep.get('timing')
    if tm:
        L += [f"_Wall time: {tm}._", '']
    return '\n'.join(L) + '\n'


def write_report(rep, out_dir, render=True):
    """analysis.json + analysis.md (+ numpy previews) into out_dir. Renders re-read the vxl (read-only) and check its
    SHA-256 against the analysis."""
    I = rep.get('identity') or {}
    src = I.get('path')
    if src and os.path.abspath(out_dir) == os.path.abspath(os.path.dirname(src)):
        raise SystemExit('refusing to write beside the input map; choose another --out')
    os.makedirs(out_dir, exist_ok=True)
    written = []
    if render and src and I.get('reader_ok') is not False and 'dna' in rep:
        try:
            with open(src, 'rb') as f:
                data = f.read()
            if hashlib.sha256(data).hexdigest() != I.get('sha256'):
                raise ValueError('input changed since the analysis')
            m, _ = read_vxl(data)
            from PIL import Image, ImageDraw
            va.top_view(m).save(os.path.join(out_dir, 'top.png'))
            va.height_view(m).save(os.path.join(out_dir, 'height.png'))
            va.contour_view(m).save(os.path.join(out_dir, 'contours.png'))
            sides = [va.side_view(m, f) for f in ('south', 'north', 'west', 'east')]
            sheet = Image.new('RGB', (512, sum(i.height + 14 for i in sides)), (15, 15, 18))
            dr = ImageDraw.Draw(sheet)
            yy = 0
            for f, im in zip(('from south (looking north) - numpy preview', 'from north', 'from west', 'from east'),
                             sides):
                dr.text((4, yy), f, fill=(230, 230, 230))
                sheet.paste(im, (0, yy + 14))
                yy += im.height + 14
            sheet.save(os.path.join(out_dir, 'sides.png'))
            written = ['top.png', 'height.png', 'contours.png', 'sides.png']
        except Exception as e:                   # noqa: BLE001
            rep['render_error'] = f'{type(e).__name__}: {e}'
    rep['previews'] = written
    with open(os.path.join(out_dir, 'analysis.json'), 'w', encoding='utf-8') as f:
        json.dump(jsonable(rep), f, indent=1, sort_keys=False)
    md = render_md(rep)
    if written:
        md += '\nPreviews (numpy, not client captures): ' + ', '.join(f'`{w}`' for w in written) + '\n'
    if rep.get('render_error'):
        md += f"\n_Render failed: {rep['render_error']}_\n"
    with open(os.path.join(out_dir, 'analysis.md'), 'w', encoding='utf-8') as f:
        f.write(md)
    return out_dir


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('vxl')
    ap.add_argument('--txt', help='the original .txt (default: same stem beside the .vxl, if present)')
    ap.add_argument('--out', help='output dir (default out/recreate/<stem>)')
    ap.add_argument('--mode', default='babel')
    ap.add_argument('--compare', metavar='NEW.vxl', help='add a fidelity section against the recreated map')
    ap.add_argument('--compare-txt', help='the new map\'s .txt (default: beside it)')
    ap.add_argument('--no-render', action='store_true')
    ap.add_argument('--fast', action='store_true', help='skip zone_profile, pyspades, island metrics (see docstring)')
    a = ap.parse_args(argv)
    if a.mode not in MODES:
        ap.error(f"--mode {a.mode!r} is not supported yet (supported: {', '.join(MODES)})")
    if not os.path.isfile(a.vxl):
        ap.error(f'not a file: {a.vxl}')
    out = a.out or os.path.join(ROOT, 'out', 'recreate', os.path.splitext(os.path.basename(a.vxl))[0])
    t0 = time.time()
    rep, ctx = _analyse(a.vxl, a.txt, a.fast)
    t1 = time.time()
    timing = {'analyse_s': round(t1 - t0, 1)}
    if a.compare:
        try:
            rep['compare'], _ = compare(rep, ctx, a.compare, a.compare_txt, a.fast)
        except Exception as e:                   # noqa: BLE001
            rep['compare'] = _err(e)
        timing['compare_s'] = round(time.time() - t1, 1)
    t2 = time.time()
    rep['timing'] = timing
    write_report(rep, out, render=not a.no_render)
    timing['write_s'] = round(time.time() - t2, 1)
    timing['total_s'] = round(time.time() - t0, 1)
    with open(os.path.join(out, 'analysis.json'), 'w', encoding='utf-8') as f:     # final timing in the json too
        json.dump(jsonable(rep), f, indent=1)
    print(f"{rep['identity'].get('file')}: {len(rep.get('problems') or [])} problems; "
          f"report {os.path.join(out, 'analysis.md')} ({timing['total_s']} s)")
    return rep


if __name__ == '__main__':
    main()
