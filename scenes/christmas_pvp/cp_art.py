"""Art pass for Christmas PVP v2: cozy Christmas evening grade + glow. Changes colours only (no geometry).

Order: per-family grade of the original (OKLab) -> paint the additions -> garlands / warm windows -> baked light + AO
(aosmap.kit.color.lighting) -> owner brightness rules (enforce_brightness) -> glow sources + bake (knowledge base
11.4 format, aosmap.kit.color.bake_glow) -> nudge lit voxels off the glow palette.
"""
from __future__ import annotations

import numpy as np

from aosmap.kit import color, noise, palette

from cp_source import CLASSES


def _oklab_grade(rgb, g):
    lab = palette.rgb_to_oklab(rgb.astype(float))
    L, a, b = lab[:, 0], lab[:, 1], lab[:, 2]
    L = L * g['L_mult'] + g['L_add']
    a, b = a * g['chroma'], b * g['chroma']
    th = np.radians(g['tint_hue'])
    a = a + g['tint_amount'] * np.cos(th)
    b = b + g['tint_amount'] * np.sin(th)
    return np.clip(palette.oklab_to_rgb(np.stack([L, a, b], 1)), 0, 255)


def _ramp(stops, t):
    return color.ramp(stops, np.clip(t, 0, 1))


def _hash(xs, ys, zs, salt):
    return noise.hash3(xs, ys, zs, salt)


def grade_original(cv, spec, seed):
    G = spec['grade']
    lay = noise.fbm2((512, 512), 48, 3, 'snow_lowfreq', seed)
    lay2 = noise.fbm2((512, 512), 12, 2, 'snow_mid', seed)
    stats = {}
    for name in CLASSES:
        mid = cv.materials['orig_' + name]
        xs, ys, zs = np.nonzero(cv.mat == mid)
        if not len(xs):
            continue
        rgb = cv.rgb[xs, ys, zs].astype(float)
        L0 = palette.rgb_to_oklab(rgb)[:, 0]
        h = _hash(xs, ys, zs, 11)
        if name == 'snow':
            tex = np.clip((L0 - 0.83) * 1.4, -0.16, 0.16)
            hfac = np.clip((62 - zs) / 40.0, 0, 1)
            t = 0.50 + tex + 0.26 * hfac + 0.22 * (lay[xs, ys] - 0.5) + 0.10 * (lay2[xs, ys] - 0.5) + 0.04 * (h - 0.5)
            out = _ramp(G['snow_ramp'], t)
        elif name == 'wall':
            band = noise.fbm2((512, 64), 16, 2, 'wall_band', seed)
            p = np.where((xs <= 92) | (xs >= 420), ys, xs)
            t = (62 - zs) / 62.0 + 0.10 * (band[p, zs] - 0.5) + 0.03 * (h - 0.5)
            out = _ramp(G['wall_ramp'], t)
        elif name == 'ice':
            t = 0.5 + (L0 - 0.76) * 2.2 + 0.16 * (lay2[xs, ys] - 0.5) + 0.06 * (h - 0.5)
            out = _ramp(G['ice_ramp'], t)
        elif name == 'water':
            t = 0.45 + (L0 - 0.50) * 1.6 + 0.30 * (lay2[xs, ys] - 0.5)
            out = _ramp(G['frozen_ramp'], t)
            crack = np.abs(noise.fbm2((512, 512), 9, 3, 'cracks', seed) - 0.5) < 0.022
            ck = crack[xs, ys]
            out[ck] = out[ck] * 0.35 + np.array(G['frost_crack']) * 0.65
            # frosted rim where the ice meets the shore
            S = cv.solid
            wm = cv.mat == mid
            shore = np.zeros(len(xs), bool)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                X, Y = np.clip(xs + dx, 0, 511), np.clip(ys + dy, 0, 511)
                shore |= (S[X, Y, zs] & ~wm[X, Y, zs]) | (S[X, Y, np.clip(zs - 1, 0, 63)] & ~wm[X, Y, np.clip(zs - 1, 0, 63)])
            out[shore] = out[shore] * 0.5 + np.array(G['frost_crack']) * 0.5
        elif name == 'glass':
            out = _ramp([(0, G['window_warm'][0]), (0.5, G['window_warm'][1]), (1, G['window_warm'][2])],
                        0.35 + 0.5 * h)
        else:
            out = _oklab_grade(rgb, G['general'])
        cv.rgb[xs, ys, zs] = np.clip(np.rint(out), 0, 255).astype(np.uint8)
        stats[name] = int(len(xs))
    return stats


