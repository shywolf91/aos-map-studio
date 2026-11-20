"""Craft checks: building quality and spawn quality for ANY game mode. Report + pass/fail gates.

    python -m aosmap.kit.craft_checks <map dir or .vxl> [--mode babel|ctf|tdm|tc|push|arena|ffa] [--out craft.json]
           [--box name,x0,x1,y0,y1 ...]

Buildings: graded per registered structure (build.json 'structures': [{'name', 'box': [x0, x1, y0, y1]}, ...],
or --box) or, when nothing is registered, per detected built object. Thresholds (CRAFT_GATES) were calibrated on the
owner's favourites (Wicker King's barn and farmhouse, Silverpine's lodge and watch-house, normandie's houses) against
Floebreaker v1's huts and towers (docs/craft_standard.md, 2026-11-20). They describe the minimum the owner has accepted,
not an ideal.

Spawns: the server's own rules (pyspades / piqueserver 1.4.2, read in source):
  babel  +-20 around (118,256) / (394,256), topmost voxel
  ctf / tdm (no hook)  random land column (z 62 solid) in x 0-127 / 384-511, y 128-383, topmost voxel
  tc     random land within 32 of an owned territory point (needs --tc-points or build.json 'tc_points')
  push   +- push_spawn_range around push_*_spawn; arena: the listed points; ffa: any land column
A custom get_spawn_location hook is never executed; pass the points with build.json 'spawn_points' instead.
"""
from __future__ import annotations

import argparse
import ast
import glob
import json
import os

import numpy as np
from scipy import ndimage as ndi

from .codec import decode, surface_mask, unpack_rgb

CRAFT_GATES = {
    # Per role. Calibrated 2026-11-20 on Silverpine's lodge, Wicker King's barn/farmhouse/shed and normandie's church
    # (all pass 'main' or 'small') against Floebreaker v1's huts and weather towers (all fail). Minimums, not ideals.
    'main': {'area': 200, 'height': 12, 'roof_pitched': 0.65, 'roof_rise_share': 0.30, 'massing': 2,
             'colours': 30, 'wall_value_range': 15.0, 'openings_per_10_perim': 3.0, 'indoor_share': 0.20,
             'yard_props': 8},
    'small': {'roof_pitched': 0.60, 'roof_rise_share': 0.25, 'colours': 20, 'wall_value_range': 15.0,
              'openings_per_10_perim': 2.0, 'indoor_share': 0.20, 'yard_props': 4},
    'tower': {'height': 14, 'colours': 30, 'wall_value_range': 15.0, 'openings_per_10_perim': 2.0,
              'indoor_share': 0.15, 'massing': 2, 'yard_props': 4},     # roof may be a deck or a spire
    'ruin': {'colours': 30, 'wall_value_range': 15.0, 'openings_per_10_perim': 2.0, 'yard_props': 6},
    'vessel': {'colours': 30, 'wall_value_range': 15.0, 'openings_per_10_perim': 2.0, 'indoor_share': 0.15,
               'massing': 2},
}
REPORT_ONLY = ('roof_eave', 'base_course', 'roof_wall_contrast', 'wall_colours')
SPAWN_GATES = {
    'water_share': 0.0,
    'object_top_share': 0.03,   # spawning on a roof, tree or boulder top (players land on topmost voxels)
    'air_below_share': 0.02,    # spawning above an overhang or room (roof/canopy spawns)
    'steep_share': 0.15,        # columns with a >= 2 step to a neighbour
    'walk_out_share': 0.98,     # spawns standing in a walkable region of >= 1500 columns (no pits / sealed pockets)
    'cover_within_8_min': 0.35, # spawns with a 3+ rise within 8 voxels (somewhere to duck)
}

BABEL = {'bases': ((118, 256), (394, 256)), 'half': 20}


