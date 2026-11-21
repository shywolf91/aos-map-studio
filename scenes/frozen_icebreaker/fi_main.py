"""Build Frozen Icebreaker.

    python scenes/frozen_icebreaker/fi_main.py OUTDIR [decor_seed] [--graybox]

Layout seed is fixed (SPEC['layout_seed']); the decor seed (ice rubble, ridge blocks, bow-wave floes) is drawn from
the OS per build by owner rule and saved in build.json, so the exact map can be rebuilt. --graybox skips the
colour passes (function colours stay flat) for the gameplay review.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..', '..')]

from aosmap.kit import Canvas, build, color, noise, symmetry, tag  # noqa: E402
from aosmap.kit.symmetry import mirror_index  # noqa: E402
import fi_world  # noqa: E402
from fi_spec import SPEC  # noqa: E402
import fi_terrain  # noqa: E402
import fi_places as places  # noqa: E402
import fi_ship  # noqa: E402
from fi_struct import polar_bear, walrus  # noqa: E402

BEAR_BOX = [166, 196, 404, 424]
WALRUS_BOX = [414, 446, 318, 340]


def one_offs(cv, rng):
    """Cosmetic, deliberately asymmetric one-off animals (owner loves unique objects): a polar bear with her cub
    on the south-west skirts and a walrus haul-out on the east shore. Low (<= 8), outside every gameplay zone."""
    polar_bear(cv, 170, 410, 1, 1)
    _cub(cv, 186, 418)
    for k, (x, y) in enumerate(((418, 322), (428, 326), (420, 332), (434, 334))):
        walrus(cv, x, y, 'x', k)


def _cub(cv, x, y):
    from fi_world import boxm, put
    g = places.g_at(cv, x, y)
    boxm(cv, x, x + 5, y, y + 2, g - 4, g - 2, 'fur')
    for (a, b) in ((x, y), (x + 5, y), (x, y + 2), (x + 5, y + 2)):
        boxm(cv, a, a, b, b, g - 1, g - 1, 'fur')
    boxm(cv, x - 2, x - 1, y, y + 2, g - 5, g - 3, 'fur')
    put(cv, x - 3, y + 1, g - 4, 'fur_dark')


def build_map(out, decor_seed=None, graybox=False):
    decor_seed = noise.os_seed() if decor_seed is None else int(decor_seed)
    rng = np.random.default_rng(decor_seed)
    fi_world.STRUCTS.clear()
    cv = Canvas(SPEC['name'])
    terr = fi_terrain.build_terrain(cv)
    # ---------------------------------------------------------------- west half (mirrored)
    places.tunnels(cv, rng)
    places.spawn_camp(cv, rng)
    places.front_dressing(cv, rng)
    places.under_platform(cv, rng)
    places.station(cv, rng)
    places.schooner(cv, rng)
    places.plane(cv, rng)
    n_ridge = places.ridges(cv, rng)
    n_berg = places.bergs(cv, rng)
    places.skirts(cv, rng)
    centre_int = [i for i in cv.interiors if i[1] >= 256]
    orphans_w = symmetry.remove_orphans(cv)
    symmetry.mirror_canvas(cv, SPEC['axis'])
    cv.interiors.extend(centre_int)
    fi_world.mirror_structs()
    color.team_recolor(cv, west_rgb=(60, 84, 206), east_rgb=(206, 64, 52), mat='team')
    # ---------------------------------------------------------------- after the mirror: the ship + one-offs
    fi_ship.build_ship(cv, rng)
    places.open_tunnel_into_hold(cv)
    one_offs(cv, rng)
    orphans = symmetry.remove_orphans(cv)
    pits = 0                     # kit fill_pits tests the highest neighbour, not all four: not used (trap check instead)
    # ---------------------------------------------------------------- colour
    bright, glow_n, stored = {}, 0, {}
    if not graybox:
        surf = color.lighting(cv, sun=(0.07, 0.04, -0.06, -0.03), side_f=0.86, ao_size=5, cover_f=0.84)
        stored, glow_n = color.bake_glow(cv, surf, radius=6.5, strength=0.30)
        bright = color.enforce_brightness(cv)
    rect = tag.paint_tag(cv, SPEC['name'], corner=SPEC['tag_corner'], rgb=(196, 190, 168), shadow=(40, 60, 90))
    ext = {'babel': True, 'water_damage': 0, 'heavens_color': SPEC['heavens']}
    if stored:
        ext = build.glow_extensions(stored, ext)
    cosmetic = [SPEC['ship_cosmetic_box'], BEAR_BOX, WALRUS_BOX, list(rect[:4])]
    info = build.export(
        cv, out, SPEC['file'],
        txt=dict(name=SPEC['name'], version=SPEC['version'],
                 description=('Babel: polar night on the pack ice. An icebreaker lies beset north of the tower, '
                              'a drift station south of it; blue-ice tunnels run from both north flanks into '
                              'the ship. Stock babel_script, walkable sea.'),
                 fog=SPEC['fog'], extensions=ext),
        build_info={'mode': 'babel', 'axis': SPEC['axis'], 'layout_seed': SPEC['layout_seed'],
                    'decor_seed': decor_seed, 'graybox': graybox, 'land_share': terr['land_share'],
                    'ridge_blocks_west': n_ridge, 'icebergs_west': n_berg, 'glow_sources': glow_n,
                    'cleanup_west': orphans_w, 'cleanup': orphans, 'pits_filled': pits, 'brightness': bright,
                    'tag_rect': list(rect), 'cosmetic_asymmetric_boxes': cosmetic,
                    'structures': fi_world.STRUCTS,
                    'check_targets': {'ship hold (tunnel end W)': [232, 240, 160, 172, 55, 61],
                                      'ship bridge': [224, 243, 171, 181, 24, 29],
                                      'drill tower top floor': [253, 259, 317, 327, 40, 48]}})
    return info


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = args[0]
    info = build_map(out, args[1] if len(args) > 1 else None, graybox='--graybox' in sys.argv)
    print(json.dumps({k: info[k] for k in ('sha256', 'bytes', 'decor_seed', 'land_share', 'cleanup', 'pits_filled',
                                           'brightness', 'glow_sources')}, indent=1, default=str))
    print('structures:', len(info['structures']), 'interiors:', len(info.get('interiors', [])))
    print('txt:', build.check_txt(os.path.join(out, SPEC['file'] + '.txt')))
