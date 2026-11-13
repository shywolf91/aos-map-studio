"""Corpus runner for the Babel zone study (docs/babel_zone_study.md).

Finds the Babel maps in the community collection (read-only), dedupes near-identical geometry, computes
aosmap.kit.zones.zone_profile for every unique map and for our own maps, and writes
out/zone_study/metrics.json + metrics.csv (per-map results cached in out/zone_study/cache/).

    python tools/babel_zone_study.py [--collection D:/.../map_collection] [--updates D:/.../_updates]
        [--out out/zone_study] [--workers 4] [--limit N]

The collection's .txt files are never executed: they are parsed with `ast` (literal values only) or regex.
Nothing is written into the collection.
"""
from __future__ import annotations

import argparse
import ast
import csv
import glob
import json
import os
import re
import sys
import time
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT)
from aosmap.kit import zones  # noqa: E402

CODE_VERSION = 'zones-4'

# Rotation-guide labels (Babel map rotations guide v1.8, aloha.pk; section headings of its "Overview of tested
# maps"). Matched case-insensitively on the file stem. [GUIDE]
GUIDE_GOOD = ['trademas', 'tradeoff', 'tradeoffnight', 'lard', 'crossfire3', 'GoonassaultJapan', 'hezeehills',
              'plateau', 'swampcanyon', 'yarr', 'makewar', 'JoeyRaysBayou', 'swag2', 'newfort', 'skullfort',
              'halongbabel', 'yubacore', 'babelpocalypse', 'yukon', 'nine_eye_babel', 'oasis', 'oasis2', 'normandie',
              'battlefarm', 'bigasssideforts', 'roadisland']
GUIDE_PROBLEM = ['turtlesoup', 'koth', 'HallweebWIP', 'matrix_babel', 'TowerDive', 'summerfields', 'blackwidow',
                 'AtlasNovus', 'pinline', 'pinline2', 'jsweet', 'stackattack', 'winter']
# every map named in one of the guide's rotation strings (rotation membership, weaker than "works fairly well")
GUIDE_ROTATION = ['trademas', 'swag2', 'newfort', 'skullfort', 'icecraft', 'royalparadenight', '1river2forts',
                  'catseyebabel', 'xmasfire2', 'yubacore', 'ruins_onigiri', 'crossfire3', 'halongbabel',
                  'winterwar11', '2keep', 'nine_eye_babel', 'yukon', 'babelpocalypse', 'abridgetoofar', 'hexclimb',
                  'oasis', 'normandie', 'abridgetoodark', 'anticbridgebabelv2', 'dankholes', 'binladenfire3',
                  'cheesus', 'pinpoint2', 'battlefarm', 'godstairs2.0', 'holes', 'bloodgulch2_mirrored', 'icetuga',
                  'waterfrontv2babel', 'frog1.1', 'crossfire2', 'castlesandshit', 'holes_hills', 'oasis2', 'tradeoff',
                  'lard', 'yarr', 'makewar', 'caves', 'hallpoint', 'hezeehills', 'capitol', 'GoonassaultJapan',
                  'hallweebalohabeta', 'roadisland', 'plateau', 'stackattack', 'bigasssideforts', 'koth',
                  'JoeyRaysBayou', 'DriftIce2', 'swampcanyon']
# named in the guide's notes with a verdict but not in the lists above (docs/babel_rotation_guide_notes.md)
GUIDE_NOTED = ['alexandria-babel2', 'alexandria', 'islandbabel', 'halongbay', 'ravenloft', 'hexclimb', 'mazemountain',
               'hiesville', 'alpine', 'chute', 'bridgeyard', 'babelstairs', 'turv', 'pincushion', '1river2white',
               'pincushion2.0']