ADD_PAINT = {
    'cover_leaf': [(0.0, (28, 62, 56)), (0.5, (40, 84, 64)), (1.0, (60, 108, 76))],
    'cover_trunk': [(0.0, (66, 48, 40)), (1.0, (92, 66, 50))],
    'runner': [(0.0, (70, 66, 76)), (1.0, (92, 88, 100))],
    'sleigh': [(0.0, (128, 30, 40)), (1.0, (164, 44, 50))],
    'sleigh_trim': [(0.0, (178, 136, 60)), (1.0, (210, 170, 84))],
    'sack': [(0.0, (112, 86, 64)), (1.0, (140, 108, 78))],
}
GIFT_COLOURS = [(150, 40, 52), (46, 96, 132), (62, 116, 74), (128, 70, 140), (176, 120, 48)]
RIBBON_COLOURS = [(206, 168, 80), (188, 186, 204), (170, 44, 56)]
BAUBLE_COLOURS = [(178, 40, 48), (204, 162, 66), (150, 164, 200), (124, 72, 156)]


def paint_additions(cv, spec, deco_rng):
    G = spec['grade']
    out = {}
    for name, stops in ADD_PAINT.items():
        if name not in cv.materials:
            continue
        xs, ys, zs = np.nonzero(cv.mat == cv.materials[name])
        h = _hash(xs, ys, zs, 23)
        t = h
        if name == 'cover_leaf':
            t = 0.25 + 0.5 * h + 0.25 * np.clip((62 - zs) / 22.0, 0, 1)
        cv.rgb[xs, ys, zs] = np.rint(_ramp(stops, t)).astype(np.uint8)
        out[name] = int(len(xs))
    for name, t0 in (('cover_snow', 0.78), ('drift', 0.62)):
        if name in cv.materials:
            xs, ys, zs = np.nonzero(cv.mat == cv.materials[name])
            t = t0 + 0.10 * (_hash(xs, ys, zs, 5) - 0.5) + 0.04 * (62 - zs)
            cv.rgb[xs, ys, zs] = np.rint(_ramp(G['snow_ramp'], t)).astype(np.uint8)
            out[name] = int(len(xs))
    # gifts: one colour per box (OS-seeded), ribbons in a contrasting tone; mirrored boxes keep their own draw
    from scipy import ndimage as ndi
    for name, pal in (('gift', GIFT_COLOURS), ('gift_ribbon', RIBBON_COLOURS), ('bauble', BAUBLE_COLOURS)):
        if name not in cv.materials:
            continue
        m = cv.mat == cv.materials[name]
        lab, n = ndi.label(m, structure=ndi.generate_binary_structure(3, 1))
        cols = [pal[int(i)] for i in deco_rng.integers(0, len(pal), size=n + 1)]
        xs, ys, zs = np.nonzero(m)
        c = np.array(cols, float)[lab[xs, ys, zs]]
        c *= (0.92 + 0.12 * _hash(xs, ys, zs, 9))[:, None]
        cv.rgb[xs, ys, zs] = np.clip(np.rint(c), 0, 255).astype(np.uint8)
        out[name] = int(len(xs))
    return out


def paint_garlands(cv, spec, gar):
    greens = spec['grade']['garland_greens']
    for i, p in enumerate(gar):
        h = noise.hash3(np.array([p[0]]), np.array([p[1]]), np.array([p[2]]), 31)[0]
        cv.rgb[p] = greens[int(h * len(greens)) % len(greens)]
    return len(gar)


def place_glow(cv, spec, lights):
    """lights: list of (kind, (x, y, z), colour name). Sources must be solid voxels."""
    pal = spec['glow_palette']
    n = 0
    seen = set()
    for kind, p, cname in lights:
        p = tuple(int(v) for v in p)
        if p in seen or not cv.solid[p]:
            continue
        seen.add(p)
        cv.add_glow(*p, pal[cname])
        n += 1
    return n


def nudge_off_palette(cv, stored, spec):
    """Only true sources may equal a glow-palette colour (knowledge base 11.4): nudge lit voxels by -1."""
    pal = {tuple(c) for c in spec['glow_palette'].values()}
    srcs = {(x, y, z) for (x, y, z, _) in cv.glow}
    n = 0
    for k in stored:
        if k in srcs:
            continue
        c = tuple(int(v) for v in cv.rgb[k])
        if c in pal:
            cv.rgb[k] = tuple(max(0, v - 1) for v in c)
            n += 1
    return n
