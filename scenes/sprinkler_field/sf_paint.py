"""Sprinkler Field paint: material -> colour for every solid voxel (after the mirror, the axis objects and the
one-offs; before baked light). Coherent noise fields + per-object maths; no new geometry.

paint(cv, rep, S, seed)
    interior voxels: material base colour (soil gets packed-soil banding by depth, so digging reveals strata)
    surface voxels:  one handler per material (lawn moss carpet with clippings, soil with damp patches / worm casts /
                     grit / root hairs, mud trail, pale sky-reflecting puddles, ant-hill crumbs, packed tunnel floors;
                     hose ribbing + wide soft stripe + water beads + torn split; galvanised sprinkler with spangle,
                     rivets and scuffs, orange collar, brass with thread grooves; brushed trowel steel with soil smears
                     and rust freckles, ochre handle grain, ferrule; terracotta pot with throwing rings and bloom; teal
                     canvas glove with ochre ribbed cuff and stitching; spiral-banded snail shell; strata + lichen per
                     pebble stone type; acorn / pinecone scales; twig bark, knots and lichen; fallen-leaf veins ...)
    plants:          each grass blade (and its east twin) draws its own colour family (emerald, chartreuse, olive,
                     teal, dry straw) with a base -> tip gradient, midrib and darker edges; colour-only details drawn
                     in art_west (withered tip, chewed notch, aphids, moss collar, pollen, wet streak ...)
Add-on / flush-detail / sky voxels keep the colours set when they were placed. Glow sources are never painted.
"""
from __future__ import annotations

import math
from types import SimpleNamespace

import numpy as np

from aosmap.kit import color, noise

from sf_build import hose_lift, polyline_field

SKIP = ('beetle', 'snail_s', 'caterpillar', 'firefly', 'grass_seed', 'silk', 'spider', 'clover_flower', 'bud',
        'dew_bead', 'dew_glow', 'gill_glow', 'sky')

MOSS = (78, 106, 52)
SOIL = (108, 82, 60)

# fallback / interior colour per material
BASE = {
    'air': SOIL, 'soil': SOIL, 'lawn': (74, 102, 50), 'spawn': (88, 108, 58), 'front': (96, 98, 60),
    'anchor': (124, 98, 72), 'bank': (116, 90, 64), 'trail': (88, 68, 52), 'puddle': (150, 160, 170),
    'hose': (46, 118, 58), 'hose_stripe': (204, 180, 66), 'brick': (150, 92, 70), 'crater': (140, 106, 72),
    'tunnel': (116, 90, 66), 'crown': (122, 104, 66), 'blade': (70, 130, 64), 'clover': (58, 124, 66),
    'stalk': (112, 150, 84), 'seedhead': (196, 196, 188), 'dandelion_stalk': (112, 150, 82),
    'pebble': (146, 140, 132), 'mushroom_cap': (176, 128, 86), 'mushroom_stem': (198, 188, 166),
    'acorn': (156, 108, 56), 'acorn_cap': (112, 88, 60), 'twig': (104, 82, 62), 'leaf': (172, 124, 56),
    'cap': (184, 150, 62), 'cap_inner': (188, 182, 164), 'pinecone': (124, 86, 54), 'pinecone_dk': (94, 66, 44),
    'daisy': (200, 198, 190), 'daisy_eye': (210, 168, 46), 'seed': (96, 90, 74), 'dew': (176, 194, 200),
    'sprout': (132, 186, 90), 'pad': (146, 150, 150), 'leg': (150, 154, 158), 'rivet': (112, 114, 120),
    'collar': (206, 118, 46), 'riser': (148, 150, 154), 'step': (178, 142, 66), 'brass': (184, 150, 72),
    'arm': (160, 128, 66), 'tbar': (190, 158, 76), 'spring': (96, 96, 102), 'coupling': (182, 148, 70),
    'heap': (122, 92, 64), 'blade_steel': (166, 170, 174), 'rib': (150, 154, 158), 'handle': (176, 136, 70),
    'ferrule': (156, 158, 162), 'concrete': (158, 156, 148), 'tap': (184, 150, 72), 'reel': (44, 112, 56),
    'cart': (126, 130, 132), 'wheel': (54, 56, 60), 'pot': (184, 106, 66), 'potsoil': (80, 62, 48),
    'glove': (96, 132, 126), 'glove_cuff': (184, 148, 70), 'shell': (190, 164, 120), 'shell_dk': (132, 98, 70),
    'label': (196, 198, 184), 'print': (100, 80, 62), 'key': (98, 98, 102), 'stair': (150, 120, 84),
    'floor': (150, 118, 80),
}


def _r(stops, t):
    return color.ramp(stops, np.clip(t, 0, 1))


def _mix(col, target, t):
    t = np.asarray(t, float)
    if t.ndim == 0:
        t = np.full(len(col), float(t))
    return col * (1 - t[:, None]) + np.asarray(target, float)[None, :] * t[:, None]


def _h(x, y, z, salt):
    with np.errstate(over='ignore'):
        return noise.hash3(x, y, z, salt)


# =============================================================================================== feature owners

def _features(rep):
    """West features + their east twins. Each entry: dict(f=..., side='W'|'E'|'C', cx=placed x)."""
    out = []
    for f in rep.get('features', []):
        if abs(f['x'] - 256) < 1:
            out.append({'f': f, 'side': 'C', 'cx': f['x']})
        else:
            out.append({'f': f, 'side': 'W', 'cx': f['x']})
            out.append({'f': f, 'side': 'E', 'cx': 512 - f['x']})
    return out


def _owner(entries, pad):
    own = -np.ones((512, 512), np.int32)
    best = np.full((512, 512), np.inf)
    for i, e in enumerate(entries):
        f = e['f']
        r = (f.get('L', 0) or f['r_top']) + pad
        x0, x1 = max(0, int(e['cx'] - r - 1)), min(511, int(e['cx'] + r + 2))
        y0, y1 = max(0, int(f['y'] - r - 1)), min(511, int(f['y'] + r + 2))
        X, Y = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1), indexing='ij')
        d = np.hypot(X - e['cx'], Y - f['y'])
        sub_b = best[x0:x1 + 1, y0:y1 + 1]
        m = (d <= r) & (d < sub_b)
        own[x0:x1 + 1, y0:y1 + 1][m] = i
        sub_b[m] = d[m]
    return own


GROUPS = {'pebble': ('pebble',), 'clover': ('clover', 'clover_low'), 'dandelion': ('dandelion',),
          'mushroom': ('mushroom',), 'acorn': ('acorn',), 'twig': ('twig',), 'leaf': ('leaf',), 'cap': ('cap',),
          'pinecone': ('pinecone',), 'tussock': ('tussock',), 'front': ('front',)}


# =============================================================================================== context

def _context(cv, xs, ys, zs, F, up):
    C = SimpleNamespace()
    C.x, C.y, C.z = xs, ys, zs
    C.xw = np.where(xs > 256, 512 - xs, xs)
    C.east = xs > 256
    C.up = up[xs, ys, zs]
    C.a, C.b, C.c, C.d, C.e = (F[k][xs, ys] for k in ('a', 'b', 'c', 'd', 'e'))
    C.v = 0.5 * (F['vxz'][xs, zs] + F['vyz'][ys, zs])
    C.h = _h(xs, ys, zs, 11)
    C.h2 = _h(xs, ys, zs, 29)
    C.H = cv.H[xs, ys].astype(int)
    return C


def _sub(C, k):
    """Context restricted to mask k."""
    D = SimpleNamespace()
    for name, v in vars(C).items():
        D.__dict__[name] = v[k] if isinstance(v, np.ndarray) and v.shape[:1] == C.x.shape[:1] else v
    return D


# =============================================================================================== terrain

