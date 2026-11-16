"""Northgale Freighter extra checks on top of aosmap.kit.babel_checks (graph model, numpy; not in-game proof).

boundary        ground columns (z 62 solid) outside the boundary_damage box (must be 0: the deep sea is open water)
water           engine water share (z 62 air) of all columns (classic target 70-80 %)
anchors         the flat deck under both platform ends (x 200-216 / 296-312, y 240-272): top-z range, props on top
platform_margin solid at z <= 3 over the platform or within 1 column of it (must be 0)
spawn_clear     columns of each spawn square with anything more than 1 above the deck (hatch panels are 1)
lane            cells of the lane (square edge -> anchor, y 236-276) with an object taller than 10 (must be 0)
clearance       nearest solid voxel (3D) of each tall piece (cranes, bridge, foremast, funnel) to the platform
below_deck      route steps spawn -> tween deck / lower hold / forecastle store / sea (safe graph)
"""
from __future__ import annotations

import numpy as np

from aosmap.kit import codec
from aosmap.kit.babel_checks import Nav
from aosmap.kit.params import BABEL_DEFAULT as P


def run(out, data, info, S, H):
    solid = codec.decode(data)[0]
    top = np.argmax(solid, axis=2)
    R = {}
    X, Y = np.indices((512, 512))
    b = S['boundary']
    outside = (X < b['left']) | (X > b['right']) | (Y < b['top']) | (Y > b['bottom'])
    R['boundary'] = {'ground_cols_outside': int((solid[:, :, 62] & outside).sum())}
    water = ~solid[:, :, 62]
    R['water'] = {'water_pct': round(100 * float(water.mean()), 2), 'land_cols': int((~water).sum())}
    obj = top < H - 1
    an = {}
    for name, (xa, xb) in (('blue', (200, 216)), ('red', (296, 312))):
        t = top[xa:xb + 1, 240:273]
        an[name] = {'top_z_min': int(t.min()), 'top_z_max': int(t.max()),
                    'cols_with_props': int(obj[xa:xb + 1, 240:273].sum())}
    R['anchors'] = an
    (px0, px1), (py0, py1) = P['platform_x'], P['platform_y']
    R['platform_margin'] = {'solid_z_le_3': int(solid[px0 - 1:px1 + 2, py0 - 1:py1 + 2, :4].sum())}
    h = P['spawn_half']
    R['spawn_clear'] = {}
    for name, (bx, by) in zip(('blue', 'red'), P['bases']):
        R['spawn_clear'][name] = {'cols_over_1': int(obj[bx - h:bx + h + 1, by - h:by + h + 1].sum()),
                                  'top_z': sorted(set(int(v) for v in top[bx - h:bx + h + 1,
                                                                            by - h:by + h + 1].ravel()))}
    lane = {}
    for name, (xa, xb) in (('blue', (139, 199)), ('red', (313, 373))):
        hh = (H - top)[xa:xb + 1, 236:277]
        lane[name] = {'cells_over_10': int((hh > 10).sum()), 'max_h': int(hh.max())}
    R['lane'] = lane
    pieces = {'crane NW': (184, 206, 210, 226), 'crane NE': (306, 328, 210, 226),
              'bridge': (446, 478, 207, 305), 'foremast': (28, 42, 248, 264), 'funnel+smoke': (480, 511, 240, 272)}
    clr = {}
    for nm, (a, bb, c, d) in pieces.items():
        sub = solid[a:bb + 1, c:d + 1, :38]
        xs, ys, zs = np.nonzero(sub)
        if len(xs) == 0:
            continue
        xs, ys = xs + a, ys + c
        dx = np.maximum(np.maximum(px0 - xs, xs - px1), 0)
        dy = np.maximum(np.maximum(py0 - ys, ys - py1), 0)
        d3 = np.sqrt(dx ** 2 + dy ** 2 + (zs - P['platform_z']) ** 2)
        k = int(np.argmin(d3))
        clr[nm] = {'nearest_3d': round(float(d3[k]), 1), 'top_z': int(zs.min())}
    R['clearance'] = clr
    nav = Nav(solid)
    bx, by = P['bases'][0]
    src = nav.nodes_in(bx - h, bx + h, by - h, by + h, 0, 62)
    d = nav.dist_from(src)
    tg = {'tween_deck': (82, 168, 208, 304, 49, 51), 'lower_hold': (178, 250, 212, 300, 58, 60),
          'forecastle_store': (26, 62, 230, 282, 39, 41), 'sea_north': (100, 400, 150, 190, 62, 63),
          'islet_north': (80, 112, 100, 132, 50, 62), 'red_spawn': (374, 414, 236, 276, 30, 41)}
    bd = {}
    for k, box in tg.items():
        n = nav.nodes_in(*box)
        dd = d[n] if len(n) else np.array([np.inf])
        bd[k] = float(dd.min()) if np.isfinite(dd).any() else None
    R['below_deck_routes_blue'] = bd
    R['centre_footprint_relaxed'] = centre_relaxed(solid, H)
    return R


def centre_relaxed(solid, H):
    """The kit centre rule is N/A here (central zone land < 0.50: the sea); report the measured median anyway."""
    from aosmap.kit import zones
    zr = zones.zone_rules(solid, overrides={'applicable_land_min': 0.3}, terrain_H=H)
    return {'note': 'applicable_land_min lowered to 0.3 for reporting only',
            'status': zr['centre_footprint']['status'], 'values': zr['centre_footprint']['values']}
