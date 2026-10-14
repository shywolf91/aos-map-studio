#!/usr/bin/env python3
"""vxl_analyzer.py - standalone analyzer for classic Ace of Spades 0.75 maps (.vxl).

One file, needs only numpy + Pillow (scipy optional: enables the floating-component check).
Written for the AoS map-making project (piqueserver 1.4.2 / OpenSpades / BetterSpades target) so that
any assistant or person can measure reference maps the same way we do and feed the findings back.

USAGE
    python vxl_analyzer.py MAP.vxl [MAP2.vxl ...] --out analysis [--babel] [--iso] [--no-render]
    python vxl_analyzer.py --selftest

    --babel      also run the Babel spawn-exposure check (stock piqueserver babel_script geometry; ~5-20 s/map)
    --iso        also render 4 isometric views (slower, ~1-3 s each, bigger PNGs)
    --no-render  numbers only

  Per map it writes  <out>/<mapname>/report.md   (read this first - text, ASCII height map, region grid)
                     <out>/<mapname>/report.json (every number)
                     <out>/<mapname>/*.png       (top.png, height.png, sides.png, iso_*.png)
  and for several maps <out>/summary.md + summary.csv (one row per map).

AS A LIBRARY
    import vxl_analyzer as va
    m = va.load('normandie.vxl')                  # m.solid[x,y,z] bool, m.color[x,y,z] uint32 0xAARRGGBB
    va.column(m, 256, 256)                         # solid runs + colours of one column
    va.iso(m, crop=(180, 200, 330, 310)).save('mid.png')   # isometric close-up of a region
    va.side_view(m, 'south').save('s.png')
    rep = va.analyze(m, name='normandie', babel=True)

FORMAT FACTS (verified against piqueserver 1.4.2 pyspades/vxl_c.h and the aosprotocol map spec)
    512 x 512 columns, 64 voxels deep. x, y in 0..511; z in 0..63 with z = 0 the TOP (sky) and z = 63 the BOTTOM.
    Height above the water = 63 - z. z = 63 is the water plane / bottom layer and must be solid everywhere.
    No file header. Columns are stored y-major, x-minor: (0,0), (1,0) ... (511,0), (0,1) ...
    Each column = spans. Span header 4 bytes: N (span length in 4-byte words incl. header, 0 = last span),
    S (first z of the top coloured run), E (last z of the top coloured run, inclusive), A (z where this span's
    air starts; for later spans it ends the previous span's bottom colours). Then (E - S + 1) top colours, then
    the previous solid block's bottom colours. Colours: 4 bytes B, G, R, A(=shade byte, ignored by OpenSpades).
    Voxels between coloured runs are solid but uncoloured (buried). Everything below the last span is solid.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import struct
import sys
from dataclasses import dataclass, field

import numpy as np

try:
    from PIL import Image, ImageDraw
except ImportError:                       # renders are skipped without Pillow
    Image = None

X, Y, Z = 512, 512, 64
WATER_Z = 63

# Stock piqueserver 1.4.2 Babel geometry (piqueserver/scripts/babel_script.py + babel.py):
#   platform: solid layer at z = 1 over x 206..305, y 240..271 (built by the script, not the map)
#   bases/tents fixed at (118, 256) and (394, 256); spawns random within +-20 of the base, on the TOPMOST voxel.
BABEL_PLATFORM = {'x': (206, 305), 'y': (240, 271), 'z': 1}
BABEL_BASES = ((118, 256), (394, 256))
BABEL_SPAWN_HALF = 20


# =========================================================================== reading

@dataclass
class VoxelMap:
    solid: np.ndarray            # bool [x, y, z]
    color: np.ndarray            # uint32 [x, y, z], 0xAARRGGBB, 0 where no colour stored
    colored: np.ndarray          # bool [x, y, z]
    report: dict = field(default_factory=dict)


def read_vxl(data: bytes) -> VoxelMap:
    """Spec decoder with bounds checks. Raises ValueError on truncation; other anomalies go in report['issues']."""
    solid = np.ones((Y, X, Z), bool)              # [y, x, z] while reading (file order), transposed at the end
    color = np.zeros((Y, X, Z), np.uint32)
    colored = np.zeros((Y, X, Z), bool)
    u32 = struct.Struct('<I').unpack_from
    n, p = len(data), 0
    issues, spans, void_cols = [], 0, 0

    def flag(kind, x, y, d=''):
        if len(issues) < 50:
            issues.append(f'{kind} at ({x},{y}) {d}')

    for y in range(Y):
        for x in range(X):
            cs, cc, ck = solid[y, x], color[y, x], colored[y, x]
            z = 0
            while True:
                if p + 4 > n:
                    raise ValueError(f'VXL truncated at column ({x},{y}), byte {p} of {n}')
                N, S, E, A = data[p], data[p + 1], data[p + 2], data[p + 3]
                spans += 1
                if N == 0 and S == 64 and E == 63:
                    void_cols += 1                # all-air column (non-standard but loads in pyspades)
                elif S > 63 or E > 63:
                    flag('z_out_of_range', x, y, f'S={S} E={E}')
                if E < S - 1:
                    flag('negative_top_run', x, y, f'S={S} E={E}')
                if S < z:
                    flag('span_starts_above_cursor', x, y, f'S={S} cursor={z}')
                cs[z:S] = False
                K = max(E - S + 1, 0)
                cp = p + 4
                for i in range(K):
                    cc[S + i] = u32(data, cp)[0]
                    ck[S + i] = True
                    cp += 4
                if N == 0:
                    p += 4 * (K + 1)
                    break
                Zb = (N - 1) - K
                p += 4 * N
                if p + 4 > n:
                    raise ValueError(f'VXL truncated after column ({x},{y})')
                M = data[p + 3]
                if Zb < 0 or M < E + 1 + max(Zb, 0):
                    flag('bad_bottom_run', x, y, f'N={N} K={K} M={M}')
                for i in range(max(Zb, 0)):
                    zz = M - Zb + i
                    if 0 <= zz < Z:
                        cc[zz] = u32(data, cp)[0]
                        ck[zz] = True
                    cp += 4
                z = M
    if p != n:
        flag('trailing_bytes', -1, -1, f'{n - p} bytes after the last column')
    m = VoxelMap(np.ascontiguousarray(solid.transpose(1, 0, 2)),
                 np.ascontiguousarray(color.transpose(1, 0, 2)),
                 np.ascontiguousarray(colored.transpose(1, 0, 2)))
    m.report = {'bytes': n, 'bytes_consumed': p, 'spans': spans, 'all_air_columns': void_cols,
                'issues': issues, 'parse_ok': not issues and p == n}
    return m


def load(path) -> VoxelMap:
    with open(path, 'rb') as f:
        return read_vxl(f.read())


def read_metadata_txt(vxl_path):
    """Companion piqueserver metadata (<map>.txt, a Python file). Returned as TEXT only - never executed."""
    txt = os.path.splitext(vxl_path)[0] + '.txt'
    if not os.path.exists(txt):
        return None
    raw = open(txt, encoding='utf-8', errors='replace').read()
    keys = {}
    import re
    for k in ('name', 'version', 'author', 'description'):
        mm = re.search(rf'^{k}\s*=\s*(.+)$', raw, re.M)
        if mm:
            keys[k] = mm.group(1).strip()[:200]
    hooks = [h for h in ('get_spawn_location', 'get_entity_location', 'on_map_change', 'on_block_build_attempt',
                         'is_indestructable', 'on_map_leave') if h in raw]
    ext = re.search(r'extensions\s*=\s*(\{.*?\n\})', raw, re.S) or re.search(r'extensions\s*=\s*(\{.*?\})', raw, re.S)
    return {'file': os.path.basename(txt), 'fields': keys, 'hooks_defined': hooks,
            'extensions_text': ext.group(1)[:800] if ext else None, 'first_lines': raw[:1500]}


# =========================================================================== helpers

def surface_mask(solid):
    """pyspades is_surface(): solid and (z == 0 or any in-map face neighbour is air). Off-map counts as solid."""
    air = ~solid
    e = np.zeros_like(solid)
    e[:, :, 0] = True
    e[:, :, 1:] |= air[:, :, :-1]
    e[:, :, :-1] |= air[:, :, 1:]
    e[1:] |= air[:-1]
    e[:-1] |= air[1:]
    e[:, 1:] |= air[:, :-1]
    e[:, :-1] |= air[:, 1:]
    return solid & e


def rgb_of(c):
    c = np.asarray(c).astype(np.uint32)
    return np.stack([(c >> 16) & 255, (c >> 8) & 255, c & 255], -1).astype(np.float32)


def hexcol(c):
    return '#%06x' % (int(c) & 0xFFFFFF)


def lightness(rgb):
    """CIE L* (0-100) of sRGB."""
    c = rgb / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    Yl = 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]
    return np.where(Yl > 0.008856, 116 * np.cbrt(Yl) - 16, 903.3 * Yl)


def hue_bin(rgb):
    """12 hue bins of 30 degrees, bin 12 = grey/desaturated."""
    r, g, b = rgb[..., 0] / 255, rgb[..., 1] / 255, rgb[..., 2] / 255
    mx, mn = np.maximum(np.maximum(r, g), b), np.minimum(np.minimum(r, g), b)
    d = mx - mn
    sat = np.where(mx > 0, d / np.maximum(mx, 1e-6), 0)
    dd = np.where(d > 1e-6, d, 1)
    rc, gc, bc = (mx - r) / dd, (mx - g) / dd, (mx - b) / dd
    h = np.where(r == mx, bc - gc, np.where(g == mx, 2 + rc - bc, 4 + gc - rc))
    bins = (((h / 6.0) % 1.0) * 12).astype(int)
    return np.where(sat < 0.12, 12, bins)


HUE_NAMES = ['red', 'orange', 'yellow', 'yellow-green', 'green', 'green-cyan', 'cyan', 'azure', 'blue', 'violet',
             'magenta', 'pink-red', 'grey/neutral']


def topmost(solid):
    """z of the first solid voxel from the sky per column (63 = only the water plane). All-air columns (seen in a
    few community maps; pyspades still loads them) are reported as 63 so they count as water, not as sky towers."""
    return np.where(solid.any(axis=2), np.argmax(solid, axis=2), 63)


def column(m: VoxelMap, x, y):
    """Human-readable dump of one column: solid runs top->bottom with their surface colours."""
    col = m.solid[x, y]
    runs, z = [], 0
    while z < Z:
        if col[z]:
            z0 = z
            while z < Z and col[z]:
                z += 1
            cols = [hexcol(m.color[x, y, k]) for k in range(z0, z) if m.colored[x, y, k]]
            runs.append({'z_top': z0, 'z_bottom': z - 1, 'height_top': 63 - z0, 'n_colours': len(cols),
                         'top_colour': cols[0] if cols else None})
        else:
            z += 1
    return {'x': x, 'y': y, 'runs': runs}


# =========================================================================== analysis

def basic_stats(m):
    s = m.solid
    top = topmost(s)
    land = top < WATER_Z
    h = 63 - top
    hl = h[land]
    surf = surface_mask(s)
    runs = (s[:, :, 1:] & ~s[:, :, :-1]).sum(axis=2) + s[:, :, 0]       # solid runs per column (incl. bottom)
    hist_edges = [0, 1, 4, 8, 16, 24, 32, 40, 48, 56, 64]
    hist = np.histogram(hl, bins=hist_edges)[0] if hl.size else np.zeros(len(hist_edges) - 1, int)
    return {
        'solid_voxels': int(s.sum()), 'surface_voxels': int(surf.sum()),
        'surface_voxels_above_water': int(surf[:, :, :63].sum()),
        'land_columns_pct': round(100 * land.mean(), 1), 'water_columns_pct': round(100 * (~land).mean(), 1),
        'height_min': int(hl.min()) if hl.size else 0, 'height_max': int(hl.max()) if hl.size else 0,
        'height_mean_land': round(float(hl.mean()), 1) if hl.size else 0,
        'height_median_land': float(np.median(hl)) if hl.size else 0,
        'height_histogram_land': {f'{a}-{b - 1}': int(c) for a, b, c in zip(hist_edges[:-1], hist_edges[1:], hist)},
        'highest_point': [int(v) for v in np.unravel_index(int(np.argmax(h)), h.shape)] + [int(top.min())],
        'columns_with_overhang_pct': round(100 * (runs >= 2).mean(), 2),
        'max_runs_in_a_column': int(runs.max()),
        'sky_level_columns(z<=3)': int((top <= 3).sum()),
        'bounding_box_of_land': _bbox(land),
    }


def _bbox(mask):
    if not mask.any():
        return None
    xs, ys = np.nonzero(mask)
    return {'x': [int(xs.min()), int(xs.max())], 'y': [int(ys.min()), int(ys.max())]}


def spike_stats(m):
    """1x1 pillars / spikes: land columns >= 3 higher than all 4 neighbours (flicker/lag/readability hint)."""
    h = (63 - topmost(m.solid)).astype(int)
    p = np.pad(h, 1, mode='edge')
    nb = np.maximum.reduce([p[:-2, 1:-1], p[2:, 1:-1], p[1:-1, :-2], p[1:-1, 2:]])
    spikes = (h - nb >= 3) & (h > 0)
    return {'one_by_one_spikes': int(spikes.sum())}


def connectivity(m, top_n=10):
    """6-connected components not connected to the z = 63 layer = floating. Needs scipy."""
    try:
        from scipy import ndimage
    except ImportError:
        return {'available': False, 'note': 'install scipy for the floating-component check'}
    lab, n = ndimage.label(m.solid, structure=ndimage.generate_binary_structure(3, 1))
    grounded = np.unique(lab[:, :, 63])
    grounded = grounded[grounded > 0]
    sizes = np.bincount(lab.ravel(), minlength=n + 1)
    floating = np.setdiff1d(np.arange(1, n + 1), grounded)
    out = {'available': True, 'components_total': int(n), 'floating_components': int(len(floating)),
           'floating_voxels': int(sizes[floating].sum()) if len(floating) else 0, 'largest_floating': []}
    if len(floating):
        biggest = floating[np.argsort(sizes[floating])[::-1][:top_n]]
        sl = ndimage.find_objects(lab)
        for c in biggest:
            bx, by, bz = sl[c - 1]
            out['largest_floating'].append({'voxels': int(sizes[c]), 'x': [bx.start, bx.stop - 1],
                                            'y': [by.start, by.stop - 1], 'z': [bz.start, bz.stop - 1]})
    return out


def symmetry(m):
    """How symmetric is the layout? % of columns whose height matches the mirrored column within 1 voxel,
    and % of above-water solid voxels that match. Babel/CTF maps are usually mirrored across x = 256 (x' = 512 - x)
    or x' = 511 - x; we report the best of both offsets."""
    h = (63 - topmost(m.solid)).astype(int)
    s = m.solid[:, :, :63]
    res = {}

    def score(h2, s2):
        return round(100 * float((np.abs(h - h2) <= 1).mean()), 1), round(100 * float((s & s2).sum() / max(s.sum(), 1)), 1)

    def shift_x(a, k):          # a[512 - x] style mirror: reverse then roll by k
        return np.roll(a[::-1], k, axis=0)

    best = max((score(shift_x(h, k), shift_x(s, k)) + (k,) for k in (0, 1)), key=lambda t: t[0])
    res['mirror_x (east-west)'] = {'height_match_pct': best[0], 'voxel_match_pct': best[1],
                                   'axis': 'x = 255.5' if best[2] == 0 else 'x = 256'}
    best = max((score(np.roll(h[:, ::-1], k, axis=1), np.roll(s[:, ::-1], k, axis=1)) + (k,) for k in (0, 1)),
               key=lambda t: t[0])
    res['mirror_y (north-south)'] = {'height_match_pct': best[0], 'voxel_match_pct': best[1]}
    best = max((score(np.roll(np.roll(h[::-1, ::-1], k, 0), k, 1), np.roll(np.roll(s[::-1, ::-1], k, 0), k, 1)) + (k,)
                for k in (0, 1)), key=lambda t: t[0])
    res['rotate_180'] = {'height_match_pct': best[0], 'voxel_match_pct': best[1]}
    best_key = max(res, key=lambda k: res[k]['height_match_pct'])
    res['best'] = best_key
    return res


def art_metrics(m):
    """Colour/shading statistics on authored surfaces (z = 63 water plane excluded). Same definitions as our
    tools/art_metrics.py so numbers are comparable with the project's calibration table."""
    s = m.solid
    surf = surface_mask(s)
    surf[:, :, 63] = False
    col = m.color[surf] & 0xFFFFFF
    out = {}
    if col.size == 0:
        return {'note': 'no surface above water'}
    rgb = rgb_of(col)
    uniq, cnt = np.unique(col, return_counts=True)
    out['unique_colours'] = int(uniq.size)
    order = np.argsort(cnt)[::-1][:16]
    out['top_colours'] = [{'hex': hexcol(uniq[i]), 'share_pct': round(100 * cnt[i] / cnt.sum(), 2)} for i in order]
    hb = hue_bin(rgb)
    hc = np.bincount(hb, minlength=13)
    cum = np.sort(hc)[::-1].cumsum() / hc.sum()
    out['hue_families_90'] = int(np.searchsorted(cum, 0.9) + 1)
    out['hue_shares_pct'] = {HUE_NAMES[i]: round(float(100 * hc[i] / hc.sum()), 1) for i in np.argsort(hc)[::-1] if hc[i] > 0}
    Lall = lightness(rgb)
    out['lightness_L_median'] = round(float(np.median(Lall)), 1)
    out['lightness_L_p10_p90'] = [round(float(np.percentile(Lall, 10)), 1), round(float(np.percentile(Lall, 90)), 1)]
    top = topmost(s)
    land = top < 62
    xs, ys = np.indices(top.shape)
    tc = m.color[xs, ys, top] & 0xFFFFFF
    L = lightness(rgb_of(tc))

    def dl_at(k):
        a = np.abs(L[k:] - L[:-k])[(top[k:] == top[:-k]) & land[k:] & land[:-k]]
        b = np.abs(L[:, k:] - L[:, :-k])[(top[:, k:] == top[:, :-k]) & land[:, k:] & land[:, :-k]]
        v = np.concatenate([a, b])
        return v
    d1 = dl_at(1)
    same = np.concatenate([(tc[1:] == tc[:-1])[(top[1:] == top[:-1]) & land[1:] & land[:-1]],
                           (tc[:, 1:] == tc[:, :-1])[(top[:, 1:] == top[:, :-1]) & land[:, 1:] & land[:, :-1]]])
    d4 = dl_at(4)
    out['top_noise_dL'] = round(float(d1.mean()), 2) if d1.size else None
    out['coherence_4'] = round(float(d4.mean() / d1.mean()), 2) if d1.size and d1.mean() > 1e-6 else None
    out['top_equal_neighbour_pct'] = round(100 * float(same.mean()), 1) if same.size else None
    out['shading_step_dL'] = round(float(np.median(d1[d1 > 0])), 2) if (d1 > 0).any() else None
    hh = (63 - top)[land].astype(float)
    out['height_vs_lightness_corr'] = round(float(np.corrcoef(hh, L[land])[0, 1]), 2) \
        if land.sum() > 10 and hh.std() > 0 and L[land].std() > 0 else None
    up_air = np.zeros_like(s)
    up_air[:, :, 0] = True
    up_air[:, :, 1:] = ~s[:, :, :-1]
    Lt = lightness(rgb_of(m.color[surf & up_air] & 0xFFFFFF))
    Ls = lightness(rgb_of(m.color[surf & ~up_air] & 0xFFFFFF))
    out['side_minus_top_L'] = round(float(np.median(Ls) - np.median(Lt)), 1) if Ls.size and Lt.size else None
    out['surface_voxels_per_land_column'] = round(float(surf[land].sum() / max(land.sum(), 1)), 2)
    rel = []
    for cx in range(0, X, 16):
        for cy in range(0, Y, 16):
            ch = land[cx:cx + 16, cy:cy + 16]
            if ch.mean() > 0.5:
                t = top[cx:cx + 16, cy:cy + 16][ch]
                rel.append(int(t.max() - t.min()))
    out['relief_16'] = round(float(np.mean(rel)), 1) if rel else None
    # the z = 63 plane: painted backdrop? (Cloud Smash paints a sunset into it)
    wc = m.color[:, :, 63][m.colored[:, :, 63] & (top == 63)] & 0xFFFFFF
    if wc.size:
        wu, wn = np.unique(wc, return_counts=True)
        out['water_plane_colours'] = int(wu.size)
        out['water_plane_main_colour'] = hexcol(wu[wn.argmax()])
    else:
        out['water_plane_colours'], out['water_plane_main_colour'] = 0, None
    return out


def region_grid(m, cells=8):
    """cells x cells grid (64-voxel cells for 8): land %, mean/max height, detail, dominant top colour."""
    top = topmost(m.solid)
    h = 63 - top
    land = top < WATER_Z
    surf = surface_mask(m.solid)
    surf[:, :, 63] = False
    det = surf.sum(axis=2)
    xs, ys = np.indices(top.shape)
    tc = m.color[xs, ys, top] & 0xFFFFFF
    k = X // cells
    rows = []
    for gy in range(cells):
        row = []
        for gx in range(cells):
            sl = (slice(gx * k, gx * k + k), slice(gy * k, gy * k + k))
            l = land[sl]
            c = tc[sl][l] if l.any() else tc[sl].ravel()
            u, n = np.unique(c, return_counts=True)
            row.append({'cell': f'{"ABCDEFGHIJKLMNOP"[gx]}{gy + 1}', 'x': [gx * k, gx * k + k - 1],
                        'y': [gy * k, gy * k + k - 1], 'land_pct': int(round(100 * l.mean())),
                        'h_mean': int(round(h[sl][l].mean())) if l.any() else 0,
                        'h_max': int(h[sl].max()), 'detail': round(float(det[sl][l].mean()), 1) if l.any() else 0,
                        'colour': hexcol(u[n.argmax()])})
        rows.append(row)
    return rows


def ascii_height(m, cell=8):
    """64x64 character height map (each char = 8x8 columns, max height). '~' = water only.
    The ramp ' .:-=+*#%@' is stretched over THIS map's land height range (printed underneath), so low maps still
    show their relief. North (y = 0) at the top, west (x = 0) on the left - same orientation as top.png."""
    top = topmost(m.solid)
    h = 63 - top
    land = h > 0
    lo, hi = (int(h[land].min()), int(h[land].max())) if land.any() else (0, 1)
    ramp = '.:-=+*#%@'
    n = X // cell
    lines = ['    ' + ''.join('ABCDEFGH'[i * cell // 64] if (i * cell) % 64 == 0 else ' ' for i in range(n))]
    for gy in range(n):
        line = ''
        for gx in range(n):
            mx = int(h[gx * cell:(gx + 1) * cell, gy * cell:(gy + 1) * cell].max())
            line += '~' if mx == 0 else ramp[min(len(ramp) - 1, (mx - lo) * len(ramp) // max(hi - lo + 1, 1))]
        lines.append(f'{gy * cell:3d} ' + line)
    R = max(hi - lo + 1, 1)
    vals = {c: [v for v in range(lo, hi + 1) if ramp[min(len(ramp) - 1, (v - lo) * len(ramp) // R)] == c] for c in ramp}
    legend = ', '.join(f"'{c}' {v[0]}-{v[-1]}" for c, v in vals.items() if v)
    return '\n'.join(lines) + f'\n    ~ water only; heights (63 - z): {legend}'


# ---------------------------------------------------------------- Babel-specific

def babel_geometry(m):
    """Things the stock babel_script cares about. Platform is ADDED by the script at z = 1; the map should leave
    room for it and keep a fair building gap from both sides."""
    s = m.solid
    P = BABEL_PLATFORM
    (x0, x1), (y0, y1), pz = P['x'], P['y'], P['z']
    top = topmost(s)
    out = {'platform_footprint_occupied_voxels_z0_3': int(s[x0:x1 + 1, y0:y1 + 1, 0:4].sum())}
    xs, ys, zs = np.nonzero(s[:, :, :63])
    dx = np.maximum(0, np.maximum(x0 - xs, xs - x1))
    dy = np.maximum(0, np.maximum(y0 - ys, ys - y1))
    dz = np.maximum(0, zs - pz)
    d = np.sqrt(dx ** 2 + dy ** 2 + dz ** 2)
    for side, sel in (('west', xs < 256), ('east', xs >= 256)):
        if sel.any():
            k = np.argmin(np.where(sel, d, 1e9))
            out[f'nearest_solid_to_platform_{side}'] = {'distance': round(float(d[k]), 1),
                                                        'at': [int(xs[k]), int(ys[k]), int(zs[k])]}
    for i, (bx, by) in enumerate(BABEL_BASES):
        sl = (slice(bx - BABEL_SPAWN_HALF, bx + BABEL_SPAWN_HALF + 1), slice(by - BABEL_SPAWN_HALF, by + BABEL_SPAWN_HALF + 1))
        f = top[sl]
        out[f'team{i + 1}_spawn_zone'] = {
            'base': [bx, by], 'floor_z_min_median_max': [int(f.min()), int(np.median(f)), int(f.max())],
            'floor_height_median': int(63 - np.median(f)),
            'on_water_pct': round(100 * float((f >= 62).mean()), 1),
            'vertical_drop_to_platform': int(np.median(f)) - pz}
    return out


def _visible(opaque, a, b, step=0.25):
    d = b - a
    L = np.linalg.norm(d, axis=1)
    n = int(np.ceil(L.max() / step)) + 1
    vis = np.ones(len(a), bool)
    for k in range(1, n - 1):
        t = np.minimum(k * step / np.maximum(L, 1e-6), 1.0)
        p = a + d * t[:, None]
        active = (t < 0.995) & vis
        if not active.any():
            break
        xi, yi, zi = (np.floor(p[:, i]).astype(int) for i in range(3))
        inside = (xi >= 0) & (xi < X) & (yi >= 0) & (yi < Y) & (zi >= 0) & (zi < Z)
        hit = np.zeros(len(a), bool)
        hit[inside] = opaque[xi[inside], yi[inside], zi[inside]]
        vis &= ~(hit & active)
    return vis


def babel_spawn_exposure(m, viewer_step=4, spawn_step=2, chunk=40000):
    """How visible is each team's spawn zone from the platform edge? (geometry only, fog ignored = upper bound)
    Eyes on the platform perimeter (z = 1 - 2.4), targets = heads 2.2 above the topmost voxel on a 2-voxel grid of
    the +-20 spawn square. Calibration on rated maps is in the guide."""
    P = BABEL_PLATFORM
    (x0, x1), (y0, y1), pz = P['x'], P['y'], P['z']
    opaque = m.solid.copy()
    opaque[x0:x1 + 1, y0:y1 + 1, pz] = True
    V = []
    for x in range(x0, x1 + 1, viewer_step):
        V += [(x + 0.5, y0 + 0.5), (x + 0.5, y1 + 0.5)]
    for y in range(y0, y1 + 1, viewer_step):
        V += [(x0 + 0.5, y + 0.5), (x1 + 0.5, y + 0.5)]
    V = np.unique(np.array(V), axis=0)
    V = np.column_stack([V, np.full(len(V), pz - 2.4)])
    res = {}
    for i, (bx, by) in enumerate(BABEL_BASES):
        T = []
        for x in range(bx - BABEL_SPAWN_HALF, bx + BABEL_SPAWN_HALF + 1, spawn_step):
            for y in range(by - BABEL_SPAWN_HALF, by + BABEL_SPAWN_HALF + 1, spawn_step):
                col = m.solid[x, y]
                z = int(np.argmax(col)) if col.any() else 63
                T.append((x + 0.5, y + 0.5, z - 2.2, z))
        T = np.array(T, float)
        ia, ib = np.meshgrid(np.arange(len(V)), np.arange(len(T)), indexing='ij')
        ia, ib = ia.ravel(), ib.ravel()
        vis = np.zeros(len(ia), bool)
        for s0 in range(0, len(ia), chunk):
            sl = slice(s0, s0 + chunk)
            vis[sl] = _visible(opaque, V[ia[sl]], T[ib[sl], :3])
        vis = vis.reshape(len(V), len(T))
        horiz = np.array([math.hypot(max(0, x0 - tx, tx - x1 - 1), max(0, y0 - ty, ty - y1 - 1)) for tx, ty in T[:, :2]])
        ang = np.degrees(np.arctan2(T[:, 3] - pz, np.maximum(horiz, 0.1)))
        res[f'team{i + 1}'] = {'spawn_points': int(len(T)), 'exposed_pct': round(100 * float(vis.any(axis=0).mean()), 1),
                               'viewers_per_spawn_point': round(float(vis.sum(axis=0).mean()), 1),
                               'hidden_pct': round(100 * float((~vis.any(axis=0)).mean()), 1),
                               'median_depression_angle_deg': round(float(np.median(ang)), 1),
                               'median_floor_z': int(np.median(T[:, 3]))}
    v = [res[t]['viewers_per_spawn_point'] for t in res]
    hid = [res[t]['hidden_pct'] for t in res]
    res['verdict'] = ('HIGH camping risk (sky-deck/tradeoff-like)' if max(v) > 20 else
                      'elevated - add cover toward the platform' if max(v) > 10 else
                      'typical ground map; good if >= 15% hidden' if min(hid) < 15 else 'well covered')
    return res


# =========================================================================== renders

def top_view(m, scale=1):
    top = topmost(m.solid)
    xs, ys = np.indices(top.shape)
    col = rgb_of(m.color[xs, ys, top])
    h = (63 - top).astype(np.float32)
    gx = np.zeros_like(h); gy = np.zeros_like(h)
    gx[1:] = h[1:] - h[:-1]
    gy[:, 1:] = h[:, 1:] - h[:, :-1]
    shade = np.clip(1.0 + 0.10 * (gx + gy), 0.55, 1.25)
    img = np.clip(col * shade[..., None], 0, 255).astype(np.uint8).transpose(1, 0, 2)
    im = Image.fromarray(img, 'RGB')
    return im.resize((X * scale, Y * scale), Image.NEAREST) if scale != 1 else im


def height_view(m):
    top = topmost(m.solid)
    h = (63 - top).astype(np.float32)
    land = top < 63
    lo, hi = (h[land].min(), h[land].max()) if land.any() else (0, 1)
    g = (40 + 215 * np.clip((h - lo) / max(hi - lo, 1), 0, 1)).astype(np.uint8)    # stretched to this map's range
    img = np.stack([g, g, g], -1)
    img[top == 63] = (40, 70, 140)
    im = Image.fromarray(img.transpose(1, 0, 2), 'RGB')
    d = ImageDraw.Draw(im)
    for k in range(64, 512, 64):              # 64-voxel grid matching the region-grid cells
        d.line([(k, 0), (k, 511)], fill=(200, 60, 60))
        d.line([(0, k), (511, k)], fill=(200, 60, 60))
    for gx in range(8):
        d.text((gx * 64 + 3, 2), 'ABCDEFGH'[gx], fill=(255, 220, 0))
    for gy in range(8):
        d.text((3, gy * 64 + 12), str(gy + 1), fill=(255, 220, 0))
    d.text((70, 500), f'grey = land height {int(lo)} (dark) .. {int(hi)} (white); blue = water', fill=(255, 220, 0))
    return im


def side_view(m, frm='south', fog=(150, 160, 175)):
    """Orthographic elevation: first solid voxel seen looking in from one side; distance fades toward fog.
    'south' looks north from y = 511 (x left->right), 'north' from y = 0, 'west' from x = 0, 'east' from x = 511."""
    s, c = m.solid, m.color
    if frm == 'south':
        s, c = s[:, ::-1, :], c[:, ::-1, :]
    elif frm == 'north':
        s, c = s[::-1, :, :], c[::-1, :, :]
    elif frm == 'west':
        s, c = s.transpose(1, 0, 2), c.transpose(1, 0, 2)
    elif frm == 'east':
        s, c = s.transpose(1, 0, 2)[::-1, ::-1, :], c.transpose(1, 0, 2)[::-1, ::-1, :]
    hit = s.any(axis=1)                                   # [u, z]
    depth = np.argmax(s, axis=1)
    u, z = np.indices(depth.shape)
    col = rgb_of(c[u, depth, z])
    t = np.clip(depth / 400.0, 0, 0.85)[..., None]
    img = col * (1 - t) + np.array(fog, np.float32) * t
    img[~hit] = (25, 28, 34)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8).transpose(1, 0, 2), 'RGB')
    return im.resize((im.width, im.height * 2), Image.NEAREST)


def _sprite(s):
    faces = {'top': [], 'left': [], 'right': []}
    for v in range(2 * s):
        for u in range(2 * s):
            cu, cv = u + 0.5, v + 0.5
            d = abs(cu - s)
            if cv < s / 2 - d / 2 or cv > 1.5 * s + (s - d) / 2:
                continue
            if cv <= s / 2 + (s - d) / 2:
                faces['top'].append((u, v))
            elif cu < s:
                faces['left'].append((u, v))
            else:
                faces['right'].append((u, v))
    return {k: np.array(v, np.int32) for k, v in faces.items()}


def iso(m, crop=None, view=0, s=2, bg=(24, 26, 30)):
    """Isometric render. crop=(x0, y0, x1, y1) inclusive; view 0..3 rotates 90 degrees."""
    solid, color = m.solid, m.color
    if crop:
        x0, y0, x1, y1 = crop
        solid, color = solid[x0:x1 + 1, y0:y1 + 1], color[x0:x1 + 1, y0:y1 + 1]
    solid = np.rot90(solid, view, axes=(0, 1))
    color = np.rot90(color, view, axes=(0, 1))
    Xs, Ys, _ = solid.shape
    air = ~solid
    e = np.zeros_like(solid)
    e[:, :, 0] = True
    e[:, :, 1:] |= air[:, :, :-1]
    e[:-1] |= air[1:]
    e[:, :-1] |= air[:, 1:]
    e[-1] = True
    e[:, -1] = True
    vis = solid & e
    x, y, z = np.nonzero(vis)
    h = 63 - z
    sx = (x - y + Ys) * s
    sy = ((x + y) * s) // 2 + (63 - h) * s
    depth = (x + y + h).astype(np.int32)
    rgb = rgb_of(color[x, y, z])
    W = (Xs + Ys + 2) * s
    H = ((Xs + Ys) * s) // 2 + 64 * s + 2 * s
    sp = _sprite(s)
    pid, dep, cols = [], [], []
    for face, mul in (('top', 1.0), ('left', 0.80), ('right', 0.64)):
        offs = sp[face]
        pid.append(((sy[:, None] + offs[None, :, 1]).astype(np.int64) * W + (sx[:, None] + offs[None, :, 0])).ravel())
        dep.append(np.repeat(depth, len(offs)))
        cols.append(np.repeat(np.clip(rgb * mul, 0, 255).astype(np.uint8), len(offs), axis=0))
    pid, dep, cols = np.concatenate(pid), np.concatenate(dep), np.concatenate(cols)
    order = np.lexsort((dep, pid))
    pid, cols = pid[order], cols[order]
    last = np.ones(len(pid), bool)
    last[:-1] = pid[1:] != pid[:-1]
    img = np.empty((H * W, 3), np.uint8)
    img[:] = bg
    img[pid[last]] = cols[last]
    return Image.fromarray(img.reshape(H, W, 3), 'RGB')


# =========================================================================== driver

def analyze(m, name='map', babel=False, meta=None):
    rep = {'map': name, 'parse': m.report, 'metadata_txt': meta}
    rep['basic'] = basic_stats(m)
    rep['spikes'] = spike_stats(m)
    rep['connectivity'] = connectivity(m)
    rep['symmetry'] = symmetry(m)
    rep['art'] = art_metrics(m)
    rep['babel_geometry'] = babel_geometry(m)
    if babel:
        rep['babel_spawn_exposure'] = babel_spawn_exposure(m)
    rep['regions'] = region_grid(m)
    rep['ascii_height'] = ascii_height(m)
    return rep


def report_md(rep):
    b, a, sy, cn = rep['basic'], rep['art'], rep['symmetry'], rep['connectivity']
    L = [f"# VXL analysis: {rep['map']}", '',
         'Measured by vxl_analyzer.py (geometry + colour only; no in-game behaviour is implied).', '']
    p = rep['parse']
    L += ['## File', f"- parse ok: **{p['parse_ok']}**, {p['bytes']:,} bytes, {p['spans']:,} spans, "
          f"all-air columns: {p['all_air_columns']}", *(f'- issue: {i}' for i in p['issues'][:10])]
    if rep.get('metadata_txt'):
        mt = rep['metadata_txt']
        L += [f"- metadata {mt['file']}: {mt['fields']}; hooks: {mt['hooks_defined'] or 'none'}"]
        if mt['extensions_text']:
            L += ['```', mt['extensions_text'], '```']
    L += ['', '## Terrain',
          f"- land {b['land_columns_pct']}% / water {b['water_columns_pct']}% of columns; land bbox {b['bounding_box_of_land']}",
          f"- land height (63 - z): min {b['height_min']}, median {b['height_median_land']}, mean {b['height_mean_land']}, "
          f"max {b['height_max']} at {b['highest_point']} [x, y, z]",
          f"- height histogram (land columns): {b['height_histogram_land']}",
          f"- columns with overhangs/bridges/tunnels (>= 2 solid runs): {b['columns_with_overhang_pct']}% "
          f"(max runs in one column {b['max_runs_in_a_column']})",
          f"- sky-level columns (top z <= 3): {b['sky_level_columns(z<=3)']}; 1x1 spikes: {rep['spikes']['one_by_one_spikes']}",
          f"- solid voxels {b['solid_voxels']:,}; surface voxels above water {b['surface_voxels_above_water']:,}"]
    if cn.get('available'):
        L += [f"- floating components: {cn['floating_components']} ({cn['floating_voxels']} voxels)"
              + (f"; largest: {cn['largest_floating'][:3]}" if cn['largest_floating'] else '')]
    else:
        L += [f"- floating components: n/a ({cn['note']})"]
    L += ['', '## Symmetry (height match within 1 voxel / above-water voxel match)']
    for k in ('mirror_x (east-west)', 'mirror_y (north-south)', 'rotate_180'):
        L += [f"- {k}: {sy[k]['height_match_pct']}% / {sy[k]['voxel_match_pct']}%"]
    L += [f"- best: {sy['best']}"]
    L += ['', '## Colour and shading',
          f"- unique surface colours {a.get('unique_colours')}; hue families covering 90%: {a.get('hue_families_90')}",
          f"- hue shares %: {a.get('hue_shares_pct')}",
          f"- lightness L* median {a.get('lightness_L_median')}, p10-p90 {a.get('lightness_L_p10_p90')}",
          f"- coherence_4 {a.get('coherence_4')} (1.0 = random per-voxel noise; refs 1.4-2.5); top noise dL "
          f"{a.get('top_noise_dL')}; equal-neighbour tops {a.get('top_equal_neighbour_pct')}%; shading step dL "
          f"{a.get('shading_step_dL')}",
          f"- side faces minus tops L*: {a.get('side_minus_top_L')} (refs -5..-34); height-lightness corr "
          f"{a.get('height_vs_lightness_corr')}",
          f"- surface voxels per land column {a.get('surface_voxels_per_land_column')}; relief within 16x16 "
          f"chunks {a.get('relief_16')}",
          f"- water plane: {a.get('water_plane_colours')} colours, main {a.get('water_plane_main_colour')}",
          '- top colours: ' + ', '.join(f"{c['hex']} {c['share_pct']}%" for c in a.get('top_colours', [])[:12])]
    g = rep['babel_geometry']
    L += ['', '## Babel geometry (stock piqueserver: platform z=1, x 206-305, y 240-271; bases (118,256)/(394,256))',
          f"- map voxels inside the platform footprint z 0-3: {g['platform_footprint_occupied_voxels_z0_3']}"]
    for side in ('west', 'east'):
        k = f'nearest_solid_to_platform_{side}'
        if k in g:
            L += [f"- nearest map voxel to platform ({side}): {g[k]['distance']} at {g[k]['at']}"]
    for t in ('team1', 'team2'):
        z = g[f'{t}_spawn_zone']
        L += [f"- {t} spawn zone {z['base']}+-20: floor z min/median/max {z['floor_z_min_median_max']} "
              f"(height {z['floor_height_median']}), on water {z['on_water_pct']}%, drop to platform {z['vertical_drop_to_platform']}"]
    if 'babel_spawn_exposure' in rep:
        e = rep['babel_spawn_exposure']
        for t in ('team1', 'team2'):
            L += [f"- spawn exposure {t}: exposed {e[t]['exposed_pct']}%, hidden {e[t]['hidden_pct']}%, "
                  f"viewers/spot {e[t]['viewers_per_spawn_point']}, angle {e[t]['median_depression_angle_deg']} deg"]
        L += [f"- exposure verdict: **{e['verdict']}**"]
    L += ['', '## Region grid (64x64 cells; A-H = x west->east, 1-8 = y north->south)',
          '| | ' + ' | '.join('ABCDEFGH') + ' |', '|---' * 9 + '|']
    for row in rep['regions']:
        L.append(f"| {row[0]['cell'][1:]} | " + ' | '.join(
            f"{c['land_pct']}% h{c['h_mean']}/{c['h_max']} d{c['detail']} {c['colour']}" for c in row) + ' |')
    L += ['', 'cell = land% h(mean)/(max) d(surface voxels per land column = structure density) dominant top colour',
          '', '## ASCII height map (north up, 8x8 columns per char)', '```', rep['ascii_height'], '```']
    return '\n'.join(L) + '\n'


def run(paths, out, babel=False, iso_on=False, render=True):
    os.makedirs(out, exist_ok=True)
    rows = []
    for path in paths:
        name = os.path.splitext(os.path.basename(path))[0]
        print(f'[{name}] reading ...', flush=True)
        m = load(path)
        rep = analyze(m, name=name, babel=babel, meta=read_metadata_txt(path))
        d = os.path.join(out, name)
        os.makedirs(d, exist_ok=True)
        json.dump(rep, open(os.path.join(d, 'report.json'), 'w'), indent=1, default=str)
        open(os.path.join(d, 'report.md'), 'w').write(report_md(rep))
        if render and Image is not None:
            top_view(m).save(os.path.join(d, 'top.png'))
            height_view(m).save(os.path.join(d, 'height.png'))
            sides = [side_view(m, f) for f in ('south', 'north', 'west', 'east')]
            sheet = Image.new('RGB', (512, sum(i.height + 14 for i in sides)), (15, 15, 18))
            dr = ImageDraw.Draw(sheet)
            yy = 0
            for f, im in zip(('from south (looking north)', 'from north', 'from west', 'from east'), sides):
                dr.text((4, yy), f, fill=(230, 230, 230))
                sheet.paste(im, (0, yy + 14))
                yy += im.height + 14
            sheet.save(os.path.join(d, 'sides.png'))
            if iso_on:
                for v in range(4):
                    iso(m, view=v, s=2).save(os.path.join(d, f'iso_{v}.png'))
        b, a, sy = rep['basic'], rep['art'], rep['symmetry']
        row = {'map': name, 'parse_ok': rep['parse']['parse_ok'], 'land_pct': b['land_columns_pct'],
               'h_median': b['height_median_land'], 'h_max': b['height_max'],
               'overhang_pct': b['columns_with_overhang_pct'],
               'floating': rep['connectivity'].get('floating_components'),
               'sym_x_pct': sy['mirror_x (east-west)']['height_match_pct'], 'sym_best': sy['best'],
               'colours': a.get('unique_colours'), 'hue_fam_90': a.get('hue_families_90'),
               'coherence_4': a.get('coherence_4'), 'side_minus_top_L': a.get('side_minus_top_L'),
               'relief_16': a.get('relief_16'), 'detail': a.get('surface_voxels_per_land_column')}
        if babel:
            e = rep['babel_spawn_exposure']
            row.update({'spawn_viewers_t1': e['team1']['viewers_per_spawn_point'],
                        'spawn_viewers_t2': e['team2']['viewers_per_spawn_point'],
                        'spawn_hidden_t1': e['team1']['hidden_pct'], 'spawn_hidden_t2': e['team2']['hidden_pct']})
        rows.append(row)
        print(f'[{name}] done -> {d}', flush=True)
    if rows:
        with open(os.path.join(out, 'summary.csv'), 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[-1].keys()))
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k) for k in rows[-1].keys()})
        keys = list(rows[-1].keys())
        md = ['| ' + ' | '.join(keys) + ' |', '|' + '---|' * len(keys)]
        md += ['| ' + ' | '.join(str(r.get(k)) for k in keys) + ' |' for r in rows]
        open(os.path.join(out, 'summary.md'), 'w').write('\n'.join(md) + '\n')
    return rows


def selftest():
    """Builds a tiny synthetic map in memory, encodes it with a minimal writer and checks the reader."""
    s = np.zeros((X, Y, Z), bool)
    s[:, :, 63] = True
    s[100:110, 100:110, 50:63] = True
    s[200, 200, 10] = True                       # floating voxel
    data = bytearray()
    for y in range(Y):
        for x in range(X):
            col = s[x, y]
            if x == 200 and y == 200:
                # span 1: voxel at z=10 (air 0..9), then span 2 ends with water at 63
                data += bytes([2, 10, 10, 0]) + struct.pack('<I', 0x80FF0000)
                data += bytes([0, 63, 63, 11]) + struct.pack('<I', 0x800000FF)   # A = 11: air resumes below the voxel
            elif col[50]:
                data += bytes([0, 50, 50, 0]) + struct.pack('<I', 0x8000FF00)
            else:
                data += bytes([0, 63, 63, 0]) + struct.pack('<I', 0x800000FF)
    m = read_vxl(bytes(data))
    assert m.report['parse_ok'], m.report
    assert (m.solid == s).all(), 'occupancy mismatch'
    assert m.color[200, 200, 10] & 0xFFFFFF == 0xFF0000
    c = connectivity(m)
    if c.get('available'):
        assert c['floating_components'] == 1, c
    print('selftest ok')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('maps', nargs='*')
    ap.add_argument('--out', default='vxl_analysis')
    ap.add_argument('--babel', action='store_true', help='run the Babel spawn-exposure check')
    ap.add_argument('--iso', action='store_true', help='render 4 isometric views')
    ap.add_argument('--no-render', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        selftest()
        sys.exit(0)
    if not a.maps:
        ap.print_help()
        sys.exit(1)
    run(a.maps, a.out, babel=a.babel, iso_on=a.iso, render=not a.no_render)
