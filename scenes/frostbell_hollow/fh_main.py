"""Frostbell Hollow build: python scenes/frostbell_hollow/fh_main.py OUTDIR [veg_seed] [--graybox] [--no-checks]

graybox (fh_graybox, fixed layout seed) -> orphan report -> [graybox copy: mirror + train = the reference collision]
-> art on the west half (fh_art / fh_veg, OS seed `veg_seed`, saved in build.json) -> orphan report -> mirror x512
-> stopped train -> per-side pad one-offs, sky decor, corner tag (fh_art.art_post) -> light, grade, glow, brightness
-> export (.vxl, .txt with glow + heavens_color, build.json, mat.npy, terrain_H.npy, graybox_solid.npy) -> run_all +
fh_checks (incl. the graybox-vs-art collision diff) -> validation.json.

Same veg_seed -> same SHA-256 in a fresh process. veg_seed places the pine stand-ins (graybox) and drives every
vegetation/decoration look (art). --graybox skips the art (the gameplay reference build).
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

import fh_checks  # noqa: E402
import fh_graybox  # noqa: E402
from fh_spec import SPEC  # noqa: E402


def front_exempt_boxes(S=SPEC):
    """The owner-requested gatehouses (both sides) as declared front exemptions for the zone rules
    (babel_checks zone_rules: left out of the front object count/share/height test, still in the free-share test).
    Only build.json carries them; the .vxl/.txt are unchanged."""
    gx, gy = S['gatehouse']['x'], S['gatehouse']['y']
    if S.get('zones') and S['gatehouse'].get('variant') == 'arch':
        gx = (S['v12']['buttress_x'][0], gx[1])             # v1.2: the pier buttresses are part of the gate
    east = sorted(symmetry.mirror_index(x, S['axis']) for x in gx)
    return [[gx[0], gx[1], gy[0], gy[1]], [east[0], east[1], gy[0], gy[1]]]


def build_map(out, veg_seed=None, graybox_only=False):
    t0 = time.time()
    seed = noise.os_seed() if veg_seed is None else int(veg_seed)     # one OS seed per build, saved in build.json
    cv, rep = fh_graybox.build_west(SPEC, seed)
    floating_before = symmetry.floating_components(cv.solid)
    orphans = symmetry.remove_orphans(cv)
    cvG = copy.deepcopy(cv)
    symmetry.mirror_canvas(cvG, SPEC['axis'])
    train_box = fh_graybox.build_train(cvG, SPEC)
    info_extra = {'stage': 'graybox' if graybox_only else 'art', 'layout_seed': SPEC['layout_seed'],
                  'axis': SPEC['axis'], 'floating_before_cleanup': len(floating_before), 'cleanup': orphans,
                  'scatter': {k: v for k, v in rep['scatter'].items() if k != 'pine_list'},
                  'market_boxes': rep['market_boxes'], 'mill': rep['mill'], 'rail_tunnel': rep['rail_tunnel'],
                  'deviations': SPEC['deviations']}
    ext = {'babel': True, 'water_damage': 0}
    boxes = [train_box]
    if graybox_only:
        final = cvG
        info_extra.update({'veg_seed': seed, 'feature_pads': rep['scatter']['feature_pads']})
        version, desc = SPEC['version'], 'Babel: Christmas Eve alpine village - graybox (not a release).'
    else:
        import fh_art
        rng = np.random.default_rng(seed)
        art = fh_art.art_west(cv, rep, SPEC, rng, seed)
        art_float_before = symmetry.floating_components(cv.solid)
        art_orphans = symmetry.remove_orphans(cv)
        symmetry.mirror_canvas(cv, SPEC['axis'])
        fh_graybox.build_train(cv, SPEC)
        post = {}
        boxes += fh_art.art_post(cv, rep, SPEC, rng, post)
        post_float = symmetry.split_expected(symmetry.floating_components(cv.solid), cv.expect_floating)
        stored, fin = fh_art.finish(cv)
        ext.update({'heavens_color': SPEC['heavens_color']})
        ext = build.glow_extensions(stored, ext)
        final = cv
        version = SPEC.get('release', SPEC['release_default'])
        desc = ('Babel: Christmas Eve in an alpine village at twilight. Build your tower from the flat anchor '
                'ground under the platform; market, rink and giant spruce in the centre, railway and creek flanks, '
                'mine tunnels below.')
        info_extra.update({'veg_seed': seed, 'art': art, 'art_floating_before_cleanup': len(art_float_before),
                           'art_cleanup': art_orphans,
                           'post_mirror_floating': {'unexpected': len(post_float[0]), 'expected': len(post_float[1]),
                                                    'unexpected_list': post_float[0][:10]},
                           'pads_built': post['pads'], 'sky': post['sky'], 'tag_rect': post['tag_rect'],
                           'tag_margin': post['tag_margin'], 'finish': fin,
                           'feature_pads': rep['scatter']['feature_pads'],
                           'colour_stats': color.colour_stats(cv.solid, cv.rgb)})
    info_extra['front_exempt_boxes'] = front_exempt_boxes(SPEC)
    info_extra['cosmetic_asymmetric_bbox'] = train_box
    info_extra['cosmetic_asymmetric_boxes'] = boxes
    info_extra['materials'] = final.materials
    info_extra['build_seconds'] = round(time.time() - t0, 1)
    info = build.export(final, out, SPEC['file'],
                        txt=dict(name=SPEC['name'], version=version, description=desc, fog=SPEC['fog'],
                                 extensions=ext),
                        build_info=info_extra)
    np.save(os.path.join(out, 'graybox_solid.npy'), np.packbits(cvG.solid, axis=2))
    np.save(os.path.join(out, 'graybox_mat.npy'), cvG.mat)
    with open(os.path.join(out, 'graybox_materials.json'), 'w') as f:
        json.dump(cvG.materials, f)
    return final, info, cvG


def check(out, info, cv=None, cvG=None):
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
    gray = None
    if info.get('stage') == 'art':
        if cvG is not None:
            gray = (cvG.solid, cvG.mat, cvG.materials)
        else:
            gray = fh_checks.load_graybox(out)
    F = fh_checks.run(solid, H, SPEC, Nav(solid), build=info, graybox=gray, mat=mat,
                      materials=info.get('materials'))
    F['summary'] = fh_checks.summary(F)
    R['fh_checks'] = F
    R['txt'] = build.check_txt(os.path.join(out, SPEC['file'] + '.txt'))
    with open(os.path.join(out, 'validation.json'), 'w') as f:
        json.dump(R, f, indent=1, default=str)
    return R


if __name__ == '__main__':
    release = SPEC['release_default']
    if '--release' in sys.argv:
        release = sys.argv[sys.argv.index('--release') + 1]
    SPEC['release'] = release
    SPEC['gatehouse']['variant'] = SPEC['releases'][release]['gate']
    SPEC['zones'] = bool(SPEC['releases'][release].get('zones'))
    if '--gate' in sys.argv:                            # exposure experiment override
        SPEC['gatehouse']['variant'] = sys.argv[sys.argv.index('--gate') + 1]
    if '--flank-cover' in sys.argv:
        SPEC['gatehouse']['flank_cover'] = True
    args = [a for a in sys.argv[1:] if not a.startswith('--') and a not in (SPEC['gatehouse']['variant'], release)]
    out = args[0]
    seed = args[1] if len(args) > 1 else None
    cv, info, cvG = build_map(out, seed, graybox_only='--graybox' in sys.argv)
    keys = ('sha256', 'bytes', 'veg_seed', 'floating_before_cleanup', 'art_floating_before_cleanup', 'art_cleanup',
            'post_mirror_floating', 'finish', 'colour_stats', 'build_seconds')
    print(json.dumps({k: info.get(k) for k in keys}, indent=1, default=str))
    if '--no-checks' not in sys.argv:
        R = check(out, info, cv, cvG)
        for row in R['summary'] + R['fh_checks']['summary']:
            if row.get('status'):
                print(babel_checks.format_row(row))
            else:
                print(('PASS ' if row['ok'] else 'FAIL ') + row['rule'] + '  ' +
                      json.dumps(row['detail'], default=str)[:300])
        print('txt:', R['txt'])
        print('check seconds', R.get('check_seconds'))
