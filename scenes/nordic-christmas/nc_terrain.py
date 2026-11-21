"""Hrafnfjord Yule: terrain (graybox). Heightfield from the SPEC, solid to z 63, ice as solid ice-coloured land.

Everything here is symmetric about x = 256 by formula; the canvas is mirrored afterwards anyway.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from aosmap.kit import noise
from nc_world import FC
from nordic_christmas_spec import SPEC

S = SPEC
Z = S['z']
X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
XF = np.minimum(X, 512 - X)          # folded x (west coordinate) for symmetric formulas


def _fbm(cell, octv, tag):
    return noise.fbm2((512, 512), cell, octv, tag, S['layout_seed'])


def _ramp(v, a, b):
    """0 at a, 1 at b (works both directions), clipped."""
    return np.clip((v - a) / (b - a), 0, 1)


def fell_rise():
    rises = np.zeros((512, 512))
    for u in (Y, 511 - Y):                               # north fell, south fell (mirror in y)
        ry = np.where(u < 36, 4 + 8 * u / 36, np.where(u <= 80, 12.0, np.where(u < 124, 12 * (124 - u) / 44, 0)))
        rises = np.maximum(rises, ry)
    rx = np.where(XF <= 190, 1.0, np.clip((226 - XF) / 36, 0, 1))
    bump = (_fbm(24, 3, 'fellbump') - 0.5) * 5
    r = rises * rx
    return r + bump * np.clip(r / 12, 0, 1)


def rear_hill():
    """Backdrop hill behind each Babel spawn (in the CTF strip): a broad rolling crest >= 26 wide (so it reads as
    ground, not as an object top, in the 25-window ground estimate) with +-1 bumps (no flat top), slopes 1:2."""
    rh = S['rear_hills']
    h = 8.0
    c0, c1 = 54, 80
    xs = XF
    prof = np.where(xs < c0, h * np.clip((xs - 38) / (c0 - 38), 0, 1),
                    np.where(xs > c1, h * np.clip((96 - xs) / (96 - c1), 0, 1), h))
    ty = np.minimum(_ramp(Y, rh['box'][2], 214), _ramp(Y, rh['box'][3], 298))
    bump = (_fbm(5, 2, 'hillbump') - 0.5) * 3.0
    r = prof * ty
    return np.where(r > 0, r + bump * np.clip(r / h, 0, 1), 0)


def lateral_berms():
    out = np.zeros((512, 512))
    lb = S['lateral_berms']
    xf0, xf1 = lb['x_full']
    tx = np.minimum(_ramp(XF, lb['north'][0], xf0), _ramp(XF, lb['north'][1], xf1))
    h = lb['crest_rise']
    for c in lb['crest_y']:
        ry = np.clip(h - np.maximum(0, np.abs(Y - c) - 1) / 2, 0, None)
        out = np.maximum(out, ry * tx)
    return out


def ice_mask():
    f = S['fjord']
    ch = f['channel']
    m = (X >= ch[0]) & (X <= ch[1])
    for (cx, cy, rx, ry) in ((256, 148, 34.4, 28.4), (256, 356, 34.4, 26.4)):
        m |= ((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2 <= 1
    b = f['bay']
    m |= ((X - b['cx']) / (b['rx'] + 0.4)) ** 2 + ((Y - b['cy']) / b['ry']) ** 2 <= 1
    return m


def slope_limit(H):
    """Every column at most 1 above its lowest 4-neighbour (walkable everywhere); only lowers columns."""
    hh = 63 - H
    for _ in range(60):
        e = np.pad(hh, 1, mode='edge')
        nb = np.minimum.reduce([e[:-2, 1:-1], e[2:, 1:-1], e[1:-1, :-2], e[1:-1, 2:]])
        new = np.minimum(hh, nb + 1)
        if (new == hh).all():
            break
        hh = new
    return 63 - hh


def heightfield():
    roll = np.rint(_fbm(48, 3, 'roll') * 2 - 1)
    h = fell_rise() + rear_hill() + lateral_berms()
    H = (Z['land'] - np.rint(h) + roll).astype(int)
    zone = np.full((512, 512), 'ground', object)
    # spawn squares: gentle mounds 39..41
    for (bx, by) in S['babel']['bases']:
        hf = S['babel']['spawn_half']
        sl = (slice(bx - hf, bx + hf + 1), slice(by - hf, by + hf + 1))
        H[sl] = np.clip(H[sl], *S['z']['spawn_floor'])
    # tower zone + anchor ground: flat z 40
    for k in ('blue', 'red'):
        a = S['anchor'][k]
        t = S['tower_zone'][k]
        H[min(a[0], t[0]):max(a[1], t[1]) + 1, a[2]:a[3] + 1] = Z['anchor']
    H = slope_limit(H)
    # ice: fjord, pools, bay (banks 41 / 42, floor 43); farm ponds 41
    ice = ice_mask()
    d = ndi.distance_transform_cdt(ice, metric='taxicab')
    H = np.where(ice, np.where(d <= 1, 41, np.where(d <= 2, 42, Z['ice'])), H)
    zone[ice] = 'ice'
    zone[ice & (d <= 2)] = 'bank'
    for (cx, cy, r, ztop) in ((256, 148, 16, 40), (256, 356, 20, 41)):          # holms
        rr = np.hypot(X - cx, Y - cy)
        hz = np.where(rr <= r - 2, ztop, np.where(rr <= r - 1, ztop + 1, np.where(rr <= r, ztop + 2, 99)))
        hz = np.minimum(hz, Z['ice'])
        m = rr <= r
        H = np.where(m, np.minimum(H, hz), H)
        zone[m & (rr <= r - 2)] = 'holm'
    p = S['farm_pond']
    for cx in (p['cx'], 512 - p['cx']):
        m = ((X - cx) / p['rx']) ** 2 + ((Y - p['cy']) / p['ry']) ** 2 <= 1
        H = np.where(m, p['z'], H)
        zone[m] = 'ice'
    H = slope_limit(H)
    # zones for colour
    for k in ('blue', 'red'):
        s = S['ctf_strip'][k]
        m = (X >= s[0]) & (X <= s[1]) & (Y >= s[2]) & (Y <= s[3]) & (zone == 'ground')
        zone[m] = 'field'
    zone[(fell_rise() > 1.5) & (zone == 'ground')] = 'fell'
    zone[(lateral_berms() > 1.5) & (zone == 'ground')] = 'berm'
    zone[(rear_hill() > 1.5) & (zone == 'field')] = 'hill'
    return H, zone, ice


def build_terrain(cv):
    H, zone, ice = heightfield()
    lut = {k: np.array(FC[k], np.uint8) for k in ('ground', 'field', 'fell', 'ice', 'bank', 'holm', 'berm', 'hill')}
    col = np.zeros((512, 512, 3), np.uint8)
    for k, c in lut.items():
        col[zone == k] = c
    cv.fill_terrain(H, lambda xs, ys, zs: col[xs, ys], 'ground')
    m = np.zeros(cv.solid.shape, bool)
    m[ice] = True
    cv.mat[m & cv.solid] = cv.material('ice')
    return {'ice_share': round(float(ice.mean()), 3), 'zone': zone, 'ice': ice}
