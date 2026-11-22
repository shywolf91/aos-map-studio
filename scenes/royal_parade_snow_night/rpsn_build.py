"""Royal Parade Snow Night: geometry pass (the graybox of this rework).

original map (read-only) -> materials -> festive vehicles (gift trucks, tree floats, two sleigh floats) -> light spawn
cover (great trees, sleigh, drifts) -> street lamps -> snow details (snowmen, kerb drifts, icicles; OS seed) ->
connectivity audit. Original colours stay; new pieces get function colours (rpsn_props.FUNC) until rpsn_art.

build(spec, deco_seed) -> (cv, rep, P, orig_solid)
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from aosmap.kit import noise, symmetry

import rpsn_props as props
import rpsn_source


def _vehicle_masks(cv, spec, lab):
    """name -> boolean mask (full size, z < street) of the vehicle's original component."""
    out = {}
    zs = spec['street_z']
    for name, box in spec['vehicles'].items():
        x0, x1, y0, y1 = box
        sub = lab[x0:x1 + 1, y0:y1 + 1]
        ids, cnt = np.unique(sub[sub > 0], return_counts=True)
        best = None
        for i in ids:
            m = lab == i
            xs, ys = np.nonzero(m.any(2))
            if (xs.min(), xs.max(), ys.min(), ys.max()) == (x0, x1, y0, y1):
                best = m
                break
        if best is None:
            raise SystemExit(f'vehicle {name} not found')
        full = np.zeros(cv.solid.shape, bool)
        full[:, :, :zs] = best
        out[name] = full
    return out


def festive_vehicles(cv, spec, P, lab, rng_layout):
    rep = {}
    masks = _vehicle_masks(cv, spec, lab)
    for name, cfg in spec['gift_stack'].items():
        x0, x1 = cfg['x']
        bx = spec['vehicles'][name]
        rep[name] = props.gift_stack(P, masks[name], x0, x1, bx[2], bx[3], cfg['top_z'], rng_layout,
                                     name=f'{name} gift stack')
    for name, cfg in spec['tree_float'].items():
        cx, cy = cfg['c']
        rec, _ = props.fir(P, cx, cy, cfg['r'], cfg['h'], mat='floattree', tub=False, name=f'{name} tree')
        rep[name] = rec
    for name, facing in (('sleigh_w', 'x+'), ('sleigh_e', 'x-')):
        box = spec['vehicles'][name]
        h_old = spec['street_z'] - int(np.nonzero(masks[name].any((0, 1)))[0].min())
        rep[name] = props.sleigh_float(P, cv, masks[name], box, facing, h_old, name=f'{name} santa sleigh')
        rep[name]['h_before'] = h_old
    # every other listed vehicle keeps its geometry and gets a parade livery in the art pass
    return rep, masks


def spawn_cover(cv, spec, P, rng_layout):
    rep = {}
    for team, pieces in spec['cover'].items():
        out = []
        for pc in pieces:
            k = pc['kind']
            if k == 'great_tree':
                rec, _ = props.fir(P, pc['c'][0], pc['c'][1], pc['r'], pc['h'], mat='greattree', tub=True,
                                   name=pc['name'])
            elif k == 'drift':
                rec = props.drift(P, *pc['x'], *pc['y'], pc['h'], rng_layout, mat='coverdrift', name=pc['name'],
                                  zmin=spec['street_z'] - 3)
            elif k == 'sleigh':
                facing = 1 if team == 'blue' else -1
                rec = props.sleigh(P, *pc['x'], *pc['y'], pc['h'], facing, mat='parkedsleigh', name=pc['name'],
                                   zmin=spec['street_z'] - 3)
            else:
                raise ValueError(k)
            rec['team'] = team
            out.append(rec)
            if pc.get('snowman'):                        # a snowman built into the drift (cover + vignette)
                sx, sy = pc['snowman']
                sm = props.snowman(P, sx, sy, rng_layout, name=pc['name'] + ' snowman')
                sm['team'] = team
                out.append(sm)
        rep[team] = out
    return rep


def street_lamps(cv, spec, P):
    L = spec['lamps']
    top = np.argmax(cv.solid, axis=2)
    lights = []
    for y in L['rows_y']:
        for x0 in range(L['x_range'][0], L['x_range'][1] + 1, L['x_step']):
            for dx in (0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6, -6):
                x = x0 + dx
                if P.forbid[x - 2:x + 3, y - 2:y + 3].any():
                    continue
                area = top[x - 2:x + 3, y - 2:y + 3]
                if (area == spec['street_z']).all():
                    rec = props.lamp(P, x, y, L['post_h'], name=f'lamp {x},{y}')
                    lights.append(rec['light'])
                    top = np.argmax(cv.solid, axis=2)
                    break
    return {'count': len(lights), 'lights': lights}


