"""Sprinkler Field build: python scenes/sprinkler_field/sf_main.py OUTDIR [veg_seed] [--graybox] [--no-checks]

graybox (sf_build, fixed layout seed) -> orphan report/cleanup -> [art: sf_art.art_west (OS seed)] -> mirror x512
-> axis objects (sf_axis: sprinkler, feeder, trowel, queen chamber, cap, valve key; self-symmetric, built after the
mirror) -> one-off landmarks (sf_oneoffs, cosmetic boxes) -> [art: sf_art.finish (light, glow, brightness, sky
decor, tag)] -> export -> aosmap.kit checks + sf_checks -> validation.json.

Only the --graybox path exists so far. The art pass (sf_art) is a later stage; its hooks are marked ART HOOK.
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

import sf_axis  # noqa: E402
import sf_build  # noqa: E402
import sf_oneoffs  # noqa: E402
from sf_spec import SPEC  # noqa: E402


def build_map(out, veg_seed=None, graybox_only=False):
    t0 = time.time()
    seed = noise.os_seed() if veg_seed is None else int(veg_seed)
    cv, rep = sf_build.build_west(SPEC, SPEC['layout_seed'])
    fl_before = symmetry.floating_components(cv.solid)
    orphans = symmetry.remove_orphans(cv)
    info = {'stage': 'graybox' if graybox_only else 'art', 'layout_seed': SPEC['layout_seed'],
            'veg_seed': None if graybox_only else seed, 'axis': SPEC['axis'],
            'floating_before_cleanup': len(fl_before), 'floating_before_list': fl_before[:15], 'cleanup': orphans,
            'waivers': SPEC['waivers'], 'zone_rules_skip': SPEC['zone_rules_skip'],
            'deviations': SPEC['deviations']}
    if not graybox_only:
        import sf_art                                   # ART HOOK: vegetation / decoration on the west half (OS seed)
        rng = np.random.default_rng(seed)
        info['art_west'] = sf_art.art_west(cv, rep, SPEC, rng)
        info['art_cleanup'] = symmetry.remove_orphans(cv)
    symmetry.mirror_canvas(cv, SPEC['axis'])
    ax = sf_axis.build(cv, rep, SPEC)
    one = sf_oneoffs.build(cv, rep, SPEC)
    boxes = ax['boxes'] + one['boxes']
    info['cosmetic_boxes_named'] = {**ax['boxes_named'], **one['named']}
    info['oneoffs'] = {k: rep.get(k) for k in ('spigot', 'hose_reel', 'flowerpot', 'glove', 'snail_shell',
                                               'footprint', 'plant_label')}
    info['oneoff_flatten_removed_prop_voxels'] = one['flatten_removed_prop_voxels']
    info['oneoff_outside_site'] = one['outside_site']
    post = symmetry.split_expected(symmetry.floating_components(cv.solid), cv.expect_floating)
    info['post_mirror_floating'] = {'unexpected': len(post[0]), 'expected': len(post[1]),
                                    'unexpected_list': post[0][:12]}
    info['post_cleanup'] = symmetry.remove_orphans(cv)
    ext = {'babel': True, 'water_damage': SPEC['water_damage']}
    if not graybox_only:
        stored, fin = sf_art.finish(cv, rep, SPEC, seed)  # ART HOOK: lighting, glow bake, brightness, sky, tag
        info['finish'] = fin
        ext = build.glow_extensions(stored, ext)
        desc = ('Babel with assist structures: a lawn just after watering, at ant scale. Climb the tripod '
                'sprinkler or the half-buried trowel toward the intel, or build from your anchor; hose, brick '
                'edging and an ant nest on the flanks.')
    else:
        desc = 'Babel: Sprinkler Field - graybox (not a release).'
    info['cosmetic_asymmetric_boxes'] = boxes
    info['materials'] = cv.materials
    info['interiors_n'] = len(cv.interiors)
    for k in ('terrain', 'hose', 'edging', 'nest', 'blades', 'keep_violations', 'tight_pairs', 'sprinkler',
              'helix', 'feeder', 'queen', 'trowel', 'valve_key', 'landings'):
        info[k] = rep.get(k)
    info['check_targets'] = targets()
    info['assist'] = assist()
    info['build_seconds'] = round(time.time() - t0, 1)
    res = build.export(cv, out, SPEC['file'], txt=dict(name=SPEC['name'], version=SPEC['version'], description=desc,
                                                       fog=SPEC['fog'], extensions=ext), build_info=info)
    return cv, res


def targets():
    """Extra route targets (x0, x1, y0, y1, z0, z1) for the kit route report."""
    T = SPEC['sprinkler']['tbar']
    C = SPEC['trowel']['cap']
    qx, qy, qrx, qry = SPEC['nest']['queen']
    nx, ny, nrx, nry = SPEC['nest']['chambers']['north']
    fl = SPEC['z']['tunnel_floor']
    sp = SPEC['sprinkler']
    (hx, hy), hr, hz = sp['hub'], sp['head_r'], sp['head_z']
    (a0, a1), lift = SPEC['hose']['arches'][0]
    ay = sf_build.hose_y(SPEC, (a0 + a1) / 2)
    atop = SPEC['hose']['cz'] - SPEC['hose']['r_out'] - lift
    snx, sny = SPEC['oneoffs']['snail_shell']
    dz = SPEC['oneoff_dims']['snail_shell']['deck_z']
    rx, ry = SPEC['oneoffs']['hose_reel']
    rd = SPEC['oneoff_dims']['hose_reel']
    return {
        'sprinkler_tbar': (T['x'][0], T['x'][1], T['y'][0] - 2, T['y'][1], T['z'] - 1, T['z'] + 1),
        'sprinkler_head_deck': (hx - hr, hx + hr, hy - hr, hy + hr, hz - 1, hz + 1),
        'trowel_cap': (C['c'][0] - C['r'], C['c'][0] + C['r'], C['c'][1] - C['r'], C['c'][1] + C['r'], C['z'] - 1,
                       C['z'] + 1),
        'queen_chamber': (qx - qrx + 3, qx + qrx - 3, qy - qry + 3, qy + qry - 3, fl - 1, fl + 1),
        'nest_north_chamber_w': (nx - nrx + 3, nx + nrx - 3, ny - nry + 3, ny + nry - 3, fl - 1, fl + 1),
        'hose_arch1_top_w': (a0 + 4, a1 - 4, int(ay) - 3, int(ay) + 3, atop - 1, atop + 1),
        'snail_lookout': (snx - 3, snx + 3, sny - 3, sny + 3, dz - 1, dz + 1),
        'hose_reel_drum': (rx - 5, rx + 5, rd['drum_y'][0] + 2, rd['drum_y'][1] - 2, rd['floor_z'] - 1,
                           rd['floor_z'] + 1),
    }


def assist():
    T = SPEC['sprinkler']['tbar']
    C = SPEC['trowel']['cap']
    return {'sprinkler': (T['x'][0], T['x'][1], T['y'][0] - 2, T['y'][1]),
            'trowel': (C['c'][0] - C['r'], C['c'][0] + C['r'], C['c'][1] - C['r'], C['c'][1] + C['r'])}


def check(out, info):
    data = open(os.path.join(out, SPEC['file'] + '.vxl'), 'rb').read()
    mat = np.load(os.path.join(out, 'mat.npy'))
    H = np.load(os.path.join(out, 'terrain_H.npy')).astype(int)
    names = {v: k for k, v in info.get('materials', {}).items()}
    R = babel_checks.run_all(data, build=info, mat=mat, mat_names=names, terrain_H=H, axis=SPEC['axis'],
                             targets=targets(), assist=assist())
    R['summary'] = babel_checks.summary(R)
    import sf_checks
    R['sf_checks'] = sf_checks.run(out, data, info, SPEC, mat=mat, terrain_H=H)
    R['txt'] = build.check_txt(os.path.join(out, SPEC['file'] + '.txt'))
    with open(os.path.join(out, 'validation.json'), 'w') as f:
        json.dump(R, f, indent=1, default=str)
    return R


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = args[0]
    seed = args[1] if len(args) > 1 else None
    graybox = '--graybox' in sys.argv
    if not graybox:
        try:
            import sf_art  # noqa: F401
        except ImportError:
            raise SystemExit('sf_art (the art pass) is not written yet: run with --graybox')
    cv, info = build_map(out, seed, graybox_only=graybox)
    keys = ('sha256', 'bytes', 'floating_before_cleanup', 'cleanup', 'post_mirror_floating', 'post_cleanup',
            'keep_violations', 'tight_pairs', 'build_seconds', 'oneoff_flatten_removed_prop_voxels',
            'oneoff_outside_site')
    print(json.dumps({k: info.get(k) for k in keys}, indent=1, default=str)[:5000])
    if '--no-checks' not in sys.argv:
        R = check(out, info)
        for row in R['summary']:
            print(babel_checks.format_row(row) if row.get('status') else
                  ('PASS ' if row['ok'] else 'FAIL ') + row['rule'] + '  ' + json.dumps(row['detail'], default=str)[:240])
        print('sf_checks:', json.dumps(R['sf_checks']['summary'], default=str))
        print('txt:', R['txt'])
