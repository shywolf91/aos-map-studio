"""Island-style metrics: how "classic" (community island Babel) vs "current" (our dense house style) a map is.

Usage:
    python tools/island_style_metrics.py <map.vxl> [more.vxl ...] [--json out.json]

Every number this tool prints is a [RUN] measurement of the file it was given. The "classic ranges" at the bottom
are [DERIVED] from four community island maps (islandbabel, toast, utopia2, babelpocalypse; measured 2026-11-15)
and contrasted against our own yulehaven_isles (the "current" style). See docs/classic_island_style.md.
Reference maps are third-party: measure them locally, never copy them into the repo.

Definitions (z = 0 is the sky top, z = 63 the bottom):
  ground top     per column, the top of the solid run that reaches z 63 (the "bottom run"). Overhangs, roofs,
                 canopies, bridges and floating sky decor sit above an air gap and are NOT ground.
  water column   ground top == 63, i.e. z 62 is air. This is the engine's definition of water ([SRC] pyspades:
                 a column whose z 62 is air; see docs/vxl_and_runtime_reference.md). All five measured maps store
                 the sea as a painted z 63 layer, and every column whose ground top is z 62 or higher was sand,
                 dirt, rock or snow, never painted water (checked 2026-11-15) - so z 62 counts as land (a 1-high beach).
  land           ground top <= 62.  height h = 63 - ground top (0 = sea level).
  landmass       4-connected land columns. Moored ships whose hull reaches z 62 count as (tiny) land too; the
                 landmass count therefore uses a minimum size (LANDMASS_MIN columns).
  terrain        grey opening of the height field with a TERRAIN_WINDOW square window: removes anything narrower
                 than the window (trunks, huts, houses, walls, towers) and keeps broad landforms. Slopes, cliffs and
                 the shore profile are measured on this terrain, not on the raw ground top.
  floating       solid components (6-face) not connected to z >= 62 = sky decor (clouds, planes, birds, tags) or
                 errors. Reported separately and excluded from the structure proxy.
  structure proxy  grounded solid voxels at least 2 above the terrain, grouped into 6-connected components of
                 >= STRUCT_MIN voxels. It counts buildings, ships, bridges, trees, rocks and fences ALIKE - it is a
                 measure of how much authored stuff stands on the land, not a building count. A large terrain
                 feature narrower than the window (a sea stack, a narrow ridge) also lands here.
  roofed columns land columns where some grounded solid sits above an air gap (roofs, canopies, bridges, arches).

Hue families: 30-degree hue bins + one grey bin (saturation < 0.12) covering 90 % of the authored surface (all
surface voxels except the z 63 sea plane and floating pieces) - same binning as tools/art_metrics.py.
"""
import argparse
import json
import os
import sys

import numpy as np
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from aosmap.vxl import load, surface_mask  # noqa: E402
from art_metrics import hue_bins, rgb_of, srgb_to_L  # noqa: E402

LANDMASS_MIN = 200        # columns; smaller land bits (ship hulls, rocks, buoys) are listed as "specks"
TERRAIN_WINDOW = 17       # columns; grey-opening window that separates landforms from props/buildings
STRUCT_MIN = 20           # voxels; smaller above-terrain components are ignored as litter/noise
FACE6 = ndimage.generate_binary_structure(3, 1)

# Stock Babel geometry (piqueserver 1.4.2 babel_script; knowledge base section 7.1) - parameters, not truths.
SPAWN_BLUE = (98, 138, 236, 276)       # x0, x1, y0, y1 inclusive
SPAWN_RED = (374, 414, 236, 276)
PLATFORM = (206, 305, 240, 271)
PLAT_END_BLUE = (206, 211, 240, 271)
PLAT_END_RED = (300, 305, 240, 271)
CENTRE_ZONE = (81, 431, 156, 356)      # owner's "centre combat zone" (knowledge base section 8.2)