def _free_street(cv, spec, P):
    """Street columns with nothing standing on them (top == street level), outside the protected boxes."""
    top = np.argmax(cv.solid, axis=2)
    return (top == spec['street_z']) & ~P.forbid


def snowmen(cv, spec, P, rng, lamp_rep):
    S = spec['snowmen']
    free = _free_street(cv, spec, P)
    r = S['clear_r'] + 1
    ok = ndi.binary_erosion(free, structure=np.ones((2 * r + 1, 2 * r + 1), bool))
    by0, by1 = spec['boulevard_y']
    ok[:, by0 - 1:by1 + 2] = False                  # keep the boulevard lanes clear
    near = np.zeros_like(ok)
    for (x, y, _) in lamp_rep['lights']:
        near[max(0, x - 6):x + 7, max(0, y - 6):y + 7] = True
    for (x0, x1, y0, y1) in spec['spawn_squares'].values():
        near[x0 - 6:x1 + 7, y0 - 6:y1 + 7] = True
    ok &= ~near
    cand = np.argwhere(ok)
    rng.shuffle(cand)
    chosen, recs = [], []
    for (x, y) in cand:
        if len(chosen) >= S['count']:
            break
        if any((x - a) ** 2 + (y - b) ** 2 < S['min_spacing'] ** 2 for a, b in chosen):
            continue
        chosen.append((int(x), int(y)))
        props.drift(P, int(x) - 4, int(x) + 4, int(y) - 4, int(y) + 4, 2, rng, mat='kerbdrift',
                    name=f'snowman drift {x},{y}', zmin=spec['street_z'] - 3)
        recs.append(props.snowman(P, int(x), int(y), rng, name=f'snowman {x},{y}'))
    return {'count': len(recs), 'at': chosen}


def kerb_drifts(cv, spec, P, rng, seed):
    """1-2 high snow drifts along building feet, broken up by noise; never in an opening, never narrowing a lane
    below 4 free columns."""
    K = spec['kerb_drift']
    zs = spec['street_z']
    bmat = cv.materials['building']
    wall = (cv.mat[:, :, zs - 3:zs] == bmat).all(axis=2)             # building wall solid at z 53..55
    wall2 = wall & (cv.mat[:, :, zs - 4] == bmat)
    free = _free_street(cv, spec, P)
    n1 = noise.fbm2((512, 512), K['cell'], 3, 'kerb', seed)
    added1 = added2 = 0
    for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nb = np.roll(wall, (-dx, -dy), axis=(0, 1))                  # wall at (x+dx, y+dy)
        nb2 = np.roll(wall2, (-dx, -dy), axis=(0, 1))
        # free run of street away from the wall: (x-dx*k, y-dy*k) for k = 0..3
        run = free.copy()
        for k in range(1, 4):
            run &= np.roll(free, (dx * k, dy * k), axis=(0, 1))
        cand = run & nb & (n1 > K['thresh_1'])
        for (x, y) in np.argwhere(cand):
            if not cv.solid[x, y, zs - 1]:
                if P.put(int(x), int(y), zs - 1, props.FUNC['snow'], 'kerbdrift'):
                    added1 += 1
            if nb2[x, y] and n1[x, y] > K['thresh_2'] and cv.solid[x, y, zs - 1] and not cv.solid[x, y, zs - 2]:
                if P.put(int(x), int(y), zs - 2, props.FUNC['snow'], 'kerbdrift'):
                    added2 += 1
    return {'cols_1': added1, 'cols_2': added2}


def icicles(cv, spec, P, rng):
    """Short icicles (1-3) under the top edges of building facades; each hangs face-connected to the edge."""
    I = spec['icicles']
    zs = spec['street_z']
    bmat = cv.materials['building']
    S = cv.solid
    edge = (cv.mat == bmat) & S
    edge[:, :, 1:] &= ~S[:, :, :-1]                       # nothing above: a top edge
    edge[:, :, zs - I['min_height']:] = False             # at least min_height above the street
    n = 0
    used = np.zeros((512, 512), bool)
    for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        out_air = ~np.roll(S, (-dx, -dy), axis=(0, 1))            # the outward cell at the same z is air
        pts = np.argwhere(edge & out_air)
        for (x, y, z) in pts:
            ox, oy = x + dx, y + dy
            if not (0 <= ox < 512 and 0 <= oy < 512) or used[ox, oy] or P.forbid[ox, oy]:
                continue
            if S[ox, oy, z:z + I['min_height']].any():
                continue                                  # not a sheer drop: a roof step or a ledge
            if rng.random() > I['spacing_p']:
                continue
            if used[max(0, ox - 1):ox + 2, max(0, oy - 1):oy + 2].any():
                continue
            L = int(rng.choice([1, 1, 2, 2, 3])) if I['max_len'] >= 3 else 1
            for k in range(L):
                P.put(int(ox), int(oy), int(z + k), props.FUNC['snow'], 'icicle')
            used[ox, oy] = True
            n += 1
    return {'count': n}


