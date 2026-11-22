"""Graybox additions for Christmas PVP v2: spawn cover (west, mirrored x' = 512 - x) and the light layout.

Geometry added: three lit firs, low snow drifts, a gift pile and a parked sleigh per spawn, all outside the stock
+/-20 spawn squares. The light strings are paint on existing voxels (wall garlands, rail bulbs, tower rings, tree
strings, lamp heads, path stars, warm windows): no geometry, so the arena walls give no new footholds.

Every function returns plain data (positions, boxes) so the art pass and the checks can reuse it.
Graybox colours are function colours; cp_art repaints every material.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage as ndi

from aosmap.kit import noise, veg

FUNC = {  # graybox function colours
    'cover_trunk': (120, 80, 40), 'cover_leaf': (40, 160, 60), 'cover_snow': (230, 230, 240),
    'drift': (220, 220, 235), 'gift': (230, 60, 200), 'gift_ribbon': (250, 230, 60),
    'sleigh': (220, 40, 40), 'sleigh_trim': (250, 200, 40), 'runner': (60, 60, 70),
    'bauble': (240, 60, 60), 'garland': (20, 200, 120), 'bulb': (255, 255, 0),
}


def _floor(cv, x, y):
    return int(np.argmax(cv.solid[x, y]))


# ------------------------------------------------------------------------------------------------ cover pieces
def lit_fir(cv, lrng, drng, t, min_x, skirts=(6.0, 4.8, 3.6, 2.4), lengths=(4, 4, 4, 3)):
    """Stacked-skirt fir: 2x2 trunk, crown from `clear` above the floor (walk under it), four skirts that narrow
    going up (each tapers to 45 % of its base radius), snow only on the up-facing lip of each skirt, a darker
    inner core, a warm star and five warm bulbs (2 on the lowest skirt, 1 on each other). Crown radius never exceeds t['r'].
    Geometry from the layout rng; bulb angles from the OS-seeded rng."""
    x, y, h, R, clear = t['x'], t['y'], t['h'], t['r'], t['clear']
    g = min(_floor(cv, x + dx, y + dy) for dx in (0, 1) for dy in (0, 1))
    for k in range(h):
        for dx in (0, 1):
            for dy in (0, 1):
                cv.set(x + dx, y + dy, g - 1 - k, FUNC['cover_trunk'], 'cover_trunk')
    jag = veg._jag(lrng)
    cx, cy = x + 0.5, y + 0.5
    k = clear
    lips, bulbs = [], []
    ph = drng.random() * 2 * math.pi
    for si, (rb, n) in enumerate(zip(skirts, lengths)):
        rb = min(rb * R / 6.0, R)
        for j in range(n):
            if k > h:
                break
            r = rb * (1 - 0.55 * j / max(n - 1, 1))
            z = g - 1 - k
            ri = int(math.ceil(r + 2))
            ring = []
            for X in range(x - ri, x + ri + 2):
                if X < min_x:
                    continue
                for Y in range(y - ri, y + ri + 2):
                    d = math.hypot(X - cx, Y - cy)
                    rr = min(R, r * (1 + 0.6 * (jag(math.atan2(Y - cy, X - cx)) - 1)))
                    if d <= rr and not cv.solid[X, Y, z]:
                        inner = d < 0.55 * rr
                        cv.set(X, Y, z, FUNC['cover_leaf'], 'fir_inner' if inner else 'cover_leaf')
                        if j == 0 and not inner:
                            ring.append((X, Y, z, d))
            if j == 0:
                lips += [p[:3] for p in ring]
                if ring:
                    for a in (ph + si * 2.1, ph + si * 2.1 + math.pi)[:2 if si == 0 else 1]:
                        best = max(ring, key=lambda p: math.cos(math.atan2(p[1] - cy, p[0] - cx) - a) * 3 + p[3])
                        bulbs.append(best[:3])
            k += 1
    # snow only on the up-facing lip of each skirt (the bottom ring that sticks out under the next skirt)
    for (X, Y, z) in lips:
        if not cv.solid[X, Y, z - 1] and noise.hash3(np.array([X]), np.array([Y]), np.array([z]), 41)[0] < 0.75:
            cv.set(X, Y, z, FUNC['cover_snow'], 'cover_snow')
    tip = g - 1 - h
    cv.set(x, y, tip, FUNC['cover_leaf'], 'cover_leaf')               # leader shoot under the star
    cv.set(x, y, tip - 1, FUNC['cover_leaf'], 'cover_leaf')
    centre = (x, y, tip - 2)
    arms = [(x - 1, y, tip - 2), (x + 1, y, tip - 2), (x, y - 1, tip - 2), (x, y + 1, tip - 2)]
    cv.set(*centre, FUNC['bulb'], 'star')
    for p in arms:
        cv.set(*p, FUNC['bulb'], 'star')
    for p in bulbs:                                                    # bulbs replace lip voxels (snow or leaf)
        cv.set(*p, FUNC['bulb'], 'cover_leaf')
    return {'name': t['name'], 'floor_z': g, 'tip_z': tip - 2, 'bulbs': bulbs, 'star': [centre] + arms,
            'baubles': 0, 'box': [max(min_x, x - int(R) - 1), x + int(R) + 2, y - int(R) - 1, y + int(R) + 2]}


def drift(cv, d):
    out = 0
    for X in range(d['x'] - d['rx'], d['x'] + d['rx'] + 1):
        for Y in range(d['y'] - d['ry'], d['y'] + d['ry'] + 1):
            q = ((X - d['x']) / (d['rx'] + 0.5)) ** 2 + ((Y - d['y']) / (d['ry'] + 0.5)) ** 2
            if q > 1:
                continue
            hh = int(round(d['h'] * (1 - q) + 0.3))
            g = _floor(cv, X, Y)
            for k in range(hh):
                if not cv.solid[X, Y, g - 1 - k]:
                    cv.set(X, Y, g - 1 - k, FUNC['drift'], 'drift')
                    out += 1
    return out


def gifts(cv, boxes):
    for b in boxes:
        (x0, x1), (y0, y1), hh = b['x'], b['y'], b['h']
        g = max(_floor(cv, X, Y) for X in range(x0, x1 + 1) for Y in range(y0, y1 + 1))
        cxm, cym = (x0 + x1) // 2, (y0 + y1) // 2
        for X in range(x0, x1 + 1):
            for Y in range(y0, y1 + 1):
                for k in range(hh):
                    z = g - 1 - k
                    rib = X == cxm or Y == cym
                    cv.set(X, Y, z, FUNC['gift_ribbon' if rib else 'gift'], 'gift_ribbon' if rib else 'gift')
                # fill any gap down to the floor so nothing floats on uneven ground
                zz = g
                while zz < 63 and not cv.solid[X, Y, zz]:
                    cv.set(X, Y, zz, FUNC['gift'], 'gift')
                    zz += 1


def sleigh(cv, s):
    (x0, x1), (y0, y1), hh = s['x'], s['y'], s['h']
    g = max(_floor(cv, X, Y) for X in range(x0, x1 + 2) for Y in range(y0, y1 + 1))
    for X in range(x0, x1 + 1):                                  # runners
        for Y in (y0, y1):
            cv.set(X, Y, g - 1, FUNC['runner'], 'runner')
    for Y in (y0, y1):                                          # front curl (east end, toward the platform)
        cv.set(x1 + 1, Y, g - 1, FUNC['runner'], 'runner')
        cv.set(x1 + 1, Y, g - 2, FUNC['runner'], 'runner')
        cv.set(x1 + 1, Y, g - 3, FUNC['runner'], 'runner')
        cv.set(x1, Y, g - 3, FUNC['runner'], 'runner')
    for X in range(x0 + 1, x1):                                 # body floor
        for Y in range(y0, y1 + 1):
            cv.set(X, Y, g - 2, FUNC['sleigh'], 'sleigh')
    for X in range(x0 + 1, x1):                                 # side panels with a gold rim
        for Y in (y0, y1):
            cv.set(X, Y, g - 3, FUNC['sleigh'], 'sleigh')
            if X in (x0 + 1, x1 - 1) or (X - x0) % 3 == 0:
                cv.set(X, Y, g - 4, FUNC['sleigh_trim'], 'sleigh_trim')
    for Y in range(y0, y1 + 1):                                 # tall back, low dash
        for k in (3, 4, 5):
            cv.set(x0 + 1, Y, g - k, FUNC['sleigh' if k < 5 else 'sleigh_trim'], 'sleigh' if k < 5 else 'sleigh_trim')
        cv.set(x1 - 1, Y, g - 3, FUNC['sleigh'], 'sleigh')
    for Y in range(y0 + 1, y1):                                 # bench
        cv.set(x0 + 2, Y, g - 3, FUNC['sleigh_trim'], 'sleigh_trim')
    # gift sack on the back seat
    for (X, Y, k) in ((x0 + 3, y0 + 2, 3), (x0 + 3, y0 + 2, 4), (x0 + 4, y0 + 2, 3), (x0 + 3, y0 + 1, 3)):
        cv.set(X, Y, g - k, FUNC['gift'], 'sack')
    return {'floor_z': g, 'box': [x0, x1 + 1, y0, y1]}


def add_cover(cv, spec, layout_seed, deco_seed):
    """Build the west cover, then copy every new voxel (and glow source) to x' = 512 - x."""
    C = spec['cover']
    lrng = noise.rng('cover_layout', layout_seed)
    drng = np.random.default_rng(deco_seed)
    before = cv.solid.copy()
    rep = {'trees': [], 'drift_voxels': 0}
    for t in C['trees']:
        rep['trees'].append(lit_fir(cv, lrng, drng, t, C['min_x']))
    for d in C['drifts']:
        rep['drift_voxels'] += drift(cv, d)
    gifts(cv, C['gifts'])
    rep['sleigh'] = sleigh(cv, C['sleigh'])
    new = cv.solid & ~before
    # face-connectivity: drop any new voxel that does not reach the ground through faces (diagonal-only floats)
    sub = (slice(C['min_x'], 256), slice(0, 512), slice(0, 64))
    lab, n = ndi.label(cv.solid[sub], structure=ndi.generate_binary_structure(3, 1))
    grounded = np.zeros(n + 1, bool)
    grounded[np.unique(lab[:, :, 63])] = True
    grounded[0] = True
    drop = new[sub] & ~grounded[lab]
    cv.solid[sub][drop] = False
    cv.mat[sub][drop] = 0
    rep['pruned_voxels'] = int(drop.sum())
    new = cv.solid & ~before
    xs, ys, zs = np.nonzero(new)
    assert xs.max() < 256 and xs.min() >= C['min_x'], 'cover must stay west of 256 and outside the spawn square'
    mx = 512 - xs
    clash = before[mx, ys, zs]
    cv.solid[mx, ys, zs] = True
    cv.rgb[mx, ys, zs] = cv.rgb[xs, ys, zs]
    cv.mat[mx, ys, zs] = cv.mat[xs, ys, zs]
    rep['voxels_per_side'] = int(len(xs))
    rep['mirror_clash_voxels'] = int(clash.sum())
    boxes = []
    for t in rep['trees']:
        boxes.append({'name': t['name'], 'box': t['box']})
    boxes.append({'name': 'sleigh', 'box': rep['sleigh']['box']})
    boxes.append({'name': 'gift pile', 'box': [min(b['x'][0] for b in C['gifts']), max(b['x'][1] for b in C['gifts']),
                                               min(b['y'][0] for b in C['gifts']), max(b['y'][1] for b in C['gifts'])]})
    rep['boxes_west'] = boxes
    rep['boxes_east'] = [{'name': b['name'], 'box': [512 - b['box'][1], 512 - b['box'][0], b['box'][2], b['box'][3]]}
                         for b in boxes]
    lights = []
    for t in rep['trees']:
        for p in t['bulbs']:
            lights.append(('fir_string', p))
        lights.append(('fir_star', t['star'][0]))      # star centre glows; the arms are gold paint
    lights += [(k, (512 - p[0], p[1], p[2])) for k, p in lights]
    rep['lights'] = lights
    return rep