# ------------------------------------------------------------------ io
def load(path):
    if os.path.isdir(path):
        vx = sorted(glob.glob(os.path.join(path, '*.vxl')))
        if len(vx) != 1:
            raise SystemExit(f'expected one .vxl in {path}, found {len(vx)}')
        path = vx[0]
    d = os.path.dirname(path)
    stem = os.path.splitext(path)[0]
    build = {}
    for cand in (stem + '_build.json', os.path.join(d, 'build.json')):
        if os.path.exists(cand):
            build = json.load(open(cand))
            break
    ext = {}
    if os.path.exists(stem + '.txt'):
        src = open(stem + '.txt', encoding='utf-8', errors='replace').read()
        try:
            for node in ast.parse(src).body:
                if isinstance(node, ast.Assign) and getattr(node.targets[0], 'id', '') == 'extensions':
                    ext = ast.literal_eval(node.value)
        except Exception:                                                     # noqa: BLE001
            pass
        build.setdefault('_has_spawn_hook', 'def get_spawn_location' in src)
    solid, color, _ = decode(open(path, 'rb').read())
    return path, solid, color, build, ext


def luma(rgb):
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


# ------------------------------------------------------------------ buildings
def ground_field(solid):
    s = solid[:, :, :63]
    land = solid[:, :, 62]
    top = np.where(s.any(axis=2), np.argmax(s, axis=2), 63)
    elev = np.where(land, 63 - top, 0).astype(np.int16)
    ground = ndi.grey_opening(elev, size=(25, 25))
    return top, land, elev, ground


