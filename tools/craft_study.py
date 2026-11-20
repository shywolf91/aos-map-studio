"""Craft study: structures, spawns (every game mode) and colour for a folder of classic AoS maps.

    python tools/craft_study.py H:/maps [--out out/craft_study] [--workers 8] [--limit N] [--only name1,name2]

Per map (cached in OUT/cache/<stem>.json):
  * mode guess from the .txt (parsed with ast, literal values only, NEVER executed) and the file name
  * structures: objects = columns rising >= 3 above a ground estimate (grey opening of the height field, 21 wide);
    8-connected footprints >= 12 cells and >= 4 tall. Each object is classed vegetation / built by hue, then measured:
    indoor share (roofed air between ground and roof), wall openings, roof form (flat share, distinct roof levels,
    eave overhang), surface detail (exposed voxels per footprint and height), palette (distinct colours, value range),
    base course (does the bottom band differ from the wall band).
  * spawns by mode, from the server's own rules (pyspades / piqueserver 1.4.2):
      ctf/tdm default: random land column (z 62 solid) in x 0-127 (team 1) / 384-511 (team 2), y 128-383, topmost voxel
      tc: +-32 around an owned territory point; push: +-push_spawn_range around push_*_spawn; arena: listed points;
      babel: +-20 around (118,256) / (394,256); ffa: any non-water column.
    measured: roof/object-top share (spawning on a building, tree or rock top), water share, floor roughness,
    walk-out share (2D top-surface graph: step up <= 1, any drop <= 9) to the map's middle band, cover 3+ within 8.
  * colour: distinct colours, top-surface luma p10/p50/p90, white (max ch >= 235) and dark (luma < 40) shares,
    neighbour colour jump (noise), coherence (|dL| at 4 / at 1).
Nothing is written into the map folder.
"""
from __future__ import annotations

import argparse
import ast
import glob
import json
import os
import re
import sys
import time
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from scipy import ndimage as ndi

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT)

CODE_VERSION = 'craft-2'


# ------------------------------------------------------------------ metadata (never executed)
def read_txt(path):
    out = {'has_txt': False}
    if not os.path.exists(path):
        return out
    out['has_txt'] = True
    try:
        src = open(path, 'r', encoding='utf-8', errors='replace').read()
    except OSError:
        return out
    out['has_spawn_hook'] = 'def get_spawn_location' in src
    out['has_entity_hook'] = 'def get_entity_location' in src
    try:
        tree = ast.parse(src)
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                k = node.targets[0].id
                if k in ('name', 'author', 'description', 'extensions', 'fog', 'version'):
                    try:
                        v = ast.literal_eval(node.value)
                        out[k] = v if k != 'extensions' else {str(a): b for a, b in v.items()} if isinstance(v, dict) else None
                    except Exception:                                    # noqa: BLE001
                        pass
    except SyntaxError:
        out['txt_syntax_error'] = True
        m = re.search(r"author\s*=\s*['\"]([^'\"]*)", src)
        if m:
            out['author'] = m.group(1)
    # literal spawn tuples in hooks (report only)
    out['hook_points'] = [tuple(int(t) for t in m) for m in
                          re.findall(r'\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,2})\s*\)', src)][:64] \
        if out.get('has_spawn_hook') else []
    return out


def guess_mode(stem, meta):
    s = stem.lower()
    ext = meta.get('extensions') or {}
    keys = set(ext)
    if any(k.startswith('push_') for k in keys):
        return 'push'
    if any(k.startswith('arena') for k in keys) or 'arena' in s:
        return 'arena'
    if ext.get('babel') or 'babel' in s or 'tower' in s:
        return 'babel'
    if 'push' in s:
        return 'push'
    if any(k.startswith('tow') for k in keys) or 'tow' in s.split('_'):
        return 'tc'
    if 'ffa' in s or 'freeforall' in s:
        return 'ffa'
    if '1v1' in s or 'duel' in s:
        return 'duel'
    return 'ctf'


# ------------------------------------------------------------------ helpers
def unpack(c):
    c = c.astype(np.uint32)
    return np.stack([(c >> 16) & 255, (c >> 8) & 255, c & 255], -1).astype(np.float32)