# ------------------------------------------------------------------------------------------------ light layout
def wall_faces(cv, spec):
    """Inner face voxel of the perimeter wall per (side, p, z): the last solid of the run that starts at the
    perimeter, only where that run is <= max_face_depth deep (the plain wall core, not a relief or terrace)."""
    (px0, px1), (py0, py1) = spec['perimeter']['x'], spec['perimeter']['y']
    dmax = spec['garland']['max_face_depth']
    S = cv.solid
    out = {}

    def run(get):
        r = 0
        while r < dmax + 1 and get(r):
            r += 1
        return r

    for z in range(0, 57):
        for y in range(py0 + 1, py1):
            r = run(lambda k: S[px0 + k, y, z])
            if 1 <= r <= dmax:
                out[('W', y, z)] = (px0 + r - 1, y, z)
            r = run(lambda k: S[px1 - k, y, z])
            if 1 <= r <= dmax:
                out[('E', y, z)] = (px1 - r + 1, y, z)
        for x in range(px0 + 1, px1):
            r = run(lambda k: S[x, py0 + k, z])
            if 1 <= r <= dmax:
                out[('N', x, z)] = (x, py0 + r - 1, z)
            r = run(lambda k: S[x, py1 - k, z])
            if 1 <= r <= dmax:
                out[('S', x, z)] = (x, py1 - r + 1, z)
    return out


