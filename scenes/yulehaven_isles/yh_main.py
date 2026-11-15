"""Yulehaven Isles build: python scenes/yulehaven_isles/yh_main.py OUTDIR [veg_seed] [--graybox] [--no-checks]

graybox (yh_build, fixed layout seed) -> orphan report -> mirror x512 -> [graybox: export here]
-> art (yh_art: materials -> colours, snow dusting, decoration, glow; vegetation and decoration from the OS seed
`veg_seed`, saved in build.json) -> one-off landmarks after the mirror (yh_oneoffs) -> sky decor + sky-level tag
-> light, glow bake, brightness rules -> export -> aosmap.kit checks + yh_checks -> validation.json.
"""
from __future__ import annotations

import copy
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..'))
from aosmap.kit import babel_checks, build, color, noise, symmetry  # noqa: E402

import yh_build  # noqa: E402
from yh_spec import SPEC  # noqa: E402


def build_map(out, veg_seed=None, graybox_only=False):
    t0 = time.time()
    seed = noise.os_seed() if veg_seed is None else int(veg_seed)
    cv, rep = yh_build.build_west(SPEC, SPEC['layout_seed'])
    fl_before = symmetry.floating_components(cv.solid)
    orphans = symmetry.remove_orphans(cv)
    info = {'stage': 'graybox' if graybox_only else 'art', 'layout_seed': SPEC['layout_seed'], 'veg_seed': seed,
            'axis': SPEC['axis'], 'floating_before_cleanup': len(fl_before), 'floating_before_list': fl_before[:15],
            'cleanup': orphans, 'passage': rep.get('passage'), 'sea_cave_mouth': rep.get('sea_cave_mouth')}
    boxes = []
    import yh_art
    if not graybox_only:
        rng = np.random.default_rng(seed)
        info['art_west'] = yh_art.art_west(cv, rep, SPEC, rng)
        info['art_cleanup'] = symmetry.remove_orphans(cv)
        info['untrap'] = untrap(cv)
    symmetry.mirror_canvas(cv, SPEC['axis'])
    import yh_oneoffs
    rng2 = np.random.default_rng(seed + 1)
    one = yh_oneoffs.build(cv, rep, SPEC, rng2, art=not graybox_only)
    boxes += one['boxes']
    info['oneoffs'] = {k: v for k, v in one.items() if k != 'boxes'}
    if not graybox_only:
        info['oneoff_glow'] = yh_art.oneoff_glow(cv, rep)
        info['paint'] = yh_art.paint(cv, SPEC, seed)
    post = symmetry.split_expected(symmetry.floating_components(cv.solid), cv.expect_floating)
    info['post_mirror_floating'] = {'unexpected': len(post[0]), 'expected': len(post[1]),
                                    'unexpected_list': post[0][:12]}
    ext = {'babel': True, 'water_damage': SPEC['water_damage']}
    if not graybox_only:
        import yh_art
        stored, fin = yh_art.finish(cv)
        info['finish'] = fin
        ext['heavens_color'] = SPEC['heavens_color']
        ext = build.glow_extensions(stored, ext)
        info['colour_stats'] = color.colour_stats(cv.solid, cv.rgb)
        desc = ('Babel: Christmas Eve in a Nordic fishing archipelago. Build your tower from the granite anchor '
                'ground on your island shore; ice-locked cargo ship, bonfire ring and spruce on the islet, skerry '
                'flanks with a lighthouse and a chapel, smugglers sea caves below. Swimming hurts.')
    else:
        desc = 'Babel: Yulehaven Isles - graybox (not a release).'
    info['cosmetic_asymmetric_boxes'] = boxes
    info['materials'] = cv.materials
    info['interiors_n'] = len(cv.interiors)
    info['build_seconds'] = round(time.time() - t0, 1)
    res = build.export(cv, out, SPEC['file'], txt=dict(name=SPEC['name'], version=SPEC['version'], description=desc,
                                                       fog=SPEC['fog'], extensions=ext), build_info=info)
    return cv, res


