"""Janjira Sound art pass (stage 2): COLOUR ONLY. The solid array is asserted unchanged (result in build.json).

Every voxel addition (plant details, dome finials, the dhow's furled sail) happens earlier, in js_build, before the
checks. Here: materials -> colours (continuous cover model, coherent noise, no speckle), the painted z 63 sea with
shore halos, wave bands, channel currents, sandbar ghosts, reefs, foam and a tide rose; per-plant vegetation hues
with smooth top-to-underside gradients; lamps (existing voxels recoloured to a glow source); baked light + glow bake;
brightness rules; the corner tag painted on the sea.

art(cv, rep, S, veg_seed) -> (stored glow colours, report)
"""
from __future__ import annotations

import hashlib
import math

import numpy as np
from scipy import ndimage as ndi

from aosmap.kit import color, noise, tag
from aosmap.kit.codec import surface_mask

LAMP = (255, 175, 95)                           # glow palette colour (knowledge base §11.4)
GLOW_PALETTE = {(255, 255, 255), (255, 95, 95), (255, 255, 95), (95, 255, 255), (255, 175, 95), (95, 255, 95)}

SAND_WET, SAND_DAMP, SAND_DRY = (164, 146, 112), (186, 166, 126), (204, 184, 142)
LATERITE = (148, 106, 62)
BASALT = (114, 116, 124)
PLASTER = (198, 188, 166)
GREENS = [(74, 114, 62), (86, 126, 68), (98, 134, 74), (110, 142, 82)]
SEA_STOPS = [(0, (174, 202, 182)), (1.5, (150, 196, 178)), (5, (122, 180, 164)), (12, (96, 156, 148)),
             (22, (76, 130, 132)), (38, (58, 106, 116)), (70, (46, 88, 102))]


def _f(tag_, cell, seed, octaves=3):
    return noise.fbm2((512, 512), cell, octaves, tag_, seed)


def _mix(a, b, t):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    t = np.asarray(t, float)[..., None] if np.ndim(t) else t
    return a + (b - a) * t


def _rot(x, y):
    return 512 - x, 512 - y