def garlands(cv, spec, faces, wall_mat):
    """Swagged garlands on the plain wall: hooks every `period`, symmetric about x = 256 on the N/S walls and
    identical on W/E (mirror pair). Returns (garland voxels, bulb positions)."""
    G = spec['garland']
    (px0, px1), (py0, py1) = spec['perimeter']['x'], spec['perimeter']['y']
    gar, bulbs = [], []
    per = G['period']

    def swag(p, origin):
        f = ((p - origin) % per) / per
        return G['hook_z'] + G['sag'] * math.sin(math.pi * f)

    sides = {'W': (range(py0 + 6, py1 - 5), py0 + 6), 'E': (range(py0 + 6, py1 - 5), py0 + 6),
             'N': (range(px0 + 6, px1 - 5), 256), 'S': (range(px0 + 6, px1 - 5), 256)}
    for side, (prange, origin) in sides.items():
        for p in prange:
            if side in 'NS':
                q = abs(p - 256)                       # symmetric about 256
                zc = swag(q, 0)
                idx = q
            else:
                zc = swag(p, origin)
                idx = p - origin
            z0 = int(round(zc))
            for k in range(G['thick']):
                key = (side, p, z0 + k)
                v = faces.get(key)
                if v is None or cv.mat[v] != wall_mat:
                    continue
                gar.append(v)
            v = faces.get((side, p, z0 + G['thick']))      # bulbs hang just under the garland
            if v is not None and cv.mat[v] == wall_mat and idx % G['bulb_every'] == 2:
                bulbs.append(v)
    return gar, bulbs


