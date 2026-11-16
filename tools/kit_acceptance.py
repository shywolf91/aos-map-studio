"""Acceptance test for aosmap.kit.babel_checks: it must reproduce the legacy validation.json of the maps it replaces.

Each map dir must hold the .vxl plus the git-ignored build artefacts its old checker read (mat.npy, terrain_H.npy,
build.json); rebuild them first with the map's own generator, e.g.
    python scenes/hollow_crown/hc_main.py <scratch>/hc
    (cd scenes/silverpine_hunt_v2 && python sph_main.py <scratch>/sph)
    (cd scenes/bloomhop_kingdom && python main.py <scratch>/bk 955290020)   # needs libvxlenc.so built first

    python tools/kit_acceptance.py --hc <scratch>/hc maps/the_hollow_crown_v1_1/validation.json \
        --sph <scratch>/sph maps/silverpine_hunt_v2_2/validation.json \
        --bk <scratch>/bk maps/bloomhop_kingdom_v1/validation.json [--out report.json]

Exit code 0 only if every compared value matches.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from aosmap.kit import babel_checks as bc  # noqa: E402


def _load(d, name):
    data = open(os.path.join(d, name), 'rb').read()
    b = json.load(open(os.path.join(d, 'build.json'))) if os.path.exists(os.path.join(d, 'build.json')) else {}
    mat = np.load(os.path.join(d, 'mat.npy')) if os.path.exists(os.path.join(d, 'mat.npy')) else None
    H = np.load(os.path.join(d, 'terrain_H.npy')) if os.path.exists(os.path.join(d, 'terrain_H.npy')) else None
    return data, b, mat, H


def _cmp(rows, label, kit, legacy):
    rows.append({'check': label, 'kit': kit, 'legacy': legacy, 'match': kit == legacy})


def hc_family(rows, R, L, extra_route_keys):
    _cmp(rows, 'reader', {k: R['reader'][k] for k in L['reader']}, L['reader'])
    if 'pyspades' in L:
        _cmp(rows, 'pyspades', {k: R['pyspades'][k] for k in ('generate_identical', 'solid_mismatch_20k',
                                                               'colour_mismatch_20k')},
             {k: L['pyspades'][k] for k in ('generate_identical', 'solid_mismatch_20k', 'colour_mismatch_20k')})
    _cmp(rows, 'floating count', R['floating_components']['count'], L['floating_components']['count'])
    _cmp(rows, 'mirror solid', R['mirror']['solid_mismatch'], L['mirror_solid_mismatch'])
    _cmp(rows, 'mirror material', R['mirror']['material_mismatch'], L['mirror_material_mismatch'])
    _cmp(rows, 'platform volume', R['platform_volume_voxels'], L['platform_volume_voxels'])
    _cmp(rows, 'platform margin', R['platform_margin_voxels'], L['platform_margin_voxels'])
    _cmp(rows, 'ground under ends', list(R['ground_under_platform_ends'].values()),
         list(L['ground_under_platform_ends'].values()))
    for t in ('blue', 'red'):
        _cmp(rows, f'spawn tops {t}', R['spawn_squares'][t]['top_z_values'], L['spawn_squares'][t]['top_z_values'])
    _cmp(rows, 'spawn mirror equal', R['spawn_squares']['mirror_equal_share'] == 1.0, L['spawn_heights_mirror_equal'])
    for t in ('blue', 'red'):
        keys = ['to_own_platform_end', 'to_enemy_spawn', 'reachable_nodes_pct'] + extra_route_keys
        _cmp(rows, f'routes {t}', {k: R['routes'][t].get(k) for k in keys}, {k: L['routes'][t].get(k) for k in keys})
    _cmp(rows, 'build gap', {k: R['build_gap']['blue'][k] for k in L['build_gap']}, L['build_gap'])
    for t in ('blue', 'red'):
        e = R['spawn_exposure'][t]
        _cmp(rows, f'exposure {t}', {k: e[k] for k in L['spawn_exposure'][t]}, L['spawn_exposure'][t])


def run_hc(d, legacy):
    data, b, mat, H = _load(d, 'the_hollow_crown.vxl')
    R = bc.run_all(data, build=b, mat=mat, terrain_H=H, end_z=(30, 62), trap_anchor=(180, 332, 214, 298, 42, 42),
                   trap_stride=5, targets={'throne_hall': (236, 276, 172, 194, 30, 62),
                                           'chapel_door': (250, 262, 62, 70, 0, 62),
                                           'village_square': (230, 282, 436, 470, 30, 62),
                                           'stone_circle_own': {'blue': (36, 56, 246, 266, 0, 62),
                                                                'red': (456, 476, 246, 266, 0, 62)}})
    L = json.load(open(legacy))
    rows = []
    hc_family(rows, R, L, ['to_throne_hall', 'to_chapel_door', 'to_village_square', 'to_stone_circle_own'])
    _cmp(rows, 'trap cells', R['trap_cells']['count'], L['trap_cells_ground']['count'])
    _cmp(rows, 'interiors', [R['interiors']['checked'], R['interiors']['reachable_and_exit']],
         [L['interiors']['checked'], L['interiors']['reachable_and_exit']])
    return R, rows


def run_sph(d, legacy):
    data, b, mat, _ = _load(d, 'silverpine_hunt.vxl')
    R = bc.run_all(data, build=b, mat=mat, end_z=(30, 62), trap_anchor=(0, 511, 0, 511, 45, 47), trap_stride=7,
                   trap_z=(45, 61), exits={'lake_ice_z50': (50, 50), 'cave_floor_z56': (56, 56),
                                           'creek_z47_48': (47, 48)},
                   targets={'kill_site': (236, 276, 120, 160, 0, 62), 'mine_tunnel': (150, 362, 412, 420, 44, 47),
                            'nest_hall': (230, 282, 236, 276, 55, 57)})
    L = json.load(open(legacy))
    rows = []
    hc_family(rows, R, L, ['to_kill_site', 'to_mine_tunnel', 'to_nest_hall'])
    _cmp(rows, 'trap cells', R['trap_cells']['count'], L['trap_cells_z45_61']['count'])
    _cmp(rows, 'exits', {k: v['can_reach_anchor_pct'] for k, v in R['exits'].items()},
         {k: v['can_reach_basin_pct'] for k, v in L['exits'].items()})
    return R, rows


def run_bk(d, legacy):
    data, b, _, _ = _load(d, 'bloomhop_kingdom.vxl')
    R = bc.run_all(data, build=b, rules='bloomhop', exposure_preset='bloomhop', axis='x511',
                   tower_zone={'blue': (168, 211, 50, 63), 'red': (300, 343, 50, 63)},
                   build_gap_margin=3, build_gap_graph='any', anchor_face=(212, 299))
    L = json.load(open(legacy))
    rows = []
    _cmp(rows, 'reencode identical', R['reader']['reencode_identical'], L['reencode_identical'])
    _cmp(rows, 'z63 solid', R['reader']['z63_solid'], L['z63_solid_everywhere'])
    _cmp(rows, 'floating (unexpected + kept)', R['floating_components']['count'] +
         R['floating_components']['expected_count'], L['floating_components'])
    _cmp(rows, 'platform clear', R['platform_volume_voxels'] + R['platform_margin_voxels'] == 0,
         L['platform_volume_clear'])
    for k, (t, sq) in enumerate(zip(('blue', 'red'), L['spawn_squares'])):
        s = R['spawn_squares'][t]
        _cmp(rows, f'spawn square {t}', [s['top_z_min'], s['top_z_max'], s['flat_share'], s['water_cols']],
             [sq['zmin'], sq['zmax'], sq['flat_share'], sq['water_columns']])
    _cmp(rows, 'solid mirror equal', round(1 - R['mirror']['solid_mismatch_unfiltered'] / (256 * 512 * 64), 4),
         L['solid_mirror_equal'])
    for t, lt in (('blue', 'team1'), ('red', 'team2')):
        r, lr = R['routes'][t], L['routes'][lt]
        _cmp(rows, f'routes {t}', {'reachable': r['reachable_nodes_any'], 'safe': r['reachable_nodes_safe'],
                                   'tower_zone_cost': r['tower_zone_min_cost'],
                                   'enemy_spawn_cost': r['to_enemy_spawn_any_drop']},
             {'reachable': lr['reachable_nodes'], 'safe': lr['safe_nodes'],
              'tower_zone_cost': lr['tower_zone_min_cost'], 'enemy_spawn_cost': lr['enemy_spawn_min_cost']})
        _cmp(rows, f'build gap {t}', R['build_gap'][t]['highest_reachable_near_platform_z'] - 1, lr['build_gap'])
    _cmp(rows, 'anchor front step', R['anchors']['blue']['enemy_face_step_min'], L['anchor_front_step_min'])
    # Bloomhop's old check measured red on x 373-413 (511 - x mirror of blue's square); the stock server spawns red
    # at 394 +- 20 = x 374-414, which is what the kit measures. Re-run the kit model on the legacy square to show the
    # model itself is identical.
    solid = bc.codec.decode(data)[0]
    legacy_params = dict(bc.BABEL_DEFAULT, bases=((118, 256), (393, 256)))
    e = bc.spawn_exposure(solid, (393, 256), legacy_params, 'bloomhop')
    le = L['spawn_exposure']['team2']
    _cmp(rows, 'exposure red on the legacy square x 373-413',
         [e['exposed_pct'], e['viewers_per_spot_mean'], e['hidden_pct'], e['n_viewers'], e['n_spots']],
         [le['exposed_pct'], le['mean_viewers'], le['hidden_pct'], le['eyes'], le['spots']])
    for t, lt in (('blue', 'team1'),):
        e, le = R['spawn_exposure'][t], L['spawn_exposure'][lt]
        _cmp(rows, f'exposure {t}', [e['exposed_pct'], e['viewers_per_spot_mean'], e['hidden_pct'], e['n_viewers'],
                                     e['n_spots']],
             [le['exposed_pct'], le['mean_viewers'], le['hidden_pct'], le['eyes'], le['spots']])
    return R, rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--hc', nargs=2, metavar=('DIR', 'LEGACY_JSON'))
    ap.add_argument('--sph', nargs=2, metavar=('DIR', 'LEGACY_JSON'))
    ap.add_argument('--bk', nargs=2, metavar=('DIR', 'LEGACY_JSON'))
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    report, ok = {}, True
    for key, fn in (('hc', run_hc), ('sph', run_sph), ('bk', run_bk)):
        args = getattr(a, key)
        if not args:
            continue
        R, rows = fn(*args)
        report[key] = {'rows': rows, 'new_checks': {k: R.get(k) for k in ('safe_descent', 'flank', 'anchors',
                                                                           'periphery', 'trap_cells')},
                       'seconds': R.get('check_seconds')}
        bad = [r for r in rows if not r['match']]
        ok &= not bad
        print(f'== {key}: {len(rows) - len(bad)}/{len(rows)} match ({R.get("check_seconds")} s)')
        for r in bad:
            print(f'   MISMATCH {r["check"]}: kit={r["kit"]} legacy={r["legacy"]}')
    if a.out:
        json.dump(report, open(a.out, 'w'), indent=1, default=str)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
