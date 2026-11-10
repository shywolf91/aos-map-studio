"""Kit example: a small ground-Babel graybox built only with aosmap.kit (the template /new-map starts from).

    python scenes/kit_example/kit_example_main.py OUTDIR [veg_seed]

Not a released map. It exercises every kit module end to end: SPEC dict -> terrain -> anchors -> an enterable
building per side -> mirror -> groves (OS seed saved) -> orphan cleanup -> lighting -> tag -> export -> checks.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from aosmap.kit import Canvas, babel_checks, build, color, noise, structures, symmetry, tag, veg  # noqa: E402

SPEC = {
    'name': 'Kit Example', 'file': 'kit_example', 'layout_seed': 20261110, 'axis': 'x512',
    'ground_z': 50, 'anchor_z': 46, 'anchor_x': (180, 211), 'anchor_y': (236, 275),
    'spawn': {'base': (118, 256), 'half': 20},
    'house': {'x': (60, 75), 'y': (200, 215)},
    'groves': [(60, 120), (150, 90), (60, 400), (170, 430), (200, 160)],
    'fog': (172, 168, 190),
}

GRASS = (96, 142, 70)
DIRT = (128, 100, 72)
STONE = (150, 146, 140)


def ground_colour(xs, ys, zs):
    n = noise.hash3(xs, ys, zs, 7)
    base = np.where(zs[:, None] <= SPEC['ground_z'], np.array(GRASS), np.array(DIRT))
    return np.clip(base * (0.92 + 0.12 * n[:, None]), 0, 255).astype(np.uint8)


def build_map(out, veg_seed=None):
    veg_seed = noise.os_seed() if veg_seed is None else int(veg_seed)
    cv = Canvas(SPEC['name'])
    # terrain: gentle rolling ground, solid to the bottom (owner rule)
    H = SPEC['ground_z'] + np.rint(2 * noise.fbm2((512, 512), 64, 3, 'ground', SPEC['layout_seed']) - 1).astype(int)
    bx, by = SPEC['spawn']['base']
    h = SPEC['spawn']['half']
    H[bx - h:bx + h + 1, by - h:by + h + 1] = np.clip(H[bx - h:bx + h + 1, by - h:by + h + 1], 49, 50)  # gentle
    cv.fill_terrain(H, ground_colour, 'ground')
    cv.no_prop(bx - h - 4, bx + h + 4, by - h - 4, by + h + 4)
    # raised tower anchor under the platform end: sheer on the enemy face, ramps on its north and south sides
    ax0, ax1 = SPEC['anchor_x']
    ay0, ay1 = SPEC['anchor_y']
    cv.box(ax0, ax1, ay0, ay1, SPEC['anchor_z'], 63, STONE, 'anchor')
    for i in range(1, 5):
        cv.box(ax0, ax1 - 4, ay0 - i, ay0 - i, SPEC['anchor_z'] + i, 63, STONE, 'anchor')
        cv.box(ax0, ax1 - 4, ay1 + i, ay1 + i, SPEC['anchor_z'] + i, 63, STONE, 'anchor')
    cv.no_prop(ax0 - 2, ax1 + 2, ay0 - 6, ay1 + 6)
    # one enterable two-storey house (doors, windows, stairs, recorded interiors)
    hx, hy = SPEC['house']['x'], SPEC['house']['y']
    g = int(cv.H[hx[0]:hx[1] + 1, hy[0]:hy[1] + 1].min())
    cv.box(hx[0], hx[1], hy[0], hy[1], g, 63, DIRT, 'ground')
    structures.building(cv, hx[0], hx[1], hy[0], hy[1], g, storeys=2, doors=('E', 'S'), name='example house')
    cv.no_prop(hx[0] - 3, hx[1] + 3, hy[0] - 3, hy[1] + 3)
    # vegetation on the west half, then mirror: balanced groves. Non-deterministic by owner rule, seed saved.
    rng = np.random.default_rng(veg_seed)
    pal = veg.palette_family([(60, 110, 50), (88, 132, 58), (120, 140, 66), (150, 120, 70)], n=8)
    vrep = veg.plant_groves(cv, rng, SPEC['groves'], pal, region_ok=lambda x, y: 8 <= x <= 246)
    orphans = symmetry.remove_orphans(cv)
    symmetry.mirror_canvas(cv, SPEC['axis'])
    color.lighting(cv)
    bright = color.enforce_brightness(cv)
    rect = tag.paint_tag(cv, SPEC['name'], corner='SW')
    info = build.export(cv, out, SPEC['file'],
                        txt=dict(name=SPEC['name'], description='Babel: kit example graybox (not a release).',
                                 fog=SPEC['fog'], extensions={'babel': True, 'water_damage': 0}),
                        build_info={'layout_seed': SPEC['layout_seed'], 'veg_seed': veg_seed, 'vegetation': vrep,
                                    'cleanup': orphans, 'brightness': bright, 'tag_rect': list(rect),
                                    'cosmetic_asymmetric_bbox': list(rect[:4])})
    return info


if __name__ == '__main__':
    out = sys.argv[1]
    info = build_map(out, sys.argv[2] if len(sys.argv) > 2 else None)
    data = open(os.path.join(out, SPEC['file'] + '.vxl'), 'rb').read()
    R = babel_checks.run_all(data, build=info, mat=np.load(os.path.join(out, 'mat.npy')),
                             terrain_H=np.load(os.path.join(out, 'terrain_H.npy')))
    R['summary'] = babel_checks.summary(R)
    json.dump(R, open(os.path.join(out, 'validation.json'), 'w'), indent=1, default=str)
    print(json.dumps({k: info[k] for k in ('sha256', 'veg_seed', 'vegetation', 'cleanup')}, indent=1, default=str))
    for row in R['summary']:
        print(('PASS ' if row['ok'] else 'FAIL ') + row['rule'])
    print('txt:', build.check_txt(os.path.join(out, SPEC['file'] + '.txt')))
