"""Summarise out/craft_study/metrics.json (+ our maps) into tables for docs/craft_standard.md.

    python tools/craft_study_report.py [--study out/craft_study] [--ours out/craft_study_ours] [--out out/craft_study/report.json]
"""
import argparse
import json
import os
from collections import Counter, defaultdict

import numpy as np


def pct(vals, qs=(10, 25, 50, 75, 90)):
    v = np.array([x for x in vals if x is not None and np.isfinite(x)], float)
    return {f'p{q}': round(float(np.percentile(v, q)), 3) for q in qs} | {'n': int(len(v))} if len(v) else {'n': 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--study', default='out/craft_study')
    ap.add_argument('--ours', default='out/craft_study_ours')
    ap.add_argument('--out', default='out/craft_study/report.json')
    a = ap.parse_args()
    rows = json.load(open(os.path.join(a.study, 'metrics.json')))
    ours = json.load(open(os.path.join(a.ours, 'metrics.json'))) if os.path.exists(os.path.join(a.ours, 'metrics.json')) else []
    ok = [r for r in rows if 'error' not in r]
    # dedupe near-identical geometry (variants, backups): keep the first of each fingerprint
    seen, uniq = set(), []
    for r in ok:
        if r['fp'] in seen:
            continue
        seen.add(r['fp']); uniq.append(r)
    out = {'files': len(rows), 'errors': len(rows) - len(ok), 'unique': len(uniq)}
    out['modes'] = dict(Counter(r['mode'] for r in uniq))
    ourname = lambda r: (r.get('meta') or {}).get('author') and 'shywolf91' in str(r['meta']['author'])   # noqa: E731
    comm = [r for r in uniq if not ourname(r)]
    out['ours_in_folder'] = sorted(r['map'] for r in uniq if ourname(r))
    # structures
    def bstats(rs):
        S = [r['structures'] for r in rs if r.get('structures', {}).get('n')]
        return {k: pct([s.get(k) for s in S]) for k in ('n', 'median_area', 'median_h', 'indoor_p50', 'holes_p50',
                                                      'flat_roof_p50', 'roof_levels_p50', 'colours_p50',
                                                      'value_range_p50', 'base_course_p50', 'box_share')} | \
               {'maps_with_buildings': len(S), 'of': len(rs)}
    out['structures_community'] = bstats(comm)
    out['structures_ours'] = {r['map']: r.get('structures') for r in ours + [u for u in uniq if ourname(u)]}
    # spawns per mode
    sp = defaultdict(list)
    for r in comm:
        s = r.get('spawns') or {}
        for t in ('t1', 't2', 'all'):
            if t in s:
                sp[r['mode']].append(s[t])
    out['spawns_community'] = {m: {k: pct([v.get(k) for v in L]) for k in ('object_top_share', 'air_below_share',
                                                                          'water_share', 'steep_share', 'roughness',
                                                                          'walk_out_share', 'cover_within_8')} | {'teams': len(L)}
                               for m, L in sp.items()}
    out['spawn_rules_seen'] = dict(Counter((r.get('spawns') or {}).get('rule') for r in comm))
    out['spawns_ours'] = {r['map']: {t: r['spawns'].get(t) for t in ('t1', 't2')} for r in ours if r.get('spawns')}
    # failure prevalence (community, per team)
    prev = {}
    for m, L in sp.items():
        n = len(L)
        if not n:
            continue
        prev[m] = {'roof_or_object_top >5%': round(sum((v.get('object_top_share') or 0) > 0.05 for v in L) / n, 3),
                   'air_below >5%': round(sum((v.get('air_below_share') or 0) > 0.05 for v in L) / n, 3),
                   'water >0': round(sum((v.get('water_share') or 0) > 0 for v in L) / n, 3),
                   'steep >15%': round(sum((v.get('steep_share') or 0) > 0.15 for v in L) / n, 3),
                   'walk_out <98%': round(sum((v.get('walk_out_share') if v.get('walk_out_share') is not None else 1) < 0.98 for v in L) / n, 3),
                   'cover8 <35%': round(sum((v.get('cover_within_8') or 0) < 0.35 for v in L) / n, 3)}
    out['spawn_failure_prevalence'] = prev
    # colour
    out['colour_community'] = {k: pct([r['colour'].get(k) for r in comm if r.get('colour')]) for k in
                               ('top_colours', 'luma_p50', 'white_share', 'dark_share', 'neighbour_jump', 'coherence_4')}
    out['colour_ours'] = {r['map']: r.get('colour') for r in ours}
    # best-crafted community buildings: maps whose buildings have pitched roofs, rooms, many colours
    cand = []
    for r in comm:
        s = r.get('structures') or {}
        if s.get('n', 0) >= 4:
            score = (1 - s.get('flat_roof_p50', 1)) + s.get('indoor_p50', 0) * 2 + min(s.get('colours_p50', 0), 60) / 60 \
                + min(s.get('value_range_p50', 0), 60) / 60 - s.get('box_share', 1)
            cand.append((round(score, 3), r['map'], s.get('n'), r['mode']))
    out['top_building_maps'] = sorted(cand, reverse=True)[:40]
    out['worst_box_maps'] = sorted(((r['structures'].get('box_share', 0), r['map']) for r in comm
                                    if (r.get('structures') or {}).get('n', 0) >= 4), reverse=True)[:15]
    json.dump(out, open(a.out, 'w'), indent=1, default=float)
    print(json.dumps({k: out[k] for k in ('files', 'errors', 'unique', 'modes', 'spawn_rules_seen')}, indent=1))
    print('spawn failure prevalence', json.dumps(prev, indent=1))
    print('top building maps', out['top_building_maps'][:25])


if __name__ == '__main__':
    main()
