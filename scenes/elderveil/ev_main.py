"""Elderveil build: python scenes/elderveil/ev_main.py OUTDIR [veg_seed] [--graybox] [--no-checks]

graybox (ev_graybox, fixed layout seed; veg_seed places the vegetation stand-ins) -> orphan report -> [graybox copy:
mirror = the reference collision] -> art on the west half (ev_art / ev_veg / ev_props, same veg_seed) -> orphan
report -> mirror x512 -> sky islets, crows, sky tag (ev_sky) -> light, grade, glow, brightness -> export (.vxl, .txt
with glow, build.json, mat.npy, terrain_H.npy, graybox_solid.npy) -> babel_checks.run_all (zone rules, declared
waivers, assist spires) + ev_checks (incl. the graybox-vs-art collision diff) -> validation.json + PASS/FAIL print.

Same veg_seed -> same SHA-256 in a fresh process. Without a veg_seed an OS seed is drawn and saved in build.json.
--graybox exports the gameplay reference build only.
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
from aosmap.kit.babel_checks import Nav  # noqa: E402

import ev_checks  # noqa: E402
import ev_graybox  # noqa: E402
from ev_spec import SPEC  # noqa: E402


def assist_boxes(S=SPEC):
    bx = S['spire']['box']
    e = sorted(symmetry.mirror_index(x, S['axis']) for x in bx[:2])
    return {'west spire': [bx[0], bx[1], bx[2], bx[3]], 'east spire': [e[0], e[1], bx[2], bx[3]]}


def build_map(out, veg_seed=None, graybox_only=False):
    t0 = time.time()
    seed = noise.os_seed() if veg_seed is None else int(veg_seed)
    cv, rep = ev_graybox.build_west(SPEC, seed)
    floating_before = symmetry.floating_components(cv.solid)
    orphans = symmetry.remove_orphans(cv)
    cvG = copy.deepcopy(cv)
    symmetry.mirror_canvas(cvG, SPEC['axis'])
    sc = rep['scatter']
    info = {'stage': 'graybox' if graybox_only else 'art', 'layout_seed': SPEC['layout_seed'], 'veg_seed': seed,
            'axis': SPEC['axis'], 'floating_before_cleanup': len(floating_before),
            'floating_before_list': floating_before[:10], 'cleanup': orphans,
            'scatter': {k: v for k, v in sc.items() if k not in ('tree_list',)},
            'spire': rep['spire'], 'aqueduct': rep['aqueduct'], 'bridge_y': rep['bridge_y'],
            'mushrooms': rep['mushrooms'], 'wall_columns': rep['wall_columns'], 'cascade': rep.get('cascade'),
            'sites': rep.get('sites'), 'crest_wall_columns': rep['crest_wall_columns'],
            **({k: rep[k] for k in ('lanterns', 'queen_v11', 'under_v11', 'late_seal', 'nav_seal') if k in rep}),
            'assist_structures': assist_boxes(SPEC), 'deviations': SPEC['deviations'], 'waivers': SPEC['waivers']}
    ext = {'babel': True, 'water_damage': 0}
    boxes = []
    if graybox_only:
        final = cvG
        version, desc = SPEC['version'], 'Babel with assist spires: elder ruins in a forest valley - graybox.'
    else:
        import ev_art
        rng = np.random.default_rng(seed)
        art = ev_art.art_west(cv, rep, SPEC, rng, seed, solid_gray=cvG.solid)
        art_float = symmetry.floating_components(cv.solid)
        art_orphans = symmetry.remove_orphans(cv)
        symmetry.mirror_canvas(cv, SPEC['axis'])
        post = {}
        boxes += ev_art.art_post(cv, rep, SPEC, rng, post)
        post_float = symmetry.split_expected(symmetry.floating_components(cv.solid), cv.expect_floating)
        stored, fin = ev_art.finish(cv)
        ext = build.glow_extensions(stored, ext)
        final = cv
        version, desc = SPEC.get('release_name', SPEC['release']['version']), SPEC['release']['description']
        info.update({'art': art, 'art_floating_before_cleanup': len(art_float), 'art_cleanup': art_orphans,
                     'post_mirror_floating': {'unexpected': len(post_float[0]), 'expected': len(post_float[1]),
                                              'unexpected_list': post_float[0][:10]},
                     'sky': post['sky'], 'tag': post['tag'], 'tag_rect': post['tag']['box'], 'finish': fin,
                     'feature_pads': sc['feature_pads'], 'colour_stats': color.colour_stats(cv.solid, cv.rgb)})
    info['cosmetic_asymmetric_boxes'] = boxes
    info['materials'] = final.materials
    info['build_seconds'] = round(time.time() - t0, 1)
    info = build.export(final, out, SPEC['file'],
                        txt=dict(name=SPEC['name'], version=version, description=desc, fog=SPEC['fog'],
                                 extensions=ext), build_info=info)
    np.save(os.path.join(out, 'graybox_solid.npy'), np.packbits(cvG.solid, axis=2))
    np.save(os.path.join(out, 'graybox_mat.npy'), cvG.mat)
    with open(os.path.join(out, 'graybox_materials.json'), 'w') as f:
        json.dump(cvG.materials, f)
    return final, info, cvG


def check(out, info, cv=None, cvG=None):
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
    gray = None
    if info.get('stage') == 'art':
        gray = (cvG.solid, cvG.mat, cvG.materials) if cvG is not None else ev_checks.load_graybox(out)
    F = ev_checks.run(solid, H, SPEC, Nav(solid), build=info, mat=mat, materials=info.get('materials'),
                      graybox=gray)
    F['summary'] = ev_checks.summary(F)
    R['ev_checks'] = F
    R['txt'] = build.check_txt(os.path.join(out, SPEC['file'] + '.txt'))
    R['all_check_seconds'] = round(time.time() - t0, 1)
    with open(os.path.join(out, 'validation.json'), 'w') as f:
        json.dump(R, f, indent=1, default=str)
    return R


if __name__ == '__main__':
    release = SPEC['release_default']
    if '--release' in sys.argv:
        release = sys.argv[sys.argv.index('--release') + 1]
    SPEC['release_name'] = release
    SPEC['v11'] = bool(SPEC['releases'][release]['v11'])
    args = [a for a in sys.argv[1:] if not a.startswith('--') and a != release]
    out = args[0]
    seed = args[1] if len(args) > 1 else None
    cv, info, cvG = build_map(out, seed, graybox_only='--graybox' in sys.argv)
    keys = ('sha256', 'bytes', 'veg_seed', 'floating_before_cleanup', 'art_floating_before_cleanup', 'art_cleanup',
            'post_mirror_floating', 'finish', 'colour_stats', 'build_seconds')
    print(json.dumps({k: info.get(k) for k in keys}, indent=1, default=str)[:3000])
    if '--no-checks' not in sys.argv:
        R = check(out, info, cv, cvG)
        for row in R['summary'] + R['ev_checks']['summary']:
            if row.get('status'):
                print(babel_checks.format_row(row))
            else:
                print(('PASS ' if row['ok'] else 'FAIL ') + row['rule'] + '  ' +
                      json.dumps(row['detail'], default=str)[:400])
        print('txt:', R['txt'])
        print('check seconds', R.get('check_seconds'), 'all', R.get('all_check_seconds'))