def rail_bulbs(cv, spec, rail_rgb=(142, 33, 33)):
    """Top-exposed rail voxels of the wall coasters (dark red, within max_from_wall of the perimeter)."""
    S = cv.solid
    (px0, px1), (py0, py1) = spec['perimeter']['x'], spec['perimeter']['y']
    m = np.all(cv.rgb == np.array(rail_rgb, np.uint8), axis=-1) & S
    air_up = np.zeros_like(S)
    air_up[:, :, 1:] = ~S[:, :, :-1]
    m &= air_up
    xs, ys, zs = np.nonzero(m)
    dw = np.minimum.reduce([xs - px0, px1 - xs, ys - py0, py1 - ys])
    keep = (dw <= spec['rail']['max_from_wall']) & (zs < 54)
    xs, ys, zs = xs[keep], ys[keep], zs[keep]
    n = spec['rail']['bulb_every']
    # spacing along the rail: a voxel is a bulb if it is the smallest (x+y) in its n-cell of a mirrored lattice
    sel = ((np.abs(xs - 256) + ys + zs) % n) == 0
    return [tuple(int(v) for v in p) for p in zip(xs[sel], ys[sel], zs[sel])]


def tower_rings(cv, boxes, red=(142, 33, 33), every=29):
    """Candy towers: the underside of the red spiral ribbon (red voxel, air below, open to the outside),
    thinned on a lattice that is symmetric about x = 256 -> bulbs hanging under the ribbon."""
    S = cv.solid
    out = []
    for (x0, x1, y0, y1) in boxes:
        sub = (slice(x0, x1 + 1), slice(y0, y1 + 1))
        R = np.all(cv.rgb[sub] == np.array(red, np.uint8), -1) & S[sub]
        below_air = np.zeros_like(R)
        below_air[:, :, :-1] = ~S[sub][:, :, 1:]
        xs, ys, zs = np.nonzero(R & below_air)
        X, Y = xs + x0, ys + y0
        sel = ((np.abs(X - 256) * 3 + Y * 5 + zs * 7) % every) == 0
        out += [(int(a), int(b), int(c)) for a, b, c in zip(X[sel], Y[sel], zs[sel])]
    return out