UPD = 'D:/Ace of Spades/Aos_Map/_updates'
OURS = [  # (name, path relative to repo or absolute, benchmark)
    ('Silverpine Hunt v2.2', UPD + '/silverpine_hunt_v2_2/maps/silverpine_hunt_v2_2/silverpine_hunt.vxl', True),
    ("Wicker King's Harvest v1.1", 'maps/wicker_kings_harvest_v1_1/wicker_kings_harvest.vxl', True),
    ('Frostbell Hollow v1.1', 'maps/frostbell_hollow_v1_1/frostbell_hollow.vxl', False),
    ('The Hollow Crown v1.1', 'maps/the_hollow_crown_v1_1/the_hollow_crown.vxl', False),
    ('Graveyard of the Forgotten v1.0', 'maps/graveyard_of_the_forgotten_v1/graveyard_of_the_forgotten.vxl', False),
    ('Bloomhop Kingdom v1.0', UPD + '/bloomhop_kingdom_v1/bloomhop_kingdom_v1/bloomhop_kingdom.vxl', False),
    ('Witchwood Isles v1.0', UPD + '/witchwood_isles_v1_0/witchwood_isles_v1_0/map/witchwood_isles.vxl', False),
    ('Haunted Fairground v1.3', UPD + '/haunted_fairground_v1_3/haunted_fairground.vxl', False),
    ('Drowned Cathedral v2', 'maps/drowned_cathedral_v2/drowned_cathedral_v2.vxl', False),
    ('Hollowfen Vale v1', 'maps/hollowfen_vale_v1/hollowfen_vale.vxl', False),
    ('Hollowfen (art v1)', 'maps/hollowfen_art_v1/hollowfen.vxl', False),
    ('Kestrel Spires (art v3)', 'maps/kestrel_spires_art_v3/kestrel_spires.vxl', False),
]


# =============================================================================================== .txt parsing

def parse_txt(path):
    """Literal metadata of a map .txt without executing it."""
    out = {'parsed': False}
    try:
        src = open(path, 'rb').read().decode('utf-8', 'replace')
    except OSError:
        return out
    out['functions'] = sorted(set(re.findall(r'^\s*def\s+(\w+)', src, re.M)))
    try:
        tree = ast.parse(src)
        out['parsed'] = True
    except SyntaxError:
        tree = None
    vals = {}
    if tree is not None:
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                k = node.targets[0].id
                try:
                    vals[k] = ast.literal_eval(node.value)
                except Exception:
                    if isinstance(node.value, ast.Dict):           # keep the literal keys/values we can read
                        d = {}
                        for kk, vv in zip(node.value.keys, node.value.values):
                            try:
                                key = ast.literal_eval(kk)
                            except Exception:
                                continue
                            try:
                                d[key] = ast.literal_eval(vv)
                            except Exception:
                                d[key] = '<non-literal>'
                        vals[k] = d
    for k in ('name', 'author', 'description'):
        v = vals.get(k)
        if v is None:
            m = re.search(r'^%s\s*=\s*[\'"](.*?)[\'"]' % k, src, re.M)
            v = m.group(1) if m else None
        out[k] = v if isinstance(v, (str, type(None))) else str(v)
    fog = vals.get('fog')
    out['fog'] = list(fog) if isinstance(fog, (tuple, list)) else None
    ext = vals.get('extensions')
    if isinstance(ext, dict):
        out['extension_keys'] = sorted(str(k) for k in ext)
        out['babel'] = ext.get('babel') is True
        wd = ext.get('water_damage')
        out['water_damage'] = wd if isinstance(wd, (int, float)) else None
    else:
        out['extension_keys'] = []
        out['babel'] = bool(re.search(r'[\'"]babel[\'"]\s*:\s*True', src))
        out['water_damage'] = None
    out['spawn_hooks'] = [f for f in out['functions'] if f in ('get_spawn_location', 'get_entity_location')]
    return out


# =============================================================================================== corpus

def find_corpus(coll):
    stems = {}
    for p in glob.glob(os.path.join(coll, '*.vxl')):
        stems[os.path.splitext(os.path.basename(p))[0]] = p
    low = {s.lower(): s for s in stems}
    named = {n.lower() for n in GUIDE_GOOD + GUIDE_PROBLEM + GUIDE_ROTATION + GUIDE_NOTED}
    rows, ours_in_coll = [], []
    for stem, p in sorted(stems.items()):
        txt = os.path.join(coll, stem + '.txt')
        meta = parse_txt(txt) if os.path.exists(txt) else {'parsed': False, 'babel': False, 'extension_keys': []}
        author = (meta.get('author') or '')
        if 'shywolf' in author.lower() or '+ ai' in author.lower():
            ours_in_coll.append(stem)
            continue
        why = []
        if meta.get('babel'):
            why.append('ext')
        if 'babel' in stem.lower() or 'babel' in (meta.get('name') or '').lower() or \
                'babel' in (meta.get('description') or '').lower():
            why.append('name')
        if stem.lower() in named:
            why.append('guide')
        if why:
            rows.append({'stem': stem, 'path': p, 'meta': meta, 'why': why})
    missing = sorted(n for n in named if n not in low)
    return rows, ours_in_coll, missing


def labels_for(stem):
    s = stem.lower()
    lab = []
    if s in {n.lower() for n in GUIDE_GOOD}:
        lab.append('guide_good')
    if s in {n.lower() for n in GUIDE_PROBLEM}:
        lab.append('guide_problem')
    if s in {n.lower() for n in GUIDE_ROTATION}:
        lab.append('guide_rotation')
    return lab