def grade_building(solid, color, box, top, ground, surf=None, role=None):
    """Measure one building inside box (x0, x1, y0, y1) -> metrics + gate results for its role
    ('main', 'small', 'tower', 'ruin', 'vessel'; default by footprint)."""
    x0, x1, y0, y1 = box
    sl = (slice(x0, x1 + 1), slice(y0, y1 + 1))
    g = int(np.median(63 - ground[sl]))                          # ground surface z
    rise = (63 - top[sl]) - (63 - g)
    fp = rise >= 2                                               # footprint: columns standing >= 2 above ground
    area = int(fp.sum())
    if area < 12:
        return {'box': list(box), 'error': 'nothing standing in the box'}
    ztop = int(top[sl][fp].min())
    H = g - ztop
    sub = solid[x0:x1 + 1, y0:y1 + 1, ztop:g]
    col = color[x0:x1 + 1, y0:y1 + 1, ztop:g]
    if surf is None:
        surf = surface_mask(solid)
    ss = surf[x0:x1 + 1, y0:y1 + 1, ztop:g]
    nz = sub.shape[2]
    # walls = solid voxels in the lower 60 % of the height that face air sideways; roof = topmost voxel per column
    side_air = np.zeros_like(sub)
    side_air[1:] |= ~sub[:-1]; side_air[:-1] |= ~sub[1:]; side_air[:, 1:] |= ~sub[:, :-1]; side_air[:, :-1] |= ~sub[:, 1:]
    zz = np.arange(nz)[None, None, :]
    wall_band = zz >= int(nz * 0.4)
    walls = sub & side_air & wall_band & ss
    wrgb = unpack_rgb(col[walls]).astype(float) if walls.any() else np.zeros((0, 3))
    roof_z = np.argmax(sub, axis=2)
    has = sub.any(axis=2)
    rx, ry = np.nonzero(has & fp)
    rrgb = unpack_rgb(col[rx, ry, roof_z[rx, ry]]).astype(float)
    m = {'box': list(box), 'area': area, 'height': H}
    # roof form
    rz = roof_z[has & fp]
    vals, cnt = np.unique(rz, return_counts=True)
    m['roof_pitched'] = round(1 - cnt.max() / len(rz), 3)
    # roof rise: eave level (roof outline) to ridge, as a share of the whole height
    outline0 = fp & ~ndi.binary_erosion(fp)
    oz = roof_z[outline0 & has]
    eave_z = float(np.median(oz)) if len(oz) else float(np.median(rz))
    m['roof_rise_share'] = round(max(0.0, eave_z - float(rz.min())) / max(H, 1), 3)
    # all exposed colours of the building (quantised /8)
    ex = sub & ss & fp[:, :, None]
    q_all = (unpack_rgb(col[ex]).astype(np.int64) // 8) if ex.any() else np.zeros((0, 3), np.int64)
    m['colours'] = int(len(np.unique(q_all[:, 0] * 1024 + q_all[:, 1] * 32 + q_all[:, 2]))) if len(q_all) else 0
    # eaves: roof outline cells whose roof voxel has air directly below it
    outline = fp & ~ndi.binary_erosion(fp)
    ox, oy = np.nonzero(outline & has)
    below = roof_z[ox, oy] + 1
    ok = below < nz
    m['roof_eave'] = round(float((~sub[ox[ok], oy[ok], below[ok]]).mean()) if ok.any() else 0.0, 3)
    # walls
    if len(wrgb):
        q = (wrgb // 8).astype(np.int64)
        m['wall_colours'] = int(len(np.unique(q[:, 0] * 1024 + q[:, 1] * 32 + q[:, 2])))
        L = luma(wrgb)
        m['wall_value_range'] = round(float(np.percentile(L, 90) - np.percentile(L, 10)), 1)
        wz = np.nonzero(walls)[2]
        low = wrgb[wz >= nz - 2]; band = wrgb[(wz < nz - 2) & (wz >= nz - 7)]
        m['base_course'] = round(float(np.abs(low.mean(0) - band.mean(0)).sum()), 1) if len(low) > 4 and len(band) > 4 else 0.0
        m['roof_wall_contrast'] = round(float(np.abs(rrgb.mean(0) - wrgb.mean(0)).sum()), 1) if len(rrgb) else 0.0
    else:
        m.update(wall_colours=0, wall_value_range=0.0, base_course=0.0, roof_wall_contrast=0.0)
    # openings: outline columns with air under a solid (door / window / arcade) in the wall band
    solid_above = np.maximum.accumulate(sub, axis=2)
    roofed_air = (~sub) & solid_above
    per = int(outline.sum())
    holes = int((roofed_air[:, :, int(nz * 0.3):].any(axis=2) & outline).sum())
    m['openings_per_10_perim'] = round(10.0 * holes / max(per, 1), 2)
    m['indoor_share'] = round(float((roofed_air & fp[:, :, None]).sum()) / max(area * H, 1), 3)
    # massing: separate roof clusters standing >= 3 above the eave level
    eave = int(np.percentile(rz, 70)) if len(rz) else 0
    hi = has & fp & (roof_z <= eave - 3)
    m['massing'] = int(ndi.label(hi)[1]) + 1 if hi.any() else 1
    # yard: small objects 2-6 tall within 10 of the walls, outside the footprint
    X0, X1, Y0, Y1 = max(x0 - 10, 0), min(x1 + 10, 511), max(y0 - 10, 0), min(y1 + 10, 511)
    el = (63 - top[X0:X1 + 1, Y0:Y1 + 1]).astype(float)
    loc = ndi.median_filter(el, size=9)                          # local ground under small props
    big = el - loc
    inner = np.zeros_like(big, bool); inner[x0 - X0:x1 - X0 + 1, y0 - Y0:y1 - Y0 + 1] = fp
    small = (big >= 1) & (big <= 6) & ~ndi.binary_dilation(inner, iterations=2)
    m['yard_props'] = int(ndi.label(small, structure=np.ones((3, 3)))[1])
    role = role or ('main' if area >= 150 else 'small')
    m['role'] = role
    gates = {k: bool(m[k] >= thr) for k, thr in CRAFT_GATES[role].items() if k in m}
    m['gates'] = gates
    m['pass'] = all(gates.values()) if area >= 30 and H >= 5 else None      # litter-sized: report only
    m['score'] = round(sum(gates.values()) / max(len(gates), 1), 2)
    return m


def detect_buildings(solid, color, top, land, ground, min_area=40, min_h=6):
    """Heuristic: built objects (not trees: base covers the footprint; not rock: has rooms or openings)."""
    elev = np.where(land, 63 - top, 0)
    obj = land & ((elev - ground) >= 3)
    lab, n = ndi.label(obj, structure=np.ones((3, 3)))
    boxes = []
    for i, sl in enumerate(ndi.find_objects(lab)):
        fp = lab[sl] == i + 1
        if fp.sum() < min_area:
            continue
        x0, x1, y0, y1 = sl[0].start, sl[0].stop - 1, sl[1].start, sl[1].stop - 1
        if x1 - x0 > 90 or y1 - y0 > 90:
            continue                                            # forests / mountains merged into one blob
        g = int(np.median(63 - ground[sl][fp]))
        if g - int(top[sl][fp].min()) < min_h:
            continue
        base = solid[x0:x1 + 1, y0:y1 + 1, g - 2:g].any(axis=2) & fp
        if base.sum() / fp.sum() < 0.35:
            continue                                            # trunk under a canopy
        boxes.append((x0, x1, y0, y1))
    return boxes


# ------------------------------------------------------------------ spawns
def spawn_sets(mode, ext, build, land):
    def rect(x0, x1, y0, y1, need_land):
        xs, ys = np.meshgrid(np.arange(max(x0, 0), min(x1, 511) + 1), np.arange(max(y0, 0), min(y1, 511) + 1),
                             indexing='ij')
        xs, ys = xs.ravel(), ys.ravel()
        if need_land and land[xs, ys].any():
            k = land[xs, ys]; xs, ys = xs[k], ys[k]
        return xs, ys
    if build.get('spawn_points'):
        return {t: (np.array([p[0] for p in pts]), np.array([p[1] for p in pts]))
                for t, pts in build['spawn_points'].items()}, 'build.json spawn_points'
    if mode == 'babel':
        return {t: rect(bx - 20, bx + 20, by - 20, by + 20, False)
                for t, (bx, by) in zip(('blue', 'red'), BABEL['bases'])}, 'babel +-20 (babel_script)'
    if mode == 'push':
        r = int(ext.get('push_spawn_range', 5))
        out = {t: rect(int(ext[k][0]) - r, int(ext[k][0]) + r, int(ext[k][1]) - r, int(ext[k][1]) + r, False)
               for t, k in (('blue', 'push_blue_spawn'), ('red', 'push_green_spawn')) if ext.get(k)}
        return out, f'push +-{r}'
    if mode == 'arena':
        out = {}
        for t, k in (('blue', 'arena_blue_spawns'), ('red', 'arena_green_spawns')):
            pts = ext.get(k) or ((ext[k[:-1]],) if ext.get(k[:-1]) else ())
            if pts:
                out[t] = (np.array([p[0] for p in pts]), np.array([p[1] for p in pts]))
        return out, 'arena points'
    if mode == 'tc':
        pts = build.get('tc_points') or []
        if not pts:
            return {}, 'tc: give build.json tc_points'
        out = {}
        for i, (x, y) in enumerate(pts):
            out[f'cp{i}'] = rect(x - 32, x + 32, y - 32, y + 32, True)
        return out, 'tc +-32 around each point'
    if build.get('_has_spawn_hook'):
        return {}, 'custom get_spawn_location hook: give build.json spawn_points'
    if mode == 'ffa':
        return {'all': rect(0, 511, 0, 511, True)}, 'ffa any land'
    return {'blue': rect(0, 127, 128, 383, True), 'red': rect(384, 511, 128, 383, True)}, 'ctf/tdm team strip'


def walk_out(top, land, xs, ys, min_region=1500):
    """Share of spawn columns whose walkable top-surface region (4-neighbour steps of at most 1) holds at least
    min_region columns: not a pit, ledge or sealed pocket. Mode-neutral (works on push islands and sky decks)."""
    elev = np.where(land, 63 - top, -999).astype(np.int32)
    lab = np.zeros(elev.shape, np.int32)
    # union of 4-neighbour links with |dz| <= 1: label by flood over a graph of equal-ish heights
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    idx = np.arange(512 * 512).reshape(512, 512)
    rows, cols = [], []
    for dx, dy in ((1, 0), (0, 1)):
        a = elev[:512 - dx, :512 - dy]; b = elev[dx:, dy:]
        ok = (np.abs(a - b) <= 1) & (a > -999) & (b > -999)
        rows.append(idx[:512 - dx, :512 - dy][ok]); cols.append(idx[dx:, dy:][ok])
    r = np.concatenate(rows); c = np.concatenate(cols)
    g = coo_matrix((np.ones(len(r), np.int8), (r, c)), shape=(512 * 512, 512 * 512))
    n, labels = connected_components(g, directed=False)
    sizes = np.bincount(labels)
    lab = labels.reshape(512, 512)
    return float((sizes[lab[xs, ys]] >= min_region).mean()) if len(xs) else None


def grade_spawns(solid, mode, ext, build, top, land, ground):
    sets, rule = spawn_sets(mode, ext, build, land)
    out = {'rule': rule, 'teams': {}}
    if not sets:
        out['pass'] = None
        return out
    rise = (63 - top) - ground
    elev = (63 - top).astype(np.int16)
    dz = np.maximum(np.abs(np.diff(elev, axis=0, prepend=elev[:1])), np.abs(np.diff(elev, axis=1, prepend=elev[:, :1])))
    mid = np.zeros((512, 512), bool); mid[200:312, 160:352] = True
    cover = ndi.maximum_filter((rise >= 3).astype(np.uint8), size=17) > 0
    ok_all = True
    if mode == 'arena':
        # arena spawns use the listed (x, y, z) as the player position (eye ~2.4 above the floor): judge the floor
        # under each point and the headroom, not the column top
        pts = {}
        for t, k in (('blue', 'arena_blue_spawns'), ('red', 'arena_green_spawns')):
            P = ext.get(k) or ((ext[k[:-1]],) if ext.get(k[:-1]) else ())
            pts[t] = [p for p in P if p and len(p) >= 3]
        for t, P in pts.items():
            rows = []
            for x, y, z in P:
                x, y, z = int(x), int(y), float(z)
                col = solid[int(np.clip(x, 0, 511)), int(np.clip(y, 0, 511))]
                zf = next((zz for zz in range(int(z), min(int(z) + 6, 64)) if col[zz]), None)
                head = zf is not None and not col[max(zf - 3, 0):zf].any()
                rows.append({'xyz': [x, y, z], 'floor_z': zf, 'floor_found': zf is not None, 'headroom_ok': bool(head)})
            ok = bool(rows) and all(r['floor_found'] and r['headroom_ok'] for r in rows) and len(rows) >= 3
            out['teams'][t] = {'points': rows, 'count': len(rows), 'gates': {'floor_and_headroom': all(r['floor_found'] and r['headroom_ok'] for r in rows),
                                                                             'at_least_3_points': len(rows) >= 3}, 'pass': ok}
            ok_all &= ok
        out['pass'] = ok_all
        return out
    for t, (xs, ys) in sets.items():
        xs = np.clip(xs, 0, 511); ys = np.clip(ys, 0, 511)
        r = {'columns': int(len(xs))}
        r['water_share'] = round(float((top[xs, ys] >= 63).mean()), 3)
        r['sea_level_share'] = round(float((top[xs, ys] >= 61).mean()), 3)        # matters only with water_damage
        r['object_top_share'] = round(float((rise[xs, ys] >= 3).mean()), 3)
        gap = [bool((~solid[x, y, top[x, y]:63]).any()) for x, y in zip(xs[:3000], ys[:3000])]
        r['air_below_share'] = round(float(np.mean(gap)), 3)
        r['steep_share'] = round(float((dz[xs, ys] >= 2).mean()), 3)
        r['walk_out_share'] = round(walk_out(top, land, xs, ys) or 0.0, 3)
        r['cover_within_8'] = round(float(cover[xs, ys].mean()), 3)
        gates = {'water_share': r['water_share'] <= SPAWN_GATES['water_share'],
                 'object_top_share': r['object_top_share'] <= SPAWN_GATES['object_top_share'],
                 'air_below_share': r['air_below_share'] <= SPAWN_GATES['air_below_share'],
                 'steep_share': r['steep_share'] <= SPAWN_GATES['steep_share'],
                 'cover_within_8': r['cover_within_8'] >= SPAWN_GATES['cover_within_8_min']}
        gates['walk_out_share'] = r['walk_out_share'] >= SPAWN_GATES['walk_out_share']
        if (ext.get('water_damage') or 0) > 0 or mode == 'push':
            gates['sea_level_share'] = r['sea_level_share'] <= 0.0
        r['gates'] = gates
        r['pass'] = all(gates.values())
        ok_all &= r['pass']
        out['teams'][t] = r
    out['pass'] = ok_all
    return out


# ------------------------------------------------------------------ main
def run(path, mode=None, boxes=None, box_roles=None):
    path, solid, color, build, ext = load(path)
    if mode is None:
        mode = build.get('mode') or ('push' if any(k.startswith('push_') for k in ext) else
                                     'arena' if any(k.startswith('arena') for k in ext) else
                                     'babel' if ext.get('babel') else 'ctf')
    top, land, elev, ground = ground_field(solid)
    surf = surface_mask(solid)
    reg = boxes or [tuple(s['box']) for s in build.get('structures', [])]
    names = [s.get('name', f's{i}') for i, s in enumerate(build.get('structures', []))] if not boxes else \
        [f'box{i}' for i in range(len(reg))]
    roles = [s.get('role') for s in build.get('structures', [])] if not boxes else (box_roles or [None] * len(reg))
    detected = False
    if not reg:
        reg = detect_buildings(solid, color, top, land, ground)
        names = [f'auto{i}' for i in range(len(reg))]
        roles = [None] * len(reg)
        detected = True
    bld = [dict(name=n, **grade_building(solid, color, b, top, ground, surf, r)) for n, b, r in zip(names, reg, roles)]
    graded = [b for b in bld if b.get('pass') is not None]
    res = {'map': os.path.basename(path), 'mode': mode, 'buildings_source': 'detected' if detected else 'registered',
           'buildings': bld,
           'buildings_pass': (sum(b['pass'] for b in graded), len(graded)),
           'buildings_mean_score': round(float(np.mean([b['score'] for b in graded])), 2) if graded else None,
           'spawns': grade_spawns(solid, mode, ext, build, top, land, ground)}
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('path')
    ap.add_argument('--mode')
    ap.add_argument('--out')
    ap.add_argument('--box', action='append', default=[])
    a = ap.parse_args(argv)
    boxes = [tuple(int(v) for v in b.split(',')[1:5]) for b in a.box] or None
    R = run(a.path, a.mode, boxes, [b.split(',')[5] if len(b.split(',')) > 5 else None for b in a.box])
    if a.out:
        json.dump(R, open(a.out, 'w'), indent=1, default=float)
    print(f"{R['map']}  mode {R['mode']}  buildings ({R['buildings_source']}): pass {R['buildings_pass'][0]}/"
          f"{R['buildings_pass'][1]}  mean gate score {R['buildings_mean_score']}")
    for b in R['buildings']:
        if b.get('pass') is None:
            continue
        fails = [k for k, v in b['gates'].items() if not v]
        print(f"  {'PASS' if b['pass'] else 'FAIL'} {b['name']:<14} {b.get('role', ''):<6} {b['box']} h{b['height']} a{b['area']}  "
              + ('' if not fails else 'fails: ' + ', '.join(f"{k}={b[k]}" for k in fails)))
    sp = R['spawns']
    print(f"spawns: {sp['rule']}  {'PASS' if sp.get('pass') else 'FAIL' if sp.get('pass') is False else 'N/A'}")
    for t, r in sp['teams'].items():
        fails = [k for k, v in r['gates'].items() if not v]
        print(f"  {t:<5} {'PASS' if r['pass'] else 'FAIL'}  " + ', '.join(f"{k} {r[k]}" for k in r if k not in ('gates', 'pass', 'points'))
              + ('' if not fails else '   fails: ' + ', '.join(fails)))
    return R


if __name__ == '__main__':
    main()