def connectivity(cv, orig_floating):
    """Floating components after the geometry pass vs the original's; new pieces must all be grounded."""
    fl = symmetry.floating_components(cv.solid)
    key = {(tuple(f['x']), tuple(f['y']), tuple(f['z']), f['voxels']) for f in orig_floating}
    new = [f for f in fl if (tuple(f['x']), tuple(f['y']), tuple(f['z']), f['voxels']) not in key]
    return {'floating_now': len(fl), 'floating_original': len(orig_floating), 'new_floating': new}


def build(spec, deco_seed):
    solid, rgb, sha = rpsn_source.load(spec)
    orig_solid = solid.copy()
    orig_floating = symmetry.floating_components(solid)
    cv, cinfo, lab = rpsn_source.classify(spec, solid, rgb)
    for f in orig_floating:                                # original jets + stubs: expected floating, kept as-is
        cv.expect('original floating piece', f['x'][0], f['x'][1], f['y'][0], f['y'][1], f['z'][0], f['z'][1])
    P = props.Placer(cv, spec['no_new_geometry'])
    rng_layout = np.random.default_rng(spec['layout_seed'])
    rng = np.random.default_rng(deco_seed)
    rep = {'source_sha256': sha, 'classify': cinfo}
    rep['vehicles'], vmasks = festive_vehicles(cv, spec, P, lab, rng_layout)
    rep['cover'] = spawn_cover(cv, spec, P, rng_layout)
    rep['lamps'] = street_lamps(cv, spec, P)
    rep['snowmen'] = snowmen(cv, spec, P, rng, rep['lamps'])
    rep['kerb_drifts'] = kerb_drifts(cv, spec, P, rng, deco_seed)
    rep['icicles'] = icicles(cv, spec, P, rng)
    rep['connectivity'] = connectivity(cv, orig_floating)
    rep['placer_refused'] = P.refused
    rep['pieces'] = P.pieces
    rep['vehicle_names'] = {k: v for k, v in spec['vehicles'].items()}
    return cv, rep, P, orig_solid, vmasks


def build_recolor(spec, deco_seed):
    """Recolour-only variant: the original geometry untouched (+0 / -0 voxels, asserted). Festive vehicles, windows,
    string lights and bunting become paint in rpsn_art; the original 2-column street posts ('figure' components)
    serve as the lamps: their open-topped top voxel becomes the lantern (glow) and the pool is painted around it."""
    solid, rgb, sha = rpsn_source.load(spec)
    orig_solid = solid.copy()
    orig_floating = symmetry.floating_components(solid)
    cv, cinfo, lab = rpsn_source.classify(spec, solid, rgb)
    for f in orig_floating:
        cv.expect('original floating piece', f['x'][0], f['x'][1], f['y'][0], f['y'][1], f['z'][0], f['z'][1])
    P = props.Placer(cv, spec['no_new_geometry'])
    fig = cv.materials.get('figure')
    lights = []
    if fig is not None:
        fl, _ = ndi.label(cv.mat == fig)
        for sl in ndi.find_objects(fl):
            if sl is None:
                continue
            z = sl[2].start
            xs, ys = np.nonzero(cv.solid[sl][:, :, 0] & (cv.mat[sl][:, :, 0] == fig))
            x, y = int(xs[0] + sl[0].start), int(ys[0] + sl[1].start)
            if z == 0 or not cv.solid[x, y, z - 1]:                   # open top face
                lights.append([x, y, int(z)])
    rep = {'source_sha256': sha, 'classify': cinfo, 'vehicles': {}, 'cover': {},
           'lamps': {'count': len(lights), 'lights': lights, 'note': 'original street posts used as lamps'},
           'snowmen': {'count': 0}, 'kerb_drifts': {'cols_1': 0, 'cols_2': 0}, 'icicles': {'count': 0},
           'connectivity': connectivity(cv, orig_floating), 'placer_refused': 0, 'pieces': [],
           'vehicle_names': dict(spec['vehicles'])}
    assert np.array_equal(cv.solid, orig_solid), 'recolour variant changed geometry'
    return cv, rep, P, orig_solid, {}