def luma(rgb):
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def hue_sat(rgb):
    r, g, b = rgb[..., 0] / 255, rgb[..., 1] / 255, rgb[..., 2] / 255
    mx = np.maximum(np.maximum(r, g), b); mn = np.minimum(np.minimum(r, g), b); d = mx - mn
    h = np.zeros_like(mx)
    m = d > 1e-6
    rr = m & (mx == r); gg = m & (mx == g) & ~rr; bb = m & ~rr & ~gg
    h[rr] = ((g - b)[rr] / d[rr]) % 6
    h[gg] = (b - r)[gg] / d[gg] + 2
    h[bb] = (r - g)[bb] / d[bb] + 4
    s = np.where(mx > 0, d / np.maximum(mx, 1e-6), 0)
    return h * 60, s


def surface_mask(solid):
    air = ~solid
    e = np.zeros_like(solid)
    e[:, :, 0] = True
    e[:, :, 1:] |= air[:, :, :-1]; e[:, :, :-1] |= air[:, :, 1:]
    e[1:] |= air[:-1]; e[:-1] |= air[1:]
    e[:, 1:] |= air[:, :-1]; e[:, :-1] |= air[:, 1:]
    return solid & e


# ------------------------------------------------------------------ structures
def structures(solid, color, top, land):
    elev = np.where(land, 63 - top, 0).astype(np.int16)
    ground = ndi.grey_opening(elev, size=(21, 21))
    rise = elev - ground
    obj = land & (rise >= 3)
    lab, n = ndi.label(obj, structure=np.ones((3, 3)))
    if n == 0:
        return {'objects': 0, 'built': [], 'veg': 0}
    slices = ndi.find_objects(lab)
    built, veg = [], 0
    surf = surface_mask(solid)
    for i, sl in enumerate(slices):
        fp = lab[sl] == i + 1
        area = int(fp.sum())
        if area < 12:
            continue
        x0, y0 = sl[0].start, sl[1].start
        g = int(np.median(63 - ground[sl][fp]))           # ground surface z (top voxel of the ground)
        ztop = int(top[sl][fp].min())
        height = g - ztop
        if height < 4:
            continue
        sub = solid[sl[0], sl[1], ztop:g]                  # [x, y, z] above ground
        csub = color[sl[0], sl[1], ztop:g]
        ssub = surf[sl[0], sl[1], ztop:g]
        fp3 = fp[:, :, None]
        vox = sub & fp3
        svox = ssub & fp3
        if svox.sum() < 8:
            continue
        rgb = unpack(csub[svox])
        h, s = hue_sat(rgb)
        green = ((h > 65) & (h < 170) & (s > 0.18)).mean()
        # trunk test: share of the footprint that is solid in the 2 layers just above the ground
        base_cov = float((sub[:, :, -2:].any(axis=2) & fp).sum()) / area
        if green > 0.35 or base_cov < 0.3:
            veg += 1
            continue
        # roofed air: air voxels inside the footprint with solid somewhere above in the same column
        solid_above = np.maximum.accumulate(sub, axis=2)
        roofed_air = (~sub) & solid_above & fp3
        vol = area * height
        indoor = float(roofed_air.sum()) / max(vol, 1)
        # perimeter columns with a hole below the roof (doors / windows / arcades)
        er = fp & ~ndi.binary_erosion(fp)
        per = int(er.sum())
        holes = int(((roofed_air.any(axis=2)) & er).sum())
        # roof form
        tops_fp = top[sl][fp]
        vals, cnt = np.unique(tops_fp, return_counts=True)
        flat_share = float(cnt.max()) / area
        levels = int(len(vals))
        overhang = float((roofed_air[:, :, :].any(axis=2) & er).mean()) if per else 0.0
        # detail: exposed voxels per (perimeter * height + area)
        detail = float(svox.sum()) / max(per * height + area, 1)
        q = (rgb // 8).astype(np.int32)
        ncol = int(len(np.unique(q[:, 0] * 1024 + q[:, 1] * 32 + q[:, 2])))
        L = luma(rgb)
        vrange = float(np.percentile(L, 90) - np.percentile(L, 10))
        # base course: colour of the lowest 2 layers vs the wall band 3..6 above ground
        zz = np.nonzero(svox)[2]
        lowband = rgb[zz >= (g - ztop) - 2]
        wall = rgb[(zz < (g - ztop) - 2) & (zz >= (g - ztop) - 7)]
        base_course = float(np.abs(lowband.mean(0) - wall.mean(0)).sum()) if len(lowband) > 4 and len(wall) > 4 else 0.0
        # roof colour vs wall colour
        topz = np.argmax(sub | ~fp3, axis=2)
        kind = 'mass' if (indoor < 0.03 and holes / max(per, 1) < 0.03 and flat_share < 0.5) else             ('box' if (indoor < 0.03 and holes / max(per, 1) < 0.03) else 'building')
        built.append({'kind': kind, 'base_cov': round(base_cov, 2), 'x': int(x0), 'y': int(y0), 'w': int(fp.shape[0]), 'd': int(fp.shape[1]), 'area': area,
                      'h': height, 'indoor': round(indoor, 3), 'holes_per_perim': round(holes / max(per, 1), 3),
                      'flat_roof_share': round(flat_share, 3), 'roof_levels': levels, 'overhang': round(overhang, 3),
                      'detail': round(detail, 3), 'colours': ncol, 'value_range': round(vrange, 1),
                      'base_course': round(base_course, 1)})
    return {'objects': int(n), 'built': built, 'veg': veg}


def summarize_built(built):
    allb = [o for o in built if o['area'] >= 24 and o['h'] >= 5]
    kinds = {k: sum(o['kind'] == k for o in allb) for k in ('building', 'box', 'mass')}
    b = [o for o in allb if o['kind'] == 'building']
    if not b:
        return {'n': 0, 'kinds': kinds}
    a = lambda k: np.array([o[k] for o in b], float)                          # noqa: E731
    solid_box = ((a('indoor') < 0.04) & (a('holes_per_perim') < 0.02)).mean()
    return {'n': len(b), 'kinds': kinds, 'box_share': round(kinds['box'] / max(kinds['box'] + kinds['building'], 1), 3),
            'median_area': float(np.median(a('area'))), 'median_h': float(np.median(a('h'))),
            'indoor_p50': round(float(np.median(a('indoor'))), 3),
            'holes_p50': round(float(np.median(a('holes_per_perim'))), 3),
            'flat_roof_p50': round(float(np.median(a('flat_roof_share'))), 3),
            'roof_levels_p50': float(np.median(a('roof_levels'))),
            'detail_p50': round(float(np.median(a('detail'))), 3),
            'colours_p50': float(np.median(a('colours'))), 'value_range_p50': round(float(np.median(a('value_range'))), 1),
            'base_course_p50': round(float(np.median(a('base_course'))), 1),
            'solid_box_share': round(float(solid_box), 3)}


# ------------------------------------------------------------------ spawns
def spawn_columns(mode, meta, land, top):
    """-> {team: (xs, ys)} candidate spawn columns according to the server's rule for this mode."""
    ext = meta.get('extensions') or {}
    def rect(x0, x1, y0, y1, need_land=True):
        xs, ys = np.meshgrid(np.arange(max(x0, 0), min(x1, 511) + 1), np.arange(max(y0, 0), min(y1, 511) + 1),
                             indexing='ij')
        xs, ys = xs.ravel(), ys.ravel()
        if need_land:
            k = land[xs, ys]
            if k.any():
                xs, ys = xs[k], ys[k]
        return xs, ys
    if mode == 'babel':
        return {'t1': rect(98, 138, 236, 276, False), 't2': rect(374, 414, 236, 276, False)}, 'babel +-20'
    if mode == 'push':
        r = int(ext.get('push_spawn_range', 5))
        out = {}
        for t, k in (('t1', 'push_blue_spawn'), ('t2', 'push_green_spawn')):
            p = ext.get(k)
            if p and len(p) >= 2:
                out[t] = rect(int(p[0]) - r, int(p[0]) + r, int(p[1]) - r, int(p[1]) + r, False)
        return (out, f'push +-{r}') if out else (None, 'push without spawns')
    if mode == 'arena':
        out = {}
        for t, k in (('t1', 'arena_blue_spawns'), ('t2', 'arena_green_spawns')):
            pts = ext.get(k) or ((ext.get(k[:-1]),) if ext.get(k[:-1]) else ())
            pts = [p for p in pts if p and len(p) >= 2]
            if pts:
                out[t] = (np.array([int(p[0]) for p in pts]), np.array([int(p[1]) for p in pts]))
        return (out, 'arena points') if out else (None, 'arena without spawns')
    if meta.get('has_spawn_hook'):
        return None, 'custom get_spawn_location hook (not executed)'
    if mode == 'ffa':
        return {'all': rect(0, 511, 0, 511)}, 'ffa any land'
    return {'t1': rect(0, 127, 128, 383), 't2': rect(384, 511, 128, 383)}, 'ctf/tdm default team strip'


def walkable_out(top, land, srcs, target_mask, max_drop=9):
    """2D top-surface flood fill: step up <= 1, drop <= max_drop. Share of source cells that reach target_mask."""
    elev = np.where(land, 63 - top, -99).astype(np.int16)
    # reverse search from the target: a cell is 'good' if it can reach a good neighbour
    good = target_mask & land
    frontier = good.copy()
    for _ in range(600):
        new = np.zeros_like(good)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = np.roll(np.roll(frontier, dx, 0), dy, 1)          # neighbour is good -> can I step onto it?
            nb_e = np.roll(np.roll(np.where(frontier, elev, -99), dx, 0), dy, 1)
            ok = nb & land & ~good & (nb_e - elev <= 1) & (elev - nb_e <= max_drop)
            new |= ok
        if not new.any():
            break
        good |= new
        frontier = new
    xs, ys = srcs
    return float(good[xs, ys].mean()) if len(xs) else None


def spawn_metrics(mode, meta, solid, top, land, ground_rise):
    cols, rule = spawn_columns(mode, meta, land, top)
    res = {'rule': rule}
    if not cols:
        return res
    mid = np.zeros((512, 512), bool); mid[200:312, 160:352] = True
    elev = (63 - top).astype(np.int16)
    for t, (xs, ys) in cols.items():
        if len(xs) == 0:
            continue
        r = {}
        r['columns'] = int(len(xs))
        r['water_share'] = round(float((top[xs, ys] >= 62).mean()), 3)
        r['object_top_share'] = round(float((ground_rise[xs, ys] >= 3).mean()), 3)      # roofs, trees, rocks
        # roofed spawn: solid voxel below the top with an air gap under it (spawning on an overhang/roof)
        gap = []
        for x, y in zip(xs[:4000], ys[:4000]):
            c = solid[x, y, :63]
            z = top[x, y]
            run = c[z:]
            gap.append(bool((~run).any()))
        r['air_below_share'] = round(float(np.mean(gap)), 3)
        if mode != 'arena':
            e = elev
            dz = np.maximum(np.abs(np.diff(e, axis=0, prepend=e[:1])), np.abs(np.diff(e, axis=1, prepend=e[:, :1])))
            r['roughness'] = round(float(dz[xs, ys].mean()), 2)
            r['steep_share'] = round(float((dz[xs, ys] >= 2).mean()), 3)
            r['walk_out_share'] = round(walkable_out(top, land, (xs[::7], ys[::7]), mid) or 0, 3)
        # nearby cover: share of spawn columns with a 3+ rise within 8 voxels
        cover = ndi.maximum_filter((ground_rise >= 3).astype(np.uint8), size=17) > 0
        r['cover_within_8'] = round(float(cover[xs, ys].mean()), 3)
        res[t] = r
    return res


# ------------------------------------------------------------------ colour
def colour_metrics(solid, color, top, land):
    xs, ys = np.nonzero(land)
    c = color[xs, ys, top[xs, ys]]
    rgb = unpack(c)
    L = luma(rgb)
    mx = rgb.max(1)
    full = np.zeros((512, 512), np.float32); full[xs, ys] = L
    lm = land.copy()
    def dl(k):
        a = np.abs(full[k:] - full[:-k])[lm[k:] & lm[:-k] & (top[k:] == top[:-k])]
        b = np.abs(full[:, k:] - full[:, :-k])[lm[:, k:] & lm[:, :-k] & (top[:, k:] == top[:, :-k])]
        v = np.concatenate([a, b]); return float(v.mean()) if v.size else float('nan')
    d1, d4 = dl(1), dl(4)
    q = (rgb // 4).astype(np.int64)
    return {'top_colours': int(len(np.unique(q[:, 0] * 4096 + q[:, 1] * 64 + q[:, 2]))),
            'luma_p10': round(float(np.percentile(L, 10)), 1), 'luma_p50': round(float(np.percentile(L, 50)), 1),
            'luma_p90': round(float(np.percentile(L, 90)), 1), 'white_share': round(float((mx >= 235).mean()), 3),
            'dark_share': round(float((L < 40).mean()), 3), 'neighbour_jump': round(d1, 2),
            'coherence_4': round(d4 / d1, 2) if d1 > 1e-6 else None}


# ------------------------------------------------------------------ one map
def analyse(path, cache_dir):
    stem = os.path.splitext(os.path.basename(path))[0]
    cp = os.path.join(cache_dir, stem + '.json')
    if os.path.exists(cp):
        try:
            r = json.load(open(cp))
            if r.get('code') == CODE_VERSION:
                return r
        except Exception:                                                     # noqa: BLE001
            pass
    t0 = time.time()
    res = {'map': stem, 'code': CODE_VERSION, 'bytes': os.path.getsize(path)}
    try:
        from aosmap.kit.codec import decode
        data = open(path, 'rb').read()
        solid, color, colored = decode(data)
    except Exception as e:                                                    # noqa: BLE001
        res['error'] = repr(e)[:200]
        json.dump(res, open(cp, 'w'))
        return res
    meta = read_txt(os.path.splitext(path)[0] + '.txt')
    res['meta'] = {k: meta.get(k) for k in ('name', 'author', 'fog', 'has_spawn_hook', 'has_entity_hook', 'has_txt')}
    res['meta']['ext_keys'] = sorted((meta.get('extensions') or {}).keys())
    mode = guess_mode(stem, meta)
    res['mode'] = mode
    s63 = solid[:, :, :63]
    land = solid[:, :, 62]
    top = np.where(s63.any(axis=2), np.argmax(s63, axis=2), 63)
    res['land_share'] = round(float(land.mean()), 3)
    # geometry fingerprint for dedupe
    small = (63 - top[::8, ::8]).astype(np.uint8)
    res['fp'] = zlib.crc32(small.tobytes())
    try:
        return _analyse_body(res, solid, color, meta, mode, top, land, cp, t0)
    except Exception as e:                                                    # noqa: BLE001
        res['error'] = 'analysis: ' + repr(e)[:200]
        json.dump(res, open(cp, 'w'), default=float)
        return res


def _analyse_body(res, solid, color, meta, mode, top, land, cp, t0):
    elev = np.where(land, 63 - top, 0).astype(np.int16)
    ground = ndi.grey_opening(elev, size=(21, 21))
    rise = elev - ground
    st = structures(solid, color, top, land)
    res['structures'] = summarize_built(st['built'])
    res['structures']['veg_objects'] = st['veg']
    res['structures']['all_objects'] = st['objects']
    # keep the 6 biggest built objects for exemplar look-ups
    res['built_top'] = sorted(st['built'], key=lambda o: -o['area'] * o['h'])[:6]
    res['spawns'] = spawn_metrics(mode, meta, solid, top, land, rise)
    res['colour'] = colour_metrics(solid, color, top, land)
    res['seconds'] = round(time.time() - t0, 1)
    json.dump(res, open(cp, 'w'), default=float)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('folder')
    ap.add_argument('--out', default=os.path.join(ROOT, 'out', 'craft_study'))
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--only', default='')
    a = ap.parse_args(argv)
    cache = os.path.join(a.out, 'cache'); os.makedirs(cache, exist_ok=True)
    paths = sorted(glob.glob(os.path.join(a.folder, '*.vxl')))
    paths = [p for p in paths if '.manual.' not in os.path.basename(p)]     # editor autosaves
    if a.only:
        want = set(a.only.split(','))
        paths = [p for p in paths if os.path.splitext(os.path.basename(p))[0] in want]
    if a.limit:
        paths = paths[:a.limit]
    t0 = time.time()
    rows = []
    with ProcessPoolExecutor(a.workers) as ex:
        for i, r in enumerate(ex.map(analyse, paths, [cache] * len(paths), chunksize=2)):
            rows.append(r)
            if i % 50 == 0:
                print(f'{i}/{len(paths)} {time.time() - t0:.0f}s', flush=True)
    json.dump(rows, open(os.path.join(a.out, 'metrics.json'), 'w'), default=float)
    print('done', len(rows), f'{time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
