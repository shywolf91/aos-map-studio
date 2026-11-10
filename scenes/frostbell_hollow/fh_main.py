"""Frostbell Hollow graybox build: python scenes/frostbell_hollow/fh_main.py OUTDIR [--no-checks]

Builds the west half + axis halves (fh_graybox), reports/removes orphans, mirrors x512, adds the stopped train
(the one asymmetric piece), exports .vxl/.txt/build.json/mat.npy/terrain_H.npy via aosmap.kit.build.export,
runs aosmap.kit.babel_checks.run_all + fh_checks and writes validation.json. Layout seed fixed: same SHA-256 in a
fresh process. The graybox has no vegetation art, so there is no OS vegetation seed yet.
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
from aosmap.kit import babel_checks, build, symmetry  # noqa: E402
from aosmap.kit.babel_checks import Nav  # noqa: E402

import fh_checks  # noqa: E402
import fh_graybox  # noqa: E402
from fh_spec import SPEC  # noqa: E402


def build_map(out):
    t0 = time.time()
    cv, rep = fh_graybox.build_west(SPEC)
    floating_before = symmetry.floating_components(cv.solid)
    orphans = symmetry.remove_orphans(cv)
    symmetry.mirror_canvas(cv, SPEC['axis'])
    train_box = fh_graybox.build_train(cv, SPEC)
    floating_after_train = symmetry.floating_components(cv.solid)
    info = build.export(
        cv, out, SPEC['file'],
        txt=dict(name=SPEC['name'], version=SPEC['version'],
                 description='Babel: Christmas Eve alpine village - graybox (not a release).',
                 fog=SPEC['fog'], extensions={'babel': True, 'water_damage': 0}),
        build_info={'stage': 'graybox', 'layout_seed': SPEC['layout_seed'], 'axis': SPEC['axis'],
                    'veg_seed': None,
                    'cosmetic_asymmetric_bbox': train_box,
                    'cosmetic_asymmetric_boxes': [train_box],
                    'cosmetic_asymmetric_note': 'stopped train on the axis (locomotive at the east end)',
                    'floating_before_cleanup': len(floating_before), 'cleanup': orphans,
                    'floating_after_train': len(floating_after_train),
                    'scatter': {k: v for k, v in rep['scatter'].items() if k != 'pine_list'},
                    'feature_pads': rep['scatter']['feature_pads'],
                    'market_boxes': rep['market_boxes'], 'mill': rep['mill'], 'rail_tunnel': rep['rail_tunnel'],
                    'materials': cv.materials, 'deviations': SPEC['deviations'],
                    'build_seconds': round(time.time() - t0, 1)})
    return cv, info


def check(out, info, cv=None):
    data = open(os.path.join(out, SPEC['file'] + '.vxl'), 'rb').read()
    mat = np.load(os.path.join(out, 'mat.npy'))
    H = np.load(os.path.join(out, 'terrain_H.npy')).astype(int)
    names = {v: k for k, v in info.get('materials', {}).items()}
    R = babel_checks.run_all(data, build=info, mat=mat, mat_names=names, terrain_H=H, axis=SPEC['axis'])
    R['summary'] = babel_checks.summary(R)
    solid = cv.solid if cv is not None else None
    if solid is None:
        from aosmap.kit import codec
        solid = codec.decode(data)[0]
    F = fh_checks.run(solid, H, SPEC, Nav(solid), build=info)
    F['summary'] = fh_checks.summary(F)
    R['fh_checks'] = F
    R['txt'] = build.check_txt(os.path.join(out, SPEC['file'] + '.txt'))
    with open(os.path.join(out, 'validation.json'), 'w') as f:
        json.dump(R, f, indent=1, default=str)
    return R


if __name__ == '__main__':
    out = sys.argv[1]
    cv, info = build_map(out)
    print(json.dumps({k: info[k] for k in ('sha256', 'bytes', 'floating_before_cleanup', 'cleanup',
                                           'floating_after_train', 'build_seconds')}, indent=1, default=str))
    if '--no-checks' not in sys.argv:
        R = check(out, info, cv)
        for row in R['summary'] + R['fh_checks']['summary']:
            print(('PASS ' if row['ok'] else 'FAIL ') + row['rule'] + '  ' + json.dumps(row['detail'], default=str)[:300])
        print('txt:', R['txt'])
        print('check seconds', R.get('check_seconds'))