def soil_top(c):
    col = _r([(0, (94, 70, 50)), (0.4, (110, 82, 58)), (0.7, (126, 96, 66)), (1, (120, 94, 70))],
             c.a * 0.75 + c.h * 0.25)
    damp = np.clip((c.d - 0.55) * 4, 0, 1)
    col = col * (1 - 0.15 * damp)[:, None] + np.array([-2, -1, 2]) * damp[:, None]
    x, y = c.x, c.y
    cast = (_h(x // 3, y // 3, 0, 5) > 0.93) & (((x % 3) != 1) | ((y % 3) != 1))
    col[cast] = col[cast] * 0.45 + np.array([136, 116, 92]) * 0.55
    grit = c.h2 > 0.986
    col[grit] = col[grit] * 0.5 + np.array([162, 150, 130]) * 0.5
    root = (np.abs(np.sin((x + 54 * c.e) * 0.33 + y * 0.11)) < 0.05) & (c.b > 0.62)
    col[root] = col[root] * 0.5 + np.array([150, 120, 88]) * 0.5
    return col


def soil_side(c):
    band = 0.5 + 0.5 * np.sin(c.z * 1.9 + c.v * 7)
    col = _r([(0, (96, 72, 52)), (0.5, (112, 86, 62)), (1, (130, 100, 70))], band * 0.7 + c.h * 0.3)
    stone = _h(c.x // 2, c.y // 2, c.z // 2, 7) > 0.965
    col[stone] = np.array([132, 124, 112]) * (0.9 + 0.2 * c.h[stone])[:, None]
    root = c.h2 > 0.993
    col[root] = (170, 138, 96)
    deep = c.z >= 55                                            # tunnel walls: a touch lighter (they sit in shadow)
    col[deep] *= 1.14
    return col


def lawn_top(c):
    col = _r([(0, (58, 84, 44)), (0.3, (70, 100, 50)), (0.55, (84, 112, 54)), (0.8, (100, 120, 58)),
              (1, (116, 124, 64))], c.a * 0.65 + c.c * 0.25 + c.h * 0.10)
    col = _mix(col, (136, 120, 78), np.clip((c.b - 0.58) * 3, 0, 0.55))
    x, y = c.x, c.y
    s = np.where(c.d > 0.5, _h(x, y // 7, 0, 13), _h(x // 7, y, 0, 14))
    clip_ = s > 0.955
    dry = _h(x // 7, y // 7, 1, 15) > 0.45
    col[clip_ & dry] = col[clip_ & dry] * 0.55 + np.array([166, 150, 94]) * 0.45
    col[clip_ & ~dry] = col[clip_ & ~dry] * 0.55 + np.array([104, 146, 64]) * 0.45
    star = (_h(x // 2, y // 2, 3, 16) > 0.992)
    col[star] = col[star] * 0.5 + np.array([126, 150, 72]) * 0.5          # moss stars
    col[c.c > 0.78] *= 1.06
    return col


def h_soil(c):
    out = soil_side(c)
    out[c.up] = soil_top(_sub(c, c.up))
    return out


def h_lawn(c):
    out = soil_side(c)
    out[c.up] = lawn_top(_sub(c, c.up))
    return out


def h_spawn(c):
    out = lawn_top(c)
    out = _mix(out, (140, 126, 84), 0.18 + 0.12 * c.c) * 1.04
    return out


def h_front(c):
    t = np.clip((c.xw - 139) / 60.0, 0, 1)
    a = lawn_top(c)
    b = soil_top(c) * 1.04
    return a * (1 - 0.7 * t)[:, None] + b * (0.7 * t)[:, None]


def h_anchor(c):
    return _mix(soil_top(c) * 1.05, (150, 128, 96), 0.15)


def h_bank(c):
    col = soil_top(c) * 1.03
    x, y = c.x, c.y
    cast = (_h(x // 3, y // 3, 0, 6) > 0.6) & (((x % 3) != 1) | ((y % 3) != 1))
    col[cast] = col[cast] * 0.4 + np.array([140, 120, 96]) * 0.6
    side = ~c.up
    col[side] = soil_side(_sub(c, side))
    return col


def h_trail(c):
    col = _r([(0, (80, 60, 46)), (0.6, (92, 70, 54)), (1, (100, 78, 60))], c.a * 0.7 + c.h * 0.3)
    wet = c.c > 0.6
    col[wet] = col[wet] * 0.6 + np.array([118, 102, 88]) * 0.4
    edge = (np.abs(c.y - 384) <= 1) | (np.abs(c.y - 396) <= 1)
    col[edge] *= 0.92
    tread = (_h(c.x // 3, c.y, 0, 17) > 0.9) & ~wet
    col[tread] *= 0.93
    return col


def make_puddle(S):
    P = [(px, py, pr) for (px, py, pr) in S['puddles']]
    P += [(px, py, pr) for (k, px, py, pr) in S['under_platform'] if k == 'puddle']
    P += [(512 - px, py, pr) for (px, py, pr) in P if abs(px - 256) > 1]

    def h_puddle(c):
        best = np.full(len(c.x), 99.0)
        for (px, py, pr) in P:
            best = np.minimum(best, np.hypot(c.x - px, c.y - py) / pr)
        dist = best
        col = np.zeros((len(c.x), 3))
        ripple = 0.03 * np.sin(dist * 14)
        water = _r([(0, (172, 182, 198)), (0.5, (164, 176, 192)), (0.8, (150, 158, 164)), (1.0, (122, 114, 98))],
                   dist)
        col[:] = water * (1 + ripple)[:, None]
        rim = c.z <= 53
        col[rim] = col[rim] * 0.55 + np.array([118, 110, 94]) * 0.45
        foot = dist > 1.25                                      # sneaker-print tread puddles
        col[foot] = _mix(np.tile([[142, 150, 154]], (int(foot.sum()), 1)).astype(float), (112, 102, 88),
                         0.35 * c.h[foot])
        col[~c.up] = (104, 84, 64)
        return col
    return h_puddle


def h_crater(c):
    col = _r([(0, (126, 94, 64)), (0.5, (142, 108, 74)), (1, (156, 120, 82))], c.a * 0.6 + c.h * 0.4)
    crumb = _h(c.x // 2, c.y // 2, c.z // 2, 3)
    col *= (0.88 + 0.24 * crumb)[:, None]
    ant = c.up & (_h(c.x, c.y, 0, 77) > 0.994)
    col[ant] = (66, 54, 46)
    return col


def h_tunnel(c):
    col = _r([(0, (106, 82, 60)), (0.5, (118, 92, 66)), (1, (128, 100, 72))], c.a * 0.5 + c.h * 0.5)
    trod = _h(c.x // 3, c.y // 3, 0, 19) > 0.7
    col[trod] *= 0.95
    return col


def h_heap(c):
    col = _r([(0, (110, 82, 58)), (0.5, (126, 94, 66)), (1, (138, 104, 72))], c.a * 0.5 + c.h * 0.5)
    col *= (0.88 + 0.24 * _h(c.x // 2, c.y // 2, c.z // 2, 23))[:, None]
    bits = c.h2 > 0.985
    col[bits] = (166, 134, 94)
    st = _h(c.x // 2, c.y // 2, c.z // 2, 24) > 0.975
    col[st] = (140, 134, 122)
    return col


def h_print(c):
    col = _r([(0, (92, 72, 56)), (1, (108, 86, 66))], c.a * 0.5 + c.h * 0.5)
    col[c.c > 0.65] *= 1.06
    return col


def h_potsoil(c):
    col = _r([(0, (70, 54, 42)), (0.5, (82, 62, 48)), (1, (92, 70, 52))], c.a * 0.5 + c.h * 0.5)
    perl = c.h2 > 0.965
    col[perl] = (186, 182, 170)
    bark = (_h(c.x // 2, c.y // 2, c.z, 9) > 0.93) & ~perl
    col[bark] = (122, 86, 56)
    return col


# =============================================================================================== plants

def h_crown(c, ctx):
    E, own = ctx['tussock']
    i = own[c.x, c.y]
    cx = np.array([E[j]['f']['x'] if j >= 0 else 0 for j in i], float)
    cy = np.array([E[j]['f']['y'] if j >= 0 else 0 for j in i], float)
    a = np.arctan2(c.y - cy, c.xw - cx)
    streak = np.sin(a * 13 + c.z * 0.7 + 2 * c.h)
    col = _r([(0, (94, 82, 54)), (0.5, (122, 104, 66)), (1, (150, 130, 84))], 0.5 + 0.4 * streak + (c.h - 0.5) * 0.2)
    moss = c.up & (c.b > 0.52)
    col[moss] = col[moss] * 0.55 + np.array(MOSS) * 0.45
    return col


def _fparams(E, idx, key, default=0.0):
    return np.array([float(E[j]['f'].get(key, default)) if j >= 0 else default for j in idx])


def _fdet(E, idx, dets, name):
    return np.array([j >= 0 and name in dets.get(E[j]['f']['name'], ()) for j in idx])


def h_clover(c, ctx):
    E, own = ctx['clover']
    i = own[c.x, c.y]
    dets = ctx['dets']
    cx, cy = _fparams(E, i, 'x'), _fparams(E, i, 'y')
    R, rot, zc = _fparams(E, i, 'R', 6), _fparams(E, i, 'rot'), _fparams(E, i, 'zc')
    px, py = c.xw + 0.5, c.y + 0.5
    ox, oy = cx + 0.5, cy + 0.5
    ang = np.arctan2(py - oy, px - ox)
    kk = np.round(((ang - rot) % (2 * np.pi)) / (2 * np.pi / 3)).astype(int) % 3
    ak = rot + kk * 2 * np.pi / 3
    lx, ly = ox + 0.5 * R * np.cos(ak), oy + 0.5 * R * np.sin(ak)
    rl = 0.55 * R
    u = ((px - lx) * np.cos(ak) + (py - ly) * np.sin(ak)) / rl
    vv = (-(px - lx) * np.sin(ak) + (py - ly) * np.cos(ak)) / rl
    rr = np.hypot(u, vv)
    fam = np.array([ctx['fam'][j % len(ctx['fam'])] if j >= 0 else 0 for j in i])
    bases = np.array([(50, 116, 60), (58, 126, 62), (46, 110, 74), (66, 128, 58)], float)
    base = bases[fam % 4]
    light = base * 1.28
    t = np.clip(0.55 - 0.45 * rr + 0.2 * (c.h - 0.5), 0, 1)
    col = base * (1 - t)[:, None] + light * t[:, None]
    col[rr > 0.82] *= 0.9
    col[c.z < zc] *= 0.92                                     # cupped rim layer
    curve = -0.15 + 0.85 * np.abs(vv)
    chev = (np.abs(u - curve) < 0.14) & (rr < 0.88)
    col[chev] = col[chev] * 0.3 + np.array([162, 198, 152]) * 0.7
    vein = (np.abs(vv) < 0.07) & (u > -0.9)
    col[vein] *= 1.1
    hub = rr > 1.15                                           # connector box round the stalk top
    col[hub] = base[hub] * 0.95
    wl = _fdet(E, i, dets, 'withered leaflet') & (kk == (np.abs(i) % 3))
    col[wl] = col[wl] * 0.35 + np.array([176, 152, 84]) * 0.65
    spot = wl & (c.h > 0.82)
    col[spot] = (128, 98, 58)
    ch = _fdet(E, i, dets, 'chewed holes') | _fdet(E, i, dets, 'chewed notch')
    for (u0, v0) in ((0.25, 0.32), (-0.1, -0.4)):
        dd = np.hypot(u - u0, vv - v0)
        ring = ch & (dd < 0.24) & (kk != 1)
        col[ring] = (120, 96, 58)
        col[ring & (dd < 0.13)] = (176, 160, 104)
    we = _fdet(E, i, dets, 'withered edge') & (rr > 0.75)
    col[we] = col[we] * 0.4 + np.array([176, 150, 90]) * 0.6
    po = _fdet(E, i, dets, 'pollen dusting') & c.up & (c.h > 0.8)
    col[po] = col[po] * 0.4 + np.array([206, 192, 112]) * 0.6
    ap = _fdet(E, i, dets, 'aphids') & (c.h2 > 0.9)
    col[ap] = (178, 206, 108)
    return col


def h_stalk(c, ctx):
    hh = (c.H - c.z).astype(float)
    col = _r([(0, (96, 124, 70)), (0.4, (114, 152, 86)), (1, (132, 170, 98))], hh / 16 + (c.h - 0.5) * 0.08)
    E, own = ctx['clover']
    i = own[c.x, c.y]
    dets = ctx['dets']
    mc = _fdet(E, i, dets, 'moss collar') & (hh < 3.5)
    col[mc] = np.array(MOSS) * (0.9 + 0.2 * c.h[mc])[:, None]
    ap = _fdet(E, i, dets, 'aphids') & (hh > 3) & (c.h2 > 0.8)
    col[ap] = (178, 206, 108)
    return col


def h_dstalk(c, ctx):
    E, own = ctx['dandelion']
    i = own[c.x, c.y]
    dets = ctx['dets']
    hh = (c.H - c.z).astype(float)
    hgt = _fparams(E, i, 'hgt', 32)
    col = _r([(0, (98, 128, 68)), (0.5, (112, 150, 82)), (1, (124, 162, 90))], hh / np.maximum(hgt, 1))
    col *= (0.96 + 0.08 * ((c.x + c.y) % 2))[:, None]
    rec = hh > hgt - 1
    col[rec] = (92, 118, 62)
    mc = _fdet(E, i, dets, 'moss collar') & (hh < 3.5)
    col[mc] = np.array(MOSS) * (0.9 + 0.2 * c.h[mc])[:, None]
    ap = _fdet(E, i, dets, 'aphids') & (hh > 3) & (c.h2 > 0.82)
    col[ap] = (178, 206, 108)
    return col


def h_seedhead(c, ctx):
    E, own = ctx['dandelion']
    i = own[c.x, c.y]
    dets = ctx['dets']
    gx, gy, gz = _fparams(E, i, 'x'), _fparams(E, i, 'y'), _fparams(E, i, 'gz')
    dx, dy, dz = c.xw - gx, c.y - gy, c.z - gz
    n = np.maximum(np.sqrt(dx * dx + dy * dy + dz * dz), 0.5)
    th = np.arctan2(dy, dx)
    ph = np.arcsin(np.clip(-dz / n, -1, 1))
    cell = _h(np.floor((th + np.pi) / (2 * np.pi) * 16).astype(int), np.floor((ph + np.pi / 2) / np.pi * 10).astype(int),
              i, 41)
    col = np.tile(np.array([[200.0, 200, 192]]), (len(c.x), 1))
    col[cell > 0.86] = (172, 162, 138)                         # achenes showing through
    col[cell < 0.3] = (208, 206, 198)                          # pappus tips
    col[(cell >= 0.3) & (cell <= 0.86) & (c.h > 0.7)] = (192, 192, 184)
    col[ph > 0.4] *= 1.03
    bald = _fdet(E, i, dets, 'bald patch')
    if bald.any():
        az = _h(i, 0, 0, 43) * 2 * np.pi
        d0 = np.stack([np.cos(az) * 0.9, np.sin(az) * 0.9, np.full(len(az), 0.43)], 1)
        dot = (dx * d0[:, 0] + dy * d0[:, 1] - dz * d0[:, 2]) / n
        bp = bald & (dot > 0.7)
        col[bp] = np.where(((c.x + c.y + c.z) % 2 == 0)[bp, None], np.array([[156, 134, 96]]),
                           np.array([[132, 114, 82]]))
    return col


def h_mcap(c, ctx):
    E, own = ctx['mushroom']
    i = own[c.x, c.y]
    dets = ctx['dets']
    cx, cy, R = _fparams(E, i, 'x'), _fparams(E, i, 'y'), _fparams(E, i, 'R', 7)
    rr = np.hypot(c.xw - cx, c.y - cy) / np.maximum(R, 1)
    a = np.arctan2(c.y - cy, c.xw - cx)
    tint = np.array([[1.0, 1.0, 1.0], [1.04, 0.96, 0.9], [0.96, 0.98, 1.0], [1.02, 1.02, 0.92]])
    tt = tint[np.abs(i) % 4]
    col = _r([(0, (150, 100, 66)), (0.5, (176, 128, 86)), (1, (194, 152, 106))], rr) * tt
    spots = c.up & (_h(c.x // 2, c.y // 2, i, 45) > 0.8) & (rr < 0.85)
    col[spots] = (204, 190, 160)
    under = ~c.up
    gill = np.abs(np.sin(a * 22)) < 0.35
    col[under & gill] = (150, 124, 98)
    col[under & ~gill] = (186, 164, 132)
    sb = _fdet(E, i, dets, 'slug bite')
    if sb.any():
        a0 = _h(i, 1, 0, 47) * 2 * np.pi - np.pi
        da = np.abs((a - a0 + np.pi) % (2 * np.pi) - np.pi)
        bite = sb & (rr > 0.72) & (da < 0.32)
        col[bite] = (206, 196, 170)
        col[sb & (rr > 0.6) & (da < 0.45) & ~bite] *= 0.85
    sd = _fdet(E, i, dets, 'spore dust') & c.up & (c.h > 0.55)
    col[sd] = col[sd] * 0.7 + np.array([196, 172, 132]) * 0.3
    cc = _fdet(E, i, dets, 'cap cracks') & c.up & (np.abs(np.sin(a * 7 + rr * 9)) < 0.1) & (rr > 0.3)
    col[cc] = (206, 190, 156)
    return col


def h_mstem(c, ctx):
    E, own = ctx['mushroom']
    i = own[c.x, c.y]
    dets = ctx['dets']
    hh = (c.H - c.z).astype(float)
    hgt = _fparams(E, i, 'hgt', 10)
    col = np.array([198.0, 188, 166]) * (0.96 + 0.08 * c.h)[:, None]
    col[np.abs(hh - (hgt - 3)) < 0.5] *= 0.88                  # annulus
    col[hh < 2] = (164, 144, 112)
    mc = _fdet(E, i, dets, 'moss collar') & (hh < 3.5)
    col[mc] = np.array(MOSS) * (0.9 + 0.2 * c.h[mc])[:, None]
    return col


def h_daisy(c, ctx):
    E, own = ctx['front']
    i = own[c.x, c.y]
    dets = ctx['dets']
    cx, cy = _fparams(E, i, 'x'), _fparams(E, i, 'y')
    rr = np.hypot(c.xw - cx - 0.5, c.y - cy - 0.5)
    a = np.arctan2(c.y - cy - 0.5, c.xw - cx - 0.5)
    col = _r([(0, (190, 194, 160)), (0.45, (200, 198, 190)), (1, (206, 202, 186))], rr / 3.6)
    col[np.abs(np.sin(a * 8)) < 0.2] *= 0.86
    we = _fdet(E, i, dets, 'withered edge') & (rr > 2.8)
    col[we] = (178, 162, 120)
    ch = _fdet(E, i, dets, 'chewed notch') & (np.abs(a - 0.8) < 0.35) & (rr > 2.4)
    col[ch] = (150, 140, 110)
    return col


def h_daisy_eye(c, ctx):
    col = np.where(((c.x + c.y) % 2 == 0)[:, None], np.array([[212, 170, 46]]), np.array([[188, 140, 38]])).astype(float)
    E, own = ctx['front']
    i = own[c.x, c.y]
    po = _fdet(E, i, ctx['dets'], 'pollen dusting') & (c.h > 0.5)
    col[po] = (214, 192, 96)
    return col


def h_sprout(c, ctx):
    hh = (c.H - c.z).astype(float)
    col = _r([(0, (110, 160, 76)), (0.6, (132, 186, 90)), (1, (150, 198, 106))], hh / 8)
    col[c.up] *= 1.05
    E, own = ctx['front']
    i = own[c.x, c.y]
    dets = ctx['dets']
    we = _fdet(E, i, dets, 'withered edge') & (c.h > 0.6) & (hh > 5)
    col[we] = (172, 160, 96)
    ap = _fdet(E, i, dets, 'aphids') & (c.h2 > 0.85)
    col[ap] = (180, 208, 112)
    mc = _fdet(E, i, dets, 'moss collar') & (hh < 2)
    col[mc] = MOSS
    return col


def h_seed(c, ctx):
    E, own = ctx['front']
    i = own[c.x, c.y]
    cy = _fparams(E, i, 'y')
    stripe = (np.round(c.y - cy).astype(int) % 2) == 0
    col = np.where(stripe[:, None], np.array([[84, 76, 62]]), np.array([[150, 144, 124]])).astype(float)
    return col * (0.95 + 0.1 * c.h)[:, None]


def h_dew(c):
    col = np.tile(np.array([[132.0, 150, 148]]), (len(c.x), 1))
    col[c.up] = (182, 198, 206)
    col[c.up & (c.h > 0.7)] = (204, 210, 212)
    return col


def h_pebble(c, ctx):
    E, own = ctx['pebble']
    i = own[c.x, c.y]
    g = _fparams(E, i, 'g', 52)
    kind = (np.abs(i) * 7 + ctx['salt']) % 5
    v = c.v
    col = np.zeros((len(c.x), 3))
    strata = np.sin(c.z * 1.5 + v * 5)
    # granite
    k = kind == 0
    col[k] = np.array([150, 142, 136]) * (0.95 + 0.05 * strata[k])[:, None]
    sp = k & (c.h > 0.78)
    col[sp] = (98, 94, 92)
    sp = k & (c.h < 0.12)
    col[sp] = (178, 154, 144)
    # sandstone
    k = kind == 1
    col[k] = _r([(0, (148, 122, 88)), (0.5, (170, 144, 106)), (1, (184, 160, 120))], 0.5 + 0.5 * strata[k])
    # slate (grey-green)
    k = kind == 2
    col[k] = np.array([112, 118, 112]) * (0.93 + 0.07 * np.sin(c.z[k] * 2.3))[:, None]
    # quartzite with rusty veins
    k = kind == 3
    col[k] = np.array([186, 180, 166]) * (0.96 + 0.04 * strata[k])[:, None]
    vein = k & (np.abs(np.sin(c.xw * 0.4 + c.y * 0.3 + c.z)) < 0.07)
    col[vein] = (160, 120, 84)
    # flint with chalky cortex
    k = kind == 4
    col[k] = np.array([106, 98, 90]) * (0.96 + 0.08 * c.h[k])[:, None]
    cortex = k & c.up & (c.b > 0.45)
    col[cortex] = (176, 170, 156)
    col *= (0.97 + 0.06 * c.h)[:, None]
    lich = c.up & (c.e > 0.6)
    yel = _h(c.x // 3, c.y // 3, 0, 49) > 0.5
    col[lich & yel] = col[lich & yel] * 0.35 + np.array([176, 170, 92]) * 0.65
    col[lich & ~yel] = col[lich & ~yel] * 0.35 + np.array([150, 160, 130]) * 0.65
    base = ~c.up & (c.z >= g - 2)
    col[base] = col[base] * 0.6 + np.array(MOSS) * 0.4
    return col


def h_acorn(c, ctx):
    E, own = ctx['acorn']
    i = own[c.x, c.y]
    cx, cy, g, R = _fparams(E, i, 'x'), _fparams(E, i, 'y'), _fparams(E, i, 'g', 52), _fparams(E, i, 'R', 5)
    a = np.arctan2(c.y - cy, c.xw - cx)
    t = np.clip((g - c.z) / (2 * R), 0, 1)
    col = _r([(0, (118, 84, 48)), (0.4, (154, 106, 56)), (0.8, (162, 122, 64)), (1, (150, 132, 72))], t)
    col *= (1 + 0.06 * np.sin(a * 14))[:, None]
    col[c.up & (c.h > 0.6)] *= 1.06
    return col


def h_acorn_cap(c, ctx):
    E, own = ctx['acorn']
    i = own[c.x, c.y]
    cx, cy = _fparams(E, i, 'x'), _fparams(E, i, 'y')
    a = np.arctan2(c.y - cy, c.xw - cx)
    sc = (np.floor(a * 10 / np.pi).astype(int) + c.z) % 2
    col = np.where(sc[:, None] == 0, np.array([[120, 94, 64]]), np.array([[98, 76, 52]])).astype(float)
    rim = ~c.up & (c.h > 0.5)
    col[rim] *= 1.08
    return col


def h_twig(c, ctx):
    E, own = ctx['twig']
    i = own[c.x, c.y]
    cx, cy, ang, L = _fparams(E, i, 'x'), _fparams(E, i, 'y'), _fparams(E, i, 'ang'), _fparams(E, i, 'L', 6)
    ux, uy = np.cos(ang), np.sin(ang)
    u = (c.xw - cx) * ux + (c.y - cy) * uy
    v = -(c.xw - cx) * uy + (c.y - cy) * ux
    col = np.array([104.0, 82, 62]) * (0.94 + 0.12 * c.h)[:, None]
    fis = np.sin(v * 3.0 + 0.5 * np.sin(u * 0.4) + c.z * 1.1) > 0.72
    col[fis] *= 0.8
    k0 = (_h(i, 2, 0, 51) - 0.5) * L
    knot = np.hypot(u - k0, v * 1.4) < 1.6
    col[knot] = (74, 58, 44)
    col[np.hypot(u - k0, v * 1.4) < 0.7] = (92, 74, 54)
    lich = c.up & (c.b > 0.6)
    col[lich] = col[lich] * 0.35 + np.array([150, 158, 120]) * 0.65
    end = (np.abs(u) > L - 1.5) & (i >= 0)
    col[end] = (178, 150, 104)
    col[i < 0] = np.array([104.0, 82, 62]) * 0.95
    return col


def h_leaf(c, ctx):
    E, own = ctx['leaf']
    i = own[c.x, c.y]
    cx, cy, ang, R = _fparams(E, i, 'x'), _fparams(E, i, 'y'), _fparams(E, i, 'ang'), _fparams(E, i, 'R', 10)
    ux, uy = np.cos(ang), np.sin(ang)
    u = (c.xw - cx) * ux + (c.y - cy) * uy
    v = -(c.xw - cx) * uy + (c.y - cy) * ux
    Wh = 0.6 * R
    wv = Wh * np.sqrt(np.clip(1 - (u / R) ** 2, 0, 1))
    pal = np.array([(178, 126, 52), (168, 120, 62), (144, 122, 60), (172, 138, 58)], float)
    base = pal[np.abs(i) % 4]
    col = base * (0.95 + 0.1 * c.a)[:, None]
    edge = np.abs(v) > wv - 1.4
    col[edge] = col[edge] * 0.55 + np.array([124, 88, 54]) * 0.45
    mid = np.abs(v) < 0.8
    col[mid] = (196, 164, 100)
    lat = (np.abs(((u * 0.8 + np.abs(v)) % 5) - 2.5) < 0.45) & ~mid & ~edge
    col[lat] *= 1.12
    spot = _h(c.x // 2, c.y // 2, 0, 52) > 0.965
    col[spot] = (112, 78, 46)
    col[~c.up] *= 0.88
    return col


def h_cap(c, ctx, inner=False):
    E, own = ctx['cap']
    i = own[c.x, c.y]
    cx, cy, R = _fparams(E, i, 'x'), _fparams(E, i, 'y'), _fparams(E, i, 'R', 7)
    rr = np.hypot(c.xw - cx, c.y - cy)
    th = np.arctan2(c.y - cy, c.xw - cx)
    if inner:
        col = np.array([188.0, 182, 164]) * (0.97 + 0.05 * c.h)[:, None]
        col[np.abs(rr - (R - 3.2)) < 0.6] *= 0.9
        return col
    axis = np.abs(cx - 256) < 1
    enamel = np.where(axis[:, None], np.array([[112, 134, 96]]), np.array([[184, 150, 62]])).astype(float)
    crimp = (np.floor((th + np.pi) / (2 * np.pi) * 24).astype(int) % 2) == 0
    steel = np.array([166.0, 168, 168])
    col = np.where((crimp & (rr > R - 0.4))[:, None], steel[None, :], enamel)
    col[c.up] *= 1.05
    return col * (0.97 + 0.05 * c.h)[:, None]


def h_pinecone(c, ctx, dark=False):
    E, own = ctx['pinecone']
    i = own[c.x, c.y]
    cx, cy, g, R = _fparams(E, i, 'x'), _fparams(E, i, 'y'), _fparams(E, i, 'g', 52), _fparams(E, i, 'R', 7)
    k = g - 1 - c.z
    rr = np.hypot(c.xw - cx, c.y - cy) / np.maximum(R - k, 1)
    col = np.array([96.0, 66, 44] if dark else [126, 88, 54]) * (0.94 + 0.12 * c.h)[:, None]
    tip = c.up & (rr > 0.72)
    col[tip] = (156, 116, 74)
    gap = ~c.up & (c.h < 0.25)
    col[gap] *= 0.8
    res = c.h2 > 0.99
    col[res] = (196, 170, 100)
    return col


# =============================================================================================== hose

def make_hose(S):
    Hs = S['hose']
    path = Hs['path']
    sx0, sx1 = Hs['split']
    F = Hs['feeder']
    g = S['z']['lawn']
    ra, rb = F['rut']

    def phi_col(s, dzc, rr_out, along, h, bead_key, a):
        rho = np.hypot(s, dzc)
        phi = np.degrees(np.arctan2(-dzc, s))
        col = np.array([46.0, 118, 58]) * (0.97 + 0.05 * a)[:, None]
        col[(along % 4) < 1] *= 0.95                          # ribbing (low contrast: no flicker)
        dphi = np.abs(phi - 90)
        outer = rho >= rr_out - 1.6
        st = outer & (dphi < 16)
        col[st] = (206, 182, 66)
        soft = outer & (dphi >= 16) & (dphi < 23)
        col[soft] = col[soft] * 0.5 + np.array([206, 182, 66]) * 0.5
        dirt = phi < -40
        col[dirt] = col[dirt] * 0.7 + np.array([104, 80, 58]) * 0.3
        bead = outer & (((phi > 25) & (phi < 75)) | ((phi > 105) & (phi < 155))) & (bead_key > 0.972)
        col[bead] = (182, 206, 200)
        col[bead & (h > 0.5)] = (204, 214, 210)
        return col, rho

    def h_hose(c):
        col = np.zeros((len(c.x), 3))
        feeder = (np.abs(c.x - 256) <= 6) & (c.y >= 112) & (c.y <= 170)
        reel = (c.x >= 481) & (c.y >= 110) & (c.y <= 156)
        main = ~feeder
        if main.any():
            m = _sub(c, main)
            d, bx, by = polyline_field(path, m.xw.astype(float), m.y.astype(float))
            czc = np.round(Hs['cz'] - hose_lift(S, bx))
            cm, rho = phi_col(m.y - by, m.z - czc, Hs['r_out'], bx, m.h, _h(m.xw // 2, m.y // 2, m.z // 2, 61), m.a)
            inner = rho < Hs['r_in'] + 1.2
            cm[inner] = np.array([36.0, 90, 46]) * (0.95 + 0.1 * m.h[inner])[:, None]
            torn = ((bx >= sx0) & (bx <= sx0 + 2)) | ((bx >= sx1 - 2) & (bx <= sx1))
            cm[torn] = cm[torn] * 0.5 + np.array([128, 150, 120]) * 0.5
            fib = torn & (m.h > 0.7)
            cm[fib] = (186, 170, 110)
            col[main] = cm
        if feeder.any():
            m = _sub(c, feeder)
            dist = np.maximum(np.maximum(ra - m.y, m.y - rb), 0)
            czy = g - F['r_out'] + np.maximum(0, 2 * F['r_out'] - dist)
            cf, _ = phi_col(m.x - 256.0, m.z - czy, F['r_out'], m.y.astype(float), m.h,
                            _h(m.x // 2, m.y // 2, m.z // 2, 62), m.a)
            col[feeder] = cf
        if reel.any():
            m = _sub(c, reel)
            stripe_here = c.mat_name[reel] == 'hose_stripe'
            cr = np.array([44.0, 112, 56]) * (0.9 + 0.1 * ((m.y % 2) == 0))[:, None]
            cr[stripe_here] = cr[stripe_here] * 0.55 + np.array([206, 182, 66]) * 0.45
            col[reel] = cr
        return col
    return h_hose


def h_reel(c):
    return np.array([44.0, 112, 56]) * (0.9 + 0.1 * ((c.y % 2) == 0) + 0.04 * c.h)[:, None]


def h_coupling(c):
    col = np.array([182.0, 148, 70]) * (0.96 + 0.06 * c.h)[:, None]
    col[(c.x + c.y + c.z) % 3 == 0] *= 0.85
    pat = c.b > 0.62
    col[pat & ~c.up] = col[pat & ~c.up] * 0.6 + np.array([120, 150, 124]) * 0.4
    return col


# =============================================================================================== sprinkler

HUB = (256, 210)


def _spangle(c, base, cell=3):
    return np.array(base, float) * (0.96 + 0.07 * _h(c.x // cell, c.y // cell, c.z // cell, 21) +
                                    0.03 * c.v)[:, None]


def h_pad(c):
    col = _spangle(c, (146, 150, 150))
    wet = c.up & (c.h2 > 0.985)
    col[wet] = (186, 200, 198)
    col[c.z >= 51] = col[c.z >= 51] * 0.8 + np.array(SOIL) * 0.2
    return col


def h_leg(c):
    col = _spangle(c, (150, 154, 158))
    scuff = c.v > 0.62
    col[scuff] = col[scuff] * 0.7 + np.array([124, 114, 100]) * 0.3
    low = c.z >= 46
    col[low] = col[low] * 0.75 + np.array(SOIL) * 0.25
    bead = c.up & (c.h2 > 0.985)
    col[bead] = (188, 204, 202)
    return col


def h_rivet(c):
    col = np.tile(np.array([[104.0, 106, 112]]), (len(c.x), 1))
    col[c.up] = (138, 140, 146)
    return col


def h_collar(c):
    a = np.arctan2(c.y - HUB[1], c.x - HUB[0])
    col = np.array([206.0, 118, 46]) * (0.97 + 0.05 * c.h)[:, None]
    col[np.abs(np.sin(6 * a)) < 0.07] *= 0.88
    col[c.up] *= 1.03
    sc = c.h2 > 0.975
    col[sc] = (210, 150, 96)
    return col


def h_riser(c):
    col = _spangle(c, (148, 150, 154), 2)
    col[(np.abs(c.x - HUB[0]) <= 0) & (c.y < HUB[1])] *= 0.88
    return col


def h_brass(c):
    col = np.array([184.0, 150, 72]) * (0.95 + 0.08 * c.h)[:, None]
    groove = ~c.up & (c.z % 2 == 0)
    col[groove] *= 0.86
    col[c.up] = np.array([198.0, 166, 86]) * (0.96 + 0.06 * c.h[c.up])[:, None]
    pat = ~c.up & (c.b > 0.64)
    col[pat] = col[pat] * 0.65 + np.array([120, 150, 124]) * 0.35
    return col


def h_step(c):
    snail = (c.x > 380) & (c.y < 100)
    col = np.array([176.0, 140, 66]) * (0.92 + 0.12 * _h(c.z, 0, 0, 53))[:, None]
    col[~c.up & (c.z % 2 == 0)] *= 0.9
    col[snail] = np.array([176.0, 160, 140]) * (0.95 + 0.08 * c.h[snail])[:, None]
    return col


def h_arm(c):
    col = np.array([160.0, 128, 66]) * (0.95 + 0.08 * c.h)[:, None]
    col[(c.y % 4) == 0] *= 0.9
    return col


def h_tbar(c):
    col = np.array([190.0, 158, 76]) * (0.96 + 0.06 * c.h)[:, None]
    hole = ~c.up & ((c.x % 4) == 0)
    col[hole] = (78, 66, 44)
    return col


def h_spring(c):
    return np.where(((c.y % 2) == 0)[:, None], np.array([[116, 116, 122]]), np.array([[80, 80, 86]])).astype(float)


# =============================================================================================== trowel

def make_trowel(S):
    B = S['trowel']['blade']
    bx0, bx1 = B['x']
    by0, by1 = B['y']
    hw_full = (bx1 - bx0) / 2

    def h_steel(c):
        col = np.array([164.0, 168, 172]) * (0.96 + 0.08 * _h(c.x, c.y // 6, 0, 31))[:, None]
        hw = hw_full * np.clip((by1 - c.y) / 18.0, 0, 1) ** 0.7
        bev = np.abs(c.x - 256) >= hw - 1.2
        col[bev] = (190, 192, 196)
        s = np.clip((c.y - (by1 - 16)) / 16.0, 0, 1) * (0.35 + 0.65 * c.b)
        s = np.maximum(s, np.clip((c.z - 47) / 5.0, 0, 1) * 0.8)
        col = col * (1 - 0.75 * s)[:, None] + np.array([112, 86, 62]) * (0.75 * s)[:, None]
        rust = _h(c.x, c.y, c.z, 41) > 0.982
        col[rust] = (150, 94, 58)
        bloom = (c.e > 0.7) & (c.h > 0.75)
        col[bloom] = col[bloom] * 0.5 + np.array([140, 98, 68]) * 0.5
        return col

    def h_rib(c):
        col = np.array([150.0, 154, 158]) * (0.97 + 0.05 * c.h)[:, None]
        s = np.clip((c.y - (by1 - 14)) / 14.0, 0, 1) * 0.6
        return col * (1 - s)[:, None] + np.array([112, 86, 62]) * s[:, None]
    return h_steel, h_rib


def h_handle(c):
    g = np.sin(c.x * 1.3 + c.z * 0.9 + 2.0 * np.sin(c.y * 0.12))
    col = np.array([176.0, 136, 70]) * (1 + 0.07 * g)[:, None]
    knot = (np.hypot(c.y - 290, (c.x - 255) * 1.5) < 2.2) | (np.hypot(c.y - 297, (c.x - 258) * 1.5) < 1.6)
    col[knot] = (128, 94, 50)
    col[c.up] *= 1.04
    worn = c.up & (c.c > 0.7)
    col[worn] = col[worn] * 0.7 + np.array([196, 166, 110]) * 0.3
    return col


def h_ferrule(c):
    col = np.array([156.0, 158, 162]) * (0.96 + 0.06 * c.h)[:, None]
    col[~c.up & ((c.y % 2) == 0)] *= 0.9
    cap = (c.y <= 281) & c.up
    ring = cap & (np.abs(np.hypot(c.x - 256, c.y - 276) - 1.8) < 0.7)
    col[ring] = (104, 104, 108)
    return col


# =============================================================================================== one-offs

def h_concrete(c):
    col = np.array([158.0, 156, 148]) * (0.91 + 0.18 * _h(c.x // 2, c.y // 2, c.z // 2, 5))[:, None]
    stain = ~c.up & (c.v > 0.6)
    col[stain] *= 0.9
    moss = ~c.up & (c.z >= 49)
    col[moss] = col[moss] * 0.6 + np.array(MOSS) * 0.4
    lich = c.up & (c.e > 0.68)
    col[lich] = col[lich] * 0.4 + np.array([170, 168, 110]) * 0.6
    return col


def h_tap(c):
    col = np.array([184.0, 150, 72]) * (0.95 + 0.08 * c.h)[:, None]
    pat = (c.b > 0.56) & ~c.up
    col[pat] = col[pat] * 0.45 + np.array([118, 150, 124]) * 0.55
    col[c.up] *= 1.06
    return col


def h_cart(c):
    col = np.array([126.0, 130, 132]) * (0.94 + 0.1 * c.h)[:, None]
    rust = c.e > 0.66
    col[rust] = col[rust] * 0.6 + np.array([140, 96, 64]) * 0.4
    return col


def make_wheel(S):
    rx, _ = S['oneoffs']['hose_reel']
    cz = S['oneoff_dims']['hose_reel']['drum_cz']

    def h_wheel(c):
        dd = np.hypot(c.x - rx, c.z - cz)
        col = np.array([54.0, 56, 60]) * (0.95 + 0.1 * c.h)[:, None]
        tread = (dd > 8) & (((c.x + c.z) % 2) == 0)
        col[tread] *= 0.88
        hub = dd <= 2.6
        col[hub] = (140, 142, 146)
        return col
    return h_wheel


def make_pot(S):
    px, py = S['oneoffs']['flowerpot']
    O = S['oneoff_dims']['flowerpot']
    xb, xm, rb, rm = O['base_x'], O['mouth_x'], O['r_base'], O['r_mouth']
    g = S['z']['lawn']

    def h_pot(c):
        x = c.x.astype(float)
        r = rb + (rm - rb) * (np.minimum(x, xm) - xb) / (xm - xb)
        czx = g - r - 0.5
        rho = np.hypot(c.y - py, c.z - czx)
        col = np.array([184.0, 106, 66]) * (1 + 0.045 * np.sin(x * 1.7 + 0.3 * c.a))[:, None]
        col *= (0.97 + 0.05 * c.h)[:, None]
        outer = rho >= r - 0.8
        bloom = outer & (c.b > 0.58)
        col[bloom] = col[bloom] * 0.6 + np.array([198, 186, 170]) * 0.4
        moss = outer & (c.z >= g - 4)
        col[moss] = col[moss] * (1 - 0.5 * c.c[moss])[:, None] + np.array([92, 112, 58]) * (0.5 * c.c[moss])[:, None]
        lip = x >= xm - 1
        col[lip] *= 0.93
        inner = (rho < r - 0.9) & (x > xb + 1)
        col[inner] = col[inner] * 0.6 + np.array([96, 72, 56]) * 0.4
        return col
    return h_pot


def make_glove(S):
    O = S['oneoff_dims']['glove']
    px0, px1, py0, py1 = O['palm']

    def h_glove(c, solid):
        col = np.array([96.0, 132, 126]) * (0.97 + 0.06 * (((c.x + c.z) % 2) ^ ((c.y + c.z) % 2)))[:, None]
        dirt = c.b > 0.62
        col[dirt] = col[dirt] * 0.75 + np.array([110, 86, 62]) * 0.25
        wear = c.up & (c.c > 0.7)
        col[wear] = col[wear] * 0.6 + np.array([128, 160, 150]) * 0.4
        # stitching along the upper shell edges
        T = np.argmax(solid, axis=2)
        lower = np.zeros(len(c.x), bool)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            lower |= T[np.clip(c.x + dx, 0, 511), np.clip(c.y + dy, 0, 511)] >= c.z + 2
        seam = c.up & lower
        st = seam & ((c.x + c.y) % 3 == 0)
        col[st] = (198, 186, 152)
        col[seam & ~st] *= 0.86
        return col

    def h_cuff(c):
        col = np.array([176.0, 146, 78]) * (0.95 + 0.06 * c.h)[:, None]
        col[(c.x % 2) == 0] *= 0.92
        ridge = (c.x >= px0) & (c.x <= px1) & (c.y >= py0) & (c.y <= py1)
        col[ridge & (c.y % 3 == 0)] = (110, 90, 56)
        col[ridge & (c.y % 3 != 0)] = (200, 186, 150)
        return col
    return h_glove, h_cuff


def make_shell(S):
    sx, sy = S['oneoffs']['snail_shell']
    O = S['oneoff_dims']['snail_shell']
    R, Rz, cz, th = O['r'], O['rz'], O['cz'], O['wall']

    def h_shell(c, dark=False):
        a = np.arctan2(c.y - sy, c.x - sx)
        band = 0.5 + 0.5 * np.sin(a * 2 + c.z * 0.9)
        band = band * band * (3 - 2 * band)
        cream, brown = np.array([192.0, 166, 122]), np.array([124.0, 88, 58])
        col = cream * (1 - band)[:, None] + brown * band[:, None]
        if dark:
            col = col * 0.72
        col[np.abs(np.sin(a * 30)) < 0.12] *= 0.93
        col *= (0.96 + 0.06 * c.b)[:, None]
        e_in = ((c.x - sx) / (R - th)) ** 2 + ((c.y - sy) / (R - th)) ** 2 + ((c.z - cz) / (Rz - th)) ** 2
        inner = e_in <= 1.25
        col[inner] = col[inner] * 0.4 + np.array([190, 176, 166]) * 0.6
        crown = (c.z <= O['deck_z'] + 2) & (np.hypot(c.x - sx, c.y - sy) <= O['hole_r'] + 1.5) & ~dark
        col[crown] = (186, 176, 158)
        return col
    return h_shell


def h_label(c):
    col = np.array([196.0, 198, 186]) * (0.97 + 0.04 * c.h)[:, None]
    col[c.h2 > 0.93] *= 0.95
    col[~c.up] = col[~c.up] * 0.9 + np.array([90, 120, 80]) * 0.1
    splash = c.z >= 46
    s = np.clip((c.z - 46) / 6.0, 0, 1) * c.b
    col[splash] = col[splash] * (1 - 0.6 * s[splash])[:, None] + np.array(SOIL) * (0.6 * s[splash])[:, None]
    return col


def h_key(c):
    col = np.array([98.0, 98, 102]) * (0.95 + 0.08 * c.h)[:, None]
    rust = c.b > 0.55
    t = np.clip((c.b - 0.55) * 3, 0, 0.7)
    col[rust] = col[rust] * (1 - t[rust])[:, None] + np.array([134, 88, 58]) * t[rust][:, None]
    col[c.up & ~rust] = (126, 126, 130)
    return col


def h_stair(c):
    conc = c.x < 100
    col = np.zeros((len(c.x), 3))
    col[conc] = np.array([150.0, 148, 140]) * (0.93 + 0.12 * c.h[conc])[:, None]
    w = ~conc
    col[w] = np.array([150.0, 116, 76]) * (1 + 0.06 * np.sin(c.x[w] * 1.1 + c.z[w] * 2.0))[:, None]
    return col


def h_floor(c):
    nac = (c.x > 380) & (c.y < 100)
    col = np.array([150.0, 118, 80]) * (0.95 + 0.08 * c.h)[:, None]
    col[(c.y % 4) == 0] *= 0.85
    col[nac] = np.array([172.0, 160, 146]) * (0.95 + 0.08 * c.h[nac])[:, None]
    return col


def make_brick(S):
    E = S['edging']
    period = E['brick_len'] + E['gap']
    y0, y1, top = E['y'][0], E['y'][1], E['top_z']

    def h_brick(c):
        idx = c.xw // period
        within = c.xw % period
        tint = 0.92 + 0.14 * _h(idx, c.east.astype(int), 0, 55)
        col = np.array([152.0, 92, 70]) * tint[:, None]
        col = col * 0.85 + np.array([180, 164, 144]) * 0.15
        col *= (0.96 + 0.06 * c.h)[:, None]
        nx = (within <= 0) | (within >= E['brick_len'] - 1)
        ny = (c.y <= y0) | (c.y >= y1)
        edge = (nx & ny) | ((nx | ny) & (c.z <= top))           # brick arrises only
        chip = edge & (c.h2 > 0.6)
        col[chip] = (170, 162, 150)
        moss_t = c.up & edge & (c.b > 0.5)
        col[moss_t] = col[moss_t] * 0.5 + np.array([98, 114, 62]) * 0.5
        moss_s = ~c.up & (c.z >= 54) & (c.c > 0.45)
        col[moss_s] = col[moss_s] * 0.6 + np.array(MOSS) * 0.4
        frog = c.up & (c.z == top + 1)
        col[frog] *= 0.82
        return col
    return h_brick


# =============================================================================================== blades

FAMILIES = {
    'emerald': ([(0, (70, 96, 52)), (0.25, (52, 118, 58)), (0.6, (58, 142, 70)), (1, (96, 170, 86))], 0.30),
    'chartreuse': ([(0, (96, 104, 52)), (0.25, (110, 140, 50)), (0.6, (140, 170, 58)), (1, (176, 196, 90))], 0.22),
    'olive': ([(0, (90, 88, 52)), (0.25, (98, 110, 56)), (0.6, (116, 130, 62)), (1, (146, 150, 82))], 0.20),
    'teal': ([(0, (60, 90, 64)), (0.25, (48, 112, 86)), (0.6, (56, 134, 104)), (1, (92, 160, 128))], 0.18),
    'dry straw': ([(0, (110, 96, 60)), (0.25, (150, 132, 76)), (0.6, (176, 156, 92)), (1, (196, 178, 116))], 0.10),
}


def paint_blades(cv, rep, seed):
    mid = cv.materials.get('blade')
    plants = {p['id']: p for p in rep.get('art_plants', []) if p['kind'] == 'blade'}
    names = list(FAMILIES)
    w = np.array([FAMILIES[k][1] for k in names])
    counts = {k: 0 for k in names}
    n_vox = 0
    for side in ('W', 'E'):
        rng = noise.rng('blades' + side, seed)
        # one calm family per tussock (groves of close colours, not confetti); blades vary by a small tint and,
        # rarely, a neighbouring family
        tfam = {}
        for bi, br in enumerate(rep.get('blade_records', [])):
            t = br['tussock']
            if t not in tfam:
                tfam[t] = int(rng.choice(len(names), p=w / w.sum()))
            fi = tfam[t]
            if rng.random() < 0.18:
                fi = (fi + (1 if rng.random() < 0.5 else -1)) % len(names)
            fam = names[fi]
            jit = 1 + rng.normal(0, 0.025, 3)
            fw = rng.uniform(0.6, 0.8)
            fn = rng.uniform(0.35, 0.65)
            notch_side = int(rng.integers(0, 2))
            if not br['vox']:
                continue
            v = np.array(br['vox'], float)
            x, y, z = v[:, 0].astype(int), v[:, 1].astype(int), v[:, 2].astype(int)
            if side == 'E':
                x = 512 - x
            f, a, b, wd = v[:, 3], v[:, 4].astype(int), v[:, 5].astype(int), v[:, 6].astype(int)
            col = color.ramp(FAMILIES[fam][0], f) * jit[None, :]
            col[(a == 0) & (wd >= 2)] *= 1.05                        # midrib
            amin, amax = -(wd // 2), wd - wd // 2 - 1
            edge = (wd == 3) & ((a == amin) | (a == amax))
            col[edge] *= 0.96
            col *= (1 + 0.015 * np.sin(z * 0.5 + bi))[:, None]
            dets = set(plants.get(bi, {}).get('details', ()))
            if 'withered tip' in dets:
                t = np.clip((f - fw) / (1 - fw), 0, 1)
                col = col * (1 - 0.85 * t)[:, None] + np.array([178, 154, 96]) * (0.85 * t)[:, None]
                col[t > 0.8] = (140, 114, 72)
            if 'chewed notch' in dets:
                Hb = max(br['Hb'], 1)
                es = np.where(notch_side == 0, amin, amax)
                band = np.abs(f - fn) * Hb
                bite = (band < 2.5) & (a == es) & (wd >= 2)
                col[bite] = (176, 160, 104)
                ring = (band < 4.5) & (a == es) & ~bite
                col[ring] *= 0.8
            if 'aphids' in dets:
                cand = np.nonzero((f > 0.3) & (f < 0.85))[0]
                if len(cand):
                    sel = rng.choice(cand, size=min(6, len(cand)), replace=False)
                    col[sel[:4]] = (178, 206, 108)
                    col[sel[4:]] = (150, 184, 90)
            if 'moss collar' in dets:
                m = f < 0.13
                col[m] = np.array(MOSS) * (0.9 + 0.2 * _h(x[m], y[m], z[m], 57))[:, None]
            if 'pollen dusting' in dets:
                m = (f > 0.45) & (_h(x, y, z, 58) > 0.8)
                col[m] = col[m] * 0.4 + np.array([206, 192, 112]) * 0.6
            if 'wet streak' in dets:
                m = (a == 0) & (f > 0.3) & (f < 0.95)
                col[m] = col[m] * 1.14 + np.array([0, 4, 8])
            ok = cv.mat[x, y, z] == mid
            cv.rgb[x[ok], y[ok], z[ok]] = np.clip(col[ok], 0, 255).astype(np.uint8)
            n_vox += int(ok.sum())
            counts[fam] += 1
    return {'families': counts, 'blade_voxels_painted': n_vox}


# =============================================================================================== main

_FIELDS = {}


def fields(seed):
    if seed not in _FIELDS:
        _FIELDS[seed] = {
            'a': noise.fbm2((512, 512), 9, 3, 'pA', seed), 'b': noise.fbm2((512, 512), 23, 3, 'pB', seed),
            'c': noise.fbm2((512, 512), 4, 2, 'pC', seed), 'd': noise.fbm2((512, 512), 60, 2, 'pD', seed),
            'e': noise.fbm2((512, 512), 14, 2, 'pE', seed),
            'vxz': noise.fbm2((512, 64), 6, 2, 'vxz', seed), 'vyz': noise.fbm2((512, 64), 6, 2, 'vyz', seed)}
    return _FIELDS[seed]


def surface_masks(solid):
    P = np.pad(solid, 1, constant_values=True)
    P[:, :, 0] = False
    air = ~P
    up = solid & air[1:-1, 1:-1, :-2]
    surf = up | (solid & (air[:-2, 1:-1, 1:-1] | air[2:, 1:-1, 1:-1] | air[1:-1, :-2, 1:-1] | air[1:-1, 2:, 1:-1] |
                          air[1:-1, 1:-1, 2:]))
    return surf, up


def paint(cv, rep, S, seed):
    with np.errstate(over='ignore', invalid='ignore'):
        return _paint(cv, rep, S, seed)


def _paint(cv, rep, S, seed):
    F = fields(seed)
    mats = cv.materials
    names = {v: k for k, v in mats.items()}
    skip_ids = [mats[m] for m in SKIP if m in mats]
    skipm = cv.nolight | np.isin(cv.mat, skip_ids)
    surf, up = surface_masks(cv.solid)
    lut = np.zeros((max(mats.values()) + 1, 3))
    for k, v in mats.items():
        lut[v] = BASE.get(k, SOIL)
    # ---------------------------------------------------------------- interior (never seen unless dug)
    soil_ids = [mats[m] for m in ('soil', 'lawn', 'spawn', 'front', 'anchor', 'bank', 'trail', 'tunnel', 'crater')
                if m in mats]
    band = np.array([_r([(0, (96, 72, 52)), (0.5, (112, 86, 62)), (1, (130, 100, 70))],
                        np.array([0.5 + 0.5 * math.sin(z * 1.9)]))[0] for z in range(64)])
    for x0 in range(0, 512, 64):
        sl = slice(x0, x0 + 64)
        inter = cv.solid[sl] & ~surf[sl] & ~skipm[sl]
        xi, yi, zi = np.nonzero(inter)
        m = cv.mat[sl][xi, yi, zi]
        col = lut[m]
        so = np.isin(m, soil_ids)
        col[so] = band[zi[so]] * (0.95 + 0.1 * _h(xi[so] + x0, yi[so], zi[so], 3))[:, None]
        cv.rgb[sl][xi, yi, zi] = np.clip(col, 0, 255).astype(np.uint8)
    # ---------------------------------------------------------------- surface
    xs, ys, zs = np.nonzero(surf & ~skipm)
    C = _context(cv, xs, ys, zs, F, up)
    m = cv.mat[xs, ys, zs]
    C.mat_name = np.array([names[int(i)] for i in range(lut.shape[0])], object)[m]
    out = lut[m].copy()
    E = _features(rep)
    ctx = {'dets': {p['name']: p['details'] for p in rep.get('art_plants', []) if 'name' in p},
           'fam': list(noise.rng('clover_fam', seed).integers(0, 4, 64)), 'salt': int(seed % 5)}
    for grp, kinds in GROUPS.items():
        ents = [e for e in E if e['f']['kind'] in kinds]
        ctx[grp] = (ents, _owner(ents, 4 if grp != 'twig' else 3))
    h_steel, h_rib = make_trowel(S)
    h_glove, h_cuff = make_glove(S)
    h_shell = make_shell(S)
    H = {
        'soil': h_soil, 'lawn': h_lawn, 'spawn': h_spawn, 'front': h_front, 'anchor': h_anchor, 'bank': h_bank,
        'trail': h_trail, 'puddle': make_puddle(S), 'crater': h_crater, 'tunnel': h_tunnel, 'heap': h_heap,
        'print': h_print, 'potsoil': h_potsoil, 'dew': h_dew,
        'crown': lambda c: h_crown(c, ctx), 'clover': lambda c: h_clover(c, ctx), 'stalk': lambda c: h_stalk(c, ctx),
        'dandelion_stalk': lambda c: h_dstalk(c, ctx), 'seedhead': lambda c: h_seedhead(c, ctx),
        'mushroom_cap': lambda c: h_mcap(c, ctx), 'mushroom_stem': lambda c: h_mstem(c, ctx),
        'daisy': lambda c: h_daisy(c, ctx), 'daisy_eye': lambda c: h_daisy_eye(c, ctx),
        'sprout': lambda c: h_sprout(c, ctx), 'seed': lambda c: h_seed(c, ctx), 'pebble': lambda c: h_pebble(c, ctx),
        'acorn': lambda c: h_acorn(c, ctx), 'acorn_cap': lambda c: h_acorn_cap(c, ctx),
        'twig': lambda c: h_twig(c, ctx), 'leaf': lambda c: h_leaf(c, ctx), 'cap': lambda c: h_cap(c, ctx),
        'cap_inner': lambda c: h_cap(c, ctx, inner=True), 'pinecone': lambda c: h_pinecone(c, ctx),
        'pinecone_dk': lambda c: h_pinecone(c, ctx, dark=True),
        'hose': make_hose(S), 'hose_stripe': make_hose(S), 'reel': h_reel, 'coupling': h_coupling,
        'pad': h_pad, 'leg': h_leg, 'rivet': h_rivet, 'collar': h_collar, 'riser': h_riser, 'brass': h_brass,
        'step': h_step, 'arm': h_arm, 'tbar': h_tbar, 'spring': h_spring,
        'blade_steel': h_steel, 'rib': h_rib, 'handle': h_handle, 'ferrule': h_ferrule,
        'concrete': h_concrete, 'tap': h_tap, 'cart': h_cart, 'wheel': make_wheel(S), 'pot': make_pot(S),
        'glove': lambda c: h_glove(c, cv.solid), 'glove_cuff': h_cuff, 'shell': h_shell,
        'shell_dk': lambda c: h_shell(c, dark=True), 'label': h_label, 'key': h_key, 'stair': h_stair,
        'floor': h_floor, 'brick': make_brick(S),
    }
    # hose + hose_stripe share one handler call (the stripe is drawn from the tube geometry, not the material)
    done = np.zeros(len(xs), bool)
    counts = {}
    for name, fn in H.items():
        if name == 'hose_stripe':
            continue
        if name == 'hose':
            k = np.isin(m, [mats[n] for n in ('hose', 'hose_stripe') if n in mats])
        else:
            if name not in mats:
                continue
            k = m == mats[name]
        if not k.any():
            continue
        out[k] = fn(_sub(C, k))
        done |= k
        counts[name] = int(k.sum())
    cv.rgb[xs, ys, zs] = np.clip(np.rint(out), 0, 255).astype(np.uint8)
    blades = paint_blades(cv, rep, seed)
    unhandled = sorted({names[int(i)] for i in np.unique(m[~done])} - {'blade'})   # blades: paint_blades
    return {'surface_voxels': int(len(xs)), 'by_material': counts, 'unhandled_materials': unhandled, 'blades': blades}


def retexture_tag_strip(cv, rect, keep_cols, seed):
    """After paint_tag levels the strip: give the strip's non-letter top voxels a tamped-soil texture."""
    bx0, bx1, by0, by1, z = rect
    F = fields(seed)
    xs, ys = np.meshgrid(np.arange(bx0, bx1 + 1), np.arange(by0, by1 + 1), indexing='ij')
    xs, ys = xs.ravel(), ys.ravel()
    zs = np.full(len(xs), z)
    cur = cv.rgb[xs, ys, zs]
    letter = np.zeros(len(xs), bool)
    for kc in keep_cols:
        letter |= (cur == np.array(kc)).all(1)
    _, up = surface_masks(cv.solid)
    with np.errstate(over='ignore'):
        C = _context(cv, xs, ys, zs, F, up)
        col = _mix(lawn_top(C) * 0.97, (120, 100, 70), 0.35)
    k = ~letter
    cv.rgb[xs[k], ys[k], zs[k]] = np.clip(col[k], 0, 255).astype(np.uint8)
    for x, y in zip(xs, ys):                                     # mat for levelled voxels (paint_tag leaves 0)
        for zz in range(z, 64):
            if cv.mat[x, y, zz] == 0 and cv.solid[x, y, zz]:
                cv.mat[x, y, zz] = cv.material('soil')
    cv.mat[xs, ys, zs] = cv.material('lawn')
    return int(k.sum())
