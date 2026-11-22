"""Royal Parade Snow Night v2 build.

    python scenes/royal_parade_snow_night/rpsn_main.py OUTDIR [--stage graybox|art] [--deco-seed N]
                                                       [--no-checks] [--no-pyspades]

Reads the original RoyalParadeSnowNight.vxl read-only (path + SHA-256 pinned in rpsn_spec.SPEC), applies the geometry
pass (rpsn_build) and, for --stage art (default), the colour pass (rpsn_art: moonlit grade, lit windows, lamps, lights,
ice, baked light + AO, glow bake), exports .vxl + .txt + build.json with aosmap.kit.build, then runs the kit Babel
suite plus rpsn_check and writes validation.json. Decoration placement (snowmen, kerb drifts, icicles, bulb and
window choices) uses an OS seed saved in build.json as deco_seed; pass it back with --deco-seed to rebuild that map.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..'))
from aosmap.kit import babel_checks, build, codec, noise  # noqa: E402

import rpsn_build  # noqa: E402
import rpsn_check  # noqa: E402
from rpsn_spec import SPEC  # noqa: E402

DESCRIPTION = ('Babel: the Royal Parade boulevard on a moonlit snow night - a Christmas parade of gift trucks, tree '
               'floats and sleighs under lit windows and string lights. Original map by Bradley & Mile, courtesy of '
               'Sauerkraut; snow night rework by shywolf91 + AI.')


def build_map(out, stage='art', deco_seed=None):
    t0 = time.time()
    seed = noise.os_seed() if deco_seed is None else int(deco_seed)
    cv, rep, P, orig, vmasks = rpsn_build.build(SPEC, seed)
    geom_sha = None
    art = {}
    stored = {}
    if stage == 'art':
        import rpsn_art
        stored, art = rpsn_art.art(cv, rep, SPEC, seed, P)
    ext = {'babel': True, 'water_damage': SPEC['water_damage']}
    if stage == 'art':
        ext['heavens_color'] = SPEC['heavens_color']
        ext = build.glow_extensions(stored, ext)
    info = {'stage': stage, 'version': SPEC['version'], 'layout_seed': SPEC['layout_seed'], 'deco_seed': seed,
            'source': SPEC['source'], 'regenerate': f'python scenes/royal_parade_snow_night/rpsn_main.py <out> '
                                                    f'--stage {stage} --deco-seed {seed}',
            'classify': rep['classify'], 'vehicles': rep['vehicles'], 'cover': rep['cover'], 'lamps': rep['lamps'],
            'snowmen': rep['snowmen'], 'kerb_drifts': rep['kerb_drifts'], 'icicles': rep['icicles'],
            'connectivity_build': rep['connectivity'], 'placer_refused': rep['placer_refused'],
            'pieces': [p for p in rep['pieces'] if p['kind'] != 'icicle'] +
                      [{'name': 'icicles', 'kind': 'icicle', 'voxels': rep['icicles']['count']}],
            'materials': cv.materials, 'art': art, 'structures': [],
            'kept_floating_note': 'original jets and stubs: listed in sky_objects, unchanged'}
    info['build_seconds'] = round(time.time() - t0, 1)
    if geom_sha:
        info['geometry_sha'] = geom_sha
    res = build.export(cv, out, SPEC['file'],
                       txt=dict(name=SPEC['name'], version=SPEC['version'], description=DESCRIPTION, fog=SPEC['fog'],
                                extensions=ext),
                       build_info=info)
    return cv, res, orig


def check(out, info, cv, orig, pyspades=True):
    data = open(os.path.join(out, SPEC['file'] + '.vxl'), 'rb').read()
    mat = np.load(os.path.join(out, 'mat.npy'))
    H = np.load(os.path.join(out, 'terrain_H.npy')).astype(int)
    names = {v: k for k, v in info['materials'].items()}
    R = babel_checks.run_all(data, build=info, mat=mat, mat_names=names, terrain_H=H, pyspades=pyspades)
    R['summary'] = babel_checks.summary(R)
    solid = cv.solid
    R['rework'] = {
        'diff': rpsn_check.diff_report(orig, solid, SPEC, info['pieces']),
        'connectivity': rpsn_check.connectivity(orig, solid),
        'exposure_before_after': rpsn_check.exposure(orig, solid),
        'front_lanes': rpsn_check.front_lanes(solid, SPEC),
        'clear_width': rpsn_check.clear_width(orig, solid, SPEC, info['pieces']),
        'colour': rpsn_check.colour_stats(solid, cv.rgb, cv.nolight),
        'txt': build.check_txt(os.path.join(out, SPEC['file'] + '.txt')),
    }
    if info['stage'] == 'art':
        srcs = [(x, y, z) for (x, y, z, _) in cv.glow]
        R['rework']['glow_palette_collisions'] = rpsn_check.palette_collisions(cv.rgb, solid, srcs)
    o_solid, o_col, _ = codec.decode(open(SPEC['source']['vxl'], 'rb').read())
    o_rgb = codec.unpack_rgb(o_col).astype(np.uint8)
    R['rework']['colour_original'] = rpsn_check.colour_stats(o_solid, o_rgb)
    # the same kit suite on the untouched original, so every FAIL row can be read as "inherited" or "new"
    o_data = open(SPEC['source']['vxl'], 'rb').read()
    o_build = {'sky_objects': info.get('sky_objects', [])}
    Ro = babel_checks.run_all(o_data, build=o_build, terrain_H=H, pyspades=False, zone_profile=False)
    R['rework']['kit_original_summary'] = babel_checks.summary(Ro)
    R['rework']['kit_original_numbers'] = {k: Ro.get(k) for k in ('spawn_squares', 'trap_cells', 'anchors', 'flank',
                                                                    'zone_rules')}
    R['rework']['kit_original_numbers']['trap_cells'] = {'count': Ro['trap_cells']['count'],
                                                         'of_cells': Ro['trap_cells']['of_cells']}
    json.dump(R, open(os.path.join(out, 'validation.json'), 'w'), indent=1, default=str)
    return R


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--stage', default='art', choices=('graybox', 'art'))
    ap.add_argument('--deco-seed', type=int)
    ap.add_argument('--no-checks', action='store_true')
    ap.add_argument('--no-pyspades', action='store_true')
    a = ap.parse_args()
    cv, info, orig = build_map(a.out, a.stage, a.deco_seed)
    print(json.dumps({k: info[k] for k in ('sha256', 'bytes', 'deco_seed', 'build_seconds')}, indent=1))
    if not a.no_checks:
        R = check(a.out, info, cv, orig, pyspades=not a.no_pyspades)
        for row in R['summary']:
            print(babel_checks.format_row(row))
        print(json.dumps(R['rework'], indent=1, default=str)[:5000])