# ---------------------------------------------------------------------------------------------------------------
# Classic target ranges [DERIVED] from the four classic references measured with THIS tool on 2026-11-15
# (islandbabel, toast, utopia2, babelpocalypse). lo/hi = the refs' envelope, rounded outward a little.
# 'separates' records whether yulehaven_isles (current style, the only contrast map measured) falls outside the
# range. Only those metrics are style targets; 'info' rows are printed for context and must not be read as a style
# test. One contrast map is thin evidence: re-derive the ranges when more maps of either style are measured.
# Measured envelopes (classic refs -> yulehaven) are in docs/classic_island_style.md.
# ---------------------------------------------------------------------------------------------------------------
CLASSIC_RANGES = [
    # key,                      lo,    hi,    separates, note
    ('water_pct',               68.0,  84.0,  True,  'sea share of the 512x512 columns (refs 70.8-80.6; weak)'),
    ('landmasses',               1,    10,    True,  f'landmasses >= {LANDMASS_MIN} columns (refs 1-9)'),
    ('main_neck_min_y_width',   40,   150,    True,  'narrowest y extent of the main island, middle third (refs 47-142)'),
    ('struct_components',        0,    90,    True,  f'above-terrain components >= {STRUCT_MIN} voxels (refs 46-72)'),
    ('struct_vox_per_land_col',  0.0,   1.8,  True,  'above-terrain grounded voxels per land column (refs 0.33-1.69)'),
    ('roofed_pct',               0.0,  13.0,  True,  '% land columns under a roof/canopy/bridge (refs 5.3-10.2)'),
    ('surface_colours',          0, 26000,    True,  'unique authored surface colours, sea excluded (refs 1962-22414)'),
    ('hue_families_90',          1,     4,    True,  'hue bins covering 90 % of the authored surface (refs 1-4)'),
    ('main_share_pct',          85.0, 100.0,  False, 'share of land in the largest landmass (refs 86.5-100)'),
    ('main_aspect_x_over_y',     1.6,   2.6,  False, 'main island bbox width (x) / height (y) (refs 1.71-2.47)'),
    ('terrain_slope',            0.0,   0.3,  False, 'mean |dh| between 4-neighbours on terrain (refs 0.02-0.26)'),
    ('cliff_pct',                0.0,   0.5,  False, '% terrain neighbour steps >= 3 (refs 0-0.38)'),
    ('struct_footprint_pct_of_land', 0.0, 40.0, False, '% land columns under structure (refs 7.6-38.7)'),
    ('sea_colours',              0, 32000,    False, 'unique colours on the z 63 sea plane (refs 245-31023)'),
    ('mirror_x_land',            0.35,  1.0,  False, 'ground-top mirror agreement on land columns (refs 0.38-0.97)'),
]


def _box(a, b):
    x0, x1, y0, y1 = b
    return a[x0:x1 + 1, y0:y1 + 1]


def ground_top(solid):
    """z of the top of the bottom solid run per column (63 = only the bottom voxel, i.e. water)."""
    run = np.cumprod(solid[:, :, ::-1], axis=2).sum(axis=2)
    return (64 - run).astype(np.int16)


