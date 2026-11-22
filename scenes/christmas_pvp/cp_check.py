"""Christmas PVP v2 validation: the kit Babel suite (with the assist trees) plus rework-specific evidence:
spawn exposure before/after, voxel diff against the original, new floating voxels, mirror of the additions,
colour statistics and glow / .txt facts. Writes OUTDIR/validation.json.

    python scenes/christmas_pvp/cp_check.py OUTDIR
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..'))

from aosmap.kit import babel_checks, build, codec, palette  # noqa: E402
from aosmap.kit.params import BABEL_DEFAULT  # noqa: E402
from aosmap import sightline  # noqa: E402

from cp_spec import SPEC  # noqa: E402

# Inherited from the original and kept by the owner's "light rework" (~90 % same) decision; the rows still print
# their measured numbers (status 'waived').
WAIVERS = {
    'floating': 'inherited: 1 419 floating pieces of the Minecraft export (wall paintings, coaster decor, ornaments); '
                'this rework adds none (see rework.new_floating_voxels)',
    'mirror': 'inherited asymmetry of the original (PLAY letters, ? block, corner props); the additions are exact '
              'x512 mirrors (rework.additions_mirror_mismatch)',
    'platform_ends': 'owner decision 2026-11-22: the giant trees under both platform ends stay as assist structures',
    'spawn_squares': 'inherited: the arena floor is at z 62 (water level for the kit); spawn squares unchanged',
    'traps': 'inherited pockets in the wall terraces of the original; no new trap cells near the additions',
    'anchor_face': 'owner decision 2026-11-22: the giant trees are the climbable assists (Babel with assist structures)',
    'under_platform': 'owner decision 2026-11-22: giant trees under the platform kept unchanged',
}


ZONE_SKIP = {'front_dressing': 'model does not fit: the arena floor is z 62, which the kit counts as water, so free '
                               'ground reads as 0 and the band is "land" only where objects stand (original: N/A). '
                               'Forced numbers before/after are in rework.front_forced; the cover firs are 18 tall '
                               'walk-under trees (owner chose lit trees as light cover)'}


def front_forced(data, solid):
    import cp_source
    R = babel_checks.run_all(data, terrain_H=None, pyspades=False, zone_profile=False,
                             zone_rules={'applicable_land_min': 0.0})
    fd = R['zone_rules']['front_dressing']
    return {'status': fd['status'], 'avg': fd.get('avg')}


def traps_original(src, s0):
    import cp_source
    R = babel_checks.run_all(src, terrain_H=cp_source.ground_estimate(s0), pyspades=False, zone_profile=False,
                             zone_rules=False)
    return R['trap_cells']


def crest_gaps(solid, pz=1):
    out = {}
    for name, (x0, x1, y0, y1) in SPEC['assist_trees'].items():
        sub = solid[x0:x1 + 1, y0:y1 + 1, :57]
        zs = np.nonzero(sub.any((0, 1)))[0]
        crest = int(zs.min())
        out[name] = {'crest_z': crest, 'blocks_from_crest_to_platform_level': crest - (pz + 1)}
    return out


def floating_mask(solid):
    lab, n = ndi.label(solid, structure=ndi.generate_binary_structure(3, 1))
    grounded = np.zeros(n + 1, bool)
    grounded[np.unique(lab[:, :, 63])] = True
    grounded[0] = True
    return ~grounded[lab]


def clusters(mask, limit=40):
    lab, n = ndi.label(mask, structure=ndi.generate_binary_structure(3, 3))
    out = []
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        out.append({'voxels': int((lab[sl] == i).sum()), 'x': [sl[0].start, sl[0].stop - 1],
                    'y': [sl[1].start, sl[1].stop - 1], 'z': [sl[2].start, sl[2].stop - 1]})
    out.sort(key=lambda r: -r['voxels'])
    return {'clusters': n, 'list': out[:limit]}


def colour_stats(solid, rgb, glow_keys=None):
    top = np.argmax(solid, axis=2)
    xs, ys = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    arena = (xs >= 92) & (xs <= 420) & (ys >= 133) & (ys <= 380)
    t = rgb[xs, ys, top][arena].astype(float)
    L = palette.luma(t)
    surf = codec.surface_mask(solid)
    s = rgb[surf].astype(float)
    res = {'top_luma_p10': round(float(np.percentile(L, 10)), 1), 'top_luma_p50': round(float(np.median(L)), 1),
           'top_luma_p90': round(float(np.percentile(L, 90)), 1),
           'top_luma_spread_p90_p10': round(float(np.percentile(L, 90) - np.percentile(L, 10)), 1),
           'top_dark_lt40_pct': round(100 * float((L < 40).mean()), 2),
           'top_maxch_gt212_pct': round(100 * float((t.max(-1) > 212).mean()), 2),
           'surface_maxch_gt212_pct': round(100 * float((s.max(-1) > 212).mean()), 2)}
    if glow_keys is not None:
        g = np.zeros(solid.shape, bool)
        if glow_keys:
            k = np.array(list(glow_keys))
            g[k[:, 0], k[:, 1], k[:, 2]] = True
        tg = g[xs, ys, top][arena]
        res['top_maxch_gt212_pct_excl_glow_lit'] = round(100 * float((t[~tg].max(-1) > 212).mean()), 2)
        res['surface_maxch_gt212_pct_excl_glow_lit'] = round(100 * float((s[~g[surf]].max(-1) > 212).mean()), 2)
    return res


def exposure(solid):
    return {k: {kk: v[kk] for kk in ('exposed_pct', 'mean_viewers_per_point')}
            for k, v in sightline.babel_spawn_report(solid).items()}


def map_file(out):
    import glob
    v = sorted(glob.glob(os.path.join(out, '*.vxl')))
    assert len(v) == 1, f'expected one .vxl in {out}'
    return os.path.splitext(os.path.basename(v[0]))[0]


RECOLOR_WAIVERS = {
    'spawn_exposure_blue': 'owner choice 2026-11-22: recolour-only variant keeps the original geometry (no cover)',
    'spawn_exposure_red': 'owner choice 2026-11-22: recolour-only variant keeps the original geometry (no cover)',
}


def run(out):
    fname = map_file(out)
    vx = os.path.join(out, fname + '.vxl')
    data = open(vx, 'rb').read()
    bj = json.load(open(os.path.join(out, 'build.json')))
    mat = np.load(os.path.join(out, 'mat.npy'))
    H = np.load(os.path.join(out, 'terrain_H.npy'))
    assist = {k: tuple(v) for k, v in SPEC['assist_trees'].items()}
    wv = dict(WAIVERS, **(RECOLOR_WAIVERS if bj.get('build_variant') == 'recolor' else {}))
    R = babel_checks.run_all(data, build=bj, mat=mat, terrain_H=H, axis=SPEC['axis'], assist=assist,
                             waivers=wv, zone_rules_skip=ZONE_SKIP)
    R['summary'] = babel_checks.summary(R)
    solid, color, _ = codec.decode(data)
    rgb = codec.unpack_rgb(color)
    src = open(SPEC['source'], 'rb').read()
    s0, c0, _ = codec.decode(src)
    rgb0 = codec.unpack_rgb(c0)
    added, removed = solid & ~s0, s0 & ~solid
    fl0, fl1 = floating_mask(s0), floating_mask(solid)
    mx = added[::-1]
    mx = np.roll(mx, 1, axis=0)                        # x512 mirror: index x -> 512 - x
    txt = os.path.join(out, fname + '.txt')
    from aosmap import meta
    mod = meta.check_map_txt(txt)
    stored = mod.extensions.get('glow_stored_colors', {})
    surf0, surf1 = codec.surface_mask(s0), codec.surface_mask(solid)
    common = surf0 & surf1
    R['rework'] = {
        'source_sha256': build.sha256(src),
        'geometry_identical_to_original': bool(np.array_equal(solid, s0)),
        'voxel_diff': {'added': int(added.sum()), 'removed': int(removed.sum()),
                       'added_where': clusters(added), 'removed_where': clusters(removed),
                       'unchanged_solid_pct': round(100 * float((s0 & solid).sum() / s0.sum()), 3),
                       'recoloured_surface_pct': round(100 * float((np.any(rgb0 != rgb, -1) & common).sum()
                                                                   / common.sum()), 2)},
        'new_floating_voxels': int((fl1 & ~fl0).sum()),
        'floating_voxels_before_after': [int(fl0.sum()), int(fl1.sum())],
        'additions_mirror_mismatch': int((added & ~mx).sum()),
        'additions_inside_spawn_squares': int(added[98:139, 236:277].sum() + added[374:415, 236:277].sum()),
        'additions_in_platform_volume': int(added[206:306, 240:272, 0:3].sum()),
        'spawn_exposure_before': exposure(s0),
        'spawn_exposure_after': exposure(solid),
        'colour_before': colour_stats(s0, rgb0),
        'colour_after': colour_stats(solid, rgb, set(stored.keys()) if stored else set()),
        'glow': {'sources': sum(1 for k, v in stored.items() if tuple(v) in {tuple(c) for c in SPEC['glow_palette'].values()} and tuple(rgb[k]) == tuple(v)),
                 'stored_entries': len(stored), 'txt_bytes': os.path.getsize(txt)},
        'txt_check': build.check_txt(txt),
        'assist_crest_gap': crest_gaps(solid),
        'trap_cells_original_same_model': traps_original(src, s0),
        'front_forced': {'before': front_forced(src, s0), 'after': front_forced(data, solid)},
    }
    with open(os.path.join(out, 'validation.json'), 'w') as f:
        json.dump(R, f, indent=1, default=str)
    for row in R['summary']:
        print(babel_checks.format_row(row))
    print(json.dumps({k: R['rework'][k] for k in R['rework'] if k != 'voxel_diff'}, indent=1, default=str)[:4000])
    print(json.dumps({k: v for k, v in R['rework']['voxel_diff'].items() if 'where' not in k}))
    print('assist:', json.dumps(R.get('assist_structures'), default=str))
    print('summary rows:', [(r.get('key', r['rule'][:30]), r.get('status', r['ok'])) for r in R['summary']])
    return R


if __name__ == '__main__':
    run(sys.argv[1])
