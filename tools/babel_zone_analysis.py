"""Analysis of out/zone_study/metrics.json (written by tools/babel_zone_study.py).

    python tools/babel_zone_analysis.py [--out out/zone_study]

Writes out/zone_study/analysis.json, analysis.md (tables used in docs/babel_zone_study.md) and top-down
thumbnails (numpy previews, out/zone_study/thumbs/) for exemplars and our maps. Community renders stay in out/.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy.stats import mannwhitneyu

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT)
from aosmap.kit.params import BABEL_DEFAULT  # noqa: E402

# (key, path in zone_profile, label, zone)
HEADLINE = [
    ('sp_viewers', 'avg.spawn.platform_viewers_mean', 'platform viewers / spawn spot', 'spawn'),
    ('sp_hidden', 'avg.spawn.platform_hidden_pct', 'spawn spots hidden from platform %', 'spawn'),
    ('sp_angle', 'avg.spawn.platform_angle_deg', 'angle platform end -> base (deg)', 'spawn'),
    ('sp_drop', 'avg.spawn.platform_drop', 'spawn floor below platform (blocks)', 'spawn'),
    ('sp_flat', 'avg.spawn.near_mode_share', 'spawn square within +-1 of mode', 'spawn'),
    ('sp_rough', 'avg.spawn.roughness', 'spawn roughness (mean |dz|)', 'spawn'),
    ('sp_above_front', 'avg.spawn.height_above_front', 'spawn height above front (blocks)', 'spawn'),
    ('sp_cov_e0', 'avg.spawn.enclosure.r0_8_enemy_cover3', 'cover>=3 share, 0-8 enemy side', 'spawn'),
    ('sp_cov_e8', 'avg.spawn.enclosure.r8_20_enemy_cover3', 'cover>=3 share, 8-20 enemy side', 'spawn'),
    ('sp_cov_l8', 'avg.spawn.enclosure.r8_20_lateral_cover3', 'cover>=3 share, 8-20 lateral', 'spawn'),
    ('sp_cov_r20', 'avg.spawn.enclosure.r20_40_rear_cover3', 'cover>=3 share, 20-40 rear', 'spawn'),
    ('sp_cut', 'avg.spawn.exit_min_cut', 'spawn exit min cut (cells)', 'spawn'),
    ('sp_seen_tz', 'avg.spawn.seen_from_tower_zone_ground_share', 'spawn spots seen from own tower-zone ground', 'spawn'),
    ('sp_seen_c', 'avg.spawn.seen_from_centre_ground_share', 'spawn spots seen from centre ground', 'spawn'),
    ('sp_steps', 'avg.spawn.steps_to_own_end_median', 'steps spawn spot -> own platform end (median)', 'spawn'),
    ('sp_detour', 'avg.spawn.detour_to_own_end_median', 'detour ratio spawn -> own end (median)', 'spawn'),
    ('fr_raised', 'avg.front.raised_vs_spawn', 'front height vs spawn (blocks)', 'front'),
    ('fr_slope', 'avg.front.slope_per10_toward_platform', 'front slope (blocks/10 toward platform)', 'front'),
    ('fr_flat', 'avg.front.flat_share', 'front flat share (+-1 of median)', 'front'),
    ('fr_water', 'avg.front.water_share', 'front water share', 'front'),
    ('fr_obj', 'avg.front.object_share', 'front object share', 'front'),
    ('fr_nobj', 'avg.front.objects', 'front objects (count)', 'front'),
    ('fr_objh', 'avg.front.object_h.p90', 'front object height p90', 'front'),
    ('fr_free8', 'avg.front.free_share_min_section8', 'front min free share per 8-col section', 'front'),
    ('fr_width', 'avg.front.land_width_min', 'front land width min', 'front'),
    ('fr_gap', 'avg.front.build_gap_blocks', 'build gap (blocks)', 'front'),
    ('fr_los', 'avg.front.los_toward_platform_mean', 'front LOS toward platform', 'front'),
    ('fr_seen', 'avg.front.seen_from_enemy_tower_zone_share', 'front seen from enemy tower zone', 'front'),
    ('ce_gap', 'centre.strip.min_gap_to_platform', 'min gap under platform (blocks)', 'centre'),
    ('ce_sobj', 'centre.strip.object_share', 'under-platform object share', 'centre'),
    ('ce_water', 'centre.strip.water_share', 'under-platform water share', 'centre'),
    ('cz_land', 'centre.zone.land_share', 'central zone land share', 'centre'),
    ('cz_obj', 'centre.zone.object_share', 'central zone object share', 'centre'),
    ('cz_n', 'centre.zone.objects_per_10k', 'central objects per 10k cols', 'centre'),
    ('cz_h', 'centre.zone.object_height.p90', 'central object height p90', 'centre'),
    ('cz_vol', 'centre.zone.built_volume_per_col', 'central built volume / col', 'centre'),
    ('cz_gap', 'centre.zone.gap_width.p50', 'gap between objects p50', 'centre'),
    ('cz_empty', 'centre.zone.largest_empty_diam', 'largest empty disk diam', 'centre'),
    ('cz_indoor', 'centre.zone.indoor_share', 'central indoor share', 'centre'),
    ('cz_multi', 'centre.zone.multilevel_share', 'central multi-level share', 'centre'),
    ('cz_cross', 'centre.zone.crossing_width', 'central crossing width (cells)', 'centre'),
    ('cz_los', 'centre.zone.los_mean', 'central LOS mean', 'centre'),
    ('cz_los90', 'centre.zone.los_p90', 'central LOS p90', 'centre'),
    ('cz_seen', 'centre.zone.seen_from_ends', 'central cells seen from platform ends', 'centre'),
    ('rt_steps', 'routes.spawn_to_enemy_spawn_steps', 'steps spawn -> enemy spawn', 'centre'),
    ('rt_flank', 'routes.flank_ratio', 'flank / direct length', 'centre'),
    ('rt_cross', 'routes.map_crossing_width', 'whole-map crossing width', 'centre'),
    ('mp_land', 'map.land_share', 'map land share', 'map'),
]


def get(zp, path):
    if path == 'centre.zone.seen_from_ends':
        z = (zp.get('centre') or {}).get('zone') or {}
        a, b = z.get('seen_from_blue_end_share'), z.get('seen_from_red_end_share')
        return None if a is None or b is None else (a + b) / 2
    cur = zp
    for k in path.split('.'):
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur if isinstance(cur, (int, float)) and not isinstance(cur, bool) else None


def dist(vals):
    v = np.array([x for x in vals if x is not None], float)
    if not len(v):
        return {'n': 0}
    q = np.percentile(v, [10, 25, 50, 75, 90])
    return {'n': int(len(v)), 'p10': round(q[0], 2), 'p25': round(q[1], 2), 'p50': round(q[2], 2),
            'p75': round(q[3], 2), 'p90': round(q[4], 2)}


def pctile(vals, x):
    v = np.array([y for y in vals if y is not None], float)
    if x is None or not len(v):
        return None
    return round(100 * (np.sum(v < x) + 0.5 * np.sum(v == x)) / len(v))


def fmt(x, nd=2):
    if x is None:
        return '-'
    if isinstance(x, float):
        return f'{x:.{nd}f}'.rstrip('0').rstrip('.') if abs(x) < 1000 else f'{x:.0f}'
    return str(x)


# =============================================================================================== thumbnails

def thumb(cache, key, path, crop=(58, 454, 116, 396), scale=2):
    z = np.load(os.path.join(cache, key + '_top.npz'))
    top, rgb = z['top'].astype(float), z['rgb'].astype(float)
    water = top >= 62
    rgb[water] = rgb[water] * 0.6 + np.array([40, 80, 140]) * 0.4
    # hillshade from the top field
    gx = np.gradient(-top, axis=0)
    gy = np.gradient(-top, axis=1)
    shade = np.clip(1.0 + 0.12 * (-gx - gy), 0.55, 1.35)
    img = np.clip(rgb * shade[..., None], 0, 255).astype(np.uint8)
    x0, x1, y0, y1 = crop
    im = Image.fromarray(img[x0:x1, y0:y1].transpose(1, 0, 2))      # rows = y, cols = x
    im = im.resize(((x1 - x0) * scale, (y1 - y0) * scale), Image.NEAREST)
    d = ImageDraw.Draw(im)
    P = BABEL_DEFAULT
    (px0, px1), (py0, py1) = P['platform_x'], P['platform_y']
    half = P['spawn_half']

    def rect(a, b, c, e, col):
        d.rectangle([((a - x0) * scale, (c - y0) * scale), ((b - x0 + 1) * scale - 1, (e - y0 + 1) * scale - 1)],
                    outline=col, width=2)
    for bx, by in P['bases']:
        rect(bx - half, bx + half, by - half, by + half, (255, 255, 255))
    rect(98 + 41, px0 + 5, 236, 276, (255, 220, 0))
    rect(px1 - 5, 414 - 41, 236, 276, (255, 220, 0))
    rect(px0, px1, py0, py1, (0, 255, 255))
    rect(150, 362, 130, 382, (255, 120, 255))
    d.text((4, 4), 'numpy preview - not a client capture', fill=(255, 255, 255))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)


# =============================================================================================== exemplars

def spawn_ok(zp):
    s = zp['avg']['spawn']
    return (zp['class']['stock_fit'] and s['platform_viewers_mean'] <= 9 and s['platform_hidden_pct'] >= 15 and
            not any(zp['teams'][t]['spawn'].get('sealable') for t in zp['teams']) and
            s['roof_cols'] <= 20 and s['water_cols'] <= 20)


def front_ok(zp):
    f = zp['avg']['front']
    return (zp['class']['stock_fit'] and f['anchor_water_cols'] == 0 and f['land_width_min'] >= 32 and
            0.05 <= f['object_share'] <= 0.30 and (f['object_h'].get('p90') or 0) <= 10 and
            f['free_share_min_section8'] >= 0.5 and f['build_gap_blocks'] is not None and
            15 <= f['build_gap_blocks'] <= 55 and abs(f['raised_vs_spawn']) <= 6)


def centre_ok(zp):
    z = zp['centre']['zone']
    r = zp['routes']
    return (zp['class']['stock_fit'] and z['object_share'] >= 0.12 and (z.get('crossing_width') or 0) >= 40 and
            6 <= (z['gap_width'].get('p50') or 0) <= 14 and r.get('flank_exists') and (z.get('los_mean') or 999) <= 60)


def describe(zone, zp):
    a, c, r = zp['avg'], zp['centre'], zp['routes']
    s, f, z = a['spawn'], a['front'], c['zone']
    if zone == 'spawn':
        e = s['enclosure']
        return (f"Spawn floor z {s['floor_z']:.0f} ({s['platform_drop']:.0f} below platform, {s['platform_angle_deg']}°), "
                f"{100 * s['near_mode_share']:.0f} % within ±1 of the mode, roughness {s['roughness']:.2f}. "
                f"Cover >= 3 high: {100 * e.get('r0_8_enemy_cover3', 0):.0f} % / {100 * e.get('r8_20_enemy_cover3', 0):.0f} % "
                f"of the 0-8 / 8-20 enemy-side rings, {100 * e.get('r8_20_lateral_cover3', 0):.0f} % lateral, "
                f"{100 * e.get('r20_40_rear_cover3', 0):.0f} % rear backdrop. "
                f"{s['platform_viewers_mean']:.1f} platform viewers/spot, {s['platform_hidden_pct']:.0f} % hidden; "
                f"exit min cut {s.get('exit_min_cut')} cells.")
    if zone == 'front':
        return (f"Front {f['raised_vs_spawn']:+.1f} blocks vs spawn, slope {f['slope_per10_toward_platform']:+.2f}/10, "
                f"{100 * f['flat_share']:.0f} % flat, land width min {f['land_width_min']}. "
                f"{f['objects']:.0f} objects covering {100 * f['object_share']:.0f} % (height p90 {f['object_h'].get('p90')}), "
                f"min free share per 8-column section {100 * f['free_share_min_section8']:.0f} %. "
                f"Build gap {f['build_gap_blocks']} blocks; LOS toward platform {f.get('los_toward_platform_mean')}.")
    return (f"Central zone {100 * z['object_share']:.0f} % object columns, {z['objects_per_10k']} objects/10k cols "
            f"(height p90 {z['object_height'].get('p90')}), gaps p50 {z['gap_width'].get('p50')}, "
            f"largest empty disk {z['largest_empty_diam']}. Indoor {100 * (z.get('indoor_share') or 0):.0f} %, "
            f"multi-level {100 * (z.get('multilevel_share') or 0):.0f} %, crossing width {z.get('crossing_width')}, "
            f"LOS mean {z.get('los_mean')}. Under platform: gap {c['strip']['min_gap_to_platform']}, "
            f"objects {100 * c['strip']['object_share']:.0f} %. Flank/direct {r.get('flank_ratio')}.")


# =============================================================================================== main

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(ROOT, 'out', 'zone_study'))
    a = ap.parse_args(argv)
    M = json.load(open(os.path.join(a.out, 'metrics.json')))
    cache = os.path.join(a.out, 'cache')
    maps = M['maps']
    com = [m for m in maps if m['source'] == 'community']
    ours = [m for m in maps if m['source'] == 'ours']

    def rotated(m):
        return m['zone_profile']['map']['symmetry']['type'].startswith('y')
    main_set = [m for m in com if m['zone_profile']['class']['stock_fit'] and not rotated(m)]
    groups = {'all': main_set,
              'guide_good': [m for m in main_set if 'guide_good' in m['labels']],
              'guide_rotation': [m for m in main_set if 'guide_rotation' in m['labels']],
              'guide_problem': [m for m in main_set if 'guide_problem' in m['labels']],
              'ground': [m for m in main_set if m['zone_profile']['class']['class'] == 'ground']}
    A = {'corpus': {'candidates': M['n_candidates'], 'decoded': M['n_decoded'], 'unique': M['n_unique'],
                    'profiled': len(com), 'main_set': len(main_set),
                    'excluded_not_stock_fit': sorted(m['name'] for m in com
                                                     if not m['zone_profile']['class']['stock_fit']),
                    'excluded_rotated': sorted(m['name'] for m in com if rotated(m) and
                                               m['zone_profile']['class']['stock_fit']),
                    'decode_failed': M['log']['decode_failed'], 'profile_failed': M['log']['profile_failed'],
                    'runtime_s': M['runtime_s']}}
    cnt = {}
    for key in ('class', 'assist'):
        cnt[key] = {}
        for m in com:
            v = str(m['zone_profile']['class'][key])
            cnt[key][v] = cnt[key].get(v, 0) + 1
    cnt['symmetry'] = {}
    for m in com:
        v = m['zone_profile']['map']['symmetry']['type']
        cnt['symmetry'][v] = cnt['symmetry'].get(v, 0) + 1
    A['corpus']['counts'] = cnt
    A['corpus']['main_counts'] = {c: sum(1 for m in main_set if m['zone_profile']['class']['class'] == c)
                                  for c in ('ground', 'island', 'sky_bridge')}
    A['groups'] = {g: sorted(m['name'] for m in ms) for g, ms in groups.items() if g != 'all'}
    # distributions
    D = {}
    for key, path, label, zone in HEADLINE:
        D[key] = {'label': label, 'zone': zone, 'path': path}
        for g, ms in groups.items():
            D[key][g] = dist([get(m['zone_profile'], path) for m in ms])
        gv = [get(m['zone_profile'], path) for m in groups['guide_good']]
        pv = [get(m['zone_profile'], path) for m in groups['guide_problem']]
        gv, pv = [x for x in gv if x is not None], [x for x in pv if x is not None]
        if len(gv) >= 4 and len(pv) >= 4:
            D[key]['good_vs_problem_p'] = round(float(mannwhitneyu(gv, pv).pvalue), 3)
        allv = [get(m['zone_profile'], path) for m in main_set]
        D[key]['ours'] = {o['name']: {'v': get(o['zone_profile'], path), 'pct': pctile(allv, get(o['zone_profile'],
                                                                                                    path))}
                          for o in ours}
    A['distributions'] = D
    # benchmark comparison
    bench = [o for o in ours if o.get('benchmark')]
    other = [o for o in ours if not o.get('benchmark')]
    B = {}
    for key, path, label, zone in HEADLINE:
        bv = [get(o['zone_profile'], path) for o in bench]
        ov = [get(o['zone_profile'], path) for o in other]
        ov = [x for x in ov if x is not None]
        if None in bv or not ov:
            continue
        iqr = (D[key]['all'].get('p75', 0) - D[key]['all'].get('p25', 0)) or 1e-9
        lo, hi, med = min(ov), max(ov), float(np.median(ov))
        if all(x > hi for x in bv) or all(x < lo for x in bv):
            verdict = 'clear (both benchmarks outside the range of our other maps)'
        elif (all(x > med for x in bv) or all(x < med for x in bv)) and abs(np.mean(bv) - med) >= 0.5 * iqr:
            verdict = 'weak (same side of our others median, >= 0.5 community IQR away)'
        else:
            verdict = 'no clear difference'
        n_beyond = sum(1 for x in ov if (x > max(bv) if np.mean(bv) > med else x < min(bv)))
        B[key] = {'label': label, 'zone': zone, 'benchmarks': bv, 'others_median': round(med, 2),
                  'others_range': [round(lo, 2), round(hi, 2)], 'verdict': verdict,
                  'bench_pct': [pctile([get(m['zone_profile'], path) for m in main_set], x) for x in bv],
                  'others_on_bench_side': n_beyond,
                  'others': {o['name']: get(o['zone_profile'], path) for o in other}}
    A['benchmark_comparison'] = B
    # exemplars
    E = {}
    for zone, ok, rank in (('spawn', spawn_ok, lambda zp: zp['avg']['spawn']['platform_hidden_pct']),
                           ('front', front_ok, lambda zp: zp['avg']['front']['objects']),
                           ('centre', centre_ok, lambda zp: zp['centre']['zone']['objects_per_10k'])):
        cand = [m for m in main_set if ok(m['zone_profile']) and 'guide_problem' not in m['labels']]
        cand.sort(key=lambda m: (-(('guide_good' in m['labels']) + ('guide_rotation' in m['labels'])),
                                 -rank(m['zone_profile'])))
        pick = cand[:8]
        E[zone] = {'criteria_pass': len(cand), 'picked': []}
        for m in pick:
            fn = os.path.join(a.out, 'thumbs', f'{zone}_{m["name"]}.png')
            try:
                thumb(cache, m['cache_key'], fn)
            except Exception as e:     # noqa: BLE001
                fn = f'thumb failed: {e}'
            E[zone]['picked'].append({'name': m['name'], 'labels': m['labels'], 'aliases': m['aliases'],
                                      'class': m['zone_profile']['class'],
                                      'description': describe(zone, m['zone_profile']), 'thumb': fn})
        E[zone]['all_passing'] = [m['name'] for m in cand]
        E[zone]['problem_maps_passing'] = [m['name'] for m in main_set
                                           if ok(m['zone_profile']) and 'guide_problem' in m['labels']]
    A['exemplars'] = E
    for o in ours:
        try:
            thumb(cache, o['cache_key'], os.path.join(a.out, 'thumbs', f'ours_{o["name"].replace(" ", "_").replace("/", "_")}.png'))
        except Exception as e:     # noqa: BLE001
            print('thumb failed', o['name'], e)
    # our maps' exemplar criteria pass/fail
    A['ours_criteria'] = {o['name']: {'spawn': bool(spawn_ok(o['zone_profile'])),
                                      'front': bool(front_ok(o['zone_profile'])),
                                      'centre': bool(centre_ok(o['zone_profile']))} for o in ours}
    json.dump(A, open(os.path.join(a.out, 'analysis.json'), 'w'), indent=1, default=str)
    write_md(A, ours, os.path.join(a.out, 'analysis.md'))
    print('wrote analysis.json / analysis.md')


def write_md(A, ours, path):
    L = []
    c = A['corpus']
    L.append(f"Corpus: {c['candidates']} candidates, {c['decoded']} decoded, {c['unique']} unique, main set {c['main_set']}.")
    L.append(f"Counts: {json.dumps(c['counts'])}; main set by class {json.dumps(c['main_counts'])}")
    L.append('')
    short = {o['name']: o['name'].split(' v')[0].split(' (')[0][:14] for o in ours}
    L.append('| metric | all p10 | p25 | p50 | p75 | p90 | ground p50 (n) | good p50 (n) | problem p50 (n) | p (MWU) | ' +
             ' | '.join(short[o['name']] for o in ours) + ' |')
    L.append('|' + '---|' * (10 + len(ours)))
    for key, d in A['distributions'].items():
        al, g, p = d['all'], d['guide_good'], d['guide_problem']
        row = [d['label'], fmt(al.get('p10')), fmt(al.get('p25')), fmt(al.get('p50')), fmt(al.get('p75')),
               fmt(al.get('p90')), f"{fmt(d['ground'].get('p50'))} ({d['ground']['n']})", f"{fmt(g.get('p50'))} ({g['n']})", f"{fmt(p.get('p50'))} ({p['n']})",
               fmt(d.get('good_vs_problem_p'), 3)]
        for o in ours:
            v = d['ours'][o['name']]
            row.append(f"{fmt(v['v'])} ({v['pct']})" if v['v'] is not None else '-')
        L.append('| ' + ' | '.join(row) + ' |')
    L.append('')
    L.append('| metric | SH | WKH | others median | others range | verdict | others on bench side |')
    L.append('|---|---|---|---|---|---|---|')
    for key, b in A['benchmark_comparison'].items():
        L.append(f"| {b['label']} | {fmt(b['benchmarks'][0])} | {fmt(b['benchmarks'][1])} | {fmt(b['others_median'])} | "
                 f"{fmt(b['others_range'][0])}..{fmt(b['others_range'][1])} | {b['verdict']} | {b['others_on_bench_side']} |")
    L.append('')
    for zone, e in A['exemplars'].items():
        L.append(f"### {zone}: {e['criteria_pass']} pass")
        for p in e['picked']:
            L.append(f"* **{p['name']}** {p['labels']} {p['class']['class']}: {p['description']}")
        L.append('')
    open(path, 'w', encoding='utf-8').write('\n'.join(L))


if __name__ == '__main__':
    main()
