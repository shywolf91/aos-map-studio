"""Christmas PVP v2 generator (rework of GTR-CODE's Christmas PVP): single command.

    python scenes/christmas_pvp/cp_main.py OUTDIR [--stage graybox|art] [--deco-seed N] [--no-check]

graybox: original colours + spawn cover and light layout in function colours.
art:     cozy Christmas evening grade, painted additions, garlands, baked light + AO, glow blocks.
The layout (cover geometry, light positions) is fixed by SPEC['layout_seed']; decoration (bauble / gift colours,
tree string phase) uses an OS seed saved in build.json (owner rule), pass --deco-seed to rebuild that exact map.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..'))

from aosmap.kit import build, color, noise  # noqa: E402

import cp_art  # noqa: E402
import cp_graybox as gb  # noqa: E402
import cp_source  # noqa: E402
from cp_spec import SPEC  # noqa: E402

TOWERS = [(121, 146, 201, 227), (366, 391, 201, 227), (224, 250, 313, 339), (262, 288, 313, 339)]


def light_layout(cv, spec, cover_rep):
    """All light positions with their colour name: [(kind, (x, y, z), colour)]."""
    cyc = spec['bulb_cycle']
    lights = []
    faces = gb.wall_faces(cv, spec)
    gar, wall_b = gb.garlands(cv, spec, faces, cv.materials['orig_wall'])
    for i, p in enumerate(sorted(wall_b, key=lambda q: (q[2], abs(q[0] - 256), q[1]))):
        lights.append(('wall_bulb', p, cyc[i % len(cyc)]))
    for i, p in enumerate(gb.rail_bulbs(cv, spec)):
        lights.append(('rail_bulb', p, cyc[i % len(cyc)]))
    for i, p in enumerate(gb.tower_rings(cv, TOWERS)):
        lights.append(('tower_ring', p, ('amber', 'yellow')[i % 2]))
    trees = [tuple(v[:4]) for v in spec['assist_trees'].values()]
    for i, p in enumerate(gb.tree_strings(cv, trees, spec['tree_lights']['every'])):
        lights.append(('giant_tree_string', p, cyc[i % len(cyc)]))
    for p in gb.gold_heads(cv, TOWERS):
        lights.append(('lamp_head' if p[2] < 61 else 'path_star', p, 'amber' if p[2] < 61 else 'yellow'))
    for p in gb.window_lights(cv, cv.materials['orig_glass']):
        lights.append(('window', p, 'amber'))
    for i, (kind, p) in enumerate(cover_rep['lights']):
        lights.append((kind, p, 'yellow' if kind == 'fir_star' else ('amber', 'red', 'yellow')[i % 3]))
    return gar, lights


def build_map(out, stage='art', deco_seed=None):
    deco_seed = noise.os_seed() if deco_seed is None else int(deco_seed)
    data0, solid0, rgb0, sha0 = cp_source.load(SPEC['source'])
    cls = cp_source.classify(solid0, rgb0, SPEC)
    cv = cp_source.to_canvas(solid0, rgb0, cls, SPEC['name'])
    cover = gb.add_cover(cv, SPEC, SPEC['layout_seed'], deco_seed)
    gar, lights = light_layout(cv, SPEC, cover)
    counts = {}
    for kind, _, _ in lights:
        counts[kind] = counts.get(kind, 0) + 1
    info = {'stage': stage, 'source': os.path.basename(SPEC['source']), 'source_sha256': sha0,
            'layout_seed': SPEC['layout_seed'], 'deco_seed': deco_seed, 'axis': SPEC['axis'],
            'variant': 'Babel with assist structures',
            'assist_structures': {k: list(v) for k, v in SPEC['assist_trees'].items()},
            'cover': {k: v for k, v in cover.items() if k != 'lights'},
            'garland_voxels': len(gar), 'light_counts': counts,
            'corner_tag': 'skipped: every arena corner is occupied by coaster terraces / props',
            'structures': [], 'class_counts': {c: int((cls == i).sum()) for i, c in enumerate(cp_source.CLASSES)}}
    ext = {'babel': True, 'water_damage': 0}
    if stage == 'graybox':
        for p in gar:
            cv.rgb[p] = gb.FUNC['garland']
        for _, p, _ in lights:
            cv.rgb[p] = gb.FUNC['bulb']
    else:
        drng = np.random.default_rng(deco_seed ^ 0x5EED)
        info['grade_counts'] = cp_art.grade_original(cv, SPEC, SPEC['layout_seed'])
        info['paint_counts'] = cp_art.paint_additions(cv, SPEC, drng)
        cp_art.paint_garlands(cv, SPEC, gar)
        info['n_glow_sources'] = cp_art.place_glow(cv, SPEC, lights)
        color.lighting(cv)
        info['brightness'] = color.enforce_brightness(cv)
        stored, nsrc = color.bake_glow(cv, radius=SPEC['glow']['radius'], strength=SPEC['glow']['strength'])
        info['glow_nudged'] = cp_art.nudge_off_palette(cv, stored, SPEC)
        info['glow_stored_entries'] = len(stored)
        ext = build.glow_extensions(stored, ext)
    desc = ('Babel with assist structures: cozy Christmas evening rework of Christmas PVP by GTR-CODE '
            '(Minecraft export, planetminecraft mapa-boxpvp-free). The two giant trees under the platform ends '
            'are climbable assists.')
    res = build.export(cv, out, SPEC['file'],
                       txt=dict(name=SPEC['name'], description=desc, fog=SPEC['fog'], extensions=ext,
                                version=SPEC['version']),
                       build_info=info)
    if 'glow_stored_colors' in ext:
        compact_txt(os.path.join(out, SPEC['file'] + '.txt'), ext)
    return res


def compact_txt(path, ext):
    """Rewrite the extensions block without pprint's 24-space indents: 8 glow entries per line, no spaces.
    Same keys and values (piqueserver imports the .txt as Python); cuts the .txt by about 40 %."""
    text = open(path, encoding='utf-8').read()
    head = text[:text.index('extensions = ')]
    rest = {k: v for k, v in ext.items() if k != 'glow_stored_colors'}
    items = [f'({x},{y},{z}):({r},{g},{b})' for (x, y, z), (r, g, b) in ext['glow_stored_colors'].items()]
    rows = [','.join(items[i:i + 8]) for i in range(0, len(items), 8)]
    body = ('extensions = {' + ', '.join(f'{k!r}: {v!r}' for k, v in rest.items())
            + ",\n 'glow_stored_colors': {\n" + ',\n'.join(rows) + '}}\n')
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(head + body)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--stage', default='art', choices=('graybox', 'art'))
    ap.add_argument('--deco-seed', type=int)
    ap.add_argument('--no-check', action='store_true')
    a = ap.parse_args()
    res = build_map(a.out, a.stage, a.deco_seed)
    print(json.dumps({k: res[k] for k in ('sha256', 'deco_seed', 'light_counts', 'n_glow_sources',
                                          'glow_stored_entries', 'brightness', 'glow_nudged') if k in res},
                     default=str))
    print('cover:', {k: res['cover'][k] for k in ('voxels_per_side', 'mirror_clash_voxels', 'drift_voxels')})
    print('txt:', build.check_txt(os.path.join(a.out, SPEC['file'] + '.txt')))
    if not a.no_check:
        import cp_check
        cp_check.run(a.out)