# =============================================================================================== per map work

def _cache_key(data):
    return '%08x_%d' % (zlib.crc32(data) & 0xffffffff, len(data))


def tops_job(args):
    """Decode -> (key, tops int16, top rgb) cached as npz."""
    path, cache = args
    data = open(path, 'rb').read()
    key = _cache_key(data)
    f = os.path.join(cache, key + '_top.npz')
    if os.path.exists(f):
        return path, key, len(data), None
    try:
        solid, topc = zones.decode_solid_fast(data)
    except Exception as e:      # noqa: BLE001
        return path, key, len(data), f'decode failed: {e}'
    top = zones.tops(solid)
    rgb = np.stack([(topc >> 16) & 255, (topc >> 8) & 255, topc & 255], -1).astype(np.uint8)
    np.savez_compressed(f, top=top, rgb=rgb)
    return path, key, len(data), None


def profile_job(args):
    path, cache = args
    data = open(path, 'rb').read()
    key = _cache_key(data)
    f = os.path.join(cache, f'{key}_{CODE_VERSION}_zp.json')
    if os.path.exists(f):
        return path, json.load(open(f)), None
    t0 = time.time()
    try:
        solid, _ = zones.decode_solid_fast(data)
        zp = zones.zone_profile(solid)
        zp['class'] = zones.classify(zp)
    except Exception as e:      # noqa: BLE001
        import traceback
        return path, None, f'{type(e).__name__}: {e} | {traceback.format_exc(limit=2)[-300:]}'
    zp['seconds'] = round(time.time() - t0, 1)
    json.dump(zp, open(f, 'w'))
    return path, zp, None


# =============================================================================================== dedupe

def dedupe(items, cache, same_share=0.97):
    """items: list of dicts with 'key', 'stem', 'priority'. Groups maps whose top-z fields agree within 1 block on
    >= same_share of columns (recolours, -snow / -night copies, renamed copies). Representative = highest priority,
    then shortest stem."""
    T = {}
    small = {}
    for it in items:
        z = np.load(os.path.join(cache, it['key'] + '_top.npz'))
        t = z['top'].astype(np.int16)
        T[it['stem']] = t
        small[it['stem']] = t.reshape(64, 8, 64, 8).mean(axis=(1, 3))
    order = sorted(items, key=lambda i: (-i['priority'], len(i['stem']), i['stem']))
    groups = []
    for it in order:
        placed = False
        for g in groups:
            rep = g[0]
            if np.abs(small[rep['stem']] - small[it['stem']]).mean() > 2.0:
                continue
            share = (np.abs(T[rep['stem']] - T[it['stem']]) <= 1).mean()
            if share >= same_share:
                g.append(it)
                placed = True
                break
        if not placed:
            groups.append([it])
    return groups


# =============================================================================================== output

def flatten(d, prefix=''):
    out = {}
    for k, v in d.items():
        kk = f'{prefix}{k}'
        if isinstance(v, dict):
            out.update(flatten(v, kk + '.'))
        elif isinstance(v, list):
            if all(isinstance(x, (int, float)) for x in v) and len(v) <= 4:
                for i, x in enumerate(v):
                    out[f'{kk}.{i}'] = x
        else:
            out[kk] = v
    return out


