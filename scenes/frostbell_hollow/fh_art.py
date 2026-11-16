"""Frostbell Hollow art pass (separate from the graybox; must not change gameplay geometry, see
fh_checks.collision_diff for the definition and the allowances).

    art_west(cv, rep, S, rng, seed)   west half + axis halves, BEFORE the mirror: terrain shaders, building styles,
                                      props, real trees (fh_veg), the giant spruce, glow sources (mirrored with it)
    art_post(cv, rep, S, rng)         AFTER the mirror + graybox train: train dressing, per-side unique pad one-offs
                                      (fh_props), east-side colour variants, sky decor (fh_sky), corner tag
    finish(cv)                        baked light + AO, twilight grade, glow bake, brightness rules, palette nudge

Geometry the art adds is limited to: trees on the stand-in columns, roof-top chimneys/snow and trim at least 4 above
the ground next to structures, props on the reserved feature pads, sky decor and the tag strip. Everything else is a
recolour (including lit window panes, string-light bulbs, lantern heads, candles and mine lamps).
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage as ndi

from aosmap.kit import color, noise, tag
from aosmap.kit.color import clamp8, mix, shade
from aosmap.kit.symmetry import mirror_index

import fh_props
import fh_sky
import fh_veg
from fh_spec import SPEC

WARM, YELLOW, WHITE, CYAN, GREEN = (255, 175, 95), (255, 255, 95), (255, 255, 255), (95, 255, 255), (95, 255, 95)
GLOW_PALETTE = {WARM, YELLOW, WHITE, CYAN, GREEN, (255, 95, 95)}

SNOW_HI, SNOW_MID, SNOW_LO = (198, 202, 210), (182, 188, 202), (152, 162, 184)
SLUSH = (146, 136, 126)
COBBLE = [(166, 156, 144), (178, 166, 150), (158, 150, 142), (184, 170, 152), (170, 160, 150)]
SLATE = [(96, 98, 110), (108, 106, 114), (88, 90, 102), (118, 114, 116), (100, 96, 104)]
PLASTER = [(206, 192, 160), (196, 170, 120), (200, 168, 140), (176, 180, 150), (196, 196, 196), (204, 186, 150)]
TIMBER = [(92, 64, 44), (104, 72, 50), (84, 60, 44), (110, 78, 54)]
SHINGLE = [(112, 62, 54), (88, 92, 104), (96, 70, 60), (120, 74, 58), (82, 84, 98)]
SHUTTER = [(64, 100, 72), (120, 52, 46), (76, 92, 120), (150, 120, 60)]
STONE = (148, 144, 138)


def _ids(cv, *names):
    return [cv.materials[n] for n in names if n in cv.materials]


def _isin(cv, arr, *names):
    ids = _ids(cv, *names)
    return np.isin(arr, ids) if ids else np.zeros(arr.shape, bool)


def _paint(cv, m, c):
    cv.rgb[m] = c


# =============================================================================================== terrain

def terrain_art(cv, S, seed):
    """Recolour every terrain voxel (z >= H) by its region material, slope, height and coherent noise."""
    H = cv.H.astype(int)
    X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    n1 = noise.fbm2((512, 512), 18, 3, 'art_snow', seed)
    n2 = noise.fbm2((512, 512), 6, 2, 'art_fine', seed)
    gx = np.abs(np.roll(H, 1, 0) - np.roll(H, -1, 0))
    gy = np.abs(np.roll(H, 1, 1) - np.roll(H, -1, 1))
    slope = np.maximum(gx, gy) / 2.0
    zz = np.arange(64)[None, None, :]
    ter = (zz >= H[:, :, None]) & cv.solid
    depth = zz - H[:, :, None]
    topmat = cv.mat[X, Y, H]
    is_ = {k: (topmat == cv.materials[k]) if k in cv.materials else np.zeros((512, 512), bool)
           for k in ('ground', 'cobble', 'rock', 'ice', 'water', 'ballast', 'gravel')}
    cob = is_['cobble']
    dist_cob = ndi.distance_transform_edt(~cob)
    dist_snow = ndi.distance_transform_edt(cob)

    # ---- snow top (2D colour field), then applied to depth 0 / 1
    t = np.clip(0.55 + (n1 - 0.5) * 1.3 + (50 - H) * 0.06 - slope * 0.25, 0, 1)
    snow = (np.array(SNOW_LO)[None, None] * (1 - t[..., None]) + np.array(SNOW_HI)[None, None] * t[..., None])
    tr = np.clip(1 - dist_cob / 4.0, 0, 1) * (0.55 + 0.3 * n2)                  # trodden slush along paved edges
    snow = snow * (1 - tr[..., None]) + np.array(SLUSH)[None, None] * tr[..., None]
    # ---- cobble pattern: staggered 3x2 setts, worn darker centre on lanes, snow in joints near the edge
    sx = (X + (Y // 2 % 2) * 1) // 3
    sy = Y // 2
    hsh = noise.hash3(sx, sy, 0, 11)
    cobc = np.array(COBBLE)[(hsh * len(COBBLE)).astype(int) % len(COBBLE)].astype(float)
    joint = ((X + (Y // 2 % 2)) % 3 == 0) | (Y % 2 == 0)
    cobc = np.where(joint[..., None], cobc * 0.93, cobc)
    edge_snow = np.clip(1 - dist_snow / 3.0, 0, 1) * joint * 0.6
    cobc = cobc * (1 - edge_snow[..., None]) + np.array(SNOW_MID)[None, None] * edge_snow[..., None]
    worn = (dist_snow > 3) & (n1 > 0.55)
    cobc = np.where(worn[..., None], cobc * np.array([0.96, 0.94, 0.92]), cobc)
    # ---- water / ice / gravel
    deep = np.clip(ndi.distance_transform_edt(is_['water']) / 5.0, 0, 1)
    water = np.array((86, 126, 146))[None, None] * (1 - deep[..., None]) + np.array((44, 76, 108))[None, None] * \
        deep[..., None]
    di = ndi.distance_transform_edt(~is_['water'])
    ti = np.clip((di - 1) / 3.0, 0, 1)
    ice = np.array((140, 184, 202))[None, None] * (1 - ti[..., None]) + np.array((184, 202, 212))[None, None] * \
        ti[..., None]
    gravel = np.array((134, 126, 112))[None, None] * (0.92 + 0.12 * n2[..., None])
    ballast = np.array((98, 90, 86))[None, None] * (0.94 + 0.1 * n2[..., None])
    sleeper = is_['ballast'] & (X % 3 == 0) & (Y >= 81) & (Y <= 87)
    ballast = np.where(sleeper[..., None], np.array((108, 84, 64)), ballast)
    # ---- rock (ring, spur, outcrops below the surface): warped strata, snow caps on gentle tops
    warp = (noise.fbm2((512, 512), 24, 2, 'strata', seed) - 0.5) * 8

    tops2d = np.zeros((512, 512, 3))
    tops2d[:] = snow
    for k, arr in (('cobble', cobc), ('water', water), ('ice', ice), ('gravel', gravel), ('ballast', ballast)):
        tops2d[is_[k]] = arr[is_[k]]
    rock_top = is_['rock']
    cap = rock_top & (slope <= 1.1)
    rk_c = np.array(SLATE)[((H + warp).astype(int) // 3) % len(SLATE)].astype(float)
    tops2d[rock_top & ~cap] = rk_c[rock_top & ~cap]
    capc = snow * 0.92
    tops2d[cap] = capc[cap]
    # rink (ice material above the terrain floor): handled with props; pads: light snow
    xs, ys, zs = np.nonzero(ter)
    d = depth[xs, ys, zs]
    out = cv.rgb[xs, ys, zs].astype(float)
    top0 = d == 0
    out[top0] = tops2d[xs[top0], ys[top0]]
    # depth 1-2: snow edge on snow regions, strata rock below / on rocky columns, earth elsewhere
    sub = ~top0
    strata = np.array(SLATE)[((zs + warp[xs, ys]).astype(int) // 3) % len(SLATE)].astype(float)
    earth = np.array((112, 96, 80)) * (0.92 + 0.1 * n2[xs, ys])[:, None]
    snowy_col = is_['ground'][xs, ys] & (d <= 1)
    out[sub] = np.where((H[xs, ys][sub] <= 46)[:, None] | (d[sub] > 3)[:, None], strata[sub], earth[sub])
    sm = sub & snowy_col
    out[sm] = snow[xs[sm], ys[sm]] * 0.9
    cv.rgb[xs, ys, zs] = np.clip(out, 0, 255).astype(np.uint8)
    # outcrops (rock above the terrain): strata with snow on open tops; feature pads: clean snow
    rid = cv.materials.get('rock')
    oc = cv.solid & (cv.mat == rid) & (zz < H[:, :, None])
    ox, oy, oz = np.nonzero(oc)
    oc_c = np.array(SLATE)[((oz + warp[ox, oy]).astype(int) // 2) % len(SLATE)].astype(float)
    open_ = ~cv.solid[ox, oy, np.maximum(oz - 1, 0)]
    oc_c[open_] = np.array(SNOW_MID) * 0.94
    cv.rgb[ox, oy, oz] = oc_c.astype(np.uint8)
    pid = cv.materials.get('pad')
    if pid is not None:
        pm = cv.mat == pid
        cv.rgb[pm] = (198, 202, 210)
    # mine floors and tunnel walls (carved surfaces): planks + rock
    mid = cv.materials.get('mine')
    if mid is not None:
        m = cv.mat == mid
        mx, my, mz = np.nonzero(m)
        pl = ((mx + my) // 2) % 2
        cv.rgb[mx, my, mz] = np.where(pl[:, None] == 0, np.array((118, 94, 70)), np.array((104, 82, 62)))
    return {'snow_cols': int(is_['ground'].sum()), 'rock_cols': int(rock_top.sum()), 'cobble_cols': int(cob.sum())}


# =============================================================================================== buildings

def _windows_on_plane(plane_air, plane_solid):
    lab, n = ndi.label(plane_air)
    return lab, n


def style_building(cv, box, g, n, sh, rng, glow, style, lit=0.3, ridge='x', eave_lights=True, chimney=True,
                   wreath=True):
    """Timber frame + stone plinth + plaster infill, painted window frames and shutters, some lit panes (amber glass,
    one warm glow voxel), snow-loaded shingle roof with gingerbread barge trim, chimney, eave string lights, wreath."""
    x0, x1, y0, y1 = box
    top = g - n * sh
    plaster = style.get('plaster', PLASTER[0])
    timber = style.get('timber', TIMBER[0])
    shingle = style.get('shingle', SHINGLE[0])
    shutter = style.get('shutter', SHUTTER[0])
    bid = _ids(cv, 'building', 'roof', 'timber')
    zlo = max(0, top - 12)
    sl = (slice(x0, x1 + 1), slice(y0, y1 + 1), slice(zlo, g + 1))
    solid = cv.solid[sl]
    mat = cv.mat[sl]
    mb = solid & np.isin(mat, bid)
    xs, ys, zs = np.nonzero(mb)
    X, Yv, Z = xs + x0, ys + y0, zs + zlo
    per = (X == x0) | (X == x1) | (Yv == y0) | (Yv == y1)
    along = np.where((X == x0) | (X == x1), Yv - y0, X - x0)
    col = np.empty((len(X), 3))
    # walls
    wall = per & (Z > top) & (Z <= g)
    k = (g - Z)
    beam = (k % sh == 0) | (Z == top + 1)
    post = (along % 4 == 0) | (X == x0) & (Yv == y0) | (X == x1) & (Yv == y1) | (X == x0) & (Yv == y1) | \
        (X == x1) & (Yv == y0)
    brace = ((along % 4) == ((k % sh) % 4)) & (k % sh != 0) & (k >= sh)
    plinth = Z >= g - 1
    wc = np.array(plaster) * (0.97 + 0.05 * noise.hash3(X, Yv, Z, 3))[:, None]
    wc = np.where((post | beam | brace)[:, None], np.array(timber), wc)
    wc = np.where(plinth[:, None], np.array(STONE) * (0.9 + 0.12 * noise.hash3(X // 2, Yv // 2, Z, 5))[:, None], wc)
    col[:] = wc
    # floors inside: planks
    fl = ~per & (Z > top)
    pl = (np.where((x1 - x0) > (y1 - y0), Yv, X) // 2) % 2
    col[fl] = np.where(pl[fl][:, None] == 0, np.array((132, 100, 70)), np.array((118, 88, 62)))
    # roof slab + gable: shingle courses, snow on exposed tops (not on the eave ring), barge trim on the gable ends
    rf = Z <= top
    course = ((top - Z) % 2 == 0)
    rc = np.where(course[:, None], np.array(shingle), np.array(shade(shingle, 0.88)))
    air_above = ~cv.solid[X, Yv, np.maximum(Z - 1, 0)]
    eave = (X == x0) | (X == x1) if ridge == 'y' else (Yv == y0) | (Yv == y1)
    snowc = np.array(SNOW_MID) * (0.95 + 0.06 * noise.hash3(X, Yv, Z, 9))[:, None]
    rc = np.where((air_above & ~eave)[:, None], snowc, rc)
    endf = ((X == x0) | (X == x1)) if ridge == 'x' else ((Yv == y0) | (Yv == y1))
    gable_end = rf & endf & (Z < top)
    trim = ((along // 2) % 2 == 0)
    rc = np.where((gable_end & trim)[:, None], np.array((206, 190, 160)), rc)
    rc = np.where((gable_end & ~trim)[:, None], np.array((150, 56, 48)), rc)
    col[rf] = rc[rf]
    cv.rgb[X, Yv, Z] = np.clip(col, 0, 255).astype(np.uint8)
    # windows on each wall plane: frames, shutters, some lit panes
    planes = [('x', x0), ('x', x1), ('y', y0), ('y', y1)]
    n_lit = 0
    for ax, v in planes:
        if ax == 'x':
            air = ~cv.solid[v, y0:y1 + 1, top + 1:g]
        else:
            air = ~cv.solid[x0:x1 + 1, v, top + 1:g]
        lab, nn = ndi.label(air)
        for i in range(1, nn + 1):
            cs = np.argwhere(lab == i)
            if cs[:, 1].max() + top + 1 >= g - 1:          # reaches the floor: a door
                u0, u1 = cs[:, 0].min(), cs[:, 0].max()
                dz0 = cs[:, 1].min() + top + 1
                for u in range(u0 - 1, u1 + 2):
                    for z in (dz0 - 1,):
                        pt = (v, y0 + u, z) if ax == 'x' else (x0 + u, v, z)
                        if cv.get(*pt):
                            cv.rgb[pt] = shade(timber, 1.15)
                if wreath and u0 - 3 >= 0:
                    wu = u0 - 3
                    for (du, dz) in ((0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, -1), (-1, 1), (1, 1)):
                        zc = g - 3
                        pt = (v, y0 + wu + du, zc + dz) if ax == 'x' else (x0 + wu + du, v, zc + dz)
                        if 0 <= wu + du <= (y1 - y0 if ax == 'x' else x1 - x0) and cv.get(*pt):
                            cv.rgb[pt] = (52, 98, 60) if (du + dz) % 2 else (40, 84, 52)
                    pt = (v, y0 + wu, g - 2) if ax == 'x' else (x0 + wu, v, g - 2)
                    if cv.get(*pt):
                        cv.rgb[pt] = (170, 40, 44)
                continue
            u0, u1 = cs[:, 0].min(), cs[:, 0].max()
            za, zb = cs[:, 1].min() + top + 1, cs[:, 1].max() + top + 1
            for u in range(u0 - 1, u1 + 2):
                for z in range(za - 1, zb + 2):
                    if u0 <= u <= u1 and za <= z <= zb:
                        continue
                    pt = (v, y0 + u, z) if ax == 'x' else (x0 + u, v, z)
                    if not cv.get(*pt):
                        continue
                    if (u == u0 - 1 or u == u1 + 1) and za <= z <= zb:
                        cv.rgb[pt] = shutter
                    else:
                        cv.rgb[pt] = (214, 206, 186) if style.get('painted_frames', True) else shade(timber, 1.2)
            if rng.random() < lit:
                for (u, zl) in cs:
                    pt = (v, y0 + u, zl + top + 1) if ax == 'x' else (x0 + u, v, zl + top + 1)
                    cv.set(*pt, (212, 160, 96), 'glass')
                u, zl = cs[len(cs) // 2]
                pt = (v, y0 + u, zl + top + 1) if ax == 'x' else (x0 + u, v, zl + top + 1)
                glow.append(pt + (WARM,))
                n_lit += 1
    # eave string lights: spaced bulbs on the roof slab edge (every 4th voxel)
    if eave_lights:
        if ridge == 'x':
            pts = [(x, yy, top) for yy in (y0, y1) for x in range(x0 + 2, x1 - 1, 6)]
        else:
            pts = [(xx, y, top) for xx in (x0, x1) for y in range(y0 + 2, y1 - 1, 6)]
        for i, p in enumerate(pts):
            if cv.get(*p) and p[0] <= 255:
                glow.append(p + ((WHITE if i % 5 == 2 else (YELLOW if i % 3 == 1 else WARM)),))
    # chimney: 2x2 stone stack at a gable end, up to 3 above the local roof surface (never above z 7)
    if chimney:
        if ridge == 'x':
            cx, cy = x0 + 2, (y0 + y1) // 2 - 1 + int(rng.integers(0, 2))
        else:
            cx, cy = (x0 + x1) // 2 - 1 + int(rng.integers(0, 2)), y0 + 2
        surf = min(cv.column_top(cx + a, cy + b) for a in (0, 1) for b in (0, 1))
        ztop = max(8, surf - 4)
        for a in (0, 1):
            for b in (0, 1):
                ct = cv.column_top(cx + a, cy + b)
                for z in range(ztop, ct):
                    cv.set(cx + a, cy + b, z, shade(STONE, 0.85 if z == ztop else 0.95), 'chimney')
    return n_lit


def building_list(S, rep):
    """(name, box, ground z, storeys, storey h, ridge, style key) for every enterable building in the west half."""
    g = S['z']['village']
    out = []
    for i, h in enumerate(S['houses']):
        for j, (box, n, sh, doors, ridge) in enumerate(h['parts']):
            out.append((h['name'] + ('' if j == 0 else ' wing'), box, g, n, sh, ridge, i))
    po = S['post_office']
    out.append(('post office', po['box'], g, 1, 6, 'x', 'po'))
    out.append(('post office wing', po['wing'], g, 1, 6, 'y', 'po'))
    # axis buildings use their full graybox box (the east part is overwritten by the mirror)
    out.append(('tavern', S['tavern']['box'], S['tavern']['floor'], 2, 5, None, 'tavern'))
    st = S['station']
    out.append(('station', st['box'], st['floor'], 1, 6, None, 'station'))
    out.append(('workshop', S['workshop']['box'], S['z']['valley'], 1, S['workshop']['storey_h'], None, 'workshop'))
    ml = rep['mill']
    out.append(('water mill', tuple(ml['box']), ml['floor'], 2, 5, 'x', 'mill'))
    return out


STYLES = {
    0: {'plaster': PLASTER[0], 'timber': TIMBER[0], 'shingle': SHINGLE[0], 'shutter': SHUTTER[0]},
    1: {'plaster': PLASTER[2], 'timber': TIMBER[1], 'shingle': SHINGLE[1], 'shutter': SHUTTER[2]},
    2: {'plaster': PLASTER[1], 'timber': TIMBER[2], 'shingle': SHINGLE[2], 'shutter': SHUTTER[0]},
    3: {'plaster': PLASTER[3], 'timber': TIMBER[3], 'shingle': SHINGLE[3], 'shutter': SHUTTER[1]},
    4: {'plaster': (150, 70, 56), 'timber': TIMBER[0], 'shingle': SHINGLE[4], 'shutter': SHUTTER[3]},
    5: {'plaster': PLASTER[5], 'timber': TIMBER[1], 'shingle': SHINGLE[1], 'shutter': SHUTTER[1]},
    6: {'plaster': PLASTER[4], 'timber': TIMBER[2], 'shingle': SHINGLE[0], 'shutter': SHUTTER[2]},
    7: {'plaster': PLASTER[1], 'timber': TIMBER[3], 'shingle': SHINGLE[2], 'shutter': SHUTTER[0]},
    'po': {'plaster': (200, 170, 92), 'timber': TIMBER[0], 'shingle': SHINGLE[4], 'shutter': (52, 84, 60)},
    'tavern': {'plaster': (204, 186, 150), 'timber': (76, 54, 40), 'shingle': SHINGLE[0], 'shutter': SHUTTER[1]},
    'station': {'plaster': (196, 192, 168), 'timber': (60, 92, 70), 'shingle': SHINGLE[3], 'shutter': (60, 92, 70)},
    'workshop': {'plaster': (152, 66, 52), 'timber': (196, 180, 150), 'shingle': SHINGLE[1], 'shutter': (196, 180, 150),
                 'painted_frames': False},
    'mill': {'plaster': (176, 170, 156), 'timber': TIMBER[2], 'shingle': SHINGLE[2], 'shutter': SHUTTER[0]},
}


def chapel_art(cv, S, rng, glow):
    ch = S['chapel']
    g = S['z']['village']
    bid = _ids(cv, 'building', 'roof')
    for (box, top) in ((ch['nave'], ch['nave_roof_z']), (ch['tower'], g - ch['tower_storeys'] * ch['tower_storey_h'])):
        x0, x1, y0, y1 = box
        sl = (slice(x0, x1 + 1), slice(y0, y1 + 1), slice(top - 10, g + 1))
        m = cv.solid[sl] & np.isin(cv.mat[sl], bid)
        xs, ys, zs = np.nonzero(m)
        X, Yv, Z = xs + x0, ys + y0, zs + top - 10
        course = ((Z // 2) + ((X + Yv) // 3) % 2) % 2
        c = np.where(course[:, None] == 0, np.array((182, 174, 160)), np.array((168, 160, 148)))
        c = c * (0.95 + 0.08 * noise.hash3(X // 2, Yv, Z, 21))[:, None]
        per = (X == x0) | (X == x1) | (Yv == y0) | (Yv == y1)
        c = np.where((~per & (Z > top))[:, None], np.array((122, 94, 70)), c)                  # floors
        roof = Z <= top
        aa = ~cv.solid[X, Yv, np.maximum(Z - 1, 0)]
        gend = roof & ((X == x0) | (X == x1)) & (Z < top)              # gable end faces stay stone
        c = np.where((roof & ~gend)[:, None], np.where(aa[:, None], np.array(SNOW_MID), np.array((116, 120, 134))), c)
        cv.rgb[X, Yv, Z] = np.clip(c, 0, 255).astype(np.uint8)
    # stained glass in the nave windows (coloured panes, a few glowing), altar candles, bell bronze
    x0, x1, y0, y1 = ch['nave']
    glass = [(150, 60, 56), (70, 100, 150), (200, 160, 80), (70, 120, 90)]
    for yy in (y0, y1):
        for x in range(x0 + 1, x1):
            for z in range(top_n := ch['nave_roof_z'] + 1, g - 1):
                if not cv.solid[x, yy, z]:
                    cv.set(x, yy, z, glass[(x + z) % 4], 'glass')
                    if (x + z) % 11 == 0:
                        glow.append((x, yy, z, WARM))
    cy = (y0 + y1) // 2
    for dy in (-2, 0, 2):
        z = cv.column_top(x0 + 2, cy + dy, 40)
        glow.append((x0 + 2, cy + dy, z, WARM if dy else YELLOW))
    tx0, tx1, ty0, ty1 = ch['tower']
    roof = g - ch['tower_storeys'] * ch['tower_storey_h']
    cv.rgb[tx0 + 4:tx0 + 7, (ty0 + ty1) // 2 - 1:(ty0 + ty1) // 2 + 2, roof + 1:roof + 3] = (176, 132, 66)
    # pews / furniture in warm wood
    fid = cv.materials.get('furniture')
    sl = (slice(x0, x1 + 1), slice(y0, y1 + 1), slice(30, g))
    m = cv.mat[sl] == fid
    cv.rgb[sl][m] = (110, 78, 54)


def v12_art(cv, S, rng, glow):
    """v1.2 zone pieces: the bandstand (sector-painted roof with a gold rim, brass posts, plank floor, eight lanterns),
    hearth courts (stone seat walls, snow caps, glowing braziers), trestle tables with a cloth runner, the fir tub,
    hay bales, the gate buttresses (red brick drums, cream caps, a lantern each). Recolour only."""
    V = S['v12']
    g = S['z']['valley']
    n = 0

    def vox(mname):
        mid = cv.materials.get(mname)
        if mid is None:
            return np.zeros(0, int), np.zeros(0, int), np.zeros(0, int)
        m = cv.mat == mid
        m[256:] = False
        return np.nonzero(m)

    # bandstand
    X, Y, Z = vox('gazebo')
    cx, cy = V['gazebo']['c']
    cy += 0.5
    th = np.arctan2(Y + 0.5 - cy, X + 0.5 - cx)
    r = np.hypot(X + 0.5 - cx, Y + 0.5 - cy)
    sect = ((th + np.pi) / (np.pi / 8)).astype(int) % 2
    c = np.empty((len(X), 3))
    rz = V['gazebo']['roof_z']
    roof = Z <= rz + 1
    aa = ~cv.solid[X, Y, np.maximum(Z - 1, 0)]
    c[:] = np.where(sect[:, None] == 0, np.array((150, 58, 50)), np.array((206, 190, 150)))
    c[roof & (r > V['gazebo']['r'] - 1.1)] = (196, 158, 80)                         # gold rim / valance
    c[roof & aa & (r < V['gazebo']['r'] - 1.5)] = SNOW_MID                          # snow on the roof
    floor = Z == g - 1
    c[floor] = np.where(((X + Y) % 2 == 0)[floor][:, None], np.array((132, 100, 70)), np.array((120, 90, 64)))
    post = ~roof & ~floor
    c[post] = (196, 160, 80)                                                        # brass posts
    cv.rgb[X, Y, Z] = np.clip(c, 0, 255).astype(np.uint8)
    for k in range(8):                                                               # lanterns on the valance
        a = (k + 0.5) * math.pi / 4
        px = int(math.floor(cx + (V['gazebo']['r'] - 0.6) * math.cos(a)))
        py = int(math.floor(cy + (V['gazebo']['r'] - 0.6) * math.sin(a)))
        if px <= 255 and cv.solid[px, py, rz + 1]:
            glow.append((px, py, rz + 1, WARM))
            n += 1
    # hearth courts + braziers
    X, Y, Z = vox('hearth')
    aa = ~cv.solid[X, Y, Z - 1]
    c = np.where((((X + Y + Z) % 3) == 0)[:, None], np.array((138, 132, 126)), np.array((156, 150, 142)))
    c = np.where(aa[:, None], np.array(SNOW_MID), c)
    cv.rgb[X, Y, Z] = c.astype(np.uint8)
    X, Y, Z = vox('brazier')
    cv.rgb[X, Y, Z] = (58, 54, 56)
    for (x, y, z) in zip(X, Y, Z):
        if not cv.solid[x, y, z - 1]:
            glow.append((int(x), int(y), int(z), WARM if (x + y) % 2 else YELLOW))
            n += 1
    # trestles: timber with a white cloth runner on the table tops
    X, Y, Z = vox('trestle')
    aa = ~cv.solid[X, Y, Z - 1]
    c = np.where(((X + Y) % 2 == 0)[:, None], np.array((120, 88, 62)), np.array((108, 78, 56)))
    tx0, tx1, ty0, ty1 = V['trestle']
    runner = aa & ((Y == ty0) | (Y == ty1)) & (X > tx0 + 1)
    c[runner] = (206, 198, 180)
    cv.rgb[X, Y, Z] = c.astype(np.uint8)
    # fir tub
    X, Y, Z = vox('planter')
    cv.rgb[X, Y, Z] = np.where(((X + Y) % 2 == 0)[:, None], np.array((150, 146, 140)), np.array((136, 132, 128)))
    X, Y, Z = vox('planter_fir')
    aa = ~cv.solid[X, Y, Z - 1]
    c = np.where((Z % 2 == 0)[:, None], np.array((44, 86, 58)), np.array((56, 100, 64)))
    c = np.where((aa & (noise.hash3(X, Y, Z, 41) < 0.5))[:, None], np.array(SNOW_MID), c)
    cv.rgb[X, Y, Z] = c.astype(np.uint8)
    if len(Z):
        k = int(np.argmin(Z))
        glow.append((int(X[k]), int(Y[k]), int(Z[k]), YELLOW))                    # star on the tub fir
        n += 1
    # hay bales
    X, Y, Z = vox('hay')
    aa = ~cv.solid[X, Y, Z - 1]
    c = np.array((196, 168, 96)) * (0.9 + 0.12 * noise.hash3(X, Y, Z, 7))[:, None]
    c[aa & (noise.hash3(X, Y, Z, 8) < 0.6)] = SNOW_MID
    cv.rgb[X, Y, Z] = np.clip(c, 0, 255).astype(np.uint8)
    # gate buttresses: red brick drums, cream hoops and cap, one lantern on the spawn-side face
    X, Y, Z = vox('buttress')
    c = np.where((((Y + (Z // 2) % 2 * 2) // 4) % 2 == 0)[:, None], np.array((156, 58, 50)), np.array((140, 50, 44)))
    c[Z % 3 == 0] = (204, 190, 160)
    aa = ~cv.solid[X, Y, Z - 1]
    c[aa] = SNOW_MID
    cv.rgb[X, Y, Z] = c.astype(np.uint8)
    for (p0, p1) in S['gatehouse']['arch']['piers']:
        y = (p0 + p1) // 2
        x = V['buttress_x'][0]
        if cv.solid[x, y, g - 3]:
            glow.append((x, y, g - 3, WARM))
            n += 1
    return {'glow_added': n}


def arch_art(cv, S, glow):
    """v1.1 arch: brick/drum banding on the piers, cream masonry lintel with gold trim, snow-capped merlons, a holly
    wreath with a gold bell over the middle passage (both faces), garland swags with warm bulbs, lanterns under each
    passage and on every pier, painted toy soldiers with a gold drum, holly hedges. Recolour only."""
    from fh_graybox import C
    gh = S['gatehouse']
    x0, x1 = gh['x']
    ar = gh['arch']
    a0, a1 = ar['y']
    g = gh['floor_z']
    bid = _ids(cv, 'building', 'roof')
    sl = (slice(x0, x1 + 1), slice(a0, a1 + 1), slice(20, g))
    xs, ys, zs = np.nonzero(cv.solid[sl] & np.isin(cv.mat[sl], bid))
    X, Yv, Z = xs + x0, ys + a0, zs + 20
    c = np.empty((len(X), 3))
    pier = Z >= 41
    bond = (((Yv + (Z // 2) % 2 * 2) // 4) % 2 == 0)
    c[:] = np.where(bond[:, None], np.array((206, 196, 172)), np.array((196, 186, 162)))       # cream masonry
    c[pier] = np.where(bond[pier][:, None], np.array((156, 58, 50)), np.array((140, 50, 44)))  # red brick drums
    c[pier & (Z % 3 == 0)] = (204, 190, 160)                                                     # cream drum hoops
    c[(Z == 40) | (Z == 29) | (Z == 34)] = (196, 158, 80)                                        # gold trim courses
    aa = ~cv.solid[X, Yv, np.maximum(Z - 1, 0)]
    top = (Z <= 28) | ((Z <= 27))
    c[top & aa] = SNOW_MID                                                                       # snow cap
    c[(Z <= 27) & ~aa] = (200, 190, 168)
    cv.rgb[X, Yv, Z] = np.clip(c, 0, 255).astype(np.uint8)
    # wreath with a gold bell over the middle passage, on both faces
    for xf in (x0, x1):
        for (dy, dz) in ((-2, 0), (2, 0), (0, -2), (0, 2), (-1, -2), (1, -2), (-1, 2), (1, 2), (-2, -1), (-2, 1),
                         (2, -1), (2, 1)):
            if cv.solid[xf, 256 + dy, 32 + dz]:
                cv.rgb[xf, 256 + dy, 32 + dz] = (46, 96, 58) if (dy + dz) % 2 else (60, 112, 66)
        cv.rgb[xf, 256, 32] = (204, 166, 84)
        cv.rgb[xf, 256, 31] = (204, 166, 84)
        cv.rgb[xf, 255, 35] = (168, 46, 48)                                                      # bow
        cv.rgb[xf, 256, 35] = (168, 46, 48)
        # garland swags along both faces between the piers (sagging curve z 37-39), warm bulbs on the low points
        for y in range(a0, a1 + 1):
            k = (y - a0) % 8
            z = 37 + (2 if 2 <= k <= 5 else (1 if k in (1, 6) else 0))
            if cv.solid[xf, y, z]:
                cv.rgb[xf, y, z] = (52, 104, 62)
                if k == 4:
                    glow.append((xf, y, z, WARM))
        # lanterns on every pier face (z 44)
        for (p0, p1) in ar['piers']:
            py = (p0 + p1) // 2
            glow.append((xf, py, 44, YELLOW if p1 - p0 < 3 else WARM))
    # lanterns under each passage (on the soffit, z 40, centre line)
    for (pa, pb) in ((244, 249), (253, 259), (263, 268)):
        glow.append((148, (pa + pb) // 2, 40, WARM))
    # toy soldiers: plinth stone, black trousers, red coat with white crossed belts, gold epaulettes and buttons,
    # face, black shako with a gold plate and a white plume, gold drum with a red band
    s0, s1 = ar['statue_y']
    sid = cv.materials.get('statue')
    for (s0, s1) in ((ar['statue_y'][0], ar['statue_y'][1]), (512 - ar['statue_y'][1], 512 - ar['statue_y'][0])):
        ya, yb = s0 - 1, s1 + 1
        for x in range(145, 153):
            for y in range(ya, yb + 1):
                for z in range(20, g):
                    if not cv.solid[x, y, z] or cv.mat[x, y, z] != sid:
                        continue
                    c0 = tuple(int(v) for v in cv.rgb[x, y, z])
                    if z >= g - 2:
                        col = (150, 146, 140)
                    elif c0 == (52, 50, 58):
                        col = (40, 38, 46) if z > g - 5 else (52, 50, 58)
                        if y in (s0, s1) and z <= g - 5:
                            col = (150, 46, 44)                                                 # trouser stripe
                    elif c0 == C['soldier']:
                        col = (168, 50, 44)
                        if y in (s0 - 1, s1 + 1) and z == g - 14:
                            col = (210, 170, 80)                                                # epaulettes
                        if x in (147, 150) and z - (g - 14) == abs(y - (s0 + s1) / 2.0) * 1.2 // 1:
                            col = (214, 210, 200)                                               # crossed belts
                        if x == 150 and y in (s0 + 1, s1 - 1) and z in (g - 12, g - 10):
                            col = (210, 170, 80)                                                # buttons
                    elif c0 == C['figure']:
                        col = (212, 174, 146)
                        if x == 149 and z == g - 16 and y in (s0 + 1, s1 - 1):
                            col = (46, 44, 50)
                    elif c0 == (48, 46, 54):
                        col = (40, 38, 46)
                        if x == 149 and z == g - 20:
                            col = (210, 170, 80)                                                # shako plate
                    elif c0 == (200, 196, 190):
                        col = (204, 200, 196)
                    elif c0 == (196, 160, 80):
                        col = (150, 46, 44) if z == g - 9 else (204, 166, 84)                  # drum + band
                    else:
                        col = c0
                    cv.rgb[x, y, z] = col
    hid = cv.materials.get('hedge')
    if hid is not None:
        m = cv.mat == hid
        xs, ys, zs = np.nonzero(m)
        top_ = ~cv.solid[xs, ys, zs - 1]
        cv.rgb[xs, ys, zs] = np.where(top_[:, None], np.array(SNOW_MID), np.array((44, 88, 56)))
        k = ((xs + ys + zs) % 5 == 0) & ~top_
        cv.rgb[xs[k], ys[k], zs[k]] = (170, 40, 44)


def gatehouse_art(cv, S, glow):
    gh = S['gatehouse']
    x0, x1 = gh['x']
    yA, yB = gh['y']
    s0 = gh['statue_y'][0]
    bid = _ids(cv, 'building', 'roof')
    xa = x0 if gh.get('variant', 'full') == 'full' else 143            # variant towers reach x 143
    sl = (slice(xa, x1 + 1), slice(yA, yB + 1), slice(20, 51))
    m = cv.solid[sl] & np.isin(cv.mat[sl], bid)
    xs, ys, zs = np.nonzero(m)
    X, Yv, Z = xs + xa, ys + yA, zs + 20
    c = np.empty((len(X), 3))
    c[:] = (204, 194, 170)                                                  # cream gallery
    pier = (Z >= gh['passage_air'][0]) & (Z <= 49)
    c[pier] = (150, 58, 50)                                                 # red towers / piers
    quoin = pier & ((Z % 3 == 0) & ((X == x0) | (X == x1)))
    c[quoin] = (200, 186, 160)
    band = (Z == gh['gallery_air'][0]) | (Z == gh['gallery_air'][1]) | (Z == gh['gallery_floor'])
    c[band & ~pier] = (196, 158, 80)                                        # gold bands
    roof = Z <= gh['roof'][1]
    aa = ~cv.solid[X, Yv, np.maximum(Z - 1, 0)]
    c[roof] = (84, 90, 110)
    c[roof & aa] = SNOW_MID
    c[roof & ((X == x0) | (X == x1)) & aa & (Yv % 4 < 2)] = (196, 158, 80)
    cv.rgb[X, Yv, Z] = np.clip(c, 0, 255).astype(np.uint8)
    # toy-soldier statues (north; the south one is the y-reflection): boots, trousers, red coat, white cross belts,
    # gold buttons, face, tall bearskin with a gold plate
    for ys0 in (s0, 512 - gh['statue_y'][1]):
        for x in range(x0 + 1, x1):
            for y in range(ys0, ys0 + 4):
                for z in range(26, 50):
                    if not cv.solid[x, y, z] or cv.mat[x, y, z] != cv.materials.get('prop'):
                        continue
                    if z >= 47:
                        c = (150, 146, 140)
                    elif z >= 44:
                        c = (40, 38, 44)
                    elif z >= 41:
                        c = (60, 58, 70)
                    elif z >= 36:
                        c = (168, 50, 44)
                        if (y - ys0) in (1, 2) and z in (38, 39):
                            c = (214, 210, 200)
                        if x == x1 - 1 and (y - ys0) in (1, 2) and z in (37, 40):
                            c = (210, 170, 80)
                    elif z >= 33:
                        c = (212, 174, 146)
                        if x == x1 - 2 and z == 34:
                            c = (46, 44, 50)
                    else:
                        c = (40, 38, 44)
                        if z == 31 and x == x1 - 2:
                            c = (210, 170, 80)
                    cv.rgb[x, y, z] = c
    # gallery lanterns over the passages (lit inside the gallery wall, facing the spawn side)
    for y in (236, 248, 264, 276):
        glow.append((x0, y, 32, WARM))


# =============================================================================================== props, market, axis

def props_art(cv, S, rng, glow):
    """Recolour graybox props by component and graybox colour; lantern heads, ice and furniture styles."""
    pid = _ids(cv, 'prop', 'furniture', 'ice', 'fence', 'letters', 'animal')
    zz = np.arange(64)[None, None, :]
    m = cv.solid & np.isin(cv.mat, pid) & (zz < cv.H[:, :, None])
    m[256:] = False
    lab, n = ndi.label(m, structure=ndi.generate_binary_structure(3, 1))
    objs = ndi.find_objects(lab)
    stats = {}
    wraps = [((168, 46, 48), (206, 182, 100)), ((52, 100, 70), (200, 196, 186)), ((60, 84, 130), (206, 182, 100)),
             ((196, 170, 100), (150, 40, 44)), ((120, 60, 120), (200, 196, 186)), ((196, 196, 200), (52, 100, 70))]
    for i, sl in enumerate(objs, start=1):
        if sl is None:
            continue
        sub = lab[sl] == i
        xs, ys, zs = np.nonzero(sub)
        X, Yv, Z = xs + sl[0].start, ys + sl[1].start, zs + sl[2].start
        cols = cv.rgb[X, Yv, Z]
        c0 = tuple(int(v) for v in np.median(cols, axis=0))
        mats = cv.mat[X, Yv, Z]
        w, d, h = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start, sl[2].stop - sl[2].start
        kind = 'other'
        if (cols == (210, 190, 120)).all(axis=1).any():
            kind = 'lantern'
        elif cv.materials.get('animal') in mats:
            kind = 'animal'
        elif cv.materials.get('ice') in mats:
            kind = 'ice'
        elif cv.materials.get('letters') in mats:
            kind = 'letters'
        elif c0 == (178, 126, 66) and h >= 2:
            kind = 'presents'
        elif c0 == (178, 126, 66):
            kind = 'sled'
        elif c0 == (98, 74, 54):
            kind = 'logs'
        elif c0 == (196, 170, 96):
            kind = 'hay'
        elif c0 == (102, 80, 58):
            kind = 'wood'
        elif c0 == (132, 98, 66):
            kind = 'timber'
        elif c0 == (168, 70, 64):
            kind = 'mailbox'
        if h >= 8:                                   # statues / poles: styled elsewhere
            continue
        stats[kind] = stats.get(kind, 0) + 1
        topz = Z.min()
        open_top = (Z == topz) & ~np.array([cv.solid[a_, b_, :c_].any() for a_, b_, c_ in zip(X, Yv, Z)])
        if kind == 'lantern':
            head = (cols == (210, 190, 120)).all(axis=1)
            cv.rgb[X, Yv, Z] = (52, 50, 54)
            for (x, y, z) in zip(X[head], Yv[head], Z[head]):
                glow.append((int(x), int(y), int(z), WARM))
        elif kind == 'presents':
            body, rib = wraps[int(rng.integers(len(wraps)))]
            body2, rib2 = wraps[int(rng.integers(len(wraps)))]
            cx, cy = X.min() + 1, Yv.min() + 1
            upper = Z < Z.max() - 1
            ribbon = (X == cx) | (Yv == cy)
            c = np.where(upper[:, None], np.array(body2), np.array(body))
            c = np.where(ribbon[:, None], np.where(upper[:, None], np.array(rib2), np.array(rib)), c)
            cv.rgb[X, Yv, Z] = c
        elif kind == 'sled':
            sc = [(168, 46, 48), (52, 100, 70), (60, 84, 130), (180, 140, 60)][int(rng.integers(4))]
            edge = (X == X.min()) | (X == X.max()) | (Yv == Yv.min()) | (Yv == Yv.max())
            cv.rgb[X, Yv, Z] = np.where(edge[:, None], np.array((196, 160, 80)), np.array(sc))
        elif kind == 'logs':
            ring = ((X + Yv + Z) % 2 == 0)
            cv.rgb[X, Yv, Z] = np.where(ring[:, None], np.array((132, 96, 64)), np.array((104, 74, 52)))
            cv.rgb[X[open_top], Yv[open_top], Z[open_top]] = SNOW_MID
        elif kind == 'hay':
            cv.rgb[X, Yv, Z] = np.array((196, 168, 96)) * (0.92 + 0.1 * noise.hash3(X, Yv, Z, 4))[:, None]
            cv.rgb[X[open_top], Yv[open_top], Z[open_top]] = (200, 196, 190)
        elif kind == 'wood':
            cv.rgb[X, Yv, Z] = np.where(((X + Yv) % 2 == 0)[:, None], np.array((116, 84, 58)), np.array((104, 76, 54)))
            cv.rgb[X[open_top], Yv[open_top], Z[open_top]] = (190, 194, 204)
        elif kind == 'timber':
            cv.rgb[X, Yv, Z] = (118, 86, 60)
            cv.rgb[X[open_top], Yv[open_top], Z[open_top]] = (188, 192, 202)
        elif kind == 'mailbox':
            cv.rgb[X, Yv, Z] = (160, 44, 42)
            cv.rgb[X[Z == topz], Yv[Z == topz], Z[Z == topz]] = (196, 160, 80)
        elif kind == 'letters':
            cv.rgb[X, Yv, Z] = np.where(((X + Yv) % 2 == 0)[:, None], np.array((212, 206, 190)),
                                        np.array((200, 190, 170)))
        elif kind == 'ice':
            stats['sculpted'] = stats.get('sculpted', 0) + carve_ice(cv, X, Yv, Z, stats.get('ice', 1) - 1)
            t = np.clip((Z.max() - Z) / max(h, 1), 0, 1)
            cv.rgb[X, Yv, Z] = (np.array((146, 194, 210)) * (1 - t)[:, None] + np.array((190, 210, 218)) * t[:, None])
            if h >= 3 and w <= 4 and stats.get('ice', 0) % 2 == 1:
                k = np.argmax(Z)                                        # glow in the base, sparingly
                glow.append((int(X[k]), int(Yv[k]), int(Z[k]), CYAN))
        elif kind == 'animal':
            pass                                                     # carousel_art
        else:
            if c0 == (150, 146, 140):
                cv.rgb[X, Yv, Z] = (150, 146, 140)
    return stats


def carve_ice(cv, X, Yv, Z, idx):
    """Shape a graybox ice block into a sculpture by REMOVING voxels only (stays inside its envelope; every remaining
    voxel stays face-connected to the base): obelisk-star, bell, fir, seal on a rock, lantern-cairn."""
    x0, x1, y0, y1, zt, zb = X.min(), X.max(), Yv.min(), Yv.max(), Z.min(), Z.max()
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    shape = ['bell', 'fir', 'obelisk', 'seal', 'cairn'][idx % 5]
    if (x1 - x0) < 2 or (y1 - y0) < 2:
        shape = 'obelisk'                                    # 2-wide blocks: a stepped needle
    rm = 0
    for (x, y, z) in zip(X, Yv, Z):
        up = zb - z                                          # 0 at the base
        edge = (x in (x0, x1)) or (y in (y0, y1))
        corner = (x in (x0, x1)) and (y in (y0, y1))
        cut = False
        if shape == 'bell':
            cut = (up >= 2 and corner) or (up == (zb - zt) and edge)
        elif shape == 'fir':
            cut = (up >= 1 and corner) or (up >= 3 and edge and (x1 - x0) >= 2)
        elif shape == 'obelisk':
            cut = up >= 3 and (x != x0 or y != y0)
        elif shape == 'seal':
            cut = up >= 1 and not (x == x0) and not (up == 1 and y == cy)
        elif shape == 'cairn':
            cut = (up % 2 == 1 and corner)
        if cut and up > 0:
            cv.solid[x, y, z] = False
            cv.mat[x, y, z] = 0
            rm += 1
    return rm


def market_art(cv, S, rep, rng, glow):
    """Striped canvas stall roofs with a scalloped valance, goods on the counters, spaced string-light bulbs."""
    canvas = [(168, 52, 48), (52, 100, 70), (70, 92, 130), (190, 150, 70), (120, 60, 110)]
    goods = [(150, 96, 56), (214, 200, 160), (150, 50, 46), (60, 100, 60), (196, 160, 80), (110, 72, 50)]
    rid, fid = cv.materials.get('roof'), cv.materials.get('furniture')
    n_bulbs = 0
    for nm, x0, x1, y0, y1 in rep['market_boxes']:
        cc = canvas[int(rng.integers(len(canvas)))]
        sl = (slice(x0, x1 + 1), slice(y0, y1 + 1), slice(40, 50))
        xs, ys, zs = np.nonzero(cv.solid[sl])
        X, Yv, Z = xs + x0, ys + y0, zs + 40
        mats = cv.mat[X, Yv, Z]
        roof = mats == rid
        stripe = (((X if (x1 - x0) >= (y1 - y0) else Yv) // 2) % 2 == 0)
        rc = np.where(stripe[:, None], np.array(cc), np.array((206, 196, 172)))
        aa = ~cv.solid[X, Yv, Z - 1]
        snowy = aa & (noise.hash3(X, Yv, Z, 31) < 0.35)
        rc = np.where(snowy[:, None], np.array(SNOW_MID), rc)
        cv.rgb[X[roof], Yv[roof], Z[roof]] = rc[roof]
        tim = (mats == cv.materials.get('timber'))
        cv.rgb[X[tim], Yv[tim], Z[tim]] = (110, 78, 54)
        fu = mats == fid
        for (x, y, z) in zip(X[fu], Yv[fu], Z[fu]):
            cv.rgb[x, y, z] = goods[int(rng.integers(len(goods)))]
        # bulbs: every 3rd roof-edge voxel along the perimeter (spaced, never a continuous line)
        edge = roof & ((X == X[roof].min()) | (X == X[roof].max()) | (Yv == Yv[roof].min()) | (Yv == Yv[roof].max()))
        ei = np.nonzero(edge)[0]
        for j, k in enumerate(ei):
            if (X[k] + Yv[k]) % 17 == 0 and X[k] <= 255:
                glow.append((int(X[k]), int(Yv[k]), int(Z[k]), [WARM, YELLOW, WARM, WHITE][j % 4]))
                n_bulbs += 1
    return n_bulbs


def hut_art(cv, S, glow):
    for h in S['front_huts']:
        x0, x1, y0, y1 = h['box']
        sl = (slice(x0, x1 + 1), slice(y0, y1 + 1), slice(42, 50))
        xs, ys, zs = np.nonzero(cv.solid[sl] & np.isin(cv.mat[sl], _ids(cv, 'building')))
        X, Yv, Z = xs + x0, ys + y0, zs + 42
        roof = Z == Z.min()
        c = np.where(((X + Yv) % 3 == 0)[:, None], np.array((96, 70, 50)), np.array((112, 82, 58)))
        aa = ~cv.solid[X, Yv, Z - 1]
        c = np.where((roof & aa)[:, None], np.array(SNOW_MID), c)
        cv.rgb[X, Yv, Z] = c
        back = y0 if h['open'] == 'S' else y1
        glow.append(((x0 + x1) // 2, back, 47, WARM))


def axis_art(cv, S, rng, glow):
    g = S['z']['valley']
    # nativity: dark timber, straw floor, robed figures, warm star lantern
    nx0, nx1, ny0, ny1 = S['nativity']['box']
    sl = (slice(nx0, 256), slice(ny0 - 1, ny1 + 2), slice(38, 51))
    xs, ys, zs = np.nonzero(cv.solid[sl])
    X, Yv, Z = xs + nx0, ys + ny0 - 1, zs + 38
    mats = cv.mat[X, Yv, Z]
    for (x, y, z, mm) in zip(X, Yv, Z, mats):
        name = None
        if mm == cv.materials.get('building'):
            cv.rgb[x, y, z] = (88, 64, 46) if (x + z) % 3 else (100, 74, 52)
        elif mm == cv.materials.get('roof'):
            cv.rgb[x, y, z] = SNOW_MID if not cv.solid[x, y, z - 1] else (150, 122, 72)
        elif mm == cv.materials.get('prop') and z <= 42:
            cv.rgb[x, y, z] = (214, 190, 120)
        elif mm == cv.materials.get('prop'):
            if (x, y) == (nx0 + 4, ny0 + 3):
                cv.rgb[x, y, z] = (90, 110, 150) if z > 47 else (212, 174, 146) if z == 47 else (90, 110, 150)
            elif (x, y) == (nx0 + 2, ny0 + 6):
                cv.rgb[x, y, z] = (120, 84, 56) if z != 47 else (212, 174, 146)
            elif cv.rgb[x, y, z].tolist() == [196, 170, 96]:
                cv.rgb[x, y, z] = (200, 176, 100)
            else:
                cv.rgb[x, y, z] = (140, 128, 116)
    for y in range(ny0, ny1 + 1):
        for x in range(nx0 + 1, 256):
            if cv.solid[x, y, g] and not cv.solid[x, y, g - 1]:
                cv.rgb[x, y, g] = (190, 160, 90) if (x + y) % 2 else (176, 148, 84)
    sy = (ny0 + ny1) // 2
    glow.append((255, sy, g - 9, YELLOW))
    # carousel: brass poles, sector-painted canopy, timber platform
    ca = S['carousel']
    cx, cy = ca['c']
    sl = (slice(cx - 10, 256), slice(cy - 10, cy + 11), slice(ca['canopy_z'] - 1, g))
    xs, ys, zs = np.nonzero(cv.solid[sl])
    X, Yv, Z = xs + cx - 10, ys + cy - 10, zs + ca['canopy_z'] - 1
    th = np.arctan2(Yv + 0.5 - cy - 0.5, X + 0.5 - cx)
    sect = ((th + np.pi) / (np.pi / 6)).astype(int) % 2
    for (x, y, z, s_) in zip(X, Yv, Z, sect):
        mm = cv.mat[x, y, z]
        if mm == cv.materials.get('roof'):
            cv.rgb[x, y, z] = (176, 52, 50) if s_ else (206, 190, 150)
            r = math.hypot(x + 0.5 - cx, y + 0.5 - cy - 0.5)
            if r > 7.2:
                cv.rgb[x, y, z] = (196, 158, 80)
                if (x + y) % 6 == 0:
                    glow.append((int(x), int(y), int(z), YELLOW))
        elif mm == cv.materials.get('prop'):
            cv.rgb[x, y, z] = (196, 160, 80) if z < g - 1 else ((120, 84, 58) if s_ else (132, 94, 64))
    carousel_animals(cv, cx, cy, ca, g, west=True)
    # rink: ice with faint skate scratches (low contrast), stone kerb with snow
    rx0, rx1, ry0, ry1 = S['rink']['box']
    for x in range(rx0, 256):
        for y in range(ry0, ry1 + 1):
            if cv.mat[x, y, g] == cv.materials.get('ice'):
                d1 = math.hypot(x - 248, y - 322)
                d2 = math.hypot(x - 245, y - 331)
                sc = (abs(d1 - 6) < 0.45) or (abs(d2 - 4) < 0.45) or (abs((x - y) % 17) == 0 and x < 250)
                base = clamp8(mix((156, 196, 210), (176, 206, 216), ((x * 7 + y * 3) % 10) / 10))
                cv.rgb[x, y, g] = shade(base, 1.04) if sc else base
            if cv.solid[x, y, g - 1] and cv.mat[x, y, g - 1] == cv.materials.get('prop'):
                cv.rgb[x, y, g - 1] = (150, 146, 140) if (x + y) % 2 else (190, 194, 204)
    # workshop sleigh: red body with gold trim, brass runners
    wk = S['workshop']['box']
    sy0 = (wk[2] + wk[3]) // 2
    for x in range(244, 253):
        for y in range(sy0 - 3, sy0 + 4):
            for z in range(g - 6, g):
                if cv.solid[x, y, z] and cv.mat[x, y, z] == cv.materials.get('prop'):
                    c = tuple(int(v) for v in cv.rgb[x, y, z])
                    if c == (112, 114, 124):
                        cv.rgb[x, y, z] = (196, 160, 80)
                    else:
                        edge = y in (sy0 - 2, sy0 + 2) or z == g - 3 and x in (246, 251)
                        cv.rgb[x, y, z] = (200, 160, 80) if edge else (160, 40, 40)
    # station lamps under the canopy, bridge portal lanterns
    st = S['station']
    for px in (st['box'][0] + 2, st['box'][0] + 8):
        glow.append((px, st['canopy_y'][1], st['floor'] - 6, WARM))
    bd = S['bridge']
    for y in (bd['y'][0], bd['y'][1]):
        glow.append((bd['x'][0], y, bd['deck_z'] - 6, WARM))
    # covered bridge planks and roof
    sl = (slice(bd['x'][0] - 1, 256), slice(bd['y'][0] - 1, bd['y'][1] + 2), slice(bd['roof_z'], bd['deck_z'] + 1))
    xs, ys, zs = np.nonzero(cv.solid[sl] & np.isin(cv.mat[sl], _ids(cv, 'building', 'roof')))
    X, Yv, Z = xs + bd['x'][0] - 1, ys + bd['y'][0] - 1, zs + bd['roof_z']
    roof = Z == bd['roof_z']
    c = np.where((Yv % 3 == 0)[:, None], np.array((96, 68, 48)), np.array((116, 84, 58)))
    c = np.where(roof[:, None], np.where(((X + Yv) % 4 < 2)[:, None], np.array(SNOW_MID), np.array((120, 64, 56))), c)
    cv.rgb[X, Yv, Z] = c


def carousel_animals(cv, cx, cy, ca, g, west=True):
    """Recolour the carousel animals: reindeer + goose on the west, fox + polar bear on the east (unique per side)."""
    pal = [((132, 92, 62), (206, 190, 160)), ((204, 204, 206), (210, 150, 60))] if west else \
          [((186, 96, 48), (204, 196, 186)), ((200, 200, 204), (60, 56, 64))]
    xr = range(cx - 8, 256) if west else range(257, cx + 9)
    k = 0
    for x in xr:
        for y in range(cy - 8, cy + 9):
            col = [z for z in range(g - 8, g) if cv.solid[x, y, z] and cv.mat[x, y, z] == cv.materials.get('animal')]
            if not col:
                continue
            body, acc = pal[0] if y < cy else pal[1]
            for z in col:
                cv.rgb[x, y, z] = acc if z == min(col) else body
            k += 1
    return k


def underground_art(cv, S, rng, glow):
    """Mine supports painted on the tunnel walls/roof every 10 voxels (no geometry), a lamp on every second
    support, crystal clusters glowing cyan, casks and carts recoloured."""
    fz = S['z']['underground_floor']
    a0, a1 = S['z']['tunnel_air']
    n = 0
    for name, (x0, x1, y0, y1) in S['tunnels']:
        along_x = (x1 - x0) >= (y1 - y0)
        L = (x1 - x0) if along_x else (y1 - y0)
        for i in range(2, L, 10):
            u = (x0 + i) if along_x else (y0 + i)
            ring = []
            if along_x:
                for y in range(y0 - 1, y1 + 2):
                    ring += [(u, y, a0 - 1)]
                ring += [(u, y0 - 1, z) for z in range(a0, fz)] + [(u, y1 + 1, z) for z in range(a0, fz)]
            else:
                for x in range(x0 - 1, x1 + 2):
                    ring += [(x, u, a0 - 1)]
                ring += [(x0 - 1, u, z) for z in range(a0, fz)] + [(x1 + 1, u, z) for z in range(a0, fz)]
            for p in ring:
                if cv.get(*p):
                    cv.rgb[p] = (110, 80, 56)
            if (i // 10) % 3 == 0:
                p = (u, y0 - 1, a0 + 1) if along_x else (x0 - 1, u, a0 + 1)
                if cv.get(*p) and p[0] <= 255:
                    glow.append(p + (WARM,))
                    n += 1
    for name, (x0, x1, y0, y1) in S['chambers']:
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(fz - 4, fz):
                    if cv.solid[x, y, z] and cv.mat[x, y, z] == cv.materials.get('prop'):
                        c = tuple(int(v) for v in cv.rgb[x, y, z])
                        if c == (150, 194, 208):
                            cv.rgb[x, y, z] = (120, 200, 210)
                        elif c == (112, 114, 124):
                            cv.rgb[x, y, z] = (84, 80, 82)
        glow.append((x1 - 3, y1 - 3, fz - 3, CYAN))
        glow.append((x0 + 3, y0 - 1, fz - 3, WARM))
        n += 2
    cx0, cx1, cy0, cy1 = S['tavern']['cellar']
    glow.append((cx0 + 3, cy0 - 1, fz - 3, WARM))
    return n


# =============================================================================================== top level

def art_west(cv, rep, S, rng, seed):
    glow = []
    out = {}
    out['terrain'] = terrain_art(cv, S, seed)
    lit = 0
    for (nm, box, g, n, sh, ridge, key) in building_list(S, rep):
        st = STYLES[key]
        lit += style_building(cv, box, g, n, sh, rng, glow, st, lit=0.45 if key == 'tavern' else 0.22,
                              ridge=ridge or 'x', eave_lights=(key in (0, 2, 3, 'tavern', 'po')),
                              chimney=(ridge is not None), wreath=True)
    out['lit_windows'] = lit
    chapel_art(cv, S, rng, glow)
    if S['gatehouse'].get('variant') == 'arch':
        arch_art(cv, S, glow)
    else:
        gatehouse_art(cv, S, glow)
    if S.get('zones'):
        out['v12'] = v12_art(cv, S, rng, glow)
    out['props'] = props_art(cv, S, rng, glow)
    out['stall_bulbs'] = market_art(cv, S, rep, rng, glow)
    hut_art(cv, S, glow)
    axis_art(cv, S, rng, glow)
    out['mine_lamps'] = underground_art(cv, S, rng, glow)
    # vegetation (holly bushes keep their voxels; spruce one-off; real trees on every stand-in column)
    if S.get('zones'):
        bushes = [(x - 4, x + 4, y - 4, y + 4) for (x, y, k) in S['front_props_v12'] if k == 'bush']
    else:
        bushes = [(x - 3, x + 3, y - 3, y + 3) for (x, y, k) in S['front_props'] if k == 'bush']
    out['holly_voxels'] = fh_veg.holly_recolour(cv, rng, bushes)
    out['spruce'] = fh_veg.giant_spruce(cv, rng, S, glow)
    pines = rep['scatter']['pine_list']
    import fh_graybox
    fest = fh_graybox.plaza_mask(S) | fh_graybox._box(*[S['village'][k] for k in ('x', 'y')])
    fest = ndi.binary_dilation(fest, iterations=14)
    out['trees'] = fh_veg.replace_stand_ins(cv, pines, rng, seed, glow, festive=fest)
    skipped = 0
    for (x, y, z, c) in glow:                 # glow is a recolour: only on voxels that already exist
        if x <= 255 and cv.inside(x, y, z) and cv.solid[x, y, z]:
            cv.add_glow(x, y, z, c)
        else:
            skipped += 1
    out['glow_sources_west'] = len(glow) - skipped
    out['glow_skipped'] = skipped
    return out


def tree_nooks(cv, rounds=6):
    """A ground cell boxed in by tree canopies / a terrace step on every side (every neighbour's walkable top more than
    1 above it) gets a snow drift up to the lowest neighbour - 1, so nobody can drop in and stay stuck. Only next to
    plants (inside the vegetation allowance of the collision check)."""
    from aosmap.kit.symmetry import standable
    veg = np.isin(cv.mat, _ids(cv, 'leaf', 'bark', 'twig', 'spruce')).any(2)
    near = ndi.binary_dilation(veg, iterations=1)
    n = 0
    for _ in range(rounds):
        st = standable(cv.solid)
        ht = np.where(st.any(2), np.argmax(st, axis=2), 64)          # highest standable floor per column
        floor = np.where(st[np.arange(512)[:, None], np.arange(512)[None, :], cv.H], cv.H, 64)
        nb = np.stack([np.roll(ht, 1, 0), np.roll(ht, -1, 0), np.roll(ht, 1, 1), np.roll(ht, -1, 1)])
        ok_nb = np.abs(nb - floor[None]) <= 1
        pit = near & (floor < 62) & ~ok_nb.any(0)
        pit[256:] = False
        if not pit.any():
            break
        for x, y in zip(*np.nonzero(pit)):
            z = int(cv.H[x, y]) - 1
            if not cv.solid[x, y, z]:
                cv.set(x, y, z, SNOW_MID, 'drift')
                cv.H[x, y] = z
                n += 1
    return n


def train_art(cv, S, glow):
    tr = S['train']
    x0, x1, y0, y1 = tr['box']
    cz = tr['chassis_z']
    tid = cv.materials.get('train')
    cars = [(x0, x0 + 12), (x0 + 14, x0 + 26), (x0 + 28, x0 + 40)]
    livery = [(64, 96, 72), (120, 50, 46), (64, 82, 112)]
    for k, (a, b) in enumerate(cars):
        for x in range(a, b + 1):
            for y in range(y0 - 1, y1 + 2):
                for z in range(cz - 3, cz + 2):
                    if cv.solid[x, y, z] and cv.mat[x, y, z] == tid:
                        if z == cz:
                            cv.rgb[x, y, z] = (118, 88, 62) if (x % 2) else (106, 78, 56)
                        elif z == cz + 1:
                            cv.rgb[x, y, z] = (110, 82, 58)
                        else:
                            cv.rgb[x, y, z] = (200, 162, 82) if z == cz - 2 else livery[k]
    a, b = x0 + 42, x1
    for x in range(a, b + 1):
        for y in range(y0 - 1, y1 + 2):
            for z in range(cz - 8, cz + 2):
                if cv.solid[x, y, z] and cv.mat[x, y, z] == tid:
                    if x >= b - 5:
                        cv.rgb[x, y, z] = (150, 50, 44) if z > cz - 6 else (60, 60, 68)
                        if z == cz - 1 and y in (y0, y1):
                            cv.rgb[x, y, z] = (200, 162, 82)
                    elif z == cz:
                        cv.rgb[x, y, z] = (150, 50, 44)
                    else:
                        cv.rgb[x, y, z] = (200, 162, 82) if (x - a) % 3 == 0 else (64, 64, 74)
    glow.append((a + 1, (y0 + y1) // 2, cz - 3, YELLOW))                    # headlamp on the boiler front
    # rails steel
    rid = cv.materials.get('rail')
    m = cv.mat == rid
    cv.rgb[m] = (112, 112, 122)


def art_post(cv, rep, S, rng, out_info):
    """After mirror + train: train dressing, east carousel animals, unique pad one-offs per side, sky, tag."""
    glow = []
    train_art(cv, S, glow)
    ca = S['carousel']
    carousel_animals(cv, ca['c'][0], ca['c'][1], ca, S['z']['valley'], west=False)
    pads = []
    for p in rep['scatter']['feature_pads']:
        x0, x1, y0, y1 = p['box']
        pads.append({'kind': p['kind'], 'box': [x0, x1, y0, y1]})
        pads.append({'kind': p['kind'], 'box': [mirror_index(x1), mirror_index(x0), y0, y1]})
    g2, recs = fh_props.build_pads(cv, rng, pads)
    glow += g2
    sky_recs = fh_sky.place_sky(cv)
    rect = paint_tag_at(cv, S['name'], S['tag']['x0'], S['tag']['y0'])
    best = None
    for (x, y, z, c) in glow:
        if cv.inside(x, y, z) and cv.solid[x, y, z]:
            cv.add_glow(x, y, z, c)
    out_info.update({'pads': recs, 'sky': sky_recs, 'tag_rect': list(rect), 'tag_margin': best,
                     'glow_sources_post': len(glow)})
    boxes = [list(rect[:4])]
    boxes += [p['box'] for p in pads]
    boxes += [[r['x'][0], r['x'][1], r['y'][0], r['y'][1]] for r in sky_recs]
    return boxes


def paint_tag_at(cv, text, x0, y0, rgb=(206, 186, 140), shadow=(92, 76, 60)):
    """aosmap.kit.tag.paint_tag's painting on an explicit origin in the NE quadrant (the graybox reserves this strip
    flat and clear, so nothing is levelled or cleared): map name only, painted on the ground, with a 1-voxel shadow."""
    from aosmap.pixelfont import text_mask
    m = text_mask([text.upper()])
    z = int(cv.H[x0, y0])
    for (i, j) in zip(*np.nonzero(m)):
        x, y = x0 + i, y0 + j
        cv.rgb[x, y, z] = rgb
        if not m[min(i + 1, m.shape[0] - 1), min(j + 1, m.shape[1] - 1)]:
            cv.rgb[x + 1, y + 1, z] = shadow
    return (x0 - 2, x0 + m.shape[0] + 1, y0 - 2, y0 + m.shape[1] + 1, z)


def finish(cv, target_median=90.0, tint=(0.97, 0.98, 1.06)):
    """Baked light + AO, twilight grade (cool, dimmer so glow reads), brightness rules, glow bake, palette nudge."""
    surf = color.lighting(cv)
    # twilight grade: cool tint + one scalar so the top-surface median luma lands on target (glow stays full)
    top = np.argmax(cv.solid, axis=2)
    X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    L = color.luma(cv.rgb[X, Y, top].astype(float) * np.array(tint))
    k = float(np.clip(target_median / max(np.median(L), 1.0), 0.45, 1.0))
    grade = tuple(k * t for t in tint)
    m = cv.solid & ~cv.nolight
    c = cv.rgb[m].astype(np.float32) * np.array(grade, np.float32)
    cv.rgb[m] = np.clip(c, 0, 255).astype(np.uint8)
    bright = color.enforce_brightness(cv, floor_min=41)
    stored, n_src = bake_glow_fast(cv, surf)
    # nudge lit voxels that landed exactly on a glow-palette colour (only true sources may match)
    srcs = {(x, y, z) for (x, y, z, _) in cv.glow}
    nudged = 0
    for k in list(stored):
        if k in srcs:
            continue
        cc = tuple(int(v) for v in cv.rgb[k])
        if cc in GLOW_PALETTE:
            cv.rgb[k] = (max(0, cc[0] - 1), cc[1], cc[2])
            nudged += 1
    return stored, {'grade': [round(g, 3) for g in grade], 'brightness': bright, 'glow_sources': n_src, 'glow_lit_voxels': len(stored) - n_src,
                    'palette_nudged': nudged}


def bake_glow_fast(cv, surf, radius=6.5, strength=0.32):
    """Same model as aosmap.kit.color.bake_glow (additive, linear falloff, Euclidean d, sources keep their exact
    colour, originals stored for the glow-aware server) but vectorised per source."""
    srcs, seen = [], set()
    for (x, y, z, c) in cv.glow:
        if (x, y, z) in seen or not cv.inside(x, y, z) or not cv.solid[x, y, z]:
            continue
        seen.add((x, y, z))
        srcs.append((x, y, z, c))
    R = int(math.ceil(radius))
    o = np.arange(-R, R + 1)
    DX, DY, DZ = np.meshgrid(o, o, o, indexing='ij')
    D = np.sqrt(DX ** 2 + DY ** 2 + DZ ** 2)
    W = np.where((D < radius) & (D > 0), (1 - D / radius) * strength, 0.0)
    acc = {}
    for (x, y, z, c) in srcs:
        xs, ys, zs = x + DX, y + DY, z + DZ
        ok = (W > 0) & (xs >= 0) & (xs < 512) & (ys >= 0) & (ys < 512) & (zs >= 0) & (zs < 64)
        xs, ys, zs, w = xs[ok], ys[ok], zs[ok], W[ok]
        s = surf[xs, ys, zs]
        for (a, b, cc, ww) in zip(xs[s], ys[s], zs[s], w[s]):
            k = (int(a), int(b), int(cc))
            v = acc.get(k)
            if v is None:
                acc[k] = [c[0] * ww, c[1] * ww, c[2] * ww]
            else:
                v[0] += c[0] * ww
                v[1] += c[1] * ww
                v[2] += c[2] * ww
    stored = {}
    for k, a in acc.items():
        if k in seen:
            continue
        orig = tuple(int(v) for v in cv.rgb[k])
        stored[k] = orig
        cv.rgb[k] = (min(255, int(orig[0] + a[0])), min(255, int(orig[1] + a[1])), min(255, int(orig[2] + a[2])))
    for (x, y, z, c) in srcs:
        cv.rgb[x, y, z] = c
        stored[(x, y, z)] = tuple(c)
    return stored, len(srcs)
