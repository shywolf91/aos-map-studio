"""Northgale Freighter build: python scenes/northgale_freighter/nf_main.py OUTDIR [veg_seed] [--no-checks]

sea + islets + hull core, decks, holds, access, props, vegetation (west half; vegetation OS seed `veg_seed`, saved in
build.json - pass it back to rebuild the exact map) -> orphan cleanup -> mirror x512 -> one-off ends (bow,
forecastle, foremast / bridge, funnel, smoke, lifeboats, poop deck) -> sky decor -> art (colour only) -> export ->
aosmap.kit checks + nf_checks -> validation.json.
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

import nf_build  # noqa: E402
from nf_spec import SPEC  # noqa: E402

DESCRIPTION = ('Babel at night on a cold north sea: build your tower from the deck of a huge freighter. '
               'Explore the holds below deck, or climb down the gangways and wade the shallows to flank.')


def build_map(out, veg_seed=None):
    t0 = time.time()
    seed = noise.os_seed() if veg_seed is None else int(veg_seed)
    cv, rep = nf_build.build_west(SPEC, seed)
    fl_before = symmetry.floating_components(cv.solid)
    orphans = symmetry.remove_orphans(cv)
    symmetry.mirror_canvas(cv, SPEC['axis'])
    ends = nf_build.ends(cv, SPEC, rep)
    lighthouses = [nf_build.lighthouse(cv, SPEC, bx, by) for (bx, by) in SPEC['beacons']]
    detail = nf_build.details(cv, SPEC)
    sky = nf_build.sky(cv, SPEC)
    post = symmetry.split_expected(symmetry.floating_components(cv.solid), cv.expect_floating)
    import nf_art
    stored, art = nf_art.art(cv, rep, SPEC)
    boxes = [list(b) for b in SPEC['cosmetic_boxes']] + [art['tag_rect'][:4]] + [lh['box'] for lh in lighthouses]
    info = {'stage': SPEC['stage'], 'layout_seed': SPEC['layout_seed'], 'veg_seed': seed, 'axis': SPEC['axis'],
            'floating_before_cleanup': len(fl_before), 'cleanup': orphans,
            'post_mirror_floating': {'unexpected': len(post[0]), 'list': post[0][:12]},
            'props': rep['props'], 'companionways': rep['companionways'], 'cranes': rep['cranes'],
            'gangways': rep['gangways'], 'huts': rep['huts'], 'vegetation': rep['vegetation'], 'ends': ends, 'lighthouses': lighthouses, 'detail': detail,
            'sky_records': sky, 'cosmetic_asymmetric_boxes': boxes, 'waivers': SPEC['waivers'],
            'materials': cv.materials, 'art': art, 'tag_rect': art['tag_rect']}
    info['interiors_n'] = len(cv.interiors)
    info['build_seconds'] = round(time.time() - t0, 1)
    ext = {'babel': True, 'water_damage': SPEC['water_damage'], 'boundary_damage': dict(SPEC['boundary']),
           'heavens_color': SPEC['heavens_color']}
    from aosmap.kit import build as kb
    ext = kb.glow_extensions(stored, ext)
    res = build.export(cv, out, SPEC['file'], txt=dict(name=SPEC['name'], version=SPEC['version'],
                                                       description=DESCRIPTION, fog=SPEC['fog'], extensions=ext),
                       build_info=info)
    return cv, res


def targets():
    """Extra route targets (graph model)."""
    return {
        'tween_deck_w': (82, 168, 210, 302, 49, 51), 'lower_hold_w': (178, 250, 212, 300, 58, 60),
        'crane_cab_nw': (186, 204, 210, 226, 27, 29), 'forecastle_deck': (20, 64, 220, 292, 34, 36),
        'forecastle_store': (26, 62, 230, 282, 39, 41), 'bridge_wheelhouse': (447, 477, 221, 291, 15, 17),
        'islet_nw': (80, 112, 100, 132, 50, 63), 'islet_n_mid': (240, 256, 108, 140, 50, 63),
        'hut_n': (172, 184, 94, 106, 55, 58),
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
    import nf_checks
    R['nf_checks'] = nf_checks.run(out, data, info, SPEC, H)
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
    keys = ('sha256', 'bytes', 'veg_seed', 'floating_before_cleanup', 'cleanup', 'post_mirror_floating',
            'build_seconds', 'interiors_n')
    print(json.dumps({k: info.get(k) for k in keys}, indent=1, default=str)[:3000])
    print('vegetation:', info['vegetation'])
    if '--no-checks' not in sys.argv:
        R = check(out, info, pyspades='--no-pyspades' not in sys.argv)
        for row in R['summary']:
            print(babel_checks.format_row(row), '' if row.get('status') else
                  json.dumps(row['detail'], default=str)[:220])
        print('nf_checks:', json.dumps(R['nf_checks'], default=str)[:4000])
        print('txt:', R['txt'])
        print('check seconds:', R['check_wall_seconds'])