def art(cv, rep, S, veg_seed):
    seed = S['layout_seed']
    before = hashlib.sha256(np.packbits(cv.solid).tobytes()).hexdigest()
    solid = cv.solid
    surf = surface_mask(solid)
    top = np.argmax(solid, axis=2)
    water = top >= 63
    dland = ndi.distance_transform_edt(water)               # sea: distance to land
    dsea = ndi.distance_transform_edt(~water)               # land: distance to water
    up = np.zeros_like(solid)
    up[:, :, 1:] = ~solid[:, :, :-1]
    up[:, :, 0] = True
    F = {k: _f(k, c, seed) for k, c in (('lo', 48), ('mid', 18), ('fine', 6), ('grass', 30), ('track', 40),
                                        ('lichen', 9), ('streak', 3), ('reef', 22), ('bar', 34), ('foam', 5),
                                        ('wave', 16), ('stone', 4))}
    mid = {v: k for k, v in cv.materials.items()}
    rep_out = {'materials_painted': {}}

    def sel(*names):
        ids = [cv.materials[n] for n in names if n in cv.materials]
        m = surf & np.isin(cv.mat, ids)
        return np.nonzero(m)

    def put(idx, rgb, name):
        cv.rgb[idx] = np.clip(np.rint(rgb), 0, 255).astype(np.uint8)
        rep_out['materials_painted'][name] = int(len(idx[0]))

    # ------------------------------------------------------------------ ground: sand, laterite, grass, rock, paving
    xs, ys, zs = idx = sel('sand')
    if len(xs):
        d = dsea[xs, ys]
        base = color.ramp([(0, SAND_WET), (1.6, SAND_WET), (3.5, SAND_DAMP), (7, SAND_DRY)], d)
        base *= (0.96 + 0.08 * F['mid'][xs, ys])[:, None]
        # tide pools on the damp band: a pale jade wash, soft-edged
        tp = np.clip((F['bar'][xs, ys] - 0.66) / 0.08, 0, 1) * ((d >= 2) & (d <= 5))
        base = _mix(base, (150, 180, 164), 0.45 * tp)
        # shell / pebble flecks: small, clustered, low contrast
        fl = (F['stone'][xs, ys] > 0.78) & (d > 3)
        base[fl] *= 1.05
        put(idx, base, 'sand')

    # causeway / plaza / front: sand with a worn laterite cart track winding along it; packed earth on the plaza
    xs, ys, zs = idx = sel('laterite')
    if len(xs):
        d = dsea[xs, ys]
        xw = np.where(xs <= 256, xs, 512 - xs).astype(float)
        yw = np.where(xs <= 256, ys, 512 - ys).astype(float)
        yc = 256 + 7 * np.sin(xw / 21.0 + 0.6) + 5 * (F['track'][xs, ys] - 0.5)
        w_tr = np.clip(1 - (np.abs(yw - yc) - 2.0) / 3.0, 0, 1)             # track ~6 wide, soft edges
        rut = np.clip(1 - np.abs(np.abs(yw - yc) - 1.5) / 0.9, 0, 1) * 0.06  # two faint wheel ruts
        sand = color.ramp([(0, SAND_WET), (1.6, SAND_WET), (3.5, SAND_DAMP), (8, (198, 176, 136))], d)
        plaza = (xw <= 152)
        earth = _mix(sand, (176, 138, 98), 0.45)                             # packed earth on the plaza
        g = np.where(plaza[:, None], earth, sand)
        lat = np.array(LATERITE, float) * (0.94 + 0.12 * F['mid'][xs, ys])[:, None]
        # beach-grass tufts and damp stains in big soft patches (no speckle), kept off the track
        tuft = np.clip((F['grass'][xs, ys] - 0.62) / 0.12, 0, 1) * np.clip((d - 5) / 4, 0, 1)
        g = _mix(g, (150, 150, 98), 0.35 * tuft)
        damp = np.clip((F['bar'][xs, ys] - 0.6) / 0.15, 0, 1)
        g = _mix(g, (170, 150, 116), 0.25 * damp)
        g = _mix(g, lat, 0.85 * w_tr)
        g *= (1 - rut)[:, None]
        g *= (0.97 + 0.06 * F['fine'][xs, ys])[:, None]
        put(idx, g, 'laterite')

    xs, ys, zs = idx = sel('grass')
    if len(xs):
        h = (63 - zs).astype(float)
        t = np.clip(F['grass'][xs, ys] * 1.4 - 0.2, 0, 1)
        g = color.ramp([(0, GREENS[0]), (0.35, GREENS[1]), (0.7, GREENS[2]), (1, GREENS[3])], t)
        g = _mix(g, (118, 140, 88), np.clip((h - 4) / 6, 0, 1) * 0.3)          # knolls drier and paler
        g = _mix(g, SAND_DAMP, np.clip((3 - dsea[xs, ys]) / 3, 0, 1) * 0.5)   # grass thins toward the beach
        g *= (0.97 + 0.06 * F['fine'][xs, ys])[:, None]
        put(idx, g, 'grass')

    xs, ys, zs = idx = sel('rock')
    if len(xs):
        g = np.array(BASALT, float) * (0.9 + 0.2 * F['mid'][xs, ys])[:, None]
        g = _mix(g, (126, 132, 104), np.clip((F['lichen'][xs, ys] - 0.6) / 0.15, 0, 1) * up[xs, ys, zs] * 0.5)
        g = _mix(g, (86, 92, 96), np.clip((2.5 - dsea[xs, ys]) / 2.5, 0, 1) * 0.5)    # wet at the waterline
        put(idx, g, 'rock')

    xs, ys, zs = idx = sel('paving')
    if len(xs):                                   # basalt flagstones: per-stone value, soft joints
        sx, sy = xs // 4, (ys + (xs // 4) % 2 * 2) // 3
        v = noise.hash3(sx, sy, 0, 11)
        g = np.array((116, 116, 120), float) * (0.92 + 0.12 * v)[:, None]
        joint = ((xs % 4 == 0) | ((ys + (xs // 4) % 2 * 2) % 3 == 0))
        g[joint] *= 0.94
        g = _mix(g, (124, 128, 104), np.clip((F['lichen'][xs, ys] - 0.68) / 0.12, 0, 1) * 0.35)
        put(idx, g, 'paving')

    # ------------------------------------------------------------------ masonry
    xs, ys, zs = idx = sel('basalt', 'basalt_dk', 'stair')
    if len(xs):
        g = np.array(BASALT, float) * (0.9 + 0.18 * F['lo'][xs, ys])[:, None]
        course = ((zs % 3) == 0) & ~up[xs, ys, zs]
        g[course] *= 0.95                                                        # courses, low contrast
        streak = np.clip((F['streak'][xs, ys] - 0.55) / 0.2, 0, 1) * np.clip((zs - 40) / 20, 0, 1)
        g *= (1 - 0.10 * streak)[:, None]                                        # rain streaks, darker low down
        lich = np.clip((F['lichen'][xs, ys + zs] - 0.62) / 0.14, 0, 1)
        g = _mix(g, (122, 128, 100), lich * 0.4)
        moss = np.clip((zs - (cv.H[xs, ys] - 4)) / 4, 0, 1)
        g = _mix(g, (84, 100, 72), moss * 0.35)                                  # damp foot of the walls
        dk = cv.mat[xs, ys, zs] == cv.materials.get('basalt_dk', -1)
        g[dk & up[xs, ys, zs]] = _mix(g[dk & up[xs, ys, zs]], (138, 138, 142), 0.6)   # pale parapet coping
        st = cv.mat[xs, ys, zs] == cv.materials.get('stair', -1)
        g[st] = _mix(g[st], (140, 132, 122), 0.5)                                # worn steps, warmer
        put(idx, g, 'basalt')

    xs, ys, zs = idx = sel('plaster')
    if len(xs):
        g = np.array(PLASTER, float) * (0.95 + 0.07 * F['mid'][xs, ys])[:, None]
        g = _mix(g, (150, 146, 134), np.clip((F['streak'][xs, ys] - 0.6) / 0.25, 0, 1) * 0.35)  # weathering
        g[~up[xs, ys, zs]] *= 0.95
        put(idx, g, 'plaster')

    xs, ys, zs = idx = sel('kerb')
    if len(xs):
        g = np.array(LATERITE, float) * (0.9 + 0.16 * noise.hash3(xs // 2, ys // 3, zs // 2, 3))[:, None]
        g = _mix(g, (120, 116, 92), np.clip((F['lichen'][xs, ys] - 0.65) / 0.15, 0, 1) * 0.3)
        put(idx, g, 'kerb')

    simple = {
        'timber': ((126, 96, 64), 0.10), 'floor': ((144, 112, 80), 0.08), 'furniture': ((108, 82, 56), 0.06),
        'thatch': ((178, 152, 98), 0.12), 'rope': ((168, 148, 104), 0.06), 'net': ((108, 126, 116), 0.06),
        'crate': ((152, 120, 80), 0.10), 'keg': ((114, 86, 58), 0.08), 'iron': ((170, 134, 62), 0.08),
        'hull': ((104, 80, 54), 0.08), 'deck': ((150, 120, 84), 0.08), 'mast': ((118, 90, 60), 0.06),
        'sail': ((198, 188, 162), 0.05), 'finial': ((178, 142, 68), 0.04), 'flag_teal': ((70, 136, 126), 0.04),
        'pool': ((98, 150, 140), 0.05), 'fig': ((122, 88, 70), 0.06), 'nest': ((118, 94, 66), 0.08),
        'deadwood': ((126, 112, 96), 0.06), 'ribbon': ((222, 148, 52), 0.05), 'coconut': ((104, 96, 50), 0.06),
        'moss': ((84, 108, 60), 0.08), 'root': ((128, 114, 98), 0.06), 'dryfrond': ((156, 130, 78), 0.06),
        'palm_ring': ((112, 94, 70), 0.04), 'frond_young': ((150, 170, 86), 0.04),
        'bark': ((96, 80, 60), 0.08), 'palm_trunk': ((140, 118, 88), 0.06), 'shrub': ((76, 114, 62), 0.10),
    }
    for name, (c, amp) in simple.items():
        xs, ys, zs = idx = sel(name)
        if len(xs):
            g = np.array(c, float) * (1 - amp / 2 + amp * F['fine'][xs, ys + zs])[:, None]
            if name in ('hull', 'deck', 'crate'):                                 # planks: 2-high strakes
                g[(zs // 2) % 2 == 0] *= 0.96
            put(idx, g, name)
    # cloth: flags saffron (high up), cart sacks undyed
    xs, ys, zs = idx = sel('cloth')
    if len(xs):
        g = np.where((zs < 45)[:, None], np.array((222, 146, 50), float), np.array((190, 178, 146), float))
        put(idx, g * (0.96 + 0.06 * F['fine'][xs, ys])[:, None], 'cloth')

    # ------------------------------------------------------------------ vegetation: per-plant hues, gradients
    vrng = np.random.default_rng(veg_seed + 7)
    plants = []
    for p in rep['vegetation']['banyan'] + rep['vegetation']['palm']:
        for (x, y) in ((p['x'], p['y']), _rot(p['x'], p['y'])):
            plants.append(dict(p, x=x, y=y))
    pid = -np.ones((512, 512), int)
    best = np.full((512, 512), 1e9)
    leaf_fam = [(54, 96, 52), (64, 104, 54), (72, 112, 58), (60, 104, 70), (80, 114, 56)]
    frond_fam = [(92, 138, 62), (104, 146, 66), (116, 150, 70), (98, 140, 76)]
    for k, p in enumerate(plants):
        R = p.get('R', 7) + 4
        x0, x1, y0, y1 = int(p['x'] - R), int(p['x'] + R) + 1, int(p['y'] - R), int(p['y'] + R) + 1
        X, Y = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1), indexing='ij')
        dd = np.hypot(X - p['x'], Y - p['y'])
        b = best[x0:x1 + 1, y0:y1 + 1]
        m = (dd <= R) & (dd < b)
        b[m] = dd[m]
        pid[x0:x1 + 1, y0:y1 + 1][m] = k
        fam = leaf_fam if p['species'] == 'banyan' else frond_fam
        i = int(vrng.integers(len(fam)))
        p['c0'] = np.array(fam[i], float) * vrng.uniform(0.94, 1.06, 3)
        p['c1'] = np.array(fam[(i + 1) % len(fam)], float)
    for name in ('leaf', 'frond'):
        xs, ys, zs = idx = sel(name)
        if not len(xs):
            continue
        k = pid[xs, ys]
        c0 = np.array([plants[j]['c0'] if j >= 0 else (80, 120, 60) for j in k])
        c1 = np.array([plants[j]['c1'] if j >= 0 else (90, 128, 64) for j in k])
        if name == 'leaf':                       # canopy: lighter, yellower on top, cooler underside
            zb = np.array([plants[j].get('zb', z) if j >= 0 else z for j, z in zip(k, zs)])
            t = np.clip((zb - zs) / 4.0, 0, 1)
        else:                                    # fronds: tips lighter
            px = np.array([plants[j]['x'] if j >= 0 else x for j, x in zip(k, xs)])
            py = np.array([plants[j]['y'] if j >= 0 else y for j, y in zip(k, ys)])
            t = np.clip(np.hypot(xs - px, ys - py) / 6.0, 0, 1)
        blend = np.clip(F['mid'][xs, ys] * 1.6 - 0.3, 0, 1)
        base = _mix(c0, c1, blend)
        g = _mix(base * 0.80, base * 1.16 + np.array((6, 6, -4)), t)
        put(idx, g, name)

    # ------------------------------------------------------------------ painted sea (z 63)
    sea_id = cv.materials.get('sea')
    sx, sy = np.nonzero(water)
    sz = np.full(len(sx), 63)
    d = dland[sx, sy]
    g = color.ramp(SEA_STOPS, d)
    wave = 0.5 + 0.5 * np.sin(2 * math.pi * d / 9.0 + 6 * F['wave'][sx, sy])
    g *= (1 + 0.035 * (wave - 0.5) * np.clip((30 - d) / 30, 0, 1))[:, None]
    # current lines through the channels and the mid channel (long soft streaks along x)
    yy = np.where(sx <= 256, sy, 512 - sy).astype(float)
    xx = np.where(sx <= 256, sx, 512 - sx).astype(float)
    chan = ((xx >= 150) & (np.abs(yy - 231) <= 6)) | ((xx >= 150) & (np.abs(yy - 281) <= 6)) | \
        ((np.abs(xx - 256) <= 10) & (np.abs(yy - 256) <= 80))
    cur = 0.5 + 0.5 * np.sin(yy * 1.3 + 3 * F['lo'][sx, sy])
    g *= (1 + 0.04 * chan * (cur - 0.5) * 2)[:, None]
    # sandbar ghosts in the shallows, reef patches further out (soft edges)
    ghost = np.clip((F['bar'][sx, sy] - 0.6) / 0.12, 0, 1) * np.clip((26 - d) / 10, 0, 1) * (d > 3)
    g = _mix(g, (170, 182, 146), 0.28 * ghost)
    reef = np.clip((F['reef'][sx, sy] - 0.64) / 0.1, 0, 1) * np.clip((d - 8) / 6, 0, 1) * np.clip((48 - d) / 8, 0, 1)
    g = _mix(g, (60, 92, 84), 0.32 * reef)
    # foam at the shore: a broken band, coherent clusters (no speckle)
    foam = (d <= 2.2) * np.clip((F['foam'][sx, sy] - 0.45) / 0.15, 0, 1)
    g = _mix(g, (196, 214, 200), 0.45 * foam)
    # tide rose on the open sea, south-east quadrant, clear of the dhow
    rx_, ry_, rr = S['tide_rose']
    u, v = sx - rx_, sy - ry_
    rho, th = np.hypot(u, v), np.arctan2(v, u)
    light, dark = np.array((204, 198, 172), float), np.array((40, 76, 88), float)
    ring = ((rho >= rr - 2) & (rho <= rr)) | ((rho >= rr * 0.7) & (rho <= rr * 0.7 + 1))
    star_l = np.zeros(len(sx), bool)
    star_d = np.zeros(len(sx), bool)
    for kk in range(8):
        L = rr - 1 if kk % 2 == 0 else rr * 0.6
        bw = 4.5 if kk % 2 == 0 else 3.0
        a = kk * math.pi / 4 - math.pi / 2
        pu = rho * np.cos(th - a)
        pv = rho * np.sin(th - a)
        inside = (pu >= 0) & (np.abs(pv) <= bw * (1 - pu / L))
        star_l |= inside & (pv >= 0)
        star_d |= inside & (pv < 0)
    near = rho <= rr + 1
    g[near & ring] = _mix(g[near & ring], light, 0.75)
    g[star_d] = _mix(g[star_d], dark, 0.8)
    g[star_l] = _mix(g[star_l], light, 0.8)
    g[rho <= 1.6] = light
    cv.rgb[sx, sy, sz] = np.clip(np.rint(g), 0, 255).astype(np.uint8)
    rep_out['materials_painted']['sea'] = int(len(sx))

    # ------------------------------------------------------------------ details by paint: slits, door frames, eye
    # arrow-slit / window shadows: wall voxels next to a carved opening in a wall get darker
    wall_ids = [cv.materials[n] for n in ('basalt', 'kerb', 'timber') if n in cv.materials]
    wm = surf & np.isin(cv.mat, wall_ids) & ~up
    wx, wy, wz = np.nonzero(wm)
    side_air = np.zeros(len(wx), int)
    for dx_, dy_ in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        side_air += ~solid[np.clip(wx + dx_, 0, 511), np.clip(wy + dy_, 0, 511), wz]
    # a voxel with air on two opposite sides is a jamb of a slit or doorway: frame it
    jamb = (~solid[np.clip(wx + 1, 0, 511), wy, wz] & ~solid[np.clip(wx - 1, 0, 511), wy, wz]) | \
           (~solid[wx, np.clip(wy + 1, 0, 511), wz] & ~solid[wx, np.clip(wy - 1, 0, 511), wz])
    cv.rgb[wx[jamb], wy[jamb], wz[jamb]] = np.clip(cv.rgb[wx[jamb], wy[jamb], wz[jamb]] * 0.82, 0, 255)
    # painted eye on the dhow's prow (both sides)
    dh = rep['dhow_geom']
    for side in (-1, 1):
        ex, ey = dh['x1'] - 4, dh['yc'] + side * dh['w_bow']
        for (ox, oz, c) in ((0, 0, (40, 44, 46)), (1, 0, (196, 192, 176)), (-1, 0, (196, 192, 176)),
                            (0, -1, (196, 192, 176)), (0, 1, (196, 192, 176))):
            X, Z = ex + ox, dh['eye_z'] + oz
            for k in range(0, 3):
                Y = ey + side * k
                if 0 <= Y < 512 and solid[X, Y, Z] and surf[X, Y, Z]:
                    cv.rgb[X, Y, Z] = c
                    break

    # ------------------------------------------------------------------ lamps (existing voxels -> glow sources)
    lamps = []
    def lamp(x, y, z):
        if 0 <= x < 512 and 0 <= y < 512 and solid[x, y, z]:
            lamps.append((int(x), int(y), int(z)))
    fort = rep['fort']
    for t in fort['corner_bastions'] + fort['gate_bastions']:
        (cx, cy), r = t['centre'], t['r']
        deg, G = t['doors']['ground']
        a = math.radians(deg)
        x, y = int(math.floor(cx + 0.5 + (r - 0.5) * math.cos(a))), int(math.floor(cy + 0.5 + (r - 0.5) * math.sin(a)))
        for (X, Y) in ((x, y), _rot(x, y)):
            lamp(X, Y, G - 5)
    wz = S['wall']['walk_z']
    for y in S['lamps']['brazier_y']:
        for (X, Y) in ((S['wall']['x'][0], y), _rot(S['wall']['x'][0], y)):
            lamp(X, Y, wz - 2)
    sh = rep['shrine']
    cx = (sh['box'][0] + sh['box'][1]) // 2
    for (X, Y) in ((cx, sh['box'][3]), _rot(cx, sh['box'][3])):
        lamp(X, Y, sh['G'] - 4)
    b = S['baoli']
    (bx, by), hb = b['c'], b['half']
    for (X, Y) in ((bx - hb, by - hb), (bx + hb, by - hb), (bx - hb, by + hb), (bx + hb, by + hb)):
        lamp(X, Y, b['top'] - 1)
    lamp(dh['x1'], dh['yc'], dh['stern_z'])
    for (x, y, z) in lamps:
        cv.rgb[x, y, z] = LAMP
        cv.glow.append((x, y, z, LAMP))
        cv.nolight[x, y, z] = True
    rep_out['lamps'] = lamps

    # ------------------------------------------------------------------ light, glow, brightness, tag
    color.lighting(cv, side_f=0.86)
    stored, nsrc = color.bake_glow(cv, surf, radius=6.5, strength=0.32)
    rep_out['brightness'] = color.enforce_brightness(cv)
    nudged = 0
    src = {(x, y, z) for (x, y, z) in lamps}
    pal = np.array(sorted(GLOW_PALETTE))
    sxs, sys_, szs = np.nonzero(surf)
    rgb = cv.rgb[sxs, sys_, szs].astype(int)
    hit = (rgb[:, None, :] == pal[None, :, :]).all(-1).any(-1)
    for i in np.nonzero(hit)[0]:
        k = (int(sxs[i]), int(sys_[i]), int(szs[i]))
        if k not in src:
            cv.rgb[k][1] = max(0, int(cv.rgb[k][1]) - 1)
            nudged += 1
    for k in src:                       # the glow-aware server redoes the bake from the stored (unlit) colours
        cv.rgb[k] = LAMP
    rep_out['glow'] = {'sources': nsrc, 'stored_entries': len(stored), 'nudged_off_palette': nudged}
    T = S['tag']
    rect = tag.paint_tag(cv, T['text'], corner=T['corner'], margin=T['margin'], scale=T['scale'], rgb=T['rgb'],
                         shadow=T['shadow'], level=False)
    rep_out['tag_rect'] = list(rect)
    after = hashlib.sha256(np.packbits(cv.solid).tobytes()).hexdigest()
    assert before == after, 'art pass changed solid geometry'
    rep_out['solid_unchanged'] = {'asserted': True, 'sha256_before': before, 'sha256_after': after}
    return stored, rep_out
