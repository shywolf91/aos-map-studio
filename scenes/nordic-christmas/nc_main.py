"""Build Hrafnfjord Yule (graybox stage).

    python scenes/nordic-christmas/nc_main.py OUTDIR [veg_seed] [decor_seed]

Layout seed fixed (SPEC['layout_seed']); vegetation and yard-prop seeds are drawn from the OS per build (owner rule)
and saved in build.json, so the exact map can be rebuilt by passing them back. Graybox: function colours only.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..', '..')]

import nc_world as W  # noqa: E402
from aosmap.kit import Canvas, build, noise, symmetry  # noqa: E402
from nordic_christmas_spec import SPEC  # noqa: E402
import nc_terrain  # noqa: E402
import nc_places as places  # noqa: E402


def open_leaf_traps(cv, rounds=3):
    """Foliage can close small pockets (lesson: Backyard Babel). Find standable ground cells reached from a spawn
    that cannot walk back (the babel_checks trap model) and clear leaves/bark in a 7 x 7 window above them, at the
    cell and its mirror so the map stays symmetric. Returns the number of cells opened."""
    from aosmap.kit.babel_checks import Nav
    veg_m = [cv.materials[k] for k in ('leaf', 'bark', 'moss', 'deadwood') if k in cv.materials]
    opened = 0
    for _ in range(rounds):
        nav = Nav(cv.solid)
        p = nav.xyz
        src = np.concatenate([nav.nodes_in(98, 138, 236, 276), nav.nodes_in(374, 414, 236, 276)])
        fwd = np.isfinite(nav.dist_from(src))
        back = np.isfinite(nav.dist_from(nav.nodes_in(98, 414, 200, 312, 0, 62)[::5], reverse=True))
        land = np.abs(p[:, 2] - cv.H[p[:, 0], p[:, 1]]) <= 3
        trap = p[fwd & ~back & land]
        if not len(trap):
            break
        for (x, y, z) in trap:
            for xx in {int(x), 512 - int(x)}:
                if not 0 <= xx < 512:
                    continue
                sl = (slice(max(xx - 3, 0), xx + 4), slice(max(y - 3, 0), y + 4), slice(max(z - 8, 0), z))
                m = np.isin(cv.mat[sl], veg_m)
                cv.solid[sl][m] = False
                cv.mat[sl][m] = 0
            opened += 1
    return opened


def build_map(out, veg_seed=None, decor_seed=None):
    veg_seed = noise.os_seed() if veg_seed is None else int(veg_seed)
    decor_seed = noise.os_seed() if decor_seed is None else int(decor_seed)
    vrng = np.random.default_rng(veg_seed)
    drng = np.random.default_rng(decor_seed)
    W.STRUCTS.clear()
    W.LANDMARKS.clear()
    cv = Canvas(SPEC['name'])
    terr = nc_terrain.build_terrain(cv)
    # ---------------------------------------------------------------- west half (mirrored)
    places.keep_zones(cv)
    places.mead_hall(cv, drng)
    places.smithy(cv, drng)
    places.boat_sheds(cv, drng)
    places.longhouse(cv, drng)
    places.bathhouse(cv, drng)
    places.stave_church(cv, drng)
    places.beacons(cv, drng)
    places.lodges(cv, drng)
    places.bay(cv, drng)
    places.fjord_landmarks(cv)
    places.front_dressing(cv)
    places.strip_dressing(cv)
    n_hesjer = places.strip_hesjer(cv)
    places.spawn_yard(cv, vrng)
    vrep = places.forest(cv, vrng)
    # authored half only: wipe anything that strayed east of x 255 before the mirror
    cv.solid[256:] = False
    cv.mat[256:] = 0
    nc_terrain_cols = cv.H.copy()
    orphans_w = symmetry.remove_orphans(cv)
    symmetry.mirror_canvas(cv, SPEC['axis'])
    W.mirror_registry(W.STRUCTS)
    W.mirror_registry(W.LANDMARKS)
    traps_opened = open_leaf_traps(cv)
    orphans = symmetry.remove_orphans(cv)
    info = build.export(
        cv, out, SPEC['file'],
        txt=dict(name=SPEC['name'], version=SPEC['version'], description=SPEC['txt']['description'],
                 fog=SPEC['fog'], extensions=dict(SPEC['txt']['extensions'],
                                                  heavens_color=SPEC['heavens_color'])),
        build_info={'mode': 'babel', 'modes': SPEC['modes'], 'axis': SPEC['axis'], 'stage': 'graybox',
                    'layout_seed': SPEC['layout_seed'], 'veg_seed': veg_seed, 'decor_seed': decor_seed,
                    'ice_share': terr['ice_share'], 'vegetation': vrep, 'cleanup_west': orphans_w,
                    'cleanup': orphans, 'trap_cells_opened': traps_opened, 'hesjer_west': n_hesjer, 'materials': dict(cv.materials), 'structures': W.STRUCTS, 'landmarks': W.LANDMARKS, 'waivers': {k: 'owner 2026-11-20 (popup): keep the fronts open, take a waiver if under 15 % hidden; graybox 0 % hidden; Blue 10.98 vs Red 10.00 is the babel_checks sampler phase, the map is exactly mirrored' for k in ('spawn_exposure_blue', 'spawn_exposure_red')}, 
                    'check_targets': {
                        'raven_gate_crown': [234, 278, 98, 106, 16, 19],
                        'church_bell_loft': {'blue': [139, 145, 81, 87, 0, 40], 'red': [367, 373, 81, 87, 0, 40]},
                        'beacon_north_top': {'blue': [177, 183, 41, 47, 0, 34], 'red': [329, 335, 41, 47, 0, 34]},
                        'thing_rock_room': [249, 263, 249, 263, 42, 44]}})
    del nc_terrain_cols
    return info


if __name__ == '__main__':
    a = sys.argv[1:]
    out = a[0]
    info = build_map(out, a[1] if len(a) > 1 else None, a[2] if len(a) > 2 else None)
    print(json.dumps({k: info[k] for k in ('sha256', 'bytes', 'veg_seed', 'decor_seed', 'ice_share', 'cleanup_west',
                                           'cleanup')}, indent=1, default=str)[:3000])
    print('structures:', len(info['structures']), 'interiors:', len(info.get('interiors', [])))
    print('txt:', build.check_txt(os.path.join(out, SPEC['file'] + '.txt')))