def untrap(cv, rounds=3):
    """Remove vegetation round any trap cell (standable cell reached from a spawn that cannot walk back to the
    spawn band - same definition as aosmap.kit.babel_checks) - dense foliage makes walk-out pockets."""
    from aosmap.kit.babel_checks import Nav
    from aosmap.kit.params import BABEL_DEFAULT as P
    veg_ids = [cv.materials[m] for m in ('leaf', 'bark', 'moss', 'vine', 'mushroom', 'deadwood', 'fruit', 'nest',
                                         'ribbon', 'iron') if m in cv.materials]
    removed = 0
    left = None
    for _ in range(rounds):
        nav = Nav(cv.solid)
        half = P['spawn_half']
        srcs = np.concatenate([nav.nodes_in(b[0] - half, b[0] + half, b[1] - half, b[1] + half, 0, 62)
                               for b in P['bases']])
        fwd = np.isfinite(nav.dist_from(srcs))
        anchor = nav.nodes_in(78, 434, 200, 312, 0, 62)[::5]
        back = np.isfinite(nav.dist_from(anchor, reverse=True))
        p = nav.xyz
        Hm = cv.H.astype(int)
        landish = np.abs(p[:, 2] - Hm[p[:, 0], p[:, 1]]) <= 3
        trap = landish & fwd & ~back
        left = p[trap].tolist()
        if not trap.any():
            break
        for (x, y, z) in left:
            sl = (slice(max(0, x - 3), x + 4), slice(max(0, y - 3), y + 4), slice(max(0, z - 6), z))
            m = np.isin(cv.mat[sl], veg_ids)
            removed += int(m.sum())
            cv.solid[sl][m] = False
            cv.mat[sl][m] = 0
    return {'removed_voxels': removed, 'traps_left': len(left or []), 'left_sample': (left or [])[:8]}


def targets():
    S = SPEC
    return {
        'islet_bonfire': (240, 272, 300, 340, 40, 62),
        'cargo_hold': (248, 264, 234, 288, 58, 62),
        'ship_deck': (248, 264, 220, 291, 44, 50),
        'north_chain_mid': (242, 270, 72, 100, 40, 63),
        'south_chain_mid': (242, 270, 411, 439, 40, 63),
        'islet_sea_cave': (240, 272, 312, 324, 58, 62),
    }


def check(out, info):
    data = open(os.path.join(out, SPEC['file'] + '.vxl'), 'rb').read()
    mat = np.load(os.path.join(out, 'mat.npy'))
    H = np.load(os.path.join(out, 'terrain_H.npy')).astype(int)
    names = {v: k for k, v in info.get('materials', {}).items()}
    R = babel_checks.run_all(data, build=info, mat=mat, mat_names=names, terrain_H=H, axis=SPEC['axis'],
                             targets=targets())
    R['summary'] = babel_checks.summary(R)
    import yh_checks
    R['yh_checks'] = yh_checks.run(out, data, info, SPEC)
    R['txt'] = build.check_txt(os.path.join(out, SPEC['file'] + '.txt'))
    with open(os.path.join(out, 'validation.json'), 'w') as f:
        json.dump(R, f, indent=1, default=str)
    return R


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = args[0]
    seed = args[1] if len(args) > 1 else None
    cv, info = build_map(out, seed, graybox_only='--graybox' in sys.argv)
    keys = ('sha256', 'bytes', 'veg_seed', 'floating_before_cleanup', 'cleanup', 'post_mirror_floating', 'passage',
            'sea_cave_mouth', 'finish', 'colour_stats', 'build_seconds', 'oneoffs')
    print(json.dumps({k: info.get(k) for k in keys}, indent=1, default=str)[:4000])
    if '--no-checks' not in sys.argv:
        R = check(out, info)
        for row in R['summary']:
            print(babel_checks.format_row(row) if row.get('status') else
                  ('PASS ' if row['ok'] else 'FAIL ') + row['rule'] + '  ' + json.dumps(row['detail'], default=str)[:240])
        print('yh_checks:', json.dumps(R['yh_checks'], default=str)[:3000])
        print('txt:', R['txt'])
