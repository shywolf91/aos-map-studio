"""Measure art-direction statistics of VXL maps (for calibrating the art kit, not for copying).

Per map, on authored surfaces (excluding the z = 63 water/backdrop plane):
  colours            unique RGB on surface voxels
  hue_families_90    number of 30-degree hue bins (+1 grey bin) covering 90 % of surface voxels
  top_noise          mean |dL| (CIE L*, 0-100) between 4-adjacent TOP voxels at the same height
  top_flat_pct       % of those neighbour pairs with identical colour
  ramp_step          median |dL| between neighbours that differ (size of a shading step)
  height_L_corr      correlation of top-surface L* with height (63 - z) on land
  side_dark          median L*(side faces) - L*(top faces) on the same material family
  vert_detail        surface voxels per land column (vertical complexity)
  relief_16          mean max-min height inside 16x16 chunks with land (terrain articulation)
Usage: python tools/art_metrics.py out.json map1.vxl map2.vxl ...
"""
import json, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aosmap.vxl import load, surface_mask  # noqa: E402


def srgb_to_L(rgb):
    c = rgb / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    Y = 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]
    return np.where(Y > 0.008856, 116 * np.cbrt(Y) - 16, 903.3 * Y)


def rgb_of(col):
    col = col.astype(np.uint32)
    return np.stack([(col >> 16) & 255, (col >> 8) & 255, col & 255], -1).astype(np.float32)


def hue_bins(rgb):
    r, g, b = rgb[..., 0] / 255, rgb[..., 1] / 255, rgb[..., 2] / 255
    mx, mn = np.maximum(np.maximum(r, g), b), np.minimum(np.minimum(r, g), b)
    d = mx - mn
    sat = np.where(mx > 0, d / np.maximum(mx, 1e-6), 0)
    h = np.zeros_like(mx)
    m = d > 1e-6
    rc = np.where(m, (mx - r) / np.where(m, d, 1), 0); gc = np.where(m, (mx - g) / np.where(m, d, 1), 0)
    bc = np.where(m, (mx - b) / np.where(m, d, 1), 0)
    h = np.where(r == mx, bc - gc, np.where(g == mx, 2 + rc - bc, 4 + gc - rc))
    h = (h / 6.0) % 1.0
    bins = (h * 12).astype(int)
    bins = np.where(sat < 0.12, 12, bins)          # grey / desaturated bin
    return bins


def metrics(path):
    m, _ = load(path)
    s = m.solid
    surf = surface_mask(s)
    surf[:, :, 63] = False
    col = m.color[surf] & 0xFFFFFF
    rgb = rgb_of(col)
    res = {'map': os.path.basename(path).split('-', 1)[-1].rsplit('.', 1)[0]}
    res['colours'] = int(np.unique(col).size)
    hb = hue_bins(rgb)
    cnt = np.bincount(hb, minlength=13)
    order = np.sort(cnt)[::-1].cumsum() / cnt.sum()
    res['hue_families_90'] = int(np.searchsorted(order, 0.9) + 1)
    top = np.argmax(s, axis=2)
    land = top < 62
    xs, ys = np.indices(top.shape)
    tc = m.color[xs, ys, top] & 0xFFFFFF
    L = srgb_to_L(rgb_of(tc))
    dLs, same = [], []
    for a, b, ta, tb, la, lb, ca, cb in (
            (L[1:], L[:-1], top[1:], top[:-1], land[1:], land[:-1], tc[1:], tc[:-1]),
            (L[:, 1:], L[:, :-1], top[:, 1:], top[:, :-1], land[:, 1:], land[:, :-1], tc[:, 1:], tc[:, :-1])):
        sel = (ta == tb) & la & lb
        dLs.append(np.abs(a - b)[sel]); same.append((ca == cb)[sel])
    dL = np.concatenate(dLs); sm = np.concatenate(same)
    res['top_noise'] = round(float(dL.mean()), 2) if dL.size else None
    # spatial coherence: |dL| at distance 4 / |dL| at distance 1 on same-height land.
    # smooth gradients -> >> 1 ; per-voxel random noise -> ~1 ; flat fills -> undefined/high
    def dl_at(k):
        a, b = L[k:], L[:-k]; sel = (top[k:] == top[:-k]) & land[k:] & land[:-k]
        a2, b2 = L[:, k:], L[:, :-k]; sel2 = (top[:, k:] == top[:, :-k]) & land[:, k:] & land[:, :-k]
        v = np.concatenate([np.abs(a - b)[sel], np.abs(a2 - b2)[sel2]])
        return v.mean() if v.size else np.nan
    d1, d4 = dl_at(1), dl_at(4)
    res['coherence_4'] = round(float(d4 / d1), 2) if d1 > 1e-6 else None
    res['top_flat_pct'] = round(100 * float(sm.mean()), 1) if sm.size else None
    res['ramp_step'] = round(float(np.median(dL[~sm])), 2) if (~sm).any() else None
    h = (63 - top)[land].astype(float)
    res['height_L_corr'] = round(float(np.corrcoef(h, L[land])[0, 1]), 2) if land.sum() > 10 and h.std() > 0 else None
    # side vs top lightness: surface voxels with air above = top faces; others = sides/undersides
    up_air = np.zeros_like(s); up_air[:, :, 0] = True; up_air[:, :, 1:] = ~s[:, :, :-1]
    topface = surf & up_air
    side = surf & ~up_air
    Lt = srgb_to_L(rgb_of(m.color[topface] & 0xFFFFFF)); Ls = srgb_to_L(rgb_of(m.color[side] & 0xFFFFFF))
    res['side_minus_top_L'] = round(float(np.median(Ls) - np.median(Lt)), 1) if Ls.size and Lt.size else None
    res['vert_detail'] = round(float(surf[land].sum() / max(land.sum(), 1)), 2)
    rel = []
    for cx in range(0, 512, 16):
        for cy in range(0, 512, 16):
            ch = land[cx:cx + 16, cy:cy + 16]
            if ch.mean() > 0.5:
                t = top[cx:cx + 16, cy:cy + 16][ch]
                rel.append(int(t.max() - t.min()))
    res['relief_16'] = round(float(np.mean(rel)), 1) if rel else None
    res['land_cols'] = int(land.sum())
    return res


if __name__ == '__main__':
    out = sys.argv[1]
    rows = [metrics(p) for p in sys.argv[2:]]
    json.dump(rows, open(out, 'w'), indent=1)
    keys = ['colours', 'hue_families_90', 'coherence_4', 'top_noise', 'top_flat_pct', 'ramp_step', 'height_L_corr',
            'side_minus_top_L', 'vert_detail', 'relief_16']
    print(f"{'map':22s} " + ' '.join(f'{k[:12]:>12s}' for k in keys))
    for r in rows:
        print(f"{r['map']:22s} " + ' '.join(f'{str(r[k]):>12s}' for k in keys))