def tree_strings(cv, boxes, every=5):
    """Giant centre trees: pink / white garland and ornament voxels exposed to air, thinned on a lattice."""
    S = cv.solid
    out = []
    for (x0, x1, y0, y1) in boxes:
        sub = (slice(x0, x1 + 1), slice(y0, y1 + 1))
        c = cv.rgb[sub].astype(int)
        pink = (c[..., 0] > 200) & (c[..., 1] > 120) & (c[..., 1] < 200) & (c[..., 2] > 130)
        white = (c.min(-1) > 215)
        m = (pink | white) & S[sub]
        air = ~S[sub]
        ex = np.zeros_like(m)
        ex[1:] |= air[:-1]; ex[:-1] |= air[1:]; ex[:, 1:] |= air[:, :-1]; ex[:, :-1] |= air[:, 1:]
        ex[:, :, 1:] |= air[:, :, :-1]
        m &= ex
        xs, ys, zs = np.nonzero(m)
        X = xs + x0
        sel = ((np.abs(X - 256) * 3 + (ys + y0) * 5 + zs * 7) % every) == 0
        out += [(int(a), int(b), int(c_)) for a, b, c_ in zip(X[sel], ys[sel] + y0, zs[sel])]
    return out


def gold_heads(cv, exclude_boxes, max_size=60):
    """Small gold components (lamp heads, path stars, finials): their topmost voxel glows."""
    from aosmap.kit import palette
    S = cv.solid
    lch = np.zeros(S.shape + (3,), np.float32)
    lch[S] = palette.rgb_to_oklch(cv.rgb[S].astype(float))
    gold = S & (lch[..., 2] > 70) & (lch[..., 2] < 110) & (lch[..., 1] > 0.12) & (lch[..., 0] > 0.7)
    for (x0, x1, y0, y1) in exclude_boxes:
        gold[x0:x1 + 1, y0:y1 + 1] = False
    gold[:94] = False                                    # paintings on the perimeter wall stay paint
    gold[419:] = False
    gold[:, :135] = False
    gold[:, 379:] = False
    lab, n = ndi.label(gold, structure=ndi.generate_binary_structure(3, 3))
    out = []
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        comp = lab[sl] == i
        sz = int(comp.sum())
        if sz < 3 or sz > max_size:
            continue
        xs, ys, zs = np.nonzero(comp)
        k = np.argmin(zs)
        p = (int(xs[k] + sl[0].start), int(ys[k] + sl[1].start), int(zs[k] + sl[2].start))
        if p[2] >= 61:                                   # flat path stars: use the middle of the star
            k = np.argmin((xs - xs.mean()) ** 2 + (ys - ys.mean()) ** 2)
            p = (int(xs[k] + sl[0].start), int(ys[k] + sl[1].start), int(zs[k] + sl[2].start))
        out.append(p)
    return out


def window_lights(cv, glass_mat):
    """Glass components (gate-house windows): one warm source per pane (the voxel closest to its centre)."""
    m = cv.mat == glass_mat
    lab, n = ndi.label(m, structure=ndi.generate_binary_structure(3, 3))
    out = []
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        comp = lab[sl] == i
        if comp.sum() < 2:
            continue
        xs, ys, zs = np.nonzero(comp)
        k = np.argmin((xs - xs.mean()) ** 2 + (ys - ys.mean()) ** 2 + (zs - zs.mean()) ** 2)
        out.append((int(xs[k] + sl[0].start), int(ys[k] + sl[1].start), int(zs[k] + sl[2].start)))
    return out
