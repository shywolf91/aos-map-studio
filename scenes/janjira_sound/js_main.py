"""Janjira Sound build (stage 1 graybox): python scenes/janjira_sound/js_main.py OUTDIR [veg_seed] [--no-checks]

terrain (point-symmetric) -> fort, towers, islet buildings, props, baoli on the source half -> vegetation (OS seed
`veg_seed`, saved in build.json; pass it back to rebuild the exact map) -> orphan cleanup -> 180-degree rotation
about (256, 256) (aosmap.kit 'point512') -> beached dhow (one-off, cosmetic box) -> export -> aosmap.kit checks +
js_checks -> validation.json.
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

import js_build  # noqa: E402
from js_spec import SPEC  # noqa: E402

DESCRIPTION = ('Babel: Janjira Sound - Konkan sea forts on four wooded islands around a sand causeway, '
               'a recreate of newfort by JoJoe Stinky. Stage 1 graybox (not a release).')


def build_map(out, veg_seed=None):
    t0 = time.time()
    seed = noise.os_seed() if veg_seed is None else int(veg_seed)
    cv, rep, H, Z = js_build.build_west(SPEC, SPEC['layout_seed'], seed)
    fl_before = symmetry.floating_components(cv.solid)
    orphans = symmetry.remove_orphans(cv)
    symmetry.mirror_canvas(cv, SPEC['axis'])
    dh = js_build.dhow(cv, SPEC)
    post = symmetry.split_expected(symmetry.floating_components(cv.solid), cv.expect_floating)
    info = {'stage': SPEC['stage'], 'layout_seed': SPEC['layout_seed'], 'veg_seed': seed, 'axis': SPEC['axis'],
            'floating_before_cleanup': len(fl_before), 'floating_before_list': fl_before[:15], 'cleanup': orphans,
            'post_rotation_floating': {'unexpected': len(post[0]), 'list': post[0][:12]},
            'terrain': {'land_cols_spec': rep['land_cols'], 'water_pct_spec': rep['water_pct']},
            'fort': rep['fort'], 'watch_towers': rep['watch_towers'], 'shrine': rep['shrine'], 'hut': rep['hut'],
            'props': rep['props'], 'baoli': rep['baoli'], 'vegetation': rep['vegetation'], 'dhow': dh,
            'cosmetic_asymmetric_boxes': [dh['box']], 'waivers': SPEC['waivers'], 'materials': cv.materials}
    info['interiors_n'] = len(cv.interiors)
    info['build_seconds'] = round(time.time() - t0, 1)
    ext = {'babel': True, 'water_damage': SPEC['water_damage'], 'boundary_damage': dict(SPEC['boundary'])}
    res = build.export(cv, out, SPEC['file'], txt=dict(name=SPEC['name'], version=SPEC['version'],
                                                       description=DESCRIPTION, fog=SPEC['fog'], extensions=ext),
                       build_info=info)
    return cv, res


def targets():
    """Extra route targets (graph model): every island, the islets, each tower terrace, the dhow deck."""
    return {
        'nw_island': (130, 240, 186, 226, 40, 62), 'sw_island': (150, 244, 288, 334, 40, 62),
        'west_islet_n': (50, 78, 202, 230, 40, 62), 'west_islet_s': (52, 80, 282, 310, 40, 62),
        'mid_islet_n': (250, 262, 190, 202, 55, 63), 'dhow_deck': (240, 270, 331, 339, 54, 57),
        'nw_tower_terrace': (214, 226, 197, 209, 40, 42), 'sw_tower_terrace': (184, 196, 308, 320, 40, 42),
    }


def check(out, info, pyspades=True):
    t0 = time.time()
    data = open(os.path.join(out, SPEC['file'] + '.vxl'), 'rb').read()
    mat = np.load(os.path.join(out, 'mat.npy'))
    H = np.load(os.path.join(out, 'terrain_H.npy')).astype(int)
    names = {v: k for k, v in info.get('materials', {}).items()}
    R = babel_checks.run_all(data, build=info, mat=mat, mat_names=names, terrain_H=H, axis=SPEC['axis'],
                             targets=targets(), pyspades=pyspades)
    R['summary'] = babel_checks.summary(R)
    import js_checks
    R['js_checks'] = js_checks.run(out, data, info, SPEC, H)
    R['txt'] = build.check_txt(os.path.join(out, SPEC['file'] + '.txt'))
    R['check_wall_seconds'] = round(time.time() - t0, 1)
    with open(os.path.join(out, 'validation.json'), 'w') as f:
        json.dump(R, f, indent=1, default=str)
    return R


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = args[0]
    seed = args[1] if len(args) > 1 else None
    cv, info = build_map(out, seed)
    keys = ('sha256', 'bytes', 'veg_seed', 'floating_before_cleanup', 'cleanup', 'post_rotation_floating',
            'build_seconds', 'interiors_n')
    print(json.dumps({k: info.get(k) for k in keys}, indent=1, default=str)[:3000])
    print('vegetation:', info['vegetation']['counts'])
    if '--no-checks' not in sys.argv:
        R = check(out, info, pyspades='--no-pyspades' not in sys.argv)
        for row in R['summary']:
            print(babel_checks.format_row(row), '' if row.get('status') else
                  json.dumps(row['detail'], default=str)[:220])
        print('js_checks:', json.dumps(R['js_checks'], default=str)[:4000])
        print('txt:', R['txt'])
        print('check seconds:', R['check_wall_seconds'])
