"""Cursed Skull Reef build: python scenes/cursed_skull_reef/csr_main.py OUTDIR [veg_seed] [--graybox] [--no-checks]

graybox (csr_build, fixed layout seed) -> orphan report -> mirror x512 -> [graybox: export here]
-> art (csr_art: decoration, vegetation and glow on the west half from the OS seed `veg_seed`, saved in build.json)
-> one-offs after the mirror (csr_oneoffs) -> sky decor (csr_sky) -> paint, light, glow bake, brightness rules
-> corner tag -> export -> aosmap.kit checks + csr_checks -> validation.json.
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
from aosmap.kit import babel_checks, build, color, noise, symmetry, tag  # noqa: E402

import csr_build  # noqa: E402
from csr_spec import SPEC  # noqa: E402


def assist_boxes(S=SPEC):
    x0, x1, y0, y1 = S['assist_box']
    e = sorted(symmetry.mirror_index(x, S['axis']) for x in (x0, x1))
    return {'west mast wreck': [x0, x1, y0, y1], 'east mast wreck': [e[0], e[1], y0, y1]}


def build_map(out, veg_seed=None, graybox_only=False):
    t0 = time.time()
    seed = noise.os_seed() if veg_seed is None else int(veg_seed)
    cv, rep = csr_build.build_west(SPEC, SPEC['layout_seed'])
    fl_before = symmetry.floating_components(cv.solid)
    orphans = symmetry.remove_orphans(cv)
    info = {'stage': 'graybox' if graybox_only else 'art', 'layout_seed': SPEC['layout_seed'], 'veg_seed': seed,
            'axis': SPEC['axis'], 'variant': 'Babel, assist structures', 'floating_before_cleanup': len(fl_before),
            'floating_before_list': fl_before[:15], 'cleanup': orphans, 'assist': rep.get('assist'),
            'galleon': rep.get('galleon'), 'skull': rep.get('skull'), 'links': rep.get('links'),
            'assist_structures': assist_boxes(), 'waivers': SPEC['waivers'], 'deviations': SPEC['deviations']}
    boxes = []
    if not graybox_only:
        import csr_art
        rng = np.random.default_rng(seed)
        info['art_west'] = csr_art.art_west(cv, rep, SPEC, rng)
        info['art_cleanup'] = symmetry.remove_orphans(cv)
        info['untrap'] = untrap(cv)
    symmetry.mirror_canvas(cv, SPEC['axis'])
    import csr_oneoffs
    rng2 = np.random.default_rng(seed + 1)
    one = csr_oneoffs.build(cv, rep, SPEC, rng2, art=not graybox_only)
    boxes += one['boxes']
    info['oneoffs'] = {k: v for k, v in one.items() if k != 'boxes'}
    ext = {'babel': True, 'water_damage': SPEC['water_damage']}
    if not graybox_only:
        import csr_sky
        info['sky_objects_placed'] = csr_sky.place_all(cv, rep, SPEC, np.random.default_rng(seed + 2))
        info['oneoff_glow'] = csr_art.oneoff_glow(cv, rep)
        info['paint'] = csr_art.paint(cv, SPEC, seed)
    post = symmetry.split_expected(symmetry.floating_components(cv.solid), cv.expect_floating)
    info['post_mirror_floating'] = {'unexpected': len(post[0]), 'expected': len(post[1]),
                                    'unexpected_list': post[0][:12]}
    if not graybox_only:
        stored, fin = csr_art.finish(cv)
        info['finish'] = fin
        ext = build.glow_extensions(stored, ext)
        info['colour_stats'] = color.colour_stats(cv.solid, cv.rgb)
        desc = ('Babel, assist structures: a cursed pirate reef on a moonlit storm night. Two harbour isles joined '
                'by a shoal neck under the platform; climb the mast of your beached wreck for a short build to the '
                'intel, or build from your anchor rock. Skull crag with a sea cave, half-sunk galleon, cannon fort, '
                'maelstrom. Swimming hurts.')
    else:
        desc = 'Babel, assist structures: Cursed Skull Reef - graybox (not a release).'
    rect = tag.paint_tag(cv, SPEC['tag']['text'], corner=SPEC['tag']['corner'], margin=10,
                         rgb=(214, 184, 96), shadow=(80, 60, 40))
    info['tag_rect'] = list(rect)
    boxes.append(list(rect[:4]))
    info['cosmetic_asymmetric_boxes'] = boxes
    info['materials'] = cv.materials
    info['interiors_n'] = len(cv.interiors)
    info['check_targets'] = targets()
    info['build_seconds'] = round(time.time() - t0, 1)
    res = build.export(cv, out, SPEC['file'], txt=dict(name=SPEC['name'], version=SPEC['version'], description=desc,
                                                       fog=SPEC['fog'], extensions=ext), build_info=info)
    return cv, res


def untrap(cv, rounds=3):
    """Remove vegetation round any trap cell (standable cell reached from a spawn that cannot walk back) - dense
    foliage makes walk-out pockets (same definition as aosmap.kit.babel_checks)."""
    from aosmap.kit.babel_checks import Nav
    from aosmap.kit.params import BABEL_DEFAULT as P
    veg_ids = [cv.materials[m] for m in ('leaf', 'bark', 'moss', 'vine', 'mushroom', 'deadwood', 'fruit', 'nest',
                                         'ribbon', 'frond', 'coconut', 'root') if m in cv.materials]
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
        trap = landish & fwd & ~back & (p[:, 0] <= 255)
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
    return {
        'fort_rampart': (228, 284, 120, 158, 38, 44),
        'galleon_quarterdeck': (246, 266, 206, 226, 36, 44),
        'skull_eye_rooms': (236, 276, 314, 332, 30, 33),
        'skull_sea_cave': (236, 276, 318, 346, 58, 61),
        'north_chain_mid': (242, 270, 64, 92, 40, 62),
        'south_chain_mid': (242, 270, 419, 447, 40, 62),
        'blue_crow_nest': (212, 230, 220, 238, 6, 9),
        'red_crow_nest': (282, 300, 220, 238, 6, 9),
    }


def check(out, info):
    data = open(os.path.join(out, SPEC['file'] + '.vxl'), 'rb').read()
    mat = np.load(os.path.join(out, 'mat.npy'))
    H = np.load(os.path.join(out, 'terrain_H.npy')).astype(int)
    names = {v: k for k, v in info.get('materials', {}).items()}
    R = babel_checks.run_all(data, build=info, mat=mat, mat_names=names, terrain_H=H, axis=SPEC['axis'],
                             targets=targets(), assist=assist_boxes())
    R['summary'] = babel_checks.summary(R)
    import csr_checks
    R['csr_checks'] = csr_checks.run(out, data, info, SPEC)
    R['txt'] = build.check_txt(os.path.join(out, SPEC['file'] + '.txt'))
    with open(os.path.join(out, 'validation.json'), 'w') as f:
        json.dump(R, f, indent=1, default=str)
    return R


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = args[0]
    seed = args[1] if len(args) > 1 else None
    cv, info = build_map(out, seed, graybox_only='--graybox' in sys.argv)
    keys = ('sha256', 'bytes', 'veg_seed', 'floating_before_cleanup', 'cleanup', 'post_mirror_floating', 'assist',
            'finish', 'colour_stats', 'build_seconds', 'oneoffs', 'art_west', 'untrap')
    print(json.dumps({k: info.get(k) for k in keys}, indent=1, default=str)[:5000])
    if '--no-checks' not in sys.argv:
        R = check(out, info)
        for row in R['summary']:
            print(babel_checks.format_row(row))
        print('assist:', json.dumps(R.get('assist_structures'), default=str))
        print('build_gap:', json.dumps(R.get('build_gap'), default=str))
        print('routes:', json.dumps(R.get('routes'), default=str)[:1500])
        print('interior failures:', json.dumps(R['interiors']['failures'], default=str)[:1500])
        print('zone_rules:', json.dumps({k: R['zone_rules'][k] for k in ('front_dressing', 'spawn_cover',
                                                                        'under_platform', 'centre_footprint')},
                                       default=str)[:3000])
        print('csr_checks:', json.dumps(R['csr_checks'], default=str)[:3000])
        print('txt:', R['txt'])
