"""Janjira Sound extra checks on top of aosmap.kit.babel_checks (graph model, numpy; not in-game proof).

boundary        land / solid columns outside the boundary_damage box x 32-480, y 160-352 (must be 0)
water           engine water share (z 62 air) of all columns (classic target >= 75 %)
anchors         both anchor blocks (x 200-216 / 296-312, y 240-272): top-z range, columns with anything on top
platform_margin solid at z <= 3 over the platform or within 1 column of it (must be 0)
spawn_clear     columns of each spawn square with anything standing above the terrain (must be 0)
lane            cells of the lane (square edge -> anchor, y 236-276) with an object taller than 10 (must be 0)
clearance       nearest solid voxel (3D) of each tower / bastion / the dhow to the platform footprint
flank_islands   spawn -> enemy spawn inside the boundary box with the centre band |y - 256| < fmin removed in
                x 176-336 (the kit's default band 130-210 lies outside the boundary box on this map), with the number
                of water (wading) cells on the cheapest route
"""
from __future__ import annotations

import numpy as np

from aosmap.kit import codec
from aosmap.kit.babel_checks import Nav
from aosmap.kit.params import BABEL_DEFAULT as P


def _dist_to_platform(xs, ys, zs):
    (x0, x1), (y0, y1), pz = P['platform_x'], P['platform_y'], P['platform_z']
    dx = np.maximum(np.maximum(x0 - xs, xs - x1), 0)
    dy = np.maximum(np.maximum(y0 - ys, ys - y1), 0)
    dz = np.abs(zs - pz)
    return np.sqrt(dx ** 2 + dy ** 2 + dz ** 2), np.sqrt(dx ** 2 + dy ** 2)


def run(out, data, info, S, H):
    solid = codec.decode(data)[0]
    top = np.argmax(solid, axis=2)
    R = {}
    X, Y = np.indices((512, 512))
    b = S['boundary']
    outside = (X < b['left']) | (X > b['right']) | (Y < b['top']) | (Y > b['bottom'])
    R['boundary'] = {'solid_cols_outside': int(((top < 63) & outside).sum())}
    water = ~solid[:, :, 62]
    R['water'] = {'water_pct': round(100 * float(water.mean()), 2), 'land_cols': int((~water).sum())}
    obj = (top < H)                                   # anything standing on the terrain
    an = {}
    for name, (xa, xb) in (('blue', S['anchor']['x']), ('red', (512 - S['anchor']['x'][1], 512 - S['anchor']['x'][0]))):
        ya, yb = S['anchor']['y']
        t = top[xa:xb + 1, ya:yb + 1]
        an[name] = {'x': [xa, xb], 'y': [ya, yb], 'top_z_min': int(t.min()), 'top_z_max': int(t.max()),
                    'cols_with_props': int(obj[xa:xb + 1, ya:yb + 1].sum()),
                    'air_gap_cols': int(sum((~solid[x, y, top[x, y]:63]).any() for x in range(xa, xb + 1)
                                            for y in range(ya, yb + 1)))}
    R['anchors'] = an
    (px0, px1), (py0, py1) = P['platform_x'], P['platform_y']
    R['platform_margin'] = {'solid_z_le_3': int(solid[px0 - 1:px1 + 2, py0 - 1:py1 + 2, :4].sum())}
    h = P['spawn_half']
    R['spawn_clear'] = {}
    for name, (bx, by) in zip(('blue', 'red'), P['bases']):
        R['spawn_clear'][name] = int(obj[bx - h:bx + h + 1, by - h:by + h + 1].sum())
    lane = {}
    for name, (xa, xb) in (('blue', (139, 199)), ('red', (313, 373))):
        hh = (H - top)[xa:xb + 1, 236:277]
        lane[name] = {'cells_over_10': int((hh > 10).sum()), 'max_h': int(hh.max())}
    R['lane'] = lane
    # clearance of each tall piece to the platform footprint
    pieces = {}
    for (cx, cy) in S['watch_towers']:
        pieces[f'watch tower ({cx},{cy})'] = (cx - 12, cx + 12, cy - 12, cy + 12)
        pieces[f'watch tower ({512 - cx},{512 - cy})'] = (500 - cx, 524 - cx, 500 - cy, 524 - cy)
    for (cx, cy) in S['gate_bastions'] + S['corner_bastions']:
        pieces[f'bastion ({cx},{cy})'] = (cx - 12, cx + 12, cy - 12, cy + 12)
    pieces['dhow'] = tuple(info['dhow']['box'])
    clr = {}
    for nm, (a, bb, c, d) in pieces.items():
        sub = solid[a:bb + 1, c:d + 1, :62].copy()
        hs = H[a:bb + 1, c:d + 1]
        zz = np.arange(62)[None, None, :]
        sub &= zz < hs[:, :, None] - 1                # above the terrain only
        xs, ys, zs = np.nonzero(sub)
        if len(xs) == 0:
            continue
        d3, d2 = _dist_to_platform(xs + a, ys + c, zs)
        k = int(np.argmin(d3))
        clr[nm] = {'nearest_3d': round(float(d3[k]), 1), 'at': [int(xs[k] + a), int(ys[k] + c), int(zs[k])],
                   'nearest_2d': round(float(d2.min()), 1), 'top_z': int(zs.min())}
    R['clearance'] = clr
    # flank routes on the islands (inside the boundary box): steps, and whether a dry (no wading) route exists
    nav = Nav(solid)
    p = nav.xyz
    wat = p[:, 2] == 63
    inb = (p[:, 0] >= b['left']) & (p[:, 0] <= b['right']) & (p[:, 1] >= b['top']) & (p[:, 1] <= b['bottom'])
    fl = {}
    src = nav.nodes_in(P['bases'][0][0] - h, P['bases'][0][0] + h, 236, 276, 0, 62)
    dst = nav.nodes_in(P['bases'][1][0] - h, P['bases'][1][0] + h, 236, 276, 0, 62)
    for fmin in (50, 60, 70):
        for side, sgn in (('north', -1), ('south', 1)):
            dy = (p[:, 1] - 256) * sgn
            band = (p[:, 0] >= 176) & (p[:, 0] <= 336)
            ok = inb & (~band | (dy >= fmin))
            d = nav.dist_from(src, allowed=np.nonzero(ok)[0])
            d_dry = nav.dist_from(src, allowed=np.nonzero(ok & ~wat)[0])
            fl[f'{side}_{fmin}'] = {'steps': float(d[dst].min()) if np.isfinite(d[dst]).any() else None,
                                    'dry_route': bool(np.isfinite(d_dry[dst]).any())}
    R['flank_islands'] = fl
    # centre footprint: the kit rule is N/A here (central zone land 0.46 < 0.50); report the measured median anyway
    from aosmap.kit import zones
    zr = zones.zone_rules(solid, overrides={'applicable_land_min': 0.3}, terrain_H=H)
    R['centre_footprint_relaxed'] = {'note': 'applicable_land_min lowered to 0.3 for reporting only',
                                     'status': zr['centre_footprint']['status'],
                                     'values': zr['centre_footprint']['values']}
    return R
