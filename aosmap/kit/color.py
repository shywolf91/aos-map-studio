"""Colour helpers and the baked colour passes.

Merged from Bloomhop geo.mix/shade/clamp8 + main.lighting / bake_glow, ds_color.lerp/ramp3, sph_color._blend
and the team_recolor functions of gf/hc/wkh_color. Owner rules enforced here: floors not near-black
(luma >= ~40), snow / whites capped (max channel ~212), glow-block format of knowledge base §11.4.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage as ndi

LUMA_FLOOR_MIN = 40
WHITE_CAP = 212


def clamp8(c):
    return tuple(int(max(0, min(255, round(v)))) for v in c)


def mix(a, b, t):
    return tuple(float(a[i]) + (float(b[i]) - float(a[i])) * t for i in range(3))


def shade(c, f):
    return clamp8((c[0] * f, c[1] * f, c[2] * f))


def hex_rgb(h: str):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def ramp(stops, t):
    """stops: [(t0, rgb), (t1, rgb), ...] sorted by t; t: array -> (..., 3) float array (linear interpolation)."""
    t = np.asarray(t, float)
    ts = np.array([s[0] for s in stops], float)
    cs = np.array([s[1] for s in stops], float)
    out = np.empty(t.shape + (3,))
    for k in range(3):
        out[..., k] = np.interp(t, ts, cs[:, k])
    return out


def luma(rgb):
    rgb = np.asarray(rgb, float)
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


def lighting(cv, sun=(0.06, 0.03, -0.05, -0.02), side_f=0.84, ao_size=5, cover_f=0.86):
    """Baked light + ambient occlusion on surface voxels (Bloomhop main.lighting): tops full, sides darker,
    a west/north key light, a 5^3 occupancy AO term and a 0.86 factor under any overhang. Skips cv.nolight."""
    S = cv.solid
    P = np.pad(S, 1, constant_values=True)
    P[:, :, 0] = False
    air = ~P
    a_xm, a_xp = air[:-2, 1:-1, 1:-1], air[2:, 1:-1, 1:-1]
    a_ym, a_yp = air[1:-1, :-2, 1:-1], air[1:-1, 2:, 1:-1]
    a_zm, a_zp = air[1:-1, 1:-1, :-2], air[1:-1, 1:-1, 2:]
    surf = S & (a_xm | a_xp | a_ym | a_yp | a_zm | a_zp)
    occ = ndi.uniform_filter(S.astype(np.float32), size=ao_size, mode='constant', cval=1.0)
    f = np.where(a_zm, 1.0, side_f).astype(np.float32)
    side = ~a_zm
    f += side * (sun[0] * a_xm + sun[1] * a_ym + sun[2] * a_xp + sun[3] * a_yp)
    f *= np.clip(1.16 - 0.42 * occ, 0.72, 1.06)
    covered = np.cumsum(S, axis=2) - S
    f *= np.where(covered > 0, cover_f, 1.0)
    m = surf & ~cv.nolight
    c = cv.rgb[m].astype(np.float32) * f[m][:, None]
    cv.rgb[m] = np.clip(c, 0, 255).astype(np.uint8)
    return surf


def bake_glow(cv, surf=None, radius=6.5, strength=0.32):
    """Warm the surfaces around each glow source and return the glow_stored_colors dict for the .txt
    (owner's glow setup, knowledge base §11.4). Sources keep their exact colour."""
    if surf is None:
        from .codec import surface_mask
        surf = surface_mask(cv.solid)
    srcs, seen = [], set()
    for (x, y, z, c) in cv.glow:
        if (x, y, z) in seen or not cv.inside(x, y, z) or not cv.solid[x, y, z]:
            continue
        seen.add((x, y, z))
        srcs.append((x, y, z, c))
    add = {}
    R = int(math.ceil(radius))
    for (x, y, z, c) in srcs:
        for dx in range(-R, R + 1):
            for dy in range(-R, R + 1):
                for dz in range(-R, R + 1):
                    d = math.sqrt(dx * dx + dy * dy + dz * dz)
                    if d >= radius or d == 0:
                        continue
                    X, Y, Z = x + dx, y + dy, z + dz
                    if not cv.inside(X, Y, Z) or not surf[X, Y, Z]:
                        continue
                    a = add.setdefault((X, Y, Z), np.zeros(3))
                    a += np.array(c) * strength * (1 - d / radius)
    stored = {}
    for k, a in add.items():
        if k in seen:
            continue
        orig = tuple(int(v) for v in cv.rgb[k])
        stored[k] = orig
        cv.rgb[k] = np.clip(np.array(orig) + a, 0, 255).astype(np.uint8)
    for (x, y, z, c) in srcs:
        cv.rgb[x, y, z] = c
        stored[(x, y, z)] = tuple(c)
    return stored, len(srcs)


def team_recolor(cv, west_rgb=(70, 90, 200), east_rgb=(200, 60, 50), mat='team', axis_x=256):
    """Voxels of material `mat` take the team colour of their half (blue west, red east)."""
    mid = cv.materials.get(mat)
    if mid is None:
        return 0
    m = cv.mat == mid
    xs = np.arange(512)[:, None, None]
    cv.rgb[m & (xs < axis_x)] = west_rgb
    cv.rgb[m & (xs >= axis_x)] = east_rgb
    return int(m.sum())


def enforce_brightness(cv, floor_min=LUMA_FLOOR_MIN, white_cap=WHITE_CAP, glow_exempt=True):
    """Owner rules: no near-black walkable tops (luma < floor_min raised) and no glaring whites (channels capped).
    Returns counts for build.json."""
    from .symmetry import standable
    st = standable(cv.solid)
    rgb = cv.rgb.astype(float)
    L = luma(rgb)
    dark = st & (L < floor_min)
    if glow_exempt:
        dark &= ~cv.nolight
    if dark.any():
        k = floor_min / np.maximum(L[dark], 1.0)
        rgb[dark] = np.clip(rgb[dark] * k[:, None] + (L[dark] < 4)[:, None] * floor_min, 0, 255)
    hot = cv.solid & (rgb.max(-1) > white_cap)
    if glow_exempt:
        hot &= ~cv.nolight
    if hot.any():
        rgb[hot] = rgb[hot] * (white_cap / rgb[hot].max(-1))[:, None]
    cv.rgb[:] = np.clip(np.rint(rgb), 0, 255).astype(np.uint8)
    return {'dark_floors_raised': int(dark.sum()), 'whites_capped': int(hot.sum())}


def colour_stats(solid, rgb_or_packed):
    """Top-surface colour stats used in reports: median luma, share of dark (<40) and bright (>212) tops."""
    from .codec import unpack_rgb
    c = np.asarray(rgb_or_packed)
    top = np.argmax(solid, axis=2)
    xs, ys = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    t = c[xs, ys, top]
    rgb = t if t.ndim == 3 and t.shape[-1] == 3 else unpack_rgb(t)
    L = luma(rgb)
    return {'top_luma_median': round(float(np.median(L)), 1),
            'top_dark_share_pct': round(100 * float((L < LUMA_FLOOR_MIN).mean()), 2),
            'top_bright_share_pct': round(100 * float((np.asarray(rgb).max(-1) > WHITE_CAP).mean()), 2)}