def measure(m, name='map', nbytes=None):
    s = m.solid
    xs, ys = np.indices((512, 512))
    gtop = ground_top(s)
    top = np.argmax(s, axis=2).astype(np.int16)
    land = gtop <= 62
    water = ~land
    h = (63 - gtop).astype(np.int16)
    r = {'map': name}
    if nbytes is not None:
        r['bytes'] = int(nbytes)

    # ---- floating components (sky decor) - 6-face, grounded iff touching z >= 62
    lab3, n3 = ndimage.label(s, structure=FACE6)
    grounded_ids = np.unique(lab3[:, :, 62:][s[:, :, 62:]])
    is_g = np.zeros(n3 + 1, bool)
    is_g[grounded_ids] = True
    is_g[0] = False
    grounded = is_g[lab3]
    floating = s & ~grounded
    fl_sizes = np.bincount(lab3[floating], minlength=n3 + 1)
    fl_ids = np.nonzero(fl_sizes)[0]
    r['floating_components'] = int(fl_ids.size)
    r['floating_voxels'] = int(floating.sum())
    if fl_ids.size:
        zs = np.nonzero(floating)[2]
        r['floating_z_range'] = [int(zs.min()), int(zs.max())]
        r['floating_over_water_pct'] = round(100 * float(water[floating.any(axis=2)].mean()), 1)

    # ---- land, landmasses, main island
    r['water_pct'] = round(100 * float(water.mean()), 1)
    r['land_cols'] = int(land.sum())
    lab, n = ndimage.label(land)
    sizes = np.bincount(lab.ravel())[1:]
    order = np.argsort(-sizes)
    big = [int(sizes[i]) for i in order if sizes[i] >= LANDMASS_MIN]
    r['landmasses'] = len(big)
    r['landmass_sizes'] = big[:12]
    r['specks'] = int((sizes < LANDMASS_MIN).sum())
    if n:
        main = lab == (order[0] + 1)
        mx, my = np.nonzero(main)
        w, hgt = int(mx.max() - mx.min() + 1), int(my.max() - my.min() + 1)
        r['main_bbox'] = [int(mx.min()), int(mx.max()), int(my.min()), int(my.max())]
        r['main_aspect_x_over_y'] = round(w / hgt, 2)
        r['main_fill_pct'] = round(100 * float(main.sum()) / (w * hgt), 1)
        r['main_share_pct'] = round(100 * float(main.sum()) / max(1, land.sum()), 1)
        # neck: narrowest land extent in y across the middle third of the main island's x span
        x0 = mx.min() + w // 3
        x1 = mx.max() - w // 3
        widths = main[x0:x1 + 1].sum(axis=1)
        r['main_neck_min_y_width'] = int(widths.min()) if widths.size else None
        r['main_lobe_max_y_width'] = int(main.sum(axis=1).max())

    # ---- heights and terrain
    if land.any():
        hl = h[land]
        r['land_h'] = {'med': float(np.median(hl)), 'p90': float(np.percentile(hl, 90)), 'max': int(hl.max())}
        terr = ndimage.grey_opening(np.where(land, h, 0).astype(np.int16), size=(TERRAIN_WINDOW, TERRAIN_WINDOW))
        terr = np.minimum(terr, h)
        tl = terr[land]
        r['terrain_h'] = {'med': float(np.median(tl)), 'p90': float(np.percentile(tl, 90)), 'max': int(tl.max())}
        dx = np.abs(np.diff(terr.astype(int), axis=0))[land[1:] & land[:-1]]
        dy = np.abs(np.diff(terr.astype(int), axis=1))[land[:, 1:] & land[:, :-1]]
        steps = np.concatenate([dx, dy])
        r['terrain_slope'] = round(float(steps.mean()), 3) if steps.size else 0.0
        r['cliff_pct'] = round(100 * float((steps >= 3).mean()), 2) if steps.size else 0.0
        # shore profile: median terrain height by distance (columns) from the nearest water column
        dist = ndimage.distance_transform_edt(land)
        prof = {}
        for d in (1, 2, 4, 8, 16, 32):
            sel = land & (dist >= d) & (dist < d + 1 if d < 4 else dist < d * 1.5)
            if sel.sum() >= 20:
                prof[str(d)] = float(np.median(terr[sel]))
        r['shore_profile_med_h'] = prof
        # shore band: land within 6 columns of the sea that is at most 2 high (walk-in beach), as % of that ring
        ring = land & (dist <= 6)
        r['beach_ring_low_pct'] = round(100 * float((terr[ring] <= 2).mean()), 1) if ring.any() else None
        r['low_land_pct'] = round(100 * float((tl <= 3).mean()), 1)
        r['land_inland_dist_p90'] = float(np.percentile(dist[land], 90))
    else:
        terr = np.zeros_like(h)

    # ---- structure proxy (grounded, >= 2 above terrain)
    zgrid = np.arange(64)[None, None, :]
    above = grounded & (zgrid <= (63 - terr - 2)[:, :, None]) & land[:, :, None]
    # bridges/piers over water also count: grounded voxels above an air gap in water columns
    gap = grounded & (zgrid < gtop[:, :, None]) & water[:, :, None]
    struct = above | gap
    lab_s, ns = ndimage.label(struct, structure=FACE6)
    ssz = np.bincount(lab_s.ravel())
    keep = np.zeros(ns + 1, bool)
    keep[1:] = ssz[1:] >= STRUCT_MIN
    struct = keep[lab_s]
    r['struct_components'] = int(keep.sum())
    r['struct_voxels'] = int(struct.sum())
    r['struct_vox_per_land_col'] = round(r['struct_voxels'] / max(1, int(land.sum())), 3)
    fp = struct.any(axis=2)
    r['struct_footprint_cols'] = int(fp.sum())
    r['struct_footprint_pct_of_land'] = round(100 * float(fp[land].mean()), 1) if land.any() else 0.0
    cz = _box(fp, CENTRE_ZONE)
    r['centre_zone_struct_footprint_pct'] = round(100 * float(cz.mean()), 1)
    r['centre_zone_land_pct'] = round(100 * float(_box(land, CENTRE_ZONE).mean()), 1)
    r['struct_max_height_above_terrain'] = int(((63 - zgrid) - terr[:, :, None])[struct].max()) if struct.any() else 0
    roofed = (grounded & (zgrid < gtop[:, :, None])).any(axis=2) & land
    r['roofed_pct'] = round(100 * float(roofed.sum()) / max(1, int(land.sum())), 1)

    # ---- colours
    surf = surface_mask(s)
    surf[:, :, 63] = False
    auth = surf & grounded
    col = m.color[auth] & 0xFFFFFF
    r['surface_colours'] = int(np.unique(col).size)
    if col.size:
        hb = hue_bins(rgb_of(col))
        cnt = np.bincount(hb, minlength=13)
        cum = np.sort(cnt)[::-1].cumsum() / cnt.sum()
        r['hue_families_90'] = int(np.searchsorted(cum, 0.9) + 1)
    sea = m.color[:, :, 63][water] & 0xFFFFFF
    r['sea_colours'] = int(np.unique(sea).size)
    if sea.size:
        Ls = srgb_to_L(rgb_of(sea))
        r['sea_L_std'] = round(float(Ls.std()), 2)
        if land.any():
            dw = ndimage.distance_transform_edt(water)
            near, far = dw[water] <= 12, dw[water] >= 48
            if near.any() and far.any():
                r['sea_halo_dL_near_minus_far'] = round(float(Ls[near].mean() - Ls[far].mean()), 2)
    tc = m.color[xs, ys, gtop] & 0xFFFFFF
    if land.any():
        rgb = rgb_of(tc[land])
        luma = 0.299 * rgb[:, 0] + 0.587 * rgb[:, 1] + 0.114 * rgb[:, 2]
        r['land_top_luma'] = {'p5': round(float(np.percentile(luma, 5)), 1), 'med': round(float(np.median(luma)), 1),
                              'p95': round(float(np.percentile(luma, 95)), 1)}
        r['land_top_max_channel_p99'] = float(np.percentile(rgb.max(axis=1), 99))

    # ---- mirror. Our Babel maps mirror x' = 512 - x (bases at 118/394); some community maps use x' = 511 - x.
    # Agreement of ground top over columns where either side is land; the better of the two axes is reported.
    best = None
    for c in (512, 511):
        xa = np.arange(0, 256) if c == 511 else np.arange(1, 256)
        xb = c - xa
        a, b = gtop[xa], gtop[xb]
        either = land[xa] | land[xb]
        if either.any():
            v = float((a == b)[either].mean())
            if best is None or v > best[0]:
                best = (v, c, float((a == b).mean()))
    if best:
        r['mirror_x_land'] = round(best[0], 3)
        r['mirror_x_axis'] = f"x' = {best[1]} - x"
        r['mirror_x_all'] = round(best[2], 3)

    # ---- stock Babel checks
    def sq(box):
        g, t, lnd = _box(gtop, box), _box(top, box), _box(land, box)
        return {'land_pct': round(100 * float(lnd.mean()), 1), 'top_z': [int(t.min()), int(t.max())],
                'top_z_med': float(np.median(t)), 'ground_z_med': float(np.median(g))}
    r['spawn_blue'] = sq(SPAWN_BLUE)
    r['spawn_red'] = sq(SPAWN_RED)
    r['plat_end_blue'] = sq(PLAT_END_BLUE)
    r['plat_end_red'] = sq(PLAT_END_RED)
    r['solid_z_le2'] = int(s[:, :, :3].sum())
    x0, x1, y0, y1 = PLATFORM
    r['solid_z_le2_over_platform'] = int(s[x0:x1 + 1, y0:y1 + 1, :3].sum())
    r['solid_z_le3_over_platform'] = int(s[x0:x1 + 1, y0:y1 + 1, :4].sum())
    r['under_platform_top_z_min'] = int(_box(top, PLATFORM).min())
    return r


