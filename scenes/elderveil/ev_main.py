"""Elderveil build: python scenes/elderveil/ev_main.py OUTDIR [veg_seed] [--graybox] [--no-checks]

graybox (ev_graybox, fixed layout seed; veg_seed places the vegetation stand-ins) -> orphan report -> mirror x512
-> export (.vxl, .txt, build.json, mat.npy, terrain_H.npy) -> babel_checks.run_all (zone rules on, assist spires
declared) + ev_checks -> validation.json + PASS/FAIL print.

Same veg_seed -> same SHA-256 in a fresh process. Without a veg_seed an OS seed is drawn and saved in build.json.
Only the graybox stage exists so far (--graybox is accepted for the same command line as later stages).
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..'))
from aosmap.kit import babel_checks, build, noise, symmetry  # noqa: E402
from aosmap.kit.babel_checks import Nav  # noqa: E402

import ev_checks  # noqa: E402
import ev_graybox  # noqa: E402
from ev_spec import SPEC  # noqa: E402


def assist_boxes(S=SPEC):
    bx = S['spire']['box']
    e = sorted(symmetry.mirror_index(x, S['axis']) for x in bx[:2])
    return {'west spire': [bx[0], bx[1], bx[2], bx[3]], 'east spire': [e[0], e[1], bx[2], bx[3]]}


def build_map(out, veg_seed=None):
    t0 = time.time()
    seed = noise.os_seed() if veg_seed is None else int(veg_seed)
    cv, rep = ev_graybox.build_west(SPEC, seed)
    floating_before = symmetry.floating_components(cv.solid)
    orphans = symmetry.remove_orphans(cv)
    symmetry.mirror_canvas(cv, SPEC['axis'])
    sc = rep['scatter']
    info = {'stage': 'graybox', 'layout_seed': SPEC['layout_seed'], 'veg_seed': seed, 'axis': SPEC['axis'],
            'floating_before_cleanup': len(floating_before), 'floating_before_list': floating_before[:10],
            'cleanup': orphans,
            'scatter': {k: v for k, v in sc.items() if k not in ('tree_list',)},
            'spire': rep['spire'], 'aqueduct': rep['aqueduct'], 'bridge_y': rep['bridge_y'],
            'mushrooms': rep['mushrooms'], 'wall_columns': rep['wall_columns'],
            'crest_wall_columns': rep['crest_wall_columns'], 'assist_structures': assist_boxes(SPEC),
            'deviations': SPEC['deviations'], 'materials': cv.materials}
    info['build_seconds'] = round(time.time() - t0, 1)
    info = build.export(cv, out, SPEC['file'],
                        txt=dict(name=SPEC['name'], version=SPEC['version'],
                                 description='Babel with assist spires: overgrown elder ruins in a misty forest '
                                             'valley - graybox (not a release).',
                                 fog=SPEC['fog'], extensions={'babel': True, 'water_damage': 0}),
                        build_info=info)
    return cv, info


def check(out, info, cv=None):
    t0 = time.time()
    data = open(os.path.join(out, SPEC['file'] + '.vxl'), 'rb').read()
    mat = np.load(os.path.join(out, 'mat.npy'))
    H = np.load(os.path.join(out, 'terrain_H.npy')).astype(int)
    names = {v: k for k, v in info.get('materials', {}).items()}
    R = babel_checks.run_all(data, build=info, mat=mat, mat_names=names, terrain_H=H, axis=SPEC['axis'],
                             assist=assist_boxes(SPEC))
    R['summary'] = babel_checks.summary(R)
    solid = cv.solid if cv is not None else None
    if solid is None:
        from aosmap.kit import codec
        solid = codec.decode(data)[0]
    F = ev_checks.run(solid, H, SPEC, Nav(solid), build=info, mat=mat, materials=info.get('materials'))
    F['summary'] = ev_checks.summary(F)
    R['ev_checks'] = F
    R['txt'] = build.check_txt(os.path.join(out, SPEC['file'] + '.txt'))
    R['all_check_seconds'] = round(time.time() - t0, 1)
    with open(os.path.join(out, 'validation.json'), 'w') as f:
        json.dump(R, f, indent=1, default=str)
    return R


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = args[0]
    seed = args[1] if len(args) > 1 else None
    cv, info = build_map(out, seed)
    keys = ('sha256', 'bytes', 'veg_seed', 'floating_before_cleanup', 'cleanup', 'build_seconds')
    print(json.dumps({k: info.get(k) for k in keys}, indent=1, default=str))
    if '--no-checks' not in sys.argv:
        R = check(out, info, cv)
        for row in R['summary'] + R['ev_checks']['summary']:
            if row.get('status'):
                print(babel_checks.format_row(row))
            else:
                print(('PASS ' if row['ok'] else 'FAIL ') + row['rule'] + '  ' +
                      json.dumps(row['detail'], default=str)[:400])
        print('txt:', R['txt'])
        print('check seconds', R.get('check_seconds'), 'all', R.get('all_check_seconds'))
