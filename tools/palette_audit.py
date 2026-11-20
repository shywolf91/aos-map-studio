"""Audit the colour palette of finished VXL maps against the owner's rules and the palette guide.

What it measures on the TOP surface (what a player mostly sees; z = 63 backdrop excluded) and on all surface voxels:
  value_bands      % of top surface in Rec.601 luma bands <40 | 40-90 | 90-150 | 150-190 | >=190
  dominant         the most common top colour family (OKLab quantised) and its share ("which colour fills the view")
  snow_share       % of top surface that is snow-like (light, low chroma)
  over_cap         % of snow-like top voxels whose max channel > 212 (owner "too white" cap)   -> want 0
  dark_top         % of top voxels with luma < 40 (owner floor rule; also counts dark canopies and roofs)
  brightest_share  % of top surface in the map's brightest 10 luma units band (crest coverage; guide: keep small)
  sparkle          isolated bright top voxels per 10k land columns (bright single voxels flicker in motion)
  hue_families     30-degree OKLCH hue bins (+ neutral bin) covering 90 % of the surface
  fog checks       if the map's .txt is next to it (or --fog r,g,b): brightness, hue clash, team lean, near-match
Usage:
  python tools/palette_audit.py maps/x_v1/x.vxl [more.vxl ...] [--fog 168,164,178] [--json out.json]
"""
import argparse
import ast
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aosmap.vxl import load, surface_mask  # noqa: E402
from aosmap import palette as P  # noqa: E402


def rgb_arr(col):
    col = col.astype(np.uint32)
    return np.stack([(col >> 16) & 255, (col >> 8) & 255, col & 255], -1).astype(np.float64)


def read_fog(vxl_path):
    txt = os.path.splitext(vxl_path)[0] + '.txt'
    if not os.path.exists(txt):
        return None
    m = re.search(r'^\s*fog\s*=\s*(\([^)]*\))', open(txt, encoding='utf-8', errors='replace').read(), re.M)
    return tuple(ast.literal_eval(m.group(1)))[:3] if m else None