def classic_table(r):
    rows = []
    for key, lo, hi, sep, note in CLASSIC_RANGES:
        v = r.get(key)
        ok = None if v is None else bool(lo <= v <= hi)
        rows.append((key, lo, hi, v, ok, sep, note))
    return rows


def print_report(r):
    print(f"\n=== {r['map']} ===")
    for k in ('bytes', 'water_pct', 'landmasses', 'landmass_sizes', 'specks', 'main_bbox', 'main_aspect_x_over_y',
              'main_fill_pct', 'main_share_pct', 'main_neck_min_y_width', 'main_lobe_max_y_width', 'land_h',
              'terrain_h', 'terrain_slope', 'cliff_pct', 'shore_profile_med_h', 'beach_ring_low_pct', 'low_land_pct',
              'struct_components', 'struct_voxels', 'struct_vox_per_land_col', 'struct_footprint_pct_of_land',
              'centre_zone_land_pct', 'centre_zone_struct_footprint_pct', 'struct_max_height_above_terrain',
              'roofed_pct', 'floating_components', 'floating_voxels', 'floating_z_range', 'surface_colours',
              'hue_families_90', 'sea_colours', 'sea_L_std', 'sea_halo_dL_near_minus_far', 'land_top_luma',
              'land_top_max_channel_p99', 'mirror_x_land', 'mirror_x_axis', 'mirror_x_all', 'spawn_blue', 'spawn_red',
              'plat_end_blue', 'plat_end_red', 'solid_z_le2', 'solid_z_le2_over_platform',
              'solid_z_le3_over_platform', 'under_platform_top_z_min'):
        if k in r:
            print(f"  {k:34s} {r[k]}")
    print(f"  {'-- classic comparison':34s} (ranges from 4 community island maps; 'info' rows do not separate styles)")
    print(f"  {'metric':26s} {'classic range':>16s} {'this map':>10s}  in range?")
    for key, lo, hi, v, ok, sep, _ in classic_table(r):
        tag = '' if sep else '  (info)'
        print(f"  {key:26s} {f'{lo}-{hi}':>16s} {str(v):>10s}  {'-' if ok is None else ('yes' if ok else 'NO')}{tag}")
    n_sep = [ok for _, _, _, _, ok, sep, _ in classic_table(r) if sep and ok is not None]
    print(f"  style-separating metrics in classic range: {sum(n_sep)}/{len(n_sep)}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('maps', nargs='+', help='.vxl files')
    ap.add_argument('--json', help='write all results to this JSON file')
    a = ap.parse_args(argv)
    res = []
    for p in a.maps:
        m, rep = load(p)
        r = measure(m, os.path.basename(p).rsplit('.', 1)[0], os.path.getsize(p))
        r['reader_ok'] = rep.ok
        r['classic'] = [dict(metric=k, lo=lo, hi=hi, value=v, in_range=ok, separates=sep)
                        for k, lo, hi, v, ok, sep, _ in classic_table(r)]
        print_report(r)
        res.append(r)
    if a.json:
        with open(a.json, 'w') as f:
            json.dump(res, f, indent=1)
    return res


if __name__ == '__main__':
    main()