def csv_row(m):
    zp = m['zone_profile']
    row = {'name': m['name'], 'source': m['source'], 'file': m['file'], 'labels': ';'.join(m.get('labels', [])),
           'aliases': ';'.join(m.get('aliases', [])), 'class': zp['class']['class'], 'assist': zp['class']['assist'],
           'stock_fit': zp['class']['stock_fit'], 'symmetry': zp['map']['symmetry']['type'], 'bytes': m['bytes']}
    f = flatten({'avg': zp['avg']})
    f = {k: v for k, v in f.items() if 'profile_h_every4' not in k and 'anchor_enemy_face.face_x' not in k}
    row.update(f)
    row.update(flatten({'centre': zp['centre'] or {}}))
    row.update(flatten({'routes': zp['routes'] or {}}))
    row.update(flatten({'map': {k: v for k, v in zp['map'].items() if k != 'symmetry'}}))
    return row


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--collection', default='D:/Ace of Spades/Aos_Map/map_collection')
    ap.add_argument('--out', default=os.path.join(ROOT, 'out', 'zone_study'))
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args(argv)
    t0 = time.time()
    cache = os.path.join(a.out, 'cache')
    os.makedirs(cache, exist_ok=True)
    rows, ours_in_coll, missing = find_corpus(a.collection)
    if a.limit:
        rows = rows[:a.limit]
    print(f'{len(rows)} Babel candidates; our maps in the collection skipped: {ours_in_coll}')
    ours = []
    for name, rel, bench in OURS:
        p = rel if os.path.isabs(rel) else os.path.join(ROOT, rel)
        if os.path.exists(p):
            ours.append({'name': name, 'path': p, 'benchmark': bench})
        else:
            print('missing our map', name, p)
    paths = [r['path'] for r in rows] + [o['path'] for o in ours]
    log = {'decode_failed': {}, 'profile_failed': {}}
    keys, sizes = {}, {}
    with ProcessPoolExecutor(a.workers) as ex:
        for path, key, nbytes, err in ex.map(tops_job, [(p, cache) for p in paths]):
            keys[path], sizes[path] = key, nbytes
            if err:
                log['decode_failed'][os.path.basename(path)] = err
    print(f'decoded in {time.time() - t0:.0f}s, failed {len(log["decode_failed"])}')
    items = []
    for r in rows:
        if os.path.basename(r['path']) in log['decode_failed']:
            continue
        lab = labels_for(r['stem'])
        pr = 3 * ('guide_good' in lab) + 3 * ('guide_problem' in lab) + 2 * ('guide_rotation' in lab) + \
            ('guide' in r['why'])
        items.append({'stem': r['stem'], 'key': keys[r['path']], 'priority': pr, 'row': r})
    groups = dedupe(items, cache)
    print(f'{len(items)} decoded -> {len(groups)} unique after dedupe ({time.time() - t0:.0f}s)')
    reps = [g[0] for g in groups]
    todo = [g['row']['path'] for g in reps] + [o['path'] for o in ours]
    prof = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for i, (path, zp, err) in enumerate(ex.map(profile_job, [(p, cache) for p in todo])):
            if err:
                log['profile_failed'][os.path.basename(path)] = err
            else:
                prof[path] = zp
            if (i + 1) % 20 == 0:
                print(f'  profiled {i + 1}/{len(todo)} ({time.time() - t0:.0f}s)', flush=True)
    maps = []
    for g in groups:
        r = g[0]['row']
        if r['path'] not in prof:
            continue
        labs = set()
        for it in g:
            labs.update(labels_for(it['stem']))
        maps.append({'name': r['stem'], 'source': 'community', 'file': os.path.basename(r['path']),
                     'bytes': sizes[r['path']], 'why': r['why'], 'labels': sorted(labs),
                     'aliases': [it['stem'] for it in g[1:]],
                     'meta': {k: r['meta'].get(k) for k in ('name', 'author', 'fog', 'extension_keys', 'babel',
                                                            'water_damage', 'spawn_hooks', 'parsed')},
                     'zone_profile': prof[r['path']]})
    for o in ours:
        if o['path'] not in prof:
            continue
        txt = glob.glob(os.path.join(os.path.dirname(o['path']), '*.txt'))
        meta = parse_txt(txt[0]) if txt else {}
        maps.append({'name': o['name'], 'source': 'ours', 'benchmark': o['benchmark'], 'file': o['path'],
                     'bytes': sizes[o['path']], 'labels': ['benchmark'] if o['benchmark'] else [],
                     'meta': {k: meta.get(k) for k in ('name', 'author', 'fog', 'extension_keys', 'babel',
                                                       'water_damage', 'spawn_hooks', 'parsed')},
                     'zone_profile': prof[o['path']], 'cache_key': keys[o['path']]})
    for m in maps:
        if m['source'] == 'community':
            m['cache_key'] = keys[os.path.join(a.collection, m['file'])]
    res = {'generated_by': 'tools/babel_zone_study.py', 'code_version': CODE_VERSION,
           'collection': a.collection, 'n_candidates': len(rows), 'n_decoded': len(items), 'n_unique': len(groups),
           'our_maps_in_collection_skipped': ours_in_coll, 'guide_names_not_in_collection': missing,
           'log': log, 'runtime_s': round(time.time() - t0, 1), 'maps': maps}
    json.dump(res, open(os.path.join(a.out, 'metrics.json'), 'w'), indent=1)
    rows_csv = [csv_row(m) for m in maps]
    cols = []
    for r in rows_csv:
        for k in r:
            if k not in cols:
                cols.append(k)
    with open(os.path.join(a.out, 'metrics.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(rows_csv)
    print(f'wrote {len(maps)} maps; profile failures {len(log["profile_failed"])}; {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