def audit(path, fog=None):
    m, _ = load(path)
    s = m.solid
    top = np.argmax(s, axis=2)
    land = top < 62
    xs, ys = np.indices(top.shape)
    trgb = rgb_arr(m.color[xs, ys, top] & 0xFFFFFF)[land]
    lu = P.luma(trgb)
    n = max(len(lu), 1)
    res = {'map': os.path.basename(path), 'land_cols': int(land.sum())}
    bands = [0, 40, 90, 150, 190, 256]
    res['value_bands'] = [round(100 * float(((lu >= a) & (lu < b)).sum()) / n, 1) for a, b in zip(bands, bands[1:])]
    lab = P.rgb_to_oklab(trgb)
    q = np.round(lab / np.array([0.05, 0.03, 0.03])).astype(int)
    keys, inv, cnt = np.unique(q, axis=0, return_inverse=True, return_counts=True)
    k = int(cnt.argmax())
    res['dominant'] = P.rgb_hex(trgb[inv.ravel() == k].mean(0))
    res['dominant_share'] = round(100 * float(cnt[k]) / n, 1)
    snow = P.is_snowlike(trgb)
    res['snow_share'] = round(100 * float(snow.sum()) / n, 1)
    res['over_cap'] = round(100 * float((snow & (trgb.max(1) > P.SNOW_MAX_CHANNEL)).sum()) / max(snow.sum(), 1), 1)
    res['dark_top'] = round(100 * float((lu < P.FLOOR_MIN_LUMA).sum()) / n, 2)
    res['max_top_luma'] = round(float(lu.max()), 0) if lu.size else None
    res['brightest_share'] = round(100 * float((lu >= lu.max() - 10).sum()) / n, 1) if lu.size else None
    # sparkle: a top voxel >= 30 luma brighter than all 4 neighbours at the same height (isolated highlight)
    L2 = np.full(top.shape, np.nan)
    L2[land] = lu
    c = L2[1:-1, 1:-1]
    nb = np.stack([L2[2:, 1:-1], L2[:-2, 1:-1], L2[1:-1, 2:], L2[1:-1, :-2]])
    iso = np.all(c - nb >= 30, axis=0) & ~np.isnan(c)
    res['sparkle_per_10k'] = round(1e4 * float(iso.sum()) / max(land.sum(), 1), 1)
    # hue families over all surface voxels (sides included), excluding the z = 63 plane
    surf = surface_mask(s)
    surf[:, :, 63] = False
    argb = rgb_arr(m.color[surf] & 0xFFFFFF)
    lch = P.rgb_to_oklch(argb)
    b = np.where(lch[:, 1] < 0.03, 12, (lch[:, 2] // 30).astype(int))
    bc = np.bincount(b, minlength=13)
    order = np.argsort(bc)[::-1]
    cum = np.cumsum(bc[order]) / max(bc.sum(), 1)
    nfam = int(np.searchsorted(cum, 0.9) + 1)
    names = ['%d-%d' % (i * 30, i * 30 + 30) if i < 12 else 'neutral' for i in order[:nfam]]
    res['hue_families_90'] = nfam
    res['families'] = [f'{nm}:{100 * bc[i] / bc.sum():.0f}%' for nm, i in zip(names, order[:nfam])]
    fog = fog or read_fog(path)
    if fog:
        res['fog'] = list(fog)
        # palette = the 8 most common quantised top colours, as a proxy for the authoring palette
        top8 = np.argsort(cnt)[::-1][:8]
        pal = {f'top#{r + 1}': tuple(trgb[inv.ravel() == i].mean(0)) for r, i in enumerate(top8)}
        rep = P.check_palette(pal, fog=fog)
        res['fog_warnings'] = [w for w in rep.warnings if w.startswith('fog')]
        res['fog_team_lean'] = rep.info.get('fog_team_lean')
    return res


def verdict(r):
    out = []
    if r['over_cap'] > 1 and r['snow_share'] >= 2:
        out.append(f"snow over cap on {r['over_cap']}% of snow")
    if r['dark_top'] > 0.5:
        out.append(f"{r['dark_top']}% top voxels below luma 40 (check which are walkable floors)")
    if r['snow_share'] > 20 and r['brightest_share'] > 15:
        out.append('brightest snow covers too much (crest should be short)')
    if r['sparkle_per_10k'] > 30:
        out.append('many isolated bright voxels (sparkle)')
    if r['hue_families_90'] > 5:
        out.append('more than 5 hue families')
    out += r.get('fog_warnings', [])
    return out or ['ok']


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('vxl', nargs='+')
    ap.add_argument('--fog', help='r,g,b (default: read fog from the .txt beside each map)')
    ap.add_argument('--json')
    a = ap.parse_args()
    fog = tuple(int(v) for v in a.fog.split(',')) if a.fog else None
    rows = [audit(p, fog) for p in a.vxl]
    for r in rows:
        print(f"\n== {r['map']}  (land columns {r['land_cols']})")
        print(f"  value bands <40|40-90|90-150|150-190|190+ : {r['value_bands']}")
        print(f"  dominant {r['dominant']} covers {r['dominant_share']}% | snow {r['snow_share']}% "
              f"(over cap {r['over_cap']}%) | max top luma {r['max_top_luma']} "
              f"(brightest band {r['brightest_share']}%)")
        print(f"  dark tops {r['dark_top']}% | sparkle {r['sparkle_per_10k']}/10k | "
              f"hue families {r['hue_families_90']}: {', '.join(r['families'])}")
        if r.get('fog'):
            print(f"  fog {tuple(r['fog'])}  team lean {r['fog_team_lean']}")
        print('  verdict: ' + '; '.join(verdict(r)))
    if a.json:
        json.dump(rows, open(a.json, 'w'), indent=1)
